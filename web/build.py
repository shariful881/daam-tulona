"""data/ থেকে পুরো স্ট্যাটিক সাইট dist/ ফোল্ডারে বানায়।

চালানো: BASE_URL= SITE_URL=https://damtulona.com python -m web.build
(GitHub Pages-এ রিপোর নামের সাব-ফোল্ডারে থাকে, তাই BASE_URL লাগে। নিজের ডোমেইনে BASE_URL ফাঁকা রাখুন।)
"""
import csv
import math
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

from scraper.details_generic import normalize_specs
from web.keyspecs import key_specs, schema as spec_schema
from web import insights as INS
from web.facets import facets_for, facet_defs
from web.automatch import auto_merges
from web import market

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DIST = ROOT / "dist"
BASE = os.environ.get("BASE_URL", "").rstrip("/")
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")
PER_PAGE = 48

FEAT_BN = {"processor": "প্রসেসর", "ram": "র‍্যাম", "storage": "স্টোরেজ", "display": "ডিসপ্লে", "screen": "স্ক্রিন",
           "features": "ফিচার", "feature": "ফিচার", "battery": "ব্যাটারি", "camera": "ক্যামেরা", "graphics": "গ্রাফিক্স",
           "resolution": "রেজোলিউশন", "screen size": "স্ক্রিন সাইজ", "display size": "স্ক্রিন সাইজ", "panel": "প্যানেল",
           "panel type": "প্যানেল টাইপ", "refresh rate": "রিফ্রেশ রেট", "ports": "পোর্ট", "port": "পোর্ট",
           "connectivity": "কানেক্টিভিটি", "connection": "কানেকশন", "capacity": "ক্যাপাসিটি", "type": "টাইপ",
           "speed": "স্পিড", "color": "রং", "colour": "রং", "weight": "ওজন", "os": "অপারেটিং সিস্টেম",
           "operating system": "অপারেটিং সিস্টেম", "chipset": "চিপসেট", "memory": "মেমোরি", "interface": "ইন্টারফেস",
           "power": "পাওয়ার", "output": "আউটপুট", "input": "ইনপুট", "wattage": "ওয়াট", "warranty": "ওয়ারেন্টি",
           "model": "মডেল", "size": "সাইজ", "sensor": "সেন্সর", "dpi": "DPI", "switch": "সুইচ", "frequency": "ফ্রিকোয়েন্সি",
           "driver": "ড্রাইভার", "material": "উপাদান", "compatibility": "সাপোর্ট করে", "compressor": "কম্প্রেসর",
           "smart features": "স্মার্ট ফিচার", "sound": "সাউন্ড", "audio": "অডিও", "voltage": "ভোল্টেজ", "socket": "সকেট",
           "form factor": "ফর্ম ফ্যাক্টর", "cores": "কোর", "cache": "ক্যাশ", "network": "নেটওয়ার্ক", "wifi": "ওয়াইফাই"}



SPEC_NAMES = {"capacity": "ক্যাপাসিটি", "type": "টাইপ", "speed": "বাস স্পিড", "form": "ফর্ম ফ্যাক্টর",
              "interface": "ইন্টারফেস", "brand_cpu": "প্রসেসর ব্র্যান্ড", "model": "মডেল"}
SECTION_BN = {"key features": "মূল বৈশিষ্ট্য", "warranty information": "ওয়ারেন্টি", "physical specification": "শারীরিক বৈশিষ্ট্য",
              "physical dimension": "আকার", "display": "ডিসপ্লে", "processor": "প্রসেসর", "memory": "মেমরি", "storage": "স্টোরেজ",
              "camera": "ক্যামেরা", "battery": "ব্যাটারি", "connectivity": "কানেক্টিভিটি", "graphics": "গ্রাফিক্স",
              "keyboard & touchpad": "কিবোর্ড ও টাচপ্যাড", "audio": "অডিও", "network": "নেটওয়ার্ক", "power": "পাওয়ার",
              "general": "সাধারণ", "basic information": "সাধারণ তথ্য", "ports & slots": "পোর্ট ও স্লট", "operating system": "অপারেটিং সিস্টেম"}
MANUAL_MAX_DAYS = 14  # হাতে বসানো দাম এর বেশি পুরনো হলে দেখানো হয় না
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


SUSPECT_RATIO = 1.5  # এর বেশি ফারাক হলে দামটা "যাচাই চলছে" (ভুল ম্যাচ বা ভুল দাম হতে পারে)


def suspect_stores(live: list) -> set:
    """স্টকে থাকা দামগুলোর মধ্যে অবাস্তব দাম খোঁজে। live = [(store, offer)] দাম অনুযায়ী সাজানো।
    ৩+ দোকান: মিডিয়ান থেকে ১.৫ গুণের বেশি দূরের দাম সন্দেহজনক।
    ২ দোকান: একটা আরেকটার ১.৫ গুণ বা বেশি হলে কোনটা ঠিক বলা যায় না, তাই দুটোই।"""
    ps = [o["price"] for _, o in live]
    if len(ps) < 2:
        return set()
    if len(ps) == 2:
        return {s for s, _ in live} if ps[1] >= ps[0] * SUSPECT_RATIO else set()
    srt = sorted(ps)
    med = srt[len(srt) // 2] if len(srt) % 2 else (srt[len(srt) // 2 - 1] + srt[len(srt) // 2]) / 2
    return {s for s, o in live if o["price"] * SUSPECT_RATIO < med or o["price"] > med * SUSPECT_RATIO}


PHONE_CATS = {"smartphone", "tablet", "feature-phone"}


def phone_type(offer_name, store_conf):
    """মোবাইল/ট্যাবলেটের অফিসিয়াল-আনঅফিসিয়াল: নামে লেখা থাকলে সেটা, না হলে স্টোরের ডিফল্ট (অ্যাডমিন থেকে)।"""
    n = (offer_name or "").lower()
    if re.search(r"\bunofficial\b|\bglobal (?:version|variant)\b|\b(?:cn|china|indian?|uk|us|usa|hk|japan|jp) (?:version|variant)\b", n):
        return "unofficial"
    if re.search(r"\bofficial\b", n):
        return "official"
    return store_conf.get("phone_type") or None


def nice_round(x):
    """দামের রেঞ্জের জন্য গোল সংখ্যা: ১২,৩৪০ → ১২,০০০ / ১,৮৭০ → ২,০০০"""
    if x <= 0:
        return 0
    mag = 10 ** (len(str(int(x))) - 1)
    return min((m * mag for m in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 7.5, 8, 10)), key=lambda v: abs(v - x))


def price_presets(prices):
    """তালিকার দামের ভাগ (২০/৪০/৬০/৮০ শতাংশ) থেকে ৪-৫টা গোল রেঞ্জ।"""
    if len(prices) < 8:
        return []
    ps = sorted(prices)
    cuts = sorted({int(nice_round(ps[int(len(ps) * q)])) for q in (0.2, 0.4, 0.6, 0.8)})
    edges = [0] + [c for c in cuts if c > 0]
    out = [[edges[i], edges[i + 1]] for i in range(len(edges) - 1)] + [[edges[-1], None]]
    return out if len(out) >= 3 else []


LAPTOP_MAKERS = [("hp", "HP"), ("asus", "Asus"), ("lenovo", "Lenovo"), ("dell", "Dell"), ("acer", "Acer"), ("toshiba", "Toshiba"),
                 ("apple", "Apple"), ("macbook", "Apple"), ("samsung", "Samsung"), ("fujitsu", "Fujitsu"), ("msi", "MSI"), ("sony", "Sony"),
                 ("huawei", "Huawei"), ("xiaomi", "Xiaomi"), ("microsoft", "Microsoft"), ("gigabyte", "Gigabyte"), ("razer", "Razer"),
                 ("walton", "Walton"), ("compaq", "HP"), ("thinkpad", "Lenovo"), ("ideapad", "Lenovo"), ("avita", "Avita"), ("mac", "Apple")]
LAPTOP_RANK = {d: k for k, d in enumerate(dict.fromkeys(d for _, d in LAPTOP_MAKERS))}


def category_filters(lst):
    """ক্যাটাগরির ফিল্টার: যে ফ্যাসেট অন্তত ২৫% প্রোডাক্টে আছে আর ২+ রকম মান, শুধু সেগুলো দেখায়।"""
    if not lst:
        return []
    out = []
    for d in facet_defs(lst[0]["category"]):
        vals = Counter()
        num = {}
        for i in lst:
            v = i["fx"].get(d["id"])
            if v:
                vals[v[0]] += 1
                num[v[0]] = v[1]
        if sum(vals.values()) >= len(lst) * 0.25 and len(vals) >= 2:
            opts = sorted(vals, key=lambda k: num[k])
            out.append({"id": d["id"], "name": d["name"], "opts": [[k, vals[k]] for k in opts]})
    fit = Counter(i["fx"]["fit"][0] for i in lst if i["fx"].get("fit"))
    if sum(fit.values()) >= 10 and len(fit) >= 2:  # রিপ্লেসমেন্ট পার্টস: কোন ল্যাপটপের জন্য
        out.insert(0, {"id": "fit", "name": "কোন ল্যাপটপের জন্য", "opts": [[k, fit[k]] for k in sorted(fit, key=lambda k: LAPTOP_RANK.get(k, 99))]})
    return out


SPLIT_RX = re.compile(r"[\s\-_/,()\[\]+|:;\"'.!?&*#@]+")


def search_tokens(text):
    """search.js-এর tokens()-এর সাথে হুবহু মিলতে হবে।"""
    return [t for t in SPLIT_RX.split(text.lower()) if t]


def shard_key(tok):
    """শব্দের প্রথম ২ অক্ষরের কোডপয়েন্ট (ফাইলের নাম), search.js-এর key()-এর মতো।"""
    return "_".join(format(ord(c), "x") for c in tok[:2])


TITLE_MAX = 70  # Google ~৬০০ পিক্সেলের বেশি শিরোনাম কেটে দেখায়; প্রোডাক্টের পুরো নাম H1-এ থাকে
_FLUFF = re.compile(r"\s*(,\s*)?(copilot\s*(\+|plus)\s*(pc)?\s*(&|and)?\s*ai\s+optimized|copilot\+\s*pc|&\s*ai\s+optimized)\b", re.I)


def short_name(name: str) -> str:
    """শিরোনামের জন্য নাম: শেষের দোকান-কোড (#C0PN3PA-3Y) আর বিজ্ঞাপনী অংশ বাদ।"""
    s = re.sub(r"\s*#[\w.\-/]+\s*$", "", name)
    s = _FLUFF.sub("", s)
    return re.sub(r"\s+", " ", s).strip(" ,-/")


def fit_name(name: str, limit: int) -> str:
    """নাম limit অক্ষরের মধ্যে, শব্দের মাঝখানে না কেটে; অসমাপ্ত বন্ধনী আর ঝুলে থাকা সংযোগ-শব্দ বাদ।"""
    if len(name) <= limit:
        return name
    cut = name[:limit + 1]
    cut = cut[:cut.rfind(" ")] if " " in cut else name[:limit]
    if cut.count("(") > cut.count(")"):
        cut = cut[:cut.rfind("(")]
    cut = re.sub(r"(\s+(with|and|for|&|\+|-|/|,|in|of|the))+$", "", cut.strip(" ,-/(&+"), flags=re.I)
    return cut.strip(" ,-/(&+") or name[:limit]


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


def window_min(changes, today, days):
    """গত `days` দিনে সর্বনিম্ন দৈনিক দাম (শুরুর দিনে যে দাম চলছিল সেটাও ধরে)।"""
    cut = (date.fromisoformat(today) - timedelta(days=days)).isoformat()
    before = [v for d, v in changes if d <= cut]
    vals = [v for d, v in changes if d > cut] + before[-1:]
    return min(vals) if vals else None


def sparkline(changes: list[tuple[str, int]], today: str, days: int = 90) -> str:
    """দাম বদলের তারিখগুলো থেকে প্রতিদিনের ধারা বানিয়ে শেষ `days` দিনের চার্ট।"""
    if not changes:
        return ""
    end = date.fromisoformat(today)
    start = max(date.fromisoformat(changes[0][0]), end - timedelta(days=days))
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
    series, d = [], max(date.fromisoformat(start), end - timedelta(days=370))
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
        if rest.lower() == "compressor":
            return f"কম্প্রেসরে {bn_num(m.group(1))} {unit} ওয়ারেন্টি"
        return f"{bn_num(m.group(1))} {unit} ওয়ারেন্টি" + (f" ({rest})" if rest else "")
    if re.search(r"no\s+warranty", s, re.I):
        return "ওয়ারেন্টি নেই"
    return s


def section_bn(name):
    return SECTION_BN.get(name.lower(), name)


HINTS = {
    "laptop-ram": "কেনার আগে আপনার ল্যাপটপ কোন টাইপ ও স্পিডের র‍্যাম সাপোর্ট করে দেখে নিন।",
    "desktop-ram": "মাদারবোর্ড কোন টাইপ (DDR4/DDR5) সাপোর্ট করে আগে মিলিয়ে নিন।",
    "ssd": "মাদারবোর্ড বা ল্যাপটপে M.2 না SATA স্লট আছে আগে দেখে নিন।",
    "processor": "মাদারবোর্ডের সকেট ও চিপসেট মিলিয়ে নিন।",
    "smartphone": "অফিসিয়াল ও আনঅফিসিয়াল ফোনের ওয়ারেন্টি আলাদা, কেনার সময় নিশ্চিত হয়ে নিন।",
}


def popular_first(i):
    """তালিকার ক্রম: যেটা বেশি দোকানে স্টকে আছে সেটা আগে (মানুষ আসলেই তুলনা দেখতে পায়), তারপর মোট দোকান, তারপর কম দাম"""
    return (i["best"] is None, -i["live_count"], -i["store_count"], (i["best"] or {}).get("price", 0))


def blurb(p, leaf, det):
    name = p["name"]
    feats = det.get("key_features", [])[:4] if det else []
    parts = [f"{name} একটি {leaf['name_bn']}।"]
    if feats:
        parts.append("মূল বৈশিষ্ট্য: " + "; ".join(feats) + "।")
    w = warranty_bn(det.get("warranty")) if det else None
    if w:
        parts.append(f"বিক্রেতার তথ্য অনুযায়ী ওয়ারেন্টি: {w}।")
    hint = HINTS.get(leaf["slug"])
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


