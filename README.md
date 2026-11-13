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

Then **Actions** tab → enable workflows if asked. Test each with **Run workflow**.

---

## What runs automatically

| When | Job | What it does |
|---|---|---|
| Every morning, 06:23 Lagos | **News and event leads** | Refreshes the news ticker (`data/news.json`) from Nigerian news feeds, and lists articles that look like upcoming event announcements on `/admin/` as leads. |
| Every morning, 06:11 Lagos | **Refresh landing data** | Rebuilds `data/landing.json` from the site + database, so landing numbers stay current. |
| Mondays, 07:37 Lagos | **Monday event sweep** | Reads the sources in `scripts/sources.json`, adds new upcoming events to the **Review queue**. |
| Any time | Visitors | "Add event" and corrections go to the Review queue. |
| Any time | You | Approve, edit or hide events on the site after signing in at `/admin/`. Approved events go live instantly. |

Nothing from the sweep or from visitors goes live until an admin approves it.

## News feeds and event leads
The feeds are listed in [`scripts/news_feeds.json`](scripts/news_feeds.json) (Premium Times, Vanguard, The Guardian Nigeria, Channels TV, Punch, TheCable, Daily Post, BusinessDay, BellaNaija, Notjustok, TechCabal). Set `"on": false` to stop using one.
Only headlines and links are used, always credited to the outlet. Leads appear on `/admin/` after you sign in: read the article, then **Add as event** or **Dismiss**.

## Adding sweep sources
Edit [`scripts/sources.json`](scripts/sources.json) on GitHub, set `"on": true`, save. Supported:
- `page`: a website that publishes schema.org Event data (many organiser and venue sites do)
- `ics`: a public calendar feed
- `eventbrite_organizer`: an organiser on Eventbrite, through the official API (needs `EVENTBRITE_TOKEN`)

Only add sources whose terms allow automated reading. The sweep respects robots.txt and waits between requests.
Each run's summary (Actions tab → the run) shows how many events each source gave.

## Notes
- Reading flyers automatically with AI isn't available on this version; type details in, or add an AI service later.
- Flyers uploaded through the site are stored in Supabase Storage (bucket `flyers`) and shown at `/_blob/...`.
- Flyers from the Claude version are in `_blob/` and `events/flyers/`.
