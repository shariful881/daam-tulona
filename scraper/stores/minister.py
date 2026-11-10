"""Minister (ministerbd.com, নিজস্ব অফিসিয়াল সাইট) — ফ্রিজ/ফ্রিজার।
robots.txt তালিকার পরের পাতা (?p=2) নিষেধ করে, তাই sitemap.xml থেকে প্রোডাক্ট পাতার ঠিকানা নিয়ে
প্রতিটা পাতা থেকে দাম, স্টক আর সাইজ তোলা হয়। যে পাতা ফ্রিজ নয় সেটা মনে রাখা হয়, আর খোলা হয় না।"""
import re
from datetime import date

from bs4 import BeautifulSoup

from scraper import brand_specs
from scraper.common import fetch, offer, parse_price

SKIP = re.compile(r"ton|inch|tv|led|fan|iron|blender|grinder|mixer|kettle|cooker|oven|stove|bulb|light|stabilizer|"
                  r"washing|ac-|-ac|air|vacuum|heater|geyser|trimmer|dryer|purifier|solar", re.I)
WANT = re.compile(r"^minister-m-\d|freezer|refrigerator|fridge|myone", re.I)
MAX_PAGES = 220


def parse_product(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.select_one("h1.page-title")
    main = soup.select_one(".product-info-main") or soup
    prices = {p.get("data-price-type"): int(float(p["data-price-amount"])) for p in main.select("[data-price-amount]")
              if p.get("data-price-amount")}
    rows = {}
    for tr in soup.select("tr"):
        tds = tr.find_all(["td", "th"])
        if len(tds) == 2:
            rows[tds[0].get_text(" ", strip=True).lower()] = tds[1].get_text(" ", strip=True)
    text = soup.get_text(" ", strip=True)
    cap = None
    for k in ("gross capacity (liter)", "refrigerator capacity", "gross capacity"):
        if rows.get(k):
            m = re.search(r"\d{2,4}", rows[k])
            if m:
                cap = int(m.group())
                break
    stock = main.select_one(".stock")
    m = re.search(r"Cooling Type\s*([A-Za-z -]+?)\s+(?:Door|Dimension|Compressor)", text)
    cool = m.group(1).strip() if m else None
    m = re.search(r"Compressor Guarant\w*\s*(\d+\s*Years?)", text, re.I)
    og = soup.select_one('meta[property="og:image"]')
    return {"name": title.get_text(" ", strip=True) if title else None, "capacity": cap, "image": og.get("content") if og else None,
            "price": prices.get("finalPrice"), "regular": prices.get("oldPrice"),
            "in_stock": bool(stock and "in stock" in stock.get_text().lower()),
            "type": ("No-Frost" if cool and "non" in cool.lower() else ("Direct Cool" if cool else None)),
            "inverter": bool(re.search(r"inverter", (title.get_text() if title else ""), re.I)),
            "warranty": ("Compressor " + m.group(1)) if m else None}


def make_name(p: dict) -> str:
    n = re.sub(r"\s+", " ", p["name"] or "").strip()
    n = re.sub(r"^minister\b", "Minister", n, flags=re.I)
    n = re.sub(r"\s*(MATCH/FULL MATCH|FULL MATCH|MATCH)\s*$", "", n, flags=re.I)
    kind = "Freezer" if re.search(r"freezer", n, re.I) else "Refrigerator"
    extra = [f"{p['capacity']}L"] if p.get("capacity") and not re.search(rf"\b{p['capacity']}\s*L", n, re.I) else []
    if p.get("type") and kind == "Refrigerator":
        extra.append(p["type"])
    if not re.search(kind, n, re.I):
        extra.append(kind)
    return " ".join([n] + extra)


def scrape(url: str, max_pages: int = 1, delay: float = 5, limit=None) -> list[dict]:
    """url = https://ministerbd.com/sitemap.xml"""
    known = brand_specs.load("minister")  # url -> {"fridge": bool, ...}
    xml = fetch(url, delay)
    urls = [u for u in re.findall(r"<loc>\s*(.*?)\s*</loc>", xml) if u.endswith(".html") and u.count("/") == 3]
    urls = [u for u in urls if WANT.search(u.rsplit("/", 1)[-1]) and not SKIP.search(u.rsplit("/", 1)[-1].replace(".html", ""))
            and known.get(u, {}).get("fridge", True)]
    results = []
    for u in urls[:MAX_PAGES]:
        try:
            p = parse_product(fetch(u, delay))
        except Exception as e:
            print("minister:", u, e)
            continue
        is_fridge = bool(p.get("capacity")) and bool(re.search(r"refrigerator|freezer|fridge|\bm-\d", (p["name"] or "") + u, re.I))
        known[u] = {"fridge": is_fridge, "seen": date.today().isoformat(),
                    **({k: p[k] for k in ("capacity", "type", "inverter", "warranty")} if is_fridge else {})}
        if not is_fridge:
            continue
        results.append(offer(name=make_name(p), url=u, price=p["price"], regular=p["regular"] if p["regular"] != p["price"] else None,
                             in_stock=p["in_stock"] and bool(p["price"]), status="ok" if p["in_stock"] else "out", brand="Minister",
                             image=p.get("image")))
    brand_specs.save("minister", known)
    return results
