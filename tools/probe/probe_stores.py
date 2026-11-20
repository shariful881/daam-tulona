"""দরদামের দোকানগুলো থেকে দাম তোলা যায় কিনা যাচাই: robots.txt, প্ল্যাটফর্ম, ঢোকা যায় কিনা। প্রতি দোকানে ৪-৬টি অনুরোধ, ধীরে।"""
import json, re, sys, time, urllib.robotparser
import requests
UA = "DaamTulonaBot/0.1 (+https://github.com/shariful881/daam-tulona)"
H = {"User-Agent": UA, "Accept-Language": "en,bn;q=0.8"}
OURS = {"Star Tech","PC House","Diamu","Apple Gadgets","Computer Vision","PQS","Sell Tech"}
def get(url, **kw):
    try:
        r = requests.get(url, headers=H, timeout=25, allow_redirects=True, **kw)
        return r
    except Exception as e:
        return e
def chal(r):
    if not hasattr(r, "status_code"): return False
    t = r.text[:4000].lower()
    return r.status_code in (403, 503, 429) and ("cloudflare" in t or "cf-chl" in t or "just a moment" in t or "attention required" in t) or "cf-chl" in t or "challenge-platform" in t
out = []
for line in open(sys.argv[1]):
    name, dom, n = line.strip().split("|")
    if name in OURS: continue
    base = f"https://{dom}" if dom.count(".") > 1 or dom.startswith("shop.") else f"https://{dom}"
    rec = {"name": name, "domain": dom, "dordam_products": int(n)}
    home = get(base + "/")
    if isinstance(home, Exception):
        home = get(f"https://www.{dom}/")
    if isinstance(home, Exception):
        rec["home"] = "error:" + type(home).__name__; out.append(rec); print(rec, flush=True); continue
    base = re.match(r"https?://[^/]+", home.url).group(0)
    html = home.text
    rec.update(home=home.status_code, final=base, server=home.headers.get("server", ""), cf=("cloudflare" in home.headers.get("server", "").lower()), challenge=chal(home), size=len(html))
    low = html.lower()
    plat = []
    if "cdn.shopify.com" in low or "shopify" in home.headers.get("x-shopid", "") : plat.append("shopify")
    if "wp-content" in low or "woocommerce" in low: plat.append("woocommerce" if "woocommerce" in low else "wordpress")
    if "catalog/view" in low or "route=product" in low or "route=common" in low: plat.append("opencart")
    if "_next/static" in low or "__next_data__" in low: plat.append("nextjs")
    if "/_nuxt/" in low: plat.append("nuxt")
    if "mage/" in low or "magento" in low: plat.append("magento")
    if "laravel" in low or "livewire" in low: plat.append("laravel")
    if "bigcommerce" in low: plat.append("bigcommerce")
    rec["platform"] = plat
    rb = get(base + "/robots.txt")
    rp = urllib.robotparser.RobotFileParser()
    if hasattr(rb, "status_code") and rb.status_code == 200 and "<html" not in rb.text[:200].lower():
        rp.parse(rb.text.splitlines()); rec["robots"] = "ok"
        rec["crawl_delay"] = rp.crawl_delay(UA)
        rec["sitemaps"] = rp.site_maps() or []
    else:
        rp.parse([]); rec["robots"] = getattr(rb, "status_code", "err")
    rec["allow_home"] = rp.can_fetch(UA, base + "/")
    tests = {}
    if "shopify" in plat:
        u = base + "/products.json?limit=2"
        r = get(u); tests["shopify_json"] = [getattr(r, "status_code", "err"), rp.can_fetch(UA, u), bool(hasattr(r, "text") and '"variants"' in r.text)]
    if any(p in plat for p in ("woocommerce", "wordpress")):
        u = base + "/wp-json/wc/store/v1/products?per_page=2"
        r = get(u); ok = hasattr(r, "text") and r.text.strip().startswith("[") and '"prices"' in r.text
        tests["woo_store_api"] = [getattr(r, "status_code", "err"), rp.can_fetch(UA, u), ok]
    for sm in ["/sitemap.xml", "/sitemap_index.xml", "/product-sitemap.xml"]:
        u = base + sm; r = get(u)
        if hasattr(r, "status_code") and r.status_code == 200 and "<urlset" in r.text[:3000] or (hasattr(r, "text") and "<sitemapindex" in r.text[:3000]):
            tests["sitemap"] = [sm, rp.can_fetch(UA, u), r.text.count("<loc>")]; break
    rec["tests"] = tests
    rec["has_price_in_home"] = bool(re.search(r"৳\s?[\d,]{3,}|tk\.?\s?[\d,]{3,}|bdt\s?[\d,]{3,}", low))
    out.append(rec); print(json.dumps(rec, ensure_ascii=False), flush=True)
    time.sleep(2)
json.dump(out, open("probe_result.json", "w"), ensure_ascii=False, indent=1)
