/*
 * NaijaOuting app helper (service worker).
 * - Pages and data: always try the internet first, so people see the latest events;
 *   fall back to the last saved copy when offline.
 * - Pictures, fonts and libraries: saved after the first visit, so the app opens fast
 *   (font files have a version in their name, so a saved copy is never stale).
 * - The database (Supabase) and other websites are never cached here.
 * Change VERSION to make every phone refresh its saved copy.
 */
const VERSION = "v74";
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
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => ![SHELL, MEDIA].includes(k)).map(k => caches.delete(k))))
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
  if (url.pathname.startsWith("/admin")) return;
  if (/^\/(_blob|events\/flyers|img|covers|icons|events\/lib|fonts)\//.test(url.pathname)) { e.respondWith(cacheFirst(req)); return; }
  e.respondWith(networkFirst(req));
});
