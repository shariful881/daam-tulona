/* হোম পেজ: চলমান দামের লাইন, "লাইভ" সময়, উঠানামার ট্যাব, সংখ্যার অ্যানিমেশন, শেষবার দেখা প্রোডাক্ট। */
(function () {
  var B = window.DT_BASE || "", D = "০১২৩৪৫৬৭৮৯";
  function bn(n) { return String(n).replace(/[0-9]/g, function (d) { return D[d]; }); }
  function bnc(n) { return bn(Math.round(n).toLocaleString("en-US")); }
  function get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function put(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  // চলমান লাইন: লুকানো/দেখানো মনে রাখে
  var tb = document.getElementById("tkbar"), to = document.getElementById("tkopen");
  if (tb && to) {
    var setT = function (h) { tb.hidden = h; to.hidden = !h; put("dt_ticker_hidden", h ? "1" : ""); };
    if (get("dt_ticker_hidden") === "1") { tb.hidden = true; to.hidden = false; }
    document.getElementById("tkx").onclick = function () { setT(true); };
    to.onclick = function () { setT(false); };
  }

  // "লাইভ · কত আগে আপডেট" (দাম আনার সময় থেকে)
  var ago = document.querySelectorAll("[data-since]");
  function tick() {
    [].forEach.call(ago, function (e) {
      var t = Date.parse(e.getAttribute("data-since")); if (!t) return;
      var m = Math.max(0, Math.floor((Date.now() - t) / 60000));
      e.textContent = "· " + (m < 60 ? bn(m) + " মিনিট আগে" : m < 1440 ? bn(Math.floor(m / 60)) + " ঘণ্টা আগে" : bn(Math.floor(m / 1440)) + " দিন আগে");
    });
  }
  if (ago.length) { tick(); setInterval(tick, 30000); }

  // উঠানামার ক্যাটাগরি ট্যাব
  var tabs = document.querySelectorAll(".mvtabs button");
  [].forEach.call(tabs, function (b) {
    b.addEventListener("click", function () {
      var t = b.getAttribute("data-t");
      [].forEach.call(tabs, function (x) { x.setAttribute("aria-selected", String(x === b)); });
      [].forEach.call(document.querySelectorAll(".mvpane"), function (p) { p.hidden = p.getAttribute("data-t") !== t; });
    });
  });
  // ফোনে আঙুল রাখলে স্ক্রল থামে
  [].forEach.call(document.querySelectorAll(".mvview"), function (v) {
    v.addEventListener("touchstart", function () { v.classList.add("hold"); }, { passive: true });
    v.addEventListener("touchend", function () { setTimeout(function () { v.classList.remove("hold"); }, 2500); });
  });

  // সংখ্যায় দামতুলনা: দেখা গেলেই গুনে ওঠে, আর বারবার দেখা যায়
  var sec = document.getElementById("nstat");
  if (sec) {
    var nums = [].slice.call(sec.querySelectorAll("[data-count]")), raf = 0;
    var play = function () {
      cancelAnimationFrame(raf);
      sec.classList.remove("go"); sec.classList.add("pre"); void sec.offsetWidth;
      nums.forEach(function (el) { el.textContent = bn(0); });
      requestAnimationFrame(function () {
        sec.classList.remove("pre"); sec.classList.add("go");
        var t0 = null;
        var f = function (t) {
          if (!t0) t0 = t;
          var k = Math.min(1, (t - t0) / 1600), e = 1 - Math.pow(1 - k, 3);
          nums.forEach(function (el) { el.textContent = bnc(+el.getAttribute("data-count") * e); });
          if (k < 1) raf = requestAnimationFrame(f);
        };
        raf = requestAnimationFrame(f);
      });
    };
    document.getElementById("nsreplay").onclick = play;
    [].forEach.call(sec.querySelectorAll(".ns-card"), function (c) { c.addEventListener("click", play); });
    if ("IntersectionObserver" in window) {
      var away = true;
      new IntersectionObserver(function (es) {
        es.forEach(function (e) {
          if (e.intersectionRatio >= 0.3 && away) { away = false; play(); }
          else if (!e.isIntersecting) away = true;
        });
      }, { threshold: [0, 0.3] }).observe(sec);
    }
  }

  // শেষবার যা দেখেছিলেন: প্রোডাক্ট পেজ এই ফোনে তালিকা রাখে (dt_seen); এখানে আজকের দামের সাথে মেলানো হয়
  var box = document.getElementById("recent"), list = document.getElementById("rvl");
  var seen = [];
  try { seen = JSON.parse(get("dt_seen") || "[]"); } catch (e) {}
  if (box && list && seen.length) {
    seen = seen.slice(0, 8);
    var cats = {};
    seen.forEach(function (s) { if (s.c) cats[s.c] = 1; });
    var now = {};
    Promise.all(Object.keys(cats).map(function (c) {
      return fetch(B + "/c/" + c + "/items.json").then(function (r) { return r.ok ? r.json() : { items: [] }; })
        .then(function (d) { (d.items || []).forEach(function (x) { now[x.i] = x; }); }).catch(function () {});
    })).then(function () {
      var html = seen.map(function (s) {
        var cur = now[s.i], p = cur && cur.p, diff = p && s.p ? p - s.p : 0;
        var st = !p ? '<span class="rvc">এখন স্টকে নেই</span>'
          : diff < 0 ? '<span class="rvc dn">▼ ৳' + bnc(-diff) + " কমেছে</span>"
          : diff > 0 ? '<span class="rvc up">▲ ৳' + bnc(diff) + " বেড়েছে</span>" : '<span class="rvc">দাম একই আছে</span>';
        var days = Math.floor((Date.now() - (s.t || Date.now())) / 86400000);
        var when = days <= 0 ? "আজ" : days === 1 ? "গতকাল" : bn(days) + " দিন আগে";
        var img = (cur && cur.im && cur.im[0]) || s.m;
        return '<a class="rvi" href="' + B + "/p/" + esc(s.i) + '/"><span class="rimg' + (img ? "" : " noimg") + '" data-img>' +
          (img ? '<img src="' + esc(img) + '" alt="" width="48" height="48" loading="lazy" onerror="this.parentNode.classList.add(\'noimg\');this.remove()">' : "") +
          '</span><span class="rvn">' + esc(s.n) + '</span>' + (p ? '<b class="price">৳' + bnc(p) + "</b>" : "") + st +
          "<small>" + when + " দেখেছিলেন" + (s.p ? " (৳" + bnc(s.p) + ")" : "") + "</small></a>";
      }).join("");
      list.innerHTML = html; box.hidden = false;
    });
    document.getElementById("rvclr").onclick = function () { put("dt_seen", "[]"); box.hidden = true; };
  }
})();
