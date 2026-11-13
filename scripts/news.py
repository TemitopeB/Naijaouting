"""
Daily news job (runs on GitHub Actions, no Claude needed).

Reads the public RSS feeds in scripts/news_feeds.json and:
  1. writes data/news.json: about 24 recent headlines for the news ticker on /events/
     (headline + link + outlet only; every story opens at its source);
  2. finds articles that look like announcements of upcoming events and saves them as
     "leads" for the admin page (Supabase docs: col "leads", id "news").
     Leads never go live by themselves: an admin opens the article and adds the event.

Respects robots.txt, identifies itself, waits between requests.

Run:      SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python scripts/news.py
No DB:    python scripts/news.py            (writes data/news.json, prints leads)
Test:     python scripts/news.py --file saved_feed.xml --name "Test" --no-write
"""
import argparse
import datetime as dt
import email.utils
import hashlib
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
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = "NaijaOutingBot/1.0 (+https://github.com/TemitopeB/Naijaouting)"
LAGOS = dt.timezone(dt.timedelta(hours=1))
NOW = dt.datetime.now(LAGOS)
TODAY = NOW.date()

sys.path.insert(0, str(ROOT / "scripts"))
from sweep import CATS, guess_city, norm  # same category names and city list as the sweep

# ---------------- ticker categories ----------------
TOPICS = [
    ("Sports", r"super eagles|super falcons|afcon|npfl|premier league|la liga|champions league|football|footballer|striker|"
               r"midfielder|goalkeeper|coach|match|fixture|olympic|athlet|boxing|boxer|basketball|tennis|\bfifa\b|\bcaf\b|marathon"),
    ("Security", r"bandit|kidnap|abduct|gunmen|terror|boko haram|iswap|insurgen|military|soldier|troops|army|police|"
                 r"killed|attack|clash|insecurity|explosion|\bdss\b|cult"),
    ("Health", r"health|hospital|doctor|nurse|disease|cholera|malaria|lassa|mpox|measles|vaccin|nafdac|ncdc|\bwho\b|"
               r"outbreak|patients|medical|cancer|diabetes"),
    ("Economy", r"inflation|naira|\bcbn\b|central bank|\bgdp\b|budget|\btax|petrol price|fuel price|pump price|economy|"
                r"interest rate|\bmpr\b|debt|revenue|\bimf\b|world bank|exchange rate|forex|subsidy|recession|unemployment"),
    ("Business", r"company|firm|shares|\bngx\b|stock|investor|profit|revenue|startup|telecom|\bmtn\b|airtel|dangote|"
                 r"airline|business|bank\b|banks\b|fintech|merger|acquisition|ipo|oil and gas|nnpc|refinery"),
    ("Entertainment", r"music|album|single|song|nollywood|movie|film|actor|actress|singer|rapper|afrobeats|concert|"
                      r"bbnaija|big brother|celebrity|award|grammy|headies|amvca|festival|fashion|comedian|skit|box office"),
    ("Politics", r"\bapc\b|\bpdp\b|labour party|\badc\b|tinubu|shettima|senate|senator|governor|election|\binec\b|"
                 r"party|president|minister|house of reps|lawmakers|assembly|2027|campaign|impeach|politic"),
]

# ---------------- event announcement detection ----------------
EVENT = re.compile(r"\b(concert|festival|fest|carnival|summit|conference|expo|exhibition|fair|tour|show|awards?|premiere|"
                   r"hackathon|marathon|party|gala|parade|competition|pageant|tournament|workshop|masterclass|"
                   r"bootcamp|seminar|crusade|convention|meetup|week|edition|screening|play|stage)\b", re.I)
AHEAD = re.compile(r"\b(to hold|will hold|set to|set for|slated|scheduled|returns|is back|unveils?|announces?|announced|"
                   r"tickets?|kicks? off|this weekend|upcoming|ahead of|to host|to headline|to perform|to stage|"
                   r"opens? (on|in|this)|registration|register|save the date|coming to|heads? to|counts? down|"
                   r"line-?up|date for|dates for|on (mon|tues|wednes|thurs|fri|satur|sun)day|next (week|month))\b", re.I)
PAST = re.compile(r"\b(held|ended|wraps? up|wrapped|recap|highlights|photos from|pictures from|stole the show|thrilled|"
                  r"concluded|was held|closes? with|last (week|weekend|night)|yesterday|winners? (list|emerge)|"
                  r"won|wins|emerged|dies|died|death|arrested|court|obituary|tribute)\b", re.I)
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
DATE1 = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?(?:\s*(?:-|–|to|&|and)\s*\d{1,2}(?:st|nd|rd|th)?)?\s+(?:of\s+)?"
                   r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?(?:,?\s+(20\d\d))?", re.I)
