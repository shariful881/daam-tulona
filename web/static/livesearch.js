/* হেডারের সার্চ বক্সে টাইপ করার সাথে সাথে ফল (লাইভ সার্চ)। search.js প্রথমবার ফোকাস করলে নামে। */
(function () {
  var BASE = window.DT_BASE || "", form = document.querySelector(".hdr .sform"), q = form && form.querySelector("input.search"),
    box = document.getElementById("sdrop");
  if (!q || !box) return;
  var seq = 0, timer, active = -1, loading = null;
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function bn(n) { return String(n).replace(/\d/g, function (d) { return "০১২৩৪৫৬৭৮৯"[d]; }); }
  function taka(n) { return "৳" + Number(n).toLocaleString("en-US"); }
  function lib() {
    if (window.DTSearch) return Promise.resolve();
    if (!loading) loading = new Promise(function (ok) {
      var s = document.createElement("script");
      s.src = BASE + "/static/search.js?v=" + (window.DT_BUILD || "");
      s.onload = ok; s.onerror = ok; document.head.appendChild(s);
    });
    return loading;
  }
  function hide() { box.hidden = true; q.setAttribute("aria-expanded", "false"); active = -1; }
  function hl(name, v) {  // মিলে যাওয়া শব্দ মোটা করে
    var words = v.toLowerCase().split(/\s+/).filter(function (w) { return w.length > 1; });
    var out = esc(name);
    words.forEach(function (w) {
      var i = out.toLowerCase().indexOf(esc(w));
      if (i > -1) out = out.slice(0, i) + "<b>" + out.slice(i, i + esc(w).length) + "</b>" + out.slice(i + esc(w).length);
    });
    return out;
  }
  function run() {
    var v = q.value.trim(), my = ++seq;
    if (Array.from(v).length < 2) { hide(); return; }
    box.hidden = false; q.setAttribute("aria-expanded", "true");
    if (!box.innerHTML) box.innerHTML = '<div class="sd-msg">খোঁজা হচ্ছে…</div>';
    lib().then(function () {
      if (!window.DTSearch) { box.innerHTML = '<div class="sd-msg">সার্চ লোড হয়নি, Enter চাপুন</div>'; return; }
      return window.DTSearch(v, { limit: 8 }).then(function (hits) {
        if (my !== seq) return;
        active = -1;
        var all = BASE + "/search/?q=" + encodeURIComponent(v);
        box.innerHTML = hits.length ? hits.map(function (d) {
          return '<a class="sd-row" role="option" href="' + BASE + "/p/" + encodeURIComponent(d.id) + '/"><span class="sd-n"><span class="sd-t">' + hl(d.n, v) + "</span>" +
            '<small>' + esc(d.c) + (d.k > 1 ? ' · <i>' + bn(d.k) + " দোকানে</i>" : "") + "</small></span>" +
            '<span class="sd-p">' + (d.p ? taka(d.p) : "—") + "</span></a>";
        }).join("") + '<a class="sd-all" href="' + all + '">সব ফল দেখুন' + (hits.total > 8 ? " (" + bn(hits.total) + "টা)" : "") + " ›</a>"
          : '<div class="sd-msg">"' + esc(v) + '" নামে কিছু পাওয়া যায়নি</div>';
      });
    });
  }
  q.addEventListener("focus", lib, { once: true });
  q.addEventListener("input", function () { clearTimeout(timer); timer = setTimeout(run, 120); });
  q.addEventListener("focus", function () { if (box.innerHTML && Array.from(q.value.trim()).length >= 2) { box.hidden = false; } });
  q.addEventListener("keydown", function (e) {
    var rows = box.querySelectorAll("a");
    if (box.hidden || !rows.length) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      active = (active + (e.key === "ArrowDown" ? 1 : -1) + rows.length) % rows.length;
      rows.forEach(function (r, i) { r.classList.toggle("on", i === active); });
    } else if (e.key === "Enter" && active > -1) {
      e.preventDefault(); location.href = rows[active].href;
    } else if (e.key === "Escape") hide();
  });
  document.addEventListener("click", function (e) { if (!form.contains(e.target)) hide(); });
})();
