/* দামতুলনা — স্টোরে যাওয়ার লিংক।
   লিংক সাথে সাথে নতুন ট্যাবে খোলে (কোনো অপেক্ষা বা পপআপ নেই)।
   শুধু এই ট্যাবে নিচে একটা ছোট বার্তা দেখায়, যাতে ক্রেতা ফিরে এসে বুঝতে পারেন কী হলো। */
(function () {
  var t, box;
  document.addEventListener("click", function (e) {
    var a = e.target.closest("a[data-go]");
    if (!a) return;
    if (!box) {
      box = document.createElement("div");
      box.className = "gonote";
      box.setAttribute("role", "status");
      document.body.appendChild(box);
    }
    box.innerHTML = "<b>" + a.dataset.go + "</b> নতুন ট্যাবে খুলেছে। কেনার আগে সেখানে দাম ও স্টক মিলিয়ে নিন।" +
      (a.dataset.seen ? " এখানে দেখানো দাম " + a.dataset.seen + "।" : "") +
      '<button type="button" aria-label="বন্ধ করুন">✕</button>';
    box.classList.add("on");
    clearTimeout(t);
    t = setTimeout(function () { box.classList.remove("on"); }, 7000);
  });
  document.addEventListener("click", function (e) {
    if (box && e.target.closest(".gonote button")) box.classList.remove("on");
  });
})();
