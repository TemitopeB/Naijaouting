"""
Builds the public files that let NaijaOuting travel outside the app:

  e/<event>/index.html   a light page for every event, with the tags WhatsApp, Facebook, X
                         and Google read, so a shared link shows the flyer, name, date and city
  e/img/<event>.jpg      the 1200x630 preview picture for that page
  data/feed.json         the checked upcoming events, read by the calendar feeds (api/cal.js)
                         and by the installed app's reminders
  weekend/               this weekend's picks per city, with a ready-to-paste WhatsApp message
  sitemap.xml            so search engines can find the event pages

It loads the main site (events/index.html) in a headless browser, feeds it the approved
events, fixes and status changes from Supabase, and asks the site's own code for the final
list, so these pages always match what the site shows. Nothing here invents a price, venue
or date: unknown details are left out.

Runs on GitHub Actions (.github/workflows/publish.yml) a few times a day.
Run it yourself:  SUPABASE_URL=... SUPABASE_ANON_KEY=... python scripts/publish.py
Without Supabase (only the events written into the site):  python scripts/publish.py --offline
"""
import argparse
import datetime as dt
import hashlib
import html
import io
import json
import os
import pathlib
import re
import shutil
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = os.environ.get("SITE_URL", "https://naijaouting-ng.vercel.app").rstrip("/")
LAGOS = dt.timezone(dt.timedelta(hours=1))
KEEP_ENDED_DAYS = 45          # pages for events that ended stay this long, so old shares still preview
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
STATUS = {"cancelled": "Cancelled", "postponed": "Postponed", "venue": "Venue changed", "soldout": "Sold out"}

esc = lambda s: html.escape(str(s or ""), quote=True)


# ---------------------------------------------------------------- data

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


def load_events(offline):
    remote, ovr, sts = [], {}, {}
    if not offline:
        url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY")
        if not url or not key:
            sys.exit("Set SUPABASE_URL and SUPABASE_ANON_KEY, or pass --offline.")
        for r in fetch_col(url, key, "events"):
            remote.append(dict(r["data"], id="r" + r["id"], src=0, pend=0, rev=1))
        for r in fetch_col(url, key, "overrides"):
            d = r["data"] or {}
            if r["id"] in ("notdup", "block", "scam") or r["id"][:3] in ("ph-", "pd-") or not d.get("name"):
                continue
            if d.get("status"):
                sts[d["name"]] = d["status"]
            else:
                ovr[d["name"]] = dict(d, oid=r["id"])

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.route("**/js/*.js", lambda route: route.fulfill(status=200, content_type="text/javascript", body=""))
        pg.add_init_script(path=str(ROOT / "scripts" / "headless_mock.js"))
        pg.goto((ROOT / "events" / "index.html").as_uri())
        pg.wait_for_timeout(1500)
        cutoff = (dt.datetime.now(LAGOS).date() - dt.timedelta(days=KEEP_ENDED_DAYS)).isoformat()
        ev = pg.evaluate(
            """([R,O,S,cut])=>{REMOTE=R.filter(v=>!v.hide).map(cleanEv);OVR=O;STS=S;applyOvr();_AC=null;
            return dedupeEv(allRaw()).filter(v=>!v.hide&&!v.pend&&(v.e&&v.e!=='?'?v.e:v.s)>=cut).map(v=>{
              const a=access(v),en=entLabel(v),x=stOf(v),L=(a.l||[]).filter(l=>/^https:\\/\\//.test(l[1]||''));
              return {k:evSlug(v),n:v.name,c:v.cat,ci:v.city,stt:v.state||'',s:v.s,e:(v.e&&v.e!=='?'?v.e:v.s),
                ve:v.venue||'',t:v.time||'',f:en[0]||'',fr:en[1]?1:0,at:a.t,p:a.p||'',lk:L.length?L[0][1]:'',
                im:safeImg(v.img)||'',ab:String(v.about||'').slice(0,600),onl:v.online?1:0,pl:v.plat||'',
                st:x&&x.st!=='ok'?x.st:'',sn:x&&x.st!=='ok'?(x.note||''):'',vx:vxOf(v).slice(0,5).map(o=>[o.venue||'',o.city||'']),
                cl:cc(v.cat),cv:coverImg(v.cat)||''}})}""",
            [remote, ovr, sts, cutoff],
        )
        b.close()
    seen, out = set(), []
    for e in ev:
        if e["k"] in seen:
            continue
        seen.add(e["k"])
        out.append(e)
    out.sort(key=lambda e: (e["s"], e["n"]))
    return out


# ---------------------------------------------------------------- text helpers

def d(s):
    return dt.date.fromisoformat(s)


