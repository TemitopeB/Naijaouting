# NaijaOuting

Website that gathers events from ticket sites, organisers and flyers, checks them, and sends you to the official seller.

- `/` landing page (`index.html`, reads `data/landing.json`)
- `/events/` the main site: map, list, calendar, event pages, Add event, Review queue
- `/admin/` admin sign-in

Hosting: **Vercel** (free). Database, logins and flyer uploads: **Supabase** (free tier). Scheduled jobs: **GitHub Actions** (free).

---

## One-time setup

### 1. Create the Supabase project
1. Sign in at [supabase.com](https://supabase.com) (you can use GitHub) → **New project**.
   Name: `naijaouting`. Region: **West EU (London)** or the closest one offered. Save the database password somewhere safe.
2. When it's ready, open **SQL Editor → New query**, paste everything from [`supabase/schema.sql`](supabase/schema.sql), press **Run**.
3. New query again: paste [`supabase/import.sql`](supabase/import.sql) and press **Run**. This copies your current events and fixes.
4. New query again: paste [`supabase/security.sql`](supabase/security.sql) and press **Run**. This adds anti-spam limits (size and count limits for visitors, a cap on daily flyer uploads) and keeps scam reports private.

### 2. Allow visitors to submit without an account
**Authentication → Sign In / Providers** (may be called "Auth Providers") → turn on **Allow anonymous sign-ins** → Save.
Visitors get an invisible guest session, so they can send events and corrections without signing up.

### 3. Connect the website to Supabase
**Project Settings → API** (or the **Connect** button). Copy:
- **Project URL** (looks like `https://abcd1234.supabase.co`)
- **anon / publishable key** (safe to publish)

Put both in [`js/config.js`](js/config.js), and put the project URL in [`vercel.json`](vercel.json) in place of `YOUR-PROJECT`.
**Never** put the `service_role` / secret key in the website files.

### 4. Put the site online with Vercel
1. Sign in at [vercel.com](https://vercel.com) with GitHub → **Add New → Project** → import **Naijaouting**.
2. Framework preset: **Other**. No build command. Press **Deploy**.
3. Optional: **Settings → Domains** to set `naijaouting.vercel.app`, and later your own domain.
Every change saved to GitHub now goes live automatically in about a minute.

### 5. Make yourself an admin
1. Supabase → **Authentication → Users → Add user → Create new user**: your email and a strong password, tick **Auto confirm**.
2. SQL Editor, run (with your email):
   ```sql
   insert into public.admins (user_id) select id from auth.users where email = 'you@example.com';
   ```
3. Open `https://YOUR-SITE.vercel.app/admin/`, sign in, then press **Review** on the site.

### 6. Turn on the scheduled jobs
GitHub → this repository → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value | Used by |
|---|---|---|
| `SUPABASE_URL` | Project URL | both jobs |
| `SUPABASE_ANON_KEY` | anon / publishable key | daily landing refresh |
| `SUPABASE_SERVICE_KEY` | **service_role / secret key** (keep private) | Monday sweep |
| `EVENTBRITE_TOKEN` | optional, Eventbrite private token | Monday sweep, Eventbrite sources |
| `GEMINI_API_KEY` | Google AI Studio API key (starts with `AQ.`) | smart sweep and news lead pre-fill |

Then **Actions** tab → enable workflows if asked. Test each with **Run workflow**.

---

## What runs automatically

| When | Job | What it does |
|---|---|---|
| Every morning, 06:23 Lagos | **News and event leads** | Refreshes the news ticker (`data/news.json`) from Nigerian news feeds, and lists articles that look like upcoming event announcements on `/admin/` as leads. |
| Every morning, 06:11 Lagos | **Refresh landing data** | Rebuilds `data/landing.json` from the site + database, so landing numbers stay current. |
| Every morning, 07:41 Lagos | **Event reminders** | Emails signed-in visitors about saved events that start tomorrow (needs the email secrets). |
| Mondays, 07:37 Lagos | **Monday event sweep** | Reads the sources in `scripts/sources.json`, then the **smart sweep** has Google Gemini search the web for upcoming Nigerian events (next 8 weeks, 6 regions × 3 themes). New events go to the **Review queue**; each shows where it was found. |
| Any time | Visitors | "Add event" and corrections go to the Review queue. |
| Any time | You | Approve, edit or hide events on the site after signing in at `/admin/`. Approved events go live instantly. |

Nothing from the sweep or from visitors goes live until an admin approves it.

## Visitor accounts (sign in with Google or an email code)
Optional for visitors. Signing in gives them saved events, tourism list and trip on every device, an email reminder the day before a saved event, and **Your account → My submissions** (waiting / approved / not approved). Anything saved or sent in as a guest moves into the account. Code: `js/account.js`, rules: `supabase/accounts.sql`, reminders: `scripts/reminders.py`.

Until it's switched on, only admins see **Sign in** (so you can test with your own email). Setup, once:

1. **Database rules.** Supabase → SQL Editor → New query → paste [`supabase/accounts.sql`](supabase/accounts.sql) → Run.
2. **Website address.** Supabase → Authentication → URL Configuration: Site URL `https://naijaouting-ng.vercel.app`; add Redirect URL `https://naijaouting-ng.vercel.app/**`.
3. **Email service (needed for codes and reminders).** Supabase's built-in email only sends to your own team. Create a free account with an email service such as Brevo (300 emails a day free), verify the sender address, and copy its SMTP details.
   - Supabase → Authentication → Emails → SMTP Settings → turn on custom SMTP and paste them.
   - Supabase → Authentication → Emails → Templates: in **Magic Link** and **Confirm signup**, add the code line `Your NaijaOuting code is {{ .Token }}` so visitors get a 6-digit code.
   - GitHub → Settings → Secrets → Actions: add `SMTP_HOST`, `SMTP_PORT` (usually 587), `SMTP_USER`, `SMTP_PASS`, `MAIL_FROM` (e.g. `NaijaOuting <you@yourmail.com>`) for the reminder emails.
4. **Google sign-in (optional but recommended).** Google Cloud Console → APIs & Services → OAuth consent screen (External, app name NaijaOuting) → Credentials → Create OAuth client ID (Web application) with Authorized redirect URI `https://fcdebtyopthaikonnfsd.supabase.co/auth/v1/callback`. Paste the Client ID and secret into Supabase → Authentication → Sign In / Providers → Google → Enable.
5. **Test** on the site as admin: Sign in (top right) with another email, save an event, check Your account.
6. **Switch on for everyone:** in [`js/config.js`](js/config.js) set `accounts: true`.

The sign-in window only shows the methods that are switched on in Supabase. Reminder emails run every morning at 07:41 Lagos (**Event reminders** in the Actions tab); without the email secrets the job only counts.

## News feeds and event leads
The feeds are listed in [`scripts/news_feeds.json`](scripts/news_feeds.json) (Premium Times, Vanguard, The Guardian Nigeria, Channels TV, Punch, TheCable, Daily Post, BusinessDay, BellaNaija, Notjustok, TechCabal). Set `"on": false` to stop using one.
Only headlines and links are used, always credited to the outlet. Leads appear on `/admin/` after you sign in: read the article, then **Add as event** or **Dismiss**.

## Smart sweep (Gemini)
`scripts/smart_sweep.py` uses the `GEMINI_API_KEY` secret. Gemini searches Google and returns events; an event is kept only if its source is one of the pages Google actually returned, its date is in the next 8 weeks, and it isn't already listed. A source on an official ticket site becomes the ticket link; any other source is shown in the description for you to check. Free tier: about 18 requests per Monday. Set `GEMINI_MODEL` (repository variable or env) to force a model.

**Web search needs billing.** On Google's free tier Gemini can read text (used for the news lead pre-fill) but cannot search Google. To use the smart sweep, turn on billing for the Google AI Studio project: Gemini 3+ models include 5,000 free web searches a month, which covers the sweep (about 80 a month); the AI's reading costs well under $1 a month at this size. Set a budget alert in Google Cloud billing. Without billing, the smart sweep stops at once and the rest keeps working.

## Adding sweep sources
Edit [`scripts/sources.json`](scripts/sources.json) on GitHub, set `"on": true`, save. Supported:
- `page`: a website that publishes schema.org Event data (many organiser and venue sites do)
- `ics`: a public calendar feed
- `eventbrite_organizer`: an organiser on Eventbrite, through the official API (needs `EVENTBRITE_TOKEN`)

Only add sources whose terms allow automated reading. The sweep respects robots.txt and waits between requests.
Each run's summary (Actions tab → the run) shows how many events each source gave.

## Security notes
- Secrets (service key, Gemini key, email password) live only in GitHub secrets, never in site files. The anon key in `js/config.js` is public by design.
- Scam reports never switch an event off by themselves: in Review, choose **Show warning** to warn visitors, **Hide now**, or **Not a scam**.
- Security headers are set in `vercel.json`; `.vercelignore` keeps scripts and SQL off the website.
- Turn on two-step verification for GitHub, Vercel, Supabase and Google, and use a strong unique admin password.

## Notes
- Reading flyers automatically with AI isn't available on this version; type details in, or add an AI service later.
- Flyers uploaded through the site are stored in Supabase Storage (bucket `flyers`) and shown at `/_blob/...`.
- Flyers from the Claude version are in `_blob/` and `events/flyers/`.
