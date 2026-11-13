/*
 * NaijaOuting database adapter.
 *
 * The site was first built to run inside Claude, where it calls claude.use("db"),
 * claude.use("user"), claude.use("assets") and claude.use("downloads").
 * This file answers those same calls using Supabase, so the site code stays the same.
 *
 * Data model: one Supabase table, public.docs (col, id, data jsonb).
 * A path such as "overrides/o123" means col = "overrides", id = "o123".
 * Access rules live in supabase/schema.sql (row level security), not here.
 */
(function () {
  "use strict";
  var C = window.NO_CONFIG || {};
  var ready = !!(C.supabaseUrl && C.supabaseAnonKey && window.supabase && window.supabase.createClient);
  var sb = ready
    ? window.supabase.createClient(C.supabaseUrl, C.supabaseAnonKey, {
        auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
      })
    : null;
  window.NO_SB = sb;

  /* ---------- session: visitors get a quiet anonymous session, admins sign in at /admin ---------- */
  var sessP = null;
  function session() {
    if (!sb) return Promise.resolve(null);
    if (!sessP) {
      sessP = sb.auth.getSession().then(function (r) {
        var s = r && r.data && r.data.session;
        if (s) return s;
        return sb.auth.signInAnonymously().then(function (a) {
          return (a && a.data && a.data.session) || null;
        }).catch(function () { return null; });
      }).catch(function () { return null; });
    }
    return sessP;
  }
  if (sb) sb.auth.onAuthStateChange(function (ev) { if (ev === "SIGNED_OUT") sessP = null; });

  /* ---------- helpers ---------- */
  function split(p) { var a = String(p).split("/"); return { col: a.slice(0, -1).join("/"), id: a[a.length - 1] }; }
  function clone(o) { return o == null ? o : JSON.parse(JSON.stringify(o)); }
  function rid(n) {
    var c = "abcdefghijklmnopqrstuvwxyz0123456789", s = "", b = crypto.getRandomValues(new Uint8Array(n || 20));
    for (var i = 0; i < b.length; i++) s += c[b[i] % 36];
    return s;
  }
  function fail(error) { var e = new Error((error && error.message) || "Database error"); e.msg = e.message; throw e; }

  function getDoc(col, id) {
    return session().then(function () {
      return sb.from("docs").select("data").eq("col", col).eq("id", id).maybeSingle();
    }).then(function (r) { if (r.error) fail(r.error); return r.data ? r.data.data : null; });
  }
  function putDoc(col, id, obj) {
    return session().then(function () {
      return sb.from("docs").upsert({ col: col, id: id, data: clone(obj) || {} }, { onConflict: "col,id" });
    }).then(function (r) { if (r.error) fail(r.error); bump(col); });
  }
  function delDoc(col, id) {
    return session().then(function () {
      return sb.from("docs").delete().eq("col", col).eq("id", id);
    }).then(function (r) { if (r.error) fail(r.error); bump(col); });
  }
  function listCol(col) {
    var out = [];
    function page(from) {
      return sb.from("docs").select("id,data").eq("col", col).range(from, from + 999).then(function (r) {
        if (r.error) fail(r.error);
        out = out.concat(r.data || []);
        return (r.data || []).length < 1000 ? out : page(from + 1000);
      });
    }
    return session().then(function () { return page(0); });
  }

  function docRef(path) {
    var p = split(path), col = p.col, id = p.id;
    return {
      id: id,
      get: function () { return getDoc(col, id).then(function (d) { return { exists: d != null, id: id, data: function () { return clone(d); } }; }); },
      set: function (obj) { return putDoc(col, id, obj); },
      update: function (obj) {
        return getDoc(col, id).then(function (cur) {
          if (cur == null) fail({ message: "That item no longer exists." });
          return putDoc(col, id, Object.assign({}, cur, clone(obj)));
        });
      },
      "delete": function () { return delDoc(col, id); }
    };
  }

  /* ---------- live listeners: realtime when enabled, plus a slow safety refresh ---------- */
  var subs = {}, timers = {}, chan = null, poll = null;
  function snapOf(rows) {
    var docs = rows.map(function (r) { return { id: r.id, exists: true, data: function () { return clone(r.data); } }; });
    return { docs: docs, size: docs.length, empty: !docs.length };
  }
  function refresh(col) {
    var set = subs[col];
    if (!set || !set.length) return;
    listCol(col).then(function (rows) {
      var snap = snapOf(rows);
      set.slice().forEach(function (s) { try { s.fn(snap); } catch (e) { console.error(e); } });
    }).catch(function (e) { set.slice().forEach(function (s) { if (s.err) s.err(e); }); });
  }
  function bump(col) { clearTimeout(timers[col]); timers[col] = setTimeout(function () { refresh(col); }, 250); }
  function ensureLive() {
    if (!sb) return;
    if (!chan) {
      chan = sb.channel("docs-live").on("postgres_changes", { event: "*", schema: "public", table: "docs" }, function (p) {
        var col = (p["new"] && p["new"].col) || (p.old && p.old.col);
        if (col) bump(col); else Object.keys(subs).forEach(bump);
      }).subscribe();
    }
    if (!poll) poll = setInterval(function () { if (!document.hidden) Object.keys(subs).forEach(bump); }, 90000);
  }

  function collection(col) {
    return {
      doc: function (id) { return docRef(col + "/" + id); },
      add: function (obj) { var id = rid(20); return putDoc(col, id, obj).then(function () { return docRef(col + "/" + id); }); },
      get: function () { return listCol(col).then(snapOf); },
      onSnapshot: function (fn, err) {
        var s = { fn: fn, err: err };
        (subs[col] = subs[col] || []).push(s);
        ensureLive();
        refresh(col);
        return function () { subs[col] = (subs[col] || []).filter(function (x) { return x !== s; }); };
      }
    };
  }
  var db = { collection: collection, doc: docRef };

  /* ---------- who is viewing ---------- */
  var adminP = null;
  var user = {
    id: function () { return session().then(function (s) { return s ? s.user.id : null; }); },
    canEdit: function () {
      if (!adminP) {
        adminP = session().then(function (s) {
          if (!s || s.user.is_anonymous) return false;
          return sb.from("admins").select("user_id").eq("user_id", s.user.id).maybeSingle().then(function (r) { return !!(r && r.data); });
        }).catch(function () { return false; });
      }
      return adminP;
    }
  };
  user.isOwner = user.canEdit;

  /* ---------- flyer uploads: Supabase Storage bucket "flyers", served at /_blob/<id> ---------- */
  var assets = {
    upload: function (blob, opt) {
      var type = (opt && opt.type) || blob.type || "image/jpeg", id = "s-" + rid(24);
      return session().then(function () {
        return sb.storage.from("flyers").upload(id, blob, { contentType: type, upsert: false, cacheControl: "31536000" });
      }).then(function (r) {
        if (r.error) fail(r.error);
        return { id: id, url: "/_blob/" + id, sizeBytes: blob.size, contentType: type };
      });
    },
    "delete": function (id) {
      if (!/^s-[0-9a-z]+$/.test(String(id))) return Promise.resolve();
      return session().then(function () { return sb.storage.from("flyers").remove([id]); });
    }
  };

  /* ---------- downloads: a normal browser download ---------- */
  var downloads = {
    save: function (r) {
      r = r || {};
      var data = r.data, blob = data instanceof Blob ? data : new Blob([data == null ? "" : data], { type: r.mimeType || r.type || "text/plain" });
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = r.filename || "download";
      document.body.appendChild(a);
      a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
      return Promise.resolve({ saved: true });
    }
  };

  window.claude = {
    ai: false, /* reading flyers with AI is not available on the own-domain site */
    use: function (k) {
      if (k === "downloads") return Promise.resolve(downloads);
      if (!ready) return Promise.resolve(null);
      if (k === "db") return Promise.resolve(db);
      if (k === "user") return Promise.resolve(user);
      if (k === "assets") return Promise.resolve(assets);
      return Promise.resolve(null);
    }
  };
  if (!ready) console.warn("NaijaOuting: Supabase is not configured yet (js/config.js). Showing built-in events only.");
})();