def nice_date(s, e):
    a, b = d(s), d(e or s)
    if a == b:
        return f"{DOW[a.weekday()]} {a.day} {MON[a.month - 1]} {a.year}"
    if a.year == b.year and a.month == b.month:
        return f"{a.day}–{b.day} {MON[a.month - 1]} {a.year}"
    if a.year == b.year:
        return f"{a.day} {MON[a.month - 1]} – {b.day} {MON[b.month - 1]} {a.year}"
    return f"{a.day} {MON[a.month - 1]} {a.year} – {b.day} {MON[b.month - 1]} {b.year}"


def short_date(s):
    a = d(s)
    return f"{DOW[a.weekday()]} {a.day} {MON[a.month - 1]}"


def place(e):
    if e["onl"]:
        return "Online" + (f" · {e['pl']}" if e["pl"] else "")
    v = e["ve"].strip()
    return f"{v}, {e['ci']}" if v and e["ci"].lower() not in v.lower() else (v or e["ci"])


def host(u):
    try:
        return urllib.parse.urlparse(u).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def ticket_label(e):
    h = host(e["lk"])
    if e["at"] in ("paid", "mixed", "soon"):
        return f"Get tickets on {h}" if h else "Get tickets"
    if e["at"] == "reg":
        return f"Register on {h}" if h else "Register"
    return f"Official page · {h}" if h else "Official page"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower().replace("&", " and ")).strip("-")


TIME_RE = re.compile(r"\b(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)\b", re.I)
H24_RE = re.compile(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b")


def parse_times(t):
    """'6pm', '10:00 AM – 4:00 PM', '18:00' -> ('18:00', '22:00' or '')"""
    t = str(t or "")
    hits = []
    for m in TIME_RE.finditer(t):
        h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3).lower()
        if not 1 <= h <= 12:
            continue
        h = h % 12 + (12 if ap == "pm" else 0)
        hits.append(f"{h:02d}:{mi:02d}")
    if not hits:
        for m in H24_RE.finditer(t):
            hits.append(f"{int(m.group(1)):02d}:{m.group(2)}")
    if not hits:
        return "", ""
    return hits[0], (hits[1] if len(hits) > 1 and hits[1] > hits[0] else "")


# ---------------------------------------------------------------- preview pictures

FONT_DIR = ROOT / "fonts"
_fonts = {}


def font_file(name):
    """The site's woff2 fonts, unpacked once to .ttf for the picture maker."""
    cache = pathlib.Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "no-fonts"
    cache.mkdir(parents=True, exist_ok=True)
    out = cache / (name + ".ttf")
    if not out.exists():
        from fontTools.ttLib import TTFont
        f = TTFont(str(FONT_DIR / (name + ".woff2")))
        f.flavor = None
        f.save(str(out))
    return str(out)


def font(name, size, wght):
    k = (name, size, wght)
    if k not in _fonts:
        from PIL import ImageFont
        f = ImageFont.truetype(font_file(name), size)
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
        _fonts[k] = f
    return _fonts[k]


def has_glyphs(name):
    from fontTools.ttLib import TTFont
    key = ("cmap", name)
    if key not in _fonts:
        _fonts[key] = set(TTFont(font_file(name)).getBestCmap().keys())
    return _fonts[key]


def runs(text, family):
    """Split text into runs drawn by the main font or, for characters it lacks, the -ext file / Plex."""
    order = [family, family.replace("-latin-", "-latin-ext-"), "ibm-plex-sans-latin-ext-v1"]
    out = []
    for ch in text:
        name = next((n for n in order if ord(ch) in has_glyphs(n)), family)
        if out and out[-1][0] == name:
            out[-1][1] += ch
        else:
            out.append([name, ch])
    return out


def text_w(text, family, size, wght):
    return sum(font(n, size, wght).getlength(s) for n, s in runs(text, family))


def draw_text(dr, xy, text, family, size, wght, fill):
    x, y = xy
    for n, s in runs(text, family):
        f = font(n, size, wght)
        dr.text((x, y), s, font=f, fill=fill)
        x += f.getlength(s)


def wrap(text, family, size, wght, width, max_lines):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if text_w(t, family, size, wght) <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and text_w(last + "…", family, size, wght) > width:
            last = last[:-1].rstrip()
        lines[-1] = last + "…"
    return lines


def load_picture(src):
    from PIL import Image
    if not src:
        return None
    m = re.match(r"^/_blob/(s-[0-9a-z]+)$", src)
    if m:  # flyers kept in Supabase storage (the site serves them through a rewrite)
        src = "https://fcdebtyopthaikonnfsd.supabase.co/storage/v1/object/public/flyers/" + m.group(1)
    try:
        if src.startswith("https://"):
            req = urllib.request.Request(src, headers={"User-Agent": "NaijaOuting preview builder"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = r.read(8_000_000)
            im = Image.open(io.BytesIO(data))
        else:
            p = ROOT / ("events/" + src if src.startswith("flyers/") else src.lstrip("/").split("?")[0])
            if not p.exists():
                return None
            im = Image.open(p)
        im.load()
        return im.convert("RGB")
    except Exception as x:
        print("  picture skipped:", src[:80], type(x).__name__)
        return None


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rounded(im, r):
    from PIL import Image, ImageDraw
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, im.size[0] - 1, im.size[1] - 1), r, fill=255)
    return m


