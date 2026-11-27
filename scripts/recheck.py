"""
Daily re-check: looks again at the official page of every upcoming event and spots
cancellations, postponements, new dates, venue changes and sold-out notices.

Clear changes are applied on the site straight away: Eventbrite's own data, or a sentence copied
from the official page (or a news report) that really is on that page, with high confidence.
Each one is also listed in Review ("Updated on the site by the daily check") with the page link,
the exact sentence and an Undo button. Less certain findings wait in Review for one tap.
Set RECHECK_AUTO_APPLY=0 to go back to suggestions only.

How it checks:
  - Eventbrite links: Eventbrite's own API says whether the event was cancelled and gives
    its current date and venue (needs the EVENTBRITE_TOKEN secret; skipped without it).
  - Other official pages: the page text is read; only if it mentions words like
    "cancelled", "postponed", "new date" or "venue" does Gemini read it closely. Gemini's
    answer is used only when the sentence it quotes is really on the page.
  - Instagram, Facebook and WhatsApp links can't be read automatically. For events in the next
    10 days that only have those links (or none), Gemini searches the web for news of a change,
    and the finding counts only if the quoted sentence is really on the source page.
  - It follows each website's robots.txt (pages a site asks robots not to visit are skipped),
    says who it is, and waits at least 3 seconds between pages on the same website.

Schedule: twice a day for events in the next 14 days; later events on Mondays.
A change already suggested (waiting, applied or dismissed) is not suggested again.

Runs on GitHub Actions (.github/workflows/recheck.yml).
Run it yourself:
  SUPABASE_URL=... SUPABASE_SERVICE_KEY=... GEMINI_API_KEY=... python scripts/recheck.py --dry-run
Options: --all (check every upcoming event today), --limit N, --only "event name".
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gemini  # noqa: E402

UA = "NaijaOutingBot/1.0 (+https://github.com/TemitopeB/Naijaouting; checks event status)"
SKIP_HOSTS = re.compile(r"(^|\.)(instagram\.com|facebook\.com|fb\.me|wa\.me|whatsapp\.com|x\.com|twitter\.com|"
                        r"tiktok\.com|t\.me|linktr\.ee|bit\.ly|youtube\.com|youtu\.be|google\.com|goo\.gl)$", re.I)
WORDS = re.compile(r"cancel+ed|cancel+ation|postpone|reschedul|new date|date change|moved to|change of venue|"
                   r"venue change|new venue|relocat|called off|no longer (hold|tak)|will not (hold|go ahead)|"
                   r"sold[\s-]*out|tickets? (are )?(no longer|not) available|suspend", re.I)
STATES = {"cancelled", "postponed", "venue", "soldout"}
LABEL = {"cancelled": "cancelled", "postponed": "postponed", "venue": "venue changed", "soldout": "sold out"}
CORR_DOC = "autocheck"     # corrections/<this>: the Review queue reads items from here
STATE = ("jobs", "recheck")
MAX_ITEMS = 90             # the Review queue shows up to 100 items per document


def log(*a):
    print(*a, flush=True)


def summary(md):
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a") as f:
            f.write(md + "\n")


class DB:
    def __init__(self, url, key):
        self.url, self.key = url.rstrip("/"), key

    def _req(self, method, path, body=None, extra=None):
        h = {"apikey": self.key, "Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        h.update(extra or {})
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.url + path, data=data, headers=h, method=method)
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else None

    def col(self, col):
        rows, start = [], 0
        while True:
            page = self._req("GET", f"/rest/v1/docs?select=id,data&col=eq.{col}", extra={"Range": f"{start}-{start + 999}"}) or []
            rows += page
            if len(page) < 1000:
                return rows
            start += 1000

    def get(self, col, id_):
        rows = self._req("GET", f"/rest/v1/docs?select=data&col=eq.{col}&id=eq.{urllib.parse.quote(id_)}") or []
        return rows[0]["data"] if rows else None

    def put(self, col, id_, data):
        self._req("POST", "/rest/v1/docs?on_conflict=col,id", [{"col": col, "id": id_, "data": data}],
                  {"Prefer": "resolution=merge-duplicates,return=minimal"})


# ---------------- the site's own event list ----------------
def site_events(db):
    """Load events/index.html headless, feed it the approved events and fixes, and ask the
    site's own code for each upcoming event with its official links (same list visitors see)."""
    ev_rows, ov_rows = db.col("events"), db.col("overrides")
    remote = [dict(r["data"], id="r" + r["id"], src=0, pend=0, rev=1) for r in ev_rows]
    ovr, status = {}, {}
    for r in ov_rows:
        d = r["data"] or {}
        if d.get("status") and d.get("name"):
            status[d["name"]] = d["status"]
            continue
        if r["id"] == "notdup" or not d.get("name"):
            continue
        ovr[d["name"]] = dict(d, oid=r["id"])
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.route("**/js/*.js", lambda route: route.fulfill(status=200, content_type="text/javascript", body=""))
        pg.add_init_script(path=str(ROOT / "scripts" / "headless_mock.js"))
        pg.goto((ROOT / "events" / "index.html").as_uri())
        pg.wait_for_timeout(1500)
        ev = pg.evaluate(
            """([R,O])=>{REMOTE=R.filter(v=>!v.hide).map(cleanEv);OVR=O;applyOvr();_AC=null;
            return all().filter(v=>(v.e&&v.e!=='?'?v.e:v.s)>=TODAY&&!v.pend).map(v=>{let l=[];try{l=(access(v).l||[]).map(x=>x[1])}catch(x){}
              if(v.link)l.push(v.link);return {id:v.id,n:v.name,s:v.s,e:(v.e&&v.e!=='?'?v.e:v.s),ve:v.venue||'',ci:v.city||'',on:!!v.online,u:[...new Set(l.filter(Boolean))]}})}""",
            [remote, ovr])
        b.close()
    for e in ev:
        e["st"] = (status.get(e["n"]) or {}).get("st", "")
    return ev


