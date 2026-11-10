/* দামতুলনা — প্রোডাক্টের ছবি বড় করে দেখা (পুরো স্ক্রিন, সোয়াইপ করে অন্য স্টোরের ছবি)।
   ছবি স্টোরের সার্ভার থেকেই আসে; বড় সাইজ না খুললে ছোটটা, সেটাও না খুললে পরের ছবি। */
(function () {
  var el = document.getElementById("galdata");
  if (!el) return;
  var G = JSON.parse(el.textContent), dead = {}, box, idx = 0, x0 = null;

  function bn(n) { return String(n).replace(/\d/g, function (d) { return "০১২৩৪৫৬৭৮৯"[d]; }); }
  function esc(s) { return String(s || "").replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function live() { return G.filter(function (g, i) { return !dead[i]; }).length; }

  function show(i) {
    var n = G.length;
    for (var k = 0; k < n && dead[(i + n) % n]; k++) i++;
    idx = ((i % n) + n) % n;
    var g = G[idx];
    box.querySelector(".gl-img").innerHTML = '<img src="' + esc(g.big) + '" alt="">';
    var img = box.querySelector(".gl-img img");
    img.onerror = function () {
      if (img.src.indexOf(g.u) < 0 && g.big !== g.u) { img.src = g.u; return; }
      dead[idx] = true;
      if (live()) show(idx + 1); else box.querySelector(".gl-img").innerHTML = '<p class="gl-none">ছবি পাওয়া যায়নি</p>';
    };
    box.querySelector(".gl-cap").innerHTML = '<a href="' + esc(g.h) + '" target="_blank" rel="nofollow noopener">ছবি: ' + esc(g.n) + "</a>" +
      (G.length > 1 ? ' <span>' + bn(idx + 1) + " / " + bn(G.length) + "</span>" : "");
    box.querySelectorAll(".gl-nav").forEach(function (b) { b.hidden = live() < 2; });
  }
  function open(i) {
    box = document.createElement("div");
    box.className = "gl";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-label", "প্রোডাক্টের ছবি");
    box.innerHTML = '<button type="button" class="gl-x" aria-label="বন্ধ করুন">✕</button>' +
      '<button type="button" class="gl-nav gl-prev" aria-label="আগের ছবি">‹</button>' +
      '<div class="gl-img"></div>' +
      '<button type="button" class="gl-nav gl-next" aria-label="পরের ছবি">›</button>' +
      '<div class="gl-cap"></div>';
    document.body.appendChild(box);
    document.body.classList.add("go-on");
    show(i);
    box.querySelector(".gl-x").focus();
    try { history.pushState({ gl: 1 }, ""); } catch (e) {}
  }
  function close(fromPop) {
    if (!box) return;
    box.remove(); box = null;
    document.body.classList.remove("go-on");
    if (!fromPop) { try { if (history.state && history.state.gl) history.back(); } catch (e) {} }
  }

  document.addEventListener("click", function (e) {
    var t = e.target.closest("[data-gal]");
    if (t) { e.preventDefault(); open(+t.dataset.gal || 0); return; }
    if (!box) return;
    if (e.target.closest(".gl-x") || e.target === box) close();
    else if (e.target.closest(".gl-prev")) show(idx - 1);
    else if (e.target.closest(".gl-next")) show(idx + 1);
  });
  document.addEventListener("keydown", function (e) {
    if (!box) return;
    if (e.key === "Escape") close();
    if (e.key === "ArrowLeft") show(idx - 1);
    if (e.key === "ArrowRight") show(idx + 1);
  });
  document.addEventListener("touchstart", function (e) { if (box) x0 = e.touches[0].clientX; }, { passive: true });
  document.addEventListener("touchend", function (e) {
    if (!box || x0 == null) return;
    var dx = e.changedTouches[0].clientX - x0; x0 = null;
    if (Math.abs(dx) > 50 && live() > 1) show(idx + (dx < 0 ? 1 : -1));
  });
  window.addEventListener("popstate", function () { close(true); });
})();
