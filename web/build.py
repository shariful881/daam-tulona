"""data/ থেকে পুরো স্ট্যাটিক সাইট dist/ ফোল্ডারে বানায়।

চালানো: BASE_URL=/daam-tulona SITE_URL=https://shariful881.github.io/daam-tulona python -m web.build
(GitHub Pages-এ রিপোর নামের সাব-ফোল্ডারে থাকে, তাই BASE_URL লাগে। নিজের ডোমেইনে BASE_URL ফাঁকা রাখুন।)
"""
import csv
import json
import os
import re
import shutil
import time
import zlib
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DIST = ROOT / "dist"
BASE = os.environ.get("BASE_URL", "").rstrip("/")
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")
PER_PAGE = 48

SPEC_NAMES = {"capacity": "ক্যাপাসিটি", "type": "টাইপ", "speed": "বাস স্পিড", "form": "ফর্ম ফ্যাক্টর",
              "interface": "ইন্টারফেস", "brand_cpu": "প্রসেসর ব্র্যান্ড", "model": "মডেল"}
SECTION_BN = {"key features": "মূল বৈশিষ্ট্য", "warranty information": "ওয়ারেন্টি", "physical specification": "শারীরিক বৈশিষ্ট্য",
              "physical dimension": "আকার", "display": "ডিসপ্লে", "processor": "প্রসেসর", "memory": "মেমরি", "storage": "স্টোরেজ",
              "camera": "ক্যামেরা", "battery": "ব্যাটারি", "connectivity": "কানেক্টিভিটি", "graphics": "গ্রাফিক্স",
              "keyboard & touchpad": "কিবোর্ড ও টাচপ্যাড", "audio": "অডিও", "network": "নেটওয়ার্ক", "power": "পাওয়ার",
              "general": "সাধারণ", "basic information": "সাধারণ তথ্য", "ports & slots": "পোর্ট ও স্লট", "operating system": "অপারেটিং সিস্টেম"}
STATUS = {"ok": ("স্টকে আছে", "ok"), "out": ("স্টক আউট", "out"), "pre": ("প্রি-অর্ডার", "out"),
          "upcoming": ("শীঘ্রই আসছে", "out"), "no_price": ("দাম জানতে কল করুন", "")}
BN_MONTHS = ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"]
BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")

ICONS = {
    "ram": '<svg viewBox="0 0 120 60"><rect x="2" y="6" width="116" height="40" rx="2" fill="#2f6d62"/><g fill="#1b1f1e"><rect x="10" y="12" width="18" height="24" rx="1"/><rect x="34" y="12" width="18" height="24" rx="1"/><rect x="68" y="12" width="18" height="24" rx="1"/><rect x="92" y="12" width="18" height="24" rx="1"/></g><rect x="4" y="46" width="54" height="8" fill="#c99a3a"/><rect x="62" y="46" width="54" height="8" fill="#c99a3a"/></svg>',
    "chip": '<svg viewBox="0 0 80 80"><rect x="10" y="10" width="60" height="60" rx="4" fill="#2f6d62"/><rect x="22" y="22" width="36" height="36" rx="2" fill="#c99a3a"/><g stroke="#5b706c" stroke-width="3"><path d="M20 2v8M32 2v8M44 2v8M56 2v8M20 70v8M32 70v8M44 70v8M56 70v8M2 20h8M2 32h8M2 44h8M2 56h8M70 20h8M70 32h8M70 44h8M70 56h8"/></g></svg>',
    "box": '<svg viewBox="0 0 120 80"><rect x="10" y="12" width="100" height="56" rx="6" fill="#2f6d62"/><rect x="22" y="24" width="50" height="8" rx="2" fill="#c99a3a"/><rect x="22" y="38" width="30" height="6" rx="2" fill="#eef2f1" opacity=".6"/><circle cx="92" cy="40" r="10" fill="#c99a3a"/></svg>',
    "phone": '<svg viewBox="0 0 60 100"><rect x="8" y="4" width="44" height="92" rx="8" fill="#2f6d62"/><rect x="13" y="14" width="34" height="66" rx="2" fill="#c99a3a"/><circle cx="30" cy="88" r="3" fill="#eef2f1"/></svg>',
    "screen": '<svg viewBox="0 0 120 90"><rect x="6" y="6" width="108" height="64" rx="4" fill="#2f6d62"/><rect x="12" y="12" width="96" height="52" fill="#c99a3a"/><rect x="52" y="70" width="16" height="10" fill="#5b706c"/><rect x="36" y="80" width="48" height="5" rx="2" fill="#5b706c"/></svg>',
}
GROUP_ICON = {"computer-parts": "chip", "mobile-tablet": "phone", "monitor": "screen", "laptop-desktop": "screen"}


