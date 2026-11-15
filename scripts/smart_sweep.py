"""
Smart Monday sweep (GitHub Actions + Google Gemini; no Claude needed).

For each region and theme, Gemini searches Google for upcoming public events in Nigeria and
returns them as structured data. We then:
  - keep only events with a date in the next 8 weeks, a city, and a source page Google actually used;
  - drop anything already on the site or already waiting for review;
  - add the rest to the site's Review queue (Supabase docs: col "submissions", id "sweep").
Nothing goes live until an admin approves it.

Ticket links: the source page is only used as the event's link when it's an official ticket
seller's page; otherwise it's shown in the description for the admin to check.

Run:      SUPABASE_URL=... SUPABASE_SERVICE_KEY=... GEMINI_API_KEY=... python scripts/smart_sweep.py
Dry run:  GEMINI_API_KEY=... python scripts/smart_sweep.py --dry-run
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import random
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gemini  # noqa: E402
from sweep import DB, key, norm, guess_city, log, summary, MAX_WAITING  # noqa: E402

LAGOS = dt.timezone(dt.timedelta(hours=1))
TODAY = dt.datetime.now(LAGOS).date()
END = TODAY + dt.timedelta(days=56)

CATS = ["Music", "Arts & Culture", "Business", "Tech", "Fashion", "Faith", "Civic", "Sports", "Comedy",
        "Nightlife & Parties", "Food & Drink", "Festivals & Carnivals", "Film & Theatre", "Careers & Education",
        "Kids & Family", "Health & Fitness", "Expos & Trade Fairs", "Workshops & Classes", "Markets & Pop-ups",
        "Gaming & Esports", "Books & Literature", "Charity & Volunteering", "Agriculture"]
REGIONS = ["Lagos", "Abuja (FCT)", "Port Harcourt and Rivers State", "Ibadan, Abeokuta and the South West",
           "Enugu, Calabar, Uyo, Owerri and Benin City", "Kano, Kaduna, Jos and the North"]
THEMES = [
    ["Music", "Nightlife & Parties", "Comedy", "Festivals & Carnivals", "Film & Theatre"],
    ["Business", "Tech", "Careers & Education", "Expos & Trade Fairs", "Workshops & Classes"],
    ["Arts & Culture", "Fashion", "Food & Drink", "Books & Literature", "Sports", "Faith", "Kids & Family", "Markets & Pop-ups"],
]
# Official ticket sellers: a source on these sites can be used as the event's ticket link.
SELLERS = ("tix.africa", "nairabox.com", "dottix.com", "dottix.ng", "cene.ng", "cene.africa", "eventbrite.com",
           "eventbrite.co.uk", "eventskona.com", "shows.ng", "selar.com", "selar.co", "jetronticket.com",
           "ticketmaster.com", "flutterwave.com", "paystack.com", "lu.ma", "luma.com", "afrotix.com", "zikoko.com/tickets")
# Sites never accepted as a source (resellers, social posts that can't be checked, generic listings).
SKIP = ("viagogo", "stubhub", "facebook.com", "instagram.com", "tiktok.com", "x.com", "twitter.com", "youtube.com")

PROMPT = """Today is {today} in Lagos, Nigeria.
Use Google Search to find specific public events taking place in {region}, Nigeria, starting between {today} and {end}.
Categories to look for: {cats}.

Rules:
- Only events whose date has been published by the organiser, an official ticket seller, or a reputable news outlet.
- No online-only events, no past events, no "call for vendors/entries" posts, no recurring weekly club nights without a specific date.
- If you are not sure of a field, leave it as an empty string. Never guess a price or a venue.
- "about" is one or two plain sentences in your own words.
- "source" is the web address of the page where you confirmed the date.

