"""data/ থেকে পুরো স্ট্যাটিক সাইট dist/ ফোল্ডারে বানায়।

চালানো: BASE_URL=/daam-tulona SITE_URL=https://shariful881.github.io/daam-tulona python -m web.build
(GitHub Pages-এ রিপোর নামের সাব-ফোল্ডারে থাকে, তাই BASE_URL লাগে। নিজের ডোমেইনে BASE_URL ফাঁকা রাখুন।)
"""
import csv
import json
import os
import shutil
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DIST = ROOT / "dist"
BASE = os.environ.get("BASE_URL", "").rstrip("/")
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")

SPEC_NAMES = {"capacity": "ক্যাপাসিটি", "type": "টাইপ", "speed": "বাস স্পিড", "form": "ফর্ম ফ্যাক্টর",
              "interface": "ইন্টারফেস", "brand_cpu": "প্রসেসর ব্র্যান্ড", "model": "মডেল"}
STATUS = {"ok": ("স্টকে আছে", "ok"), "out": ("স্টক আউট", "out"), "pre": ("প্রি-অর্ডার", "out"),
          "upcoming": ("শীঘ্রই আসছে", "out"), "no_price": ("দাম জানতে কল করুন", "")}
BN_MONTHS = ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"]

ICONS = {
    "ram": '<svg viewBox="0 0 120 60"><rect x="2" y="6" width="116" height="40" rx="2" fill="#2f6d62"/><g fill="#1b1f1e"><rect x="10" y="12" width="18" height="24" rx="1"/><rect x="34" y="12" width="18" height="24" rx="1"/><rect x="68" y="12" width="18" height="24" rx="1"/><rect x="92" y="12" width="18" height="24" rx="1"/></g><rect x="4" y="46" width="54" height="8" fill="#c99a3a"/><rect x="62" y="46" width="54" height="8" fill="#c99a3a"/></svg>',
    "ssd": '<svg viewBox="0 0 120 50"><rect x="2" y="8" width="104" height="34" rx="3" fill="#2f6d62"/><rect x="106" y="14" width="12" height="22" fill="#c99a3a"/><rect x="14" y="15" width="30" height="20" rx="1" fill="#1b1f1e"/><rect x="52" y="15" width="30" height="20" rx="1" fill="#1b1f1e"/><circle cx="8" cy="25" r="3" fill="#eef2f1"/></svg>',
    "processor": '<svg viewBox="0 0 80 80"><rect x="10" y="10" width="60" height="60" rx="4" fill="#2f6d62"/><rect x="22" y="22" width="36" height="36" rx="2" fill="#c99a3a"/><g stroke="#5b706c" stroke-width="3"><path d="M20 2v8M32 2v8M44 2v8M56 2v8M20 70v8M32 70v8M44 70v8M56 70v8M2 20h8M2 32h8M2 44h8M2 56h8M70 20h8M70 32h8M70 44h8M70 56h8"/></g></svg>',
}


def taka(n):
    return "৳" + f"{int(n):,}" if n is not None else "—"


def bn_date(d: str) -> str:
    y, m, day = d[:10].split("-")
    return f"{int(day)} {BN_MONTHS[int(m) - 1]} {y}"


def icon_for(cat):
    return ICONS["ram"] if "ram" in cat else ICONS.get(cat, ICONS["ssd"])


def sparkline(points: list[tuple[str, int]]) -> str:
    if len(points) < 2:
        return ""
    w, h, pad = 320, 90, 18
    vals = [v for _, v in points]
    lo, hi = min(vals), max(vals)
    span = max(1, hi - lo)
    xs = [pad + i * (w - 2 * pad) / (len(points) - 1) for i in range(len(points))]
    ys = [h - pad - (v - lo) * (h - 2 * pad) / span for v in vals]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area = f"{xs[0]:.1f},{h - pad} " + line + f" {xs[-1]:.1f},{h - pad}"
    return (f'<svg class="spark" viewBox="0 0 {w} {h}" role="img" aria-label="দামের ইতিহাস">'
            f'<polygon points="{area}" fill="var(--best-soft)"/>'
            f'<polyline points="{line}" fill="none" stroke="var(--best)" stroke-width="2"/>'
            f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="3.5" fill="var(--best)"/>'
            f'<text x="{pad}" y="12">{taka(hi)}</text><text x="{pad}" y="{h - 3}">{taka(lo)}</text>'
            f'<text x="{w - pad}" y="{h - 3}" text-anchor="end">{bn_date(points[-1][0])}</text></svg>')