def build_size_pages(items, products, details, write, offers=None, crumbs_ld=None):
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
        bspec = {}  # ব্র্যান্ডের নিজস্ব সাইট থেকে পাওয়া স্পেক (url ধরে)
        for bf in (DATA / "brand_specs").glob("*.json") if (DATA / "brand_specs").exists() else []:
            bspec.update(json.loads(bf.read_text()))
        models = []
        for it in rows:
            m = rx.search(it["name"])
            if not m:
                continue
            cap = float(m.group(1))
            cap = int(cap) if cap == int(cap) else cap
            det = details.get(it["id"], {})
            if not det.get("warranty") and offers:
                for o in (offers.get(it["id"]) or {}).values():
                    w = (bspec.get(o.get("url")) or {}).get("warranty")
                    if w:
                        det = {"warranty": w}
                        break
            models.append({"id": it["id"], "n": it["name"], "b": canon[it["brand"].lower()], "s": cap,
                           "t": [k for k, r in types.items() if r.search(it["name"])],
                           "p": (it["best"] or {}).get("price"), "ap": it["any_price"],
                           "st": (it["best"] or {}).get("store"), "w": warranty_bn(det.get("warranty")),
                           "i": [u for u, _ in it["imgs"][:2]]})
        if not models:
            continue
        unit_slug = conf.get("unit_slug", "size")

        def num(x):
            return str(int(x)) if float(x) == int(x) else str(x)

        ranges = []
        for r in conf["ranges"]:
            r = r if isinstance(r, dict) else {"lo": r[0], "hi": r[1]}
            lo, hi = r["lo"], r["hi"]
            label = r.get("label") or (f"{num(hi)}-এর কম" if lo == 0 else f"{num(lo)}+" if hi >= 1000 else f"{num(lo)}–{num(hi)}")
            label = label.translate(BN_DIGITS)
            rslug = r.get("slug") or (f"under-{num(hi)}-{unit_slug}" if lo == 0 else f"{num(lo)}-plus-{unit_slug}" if hi >= 1000
                                      else f"{num(lo)}-{num(hi)}-{unit_slug}")
            sub = [m for m in models if lo <= m["s"] < hi]
            pr = [m["p"] for m in sub if m["p"]]
            ranges.append({"lo": lo, "hi": hi, "label": label, "slug": rslug, "n": len(sub),
                           "b": len({m["b"] for m in sub}), "min": min(pr) if pr else None, "models": sub})

        def page(path, subset, rng):
            sizes = Counter(m["s"] for m in subset)
            bys = defaultdict(set)
            for m in subset:
                bys[m["s"]].add(m["b"])
            exact = [{"s": sz, "n": sizes[sz], "b": len(bys[sz])} for sz in sorted(sizes)]
            priced = [m["p"] for m in subset if m["p"]]
            # প্রথমবার দেখানোর জন্য ব্র্যান্ডভিত্তিক সর্বনিম্ন দাম (স্টকে থাকা), পাতার HTML-এই থাকে
            bmin = {}
            for m in subset:
                if m["p"] and (m["b"] not in bmin or m["p"] < bmin[m["b"]]):
                    bmin[m["b"]] = m["p"]
            bars = sorted(bmin.items(), key=lambda x: x[1])
            nb = len({m["b"] for m in subset})
            what = f"{rng['label']} {conf['unit']} {conf['title']}" if rng else conf["title"]
            of = conf.get("title_of") or conf["title"] + "ের"
            write(path, "size.html", conf=conf, slug=slug, rng=rng, ranges=ranges, exact=exact,
                  models_json=json.dumps(subset, ensure_ascii=False, separators=(",", ":")),
                  total=len(subset), brand_count=nb, lo=min(priced) if priced else None, hi=max(priced) if priced else None,
                  bars=bars, bar_max=max(bmin.values()) if bmin else 1,
                  title=(f"{rng['label']} {conf['unit']} {of} দাম বাংলাদেশে | কোন ব্র্যান্ড কত টাকা | দামতুলনা" if rng
                         else f"{of} দাম সাইজ অনুযায়ী | কোন ব্র্যান্ডের {conf['title']} কত টাকা | দামতুলনা"),
                  description=f"{what}: {nb}টি ব্র্যান্ডের {len(subset)}টি মডেলের দাম পাশাপাশি।"
                              + (f" শুরু {taka(min(priced))} থেকে।" if priced else "") + " কোন ব্র্যান্ড সবচেয়ে কম দামে, এক নজরে।",
                  crumbs=crumbs_ld(("হোম", ""), (f"{conf['title']} সাইজ অনুযায়ী", f"size/{slug}/"),
                                   *([(f"{rng['label']} {conf['unit']}", f"{path}/")] if rng else [])) if crumbs_ld else None,
                  canonical=f"{SITE_URL}/{path}/" if SITE_URL else None)

        page(f"size/{slug}", models, None)
        for r in ranges:
            if r["n"]:
                page(f"size/{slug}/{r['slug']}", r["models"], r)
        for r in ranges:
            r.pop("models")
        made.append({"slug": slug, "category": conf["category"], "title": conf["title"], "unit": conf["unit"], "total": len(models)})
    return made


def image_list(pid, so, products, stores):
    """প্রোডাক্টের ছবির বিকল্প তালিকা [(url, store)], ক্রম: কোম্পানির নিজের সাইট → স্টকে থাকা স্টোর → বাকিরা।
    ছবি আমাদের সার্ভারে রাখা হয় না; স্টোরের ঠিকানা থেকেই দেখানো হয়, না খুললে ব্রাউজার পরেরটা চেষ্টা করে।"""
    out = []
    order = sorted(so.items(), key=lambda kv: (stores.get(kv[0], {}).get("kind") != "brand", not kv[1].get("in_stock")))
    for sid, o in order:
        st = stores.get(sid, {})
        if (o.get("img") or "").startswith("http") and st.get("images", True) and o["img"] not in [u for u, _ in out]:
            out.append((o["img"], sid))
    si = (products.get(pid) or {}).get("store_image")
    if si and si.startswith("http") and si not in [u for u, _ in out]:  # data:… = স্টোরের ফাঁকা লেজি-লোড ছবি, আসল নয়
        host = re.sub(r"^https?://(www\.)?", "", si).split("/")[0]
        sid = next((k for k, v in stores.items() if host and host in v.get("home", "")), None)
        if sid and stores[sid].get("images", True):
            out.append((si, sid))
    return out[:4]


def big_image(url):
    """বড় করে দেখানোর জন্য বড় সাইজের ঠিকানা (জানা নিয়ম থাকলে); না খুললে ব্রাউজার ছোটটাই দেখায়।"""
    return re.sub(r"-(228x228|200x200|250x250|364x364)\.(webp|jpg|png)$", r"-500x500.\2", url)


def brand_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


class Brands:
    """ব্র্যান্ডের নাম পরিষ্কার করা: 'Laptop'/'Paper'-এর মতো সাধারণ শব্দ বাদ, দুই শব্দের ব্র্যান্ড (Cooler Master),
    ভিন্ন বানান এক করা (ASUS/Asus), আর config/brands.json-এর aliases।"""

    def __init__(self):
        f = ROOT / "config/brands.json"
        self.conf = json.loads(f.read_text()) if f.exists() else {}
        self.multi = sorted(self.conf.get("multiword", []), key=len, reverse=True)
        self.generic = set(self.conf.get("generic", []))
        self.aliases = self.conf.get("aliases", {})
        self.info = self.conf.get("info", {})
        self.contains = {k.lower(): v for k, v in self.conf.get("contains", {}).items()}
        self.manual = self.conf.get("manual", {})
        mf = ROOT / "web/static/brands/meta.json"  # tools/fetch_brand_meta: অফিসিয়াল সাইটের লোগো ও সোশ্যাল লিংক
        for slug, m in (json.loads(mf.read_text()) if mf.exists() else {}).items():
            if slug in self.info:
                for k, v in m.items():
                    self.info[slug].setdefault(k, v)
        self.spell = defaultdict(Counter)

    def of(self, name: str, raw: str | None, pid: str | None = None) -> str | None:
        low = name.lower()
        if pid and self.manual.get(pid):  # অ্যাডমিন থেকে হাতে বসানো
            raw = self.manual[pid]
            slug = self.aliases.get(brand_slug(raw), brand_slug(raw))
            self.spell[slug][raw] += 1
            return slug
        for k, v in self.contains.items():  # নামের মাঝখানে থাকা ব্র্যান্ড (যেমন "... BIRLA CABLE")
            if k in low:
                slug = self.aliases.get(brand_slug(v), brand_slug(v))
                self.spell[slug][v] += 1
                return slug
        for m in self.multi:
            if low.startswith(m.lower() + " ") or low.startswith(m.lower().replace(" ", "-") + " "):
                raw = m
                break
        raw = (raw or name.split()[0]).strip()
        if not raw or raw.lower() in self.generic or re.fullmatch(r"[\d\W]+", raw):
            return None
        slug = brand_slug(raw)
        slug = self.aliases.get(slug, slug)
        self.spell[slug][raw] += 1
        return slug

    def display(self, slug: str) -> str:
        if self.info.get(slug, {}).get("name"):
            return self.info[slug]["name"]
        c = self.spell.get(slug)
        if not c:
            return slug
        # সবচেয়ে বেশি ব্যবহৃত বানান; সব বড় হাতের হলে আর ৪ অক্ষরের বেশি হলে প্রথম অক্ষর বড়
        best = c.most_common(1)[0][0]
        mixed = [b for b, _ in c.most_common() if not b.isupper()]
        return best if not best.isupper() or len(best) <= 4 or not mixed else mixed[0]


