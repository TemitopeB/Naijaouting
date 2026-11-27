"""
Collect recent event posts from the promoters in promoters.txt, ready for the site's
Import (Review -> Import events -> choose the zip). Claude then reads each flyer and caption
on the site, and nothing goes live until you press Publish.

It uses Instagram's official API (Business Discovery), so it only works for Business and
Creator accounts. Personal accounts are skipped and listed at the end.

Setup (once):
  1. Copy config.example.json to config.json in this folder and fill in your token and your
     own Instagram business account ID. config.json is never uploaded (it's in .gitignore).
  2. pip install requests

Run:
  python fetch_promoters.py                 posts from the last 21 days that look like events
  python fetch_promoters.py --days 7        only the last week
  python fetch_promoters.py --all           every post, not only the ones that look like events
  python fetch_promoters.py --only flytimefest,gidifest   just these accounts
  python fetch_promoters.py --again         include posts you already collected before

Output: out/posts_<date>.zip with posts.csv (instagram_account, post_url, post_date,
flyer_files, caption) and the flyer pictures. Posts already collected are remembered in
seen.json, so next week's zip only has new posts.
"""
import argparse
import csv
import datetime as dt
import io
import json
import pathlib
import re
import sys
import time
import zipfile

try:
    import requests
except ImportError:
    sys.exit("Please install requests first:  pip install requests")

HERE = pathlib.Path(__file__).resolve().parent
API = "https://graph.facebook.com"

# words and patterns that suggest a post is about an event (kept generous: Claude does the real reading)
EVENT_RE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*\d{1,2}\b|\b\d{1,2}(st|nd|rd|th)\b|"
    r"\b\d{1,2}[/.-]\d{1,2}([/.-]\d{2,4})?\b|\b(mon|tue|wed|thu|fri|sat|sun)(day)?\b|"
    r"ticket|tix|rsvp|regist|venue|gate|admission|free entry|entry fee|early bird|vip|table|"
    r"live in|concert|festival|fest\b|carnival|show\b|tour\b|party|rave|night\b|edition|"
    r"conference|summit|expo|fair\b|workshop|masterclass|bootcamp|meetup|hangout|exhibition|"
    r"crusade|worship|praise|convention|retreat|link in bio|save the date|happening|this (fri|sat|sun)|"
    r"\b\d{1,2}(:\d{2})?\s?(am|pm)\b|₦|naira", re.I)


def handles(path):
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        for h in re.findall(r"@([A-Za-z0-9._]{1,30})", line):
            h = h.lower().rstrip(".")
            if h not in out:
                out.append(h)
    return out


def load_config():
    p = HERE / "config.json"
    if not p.exists():
        sys.exit("Missing config.json. Copy config.example.json to config.json and fill it in.")
    c = json.loads(p.read_text(encoding="utf-8"))
    tok = c.get("access_token") or c.get("token")
    uid = c.get("ig_user_id") or c.get("instagram_user_id") or c.get("instagram_business_account_id") or c.get("user_id")
    if not tok or not uid or "PASTE" in str(tok):
        sys.exit("config.json needs access_token and ig_user_id.")
    return tok, str(uid), c.get("api_version") or c.get("graph_version") or "v21.0"


FIELDS = ("business_discovery.username({h}){{username,name,"
          "media.limit({n}){{id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,"
          "children{{media_type,media_url,thumbnail_url}}}}}}")


def fetch_account(s, ver, uid, tok, h, n):
    r = s.get(f"{API}/{ver}/{uid}", params={"fields": FIELDS.format(h=h, n=n), "access_token": tok}, timeout=40)
    j = r.json()
    if "error" in j:
        e = j["error"]
        return None, e
    return (j.get("business_discovery") or {}).get("media", {}).get("data", []), None


