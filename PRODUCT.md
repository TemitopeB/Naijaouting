# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Everyone looking for something to do in Nigeria, in this order of priority (confirmed by the owner, 18 Nov 2026):

1. **Visitors, tourists and diaspora**: people coming home (especially for December) or visiting a Nigerian city, who need to find events, plan trips and see what a place offers.
2. **Professionals and learners**: conferences, tech events, career fairs, workshops, and online webinars.
3. **Families and everyone else**: kids' events, faith events, markets, festivals, free things to do.
4. **Young adults in big cities**: Lagos, Abuja, Port Harcourt, Ibadan, planning weekends, concerts, parties and nightlife.
5. **Event-goers in general**: anyone deciding what to attend.

Secondary audiences:
- **Organisers** submit events through the Add event form.
- **The site admin** reviews submissions, corrections and scam reports in the Review panel before anything goes live.

## Product Purpose

NaijaOuting gathers events from ticket sites, organisers, flyers and news across Nigeria, checks them, and sends people to the official seller or organiser. Success means a visitor finds a real event, trusts what the listing says, and reaches the right ticket or registration page, without being misled.

## Positioning

Four things, together, set it apart from Instagram event pages and ticketing sites:

- **Honest and verified**: listings are reviewed by an admin before going live. Ticket links point only to official sellers or organisers. Prices, venues and dates are never invented; unknown details show as "to be confirmed". Visitor scam reports produce admin-confirmed warnings.
- **All of Nigeria in one place**: every city and state, not just Lagos, plus online events and webinars.
- **Plan the outing, not just browse**: map, near me, calendar, trip planner, budget planner, directions, tourism guide.
- **Free to use, no account needed**: anyone can browse, save and plan without signing up or paying. An optional account (planned) only syncs saves and reminders.

## Operating Context

- Most visitors are on **phones using mobile data**, which is often slow or costly, so pages must load fast and stay light.
- Many arrive from **event links shared on WhatsApp**, so a shared event link is a real front door to the site.
- A real share also visit on **computers**, for example planning at work.
- Events come in through the Add event form, a weekly sweep of event websites, an AI sweep (Gemini, waiting on billing), Claude scans via the inbox, and news leads. All of them land in the admin Review panel first.
- Ended events move off the page monthly. Old shared links show a "This event has ended" page with similar upcoming events.

## Capabilities and Constraints

- Static site (HTML, CSS, JS) on Vercel, with Supabase for data, sign-in and flyer uploads, and GitHub Actions for scheduled jobs. The main app is `events/index.html`; the landing page is `index.html`; the admin sign-in is `/admin/`.
- Main views: Events (cards), Map, Near me, Calendar, Saved, Trip planner, Tourism, Explore, News, Online (webinars), event pages, and the admin Review panel.
- Installable as a web app (service worker, manifest). Phone app store buttons say "Coming soon"; no store links exist.
- Strict listing rules for online events: forex, crypto, "investment opportunity", "earn daily" and similar are rejected or flagged, and paid masterclasses from unknown organisers are never listed.
- **Undecided:** visitor accounts are built but switched off until setup is finished.

## Brand Commitments

- Name: **NaijaOuting** (one word, capital N and O).
- **The logo and wordmark stay hidden** until the owner asks to add the logo back.
- **No logos taken from the internet**: no third-party brand logos, ticket-site logos or event logos used as decoration.
- Contact email and WhatsApp stay empty on the site; the owner's personal email is never published.
- Voice: plain, friendly British English, short sentences, direct about what's known and what isn't ("Venue to be confirmed", "See organiser").

## Evidence on Hand

- Real event listings: built-in events in `events/index.html`, approved events in Supabase, ended events in `data/past-events.json`.
- Real flyers: `/flyers/` and Supabase storage (`/_blob/`), credited to their Instagram source.
- Category cover illustrations: `/covers/`.
- **Absences that must not be faked:** no visitor counts, no testimonials, no press mentions, no app store listings, no partner or sponsor logos. Don't show fabricated numbers or reviews.

## Product Principles

1. **Truth over completeness.** A blank "to be confirmed" beats a guessed venue, price or link.
2. **Trust is earned in the details.** Official links, sources and scam warnings matter more than polish.
3. **Light and fast on a phone.** Every page should work on a cheap phone on mobile data.
4. **Nigeria-wide, visitor-friendly.** Someone new to a city should understand where, when and how to get there.
5. **Free and open.** No sign-up walls in front of browsing, saving or planning.

## Accessibility & Inclusion

- Must work well on small, low-end phones and slow connections.
- Readable in light and dark mode.
- Keyboard-reachable admin and visitor controls; reduced-motion respected for animations.