DATE2 = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?"
                   r"(?:\s*(?:-|–|to|&|and)\s*\d{1,2}(?:st|nd|rd|th)?)?(?:,?\s+(20\d\d))?\b", re.I)


def log(*a):
    print(*a, flush=True)


def summary(md):
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a") as f:
            f.write(md + "\n")


# ---------------- fetching and parsing ----------------
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
            rp.parse([])
        _robots[base] = rp
    return _robots[base].can_fetch(UA, url)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml,application/atom+xml,application/xml,text/xml;q=0.9,*/*;q=0.5"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read(6_000_000)


def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()


def when(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        d = email.utils.parsedate_to_datetime(s)
    except Exception:
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(LAGOS)


def local(tag):
    return tag.rsplit("}", 1)[-1].lower()


def parse_feed(raw):
    """RSS 2.0 or Atom -> list of {title, link, date, cats, text}."""
    raw = re.sub(rb"^[^<]+", b"", raw)  # stray bytes before the XML
    root = ET.fromstring(raw)
    items = []
    for el in root.iter():
        if local(el.tag) not in ("item", "entry"):
            continue
        f = {"cats": []}
        for c in el:
            t = local(c.tag)
            if t == "title":
                f["title"] = clean("".join(c.itertext()))
            elif t == "link":
                f.setdefault("link", (c.get("href") or (c.text or "")).strip())
            elif t in ("pubdate", "published", "updated", "date"):
                f.setdefault("date", when(c.text))
            elif t == "category":
                f["cats"].append(clean(c.get("term") or c.text or ""))
            elif t in ("description", "summary", "encoded", "content"):
                f["text"] = (f.get("text", "") + " " + clean("".join(c.itertext()))[:1200]).strip()
        if f.get("title") and f.get("link", "").startswith("http"):
            items.append(f)
    return items


# ---------------- ticker ----------------
def topic(it, default):
    s = (it["title"] + " " + " ".join(it["cats"])).lower()
    for name, rx in TOPICS:
        if re.search(rx, s):
            return name
    return default


def build_ticker(all_items):
    fresh = [x for x in all_items if x["feed"].get("ticker") and x.get("date") and NOW - x["date"] <= dt.timedelta(days=3)]
    fresh.sort(key=lambda x: x["date"], reverse=True)
    out, per_cat, per_src, seen = [], {}, {}, set()
    for x in fresh:
        c = topic(x, x["feed"].get("default", "Politics"))
        k = norm(x["title"])
        if k in seen or per_cat.get(c, 0) >= 5 or per_src.get(x["feed"]["name"], 0) >= 6:
            continue
        seen.add(k)
        per_cat[c] = per_cat.get(c, 0) + 1
        per_src[x["feed"]["name"]] = per_src.get(x["feed"]["name"], 0) + 1
        title = x["title"] if len(x["title"]) <= 140 else x["title"][:137].rsplit(" ", 1)[0] + "…"
        out.append({"c": c, "t": title, "s": x["feed"]["name"], "d": x["date"].date().isoformat(), "u": x["link"]})
        if len(out) >= 24:
            break
    return out


# ---------------- event leads ----------------
def find_date(s, published):
    """First date mentioned in the text that falls after publication and within ~6 months."""
    pub = (published or NOW).date()
    for rx, di, mi in ((DATE1, 1, 2), (DATE2, 2, 1)):
        for m in rx.finditer(s):
            try:
                day, mon = int(m.group(di)), MONTHS[m.group(mi).lower()[:3]]
                year = int(m.group(3)) if m.group(3) else pub.year
                d = dt.date(year, mon, day)
                if not m.group(3) and d < pub - dt.timedelta(days=7):
                    d = dt.date(year + 1, mon, day)
            except (ValueError, KeyError):
                continue
            if pub - dt.timedelta(days=1) <= d <= pub + dt.timedelta(days=200):
                return d
    return None


def guess_cat(s):
    s = s.lower()
    for cat, rx in CATS:
        if re.search(rx, s):
            return cat
    return ""


def lead_of(x, known_names):
    title, text = x["title"], x.get("text", "")
    if not x["feed"].get("leads") or not x.get("date") or NOW - x["date"] > dt.timedelta(days=14):
        return None
    head = f"{title}. {text[:400]}"
    if not EVENT.search(title) or PAST.search(title):
        return None
    d = find_date(head, x["date"])
    if d and d < TODAY:
        return None
    score = (2 if AHEAD.search(title) else 1 if AHEAD.search(text[:400]) else 0) + (2 if d else 0)
    if score < 2:
        return None
    nt = norm(title)
    listed = next((n for n in known_names if len(n) >= 8 and n in nt), "")
    return {
        "id": hashlib.sha1(x["link"].encode()).hexdigest()[:16],
        "title": title[:200], "link": x["link"], "source": x["feed"]["name"],
        "published": x["date"].date().isoformat(), "date": d.isoformat() if d else "",
        "city": guess_city(head), "cat": guess_cat(head), "listed": bool(listed),
    }


# ---------------- Supabase ----------------
def db_req(method, path, body=None, extra=None):
    url, key = os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_KEY"]
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    h.update(extra or {})
    req = urllib.request.Request(url + path, data=json.dumps(body).encode() if body is not None else None, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="read one saved feed file instead of the list (testing)")
    ap.add_argument("--name", default="Test feed")
    ap.add_argument("--no-write", action="store_true", help="don't write data/news.json or the database")
    args = ap.parse_args()

    feeds = [f for f in json.load(open(ROOT / "scripts" / "news_feeds.json"))["feeds"] if f.get("on", True)]
    if args.file:
        feeds = [{"name": args.name, "url": "file", "ticker": True, "leads": True, "default": "Politics"}]

    all_items, report = [], ["| Feed | Stories read |", "|---|---|"]
    for f in feeds:
        try:
            if args.file:
                raw = open(args.file, "rb").read()
            else:
                if not allowed(f["url"]):
                    log(f"- {f['name']}: skipped (robots.txt)")
                    report.append(f"| {f['name']} | skipped: robots.txt |")
                    continue
                raw = fetch(f["url"])
                time.sleep(1 + random.random())
            items = parse_feed(raw)
        except Exception as ex:
            log(f"- {f['name']}: could not read ({ex.__class__.__name__}: {ex})")
            report.append(f"| {f['name']} | error: {ex.__class__.__name__} |")
            continue
        for it in items:
            it["feed"] = f
        all_items += items
        log(f"- {f['name']}: {len(items)} stories")
        report.append(f"| {f['name']} | {len(items)} |")

    # 1. ticker
    ticker = build_ticker(all_items)
    log(f"\nTicker: {len(ticker)} headlines")
    if len(ticker) >= 5 and not args.no_write:
        out = ROOT / "data" / "news.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps({"updated": NOW.strftime("%-d %b %Y, %-I:%M %p WAT").replace("AM", "am").replace("PM", "pm"),
                                   "items": ticker}, ensure_ascii=False, indent=0))
    elif len(ticker) < 5:
        log("Too few fresh headlines; keeping the previous ticker.")

    # 2. leads
    known = set()
    try:
        known = {norm(e["n"]) for e in json.load(open(ROOT / "data" / "landing.json"))["ev"]}
    except Exception:
        pass
    leads, seen = [], set()
    for x in all_items:
        ld = lead_of(x, known)
        if ld and ld["id"] not in seen and norm(ld["title"]) not in seen:
            seen.update([ld["id"], norm(ld["title"])])
            leads.append(ld)
    log(f"Leads: {len(leads)} possible event announcements")
    for ld in leads[:40]:
        log(f"  {ld['date'] or '  no date  '}  {ld['source']:<22} {ld['title'][:90]}{'  (maybe listed)' if ld['listed'] else ''}")

    have_db = os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY")
    new = 0
    if have_db and not args.no_write:
        rows = db_req("GET", "/rest/v1/docs?select=data&col=eq.leads&id=eq.news") or []
        cur = rows[0]["data"] if rows else {}
        dismissed = cur.get("dismissed", [])
        keep = [l for l in cur.get("items", []) if l["id"] not in dismissed
                and (not l.get("date") or l["date"] >= TODAY.isoformat())
                and l.get("published", "") >= (TODAY - dt.timedelta(days=30)).isoformat()]
        ids = {l["id"] for l in keep} | set(dismissed)
        for ld in leads:
            if ld["id"] not in ids:
                ld["found"] = TODAY.isoformat()
                keep.append(ld)
                new += 1
        keep.sort(key=lambda l: (l.get("found", ""), l.get("published", "")), reverse=True)
        db_req("POST", "/rest/v1/docs?on_conflict=col,id",
               [{"col": "leads", "id": "news", "data": {"updated": NOW.isoformat(), "items": keep[:150], "dismissed": dismissed[-600:]}}],
               {"Prefer": "resolution=merge-duplicates,return=minimal"})
        log(f"Saved {new} new leads ({len(keep[:150])} waiting on the admin page).")
    elif not have_db:
        log("No database secrets set: leads were not saved.")

    summary("## News and event leads\n\n" + "\n".join(report) +
            f"\n\n**Ticker:** {len(ticker)} headlines. **Event leads:** {len(leads)} found, {new} new on the admin page.")


if __name__ == "__main__":
    main()
