/* দামতুলনা অ্যাডমিন প্যানেল
   সাইট স্ট্যাটিক (GitHub Pages), তাই আলাদা সার্ভার নেই। প্যানেল আপনার GitHub টোকেন দিয়ে সরাসরি রিপোর
   config/ ফাইল বদলায় ও কাজ (workflow) চালায়। টোকেন শুধু এই ব্রাউজারে থাকে, কোথাও পাঠানো হয় না (GitHub ছাড়া)। */
(function () {
  "use strict";
  var root = document.getElementById("adm");
  var REPO = root.dataset.repo, BASE = root.dataset.base, SITE = location.origin + BASE;
  var API = "https://api.github.com";
  var TKEY = "dt-admin-token";
  var S = { token: null, user: null, admin: null, files: {}, tab: "dash", dirty: {}, runs: [], search: null, runTimer: null };
  var PLACES = [["product", "প্রোডাক্ট পাতা: স্টোরের তালিকার নিচে"], ["product_bottom", "প্রোডাক্ট পাতা: প্রশ্নোত্তরের আগে"],
    ["category", "ক্যাটাগরি পাতা: তালিকার মাঝে"], ["group", "গ্রুপ পাতা"], ["home", "হোম পেজ"]];
  var FLOWS = { "daily-prices": "দাম আপডেট", "product-details": "স্পেক সংগ্রহ", "deploy-now": "সাইট প্রকাশ",
    "store-logos": "স্টোরের লোগো", "startech-catalog": "ক্যাটালগ গণনা", "catalog": "ক্যাটালগ গণনা" };

  /* ---------- ছোট সহায়ক ---------- */
  function $(s, el) { return (el || document).querySelector(s); }
  function $$(s, el) { return [].slice.call((el || document).querySelectorAll(s)); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function bn(n) { return Number(n || 0).toLocaleString("en-IN").replace(/\d/g, function (d) { return "০১২৩৪৫৬৭৮৯"[d]; }); }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  function ago(iso) {
    var s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (s < 60) return "এইমাত্র";
    if (s < 3600) return bn(Math.round(s / 60)) + " মিনিট আগে";
    if (s < 86400) return bn(Math.round(s / 3600)) + " ঘণ্টা আগে";
    return bn(Math.round(s / 86400)) + " দিন আগে";
  }
  function toast(msg, err) {
    var t = $("#toast"); t.textContent = msg; t.className = "atoast on" + (err ? " err" : "");
    clearTimeout(toast.t); toast.t = setTimeout(function () { t.className = "atoast"; }, err ? 7000 : 4000);
  }
  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) {} }
  function b64enc(str) { var b = new TextEncoder().encode(str), s = ""; for (var i = 0; i < b.length; i += 8192) s += String.fromCharCode.apply(null, b.subarray(i, i + 8192)); return btoa(s); }
  function b64dec(b64) { var s = atob(b64.replace(/\n/g, "")), a = new Uint8Array(s.length); for (var i = 0; i < s.length; i++) a[i] = s.charCodeAt(i); return new TextDecoder().decode(a); }
  function fileB64(file) { return new Promise(function (ok, no) { var r = new FileReader(); r.onload = function () { ok(String(r.result).split(",")[1]); }; r.onerror = no; r.readAsDataURL(file); }); }

  /* ---------- GitHub API ---------- */
  function api(path, opt) {
    opt = opt || {};
    var h = { "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28" };
    if (S.token) h.Authorization = "Bearer " + S.token;
    if (opt.body) h["Content-Type"] = "application/json";
    return fetch(API + path, { method: opt.method || "GET", headers: h, body: opt.body ? JSON.stringify(opt.body) : undefined, cache: "no-store" })
      .then(function (r) {
        if (r.status === 204) return null;
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!r.ok) { var e = new Error(j.message || ("HTTP " + r.status)); e.status = r.status; throw e; }
          return j;
        });
      });
  }
  function getFile(path) {
    return api("/repos/" + REPO + "/contents/" + path + "?ref=main").then(function (j) {
      var text = b64dec(j.content);
      S.files[path] = { sha: j.sha, text: text };
      return text;
    });
  }
  function getJSON(path) {
    if (S.files[path] && S.files[path].data) return Promise.resolve(S.files[path].data);
    return getFile(path).then(function (t) { var d = JSON.parse(t); S.files[path].data = d; return d; });
  }
  function shaOf(path) {
    if (S.files[path]) return Promise.resolve(S.files[path].sha);
    return api("/repos/" + REPO + "/contents/" + path + "?ref=main").then(function (j) { return j.sha; }, function (e) { if (e.status === 404) return null; throw e; });
  }
  function putRaw(path, b64, msg) {
    return shaOf(path).then(function (sha) {
      var body = { message: msg + " (অ্যাডমিন প্যানেল)", content: b64, branch: "main" };
      if (sha) body.sha = sha;
      return api("/repos/" + REPO + "/contents/" + path, { method: "PUT", body: body });
    }).then(function (j) { S.files[path] = { sha: j.content.sha }; return j; });
  }
  function putJSON(path, data, msg) {
    var text = JSON.stringify(data, null, 2) + "\n";
    return putRaw(path, b64enc(text), msg).then(function (j) { S.files[path] = { sha: j.content.sha, text: text, data: data }; return j; });
  }
  function dispatch(file, inputs) {
    return api("/repos/" + REPO + "/actions/workflows/" + file + "/dispatches", { method: "POST", body: { ref: "main", inputs: inputs || {} } });
  }

  /* ---------- লগইন ---------- */
  function renderAuth() {
    var box = $("#authbox"), chip = $("#aconn");
    if (S.user) {
      box.innerHTML = "";
      chip.innerHTML = '<span class="adot ok"></span>' + esc(S.user); chip.title = "চাপলে এই ব্রাউজার থেকে বিচ্ছিন্ন হবে";
      chip.onclick = function () { if (confirm("এই ব্রাউজার থেকে টোকেন মুছে দেবেন?")) { lsSet(TKEY, null); location.reload(); } };
      return;
    }
    chip.innerHTML = '<span class="adot"></span>সংযুক্ত নয়'; chip.title = "";
    chip.onclick = function () { var t = $("#tok"); if (t) t.focus(); };
    box.innerHTML =
      '<div class="abanner"><span class="ab-t"><b>🔒 শুধু দেখা যাবে।</b> পরিবর্তন সেভ করতে GitHub টোকেন দিয়ে সংযুক্ত করুন (কীভাবে বানাবেন: "সেটিং" পাতায়)।</span>' +
      '<span class="ab-f"><input type="password" id="tok" autocomplete="off" spellcheck="false" placeholder="github_pat_…" aria-label="GitHub টোকেন">' +
      '<button type="button" class="abtn" id="login">সংযুক্ত করুন</button></span></div>';
    $("#login").onclick = function () {
      var t = $("#tok").value.trim();
      if (!t) return;
      S.token = t;
      checkToken().then(function (ok) {
        if (ok) { lsSet(TKEY, t); toast("সংযুক্ত হয়েছে"); renderAuth(); show(S.tab); }
        else { S.token = null; }
      });
    };
  }
  function checkToken() {
    return Promise.all([api("/user"), api("/repos/" + REPO)]).then(function (r) {
      if (!r[1].permissions || !r[1].permissions.push) { toast("এই টোকেনে রিপোতে লেখার অনুমতি নেই। Contents: Read and write দিয়ে নতুন টোকেন বানান।", true); return false; }
      S.user = r[0].login; return true;
    }, function (e) { toast("টোকেন কাজ করছে না: " + e.message, true); return false; });
  }
  function need() { if (!S.token) { toast("আগে উপরে GitHub টোকেন দিয়ে সংযুক্ত করুন", true); return false; } return true; }

  /* ---------- সেভ বার ---------- */
  var savers = {};
  function markDirty(tab) {
    S.dirty[tab] = true;
    $("#savebar").hidden = false; document.body.classList.add("adm-dirty");
    var b = $('#tabs [data-tab="' + tab + '"]'); if (b && !b.querySelector(".dot")) b.insertAdjacentHTML("beforeend", '<span class="dot"></span>');
  }
  function clearDirty(tab) {
    delete S.dirty[tab];
    var b = $('#tabs [data-tab="' + tab + '"] .dot'); if (b) b.remove();
    if (!Object.keys(S.dirty).length) { $("#savebar").hidden = true; document.body.classList.remove("adm-dirty"); }
  }
  $("#savebtn").onclick = function () {
    if (!need()) return;
    var tabs = Object.keys(S.dirty), btn = $("#savebtn");
    btn.disabled = true; btn.textContent = "সেভ হচ্ছে…";
    tabs.reduce(function (p, t) { return p.then(function () { return savers[t] ? savers[t]() : null; }).then(function () { clearDirty(t); }); }, Promise.resolve())
      .then(function () { toast("সেভ হয়েছে। ২-৩ মিনিটের মধ্যে সাইটে দেখা যাবে।"); setTimeout(loadRuns, 4000); },
        function (e) { toast("সেভ হয়নি: " + (e.status === 409 ? "অন্য কোথাও থেকে ফাইলটা বদলেছে, পাতা রিফ্রেশ করে আবার চেষ্টা করুন" : e.message), true); })
      .then(function () { btn.disabled = false; btn.textContent = "সেভ করুন"; });
  };
  window.addEventListener("beforeunload", function (e) { if (Object.keys(S.dirty).length) { e.preventDefault(); e.returnValue = ""; } });

  /* ---------- ট্যাব ---------- */
  $("#tabs").addEventListener("click", function (e) {
    var b = e.target.closest("[data-tab]"); if (!b) return;
    var tab = b.dataset.tab, sub = b.dataset.psub || null;
    closeSide();
    if (tab === S.tab && (!sub || sub === S.psub)) return;
    function go() { if (sub) { S.psub = sub; lsSet("dt_admin_psub", sub); } show(tab); }
    if (S.dirty[S.tab] && tab !== S.tab) {
      if (confirm("এই পাতায় সেভ না করা পরিবর্তন আছে। এখনই সেভ করবেন?\n(বাতিল চাপলে পরিবর্তনগুলো মুছে যাবে)")) {
        $("#savebtn").click(); var w = setInterval(function () { if (!S.dirty[S.tab] && !$("#savebtn").disabled) { clearInterval(w); go(); } }, 300);
        return;
      }
      clearDirty(S.tab); S.files = {};
    }
    go();
  });
  function closeSide() { $("#aside").classList.remove("open"); $("#ascrim").classList.remove("open"); }
  $("#aburger").onclick = function () { $("#aside").classList.add("open"); $("#ascrim").classList.add("open"); };
  $("#ascrim").onclick = closeSide;
  function navFor(tab) {
    var all = $$("#tabs [data-tab]").filter(function (b) { return b.dataset.tab === tab; });
    if (all.length > 1) { var sub = S.psub || lsGet("dt_admin_psub") || "sg"; return all.filter(function (b) { return b.dataset.psub === sub; })[0] || all[0]; }
    return all[0];
  }
  function show(tab) {
    if (!VIEWS[tab]) tab = "dash";
    S.tab = tab;
    var cur = navFor(tab);
    $$("#tabs [data-tab]").forEach(function (b) { if (b === cur) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current"); });
    if (cur) {
      var g = cur.previousElementSibling; while (g && !g.classList.contains("agrp")) g = g.previousElementSibling;
      $("#acrumb").textContent = g ? g.textContent : ""; $("#attl").textContent = cur.querySelector(".lb").textContent;
      document.title = cur.querySelector(".lb").textContent + " · অ্যাডমিন | দামতুলনা";
    }
    try { history.replaceState(null, "", "#" + tab); } catch (e) {}
    var old = $("#panel"), p = old.cloneNode(false);  // নতুন এলিমেন্ট: আগের ট্যাবের ইভেন্ট লিসেনার যেন না থাকে
    old.replaceWith(p);
    p.innerHTML = '<section class="card"><p class="aempty">লোড হচ্ছে…</p></section>';
    clearInterval(S.runTimer);
    window.scrollTo(0, 0);
    (VIEWS[tab] || VIEWS.dash)(p).catch(function (e) {
      p.innerHTML = '<section class="card"><p class="aempty" style="color:var(--warn)">লোড হয়নি: ' + esc(e.message) + "</p></section>";
    });
  }
  function counts() {  // সাইডবারে কাজ বাকির সংখ্যা
    var a = S.admin, sx = a.seo || {}, h = a.health || {}, st = h.stores || {};
    var C = { "stores": [Object.keys(st).length, 0], "products-sg": [a.sugg_total || 0, 1], "products-am": [(a.auto_merges || []).length, 0],
      "products-pc": [(a.price_checks || []).length, 1], "manual": [Object.keys(st).filter(function (k) { return !st[k].enabled; }).length, 0],
      "cats": [(a.categories || []).length, 0], "brands": [(a.brands || []).length, 0], "seo-meta": [sx.dup_titles || 0, 1] };
    $$("#tabs [data-cnt-key]").forEach(function (b) {
      var c = C[b.dataset.cntKey], el = b.querySelector(".cnt"); if (!c || !c[0]) return;
      el.hidden = false; el.textContent = bn(c[0]); el.classList.toggle("hot", !!c[1]);
    });
  }
  // উপরের "দাম আপডেট" বোতাম
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-toprun]"); if (!b || !need()) return;
    if (!confirm("সব দোকান থেকে এখনই দাম আনা শুরু হবে (২.৫–৩ ঘণ্টা)। চালাবেন?")) return;
    b.disabled = true;
    dispatch(b.dataset.toprun, {}).then(function () { toast("দাম আপডেট শুরু হয়েছে। ড্যাশবোর্ডের \"সাম্প্রতিক কাজ\"-এ অগ্রগতি দেখা যাবে।"); },
      function (er) { toast("চালু হয়নি: " + er.message, true); }).then(function () { setTimeout(function () { b.disabled = false; }, 8000); });
  });
  function bindDirty(el, tab, fn) {
    var CH = "input[type=checkbox],input[type=file],select,input[type=date]";
    el.addEventListener("input", function (e) { var t = e.target; if (t.matches("input,textarea") && !t.matches(CH)) { if (fn(t) !== false) markDirty(tab); } });
    el.addEventListener("change", function (e) { var t = e.target; if (t.matches(CH) && t.type !== "file") { if (fn(t) !== false) markDirty(tab); } });
  }
  function tog(name, label, on, extra) { return '<label class="atog"><span>' + label + '</span><input type="checkbox" data-k="' + name + '"' + (on ? " checked" : "") + (extra || "") + "></label>"; }
  function fld(name, label, val, type, hint, attrs) {
    return '<div class="af"><label>' + label + "</label>" +
      (type === "textarea" ? '<textarea data-k="' + name + '"' + (attrs || "") + ">" + esc(val) + "</textarea>"
        : '<input type="' + (type || "text") + '" data-k="' + name + '" value="' + esc(val) + '"' + (attrs || "") + ">") +
      (hint ? "<small>" + hint + "</small>" : "") + "</div>";
  }
  function setPath(obj, path, val) { var k = path.split("."), o = obj; for (var i = 0; i < k.length - 1; i++) { o = o[k[i]] = o[k[i]] || {}; } o[k[k.length - 1]] = val; }
  function valOf(el) { return el.type === "checkbox" ? el.checked : el.type === "number" ? Number(el.value) : el.value.trim(); }

  /* ---------- ড্যাশবোর্ড ---------- */
  function loadRuns() {
    return api("/repos/" + REPO + "/actions/runs?per_page=10").then(function (j) {
      S.runs = j.workflow_runs || []; var box = $("#runs"); if (box) box.innerHTML = runsHTML();
      clearInterval(S.runTimer);
      if (S.runs.some(function (r) { return r.status !== "completed"; }) && S.tab === "dash") S.runTimer = setInterval(loadRuns, 20000);
    }, function () { var box = $("#runs"); if (box) box.innerHTML = '<p class="aempty">কাজের তালিকা আনা যায়নি।</p>'; });
  }
  function runsHTML() {
    if (!S.runs.length) return '<p class="aempty">কোনো কাজ নেই।</p>';
    return S.runs.map(function (r) {
      var done = r.status === "completed", c = done ? (r.conclusion || "skipped") : "run";
      var lbl = done ? ({ success: "সফল", failure: "ব্যর্থ", cancelled: "বাতিল", skipped: "বাদ" }[r.conclusion] || r.conclusion) : (r.status === "queued" || r.status === "pending" || r.status === "waiting" ? "অপেক্ষায়" : "চলছে");
      return '<div class="arun"><span class="rs ' + c + '">' + (c === "success" ? "✓" : c === "failure" ? "!" : "") + '</span><div style="min-width:0"><b>' + esc(FLOWS[r.name] || r.name) +
        '</b> <small>· ' + lbl + " · " + ago(r.run_started_at || r.created_at) + '</small></div><a href="' + esc(r.html_url) + '" target="_blank" rel="noopener" style="font-size:.8rem;text-decoration:underline">বিস্তারিত</a></div>';
    }).join("");
  }
  var VIEWS = {};
  function card(h, sub, body, extra) { return '<section class="card"><div class="chd"><h2>' + h + "</h2>" + (sub ? '<span class="sub">' + sub + "</span>" : "") + '<span class="asp"></span>' + (extra || "") + "</div>" + body + "</section>"; }
  function storeState(k, x) {
    if (!x.enabled) return ["off", "হাতে দাম / বন্ধ"];
    if ((x.errors && x.errors.length) || (x.failed_cats && x.failed_cats.length)) return ["bad", "সমস্যা"];
    if (!x.items) return ["bad", "কিছু আসেনি"];
    return ["ok", "ঠিক আছে"];
  }
  VIEWS.dash = function (p) {
    var a = S.admin, st = a.stats, h = a.health || {}, hs = h.stores || {}, sk = a.stock || {}, sn = a.store_news || {}, names = a.store_names || {}, sx = a.seo || {};
    var listed = (sk["in"] || 0) + (sk.partial || 0) + (sk.coming || 0) + (sk.grace || 0), totSt = 0;
    Object.keys(sk).forEach(function (k) { totSt += sk[k]; });
    var keys = Object.keys(hs), live = keys.filter(function (k) { return hs[k].enabled; });
    var bad = live.filter(function (k) { return storeState(k, hs[k])[0] === "bad"; });
    var nDn = 0, nUp = 0, nNew = 0, nOos = 0;
    keys.forEach(function (k) { var c = sn[k] || {}; nDn += c.dn || 0; nUp += c.up || 0; nNew += c["new"] || 0; nOos += c.oos || 0; });
    var tr = a.track || {}, npc = (a.price_checks || []).length;
    var todo = [];
    bad.forEach(function (k) { todo.push(["bad", "!", (names[k] || k) + ": দাম আনায় সমস্যা", (hs[k].errors || []).concat(hs[k].failed_cats || []).join(", ") || "কোনো আইটেম আসেনি", "stores"]); });
    if (a.sugg_total) todo.push(["bad", "⇄", bn(a.sugg_total) + "টি সম্ভাব্য মিল যাচাই বাকি", "মেলালে প্রোডাক্টগুলো এক পাতায় তুলনা হবে", "products", "sg"]);
    if (npc) todo.push(["warn", "৳", bn(npc) + "টি প্রোডাক্টে দামে বড় ফারাক", "এক দোকানের দাম অন্যদের চেয়ে অনেক আলাদা; ভুল মিল বা ভুল দাম হতে পারে", "products", "pc"]);
    var off = keys.filter(function (k) { return !hs[k].enabled; });
    if (off.length) todo.push(["info", "✋", bn(off.length) + "টি দোকানের দাম হাতে বসাতে হয়", off.map(function (k) { return names[k] || k; }).join(", "), "manual"]);
    if (sx.dup_titles) todo.push(["warn", "T", bn(sx.dup_pages) + "টি পাতার শিরোনাম হুবহু এক", "একই প্রোডাক্ট দুইবার তালিকায়; মিলিয়ে দিলে ঠিক হবে", "seo-meta"]);
    if (!tr.ga4 || !tr.gsc) todo.push(["warn", "G", (!tr.ga4 && !tr.gsc ? "Google Analytics ও Search Console" : !tr.ga4 ? "Google Analytics" : "Search Console") + " বসানো হয়নি", "ভিজিটর আর সার্চের তথ্য জমা হচ্ছে না; আইডি দিলেই চালু", "settings"]);
    var stc = [["in", "একাধিক দোকানে স্টকে", "var(--best)"], ["partial", "এক দোকানে স্টকে", "color-mix(in srgb,var(--best) 50%,var(--surface))"], ["coming", "শীঘ্রই আসছে", "var(--accent)"],
               ["grace", "সদ্য শেষ", "var(--warn)"], ["out", "স্টকে নেই (লুকানো)", "var(--line)"]];
    var mx = 1; live.forEach(function (k) { var c = sn[k] || {}; mx = Math.max(mx, (c.dn || 0) + (c.up || 0)); });
    var top = live.slice().sort(function (x, y) { var a1 = sn[x] || {}, b1 = sn[y] || {}; return ((b1.dn || 0) + (b1.up || 0)) - ((a1.dn || 0) + (a1.up || 0)); }).slice(0, 7);
    p.innerHTML =
      '<div class="akpis">' +
        kpi("এখন কেনা যায়", bn(listed), "মোট " + bn(st.total) + "টির মধ্যে", "seo-index") +
        kpi("একাধিক দোকানে তুলনা", bn(st.multi), bn((st.multi / Math.max(1, st.total) * 100).toFixed(1)) + "% প্রোডাক্ট", "products", "sg") +
        kpi("আজ দাম বদল", bn(nDn + nUp), '<span class="dn">▼ ' + bn(nDn) + " কমেছে</span> · " + '<span class="up">▲ ' + bn(nUp) + " বেড়েছে</span>", "stores") +
        kpi("চালু দোকান", bn(live.length) + '<small>/' + bn(keys.length) + "</small>", bad.length ? '<span class="dn">' + bn(bad.length) + "টিতে সমস্যা</span>" : "সবগুলো ঠিক আছে", "stores") +
        kpi("মিল যাচাই বাকি", bn(a.sugg_total || 0), "মেলালে তুলনা বাড়বে", "products", "sg", true) +
      "</div>" +
      '<div class="ag2">' +
        card("আজ মনোযোগ দরকার", bn(todo.length) + "টি বিষয়", '<div class="atodo">' + (todo.length ? todo.map(function (t) {
          return '<a data-go="' + t[4] + '"' + (t[5] ? ' data-gosub="' + t[5] + '"' : "") + '><span class="tic ' + t[0] + '">' + t[1] + '</span><span class="tt"><b>' + esc(t[2]) + "</b><span>" + esc(t[3]) + '</span></span><span class="tgo">দেখুন →</span></a>';
        }).join("") : '<p class="aempty">সব ঠিক আছে 🎉</p>') + "</div>") +
        '<div class="acol">' +
          card("প্রোডাক্টের স্টক", "মোট " + bn(totSt), '<div class="astack">' + stc.map(function (c) { return '<i style="width:' + ((sk[c[0]] || 0) / Math.max(1, totSt) * 100) + "%;background:" + c[2] + '"></i>'; }).join("") + "</div>" +
            '<div class="alegend">' + stc.map(function (c) { return '<div><span class="sw" style="background:' + c[2] + '"></span>' + c[1] + "<b>" + bn(sk[c[0]] || 0) + "</b></div>"; }).join("") + "</div>") +
          card("আজকের দাম আনা", "", '<div class="aline"><span class="adot ok"></span>শেষ: ' + esc(a.updated) + '</div><div class="aline"><span class="adot"></span>পরের বার: প্রতিদিন ভোর ৪:০০</div><div class="aline"><span class="adot ok"></span>আজ নতুন আইটেম ' + bn(nNew) + " · স্টক শেষ " + bn(nOos) + "</div>") +
        "</div>" +
      "</div>" +
      '<div class="ag2 eq">' +
        card("দোকানের অবস্থা", "আজকের দাম আনা", '<div class="ascroll"><table><tr><th>দোকান</th><th class="n">আইটেম</th><th class="n">আজ বদল</th><th>অবস্থা</th></tr>' +
          keys.map(function (k) { var x = hs[k], s2 = storeState(k, x), c = sn[k] || {};
            return '<tr><td><span class="adot ' + s2[0] + '"></span> ' + esc(names[k] || k) + '</td><td class="n">' + (x.enabled ? bn(x.items) : "—") + '</td><td class="n"><span class="dn">▼' + bn(c.dn || 0) + '</span> <span class="up">▲' + bn(c.up || 0) + "</span></td><td><span class=\"atag " + s2[0] + '">' + s2[1] + "</span></td></tr>"; }).join("") +
          "</table></div>", '<button type="button" class="abtn ghost sm" data-go="stores">সেটিং →</button>') +
        card("কোন দোকানে আজ বেশি দাম বদলেছে", "", '<div class="abars">' + top.map(function (k) { var c = sn[k] || {};
          return '<div><div class="abl"><span>' + esc(names[k] || k) + '</span><span class="dn">▼' + bn(c.dn || 0) + '</span><span class="up">▲' + bn(c.up || 0) + '</span></div><div class="astack thin"><i style="width:' + ((c.dn || 0) / mx * 100) + '%;background:var(--warn)"></i><i style="width:' + ((c.up || 0) / mx * 100) + '%;background:var(--best)"></i></div></div>'; }).join("") + "</div>") +
      "</div>" +
      '<section class="card"><h2>কাজ চালান</h2><div class="aacts">' +
        '<div class="aact"><div><b>দাম আপডেট এখনই</b><small>সব স্টোর থেকে দাম তুলে সাইট আপডেট। ২.৫-৩ ঘণ্টা লাগে। এমনিতে প্রতিদিন ভোর ৪টায় নিজে চলে।</small></div><button class="abtn" data-run="daily.yml">চালান</button></div>' +
        '<div class="aact"><div><b>স্পেক ও ওয়ারেন্টি সংগ্রহ</b><small>কতগুলো প্রোডাক্টের (দিনে ৬০০-এর বেশি দিলে Star Tech আটকে দিতে পারে)</small><input type="number" id="dlimit" value="600" min="50" max="5000" aria-label="প্রোডাক্টের সংখ্যা"></div><button class="abtn" data-run="details.yml">চালান</button></div>' +
        '<div class="aact"><div><b>সাইট আবার প্রকাশ</b><small>দাম না তুলে বর্তমান ডাটা দিয়ে ২ মিনিটে সাইট আপডেট</small></div><button class="abtn" data-run="deploy-now.yml">চালান</button></div>' +
        '<div class="aact"><div><b>স্টোরের লোগো আবার আনা</b><small>স্টোরের ওয়েবসাইট থেকে লোগো খুঁজে আনে</small></div><button class="abtn ghost" data-run="logos.yml">চালান</button></div>' +
        '<div class="aact"><div><b>ব্র্যান্ডের লোগো পরীক্ষা</b><small>যেসব ব্র্যান্ডের লোগো নেই বা ভাঙা, শুধু সেগুলো আবার খোঁজে। এমনিতে প্রতি মাসের ১ তারিখে নিজে চলে।</small></div><button class="abtn ghost" data-run="brand-meta.yml">চালান</button></div>' +
      '</div></section>' +
      '<div id="logorep"></div>' +
      '<section class="card"><h2>সাম্প্রতিক কাজ <span class="sub">· নিজে থেকে রিফ্রেশ হয়</span></h2><div class="aruns" id="runs"><p class="aempty">লোড হচ্ছে…</p></div></section>' +
      (a.fresh.length ? '<section class="card"><h2>আজ নতুন যোগ হওয়া <span class="sub">· ' + bn(a.fresh.length) + 'টি</span></h2><div class="rows">' +
        a.fresh.slice(0, 10).map(function (f) { return '<a class="row" href="' + BASE + "/p/" + f.id + '/" target="_blank"><div style="min-width:0"><div class="n">' + esc(f.n) + '</div><div class="w">' + esc(f.c) + "</div></div></a>"; }).join("") + "</div></section>" : "");
    p.addEventListener("click", function (e) {
      var b = e.target.closest("[data-run]"); if (!b || !need()) return;
      var inputs = b.dataset.run === "details.yml" ? { limit: String($("#dlimit").value || 600) } : {};
      b.disabled = true;
      dispatch(b.dataset.run, inputs).then(function () { toast("চালু হয়েছে। নিচের তালিকায় অগ্রগতি দেখা যাবে।"); setTimeout(loadRuns, 3000); },
        function (e) { toast("চালু হয়নি: " + e.message, true); }).then(function () { setTimeout(function () { b.disabled = false; }, 5000); });
    });
    loadRuns();
    // ব্র্যান্ড লোগোর মাসিক পরীক্ষার ফল; সমস্যা থাকলে সতর্কবার্তা
    fetch(BASE + "/static/brands/report.json", { cache: "no-store" }).then(function (r) { return r.ok ? r.json() : null; }).then(function (rp) {
      var box = $("#logorep"); if (!box || !rp) return;
      var miss = rp.missing || [], fixed = rp.fixed || [], okn = (rp.ok || []).length + fixed.length;
      var age = Math.round((Date.now() - new Date(rp.date + "T00:00:00+06:00")) / 864e5);
      if (!miss.length && age <= 35) return;
      box.innerHTML = '<section class="card"><h2>ব্র্যান্ডের লোগো <span class="sub">· শেষ পরীক্ষা ' + esc(rp.date) + "</span></h2>" +
        (age > 35 ? '<div class="anote warn">⚠ ' + bn(age) + " দিন ধরে লোগো পরীক্ষা হয়নি। উপরের \"ব্র্যান্ডের লোগো পরীক্ষা\" চালান।</div>" : "") +
        '<p style="margin:0 0 8px;font-size:.9rem">মোট ' + bn(rp.total) + "টি ব্র্যান্ড: <b style=\"color:var(--best)\">" + bn(okn) + "টির লোগো ঠিক আছে</b>" +
        (miss.length ? ', <b style="color:var(--warn)">' + bn(miss.length) + "টির লোগো নেই</b>" : "") + "।</p>" +
        (miss.length ? '<div class="anote warn" style="font-size:.84rem">লোগো পাওয়া যায়নি: ' + miss.map(function (m) { return "<b>" + esc(m.slug) + "</b>"; }).join(", ") + "। লোগো ফাইল পাঠালে হাতে বসানো যায়।</div>" : "") +
        "</section>";
    }).catch(function () {});
    return Promise.resolve();
  };
  function kpi(l, v, d, go, sub, hot) {
    return '<div class="akpi' + (hot ? " hot" : "") + '" data-go="' + go + '"' + (sub ? ' data-gosub="' + sub + '"' : "") + '><span class="l">' + l + '</span><span class="v">' + v + '</span><span class="d">' + d + "</span></div>";
  }
  // কার্ড/তালিকা থেকে অন্য পাতায় যাওয়া
  document.addEventListener("click", function (e) {
    var g = e.target.closest("[data-go]"); if (!g || !$("#panel").contains(g)) return;
    var nb = $$("#tabs [data-tab]").filter(function (b) { return b.dataset.tab === g.dataset.go && (!g.dataset.gosub || b.dataset.psub === g.dataset.gosub); })[0];
    if (nb) nb.click();
  });

  /* ---------- স্টোর ---------- */
  VIEWS.stores = function (p) {
    return Promise.all([getJSON("config/stores.json"), getJSON("web/static/logos/logos.json").catch(function () { return {}; })]).then(function (r) {
      var cfg = clone(r[0]), logos = clone(r[1]), pending = {}, h = S.admin.health.stores || {};
      function draw() {
        p.innerHTML = '<section class="card"><h2>স্টোর</h2><p class="muted" style="margin:0;font-size:.85rem">কোন স্টোর থেকে দাম তোলা হবে, নাম, লোগো আর কত ধীরে তোলা হবে। চালু/বন্ধ পরের দামের রান থেকে কার্যকর হবে।</p></section>' +
          Object.keys(cfg.stores).map(function (id) {
            var s = cfg.stores[id], lg = pending[id] ? pending[id].url : (logos[id] ? BASE + "/static/" + logos[id] : null), hx = h[id] || {};
            return '<section class="aitem' + (s.enabled ? "" : " off") + '" data-id="' + id + '">' +
              '<div class="ahead"><span class="alogo' + (s.logo_dark ? " dark" : "") + '">' + (lg ? '<img src="' + esc(lg) + '" alt="">' : esc(s.short)) + "</span><b>" + esc(s.name) + '</b><small class="muted">' + bn(hx.items || 0) + " অফার</small></div>" +
              tog("enabled", "দাম তোলা চালু", s.enabled) +
              tog("images", "এই স্টোরের ছবি সাইটে দেখানো", s.images !== false) +
              '<div class="agrid">' + fld("name", "নাম", s.name) + fld("short", "সংক্ষিপ্ত নাম (লোগো না থাকলে)", s.short, "text", "", ' maxlength="3"') + "</div>" +
              fld("delay", "দুই পাতার মাঝে অপেক্ষা (সেকেন্ড)", s.delay, "number", "স্টোরের robots.txt যা বলে তার কম দেবেন না, নইলে স্টোর ব্লক করতে পারে।", ' min="1" max="60"') +
              tog("logo_dark", "লোগোর পেছনে কালো রঙ (সাদা লোগোর জন্য)", !!s.logo_dark) +
              '<div class="af"><label>এই স্টোরের মোবাইল/ট্যাবলেট সাধারণত</label><select data-k="phone_type">' +
                [["", "জানা নেই (লেবেল দেখাবে না)"], ["official", "অফিসিয়াল"], ["unofficial", "আনঅফিসিয়াল"]].map(function (o) {
                  return '<option value="' + o[0] + '"' + ((s.phone_type || "") === o[0] ? " selected" : "") + ">" + o[1] + "</option>"; }).join("") +
                "</select><small>প্রোডাক্টের নামে Official/Unofficial লেখা থাকলে সেটাই আগে ধরা হয়; না থাকলে এই সেটিং।</small></div>" +
              '<div class="af"><span class="lbl">লোগো বদলান</span><input type="file" accept="image/png,image/jpeg,image/webp,image/svg+xml" data-logo="' + id + '"><small>চওড়া লোগো ভালো (যেমন ৩০০×১০০), ২০০KB-এর কম।</small></div>' +
              (hx.errors && hx.errors.length ? '<div class="anote warn" style="font-size:.78rem">' + hx.errors.map(esc).join("<br>") + "</div>" : "") +
              "</section>";
          }).join("");
      }
      draw();
      bindDirty(p, "stores", function (el) {
        var it = el.closest("[data-id]"); if (!it || !el.dataset.k) return;
        var s = cfg.stores[it.dataset.id]; s[el.dataset.k] = valOf(el);
        if (el.dataset.k === "enabled") it.classList.toggle("off", !el.checked);
        if (el.dataset.k === "logo_dark") $(".alogo", it).classList.toggle("dark", el.checked);
      });
      p.addEventListener("change", function (e) {
        var f = e.target.dataset && e.target.dataset.logo; if (!f || !e.target.files[0]) return;
        var file = e.target.files[0];
        if (file.size > 400000) { toast("ছবিটা অনেক বড় (৪০০KB-এর কম দিন)", true); e.target.value = ""; return; }
        pending[f] = { file: file, url: URL.createObjectURL(file) };
        var img = $('[data-id="' + f + '"] .alogo'); img.innerHTML = '<img src="' + pending[f].url + '" alt="">';
        markDirty("stores");
      });
      savers.stores = function () {
        var chain = Promise.resolve();
        Object.keys(pending).forEach(function (id) {
          chain = chain.then(function () {
            var file = pending[id].file, ext = (file.name.split(".").pop() || "png").toLowerCase().replace("jpeg", "jpg");
            var path = "web/static/logos/" + id + "." + ext;
            return fileB64(file).then(function (b) { return putRaw(path, b, cfg.stores[id].name + "-এর লোগো"); }).then(function () { logos[id] = "logos/" + id + "." + ext; });
          });
        });
        return chain.then(function () {
          if (Object.keys(pending).length) { pending = {}; return putJSON("web/static/logos/logos.json", logos, "লোগোর তালিকা"); }
        }).then(function () { return putJSON("config/stores.json", cfg, "স্টোরের সেটিং"); });
      };
    });
  };

  /* ---------- বিজ্ঞাপন ---------- */
  function loadAds() { return getJSON("config/ads.json").then(clone); }
  function saveAds(ads, msg) { return putJSON("config/ads.json", ads, msg); }
  VIEWS.ads = function (p) {
    return Promise.all([loadAds(), getJSON("config/stores.json")]).then(function (r) {
      var ads = r[0], stores = r[1].stores;
      S.adsDraft = ads;
      ads.adsense = ads.adsense || { client: "", slots: {} }; ads.adsense.slots = ads.adsense.slots || {};
      ads.house_ad = ads.house_ad || { active: true, texts: [] }; ads.contact = ads.contact || {};
      ads.links = ads.links || {}; ads.links.affiliate = ads.links.affiliate || {}; ads.featured_stores = ads.featured_stores || {};
      function draw() {
        var h = ads.house_ad;
        p.innerHTML =
          '<section class="card"><h2>নিজের "বিজ্ঞাপন দিন" ব্যানার</h2>' +
            '<p class="muted" style="margin:0;font-size:.84rem">কোনো স্পন্সর বা AdSense না থাকলে খালি জায়গায় এটা দেখায়, কল ও হোয়াটসঅ্যাপ বাটনসহ। লেখাগুলো পাতা ভেদে ঘুরে ঘুরে আসে।</p>' +
            tog("house_ad.active", "ব্যানার দেখানো চালু", h.active) +
            '<div id="htexts">' + (h.texts || []).map(function (t, i) {
              return '<div class="aitem" style="margin-bottom:8px" data-ht="' + i + '">' + fld("t0", "শিরোনাম " + bn(i + 1), t[0]) + fld("t1", "এক লাইনের লেখা", t[1]) +
                '<button type="button" class="abtn ghost" data-delht="' + i + '" style="justify-self:start">এই লেখা মুছুন</button></div>'; }).join("") + "</div>" +
            '<button type="button" class="abtn ghost" id="addht">+ আরেকটা লেখা যোগ করুন</button>' +
            fld("house_ad.whatsapp_message", "হোয়াটসঅ্যাপে আগে থেকে লেখা বার্তা", h.whatsapp_message || "") +
          "</section>" +
          '<section class="card"><h2>যোগাযোগ</h2><p class="muted" style="margin:0;font-size:.84rem">ব্যানারের বাটন, "বিজ্ঞাপন দিন" ও "প্রাইভেসি নীতি" পাতায় ব্যবহার হয়। ফাঁকা রাখলে দেখাবে না।</p><div class="agrid">' +
            fld("contact.phone", "ফোন নম্বর", ads.contact.phone || "", "tel", "যেমন 01XXXXXXXXX") + fld("contact.whatsapp", "হোয়াটসঅ্যাপ নম্বর", ads.contact.whatsapp || "", "tel") +
            fld("contact.email", "ইমেইল", ads.contact.email || "", "email") + fld("contact.facebook", "ফেসবুক পেজের লিংক", ads.contact.facebook || "", "url") +
          "</div></section>" +
          '<section class="card"><h2>স্টোরে যাওয়ার আগের বার্তা</h2>' +
            tog("going_note", "৫ সেকেন্ডের নির্দেশনা দেখানো", ads.going_note !== false) +
            '<p class="muted" style="margin:0;font-size:.8rem">বন্ধ করলে ক্লিক করলেই সরাসরি স্টোর খুলবে। এই বার্তার ভেতরে বিজ্ঞাপন বসানো যাবে না (গুগলের নিয়মে নিষিদ্ধ)।</p></section>' +
          '<section class="card"><h2>Google AdSense</h2><div class="anote">নিজের ডোমেইন যুক্ত হওয়ার পর AdSense অনুমোদন পেলে এখানে আইডি দিন। github.io ঠিকানায় অনুমোদন পাওয়া যায় না।</div>' +
            fld("adsense.client", "Publisher ID", ads.adsense.client || "", "text", "যেমন ca-pub-1234567890123456। দিলে সব পাতায় AdSense ও ads.txt চালু হবে; Auto ads AdSense ড্যাশবোর্ড থেকে চালু করুন।", ' placeholder="ca-pub-…"') +
            PLACES.map(function (pl) { return fld("adsense.slots." + pl[0], "Ad unit slot: " + pl[1], ads.adsense.slots[pl[0]] || "", "text", "", ' inputmode="numeric" placeholder="ফাঁকা = এখানে AdSense নেই"'); }).join("") +
          "</section>" +
          '<section class="card"><h2>স্পন্সরড স্টোর</h2><p class="muted" style="margin:0;font-size:.84rem">টাকা দেওয়া স্টোর প্রতিটা প্রোডাক্ট পাতায় "স্পন্সরড" লেখাসহ তালিকার উপরে থাকবে (স্টকে থাকলে)। শেষ তারিখের পর নিজে থেকে বন্ধ।</p>' +
            Object.keys(stores).filter(function (id) { return stores[id].enabled; }).map(function (id) {
              var f = ads.featured_stores[id];
              return '<div class="aitem" style="margin-top:8px" data-fs="' + id + '">' + tog("on", "<b>" + esc(stores[id].name) + "</b> স্পন্সরড", !!f) +
                (f ? fld("until", "শেষ তারিখ", f.until || "", "date") : "") + "</div>"; }).join("") +
          "</section>" +
          '<section class="card"><h2>অ্যাফিলিয়েট ও ট্র্যাকিং</h2>' +
            fld("links.utm", "সব স্টোরের লিংকে যুক্ত হবে (utm)", ads.links.utm || "", "text", "স্টোর তাদের Google Analytics-এ দেখবে কত ক্রেতা দামতুলনা থেকে গেছে।") +
            Object.keys(stores).filter(function (id) { return stores[id].enabled; }).map(function (id) {
              return fld("links.affiliate." + id, esc(stores[id].name) + "-এর অ্যাফিলিয়েট কোড", ads.links.affiliate[id] || "", "text", "", ' placeholder="যেমন ref=abc123"'); }).join("") +
          "</section>";
      }
      draw();
      bindDirty(p, "ads", function (el) {
        var ht = el.closest("[data-ht]"), fs = el.closest("[data-fs]");
        if (ht) { ads.house_ad.texts[+ht.dataset.ht][el.dataset.k === "t0" ? 0 : 1] = el.value; return; }
        if (fs) {
          var id = fs.dataset.fs;
          if (el.dataset.k === "on") {
            if (el.checked) { var d = new Date(); d.setMonth(d.getMonth() + 1); ads.featured_stores[id] = { until: d.toISOString().slice(0, 10) }; }
            else delete ads.featured_stores[id];
            draw();
          } else ads.featured_stores[id].until = el.value;
          return;
        }
        if (el.dataset.k) setPath(ads, el.dataset.k, valOf(el));
      });
      p.addEventListener("click", function (e) {
        if (e.target.id === "addht") { ads.house_ad.texts.push(["", ""]); draw(); markDirty("ads"); }
        var d = e.target.dataset && e.target.dataset.delht;
        if (d != null) { ads.house_ad.texts.splice(+d, 1); draw(); markDirty("ads"); }
      });
      savers.ads = function () {
        ads.house_ad.texts = ads.house_ad.texts.filter(function (t) { return t[0] || t[1]; });
        ["phone", "whatsapp"].forEach(function (k) { if (ads.contact[k]) ads.contact[k] = ads.contact[k].replace(/[^\d]/g, "").replace(/^88/, ""); });
        if (ads.adsense.client && !/^ca-pub-\d{10,20}$/.test(ads.adsense.client)) return Promise.reject(new Error("AdSense আইডি ঠিক নেই, ca-pub- দিয়ে শুরু হয়ে সংখ্যা হবে"));
        return saveAds(ads, "বিজ্ঞাপনের সেটিং");
      };
    });
  };

  /* ---------- স্পন্সর ব্যানার ---------- */
  VIEWS.sponsors = function (p) {
    return loadAds().then(function (ads) {
      ads.sponsors = (ads.sponsors || []).filter(function (s) { return s.id !== "example"; });
      var pending = {}, cats = S.admin.categories;
      function draw() {
        p.innerHTML =
          '<section class="card"><h2>স্পন্সর ব্যানার</h2><p class="muted" style="margin:0;font-size:.84rem">কোনো ব্র্যান্ড বা স্টোর টাকা দিলে তাদের ব্যানার এখানে যোগ করুন। যেখানে স্পন্সর আছে সেখানে AdSense বা নিজের ব্যানারের বদলে এটা দেখাবে। একাধিক থাকলে পাতা ভেদে ঘুরে ঘুরে আসবে।</p>' +
            '<button type="button" class="abtn" id="addsp" style="margin-top:10px">+ নতুন স্পন্সর</button></section>' +
          (ads.sponsors.length ? "" : '<section class="card"><p class="aempty">এখনো কোনো স্পন্সর নেই।</p></section>') +
          ads.sponsors.map(function (s, i) {
            var img = pending[i] ? pending[i].url : (s.image ? BASE + "/static/sponsors/" + s.image : null);
            var expired = s.until && s.until < new Date().toISOString().slice(0, 10);
            return '<section class="aitem' + (s.active && !expired ? "" : " off") + '" data-sp="' + i + '">' +
              '<div class="ahead"><b>' + esc(s.title || "নতুন স্পন্সর") + "</b>" + (expired ? '<span class="ro-badge">মেয়াদ শেষ</span>' : "") + "</div>" +
              tog("active", "চালু", s.active) +
              fld("title", "শিরোনাম", s.title || "") + fld("text", "এক লাইনের লেখা", s.text || "") +
              '<div class="agrid">' + fld("url", "কোথায় নিয়ে যাবে (লিংক)", s.url || "", "url", "", ' placeholder="https://…"') + fld("button", "বাটনের লেখা", s.button || "বিস্তারিত") + "</div>" +
              '<div class="af"><span class="lbl">ছবি (ঐচ্ছিক)</span>' + (img ? '<img class="aimg" src="' + esc(img) + '" alt="">' : "") +
                '<input type="file" accept="image/png,image/jpeg,image/webp" data-spimg="' + i + '"><small>চওড়া ব্যানার ভালো, যেমন ১২০০×৩০০, ৩০০KB-এর কম।</small></div>' +
              '<div class="af"><span class="lbl">কোথায় দেখাবে</span><div class="achk">' +
                PLACES.map(function (pl) { return '<label><input type="checkbox" data-where="' + pl[0] + '"' + ((s.where || []).indexOf(pl[0]) > -1 ? " checked" : "") + ">" + pl[1] + "</label>"; }).join("") + "</div></div>" +
              '<div class="af"><label>শুধু এই ক্যাটাগরিগুলোতে (ঐচ্ছিক)</label><select data-k="cats" multiple size="5">' +
                cats.map(function (c) { return '<option value="' + c.slug + '"' + ((s.categories || []).indexOf(c.slug) > -1 ? " selected" : "") + ">" + esc(c.group_bn + " › " + c.name_bn) + "</option>"; }).join("") +
              "</select><small>কিছু না বাছলে সব ক্যাটাগরিতে। একাধিক বাছতে Ctrl চেপে ধরুন (মোবাইলে সরাসরি টিক দিন)।</small></div>" +
              fld("until", "শেষ তারিখ", s.until || "", "date") +
              '<button type="button" class="abtn warn" data-delsp="' + i + '" style="justify-self:start;margin-top:6px">এই স্পন্সর মুছুন</button>' +
              "</section>";
          }).join("");
      }
      draw();
      bindDirty(p, "sponsors", function (el) {
        var it = el.closest("[data-sp]"); if (!it) return;
        var s = ads.sponsors[+it.dataset.sp];
        if (el.dataset.where) {
          s.where = $$("[data-where]", it).filter(function (c) { return c.checked; }).map(function (c) { return c.dataset.where; });
        } else if (el.dataset.k === "cats") {
          s.categories = [].slice.call(el.selectedOptions).map(function (o) { return o.value; });
        } else if (el.dataset.k) {
          s[el.dataset.k] = valOf(el);
          if (el.dataset.k === "title") $(".ahead b", it).textContent = el.value || "নতুন স্পন্সর";
          if (el.dataset.k === "active") it.classList.toggle("off", !el.checked);
        }
      });
      p.addEventListener("change", function (e) {
        var i = e.target.dataset && e.target.dataset.spimg; if (i == null || !e.target.files[0]) return;
        var f = e.target.files[0];
        if (f.size > 600000) { toast("ছবিটা অনেক বড় (৬০০KB-এর কম দিন)", true); e.target.value = ""; return; }
        pending[i] = { file: f, url: URL.createObjectURL(f) }; draw(); markDirty("sponsors");
      });
      p.addEventListener("click", function (e) {
        if (e.target.id === "addsp") {
          var d = new Date(); d.setMonth(d.getMonth() + 1);
          ads.sponsors.unshift({ id: "sp" + Date.now().toString(36), active: true, where: ["product", "category"], categories: [], title: "", text: "", image: "", url: "", button: "বিস্তারিত", until: d.toISOString().slice(0, 10) });
          var np = {}; Object.keys(pending).forEach(function (k) { np[+k + 1] = pending[k]; }); pending = np;
          draw(); markDirty("sponsors");
        }
        var di = e.target.dataset && e.target.dataset.delsp;
        if (di != null && confirm("এই স্পন্সর মুছে দেবেন?")) { ads.sponsors.splice(+di, 1); delete pending[di]; draw(); markDirty("sponsors"); }
      });
      savers.sponsors = function () {
        for (var i = 0; i < ads.sponsors.length; i++) {
          var s = ads.sponsors[i];
          if (s.active && !s.url && !s.image && !pending[i]) return Promise.reject(new Error((s.title || "একটা স্পন্সর") + ": লিংক বা ছবি দিন"));
          if (s.active && !(s.where || []).length) return Promise.reject(new Error((s.title || "একটা স্পন্সর") + ": কোথায় দেখাবে বাছুন"));
        }
        var chain = Promise.resolve();
        Object.keys(pending).forEach(function (k) {
          chain = chain.then(function () {
            var s = ads.sponsors[+k], f = pending[k].file, ext = (f.name.split(".").pop() || "png").toLowerCase().replace("jpeg", "jpg");
            var name = s.id + "-" + Date.now().toString(36) + "." + ext;
            return fileB64(f).then(function (b) { return putRaw("web/static/sponsors/" + name, b, "স্পন্সরের ছবি"); }).then(function () { s.image = name; });
          });
        });
        return chain.then(function () {
          pending = {};
          var full = S.files["config/ads.json"] && S.files["config/ads.json"].data ? clone(S.files["config/ads.json"].data) : ads;
          if (S.dirty.ads && S.adsDraft) full = S.adsDraft;
          full.sponsors = ads.sponsors;
          return saveAds(full, "স্পন্সর ব্যানার");
        });
      };
    });
  };

  /* ---------- ক্যাটাগরি ---------- */
  VIEWS.cats = function (p) {
    return getJSON("config/category_overrides.json").catch(function () { return { names: {}, groups: {}, hidden: [] }; }).then(function (o) {
      var co = clone(o); co.names = co.names || {}; co.groups = co.groups || {}; co.hidden = co.hidden || [];
      var cats = S.admin.categories, groups = [];
      cats.forEach(function (c) { if (!groups.some(function (g) { return g.slug === c.group; })) groups.push({ slug: c.group, name: c.group_bn }); });
      p.innerHTML = '<section class="card"><h2>ক্যাটাগরি</h2><p class="muted" style="margin:0;font-size:.84rem">বাংলা নাম বদলান বা কোনো ক্যাটাগরি সাইট থেকে লুকান। লুকালে সেই ক্যাটাগরির প্রোডাক্টও সাইটে দেখাবে না।</p>' +
        '<div class="af"><input type="search" id="catq" placeholder="ক্যাটাগরি খুঁজুন…"></div></section>' +
        groups.map(function (g) {
          return '<section class="card" data-g="' + g.slug + '"><div class="af" style="margin-top:0"><label>গ্রুপের নাম</label><input type="text" data-gname="' + g.slug + '" value="' + esc(g.name) + '"></div>' +
            cats.filter(function (c) { return c.group === g.slug; }).map(function (c) {
              return '<div class="acat' + (c.hidden ? " hid" : "") + '" data-c="' + c.slug + '" data-s="' + esc((c.name_bn + " " + c.en + " " + c.slug).toLowerCase()) + '"><input type="text" data-cname="' + c.slug + '" value="' + esc(c.name_bn) + '" aria-label="' + esc(c.en) + '">' +
                '<label class="atog" style="min-height:0"><span style="font-size:.78rem">দেখান</span><input type="checkbox" data-chide="' + c.slug + '"' + (c.hidden ? "" : " checked") + "></label>" +
                "<small>" + esc(c.en) + " · " + bn(c.count) + "টি প্রোডাক্ট · <a href=\"" + BASE + "/c/" + c.slug + '/" target="_blank" style="text-decoration:underline">দেখুন</a></small></div>';
            }).join("") + "</section>";
        }).join("");
      $("#catq").addEventListener("input", function () {
        var q = this.value.toLowerCase().trim();
        $$(".acat", p).forEach(function (r) { r.hidden = q && r.dataset.s.indexOf(q) < 0; });
        $$("[data-g]", p).forEach(function (s) { s.hidden = q && !$$(".acat", s).some(function (r) { return !r.hidden; }); });
      });
      bindDirty(p, "cats", function (el) {
        if (el.id === "catq") return false;
        if (el.dataset.gname) { el.value.trim() ? co.groups[el.dataset.gname] = el.value.trim() : delete co.groups[el.dataset.gname]; }
        if (el.dataset.cname) { el.value.trim() ? co.names[el.dataset.cname] = el.value.trim() : delete co.names[el.dataset.cname]; }
        if (el.dataset.chide) {
          var s = el.dataset.chide; co.hidden = co.hidden.filter(function (x) { return x !== s; });
          if (!el.checked) co.hidden.push(s);
          el.closest(".acat").classList.toggle("hid", !el.checked);
        }
      });
      savers.cats = function () { return putJSON("config/category_overrides.json", co, "ক্যাটাগরির নাম/লুকানো"); };
    });
  };

  /* ---------- ব্র্যান্ড ---------- */
  VIEWS.brands = function (p) {
    return getJSON("config/brands.json").then(function (d) {
      var bc = clone(d); bc.info = bc.info || {}; bc.aliases = bc.aliases || {}; bc.generic = bc.generic || [];
      var list = S.admin.brands, min = S.admin.brand_min || 5, cur = null, pending = null;
      var FIELDS = [["name", "দেখানো নাম", "text", "ফাঁকা রাখলে নিজে থেকে"], ["tagline", "এক লাইনের পরিচয়", "text", "যেমন: দক্ষিণ কোরিয়ার ইলেকট্রনিক্স কোম্পানি"],
        ["about", "পরিচিতি (২-৪ লাইন)", "textarea", "নিজের ভাষায় লিখুন, অন্য সাইট থেকে কপি নয়"], ["website", "অফিসিয়াল ওয়েবসাইট", "url", ""],
        ["facebook", "ফেসবুক পেজ", "url", "শুধু অফিসিয়াল (ভেরিফায়েড) পেজ"], ["youtube", "ইউটিউব", "url", ""], ["instagram", "ইনস্টাগ্রাম", "url", ""],
        ["linkedin", "লিংকডইন", "url", ""], ["distributor", "বাংলাদেশে পরিবেশক", "text", "যেমন: Smart Technologies (BD) Ltd."],
        ["support", "সার্ভিস সেন্টার / হেল্পলাইন", "text", "ফোন নম্বর বা ঠিকানা"], ["logo", "লোগোর লিংক", "url", "অফিসিয়াল সাইটের লোগোর ঠিকানা, অথবা নিচে আপলোড"]];
      function listHTML(q) {
        q = (q || "").toLowerCase();
        var hits = list.filter(function (b) { return !q || (b.n + " " + b.s + " " + b.v.join(" ")).toLowerCase().indexOf(q) > -1; }).slice(0, 60);
        return hits.map(function (b) {
          var has = bc.info[b.s] && Object.keys(bc.info[b.s]).length;
          return '<div class="apair" data-b="' + esc(b.s) + '"><div class="nm"><b>' + esc(b.n) + "</b> <span>· " + bn(b.k) + "টি প্রোডাক্ট" + (b.k < min ? " · পাতা নেই (" + bn(min) + "টির কম)" : "") +
            (has ? " · ✓ তথ্য আছে" : "") + (b.v.length > 1 ? "<br>বানান: " + b.v.map(esc).join(", ") : "") + '</span></div>' +
            '<div class="bt"><button type="button" class="abtn" data-edit="' + esc(b.s) + '">সম্পাদনা</button>' +
            (b.k >= min ? '<a class="abtn ghost" style="display:inline-flex;align-items:center" target="_blank" href="' + BASE + "/brand/" + esc(b.s) + '/">দেখুন</a>' : "") + "</div></div>";
        }).join("") || '<p class="aempty">পাওয়া যায়নি।</p>';
      }
      function editHTML(slug) {
        var b = list.filter(function (x) { return x.s === slug; })[0] || { s: slug, n: slug, k: 0, v: [] }, inf = bc.info[slug] || {};
        var al = Object.keys(bc.aliases).filter(function (k) { return bc.aliases[k] === slug; }).join(", ");
        return '<section class="card" data-ed="' + esc(slug) + '"><button type="button" class="abtn ghost" id="bback">‹ সব ব্র্যান্ড</button>' +
          '<h2 style="margin-top:10px">' + esc(b.n) + ' <span class="sub">· ' + bn(b.k) + "টি প্রোডাক্ট</span></h2>" +
          FIELDS.map(function (f) { return fld(f[0], f[1], inf[f[0]] || "", f[2], f[3]); }).join("") +
          '<div class="af"><span class="lbl">লোগো আপলোড</span><input type="file" accept="image/png,image/jpeg,image/webp,image/svg+xml" id="blogo"><small>বর্গাকার বা চওড়া, ২০০KB-এর কম। আপলোড করলে উপরের লিংকের বদলে এটা দেখাবে।</small></div>' +
          '<div class="af"><label>এই নামগুলোও একই ব্র্যান্ড</label><input type="text" id="balias" value="' + esc(al) + '"><small>কমা দিয়ে আলাদা করুন, যেমন: teamgroup, team-group। ওই নামের প্রোডাক্টগুলো এই ব্র্যান্ডে যোগ হবে।</small></div>' +
          '<div class="anote warn" style="margin-top:8px">এটা আসলে কোনো ব্র্যান্ড নয় (যেমন "Laptop", "Paper")? <button type="button" class="abtn warn" id="bnot" style="margin-left:6px">ব্র্যান্ড তালিকা থেকে বাদ দিন</button></div></section>';
      }
      bc.manual = bc.manual || {};
      function nobrandHTML() {
        var nb = S.admin.nobrand || [];
        if (!nb.length) return "";
        var unk = nb.filter(function (x) { return !x.u; }).length;
        return '<section class="card"><h2>ব্র্যান্ড ছাড়া প্রোডাক্ট <span class="sub">· ' + bn(unk) + "টি অজানা, " + bn(nb.length - unk) + "টি সাধারণ ব্র্যান্ডহীন</span></h2>" +
          '<p class="muted" style="margin:0 0 8px;font-size:.84rem">নাম থেকে ব্র্যান্ড বোঝা যায়নি। আসল ব্র্যান্ড জানলে ঘরে লিখে সেভ করুন; সত্যিই ব্র্যান্ড না থাকলে (যেমন সাধারণ কাগজের রোল) ফাঁকা রাখুন। ল্যাপটপের রিপ্লেসমেন্ট পার্টস এখানে আসে না, ওগুলো "কোন ল্যাপটপের জন্য" হিসেবে আলাদা দেখায়।</p>' +
          nb.map(function (x) {
            return '<div class="apair"><div class="nm"><a href="' + BASE + "/p/" + esc(x.id) + '/" target="_blank" style="text-decoration:underline"><b>' + esc(x.n) + "</b></a> <span>· " + esc(x.c) + "</span></div>" +
              '<div class="bt">' + (x.u ? '<span class="muted" style="font-size:.78rem;margin-right:6px">ব্র্যান্ডহীন</span>' : '<label style="font-size:.78rem;margin-right:6px"><input type="checkbox" data-none="' + esc(x.id) + '"' + ((bc.none || []).indexOf(x.id) >= 0 ? " checked" : "") + "> ব্র্যান্ড নেই</label>") +
                '<input type="text" data-nb="' + esc(x.id) + '" value="' + esc(bc.manual[x.id] || "") + '" placeholder="ব্র্যান্ড" style="width:150px"></div></div>';
          }).join("") + "</section>";
      }
      function draw() {
        if (cur) { p.innerHTML = editHTML(cur); return; }
        p.innerHTML = '<section class="card"><h2>ব্র্যান্ড</h2><p class="muted" style="margin:0;font-size:.84rem">' + bn(list.length) + "টি ব্র্যান্ড, এর মধ্যে " +
          bn(list.filter(function (b) { return b.k >= min; }).length) + "টির নিজের পাতা আছে (অন্তত " + bn(min) + "টি প্রোডাক্ট)। পরিচিতি, অফিসিয়াল লিংক আর লোগো যোগ করুন, ভুল বানান এক করুন।</p>" +
          '<div class="af"><input type="search" id="bq" placeholder="ব্র্যান্ড খুঁজুন…"></div><div id="blist">' + listHTML("") + "</div></section>" + nobrandHTML();
        $("#bq").addEventListener("input", function () { $("#blist").innerHTML = listHTML(this.value); });
      }
      draw();
      p.addEventListener("click", function (e) {
        var t = e.target;
        if (t.dataset && t.dataset.edit) { cur = t.dataset.edit; draw(); window.scrollTo(0, 0); }
        else if (t.id === "bback") { cur = null; draw(); }
        else if (t.id === "bnot" && cur && confirm("এটা ব্র্যান্ড তালিকা থেকে বাদ যাবে, এর প্রোডাক্টগুলো কোনো ব্র্যান্ড ছাড়া দেখাবে। ঠিক আছে?")) {
          var b = list.filter(function (x) { return x.s === cur; })[0];
          (b ? b.v : [cur]).forEach(function (v) { var k = v.toLowerCase(); if (bc.generic.indexOf(k) < 0) bc.generic.push(k); });
          markDirty("brands"); cur = null; draw(); toast("সেভ করলে কার্যকর হবে");
        }
      });
      bindDirty(p, "brands", function (el) {
        if (el.id === "bq") return false;
        if (el.dataset.none) { bc.none = (bc.none || []).filter(function (i) { return i !== el.dataset.none; }); if (el.checked) bc.none.push(el.dataset.none); return; }
        if (el.dataset.nb) { var v = el.value.trim(); if (v) bc.manual[el.dataset.nb] = v; else delete bc.manual[el.dataset.nb]; return; }
        if (!cur) return false;
        if (el.id === "balias") {
          Object.keys(bc.aliases).forEach(function (k) { if (bc.aliases[k] === cur) delete bc.aliases[k]; });
          el.value.split(",").map(function (x) { return x.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""); })
            .filter(Boolean).forEach(function (k) { if (k !== cur) bc.aliases[k] = cur; });
          return;
        }
        if (!el.dataset.k) return false;
        var inf = bc.info[cur] = bc.info[cur] || {};
        if (el.value.trim()) inf[el.dataset.k] = el.value.trim(); else delete inf[el.dataset.k];
        if (!Object.keys(inf).length) delete bc.info[cur];
      });
      p.addEventListener("change", function (e) {
        if (e.target.id !== "blogo" || !e.target.files[0] || !cur) return;
        var f = e.target.files[0];
        if (f.size > 200000) { toast("ছবিটা অনেক বড় (২০০KB-এর কম দিন)", true); e.target.value = ""; return; }
        pending = { slug: cur, file: f }; markDirty("brands");
      });
      savers.brands = function () {
        var chain = Promise.resolve();
        if (pending) {
          var pd = pending, ext = (pd.file.name.split(".").pop() || "png").toLowerCase().replace("jpeg", "jpg"), name = pd.slug + "." + ext;
          chain = fileB64(pd.file).then(function (b64) { return putRaw("web/static/brands/" + name, b64, pd.slug + "-এর লোগো"); })
            .then(function () { bc.info[pd.slug] = bc.info[pd.slug] || {}; bc.info[pd.slug].logo = name; pending = null; });
        }
        return chain.then(function () { return putJSON("config/brands.json", bc, "ব্র্যান্ডের তথ্য"); });
      };
    });
  };

  /* ---------- প্রোডাক্ট: লুকানো ও মিলানো ---------- */
  VIEWS.products = function (p) {
    var idx = S.search ? Promise.resolve(S.search) : fetch(BASE + "/search.json").then(function (r) { return r.json(); }).then(function (j) { S.search = j; return j; });
    return Promise.all([getJSON("data/manual_matches.json").catch(function () { return { merge: [], ignore: [] }; }), idx]).then(function (r) {
      var mm = clone(r[0]), list = r[1], byId = {};
      mm.merge = mm.merge || []; mm.ignore = mm.ignore || []; mm.not_same = mm.not_same || [];
      list.forEach(function (x) { byId[x.id] = x; });
      function nm(id) { return byId[id] ? byId[id].n : id; }
      function pairKey(a, b) { return [a, b].sort().join("|"); }
      function merged(a, b) { return mm.merge.some(function (m) { var s = [m.keep].concat(m.merge); return s.indexOf(a) > -1 && s.indexOf(b) > -1; }); }
      mm.price_ok = mm.price_ok || []; mm.drop_offer = mm.drop_offer || [];
      function decided(id, st) { var k = id + "|" + st; return mm.price_ok.indexOf(k) > -1 ? "ok" : mm.drop_offer.indexOf(k) > -1 ? "drop" : ""; }
      // একসাথে অনেকগুলো বাছাই: "৫০টা বাছুন" -> দরকার নেই এমনগুলোর টিক তুলে দিন -> একটা বোতামে সব
      var SEL = S.bulkSel || (S.bulkSel = { sg: {}, pc: {}, am: {} });
      function nsel(k) { return Object.keys(SEL[k]).length; }
      function cb(kind, key) { return '<label class="bsel"><input type="checkbox" data-sel="' + kind + '" value="' + esc(key) + '"' + (SEL[kind][key] ? " checked" : "") + '></label>'; }
      function bar(kind, acts) {
        var n = nsel(kind);
        return '<div class="bbar"><button type="button" class="abtn ghost" data-pick="' + kind + '">পরের ৫০টা বাছুন</button>' +
          (n ? '<button type="button" class="abtn ghost" data-unpick="' + kind + '">বাছাই মুছুন</button><b class="bn">' + bn(n) + "টা বাছা</b>" +
            acts.map(function (a) { return '<button type="button" class="abtn ' + a[2] + '" data-bulk="' + kind + "|" + a[0] + '">' + a[1] + "</button>"; }).join("")
            : '<span class="muted" style="font-size:.8rem">বাছার পর যেগুলো দরকার নেই সেগুলোর টিক তুলে দিন</span>') + "</div>";
      }
      var ACTS = {
        sg: ["সম্ভাব্য একই", [["merge", "একই, মিলান", "ok"], ["notsame", "আলাদা", "ghost"]]],
        pc: ["সন্দেহজনক দাম", [["ok", "দাম ঠিক", "ok"], ["drop", "মিল ভুল", "warn"]]],
        am: ["স্বয়ংক্রিয় মিল", [["notsame", "আলাদা করুন", "warn"]]]
      };
      function floatBar() {  // নিচে ভাসমান বার: টিক তোলার জন্য নিচে নামলেও বোতাম হাতের কাছে
        var h = Object.keys(ACTS).filter(function (k) { return nsel(k); }).map(function (k) {
          return '<div class="bfrow"><b>' + ACTS[k][0] + ": " + bn(nsel(k)) + "টা বাছা</b>" +
            ACTS[k][1].map(function (a) { return '<button type="button" class="abtn ' + a[2] + '" data-bulk="' + k + "|" + a[0] + '">' + a[1] + "</button>"; }).join("") +
            '<button type="button" class="abtn ghost" data-unpick="' + k + '">✕</button></div>';
        }).join("");
        return h ? '<div class="bfloat">' + h + "</div>" : "";
      }
      var visible = { sg: [], pc: [], am: [] };  // এখন পাতায় দেখানো, সিদ্ধান্ত বাকি এমন কী-গুলো (ক্রমে)
      function draw() {
        visible = { sg: [], pc: [], am: [] };
        var sug = S.admin.suggestions.filter(function (s) { return mm.not_same.indexOf(pairKey(s.a, s.b)) < 0; });
        // আলাদা পাতা: একসাথে সব দেখালে পাতা ভারী হয়ে আটকে যায়, তাই একবারে একটা অংশ
        var npc = (S.admin.price_checks || []).filter(function (x) { return x.o.some(function (o) { return o[3] && !decided(x.id, o[0]); }); }).length;
        var SUBS = [["sg", "সম্ভাব্য একই প্রোডাক্ট", S.admin.sugg_total || sug.length], ["am", "স্বয়ংক্রিয় মিল", (S.admin.auto_merges || []).length],
                    ["pc", "সন্দেহজনক দাম", npc], ["hide", "প্রোডাক্ট লুকান", mm.ignore.length]];
        if (!S.psub) { S.psub = lsGet("dt_admin_psub") || "sg"; }
        var sub = S.psub;
        p.innerHTML =
          '<nav class="psub" role="tablist" aria-label="প্রোডাক্টের কাজ">' + SUBS.map(function (x) {
            return '<button type="button" role="tab" data-psub="' + x[0] + '" aria-selected="' + (x[0] === sub) + '">' + x[1] + (x[2] ? " <b>" + bn(x[2]) + "</b>" : "") + "</button>";
          }).join("") + "</nav>" +
          (sub !== "hide" ? "" : '<section class="card"><h2>প্রোডাক্ট লুকান</h2><p class="muted" style="margin:0;font-size:.84rem">ভুল বা অপ্রয়োজনীয় প্রোডাক্ট খুঁজে সাইট থেকে লুকান।</p>' +
            '<div class="af"><input type="search" id="pq" placeholder="প্রোডাক্টের নাম লিখুন…"></div><div class="rows" id="pres"></div>' +
            (mm.ignore.length ? '<h3 style="font-size:.9rem;margin:14px 0 4px">লুকানো আছে (' + bn(mm.ignore.length) + ")</h3>" +
              mm.ignore.map(function (id) { return '<div class="apair"><div class="nm">' + esc(nm(id)) + '</div><div class="bt"><button type="button" class="abtn ghost" data-unhide="' + esc(id) + '">ফিরিয়ে আনুন</button></div></div>'; }).join("") : "") +
          "</section>") +
          (sub !== "pc" ? "" : (function () {
            var pc = (S.admin.price_checks || []).filter(function (x) { return x.o.some(function (o) { return o[3] && !decided(x.id, o[0]); }); });
            if (!pc.length) return "";
            return '<section class="card"><h2>সন্দেহজনক দাম <span class="sub">· ' + bn(pc.length) + "টি</span></h2>" +
              '<p class="muted" style="margin:0;font-size:.84rem">এসব প্রোডাক্টে স্টোরগুলোর দামে অস্বাভাবিক ফারাক (দেড় গুণের বেশি)। চিহ্নিত দাম এখন সর্বনিম্ন দাম ও সাশ্রয়ের হিসাবে ধরা হচ্ছে না। ' +
              '<b>দাম ঠিক</b> চাপলে আবার ধরা হবে; <b>মিল ভুল</b> চাপলে ওই স্টোরের দাম এই পাতা থেকে সরে যাবে।</p>' +
              bar("pc", [["ok", "বাছাগুলো: দাম ঠিক", "ok"], ["drop", "বাছাগুলো: মিল ভুল", "warn"]]) +
              pc.slice(0, 100).map(function (x) {
                return '<div class="apair"><div class="nm"><a href="' + BASE + "/p/" + esc(x.id) + '/" target="_blank" style="text-decoration:underline">' + esc(x.n) + "</a><br><span>" + esc(x.c) + "</span>" +
                  x.o.map(function (o) {
                    var k = x.id + "|" + o[0], st = decided(x.id, o[0]);
                    if (o[3] && !st) visible.pc.push(k);
                    return '<div class="apc' + (o[3] ? " sus" : "") + '"><span>' + (o[3] && !st ? cb("pc", k) : "") + esc(o[1]) + " · <b>৳" + Number(o[2]).toLocaleString("en-IN") + "</b></span>" +
                      (!o[3] ? "" : st ? '<span class="muted" style="font-size:.78rem">' + (st === "ok" ? "✓ দাম ঠিক" : "✓ সরানো হবে") + "</span>"
                        : '<span><button type="button" class="abtn ok" data-pok="' + esc(k) + '">দাম ঠিক</button><button type="button" class="abtn warn" data-pdrop="' + esc(k) + '">মিল ভুল</button></span>') + "</div>";
                  }).join("") + "</div></div>";
              }).join("") + "</section>";
          })()) +
          (sub !== "am" ? "" : (function () {
            var am = S.admin.auto_merges || [];
            if (!am.length) return '<section class="card"><p class="aempty">কোনো স্বয়ংক্রিয় মিল নেই।</p></section>';
            return '<section class="card"><h2>স্বয়ংক্রিয় মিল <span class="sub">· ' + bn(am.length) + "টি</span></h2>" +
              '<p class="muted" style="margin:0;font-size:.84rem">মডেল নম্বর, ব্র্যান্ড আর ক্যাপাসিটি এক হওয়ায় এগুলো নিজে থেকে এক পাতায় জোড়া লাগানো হয়েছে। ভুল হলে <b>আলাদা</b> চাপুন, পরের আপডেটে আলাদা হয়ে যাবে।</p>' +
              '<div class="af"><input type="search" id="amq" placeholder="নাম দিয়ে খুঁজুন…" value="' + esc(S.amq || "") + '"></div>' +
              bar("am", [["notsame", "বাছাগুলো আলাদা করুন", "warn"]]) + '<div id="amres"></div></section>';
          })()) +
          (sub !== "sg" ? "" : '<section class="card"><h2>সম্ভাব্য একই প্রোডাক্ট <span class="sub">· ' + bn(S.admin.sugg_total || sug.length) + "টি</span></h2>" +
            '<p class="muted" style="margin:0;font-size:.84rem">দুই স্টোরে একই জিনিস আলাদা নামে থাকলে মিলিয়ে দিন, তাহলে এক পাতায় দুই দামের তুলনা দেখাবে। <b>Tray</b> আর <b>Box</b> প্রসেসর, বা আলাদা রঙ/সাইজ/র‍্যাম হলে "আলাদা" চাপুন। ' +
            '<b class="sg-new">নতুন তুলনা</b> লেখাগুলো আগে: মেলালে এক দোকানের প্রোডাক্ট প্রথমবার দুই দোকানে তুলনা করা যাবে।</p>' +
            '<div class="af"><input type="search" id="sgq" placeholder="নাম দিয়ে খুঁজুন…" value="' + esc(S.sgq || "") + '"></div>' +
            bar("sg", [["merge", "বাছাগুলো একই, মিলান", "ok"], ["notsame", "বাছাগুলো আলাদা", "ghost"]]) +
            (function () {
              var w = (S.sgq || "").toLowerCase();
              var lst = w ? sug.filter(function (s) { return (s.a_name + " " + s.b_name).toLowerCase().indexOf(w) > -1; }) : sug;
              var n = S.sgn || 60;
              return lst.slice(0, n).map(function (s) {
              var done = merged(s.a, s.b);
              if (!done) visible.sg.push(s.a + "|" + s.b);
              var st = function (x) { return x && x.length ? ' <span class="sg-st">(' + esc(x.join(", ")) + ")</span>" : ' <span class="sg-st">(স্টক নেই)</span>'; };
              return '<div class="apair' + (done ? " done" : "") + '"><div class="nm">' + (done ? "" : cb("sg", s.a + "|" + s.b)) + '<a href="' + BASE + "/p/" + esc(s.a) + '/" target="_blank">' + esc(s.a_name) + "</a>" + st(s.sa) +
                '<br><span>↕ মিলের হার ' + bn(Math.round(s.score * 100)) + "%" + (s.why ? " · " + esc(s.why) : "") + (s.lift === 2 ? ' · <b class="sg-new">নতুন তুলনা</b>' : "") + "</span><br>" +
                '<a href="' + BASE + "/p/" + esc(s.b) + '/" target="_blank">' + esc(s.b_name) + "</a>" + st(s.sb) + "</div>" +
                '<div class="bt">' + (done ? '<span class="muted" style="font-size:.82rem">✓ মিলানো হয়েছে</span> <button type="button" class="abtn ghost" data-unmerge="' + esc(s.a) + "|" + esc(s.b) + '">বাতিল</button>'
                  : '<button type="button" class="abtn ok" data-merge="' + esc(s.a) + "|" + esc(s.b) + '">একই, মিলান</button><button type="button" class="abtn ghost" data-notsame="' + esc(pairKey(s.a, s.b)) + '">আলাদা</button>') + "</div></div>";
              }).join("") + (lst.length > n ? '<p style="text-align:center;margin:12px 0 0"><button type="button" class="abtn ghost" id="sgmore">আরও ৬০টি দেখান (বাকি ' + bn(lst.length - n) + ")</button></p>" : "");
            })() + "</section>") + floatBar();
        $$(".psub [data-psub]").forEach(function (b) {
          b.addEventListener("click", function () { S.psub = b.dataset.psub; lsSet("dt_admin_psub", S.psub); draw(); window.scrollTo(0, 0); });
        });
        var sgq = $("#sgq");
        if (sgq) sgq.addEventListener("change", function () { S.sgq = sgq.value; S.sgn = 60; draw(); });
        var sgm = $("#sgmore");
        if (sgm) sgm.addEventListener("click", function () { S.sgn = (S.sgn || 60) + 60; draw(); });
        var amq = $("#amq");
        function drawAm() {
          var am = S.admin.auto_merges || [], w = (amq.value || "").toLowerCase();
          S.amq = amq.value;
          var rows = am.filter(function (x) { return !w || (x[1] + " " + x[3]).toLowerCase().indexOf(w) > -1; }).slice(0, 100);
          visible.am = [];
          $("#amres").innerHTML = rows.map(function (x) {
            var k = pairKey(x[0], x[2]), no = mm.not_same.indexOf(k) > -1;
            if (!no) visible.am.push(k);
            return '<div class="apair' + (no ? " done" : "") + '"><div class="nm">' + (no ? "" : cb("am", k)) + esc(x[1]) + "<br><span>↕ একই পাতায়</span><br>" + esc(x[3]) + "</div>" +
              '<div class="bt">' + (no ? '<span class="muted" style="font-size:.82rem">✓ আলাদা করা হবে</span>' : '<button type="button" class="abtn ghost" data-notsame="' + esc(k) + '">আলাদা</button>') +
              '<a class="abtn ghost" style="display:inline-flex;align-items:center" href="' + BASE + "/p/" + esc(x[2]) + '/" target="_blank">দেখুন</a></div></div>';
          }).join("");
        }
        if (amq) { amq.addEventListener("input", drawAm); drawAm(); }
        if ($("#pq")) $("#pq").addEventListener("input", function () {
          var t = this.value.toLowerCase().split(/\s+/).filter(Boolean), out = $("#pres");
          if (!t.length) { out.innerHTML = ""; return; }
          var hits = list.filter(function (x) { var n = (x.n + " " + x.c).toLowerCase(); return t.every(function (w) { return n.indexOf(w) > -1; }); }).slice(0, 12);
          out.innerHTML = hits.map(function (x) { var hid = mm.ignore.indexOf(x.id) > -1;
            return '<div class="apair"><div class="nm">' + esc(x.n) + "<br><span>" + esc(x.c) + '</span></div><div class="bt">' +
              (hid ? '<span class="muted" style="font-size:.82rem">লুকানো</span>' : '<button type="button" class="abtn warn" data-hide="' + esc(x.id) + '">সাইট থেকে লুকান</button>') +
              '<a class="abtn ghost" style="display:inline-flex;align-items:center" href="' + BASE + "/p/" + x.id + '/" target="_blank">দেখুন</a></div></div>'; }).join("") || '<p class="aempty">কিছু পাওয়া যায়নি।</p>';
        });
      }
      function doMerge(ab) {
        var keep = ab[0], other = ab[1];
        if (merged(keep, other)) return;
        var m = mm.merge.filter(function (x) { return x.keep === keep; })[0];
        if (m) m.merge.push(other); else mm.merge.push({ keep: keep, merge: [other] });
      }
      function add(arr, v) { if (arr.indexOf(v) < 0) arr.push(v); }
      draw();
      p.addEventListener("change", function (e) {
        var t = e.target;
        if (t.dataset && t.dataset.sel) {
          if (t.checked) SEL[t.dataset.sel][t.value] = 1; else delete SEL[t.dataset.sel][t.value];
          var y = window.scrollY; draw(); window.scrollTo(0, y);
        }
      });
      p.addEventListener("click", function (e) {
        var d = e.target.dataset || {}, y = window.scrollY;
        if (d.pick) {  // তালিকার উপর থেকে যেগুলো এখনো বাছা হয়নি তার পরের ৫০টা
          var k = d.pick, c = 0;
          visible[k].forEach(function (key) { if (c < 50 && !SEL[k][key]) { SEL[k][key] = 1; c++; } });
          draw(); window.scrollTo(0, y); return;
        }
        if (d.unpick) { SEL[d.unpick] = {}; draw(); window.scrollTo(0, y); return; }
        if (d.bulk) {
          var kb = d.bulk.split("|"), kind = kb[0], act = kb[1], keys = Object.keys(SEL[kind]);
          if (!keys.length) return;
          keys.forEach(function (key) {
            if (kind === "sg" && act === "merge") doMerge(key.split("|"));
            else if (kind === "sg" && act === "notsame") { var ab = key.split("|"); add(mm.not_same, pairKey(ab[0], ab[1])); }
            else if (kind === "am") add(mm.not_same, key);
            else if (kind === "pc") add(act === "ok" ? mm.price_ok : mm.drop_offer, key);
          });
          SEL[kind] = {};
          toast(bn(keys.length) + "টা বদল হয়েছে। নিচে \"সেভ করুন\" চাপলে কাজ হবে।");
          draw(); window.scrollTo(0, y); markDirty("products"); return;
        }
        if (d.hide) { mm.ignore.push(d.hide); var q = $("#pq").value; draw(); $("#pq").value = q; $("#pq").dispatchEvent(new Event("input")); markDirty("products"); }
        else if (d.unhide) { mm.ignore = mm.ignore.filter(function (x) { return x !== d.unhide; }); draw(); markDirty("products"); }
        else if (d.merge) {
          doMerge(d.merge.split("|"));
          draw(); markDirty("products");
        } else if (d.unmerge) {
          var u = d.unmerge.split("|");
          mm.merge.forEach(function (x) { if (u.indexOf(x.keep) > -1) x.merge = x.merge.filter(function (y) { return u.indexOf(y) < 0; }); });
          mm.merge = mm.merge.filter(function (x) { return x.merge.length; });
          draw(); markDirty("products");
        } else if (d.notsame) { mm.not_same.push(d.notsame); draw(); markDirty("products"); }
        else if (d.pok) { mm.price_ok.push(d.pok); draw(); markDirty("products"); }
        else if (d.pdrop) { mm.drop_offer.push(d.pdrop); draw(); markDirty("products"); }
      });
      savers.products = function () { return putJSON("data/manual_matches.json", mm, "প্রোডাক্ট মিলানো/লুকানো"); };
    });
  };

  /* ---------- সেটিং ---------- */
  /* ---------- হাতে দাম: যে দোকান স্বয়ংক্রিয় ভিজিট আটকায়, সেখানে মানুষ নিজে দেখে দাম বসায় ---------- */
  VIEWS.manual = function (p) {
    var idx = S.search ? Promise.resolve(S.search) : fetch(BASE + "/search.json").then(function (r) { return r.json(); }).then(function (j) { S.search = j; return j; });
    return Promise.all([getJSON("data/manual_prices.json").catch(function () { return {}; }), getJSON("config/stores.json"), idx]).then(function (r) {
      var mp = clone(r[0]), st = r[1].stores, list = r[2], byId = {}, cur = null;
      var MS = Object.keys(st).filter(function (k) { return st[k].manual; });
      list.forEach(function (x) { byId[x.id] = x; });
      var today = new Date(Date.now() + 6 * 3600e3).toISOString().slice(0, 10);
      function days(d) { return Math.round((new Date(today) - new Date(d)) / 864e5); }
      function gsearch(sid, name) { return "https://www.google.com/search?q=" + encodeURIComponent("site:" + st[sid].home.replace(/^https?:\/\/(www\.)?/, "") + " " + name); }
      function entries() {
        var out = [];
        Object.keys(mp).forEach(function (id) { if (id[0] === "_") return; Object.keys(mp[id]).forEach(function (sid) { out.push({ id: id, sid: sid, m: mp[id][sid] }); }); });
        return out.sort(function (a, b) { return a.m.date < b.m.date ? -1 : 1; });
      }
      function editor(id) {
        var x = byId[id]; if (!x) return "";
        var have = mp[id] || {};
        return '<section class="card" id="med"><h2>' + esc(x.n) + '</h2><p class="muted" style="margin:0 0 8px;font-size:.82rem">' + esc(x.c) + (isFinite(+x.p) && +x.p > 0 ? " · এখন সাইটে সর্বনিম্ন ৳" + bn(+x.p) : "") +
          ' · <a href="' + BASE + "/p/" + id + '/" target="_blank" style="text-decoration:underline">পাতাটা দেখুন</a></p>' +
          MS.map(function (sid) {
            var m = have[sid] || {};
            return '<div class="aitem" data-sid="' + sid + '"><div class="ahead"><b>' + esc(st[sid].name) + "</b>" + (m.date ? '<small class="muted">' + bn(days(m.date)) + " দিন আগে বসানো</small>" : "") + "</div>" +
              '<a class="abtn ghost" style="display:inline-flex;align-items:center;margin-bottom:8px" target="_blank" rel="noopener" href="' + gsearch(sid, x.n) + '">' + esc(st[sid].name) + "-এ খুঁজুন ↗</a>" +
              '<div class="agrid"><div class="af"><label>দাম (৳)</label><input type="number" inputmode="numeric" data-f="price" value="' + esc(m.price || "") + '" placeholder="যেমন 13500"></div>' +
              '<div class="af"><label>প্রোডাক্ট পাতার লিংক</label><input type="url" data-f="url" value="' + esc(m.url || "") + '" placeholder="' + esc(st[sid].home) + '/…"></div></div>' +
              '<label class="atog"><input type="checkbox" data-f="in_stock"' + (m.in_stock === false ? "" : " checked") + "> স্টকে আছে</label>" +
              (m.price ? ' <button type="button" class="abtn ghost" data-del="' + sid + '" style="min-height:32px">মুছুন</button>' : "") + "</div>";
          }).join("") +
          '<button type="button" class="abtn" id="mset">এই প্রোডাক্টের দাম রাখুন</button><p class="muted" style="font-size:.8rem;margin:6px 0 0">রাখার পর নিচে "সেভ করুন" চাপলে ২-৩ মিনিটে সাইটে আসবে।</p></section>';
      }
      function draw() {
        var es = entries(), due = es.filter(function (e) { return days(e.m.date) >= 7; });
        p.innerHTML =
          '<section class="card"><h2>হাতে দাম</h2><p class="muted" style="margin:0;font-size:.85rem;line-height:1.6">যে দোকানগুলো স্বয়ংক্রিয়ভাবে দাম তুলতে দেয় না (' +
            MS.map(function (k) { return esc(st[k].name); }).join(", ") + "), সেখানে নিজে দোকানের পাতা খুলে দাম দেখে এখানে বসান। সাইটে লেখা থাকবে \"হাতে যাচাই করা\" আর কত দিন আগে। " +
            "<b>৭ দিন</b> পরে এখানে হালনাগাদের তালিকায় আসবে, <b>১৪ দিন</b> পেরোলে সাইট থেকে নিজে থেকে সরে যাবে (পুরনো দাম যেন না দেখায়)।</p>" +
            '<div class="af" style="margin-top:10px"><label for="mq">প্রোডাক্ট খুঁজুন</label><input type="search" id="mq" placeholder="নাম লিখুন, যেমন Archer C6"></div><div class="rows" id="mres"></div></section>' +
          (cur ? editor(cur) : "") +
          (due.length ? '<section class="card"><h2>এই সপ্তাহে হালনাগাদ করুন <span class="sub">· ' + bn(due.length) + "টি</span></h2>" +
            '<div class="anote warn" style="font-size:.82rem">এগুলো ৭ দিনের বেশি পুরনো। দোকানের পাতা দেখে দাম বদলে থাকলে ঠিক করুন, একই থাকলে শুধু "রাখুন" চাপলেই তারিখ নতুন হবে।</div>' +
            due.map(function (e) { return row(e); }).join("") + "</section>" : "") +
          '<section class="card"><h2>সব হাতে বসানো দাম <span class="sub">· ' + bn(es.length) + "টি</span></h2>" +
            (es.length ? es.map(function (e) { return row(e); }).join("") : '<p class="aempty">এখনো কোনো দাম বসানো হয়নি। উপরে প্রোডাক্ট খুঁজে শুরু করুন।</p>') + "</section>";
        var q = $("#mq");
        q.addEventListener("input", function () {
          var t = q.value.trim().toLowerCase(), words = t.split(/\s+/).filter(Boolean);
          $("#mres").innerHTML = words.length ? list.filter(function (x) { var n = x.n.toLowerCase(); return words.every(function (w) { return n.indexOf(w) > -1; }); }).slice(0, 12).map(function (x) {
            return '<button type="button" class="row" data-pick="' + esc(x.id) + '" style="text-align:left;width:100%"><div style="min-width:0"><div class="n">' + esc(x.n) + '</div><div class="w">' + esc(x.c) + "</div></div></button>"; }).join("") : "";
        });
      }
      function row(e) {
        var d = days(e.m.date), x = byId[e.id] || { n: e.id };
        return '<div class="apair"><div class="nm">' + esc(x.n) + '<br><small class="muted">' + esc(st[e.sid] ? st[e.sid].name : e.sid) + " · ৳" + bn(+e.m.price) + " · " +
          (d >= 14 ? '<b style="color:var(--warn)">' + bn(d) + " দিন, সাইটে দেখাচ্ছে না</b>" : bn(d) + " দিন আগে") + '</small></div><div class="bt"><button type="button" class="abtn ghost" data-pick="' + esc(e.id) + '">হালনাগাদ</button></div></div>';
      }
      draw();
      p.addEventListener("click", function (ev) {
        var pk = ev.target.closest("[data-pick]");
        if (pk) { cur = pk.dataset.pick; draw(); var ed = $("#med"); if (ed) ed.scrollIntoView({ behavior: "smooth" }); return; }
        var del = ev.target.closest("[data-del]");
        if (del && cur && mp[cur]) { delete mp[cur][del.dataset.del]; if (!Object.keys(mp[cur]).length) delete mp[cur]; markDirty("manual"); draw(); return; }
        if (ev.target.id === "mset" && cur) {
          var ok = 0, bad = "";
          $$("#med [data-sid]").forEach(function (box) {
            var sid = box.dataset.sid, price = +($("[data-f=price]", box).value || 0), url = $("[data-f=url]", box).value.trim();
            if (!price) return;
            if (price < 50 || price > 5000000) { bad = st[sid].name + "-এর দামটা ঠিক মনে হচ্ছে না"; return; }
            var host = st[sid].home.replace(/^https?:\/\/(www\.)?/, "");
            if (url && url.indexOf(host) < 0) { bad = st[sid].name + "-এর লিংক ওই দোকানের নয়"; return; }
            mp[cur] = mp[cur] || {};
            mp[cur][sid] = { price: price, url: url || st[sid].home, in_stock: $("[data-f=in_stock]", box).checked, date: today };
            ok++;
          });
          if (bad) { toast(bad, true); return; }
          if (!ok) { toast("অন্তত একটা দোকানের দাম লিখুন", true); return; }
          markDirty("manual"); toast(bn(ok) + "টি দাম রাখা হলো। নিচে সেভ চাপুন।"); cur = null; draw();
        }
      });
      savers.manual = function () { return putJSON("data/manual_prices.json", mp, "হাতে বসানো দাম"); };
    });
  };

  VIEWS.settings = function (p) {
    p.innerHTML =
      '<section class="card"><h2>GitHub টোকেন কীভাবে বানাবেন</h2><div class="anote"><ol>' +
        '<li>কম্পিউটার বা মোবাইলের ব্রাউজারে <a href="https://github.com/settings/personal-access-tokens/new" target="_blank" rel="noopener" style="text-decoration:underline">github.com/settings/personal-access-tokens/new</a> খুলুন (GitHub-এ লগইন থাকতে হবে)।</li>' +
        "<li><b>Token name</b>: দামতুলনা অ্যাডমিন। <b>Expiration</b>: ৯০ দিন (মেয়াদ শেষে আবার বানাবেন)।</li>" +
        "<li><b>Repository access</b>: Only select repositories → <b>daam-tulona</b> বাছুন।</li>" +
        "<li><b>Permissions → Repository permissions</b>-এ: <b>Contents</b> = Read and write, <b>Actions</b> = Read and write। বাকি সব যেমন আছে।</li>" +
        "<li>নিচে <b>Generate token</b> চাপুন, যে লম্বা লেখা আসবে (github_pat_ দিয়ে শুরু) কপি করুন।</li>" +
        "<li>এই পাতার উপরে \"GitHub টোকেন\" ঘরে পেস্ট করে <b>সংযুক্ত করুন</b> চাপুন।</li>" +
      '</ol></div><div class="anote warn" style="margin-top:8px">টোকেন পাসওয়ার্ডের মতো। কাউকে দেবেন না, চ্যাটে বা ফেসবুকে পাঠাবেন না। ফোন হারালে GitHub থেকে টোকেনটা মুছে (Revoke) দিন।</div></section>' +
      '<section class="card"><h2>সংযোগ</h2><dl>' +
        "<div><dt>রিপো</dt><dd><a href=\"https://github.com/" + esc(REPO) + '" target="_blank" rel="noopener" style="text-decoration:underline">' + esc(REPO) + "</a></dd></div>" +
        "<div><dt>অবস্থা</dt><dd>" + (S.user ? "✅ " + esc(S.user) + " হিসেবে সংযুক্ত" : '<span class="ro-badge">সংযুক্ত নয়</span>') + "</dd></div>" +
        "<div><dt>শেষ ডাটা</dt><dd>" + esc(S.admin.updated) + "</dd></div>" +
      "</dl></section>" +
      '<section class="card" id="leadcard"><h2>"দাম কমলে জানান" লিড</h2><p class="muted" style="margin:0 0 8px;font-size:.85rem">ক্রেতার নাম, নম্বর আর প্রোডাক্ট কোথায় জমা হবে। ঠিকানা ফাঁকা থাকলে লিড আপনার WhatsApp নম্বরে মেসেজ হয়ে আসে।</p>' +
        '<div class="af"><label>Google Sheet-এর Apps Script ঠিকানা</label><input type="url" id="leadurl" placeholder="https://script.google.com/macros/s/…/exec"><small>নিচের ধাপ মেনে একবার সেট করলেই হবে।</small></div>' +
        '<details><summary>Google Sheet কীভাবে যুক্ত করবেন (৫ মিনিট)</summary><div class="anote"><ol>' +
        '<li>Google Drive-এ একটা নতুন Google Sheet খুলুন (নাম: দামতুলনা লিড)। কিছু লিখতে হবে না, শিরোনাম সারি নিজে থেকেই তৈরি হবে।</li>' +
        '<li>উপরের মেনু থেকে <b>Extensions → Apps Script</b> খুলুন। যা লেখা আছে মুছে নিচের কোডটা পেস্ট করুন, তারপর সেভ (💾) চাপুন।</li>' +
        '<li><b>Deploy → New deployment</b> → টাইপ <b>Web app</b> বাছুন → Execute as: <b>Me</b>, Who has access: <b>Anyone</b> → Deploy। Google অনুমতি চাইলে নিজের অ্যাকাউন্ট দিয়ে Allow দিন।</li>' +
        '<li>যে <b>Web app URL</b> আসবে (…/exec দিয়ে শেষ) সেটা কপি করে উপরের ঘরে পেস্ট করুন, তারপর <b>সেভ করুন</b>।</li>' +
        '<li>শিটে প্রতিটা মোবাইল নম্বর একবারই থাকবে। একই নম্বর অন্য প্রোডাক্টের জন্য জমা দিলে সেই সারির "যেসব প্রোডাক্ট" ঘরে নতুন লাইন যোগ হবে (ক্যাটাগরি — প্রোডাক্টের নাম)।</li></ol>' +
        '<pre class="acode">function doPost(e) {\n  var lock = LockService.getScriptLock(); lock.waitLock(20000);\n  try {\n    var s = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];\n    if (s.getLastRow() === 0) s.appendRow(["মোবাইল", "নাম", "যেসব প্রোডাক্ট (ক্যাটাগরি — নাম)", "প্রোডাক্ট সংখ্যা", "প্রথম জমা", "শেষ জমা"]);\n    var d = JSON.parse(e.postData.contents);\n    var phone = String(d.phone).replace(/\\D/g, "");\n    var item = (d.category ? d.category + " — " : "") + d.product;\n    var rows = s.getRange(1, 1, s.getLastRow(), 1).getValues();\n    for (var i = 1; i < rows.length; i++) {\n      if (String(rows[i][0]).replace(/\\D/g, "") === phone) {\n        var r = i + 1, list = String(s.getRange(r, 3).getValue());\n        if (list.split("\\n").indexOf(item) < 0) list = list ? list + "\\n" + item : item;\n        s.getRange(r, 2, 1, 5).setValues([[d.name, list, list.split("\\n").length, s.getRange(r, 5).getValue(), new Date()]]);\n        return ContentService.createTextOutput("ok");\n      }\n    }\n    s.appendRow(["\'" + phone, d.name, item, 1, new Date(), new Date()]);\n    return ContentService.createTextOutput("ok");\n  } finally { lock.releaseLock(); }\n}</pre></div></details></section>' +
      '<section class="card" id="trackcard"><h2>ভিজিটর ট্র্যাকিং ও গুগল টুলস</h2><p class="muted" style="margin:0 0 8px;font-size:.85rem">কতজন ভিজিটর আসছে, কোথা থেকে আসছে, কোন দোকানে ক্লিক করছে আর গুগলে সাইট কেমন দেখাচ্ছে, তা দেখার জন্য। শুধু আইডি বসিয়ে সেভ করুন, কোড লাগবে না। ঘর ফাঁকা রাখলে সেটা বন্ধ থাকে।</p>' +
        '<div class="af"><label>Google Analytics (GA4) মেজারমেন্ট আইডি</label><input type="text" data-tk="ga4" placeholder="G-XXXXXXXXXX"><small>ভিজিটর সংখ্যা, কোন পাতা বেশি দেখা হয়, কোন দোকানে কত ক্লিক (store_click), কতজন "জানান" ফর্ম পূরণ করল (generate_lead)।</small></div>' +
        '<details><summary>GA4 আইডি কীভাবে পাবেন</summary><div class="anote"><ol>' +
          '<li><a href="https://analytics.google.com/" target="_blank" rel="noopener" style="text-decoration:underline">analytics.google.com</a> খুলে Google অ্যাকাউন্ট দিয়ে ঢুকুন → <b>Start measuring</b>।</li>' +
          "<li>Account name: দামতুলনা; Property name: দামতুলনা ওয়েবসাইট; Time zone: Bangladesh; Currency: BDT।</li>" +
          "<li>Platform: <b>Web</b> → Website URL: <b>" + esc(SITE) + "</b> → Create stream।</li>" +
          "<li>যে <b>Measurement ID</b> দেখাবে (G- দিয়ে শুরু) কপি করে উপরের ঘরে বসিয়ে সেভ করুন। ২৪ ঘণ্টার মধ্যে রিপোর্টে ডাটা আসা শুরু হবে।</li></ol></div></details>" +
        '<div class="af"><label>Google Search Console যাচাই কোড</label><input type="text" data-tk="gsc" placeholder="যেমন: aB3dE…xYz (শুধু content-এর ভেতরের লেখা)"><small>গুগলে কোন শব্দে সাইট আসছে, কতবার দেখা ও ক্লিক হচ্ছে, কোন পাতায় সমস্যা।</small></div>' +
        '<details><summary>Search Console কীভাবে যুক্ত করবেন</summary><div class="anote"><ol>' +
          '<li><a href="https://search.google.com/search-console" target="_blank" rel="noopener" style="text-decoration:underline">search.google.com/search-console</a> খুলুন → <b>Add property</b> → <b>URL prefix</b> বাছুন → লিখুন <b>' + esc(SITE + "/") + "</b>।</li>" +
          "<li>Verify-এর পদ্ধতি থেকে <b>HTML tag</b> বাছুন। <code>&lt;meta name=\"google-site-verification\" content=\"<b>এই অংশটা</b>\"&gt;</code> থেকে শুধু content-এর ভেতরের লেখাটা কপি করে উপরের ঘরে বসান, সেভ করুন।</li>" +
          "<li>২-৩ মিনিট পর সাইট আপডেট হলে Search Console-এ <b>Verify</b> চাপুন।</li>" +
          "<li>যাচাই হলে বাঁ দিকে <b>Sitemaps</b>-এ গিয়ে লিখুন <b>sitemap.xml</b> → Submit। (পুরো ঠিকানা: " + esc(SITE + "/sitemap.xml") + ")</li></ol></div></details>" +
        '<div class="af"><label>Bing Webmaster যাচাই কোড (ঐচ্ছিক)</label><input type="text" data-tk="bing" placeholder="৩২ অক্ষরের কোড"><small><a href="https://www.bing.com/webmasters" target="_blank" rel="noopener" style="text-decoration:underline">bing.com/webmasters</a> → Add site → HTML Meta Tag → content-এর লেখাটা। Search Console যুক্ত থাকলে "Import from GSC" দিয়ে কোড ছাড়াই হয়।</small></div>' +
        '<div class="af"><label>Microsoft Clarity প্রজেক্ট আইডি (ঐচ্ছিক)</label><input type="text" data-tk="clarity" placeholder="যেমন: abcd1234ef"><small>বিনামূল্যে ভিজিটরের স্ক্রিন রেকর্ডিং আর হিটম্যাপ: মানুষ কোথায় ক্লিক করে, কোথায় আটকে যায়। <a href="https://clarity.microsoft.com/" target="_blank" rel="noopener" style="text-decoration:underline">clarity.microsoft.com</a> → New project → Settings → Overview-এ Project ID।</small></div>' +
        '<div class="af"><label>Facebook Pixel আইডি (ঐচ্ছিক)</label><input type="text" data-tk="fb_pixel" placeholder="১৫-১৬ অঙ্কের সংখ্যা"><small>ফেসবুক বিজ্ঞাপন চালালে ভিজিটরদের আবার বিজ্ঞাপন দেখানো (রিটার্গেটিং) আর লিড মাপার জন্য। Meta Events Manager → Data sources → Pixel ID।</small></div>' +
        '<div class="tklinks" id="tklinks"></div></section>' +
      '<section class="card"><h2>পরিবর্তন কখন সাইটে আসে</h2><p style="margin:0;font-size:.88rem;line-height:1.6">স্টোরের নাম/লোগো, বিজ্ঞাপন, স্পন্সর, ক্যাটাগরি, প্রোডাক্ট লুকানো বা মিলানো সেভ করলে ২-৩ মিনিটে সাইট আপডেট হয়। স্টোর চালু/বন্ধ বা অপেক্ষার সময় পরের দামের রান থেকে কার্যকর হয় (প্রতিদিন ভোর ৪টায়, অথবা ড্যাশবোর্ড থেকে এখনই চালান)।</p></section>';
    var TK = { ga4: [/^G-[A-Z0-9]{4,15}$/, "GA4 আইডি G- দিয়ে শুরু হয় (যেমন G-AB12CD34EF)"], gsc: [/^[A-Za-z0-9_-]{20,80}$/, "Search Console কোডে শুধু content-এর ভেতরের লেখাটা দিন, পুরো <meta …> নয়"],
               bing: [/^[A-F0-9]{32}$/, "Bing কোড ৩২ অক্ষরের (০-৯, A-F)"], clarity: [/^[a-z0-9]{6,15}$/, "Clarity আইডি ছোট হাতের অক্ষর আর সংখ্যা"], fb_pixel: [/^\d{10,20}$/, "Pixel আইডি শুধু সংখ্যা"] };
    return Promise.all([getJSON("config/leads.json").catch(function () { return { endpoint: "" }; }), getJSON("config/tracking.json").catch(function () { return {}; })]).then(function (r) {
      var cfg = clone(r[0]), tk = clone(r[1]), inp = $("#leadurl"), ch = {};
      inp.value = cfg.endpoint || "";
      inp.addEventListener("input", function () { cfg.endpoint = inp.value.trim(); ch.lead = 1; markDirty("settings"); });
      function links() {
        var L = [];
        if (tk.ga4) L.push(['https://analytics.google.com/', "Google Analytics খুলুন"]);
        if (tk.gsc) L.push(['https://search.google.com/search-console?resource_id=' + encodeURIComponent(SITE + "/"), "Search Console খুলুন"]);
        if (tk.clarity) L.push(['https://clarity.microsoft.com/projects/view/' + encodeURIComponent(tk.clarity) + '/dashboard', "Clarity খুলুন"]);
        $("#tklinks").innerHTML = L.length ? '<p style="margin:10px 0 0;display:flex;gap:8px;flex-wrap:wrap">' + L.map(function (l) { return '<a class="abtn ghost" style="display:inline-flex;align-items:center" target="_blank" rel="noopener" href="' + esc(l[0]) + '">' + l[1] + " ↗</a>"; }).join("") + "</p>" : "";
      }
      $$("[data-tk]").forEach(function (el) {
        el.value = tk[el.dataset.tk] || "";
        el.addEventListener("input", function () {
          var v = el.value.trim();
          var m = v.match(/content=["']([^"']+)["']/); if (m) { v = m[1]; el.value = v; }  // পুরো meta পেস্ট করলে কোডটা বের করে নেয়
          tk[el.dataset.tk] = v; ch.tk = 1; markDirty("settings");
        });
      });
      links();
      savers.settings = function () {
        if (cfg.endpoint && !/^https:\/\/script\.google\.com\/macros\/s\/.+\/exec$/.test(cfg.endpoint)) return Promise.reject(new Error("ঠিকানাটা https://script.google.com/macros/s/…/exec ধরনের হতে হবে"));
        for (var k in TK) { if (tk[k] && !TK[k][0].test(tk[k])) return Promise.reject(new Error(TK[k][1])); }
        var jobs = [];
        if (ch.lead) jobs.push(function () { return putJSON("config/leads.json", cfg, "লিড ফর্মের ঠিকানা"); });
        if (ch.tk) jobs.push(function () { return putJSON("config/tracking.json", tk, "ভিজিটর ট্র্যাকিং ও গুগল টুলস"); });
        return jobs.reduce(function (pr, f) { return pr.then(f); }, Promise.resolve()).then(function () { ch = {}; links(); });
      };
    });
  };

  /* ---------- SEO (config/seo.json; কয়েকটা পাতা একই ফাইল বদলায়) ---------- */
  function seoCfg() { return getJSON("config/seo.json").catch(function () { return {}; }).then(function (raw) { if (!S.seo) S.seo = clone(raw); return S.seo; }); }
  function seoBind(p, tab, after) {
    return seoCfg().then(function (cfg) {
      $$("[data-k]", p).forEach(function (el) {
        var v = cfg[el.dataset.k];
        if (el.type === "checkbox") el.checked = !!v; else if (Array.isArray(v)) el.value = v.join("\n"); else el.value = v == null ? "" : v;
      });
      bindDirty(p, tab, function (t) {
        var k = t.dataset.k; if (!k) return false;
        if (k === "force_index" || k === "force_noindex") cfg[k] = t.value.split(/\n+/).map(function (x) { return x.trim(); }).filter(Boolean);
        else cfg[k] = valOf(t);
        if (after) after(cfg);
      });
      savers[tab] = function () {
        if (!cfg.title_product || !cfg.title_category) return Promise.reject(new Error("প্রোডাক্ট আর ক্যাটাগরির শিরোনাম ফাঁকা রাখা যাবে না"));
        if (cfg.gone_days && cfg.gone_days < 14) cfg.gone_days = 14;
        return putJSON("config/seo.json", cfg, "SEO সেটিং");
      };
      if (after) after(cfg);
      return cfg;
    });
  }
  function srow(kind, t, s, go) { return '<div class="seorow ' + kind + '"><span class="seoic">' + (kind === "ok" ? "✓" : kind === "info" ? "i" : "!") + "</span><div><b>" + t + "</b>" + (s ? "<small>" + s + "</small>" : "") + "</div>" + (go ? '<button type="button" class="abtn ghost sm" data-go="' + go + '">ঠিক করুন →</button>' : "") + "</div>"; }
  function sampleUrl() { var sx = S.admin.seo || {}; return sx.sample ? SITE + "/p/" + sx.sample + "/" : SITE + "/"; }
  function linkBtns(L) { return '<p class="alinks">' + L.map(function (l) { return '<a class="abtn ghost" target="_blank" rel="noopener" href="' + esc(l[0]) + '">' + l[1] + " ↗</a>"; }).join("") + "</p>"; }

  VIEWS.seo = function (p) {
    var sx = S.admin.seo || {}, tr = S.admin.track || {};
    var parts = [["ইনডেক্স ও সাইটম্যাপ", sx.sitemap_urls ? 18 : 0, 20], ["ডুপ্লিকেট শিরোনাম", !sx.dup_titles ? 15 : sx.dup_titles < 100 ? 11 : 6, 15],
      ["Structured data", 18, 20], ["AI-বান্ধব কন্টেন্ট", 14, 15], ["ব্র্যান্ড ও ছবি", (sx.no_brand || 0) < 100 ? 10 : 7, 10],
      ["robots.txt ও ডোমেইন", 3, 10], ["Search Console", tr.gsc ? 10 : 0, 10]];
    var score = parts.reduce(function (a, x) { return a + x[1]; }, 0), max = parts.reduce(function (a, x) { return a + x[2]; }, 0);
    score = Math.round(score / max * 100);
    var col = score >= 80 ? "var(--best)" : score >= 60 ? "var(--accent)" : "var(--warn)";
    p.innerHTML =
      '<div class="ag2 score">' +
        card("SEO স্কোর", "আজকের বিল্ড থেকে", '<div class="ascore"><svg viewBox="0 0 120 120" width="116" height="116" role="img" aria-label="স্কোর ' + score + '"><circle cx="60" cy="60" r="50" fill="none" stroke="var(--line)" stroke-width="12"/><circle cx="60" cy="60" r="50" fill="none" stroke="' + col + '" stroke-width="12" stroke-linecap="round" stroke-dasharray="' + (score / 100 * 314) + ' 314" transform="rotate(-90 60 60)"/><text x="60" y="68" text-anchor="middle" font-size="28" font-weight="700" fill="currentColor" font-family="JetBrains Mono,monospace">' + bn(score) + "</text></svg>" +
          '<div class="aparts">' + parts.map(function (x) { return "<div><span>" + x[0] + "</span><b>" + bn(x[1]) + "/" + bn(x[2]) + "</b></div>"; }).join("") + "</div></div>") +
        '<div class="akpis k3">' + kpi("Google-কে দেখানো পাতা", bn(sx.sitemap_urls), "সাইটম্যাপে", "seo-sitemap") + kpi("লুকানো (noindex)", bn(sx.noindex), "স্টকে নেই, পাতা আছে", "seo-index") +
          kpi("আজ বদলানো পাতা", bn(sx.changed_today), "IndexNow-এ যায়", "seo-sitemap") + kpi("ডুপ্লিকেট শিরোনাম", bn(sx.dup_pages), bn(sx.dup_titles) + "টি গ্রুপ", "seo-meta") +
          kpi("এক দোকানের প্রোডাক্ট", bn(sx.single_store), "তুলনা নেই, দুর্বল পাতা", "products", "sg") + kpi("স্পেকসহ পাতা", bn(sx.with_specs), "বিস্তারিত তথ্যসহ", "dash") + "</div>" +
      "</div>" +
      card("সমস্যা ও করণীয়", "গুরুত্ব অনুযায়ী", '<div class="seolist">' +
        srow("warn", "robots.txt Google পড়তে পারছে না", "সাইট github.io-এর ভেতরের ফোল্ডারে; robots.txt থাকতে হয় ডোমেইনের গোড়ায়। নিজের ডোমেইনে গেলে ঠিক হবে। ততদিন Search Console-এ sitemap.xml হাতে জমা দিন।", "seo-sitemap") +
        (tr.gsc ? "" : srow("warn", "Google Search Console যুক্ত হয়নি", "কতগুলো পাতা আসলে ইনডেক্স হয়েছে, কোন শব্দে মানুষ আসে, তা জানা যাচ্ছে না।", "settings")) +
        (sx.dup_titles ? srow("warn", bn(sx.dup_pages) + "টি পাতার শিরোনাম হুবহু এক", "একই প্রোডাক্ট দুইবার তালিকায় (নামের শেষে -2, -3)। মিলিয়ে দিলে ঠিক হবে।", "seo-meta") : "") +
        (sx.no_brand ? srow("info", bn(sx.no_brand) + "টি প্রোডাক্টে ব্র্যান্ড পাওয়া যায়নি", "জানা থাকলে \"ব্র্যান্ড\" পাতার নিচে হাতে বসান; ব্র্যান্ড না থাকলে \"ব্র্যান্ড নেই\" চিহ্ন দিন।", "brands")
          : srow("ok", "সব প্রোডাক্টের ব্র্যান্ড ঠিক আছে", (sx.unbranded ? bn(sx.unbranded) + "টি সাধারণ ব্র্যান্ডহীন পণ্য (কাগজের রোল, সাধারণ ল্যাপটপ ডিসপ্লে ইত্যাদি), এগুলোর ব্র্যান্ড লাগে না। " : "") +
            (sx.compat ? bn(sx.compat) + "টি ল্যাপটপ পার্ট \"কোন ল্যাপটপের জন্য\" হিসেবে চিহ্নিত।" : ""), "brands")) +
        srow(sx.long_titles ? "info" : "ok", sx.long_titles ? bn(sx.long_titles) + "টি শিরোনাম ৭০ অক্ষরের বেশি" : "সব শিরোনাম ৭০ অক্ষরের মধ্যে",
          sx.long_titles ? "একই নামের প্রোডাক্ট আলাদা করতে পুরো নাম লেগেছে।" : "লম্বা নাম শিরোনামে ছোট করা হয় (দোকান-কোড বাদ, শব্দের মাঝে কাটা হয় না); পুরো নাম পাতার শিরোনামে (H1) থাকে।") +
        srow("ok", "প্রতিটা পাতায় সংক্ষিপ্ত উত্তর, তারিখ আর Product/Offer স্কিমা আছে", "Google AI Overview আর AI চ্যাটবট এক বাক্যেই দাম, দোকান আর তারিখ পায়।") +
        srow(sx.indexnow ? "ok" : "warn", "IndexNow " + (sx.indexnow ? "চালু" : "বন্ধ"), "প্রতিদিন বদলানো পাতা Bing/Yandex-কে জানানো হয় (ChatGPT সার্চ Bing ব্যবহার করে)।", sx.indexnow ? "" : "seo-sitemap") +
      "</div>");
    return Promise.resolve();
  };

  VIEWS["seo-meta"] = function (p) {
    var sx = S.admin.seo || {};
    var VP = ["{name}", "{price}", "{store}", "{stores}", "{brand}", "{cat}", "{year}", "{month}", "{date}"], VC = ["{cat}", "{cat_en}", "{count}", "{low}", "{high}", "{stores}", "{year}", "{month}"];
    function chips(list, target) { return '<div class="seochips">' + list.map(function (v) { return '<button type="button" class="seochip" data-ins="' + target + '" data-v="' + v + '">' + v + "</button>"; }).join("") + "</div>"; }
    p.innerHTML = '<div class="ag2 eq">' +
      card("প্রোডাক্ট পাতা", "Google-এর নীল শিরোনাম আর ধূসর বিবরণ",
        fld("title_product", "শিরোনাম", "", "text", "", ' id="t_tp"') + chips(VP, "t_tp") +
        fld("title_product_oos", "শিরোনাম (স্টকে না থাকলে)", "", "text", "", ' id="t_tpo"') +
        fld("desc_product", "বিবরণ (ফাঁকা = দামের বিশ্লেষণ থেকে স্বয়ংক্রিয়)", "", "textarea", "", ' id="t_dp" rows="2"') + chips(VP, "t_dp") + '<div class="serp" id="serp_p"></div>') +
      card("ক্যাটাগরি পাতা", "",
        fld("title_category", "শিরোনাম", "", "text", "", ' id="t_tc"') + chips(VC, "t_tc") +
        fld("desc_category", "বিবরণ (ফাঁকা = স্বয়ংক্রিয় সারাংশ)", "", "textarea", "", ' id="t_dc" rows="2"') + chips(VC, "t_dc") + '<div class="serp" id="serp_c"></div>') +
      "</div>" +
      (sx.dup_samples && sx.dup_samples.length ? card("একই শিরোনামের পাতা", bn(sx.dup_titles) + "টি গ্রুপ · \"প্রোডাক্ট মিল\"-এ মিলিয়ে দিলে ঠিক হবে",
        '<div class="ascroll"><table><tr><th>শিরোনাম</th><th>পাতা</th></tr>' + sx.dup_samples.map(function (d) {
          return "<tr><td>" + esc(d[0]) + "</td><td>" + d[1].map(function (id) { return '<a href="' + BASE + "/p/" + esc(id) + '/" target="_blank" style="text-decoration:underline">' + esc(id) + "</a>"; }).join("<br>") + "</td></tr>"; }).join("") + "</table></div>") : "");
    var ex = { name: "Logitech C270 HD Webcam", price: "৳1,999", store: "TechLand BD", stores: "৯", brand: "Logitech", cat: "স্মার্টফোন", cat_en: "Smartphone",
               count: "৩০৭", low: "৳13,300", high: "৳549,999", year: "২০২৬", month: "নভেম্বর", date: "১২ নভেম্বর ২০২৬" };
    function fill(t) { return String(t || "").replace(/\{(\w+)\}/g, function (_, k) { return ex[k] || ""; }); }
    function box(url, t, d) { return '<small class="serpl">Google-এ যেমন দেখাবে</small><div class="serpu">' + esc(url) + '</div><div class="serpt">' + esc(t.length > 62 ? t.slice(0, 60) + "…" : t) + '</div><div class="serpd">' + esc(d.length > 158 ? d.slice(0, 155) + "…" : d) + "</div>" +
      (t.length > 62 ? '<small class="serpw">শিরোনাম ' + bn(t.length) + " অক্ষর; ৬০-এর পরে কাটা যায়</small>" : ""); }
    p.addEventListener("click", function (e) {
      var c = e.target.closest("[data-ins]"); if (!c) return;
      var inp = document.getElementById(c.dataset.ins), pos = inp.selectionStart == null ? inp.value.length : inp.selectionStart;
      inp.value = inp.value.slice(0, pos) + c.dataset.v + inp.value.slice(inp.selectionEnd || pos); inp.focus();
      inp.dispatchEvent(new Event("input", { bubbles: true }));
    });
    var host = SITE.replace(/^https?:\/\//, "");
    return seoBind(p, "seo-meta", function (cfg) {
      $("#serp_p").innerHTML = box(host + " › p › logitech-c270-hd-webcam", fill(cfg.title_product), cfg.desc_product ? fill(cfg.desc_product) : "Logitech C270 HD Webcam: আজ ৯ দোকানে, সর্বনিম্ন ৳১,৯৯৯ (TechLand BD)।");
      $("#serp_c").innerHTML = box(host + " › c › smartphone", fill(cfg.title_category), cfg.desc_category ? fill(cfg.desc_category) : "আজ বাংলাদেশে ৩০৭টি স্মার্টফোন কেনা যাচ্ছে; দাম ৳13,300 থেকে ৳549,999…");
    });
  };

  VIEWS["seo-index"] = function (p) {
    var sx = S.admin.seo || {};
    p.innerHTML = '<div class="ag2 eq">' +
      card("ইনডেক্সের নিয়ম", "কোন পাতা Google দেখবে",
        '<div class="anote">কোনো দোকানে স্টকে থাকলে বা শীঘ্রই আসছে হলে পাতা Google-এ দেখানো হয়। সব দোকানে শেষ হলে পরের দিন থেকে লুকানো (পাতা থাকে, লিংক ভাঙে না, "স্টকে এলে জানান" কাজ করে)। নিচের দিন পার হলে পাতাটা ক্যাটাগরিতে পাঠানো হয়।</div>' +
        fld("gone_days", "কত দিন কোথাও না থাকলে পাতা সরানো হবে", "", "number", "সর্বনিম্ন ১৪, প্রস্তাবিত ৯০", ' min="14" max="730"') +
        '<dl class="adl"><div><dt>এখন Google-এ দেখানো প্রোডাক্ট</dt><dd>' + bn(sx.indexable) + "</dd></div><div><dt>লুকানো (স্টকে নেই)</dt><dd>" + bn(sx.noindex) + "</dd></div><div><dt>সরানো (ক্যাটাগরিতে পাঠানো)</dt><dd>" + bn(sx.gone || 0) + "</dd></div></dl>") +
      card("হাতে নিয়ন্ত্রণ", "নির্দিষ্ট পাতা",
        fld("force_index", "সবসময় Google-এ দেখান (স্টকে না থাকলেও)", "", "textarea", "প্রতি লাইনে একটা প্রোডাক্টের লিংক বা আইডি। যেমন জনপ্রিয় ফোন যা আবার আসবে।", ' rows="4"') +
        fld("force_noindex", "কখনো Google-এ দেখাবেন না", "", "textarea", "প্রতি লাইনে একটা লিংক বা আইডি। পাতা থাকবে, শুধু সার্চে আসবে না।", ' rows="4"')) +
      "</div>" +
      card("রিডাইরেক্ট", "পুরনো ঠিকানা → নতুন পাতা (স্বয়ংক্রিয়)", '<div class="seolist">' +
        srow("ok", "মেলানো প্রোডাক্ট", "দুটো পাতা এক করলে পুরনোটা নিজে থেকে নতুনটায় যায়। এখন " + bn((S.admin.auto_merges || []).length) + "+টি স্বয়ংক্রিয় মিল।", "") +
        srow("ok", "অনেক দিন স্টকে নেই এমন প্রোডাক্ট", "উপরের দিন পার হলে পাতাটা তার ক্যাটাগরিতে পাঠানো হয়।", "") + "</div>");
    return seoBind(p, "seo-index");
  };

  VIEWS["seo-sitemap"] = function (p) {
    var sx = S.admin.seo || {}, prod = (sx.sitemap_urls || 0) - (sx.pages || 0);
    p.innerHTML = '<div class="ag2 eq">' +
      card("সাইটম্যাপ", "প্রতিদিন নিজে তৈরি হয়", '<div class="ascroll"><table><tr><th>ফাইল</th><th class="n">ঠিকানা</th></tr>' +
        '<tr><td>sitemap.xml <span class="atag">সূচি</span></td><td class="n">' + bn(1 + Math.ceil(prod / 20000)) + " ফাইল</td></tr>" +
        "<tr><td>sitemap-pages.xml</td><td class=\"n\">" + bn(sx.pages) + "</td></tr>" +
        Array.apply(null, Array(Math.ceil(prod / 20000))).map(function (_, k) { return "<tr><td>sitemap-products-" + (k + 1) + '.xml</td><td class="n">' + bn(Math.min(20000, prod - k * 20000)) + "</td></tr>"; }).join("") +
        "</table></div><p class=\"muted\" style=\"font-size:.82rem;margin:8px 0 0\">শুধু কেনা যায় এমন পাতা; প্রতিটায় শেষ দাম বদলের তারিখ (lastmod)।</p>" +
        linkBtns([[SITE + "/sitemap.xml", "সাইটম্যাপ দেখুন"], ["https://search.google.com/search-console/sitemaps?resource_id=" + encodeURIComponent(SITE + "/"), "Search Console-এ জমা দিন"]])) +
      card("IndexNow", "বদলানো পাতা সাথে সাথে জানানো",
        tog("indexnow", "IndexNow চালু", false) +
        '<p class="muted" style="font-size:.82rem;margin:6px 0 0">Bing, Yandex, Seznam, Naver পায়। ChatGPT-র সার্চ Bing-এর তথ্য ব্যবহার করে। Google IndexNow নেয় না, তার জন্য সাইটম্যাপ। প্রতিদিন দাম আনার পর নিজে চলে; আজ বদলানো পাতা: ' + bn(sx.changed_today) + "।</p>" +
        linkBtns([["https://www.bing.com/webmasters", "Bing Webmaster"]])) +
      "</div>" +
      card("robots.txt", "", '<div class="anote warn">এখন সাইট <b>' + esc(SITE.replace(/^https?:\/\//, "")) + "</b>-এ, তাই আমাদের robots.txt Google পড়ে না (robots.txt থাকতে হয় ডোমেইনের গোড়ায়)। নিজের ডোমেইনে গেলে এই নিয়মগুলো কাজ করবে:</div>" +
        '<pre class="acode">User-agent: *\nDisallow: /admin/\nDisallow: /search/\nSitemap: https://&lt;আপনার-ডোমেইন&gt;/sitemap.xml</pre>');
    return seoBind(p, "seo-sitemap");
  };

  VIEWS["seo-schema"] = function (p) {
    var sx = S.admin.seo || {}, u = sampleUrl();
    var R = [["Product + Offer (প্রতি দোকান)", "প্রোডাক্ট পাতা", sx.indexable, 1, "দাম, দোকান, স্টক"], ["AggregateOffer", "প্রোডাক্ট পাতা", sx.indexable, 1, "সর্বনিম্ন–সর্বোচ্চ দাম"],
      ["isAccessoryOrSparePartFor", "ল্যাপটপ পার্টস", sx.compat || 0, 1, "কোন ল্যাপটপের পার্ট"], ["BreadcrumbList", "সব পাতা", sx.sitemap_urls, 1, "ফলাফলে পথ দেখায়"],
      ["ItemList", "ক্যাটাগরি", null, 1, "তালিকার প্রোডাক্ট"], ["WebSite + Organization", "হোম", 1, 1, "সাইটের পরিচয়"],
      ["FAQPage", "—", 0, 0, "জুন ২০২৬ থেকে Google দেখায় না"], ["Review / Rating", "—", 0, 0, "আসল রিভিউ নেই, বানানো রিভিউ দেওয়া নিষেধ"]];
    p.innerHTML = card("Structured data", "Google ও AI যে যন্ত্র-পাঠ্য তথ্য পড়ে", '<div class="ascroll"><table><tr><th>ধরন</th><th>কোথায়</th><th class="n">পাতা</th><th>অবস্থা</th><th>কী দেয়</th></tr>' +
        R.map(function (r) { return "<tr><td><b>" + r[0] + "</b></td><td>" + r[1] + '</td><td class="n">' + (r[2] ? bn(r[2]) : "—") + "</td><td>" + (r[3] ? '<span class="atag ok">চালু</span>' : '<span class="atag off">বন্ধ</span>') + '</td><td class="muted">' + r[4] + "</td></tr>"; }).join("") + "</table></div>") +
      card("যাচাই", "নমুনা পাতা: " + esc(sx.sample || ""), linkBtns([["https://search.google.com/test/rich-results?url=" + encodeURIComponent(u), "Rich Results Test"], ["https://validator.schema.org/#url=" + encodeURIComponent(u), "Schema যাচাই"]]) +
        (sx.no_brand ? '<p class="muted" style="font-size:.82rem;margin:8px 0 0">' + bn(sx.no_brand) + "টি Product-এ brand নেই (বাধ্যতামূলক নয়)।</p>" : ""));
    return Promise.resolve();
  };

  VIEWS["seo-ai"] = function (p) {
    var sx = S.admin.seo || {};
    var B = [["Googlebot", "Google সার্চ ও AI Overview", 1], ["Bingbot", "Bing ও ChatGPT সার্চ", 1], ["OAI-SearchBot", "ChatGPT সার্চে উৎস দেখানো", 1], ["PerplexityBot", "Perplexity উত্তরে উৎস", 1],
      ["Claude-SearchBot", "Claude-এর উত্তরে উৎস", 1], ["Google-Extended", "Gemini মডেল প্রশিক্ষণ", 0], ["GPTBot", "OpenAI মডেল প্রশিক্ষণ", 0], ["ClaudeBot", "Anthropic মডেল প্রশিক্ষণ", 0], ["CCBot", "Common Crawl", 0]];
    p.innerHTML = '<div class="ag2 eq">' +
      card("AI কতটা উদ্ধৃত করতে পারবে", "Google AI Overview, AI Mode ও ফলাফল",
        '<div class="af"><select data-k="ai_snippet"><option value="full">পুরোটা (প্রস্তাবিত): দাম ও তথ্য উদ্ধৃত হতে পারবে, উৎস হিসেবে লিংক আসে</option>' +
        '<option value="limited">সীমিত: ১৬০ অক্ষর পর্যন্ত</option><option value="none">কিছুই না (nosnippet): বিবরণ দেখাবে না, ভিজিটর কমবে</option></select></div>' +
        '<p class="muted" style="font-size:.8rem;margin:0">এখন: <code>' + esc(sx.robots || "") + "</code></p>") +
      card("AI-বান্ধব কন্টেন্ট", "সাইটে যা চালু আছে", '<div class="seolist">' +
        srow("ok", "পাতার শুরুতে সংক্ষিপ্ত উত্তর", "আজকের তারিখ, সর্বনিম্ন দাম, দোকান, পরিসীমা, ৩০ দিনের সর্বনিম্ন") +
        srow("ok", "ক্যাটাগরিতে সারাংশ ও দামের তালিকা (টেবিল)", "AI টেবিল থেকে সবচেয়ে ভালো তথ্য তোলে") +
        srow("ok", "প্রতিটা পাতায় শেষ আপডেটের তারিখ", "তাজা তথ্যকে AI অগ্রাধিকার দেয়") +
        srow("ok", "\"আমাদের সম্পর্কে\"-তে পদ্ধতি ও উদ্ধৃতির নিয়ম", "বিশ্বাসযোগ্যতার সংকেত") + "</div>") +
      "</div>" +
      card("AI ক্রলার", "কোন AI আমাদের সাইট পড়ে", '<div class="anote">এখন সব ক্রলার সাইট পড়তে পারে। আলাদা করে আটকানোর নিয়ম robots.txt-এ বসে, তাই নিজের ডোমেইনে যাওয়ার পর এখান থেকে চালু/বন্ধ করা যাবে। পরামর্শ: যেগুলো ভিজিটর আনে সেগুলো খোলা রাখুন। llms.txt ফাইল Google ব্যবহার করে না।</div>' +
        '<div class="ascroll"><table><tr><th>ক্রলার</th><th>কাজ</th><th>ভিজিটর আনে?</th></tr>' + B.map(function (b) { return "<tr><td><code>" + b[0] + "</code></td><td>" + b[1] + "</td><td>" + (b[2] ? '<span class="atag ok">হ্যাঁ, উৎস লিংক</span>' : '<span class="atag off">না, শুধু প্রশিক্ষণ</span>') + "</td></tr>"; }).join("") + "</table></div>");
    return seoBind(p, "seo-ai");
  };

  VIEWS["seo-content"] = function (p) {
    var cats = (S.admin.categories || []).filter(function (c) { return !c.hidden && c.count; }).sort(function (a, b) { return b.count - a.count; }).slice(0, 12);
    p.innerHTML = card("গতি (Core Web Vitals)", "Google-এর লক্ষ্য", '<div class="akpis k3">' +
        [["LCP", "বড় অংশ দেখাতে সময়", "≤ ২.৫ সেকেন্ড"], ["INP", "চাপলে সাড়া দিতে সময়", "≤ ২০০ মি.সে."], ["CLS", "লেআউট নড়াচড়া", "≤ ০.১"]].map(function (m) { return '<div class="akpi"><span class="l">' + m[1] + '</span><span class="v">' + m[0] + '</span><span class="d">লক্ষ্য ' + m[2] + "</span></div>"; }).join("") + "</div>" +
        '<p class="muted" style="font-size:.84rem;margin:10px 0">এখনো স্বয়ংক্রিয়ভাবে মাপা হয় না। নিচের বোতামে এখনই মেপে দেখুন; Search Console যুক্ত হলে আসল ভিজিটরের মাপ সেখানে আসবে।</p>' +
        linkBtns([["https://pagespeed.web.dev/analysis?url=" + encodeURIComponent(SITE + "/"), "হোম পেজ মাপুন"], ["https://pagespeed.web.dev/analysis?url=" + encodeURIComponent(sampleUrl()), "প্রোডাক্ট পাতা মাপুন"]])) +
      card("বড় ক্যাটাগরিগুলো", "সারাংশ আর দামের তালিকা নিজে তৈরি হয়", '<div class="ascroll"><table><tr><th>ক্যাটাগরি</th><th class="n">প্রোডাক্ট</th><th></th></tr>' + cats.map(function (c) {
        return "<tr><td>" + esc(c.name_bn) + '</td><td class="n">' + bn(c.count) + '</td><td><a class="abtn ghost sm" target="_blank" href="' + BASE + "/c/" + esc(c.slug) + '/">দেখুন ↗</a></td></tr>'; }).join("") + "</table></div>");
    return Promise.resolve();
  };

  window.addEventListener("hashchange", function () { var t = location.hash.slice(1); if (VIEWS[t] && t !== S.tab && S.admin) show(t); });

  /* ---------- শুরু ---------- */
  fetch(BASE + "/admin/admin.json", { cache: "no-store" }).then(function (r) { return r.json(); }).then(function (a) {
    S.admin = a;
    counts();
    S.token = lsGet(TKEY);
    var start = (location.hash || "#dash").slice(1);
    if (S.token) {
      checkToken().then(function (ok) { if (!ok) { S.token = null; lsSet(TKEY, null); } renderAuth(); show(start); });
    } else { renderAuth(); show(start); }
  }).catch(function (e) { $("#panel").innerHTML = '<section class="card"><p class="aempty">অ্যাডমিন ডাটা লোড হয়নি: ' + esc(e.message) + "</p></section>"; });
})();
