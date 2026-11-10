/* দামতুলনা — তুলনার তালিকা (ব্রাউজারে সেভ থাকে, সর্বোচ্চ ৪টি, একই ক্যাটাগরির) */
(function () {
  var KEY = "dt-compare", MAX = 4, base = window.DT_BASE || "";
  function load() { try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch (e) { return []; } }
  function save(list) { try { localStorage.setItem(KEY, JSON.stringify(list)); } catch (e) {} }
  window.DTCompare = { load: load, save: save, MAX: MAX };

  function bn(n) { return String(n).replace(/\d/g, function (d) { return "০১২৩৪৫৬৭৮৯"[d]; }); }

  function renderBar() {
    var list = load(), bar = document.getElementById("cmpbar");
    if (!bar) return;
    var onComparePage = !!document.getElementById("cmpapp");
    bar.hidden = list.length === 0 || onComparePage;
    document.body.classList.toggle("cmp-on", !bar.hidden);
    document.getElementById("cmpcount").textContent = bn(list.length) + "টি প্রোডাক্ট তুলনার তালিকায়" + (list.length < 2 ? " · আরেকটা যোগ করুন" : "");
    document.getElementById("cmpgo").href = base + "/compare/?ids=" + list.map(function (x) { return x.id; }).join(",");
    var btn = document.querySelector(".cmpbtn");
    if (btn) {
      var on = list.some(function (x) { return x.id === btn.dataset.id; });
      btn.classList.toggle("on", on);
      btn.textContent = on ? "✓ তুলনার তালিকায় আছে (সরাতে চাপুন)" : "+ তুলনায় যোগ করুন";
    }
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest(".cmpbtn");
    if (btn) {
      var list = load(), id = btn.dataset.id, msg = document.querySelector(".cmpmsg");
      msg.hidden = true;
      if (list.some(function (x) { return x.id === id; })) {
        list = list.filter(function (x) { return x.id !== id; });
      } else {
        if (list.length && list[0].cat !== btn.dataset.cat) {
          list = [];
          msg.textContent = "আগের তালিকাটা অন্য ক্যাটাগরির ছিল, তাই নতুন করে শুরু হলো। একই ধরনের প্রোডাক্টই তুলনা করা যায়।";
          msg.hidden = false;
        }
        if (list.length >= MAX) {
          msg.textContent = "একসাথে সর্বোচ্চ " + bn(MAX) + "টি তুলনা করা যায়। নিচের বার থেকে তালিকা মুছে আবার যোগ করুন।";
          msg.hidden = false;
          return;
        }
        list.push({ id: id, cat: btn.dataset.cat, name: btn.dataset.name });
      }
      save(list); renderBar();
    }
    if (e.target.id === "cmpclear") { save([]); renderBar(); }
  });
  document.addEventListener("DOMContentLoaded", renderBar);
  if (document.readyState !== "loading") renderBar();
})();