def date_chip(e):
    a, b = d(e["s"]), d(e["e"])
    return (DOW[a.weekday()].upper(), str(a.day), MON[a.month - 1].upper()) if a == b else \
        ("FROM", str(a.day), MON[a.month - 1].upper())


def make_preview(e, out_path):
    from PIL import Image, ImageDraw, ImageFilter
    W, H = 1200, 630
    flyer = load_picture(e["im"])
    c1, c2 = hex_rgb(e["cl"][0]), hex_rgb(e["cl"][1])
    if flyer:
        bg = flyer.copy()
        s = max(W / bg.width, H / bg.height)
        bg = bg.resize((int(bg.width * s) + 1, int(bg.height * s) + 1))
        bg = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H))
        bg = bg.filter(ImageFilter.GaussianBlur(30))
        canvas = Image.blend(bg, Image.new("RGB", (W, H), (12, 14, 13)), 0.42)
        s = min(1080 / flyer.width, 566 / flyer.height)
        fw, fh = int(flyer.width * s), int(flyer.height * s)
        fl = flyer.resize((fw, fh), Image.LANCZOS)
        x, y = (W - fw) // 2, (H - fh) // 2
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((x, y + 10, x + fw, y + fh + 10), 22, fill=(0, 0, 0, 120))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), sh.filter(ImageFilter.GaussianBlur(14))).convert("RGB")
        canvas.paste(fl, (x, y), rounded(fl, 20))
        chip_x, chip_y = x + 18, y + fh - 18
    else:
        canvas = Image.new("RGB", (W, H))
        dr = ImageDraw.Draw(canvas)
        for i in range(W):  # dark-to-colour band, same pair the site uses for this category
            t = i / (W - 1)
            dr.line([(i, 0), (i, H)], fill=tuple(int(c2[k] + (c1[k] - c2[k]) * t * 0.55) for k in range(3)))
        cover = load_picture(e["cv"].split("?")[0])
        if cover:
            cv = cover.resize((530, 530), Image.LANCZOS)
            canvas.paste(cv, (50, 50), rounded(cv, 26))
        dr = ImageDraw.Draw(canvas)
        X, Wt = 625, 520
        cat = (e["c"] or "").upper()
        draw_text(dr, (X, 92), cat, "plus-jakarta-sans-latin-v1", 22, 700, (255, 255, 255, 200))
        size = 58
        while True:
            lines = wrap(e["n"], "space-grotesk-latin-v1", size, 700, Wt, 4)
            if len(lines) <= 3 or size <= 42:
                break
            size -= 4
        y = 136
        for ln in lines:
            draw_text(dr, (X, y), ln, "space-grotesk-latin-v1", size, 700, (255, 255, 255))
            y += int(size * 1.14)
        y += 18
        for ln in wrap(nice_date(e["s"], e["e"]) + ((" · " + e["t"]) if e["t"] and len(e["t"]) <= 22 else ""),
                       "ibm-plex-sans-latin-v1", 28, 600, Wt, 2):
            draw_text(dr, (X, y), ln, "ibm-plex-sans-latin-v1", 28, 600, (255, 214, 120))
            y += 38
        for ln in wrap(place(e), "plus-jakarta-sans-latin-v1", 26, 500, Wt, 2):
            draw_text(dr, (X, y), ln, "plus-jakarta-sans-latin-v1", 26, 500, (235, 238, 236))
            y += 36
        chip_x, chip_y = 50 + 20, 50 + 530 - 20
    dr = ImageDraw.Draw(canvas)
    # date chip, like the cards on the site
    a, b, c = date_chip(e)
    f1, f2 = font("ibm-plex-sans-latin-v1", 19, 600), font("ibm-plex-sans-latin-v1", 30, 700)
    w = f1.getlength(a) + f2.getlength(b) + f1.getlength(c) + 16 * 2 + 9 * 2
    dr.rounded_rectangle((chip_x, chip_y - 46, chip_x + w, chip_y), 23, fill=(255, 255, 255))
    xx = chip_x + 16
    dr.text((xx, chip_y - 34), a, font=f1, fill=(90, 96, 92)); xx += f1.getlength(a) + 9
    dr.text((xx, chip_y - 42), b, font=f2, fill=(20, 22, 20)); xx += f2.getlength(b) + 9
    dr.text((xx, chip_y - 34), c, font=f1, fill=(90, 96, 92))
    if e["st"] in ("cancelled", "postponed", "soldout"):
        lab = STATUS[e["st"]].upper()
        f3 = font("plus-jakarta-sans-latin-v1", 24, 800)
        lw = f3.getlength(lab) + 36
        col = (196, 55, 45) if e["st"] == "cancelled" else (176, 98, 0)
        dr.rounded_rectangle((30, 30, 30 + lw, 78), 24, fill=col)
        dr.text((48, 40), lab, font=f3, fill=(255, 255, 255))
    buf = io.BytesIO()
    canvas.save(buf, "JPEG", quality=82, optimize=True, progressive=True)
    data = buf.getvalue()
    if not out_path.exists() or out_path.read_bytes() != data:
        out_path.write_bytes(data)
    return hashlib.md5(data).hexdigest()[:8], flyer is not None