def taka(n):
    return "৳" + f"{int(n):,}" if n is not None else "—"


def bn_num(n):
    return f"{int(n):,}".translate(BN_DIGITS)


def bn_date(d: str) -> str:
    y, m, day = d[:10].split("-")
    return f"{int(day)} {BN_MONTHS[int(m) - 1]} {y}"


def icon_for(leaf, group):
    if "ram" in leaf:
        return ICONS["ram"]
    return ICONS[GROUP_ICON.get(group, "box")]


def sparkline(changes: list[tuple[str, int]], today: str) -> str:
    """দাম বদলের তারিখগুলো থেকে প্রতিদিনের ধারা বানিয়ে শেষ ৯০ দিনের চার্ট।"""
    if not changes:
        return ""
    end = date.fromisoformat(today)
    start = max(date.fromisoformat(changes[0][0]), end - timedelta(days=90))
    pts, i, cur = [], 0, None
    d = start
    ch = dict(changes)
    keys = sorted(ch)
    for k in keys:
        if k <= start.isoformat():
            cur = ch[k]
    while d <= end:
        ds = d.isoformat()
        if ds in ch:
            cur = ch[ds]
        if cur is not None:
            pts.append((ds, cur))
        d += timedelta(days=1)
    if len(pts) < 2:
        return ""
    w, h, pad = 320, 90, 18
    vals = [v for _, v in pts]
    lo, hi = min(vals), max(vals)
    if hi == lo:  # দাম অপরিবর্তিত: মাঝখানে সমান রেখা
        lo, hi = lo - 1, hi + 1
    xs = [pad + i * (w - 2 * pad) / (len(pts) - 1) for i in range(len(pts))]
    ys = [h - pad - (v - lo) * (h - 2 * pad) / (hi - lo) for v in vals]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area = f"{xs[0]:.1f},{h - pad} " + line + f" {xs[-1]:.1f},{h - pad}"
    return (f'<svg class="spark" viewBox="0 0 {w} {h}" role="img" aria-label="দামের ইতিহাস">'
            f'<polygon points="{area}" fill="var(--best-soft)"/>'
            f'<polyline points="{line}" fill="none" stroke="var(--best)" stroke-width="2"/>'
            f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="3.5" fill="var(--best)"/>'
            f'<text x="{pad}" y="12">{taka(max(vals))}</text><text x="{pad}" y="{h - 3}">{taka(min(vals))}</text>'
            f'<text x="{w - pad}" y="{h - 3}" text-anchor="end">{bn_date(pts[-1][0])}</text></svg>')


def daily_min(per_store: dict, today: str) -> list[tuple[str, int]]:
    """প্রতিটা স্টোরের শেষ জানা দাম দিন ধরে টেনে নিয়ে, প্রতিদিনের সর্বনিম্ন স্টকে-থাকা দাম।"""
    if not per_store:
        return []
    start = min(d for ch in per_store.values() for d, _ in ch)
    end = date.fromisoformat(today)
    series, d = [], max(date.fromisoformat(start), end - timedelta(days=120))
    state = {}
    for sid, ch in per_store.items():
        for ds, v in sorted(ch):
            if ds <= d.isoformat():
                state[sid] = v
    idx = {sid: dict(ch) for sid, ch in per_store.items()}
    while d <= end:
        ds = d.isoformat()
        for sid, m in idx.items():
            if ds in m:
                state[sid] = m[ds]
        live = [v for v in state.values() if v]
        if live:
            series.append((ds, min(live)))
        d += timedelta(days=1)
    # চার্ট শুধু বদলের বিন্দু চায়; একই দাম পরপর থাকলে বাদ
    out = []
    for ds, v in series:
        if not out or out[-1][1] != v:
            out.append((ds, v))
    if series and out[-1][0] != series[-1][0]:
        out.append(series[-1])
    return out


def warranty_bn(w: str | None) -> str | None:
    if not w:
        return None
    s = w.strip()
    m = re.search(r"(\d+)\s*(year|month|day)s?", s, re.I)
    if re.search(r"life\s*time", s, re.I):
        return "লাইফটাইম ওয়ারেন্টি"
    if m:
        unit = {"year": "বছর", "month": "মাস", "day": "দিন"}[m.group(2).lower()]
        rest = re.sub(r"\d+\s*(year|month|day)s?\s*(warranty)?", "", s, flags=re.I).strip(" ,.-()")
        return f"{bn_num(m.group(1))} {unit} ওয়ারেন্টি" + (f" ({rest})" if rest else "")
    if re.search(r"no\s+warranty", s, re.I):
        return "ওয়ারেন্টি নেই"
    return s