def blurb(p, cat):
    s = p["specs"]
    if "ram" in p["category"]:
        bits = " ".join(x for x in [s.get("capacity"), s.get("type"), s.get("speed")] if x)
        where = "ল্যাপটপের" if p["category"] == "laptop-ram" else "ডেস্কটপের"
        return (f"{p['brand']}-এর {bits} {where} জন্য র‍্যাম। কেনার আগে আপনার {where[:-2]} কোন টাইপ ও স্পিড সাপোর্ট করে দেখে নিন। "
                f"একই স্পিডের দুইটা স্টিক লাগালে ডুয়াল চ্যানেলে বেশি পারফরম্যান্স পাওয়া যায়।")
    if p["category"] == "ssd":
        return (f"{p['brand']}-এর {s.get('capacity', '')} {s.get('interface', '')} এসএসডি। পুরনো হার্ডডিস্কের জায়গায় এসএসডি দিলে "
                f"কম্পিউটার চালু হওয়া আর সফটওয়্যার খোলা অনেক দ্রুত হয়। মাদারবোর্ডে কোন স্লট (M.2 বা SATA) আছে আগে দেখে নিন।")
    if p["category"] == "processor":
        return (f"{p['name']}। প্রসেসর কেনার আগে মাদারবোর্ডের সকেট আর চিপসেট মিলিয়ে নিন। বক্সে কুলার আছে কিনা স্টোরে জিজ্ঞেস করুন।")
    return p["name"]