def build_brand_pages(items, leaves, group_of, BR, write, crumbs_ld=None):
    """প্রতিটা ব্র্যান্ডের পাতা (/brand/<slug>/), ব্র্যান্ড+ক্যাটাগরি পাতা (/brand/<slug>/<cat>/), আর সব ব্র্যান্ডের তালিকা।"""
    minp = BR.conf.get("min_products", 5)
    by = defaultdict(list)
    for it in items.values():
        if it["bslug"]:
            by[it["bslug"]].append(it)
    cards = []
    order = popular_first
    for slug, lst in by.items():
        if len(lst) < minp:
            continue
        name, info = BR.display(slug), BR.info.get(slug, {})
        cats = defaultdict(list)
        for it in lst:
            cats[it["category"]].append(it)
        cat_cards = []
        for c, cl in sorted(cats.items(), key=lambda x: -len(x[1])):
            cl.sort(key=order)
            priced = [i["best"]["price"] for i in cl if i["best"]]
            has_page = len(cl) >= 3
            cat_cards.append({"slug": c, "name_bn": leaves[c]["name_bn"], "name_en": leaves[c].get("name_en", ""), "count": len(cl),
                              "min": min(priced) if priced else None, "page": has_page, "few": cl[:6] if not has_page else []})
            if has_page:
                pages = max(1, -(-len(cl) // PER_PAGE))
                for n in range(1, pages + 1):
                    write(f"brand/{slug}/{c}" + (f"/{n}" if n > 1 else ""), "brand_cat.html", bname=name, bslug=slug, cat=leaves[c],
                          items=cl[(n - 1) * PER_PAGE:n * PER_PAGE], total=len(cl), page=n, pages=pages, info=info,
                          title=f"{name} {leaves[c]['name_bn']} দাম বাংলাদেশে | {name} {leaves[c].get('name_en', '')} Price in BD" + (f" (পাতা {n})" if n > 1 else ""),
                          description=f"{name}-এর {len(cl)}টি {leaves[c]['name_bn']}-এর দাম বিভিন্ন স্টোরে মিলিয়ে দেখুন।"
                                      + (f" শুরু {taka(min(priced))} থেকে।" if priced else "") + (f" পাতা {n}/{pages}।" if n > 1 else ""),
                          crumbs=crumbs_ld(("হোম", ""), ("সব ব্র্যান্ড", "brand/"), (name, f"brand/{slug}/"),
                                           (f"{name} {leaves[c]['name_bn']}", f"brand/{slug}/{c}/" + (f"{n}/" if n > 1 else ""))) if crumbs_ld else None,
                          canonical=f"{SITE_URL}/brand/{slug}/{c}/" + (f"{n}/" if n > 1 else "") if SITE_URL else None)
        priced = [i["best"]["price"] for i in lst if i["best"]]
        deals = sorted([i for i in lst if i["saving"] > 0], key=lambda i: (-i["live_count"], -i["saving"]))[:6]
        stats = {"count": len(lst), "cats": len(cats), "min": min(priced) if priced else None, "max": max(priced) if priced else None,
                 "live": sum(1 for i in lst if i["best"]), "multi": sum(1 for i in lst if i["store_count"] > 1)}
        write(f"brand/{slug}", "brand.html", bname=name, bslug=slug, info=info, stats=stats, cats=cat_cards, deals=deals,
              title=f"{name} প্রোডাক্টের দাম বাংলাদেশে | {name} Price in BD | দামতুলনা",
              description=(info.get("about", "")[:120] + " " if info.get("about") else "")
                          + f"{name}-এর {len(lst)}টি প্রোডাক্টের দাম {len(cats)}টি ক্যাটাগরিতে।",
              crumbs=crumbs_ld(("হোম", ""), ("সব ব্র্যান্ড", "brand/"), (name, f"brand/{slug}/")) if crumbs_ld else None,
              canonical=f"{SITE_URL}/brand/{slug}/" if SITE_URL else None)
        top = [c["name_bn"] for c in cat_cards[:3]]
        cards.append({"slug": slug, "name": name, "count": len(lst), "top": top, "logo": info.get("logo"),
                      "letter": (name[:1].upper() if name[:1].isalpha() else "#")})
    cards.sort(key=lambda c: c["name"].lower())
    letters = defaultdict(list)
    for c in cards:
        letters[c["letter"]].append(c)
    popular = sorted(cards, key=lambda c: -c["count"])[:24]
    write("brand", "brands.html", popular=popular, letters=sorted(letters.items()), total=len(cards),
          cards_json=json.dumps([{"s": c["slug"], "n": c["name"], "k": c["count"]} for c in cards], ensure_ascii=False, separators=(",", ":")),
          title="সব ব্র্যান্ড | কোন ব্র্যান্ডের কী প্রোডাক্ট, কত দাম | দামতুলনা",
          description=f"{len(cards)}টি ব্র্যান্ডের প্রোডাক্ট ও দাম এক জায়গায়।", canonical=f"{SITE_URL}/brand/" if SITE_URL else None,
          crumbs=crumbs_ld(("হোম", ""), ("সব ব্র্যান্ড", "brand/")) if crumbs_ld else None)
    return sorted(cards, key=lambda c: -c["count"])


def bn_amount(n):
    """২০০০০ → ২০ হাজার, ১০০০০০ → ১ লাখ, ১৫০০ → ১,৫০০"""
    if n >= 100000 and n % 100000 == 0:
        return f"{bn_num(n // 100000)} লাখ"
    if n >= 100000 and n % 10000 == 0:
        return f"{(n / 100000):g} লাখ".translate(BN_DIGITS)
    if n % 1000 == 0:
        return f"{bn_num(n // 1000)} হাজার"
    return bn_num(n)


def _best_badges(ranked, nums_of, prof):
    """ডাটা থেকে "কার জন্য সেরা" লেবেল: {পণ্য id: [লেবেল]}"""
    out = defaultdict(list)
    if not ranked:
        return out
    top = max(ranked, key=lambda i: (i["live_count"], -i["best"]["price"]))
    if top["live_count"] > 1:
        out[top["id"]].append("🏆 সবচেয়ে বেশি দোকানে")
    out[min(ranked, key=lambda i: i["best"]["price"])["id"]].append("💰 সবচেয়ে কম দাম")
    sv = max(ranked, key=lambda i: i["saving"])
    if sv["saving"] >= 500:
        out[sv["id"]].append("🪙 দোকান বাছলে সবচেয়ে বেশি সাশ্রয়")
    for label, _, unit, noun in INS.COMPARE.get(prof, []):
        vals = [(nums_of.get(i["id"], {}).get(label), i) for i in ranked]
        vals = [(v, i) for v, i in vals if v]
        if len(vals) < 4:
            continue
        mx = max(v for v, _ in vals)
        winners = [i for v, i in vals if v == mx]
        if len(winners) == 1 and mx > sorted(v for v, _ in vals)[len(vals) // 2]:
            out[winners[0]["id"]].append(f"⭐ এই বাজেটে সবচেয়ে বেশি {noun} ({INS.fmt_val(mx, unit)})")
    return out


def _spec_line(it, nums_of, prof):
    n = nums_of.get(it["id"]) or {}
    parts = [f"{INS.fmt_val(n[l], u)} {noun}" for l, _, u, noun in INS.COMPARE.get(prof, []) if l in n]
    if not parts and it.get("fx"):
        parts = [v[0] for v in it["fx"].values()][:3]
    return " · ".join(parts)


def build_budget_pages(items, leaves, group_of, write, today, crumbs_ld, SITE_URL, need_hub=None, peer_pool=None, cat_profile=None,
                       guides=None, stores=None):
    """config/budget_pages.json থেকে "৳X-এর মধ্যে সেরা" পেজ, আর যেখানে যথেষ্ট মডেল আছে সেখানে ব্র্যান্ড × বাজেট পেজ।
    ফেরত: (হাবের তালিকা, {ক্যাটাগরি: [(টাকা, slug)]})"""
    f = ROOT / "config/budget_pages.json"
    if not f.exists():
        return [], {}
    full = json.loads(f.read_text())
    conf, en_names, brand_min = full.get("pages", {}), full.get("en", {}), full.get("brand_min", 6)
    peer_pool, cat_profile, guides = peer_pool or {}, cat_profile or {}, guides or {}
    by_cat = defaultdict(list)
    for it in items.values():
        if it["best"] and not it["sus"]:
            by_cat[it["category"]].append(it)
    month = f"{BN_MONTHS[int(today[5:7]) - 1]} {today[:4]}".translate(BN_DIGITS)
    hub, links = [], {}
    rank_key = lambda amt: (lambda i: -(min(i["live_count"], 5) * 2 + 3 * i["best"]["price"] / amt))

    def faq_for(pool, ranked, words, cname, prof, nums_of, brand=None):
        who = f"{brand}-এর " if brand else ""
        multi = sum(1 for i in pool if i["live_count"] > 1)
        ch = min(pool, key=lambda i: i["best"]["price"])
        top = max(pool, key=lambda i: (i["live_count"], -i["best"]["price"]))
        q = [(f"{words} টাকার মধ্যে আজ {who}কয়টা {cname} স্টকে আছে?",
              f"আজ {bn_num(len(pool))}টা; এর মধ্যে {bn_num(multi)}টা একাধিক দোকানে পাওয়া যায়, তাই দাম মিলিয়ে কেনা যায়।"),
             (f"{words} টাকার মধ্যে সবচেয়ে কম দামের {who}{cname} কোনটা?",
              f"আজকের হিসাবে {ch['name']}, {taka(ch['best']['price'])} ({stores[ch['best']['store']]['name']})।")]
        if top["live_count"] > 1:
            q.append((f"সবচেয়ে বেশি দোকানে পাওয়া যায় কোনটা?",
                      f"{top['name']}, আজ {bn_num(top['live_count'])}টা দোকানে; সবচেয়ে কম {taka(top['best']['price'])} ({stores[top['best']['store']]['name']})।"))
        for label, _, unit, noun in INS.COMPARE.get(prof, [])[:2]:
            vals = [(nums_of.get(i["id"], {}).get(label), i) for i in pool]
            vals = [(v, i) for v, i in vals if v]
            if len(vals) >= 4:
                v, i = max(vals, key=lambda x: (x[0], -x[1]["best"]["price"]))
                q.append((f"এই বাজেটে সবচেয়ে বেশি {noun} কোনটায়?", f"{i['name']} ({INS.fmt_val(v, unit)}), দাম {taka(i['best']['price'])}।"))
        q.append(("এই তালিকার দাম কত দিন পরপর হালনাগাদ হয়?", "প্রতিদিন। সব দোকানের দাম নতুন করে তুলে তালিকা আবার সাজানো হয়।"))
        return q

    def render(slug, cat, leaf, amt, pool, ranked, sibl, brand=None, brand_links=None):
        prof = cat_profile.get(cat)
        nums_of = {i_: n_ for _, i_, n_ in peer_pool.get(cat, [])}
        words = bn_amount(amt)
        en = en_names.get(cat, leaf["name_bn"])
        bname = brand["name"] if brand else None
        title_bn = f"{words} টাকার মধ্যে {bname + ' ' if bname else ''}সেরা {leaf['name_bn']} ({month})"
        title_en = f"Best {bname + ' ' if bname else ''}{en} Under {amt:,} Taka in Bangladesh"
        badges = _best_badges(ranked, nums_of, prof)
        rows = [dict(i, specline=_spec_line(i, nums_of, prof), badges=badges.get(i["id"], [])) for i in ranked]
        faq = faq_for(pool, ranked, words, leaf["name_bn"], prof, nums_of, bname)
        grp = group_of[cat]
        ld = [{"@context": "https://schema.org", "@type": "ItemList", "name": title_bn, "itemListElement": [
                  {"@type": "ListItem", "position": k + 1, "url": f"{SITE_URL}/p/{i['id']}/", "name": i["name"]} for k, i in enumerate(ranked)]},
              {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                  {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in faq]}]
        crumb = [("হোম", ""), ("বাজেট অনুযায়ী সেরা", "best/"), (leaf["name_bn"], f"c/{cat}/")]
        if brand:
            crumb.append((f"{words} টাকার মধ্যে", f"best/{cat}-under-{amt}/"))
        crumb.append((bname or f"{words} টাকার মধ্যে", f"best/{slug}/"))
        write(f"best/{slug}", "best.html", cat=leaf, group=grp, amt=amt, words=words, month=month, ranked=rows,
              pool_n=len(pool), multi_n=sum(1 for i in pool if i["live_count"] > 1),
              cheapest=min(pool, key=lambda i: i["best"]["price"]), siblings=sibl, brand=brand, brand_links=brand_links or [],
              guide=guides.get(cat), faq=faq, title_en=title_en, itemlist=[json.dumps(x, ensure_ascii=False) for x in ld],
              noindex=len(pool) < 8,
              crumbs=crumbs_ld(*crumb), title=f"{title_bn} | {title_en}",
              description=(f"{words} টাকার মধ্যে আজ স্টকে থাকা {bn_num(len(pool))}টি {bname + ' ' if bname else ''}{leaf['name_bn']}: "
                           f"সর্বনিম্ন {taka(min(i['best']['price'] for i in pool))}, দোকানভেদে আজকের দাম আর কোথায় কিনলে কত বাঁচে।"),
              canonical=f"{SITE_URL}/best/{slug}/" if SITE_URL else None)

    brand_total = 0
    for cat, amounts in conf.items():
        leaf = leaves.get(cat)
        if not leaf:
            continue
        made = []
        for amt in sorted(amounts):
            pool = [i for i in by_cat.get(cat, []) if amt * 0.4 <= i["best"]["price"] <= amt]
            if len(pool) < 5:
                continue
            # বেশি দোকানে বিক্রি = বেশি চলে এমন মডেল; বাজেটের কাছাকাছি দাম = সাধারণত ভালো কনফিগারেশন
            ranked = sorted(pool, key=rank_key(amt))[:20]
            made.append((amt, f"{cat}-under-{amt}", pool, ranked))
        if not made:
            continue
        links[cat] = [(amt, slug) for amt, slug, _, _ in made]
        top_pick = None
        for amt, slug, pool, ranked in made:
            # ব্র্যান্ড × বাজেট: এই বাজেটে কোনো ব্র্যান্ডের যথেষ্ট মডেল থাকলে
            byb = defaultdict(list)
            for i in pool:
                if i.get("bslug"):
                    byb[i["bslug"]].append(i)
            blinks = []
            for bs, lst in sorted(byb.items(), key=lambda x: -len(x[1])):
                if len(lst) >= brand_min:
                    blinks.append((bs, lst[0]["brand"], f"{bs}-{cat}-under-{amt}", len(lst)))
            render(slug, cat, leaf, amt, pool, ranked, links[cat], brand_links=blinks)
            for bs, bname, bslug_page, n in blinks:
                lst = byb[bs]
                render(bslug_page, cat, leaf, amt, lst, sorted(lst, key=rank_key(amt))[:20], links[cat],
                       brand={"slug": bs, "name": bname}, brand_links=blinks)
                brand_total += 1
            if top_pick is None or len(pool) >= 8 and top_pick[0] < 8:
                top_pick = (len(pool), ranked[0], amt, slug)
        hub.append({"cat": leaf, "links": links[cat], "top": top_pick})
    print(f"বাজেট পাতা: {sum(len(v) for v in links.values())}টা, ব্র্যান্ড × বাজেট: {brand_total}টা")
    popular = [(c_, a_, f"{c_}-under-{a_}") for c_, a_ in full.get("popular", []) if (a_, f"{c_}-under-{a_}") in links.get(c_, [])]
    if hub:
        write("best", "best_hub.html", hub=hub, need_hub=need_hub or [], month=month, popular=popular,
              title="বাজেট অনুযায়ী সেরা প্রোডাক্ট (" + month + ") | Best Products by Budget in Bangladesh",
              description="বাজেট অনুযায়ী সেরা ফোন, ল্যাপটপ, মনিটর, টিভি, ফ্রিজ ও আরও অনেক কিছু: প্রতিদিনের দাম, দোকানভেদে তুলনা আর কোথায় কিনলে কত বাঁচে।",
              crumbs=crumbs_ld(("হোম", ""), ("বাজেট অনুযায়ী সেরা", "best/")), canonical=f"{SITE_URL}/best/" if SITE_URL else None)
    return hub, links


def build_need_pages(items, leaves, group_of, write, today, crumbs_ld, SITE_URL, peer_pool, cat_profile, guides=None):
    """config/need_pages.json: "পড়াশোনার ল্যাপটপ ৳৬০ হাজারের মধ্যে" ধরনের পাতা — নিয়ম (স্পেকের সর্বনিম্ন) লেখা থাকে,
    তালিকা আজকের দাম আর আমাদের স্পেক থেকে। ফেরত: হাবের তালিকা"""
    f = ROOT / "config/need_pages.json"
    if not f.exists():
        return []
    month = f"{BN_MONTHS[int(today[5:7]) - 1]} {today[:4]}".translate(BN_DIGITS)
    guides = guides or {}
    hub = []
    for pg in json.loads(f.read_text()).get("pages", []):
        cat, mx, rules = pg["cat"], pg["max"], pg["rules"]
        leaf, prof = leaves.get(cat), cat_profile.get(cat)
        if not leaf or cat not in peer_pool:
            continue
        units = {l: u for l, _, u, _ in INS.COMPARE.get(prof, [])}
        pool = [(pr, i_, n_) for pr, i_, n_ in peer_pool[cat]
                if pr <= mx and not items[i_]["sus"] and all(n_.get(l, 0) >= v for l, v in rules.items())]
        if len(pool) < 5:
            continue
        # বেশি দোকানে আছে আগে, তারপর নিয়মের ঘরগুলোয় বেশি, তারপর কম দাম
        pool.sort(key=lambda x: (-min(items[x[1]]["live_count"], 4), [-x[2].get(l, 0) for l in rules], x[0]))
        ranked = []
        for pr, i_, n_ in pool[:20]:
            it = items[i_]
            ranked.append(dict(it, specs=[f"{INS.fmt_val(n_[l], units[l])} {l}" for l in rules if l in n_]))
        words = bn_amount(mx)
        title = f"{words} টাকার মধ্যে {pg['title']} ({month})"
        rule_txt = ", ".join(f"{l} কমপক্ষে {INS.fmt_val(v, units[l])}" for l, v in rules.items())
        grp = group_of[cat]
        ld = {"@context": "https://schema.org", "@type": "ItemList", "name": title, "itemListElement": [
            {"@type": "ListItem", "position": k + 1, "url": f"{SITE_URL}/p/{i['id']}/", "name": i["name"]} for k, i in enumerate(ranked)]}
        write(f"need/{pg['slug']}", "need.html", guide=guides.get(cat), cat=leaf, group=grp, pg=pg, words=words, month=month, ranked=ranked, pool_n=len(pool),
              rule_txt=rule_txt, itemlist=json.dumps(ld, ensure_ascii=False),
              crumbs=crumbs_ld(("হোম", ""), ("বাজেট অনুযায়ী সেরা", "best/"), (pg["title"], f"need/{pg['slug']}/")),
              title=title + " | দামতুলনা",
              description=f"{words} টাকার মধ্যে {pg['title']}: {rule_txt}। আজ এমন {len(pool)}টি স্টকে আছে, দোকানভেদে আজকের দামসহ।",
              canonical=f"{SITE_URL}/need/{pg['slug']}/" if SITE_URL else None)
        hub.append({"slug": pg["slug"], "title": pg["title"], "amt": mx, "n": len(pool), "cat": leaf})
    return hub


PCB_KEY = {"প্রসেসর": "cpu", "মাদারবোর্ড": "mb", "র‍্যাম": "ram", "SSD": "ssd", "গ্রাফিক্স কার্ড": "gpu",
           "পাওয়ার সাপ্লাই": "psu", "কেসিং": "case", "সিপিইউ কুলার": "cooler"}


def build_pc_pages(items, write, today, crumbs_ld, SITE_URL, stores):
    """/build/pc-under-<টাকা>/: বাজেট অনুযায়ী পূর্ণ পিসি বিল্ড (web/pcbuild.py), প্রতিদিনের সবচেয়ে কম দামে।"""
    from web import pcbuild
    from urllib.parse import urlencode
    builds = pcbuild.build_all(items)
    month = f"{BN_MONTHS[int(today[5:7]) - 1]} {today[:4]}".translate(BN_DIGITS)
    sib = [(b["amt"], f"pc-under-{b['amt']}", b["label"]) for b in builds]
    for b in builds:
        words = bn_amount(b["amt"])
        slug = f"pc-under-{b['amt']}"
        b["slug"] = slug
        b["builder"] = "?" + urlencode({PCB_KEY[r]: p["id"] for r, p in b["parts"] if r in PCB_KEY})
        b["store_n"] = len({p["best"]["store"] for _, p in b["parts"]})
        b["left"] = b["amt"] - b["total"]
        cpu = b["parts"][0][1]
        gpu = next((p for r, p in b["parts"] if r == "গ্রাফিক্স কার্ড"), None)
        faq = [(f"{words} টাকায় পিসি বানাতে আজ মোট কত লাগবে?",
                f"আমাদের বাছাই করা পার্টস দিয়ে আজকের সর্বনিম্ন দামে মোট {taka(b['total'])}; প্রতিটা পার্টস যে দোকানে সবচেয়ে সস্তা সেখান থেকে কিনলে।"),
               ("এই বিল্ডে কোন প্রসেসর?", f"{cpu['name']}, আজ {taka(cpu['best']['price'])} ({stores[cpu['best']['store']]['name']})।"),
               ("গেম খেলা যাবে?", (f"হ্যাঁ, {gpu['name']} গ্রাফিক্স কার্ড আছে; {b['use']}।" if gpu else
                                   "এই বিল্ডে আলাদা গ্রাফিক্স কার্ড নেই, প্রসেসরের গ্রাফিক্সে হালকা ও পুরনো গেম চলবে। নিয়মিত গেম খেললে উপরের বাজেটের বিল্ড দেখুন।")),
               ("পার্টসগুলো কি একসাথে চলবে?", f"হ্যাঁ, প্রসেসর আর মাদারবোর্ডের সকেট এক ({b['socket']}), র‍্যাম {b['ddr']}, আর মাদারবোর্ড মাইক্রো-ATX যা প্রায় সব কেসিংয়ে ধরে। তবু কেনার আগে দোকানে একবার নিশ্চিত হয়ে নিন।"),
               ("দাম কত দিন পরপর হালনাগাদ হয়?", "প্রতিদিন। পার্টসের দাম বা স্টক বদলালে বিল্ডও নিজে থেকে বদলে যায়।")]
        ld = [{"@context": "https://schema.org", "@type": "ItemList", "name": f"{words} টাকায় পিসি বিল্ড", "itemListElement": [
                  {"@type": "ListItem", "position": k + 1, "url": f"{SITE_URL}/p/{p['id']}/", "name": p["name"]} for k, (_, p) in enumerate(b["parts"])]},
              {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                  {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in faq]}]
        write(f"build/{slug}", "pcbuild.html", b=b, words=words, month=month, siblings=sib, faq=faq,
              itemlist=[json.dumps(x, ensure_ascii=False) for x in ld],
              title=f"{words} টাকায় পিসি বিল্ড ({month}) | PC Build Under {b['amt']:,} Taka in Bangladesh",
              description=f"{words} টাকার মধ্যে {b['label']} পিসি বিল্ড: আজকের সর্বনিম্ন দামে মোট {taka(b['total'])}, প্রতিটা পার্টস কোন দোকানে সবচেয়ে সস্তা, আর পার্টস মানানসই কিনা যাচাই করা।",
              crumbs=crumbs_ld(("হোম", ""), ("পিসি বিল্ড", "build/"), (f"{words} টাকায়", f"build/{slug}/")),
              canonical=f"{SITE_URL}/build/{slug}/" if SITE_URL else None)
    if builds:
        write("build", "pcbuild_hub.html", builds=builds, month=month,
              title=f"বাজেট অনুযায়ী পিসি বিল্ড ({month}) | PC Build Guide Bangladesh",
              description="৩০ হাজার থেকে ১.৫ লাখ টাকা বাজেটে পূর্ণ পিসি বিল্ড: প্রতিদিনের সবচেয়ে কম দাম, প্রতিটা পার্টস কোন দোকানে সস্তা, আর পার্টস মানানসই কিনা যাচাই করা।",
              crumbs=crumbs_ld(("হোম", ""), ("পিসি বিল্ড", "build/")), canonical=f"{SITE_URL}/build/" if SITE_URL else None)
    print(f"পিসি বিল্ড পাতা: {len(builds)}টা")
    return builds


def build_store_pages(items, offers, stores, enabled, leaves, write, crumbs_ld, SITE_URL):
    """/store/<id>/: স্টোরের তথ্য (config/store_info.json) + আমাদের ডাটা থেকে কোথায় সস্তা।"""
    f = ROOT / "config/store_info.json"
    info = json.loads(f.read_text()).get("stores", {}) if f.exists() else {}
    cards = []
    for s_ in enabled:
        listed = [pid for pid in items if offers.get(pid, {}).get(s_, {}).get("price")]
        live = [pid for pid in listed if offers[pid][s_].get("in_stock")]
        contested = [pid for pid in live if items[pid]["live_count"] > 1 and items[pid]["best"]]
        wins = [pid for pid in contested if items[pid]["best"]["store"] == s_]
        cat_tot, cat_win = Counter(items[p]["category"] for p in contested), Counter(items[p]["category"] for p in wins)
        strong = sorted(((c, cat_win[c], n) for c, n in cat_tot.items() if n >= 8 and cat_win[c] / n >= 0.4),
                        key=lambda x: -x[1] / x[2])[:8]
        top_cats = Counter(items[p]["category"] for p in live).most_common(10)
        st = {"listed": len(listed), "live": len(live), "contested": len(contested), "wins": len(wins),
              "share": round(100 * len(wins) / len(contested)) if contested else None}
        card = {"id": s_, "name": stores[s_]["name"], "logo": stores[s_].get("logo"), "dark": stores[s_].get("logo_dark"),
                "home": stores[s_].get("home"), "info": info.get(s_, {}), "st": st,
                "strong": [(leaves[c], w, n) for c, w, n in strong if c in leaves],
                "top": [(leaves[c], n) for c, n in top_cats if c in leaves]}
        cards.append(card)
        write(f"store/{s_}", "store.html", s=card, title=f"{card['name']}: ঠিকানা, হটলাইন, ডেলিভারি, EMI ও দাম | দামতুলনা",
              description=f"{card['name']}-এর হটলাইন, শোরুম, ডেলিভারি ও EMI তথ্য, আর কোন কোন প্রোডাক্টে {card['name']}-এ দাম সবচেয়ে কম।",
              crumbs=crumbs_ld(("হোম", ""), ("স্টোর", "store/"), (card["name"], f"store/{s_}/")),
              canonical=f"{SITE_URL}/store/{s_}/" if SITE_URL else None)
    write("store", "stores.html", cards=cards, title="বাংলাদেশের কম্পিউটার ও ইলেকট্রনিক্স দোকান | দামতুলনা",
          description="দামতুলনায় যেসব দোকানের দাম মেলানো হয়: হটলাইন, শোরুম, ডেলিভারি, EMI আর কোথায় কী সস্তা।",
          crumbs=crumbs_ld(("হোম", ""), ("স্টোর", "store/")), canonical=f"{SITE_URL}/store/" if SITE_URL else None)
    return cards


def load_details(folder="details"):
    out = {}
    base = DATA / folder
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
    brand_details = load_details("brand_details")
    today = health["date"]
    updated = bn_date(today) + ", " + health["scraped_at"][11:16]
    # হাতে যাচাই করা দাম (অ্যাডমিন → হাতে দাম): যে দোকান স্বয়ংক্রিয় ভিজিট আটকায়, সেখানে মানুষ দেখে দাম বসায়
    manual = json.loads((DATA / "manual_prices.json").read_text()) if (DATA / "manual_prices.json").exists() else {}
    manual_n = 0
    for mpid, per in manual.items():
        if mpid.startswith("_") or mpid not in products or not isinstance(per, dict):
            continue
        for msid, m in per.items():
            try:
                age_m = (date.fromisoformat(today) - date.fromisoformat(m["date"])).days
            except Exception:
                continue
            if msid not in stores or not m.get("price") or age_m > MANUAL_MAX_DAYS or msid in (offers.get(mpid) or {}):
                continue
            instock = m.get("in_stock", True)
            offers.setdefault(mpid, {})[msid] = {"name": products[mpid]["name"], "url": m.get("url") or stores[msid]["home"],
                                                 "price": int(m["price"]), "regular": None, "in_stock": instock,
                                                 "status": "ok" if instock else "out", "seen": m["date"], "manual": True}
            manual_n += 1
    enabled = [s for s, v in stores.items() if v["enabled"] or (v.get("manual") and manual_n)]
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
    env.filters["bn_date"] = bn_date
    env.filters["galts"] = lambda g: json.dumps([[x["u"], x["n"], x["h"]] for x in g], ensure_ascii=False)
    env.filters["alts_simple"] = lambda l: json.dumps([[u] for u, _ in l])
    # ক্যাটাগরি আইকন (config/category_icons.json → static/cat-icons.svg স্প্রাইট)
    from markupsafe import Markup
    _ic_file = ROOT / "config/category_icons.json"
    _ic = json.loads(_ic_file.read_text()) if _ic_file.exists() else {"groups": {}, "leaves": {}}
    _sp = ROOT / "web/static/cat-icons.svg"
    _icv = zlib.crc32(_sp.read_bytes()) if _sp.exists() else 0  # ফাইল বদলালেই কেবল নতুন করে ডাউনলোড

    # রং: ১২টা রঙের প্যালেট (style.css-এর .k0–.k11)। প্রতিটা ক্যাটাগরি আলাদা রং, আর একই পাতায় পাশাপাশি
    # সাব-ক্যাটাগরিগুলোও আলাদা রং পায়।
    _kc = {}
    for gi, g in enumerate(tax["groups"]):
        _kc[("g", g["slug"])] = gi % 12
        for li, l in enumerate(g["leaves"]):
            _kc[("l", l["slug"])] = (gi + li) % 12

    def cicon(slug, group=False, cls="ci"):
        name = (_ic["groups"] if group else _ic["leaves"]).get(slug) or _ic["groups"].get(slug) or "box"
        k = _kc.get(("g" if group else "l", slug), 0)
        return Markup(f'<svg class="{cls} k{k}" aria-hidden="true"><use href="{BASE}/static/cat-icons.svg?v={_icv}#i-{name}"/></svg>')

    common = {"base": BASE, "cicon": cicon, "stores": stores, "updated": updated, "build_id": int(t0), "spec_names": SPEC_NAMES,
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
    for k in mm.get("drop_offer", []):  # অ্যাডমিন: "এই স্টোরের মিল ভুল" (pid|store)
        pid_, st_ = k.split("|", 1)
        if pid_ in offers:
            offers[pid_].pop(st_, None)
    price_ok = set(mm.get("price_ok", []))  # অ্যাডমিন: "দাম ঠিক আছে" (pid|store)
    # স্বয়ংক্রিয় মিল (মডেল নম্বর দিয়ে); পুরনো লিংক নতুন পাতায় রিডাইরেক্ট হবে
    amap, auto_sugg = auto_merges(products, offers, mm.get("not_same", []), {k_: g_["slug"] for k_, g_ in group_of.items()},
                                  with_suggestions=True)
    for old, keep in amap.items():
        if old in offers and keep in offers:
            for st_, o_ in offers.pop(old).items():
                k_o = offers[keep].get(st_)
                # একই দোকান দুইবার: যেটায় দাম/স্টক আছে সেটা থাকে
                if k_o is None or (not k_o.get("price") and o_.get("price")) or (o_.get("in_stock") and not k_o.get("in_stock") and o_.get("price")):
                    offers[keep][st_] = o_
            for st_, ch_ in history.pop(old, {}).items():
                if not history[keep].get(st_):
                    history[keep][st_].extend(ch_)
                    continue
                # একই দোকান দুই তালিকায়: একই দিনের দুই দাম হলে যেটায় দাম আছে সেটা (কম দামটা)
                by_d = {}
                for d_, v_ in list(history[keep][st_]) + list(ch_):
                    if d_ not in by_d or by_d[d_] is None or (v_ is not None and v_ < by_d[d_]):
                        by_d[d_] = v_ if v_ is not None or d_ not in by_d else by_d[d_]
                history[keep][st_][:] = sorted(by_d.items())
            if old in details and keep not in details:
                details[keep] = details[old]
    amap = {k: v for k, v in amap.items() if k not in offers}

    BR = Brands()
    items = {}
    for pid, so in offers.items():
        p = products.get(pid)
        if not p or p["category"] not in leaves:
            continue
        det = details.get(pid, {})
        live_all = sorted(((s, o) for s, o in so.items() if o.get("in_stock") and o.get("price")), key=lambda x: x[1]["price"])
        # বিশ্বস্ত দোকানের (stores.json-এ "trusted": true, যেমন Star Tech, Ryans) দাম কখনো সন্দেহজনক ধরা হয় না
        sus = {s_ for s_ in suspect_stores(live_all) if f"{pid}|{s_}" not in price_ok and not stores.get(s_, {}).get("trusted")}
        live = [x for x in live_all if x[0] not in sus]  # সর্বনিম্ন দাম ও সাশ্রয় শুধু বিশ্বাসযোগ্য দাম থেকে
        best = {"store": live[0][0], "price": live[0][1]["price"], "url": live[0][1]["url"]} if live else None
        any_price = min((o["price"] for o in so.values() if o.get("price")), default=None)
        bslug = BR.of(p["name"], det.get("brand") if det.get("brand") not in (None, "", "Others") else p["brand"], pid)
        brand = bslug or ""
        imgs = image_list(pid, so, products, stores)
        items[pid] = {"id": pid, "name": p["name"], "category": p["category"], "cat_name": leaves[p["category"]]["name_bn"],
                      "group": group_of[p["category"]]["slug"], "brand": brand, "bslug": bslug, "best": best, "any_price": any_price,
                      "saving": live[-1][1]["price"] - live[0][1]["price"] if len(live) > 1 else 0,
                      "worst": {"store": live[-1][0], "price": live[-1][1]["price"]} if len(live) > 1 else None,
                      "store_count": len([o for o in so.values() if o.get("price")]), "live_count": len(live_all), "sus": sorted(sus),
                      "created": p["created"], "specs": p["specs"], "imgs": imgs,
                      "facets": " ".join(x for x in [p["specs"].get(k) for k in ("capacity", "type", "interface", "brand_cpu")] if x),
                      "fx": facets_for(p["category"], p["name"], p["specs"], (det.get("key_features") or p.get("features") or []))}

    # একক স্টোরের অবাস্তব দাম (যেমন ফ্রিজ ৳২৪): ক্যাটাগরির সাধারণ দামের ৫%-এর কম হলে "যাচাই চলছে"
    cat_prices = defaultdict(list)
    for it in items.values():
        if it["best"]:
            cat_prices[it["category"]].append(it["best"]["price"])
    cat_med = {c_: sorted(v_)[len(v_) // 2] for c_, v_ in cat_prices.items() if len(v_) >= 10}
    for pid, it in items.items():
        med = cat_med.get(it["category"])
        if not med or f"{pid}|{(it['best'] or {}).get('store')}" in price_ok:
            continue
        low = {s_ for s_, o in offers[pid].items() if o.get("in_stock") and o.get("price") and o["price"] < med * 0.05
               and f"{pid}|{s_}" not in price_ok and not stores.get(s_, {}).get("trusted")}
        if low:
            it["sus"] = sorted(set(it["sus"]) | low)
            ok_ = sorted(((s_, o) for s_, o in offers[pid].items() if o.get("in_stock") and o.get("price") and s_ not in it["sus"]),
                         key=lambda x: x[1]["price"])
            it["best"] = {"store": ok_[0][0], "price": ok_[0][1]["price"], "url": ok_[0][1]["url"]} if ok_ else None
            it["saving"] = ok_[-1][1]["price"] - ok_[0][1]["price"] if len(ok_) > 1 else 0
            it["worst"] = {"store": ok_[-1][0], "price": ok_[-1][1]["price"]} if len(ok_) > 1 else None

    # ===== স্টকের অবস্থা: স্টকে / আংশিক / আসছে / সদ্য শেষ / স্টক শেষ / বন্ধ =====
    # নিয়ম (স্টক শেষ প্রোডাক্টের নীতি): শুধু কেনা যায় এমন প্রোডাক্ট তালিকা আর গুগলে যায়। কোথাও স্টকে নেই এমন
    # প্রোডাক্টের পাতা থাকে (লিংক ভাঙে না, "স্টকে এলে জানান" লিড), কিন্তু তালিকা-সাইটম্যাপের বাইরে আর noindex।
    # সদ্য শেষ (শেষবার স্টকে ছিল আগের দিনের মধ্যে) = এখনো তালিকায়: এক রাতের ভুলে কিছু লুকায় না।
    # টানা ৯০ দিন কোথাও স্টকে না থাকলে "বন্ধ": পাতার জায়গায় ক্যাটাগরিতে পাঠানো (অ্যাডমিনে "সবসময় রাখো" থাকলে নয়)।
    data_day = health.get("date") or today
    _ss = DATA / "stock_state.json"
    sstate = json.loads(_ss.read_text()) if _ss.exists() else {}
    merged_ids = defaultdict(set)
    for old_, keep_ in amap.items():
        merged_ids[keep_].add(old_)
    keep_listed = set(mm.get("keep_listed", []))
    # টেকনিক্যাল SEO সেটিং (অ্যাডমিন → SEO): টেমপ্লেট, ইনডেক্সের নিয়ম, AI স্নিপেট, IndexNow
    SEO = {"title_product": "{name} দাম বাংলাদেশে | {price}", "title_product_oos": "{name} দাম বাংলাদেশে", "desc_product": "",
           "title_category": "{cat} দাম বাংলাদেশে {year} | {cat_en} Price in BD", "desc_category": "", "gone_days": 90,
           "force_index": [], "force_noindex": [], "ai_snippet": "full", "indexnow": False, "indexnow_key": "",
           "index_min_stores": 2}
    _sf = ROOT / "config/seo.json"
    if _sf.exists():
        SEO.update({k: v for k, v in json.loads(_sf.read_text()).items() if not k.startswith("_")})
    _pid_of = lambda x: x.strip().rstrip("/").split("/p/")[-1].split("/")[-1] if x and x.strip() else ""
    force_index = {_pid_of(x) for x in SEO["force_index"]} - {""}
    force_noindex = {_pid_of(x) for x in SEO["force_noindex"]} - {""}
    keep_listed |= force_index
    GONE_DAYS, LISTED = max(14, int(SEO.get("gone_days") or 90)), {"in", "partial", "coming", "grace"}
    _dn = lambda d_: date.fromisoformat(d_).toordinal()
    for pid, it in items.items():
        last_live, last_price = None, None
        for x in {pid} | merged_ids[pid]:
            st_ = sstate.get(x)
            if st_ and st_[0] and (last_live is None or st_[0] > last_live):
                last_live, last_price = st_[0], st_[1]
        for ch_ in history.get(pid, {}).values():  # ইতিহাসে শেষবার স্টকে থাকার দিন (state ফাইল না থাকলেও)
            for d_, v_ in ch_:
                if v_ and (last_live is None or d_ > last_live):
                    last_live, last_price = d_, v_
        sts = {o.get("status") for o in offers[pid].values()}
        days = _dn(data_day) - _dn(last_live) if last_live else None
        if it["live_count"]:
            state = "in" if it["live_count"] > 1 else "partial"
        elif sts & {"upcoming", "pre"}:
            state = "coming"
        elif days is not None and days <= 1:
            state = "grace"
        elif days is not None and days >= GONE_DAYS and pid not in keep_listed:
            state = "gone"
        else:
            state = "out"
        it.update(state=state, listed=(state in LISTED or pid in keep_listed) and pid not in force_noindex, last_live=last_live,
                  last_price=last_price or it["any_price"], out_days=days, pre=bool(sts & {"pre"}))
    # Google-এ দেখানো (index + সাইটম্যাপ): তালিকায় আছে এবং কমপক্ষে index_min_stores দোকানে দাম আছে (আসল তুলনা)।
    # কম দোকানের পাতা সাইটে, ক্যাটাগরি তালিকায়, সার্চে থাকে কিন্তু noindex; দ্বিতীয় দোকানের দাম এলেই নিজে থেকে খুলে যায়।
    # Google-এর নির্দেশিকা: সাইটম্যাপে শুধু সেই পাতা যেগুলো সার্চে দেখাতে চান; প্রতিদিন বদলানো বড় সাইটে কম-মূল্যের পাতা বাদ।
    MIN_STORES = max(1, int(SEO.get("index_min_stores") or 2))
    for pid, it in items.items():
        it["indexed"] = it["listed"] and (it["store_count"] >= MIN_STORES or pid in force_index)
    from matcher.match import bad_id as _bad_id, full_slug as _full_slug
    _same_name = defaultdict(list)
    for pid_, it_ in items.items():
        if it_["state"] != "gone":
            _same_name[_full_slug(products[pid_]["name"])].append(pid_)
    _cn = defaultdict(list)
    for lf_ in leaves.values():
        for k_ in (lf_.get("name_bn"), lf_.get("name_en"), lf_.get("slug")):
            if k_:
                _cn[k_.strip().lower()].append(lf_["slug"])
    _dup_cats = sorted({tuple(sorted(set(v_))) for v_ in _cn.values() if len(set(v_)) > 1}) + \
        [(lf_["slug"],) for lf_ in leaves.values() if re.search(r"-\d+$", lf_["slug"])]
    _viol = sum(1 for i in items.values() if i["state"] != "gone" and _bad_id(i["id"], products[i["id"]]["name"])) + \
        sum(1 for v_ in _same_name.values() if len(v_) > 1) + len(_dup_cats)
    if _viol:
        print(f"⚠ সাইটের নিয়ম ভাঙা: {_viol}টি (সংখ্যাওয়ালা লিংক/ডুপ্লিকেট প্রোডাক্ট/ডুপ্লিকেট ক্যাটাগরি) — অ্যাডমিন → SEO দেখুন; ঠিক করতে: python tools/dedupe_ids.py")
    stock_counts = Counter(i["state"] for i in items.values())
    listed_items = {k_: v_ for k_, v_ in items.items() if v_["listed"]}

    for pid, it in items.items():  # ফোনে অফিসিয়াল/আনঅফিসিয়াল ফিল্টার
        if it["category"] in PHONE_CATS:
            types = {phone_type(o.get("name"), stores[s_]) for s_, o in offers[pid].items() if o.get("in_stock") and o.get("price")}
            if "official" in types:
                it["fx"]["pt"] = ["অফিসিয়াল পাওয়া যায়", 1]
            elif "unofficial" in types:
                it["fx"]["pt"] = ["শুধু আনঅফিসিয়াল", 2]

    for it in items.values():  # ব্র্যান্ডের প্রদর্শনী নাম (সব বানান গোনা হয়ে গেলে)
        it["brand"] = BR.display(it["bslug"]) if it["bslug"] else ""
    # ব্র্যান্ড নেই এমন ল্যাপটপের রিপ্লেসমেন্ট পার্টস (ব্যাটারি, কিবোর্ড, চার্জার, ডিসপ্লে): ব্র্যান্ড নয়, "কোন ল্যাপটপের জন্য"।
    # এগুলো Asus/HP-র বানানো নয়, তাই ব্র্যান্ড পাতায় যায় না; ফিল্টার আর স্কিমার isAccessoryOrSparePartFor-এ কাজে লাগে।
    for it in items.values():
        it["compat"] = None
        if it["bslug"] or not (it["category"] == "laptop-accessories" or re.search(r"\b(laptop|notebook|macbook)\b", it["name"], re.I)):
            continue
        low_ = it["name"].lower()
        hit = min(((m_.start(), disp) for key, disp in LAPTOP_MAKERS for m_ in [re.search(r"\b" + key + r"\b", low_)] if m_), default=None)
        if hit:
            it["compat"] = hit[1]
            it["fx"]["fit"] = [hit[1], LAPTOP_RANK.get(hit[1], 99)]
    # ব্র্যান্ডহীন সাধারণ পণ্য: নাম শুরু হয় সাধারণ শব্দ/মাপ দিয়ে (Paper Roll, 14 Inch Laptop Display, Universal …),
    # অথবা অ্যাডমিনে "ব্র্যান্ড নেই" চিহ্নিত (config/brands.json → none)। এগুলো সমস্যা নয়, SEO-তে আলাদা গোনা হয়।
    _none = set(BR.conf.get("none", []))
    for it in items.values():
        _w = (it["name"].split() or [""])[0].lower()
        it["unbranded"] = not it["bslug"] and not it["compat"] and (
            it["id"] in _none or _w in BR.generic or bool(re.fullmatch(r"[\d\W]+", _w)) or it["category"] == "laptop-accessories")
    # ব্র্যান্ড পাতা তৈরি হয় তালিকায় থাকা প্রোডাক্ট গুনে, তাই লিংকও একই হিসাবে (নইলে না-থাকা পাতায় লিংক = 404)
    common["brand_set"] = {b_ for b_, c_ in Counter(i["bslug"] for i in listed_items.values() if i["bslug"]).items()
                           if c_ >= BR.conf.get("min_products", 5)}
    common["brand_info"] = lambda b_: BR.info.get(b_) or {}
    _bc = Counter(i["bslug"] for i in items.values() if i["bslug"])
    common["brand_n"] = lambda b_: _bc.get(b_, 0)
    common["brand_logo"] = lambda b_: (lambda l: (l if l.startswith("http") else f"{BASE}/static/brands/{l}") if l else None)(BR.info.get(b_, {}).get("logo"))
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "static").mkdir(parents=True)
    for f in ("style.css", "home.js", "compare.js", "go.js", "admin.css", "admin.js", "gallery.js", "cat-icons.svg", "share.jpg", "filters.js", "search.js", "livesearch.js", "alert.js", "pcbuilder.js"):
        shutil.copy(ROOT / "web/static" / f, DIST / "static" / f)
    for d in ("logos", "sponsors", "brands", "icons"):
        if (ROOT / "web/static" / d).exists():
            shutil.copytree(ROOT / "web/static" / d, DIST / "static" / d)
    # ফেভিকন: ব্রাউজার আর সার্চ ইঞ্জিন সাইটের গোড়ায় /favicon.ico খোঁজে; ফোনে "হোম স্ক্রিনে যোগ" করার জন্য manifest
    shutil.copy(ROOT / "web/static/icons/favicon.ico", DIST / "favicon.ico")
    (DIST / "site.webmanifest").write_text(json.dumps({
        "name": "দামতুলনা", "short_name": "দামতুলনা", "lang": "bn", "start_url": f"{BASE}/", "scope": f"{BASE}/", "display": "standalone",
        "background_color": "#eef2f1", "theme_color": "#12302c",
        "icons": [{"src": f"{BASE}/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": f"{BASE}/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
                  {"src": f"{BASE}/static/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}]},
        ensure_ascii=False))
    urls = []
    # সাইটের নিয়ম: মিলে যাওয়া (ডুপ্লিকেট) প্রোডাক্টের পুরনো পাতা আর থাকে না — রিডাইরেক্ট পাতাও না (মালিকের সিদ্ধান্ত)

    def write(path, template, **ctx):
        out = DIST / path / "index.html" if path else DIST / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(env.get_template(template).render(**common, **ctx))
        if not ctx.get("noindex"):
            urls.append(f"{SITE_URL}/{path + '/' if path else ''}")

    by_cat, by_cat_all = defaultdict(list), defaultdict(list)
    for it in items.values():
        by_cat_all[it["category"]].append(it)
        if it["listed"]:
            by_cat[it["category"]].append(it)
    product_tpl = env.get_template("product.html")
    bcount_all = Counter(i["bslug"] for i in items.values() if i["bslug"])
    BSPEC = {}  # Walton/Minister-এর নিজস্ব স্পেক, url ধরে
    for bf in sorted((DATA / "brand_specs").glob("*.json")) if (DATA / "brand_specs").exists() else []:
        BSPEC.update(json.loads(bf.read_text()))

    # SEO: শেয়ার-ছবি (ফেসবুকে লিংকের সাথে ছবি) আর ব্রেডক্রাম্ব স্কিমা
    common["og_default"] = f"{SITE_URL or BASE}/static/share.jpg"
    _si = ROOT / "config/store_info.json"
    common["store_info"] = json.loads(_si.read_text()).get("stores", {}) if _si.exists() else {}
    # ভিজিটর ট্র্যাকিং আর গুগল/বিং ওয়েবমাস্টার যাচাই (অ্যাডমিন → সেটিং থেকে বসানো)
    _tf = ROOT / "config/tracking.json"
    _tr = json.loads(_tf.read_text()) if _tf.exists() else {}
    _ok = lambda k, pat: (_tr.get(k) or "").strip() if re.fullmatch(pat, (_tr.get(k) or "").strip()) else ""
    common["track"] = {"ga4": _ok("ga4", r"G-[A-Z0-9]{4,15}"), "gsc": _ok("gsc", r"[A-Za-z0-9_-]{20,80}"),
                       "bing": _ok("bing", r"[A-F0-9]{32}"), "clarity": _ok("clarity", r"[a-z0-9]{6,15}"),
                       "fb_pixel": _ok("fb_pixel", r"\d{10,20}")}
    # কোন পাতার লেখা Google/AI সার্চ কতটা উদ্ধৃত করতে পারবে (robots meta)
    common["robots_meta"] = {"full": "index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1",
                             "limited": "index, follow, max-snippet:160, max-image-preview:large",
                             "none": "index, follow, nosnippet"}.get(SEO.get("ai_snippet"), "index, follow, max-snippet:-1, max-image-preview:large")
    _now = date.fromisoformat(today)
    _MONTH = ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"]
    year_bn, month_bn = bn_num(_now.year).replace(",", ""), _MONTH[_now.month - 1]
    common["month_year"], common["day_bn"] = f"{month_bn} {year_bn}", bn_date(today)

    class _CaseFree(dict):  # শিরোনাম মেলানো বড়/ছোট হাতের অক্ষর ছাড়া (ASUS আর Asus একই ধরা)
        def __contains__(self, k):
            return dict.__contains__(self, k.lower())

        def __getitem__(self, k):
            return dict.__getitem__(self, k.lower())

        def __setitem__(self, k, v):
            dict.__setitem__(self, k.lower(), v)
    used_titles = _CaseFree()  # শিরোনাম → যে প্রোডাক্টের নাম থেকে এসেছে

    def tpl(t, **kv):
        """অ্যাডমিনের টেমপ্লেট ভরানো; অজানা {শব্দ} ফাঁকা হয়ে যায়, বাড়তি ফাঁকা জায়গা মুছে।"""
        class _D(dict):
            def __missing__(self, k):
                return ""
        try:
            out = str(t).format_map(_D(kv, year=year_bn, month=month_bn, date=bn_date(today)))
        except (ValueError, IndexError):
            return ""
        return re.sub(r"\s+", " ", out).replace(" |  ", " | ").strip(" |")
    _lf = ROOT / "config/leads.json"
    common["lead_cfg"] = {"endpoint": (json.loads(_lf.read_text()).get("endpoint") or "") if _lf.exists() else "",
                          "wa": (ads.get("contact") or {}).get("whatsapp") or (ads.get("contact") or {}).get("phone") or ""}

    def crumbs_ld(*pairs):
        """[(নাম, path)] থেকে BreadcrumbList JSON-LD (Google ফলাফলে পথ দেখায়)।"""
        return json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": f"{SITE_URL}{BASE if not SITE_URL else ''}/{p_}"}
            for i, (n, p_) in enumerate(pairs)]}, ensure_ascii=False)
    lastmod = {}  # url → তারিখ (সাইটম্যাপের জন্য)
    seo_titles = {}  # অ্যাডমিনের SEO স্বাস্থ্য: একই/লম্বা শিরোনাম খোঁজা
    drops = []    # আজ যেসব প্রোডাক্টের সর্বনিম্ন দাম কমেছে

    # পিসির হেডারে ক্যাটাগরি মেনু (যেসব গ্রুপে প্রোডাক্ট আছে)
    _live = {group_of[i["category"]]["slug"] for i in items.values()}
    common["nav_groups"] = [(g["slug"], g["name_bn"]) for g in tax["groups"] if g["slug"] in _live]

    _spec_cache = {}

    def specs_for(pid):
        """এক নজরের সারি (একবার হিসাব, তুলনার আগাম ধাপ আর পাতা দুই জায়গায় কাজে লাগে)"""
        if pid in _spec_cache:
            return _spec_cache[pid]
        p_, it_, so_ = products[pid], items[pid], offers[pid]
        det_ = details.get(pid, {})
        feats_ = det_.get("key_features") or p_.get("features") or []
        bsp_ = next((BSPEC[o["url"]] for o in so_.values() if o.get("url") in BSPEC), None)
        bdet_ = brand_details.get(pid) or {}
        if bdet_.get("specs"):
            bdet_ = dict(bdet_, specs=normalize_specs(bdet_["specs"]))
        all_ = dict(bdet_.get("specs") or {})
        for sec_, rows_ in (det_.get("specs") or {}).items():
            all_[sec_ + " (স্টোর)" if sec_ in all_ else sec_] = rows_
        fr, fx = key_specs(it_["category"], p_["name"], all_ or None, feats_, bsp_, FEAT_BN)
        _spec_cache[pid] = (fr, fx, feats_, bsp_, bdet_, all_)
        return _spec_cache[pid]

    # দামের বিশ্লেষণের আগাম ধাপ: ক্যাটাগরি ধরে আজকের দাম (অবস্থান), আর তুলনার সংখ্যা (একই দামের অন্যগুলো)
    import bisect
    cat_profile = spec_schema()[1]
    live_by_cat, brand_by_cat, peer_pool = {}, {}, {}
    for c, lst in by_cat.items():
        live = sorted((i["best"]["price"], i["id"]) for i in lst if i["best"] and not i["sus"])
        live_by_cat[c] = [x for x, _ in live]
        bb = defaultdict(list)
        for pr, i_ in live:
            if items[i_]["bslug"]:
                bb[items[i_]["bslug"]].append(i_)
        brand_by_cat[c] = bb
        prof = cat_profile.get(c)
        if prof in INS.COMPARE:
            pool = []
            for pr, i_ in live:
                nums_ = INS.spec_numbers(prof, specs_for(i_)[0], products[i_]["name"])
                if nums_:
                    pool.append((pr, i_, nums_))
            peer_pool[c] = pool

    # প্রোডাক্ট পাতা থেকে "এই দামের আরও …" বাজেট পাতার লিংক (build_budget_pages-এর একই নিয়মে আগাম হিসাব)
    _bconf = json.loads((ROOT / "config/budget_pages.json").read_text()).get("pages", {}) if (ROOT / "config/budget_pages.json").exists() else {}
    tier_ok = {}
    for c, amts in _bconf.items():
        prices = [i["best"]["price"] for i in by_cat_all.get(c, []) if i["best"] and not i["sus"]]
        tier_ok[c] = [a_ for a_ in sorted(amts) if sum(1 for x in prices if a_ * 0.4 <= x <= a_) >= 5]

    def tier_for(it):
        price = (it["best"] or {}).get("price")
        if not price:
            return None
        a_ = next((a_ for a_ in tier_ok.get(it["category"], []) if a_ >= price and price >= a_ * 0.4), None)
        return (a_, f"{it['category']}-under-{a_}") if a_ else None

    def insight_for(pid, it, so, leaf, changes):
        c = it["category"]
        prof = cat_profile.get(c)
        price = (it["best"] or {}).get("price")
        rank = peers = nums = None
        if price and not it["sus"]:
            arr = live_by_cat.get(c, [])
            cheaper = len(arr) - bisect.bisect_right(arr, price)  # এর চেয়ে বেশি দামের কয়টা
            bl = brand_by_cat.get(c, {}).get(it["bslug"]) or []
            brank = bl.index(pid) + 1 if pid in bl else 0
            rank = (cheaper, len(arr), brank, len(bl), it["brand"] if brank else None)
            if c in peer_pool:
                nums = INS.spec_numbers(prof, specs_for(pid)[0], products[pid]["name"])
                lo, hi = INS.peer_band(price)
                group = [n_ for pr, i_, n_ in peer_pool[c] if lo <= pr <= hi and i_ != pid]
                peers = (lo, hi, group)
        res = INS.build(pid, it, so, stores, leaf, changes, today, peers=peers, rank=rank, profile=prof, nums=nums,
                        hint=HINTS.get(leaf["slug"]))
        alts_better = INS.better_alternatives(pid, price, prof, nums, peer_pool.get(c), items) if (price and not it["sus"]) else []
        return res + (alts_better,)

    for pid, it in items.items():
        p, leaf, grp, so = products[pid], leaves[it["category"]], group_of[it["category"]], offers[pid]
        if it["state"] == "gone":  # টানা ৯০ দিন কোথাও নেই: পাতা সরানো হয় (রিডাইরেক্ট পাতা নয়)
            continue
        det = details.get(pid, {})
        rows = []
        covered = set(leaf.get("stores", {})) | set(so)  # যে স্টোর এই ক্যাটাগরি বিক্রিই করে না, তাকে "পাওয়া যায়নি"-তে দেখানো নয়
        for s in [x for x in enabled if x in covered]:
            o = so.get(s)
            label, cls = STATUS.get(o["status"], ("", "")) if o else ("", "")
            age = (date.fromisoformat(today) - date.fromisoformat(o["seen"])).days if o and o.get("seen") else None
            fresh = (None if age is None else "আজ যাচাই করা" if age == 0 else "গতকাল যাচাই করা" if age == 1
                     else f"{bn_num(age)} দিন আগে যাচাই করা")
            if o and o.get("manual"):  # হাতে দেখে বসানো দাম, সপ্তাহে একবার হালনাগাদ হয়
                fresh = "হাতে যাচাই করা · " + ("আজ" if age == 0 else "গতকাল" if age == 1 else f"{bn_num(age)} দিন আগে")
            if s in it["sus"]:
                label, cls = "দাম যাচাই চলছে", "chk"
            ptype = phone_type(o.get("name"), stores[s]) if o and it["category"] in PHONE_CATS else None
            rows.append({"store": s, "offer": o, "label": label, "cls": cls, "fresh": fresh, "old": bool(age and age >= (8 if o and o.get("manual") else 2)), "ptype": ptype,
                         "is_best": bool(it["best"] and o and it["best"]["store"] == s and it["saving"] > 0),
                         "featured": bool(o and o.get("in_stock") and stores[s].get("featured"))})
        # স্পন্সরড স্টোর (স্টকে থাকলে) উপরে, "স্পন্সরড" লেখাসহ; বাকিরা দাম অনুযায়ী
        rows.sort(key=lambda r: (not r["featured"], r["offer"] is None, not (r["offer"] and r["offer"]["in_stock"]), (r["offer"] or {}).get("price") or 10**9))
        same = [a for a in by_cat[it["category"]] if a["id"] != pid and a["best"]
                and all(a["specs"].get(k) == it["specs"].get(k) for k in ("capacity", "type", "form", "interface", "brand_cpu") if it["specs"].get(k))]
        ref = (it["best"] or {}).get("price") or it["any_price"]
        if ref and not any(it["specs"].get(k) for k in ("capacity", "type", "interface", "brand_cpu")):
            same = [a for a in same if 0.7 * ref <= a["best"]["price"] <= 1.3 * ref]
        alts = [{"id": a["id"], "name": a["name"], "price": a["best"]["price"], "store": a["best"]["store"], "imgs": a["imgs"], "category": a["category"]}
                for a in sorted(same, key=lambda a: abs(a["best"]["price"] - (ref or 0)))[:6]]
        changes = daily_min({s_: v for s_, v in history.get(pid, {}).items() if s_ not in it["sus"]}, today)
        best = it["best"]
        if best:  # আজ দাম কমেছে: একই স্টোর নিজের দাম কমিয়েছে (নতুন স্টোর যোগ হওয়াকে "কমা" ধরা হয় না)
            hs = sorted(history.get(pid, {}).get(best["store"], []))
            prev = [v_ for d_, v_ in hs if d_ < today and v_]
            if hs and hs[-1][0] == today and hs[-1][1] == best["price"] and prev and prev[-1] > best["price"]:
                drops.append(it | {"old": prev[-1], "drop": prev[-1] - best["price"]})
        real_changes = [d_ for d_, _ in changes[:-1]] if len(changes) > 1 else []
        lastmod[f"{SITE_URL}/p/{pid}/"] = max(real_changes + [p["created"]])
        warranty = warranty_bn(det.get("warranty"))
        # ব্র্যান্ডের নিজের সাইটের বিবরণ সবচেয়ে নির্ভরযোগ্য, তাই আগে (specs_for-এ)
        feat_rows, feat_extra, feats, bsp, bdet, all_specs = specs_for(pid)
        _spec_cache.pop(pid, None)
        ins_lines, ins_meta, ins_faq, better = insight_for(pid, it, so, leaf, changes)
        spec_src = bdet if bdet.get("specs") else det
        spec_sections = [(section_bn(sec), rows_) for sec, rows_ in (spec_src.get("specs") or {}).items()
                         if "warranty" not in sec.lower()]
        spec_credit = {"name": bdet["brand_site"], "url": bdet["source"]} if bdet.get("specs") else None
        faq = [
            (f"{p['name']} এর দাম কত?",
             f"আজকের হিসাবে সর্বনিম্ন দাম {taka(best['price'])}, {stores[best['store']]['name']}-এ।" if best
             else "এই মুহূর্তে আমাদের তালিকার কোনো স্টোরে এটা স্টকে নেই।"),
            ("এর ওয়ারেন্টি কত দিনের?",
             f"বিক্রেতার পাতায় লেখা আছে: {warranty}। কেনার সময় ওয়ারেন্টি কার্ড ও শর্ত মিলিয়ে নিন।" if warranty
             else "ওয়ারেন্টির তথ্য এখনো যোগ হয়নি। কেনার আগে স্টোরে জিজ্ঞেস করে নিন।"),
        ] + ins_faq + [
            ("এই দাম কখন আপডেট হয়?", "প্রতিদিন রাতে সব স্টোর থেকে দাম নতুন করে সংগ্রহ করা হয়। এই পাতার সব হিসাব সেই দাম থেকেই।"),
        ]
        if not ins_faq:
            faq.append(("কোন স্টোর থেকে কেনা ভালো?", "দামের পাশাপাশি ওয়ারেন্টি, ডেলিভারি আর বাসার কাছে শাখা আছে কিনা দেখে নিন।"))
        priced_s = sorted(((s_, o) for s_, o in so.items() if o.get("price") and o.get("in_stock") and s_ not in it["sus"]),
                          key=lambda x: x[1]["price"])
        priced = [o for _, o in priced_s]
        # সংক্ষিপ্ত উত্তর: Google AI Overview আর AI চ্যাটবট যেন এক বাক্যেই দাম, দোকান আর তারিখ পায় (পাতায় দেখা যায়)
        _low30 = window_min(changes, today, 30) if changes and (date.fromisoformat(today) - date.fromisoformat(changes[0][0])).days >= 14 else None
        if best and priced:
            answer = (f"আজ {bn_date(today)} তারিখে বাংলাদেশে {p['name']}-এর সর্বনিম্ন দাম {taka(priced[0]['price'])}, "
                      f"{stores[priced_s[0][0]]['name']}-এ।")
            if len(priced) > 1:
                answer += (f" {bn_num(len(priced))}টি দোকানে স্টকে আছে, দাম {taka(priced[0]['price'])} থেকে {taka(priced[-1]['price'])}"
                           + (": " + ", ".join(f"{stores[s_]['name']} {taka(o['price'])}" for s_, o in priced_s[:5]) if len(priced) <= 5 else "") + "।")
            if _low30 and _low30 < priced[0]["price"]:
                answer += f" গত ৩০ দিনে সর্বনিম্ন ছিল {taka(_low30)}।"
            elif _low30 and _low30 >= priced[0]["price"]:
                answer += " এটা গত ৩০ দিনের মধ্যে সবচেয়ে কম দাম।"
        elif it["state"] == "coming":
            answer = f"{p['name']} এখনো বাংলাদেশের দোকানে বিক্রি শুরু হয়নি ({'প্রি-অর্ডার চলছে' if it['pre'] else 'শীঘ্রই আসছে'})" + (f"; শেষ জানা দাম {taka(it['last_price'])}।" if it["last_price"] else "।")
        else:
            answer = (f"আজ {bn_date(today)} পর্যন্ত {p['name']} আমাদের তালিকার কোনো দোকানে স্টকে নেই"
                      + (f"; শেষবার {bn_date(it['last_live'])} তারিখে {taka(it['last_price'])} দামে পাওয়া গিয়েছিল।" if it["last_live"] and it["last_price"] else "।"))
        if warranty:
            answer += f" ওয়ারেন্টি: {warranty}।"
        page_url = f"{SITE_URL}/p/{pid}/" if SITE_URL else f"{BASE}/p/{pid}/"
        jsonld = {"@context": "https://schema.org", "@type": "Product", "name": p["name"], "url": page_url, "sku": pid,
                  "description": answer, "category": leaf["name_en"]}
        if it["brand"]:
            jsonld["brand"] = {"@type": "Brand", "name": it["brand"]}
        elif it["compat"]:
            jsonld["isAccessoryOrSparePartFor"] = {"@type": "Product", "name": f"{it['compat']} Laptop", "brand": {"@type": "Brand", "name": it["compat"]}}
        if det.get("mpn"):
            jsonld["mpn"] = det["mpn"]
        if det.get("model"):
            jsonld["model"] = det["model"]
        if it["imgs"]:
            jsonld["image"] = [u for u, _ in it["imgs"][:3]]
        if priced:
            jsonld["offers"] = {"@type": "AggregateOffer", "priceCurrency": "BDT", "offerCount": len(priced),
                                "lowPrice": min(o["price"] for o in priced), "highPrice": max(o["price"] for o in priced),
                                "availability": "https://schema.org/InStock",
                                "offers": [{"@type": "Offer", "price": o["price"], "priceCurrency": "BDT", "itemCondition": "https://schema.org/NewCondition",
                                            "availability": "https://schema.org/InStock", "url": o.get("url") or stores[s_]["home"],
                                            "seller": {"@type": "Organization", "name": stores[s_]["name"]}} for s_, o in priced_s]}
        elif it["state"] == "coming":
            jsonld["offers"] = {"@type": "Offer", "priceCurrency": "BDT", "availability": "https://schema.org/PreOrder" if it["pre"] else "https://schema.org/PreSale",
                                **({"price": it["last_price"]} if it["last_price"] else {})}
        # Google: Product-এ দাম (offers.price/lowPrice) না থাকলে ভুল দেখায় — তখন Product schema বাদ, শুধু Breadcrumb
        _of = jsonld.get("offers") or {}
        if not (_of.get("price") or _of.get("lowPrice")):
            jsonld = None
        cmp = {"id": pid, "n": p["name"], "b": it["brand"], "c": leaf["slug"], "cn": leaf["name_bn"],
               "w": warranty, "m": det.get("model"), "mpn": det.get("mpn"), "kf": feats[:6],
               "best": best, "o": {s_: {"p": o["price"], "st": o["in_stock"], "u": o["url"]} for s_, o in so.items() if o.get("price")},
               "sp": det.get("specs") or {"মূল তথ্য": dict(feat_rows) or {SPEC_NAMES.get(k, k): v for k, v in p["specs"].items()}},
               # তুলনা পাতা: এক নজরের সারি + তুলনার সংখ্যা (বেশি মান সবুজ)
               "fr": feat_rows[:14], "kn": INS.spec_numbers(cat_profile.get(it["category"]), feat_rows, p["name"])}
        (DIST / "d").mkdir(exist_ok=True)
        (DIST / f"d/{pid}.json").write_text(json.dumps(cmp, ensure_ascii=False, separators=(",", ":")))
        _pv = {"name": short_name(p["name"]), "price": taka(best["price"]) if best else "", "store": stores[best["store"]]["name"] if best else "",
               "stores": bn_num(len(priced)), "brand": it["brand"] or "", "cat": leaf["name_bn"], "cat_en": leaf["name_en"]}
        _tt = SEO["title_product"] if best else SEO["title_product_oos"]
        _budget = max(40, TITLE_MAX - len(tpl(_tt, **{**_pv, "name": ""})) - 1)
        _pv["name"] = fit_name(_pv["name"], _budget)
        _title = tpl(_tt, **_pv) or f"{_pv['name']} দাম বাংলাদেশে" + (f" | {taka(best['price'])}" if best else "")
        if _title in used_titles:
            # ছোট করায় অন্য ভ্যারিয়েন্টের সাথে মিলে গেলে নামের শেষের আলাদা অংশ (রং, মডেল) রেখে মাঝখান বাদ;
            # তাতেও না হলে পুরো নাম, তাতেও মিললে ধরন নম্বর
            _w = short_name(p["name"]).split()
            _other = {w_.lower().strip(",()") for w_ in used_titles[_title].split()}
            diff_ = [w_.strip(",()+") for w_ in _w[len(_pv["name"].split()):] if w_.lower().strip(",()") not in _other]
            diff_ = [w_ for w_ in diff_ if w_ and not w_.startswith("#")] or [w_.lstrip("#") for w_ in _w if w_.startswith("#")]
            tail_ = fit_name(" ".join(diff_[:4]), 24)
            cand_ = tail_ and tpl(_tt, **{**_pv, "name": fit_name(_pv["name"], _budget - len(tail_) - 3) + " … " + tail_})
            _title = cand_ if cand_ and cand_ not in used_titles else (tpl(_tt, **{**_pv, "name": fit_name(_pv["name"], _budget - 9) + " (ধরন ২)"}) or _title)
            n_ = 3
            while _title in used_titles:
                _title = (re.sub(r"\(ধরন [০-৯]+\)", f"(ধরন {bn_num(n_)})", _title) if "(ধরন " in _title
                          else _title + f" (ধরন {bn_num(n_ - 1)})")
                n_ += 1
        used_titles[_title] = short_name(p["name"])
        _desc = ((tpl(SEO["desc_product"], **_pv) if SEO.get("desc_product") else "") or
                 ((f"{p['name']}: " + ", ".join(ins_meta) + "।" if ins_meta else
                   f"{p['name']} এর দাম বিভিন্ন স্টোরে মিলিয়ে দেখুন।" + (f" আজকের সর্বনিম্ন দাম {taka(best['price'])}।" if best else ""))
                  + (f" {warranty}।" if warranty else "")))
        if it["listed"]:
            seo_titles[pid] = _title
        out = DIST / f"p/{pid}/index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(product_tpl.render(
            **common, p=p, it=it, cat=leaf, group=grp, det=det, warranty=warranty, spec_sections=spec_sections, spec_credit=spec_credit, feat_rows=feat_rows, feat_extra=feat_extra,
            best=best, saving=it["saving"], worst=it.get("worst"), live_count=it["live_count"], store_rows=rows, alts=alts,
            binfo=BR.info.get(it["bslug"], {}) if it["bslug"] else {}, bcount=bcount_all.get(it["bslug"], 0),
            gallery=[{"u": u, "big": big_image(u), "s": sid, "n": stores[sid]["name"], "h": (so.get(sid) or {}).get("url") or stores[sid]["home"]}
                     for u, sid in it["imgs"]],
            spark=sparkline(changes, today), hist_start=bn_date(changes[0][0]) if changes else None,
            sparks=[(lab, sparkline(changes, today, d_)) for lab, d_ in (("৩০ দিন", 30), ("৯০ দিন", 90), ("১ বছর", 365))]
                   if changes and (date.fromisoformat(today) - date.fromisoformat(changes[0][0])).days > 30 else [],
            low30=window_min(changes, today, 30) if changes and (date.fromisoformat(today) - date.fromisoformat(changes[0][0])).days >= 14 else None,
            hist_days=(date.fromisoformat(today) - date.fromisoformat(changes[0][0])).days + 1 if changes else 0,
            hist_lo=min((v for _, v in changes), default=None), hist_hi=max((v for _, v in changes), default=None), icon=icon_for(it["category"], grp["slug"]), blurb=blurb(p, leaf, det), faq=faq,
            insights=ins_lines, ins_date=bn_date(today),
            pstat=INS.price_status(changes, today) if best else None,
            better=better,
            tier=tier_for(it),
            jsonld=json.dumps(jsonld, ensure_ascii=False) if jsonld else None, buy=bool(best),
            og_image=big_image(it["imgs"][0][0]) if it["imgs"] and it["imgs"][0][0].startswith("http") else None, og_type="product",
            crumbs=crumbs_ld(("হোম", ""), (grp["name_bn"], f"g/{grp['slug']}/"), (leaf["name_bn"], f"c/{leaf['slug']}/"), (p["name"], f"p/{pid}/")),
            answer=answer,
            title=_title, description=_desc,
            canonical=f"{SITE_URL}/p/{pid}/" if SITE_URL else None, noindex=not it["indexed"]))
        if it["indexed"]:  # সাইটম্যাপে শুধু কেনা যায় আর একাধিক দোকানে দাম আছে এমন প্রোডাক্ট
            urls.append(f"{SITE_URL}/p/{pid}/")

    _gf = ROOT / "config/buying_guides.json"
    guides = json.loads(_gf.read_text()).get("guides", {}) if _gf.exists() else {}
    need_hub = build_need_pages(items, leaves, group_of, write, today, crumbs_ld, SITE_URL, peer_pool, cat_profile, guides)
    _gf = ROOT / "config/buying_guides.json"
    guides = json.loads(_gf.read_text()).get("guides", {}) if _gf.exists() else {}
    budget_hub, budget_links = build_budget_pages(items, leaves, group_of, write, today, crumbs_ld, SITE_URL, need_hub,
                                                  peer_pool=peer_pool, cat_profile=cat_profile, guides=guides, stores=stores)
    store_cards = build_store_pages(items, offers, stores, enabled, leaves, write, crumbs_ld, SITE_URL)
    # পিসি বিল্ডার (যেসব ক্যাটাগরিতে প্রোডাক্ট আছে শুধু সেগুলো)
    pc_slots = [{"key": k, "name": n, "cats": [c for c in cs if by_cat.get(c)], "req": rq} for k, n, cs, rq in (
        ("cpu", "প্রসেসর", ["processor"], True), ("mb", "মাদারবোর্ড", ["motherboard"], True), ("ram", "র‍্যাম", ["desktop-ram"], True),
        ("ssd", "স্টোরেজ (SSD)", ["ssd"], True), ("gpu", "গ্রাফিক্স কার্ড", ["graphics-card"], False), ("psu", "পাওয়ার সাপ্লাই", ["power-supply"], True),
        ("case", "কেসিং", ["casing"], True), ("cooler", "সিপিইউ কুলার", ["cpu-cooler", "liquid-cooler"], False),
        ("monitor", "মনিটর", ["monitor-all", "gaming-monitor"], False))]
    pc_slots = [x for x in pc_slots if x["cats"]]
    write("pc-builder", "pcbuilder.html", slots=pc_slots, title="পিসি বিল্ডার: সব দোকানের দাম মিলিয়ে পিসি বানান | দামতুলনা",
          description="প্রসেসর, মাদারবোর্ড, র‍্যাম, গ্রাফিক্স কার্ড বাছুন; Star Tech, PC House-সহ সব দোকানের দাম মিলিয়ে মোট খরচ, আর সকেট/র‍্যাম/পাওয়ার মানানসই কিনা দেখুন।",
          crumbs=crumbs_ld(("হোম", ""), ("পিসি বিল্ডার", "pc-builder/")), canonical=f"{SITE_URL}/pc-builder/" if SITE_URL else None)
    pc_builds = build_pc_pages(items, write, today, crumbs_ld, SITE_URL, stores)
    common["budget_links"] = budget_links

    # ক্যাটাগরি পেজ (পাতায় ভাগ করা)
    group_cards = []
    for g in tax["groups"]:
        leaf_cards = []
        for leaf in g["leaves"]:
            lst_all = sorted(by_cat_all.get(leaf["slug"], []), key=lambda i: (not i["listed"],) + popular_first(i))
            lst = [i for i in lst_all if i["listed"]]
            hidden_n = len(lst_all) - len(lst)
            if not lst_all:
                continue
            brands = [b for b, _ in Counter(i["brand"] for i in lst if i["brand"]).most_common(12)]
            # ফিল্টারের জন্য পুরো ক্যাটাগরির ছোট ডাটা ফাইল (ফিল্টার/সাজানো চাপলে তবেই নামে)
            fdefs = category_filters(lst)
            fdata = {"stores": {s_: stores[s_]["name"] for s_ in enabled},
                     "items": [{"i": i["id"], "n": i["name"], "b": i["brand"], "p": (i["best"] or {}).get("price"), "a": i["any_price"],
                                "s": (i["best"] or {}).get("store"), "k": i["store_count"], "l": i["live_count"], "v": i["saving"],
                                "im": [u for u, _ in i["imgs"][:3]], **({"f": {k: v[0] for k, v in i["fx"].items()}} if i["fx"] else {}),
                                **({} if i["listed"] else {"h": 1, "lp": i["last_price"]}), **({"cs": 1} if i["state"] == "coming" else {})}
                               for i in lst_all if i["state"] != "gone"]}
            (DIST / f"c/{leaf['slug']}").mkdir(parents=True, exist_ok=True)
            (DIST / f"c/{leaf['slug']}/items.json").write_text(json.dumps(fdata, ensure_ascii=False, separators=(",", ":")))
            presets = price_presets([i["best"]["price"] for i in lst if i["best"]])
            bcount = Counter(i["brand"] for i in lst if i["brand"])
            pages = max(1, -(-len(lst) // PER_PAGE))
            # AI-বান্ধব সারাংশ আর দামের তালিকা (প্রথম পাতায়): সংখ্যা, দামের পরিসীমা, জনপ্রিয় ব্র্যান্ড, তারিখ
            _pr = sorted(i["best"]["price"] for i in lst if i["best"] and not i["sus"])
            _cv = {"cat": leaf["name_bn"], "cat_en": leaf["name_en"], "count": bn_num(len(lst)), "stores": bn_num(len(enabled)),
                   "low": taka(_pr[0]) if _pr else "", "high": taka(_pr[-1]) if _pr else ""}
            cat_answer = ""
            if _pr:
                cat_answer = (f"আজ {bn_date(today)} তারিখে বাংলাদেশে {bn_num(len(lst))}টি {leaf['name_bn']} কেনা যাচ্ছে; দাম {taka(_pr[0])} থেকে {taka(_pr[-1])}"
                              + (f", মাঝামাঝি দাম প্রায় {taka(_pr[len(_pr) // 2])}" if len(_pr) >= 5 else "") + "।")
                if brands[:3]:
                    cat_answer += f" সবচেয়ে বেশি মডেল আছে {', '.join(brands[:3])}-এর।"
                _mc = sum(1 for i in lst if i["live_count"] > 1)
                if _mc:
                    cat_answer += f" {bn_num(_mc)}টির দাম একাধিক দোকানে মিলিয়ে দেখা যায়।"
            price_table = [i for i in sorted(lst, key=lambda i: (-i["live_count"], (i["best"] or {}).get("price") or 0)) if i["best"] and not i["sus"]][:15]
            for n in range(1, pages + 1):
                chunk = lst[(n - 1) * PER_PAGE:n * PER_PAGE]
                _il = json.dumps({"@context": "https://schema.org", "@type": "ItemList", "name": f"বাংলাদেশে {leaf['name_bn']} দাম",
                                  "numberOfItems": len(lst), "itemListElement": [
                                      {"@type": "ListItem", "position": (n - 1) * PER_PAGE + k + 1, "name": i["name"],
                                       "url": f"{SITE_URL or BASE}/p/{i['id']}/"} for k, i in enumerate(chunk[:30])]}, ensure_ascii=False)
                write(f"c/{leaf['slug']}" + (f"/{n}" if n > 1 else ""), "category.html", cat=leaf, group=g, items=chunk,
                      lds=[_il] if chunk else [], noindex=not lst,  # খালি ক্যাটাগরি: Google-এ নয়, খালি ItemList নয়
                      cat_answer=cat_answer if n == 1 else "", price_table=price_table if n == 1 else [],
                      crumbs=crumbs_ld(("হোম", ""), (g["name_bn"], f"g/{g['slug']}/"), (leaf["name_bn"], f"c/{leaf['slug']}/")),
                      total=len(lst), hidden_n=hidden_n, page=n, pages=pages, brands=brands, store_count=len(enabled),
                      fdefs=fdefs, presets=presets, all_brands=[[b_, c_] for b_, c_ in sorted(bcount.items(), key=lambda x: (-x[1], x[0]))],
                      title=(tpl(SEO["title_category"], **_cv) or f"{leaf['name_bn']} দাম বাংলাদেশে | {leaf['name_en']} Price in BD") + (f" (পাতা {bn_num(n)})" if n > 1 else ""),
                      description=((tpl(SEO["desc_category"], **_cv) if SEO.get("desc_category") and _pr else "") or cat_answer
                                  or f"{len(lst)}টি {leaf['name_bn']} এর দাম বিভিন্ন স্টোরে মিলিয়ে দেখুন।")
                                 + (f" পাতা {bn_num(n)}/{bn_num(pages)}।" if n > 1 else ""),
                      canonical=f"{SITE_URL}/c/{leaf['slug']}/" + (f"{n}/" if n > 1 else "") if SITE_URL else None)
            priced = [i["best"]["price"] for i in lst if i["best"]]
            leaf_cards.append({"slug": leaf["slug"], "name_bn": leaf["name_bn"], "count": len(lst),
                               "min": min(priced) if priced else None,
                               "multi": sum(1 for i in lst if i["store_count"] > 1)})
        if not leaf_cards:
            continue
        gitems = [i for l in leaf_cards for i in by_cat[l["slug"]]]
        deals = sorted([i for i in gitems if i["saving"] > 0], key=lambda i: (-i["live_count"], -i["saving"]))[:8]
        write(f"g/{g['slug']}", "group.html", group=g, leaves=leaf_cards, deals=deals, total=len(gitems),
              crumbs=crumbs_ld(("হোম", ""), (g["name_bn"], f"g/{g['slug']}/")),
              title=f"{g['name_bn']} দাম বাংলাদেশে | দামতুলনা",
              description=f"{g['name_bn']}: {len(leaf_cards)}টি ক্যাটাগরিতে {len(gitems)}টি প্রোডাক্টের দাম তুলনা।",
              canonical=f"{SITE_URL}/g/{g['slug']}/" if SITE_URL else None)
        group_cards.append({"slug": g["slug"], "name_bn": g["name_bn"], "count": len(gitems), "leaves": len(leaf_cards),
                            "top": [l["name_bn"] for l in sorted(leaf_cards, key=lambda l: -l["count"])[:3]]})

    vals = list(items.values())
    size_pages = build_size_pages(listed_items, products, details, write, offers, crumbs_ld=crumbs_ld)
    brand_pages = build_brand_pages(listed_items, leaves, group_of, BR, write, crumbs_ld=crumbs_ld)
    deals = sorted([i for i in vals if i["saving"] > 0], key=lambda i: (-i["live_count"], -i["saving"]))[:10]
    fresh_all = sorted([i for i in vals if i["created"] == today], key=lambda i: i["name"])
    fresh = fresh_all[:10] if len(fresh_all) < len(vals) * 0.5 else []
    # আজ দাম কমেছে: বেশি টাকা কমা আগে, শতাংশে অন্তত ১%; একাধিক স্টোরে থাকা জিনিস অগ্রাধিকার পায়
    drops_top = sorted([d_ for d_ in drops if d_["drop"] >= d_["old"] * 0.01],
                       key=lambda d_: (-d_["store_count"], -d_["drop"]))[:10]
    # ===== হোম: বাজারের অবস্থা (web/market.py) =====
    M = market.compute(history, items, offers, set(enabled), today)
    _st = health.get("scraped_at") or ""
    _hh, _mm = (int(_st[11:13]), _st[14:16]) if len(_st) >= 16 else (0, "00")
    _part = "রাত" if _hh < 4 else "ভোর" if _hh < 6 else "সকাল" if _hh < 12 else "দুপুর" if _hh < 15 else "বিকাল" if _hh < 18 else "সন্ধ্যা" if _hh < 20 else "রাত"
    upd_time = f"{_part} {bn_num((_hh - 1) % 12 + 1)}:{_mm.translate(BN_DIGITS)}"
    n_prices = sum((health["stores"].get(s_) or {}).get("items", 0) for s_ in enabled)
    tab_of = lambda it_: market.TAB_OF_GROUP.get(it_["group"], "other")
    mv = None
    if M.get("ready"):
        mv = {k: {t: ([m for m in M["movers"][k] if t == "all" or m["tab"] == t][:10]) for t, _ in market.TABS} for k in ("dn", "up")}
    # সূচকের গ্রাফ (৩ দিনের বেশি ডাটা হলে)
    idx_svg = None
    if M.get("ready") and len(M["series"]) >= 3:
        ivals = [v for _, v in M["series"]]
        w_, h_, pl, pr, pt, pb = 320, 130, 34, 10, 10, 22
        lo, hi = min(ivals) - .4, max(ivals) + .3
        X = lambda k: pl + k * (w_ - pl - pr) / (len(ivals) - 1)
        Y = lambda v: pt + (h_ - pt - pb) * (1 - (v - lo) / ((hi - lo) or 1))
        pts = " ".join(f"{X(k):.1f},{Y(v):.1f}" for k, v in enumerate(ivals))
        step = max(0.5, round((hi - lo) / 3 * 2) / 2)
        g0 = math.ceil(lo / step) * step
        grid = "".join(f'<line x1="{pl}" x2="{w_-pr}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" stroke="var(--line)"/>'
                       f'<text x="{pl-6}" y="{Y(g)+3:.1f}" text-anchor="end">{f"{g:g}".translate(BN_DIGITS)}</text>'
                       for g in [g0 + i * step for i in range(6)] if g <= hi)
        xl = "".join(f'<text x="{X(k):.1f}" y="{h_-6}" text-anchor="middle">{bn_num(int(d[8:]))}</text>' for k, (d, _) in enumerate(M["series"]))
        col = "var(--best)" if ivals[-1] <= ivals[0] else "var(--warn)"
        idx_svg = Markup(f'<svg class="ixc" viewBox="0 0 {w_} {h_}" role="img" aria-label="বাজার সূচক, শেষ {bn_num(len(ivals))} দিন">{grid}{xl}'
                         f'<polygon points="{X(0):.1f},{h_-pb} {pts} {X(len(ivals)-1):.1f},{h_-pb}" fill="{col}" opacity=".1"/>'
                         f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.2" stroke-linejoin="round"/>'
                         f'<circle cx="{X(len(ivals)-1):.1f}" cy="{Y(ivals[-1]):.1f}" r="4" fill="{col}"/></svg>')
    # হিটম্যাপ: প্রোডাক্ট বেশি এমন ১৫টা ক্যাটাগরি; রং = গত ৭ দিনের বদল
    def hcol(p):
        if p is None or abs(p) < .15:
            return "background:var(--bg)"
        a = min(abs(p) / 3.5, 1)
        return (f"background:color-mix(in srgb,{'var(--best)' if p < 0 else 'var(--warn)'} {int(14 + a * 58)}%,var(--surface));"
                + ("color:#fff" if a > .55 else ""))
    heat = [{"slug": c_, "name": leaves[c_]["name_bn"], "count": len(by_cat[c_]), "pct": (M.get("cat_week") or {}).get(c_),
             "style": f"flex:{len(by_cat[c_])} 1 {max(90, min(260, len(by_cat[c_]) // 4))}px;" + hcol((M.get("cat_week") or {}).get(c_))}
            for c_ in sorted(by_cat, key=lambda c_: -len(by_cat[c_]))[:15]]
    # দোকানের খবর
    sn_rows = []
    for c_ in sorted(store_cards, key=lambda c_: -c_["st"]["live"]):
        n_ = (M.get("store_news") or {}).get(c_["id"], Counter())
        sn_rows.append({"id": c_["id"], "name": c_["name"], "logo": c_["logo"] if c_["id"] != "walton" else None, "dark": c_["dark"],
                        "short": stores[c_["id"]].get("short") or c_["name"][:2], "checked": (health["stores"].get(c_["id"]) or {}).get("items", 0),
                        "dn": n_["dn"], "up": n_["up"], "oos": n_["oos"], "new": n_["new"], "share": c_["st"]["share"]})
    # নতুন প্রোডাক্ট: যে দোকান আজই প্রথম যোগ হয়েছে তার সব প্রোডাক্ট "নতুন" নয়
    store_first = {}
    for ss_ in history.values():
        for s_, ch_ in ss_.items():
            if ch_:
                d0_ = min(d_ for d_, _ in ch_)
                store_first[s_] = min(store_first.get(s_, d0_), d0_)
    # চলমান লাইন: ক্যাটাগরির আজকের বদল + সবচেয়ে বেশি কমা/বাড়া প্রোডাক্ট
    ticker = []
    if M.get("ready"):
        cts = sorted(((v, k) for k, v in M["cat_today"].items() if abs(v) >= 0.1), key=lambda x: x[0])
        for v, k in cts[:8] + cts[-6:][::-1] if len(cts) > 14 else cts:
            ticker.append({"href": f"c/{k}/", "label": leaves[k]["name_bn"], "pct": abs(v), "up": v > 0, "cat": True})
        for m in M["movers"]["dn"][:8]:
            ticker.append({"href": f"p/{m['it']['id']}/", "label": m["it"]["name"], "price": m["new"], "pct": m["pct"], "up": False})
        for m in M["movers"]["up"][:4]:
            ticker.append({"href": f"p/{m['it']['id']}/", "label": m["it"]["name"], "price": m["new"], "pct": m["pct"], "up": True})
    if not ticker:  # দামের বদল জমার আগে: আজকের যাচাই, দোকানভেদে বড় পার্থক্য আর নতুন প্রোডাক্ট
        ticker.append({"href": "store/", "label": f"আজ {bn_num(len(enabled))}টি দোকানের {bn_num(n_prices)}টি দাম যাচাই", "info": True})
        _nw = [i for i in fresh_all if i["best"] and store_first.get(i["best"]["store"], today) < today]
        _nw.sort(key=lambda i: (not i["imgs"], -i["live_count"], -i["best"]["price"]))
        _dl = [i for i in deals if i["best"]][:8]
        for k_ in range(max(len(_dl), 6)):
            if k_ < len(_dl):
                i = _dl[k_]
                ticker.append({"href": f"p/{i['id']}/", "label": i["name"], "price": i["best"]["price"],
                               "note": f"{stores[i['best']['store']]['name']}-এ {taka(i['saving'])} কম", "deal": True})
            if k_ < len(_nw) and k_ < 6:
                i = _nw[k_]
                ticker.append({"href": f"p/{i['id']}/", "label": i["name"], "price": i["best"]["price"], "note": "নতুন", "new": True})
    # সংখ্যায় দামতুলনা
    gl = sorted(((g["slug"], g["name_bn"], sum(len(by_cat[l["slug"]]) for l in g["leaves"])) for g in tax["groups"]), key=lambda x: -x[2])
    gl = [x for x in gl if x[2]]
    leaves_n = [(g["name_bn"], sum(1 for l in g["leaves"] if by_cat.get(l["slug"]))) for g in tax["groups"]]
    leaves_n = sorted([x for x in leaves_n if x[1]], key=lambda x: -x[1])
    st_live = sorted(((c_["name"], c_["st"]["live"]) for c_ in store_cards), key=lambda x: -x[1])
    nstat = {"segs": gl, "seg_total": sum(x[2] for x in gl), "leaves": leaves_n, "leaf_total": sum(x[1] for x in leaves_n),
             "brands": [(b_["name"], b_["count"]) for b_ in brand_pages[:5]], "brand_total": len(brand_pages), "stores": st_live[:6]}
    new_list = [i for i in fresh_all if i["best"] and store_first.get(i["best"]["store"], today) < today]
    new_list = sorted(new_list, key=lambda i: (not i["imgs"], -i["live_count"], -i["best"]["price"]))[:10]
    logo_brands = sorted(brand_pages[:40], key=lambda b_: (not common["brand_logo"](b_["slug"]), -b_["count"]))[:12]
    summ = market.summary_text(M, leaves, len(enabled), n_prices).translate(BN_DIGITS)
    home_ctx = dict(M=M, mv=mv, tabs=market.TABS, idx_svg=idx_svg, heat=heat, sn_rows=sn_rows, ticker=ticker, nstat=nstat,
                    new_list=new_list, logo_brands=logo_brands, summ=summ, upd_time=upd_time, n_prices=n_prices,
                    scraped_at=_st, today_bn=bn_date(today), new_count=len([i for i in fresh_all if store_first.get((i["best"] or {}).get("store"), today) < today]))
    _sv = sorted(i["saving"] for i in listed_items.values() if i["saving"] > 0 and not i["sus"])
    save_stat = {"n": len(_sv), "med": _sv[len(_sv) // 2] if _sv else 0, "k1": sum(1 for x in _sv if x >= 1000)}
    _pop = json.loads((ROOT / "config/budget_pages.json").read_text()).get("popular", []) if (ROOT / "config/budget_pages.json").exists() else []
    budget_popular = [(c_, a_, f"{c_}-under-{a_}", leaves[c_]) for c_, a_ in _pop if (a_, f"{c_}-under-{a_}") in budget_links.get(c_, [])][:8]
    write("", "home.html", save_stat=save_stat, budget_popular=budget_popular, pc_builds=pc_builds, groups=group_cards, **home_ctx, size_pages=size_pages, top_brands=brand_pages[:12], brand_total=len(brand_pages), deals=deals, drops=drops_top, total=len(listed_items), budget_hub=budget_hub,
          popular=[] if drops_top else sorted([i for i in vals if i["best"] and i["live_count"] > 2 and not i["sus"]],
                                             key=lambda i: (-i["live_count"], -i["best"]["price"]))[:10],
          multi=sum(1 for i in vals if i["live_count"] > 1),
          store_names=", ".join(stores[s]["name"] for s in enabled), store_count=len(enabled),
          lds=[json.dumps({"@context": "https://schema.org", "@graph": [
              {"@type": "WebSite", "@id": f"{SITE_URL or BASE}/#website", "url": f"{SITE_URL or BASE}/", "name": "দামতুলনা",
               "alternateName": ["Daam Tulona", "DaamTulona"], "inLanguage": "bn-BD", "publisher": {"@id": f"{SITE_URL or BASE}/#org"}},
              {"@type": "Organization", "@id": f"{SITE_URL or BASE}/#org", "name": "দামতুলনা", "alternateName": "Daam Tulona",
               "url": f"{SITE_URL or BASE}/", "logo": common["og_default"], "areaServed": "BD",
               "description": f"বাংলাদেশের কম্পিউটার, মোবাইল ও ইলেকট্রনিক্সের দাম তুলনার ওয়েবসাইট। প্রতিদিন {len(enabled)}টি দোকানের দাম সংগ্রহ করে এক পাতায় দেখায়।"}]},
              ensure_ascii=False)],
          title="দামতুলনা | কম্পিউটার, মোবাইল ও ইলেকট্রনিক্সের দাম তুলনা বাংলাদেশে",
          description=f"{len(listed_items)}টি প্রোডাক্টের আজকের দাম {len(enabled)}টি স্টোরে মিলিয়ে দেখুন: " + ", ".join(stores[s]["name"] for s in enabled) + "।",
          canonical=f"{SITE_URL}/" if SITE_URL else None)
    write("compare", "compare.html", title="তুলনা করুন | দামতুলনা", description="প্রোডাক্ট পাশাপাশি তুলনা", noindex=True,
          section_bn=SECTION_BN)
    write("search", "search.html", title="খুঁজুন | দামতুলনা", description="প্রোডাক্ট খুঁজুন", noindex=True)
    for slug, title, desc in (("about", "আমাদের সম্পর্কে", "দামতুলনা কী, দাম কোথা থেকে আসে, কীভাবে আয় হয়।"),
                              ("advertise", "বিজ্ঞাপন দিন", "দামতুলনায় ব্র্যান্ড বা স্টোরের বিজ্ঞাপন দেওয়ার নিয়ম।"),
                              ("privacy", "প্রাইভেসি নীতি", "দামতুলনা কোন তথ্য রাখে, কুকি ও বিজ্ঞাপন সংক্রান্ত নীতি।")):
        write(slug, "info.html", page=slug, heading=title, store_names=", ".join(stores[s]["name"] for s in enabled),
              n_items=len(listed_items), n_stores=len(enabled), n_all=len(items),
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
    bcount = Counter(i["bslug"] for i in vals if i["bslug"])
    admin_brands = [{"s": b_, "n": BR.display(b_), "k": k_, "v": [x for x, _ in BR.spell[b_].most_common(5)]}
                    for b_, k_ in bcount.most_common()]
    # সম্ভাব্য মিল: যেগুলো মেলালে এক দোকানের প্রোডাক্ট প্রথমবার দুই দোকানে তুলনা করা যাবে, সেগুলো আগে
    _lv = lambda pid_: {s_ for s_, o_ in (offers.get(pid_) or {}).items() if o_.get("in_stock") and o_.get("price")}
    not_same_ = set(mm.get("not_same", []))
    not_same_ |= set(mm.get("sugg_hidden", []))  # অ্যাডমিন তালিকা থেকে সরানো (আলাদা ঘোষণা নয়; স্বয়ংক্রিয় মিল বন্ধ হয় না)
    sugg_admin = []
    for x in auto_sugg + [dict(y, why="নাম কাছাকাছি") for y in suggestions]:
        a_, b_ = amap.get(x["a"], x["a"]), amap.get(x["b"], x["b"])
        if a_ == b_ or a_ not in offers or b_ not in offers or {a_, b_} <= done or "|".join(sorted((a_, b_))) in not_same_:
            continue
        la, lb = _lv(a_), _lv(b_)
        lift = 2 if len(la | lb) >= 2 and len(la) < 2 and len(lb) < 2 else 1 if (la - lb) and (lb - la) else 0
        sugg_admin.append(dict(x, a=a_, b=b_, a_name=products[a_]["name"], b_name=products[b_]["name"], lift=lift,
                               sa=[stores[s_]["name"] for s_ in sorted(la) if s_ in stores], sb=[stores[s_]["name"] for s_ in sorted(lb) if s_ in stores]))
    _seen = set()
    sugg_admin = [x for x in sorted(sugg_admin, key=lambda x: (-x["lift"], -x["score"]))
                  if not ("|".join(sorted((x["a"], x["b"]))) in _seen or _seen.add("|".join(sorted((x["a"], x["b"])))))]
    sugg_total = len(sugg_admin)
    sugg_admin = sugg_admin[:2000]
    admin = {"updated": updated, "health": health, "sugg_total": sugg_total, "stock": dict(stock_counts), "stats": stats, "categories": all_cats, "brands": admin_brands,
             "brand_min": BR.conf.get("min_products", 5),
             "suggestions": sugg_admin,
             "auto_merges": [[o_, products[o_]["name"], k_, products[k_]["name"]] for o_, k_ in sorted(amap.items(), key=lambda x: products[x[1]]["name"])
                             if o_ in products and k_ in products][:1500],
             "price_checks": sorted(({"id": i["id"], "n": i["name"], "c": i["cat_name"],
                                      "o": [[s_, stores[s_]["name"], o_["price"], s_ in i["sus"]]
                                            for s_, o_ in sorted(offers[i["id"]].items(), key=lambda x: x[1].get("price") or 0)
                                            if o_.get("price") and o_.get("in_stock")]}
                                     for i in vals if i["sus"]), key=lambda x: -(x["o"][-1][2] / max(1, x["o"][0][2])))[:300],
             "fresh": [{"id": i["id"], "n": i["name"], "c": i["cat_name"]} for i in fresh_all[:100]]}
    # SEO স্বাস্থ্য (অ্যাডমিন → SEO)
    _lst = list(listed_items.values())
    _tc = defaultdict(list)
    for pid_, t_ in seo_titles.items():
        _tc[t_].append(pid_)
    _dups = sorted(((t_, ps_) for t_, ps_ in _tc.items() if len(ps_) > 1), key=lambda x: -len(x[1]))
    _long = sorted(((t_, pid_) for pid_, t_ in seo_titles.items() if len(t_) > 70), key=lambda x: -len(x[0]))
    _samp = next((i["id"] for i in sorted(_lst, key=lambda i: -i["live_count"]) if i["imgs"] and i["brand"]), None)
    # অ্যাডমিন ড্যাশবোর্ড: আজ প্রতিটা দোকানে কতগুলো দাম কমল/বাড়ল/স্টক শেষ/নতুন (দামের ইতিহাস থেকে)
    _sn = {s_: Counter() for s_ in stores}
    _dd = health.get("date") or today
    for _ss in history.values():
        for s_, ch_ in _ss.items():
            if not ch_ or s_ not in _sn:
                continue
            ch_ = sorted(ch_)
            if ch_[-1][0] != _dd:
                continue
            prev_ = [v_ for d_, v_ in ch_ if d_ < _dd]
            a_, b_ = (prev_[-1] if prev_ else "new"), ch_[-1][1]
            c_ = _sn[s_]
            if a_ == "new":
                c_["new"] += 1
            elif a_ and b_:
                c_["dn" if b_ < a_ else "up" if b_ > a_ else "eq"] += 1
            elif a_ and b_ is None:
                c_["oos"] += 1
            elif a_ is None and b_:
                c_["back"] += 1
    admin["store_news"] = {s_: dict(c_) for s_, c_ in _sn.items()}
    admin["store_names"] = {s_: v_["name"] for s_, v_ in stores.items()}
    admin["enabled"] = list(enabled)
    admin["track"] = {k_: bool(v_) for k_, v_ in common["track"].items()}
    admin["nobrand"] = [{"id": i["id"], "n": i["name"], "c": i["cat_name"], "u": i["unbranded"]} for i in sorted(_lst, key=lambda i: (i["unbranded"], i["name"]))
                        if not i["brand"] and not i["compat"]][:300]
    admin["seo"] = {
        "indexable": sum(1 for i in _lst if i["indexed"]), "noindex": sum(1 for i in vals if not i["listed"] and i["state"] != "gone"),
        "held": sum(1 for i in _lst if not i["indexed"]), "min_stores": MIN_STORES,
        "gone": stock_counts.get("gone", 0), "sitemap_urls": len(urls), "pages": sum(1 for u in urls if "/p/" not in u),
        "no_image": sum(1 for i in _lst if not i["imgs"]), "no_brand": sum(1 for i in _lst if not i["brand"] and not i["compat"] and not i["unbranded"]),
        "unbranded": sum(1 for i in _lst if i["unbranded"]),
        "compat": sum(1 for i in _lst if i["compat"]),
        "single_store": sum(1 for i in _lst if i["indexed"] and i["live_count"] <= 1),
        "thin": sum(1 for i in _lst if i["live_count"] <= 1 and i["id"] not in details and not i["imgs"]),
        "with_specs": sum(1 for i in _lst if i["id"] in details),
        "changed_today": sum(1 for u in urls if lastmod.get(u) == today),
        "dup_titles": len(_dups), "dup_pages": sum(len(ps_) for _, ps_ in _dups),
        "dup_samples": [[t_, ps_[:4]] for t_, ps_ in _dups[:15]],
        "long_titles": len(_long), "long_samples": [[t_, pid_] for t_, pid_ in _long[:10]],
        # সাইটের নিয়ম পাহারা: সংখ্যাওয়ালা/ডুপ্লিকেট লিংক আর ডুপ্লিকেট ক্যাটাগরি (সব ০ থাকার কথা)
        "rule_bad_ids": [i["id"] for i in vals if i["state"] != "gone" and _bad_id(i["id"], products[i["id"]]["name"])][:20],
        "rule_dup_names": [v_ for v_ in _same_name.values() if len(v_) > 1][:20],
        "rule_dup_cats": _dup_cats,
        "force_index": sorted(force_index), "force_noindex": sorted(force_noindex),
        "sample": _samp, "robots": common["robots_meta"], "indexnow": bool(SEO.get("indexnow") and re.fullmatch(r"[a-f0-9]{32}", SEO.get("indexnow_key") or "")),
    }
    (DIST / "admin").mkdir(exist_ok=True)
    (DIST / "admin/admin.json").write_text(json.dumps(admin, ensure_ascii=False, separators=(",", ":")))
    write("admin", "admin.html", title="অ্যাডমিন প্যানেল | দামতুলনা", description="", noindex=True, noads=True, is_admin=True,
          repo=os.environ.get("GITHUB_REPOSITORY", "shariful881/daam-tulona"))

    search = [{"id": i["id"], "n": i["name"], "c": i["cat_name"], "g": i["category"], "p": (i["best"] or {}).get("price"), "k": i["store_count"]}
              for i in vals]
    (DIST / "search.json").write_text(json.dumps(search, ensure_ascii=False, separators=(",", ":")))
    # হালকা সার্চ: শব্দের প্রথম ২ অক্ষর ধরে ছোট ছোট ইনডেক্স ফাইল (s/p/) আর ৫০০টা করে প্রোডাক্টের টুকরো (s/d/)।
    # একটা খোঁজে সাধারণত ২-৩টা ছোট ফাইল নামে, পুরো তালিকা নয়। (search.json থাকছে শুধু অ্যাডমিনের জন্য)
    # ক্রম: একই ক্যাটাগরির প্রোডাক্ট পাশাপাশি (একটা খোঁজের ফল কম টুকরোয় থাকে), প্রতিটায় নিজের র‍্যাঙ্ক (বেশি স্টোর = আগে)
    rank = {i["id"]: r_ for r_, i in enumerate(sorted(vals, key=lambda i: (-i["live_count"], -i["store_count"], i["best"] is None, i["name"].lower())))}
    ranked = sorted(vals, key=lambda i: (i["category"], rank[i["id"]]))
    sdir = DIST / "s"
    (sdir / "d").mkdir(parents=True, exist_ok=True)
    (sdir / "p").mkdir(parents=True, exist_ok=True)
    for k in range(0, len(ranked), 200):
        (sdir / f"d/{k // 200}.json").write_text(json.dumps(
            [[i["id"], i["name"], i["cat_name"], i["category"], (i["best"] or {}).get("price"), i["store_count"], rank[i["id"]]]
             for i in ranked[k:k + 200]], ensure_ascii=False, separators=(",", ":")))
    post = defaultdict(lambda: defaultdict(list))
    for n_, i in enumerate(ranked):
        for tok in set(search_tokens(f"{i['name']} {i['cat_name']} {i['brand']}")):
            if len(tok) >= 2:
                post[shard_key(tok)][tok].append(n_)
    for key, toks in post.items():
        (sdir / f"p/{key}.json").write_text(json.dumps(toks, ensure_ascii=False, separators=(",", ":")))
    # সাইটম্যাপ: পাতা আর প্রোডাক্ট আলাদা ফাইলে, প্রোডাক্ট ২০,০০০ করে ভাগ (একটা ফাইলের সীমা ৫০,০০০);
    # প্রতিটা লিংকে শেষ দাম বদলের তারিখ (lastmod), যাতে Google বদলানো পাতা আগে দেখে
    head = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    prod_urls = [u for u in urls if "/p/" in u]
    page_urls = [u for u in urls if "/p/" not in u]
    parts = [("sitemap-pages.xml", page_urls)] + [(f"sitemap-products-{i // 20000 + 1}.xml", prod_urls[i:i + 20000])
                                                  for i in range(0, len(prod_urls), 20000)]
    for fn, lst in parts:
        (DIST / fn).write_text(head + "".join(f"<url><loc>{u}</loc><lastmod>{lastmod.get(u, today)}</lastmod></url>\n" for u in lst) + "</urlset>\n")
    (DIST / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      + "".join(f"<sitemap><loc>{SITE_URL}/{fn}</loc><lastmod>{today}</lastmod></sitemap>\n" for fn, _ in parts)
                                      + "</sitemapindex>\n")
    # আজকের দাম কমা (Telegram পোস্টের জন্য, tools/telegram_post.py)
    (DIST / "drops.json").write_text(json.dumps([
        {"name": d_["name"], "old": d_["old"], "new": d_["best"]["price"], "store": stores[d_["best"]["store"]]["name"],
         "url": f"{SITE_URL}/p/{d_['id']}/", "stores": d_["live_count"]} for d_ in drops_top], ensure_ascii=False))
    # IndexNow: নতুন/বদলানো পাতার খবর Bing, Yandex ইত্যাদিকে সাথে সাথে জানানো (দাম আনার পর tools/indexnow.py পাঠায়)
    _ik = SEO.get("indexnow_key") or ""
    if SEO.get("indexnow") and re.fullmatch(r"[a-f0-9]{32}", _ik) and SITE_URL:
        (DIST / f"{_ik}.txt").write_text(_ik)
        _chg = [u for u in urls if lastmod.get(u) == today or "/p/" not in u][:10000]
        (ROOT / ".indexnow.json").write_text(json.dumps({"key": _ik, "keyLocation": f"{SITE_URL}/{_ik}.txt", "site": SITE_URL, "urls": _chg}, ensure_ascii=False))
    (DIST / "robots.txt").write_text(f"User-agent: *\nDisallow: {BASE}/admin/\nDisallow: {BASE}/search/\nSitemap: {SITE_URL}/sitemap.xml\n")
    (DIST / ".nojekyll").write_text("")
    print(f"{len(urls)}টি পেজ তৈরি হয়েছে ({len(items)} প্রোডাক্ট, বিস্তারিত তথ্যসহ {stats['details']}), {time.time() - t0:.1f} সেকেন্ডে")


if __name__ == "__main__":
    main()