# ---------------- reading pages ----------------
def host(u):
    try:
        return (urllib.parse.urlparse(u).hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""


_robots, _last = {}, {}


def allowed(url):
    """Follow each site's visiting rules (robots.txt), like the weekly sweep does."""
    u = urllib.parse.urlparse(url)
    base = f"{u.scheme}://{u.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(base + "/robots.txt", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                rp.parse(r.read().decode("utf-8", "replace").splitlines())
        except urllib.error.HTTPError as ex:
            rp.parse([] if ex.code in (404, 410) else ["User-agent: *", "Disallow: /"])  # no rules: allowed; locked: stay out
        except Exception:
            rp.parse([])
        _robots[base] = rp
    return _robots[base].can_fetch(UA, url)


def polite(url):
    """At least 3 seconds between two pages on the same website."""
    h = urllib.parse.urlparse(url).netloc
    wait = 3 - (time.time() - _last.get(h, 0))
    if wait > 0:
        time.sleep(wait)
    _last[h] = time.time()


def fetch(url):
    polite(url)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
                                               "Accept-Language": "en-GB,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read(1_500_000).decode(r.headers.get_content_charset() or "utf-8", "replace")


def page_text(raw):
    t = re.sub(r"(?is)<(script|style|noscript|svg|template)[^>]*>.*?</\1>", " ", raw)
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h[1-6]|tr|section|article)>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def around_words(text, width=700, cap=9000):
    """The parts of the page near the warning words (plus the start, where the title and date usually are)."""
    parts, last = [text[:1500]], 0
    for m in WORDS.finditer(text):
        a, b = max(0, m.start() - width), min(len(text), m.end() + width)
        if a < last:
            a = last
        if b > a:
            parts.append(text[a:b])
            last = b
        if sum(len(p) for p in parts) > cap:
            break
    return "\n…\n".join(parts)[:cap]


