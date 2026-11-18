"""
Event fixes: corrections to live events, checked by hand or by Claude against official sources.

Two jobs, run by .github/workflows/fixes.yml:

  python scripts/fixes.py export
      Saves every approved event and every override to data/_export.json so the
      list can be checked. The workflow saves it to the data-export branch (never deployed).

  python scripts/fixes.py apply data/fixes/2026-11-18.json [...]
      Applies the corrections in the given files. A file looks like:
        {"checked_by": "Claude", "checked_on": "2026-11-18",
         "events":  {"<event doc id>": {"set": {"venue": "..."}, "unset": ["time"], "why": "..."}},
         "builtin": {"<built-in event name>": {"set": {"link": "https://..."}, "why": "..."}}}
      "events" changes approved events (Supabase docs, col "events").
      "builtin" changes events built into events/index.html, through the same
      override the admin "Edit" button writes (col "overrides", id "o" + hash of the name),
      keeping anything already in that override.
      A built-in event the admin has removed stays removed.

Needs SUPABASE_URL and SUPABASE_SERVICE_KEY (GitHub secrets).
"""
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sweep import DB, log, summary  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIELDS = {"name", "cat", "s", "e", "time", "venue", "city", "state", "fee", "about", "link", "img", "online", "plat", "ig", "cx"}


def hsh(s):
    """Same as hsh() in events/index.html (FNV-1a over UTF-16 code units)."""
    h = 2166136261
    units = s.encode("utf-16-le")
    for i in range(0, len(units), 2):
        h ^= units[i] | (units[i + 1] << 8)
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def clean_set(d):
    bad = set(d) - FIELDS
    if bad:
        raise ValueError(f"unknown fields {sorted(bad)}")
    link = d.get("link")
    if link and not str(link).startswith("https://"):
        raise ValueError(f"link must start with https:// ({link})")
    return d


def export(db):
    out = {"events": db.col("events"), "overrides": db.col("overrides")}
    p = ROOT / "data" / "_export.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"Saved {len(out['events'])} events and {len(out['overrides'])} overrides to {p}")


def apply(db, files):
    lines, n = ["## Event fixes", ""], 0
    for f in files:
        fx = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
        for doc_id, ch in (fx.get("events") or {}).items():
            cur = db.get("events", doc_id)
            if cur is None:
                lines.append(f"- skipped `{doc_id}`: not found (removed?)")
                continue
            new = dict(cur)
            new.update(clean_set(ch.get("set") or {}))
            for k in ch.get("unset") or []:
                new.pop(k, None)
            db.put("events", doc_id, new)
            n += 1
            lines.append(f"- {new.get('name')}: {ch.get('why', 'updated')}")
        for name, ch in (fx.get("builtin") or {}).items():
            oid = "o" + str(hsh(name))
            cur = db.get("overrides", oid) or {}
            if cur.get("hide"):
                lines.append(f"- skipped {name}: removed by the admin")
                continue
            patch = dict(cur.get("patch") or {})
            patch.update(clean_set(ch.get("set") or {}))
            for k in ch.get("unset") or []:
                patch.pop(k, None)
            db.put("overrides", oid, {"name": name, "patch": patch})
            n += 1
            lines.append(f"- {name}: {ch.get('why', 'updated')}")
    lines.insert(1, f"{n} events updated.")
    summary("\n".join(lines))
    log("\n".join(lines))


def main():
    url, sk = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY")
    if not (url and sk):
        log("SUPABASE_URL or SUPABASE_SERVICE_KEY is not set.")
        sys.exit(1)
    db = DB(url, sk)
    if len(sys.argv) > 1 and sys.argv[1] == "export":
        export(db)
    elif len(sys.argv) > 2 and sys.argv[1] == "apply":
        apply(db, [f for f in sys.argv[2:] if f.endswith(".json") and os.path.exists(f)])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
