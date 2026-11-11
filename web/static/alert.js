/* "দাম কমলে জানান" ফর্ম: নাম + মোবাইল নম্বর + (ইচ্ছা হলে) টার্গেট দাম।
   লিডের ঠিকানা (Google Sheet-এর Apps Script) সেট থাকলে সেখানে জমা হয়;
   না থাকলে সাইটের WhatsApp নম্বরে একই তথ্য দিয়ে মেসেজ খোলে, যাতে কোনো লিড হারায় না। */
(function () {
  var box = document.getElementById("alertbox"), btn = document.getElementById("alertbtn");
  if (!box || !btn) return;
  var cfg = window.DT_LEAD || {}, form = box.querySelector("form"), msg = box.querySelector(".almsg");
  function bn(s) { return String(s).replace(/\d/g, function (d) { return "০১২৩৪৫৬৭৮৯"[d]; }); }
  function en(s) { return String(s).replace(/[০-৯]/g, function (d) { return "০১২৩৪৫৬৭৮৯".indexOf(d); }); }
  btn.addEventListener("click", function () {
    box.hidden = !box.hidden; btn.setAttribute("aria-expanded", String(!box.hidden));
    if (!box.hidden) form.elements.name.focus();
  });
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (form.elements.website.value) return;  // বট ধরার ফাঁদ
    msg.textContent = ""; msg.className = "almsg";
    var name = form.elements.name.value.trim();
    var phone = en(form.elements.phone.value).replace(/[\s\-()]/g, "").replace(/^\+?88/, "");
    var target = en(form.elements.target.value).replace(/[^\d]/g, "");
    if (name.length < 2) { msg.textContent = "আপনার নাম লিখুন।"; msg.className = "almsg err"; return; }
    if (!/^01[3-9]\d{8}$/.test(phone)) { msg.textContent = "সঠিক মোবাইল নম্বর দিন (যেমন ০১৭১২৩৪৫৬৭৮)।"; msg.className = "almsg err"; return; }
    if (!form.elements.ok.checked) { msg.textContent = "জানানোর জন্য সম্মতির ঘরে টিক দিন।"; msg.className = "almsg err"; return; }
    var d = { name: name, phone: phone, target: target ? +target : "", product: cfg.product, url: location.origin + location.pathname,
              price: cfg.price || "", store: cfg.store || "", category: cfg.category || "", time: new Date().toISOString() };
    var sub = form.querySelector("button[type=submit]"); sub.disabled = true;
    var done = function () {
      form.hidden = true;
      msg.className = "almsg ok";
      msg.textContent = "ধন্যবাদ, " + name + "! " + (target ? "দাম ৳" + bn(Number(target).toLocaleString("en-US")) + " বা তার কম হলে" : "দাম কমলে") + " আমরা " + bn(phone) + " নম্বরে জানাব।";
      try { localStorage.setItem("dt_alert_" + cfg.id, "1"); } catch (x) {}
    };
    if (cfg.endpoint) {
      fetch(cfg.endpoint, { method: "POST", mode: "no-cors", headers: { "Content-Type": "text/plain;charset=utf-8" }, body: JSON.stringify(d) })
        .then(done, function () { sub.disabled = false; msg.className = "almsg err"; msg.textContent = "পাঠানো যায়নি, ইন্টারনেট দেখে আবার চেষ্টা করুন।"; });
    } else if (cfg.wa) {
      var t = "দাম কমলে জানাবেন\nপ্রোডাক্ট: " + d.product + "\nএখনকার দাম: " + (d.price ? "৳" + d.price : "-") + "\nটার্গেট দাম: " + (d.target ? "৳" + d.target : "যেকোনো কমা") +
              "\nনাম: " + name + "\nমোবাইল: " + phone + "\n" + d.url;
      window.open("https://wa.me/88" + String(cfg.wa).replace(/\D/g, "").replace(/^88/, "") + "?text=" + encodeURIComponent(t), "_blank", "noopener");
      done();
    }
  });
  try { if (localStorage.getItem("dt_alert_" + cfg.id)) btn.classList.add("on"); } catch (x) {}
})();
