"""ব্র্যান্ডের নিজের ওয়েবসাইট থেকে প্রোডাক্টের বিবরণ (দাম নয়)।

ধাপ:
  ১. সূচি: ব্র্যান্ডের sitemap থেকে প্রোডাক্ট পাতার তালিকা -> data/brand_index/<ব্র্যান্ড>.json (সপ্তাহে একবার নতুন করে)
  ২. মেলানো: আমাদের প্রোডাক্টের নামের মডেল কোড (যেমন AX73, B3605, XVR5108HS) পাতার ঠিকানার সাথে মেলানো;
     নিশ্চিত মিল না হলে বাদ (ভুল বিবরণের চেয়ে বিবরণ না থাকা ভালো)
  ৩. আনা: প্রতিটা ব্র্যান্ড আলাদা থ্রেডে, robots.txt মেনে, নিজের বিরতি ও দৈনিক সীমায়
ফল: data/brand_details/<আইডির প্রথম অক্ষর>/<আইডি>.json  (১২০ দিন পর নতুন করে)
চালানো: python -m tools.brand_details [--index-only] [--dry]
"""
import json
import os
import re
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scraper.common import Blocked, fetch
from scraper.details_generic import parse_brand

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BD = timezone(timedelta(hours=6))
CONF = json.loads((ROOT / "config/brand_sources.json").read_text())["brands"]
MAX_MINUTES = int(os.environ.get("BRAND_MINUTES", "120"))
REFRESH_DAYS = 120
LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>")


def out_path(pid):
    return DATA / "brand_details" / pid[:1] / f"{pid}.json"


# ---------- ১. সূচি ----------
def _get(url, delay):
    return fetch(url, delay, cache=False)


def build_index(brand, conf):
    url_re = re.compile(conf["url_re"])
    sm_re = re.compile(conf["sitemap_re"]) if conf.get("sitemap_re") else None
    todo, seen, urls = list(conf["sitemaps"]), set(), set()
    while todo and len(seen) < 300:
        sm = todo.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        try:
            xml = _get(sm, conf.get("delay", 6) if len(seen) > 1 else 0)
        except Exception as e:
            print(f"  {brand}: sitemap ব্যর্থ {sm} ({type(e).__name__})", flush=True)
            continue
        locs = [u.replace("&amp;", "&") for u in LOC.findall(xml)]
        if "<sitemapindex" in xml[:2000]:
            todo += [u for u in locs if not sm_re or sm_re.search(u)]
        else:
            urls.update(u for u in locs if url_re.match(u))
    items = sorted(urls)
    (DATA / "brand_index").mkdir(parents=True, exist_ok=True)
    (DATA / "brand_index" / f"{brand}.json").write_text(json.dumps(
        {"built": datetime.now(BD).date().isoformat(), "urls": items}, ensure_ascii=False, indent=0))
    print(f"{brand}: সূচিতে {len(items)}টা পাতা ({len(seen)}টা sitemap)", flush=True)
    return items


def load_index(brand, conf, force=False):
    p = DATA / "brand_index" / f"{brand}.json"
    if p.exists() and not force:
        d = json.loads(p.read_text())
        if (datetime.now(BD).date() - datetime.fromisoformat(d["built"]).date()).days < 7 and d["urls"]:
            return d["urls"]
    return build_index(brand, conf)


# ---------- ২. মেলানো ----------
def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


SPEEDISH = re.compile(r"^(\d+(gb|tb|mb|hz|w|mm|cm|mah|mp|k|p|th|nd|rd|st|g|v|a|x|in|inch|ms|fps|mbps|gbps|ghz|mhz|ch|rpm|cfm|l|wh|va|kg)"
                      r"|(ddr|lpddr|gddr|pcie|gen|usb|wifi|rtx|gtx|rx|i|r|ryzen|core|wi|bt|cat|hdmi|dp|ipx|ip|cl|lga|am|ultra)\d{0,2}"
                      r"|(ax|ac|be|axe|n)\d{3,5})$")  # AX3000/AC1200 গতির শ্রেণি, মডেল নয়
VENDOR_PREFIX = re.compile(r"^(dhi|dh|tl|ds)(?=[a-z]{2,}\d)")


