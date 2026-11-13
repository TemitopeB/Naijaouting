"""
Builds data/landing.json, the event list the landing page (index.html) shows.

It loads the main site (events/index.html) in a headless browser, feeds it the
approved events and fixes from Supabase, and asks the site's own code for the
final list, so the landing page always matches the main site.

Runs every morning on GitHub Actions (.github/workflows/landing-data.yml).
Run it yourself:  SUPABASE_URL=... SUPABASE_ANON_KEY=... python scripts/build_landing_data.py
For a local test without Supabase:  python scripts/build_landing_data.py --db-dir path/to/export
"""
import argparse
import glob
import json
import os
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent


def fetch_col(url, key, col):
    rows, start = [], 0
    while True:
        req = urllib.request.Request(
            f"{url.rstrip('/')}/rest/v1/docs?select=id,data&col=eq.{col}",
            headers={"apikey": key, "Authorization": f"Bearer {key}", "Range": f"{start}-{start + 999}"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            page = json.load(r)
        rows += page
        if len(page) < 1000:
            return rows
        start += 1000


def load_rows(args):
    if args.db_dir:
        out = {}
        for col in ("events", "overrides"):
            out[col] = []
            for f in glob.glob(os.path.join(args.db_dir, col, "*.json")):
                j = json.load(open(f))
                out[col].append({"id": os.path.basename(f)[:-5], "data": j.get("data", j)})
        return out["events"], out["overrides"]
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        sys.exit("Set SUPABASE_URL and SUPABASE_ANON_KEY, or pass --db-dir.")
    return fetch_col(url, key, "events"), fetch_col(url, key, "overrides")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", help="folder with events/*.json and overrides/*.json (local test)")
    args = ap.parse_args()
    ev_rows, ov_rows = load_rows(args)

    remote = []
    for r in ev_rows:
        d = dict(r["data"], id="r" + r["id"], src=0, pend=0, rev=1)
        remote.append(d)
    ovr = {}
    for r in ov_rows:
        d = r["data"] or {}
        if r["id"] == "notdup" or d.get("status") or not d.get("name"):
            continue
        ovr[d["name"]] = dict(d, oid=r["id"])

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        # Keep the real database adapter out: the stand-in below answers instead.
        pg.route("**/js/*.js", lambda route: route.fulfill(status=200, content_type="text/javascript", body=""))
        pg.add_init_script(path=str(ROOT / "scripts" / "headless_mock.js"))
        pg.goto((ROOT / "events" / "index.html").as_uri())
        pg.wait_for_timeout(1500)
        ev = pg.evaluate(
            """([R,O])=>{REMOTE=R.filter(v=>!v.hide).map(cleanEv);OVR=O;applyOvr();_AC=null;
            const img=v=>{const i=v.img||'';if(/^flyers\\//.test(i))return '/events/'+i;if(/^\\/_blob\\/[0-9a-zA-Z_-]+$/.test(i))return i;return ''};
            return all().map(v=>{const en=entLabel(v);return {k:evSlug(v),n:v.name,c:v.cat,ci:v.city,s:v.s,
              e:(v.e&&v.e!=='?'?v.e:v.s),ve:v.venue||'',t:v.time||'',f:en[0]||'',fr:en[1]?1:0,im:img(v),cx:isCx(v)?1:0}})}""",
            [remote, ovr],
        )
        cats = pg.evaluate("Object.fromEntries(Object.entries(CAT).map(([k,v])=>[k,[v[0]||'',v[1]||'']]))")
        b.close()

    for e in ev:
        # This flyer advertises a call for vendors, not the festival itself: show the category picture instead.
        if e["n"].startswith("Lagos Book and Art Festival (LABAF)"):
            e["im"] = ""
    for e in ev:  # drop pictures that are not in the project
        if e["im"].startswith("/events/flyers/") and not (ROOT / e["im"].lstrip("/")).exists():
            e["im"] = ""
    ev.sort(key=lambda e: (e["s"], e["n"]))
    out = ROOT / "data" / "landing.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"ev": ev, "cats": cats}, ensure_ascii=False, separators=(",", ":")))
    print(f"landing.json: {len(ev)} events, {sum(1 for e in ev if e['im'])} with flyers")


if __name__ == "__main__":
    main()