# ---------------------------------------------------------------- event page

PAGE_CSS = """:root{--bg:#F6F5F1;--pn:#fff;--tx:#141614;--mu:#5A605C;--ln:#E4E2DC;--ac:#0B6B4C;--acx:#fff;--warn:#9A5B00;--bad:#B3261E}
@media (prefers-color-scheme:dark){:root{--bg:#0F1311;--pn:#171C19;--tx:#EEF1EE;--mu:#A6AFA9;--ln:#2A322D;--ac:#3DB27D;--acx:#06140D;--warn:#F2B04A;--bad:#FF8A80}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--tx);font:16px/1.5 'Plus Jakarta Sans','Noto Sans',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}
a{color:inherit}.w{max-width:560px;margin:0 auto;padding:16px 16px 40px}
.top{display:inline-flex;align-items:center;gap:6px;font-weight:600;font-size:14px;color:var(--mu);text-decoration:none;padding:8px 0 14px}
.fl{margin:0;border-radius:22px;overflow:hidden;background:var(--pn);box-shadow:0 1px 3px rgba(0,0,0,.08)}
.fl img{display:block;width:100%;height:auto;max-height:70vh;object-fit:contain;background:#0d0f0e}
.stb{margin:16px 0 0;padding:12px 14px;border-radius:14px;font-weight:600;background:color-mix(in srgb,var(--warn) 14%,var(--pn));color:var(--warn)}
.stb.bad{background:color-mix(in srgb,var(--bad) 12%,var(--pn));color:var(--bad)}.stb span{display:block;font-weight:500;color:var(--tx);margin-top:2px}
.cat{margin:20px 0 4px;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--mu)}
h1{margin:0 0 14px;font:700 clamp(26px,7vw,34px)/1.15 'Space Grotesk','Plus Jakarta Sans',system-ui,sans-serif;letter-spacing:-.02em}
.facts{list-style:none;margin:0;padding:6px 0;border-radius:18px;background:var(--pn);box-shadow:0 1px 3px rgba(0,0,0,.06)}
.facts li{display:flex;gap:12px;align-items:flex-start;padding:10px 16px}.facts li+li{border-top:1px solid var(--ln)}
.facts svg{flex:none;margin-top:3px;color:var(--ac)}.facts b{display:block;font-weight:650}.facts span{color:var(--mu);font-size:14px}
.num{font-family:'IBM Plex Sans','Plus Jakarta Sans',system-ui,sans-serif;font-variant-numeric:tabular-nums}
.act{display:grid;gap:10px;margin:18px 0}
.b{display:flex;align-items:center;justify-content:center;gap:8px;min-height:52px;padding:12px 18px;border-radius:16px;font-weight:700;text-decoration:none;text-align:center;border:1.5px solid var(--ln);background:var(--pn)}
.b.p{background:var(--ac);border-color:var(--ac);color:var(--acx)}
.ab{margin:6px 0 0;color:var(--tx);white-space:pre-line}
.note{margin:22px 0 0;padding:14px 16px;border-radius:14px;background:var(--pn);color:var(--mu);font-size:14px}
.more{display:inline-block;margin-top:18px;font-weight:700;color:var(--ac);text-decoration:none}
"""
ICO = {
    "cal": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/></svg>',
    "pin": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 21s7-6 7-11a7 7 0 1 0-14 0c0 5 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>',
    "tk": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M3 8a2 2 0 0 0 0 4v4h18v-4a2 2 0 0 1 0-4V4H3z" transform="translate(0 2)"/><path d="M14 6v12" stroke-dasharray="2 2"/></svg>',
    "back": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M15 5l-7 7 7 7"/></svg>',
}


