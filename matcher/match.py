"""বিভিন্ন স্টোরের একই প্রোডাক্টকে এক জায়গায় জোড়া লাগায় আর দামের ইতিহাস জমা রাখে।

ইনপুট:  data/raw/latest.json (স্ক্র্যাপারের আজকের ফল)
আউটপুট: data/products.json  (মাস্টার প্রোডাক্ট তালিকা)
         data/offers.json    (প্রতিটা প্রোডাক্টের প্রতিটা স্টোরের সর্বশেষ দাম)
         data/history.csv    (প্রতিদিনের দাম)
         data/suggestions.json (সম্ভাব্য মিল, মানুষের যাচাই দরকার)

চালানো: python -m matcher.match
"""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

STOP = {
    "laptop", "desktop", "ram", "memory", "module", "sodimm", "udimm", "dimm", "so", "mhz", "bus",
    "notebook", "for", "with", "the", "and", "internal", "solid", "state", "drive", "processor",
    "cpu", "bd", "price", "in", "single", "retail", "pc", "pcs", "ssd", "nvme", "m2", "m",
    "2280", "gaming", "series", "gen", "only", "tray", "box", "desktop's", "lifetime", "warranty",
    "year", "years", "new", "edition", "graphics", "with", "radeon", "inch",
}
BRAND_ALIAS = {"g.skill": "gskill", "g skill": "gskill", "western digital": "wd", "teamgroup": "team"}


def normalize(name: str) -> str:
    s = re.sub(r"\([^)]*\)", " ", name.lower())  # বন্ধনীর ভেতরের কোড/ওয়ারেন্টি বাদ
    for a, b in BRAND_ALIAS.items():
        s = s.replace(a, b)
    s = re.sub(r"so[\s-]?dimm", " sodimm ", s)
    s = re.sub(r"ddr(\d)l\b", r"ddr\1", s)
    s = re.sub(r"(\d+)\s*(gb|tb)\b", r" \1\2 ", s)
    s = re.sub(r"\b(\d{4})\s*(mhz|bus)\b", r" \1 ", s)
    s = re.sub(r"\bc(?:l)?(\d{2})\b", r" cl\1 ", s)
    s = re.sub(r"[^a-z0-9.]+", " ", s).replace(" .", " ").replace(". ", " ")
    return s


def tokens(name: str) -> list[str]:
    return [t for t in normalize(name).split() if t and t not in STOP]


def specs(name: str, category: str) -> dict:
    n = name.lower()
    out = {}
    cap = re.search(r"(\d+)\s*(gb|tb)\b", n)
    if cap:
        out["capacity"] = f"{cap.group(1)}{cap.group(2).upper()}"
    if "ram" in category:
        ddr = re.search(r"ddr\s?(\d)(l?)", n)
        if ddr:
            out["type"] = f"DDR{ddr.group(1)}{'L' if ddr.group(2) else ''}"
        sp = re.search(r"\b(\d{4})\s*(mhz|bus)?\b", n)
        if sp and 1066 <= int(sp.group(1)) <= 9600:
            out["speed"] = f"{sp.group(1)}MHz"
        out["form"] = "SO-DIMM" if category == "laptop-ram" else "DIMM"
    if category == "ssd":
        if "nvme" in n or "pcie" in n or "gen4" in n or "gen 4" in n or "gen3" in n or "gen5" in n:
            out["interface"] = "NVMe PCIe"
        elif "sata" in n or "2.5" in n:
            out["interface"] = "SATA"
        if "m.2" in n or "m2" in n:
            out["form"] = "M.2"
        elif "2.5" in n:
            out["form"] = '2.5"'
    if category == "processor":
        out["brand_cpu"] = "AMD" if ("amd" in n or "ryzen" in n or "athlon" in n) else ("Intel" if ("intel" in n or "core" in n) else None)
        m = re.search(r"(ryzen\s?\d\s?\d{4}\w*|i[3579][\s-]?\d{4,5}\w*|ultra\s?\d\s?\d{3}\w*|athlon\s?\w+|pentium\s?\w+|celeron\s?\w+)", n)
        if m:
            mdl = m.group(1).upper().replace("RYZEN", "Ryzen").replace("ULTRA", "Ultra").replace("ATHLON", "Athlon")
            out["model"] = re.sub(r"^I([3579])", r"i\1", mdl)
    return {k: v for k, v in out.items() if v}


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:80].rstrip("-") or "product"


def jaccard(a: set, b: set) -> float:
    return len(a & b) / max(1, len(a | b))


def load(path: Path, default):
    return json.loads(path.read_text()) if path.exists() else default