def section_bn(name):
    return SECTION_BN.get(name.lower(), name)


def blurb(p, leaf, det):
    name = p["name"]
    feats = det.get("key_features", [])[:4] if det else []
    parts = [f"{name} একটি {leaf['name_bn']}।"]
    if feats:
        parts.append("মূল বৈশিষ্ট্য: " + "; ".join(feats) + "।")
    w = warranty_bn(det.get("warranty")) if det else None
    if w:
        parts.append(f"বিক্রেতার তথ্য অনুযায়ী ওয়ারেন্টি: {w}।")
    hint = {
        "laptop-ram": "কেনার আগে আপনার ল্যাপটপ কোন টাইপ ও স্পিডের র‍্যাম সাপোর্ট করে দেখে নিন।",
        "desktop-ram": "মাদারবোর্ড কোন টাইপ (DDR4/DDR5) সাপোর্ট করে আগে মিলিয়ে নিন।",
        "ssd": "মাদারবোর্ড বা ল্যাপটপে M.2 না SATA স্লট আছে আগে দেখে নিন।",
        "processor": "মাদারবোর্ডের সকেট ও চিপসেট মিলিয়ে নিন।",
        "smartphone": "অফিসিয়াল ও আনঅফিসিয়াল ফোনের ওয়ারেন্টি আলাদা, কেনার সময় নিশ্চিত হয়ে নিন।",
    }.get(leaf["slug"])
    if hint:
        parts.append(hint)
    parts.append("নিচে বিভিন্ন স্টোরের দাম পাশাপাশি দেওয়া আছে, যাতে কম দামে কোথায় পাওয়া যায় এক নজরে দেখতে পারেন।")
    return " ".join(parts)


def load_ads(today: str) -> dict:
    """config/ads.json পড়ে: মেয়াদ শেষ হওয়া স্পন্সর ও ফিচার্ড স্টোর বাদ দেয়।"""
    f = ROOT / "config/ads.json"
    ads = json.loads(f.read_text()) if f.exists() else {}
    ads.setdefault("adsense", {}).setdefault("slots", {})
    ads["sponsors"] = [s for s in ads.get("sponsors", [])
                       if s.get("active") and s.get("until", "9999") >= today and (s.get("url") or s.get("image"))]
    ads["featured_stores"] = {k: v for k, v in ads.get("featured_stores", {}).items()
                              if not k.startswith("_") and (v or {}).get("until", "9999") >= today}
    ads.setdefault("links", {})
    return ads


def make_go_url(ads):
    utm = ads["links"].get("utm", "")
    aff = ads["links"].get("affiliate", {})

    def go_url(store: str, url: str) -> str:
        """স্টোরের লিংকে অ্যাফিলিয়েট ও utm যোগ করা, যাতে স্টোর বুঝতে পারে ক্রেতা দামতুলনা থেকে এসেছে।"""
        if not url:
            return url
        extra = "&".join(x for x in (aff.get(store, "").lstrip("?&"), utm) if x)
        if not extra:
            return url
        parts = urlsplit(url)
        q = parts.query + ("&" if parts.query else "") + extra
        return urlunsplit((parts.scheme, parts.netloc, parts.path, q, parts.fragment))
    return go_url


def make_sponsor_for(ads):
    sponsors = ads["sponsors"]

    def sponsor_for(where: str, cat: str | None = None, key: str = ""):
        """এই জায়গার জন্য একটা স্পন্সর (একাধিক থাকলে পাতা ভেদে ঘুরিয়ে)।"""
        ok = [s for s in sponsors if where in s.get("where", []) and (not s.get("categories") or cat in s["categories"])]
        if not ok:
            return None
        return ok[zlib.crc32(f"{where}:{key}".encode()) % len(ok)]
    return sponsor_for


def make_house_for(ads):
    h = ads.get("house_ad") or {}
    c = ads.get("contact") or {}
    texts = h.get("texts") or []
    if not h.get("active") or not texts or not (c.get("phone") or c.get("whatsapp")):
        return lambda where, key="": None
    from urllib.parse import quote
    wa = f"https://wa.me/88{c['whatsapp']}?text={quote(h.get('whatsapp_message', ''))}" if c.get("whatsapp") else None
    tel = f"tel:+88{c['phone']}" if c.get("phone") else None

    def house_for(where: str, key: str = ""):
        """নিজের 'বিজ্ঞাপন দিন' ব্যানার; লেখা পাতা ও জায়গা ভেদে বদলায়।"""
        t = texts[zlib.crc32(f"{where}:{key}".encode()) % len(texts)]
        return {"title": t[0], "text": t[1], "wa": wa, "tel": tel, "phone": c.get("phone") or c.get("whatsapp")}
    return house_for


