"""
Inbox: events found by hand or by Claude go to the site's Review queue.

Put a JSON file in data/inbox/ shaped like:
  {"found_by": "Claude", "found_on": "2026-11-17", "items": [ {event}, ... ]}
Each event uses the same fields as the Add event form:
  name, cat, s (YYYY-MM-DD), e, time, venue, city, fee, about, link, img, online (1), plat
"about" should end with "Source: <page>" so the reviewer can check it.

On push (or "Run workflow"), .github/workflows/inbox.yml runs this script. It:
  - skips events that are already on the site, already waiting, already sent before, past,
    or that break the listing rules,
  - adds the rest to the Review queue (Supabase docs: col "submissions", id "inbox").
Nothing goes live until an admin approves it.
"""
import datetime as dt
import json
import os
import pathlib
import random
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sweep import DB, key, log, summary, MAX_WAITING  # noqa: E402
from smart_sweep import risky, PLATS  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
INBOX = ROOT / "data" / "inbox"
LAGOS = dt.timezone(dt.timedelta(hours=1))
TODAY = dt.datetime.now(LAGOS).date()
FIELDS = ("name", "cat", "s", "e", "time", "venue", "city", "state", "fee", "about", "link", "img", "online", "plat")


def clean(e):
    if not isinstance(e, dict):
        return None, "not an event"
    it = {k: e[k] for k in FIELDS if e.get(k) not in (None, "")}
    it["name"] = str(it.get("name", "")).strip()[:160]
    if not it["name"]:
        return None, "no name"
    try:
        sd = dt.date.fromisoformat(str(it.get("s", ""))[:10])
    except ValueError:
        return None, "no valid date"
    try:
        ed = dt.date.fromisoformat(str(it.get("e", ""))[:10]) if it.get("e") else sd
    except ValueError:
        ed = sd
    if max(sd, ed) < TODAY:
        return None, "already over"
    it["s"], it["e"] = sd.isoformat(), max(sd, ed).isoformat()
    if risky(it.get("name"), it.get("about"), it.get("fee")):
        return None, "breaks the listing rules"
    link = str(it.get("link", ""))
    if link and not link.startswith("https://"):
        it.pop("link", None)
    if it.get("online"):
        it["online"], it["city"], it["venue"] = 1, "Online", ""
        it["plat"] = it.get("plat") if it.get("plat") in PLATS else "Online"
    elif not it.get("city"):
        return None, "no city"
    it.setdefault("fee", "See organiser")
    it["iid"] = f"{int(time.time() * 1000)}-{random.randrange(36**5):05x}"
    it["src"] = "inbox"
    it["at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    return it, "ok"


def main():
    files = sorted(INBOX.glob("*.json"))
    if not files:
        log("Inbox is empty.")
        return
    url, sk = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY")
    if not (url and sk):
        log("SUPABASE_URL or SUPABASE_SERVICE_KEY is not set.")
        sys.exit(1)
    db = DB(url, sk)

    known = {key(r["data"]) for r in db.col("events")}
    for r in db.col("submissions"):
        for it in (r["data"] or {}).get("items", []):
            known.add(key(it))
    seen = {tuple(x) for x in (db.get("inbox", "seen") or {}).get("keys", []) if isinstance(x, list) and len(x) == 2}  # sent before (even if later rejected)

    added, rows = [], ["| File | Event | Result |", "|---|---|---|"]
    for f in files:
        try:
            data = json.loads(f.read_text())
        except Exception as ex:
            rows.append(f"| {f.name} | (whole file) | not valid JSON: {ex} |")
            continue
        for e in data.get("items", []):
            it, why = clean(e)
            if it:
                k = key(it)
                if k in known:
                    it, why = None, "already on the site or waiting"
                elif k in seen:
                    it, why = None, "sent before"
            if it:
                known.add(key(it))
                seen.add(key(it))
                added.append(it)
                why = "sent to Review"
            rows.append(f"| {f.name} | {str(e.get('name', ''))[:70]} | {why} |")

    if added:
        cur = (db.get("submissions", "inbox") or {}).get("items", [])
        db.put("submissions", "inbox", {"items": (cur + added)[-MAX_WAITING:]})
    db.put("inbox", "seen", {"keys": [list(x) for x in sorted(seen)][-5000:]})
    log(f"Inbox: {len(added)} event(s) sent to Review.")
    summary(f"**Inbox: {len(added)} event(s) sent to Review.**\n\n" + "\n".join(rows))


if __name__ == "__main__":
    main()