def main():
    t0 = time.time()
    stores = json.loads((ROOT / "config/stores.json").read_text())["stores"]
    cats = {c["slug"]: c for c in json.loads((ROOT / "config/categories.json").read_text())["categories"]}
    products = json.loads((DATA / "products.json").read_text())
    offers = json.loads((DATA / "offers.json").read_text())
    health = json.loads((DATA / "health.json").read_text())
    suggestions = json.loads((DATA / "suggestions.json").read_text()) if (DATA / "suggestions.json").exists() else []
    today = health["date"]
    updated = bn_date(today) + ", " + health["scraped_at"][11:16]
    enabled = [s for s, v in stores.items() if v["enabled"]]

    history = defaultdict(lambda: defaultdict(list))
    if (DATA / "history.csv").exists():
        with (DATA / "history.csv").open() as f:
            for r in csv.DictReader(f):
                if r["in_stock"] == "1":
                    history[r["product"]][r["date"]].append(int(r["price"]))

    env = Environment(loader=FileSystemLoader(ROOT / "web/templates"), autoescape=select_autoescape(["html"]))
    env.filters["taka"] = taka
    common = {"base": BASE, "stores": stores, "updated": updated, "build_id": int(t0), "spec_names": SPEC_NAMES}

    # প্রতিটা প্রোডাক্টের সারাংশ
    items = {}
    for pid, so in offers.items():
        p = products.get(pid)
        if not p or p["category"] not in cats:
            continue
        live = sorted(((s, o) for s, o in so.items() if o.get("in_stock") and o.get("price")), key=lambda x: x[1]["price"])
        best = {"store": live[0][0], "price": live[0][1]["price"], "url": live[0][1]["url"]} if live else None
        saving = live[-1][1]["price"] - live[0][1]["price"] if len(live) > 1 else 0
        f = [p["specs"].get(k) for k in ("capacity", "type", "interface", "brand_cpu")]
        items[pid] = {"id": pid, "name": p["name"], "category": p["category"], "cat_name": cats[p["category"]]["name_bn"],
                      "best": best, "saving": saving, "store_count": len([o for o in so.values() if o.get("price")]),
                      "live_count": len(live), "facets": " ".join(x for x in f if x), "created": p["created"], "specs": p["specs"]}

    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "static").mkdir(parents=True)
    shutil.copy(ROOT / "web/static/style.css", DIST / "static/style.css")
    urls = []

    def write(path, template, **ctx):
        out = DIST / path / "index.html" if path else DIST / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(env.get_template(template).render(**common, **ctx))
        if not ctx.get("noindex"):
            urls.append(f"{SITE_URL}/{path + '/' if path else ''}")

    # প্রোডাক্ট পেজ
    by_cat = defaultdict(list)
    for it in items.values():
        by_cat[it["category"]].append(it)
    for pid, it in items.items():
        p, cat, so = products[pid], cats[it["category"]], offers[pid]
        rows = []
        for s in enabled + [s for s in so if s not in enabled]:
            o = so.get(s)
            label, cls = STATUS.get(o["status"], ("", "")) if o else ("", "")
            if o and o.get("stale"):
                label += " (আগের দাম)"
            rows.append({"store": s, "offer": o, "label": label, "cls": cls,
                         "is_best": bool(it["best"] and o and it["best"]["store"] == s and it["saving"] > 0)})
        rows.sort(key=lambda r: (r["offer"] is None, not (r["offer"] and r["offer"]["in_stock"]), (r["offer"] or {}).get("price") or 10**9))
        alts = [a for a in by_cat[it["category"]] if a["id"] != pid and a["best"]
                and all(a["specs"].get(k) == it["specs"].get(k) for k in ("capacity", "type", "form", "interface", "brand_cpu") if it["specs"].get(k))]
        alts = [{"id": a["id"], "name": a["name"], "price": a["best"]["price"], "store": a["best"]["store"]}
                for a in sorted(alts, key=lambda a: a["best"]["price"])[:6]]
        pts = sorted((d, min(v)) for d, v in history[pid].items())[-90:]
        best = it["best"]
        faq = [
            (f"{p['name']} এর দাম কত?",
             f"আজকের হিসাবে সর্বনিম্ন দাম {taka(best['price'])}, {stores[best['store']]['name']}-এ।" if best
             else "এই মুহূর্তে আমাদের তালিকার কোনো স্টোরে এটা স্টকে নেই।"),
            ("এই দাম কখন আপডেট হয়?", "প্রতিদিন রাতে সব স্টোর থেকে দাম নতুন করে সংগ্রহ করা হয়।"),
            ("কোন স্টোর থেকে কেনা ভালো?", "দামের পাশাপাশি ওয়ারেন্টি, ডেলিভারি আর বাসার কাছে শাখা আছে কিনা দেখে নিন। স্টোরের নামে চাপ দিলে তাদের পেজে যাবেন।"),
        ]
        jsonld = {"@context": "https://schema.org", "@type": "Product", "name": p["name"], "brand": {"@type": "Brand", "name": p["brand"]},
                  "category": cat["name_en"]}
        priced = [o for o in so.values() if o.get("price") and o.get("in_stock")]
        if priced:
            jsonld["offers"] = {"@type": "AggregateOffer", "priceCurrency": "BDT", "offerCount": len(priced),
                                "lowPrice": min(o["price"] for o in priced), "highPrice": max(o["price"] for o in priced)}
        write(f"p/{pid}", "product.html", p=p, cat=cat, best=best, saving=it["saving"], live_count=it["live_count"],
              store_rows=rows, alts=alts, spark=sparkline(pts), icon=icon_for(it["category"]), blurb=blurb(p, cat), faq=faq,
              jsonld=json.dumps(jsonld, ensure_ascii=False), buy=bool(best),
              title=f"{p['name']} দাম বাংলাদেশে" + (f" | {taka(best['price'])} থেকে" if best else ""),
              description=f"{p['name']} এর দাম {len(enabled)}টি স্টোরে মিলিয়ে দেখুন।" + (f" আজকের সর্বনিম্ন দাম {taka(best['price'])}।" if best else ""),
              canonical=f"{SITE_URL}/p/{pid}/" if SITE_URL else None)

    # ক্যাটাগরি পেজ
    cat_cards = []
    for slug, cat in cats.items():
        lst = sorted(by_cat.get(slug, []), key=lambda i: (i["best"] is None, (i["best"] or {}).get("price", 0)))
        facets = sorted({f for i in lst for f in i["facets"].split() if f}, key=lambda x: (len(x), x))[:14]
        write(f"c/{slug}", "category.html", cat=cat, items=lst, facets=facets, store_count=len(enabled),
              title=f"{cat['name_bn']} দাম বাংলাদেশে | {cat['name_en']} Price in BD",
              description=f"{len(lst)}টি {cat['name_bn']} এর দাম {len(enabled)}টি স্টোরে মিলিয়ে দেখুন।",
              canonical=f"{SITE_URL}/c/{slug}/" if SITE_URL else None)
        priced = [i["best"]["price"] for i in lst if i["best"]]
        if lst:
            cat_cards.append({"slug": slug, "name_bn": cat["name_bn"], "count": len(lst), "min": min(priced) if priced else None})

    vals = list(items.values())
    deals = sorted([i for i in vals if i["saving"] > 0], key=lambda i: -i["saving"])[:10]
    fresh_all = sorted([i for i in vals if i["created"] == today], key=lambda i: i["name"])
    fresh = fresh_all[:10] if len(fresh_all) < len(vals) else []
    write("", "home.html", cats=cat_cards, deals=deals, fresh=fresh, total=len(vals),
          store_names=", ".join(stores[s]["name"] for s in enabled),
          title="দামতুলনা | কম্পিউটার পার্টসের দাম তুলনা বাংলাদেশে",
          description=f"র‍্যাম, এসএসডি, প্রসেসরের দাম {len(enabled)}টি স্টোরে মিলিয়ে দেখুন: " + ", ".join(stores[s]["name"] for s in enabled) + "।",
          canonical=f"{SITE_URL}/" if SITE_URL else None)
    write("search", "search.html", title="খুঁজুন | দামতুলনা", description="প্রোডাক্ট খুঁজুন", noindex=True)
    stats = {"total": len(vals), "multi": sum(1 for i in vals if i["store_count"] > 1), "new": len(fresh_all)}
    write("admin", "admin.html", health=health, stats=stats, suggestions=suggestions, fresh=fresh_all[:150],
          title="অ্যাডমিন | দামতুলনা", description="", noindex=True)

    search = [{"id": i["id"], "n": i["name"], "c": i["cat_name"], "p": (i["best"] or {}).get("price"), "k": i["store_count"],
               "s": (i["name"] + " " + i["cat_name"]).lower()} for i in vals]
    (DIST / "search.json").write_text(json.dumps(search, ensure_ascii=False, separators=(",", ":")))
    (DIST / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      + "".join(f"<url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    (DIST / "robots.txt").write_text(f"User-agent: *\nDisallow: {BASE}/admin/\nSitemap: {SITE_URL}/sitemap.xml\n")
    (DIST / ".nojekyll").write_text("")
    print(f"{len(urls)}টি পেজ তৈরি হয়েছে, {time.time() - t0:.1f} সেকেন্ডে")


if __name__ == "__main__":
    main()