def json_ld(e, img):
    status = {"cancelled": "EventCancelled", "postponed": "EventPostponed"}.get(e["st"], "EventScheduled")
    o = {"@context": "https://schema.org", "@type": "Event", "name": e["n"], "startDate": e["s"], "endDate": e["e"],
         "eventStatus": "https://schema.org/" + status, "image": [img], "url": f"{SITE}/e/{e['k']}/",
         "eventAttendanceMode": "https://schema.org/" + ("OnlineEventAttendanceMode" if e["onl"] else "OfflineEventAttendanceMode")}
    if e["ab"]:
        o["description"] = e["ab"][:300]
    if e["onl"]:
        o["location"] = {"@type": "VirtualLocation", "url": e["lk"] or f"{SITE}/e/{e['k']}/"}
    else:
        o["location"] = {"@type": "Place", "name": e["ve"] or e["ci"],
                         "address": {"@type": "PostalAddress", "addressLocality": e["ci"],
                                     "addressRegion": e["stt"] or e["ci"], "addressCountry": "NG"}}
    return json.dumps(o, ensure_ascii=False).replace("</", "<\\/")


def event_page(e, ver):
    img = f"{SITE}/e/img/{e['k']}.jpg?v={ver}"
    url = f"{SITE}/e/{e['k']}/"
    when = nice_date(e["s"], e["e"])
    desc = " · ".join(x for x in [when + (f", {e['t']}" if e["t"] else ""), place(e), e["f"]] if x)
    if e["st"]:
        desc = STATUS.get(e["st"], "") + ". " + desc
    flyer = e["im"] if e["im"].startswith("https://") else ("/events/" + e["im"] if e["im"].startswith("flyers/") else e["im"])
    pic = flyer or e["cv"] or f"/e/img/{e['k']}.jpg?v={ver}"
    app = f"/events/#e={urllib.parse.quote(e['k'])}"
    st = ""
    if e["st"]:
        st = (f'<p class="stb{" bad" if e["st"] == "cancelled" else ""}" role="status">{esc(STATUS.get(e["st"], ""))}'
              + (f'<span>{esc(e["sn"])}</span>' if e["sn"] else "") + "</p>")
    vx = f" + {len(e['vx'])} more venue{'s' if len(e['vx']) > 1 else ''}" if e["vx"] else ""
    facts = (f'<li>{ICO["cal"]}<div><b class="num">{esc(when)}</b>' + (f'<span class="num">{esc(e["t"])}</span>' if e["t"] else "") + "</div></li>"
             f'<li>{ICO["pin"]}<div><b>{esc(e["ve"] or ("Online" if e["onl"] else "Venue to be confirmed"))}</b><span>{esc(e["pl"] if e["onl"] else e["ci"])}{esc(vx)}</span></div></li>')
    if e["f"]:
        facts += f'<li>{ICO["tk"]}<div><b class="num">{esc(e["f"])}</b>' + (f'<span class="num">{esc(e["p"])}</span>' if e["p"] and e["p"] != e["f"] and len(e["p"]) < 120 else "") + "</div></li>"
    btns = ""
    if e["lk"] and e["st"] != "cancelled":
        btns += f'<a class="b p" href="{esc(e["lk"])}" target="_blank" rel="noopener">{esc(ticket_label(e))}</a>'
    btns += f'<a class="b{"" if btns else " p"}" href="{esc(app)}">Directions, save and more details</a>'
    city_link = f"/events/#v=events&city={urllib.parse.quote(e['ci'])}" if not e["onl"] else "/events/#v=online"
    more = f"More events in {e['ci']}" if not e["onl"] else "More online events"
    title = f"{e['n']} · {short_date(e['s'])} · {e['ci']}"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} | NaijaOuting</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">
<meta name="theme-color" content="#0B6B4C">
<meta property="og:type" content="website"><meta property="og:site_name" content="NaijaOuting">
<meta property="og:title" content="{esc(e['n'])}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="{esc(img)}"><meta property="og:image:secure_url" content="{esc(img)}">
<meta property="og:image:type" content="image/jpeg"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{esc(e['n'])}, {esc(when)}, {esc(e['ci'])}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(e['n'])}"><meta name="twitter:description" content="{esc(desc)}"><meta name="twitter:image" content="{esc(img)}">
<script type="application/ld+json">{json_ld(e, img)}</script>
<script>try{{if(localStorage.getItem("ne_lv")||localStorage.getItem("ne_fav"))location.replace({json.dumps(app)})}}catch(x){{}}</script>
<link rel="stylesheet" href="/fonts/type-v2.css">
<style>{PAGE_CSS}</style>
</head><body><main class="w">
<a class="top" href="/events/">{ICO['back']}All events on NaijaOuting</a>
<figure class="fl"><img src="{esc(pic)}" alt="{'Flyer: ' if flyer else ''}{esc(e['n'])}" width="1200" height="{'1500' if flyer else '1200'}" decoding="async"{'' if flyer else ' style="max-height:none"'}></figure>
{st}<p class="cat">{esc(e['c'])}{' · Online' if e['onl'] else ''}</p>
<h1>{esc(e['n'])}</h1>
<ul class="facts">{facts}</ul>
<div class="act">{btns}</div>
{f'<p class="ab">{esc(e["ab"])}</p>' if e["ab"] else ''}
<p class="note">Checked by NaijaOuting before it went live. Tickets are sold by the organiser or their official seller, never by us. Dates and venues can change, so check with the organiser before you travel.</p>
<a class="more" href="{esc(city_link)}">{esc(more)} →</a>
</main></body></html>
"""


FALLBACK = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>NaijaOuting · Events across Nigeria</title>
<meta name="description" content="Checked events across Nigeria, with the official ticket link.">
<meta property="og:type" content="website"><meta property="og:site_name" content="NaijaOuting">
<meta property="og:title" content="NaijaOuting · Events across Nigeria">
<meta property="og:description" content="Checked events across Nigeria, with the official ticket link.">
<meta property="og:image" content="SITE/img/og-default.jpg"><meta name="twitter:card" content="summary_large_image">
<meta name="robots" content="noindex">
<script>(function(){var k=(location.pathname.match(/^\\/e\\/([^\\/]+)/)||[])[1]||"";location.replace("/events/"+(k?"#e="+k:""))})()</script>
</head><body style="font-family:system-ui,sans-serif;padding:24px">Opening NaijaOuting… <a href="/events/">Continue</a></body></html>
""".replace("SITE", SITE)


