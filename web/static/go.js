/* দামতুলনা — স্টোরে যাওয়ার লিংক।
   চাপ দিলে একটা বার্তা ৫ সেকেন্ড দেখায়, তারপর স্টোর নতুন ট্যাবে খোলে; দামতুলনার ট্যাব খোলাই থাকে।
   ব্রাউজার ট্যাপের ৫ সেকেন্ডের বেশি পরে নিজে থেকে ট্যাব খুলতে দেয় না, তাই ঠিক ৫ সেকেন্ড পূর্ণ হওয়ার মুহূর্তে খোলা হয়।
   কোনো ব্রাউজার তবু আটকে দিলে "স্টোরে যান" বাটন আসে।
   এই বার্তায় কোনো বিজ্ঞাপন বসানো যাবে না (AdSense ও Better Ads নিয়মে কাউন্টডাউনসহ বিজ্ঞাপন নিষিদ্ধ)। */
(function () {
  var WAIT = 5000, OPEN_AT = 4850;
  var box, timer, tick, toast, toastT;

  function bn(n) { return String(n).replace(/\d/g, function (d) { return "০১২৩৪৫৬৭৮৯"[d]; }); }
  function esc(s) { return String(s || "").replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  function showToast(name) {
    if (!toast) {
      toast = document.createElement("div");
      toast.className = "gonote";
      toast.setAttribute("role", "status");
      document.body.appendChild(toast);
    }
    toast.innerHTML = "<b>" + esc(name) + "</b> নতুন ট্যাবে খুলেছে। দামতুলনার এই পাতা খোলাই আছে, ফিরে এসে অন্য স্টোরের দাম দেখতে পারেন।" +
      '<button type="button" aria-label="বন্ধ করুন">✕</button>';
    toast.classList.add("on");
    clearTimeout(toastT);
    toastT = setTimeout(function () { toast.classList.remove("on"); }, 7000);
  }

  function close() {
    clearTimeout(timer); clearInterval(tick);
    if (box) { box.remove(); box = null; }
    document.body.classList.remove("go-on");
  }

  function open(url, name) {
    var w = window.open(url, "_blank");
    if (w) {
      try { w.opener = null; } catch (e) {}
      close();
      showToast(name);
      return true;
    }
    return false;
  }

  function start(a) {
    close();
    var url = a.href, name = a.dataset.go, seen = a.dataset.seen, t0 = Date.now();
    box = document.createElement("div");
    box.className = "gobox";
    box.innerHTML =
      '<div class="gocard" role="dialog" aria-modal="true" aria-labelledby="gotitle">' +
        '<div class="goic" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M14 3h7v7M10 14 21 3M19 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg></div>' +
        '<h2 id="gotitle">' + esc(name) + '-এ নিয়ে যাওয়া হচ্ছে</h2>' +
        '<p>স্টোরটি <b>নতুন ট্যাবে</b> খুলবে। দামতুলনার এই পাতা খোলাই থাকবে, ফিরে এসে অন্য স্টোরের দাম দেখতে পারবেন।</p>' +
        '<p class="gotip">কেনার আগে স্টোরে দাম, স্টক ও ওয়ারেন্টি মিলিয়ে নিন' + (seen ? ' (আমাদের এখানে দাম ' + esc(seen) + ')' : '') + '।</p>' +
        '<div class="gobar"><span></span></div>' +
        '<div class="goact"><span class="gocount" aria-live="polite">' + bn(5) + ' সেকেন্ড…</span>' +
        '<button type="button" class="gocancel">বাতিল</button></div>' +
      '</div>';
    document.body.appendChild(box);
    document.body.classList.add("go-on");
    var bar = box.querySelector(".gobar span"), count = box.querySelector(".gocount");
    requestAnimationFrame(function () { bar.style.transitionDuration = WAIT + "ms"; bar.style.width = "100%"; });
    box.querySelector(".gocancel").focus();
    tick = setInterval(function () {
      var left = Math.max(1, Math.ceil((WAIT - (Date.now() - t0)) / 1000));
      count.textContent = bn(left) + " সেকেন্ড…";
    }, 250);
    timer = setTimeout(function () {
      clearInterval(tick);
      if (open(url, name)) return;
      // ব্রাউজার আটকে দিয়েছে: এক ট্যাপে খোলার বাটন
      var act = box.querySelector(".goact");
      act.innerHTML = '<a class="btn gogo" href="' + esc(url) + '" target="_blank" rel="sponsored nofollow noopener">' + esc(name) + '-এ যান ›</a>' +
        '<button type="button" class="gocancel">বাতিল</button>';
      act.querySelector(".gogo").addEventListener("click", function () { setTimeout(function () { close(); showToast(name); }, 50); });
      act.querySelector(".gogo").focus();
    }, OPEN_AT);
  }

  document.addEventListener("click", function (e) {
    if (e.target.closest(".gonote button")) { toast.classList.remove("on"); return; }
    if (e.target.closest(".gocancel") || e.target === box) { close(); return; }
    var a = e.target.closest("a[data-go]");
    if (!a || e.ctrlKey || e.metaKey || e.shiftKey || e.button) return;  // Ctrl/মাঝের বাটনে আগের মতো সরাসরি
    e.preventDefault();
    start(a);
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && box) close(); });
})();
