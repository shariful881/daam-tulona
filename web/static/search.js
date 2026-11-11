/* হালকা সার্চ। পুরো তালিকা না নামিয়ে:
   ১) খোঁজা প্রতিটা শব্দের প্রথম ২ অক্ষরের ইনডেক্স ফাইল (s/p/<key>.json) — কোন শব্দ কোন প্রোডাক্টে আছে
   ২) মিলে যাওয়া প্রোডাক্টের টুকরো (s/d/<n>.json, ২০০টা করে) — নাম, দাম, র‍্যাঙ্ক
   টুকরোগুলোতে একই ক্যাটাগরির প্রোডাক্ট পাশাপাশি, তাই একটা খোঁজে সাধারণত ১-৩টা টুকরো লাগে; শেষে র‍্যাঙ্ক (বেশি স্টোর আগে) দিয়ে সাজানো।
   ব্যবহার: DTSearch("ryzen 5", {limit: 60, filter: fn}).then(list => …) */
(function () {
  var BASE = window.DT_BASE || "", cache = {};
  var SPLIT = /[\s\-_/,()\[\]+|:;"'.!?&*#@]+/;  // build.py-র SPLIT_RX-এর সাথে মিল রাখতে হবে
  function tokens(t) { return String(t || "").toLowerCase().split(SPLIT).filter(Boolean); }
  function key(t) { return Array.from(t).slice(0, 2).map(function (c) { return c.codePointAt(0).toString(16); }).join("_"); }
  function get(path) {
    if (!cache[path]) cache[path] = fetch(BASE + "/s/" + path + ".json").then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { delete cache[path]; return {}; });
    return cache[path];
  }
  function docs(nums) {
    var chunks = {};
    nums.forEach(function (n) { chunks[Math.floor(n / 200)] = 1; });
    return Promise.all(Object.keys(chunks).map(function (c) { return get("d/" + c).then(function (d) { return [+c, d]; }); })).then(function (all) {
      var by = {};
      all.forEach(function (x) { by[x[0]] = x[1]; });
      return nums.map(function (n) {
        var r = (by[Math.floor(n / 200)] || [])[n % 200];
        return r && { id: r[0], n: r[1], c: r[2], g: r[3], p: r[4], k: r[5], r: r[6] };
      }).filter(Boolean);
    });
  }
  window.DTSearch = function (q, opt) {
    opt = opt || {};
    var limit = opt.limit || 60, all = tokens(q);
    var long = all.filter(function (t) { return Array.from(t).length >= 2; });
    var short = all.filter(function (t) { return Array.from(t).length < 2; });  // "ryzen 5"-এর "5": নামের ভেতরে খোঁজা হয়
    if (!long.length) return Promise.resolve([]);
    return Promise.all(long.map(function (t) {
      return get("p/" + key(t)).then(function (sh) {
        var set = {};
        Object.keys(sh).forEach(function (w) { if (w.indexOf(t) === 0) sh[w].forEach(function (n) { set[n] = 1; }); });
        return set;
      });
    })).then(function (sets) {
      sets.sort(function (a, b) { return Object.keys(a).length - Object.keys(b).length; });
      var hit = Object.keys(sets[0]).map(Number).filter(function (n) { return sets.every(function (s) { return s[n]; }); }).sort(function (a, b) { return a - b; });
      // অনেক ফল হলে প্রথম ৩০০টা (একই ক্যাটাগরির গুচ্ছ) নামিয়ে র‍্যাঙ্ক অনুযায়ী সাজাই
      return docs(hit.slice(0, 300)).then(function (list) {
        list.sort(function (a, b) { return a.r - b.r; });
        if (short.length) list = list.filter(function (d) { var tk = tokens(d.n + " " + d.c); return short.every(function (s) { return tk.indexOf(s) > -1; }); });
        if (opt.filter) list = list.filter(opt.filter);
        return { items: list.slice(0, limit), total: hit.length };
      });
    }).then(function (r) { r.items.total = r.total; return r.items; });
  };
})();