# ---------------------------------------------------------------- weekend picks

GROUPS = [
    ("Nights out", "🎶", {"Music", "Nightlife & Parties", "Comedy", "Film & Theatre"}),
    ("Family and daytime", "👨‍👩‍👧", {"Kids & Family", "Festivals & Carnivals", "Markets & Pop-ups", "Food & Drink",
                                    "Arts & Culture", "Books & Literature", "Sports", "Health & Fitness", "Fashion", "Faith",
                                    "Charity & Volunteering", "Agriculture", "Gaming & Esports"}),
    ("Learn and network", "💼", {"Tech", "Business", "Careers & Education", "Workshops & Classes", "Expos & Trade Fairs", "Civic"}),
]


def weekend_range(today):
    # Mon–Thu: the coming Fri–Sun. Fri–Sun: this weekend (from today).
    wd = today.weekday()
    fri = today + dt.timedelta(days=(4 - wd)) if wd <= 4 else today - dt.timedelta(days=wd - 4)
    return fri, fri + dt.timedelta(days=2)


def pick_score(e):
    return (0 if e["im"] else 1, 0 if e["t"] else 1, (d(e["e"]) - d(e["s"])).days, e["s"], e["n"])


def weekend(events, today):
    fri, sun = weekend_range(today)
    start = max(fri, today)
    on = [e for e in events if not e["onl"] and e["st"] not in ("cancelled", "postponed")
          and d(e["s"]) <= sun and d(e["e"]) >= start]
    cities = {}
    for e in on:
        cities.setdefault(e["ci"], []).append(e)
    lab = f"{fri.day}–{sun.day} {MON[sun.month - 1]}" if fri.month == sun.month else f"{fri.day} {MON[fri.month - 1]} – {sun.day} {MON[sun.month - 1]}"
    out = {"from": fri.isoformat(), "to": sun.isoformat(), "label": lab, "cities": []}
    for ci, L in sorted(cities.items(), key=lambda x: -len(x[1])):
        groups = []
        used = set()
        for name, emo, cats in GROUPS:
            g = sorted([e for e in L if e["c"] in cats and e["k"] not in used], key=pick_score)[:5]
            used.update(e["k"] for e in g)
            if g:
                groups.append({"name": name, "emoji": emo, "ev": [wk_item(e, start) for e in g]})
        rest = sorted([e for e in L if e["k"] not in used], key=pick_score)[:3]
        if rest:
            groups.append({"name": "Also on", "emoji": "✨", "ev": [wk_item(e, start) for e in rest]})
        free = sum(1 for e in L if e["fr"])
        out["cities"].append({"city": ci, "slug": slug(ci), "n": len(L), "free": free, "groups": groups})
    return out


def wk_item(e, start):
    day = short_date(max(e["s"], start.isoformat())) if e["s"] == e["e"] or e["s"] >= start.isoformat() else "Until " + short_date(e["e"])
    if e["s"] != e["e"] and e["s"] >= start.isoformat():
        day = short_date(e["s"]) + " – " + short_date(e["e"])
    return {"k": e["k"], "n": e["n"], "day": day, "t": e["t"] if len(e["t"]) <= 24 else "", "pl": place(e),
            "f": e["f"], "fr": e["fr"], "so": 1 if e["st"] == "soldout" else 0, "im": e["im"], "cv": e["cv"], "c": e["c"]}


