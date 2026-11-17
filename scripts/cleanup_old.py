"""
12-month clean-up (runs monthly from .github/workflows/tidy.yml). PERMANENT.

Deletes, from the Supabase database:
- approved events (docs col "events") that ended more than 12 months ago
- their flyer pictures in Storage (bucket "flyers"), unless another event still uses the same picture
- Review-queue items (submissions) whose event ended more than 12 months ago

Built-in events older than 12 months are removed by scripts/tidy_past.py.
Use --dry-run to only count. The run summary lists what was deleted.
"""
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sweep import DB, log, summary  # noqa: E402

LAGOS = dt.timezone(dt.timedelta(hours=1))
TODAY = dt.datetime.now(LAGOS).date()
KEEP_DAYS = 365
CUTOFF = (TODAY - dt.timedelta(days=KEEP_DAYS)).isoformat()
DRY = "--dry-run" in sys.argv


def ended(d):
    return (d or {}).get("e") or (d or {}).get("s") or ""


def blob_id(img):
    img = str(img or "")
    if img.startswith("/_blob/s-"):
        return img[len("/_blob/"):].split("?")[0]
    return None


def main():
    url, sk = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY")
    if not (url and sk):
        log("SUPABASE_URL or SUPABASE_SERVICE_KEY is not set.")
        sys.exit(1)
    db = DB(url, sk)

    events = db.col("events")
    old = [r for r in events if ended(r["data"]) and ended(r["data"]) < CUTOFF]
    keep = [r for r in events if r not in old]
    used = {blob_id((r["data"] or {}).get("img")) for r in keep} - {None}
    subs = db.col("submissions")
    for r in subs:
        for it in (r["data"] or {}).get("items", []):
            used.add(blob_id(it.get("img")))
    flyers = sorted({blob_id((r["data"] or {}).get("img")) for r in old} - {None} - used)

    sub_changes = []
    for r in subs:
        items = (r["data"] or {}).get("items", [])
        fresh = [it for it in items if not (ended(it) and ended(it) < CUTOFF)]
        if len(fresh) != len(items):
            sub_changes.append((r["id"], fresh, len(items) - len(fresh)))

    rows = ["| Deleted | Ended |", "|---|---|"] + [f"| {str(r['data'].get('name', ''))[:70]} | {ended(r['data'])} |" for r in old[:200]]
    head = (f"**12-month clean-up{' (dry run, nothing deleted)' if DRY else ''}:** {len(old)} event(s) that ended before {CUTOFF}, "
            f"{len(flyers)} unused flyer picture(s), {sum(c[2] for c in sub_changes)} old Review item(s).")
    log(head)
    summary(head + ("\n\n" + "\n".join(rows) if old else ""))
    if DRY:
        return

    for r in old:
        db._req("DELETE", f"/rest/v1/docs?col=eq.events&id=eq.{urllib.parse.quote(r['id'])}")
    for sid, fresh, _ in sub_changes:
        db.put("submissions", sid, {"items": fresh})
    for i in range(0, len(flyers), 100):
        req = urllib.request.Request(url.rstrip("/") + "/storage/v1/object/flyers", method="DELETE",
                                     data=json.dumps({"prefixes": flyers[i:i + 100]}).encode(),
                                     headers={"apikey": sk, "Authorization": f"Bearer {sk}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp.read()


if __name__ == "__main__":
    main()
