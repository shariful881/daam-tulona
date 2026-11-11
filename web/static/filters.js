/* ক্যাটাগরি পেজের ফিল্টার ও সাজানো।
   কিছু না বাছলে পাতার নিজের (স্ট্যাটিক) তালিকা আর পাতা নম্বর দেখায়।
   কিছু বাছলেই পুরো ক্যাটাগরির ছোট ডাটা ফাইল (items.json) একবার নামিয়ে সব প্রোডাক্টের মধ্যে খোঁজে।
   বাছাই ঠিকানায় (?min=..&f.cap=..) থাকে, তাই লিংক শেয়ার করলেও একই ফল দেখায়। */
(function () {
  var C = window.DT_CAT, BASE = window.DT_BASE || "";
  if (!C) return;
  var $ = function (id) { return document.getElementById(id); };
  var list = $("list"), pager = $("pager"), panel = $("fpanel"), more = $("fload"), stat = $("fstat"), empty = $("empty");
  var original = list.innerHTML, data = null, loading = null, shown = 48, STEP = 48;
  var icon = ($("cicon") || {}).innerHTML || "";
  var order = {};  // ফ্যাসেট মানের ক্রম (ছোট থেকে বড়), সাজানোর জন্য
  [].forEach.call(document.querySelectorAll("input[data-fid]"), function (c) {
    var o = order[c.dataset.fid] || (order[c.dataset.fid] = {});
    o[c.value] = Object.keys(o).length;
  });

  function bn(n) { return String(n).replace(/\d/g, function (d) { return "০১২৩৪৫৬৭৮৯"[d]; }); }
  function taka(n) { return "৳" + Number(n).toLocaleString("en-US"); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  /* ---------- অবস্থা ---------- */
  var S = { sort: "", min: "", max: "", stock: false, multi: false, f: {} };
  function readURL() {
    var q = new URLSearchParams(location.search);
    S.sort = q.get("sort") || ""; S.min = q.get("min") || ""; S.max = q.get("max") || "";
    S.stock = q.get("stock") === "1"; S.multi = q.get("multi") === "1"; S.f = {};
    q.forEach(function (v, k) { if (k.indexOf("f.") === 0 && v) S.f[k.slice(2)] = v.split("|"); });
  }
  function writeURL() {
    var q = new URLSearchParams();
    if (S.sort) q.set("sort", S.sort);
    if (S.min) q.set("min", S.min);
    if (S.max) q.set("max", S.max);
    if (S.stock) q.set("stock", "1");
    if (S.multi) q.set("multi", "1");
    Object.keys(S.f).forEach(function (k) { if (S.f[k].length) q.set("f." + k, S.f[k].join("|")); });
    var s = q.toString();
    try { history.replaceState(null, "", location.pathname + (s ? "?" + s : "")); } catch (e) {}
  }
  function nActive() {
    var n = (S.min || S.max ? 1 : 0) + (S.stock ? 1 : 0) + (S.multi ? 1 : 0);
    Object.keys(S.f).forEach(function (k) { n += S.f[k].length; });
    return n;
  }
  function isDefault() { return !nActive() && !S.sort; }

  /* ---------- ডাটা ---------- */
  function load() {
    if (data) return Promise.resolve(data);
    if (!loading) loading = fetch(BASE + "/c/" + C.slug + "/items.json").then(function (r) { return r.json(); }).then(function (j) { data = j; return j; });
    return loading;
  }
  function val(it, fid) { return fid === "brand" ? it.b : (it.f || {})[fid]; }
  function match(it, skip) {
    var p = it.p;
    if (S.min && (p == null || p < +S.min)) return false;
    if (S.max && (p == null || p > +S.max)) return false;
    if (S.stock && p == null) return false;
    if (S.multi && it.k < 2) return false;
    for (var k in S.f) {
      if (k === skip || !S.f[k].length) continue;
      if (S.f[k].indexOf(val(it, k)) < 0) return false;
    }
    return true;
  }
  function sorter() {
    var s = S.sort, m = /^f_(.+)_(asc|desc)$/.exec(s);
    var price = function (it) { return it.p == null ? (it.a == null ? 1e12 : 1e11 + it.a) : it.p; };
    if (m) {
      var o = order[m[1]] || {}, dir = m[2] === "asc" ? 1 : -1;
      return function (a, b) {
        var x = o[val(a, m[1])], y = o[val(b, m[1])];
        if (x == null && y == null) return price(a) - price(b);
        if (x == null) return 1; if (y == null) return -1;
        return (x - y) * dir || price(a) - price(b);
      };
    }
    if (s === "price_desc") return function (a, b) { return (b.p == null ? -1 : b.p) - (a.p == null ? -1 : a.p); };
    if (s === "stores") return function (a, b) { return b.l - a.l || b.k - a.k || price(a) - price(b); };
    if (s === "saving") return function (a, b) { return (b.v || 0) - (a.v || 0) || price(a) - price(b); };
    return function (a, b) { return price(a) - price(b); };
  }

  /* ---------- আঁকা ---------- */
  function row(it) {
    var st = it.s ? data.stores[it.s] || "" : "এখন স্টকে নেই";
    var img = it.im && it.im.length ? '<img src="' + esc(it.im[0]) + '" alt="" width="44" height="44" loading="lazy" decoding="async" data-alts="' +
      esc(JSON.stringify(it.im.slice(1).map(function (u) { return [u]; }))) + '" onerror="dtImgErr(this)">' : "";
    var pr = it.p != null ? taka(it.p) : it.a != null ? '<span class="muted">' + taka(it.a) + "</span>" : "—";
    return '<a class="row wi" href="' + BASE + "/p/" + encodeURIComponent(it.i) + '/"><span class="rimg" data-img>' + icon + img + "</span>" +
      '<div style="min-width:0"><div class="n">' + esc(it.n) + '</div><div class="w">' + esc(st) + (it.k > 1 ? '<span class="badge">' + bn(it.k) + " স্টোর</span>" : "") + "</div></div>" +
      '<div><div class="p">' + pr + "</div>" + (it.v ? '<div class="d lo">' + taka(it.v) + " পার্থক্য</div>" : "") + "</div></a>";
  }
  function counts() {
    var boxes = document.querySelectorAll("input[data-fid]");
    var byF = {};
    [].forEach.call(boxes, function (c) { (byF[c.dataset.fid] = byF[c.dataset.fid] || []).push(c); });
    Object.keys(byF).forEach(function (fid) {
      var cnt = {};
      data.items.forEach(function (it) { if (match(it, fid)) { var v = val(it, fid); if (v) cnt[v] = (cnt[v] || 0) + 1; } });
      byF[fid].forEach(function (c) {
        var n = cnt[c.value] || 0, sm = c.parentNode.querySelector("small");
        if (sm) sm.textContent = bn(n);
        c.parentNode.classList.toggle("zero", !n && !c.checked);
      });
    });
  }
  function chips() {
    var box = $("fapplied"), out = [];
    if (S.min || S.max) out.push(['price', (S.min && S.max ? taka(S.min) + "–" + taka(S.max) : S.min ? taka(S.min) + "+" : taka(S.max) + " পর্যন্ত")]);
    if (S.stock) out.push(["stock", "স্টকে আছে"]);
    if (S.multi) out.push(["multi", "একাধিক স্টোর"]);
    Object.keys(S.f).forEach(function (k) { S.f[k].forEach(function (v) { out.push(["f:" + k + ":" + v, v]); }); });
    box.innerHTML = out.map(function (c) { return '<button type="button" class="fap" data-rm="' + esc(c[0]) + '">' + esc(c[1]) + ' <span aria-hidden="true">✕</span></button>'; }).join("") +
      (out.length > 1 ? '<button type="button" class="fap clear" data-rm="all">সব মুছুন</button>' : "");
    box.hidden = !out.length;
    var n = nActive(), fc = $("fcount");
    fc.hidden = !n; fc.textContent = bn(n);
  }
  function syncInputs() {
    $("fsort").value = S.sort; $("fmin").value = S.min; $("fmax").value = S.max;
    $("fstock").checked = S.stock; $("fmulti").checked = S.multi;
    [].forEach.call(document.querySelectorAll("input[data-fid]"), function (c) { c.checked = (S.f[c.dataset.fid] || []).indexOf(c.value) > -1; });
    [].forEach.call(document.querySelectorAll(".fchip"), function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.pmin === S.min && b.dataset.pmax === S.max && !!(S.min || S.max)));
    });
  }
  function render() {
    writeURL(); chips(); syncInputs();
    if (isDefault()) {
      list.innerHTML = original; if (pager) pager.hidden = false;
      stat.hidden = true; more.hidden = true; empty.hidden = true; $("fgo").textContent = "ফল দেখুন";
      if (data) counts();
      return;
    }
    list.classList.add("busy");
    load().then(function () {
      var hits = data.items.filter(function (it) { return match(it); }).sort(sorter());
      list.innerHTML = hits.slice(0, shown).map(row).join("");
      list.classList.remove("busy");
      if (pager) pager.hidden = true;
      empty.hidden = hits.length > 0;
      stat.hidden = false;
      stat.textContent = bn(hits.length) + "টি প্রোডাক্ট পাওয়া গেছে (মোট " + bn(data.items.length) + "টির মধ্যে)";
      more.hidden = hits.length <= shown;
      more.textContent = "আরও দেখুন (" + bn(hits.length - shown) + "টি বাকি)";
      $("fgo").textContent = "ফল দেখুন (" + bn(hits.length) + ")";
      counts();
    }, function () { list.classList.remove("busy"); stat.hidden = false; stat.textContent = "ফিল্টারের ডাটা লোড হয়নি। ইন্টারনেট দেখে আবার চেষ্টা করুন।"; });
  }
  function change() { shown = STEP; render(); }

  /* ---------- ঘটনা ---------- */
  $("fsort").addEventListener("change", function () { S.sort = this.value; change(); });
  var t;
  function priceInput() { clearTimeout(t); t = setTimeout(function () { S.min = $("fmin").value.trim(); S.max = $("fmax").value.trim(); change(); }, 500); }
  $("fmin").addEventListener("input", priceInput); $("fmax").addEventListener("input", priceInput);
  $("fstock").addEventListener("change", function () { S.stock = this.checked; change(); });
  $("fmulti").addEventListener("change", function () { S.multi = this.checked; change(); });
  panel.addEventListener("change", function (e) {
    var c = e.target; if (!c.dataset || !c.dataset.fid) return;
    var a = S.f[c.dataset.fid] || (S.f[c.dataset.fid] = []);
    if (c.checked) { if (a.indexOf(c.value) < 0) a.push(c.value); } else S.f[c.dataset.fid] = a.filter(function (x) { return x !== c.value; });
    change();
  });
  panel.addEventListener("click", function (e) {
    var b = e.target.closest(".fchip");
    if (b) {
      var on = b.getAttribute("aria-pressed") === "true";
      S.min = on ? "" : b.dataset.pmin; S.max = on ? "" : b.dataset.pmax; change(); return;
    }
    var m = e.target.closest(".fmore");
    if (m) { var o = m.previousElementSibling; o.classList.toggle("open"); m.textContent = o.classList.contains("open") ? "কম দেখুন" : m.dataset.t || m.textContent; }
  });
  [].forEach.call(document.querySelectorAll(".fmore"), function (m) { m.dataset.t = m.textContent; });
  $("fapplied").addEventListener("click", function (e) {
    var b = e.target.closest("[data-rm]"); if (!b) return;
    var k = b.dataset.rm;
    if (k === "all") { S = { sort: S.sort, min: "", max: "", stock: false, multi: false, f: {} }; }
    else if (k === "price") { S.min = S.max = ""; }
    else if (k === "stock") S.stock = false;
    else if (k === "multi") S.multi = false;
    else { var p = k.split(":"), fid = p[1], v = p.slice(2).join(":"); S.f[fid] = (S.f[fid] || []).filter(function (x) { return x !== v; }); }
    change();
  });
  $("freset").addEventListener("click", function () { S = { sort: S.sort, min: "", max: "", stock: false, multi: false, f: {} }; change(); });
  more.addEventListener("click", function () { shown += STEP; render(); });

  // মোবাইলে নিচ থেকে খোলা প্যানেল
  function openP(on) {
    panel.classList.toggle("open", on); document.body.classList.toggle("fp-on", on);
    $("fopen").setAttribute("aria-expanded", String(on));
    if (on) load().then(function () { counts(); });
  }
  $("fopen").addEventListener("click", function () { openP(true); });
  $("fclose").addEventListener("click", function () { openP(false); });
  $("fgo").addEventListener("click", function () { openP(false); list.scrollIntoView({ block: "start" }); });
  document.addEventListener("click", function (e) {  // পেছনের অন্ধকার জায়গায় চাপলে বন্ধ
    if (panel.classList.contains("open") && !panel.contains(e.target) && !e.target.closest("#fopen")) openP(false);
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && panel.classList.contains("open")) openP(false); });
  // পিসিতে প্যানেল সবসময় খোলা, তাই সংখ্যাগুলো নিজে থেকেই হালনাগাদ
  if (window.matchMedia("(min-width:1024px)").matches) {
    var idle = window.requestIdleCallback || function (f) { setTimeout(f, 800); };
    idle(function () { load().then(counts); });
  }

  readURL();
  if (!isDefault()) render(); else { chips(); syncInputs(); }
})();
