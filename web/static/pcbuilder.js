/* পিসি বিল্ডার: পার্টস বাছা, সব দোকানের দাম মিলিয়ে মোট, আর সকেট/র‍্যাম/পাওয়ার মানানসই কিনা।
   ক্যাটাগরির তালিকা আসে /c/<cat>/items.json থেকে (ফিল্টারের একই ফাইল), দোকানভেদে দাম /d/<id>.json থেকে।
   বাছাই ঠিকানায় থাকে (?cpu=..&mb=..), তাই লিংক শেয়ার করলে একই বিল্ড খোলে। */
(function () {
  var SLOTS = window.DT_PCB || [], STORES = window.DT_STORES || {}, BASE = window.DT_BASE || "";
  var $ = function (id) { return document.getElementById(id); };
  var lists = {}, details = {}, picks = {}, cur = null;
  function bn(n) { return String(n).replace(/\d/g, function (d) { return "০১২৩৪৫৬৭৮৯"[d]; }); }
  function taka(n) { return "৳" + Number(n).toLocaleString("en-US"); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function slot(k) { return SLOTS.filter(function (s) { return s.key === k; })[0]; }
  function f(it, k) { return it && it.f ? it.f[k] : null; }

  function loadSlot(s) {
    if (lists[s.key]) return Promise.resolve(lists[s.key]);
    return Promise.all(s.cats.map(function (c) {
      return fetch(BASE + "/c/" + c + "/items.json").then(function (r) { return r.ok ? r.json() : { items: [] }; })
        .then(function (j) { return j.items.map(function (it) { it.cat = c; return it; }); }, function () { return []; });
    })).then(function (a) { lists[s.key] = [].concat.apply([], a); return lists[s.key]; });
  }
  function detail(id) {
    if (!details[id]) details[id] = fetch(BASE + "/d/" + id + ".json").then(function (r) { return r.json(); }).catch(function () { delete details[id]; return null; });
    return details[id];
  }

  /* ---------- মানানসই ---------- */
  function watts(name) { var m = /(\d{3,4})\s*W(?:att)?\b/i.exec(name || ""); return m ? +m[1] : null; }
  function cpuW(n) {
    n = (n || "").toLowerCase();
    if (/i9|ryzen\s*9|ultra\s*9|threadripper/.test(n)) return 170;
    if (/x3d/.test(n)) return 120;
    if (/i7|ryzen\s*7|ultra\s*7/.test(n)) return 125;
    return 95;
  }
  function gpuW(n) {
    var u = (n || "").toUpperCase(), m;
    var T = { "5090": 575, "5080": 360, "5070 TI": 300, "5070": 250, "5060 TI": 180, "5060": 145, "5050": 130, "4090": 450, "4080": 320, "4070 TI": 285,
      "4070": 200, "4060 TI": 165, "4060": 115, "3090": 350, "3080": 320, "3070": 220, "3060 TI": 200, "3060": 170, "3050": 130, "1650": 75, "1660": 125,
      "9070 XT": 304, "9070": 220, "9060 XT": 160, "7900": 315, "7800": 263, "7700": 245, "7600": 165, "6700": 220, "6600": 132, "6500": 107 };
    if ((m = /(RTX|GTX)\s?(\d{4})\s?(TI)?/.exec(u)) || (m = /RX\s?(\d{4})\s?(XTX|XT)?/.exec(u))) {
      var key = m[1] === "RTX" || m[1] === "GTX" ? m[2] + (m[3] ? " TI" : "") : m[1] + (m[2] ? " " + m[2].replace("XTX", "XT") : "");
      return T[key] || T[key.split(" ")[0]] || 200;
    }
    return /ARC/.test(u) ? 190 : 0;
  }
  function needW() {
    var c = picks.cpu, g = picks.gpu;
    if (!c && !g) return null;
    var w = (c ? cpuW(c.n) : 95) + (g ? gpuW(g.n) : 0) + 100;
    return Math.ceil(w * 1.3 / 50) * 50;
  }
  function fits(key, it) {  // true = মানানসই, false = না, null = বলা যাচ্ছে না
    if (key === "mb" && picks.cpu) return cmp(f(it, "sk"), f(picks.cpu, "sk"));
    if (key === "cpu" && picks.mb) return cmp(f(it, "sk"), f(picks.mb, "sk"));
    if (key === "ram" && picks.mb) return cmp(f(it, "type"), f(picks.mb, "mt"));
    if (key === "mb" && picks.ram) { var r = cmp(f(it, "mt"), f(picks.ram, "type")); if (r === false) return false; }
    if (key === "psu") { var nw = needW(), w = watts(it.n); return nw && w ? w >= nw : null; }
    return null;
  }
  function cmp(a, b) { return a && b ? a === b : null; }
  function fitLabel(key) {
    if ((key === "mb" && picks.cpu && f(picks.cpu, "sk")) || (key === "cpu" && picks.mb && f(picks.mb, "sk"))) return "শুধু " + f(picks[key === "mb" ? "cpu" : "mb"], "sk") + " সকেট";
    if (key === "ram" && picks.mb && f(picks.mb, "mt")) return "শুধু " + f(picks.mb, "mt");
    if (key === "psu" && needW()) return "শুধু " + bn(needW()) + "W বা বেশি";
    return null;
  }

  /* ---------- বাছাইয়ের তালিকা ---------- */
  function openPicker(key) {
    cur = key; var s = slot(key);
    $("pcmtitle").textContent = s.name + " বাছুন";
    $("pcq").value = ""; $("pclist").innerHTML = '<p class="muted" style="padding:12px 0">লোড হচ্ছে…</p>';
    var fl = fitLabel(key); $("pcfitw").hidden = !fl; $("pcfitl").textContent = fl || "";
    $("pcmodal").hidden = false; document.body.classList.add("fp-on");
    setTimeout(function () { $("pcq").focus(); }, 50);
    loadSlot(s).then(drawList);
  }
  function closePicker() { $("pcmodal").hidden = true; document.body.classList.remove("fp-on"); cur = null; }
  function drawList() {
    if (!cur) return;
    var all = lists[cur] || [], q = $("pcq").value.toLowerCase().split(/\s+/).filter(Boolean);
    var onlyFit = !$("pcfitw").hidden && $("pcfit").checked, onlyStock = $("pcstock").checked;
    var hits = all.filter(function (it) {
      if (onlyStock && it.p == null) return false;
      if (onlyFit && fits(cur, it) === false) return false;
      var n = it.n.toLowerCase();
      return q.every(function (w) { return n.indexOf(w) > -1; });
    }).sort(function (a, b) {
      var fa = fits(cur, a), fb = fits(cur, b);
      if (onlyFit && fa !== fb) return fa === true ? -1 : fb === true ? 1 : 0;
      return (a.p == null ? 1e12 : a.p) - (b.p == null ? 1e12 : b.p);
    });
    $("pclist").innerHTML = (hits.length ? '<p class="fstat">' + bn(hits.length) + "টি পাওয়া গেছে" + (hits.length > 80 ? ", কম দামের ৮০টি দেখাচ্ছে। নাম লিখে খুঁজুন।" : "") + "</p>" : '<p class="muted" style="padding:12px 0">কিছু পাওয়া যায়নি। ফিল্টার সরিয়ে দেখুন।</p>') +
      hits.slice(0, 80).map(function (it) {
        var ft = fits(cur, it), tags = it.f ? Object.keys(it.f).map(function (k) { return '<span class="tag">' + esc(it.f[k]) + "</span>"; }).join("") : "";
        return '<button type="button" class="row pci" data-id="' + esc(it.i) + '"><div style="min-width:0"><div class="n">' + esc(it.n) + "</div>" +
          '<div class="w">' + (it.s ? esc(STORES[it.s] || "") : "স্টকে নেই") + (it.k > 1 ? '<span class="badge">' + bn(it.k) + " স্টোর</span>" : "") +
          (ft === true ? ' <span class="pcok">✓ মানানসই</span>' : ft === false ? ' <span class="pcno">✗ মানানসই নয়</span>' : "") + "</div>" +
          (tags ? '<div class="tags" style="margin-top:3px">' + tags + "</div>" : "") + "</div>" +
          '<div class="p">' + (it.p != null ? taka(it.p) : "—") + "</div></button>";
      }).join("");
  }
  $("pcq").addEventListener("input", drawList);
  $("pcfit").addEventListener("change", drawList);
  $("pcstock").addEventListener("change", drawList);
  $("pcmclose").addEventListener("click", closePicker);
  $("pcmodal").addEventListener("click", function (e) { if (e.target === $("pcmodal")) closePicker(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !$("pcmodal").hidden) closePicker(); });
  $("pclist").addEventListener("click", function (e) {
    var b = e.target.closest("[data-id]"); if (!b || !cur) return;
    var it = (lists[cur] || []).filter(function (x) { return x.i === b.dataset.id; })[0];
    if (it) { picks[cur] = it; closePicker(); update(); }
  });
  $("pcslots").addEventListener("click", function (e) {
    var p = e.target.closest("[data-pick]"); if (p) { openPicker(p.dataset.pick); return; }
    var r = e.target.closest("[data-rm]"); if (r) { delete picks[r.dataset.rm]; update(); }
  });

  /* ---------- মোট ও যাচাই ---------- */
  function update() {
    save();
    SLOTS.forEach(function (s) {
      var el = document.querySelector('[data-slot="' + s.key + '"]'), it = picks[s.key];
      el.classList.toggle("on", !!it);
      el.querySelector("[data-v]").innerHTML = it
        ? '<a href="' + BASE + "/p/" + encodeURIComponent(it.i) + '/" target="_blank">' + esc(it.n) + "</a>" +
          '<span class="pcs-p">' + (it.p != null ? taka(it.p) + " · " + esc(STORES[it.s] || "") : "এখন স্টকে নেই") + '</span><button type="button" class="pcs-rm" data-rm="' + s.key + '">সরান</button>'
        : '<span class="muted">এখনো বাছা হয়নি</span>';
      el.querySelector("[data-pick]").textContent = it ? "বদলান" : "বাছুন";
    });
    checks();
    var ids = Object.keys(picks).map(function (k) { return picks[k].i; });
    if (!ids.length) { $("pctotal").innerHTML = '<p class="muted" style="margin:0;font-size:.88rem">পার্টস বাছলে এখানে মোট দাম দেখাবে।</p>'; return; }
    $("pctotal").classList.add("busy");
    Promise.all(Object.keys(picks).map(function (k) { return detail(picks[k].i).then(function (d) { return [k, d]; }); })).then(function (rows) {
      $("pctotal").classList.remove("busy");
      var mix = 0, byStore = {}, missing = [], stores = {};
      rows.forEach(function (r) {
        var k = r[0], d = r[1], o = (d && d.o) || {}, best = null;
        Object.keys(o).forEach(function (s) {
          if (!o[s].st || !o[s].p) return;
          if (!best || o[s].p < best.p) best = { s: s, p: o[s].p };
          (stores[s] = stores[s] || {})[k] = o[s].p;
        });
        if (best) { mix += best.p; (byStore[best.s] = byStore[best.s] || []).push([k, best.p]); } else missing.push(k);
      });
      var n = rows.length, single = Object.keys(stores).map(function (s) {
        var ks = Object.keys(stores[s]); return { s: s, n: ks.length, t: ks.reduce(function (a, k) { return a + stores[s][k]; }, 0) };
      }).sort(function (a, b) { return b.n - a.n || a.t - b.t; });
      var full = single.filter(function (x) { return x.n === n - missing.length && !missing.length; });
      var h = '<div class="pctot"><span>সবচেয়ে কম দামের দোকান থেকে</span><b class="price">' + taka(mix) + "</b></div>";
      if (missing.length) h += '<p class="chknote" style="margin-top:8px"><b>স্টকে নেই:</b> ' + missing.map(function (k) { return esc(slot(k).name); }).join(", ") + " (মোট দামে ধরা হয়নি)</p>";
      h += '<div class="pcby">' + Object.keys(byStore).map(function (s) {
        var t = byStore[s].reduce(function (a, x) { return a + x[1]; }, 0);
        return '<div><b>' + esc(STORES[s] || s) + "</b> <span>" + byStore[s].map(function (x) { return esc(slot(x[0]).name); }).join(", ") + "</span><em>" + taka(t) + "</em></div>";
      }).join("") + "</div>";
      if (full.length) {
        var b = full.sort(function (a, b) { return a.t - b.t; })[0];
        h += '<div class="pctot one"><span>এক দোকান থেকে সব: ' + esc(STORES[b.s] || b.s) + "</span><b>" + taka(b.t) + "</b></div>" +
          (b.t > mix ? '<p class="pcsave">ভাগ করে কিনলে ' + taka(b.t - mix) + " বাঁচে; এক দোকানে কিনলে ঝামেলা কম, ওয়ারেন্টিও এক জায়গায়।</p>" : '<p class="pcsave">এক দোকান থেকে কিনলেই সবচেয়ে কম পড়ছে।</p>');
      } else if (single.length && n > 1) {
        h += '<p class="muted" style="font-size:.8rem;margin:8px 0 0">কোনো একক দোকানে সব পার্টস স্টকে নেই। সবচেয়ে বেশি আছে ' + esc(STORES[single[0].s] || "") + "-এ (" + bn(single[0].n) + "/" + bn(n) + "টি)।</p>";
      }
      $("pctotal").innerHTML = h;
    });
  }
  function checks() {
    var L = [], add = function (ok, t) { L.push('<li class="' + (ok === true ? "ok" : ok === false ? "no" : "q") + '">' + t + "</li>"); };
    var c = picks.cpu, m = picks.mb, r = picks.ram, p = picks.psu;
    if (c && m) { var a = f(c, "sk"), b = f(m, "sk"); add(cmp(a, b), a && b ? (a === b ? "প্রসেসর ও মাদারবোর্ডের সকেট এক (" + a + ")" : "সকেট মেলেনি: প্রসেসর " + a + ", মাদারবোর্ড " + b) : "সকেট নাম থেকে বোঝা যায়নি, দোকানে মিলিয়ে নিন"); }
    if (m && r) { var x = f(m, "mt"), y = f(r, "type"); add(cmp(x, y), x && y ? (x === y ? "র‍্যাম ও মাদারবোর্ড দুটোই " + x : "র‍্যাম " + y + " কিন্তু মাদারবোর্ড " + x) : "র‍্যামের ধরন বোঝা যায়নি, দোকানে মিলিয়ে নিন"); }
    var nw = needW();
    if (p && nw) { var w = watts(p.n); add(w ? w >= nw : null, w ? (w >= nw ? "পাওয়ার সাপ্লাই " + bn(w) + "W, আনুমানিক দরকার " + bn(nw) + "W" : "পাওয়ার সাপ্লাই " + bn(w) + "W, কিন্তু আনুমানিক দরকার " + bn(nw) + "W") : "পাওয়ার সাপ্লাইয়ের ওয়াট বোঝা যায়নি"); }
    else if (nw) add(null, "এই বিল্ডে আনুমানিক " + bn(nw) + "W পাওয়ার সাপ্লাই লাগবে");
    if (c && !picks.gpu && !/\d{4}G\b|ultra|\bi[3579][\s-]*\d{4,5}(?!F)/i.test(c.n)) add(null, "এই প্রসেসরে গ্রাফিক্স নাও থাকতে পারে (F/বাজেট সিরিজ হলে আলাদা গ্রাফিক্স কার্ড লাগবে)");
    var need = SLOTS.filter(function (s) { return s.req && !picks[s.key]; }).map(function (s) { return s.name; });
    if (Object.keys(picks).length && need.length) add(null, "এখনো বাকি: " + need.join(", "));
    $("pcchecks").hidden = !L.length; $("pcchk").innerHTML = L.join("");
  }

  /* ---------- সেভ ও শেয়ার ---------- */
  function save() {
    var q = new URLSearchParams();
    Object.keys(picks).forEach(function (k) { q.set(k, picks[k].i); });
    var s = q.toString();
    try { history.replaceState(null, "", location.pathname + (s ? "?" + s : "")); localStorage.setItem("dt_pcb", s); } catch (e) {}
  }
  $("pcshare").addEventListener("click", function () {
    var u = location.href, m = $("pcmsg");
    (navigator.clipboard ? navigator.clipboard.writeText(u) : Promise.reject()).then(function () { m.className = "almsg ok"; m.textContent = "লিংক কপি হয়েছে, যে কাউকে পাঠাতে পারেন।"; },
      function () { m.className = "almsg"; m.textContent = u; });
  });
  $("pcclear").addEventListener("click", function () { picks = {}; update(); });

  var q = new URLSearchParams(location.search);
  if (!location.search) { try { q = new URLSearchParams(localStorage.getItem("dt_pcb") || ""); } catch (e) {} }
  var want = SLOTS.filter(function (s) { return q.get(s.key); });
  Promise.all(want.map(function (s) {
    return loadSlot(s).then(function (l) { var it = l.filter(function (x) { return x.i === q.get(s.key); })[0]; if (it) picks[s.key] = it; });
  })).then(update);
})();
