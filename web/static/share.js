/* বাজার আপডেট: ইনফোগ্রাফিক শেয়ার, সংখ্যা গোনার অ্যানিমেশন, ক্যাটাগরির ট্যাব */
(function () {
  var B = "০১২৩৪৫৬৭৮৯";
  function bn(n) { return Number(n).toLocaleString("en-IN").replace(/\d/g, function (d) { return B[d]; }); }
  if (!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches)) {
    document.querySelectorAll(".ig [data-n]").forEach(function (t) {
      var n = +t.getAttribute("data-n"), s = null;
      function f(ts) { s = s || ts; var p = Math.min(1, (ts - s) / 900); t.textContent = bn(Math.round(n * (1 - Math.pow(1 - p, 3)))); if (p < 1) requestAnimationFrame(f); }
      requestAnimationFrame(f);
    });
  }
  // ক্যাটাগরির ট্যাব
  document.querySelectorAll("[data-btabs]").forEach(function (bar) {
    bar.addEventListener("click", function (e) {
      var b = e.target.closest("[data-btab]"); if (!b) return;
      bar.querySelectorAll("[data-btab]").forEach(function (x) { x.setAttribute("aria-selected", x === b ? "true" : "false"); });
      document.querySelectorAll("[data-bpanel]").forEach(function (p) { p.hidden = p.getAttribute("data-bpanel") !== b.getAttribute("data-btab"); });
    });
  });
  // শেয়ার
  var box = document.querySelector("[data-share]"); if (!box) return;
  var url = box.getAttribute("data-url"), title = box.getAttribute("data-title"), img = box.getAttribute("data-img");
  var msg = box.querySelector(".shmsg");
  function say(t) { if (msg) { msg.textContent = t; msg.hidden = false; setTimeout(function () { msg.hidden = true; }, 3000); } }
  function track(how) { try { if (window.gtag) gtag("event", "share", { method: how, content_type: "bazar", item_id: location.pathname }); } catch (e) {} }
  function copy() {
    var u = url + "?s=link";
    (navigator.clipboard ? navigator.clipboard.writeText(u) : Promise.reject()).then(function () { say("লিংক কপি হয়েছে"); },
      function () { window.prompt("লিংকটা কপি করুন", u); });
    track("copy");
  }
  box.addEventListener("click", function (e) {
    var b = e.target.closest("[data-sh]"); if (!b) return;
    var how = b.getAttribute("data-sh");
    if (how === "copy") { e.preventDefault(); copy(); return; }
    if (how === "native") {
      e.preventDefault(); track("native");
      var data = { title: title, text: title, url: url + "?s=share" };
      if (!navigator.share) { copy(); return; }
      fetch(img).then(function (r) { return r.blob(); }).then(function (bl) {
        var f = new File([bl], "damtulona-bazar.jpg", { type: "image/jpeg" });
        if (navigator.canShare && navigator.canShare({ files: [f] })) return navigator.share({ files: [f], title: title, text: title + "\n" + url + "?s=share" });
        return navigator.share(data);
      }).catch(function () { return navigator.share(data).catch(function () {}); });
      return;
    }
    track(how);
  });
  var nat = box.querySelector('[data-sh="native"]'); if (nat && !navigator.share) nat.hidden = true;
})();
