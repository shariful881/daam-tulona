/* "দাম কমলে জানান" ফর্ম: শুধু নাম আর মোবাইল নম্বর।
   - একই প্রোডাক্টে একটা নম্বর একবারই জমা হয় (এই ফোনে মনে রাখা হয়); অন্য প্রোডাক্টের জন্য আবার দেওয়া যায়।
   - নাম/নম্বর একবার দিলে পরের প্রোডাক্টে আগে থেকে ভরা থাকে।
   - Google Sheet-এ প্রতিটা নম্বর একটাই সারি; নতুন প্রোডাক্ট এলে সেই সারিতেই ক্যাটাগরি ও প্রোডাক্টের নাম যোগ হয় (Apps Script দেখুন: অ্যাডমিন → সেটিং)।
   - Sheet-এর ঠিকানা না থাকলে সাইটের WhatsApp নম্বরে মেসেজ খোলে, যাতে লিড হারায় না। */
(function () {
  var box = document.getElementById("alertbox"), btn = document.getElementById("alertbtn");
  if (!box || !btn) return;
  var cfg = window.DT_LEAD || {}, form = box.querySelector("form"), msg = box.querySelector(".almsg");
  var KEY = "dt_alert_" + cfg.id, ME = "dt_alert_me";
  function bn(s) { return String(s).replace(/\d/g, function (d) { return "০১২৩৪৫৬৭৮৯"[d]; }); }
  function en(s) { return String(s).replace(/[০-৯]/g, function (d) { return "০১২৩৪৫৬৭৮৯".indexOf(d); }); }
  function get(k) { try { return localStorage.getItem(k); } catch (x) { return null; } }
  function put(k, v) { try { localStorage.setItem(k, v); } catch (x) {} }
  function already(phone) {
    form.hidden = true; msg.className = "almsg ok";
    msg.textContent = "এই প্রোডাক্টের জন্য " + bn(phone) + " নম্বরটা আগেই জমা আছে। দাম কমলে জানাব।";
  }
  try { var me = JSON.parse(get(ME) || "{}"); if (me.name) form.elements.name.value = me.name; if (me.phone) form.elements.phone.value = me.phone; } catch (x) {}

  btn.addEventListener("click", function () {
    box.hidden = !box.hidden; btn.setAttribute("aria-expanded", String(!box.hidden));
    if (!box.hidden && get(KEY)) { already(get(KEY)); return; }
    if (!box.hidden) (form.elements.name.value ? form.elements.phone : form.elements.name).focus();
  });
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (form.elements.website.value) return;  // বট ধরার ফাঁদ
    msg.textContent = ""; msg.className = "almsg";
    var name = form.elements.name.value.trim();
    var phone = en(form.elements.phone.value).replace(/[\s\-()]/g, "").replace(/^\+?88/, "");
    if (name.length < 2) { msg.textContent = "আপনার নাম লিখুন।"; msg.className = "almsg err"; return; }
    if (!/^01[3-9]\d{8}$/.test(phone)) { msg.textContent = "সঠিক মোবাইল নম্বর দিন (যেমন ০১৭১২৩৪৫৬৭৮)।"; msg.className = "almsg err"; return; }
    if (get(KEY) === phone) { already(phone); return; }
    var d = { name: name, phone: phone, product: cfg.product, category: cfg.category || "", url: location.origin + location.pathname,
              price: cfg.price || "", time: new Date().toISOString() };
    var sub = form.querySelector("button[type=submit]"); sub.disabled = true;
    var done = function () {
      put(KEY, phone); put(ME, JSON.stringify({ name: name, phone: phone }));
      form.hidden = true; msg.className = "almsg ok";
      msg.textContent = "ধন্যবাদ, " + name + "! দাম কমলে " + bn(phone) + " নম্বরে জানাব।";
      btn.classList.add("on");
    };
    if (cfg.endpoint) {
      fetch(cfg.endpoint, { method: "POST", mode: "no-cors", headers: { "Content-Type": "text/plain;charset=utf-8" }, body: JSON.stringify(d) })
        .then(done, function () { sub.disabled = false; msg.className = "almsg err"; msg.textContent = "পাঠানো যায়নি, ইন্টারনেট দেখে আবার চেষ্টা করুন।"; });
    } else if (cfg.wa) {
      var t = "দাম কমলে জানাবেন\nনাম: " + name + "\nমোবাইল: " + phone + "\nক্যাটাগরি: " + d.category + "\nপ্রোডাক্ট: " + d.product + "\n" + d.url;
      window.open("https://wa.me/88" + String(cfg.wa).replace(/\D/g, "").replace(/^88/, "") + "?text=" + encodeURIComponent(t), "_blank", "noopener");
      done();
    }
  });
  if (get(KEY)) btn.classList.add("on");
})();
