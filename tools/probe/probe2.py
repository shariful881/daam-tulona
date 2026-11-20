"""ধাপ ২: প্রতিটা দোকানের sitemap থেকে একটা প্রোডাক্ট পাতা নিয়ে দেখা দাম মেশিনে পড়ার মতো আকারে আছে কিনা (JSON-LD / meta / Next.js ডেটা)।"""
import json, re, sys, time, urllib.robotparser
import requests
UA = "DaamTulonaBot/0.1 (+https://github.com/shariful881/daam-tulona)"
H = {"User-Agent": UA}
def get(u):
    try: return requests.get(u, headers=H, timeout=25)
    except Exception as e: return None
PROD = re.compile(r"/(product|products|p|item|shop)/|-\d{3,}|/[a-z0-9-]{12,}/?$", re.I)
for name, base, sm in json.load(open(sys.argv[1])):
    rec = {"name": name}
    rb = get(base + "/robots.txt"); rp = urllib.robotparser.RobotFileParser(); rp.parse(rb.text.splitlines() if rb is not None and rb.status_code == 200 else [])
    urls = []
    queue = [base + (sm or "/sitemap.xml")]; seen = 0
    while queue and seen < 6 and len(urls) < 5:
        u = queue.pop(0); seen += 1; r = get(u)
        if r is None or r.status_code != 200: continue
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.text)
        if "<sitemapindex" in r.text[:3000]:
            locs.sort(key=lambda x: 0 if "product" in x.lower() else 1); queue = locs[:4] + queue
        else:
            cand = [l for l in locs if "product" in l.lower()] or [l for l in locs if PROD.search(l) and l.rstrip("/") != base]
            urls += cand[5:8] or cand[:3]
        time.sleep(1)
    rec["sample"] = urls[:1]
    if urls:
        u = urls[0]; rec["allowed"] = rp.can_fetch(UA, u); r = get(u)
        if r is not None:
            h = r.text; rec["status"] = r.status_code
            ld = re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', h, re.S)
            rec["jsonld_price"] = any('"Product"' in x and ('"price"' in x or '"lowPrice"' in x) for x in ld)
            rec["meta_price"] = bool(re.search(r'(product:price:amount|og:price:amount|itemprop="price")', h))
            rec["next_data"] = "__NEXT_DATA__" in h or "self.__next_f" in h
            rec["visible_taka"] = bool(re.search(r"৳\s?[\d,]{3,}|tk\.?\s?[\d,]{3,}|bdt\s?[\d,]{3,}", h, re.I))
    print(json.dumps(rec, ensure_ascii=False), flush=True); time.sleep(2)