def main():
    raw = load(DATA / "raw/latest.json", None)
    if not raw:
        raise SystemExit("data/raw/latest.json নেই — আগে স্ক্র্যাপার চালান")
    today = raw["date"]
    products = load(DATA / "products.json", {})
    old_offers = load(DATA / "offers.json", {})
    manual = load(DATA / "manual_matches.json", {"merge": [], "ignore": []})

    redirect = {}
    for m in manual.get("merge", []):
        for pid in m.get("merge", []):
            redirect[pid] = m["keep"]
    ignored = set(manual.get("ignore", []))

    # নিয়ম বদলালে পুরনো প্রোডাক্টের key নতুন নিয়মে আবার হিসাব করা
    for pid, p in products.items():
        if "#" not in p["key"]:
            p["key"] = p["category"] + "|" + " ".join(sorted(set(tokens(p["name"]))))
    key_to_id = {}
    for pid, p in sorted(products.items(), key=lambda x: x[1]["created"]):
        key_to_id.setdefault(p["key"], pid)
    url_to_id = {}
    for pid, stores in old_offers.items():
        for o in stores.values():
            url_to_id[o["url"]] = pid

    # একই স্টোরে একই key দুইবার এলে সেগুলো আলাদা প্রোডাক্ট ধরা হবে
    seen = defaultdict(int)
    for o in raw["offers"]:
        o["_key"] = o["category"] + "|" + " ".join(sorted(set(tokens(o["name"]))))
        seen[(o["store"], o["_key"])] += 1

    offers: dict[str, dict] = defaultdict(dict)
    for o in raw["offers"]:
        key = o["_key"]
        if seen[(o["store"], key)] > 1:
            key += "#" + o["store"] + ":" + o["url"].rstrip("/").rsplit("/", 1)[-1]
        pid = url_to_id.get(o["url"]) or key_to_id.get(key)
        if pid is None:
            base = slugify(o["name"])
            pid, i = base, 2
            while pid in products:
                pid, i = f"{base}-{i}", i + 1
            products[pid] = {
                "name": o["name"], "category": o["category"], "key": key,
                "brand": (o.get("brand") or o["name"].split()[0]).strip(),
                "specs": specs(o["name"], o["category"]), "created": today,
                "store_image": o.get("image"),
            }
            key_to_id[key] = pid
        pid = redirect.get(pid, pid)
        if pid in ignored:
            continue
        if o.get("features") and pid in products:  # তালিকা থেকে পাওয়া মূল ফিচার, প্রতিদিন নতুন করে
            products[pid]["features"] = o["features"]
        cur = offers[pid].get(o["store"])
        if cur is None or (o["price"] or 10**9) < (cur["price"] or 10**9):
            offers[pid][o["store"]] = {k: o[k] for k in ("name", "url", "price", "regular", "in_stock", "status")} | {"seen": today} \
                | ({"img": o["image"]} if o.get("image") else {})

    # আজ যে স্টোর ব্যর্থ হয়েছে, তার আগের দাম রেখে দাও (পুরনো চিহ্নসহ)
    failed = {s for s, h in raw["health"].items() if h["enabled"] and h["items"] == 0}
    # কিছু ক্যাটাগরি ব্যর্থ হলে (ব্লক/সার্ভার ভুল) শুধু সেই ক্যাটাগরির আগের দাম রাখো
    part = {s: set(h.get("failed_cats") or []) for s, h in raw["health"].items()}
    for pid, stores in old_offers.items():
        cat = (products.get(redirect.get(pid, pid)) or {}).get("category")
        for s, o in stores.items():
            if (s in failed or cat in part.get(s, ())) and s not in offers.get(redirect.get(pid, pid), {}):
                offers[redirect.get(pid, pid)][s] = o | {"stale": True}

    # দামের ইতিহাস: শুধু দাম বা স্টক বদলালে নতুন সারি (ফাইল ছোট রাখতে)
    hist_path = DATA / "history.csv"
    rows, last = [], {}
    if hist_path.exists():
        with hist_path.open() as f:
            for r in csv.DictReader(f):
                if r["date"] == today:
                    continue
                rows.append(r)
                last[(r["product"], r["store"])] = (int(r["price"]), int(r["in_stock"]))
    for pid, stores in offers.items():
        for s, o in stores.items():
            if o.get("price") and not o.get("stale"):
                state = (o["price"], int(o["in_stock"]))
                if last.get((pid, s)) != state:
                    rows.append({"date": today, "product": pid, "store": s, "price": state[0], "in_stock": state[1]})
    with hist_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "product", "store", "price", "in_stock"])
        w.writeheader()
        w.writerows(rows)

    # সম্ভাব্য মিল: একই ক্যাটাগরি, একই ব্র্যান্ড, একই ক্যাপাসিটি, কাছাকাছি নাম, আলাদা স্টোর
    sugg = []
    live = [pid for pid in offers if pid in products]
    by_bucket = defaultdict(list)
    for pid in live:
        p = products[pid]
        by_bucket[(p["category"], p["brand"].lower(), p["specs"].get("capacity"))].append(pid)
    for group in by_bucket.values():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if set(offers[a]) & set(offers[b]):
                    continue
                score = jaccard(set(tokens(products[a]["name"])), set(tokens(products[b]["name"])))
                if score >= 0.6:
                    sugg.append({"a": a, "b": b, "score": round(score, 2),
                                 "a_name": products[a]["name"], "b_name": products[b]["name"]})
    sugg.sort(key=lambda x: -x["score"])

    (DATA / "products.json").write_text(json.dumps(products, ensure_ascii=False, indent=1, sort_keys=True))
    (DATA / "offers.json").write_text(json.dumps(offers, ensure_ascii=False, indent=1, sort_keys=True))
    (DATA / "suggestions.json").write_text(json.dumps(sugg[:200], ensure_ascii=False, indent=1))
    (DATA / "health.json").write_text(json.dumps({"date": today, "scraped_at": raw["scraped_at"], "stores": raw["health"]}, ensure_ascii=False, indent=1))
    multi = sum(1 for s in offers.values() if len([o for o in s.values() if o.get("price")]) > 1)
    print(f"প্রোডাক্ট: {len(offers)} | একাধিক স্টোরে দাম আছে: {multi} | আজ নতুন: {sum(1 for p in products.values() if p['created'] == today)} | সম্ভাব্য মিল: {len(sugg)}")


if __name__ == "__main__":
    main()