def wa_text(w, c):
    lines = [f"🗓 *This weekend in {c['city']}* ({w['label']})", ""]
    for g in c["groups"]:
        lines.append(f"{g['emoji']} *{g['name']}*")
        for x in g["ev"]:
            bits = [x["day"] + (f", {x['t']}" if x["t"] else ""), x["pl"]]
            tail = " · Sold out" if x["so"] else (f" · {x['f']}" if x["f"] in ("Free", "Free · register") else "")
            lines.append(f"• {x['n']}: {' · '.join(b for b in bits if b)}{tail}")
        lines.append("")
    lines.append(f"Every event is checked, with the official ticket link: {SITE}/weekend/{c['slug']}/")
    return "\n".join(lines)


WK_CSS = PAGE_CSS + """
.w{max-width:760px}.lead{color:var(--mu);margin:0 0 18px}
.cities{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 22px}.cities a{padding:9px 14px;border-radius:999px;background:var(--pn);border:1px solid var(--ln);text-decoration:none;font-weight:600;font-size:14px}
.cities a[aria-current]{background:var(--tx);color:var(--bg);border-color:var(--tx)}
.grp{margin:26px 0 10px;font:700 19px/1.2 'Space Grotesk','Plus Jakarta Sans',system-ui,sans-serif}
.it{display:flex;gap:14px;align-items:center;padding:10px;border-radius:18px;background:var(--pn);text-decoration:none;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,.05)}
.it img{flex:none;width:76px;height:76px;border-radius:12px;object-fit:cover;background:#ddd}
.it b{display:block;line-height:1.3}.it span{display:block;color:var(--mu);font-size:14px}.it em{font-style:normal;color:var(--ac);font-weight:700}
.copy{display:flex;gap:10px;flex-wrap:wrap;margin:8px 0 0}.copy button,.copy a{flex:1 1 200px}
button.b{font:inherit;font-weight:700;cursor:pointer;color:inherit}
.fair{font-size:13px;color:var(--mu);margin-top:6px}
"""


def weekend_page(w, c, all_cities):
    title = f"This weekend in {c['city']} ({w['label']})" if c else f"This weekend in Nigeria ({w['label']})"
    url = f"{SITE}/weekend/{c['slug']}/" if c else f"{SITE}/weekend/"
    cur = ' aria-current="page"'
    nav = "".join(f'<a href="/weekend/{x["slug"]}/"{cur if c and x["slug"] == c["slug"] else ""}>{esc(x["city"])} <span class="num">{x["n"]}</span></a>'
                  for x in all_cities[:14])
    body = ""
    show = [c] if c else all_cities[:6]
    for cc in show:
        if not c:
            body += f'<h2 class="grp" style="font-size:24px;margin-top:34px">{esc(cc["city"])}</h2>'
        for g in cc["groups"]:
            body += f'<h3 class="grp">{g["emoji"]} {esc(g["name"])}</h3>'
            for x in g["ev"]:
                im = x["im"]
                src = im if im.startswith("https://") else ("/events/" + im if im.startswith("flyers/") else im) or x["cv"] or f"/e/img/{x['k']}.jpg"
                extra = " · <em>Sold out</em>" if x["so"] else (f" · <em>{esc(x['f'])}</em>" if x["f"] else "")
                body += (f'<a class="it" href="/e/{esc(x["k"])}/"><img src="{esc(src)}" alt="" loading="lazy" decoding="async">'
                         f'<div><b>{esc(x["n"])}</b><span class="num">{esc(x["day"])}{(", " + esc(x["t"])) if x["t"] else ""}</span>'
                         f'<span>{esc(x["pl"])}{extra}</span></div></a>')
    copy = ""
    if c:
        txt = wa_text(w, c)
        copy = (f'<div class="copy"><button class="b p" type="button" id="cp">Copy for WhatsApp</button>'
                f'<a class="b" href="https://wa.me/?text={urllib.parse.quote(txt)}" target="_blank" rel="noopener">Send on WhatsApp</a></div>'
                f'<textarea id="tx" hidden>{esc(txt)}</textarea>'
                '<script>document.getElementById("cp").onclick=function(){var t=document.getElementById("tx").value,b=this;'
                'function ok(){b.textContent="✓ Copied. Paste it in your Channel or group"}'
                'if(navigator.clipboard)navigator.clipboard.writeText(t).then(ok,function(){prompt("Copy this:",t)});else prompt("Copy this:",t)}</script>')
    n = c["n"] if c else sum(x["n"] for x in all_cities)
    desc = f"{n} checked events on {w['label']}" + (f" in {c['city']}" if c else " across Nigeria") + ", with official ticket links."
    og = f"{SITE}/e/img/{(c or all_cities[0])['groups'][0]['ev'][0]['k']}.jpg" if (c or all_cities) else f"{SITE}/img/og-default.jpg"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} | NaijaOuting</title>