def build_size_pages(items, products, details, write):
    """সাইজ অনুযায়ী ব্র্যান্ড তুলনা (যেমন ১০০-১৫০ লিটার ফ্রিজে কোন ব্র্যান্ডের দাম কত)।"""
    f = ROOT / "config/size_compare.json"
    if not f.exists():
        return []
    made = []
    for slug, conf in json.loads(f.read_text())["pages"].items():
        rx = re.compile(conf["regex"], re.I)
        types = {k: re.compile(v, re.I) for k, v in conf.get("types", {}).items()}
        rows = [it for it in items.values() if it["category"] == conf["category"]]
        # ব্র্যান্ডের বানান এক করা (SAMSUNG/Samsung)
        spell = Counter(it["brand"] for it in rows)
        canon = {}
        for b_, _ in spell.most_common():
            canon.setdefault(b_.lower(), b_ if not b_.isupper() or len(b_) <= 3 else b_.title())
        models = []
        for it in rows:
            m = rx.search(it["name"])
            if not m:
                continue
            cap = float(m.group(1))
            cap = int(cap) if cap == int(cap) else cap
            det = details.get(it["id"], {})
            models.append({"id": it["id"], "n": it["name"], "b": canon[it["brand"].lower()], "s": cap,
                           "t": [k for k, r in types.items() if r.search(it["name"])],
                           "p": (it["best"] or {}).get("price"), "ap": it["any_price"],
                           "st": (it["best"] or {}).get("store"), "w": warranty_bn(det.get("warranty"))})
        if not models:
            continue
        sizes = Counter(m["s"] for m in models)
        brands_by_size = defaultdict(set)
        for m in models:
            brands_by_size[m["s"]].add(m["b"])
        exact = [{"s": sz, "n": sizes[sz], "b": len(brands_by_size[sz])} for sz in sorted(sizes)]
        priced = [m["p"] for m in models if m["p"]]
        write(f"size/{slug}", "size.html", conf=conf, slug=slug, models_json=json.dumps(models, ensure_ascii=False, separators=(",", ":")),
              ranges=conf["ranges"], exact=exact, total=len(models), brand_count=len({m["b"] for m in models}),
              lo=min(priced) if priced else None, hi=max(priced) if priced else None,
              title=f"{conf['title']}ের দাম সাইজ অনুযায়ী | কোন ব্র্যান্ডের {conf['title']} কত টাকা | দামতুলনা",
              description=f"{len({m['b'] for m in models})}টি ব্র্যান্ডের {len(models)}টি {conf['title']}ের দাম {conf['unit']} অনুযায়ী তুলনা। কোন সাইজে কোন ব্র্যান্ড সবচেয়ে কম দামে।",
              canonical=f"{SITE_URL}/size/{slug}/" if SITE_URL else None)
        made.append({"slug": slug, "category": conf["category"], "title": conf["title"], "unit": conf["unit"], "total": len(models)})
    return made


def load_details():
    out = {}
    base = DATA / "details"
    if base.exists():
        for f in base.glob("*/*.json"):
            out[f.stem] = json.loads(f.read_text())
    return out


