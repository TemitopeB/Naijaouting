"""
Monthly tidy-up of the built-in event list (runs from .github/workflows/tidy.yml).

Built-in events live in events/index.html (const RAW=[ ... ]), one event per line.
Their ids come from their position ("b0", "b1", ...), so ended events are NOT removed:
each ended line is replaced by 0, which keeps every other id the same (saved events,
fixes and links keep working). The ended event's details move to data/past-events.json,
which the site reads only when someone opens an old link to that event.

Also:
- removes ended events' flyer entries from the page's flyer list (FLY), if nothing upcoming uses them
- drops events from data/past-events.json that ended more than 12 months ago (permanent)

Usage: python scripts/tidy_past.py [--dry-run]
"""
import datetime as dt
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / "events" / "index.html"
ARCHIVE = ROOT / "data" / "past-events.json"
LAGOS = dt.timezone(dt.timedelta(hours=1))
TODAY = dt.datetime.now(LAGOS).date()
KEEP_DAYS = 365
DRY = "--dry-run" in sys.argv
SUMMARY = __import__("os").environ.get("GITHUB_STEP_SUMMARY")


def say(msg):
    print(msg)
    if SUMMARY:
        with open(SUMMARY, "a") as f:
            f.write(msg + "\n\n")


def consts(page):
    """Values of simple string constants used inside RAW rows (SEE, TBC...)."""
    out = {}
    for name in ("SEE", "TBC"):
        m = re.search(r'\b' + name + r'="([^"]*)"', page)
        if m:
            out[name] = m.group(1)
    return out


def parse_row(line, cv):
    t = line.strip().rstrip(",")
    for name, val in cv.items():
        # "text "+TBC  ->  "text <value>"
        t = re.sub(r'"\s*\+\s*' + name + r'\b', lambda m, v=val: json.dumps(v)[1:-1] + '"', t)
        # bare SEE / TBC as a value
        t = re.sub(r'(?<=[\[,])\s*' + name + r'\s*(?=[,\]])', json.dumps(val), t)
    return json.loads(t)


def main():
    page = PAGE.read_text()
    start = page.index("const RAW=[\n") + len("const RAW=[\n")
    end = page.index("\n];", start)
    lines = page[start:end].split("\n")
    cv = consts(page)
    fly_m = re.search(r"^const FLY=(\{.*\});$", page, re.M)
    fly = json.loads(fly_m.group(1)) if fly_m else {}

    archive = json.loads(ARCHIVE.read_text()) if ARCHIVE.exists() else {"events": []}
    have = {e["id"] for e in archive.get("events", [])}

    moved, kept_names, new_lines, idx = [], set(), [], 0
    for ln in lines:
        st = ln.strip()
        if not st:
            new_lines.append(ln)
            continue
        if not st.startswith("[") and st.rstrip(",") != "0":
            new_lines.append(ln)  # comments and stray commas: not events
            continue
        if st.rstrip(",") == "0":
            new_lines.append(ln)
            idx += 1
            continue
        try:
            a = parse_row(st, cv)
        except Exception as ex:
            print(f"Couldn't read line for b{idx}: {ex}")
            new_lines.append(ln)
            if st.startswith("["):
                idx += 1
            continue
        e_date = (a[3] or a[2]) if len(a) > 3 else a[2]
        if e_date and e_date < TODAY.isoformat():
            ev = {"id": f"b{idx}", "name": a[0], "cat": a[1], "s": a[2], "e": a[3] or a[2], "venue": a[4],
                  "city": a[5], "state": a[6], "src": a[7], "fee": a[8], "about": a[9] if len(a) > 9 else ""}
            f = fly.get(a[0])
            if f:
                if f.get("img"):
                    ev["img"] = f["img"]
                if f.get("ig"):
                    ev["ig"] = f["ig"]
            moved.append(ev)
            # keep the line's own trailing comma exactly, so no other id moves
            new_lines.append(ln[:len(ln) - len(ln.lstrip())] + ("0," if st.endswith(",") else "0"))
        else:
            kept_names.add(a[0])
            new_lines.append(ln)
        idx += 1

    # flyers of moved events leave the page (unless an upcoming event has the same name)
    drop_fly = [ev["name"] for ev in moved if ev["name"] in fly and ev["name"] not in kept_names]
    for n in drop_fly:
        fly.pop(n, None)

    # archive: add moved, then drop anything that ended over 12 months ago (permanent)
    events = archive.get("events", []) + [ev for ev in moved if ev["id"] not in have]
    cutoff = (TODAY - dt.timedelta(days=KEEP_DAYS)).isoformat()
    old = [ev for ev in events if (ev.get("e") or ev.get("s") or "") < cutoff]
    events = [ev for ev in events if ev not in old]
    events.sort(key=lambda ev: (ev.get("e") or ""), reverse=True)

    say(f"Built-in events: {len(moved)} ended event(s) moved out of the page; "
        f"{len(drop_fly)} flyer entr{'y' if len(drop_fly) == 1 else 'ies'} removed from the page; "
        f"{len(old)} archived event(s) older than 12 months deleted; archive now holds {len(events)}.")
    if DRY or not (moved or old or drop_fly):
        return

    new_page = page[:start] + "\n".join(new_lines) + page[end:]
    if fly_m:
        new_page = new_page.replace(fly_m.group(0), "const FLY=" + json.dumps(fly, ensure_ascii=False) + ";", 1)
    PAGE.write_text(new_page)
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE.write_text(json.dumps({"updated": TODAY.isoformat(), "note": "Built-in events that have ended. "
                                   "Read by the site only for old links. Kept for 12 months.",
                                   "events": events}, ensure_ascii=False, indent=0) + "\n")


if __name__ == "__main__":
    main()