<meta name="description" content="{esc(desc)}"><link rel="canonical" href="{esc(url)}">
<meta name="theme-color" content="#0B6B4C">
<meta property="og:type" content="website"><meta property="og:site_name" content="NaijaOuting">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="{esc(og)}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="/fonts/type-v2.css"><style>{WK_CSS}</style>
</head><body><main class="w">
<a class="top" href="/events/">{ICO['back']}All events on NaijaOuting</a>
<h1>{esc(title.split(" (")[0])} <span style="white-space:nowrap">({esc(w['label'])})</span></h1>
<p class="lead">{esc(desc)}</p>
<nav class="cities" aria-label="Cities">{'<a href="/weekend/"' + (' aria-current="page"' if not c else '') + '>All cities</a>'}{nav}</nav>
{copy}
{body or '<p class="lead">No checked events for this weekend yet.</p>'}
<p class="fair">Picked by date and type of event. Nobody pays to be listed here. Prices and times come from the organisers. Check with them before you travel.</p>
<a class="more" href="/events/#v=events&when=wk">See every event this weekend →</a>
</main></body></html>
"""


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="only the events written into the site (no Supabase)")
    ap.add_argument("--no-images", action="store_true", help="skip preview pictures (quick test)")
    args = ap.parse_args()
    today = dt.datetime.now(LAGOS).date()
    events = load_events(args.offline)
    print(f"{len(events)} events (upcoming and ended within {KEEP_ENDED_DAYS} days)")

    # 1. calendar + app feed: upcoming and the last 30 days, so calendars keep recent entries
    keep = (today - dt.timedelta(days=30)).isoformat()
    feed = []
    for e in events:
        if e["e"] < keep:
            continue
        ts, te = parse_times(e["t"])
        feed.append({"k": e["k"], "n": e["n"], "c": e["c"], "ci": e["ci"], "s": e["s"], "e": e["e"], "ve": e["ve"],
                     "t": e["t"], "ts": ts, "te": te, "f": e["f"], "fr": e["fr"], "lk": e["lk"], "onl": e["onl"],
                     "pl": e["pl"], "st": e["st"], "sn": e["sn"]})
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "feed.json").write_text(json.dumps({"built": dt.datetime.now(LAGOS).isoformat(timespec="minutes"),
                                                          "ev": feed}, ensure_ascii=False, separators=(",", ":")))

    # 2. event pages + preview pictures
    E = ROOT / "e"
    (E / "img").mkdir(parents=True, exist_ok=True)
    (E / "_" ).mkdir(exist_ok=True)
    (E / "_" / "index.html").write_text(FALLBACK)
    keep_slugs = set()
    for i, e in enumerate(events):
        keep_slugs.add(e["k"])
        img = E / "img" / f"{e['k']}.jpg"
        if args.no_images and img.exists():
            ver = hashlib.md5(img.read_bytes()).hexdigest()[:8]
        elif args.no_images:
            ver = "0"
        else:
            ver, ok = make_preview(e, img)
            if not ok:
                e["im"] = ""  # the flyer link isn't a picture we can show (e.g. an Instagram post page)
        p = E / e["k"]
        p.mkdir(exist_ok=True)
        page = event_page(e, ver)
        f = p / "index.html"
        if not f.exists() or f.read_text() != page:
            f.write_text(page)
        if (i + 1) % 50 == 0:
            print(f"  {i + 1} pages")
    removed = 0
    for p in E.iterdir():
        if p.name in ("img", "_"):
            continue
        if p.is_dir() and p.name not in keep_slugs:
            shutil.rmtree(p)
            removed += 1
    for f in (E / "img").glob("*.jpg"):
        if f.stem not in keep_slugs:
            f.unlink()
    print(f"event pages: {len(keep_slugs)} kept, {removed} removed (ended long ago or taken down)")

    # 3. weekend picks
    w = weekend([e for e in events if e["e"] >= today.isoformat()], today)
    W = ROOT / "weekend"
    if W.exists():
        shutil.rmtree(W)
    W.mkdir()
    (W / "index.html").write_text(weekend_page(w, None, w["cities"]))
    for c in w["cities"]:
        (W / c["slug"]).mkdir()
        (W / c["slug"] / "index.html").write_text(weekend_page(w, c, w["cities"]))
        c["wa"] = wa_text(w, c)
    (ROOT / "data" / "weekend.json").write_text(json.dumps(w, ensure_ascii=False, separators=(",", ":")))
    print(f"weekend {w['label']}: {len(w['cities'])} cities, {sum(c['n'] for c in w['cities'])} events")

    # 4. sitemap
    urls = [f"{SITE}/", f"{SITE}/events/", f"{SITE}/weekend/"] + [f"{SITE}/weekend/{c['slug']}/" for c in w["cities"]] + \
           [f"{SITE}/e/{e['k']}/" for e in events if e["e"] >= today.isoformat()]
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      + "".join(f"<url><loc>{esc(u)}</loc></url>\n" for u in urls) + "</urlset>\n")


if __name__ == "__main__":
    main()