def codes_of(name):
    """নামের মডেল কোড, পুরোটা (A520M-R -> a520mr; ভাঙা অংশ নয়, তাহলে A520M-A-র পাতার সাথে ভুল মিল হতো)।"""
    out = set()
    for tok in re.split(r"[\s(),/|+]+", name):
        n = norm(tok.strip(".-_\"'"))
        if len(n) >= 3 and re.search(r"\d", n) and re.search(r"[a-z]", n) and not SPEEDISH.match(n):
            out.add(n)
            v = VENDOR_PREFIX.sub("", n)  # DH-XVR5108HS -> xvr5108hs
            if v != n and len(v) >= 4:
                out.add(v)
    return out


VARIANT = {"wifi", "ii", "iii", "pro", "plus", "max", "ultra", "lite", "mini", "elite", "prime", "ti", "super", "oc",
           "d4", "d5", "csm", "se", "slim", "neo", "rgb", "argb", "v2", "v3", "x3d", "evo", "duo", "air", "wireless"}


PAGE_OK = {"case", "asus", "tplink", "tp", "link", "dahua", "corsair", "series", "display", "w", "b", "white", "black", "gaming",
           "monitor", "router", "mouse", "keyboard", "headset", "camera", "kit"}
WEAK_VARIANT = {"wifi", "wireless", "rgb", "argb", "air"}


def words_of(name):
    return {w for w in re.findall(r"[a-z]{3,}", name.lower())}


def slug_chunks(url):
    path = re.sub(r"^https?://[^/]+", "", url).lower().replace("techspec", "")
    parts = [p for p in re.split(r"[^a-z0-9]+", path) if p]
    chunks = set()
    for i in range(len(parts)):
        for j in range(i + 1, min(len(parts), i + 5) + 1):
            chunks.add("".join(parts[i:j]))
    return chunks, set(parts)


def best_match(name, index_rows):
    codes = codes_of(name)
    if not codes:
        return None
    words = words_of(name)
    scored = []
    for url, chunks, parts in index_rows:
        hit = [c for c in codes if c in chunks and not (c[0].isdigit() and len(c) < 4)]  # শুধু পুরো কোডের হুবহু মিল
        if not hit:
            continue
        # নামের লম্বা আসল মডেল কোড (FA506NCG, XVR1B04H) পাতায় নেই, মিলেছে শুধু ছোট সিরিজ কোড (A15) -> সিরিজের সাধারণ পাতা, বাদ
        longest = max(codes, key=len)
        if len(longest) >= 6 and longest not in hit and max(len(c) for c in hit) < len(longest):
            continue
        # ক্যাপাসিটি না মিললে (1TB বনাম 2TB-র পাতা) বাদ
        caps_url = set(re.findall(r"(?<![a-z0-9])(\d+(?:gb|tb))(?![a-z0-9])", url.lower().replace("-", " ")))
        caps_name = set(re.findall(r"(\d+)\s?(gb|tb)\b", name.lower()))
        caps_name = {a + b for a, b in caps_name}
        if caps_url and caps_name and not (caps_url & caps_name):
            continue
        # মডেলের বাড়তি অংশ (WIFI, II, PRO, PLUS…) দুই দিকে একই হতে হবে: A520M-PLUS II ≠ A520M-PLUS WIFI-র পাতা
        last = [t for t in re.split(r"[^a-z0-9]+", url.lower().rstrip("/").replace("/techspec", "").rsplit("/", 1)[-1]) if t]
        name_t = set(re.findall(r"[a-z0-9]+", name.lower()))
        page_v, name_v = {t for t in last if t in VARIANT}, {t for t in name_t if t in VARIANT}
        if (page_v - name_v) or ((name_v - page_v) - WEAK_VARIANT):  # নামের "WiFi"/"RGB" প্রায়ই শুধু বর্ণনা
            continue
        # ছোট মডেল-ঠিকানায় (tapo-c230, tl-sg108-m2) এমন শব্দ থাকলে যা নামে নেই -> অন্য প্রোডাক্ট লাইন/সংস্করণ
        if len(last) <= 5 and any(len(t) > 1 and t not in name_t and t not in PAGE_OK and not any(t in c for c in hit) for t in last):
            continue
        code_score = float(sum(len(c) for c in hit))
        if code_score < 3:
            continue
        scored.append((code_score + 0.3 * len(words & parts), code_score, url))
    if not scored:
        return None
    scored.sort(reverse=True)
    if len(scored) > 1 and scored[1][0] == scored[0][0]:
        # সমান মিল: ঠিকানার শেষ অংশ ছোট যেটার (মূল মডেল), নয়তো অনিশ্চিত -> বাদ
        tied = [s for s in scored if s[0] == scored[0][0]]
        tied.sort(key=lambda s: len(s[2]))
        if len(tied[0][2]) == len(tied[1][2]):
            return None
        return tied[0][2]
    return scored[0][2]