def pictures(m):
    t = m.get("media_type")
    if t == "CAROUSEL_ALBUM":
        urls = []
        for c in (m.get("children") or {}).get("data", [])[:4]:
            u = c.get("media_url") if c.get("media_type") == "IMAGE" else c.get("thumbnail_url")
            if u:
                urls.append(u)
        return urls
    if t == "VIDEO":
        return [m["thumbnail_url"]] if m.get("thumbnail_url") else []
    return [m["media_url"]] if m.get("media_url") else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=21, help="how far back to look (default 21 days)")
    ap.add_argument("--per-account", type=int, default=15, help="recent posts to look at per account (default 15)")
    ap.add_argument("--all", action="store_true", help="keep every post, not only ones that look like events")
    ap.add_argument("--only", help="comma-separated handles to read instead of the whole list")
    ap.add_argument("--again", action="store_true", help="include posts collected before")
    ap.add_argument("--list", default=str(HERE / "promoters.txt"), help="the promoters file")
    a = ap.parse_args()

    tok, uid, ver = load_config()
    H = [x.strip().lstrip("@").lower() for x in a.only.split(",")] if a.only else handles(pathlib.Path(a.list))
    seen_p = HERE / "seen.json"
    seen = set(json.loads(seen_p.read_text())) if seen_p.exists() else set()
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=a.days)
    s = requests.Session()
    s.headers["User-Agent"] = "NaijaOuting promoter reader"

    rows, files, skipped, failed, looked = [], {}, [], [], 0
    print(f"Reading {len(H)} accounts (posts from the last {a.days} days)…")
    for i, h in enumerate(H, 1):
        media, err = fetch_account(s, ver, uid, tok, h, a.per_account)
        if err:
            code, msg = err.get("code"), err.get("message", "")
            if code in (190,):
                sys.exit(f"Your token has expired or isn't valid ({msg}). Make a new one and put it in config.json.")
            if code in (4, 17, 32, 613):
                print("  Instagram says we're reading too fast. Waiting 10 minutes…")
                time.sleep(600)
                media, err = fetch_account(s, ver, uid, tok, h, a.per_account)
            if err:
                (skipped if code in (110, 100) else failed).append((h, msg[:90]))
                print(f"  [{i}/{len(H)}] @{h}: skipped ({'personal account or not found' if code in (110, 100) else msg[:60]})")
                time.sleep(1.2)
                continue
        kept = 0
        for m in media:
            looked += 1
            ts = dt.datetime.strptime(m["timestamp"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc)
            if ts < since:
                continue
            if m["id"] in seen and not a.again:
                continue
            cap = (m.get("caption") or "").strip()
            if not a.all and not EVENT_RE.search(cap):
                continue
            names = []
            for k, u in enumerate(pictures(m), 1):
                try:
                    r = s.get(u, timeout=40)
                    if r.ok and r.content:
                        name = f"{re.sub(r'[^a-z0-9_]', '_', h)}_{m['id']}_{k}.jpg"
                        files[name] = r.content
                        names.append(name)
                except requests.RequestException:
                    pass
            if not names and not cap:
                continue
            rows.append([h, m.get("permalink", ""), ts.date().isoformat(), ";".join(names), cap])
            seen.add(m["id"])
            kept += 1
        print(f"  [{i}/{len(H)}] @{h}: {kept} post{'s' if kept != 1 else ''}")
        time.sleep(1.2)  # stay well inside Instagram's limit (about 200 requests an hour)

    out = HERE / "out"
    out.mkdir(exist_ok=True)
    if rows:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["instagram_account", "post_url", "post_date", "flyer_files", "caption"])
        w.writerows(rows)
        z = out / f"posts_{dt.date.today().isoformat()}.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("posts.csv", buf.getvalue())
            for n, b in files.items():
                zf.writestr(n, b)  # pictures sit next to posts.csv so the Import matches them by name
        seen_p.write_text(json.dumps(sorted(seen)))
        print(f"\nDone: {len(rows)} posts with {len(files)} pictures -> {z}")
        print("Next: on the site, Review -> Import events -> choose this zip.")
    else:
        print("\nNo new event posts this time.")
    if skipped:
        print(f"\n{len(skipped)} accounts couldn't be read (personal accounts, renamed or not found):")
        print("  " + ", ".join("@" + h for h, _ in skipped))
    if failed:
        print(f"\n{len(failed)} accounts had other errors:")
        for h, msg in failed:
            print(f"  @{h}: {msg}")


if __name__ == "__main__":
    main()