def main():
    t0 = time.time()
    stores = json.loads((ROOT / "config/stores.json").read_text())["stores"]
    logos_file = ROOT / "web/static/logos/logos.json"
    logos = json.loads(logos_file.read_text()) if logos_file.exists() else {}
    for sid, st in stores.items():
        st["logo"] = logos.get(sid)
    tax = json.loads((ROOT / "config/taxonomy.json").read_text())
    # অ্যাডমিন প্যানেল থেকে: ক্যাটাগরির নাম বদল ও লুকানো
    co_file = ROOT / "config/category_overrides.json"
    co = json.loads(co_file.read_text()) if co_file.exists() else {}
    all_cats = []
    for g in tax["groups"]:
        g["name_bn"] = co.get("groups", {}).get(g["slug"]) or g["name_bn"]
        for l in g["leaves"]:
            l["name_bn"] = co.get("names", {}).get(l["slug"]) or l["name_bn"]
            all_cats.append({"group": g["slug"], "group_bn": g["name_bn"], "slug": l["slug"], "name_bn": l["name_bn"],
                             "en": l.get("name_en", ""), "hidden": l["slug"] in co.get("hidden", [])})
        g["leaves"] = [l for l in g["leaves"] if l["slug"] not in co.get("hidden", [])]
    leaves = {l["slug"]: l for g in tax["groups"] for l in g["leaves"]}
    group_of = {l["slug"]: g for g in tax["groups"] for l in g["leaves"]}
    products = json.loads((DATA / "products.json").read_text())
    offers = json.loads((DATA / "offers.json").read_text())
    health = json.loads((DATA / "health.json").read_text())
    suggestions = json.loads((DATA / "suggestions.json").read_text()) if (DATA / "suggestions.json").exists() else []
    details = load_details()
    today = health["date"]
    updated = bn_date(today) + ", " + health["scraped_at"][11:16]
    enabled = [s for s, v in stores.items() if v["enabled"]]
    ads = load_ads(today)
    for sid in ads["featured_stores"]:
        if sid in stores:
            stores[sid]["featured"] = True

    # প্রতিটা প্রোডাক্ট → স্টোর → [(তারিখ, দাম বা None)] (শুধু বদলের দিনগুলো)
    history = defaultdict(lambda: defaultdict(list))
    if (DATA / "history.csv").exists():
        with (DATA / "history.csv").open() as f:
            for r in csv.DictReader(f):
                history[r["product"]][r["store"]].append((r["date"], int(r["price"]) if r["in_stock"] == "1" else None))

    env = Environment(loader=FileSystemLoader(ROOT / "web/templates"), autoescape=select_autoescape(["html"]))
    env.filters["taka"] = taka
    env.filters["bn"] = bn_num
    common = {"base": BASE, "stores": stores, "updated": updated, "build_id": int(t0), "spec_names": SPEC_NAMES,
              "stores_json": json.dumps({k: v["name"] for k, v in stores.items()}, ensure_ascii=False),
              "adsense": ads["adsense"], "sponsor_for": make_sponsor_for(ads), "go_url": make_go_url(ads),
              "going_note": ads.get("going_note", True), "contact": ads.get("contact", {}),
              "house_for": make_house_for(ads),
              "size_links": {c["category"]: (k, c["title"], c["unit"]) for k, c in
                             (json.loads((ROOT / "config/size_compare.json").read_text())["pages"].items()
                              if (ROOT / "config/size_compare.json").exists() else [])}}

    # অ্যাডমিন থেকে মিলানো/লুকানো প্রোডাক্ট সাথে সাথে কার্যকর (পরের দামের রানেও matcher একই কাজ করে)
    mm_file = DATA / "manual_matches.json"
    mm = json.loads(mm_file.read_text()) if mm_file.exists() else {}
    for m in mm.get("merge", []):
        keep = m.get("keep")
        for other in m.get("merge", []):
            if keep in offers and other in offers and other != keep:
                for st, o in offers.pop(other).items():
                    if st not in offers[keep] or (o.get("price") and o.get("in_stock") and
                                                  (not offers[keep][st].get("in_stock") or o["price"] < (offers[keep][st].get("price") or 10**9))):
                        offers[keep][st] = o
    for pid in mm.get("ignore", []):
        offers.pop(pid, None)

    items = {}
    for pid, so in offers.items():
        p = products.get(pid)
        if not p or p["category"] not in leaves:
            continue
        det = details.get(pid, {})
        live = sorted(((s, o) for s, o in so.items() if o.get("in_stock") and o.get("price")), key=lambda x: x[1]["price"])
        best = {"store": live[0][0], "price": live[0][1]["price"], "url": live[0][1]["url"]} if live else None
        any_price = min((o["price"] for o in so.values() if o.get("price")), default=None)
        brand = det.get("brand") or p["brand"]
        items[pid] = {"id": pid, "name": p["name"], "category": p["category"], "cat_name": leaves[p["category"]]["name_bn"],
                      "group": group_of[p["category"]]["slug"], "brand": brand, "best": best, "any_price": any_price,
                      "saving": live[-1][1]["price"] - live[0][1]["price"] if len(live) > 1 else 0,
                      "store_count": len([o for o in so.values() if o.get("price")]), "live_count": len(live),
                      "created": p["created"], "specs": p["specs"],
                      "facets": " ".join(x for x in [p["specs"].get(k) for k in ("capacity", "type", "interface", "brand_cpu")] if x)}

    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "static").mkdir(parents=True)
    for f in ("style.css", "compare.js", "go.js", "admin.css", "admin.js"):
        shutil.copy(ROOT / "web/static" / f, DIST / "static" / f)
    for d in ("logos", "sponsors"):
        if (ROOT / "web/static" / d).exists():
            shutil.copytree(ROOT / "web/static" / d, DIST / "static" / d)
    urls = []

    def write(path, template, **ctx):
        out = DIST / path / "index.html" if path else DIST / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(env.get_template(template).render(**common, **ctx))
        if not ctx.get("noindex"):
            urls.append(f"{SITE_URL}/{path + '/' if path else ''}")

    by_cat = defaultdict(list)
    for it in items.values():
        by_cat[it["category"]].append(it)
    product_tpl = env.get_template("product.html")

    for pid, it in items.items():
        p, leaf, grp, so = products[pid], leaves[it["category"]], group_of[it["category"]], offers[pid]
        det = details.get(pid, {})
        rows = []
        for s in enabled:
            o = so.get(s)
            label, cls = STATUS.get(o["status"], ("", "")) if o else ("", "")
            age = (date.fromisoformat(today) - date.fromisoformat(o["seen"])).days if o and o.get("seen") else None
            fresh = (None if age is None else "আজ যাচাই করা" if age == 0 else "গতকাল যাচাই করা" if age == 1
                     else f"{bn_num(age)} দিন আগে যাচাই করা")
            rows.append({"store": s, "offer": o, "label": label, "cls": cls, "fresh": fresh, "old": bool(age and age >= 2),
                         "is_best": bool(it["best"] and o and it["best"]["store"] == s and it["saving"] > 0),
                         "featured": bool(o and o.get("in_stock") and stores[s].get("featured"))})
        # স্পন্সরড স্টোর (স্টকে থাকলে) উপরে, "স্পন্সরড" লেখাসহ; বাকিরা দাম অনুযায়ী
        rows.sort(key=lambda r: (not r["featured"], r["offer"] is None, not (r["offer"] and r["offer"]["in_stock"]), (r["offer"] or {}).get("price") or 10**9))
        same = [a for a in by_cat[it["category"]] if a["id"] != pid and a["best"]
                and all(a["specs"].get(k) == it["specs"].get(k) for k in ("capacity", "type", "form", "interface", "brand_cpu") if it["specs"].get(k))]
        ref = (it["best"] or {}).get("price") or it["any_price"]
        if ref and not any(it["specs"].get(k) for k in ("capacity", "type", "interface", "brand_cpu")):
            same = [a for a in same if 0.7 * ref <= a["best"]["price"] <= 1.3 * ref]
        alts = [{"id": a["id"], "name": a["name"], "price": a["best"]["price"], "store": a["best"]["store"]}
                for a in sorted(same, key=lambda a: abs(a["best"]["price"] - (ref or 0)))[:6]]
        changes = daily_min(history.get(pid, {}), today)
        best = it["best"]
        warranty = warranty_bn(det.get("warranty"))
        spec_sections = [(section_bn(sec), rows_) for sec, rows_ in det.get("specs", {}).items()
                         if "warranty" not in sec.lower()]
        faq = [
            (f"{p['name']} এর দাম কত?",
             f"আজকের হিসাবে সর্বনিম্ন দাম {taka(best['price'])}, {stores[best['store']]['name']}-এ।" if best
             else "এই মুহূর্তে আমাদের তালিকার কোনো স্টোরে এটা স্টকে নেই।"),
            ("এর ওয়ারেন্টি কত দিনের?",
             f"বিক্রেতার পাতায় লেখা আছে: {warranty}। কেনার সময় ওয়ারেন্টি কার্ড ও শর্ত মিলিয়ে নিন।" if warranty
             else "ওয়ারেন্টির তথ্য এখনো যোগ হয়নি। কেনার আগে স্টোরে জিজ্ঞেস করে নিন।"),
            ("এই দাম কখন আপডেট হয়?", "প্রতিদিন রাতে সব স্টোর থেকে দাম নতুন করে সংগ্রহ করা হয়।"),
            ("কোন স্টোর থেকে কেনা ভালো?", "দামের পাশাপাশি ওয়ারেন্টি, ডেলিভারি আর বাসার কাছে শাখা আছে কিনা দেখে নিন।"),
        ]
        jsonld = {"@context": "https://schema.org", "@type": "Product", "name": p["name"],
                  "brand": {"@type": "Brand", "name": it["brand"]}, "category": leaf["name_en"]}
        if det.get("mpn"):
            jsonld["mpn"] = det["mpn"]
        priced = [o for o in so.values() if o.get("price") and o.get("in_stock")]
        if priced:
            jsonld["offers"] = {"@type": "AggregateOffer", "priceCurrency": "BDT", "offerCount": len(priced),
                                "lowPrice": min(o["price"] for o in priced), "highPrice": max(o["price"] for o in priced)}
        cmp = {"id": pid, "n": p["name"], "b": it["brand"], "c": leaf["slug"], "cn": leaf["name_bn"],
               "w": warranty, "m": det.get("model"), "mpn": det.get("mpn"), "kf": det.get("key_features", [])[:6],
               "best": best, "o": {s_: {"p": o["price"], "st": o["in_stock"], "u": o["url"]} for s_, o in so.items() if o.get("price")},
               "sp": det.get("specs") or {"মূল তথ্য": {SPEC_NAMES.get(k, k): v for k, v in p["specs"].items()}}}
        (DIST / "d").mkdir(exist_ok=True)
        (DIST / f"d/{pid}.json").write_text(json.dumps(cmp, ensure_ascii=False, separators=(",", ":")))
        out = DIST / f"p/{pid}/index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(product_tpl.render(
            **common, p=p, it=it, cat=leaf, group=grp, det=det, warranty=warranty, spec_sections=spec_sections,
            best=best, saving=it["saving"], live_count=it["live_count"], store_rows=rows, alts=alts,
            spark=sparkline(changes, today), hist_start=bn_date(changes[0][0]) if changes else None,
            hist_days=(date.fromisoformat(today) - date.fromisoformat(changes[0][0])).days + 1 if changes else 0,
            hist_lo=min((v for _, v in changes), default=None), hist_hi=max((v for _, v in changes), default=None), icon=icon_for(it["category"], grp["slug"]), blurb=blurb(p, leaf, det), faq=faq,
            jsonld=json.dumps(jsonld, ensure_ascii=False), buy=bool(best),
            title=f"{p['name']} দাম বাংলাদেশে" + (f" | {taka(best['price'])} থেকে" if best else ""),
            description=f"{p['name']} এর দাম বিভিন্ন স্টোরে মিলিয়ে দেখুন।" + (f" আজকের সর্বনিম্ন দাম {taka(best['price'])}।" if best else "")
                        + (f" {warranty}।" if warranty else ""),
            canonical=f"{SITE_URL}/p/{pid}/" if SITE_URL else None))
        urls.append(f"{SITE_URL}/p/{pid}/")

    # ক্যাটাগরি পেজ (পাতায় ভাগ করা)
    group_cards = []
    for g in tax["groups"]:
        leaf_cards = []
        for leaf in g["leaves"]:
            lst = sorted(by_cat.get(leaf["slug"], []), key=lambda i: (i["best"] is None, (i["best"] or {}).get("price", 0)))
            if not lst:
                continue
            brands = [b for b, _ in Counter(i["brand"] for i in lst).most_common(12)]
            pages = max(1, -(-len(lst) // PER_PAGE))
            for n in range(1, pages + 1):
                chunk = lst[(n - 1) * PER_PAGE:n * PER_PAGE]
                write(f"c/{leaf['slug']}" + (f"/{n}" if n > 1 else ""), "category.html", cat=leaf, group=g, items=chunk,
                      total=len(lst), page=n, pages=pages, brands=brands, store_count=len(enabled),
                      title=f"{leaf['name_bn']} দাম বাংলাদেশে | {leaf['name_en']} Price in BD" + (f" (পাতা {n})" if n > 1 else ""),
                      description=f"{len(lst)}টি {leaf['name_bn']} এর দাম বিভিন্ন স্টোরে মিলিয়ে দেখুন।",
                      canonical=f"{SITE_URL}/c/{leaf['slug']}/" + (f"{n}/" if n > 1 else "") if SITE_URL else None)
            priced = [i["best"]["price"] for i in lst if i["best"]]
            leaf_cards.append({"slug": leaf["slug"], "name_bn": leaf["name_bn"], "count": len(lst),
                               "min": min(priced) if priced else None,
                               "multi": sum(1 for i in lst if i["store_count"] > 1)})
        if not leaf_cards:
            continue
        gitems = [i for l in leaf_cards for i in by_cat[l["slug"]]]
        deals = sorted([i for i in gitems if i["saving"] > 0], key=lambda i: -i["saving"])[:8]
        write(f"g/{g['slug']}", "group.html", group=g, leaves=leaf_cards, deals=deals, total=len(gitems),
              title=f"{g['name_bn']} দাম বাংলাদেশে | দামতুলনা",
              description=f"{g['name_bn']}: {len(leaf_cards)}টি ক্যাটাগরিতে {len(gitems)}টি প্রোডাক্টের দাম তুলনা।",
              canonical=f"{SITE_URL}/g/{g['slug']}/" if SITE_URL else None)
        group_cards.append({"slug": g["slug"], "name_bn": g["name_bn"], "count": len(gitems), "leaves": len(leaf_cards),
                            "top": [l["name_bn"] for l in sorted(leaf_cards, key=lambda l: -l["count"])[:3]]})

    vals = list(items.values())
    size_pages = build_size_pages(items, products, details, write)
    deals = sorted([i for i in vals if i["saving"] > 0], key=lambda i: -i["saving"])[:10]
    fresh_all = sorted([i for i in vals if i["created"] == today], key=lambda i: i["name"])
    fresh = fresh_all[:10] if len(fresh_all) < len(vals) * 0.5 else []
    write("", "home.html", groups=group_cards, deals=deals, fresh=fresh, total=len(vals),
          multi=sum(1 for i in vals if i["store_count"] > 1),
          store_names=", ".join(stores[s]["name"] for s in enabled), store_count=len(enabled),
          title="দামতুলনা | কম্পিউটার, মোবাইল ও ইলেকট্রনিক্সের দাম তুলনা বাংলাদেশে",
          description=f"{len(vals)}টি প্রোডাক্টের দাম {len(enabled)}টি স্টোরে মিলিয়ে দেখুন: " + ", ".join(stores[s]["name"] for s in enabled) + "।",
          canonical=f"{SITE_URL}/" if SITE_URL else None)
    write("compare", "compare.html", title="তুলনা করুন | দামতুলনা", description="প্রোডাক্ট পাশাপাশি তুলনা", noindex=True,
          section_bn=SECTION_BN)
    write("search", "search.html", title="খুঁজুন | দামতুলনা", description="প্রোডাক্ট খুঁজুন", noindex=True)
    for slug, title, desc in (("about", "আমাদের সম্পর্কে", "দামতুলনা কী, দাম কোথা থেকে আসে, কীভাবে আয় হয়।"),
                              ("advertise", "বিজ্ঞাপন দিন", "দামতুলনায় ব্র্যান্ড বা স্টোরের বিজ্ঞাপন দেওয়ার নিয়ম।"),
                              ("privacy", "প্রাইভেসি নীতি", "দামতুলনা কোন তথ্য রাখে, কুকি ও বিজ্ঞাপন সংক্রান্ত নীতি।")):
        write(slug, "info.html", page=slug, heading=title, store_names=", ".join(stores[s]["name"] for s in enabled),
              title=f"{title} | দামতুলনা", description=desc, canonical=f"{SITE_URL}/{slug}/" if SITE_URL else None)
    client = ads["adsense"].get("client", "")
    if client:
        # ads.txt ডোমেইনের মূলে থাকতে হয়; নিজের ডোমেইন যুক্ত হলে কাজ করবে
        (DIST / "ads.txt").write_text(f"google.com, {client.replace('ca-pub-', 'pub-')}, DIRECT, f08c47fec0942fa0\n")
    stats = {"total": len(vals), "multi": sum(1 for i in vals if i["store_count"] > 1), "new": len(fresh_all),
             "details": sum(1 for pid in items if pid in details)}
    manual = json.loads((DATA / "manual_matches.json").read_text()) if (DATA / "manual_matches.json").exists() else {}
    done = {m["keep"] for m in manual.get("merge", [])} | {x for m in manual.get("merge", []) for x in m.get("merge", [])}
    cat_count = Counter(i["category"] for i in vals)
    raw_count = Counter(p["category"] for p in products.values())
    for c in all_cats:
        c["count"] = cat_count.get(c["slug"], 0) or raw_count.get(c["slug"], 0)
    admin = {"updated": updated, "health": health, "stats": stats, "categories": all_cats,
             "suggestions": [x for x in suggestions if not ({x["a"], x["b"]} <= done)][:300],
             "fresh": [{"id": i["id"], "n": i["name"], "c": i["cat_name"]} for i in fresh_all[:100]]}
    (DIST / "admin").mkdir(exist_ok=True)
    (DIST / "admin/admin.json").write_text(json.dumps(admin, ensure_ascii=False, separators=(",", ":")))
    write("admin", "admin.html", title="অ্যাডমিন প্যানেল | দামতুলনা", description="", noindex=True, noads=True,
          repo=os.environ.get("GITHUB_REPOSITORY", "shariful881/daam-tulona"))

    search = [{"id": i["id"], "n": i["name"], "c": i["cat_name"], "g": i["category"], "p": (i["best"] or {}).get("price"), "k": i["store_count"]}
              for i in vals]
    (DIST / "search.json").write_text(json.dumps(search, ensure_ascii=False, separators=(",", ":")))
    # sitemap ৫০,০০০ লিংকের মধ্যে থাকলে একটা ফাইলেই চলে
    (DIST / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      + "".join(f"<url><loc>{u}</loc></url>\n" for u in urls[:50000]) + "</urlset>\n")
    (DIST / "robots.txt").write_text(f"User-agent: *\nDisallow: {BASE}/admin/\nDisallow: {BASE}/search/\nSitemap: {SITE_URL}/sitemap.xml\n")
    (DIST / ".nojekyll").write_text("")
    print(f"{len(urls)}টি পেজ তৈরি হয়েছে ({len(items)} প্রোডাক্ট, বিস্তারিত তথ্যসহ {stats['details']}), {time.time() - t0:.1f} সেকেন্ডে")


if __name__ == "__main__":
    main()
