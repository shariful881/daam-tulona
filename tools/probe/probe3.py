"""ধাপ ৩: প্রতিটা দোকানে মোট কতগুলো প্রোডাক্ট (আর সম্ভব হলে কতগুলো স্টকে) গোনা। robots.txt মেনে, ধীরে।"""
import json, re, sys, time, urllib.robotparser
import requests
UA = "DaamTulonaBot/0.1 (+https://github.com/shariful881/daam-tulona)"
H = {"User-Agent": UA}
def get(u):
    try: return requests.get(u, headers=H, timeout=40)
    except Exception: return None
def robots(base):
    rp = urllib.robotparser.RobotFileParser(); r = get(base + "/robots.txt")
    rp.parse(r.text.splitlines() if r is not None and r.status_code == 200 and "<html" not in r.text[:200].lower() else []); return rp
PRODURL = re.compile(r"/(product|products|p|item|items|shop)/[^/]+|product_id=|/[a-z0-9]+(-[a-z0-9]+){2,}(\.html)?/?$", re.I)
NOTPROD = re.compile(r"/(category|categories|product-category|collections|brand|brands|blog|blogs|tag|page|pages|news|offer|offers|compare|cart|account)(/|$)", re.I)
for s in json.load(open(sys.argv[1])):
    rec = {k: s[k] for k in ("name", "method", "kind", "dordam")}
    base = s["base"].rstrip("/")
    if s["method"] == "blocked":
        rec["note"] = "আটকে দেয়, গোনা হয়নি"; print(json.dumps(rec, ensure_ascii=False), flush=True); continue
    rp = robots(base)
    try:
        if s["method"] == "woo":
            r = get(base + "/wp-json/wc/store/v1/products?per_page=1")
            rec["total"] = int(r.headers.get("X-WP-Total", -1)) if r is not None else None
            time.sleep(1)
            r = get(base + "/wp-json/wc/store/v1/products?per_page=1&stock_status[]=instock")
            rec["instock"] = int(r.headers.get("X-WP-Total", -1)) if r is not None and r.status_code == 200 else None
        elif s["method"] == "shopify":
            tot = ins = 0; page = 1
            while page <= 60:
                r = get(f"{base}/products.json?limit=250&page={page}")
                if r is None or r.status_code != 200: break
                ps = r.json().get("products", [])
                if not ps: break
                tot += len(ps); ins += sum(1 for p in ps if any(v.get("available") for v in p.get("variants", [])))
                page += 1; time.sleep(1.5)
            rec["total"], rec["instock"] = tot, ins
        else:
            q = [base + (s["sm"] or "/sitemap.xml")]; seen = set(); urls = set(); n = 0
            while q and n < 60:
                u = q.pop(0)
                if u in seen or not rp.can_fetch(UA, u): continue
                seen.add(u); n += 1; r = get(u)
                if r is None or r.status_code != 200: continue
                locs = [x.replace("&amp;", "&") for x in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.text)]
                if "<sitemapindex" in r.text[:5000]:
                    pl = [l for l in locs if "product" in l.lower()]
                    q += pl if pl else [l for l in locs if not re.search(r"(post|page|categor|tag|blog|brand|author|news)", l, re.I)]
                else:
                    pu = "product" in u.lower()
                    urls.update(l for l in locs if pu or (PRODURL.search(l) and not NOTPROD.search(l)))
                time.sleep(1)
            rec["total"] = len(urls); rec["note"] = "sitemap থেকে প্রোডাক্ট লিংক গোনা (স্টক জানা নেই)"
    except Exception as e:
        rec["error"] = type(e).__name__
    print(json.dumps(rec, ensure_ascii=False), flush=True); time.sleep(1)
