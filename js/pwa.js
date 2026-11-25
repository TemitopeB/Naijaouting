/*
 * NaijaOuting: install as an app.
 * Any element with data-install becomes an "Install the app" button:
 *  - Android / Chrome / Edge: shows the browser's own install prompt.
 *  - iPhone / iPad (Safari): shows how to use Share -> Add to Home Screen.
 *  - Already installed: the buttons hide themselves.
 */
(function () {
  "use strict";
  if ("serviceWorker" in navigator) {
    addEventListener("load", function () { navigator.serviceWorker.register("/sw.js").catch(function () {}); });
  }
  var deferred = null;
  var standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  var ios = /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  if (standalone) document.documentElement.classList.add("installed");

  function refresh() {
    document.querySelectorAll("[data-install]").forEach(function (b) {
      b.hidden = standalone || !(deferred || ios);
      if (b.hasAttribute("data-install-always") && !standalone) b.hidden = false;
    });
  }
  addEventListener("beforeinstallprompt", function (e) { e.preventDefault(); deferred = e; refresh(); });
  addEventListener("appinstalled", function () { deferred = null; standalone = true; refresh(); });

  function sheet(html) {
    var d = document.createElement("div");
    d.className = "no-ish";
    d.setAttribute("role", "dialog");
    d.setAttribute("aria-modal", "true");
    d.setAttribute("aria-label", "Install NaijaOuting");
    d.innerHTML = '<div class="no-ish-sc" data-close></div><div class="no-ish-p">' + html +
      '<button type="button" class="no-ish-ok" data-close>Got it</button></div>';
    document.body.appendChild(d);
    var close = function () { d.remove(); removeEventListener("keydown", esc); };
    var esc = function (e) { if (e.key === "Escape") close(); };
    addEventListener("keydown", esc);
    d.addEventListener("click", function (e) { if (e.target.closest("[data-close]")) close(); });
    setTimeout(function () { var b = d.querySelector(".no-ish-ok"); if (b) b.focus(); }, 30);
  }
  var SHARE = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v12M8 7l4-4 4 4"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/></svg>';
  var PLUS = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="4"/><path d="M12 8v8M8 12h8"/></svg>';

  function install() {
    if (standalone) return;
    if (deferred) {
      deferred.prompt();
      deferred.userChoice.finally(function () { deferred = null; refresh(); });
      return;
    }
    if (ios) {
      sheet('<h3>Add NaijaOuting to your Home Screen</h3><ol>' +
        '<li>Tap the <b>Share</b> button ' + SHARE + ' at the bottom of Safari (top on iPad).</li>' +
        '<li>Scroll down and tap <b>Add to Home Screen</b> ' + PLUS + '.</li>' +
        '<li>Tap <b>Add</b>. NaijaOuting appears on your Home Screen like any app.</li></ol>' +
        '<p>Using Chrome on iPhone? Open this page in Safari first.</p>');
      return;
    }
    sheet('<h3>Install NaijaOuting</h3><ol>' +
      '<li>Open your browser’s menu (<b>⋮</b> or <b>⋯</b>).</li>' +
      '<li>Choose <b>Install app</b> or <b>Add to Home screen</b>.</li></ol>' +
      '<p>On a computer, look for the install icon at the right end of the address bar.</p>');
  }
  window.NO_INSTALL = install;
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-install]");
    if (b) { e.preventDefault(); install(); }
  });

  var st = document.createElement("style");
  st.textContent = ".no-ish{position:fixed;inset:0;z-index:9999;display:grid;align-items:end;justify-items:center}" +
    ".no-ish-sc{position:absolute;inset:0;background:rgba(31,26,22,.55)}" +
    ".no-ish-p{position:relative;width:min(440px,100%);margin:12px;background:#fff;color:#1F1A16;border-radius:24px;padding:22px 22px 18px;font:400 15px/1.55 var(--font-interface,'Plus Jakarta Sans',system-ui,sans-serif);box-shadow:0 30px 60px -20px rgba(0,0,0,.45)}" +
    "html.installed [data-install]{display:none!important}" +
    "html.installed [data-install]{display:none!important}" +
    ".no-ish-p h3{margin:0 0 10px;font-size:18px}.no-ish-p ol{margin:0 0 10px;padding-left:20px}.no-ish-p li{margin:6px 0}.no-ish-p svg{vertical-align:-3px;color:#0B6B4C}" +
    ".no-ish-p p{margin:0 0 14px;color:#6B625A;font-size:13.5px}" +
    ".no-ish-ok{width:100%;height:46px;border:0;border-radius:999px;background:#0B6B4C;color:#fff;font:600 15px/1 var(--font-interface,'Plus Jakarta Sans',system-ui,sans-serif);cursor:pointer}" +
    "@media (min-width:700px){.no-ish{align-items:center}}";
  document.head.appendChild(st);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", refresh); else refresh();
})();