def plan(brand, conf, products, offers, index):
    rows = [(u,) + slug_chunks(u) for u in index]
    today = datetime.now(BD).date()
    jobs = []
    for pid, so in offers.items():
        p = products.get(pid)
        if not p or p["brand"].lower() != brand:
            continue
        op = out_path(pid)
        if op.exists():
            try:
                if (today - datetime.fromisoformat(json.loads(op.read_text())["fetched"]).date()).days < REFRESH_DAYS:
                    continue
            except Exception:
                pass
        url = best_match(p["name"], rows)
        if url:
            multi = sum(1 for o in so.values() if o.get("price")) > 1
            jobs.append((not multi, not any(o.get("in_stock") for o in so.values()), pid, url))
    jobs.sort()
    return [(pid, url) for *_, pid, url in jobs]


# ---------- ৩. আনা ----------
def worker(brand, conf, jobs, deadline, stats, lock):
    done = failed = 0
    cache = {}  # একই পাতা কয়েকটা প্রোডাক্টের (রং/সাইজ ভেদ) হলে একবারই আনা
    for pid, url in jobs[:conf.get("limit", 200)]:
        if time.time() > deadline:
            break
        try:
            if url not in cache:
                cache[url] = parse_brand(fetch(url, conf.get("delay", 6), cache=False), brand)
            d = dict(cache[url])
        except Blocked as e:
            print(f"{brand}: ব্লক ({e}), আজ এখানেই থামা", flush=True)
            break
        except PermissionError:
            failed += 1
            continue
        except Exception:
            failed += 1
            if failed >= 20 and done == 0:
                break
            continue
        if not d.get("specs"):
            failed += 1
            continue
        d.update(fetched=datetime.now(BD).isoformat(timespec="minutes"), source=url, brand_site=conf["name"])
        with lock:
            op = out_path(pid)
            op.parent.mkdir(parents=True, exist_ok=True)
            op.write_text(json.dumps(d, ensure_ascii=False, indent=1))
        done += 1
    stats[brand] = (done, failed, len(jobs))


def main(argv):
    products = json.loads((DATA / "products.json").read_text())
    offers = json.loads((DATA / "offers.json").read_text())
    only = [a for a in argv if not a.startswith("--")]
    deadline, stats, lock, threads = time.time() + MAX_MINUTES * 60, {}, threading.Lock(), []
    plans = {}
    for brand, conf in CONF.items():
        if only and brand not in only:
            continue
        try:
            index = load_index(brand, conf, force="--reindex" in argv)
        except Blocked as e:
            print(f"{brand}: সূচি আনতে ব্লক ({e})")
            continue
        if "--index-only" in argv:
            continue
        jobs = plan(brand, conf, products, offers, index)
        mine = sum(1 for p in products.values() if p["brand"].lower() == brand)
        print(f"{brand}: আমাদের {mine}টা প্রোডাক্টের মধ্যে {len(jobs)}টা মিলেছে (এই রানে সর্বোচ্চ {conf.get('limit')})", flush=True)
        plans[brand] = jobs
        if "--dry" in argv:
            for pid, url in jobs[:15]:
                print(f"    {products[pid]['name'][:70]:70} -> {url}")
            continue
        t = threading.Thread(target=worker, args=(brand, conf, jobs, deadline, stats, lock), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    for b, (d, f, n) in stats.items():
        print(f"{b:10} সম্পন্ন {d} | ব্যর্থ {f} | মিলেছিল {n}")


if __name__ == "__main__":
    main(sys.argv[1:])
