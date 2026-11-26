/*
 * NaijaOuting app helper (service worker).
 * - Pages and data: always try the internet first, so people see the latest events;
 *   fall back to the last saved copy when offline.
 * - Pictures, fonts and libraries: saved after the first visit, so the app opens fast
 *   (font files have a version in their name, so a saved copy is never stale).
 * - The database (Supabase) and other websites are never cached here.
 * Change VERSION to make every phone refresh its saved copy.
 */
const VERSION = "v96";
// Pictures keep the same saved copy across updates (their file names change when the picture changes),
// so a new version of the site doesn't make every phone download all the pictures again.
const SHELL = `shell-${VERSION}`, MEDIA = "media-keep-1";
const COVERS = ["agriculture","arts-culture","books-literature","business","careers-education","charity-volunteering","civic","comedy",
  "expos-trade-fairs","faith","fashion","festivals-carnivals","film-theatre","food-drink","gaming-esports","health-fitness","kids-family",
  "markets-pop-ups","music","nightlife-parties","sports","tech","workshops-classes"].map(n => `/covers/${n}.webp?v=3`);
const START = ["/", "/events/", "/js/supabase.js", "/js/config.js", "/js/shim.js", "/js/account.js", "/js/pwa.js",
  "/data/landing.json", "/manifest.webmanifest", "/icons/icon-192.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(START)).catch(() => {}).then(() => self.skipWaiting()));
  // save the category pictures in the background so cards never show blank on a weak connection
  caches.open(MEDIA).then(c => Promise.all(COVERS.map(u => c.match(u).then(hit => hit || c.add(u).catch(() => {}))))).catch(() => {});
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => ![SHELL, MEDIA, "no-data"].includes(k)).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

function networkFirst(req) {
  return fetch(req).then(res => {
    if (res && res.ok && res.type === "basic") { const copy = res.clone(); caches.open(SHELL).then(c => c.put(req, copy)); }
    return res;
  }).catch(() => caches.match(req, { ignoreSearch: true }).then(r => r ||
    (req.mode === "navigate" ? caches.match("/events/") : Response.error())));
}
function cacheFirst(req) {
  return caches.match(req).then(hit => hit || fetch(req).then(res => {
    if (res && res.ok) { const copy = res.clone(); caches.open(MEDIA).then(c => c.put(req, copy)); }
    return res;
  }).catch(() => caches.match(req, { ignoreSearch: true }).then(r => r || Response.error())));
}

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) {
    // Google Fonts can be kept; everything else from other sites (database, maps, tickets) goes straight through
    if (/fonts\.(googleapis|gstatic)\.com$/.test(url.hostname)) e.respondWith(cacheFirst(req));
    // the street-map library: pinned version, so the saved copy never goes stale
    else if (url.hostname === "cdn.jsdelivr.net" && /^\/npm\/maplibre-gl@\d/.test(url.pathname)) e.respondWith(cacheFirst(req));
    return;
  }
  if (url.pathname.startsWith("/admin") || url.pathname.startsWith("/api/") || url.pathname.startsWith("/cal/")) return;
  if (/^\/(_blob|events\/flyers|img|covers|icons|events\/lib|fonts)\//.test(url.pathname)) { e.respondWith(cacheFirst(req)); return; }
  e.respondWith(networkFirst(req));
});

/* Reminders for saved events in the installed app (Android, no account needed).
   The page keeps a short list of saved events in the "no-data" cache; about twice a day the phone
   lets this helper check it against the latest checked events (/data/feed.json) and send one
   notification the day before, one on the morning of the event, and one if an event changes. */
const STL = { cancelled: "Cancelled", postponed: "Postponed", venue: "Venue changed", soldout: "Sold out" };
self.addEventListener("periodicsync", e => { if (e.tag === "no-saved") e.waitUntil(savedCheck()); });
async function savedCheck() {
  const c = await caches.open("no-data");
  const r = await c.match("/__saved.json");
  if (!r) return;
  const saved = await r.json();
  if (!saved.length) return;
  const nr = await c.match("/__notified.json");
  const done = nr ? await nr.json() : {};
  let feed = [];
  try { const f = await fetch("/data/feed.json", { cache: "no-store" }); if (f.ok) feed = (await f.json()).ev || []; } catch (x) {}
  const lag = new Date(Date.now() + 36e5), today = lag.toISOString().slice(0, 10), tm = new Date(lag.getTime() + 864e5).toISOString().slice(0, 10);
  const note = (title, body, k, tag) => self.registration.showNotification(title, { body, tag, data: { k }, icon: "/icons/icon-192.png", badge: "/icons/icon-192.png" });
  for (const s of saved) {
    const f = feed.find(x => x.k === s.k) || feed.find(x => x.n === s.n) || {};
    const st = f.st || "", start = f.s || s.s, where = [f.ve || s.ve, f.ci || s.ci].filter(Boolean).join(", "), when = s.t ? s.t + " · " : "";
    if (st && st !== s.st && !done["st|" + s.k + "|" + st]) {
      done["st|" + s.k + "|" + st] = 1;
      await note("Update: " + s.n, STL[st] + (f.sn ? ". " + f.sn : ""), f.k || s.k, "st-" + s.k);
      continue;
    }
    if (st === "cancelled" || st === "postponed") continue;
    if (start === tm && !done["tm|" + s.k + "|" + start]) { done["tm|" + s.k + "|" + start] = 1; await note("Tomorrow: " + s.n, when + where, f.k || s.k, "r-" + s.k); }
    else if (start === today && lag.getUTCHours() < 14 && !done["td|" + s.k + "|" + start]) { done["td|" + s.k + "|" + start] = 1; await note("Today: " + s.n, when + where, f.k || s.k, "r-" + s.k); }
  }
  Object.keys(done).forEach(k => { const d = k.split("|")[2]; if (/^\d{4}-/.test(d || "") && d < today) delete done[k]; });
  await c.put("/__notified.json", new Response(JSON.stringify(done), { headers: { "content-type": "application/json" } }));
}
self.addEventListener("notificationclick", e => {
  e.notification.close();
  const k = (e.notification.data || {}).k, url = "/events/" + (k ? "#e=" + encodeURIComponent(k) : "#v=saved");
  e.waitUntil(clients.matchAll({ type: "window", includeUncontrolled: true }).then(L => {
    for (const w of L) if (new URL(w.url).pathname.startsWith("/events")) { w.navigate(url); return w.focus(); }
    return clients.openWindow(url);
  }));
});
