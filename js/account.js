/*
 * NaijaOuting visitor accounts.
 *
 * Visitors browse as guests (an invisible anonymous session). Signing in, with Google or a
 * 6-digit email code, gives them:
 *   - saved events, tourism list and trip on every device (Supabase docs "users/<their id>")
 *   - an email reminder the day before a saved event (sent by .github/workflows/reminders.yml)
 *   - "My submissions": what happened to the events they sent in
 * Anything a guest saved or sent in before signing in moves into the account.
 *
 * Loaded after the main site script on /events/, so it can use the site's own state
 * (FAV, BL, TRIP, S, DB, UID, render, toast...). Database rules: supabase/accounts.sql.
 */
(function () {
  "use strict";
  var sb = window.NO_SB, C = window.NO_CONFIG || {};
  if (!sb || typeof S === "undefined") return;

  var A = window.ACCT = {
    user: null,      // signed-in (not guest) user, or null
    ready: false,    // finished checking who is signed in
    prov: null,      // which sign-in methods are switched on in Supabase
    doc: null,       // this person's account document
    subs: null,      // their submissions with status
    step: "start",   // sign-in sheet: start | code
    email: "",
    busy: false,
    err: "",
    delAsk: false
  };
  var lastV = 0, pushT = null, applying = false;
  // accounts are shown to everyone once NO_CONFIG.accounts is true; before that, only to admins (for testing)
  function live() { return C.accounts === true || (typeof ADMIN !== "undefined" && ADMIN); }

  /* ---------- small helpers ---------- */
  function ls(k, v) {
    try {
      if (v === undefined) return JSON.parse(localStorage.getItem(k) || "null");
      if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, JSON.stringify(v));
    } catch (e) { return null; }
  }
  function e(s) { return typeof esc === "function" ? esc(s) : String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function rnd(n) { var a = crypto.getRandomValues(new Uint8Array(n)), s = ""; for (var i = 0; i < a.length; i++) s += ("0" + a[i].toString(16)).slice(-2); return s; }
  function uniq(arr) { var seen = {}, out = []; (arr || []).forEach(function (x) { var k = typeof x === "string" ? x : JSON.stringify(x); if (!seen[k]) { seen[k] = 1; out.push(x); } }); return out; }
  function home() { return location.origin + "/events/"; }
  function remindOn() { return !A.doc || A.doc.remind !== false; }
  function ic(p, w) { return '<svg width="' + (w || 18) + '" height="' + (w || 18) + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + p + '</svg>'; }
  var I = {
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    bell: '<path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.9 1.9 0 0 0 3.4 0"/>',
    heart: '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8z"/>',
    send: '<path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4z"/>',
    out: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
    mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>'
  };
  var GLOGO = '<svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z"/><path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44z"/><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z"/></svg>';

  /* ---------- styles ---------- */
  var css = document.createElement("style");
  css.textContent = [
    "#acctbtn .av{width:26px;height:26px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;background:var(--ac);color:#fff;font:700 13px var(--fb,inherit)}",
    "#acctbtn.in{padding:0 6px}",
    ".acw{max-width:640px}",
    ".accard{border:1px solid var(--ln);border-radius:18px;padding:18px;background:var(--pn);margin-top:14px}",
    ".accard h2{margin:0 0 4px;font-size:18px}.accard>p{margin:0 0 12px}",
    ".acben{display:grid;gap:10px;margin:4px 0 16px;padding:0;list-style:none}",
    ".acben li{display:flex;gap:10px;align-items:flex-start;font-size:14.5px}.acben li svg{flex:none;margin-top:1px;color:var(--ac)}",
    ".acgo{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;height:46px;border-radius:12px;border:1px solid var(--ln);background:var(--bg);color:var(--tx);font:600 15px var(--fb,inherit);cursor:pointer}",
    ".acgo:hover{border-color:var(--mu)}",
    ".acor{display:flex;align-items:center;gap:10px;margin:14px 0;color:var(--mu);font-size:13px}.acor::before,.acor::after{content:'';flex:1;height:1px;background:var(--ln)}",
    ".acf{display:flex;gap:8px}.acf input{flex:1;min-width:0;height:46px;border-radius:12px;border:1px solid var(--ln);background:var(--bg);color:var(--tx);padding:0 14px;font:15px var(--fb,inherit)}",
    ".acf input.code{letter-spacing:.4em;font-weight:700;text-align:center}",
    ".acf .btn{height:46px;white-space:nowrap}",
    ".acck,.md label.acck{display:flex;flex-direction:row;gap:10px;align-items:center;margin:14px 0 4px;font-size:14px;font-weight:400;color:var(--tx);cursor:pointer}.acck input{flex:none;margin:2px 0 0;width:18px;height:18px;accent-color:var(--ac)}",
    ".acerr{margin:10px 0 0;color:var(--hot);font-size:14px}",
    ".acfine{margin:12px 0 0;font-size:12.5px;color:var(--mu)}",
    ".acrow{display:flex;align-items:center;gap:12px;padding:12px 0;border-top:1px solid var(--ln)}.acrow:first-of-type{border-top:0}",
    ".acrow .grow{flex:1;min-width:0}.acrow b{display:block;font-size:15px}.acrow .sm{margin:2px 0 0}",
    ".acsw{position:relative;width:46px;height:26px;flex:none;border-radius:999px;border:0;background:var(--ln);cursor:pointer;transition:background .15s}",
    ".acsw::after{content:'';position:absolute;top:3px;left:3px;width:20px;height:20px;border-radius:50%;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.2);transition:left .15s}",
    ".acsw[aria-checked=true]{background:var(--ac)}.acsw[aria-checked=true]::after{left:23px}",
    ".acsub{display:flex;align-items:center;gap:10px;padding:10px 0;border-top:1px solid var(--ln)}.acsub:first-child{border-top:0}",
    ".acsub .grow{flex:1;min-width:0}.acsub b{display:block;font-size:14.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
    ".acst{flex:none;padding:3px 10px;border-radius:999px;font:600 12px var(--fb,inherit);background:var(--pn3,var(--ln));color:var(--tx)}",
    ".acst.ok{background:color-mix(in srgb,#1D9E75 16%,transparent);color:#0F6E56}.acst.no{background:color-mix(in srgb,var(--hot) 14%,transparent);color:var(--hot)}",
    "html.dark .acst.ok,[data-theme=dark] .acst.ok{color:#5DCAA5}",
    ".acact{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}",
    ".acban{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:0 0 16px;padding:12px 14px;border-radius:14px;border:1px solid var(--ln);background:var(--pn)}",
    ".acban .grow{flex:1;min-width:200px;font-size:14px}",
    "#acnudge{position:fixed;left:50%;bottom:calc(16px + env(safe-area-inset-bottom));transform:translateX(-50%);z-index:60;width:min(520px,calc(100% - 24px));display:flex;align-items:center;gap:12px;padding:12px 12px 12px 16px;border-radius:16px;background:var(--tx);color:var(--bg);box-shadow:0 10px 30px rgba(0,0,0,.25)}",
    "#acnudge .grow{flex:1;font-size:14px;line-height:1.35}#acnudge .btn{flex:none}",
    "#acnudge .x{background:transparent;border:0;color:inherit;opacity:.7;font-size:18px;cursor:pointer;padding:4px 6px}",
    "html.app #acnudge{bottom:calc(76px + env(safe-area-inset-bottom))}",
    "#acm .box{max-width:440px}"
  ].join("\n");
  document.head.appendChild(css);

  /* ---------- which sign-in methods are switched on ---------- */
  function loadProviders() {
    return fetch(C.supabaseUrl + "/auth/v1/settings", { headers: { apikey: C.supabaseAnonKey } })
      .then(function (r) { return r.json(); })
      .then(function (j) { var x = (j && j.external) || {}; A.prov = { google: !!x.google, email: !!x.email }; })
      .catch(function () { A.prov = { google: false, email: false }; });
  }

  /* ---------- the sign-in form (used in the sheet and on the account page) ---------- */
  function signinForm(where) {
    if (!A.prov) return '<p class="sm">Loading…</p>';
    if (!A.prov.google && !A.prov.email) {
      return '<p class="sm">Sign-in is almost ready. Please check back soon.</p>' +
        (ADMIN ? '<p class="acerr">Admin note: switch on Google or Email sign-in in Supabase (see README, “Visitor accounts”).</p>' : "");
    }
    var h = "";
    if (A.step === "code") {
      h += '<p class="sm" style="margin:0 0 10px">We sent a 6-digit code to <b>' + e(A.email) + '</b>. It can take a minute to arrive; check your spam folder too.</p>' +
        '<form class="acf" data-acform="code"><input class="code" name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="8" placeholder="123456" aria-label="6-digit code" required><button class="btn p"' + (A.busy ? " disabled" : "") + '>' + (A.busy ? "Checking…" : "Sign in") + '</button></form>' +
        '<p class="sm" style="margin:10px 0 0"><a href="#" data-a="acctagain">Use a different email</a> · <a href="#" data-a="acctresend">Send a new code</a></p>';
    } else {
      if (A.prov.google) h += '<button class="acgo" type="button" data-a="acctgoogle"' + (A.busy ? " disabled" : "") + '>' + GLOGO + 'Continue with Google</button>';
      if (A.prov.google && A.prov.email) h += '<div class="acor">or</div>';
      if (A.prov.email) h += '<form class="acf" data-acform="email"><input type="email" name="email" autocomplete="email" placeholder="you@example.com" aria-label="Your email" value="' + e(A.email) + '" required><button class="btn p"' + (A.busy ? " disabled" : "") + '>' + (A.busy ? "Sending…" : "Email me a code") + '</button></form>';
    }
    var rem = ls("ne_acct_rem");
    h += '<label class="acck"><input type="checkbox" data-acrem' + (rem === false ? "" : " checked") + '><span>Email me a reminder the day before events I save</span></label>';
    if (A.err) h += '<p class="acerr" role="alert">' + e(A.err) + '</p>';
    h += '<p class="acfine">No password needed. We use your email only to sign you in and for the reminders you choose. See <a href="#" data-a="go" data-v="privacy">Privacy and terms</a>.</p>';
    return h;
  }
  function benefits() {
    return '<ul class="acben">' +
      '<li>' + ic(I.heart) + '<span>Your saved events, tourism list and trip on every phone and computer</span></li>' +
      '<li>' + ic(I.bell) + '<span>A reminder email the day before an event you saved</span></li>' +
      '<li>' + ic(I.send) + '<span>See whether events you send in were approved</span></li></ul>';
  }

  /* ---------- sign-in sheet ---------- */
  var M = document.createElement("div");
  M.id = "acm"; M.className = "md"; M.hidden = true;
  M.setAttribute("role", "dialog"); M.setAttribute("aria-modal", "true"); M.setAttribute("aria-labelledby", "acmttl");
  document.body.appendChild(M);
  function sheet() {
    M.innerHTML = '<div class="box"><div style="display:flex;align-items:flex-start;gap:10px"><div style="flex:1"><h2 id="acmttl" style="margin:0">Sign in to NaijaOuting</h2></div>' +
      '<button class="btn g" type="button" data-a="acctclose" aria-label="Close">✕</button></div>' + benefits() + '<div id="acmform">' + signinForm("sheet") + '</div></div>';
  }
  function openSheet() {
    if (A.user) { goAccount(); return; }
    A.err = ""; sheet(); M.hidden = false;
    if (!A.prov) loadProviders().then(refreshForms);
    setTimeout(function () { var i = M.querySelector("input:not([type=checkbox])"); if (i && window.innerWidth > 700) i.focus(); }, 60);
  }
  function refreshForms() {
    if (!M.hidden) { var f = M.querySelector("#acmform"); if (f) f.innerHTML = signinForm("sheet"); }
    var p = document.getElementById("acpform"); if (p) p.innerHTML = signinForm("page");
  }

  /* ---------- account page ---------- */
  function statusChip(st) {
    return st === "approved" ? '<span class="acst ok">Approved</span>' : st === "rejected" ? '<span class="acst no">Not approved</span>' :
      st === "pending" ? '<span class="acst">Waiting for review</span>' : '<span class="acst">Checked</span>';
  }
  A.view = function () {
    if (!A.ready) return '<div class="page acw"><p class="sm">Loading…</p></div>';
    if (!A.user && !live()) return '<div class="page acw"><div class="ph"><div><h1>Sign in</h1><p>Accounts are coming soon.</p></div></div></div>';
    if (!A.user) {
      return '<div class="page acw">' + (C.accounts !== true ? '<p class="acerr">Admin preview: visitors can’t see Sign in yet. Set accounts: true in js/config.js when setup is done.</p>' : "") + '<div class="ph"><div><h1>Sign in</h1><p>Keep everything you save, on every device.</p></div></div>' +
        '<div class="accard">' + benefits() + '<div id="acpform">' + signinForm("page") + '</div></div></div>';
    }
    var u = A.user, name = (u.user_metadata && (u.user_metadata.full_name || u.user_metadata.name)) || "", prov = (u.app_metadata && u.app_metadata.provider) || "email";
    var nfav = FAV.length, nbl = Object.keys(BL || {}).length;
    var subs = A.subs;
    var subsH = subs === null ? '<p class="sm">Loading…</p>' : !subs.length ? '<p class="sm">Nothing yet. Events you send in with <b>Add event</b> show up here with their status.</p>' :
      subs.map(function (x) { return '<div class="acsub"><div class="grow"><b>' + e(x.n || "Event") + '</b><span class="sm">' + (x.s ? e(fmtD(x.s)) + " · " : "") + 'sent ' + e(fmtD((x.at || "").slice(0, 10))) + '</span></div>' + statusChip(x.st) + '</div>'; }).join("");
    return '<div class="page acw"><div class="ph"><div><h1>Your account</h1><p>' + (name ? e(name) + " · " : "") + e(u.email || "") + ' · signed in with ' + (prov === "google" ? "Google" : "an email code") + '</p></div></div>' +
      '<div class="accard"><div class="acrow"><span style="color:var(--ac)">' + ic(I.bell, 20) + '</span><div class="grow"><b>Event reminders</b><p class="sm">An email to ' + e(u.email || "you") + ' the day before an event you saved.</p></div>' +
      '<button class="acsw" type="button" role="switch" aria-checked="' + remindOn() + '" aria-label="Event reminders" data-a="acctrem"></button></div>' +
      '<div class="acrow"><span style="color:var(--ac)">' + ic(I.heart, 20) + '</span><div class="grow"><b>' + nfav + ' saved event' + (nfav === 1 ? "" : "s") + (nbl ? " · " + nbl + " tourism place" + (nbl === 1 ? "" : "s") : "") + '</b><p class="sm">Kept in sync on every device where you sign in.</p></div>' +
      '<button class="btn" type="button" data-a="go" data-v="saved">View</button></div></div>' +
      '<div class="accard"><h2>My submissions</h2><p class="sm">Events you sent in for review.</p>' + subsH + '</div>' +
      '<div class="acact"><button class="btn" type="button" data-a="acctout">' + ic(I.out, 16) + ' Sign out</button>' +
      (A.delAsk ? '<button class="btn" type="button" data-a="acctdel" style="color:var(--hot);border-color:var(--hot)">Yes, delete my account and data</button><button class="btn g" type="button" data-a="acctdelno">Keep it</button>'
        : '<button class="btn g" type="button" data-a="acctdel" style="color:var(--hot)">Delete account</button>') + '</div>' +
      (A.delAsk ? '<p class="acerr">This removes your account, saved list, reminders and any events still waiting for review. It can’t be undone.</p>' : "") +
      '</div>';
  };
  function fmtD(d) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(d || "")) return d || "";
    var x = new Date(d + "T12:00:00");
    return x.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: x.getFullYear() === new Date().getFullYear() ? undefined : "numeric" });
  }
  function goAccount() { M.hidden = true; S.view = "account"; S.sel = null; S.open = null; render(); var v = document.getElementById("view"); if (v) v.scrollTop = 0; scrollTo(0, 0); if (A.user) loadSubs(); }

  /* ---------- links in the header, sidebar, More sheet and Saved page ---------- */
  function initial() { var u = A.user, n = (u.user_metadata && (u.user_metadata.full_name || u.user_metadata.name)) || u.email || "?"; return n.trim().charAt(0).toUpperCase(); }
  function paintHeader() {
    var b = document.getElementById("acctbtn"); if (!b) return;
    b.hidden = !live() && !A.user; if (b.hidden) return;
    if (A.user) { b.classList.add("in"); b.innerHTML = '<span class="av" aria-hidden="true">' + e(initial()) + '</span>'; b.setAttribute("aria-label", "Your account"); b.title = "Your account"; }
    else { b.classList.remove("in"); b.innerHTML = ic(I.user) + '<span class="lg">Sign in</span>'; b.setAttribute("aria-label", "Sign in"); b.title = "Sign in"; }
  }
  A.sideLink = function () {
    if (!live() && !A.user) return "";
    return '<a href="#" data-a="acct">' + ic(I.user) + (A.user ? "Your account" : "Sign in") + '</a>';
  };
  A.moreTile = function () {
    if (!live() && !A.user) return "";
    return '<button data-a="acct">' + ic(I.user, 22) + (A.user ? "Account" : "Sign in") + '</button>';
  };
  A.savedBanner = function () {
    if (!A.ready || A.user || !FAV.length || !live()) return "";
    return '<div class="acban"><span style="color:var(--ac)">' + ic(I.bell, 20) + '</span><span class="grow"><b>Saved on this device only.</b> Sign in to keep them on all your devices and get a reminder the day before.</span><button class="btn p" type="button" data-a="acct">Sign in</button></div>';
  };

  /* ---------- nudge after the first save (once per device) ---------- */
  function nudge() {
    if (A.user || !A.ready || !live() || ls("ne_acct_nudge") || document.getElementById("acnudge")) return;
    if (!A.prov || (!A.prov.google && !A.prov.email)) return;
    ls("ne_acct_nudge", Date.now());
    var n = document.createElement("div"); n.id = "acnudge"; n.setAttribute("role", "status");
    n.innerHTML = '<span class="grow"><b>Saved on this device.</b> Sign in to keep it on all your devices and get a reminder the day before.</span><button class="btn p" type="button" data-a="acct">Sign in</button><button class="x" type="button" data-a="acctnudgex" aria-label="Not now">✕</button>';
    document.body.appendChild(n);
    setTimeout(function () { var x = document.getElementById("acnudge"); if (x) x.remove(); }, 12000);
  }

  /* ---------- actions ---------- */
  function prepHandoff() {
    return sb.auth.getSession().then(function (r) {
      var s = r && r.data && r.data.session;
      if (!s || !s.user || !s.user.is_anonymous || !DB) return;
      var t = rnd(24);
      return DB.doc("handoff/" + s.user.id).set({ t: t }).then(function () { ls("ne_handoff", { a: s.user.id, t: t, at: Date.now() }); }).catch(function () {});
    });
  }
  function remChoice() { var c = document.querySelector("[data-acrem]"); if (c) ls("ne_acct_rem", !!c.checked); }
  function fail(msg) { A.busy = false; A.err = msg; refreshForms(); }
  function google() {
    remChoice(); A.busy = true; A.err = ""; refreshForms();
    prepHandoff().then(function () {
      return sb.auth.signInWithOAuth({ provider: "google", options: { redirectTo: home() + "?acct=1" } });
    }).then(function (r) { if (r && r.error) fail("Google sign-in didn’t start. Please try again."); })
      .catch(function () { fail("Google sign-in didn’t start. Please try again."); });
  }
  function sendCode(email) {
    remChoice(); A.email = email; A.busy = true; A.err = ""; refreshForms();
    prepHandoff().then(function () {
      return sb.auth.signInWithOtp({ email: email, options: { shouldCreateUser: true, emailRedirectTo: home() + "?acct=1" } });
    }).then(function (r) {
      A.busy = false;
      if (r && r.error) {
        var m = String(r.error.message || "");
        A.err = /rate|second|seconds|limit/i.test(m) ? "Too many codes sent. Please wait a minute and try again." : /invalid/i.test(m) ? "That email address doesn’t look right." : "We couldn’t send the code. Please try again in a moment.";
      } else { A.step = "code"; }
      refreshForms();
      setTimeout(function () { var i = document.querySelector("input.code"); if (i) i.focus(); }, 60);
    }).catch(function () { fail("We couldn’t send the code. Please try again in a moment."); });
  }
  function verify(code) {
    remChoice(); A.busy = true; A.err = ""; refreshForms();
    sb.auth.verifyOtp({ email: A.email, token: code.replace(/\s/g, ""), type: "email" }).then(function (r) {
      if (r && r.error) { fail("That code didn’t work. Check it, or send a new one."); return; }
      ls("ne_acct_welcome", 1);
      location.replace(home() + "?acct=1");
    }).catch(function () { fail("That code didn’t work. Check it, or send a new one."); });
  }
  function signOut() {
    ["ne_fav", "ne_bl", "ne_trip", "ne_acct_uid", "ne_mysub", "ne_handoff"].forEach(function (k) { ls(k, null); });
    sb.auth.signOut().catch(function () {}).then(function () { location.replace(home()); });
  }
  function delAccount() {
    sb.rpc("delete_me").then(function (r) {
      if (r && r.error) { toast(/admin/i.test(r.error.message || "") ? "Admins can’t delete their account here." : "That didn’t work. Please try again."); return; }
      ["ne_fav", "ne_bl", "ne_trip", "ne_acct_uid", "ne_mysub", "ne_handoff", "ne_acct_rem"].forEach(function (k) { ls(k, null); });
      sb.auth.signOut().catch(function () {}).then(function () { location.replace(home() + "?deleted=1"); });
    });
  }
  A.act = function (a, v, t, ev) {
    if (ev && t && t.tagName === "A") ev.preventDefault();
    if (a === "acct") { var n = document.getElementById("acnudge"); if (n) n.remove(); if (A.user) goAccount(); else openSheet(); }
    else if (a === "acctclose") { M.hidden = true; A.step = A.step === "code" ? "code" : "start"; }
    else if (a === "acctgoogle") google();
    else if (a === "acctagain") { A.step = "start"; A.err = ""; refreshForms(); }
    else if (a === "acctresend") { if (A.email) sendCode(A.email); }
    else if (a === "acctnudgex") { var x = document.getElementById("acnudge"); if (x) x.remove(); }
    else if (a === "acctrem") { if (!A.doc) A.doc = {}; A.doc.remind = !remindOn(); push(true); render(); toast(A.doc.remind ? "Reminders are on." : "Reminders are off."); }
    else if (a === "acctout") signOut();
    else if (a === "acctdel") { if (!A.delAsk) { A.delAsk = true; render(); } else delAccount(); }
    else if (a === "acctdelno") { A.delAsk = false; render(); }
  };
  document.addEventListener("submit", function (ev) {
    var f = ev.target.closest && ev.target.closest("[data-acform]"); if (!f) return;
    ev.preventDefault(); if (A.busy) return;
    var kind = f.getAttribute("data-acform");
    if (kind === "email") { var em = String(f.elements.email.value || "").trim(); if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em)) { fail("That email address doesn’t look right."); return; } sendCode(em); }
    else { var c = String(f.elements.code.value || "").replace(/\D/g, ""); if (c.length < 6) { fail("Enter the 6-digit code from the email."); return; } verify(c); }
  });
  document.addEventListener("keydown", function (ev) { if (ev.key === "Escape" && !M.hidden) M.hidden = true; });
  M.addEventListener("click", function (ev) { if (ev.target === M) M.hidden = true; });

  /* ---------- sync: this device <-> account ---------- */
  function snap() {
    var ev = {}, list;
    try { list = all(); } catch (x) { list = []; }
    FAV.forEach(function (id) {
      var v = list.find(function (x) { return x.id === id; });
      if (v) ev[id] = { n: v.name, s: v.s, e: v.e || v.s, t: v.time || "", vn: v.venue || "", c: v.city || "", sl: typeof evSlug === "function" ? evSlug(v) : "" };
      else if (A.doc && A.doc.ev && A.doc.ev[id]) ev[id] = A.doc.ev[id];
    });
    return ev;
  }
  function body() {
    var d = A.doc || {};
    return { fav: FAV.slice(), bl: Object.assign({}, BL), trip: TRIP.slice(), ev: snap(), subs: (d.subs || []).slice(-60),
      remind: d.remind !== false, v: lastV = Date.now(), tz: "Africa/Lagos" };
  }
  function push(now) {
    if (!A.user || !DB || applying) return;
    clearTimeout(pushT);
    pushT = setTimeout(function () { var b = body(); A.doc = b; DB.doc("users/" + A.user.id).set(b).catch(function () {}); }, now ? 0 : 900);
  }
  function applyDoc(d) {
    applying = true;
    try {
      FAV.length = 0; (d.fav || []).forEach(function (x) { FAV.push(x); }); _saveFav();
      Object.keys(BL).forEach(function (k) { delete BL[k]; }); Object.assign(BL, d.bl || {}); _saveBL();
      TRIP.length = 0; (d.trip || []).forEach(function (x) { TRIP.push(x); }); _saveTrip();
    } finally { applying = false; }
  }
  // keep the site's own save functions, then also send changes to the account
  var _saveFav = saveFav, _saveBL = saveBL, _saveTrip = saveTrip, _togFav = togFav;
  saveFav = function () { _saveFav(); push(); };
  saveBL = function () { _saveBL(); push(); };
  saveTrip = function () { _saveTrip(); push(); };
  togFav = function (id) { var was = FAV.indexOf(id) >= 0; _togFav(id); if (!was && !A.user) setTimeout(nudge, 400); };

  function startSync() {
    var uid = A.user.id;
    DB.doc("users/" + uid).get().then(function (sn) {
      var d = sn.exists ? sn.data() : null, same = ls("ne_acct_uid") === uid;
      if (d && same) {
        A.doc = d; lastV = d.v || 0; applyDoc(d);
      } else {
        // first sign-in on this device: combine what's here with what's in the account
        var cur = d || {}, rem = ls("ne_acct_rem");
        A.doc = { remind: cur.remind != null ? cur.remind : rem !== false, subs: uniq((cur.subs || []).concat(ls("ne_mysub") || [])), ev: cur.ev || {} };
        applyDoc({ fav: uniq((cur.fav || []).concat(FAV)), bl: Object.assign({}, cur.bl || {}, BL), trip: uniq((cur.trip || []).concat(TRIP)) });
        ls("ne_acct_uid", uid); ls("ne_mysub", null);
        push(true);
      }
      render();
      // other devices: apply their changes when they arrive
      DB.collection("users").onSnapshot(function (sn2) {
        var mine = sn2.docs.find(function (x) { return x.id === uid; }); if (!mine) return;
        var d2 = mine.data(); if (!d2 || !d2.v || d2.v <= lastV) return;
        lastV = d2.v; A.doc = d2; applyDoc(d2); render();
      }, function () {});
    }).catch(function () {});
  }

  /* ---------- My submissions ---------- */
  A.logSub = function (d) {
    var item = { iid: d.iid, n: d.name || "", s: d.s || "", at: new Date().toISOString() };
    if (A.user) { if (!A.doc) A.doc = {}; A.doc.subs = (A.doc.subs || []).concat([item]); push(true); }
    else { var l = ls("ne_mysub") || []; l.push(item); ls("ne_mysub", l.slice(-60)); }
  };
  function loadSubs() {
    if (!A.user || !DB) return;
    var uid = A.user.id;
    Promise.all([DB.doc("submissions/" + uid).get().catch(function () { return null; }), DB.doc("outcomes/" + uid).get().catch(function () { return null; })]).then(function (r) {
      var pend = {}, out = {};
      if (r[0] && r[0].exists) (r[0].data().items || []).forEach(function (x) { pend[x.iid] = x; });
      if (r[1] && r[1].exists) (r[1].data().items || []).forEach(function (x) { out[x.iid] = x; });
      var seen = {}, list = [];
      ((A.doc && A.doc.subs) || []).forEach(function (x) {
        if (seen[x.iid]) return; seen[x.iid] = 1;
        list.push({ n: x.n, s: x.s, at: x.at, st: pend[x.iid] ? "pending" : out[x.iid] ? out[x.iid].st : "checked" });
      });
      Object.keys(pend).forEach(function (k) { if (!seen[k]) { seen[k] = 1; var x = pend[k]; list.push({ n: x.name, s: x.s, at: new Date(+String(k).split("-")[0] || Date.now()).toISOString(), st: "pending" }); } });
      Object.keys(out).forEach(function (k) { if (!seen[k]) { seen[k] = 1; var x = out[k]; list.push({ n: x.n, s: "", at: x.at, st: x.st }); } });
      list.sort(function (a, b) { return (b.at || "") < (a.at || "") ? -1 : 1; });
      A.subs = list;
      if (S.view === "account") render();
    });
  }

  var _r = render; render = function () { _r.apply(this, arguments); paintHeader(); };

  /* ---------- start ---------- */
  var q = new URLSearchParams(location.search), back = q.get("acct") === "1", deleted = q.get("deleted") === "1",
    wantPage = /^#(signin|account)$/.test(location.hash);
  if (back || deleted || q.get("code")) history.replaceState(null, "", location.pathname + location.hash);
  if (wantPage) history.replaceState(null, "", location.pathname);
  loadProviders().then(refreshForms);
  sb.auth.getSession().then(function (r) {
    var s = r && r.data && r.data.session, u = s && s.user;
    A.user = u && !u.is_anonymous ? u : null;
    A.ready = true;
    paintHeader();
    if (!A.user) { render(); if (deleted) toast("Your account and its data have been deleted."); if (wantPage) goAccount(); return; }
    var h = ls("ne_handoff"), claim = h && h.a && h.a !== A.user.id && Date.now() - (h.at || 0) < 2 * 864e5
      ? sb.rpc("claim_guest", { old_id: h.a, tok: h.t }).then(function () {}, function () {}) : Promise.resolve();
    claim.then(function () {
      ls("ne_handoff", null);
      var wait = function (n) { if (DB || n > 40) { if (DB) startSync(); return; } setTimeout(function () { wait(n + 1); }, 150); };
      wait(0);
      if (back || wantPage) { goAccount(); if (back) toast("Signed in as " + (A.user.email || "you") + "."); }
      else render();
    });
  });
  sb.auth.onAuthStateChange(function (evt, s) {
    if (evt === "SIGNED_OUT") { A.user = null; paintHeader(); }
  });
})();
