/* দামতুলনা অ্যাডমিন প্যানেল
   সাইট স্ট্যাটিক (GitHub Pages), তাই আলাদা সার্ভার নেই। প্যানেল আপনার GitHub টোকেন দিয়ে সরাসরি রিপোর
   config/ ফাইল বদলায় ও কাজ (workflow) চালায়। টোকেন শুধু এই ব্রাউজারে থাকে, কোথাও পাঠানো হয় না (GitHub ছাড়া)। */
(function () {
  "use strict";
  var root = document.getElementById("adm");
  var REPO = root.dataset.repo, BASE = root.dataset.base;
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
    var box = $("#authbox");
    if (S.user) {
      box.innerHTML = '<p style="margin:10px 0 0;font-size:.86rem">✅ <b>' + esc(S.user) + '</b> হিসেবে সংযুক্ত। এখান থেকে সব পরিবর্তন করা যাবে। <button type="button" class="abtn ghost" id="logout" style="min-height:32px;margin-left:6px">বিচ্ছিন্ন করুন</button></p>';
      $("#logout").onclick = function () { if (confirm("এই ব্রাউজার থেকে টোকেন মুছে দেবেন?")) { lsSet(TKEY, null); location.reload(); } };
      return;
    }
    box.innerHTML =
      '<div class="anote" style="margin-top:12px"><span class="ro-badge">শুধু দেখা যাবে</span> পরিবর্তন করতে GitHub টোকেন দিয়ে সংযুক্ত করুন। কীভাবে বানাবেন, "সেটিং" ট্যাবে ধাপে ধাপে লেখা আছে।</div>' +
      '<div class="af"><label for="tok">GitHub টোকেন</label><input type="text" id="tok" autocomplete="off" spellcheck="false" placeholder="github_pat_…">' +
      '<small>টোকেন শুধু এই ব্রাউজারে সেভ থাকবে। কাউকে দেবেন না, চ্যাটেও পাঠাবেন না।</small></div>' +
      '<button type="button" class="abtn" id="login">সংযুক্ত করুন</button>';
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
    var b = e.target.closest("[data-tab]"); if (!b || b.dataset.tab === S.tab) return;
    if (S.dirty[S.tab]) {
      if (confirm("এই ট্যাবে সেভ না করা পরিবর্তন আছে। এখনই সেভ করবেন?\n(বাতিল চাপলে পরিবর্তনগুলো মুছে যাবে)")) {
        var go = b.dataset.tab; $("#savebtn").click(); var w = setInterval(function () { if (!S.dirty[S.tab] && !$("#savebtn").disabled) { clearInterval(w); show(go); } }, 300);
        return;
      }
      clearDirty(S.tab); S.files = {};
    }
    show(b.dataset.tab);
  });
  function show(tab) {
    S.tab = tab;
    $$("#tabs [data-tab]").forEach(function (b) { b.setAttribute("aria-selected", b.dataset.tab === tab); });
    try { history.replaceState(null, "", "#" + tab); } catch (e) {}
    var old = $("#panel"), p = old.cloneNode(false);  // নতুন এলিমেন্ট: আগের ট্যাবের ইভেন্ট লিসেনার যেন না থাকে
    old.replaceWith(p);
    p.innerHTML = '<section class="card"><p class="aempty">লোড হচ্ছে…</p></section>';
    clearInterval(S.runTimer);
    (VIEWS[tab] || VIEWS.dash)(p).catch(function (e) {
      p.innerHTML = '<section class="card"><p class="aempty" style="color:var(--warn)">লোড হয়নি: ' + esc(e.message) + "</p></section>";
    });
  }
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
  VIEWS.dash = function (p) {
    var a = S.admin, st = a.stats, h = a.health;
    p.innerHTML =
      '<div class="astats">' +
        '<div class="astat"><b>' + bn(st.total) + '</b><span>মোট প্রোডাক্ট</span></div>' +
        '<div class="astat"><b>' + bn(st.multi) + '</b><span>একাধিক স্টোরে দাম</span></div>' +
        '<div class="astat"><b>' + bn(st.details) + '</b><span>স্পেক ও ওয়ারেন্টিসহ</span></div>' +
        '<div class="astat"><b>' + bn(a.suggestions.length) + '</b><span>মিল যাচাই বাকি</span></div>' +
      '</div>' +
      '<section class="card"><h2>কাজ চালান</h2><div class="aacts">' +
        '<div class="aact"><div><b>দাম আপডেট এখনই</b><small>সব স্টোর থেকে দাম তুলে সাইট আপডেট। ১-২ ঘণ্টা লাগে। এমনিতে প্রতি রাতে ২:১৭-এ নিজে চলে।</small></div><button class="abtn" data-run="daily.yml">চালান</button></div>' +
        '<div class="aact"><div><b>স্পেক ও ওয়ারেন্টি সংগ্রহ</b><small>কতগুলো প্রোডাক্টের (দিনে ৬০০-এর বেশি দিলে Star Tech আটকে দিতে পারে)</small><input type="number" id="dlimit" value="600" min="50" max="5000" aria-label="প্রোডাক্টের সংখ্যা"></div><button class="abtn" data-run="details.yml">চালান</button></div>' +
        '<div class="aact"><div><b>সাইট আবার প্রকাশ</b><small>দাম না তুলে বর্তমান ডাটা দিয়ে ২ মিনিটে সাইট আপডেট</small></div><button class="abtn" data-run="deploy-now.yml">চালান</button></div>' +
        '<div class="aact"><div><b>স্টোরের লোগো আবার আনা</b><small>স্টোরের ওয়েবসাইট থেকে লোগো খুঁজে আনে</small></div><button class="abtn ghost" data-run="logos.yml">চালান</button></div>' +
      '</div></section>' +
      '<section class="card"><h2>সাম্প্রতিক কাজ <span class="sub">· নিজে থেকে রিফ্রেশ হয়</span></h2><div class="aruns" id="runs"><p class="aempty">লোড হচ্ছে…</p></div></section>' +
      '<section class="card"><h2>স্টোরের অবস্থা <span class="sub">· শেষ সংগ্রহ ' + esc(h.scraped_at || "") + '</span></h2><div class="ascroll"><table><tr><th>স্টোর</th><th>অফার</th><th>সময়</th><th>অবস্থা</th></tr>' +
        Object.keys(h.stores || {}).map(function (k) { var x = h.stores[k];
          return "<tr><td><b>" + esc(k) + "</b>" + (x.enabled ? "" : ' <span class="ro-badge">বন্ধ</span>') + "</td><td>" + bn(x.items) + "</td><td>" + bn(Math.round((x.seconds || 0) / 60)) + " মি.</td><td>" +
            (x.errors && x.errors.length ? x.errors.map(function (e) { return '<div style="color:var(--warn)">' + esc(e) + "</div>"; }).join("") : '<span style="color:var(--best)">ঠিক আছে</span>') + "</td></tr>"; }).join("") +
      "</table></div></section>" +
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
    return Promise.resolve();
  };

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
      function draw() {
        if (cur) { p.innerHTML = editHTML(cur); return; }
        p.innerHTML = '<section class="card"><h2>ব্র্যান্ড</h2><p class="muted" style="margin:0;font-size:.84rem">' + bn(list.length) + "টি ব্র্যান্ড, এর মধ্যে " +
          bn(list.filter(function (b) { return b.k >= min; }).length) + "টির নিজের পাতা আছে (অন্তত " + bn(min) + "টি প্রোডাক্ট)। পরিচিতি, অফিসিয়াল লিংক আর লোগো যোগ করুন, ভুল বানান এক করুন।</p>" +
          '<div class="af"><input type="search" id="bq" placeholder="ব্র্যান্ড খুঁজুন…"></div><div id="blist">' + listHTML("") + "</div></section>";
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
      function draw() {
        var sug = S.admin.suggestions.filter(function (s) { return mm.not_same.indexOf(pairKey(s.a, s.b)) < 0; });
        p.innerHTML =
          '<section class="card"><h2>প্রোডাক্ট লুকান</h2><p class="muted" style="margin:0;font-size:.84rem">ভুল বা অপ্রয়োজনীয় প্রোডাক্ট খুঁজে সাইট থেকে লুকান।</p>' +
            '<div class="af"><input type="search" id="pq" placeholder="প্রোডাক্টের নাম লিখুন…"></div><div class="rows" id="pres"></div>' +
            (mm.ignore.length ? '<h3 style="font-size:.9rem;margin:14px 0 4px">লুকানো আছে (' + bn(mm.ignore.length) + ")</h3>" +
              mm.ignore.map(function (id) { return '<div class="apair"><div class="nm">' + esc(nm(id)) + '</div><div class="bt"><button type="button" class="abtn ghost" data-unhide="' + esc(id) + '">ফিরিয়ে আনুন</button></div></div>'; }).join("") : "") +
          "</section>" +
          (function () {
            var pc = (S.admin.price_checks || []).filter(function (x) { return x.o.some(function (o) { return o[3] && !decided(x.id, o[0]); }); });
            if (!pc.length) return "";
            return '<section class="card"><h2>সন্দেহজনক দাম <span class="sub">· ' + bn(pc.length) + "টি</span></h2>" +
              '<p class="muted" style="margin:0;font-size:.84rem">এসব প্রোডাক্টে স্টোরগুলোর দামে অস্বাভাবিক ফারাক (দেড় গুণের বেশি)। চিহ্নিত দাম এখন সর্বনিম্ন দাম ও সাশ্রয়ের হিসাবে ধরা হচ্ছে না। ' +
              '<b>দাম ঠিক</b> চাপলে আবার ধরা হবে; <b>মিল ভুল</b> চাপলে ওই স্টোরের দাম এই পাতা থেকে সরে যাবে।</p>' +
              pc.slice(0, 60).map(function (x) {
                return '<div class="apair"><div class="nm"><a href="' + BASE + "/p/" + esc(x.id) + '/" target="_blank" style="text-decoration:underline">' + esc(x.n) + "</a><br><span>" + esc(x.c) + "</span>" +
                  x.o.map(function (o) {
                    var k = x.id + "|" + o[0], st = decided(x.id, o[0]);
                    return '<div class="apc' + (o[3] ? " sus" : "") + '"><span>' + esc(o[1]) + " · <b>৳" + Number(o[2]).toLocaleString("en-IN") + "</b></span>" +
                      (!o[3] ? "" : st ? '<span class="muted" style="font-size:.78rem">' + (st === "ok" ? "✓ দাম ঠিক" : "✓ সরানো হবে") + "</span>"
                        : '<span><button type="button" class="abtn ok" data-pok="' + esc(k) + '">দাম ঠিক</button><button type="button" class="abtn warn" data-pdrop="' + esc(k) + '">মিল ভুল</button></span>') + "</div>";
                  }).join("") + "</div></div>";
              }).join("") + "</section>";
          })() +
          (function () {
            var am = S.admin.auto_merges || [];
            if (!am.length) return "";
            return '<section class="card"><h2>স্বয়ংক্রিয় মিল <span class="sub">· ' + bn(am.length) + "টি</span></h2>" +
              '<p class="muted" style="margin:0;font-size:.84rem">মডেল নম্বর, ব্র্যান্ড আর ক্যাপাসিটি এক হওয়ায় এগুলো নিজে থেকে এক পাতায় জোড়া লাগানো হয়েছে। ভুল হলে <b>আলাদা</b> চাপুন, পরের আপডেটে আলাদা হয়ে যাবে।</p>' +
              '<div class="af"><input type="search" id="amq" placeholder="নাম দিয়ে খুঁজুন…"></div><div id="amres"></div></section>';
          })() +
          '<section class="card"><h2>সম্ভাব্য একই প্রোডাক্ট <span class="sub">· ' + bn(sug.length) + "টি</span></h2>" +
            '<p class="muted" style="margin:0;font-size:.84rem">দুই স্টোরে একই জিনিস আলাদা নামে থাকলে মিলিয়ে দিন, তাহলে এক পাতায় দুই দামের তুলনা দেখাবে। <b>Tray</b> আর <b>Box</b> প্রসেসর, বা আলাদা রঙ/সাইজ হলে "আলাদা" চাপুন।</p>' +
            sug.slice(0, 80).map(function (s) {
              var done = merged(s.a, s.b);
              return '<div class="apair' + (done ? " done" : "") + '"><div class="nm">' + esc(s.a_name) + '<br><span>↕ মিলের হার ' + bn(Math.round(s.score * 100)) + "%</span><br>" + esc(s.b_name) + "</div>" +
                '<div class="bt">' + (done ? '<span class="muted" style="font-size:.82rem">✓ মিলানো হয়েছে</span> <button type="button" class="abtn ghost" data-unmerge="' + esc(s.a) + "|" + esc(s.b) + '">বাতিল</button>'
                  : '<button type="button" class="abtn ok" data-merge="' + esc(s.a) + "|" + esc(s.b) + '">একই, মিলান</button><button type="button" class="abtn ghost" data-notsame="' + esc(pairKey(s.a, s.b)) + '">আলাদা</button>') + "</div></div>";
            }).join("") + "</section>";
        var amq = $("#amq");
        function drawAm() {
          var am = S.admin.auto_merges || [], w = (amq.value || "").toLowerCase();
          var rows = am.filter(function (x) { return !w || (x[1] + " " + x[3]).toLowerCase().indexOf(w) > -1; }).slice(0, 40);
          $("#amres").innerHTML = rows.map(function (x) {
            var k = pairKey(x[0], x[2]), no = mm.not_same.indexOf(k) > -1;
            return '<div class="apair' + (no ? " done" : "") + '"><div class="nm">' + esc(x[1]) + "<br><span>↕ একই পাতায়</span><br>" + esc(x[3]) + "</div>" +
              '<div class="bt">' + (no ? '<span class="muted" style="font-size:.82rem">✓ আলাদা করা হবে</span>' : '<button type="button" class="abtn ghost" data-notsame="' + esc(k) + '">আলাদা</button>') +
              '<a class="abtn ghost" style="display:inline-flex;align-items:center" href="' + BASE + "/p/" + esc(x[2]) + '/" target="_blank">দেখুন</a></div></div>';
          }).join("");
        }
        if (amq) { amq.addEventListener("input", drawAm); drawAm(); }
        $("#pq").addEventListener("input", function () {
          var t = this.value.toLowerCase().split(/\s+/).filter(Boolean), out = $("#pres");
          if (!t.length) { out.innerHTML = ""; return; }
          var hits = list.filter(function (x) { var n = (x.n + " " + x.c).toLowerCase(); return t.every(function (w) { return n.indexOf(w) > -1; }); }).slice(0, 12);
          out.innerHTML = hits.map(function (x) { var hid = mm.ignore.indexOf(x.id) > -1;
            return '<div class="apair"><div class="nm">' + esc(x.n) + "<br><span>" + esc(x.c) + '</span></div><div class="bt">' +
              (hid ? '<span class="muted" style="font-size:.82rem">লুকানো</span>' : '<button type="button" class="abtn warn" data-hide="' + esc(x.id) + '">সাইট থেকে লুকান</button>') +
              '<a class="abtn ghost" style="display:inline-flex;align-items:center" href="' + BASE + "/p/" + x.id + '/" target="_blank">দেখুন</a></div></div>'; }).join("") || '<p class="aempty">কিছু পাওয়া যায়নি।</p>';
        });
      }
      draw();
      p.addEventListener("click", function (e) {
        var d = e.target.dataset || {};
        if (d.hide) { mm.ignore.push(d.hide); var q = $("#pq").value; draw(); $("#pq").value = q; $("#pq").dispatchEvent(new Event("input")); markDirty("products"); }
        else if (d.unhide) { mm.ignore = mm.ignore.filter(function (x) { return x !== d.unhide; }); draw(); markDirty("products"); }
        else if (d.merge) {
          var ab = d.merge.split("|"), keep = ab[0], other = ab[1];
          var m = mm.merge.filter(function (x) { return x.keep === keep; })[0];
          if (m) m.merge.push(other); else mm.merge.push({ keep: keep, merge: [other] });
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
      '<section class="card"><h2>পরিবর্তন কখন সাইটে আসে</h2><p style="margin:0;font-size:.88rem;line-height:1.6">স্টোরের নাম/লোগো, বিজ্ঞাপন, স্পন্সর, ক্যাটাগরি, প্রোডাক্ট লুকানো বা মিলানো সেভ করলে ২-৩ মিনিটে সাইট আপডেট হয়। স্টোর চালু/বন্ধ বা অপেক্ষার সময় পরের দামের রান থেকে কার্যকর হয় (প্রতি রাতে ২:১৭, অথবা ড্যাশবোর্ড থেকে এখনই চালান)।</p></section>';
    return Promise.resolve();
  };

  window.addEventListener("hashchange", function () { var t = location.hash.slice(1); if (VIEWS[t] && t !== S.tab && S.admin) show(t); });

  /* ---------- শুরু ---------- */
  fetch(BASE + "/admin/admin.json", { cache: "no-store" }).then(function (r) { return r.json(); }).then(function (a) {
    S.admin = a;
    S.token = lsGet(TKEY);
    var start = (location.hash || "#dash").slice(1);
    if (S.token) {
      checkToken().then(function (ok) { if (!ok) { S.token = null; lsSet(TKEY, null); } renderAuth(); show(start); });
    } else { renderAuth(); show(start); }
  }).catch(function (e) { $("#panel").innerHTML = '<section class="card"><p class="aempty">অ্যাডমিন ডাটা লোড হয়নি: ' + esc(e.message) + "</p></section>"; });
})();
