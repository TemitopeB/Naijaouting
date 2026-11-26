/*
 * Calendar feed: /cal/<city>/<kinds>.ics  (vercel.json rewrites it to /api/cal?city=..&cats=..)
 *   /cal/lagos/music,comedy.ics      Lagos, music and comedy
 *   /cal/all/tech,free.ics           anywhere, tech, free entry only
 *   /cal/abuja/all.ics               everything in Abuja
 * People subscribe once in their calendar app; it checks back every few hours and new checked
 * events appear on their own. The events come from /data/feed.json, which scripts/publish.py
 * rebuilds a few times a day from the same list the site shows. Times are Nigeria time (WAT).
 */
const SITE = "https://naijaouting-ng.vercel.app";
const slug = s => String(s || "").toLowerCase().replace(/&/g, " and ").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
const esc = s => String(s || "").replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\r?\n/g, "\\n");
const ymd = s => s.replace(/-/g, "");
const nextDay = s => { const d = new Date(s + "T00:00:00Z"); d.setUTCDate(d.getUTCDate() + 1); return d.toISOString().slice(0, 10); };
const STAMP = s => s.replace(/[-:]/g, "").replace(/\.\d+/, "").slice(0, 15) + "Z";

function fold(line) {  // lines longer than 75 bytes continue on the next line, starting with a space
  const out = []; let cur = "", n = 0;
  for (const ch of line) {
    const b = Buffer.byteLength(ch);
    if (n + b > (out.length ? 74 : 75)) { out.push(cur); cur = ""; n = 0; }
    cur += ch; n += b;
  }
  out.push(cur);
  return out.join("\r\n ");
}

function addHours(day, hm, h) {
  const d = new Date(day + "T" + hm + ":00Z"); d.setUTCHours(d.getUTCHours() + h);
  return d.toISOString().slice(0, 16).replace(/[-:]/g, "") + "00";
}

module.exports = async (req, res) => {
  const q = req.query || {};
  const city = slug(String(q.city || "all").replace(/\.ics$/, "")) || "all";
  const toks = String(q.cats || "all").replace(/\.ics$/, "").split(",").map(slug).filter(Boolean);
  const free = toks.includes("free"), cats = toks.filter(t => t !== "free" && t !== "all");
  let feed;
  try {
    const r = await fetch(`https://${req.headers.host}/data/feed.json`, { headers: { "user-agent": "naijaouting-cal" } });
    if (!r.ok) throw new Error(String(r.status));
    feed = await r.json();
  } catch (e) {
    res.status(503).setHeader("Retry-After", "600");
    res.send("The calendar is updating. Please try again in a few minutes.");
    return;
  }
  const L = (feed.ev || []).filter(e => (city === "all" || slug(e.ci) === city) && (!cats.length || cats.includes(slug(e.c))) && (!free || e.fr));
  const cityName = city === "all" ? "All Nigeria" : ((feed.ev || []).find(e => slug(e.ci) === city) || {}).ci || city.replace(/-/g, " ");
  const catNames = cats.map(c => ((feed.ev || []).find(e => slug(e.c) === c) || {}).c || c.replace(/-/g, " "));
  const name = "NaijaOuting · " + cityName + (catNames.length ? " · " + catNames.join(", ") : "") + (free ? " · Free" : "");
  const stamp = STAMP(new Date(feed.built || Date.now()).toISOString());
  const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//NaijaOuting//Events//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
    "X-WR-CALNAME:" + esc(name), "X-WR-CALDESC:" + esc("Checked events from NaijaOuting, with the official ticket link. Dates can change, so check with the organiser."),
    "X-WR-TIMEZONE:Africa/Lagos", "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H",
    "BEGIN:VTIMEZONE", "TZID:Africa/Lagos", "BEGIN:STANDARD", "DTSTART:19700101T000000", "TZOFFSETFROM:+0100", "TZOFFSETTO:+0100", "TZNAME:WAT", "END:STANDARD", "END:VTIMEZONE"];
  for (const e of L) {
    const page = `${SITE}/e/${e.k}/`;
    lines.push("BEGIN:VEVENT", "UID:" + e.k + "@naijaouting", "DTSTAMP:" + stamp);
    if (e.s === e.e && e.ts) {
      lines.push("DTSTART;TZID=Africa/Lagos:" + ymd(e.s) + "T" + e.ts.replace(":", "") + "00");
      lines.push("DTEND;TZID=Africa/Lagos:" + (e.te ? ymd(e.s) + "T" + e.te.replace(":", "") + "00" : addHours(e.s, e.ts, 3)));
    } else {
      lines.push("DTSTART;VALUE=DATE:" + ymd(e.s), "DTEND;VALUE=DATE:" + ymd(nextDay(e.e)));
    }
    const pre = e.st === "cancelled" ? "Cancelled: " : e.st === "postponed" ? "Postponed: " : e.st === "soldout" ? "Sold out: " : "";
    lines.push("SUMMARY:" + esc(pre + e.n));
    const where = e.onl ? "Online" + (e.pl ? " (" + e.pl + ")" : "") : [e.ve, e.ci].filter(Boolean).join(", ");
    if (where) lines.push("LOCATION:" + esc(where));
    const desc = [e.st && e.sn ? e.sn : "", e.t ? "Time: " + e.t + " (Nigeria time)" : "", e.f ? "Entry: " + e.f : "",
      e.lk ? "Official tickets / registration: " + e.lk : "", "Details: " + page,
      "Checked by NaijaOuting. Dates and venues can change, so check with the organiser before you go."].filter(Boolean).join("\n");
    lines.push("DESCRIPTION:" + esc(desc), "URL:" + page, "CATEGORIES:" + esc(e.c));
    lines.push("STATUS:" + (e.st === "cancelled" ? "CANCELLED" : e.st === "postponed" ? "TENTATIVE" : "CONFIRMED"), "TRANSP:TRANSPARENT", "END:VEVENT");
  }
  lines.push("END:VCALENDAR");
  res.setHeader("Content-Type", "text/calendar; charset=utf-8");
  res.setHeader("Content-Disposition", 'inline; filename="naijaouting-' + city + '.ics"');
  res.setHeader("Cache-Control", "public, max-age=0, s-maxage=3600, stale-while-revalidate=86400");
  res.status(200).send(lines.map(fold).join("\r\n") + "\r\n");
};