def squash(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


# ---------------- Eventbrite ----------------
def eventbrite_check(e, url):
    tok = os.environ.get("EVENTBRITE_TOKEN")
    m = re.search(r"eventbrite\.[a-z.]+/e/(?:[^/?#]*-)?(\d{6,})", url)
    if not tok or not m:
        return None
    api = f"https://www.eventbriteapi.com/v3/events/{m.group(1)}/?expand=venue"
    req = urllib.request.Request(api, headers={"Authorization": f"Bearer {tok}", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.load(r)
    stat = (j.get("status") or "").lower()
    start = ((j.get("start") or {}).get("local") or "")[:10]
    vname = ((j.get("venue") or {}).get("name") or "").strip()
    if stat in ("canceled", "cancelled"):
        return {"status": "cancelled", "quote": "Eventbrite lists this event as cancelled.", "new_date": "", "new_venue": "", "confidence": 1, "how": "eventbrite"}
    if start and start != e["s"] and start > e["s"]:
        return {"status": "postponed", "quote": f"Eventbrite now gives the start date as {start}.", "new_date": start, "new_venue": "", "confidence": 1, "how": "eventbrite"}
    if vname and e["ve"] and squash(vname) not in squash(e["ve"]) and squash(e["ve"]) not in squash(vname) and not j.get("online_event"):
        return {"status": "venue", "quote": f"Eventbrite now gives the venue as {vname}.", "new_date": "", "new_venue": vname, "confidence": 1, "how": "eventbrite"}
    if (j.get("ticket_availability") or {}).get("is_sold_out"):
        return {"status": "soldout", "quote": "Eventbrite shows the tickets as sold out.", "new_date": "", "new_venue": "", "confidence": 1, "how": "eventbrite"}
    return {"status": "ok"}


# ---------------- Gemini reads the page ----------------
PROMPT = """You check whether an event listing is still correct. Read the web page text below and answer
ONLY with JSON in this shape:
{{"about_this_event": true/false, "status": "ok|cancelled|postponed|venue|soldout|unclear",
  "new_date": "YYYY-MM-DD or empty", "new_venue": "venue name or empty",
  "quote": "the exact sentence from the page that shows the change, copied word for word, or empty",
  "confidence": 0.0-1.0}}

Rules:
- The event we list: "{name}", on {date} at "{venue}", {city}.
- "about_this_event" is false if the page talks about a different event, a past edition, or a different year.
- "postponed" means a new later date or "postponed / date to be announced". "venue" means it moved to a different place.
- "cancelled" only if the page clearly says this event is cancelled or will not hold.
- If the page only mentions these words in passing (e.g. a refund policy "if an event is cancelled..."), answer "ok".
- If you are not sure, answer "unclear". Never guess a date or venue.

PAGE ({url}):
{text}
"""


def gemini_check(e, url, text):
    ans, _ = gemini.ask(PROMPT.format(name=e["n"], date=e["s"] if e["s"] == e["e"] else f"{e['s']} to {e['e']}",
                                      venue=e["ve"] or "venue not given", city=e["ci"] or "Nigeria", url=url,
                                      text=around_words(text)), temperature=0.0)
    j = gemini.parse_json(ans)
    if not isinstance(j, dict):
        return None
    st = str(j.get("status", "")).lower()
    q = str(j.get("quote", "")).strip()
    if st not in STATES or not j.get("about_this_event") or float(j.get("confidence") or 0) < 0.7:
        return {"status": "ok"}
    # the quote must really be on the page, word for word (ignoring spacing and punctuation)
    if len(squash(q)) < 12 or squash(q) not in squash(text):
        return {"status": "unclear"}
    nd = str(j.get("new_date", "")).strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", nd):
        nd = ""
    return {"status": st, "quote": q[:400], "new_date": nd, "new_venue": str(j.get("new_venue", "")).strip()[:120],
            "confidence": float(j.get("confidence") or 0), "how": "page"}



# ---------------- events with no readable official page: look for news of a change ----------------
SEARCH_PROMPT = """Search the web for recent news or official announcements about this event in Nigeria:
"{name}", listed for {date} at "{venue}", {city}.

Has it been postponed, cancelled, moved to another venue, or sold out? Answer ONLY with JSON:
{{"status": "ok|cancelled|postponed|venue|soldout|unclear",
  "quote": "the exact sentence from the source that says so, copied word for word, or empty",
  "source": "the web address of that source, or empty",
  "new_date": "YYYY-MM-DD or empty", "new_venue": "venue name or empty", "confidence": 0.0-1.0}}

Rules: it must be this event and this year's edition. Answer "ok" if you find nothing saying it changed.
If sources disagree or you are not sure, answer "unclear". Never guess a date or venue."""


_sm = None


def SEARCH_MODELS():
    global _sm
    if _sm is None:
        _sm = gemini.search_models()
    return _sm


def search_check(e):
    """Gemini searches the web; a change only counts if the quoted sentence is really on the source page."""
    ans, srcs = gemini.ask(SEARCH_PROMPT.format(name=e["n"], date=e["s"] if e["s"] == e["e"] else f"{e['s']} to {e['e']}",
                                                venue=e["ve"] or "venue not given", city=e["ci"] or "Nigeria"),
                           search=True, temperature=0.0, models=SEARCH_MODELS())
    j = gemini.parse_json(ans)
    if not isinstance(j, dict):
        return None
    st = str(j.get("status", "")).lower()
    q = str(j.get("quote", "")).strip()
    if st not in STATES or float(j.get("confidence") or 0) < 0.8 or len(squash(q)) < 12:
        return {"status": "ok"}
    cands = []
    for u in [str(j.get("source", "")).strip()] + [gemini.real_url(x["uri"]) for x in srcs[:6]]:
        if u.startswith("https://") and u not in cands and not SKIP_HOSTS.search(host(u)):
            cands.append(u)
    for u in cands[:4]:
        try:
            if not allowed(u):
                continue
            text = page_text(fetch(u))
        except Exception:
            continue
        if squash(q) in squash(text):
            nd = str(j.get("new_date", "")).strip()
            return {"status": st, "quote": q[:400], "new_date": nd if re.fullmatch(r"\d{4}-\d{2}-\d{2}", nd) else "",
                    "new_venue": str(j.get("new_venue", "")).strip()[:120], "url": u,
                    "confidence": float(j.get("confidence") or 0), "how": "search"}
    return {"status": "unclear"}


# ---------------- applying a change on the site straight away ----------------
AUTO = os.environ.get("RECHECK_AUTO_APPLY", "1") != "0"


def site_hash(s):
    """Same as hsh() in events/index.html (FNV-1a over UTF-16 code units), so the site finds the status."""
    h = 2166136261
    b = s.encode("utf-16-le")
    for i in range(0, len(b), 2):
        h ^= b[i] | (b[i + 1] << 8)
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def sure_enough(r):
    """Only clear, verified findings go live by themselves: Eventbrite's own data, or a sentence copied
    from the official page / a news source that really is on that page, with high confidence."""
    return r.get("how") == "eventbrite" or (r.get("how") in ("page", "search") and r.get("confidence", 0) >= 0.85)

# ---------------- suggestions ----------------
def human_date(d):
    try:
        x = dt.date.fromisoformat(d)
        return f"{x.day} {x.strftime('%b %Y')}"
    except Exception:
        return d


def make_item(e, url, r):
    st = r["status"]
    public = ""
    if st == "postponed" and r.get("new_date"):
        public = "New date: " + human_date(r["new_date"])
    elif st == "venue" and r.get("new_venue"):
        public = "Now at " + r["new_venue"]
    note = "Daily check: the official page says it is " + LABEL[st] + ((" (" + public[0].lower() + public[1:] + ")") if public else "")
    return {"iid": f"{int(time.time() * 1000)}-{hashlib.md5((e['n'] + st + url).encode()).hexdigest()[:5]}",
            "eid": e["id"], "name": e["n"], "kind": "status", "st": st, "by": "check", "note": note,
            "url": url, "quote": r.get("quote", ""), "snote": public, "contact": "",
            "found": dt.date.today().isoformat()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print what would be suggested, change nothing")
    ap.add_argument("--all", action="store_true", help="check every upcoming event, not only today's share")
    ap.add_argument("--limit", type=int, default=120, help="most pages to read in one run")
    ap.add_argument("--only", help="check just this event (name contains)")
    a = ap.parse_args()

    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_KEY (GitHub: Settings -> Secrets and variables -> Actions).")
    db = DB(url, key)
    state = db.get(*STATE) or {}
    seen = state.get("seen", {})

    today = dt.date.today()
    soon = (today + dt.timedelta(days=14)).isoformat()
    monday = today.weekday() == 0
    events = site_events(db)
    log(f"{len(events)} upcoming events on the site")

    todo, skipped_social, no_link, searchq = [], 0, 0, []
    for e in events:
        if a.only and a.only.lower() not in e["n"].lower():
            continue
        if e["st"] == "cancelled":
            continue
        if not (a.all or a.only or e["s"] <= soon or monday):
            continue
        urls = [u for u in e["u"] if u.startswith("http") and not SKIP_HOSTS.search(host(u))]
        if not urls:
            if e["s"] <= (today + dt.timedelta(days=10)).isoformat() and e["st"] not in ("postponed",):
                searchq.append(e)
            if e["u"]:
                skipped_social += 1
            else:
                no_link += 1
            continue
        todo.append((e, urls[:2]))
    todo.sort(key=lambda x: x[0]["s"])
    todo = todo[:a.limit]
    log(f"checking {len(todo)} events ({skipped_social} only have Instagram/Facebook links, {no_link} have no official link)")

    found, failed, read, ai, blocked = [], [], 0, 0, 0
    for e, urls in todo:
        res = None
        for u in urls:
            try:
                if "eventbrite." in host(u):
                    res = eventbrite_check(e, u)
                    if res is not None:
                        res["url"] = u
                        break
                if not allowed(u):
                    blocked += 1
                    continue
                raw = fetch(u)
                read += 1
                text = page_text(raw)
                if not WORDS.search(text):
                    res = {"status": "ok", "url": u}
                    break
                ai += 1
                r = gemini_check(e, u, text)
                if r:
                    r["url"] = u
                    res = r
                    if r["status"] in STATES:
                        break
            except gemini.GeminiError as ex:
                log(f"  Gemini unavailable ({ex}); stopping close reading for today")
                failed.append((e["n"], u, "Gemini unavailable"))
                res = res or {"status": "unclear", "url": u}
                break
            except (urllib.error.URLError, TimeoutError, ConnectionError, ValueError) as ex:
                failed.append((e["n"], u, str(getattr(ex, "code", "") or ex)[:60]))
        if res and res.get("status") == "postponed" and res.get("new_date") and res["new_date"] <= e["s"]:
            res = {"status": "ok"}  # the listing already shows the new date
        if res and res.get("status") in STATES and res["status"] != e["st"]:
            k = "|".join([e["n"], res["status"], res.get("new_date", ""), squash(res.get("new_venue", ""))])
            if k in seen:
                continue
            item = make_item(e, res["url"], res)
            item["_r"] = res
            found.append(item)
            seen[k] = today.isoformat()
            log(f"  CHANGE  {e['n']}: {item['note']}  <{res['url']}>  “{item['quote'][:120]}”")

    searched = 0
    for e in sorted(searchq, key=lambda x: x["s"])[:int(os.environ.get("RECHECK_SEARCH_MAX", "20"))]:
        try:
            r = search_check(e)
        except gemini.GeminiError as ex:
            log(f"  Gemini search unavailable ({str(ex)[:120]}); stopping web searches for today")
            for q_ in gemini.QUOTA_LOG[-2:]:
                log("    limit hit: " + q_[:220])
            break
        searched += 1
        if r and r.get("status") == "postponed" and r.get("new_date") and r["new_date"] <= e["s"]:
            continue
        if r and r.get("status") in STATES and r["status"] != e["st"]:
            k = "|".join([e["n"], r["status"], r.get("new_date", ""), squash(r.get("new_venue", ""))])
            if k in seen:
                continue
            item = make_item(e, r["url"], r)
            item["_r"] = r
            found.append(item)
            seen[k] = today.isoformat()
            log(f"  CHANGE (news)  {e['n']}: {item['note']}  <{r['url']}>  “{item['quote'][:120]}”")
    log(f"searched the web for {searched} events that have no readable official page")
    log(f"read {read} pages, {ai} read closely by Gemini, {len(found)} changes found, {len(failed)} couldn't be read, {blocked} skipped (the site asks robots not to visit)")
    md = [f"### Daily event re-check, {today.isoformat()}",
          f"- Events checked: **{len(todo)}** ({read} pages read, {ai} read closely, {blocked} skipped by the site's robots.txt)",
          f"- Changes found: **{len(found)}** (clear ones are applied on the site straight away; the rest wait in Review → Corrections)"]
    for it in found:
        md.append(f"  - {it['name']}: {LABEL[it['st']]}{(' · ' + it['snote']) if it['snote'] else ''} — [{host(it['url'])}]({it['url']})")
    if failed:
        md.append(f"- Couldn't read: {len(failed)} (site blocked or offline)")
    md.append(f"- Skipped: {skipped_social} with only Instagram/Facebook links, {no_link} with no official link")
    summary("\n".join(md))

    if a.dry_run:
        log("dry run: nothing saved")
        return
    applied = 0
    for it in found:
        r = it.pop("_r", {}) or {}
        if AUTO and sure_enough(r):
            db.put("overrides", "s" + str(site_hash(it["name"])),
                   {"name": it["name"], "status": {"st": it["st"], "note": it.get("snote", ""), "at": dt.datetime.now(dt.timezone.utc).isoformat(),
                                                   "by": "check", "url": it["url"]}})
            it["applied"] = True
            applied += 1
            log(f"  APPLIED on the site: {it['name']} -> {LABEL[it['st']]}")
    if applied:
        summary(f"- **Updated on the site automatically: {applied}** (each one is in Review with an Undo button)")
    if found:
        doc = db.get("corrections", CORR_DOC) or {}
        items = (doc.get("items") or []) + found
        db.put("corrections", CORR_DOC, {"items": items[-MAX_ITEMS:]})
    # forget suggestions older than 120 days so the record stays small
    cut = (today - dt.timedelta(days=120)).isoformat()
    seen = {k: v for k, v in seen.items() if v >= cut}
    db.put(*STATE, {"seen": seen, "last": today.isoformat(), "checked": len(todo), "found": len(found)})


if __name__ == "__main__":
    main()