Answer with ONLY a JSON array (no other text), up to 12 items, each:
{{"name":"","category":"one of: {allcats}","start":"YYYY-MM-DD","end":"YYYY-MM-DD","time":"","venue":"","city":"","state":"","price":"","about":"","source":""}}"""


def clean_item(e, srcs, known, now_iso):
    """Validate one event from Gemini. Returns a Review-queue item, or (None, reason)."""
    if not isinstance(e, dict):
        return None, "not an object"
    name = str(e.get("name", "")).strip()[:160]
    s, en = str(e.get("start", "")).strip()[:10], str(e.get("end", "")).strip()[:10]
    try:
        sd = dt.date.fromisoformat(s)
    except ValueError:
        return None, "no valid date"
    try:
        ed = dt.date.fromisoformat(en) if en else sd
    except ValueError:
        ed = sd
    if ed < sd:
        ed = sd
    if not name:
        return None, "no name"
    if sd < TODAY or sd > END:
        return None, "outside the 8-week window"
    city = str(e.get("city", "")).strip()
    city = guess_city(city, str(e.get("venue", "")), str(e.get("state", "")), fallback=city)[:60]
    if not city:
        return None, "no city"
    k = key({"name": name, "s": s})
    nk = norm(name)
    if k in known or any(len(n) >= 10 and (n in nk or nk in n) for n, d in known if d == s):
        return None, "already on the site or waiting"
    # source must be one of the pages Google actually returned
    claimed = gemini.domain(str(e.get("source", "")))
    match = next((x for x in srcs if claimed and (x["title"] == claimed or x["title"].endswith("." + claimed) or claimed.endswith(x["title"]))), None)
    if not match:
        return None, "source not among the pages Google used"
    url = gemini.real_url(match["uri"])
    dom = gemini.domain(url) or match["title"]
    if any(b in dom for b in SKIP):
        return None, f"source site not accepted ({dom})"
    cat = str(e.get("category", "")).strip()
    if cat not in CATS:
        cat = next((c for c in CATS if c.lower() in cat.lower()), "Festivals & Carnivals")
    price = str(e.get("price", "")).strip()[:60] or "See organiser"
    about = str(e.get("about", "")).strip()[:500]
    official = any(dom == sdom or dom.endswith("." + sdom) for sdom in SELLERS)
    src_note = f"Source: {dom}" + (f" ({url})" if url and not official else "") + ". Check the details there before approving."
    known.add(k)
    return {
        "iid": f"{int(time.time() * 1000)}-{random.randrange(36**5):05x}",
        "name": name, "cat": cat, "s": s, "e": ed.isoformat(), "time": str(e.get("time", "")).strip()[:30],
        "venue": str(e.get("venue", "")).strip()[:160], "city": city, "state": str(e.get("state", "")).strip()[:40],
        "fee": price, "about": (about + " " if about else "") + src_note,
        "link": url if official else "", "img": "", "src": "smart-sweep", "at": now_iso,
    }, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-calls", type=int, default=int(os.environ.get("SMART_MAX_CALLS", "18")))
    ap.add_argument("--probe", action="store_true", help="one tiny request per model, to see which ones have free quota")
    args = ap.parse_args()

    if not os.environ.get("GEMINI_API_KEY"):
        log("GEMINI_API_KEY is not set: smart sweep skipped.")
        summary("## Smart sweep\n\nSkipped: add the `GEMINI_API_KEY` secret to turn it on.")
        return

    if args.probe:
        for m in gemini.candidates():
            for srch in (False, True):
                try:
                    gemini._model = m
                    body = {"contents": [{"role": "user", "parts": [{"text": "Reply with OK."}]}]}
                    if srch:
                        body["tools"] = [{"google_search": {}}]
                    gemini._call("POST", f"/{m}:generateContent", body, tries=1)
                    log(f"  {m.split('/')[-1]:<28} {'with Google Search' if srch else 'plain':<20} OK")
                except gemini.GeminiError as ex:
                    log(f"  {m.split('/')[-1]:<28} {'with Google Search' if srch else 'plain':<20} {type(ex).__name__}: {str(ex)[:160]}")
                time.sleep(4)
        return

    db = None
    if not args.dry_run:
        url, k_ = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY")
        if not url or not k_:
            sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_KEY.")
        db = DB(url, k_)

    known = set()
    try:
        for e in json.load(open(ROOT / "data" / "landing.json"))["ev"]:
            known.add(key(e))
    except Exception:
        pass
    waiting = []
    if db:
        for r in db.col("events"):
            known.add(key(r["data"]))
        waiting = (db.get("submissions", "sweep") or {}).get("items", [])
        for it in waiting:
            known.add(key(it))

    log("Models to try: " + ", ".join(m.split("/")[-1] for m in gemini.candidates()))
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
    jobs = [(r, t) for t in THEMES for r in REGIONS][:args.max_calls]
    items, reasons, report = [], {}, ["| Region | Themes | Found | Kept |", "|---|---|---|---|"]
    for i, (region, cats) in enumerate(jobs):
        prompt = PROMPT.format(today=TODAY.isoformat(), end=END.isoformat(), region=region,
                               cats=", ".join(cats), allcats=" | ".join(CATS))
        try:
            text, srcs = gemini.ask(prompt, search=True)
        except gemini.QuotaError as ex:
            log(f"- {region} / {cats[0]}…: stopped, out of free quota: {ex}")
            report.append(f"| {region} | {cats[0]}… | out of quota | 0 |")
            break  # nothing left to try today
        except gemini.GeminiError as ex:
            log(f"- {region} / {cats[0]}…: Gemini error: {ex}")
            report.append(f"| {region} | {cats[0]}… | error | 0 |")
            if "HTTP 401" in str(ex) or "HTTP 403" in str(ex):
                break  # key problem: no point trying the rest
            continue
        found = gemini.parse_json(text) or []
        if isinstance(found, dict):
            found = found.get("events") or [found]
        kept = 0
        for e in found:
            it, why = clean_item(e, srcs, known, now_iso)
            if it:
                items.append(it)
                kept += 1
            else:
                reasons[why] = reasons.get(why, 0) + 1
        log(f"- {region} / {', '.join(cats[:2])}…: {len(found)} found, {kept} kept, {len(srcs)} sources")
        report.append(f"| {region} | {cats[0]}… | {len(found)} | {kept} |")
        if i < len(jobs) - 1:
            time.sleep(7)  # stay under the free tier's per-minute limit

    for q in gemini.QUOTA_LOG:
        log(f"Quota: {q}")
    log(f"Model used: {gemini.model() if not gemini.QUOTA_LOG or len(gemini._dead) < len(gemini.candidates()) else 'none'}")
    log(f"\n{len(items)} new events for review. Skipped: " + ", ".join(f"{v} {k}" for k, v in sorted(reasons.items(), key=lambda x: -x[1])))
    for it in items[:60]:
        log(f"  {it['s']}  {it['city']:<14} {it['cat']:<22} {it['name'][:70]}  [{it['about'].split('Source: ')[-1][:40]}]")
    summary("## Smart sweep (Gemini)\n\n" + "\n".join(report) + f"\n\n**{len(items)} new events** added to the Review queue."
            + ("\n\nSkipped: " + ", ".join(f"{v} {k}" for k, v in reasons.items()) if reasons else "")
            + ("\n\nQuota notes:\n" + "\n".join("- " + q for q in gemini.QUOTA_LOG) if gemini.QUOTA_LOG else ""))
    if db and items:
        keep = [w for w in waiting if (w.get("s") or "") >= TODAY.isoformat()]
        db.put("submissions", "sweep", {"items": (keep + items)[-MAX_WAITING:]})
        log("Saved to the Review queue.")


if __name__ == "__main__":
    main()
