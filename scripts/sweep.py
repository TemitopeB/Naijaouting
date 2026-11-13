"""
Monday event sweep (runs on GitHub Actions, no Claude needed).

1. Visits each page listed in scripts/sources.json.
2. Reads the structured event data many sites publish for search engines
   (schema.org "Event" in JSON-LD), calendar feeds (.ics), and Eventbrite's official API
   for organisers you list.
3. Keeps upcoming events in Nigeria, drops ones already on the site or already waiting.
4. Adds the rest to the site's Review queue (Supabase docs: col "submissions", id "sweep").
   Nothing goes live until an admin approves it on the site.

It respects each site's robots.txt, waits between requests and identifies itself.
Only add sources whose terms allow this, and link to the official event page.

Run locally:  SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python scripts/sweep.py
Dry run (no database):  python scripts/sweep.py --dry-run
Test on a saved page:   python scripts/sweep.py --dry-run --file saved.html --city Lagos
"""
import argparse
import datetime as dt
import html
import json
import os
import pathlib
import random
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = "NaijaOutingBot/1.0 (+https://github.com/TemitopeB/Naijaouting)"
LAGOS = dt.timezone(dt.timedelta(hours=1))
TODAY = dt.datetime.now(LAGOS).date()
HORIZON = TODAY + dt.timedelta(days=120)
MAX_WAITING = 300

CITIES = {
    "lagos": "Lagos", "ikeja": "Lagos", "lekki": "Lagos", "victoria island": "Lagos", "ikoyi": "Lagos", "yaba": "Lagos",
    "surulere": "Lagos", "abuja": "Abuja", "fct": "Abuja", "port harcourt": "Port Harcourt", "ibadan": "Ibadan",
    "enugu": "Enugu", "calabar": "Calabar", "kano": "Kano", "kaduna": "Kaduna", "benin city": "Benin City",
    "uyo": "Uyo", "jos": "Jos", "abeokuta": "Abeokuta", "owerri": "Owerri", "warri": "Warri", "ilorin": "Ilorin",
    "asaba": "Asaba", "akure": "Akure", "osogbo": "Osogbo", "maiduguri": "Maiduguri", "onitsha": "Onitsha",
}
NIGERIA = re.compile(r"\b(nigeria|ng)\b", re.I)

# Category guesses use the site's own category names. An admin can change them while reviewing.
CATS = [
    ("Comedy", r"comedy|stand-?up|laugh"),
    ("Nightlife & Parties", r"party|rave|nightlife|club|day party|owambe|afrobeats night"),
    ("Music", r"concert|music|live band|gig|festival of music|choir|jazz|dj\b|album"),
    ("Tech", r"tech|developer|startup|\bai\b|data|coding|hackathon|devfest|blockchain|crypto|product"),
    ("Business", r"business|summit|conference|entrepreneur|founder|investor|finance|marketing|networking|leadership"),
    ("Careers & Education", r"career|job fair|scholarship|university|bootcamp|training|masterclass"),
    ("Workshops & Classes", r"workshop|class|course|seminar|webinar"),
    ("Faith", r"church|worship|crusade|prayer|gospel|ministry|mosque|islamic|praise"),
    ("Food & Drink", r"food|drink|wine|cocktail|brunch|dinner|chef|tasting|bbq|suya"),
    ("Fashion", r"fashion|runway|style|beauty|makeup"),
    ("Film & Theatre", r"film|cinema|movie|screening|theatre|theater|stage play|drama"),
    ("Arts & Culture", r"art\b|arts|exhibition|gallery|culture|poetry|paint|museum"),
    ("Books & Literature", r"book|literary|literature|author|reading"),
    ("Sports", r"football|marathon|race|tournament|match|sport|basketball|tennis|golf|polo"),
    ("Health & Fitness", r"fitness|yoga|health|wellness|run club|workout"),
    ("Kids & Family", r"kids|children|family|teen"),
    ("Expos & Trade Fairs", r"expo|trade fair|exhibition centre|fair\b"),
    ("Markets & Pop-ups", r"market|pop-?up|bazaar|flea"),
    ("Gaming & Esports", r"gaming|esports|game night|playstation|fifa tournament"),
    ("Charity & Volunteering", r"charity|volunteer|fundrais|outreach|ngo"),
    ("Agriculture", r"agric|farm|agro"),
    ("Festivals & Carnivals", r"festival|carnival|fiesta"),
]


def log(*a):
    print(*a, flush=True)


def summary(md):
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a") as f:
            f.write(md + "\n")


# ---------------- fetching ----------------
_robots = {}


def allowed(url):
    u = urllib.parse.urlparse(url)
    base = f"{u.scheme}://{u.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(base + "/robots.txt", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                rp.parse(r.read().decode("utf-8", "replace").splitlines())
        except Exception:
            rp.parse([])  # no robots.txt: allowed
        _robots[base] = rp
    return _robots[base].can_fetch(UA, url)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,text/calendar;q=0.9,*/*;q=0.5"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read(4_000_000).decode(r.headers.get_content_charset() or "utf-8", "replace")


# ---------------- reading event data ----------------
def jsonld_blocks(page):
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', page, re.S | re.I):
        raw = html.unescape(m.group(1).strip())
        try:
            yield json.loads(raw)
        except Exception:
            try:
                yield json.loads(re.sub(r",\s*([}\]])", r"\1", raw))
            except Exception:
                continue


def walk_events(node):
    if isinstance(node, list):
        for x in node:
            yield from walk_events(x)
    elif isinstance(node, dict):
        t = node.get("@type")
        types = t if isinstance(t, list) else [t]
        if any(isinstance(x, str) and x.endswith("Event") for x in types):
            yield node
        for k in ("@graph", "itemListElement", "item", "subEvent", "event", "events"):
            if k in node:
                yield from walk_events(node[k])


def text(v):
    if isinstance(v, list):
        v = v[0] if v else ""
    if isinstance(v, dict):
        v = v.get("name") or v.get("url") or v.get("@id") or ""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(v or "")))).strip()


def day(v):
    m = re.match(r"(\d{4}-\d{2}-\d{2})", text(v))
    return m.group(1) if m else ""


def clock(v):
    m = re.match(r"\d{4}-\d{2}-\d{2}T(\d{2}):(\d{2})", text(v))
    if not m:
        return ""
    h, mi = int(m.group(1)), m.group(2)
    if h == 0 and mi == "00":
        return ""
    return f"{(h % 12) or 12}:{mi} {'AM' if h < 12 else 'PM'}"


def guess_cat(s):
    s = s.lower()
    for cat, rx in CATS:
        if re.search(rx, s):
            return cat
    return "Business"


def guess_city(*parts, fallback=""):
    s = " ".join(p for p in parts if p).lower()
    for k, v in CITIES.items():
        if re.search(r"\b" + re.escape(k) + r"\b", s):
            return v
    return fallback


def fee_of(offers):
    offers = offers if isinstance(offers, list) else [offers] if offers else []
    prices = []
    for o in offers:
        if not isinstance(o, dict):
            continue
        for k in ("price", "lowPrice"):
            try:
                prices.append(float(str(o.get(k)).replace(",", "")))
            except Exception:
                pass
        cur = o.get("priceCurrency") or ""
    if not prices:
        return "See organiser"
    lo = min(prices)
    if lo == 0:
        return "Free"
    sym = "₦" if not offers or (isinstance(offers[0], dict) and (offers[0].get("priceCurrency") or "NGN") == "NGN") else ""
    return f"From {sym}{lo:,.0f}" if sym else f"From {lo:,.2f} {cur}"


def from_jsonld(ev, src):
    loc = ev.get("location") or {}
    loc = loc[0] if isinstance(loc, list) and loc else loc
    addr = loc.get("address") if isinstance(loc, dict) else ""
    addr_s = text(addr) if not isinstance(addr, dict) else " ".join(text(addr.get(k)) for k in ("streetAddress", "addressLocality", "addressRegion", "addressCountry"))
    country = text(addr.get("addressCountry")) if isinstance(addr, dict) else ""
    venue = text(loc.get("name")) if isinstance(loc, dict) else text(loc)
    online = "OnlineEventAttendanceMode" in json.dumps(ev.get("eventAttendanceMode", ""))
    name = text(ev.get("name"))
    s, e = day(ev.get("startDate")), day(ev.get("endDate"))
    link = text(ev.get("url")) or src.get("url", "")
    img = text(ev.get("image"))
    about = text(ev.get("description"))[:600]
    return {
        "name": name[:160], "s": s, "e": e or s, "time": clock(ev.get("startDate")),
        "venue": ("Online" if online and not venue else venue)[:160],
        "city": guess_city(addr_s, venue, fallback=src.get("city", "")),
        "country": country, "addr": addr_s,
        "fee": fee_of(ev.get("offers")), "about": about,
        "link": link if link.startswith("https://") else "",
        "img": img if img.startswith("https://") else "",
        "cat": src.get("cat") or guess_cat(f"{name} {about}"), "online": online,
    }


def from_ics(page, src):
    out = []
    for blk in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", page, re.S):
        blk = re.sub(r"\r?\n[ \t]", "", blk)
        f = {}
        for line in blk.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                f[k.split(";")[0].upper()] = v.replace("\\,", ",").replace("\\n", " ").strip()
        def d8(v):
            m = re.match(r"(\d{4})(\d{2})(\d{2})", v or "")
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""
        name, about, loc = f.get("SUMMARY", ""), f.get("DESCRIPTION", "")[:600], f.get("LOCATION", "")
        s = d8(f.get("DTSTART"))
        out.append({
            "name": name[:160], "s": s, "e": d8(f.get("DTEND")) or s, "time": "", "venue": loc.split(",")[0][:160],
            "city": guess_city(loc, fallback=src.get("city", "")), "country": "", "addr": loc, "fee": "See organiser",
            "about": about, "link": f.get("URL", "") if f.get("URL", "").startswith("https://") else src.get("url", ""),
            "img": "", "cat": src.get("cat") or guess_cat(f"{name} {about}"), "online": False,
        })
    return out


def from_eventbrite(src):
    """Official Eventbrite API: live events of one organiser. Needs the EVENTBRITE_TOKEN secret."""
    tok = os.environ.get("EVENTBRITE_TOKEN")
    if not tok:
        raise RuntimeError("EVENTBRITE_TOKEN secret is not set")
    out, page = [], 1
    while page <= 5:
        url = f"https://www.eventbriteapi.com/v3/organizers/{urllib.parse.quote(str(src['id']))}/events/?status=live&expand=venue,ticket_availability&page={page}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}", "User-Agent": UA})
        with urllib.request.urlopen(req, timeout=40) as r:
            j = json.load(r)
        for ev in j.get("events", []):
            v = ev.get("venue") or {}
            a = v.get("address") or {}
            name = text((ev.get("name") or {}).get("text"))
            about = text((ev.get("description") or {}).get("text"))[:600]
            ta = ev.get("ticket_availability") or {}
            mn = (ta.get("minimum_ticket_price") or {}).get("major_value")
            fee = "Free" if ev.get("is_free") else (f"From ₦{float(mn):,.0f}" if mn and (ta.get("minimum_ticket_price") or {}).get("currency") == "NGN" else "See organiser")
            out.append({
                "name": name[:160], "s": day((ev.get("start") or {}).get("local")), "e": day((ev.get("end") or {}).get("local")),
                "time": clock((ev.get("start") or {}).get("local")), "venue": text(v.get("name"))[:160],
                "city": guess_city(a.get("city"), a.get("region"), text(v.get("name")), fallback=src.get("city", "")),
                "country": a.get("country") or "", "addr": text(a.get("localized_address_display")), "fee": fee, "about": about,
                "link": ev.get("url") or "", "img": ((ev.get("logo") or {}).get("original") or {}).get("url") or "",
                "cat": src.get("cat") or guess_cat(f"{name} {about}"), "online": bool(ev.get("online_event")),
            })
        if not (j.get("pagination") or {}).get("has_more_items"):
            break
        page += 1
    return out


# ---------------- de-duplication ----------------
def norm(name):
    n = re.sub(r"\b(20\d\d|the|edition|live|in|at|lagos|abuja)\b", " ", name.lower())
    return re.sub(r"[^a-z0-9]+", "", n)[:40]


def key(e):
    return (norm(e.get("name") or e.get("n") or ""), e.get("s") or "")


# ---------------- Supabase ----------------
class DB:
    def __init__(self, url, service_key):
        self.url, self.key = url.rstrip("/"), service_key

    def _req(self, method, path, body=None, extra=None):
        h = {"apikey": self.key, "Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        h.update(extra or {})
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.url + path, data=data, headers=h, method=method)
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else None

    def col(self, col):
        return self._req("GET", f"/rest/v1/docs?select=id,data&col=eq.{col}") or []

    def get(self, col, id_):
        rows = self._req("GET", f"/rest/v1/docs?select=data&col=eq.{col}&id=eq.{urllib.parse.quote(id_)}") or []
        return rows[0]["data"] if rows else None

    def put(self, col, id_, data):
        self._req("POST", "/rest/v1/docs?on_conflict=col,id", [{"col": col, "id": id_, "data": data}],
                  {"Prefer": "resolution=merge-duplicates,return=minimal"})


# ---------------- main ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print what would be added, change nothing")
    ap.add_argument("--file", help="read a saved page instead of the sources list (testing)")
    ap.add_argument("--city", default="", help="city to assume for --file")
    args = ap.parse_args()

    if args.file:
        sources = [{"name": "Saved page", "url": "file", "city": args.city}]
    else:
        sources = [s for s in json.load(open(ROOT / "scripts" / "sources.json"))["sources"] if s.get("on", True)]

    db = None
    if not args.dry_run:
        url, key_ = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY")
        if not url or not key_:
            sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_KEY (GitHub: Settings -> Secrets and variables -> Actions).")
        db = DB(url, key_)

    # what the site already has, so we don't suggest it again
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

    found, report = [], ["| Source | Events read | New for review |", "|---|---|---|"]
    for src in sources:
        got = []
        try:
            if src.get("type") == "eventbrite_organizer":
                got = from_eventbrite(src)
                page = None
            elif args.file:
                page = open(args.file, encoding="utf-8", errors="replace").read()
            else:
                if not allowed(src["url"]):
                    log(f"- {src['name']}: skipped (robots.txt does not allow it)")
                    report.append(f"| {src['name']} | skipped: robots.txt | 0 |")
                    continue
                page = get(src["url"])
                time.sleep(2 + random.random() * 2)
            if page is None:
                pass
            elif src.get("type") == "ics" or page.lstrip().startswith("BEGIN:VCALENDAR"):
                got = from_ics(page, src)
            else:
                for blk in jsonld_blocks(page):
                    got += [from_jsonld(ev, src) for ev in walk_events(blk)]
        except Exception as ex:
            log(f"- {src['name']}: could not read ({ex.__class__.__name__}: {ex})")
            report.append(f"| {src['name']} | error: {ex.__class__.__name__} | 0 |")
            continue

        new = 0
        for e in got:
            if not e["name"] or not e["s"]:
                continue
            try:
                start = dt.date.fromisoformat(e["s"])
            except ValueError:
                continue
            if start < TODAY or start > HORIZON or e["online"]:
                continue
            if e["country"] and not NIGERIA.search(e["country"]):
                continue
            if not e["city"]:
                continue
            k = key(e)
            if k in known:
                continue
            known.add(k)
            new += 1
            found.append(e)
        log(f"- {src['name']}: {len(got)} events read, {new} new")
        report.append(f"| {src['name']} | {len(got)} | {new} |")

    items = []
    for e in found:
        items.append({
            "iid": f"{int(time.time() * 1000)}-{random.randrange(36**5):05x}",
            "name": e["name"], "cat": e["cat"], "s": e["s"], "e": e["e"], "time": e["time"],
            "venue": e["venue"], "city": e["city"], "state": "", "fee": e["fee"],
            "about": (e["about"] or "Found by the Monday sweep. Check the details with the organiser before approving.")[:600],
            "link": e["link"], "img": e["img"], "src": "sweep", "at": dt.datetime.now(dt.timezone.utc).isoformat(),
        })

    log(f"\n{len(items)} new events for review.")
    summary("## Monday event sweep\n\n" + "\n".join(report) + f"\n\n**{len(items)} new events** added to the Review queue.")
    if args.dry_run or not db:
        for it in items[:50]:
            log(f"  {it['s']}  {it['city']:<14} {it['cat']:<22} {it['name']}")
        return
    if items:
        keep = [w for w in waiting if (w.get("s") or "") >= TODAY.isoformat()]
        db.put("submissions", "sweep", {"items": (keep + items)[-MAX_WAITING:]})
        log("Saved to the Review queue.")


if __name__ == "__main__":
    main()
