"""Walton (waltonbd.com, নিজস্ব অফিসিয়াল সাইট) — ফ্রিজ/ফ্রিজার।
তালিকার পাতায় শুধু মডেল কোড আর দাম থাকে; সাইজ (লিটার), ধরন আর কম্প্রেসর ওয়ারেন্টি প্রোডাক্ট পাতা থেকে
একবার এনে data/brand_specs/walton.json-এ রাখা হয় (৩০ দিন পর আবার যাচাই)।"""
import re

from bs4 import BeautifulSoup

from scraper import brand_specs
from scraper.common import fetch, offer, parse_price

MAX_NEW_SPECS = 150  # এক রানে সর্বোচ্চ কতগুলো নতুন প্রোডাক্ট পাতা খোলা হবে


def parse_list(html: str) -> tuple[list[dict], bool]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select(".single-prodcut"):
        a = card.select_one("h6 a")
        if not a or not a.get("href"):
            continue
        prices = [parse_price(re.sub(r"Tk\.?|BDT", "", p.get_text())) for p in card.select(".price-area p, .price-area span")]
        prices = [p for p in prices if p]
        items.append({"model": a.get_text(" ", strip=True), "url": a["href"].split("?")[0],
                      "price": min(prices) if prices else None, "regular": max(prices) if len(prices) > 1 else None,
                      "image": (card.select_one("img") or {}).get("src")})
    nxt = bool(soup.select(".pagination a"))
    return items, nxt


def parse_product(html: str) -> dict:
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    spec = {}
    m = re.search(r"Gross Volume\s*:?\s*(\d{2,4}(?:\.\d)?)\s*L", text, re.I)
    if m:
        spec["capacity"] = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
    m = re.search(r"Net Volume\s*:?\s*(\d{2,4})\s*L", text, re.I)
    if m:
        spec["net"] = int(m.group(1))
    m = re.search(r"Type\s*:?\s*(No-?Frost|Non-?Frost|Direct Cool|Frost)", text, re.I)
    if m:
        spec["type"] = "No-Frost" if "no" in m.group(1).lower() or "non" in m.group(1).lower() else m.group(1).title()
    spec["inverter"] = bool(re.search(r"inverter", text, re.I))
    m = re.search(r"Compressor\)?\s*:?\s*(\d+\s*Years?)", text, re.I)
    if m:
        spec["warranty"] = "Compressor " + m.group(1)
    return spec


def make_name(model: str, spec: dict, kind: str) -> str:
    parts = ["Walton", model]
    if spec.get("capacity"):
        parts.append(f"{spec['capacity']}L")
    if spec.get("type"):
        parts.append(spec["type"])
    if spec.get("inverter"):
        parts.append("Inverter")
    parts.append(kind)
    return " ".join(parts)


def scrape(url: str, max_pages: int = 5, delay: float = 5, limit=None) -> list[dict]:
    specs = brand_specs.load("walton")
    kind = "Freezer" if "freezer" in url else "Refrigerator"
    results, new = [], 0
    for page in range(1, max_pages + 1):
        rows, nxt = parse_list(fetch(f"{url}?limit=100" + (f"&page={page}" if page > 1 else ""), delay))
        for r in rows:
            sp = specs.get(r["url"])
            if not brand_specs.fresh(sp) and new < MAX_NEW_SPECS:
                try:
                    sp = parse_product(fetch(r["url"], delay))
                    sp["seen"] = __import__("datetime").date.today().isoformat()
                    specs[r["url"]] = sp
                    new += 1
                except Exception as e:  # একটা পাতা না খুললে বাকিগুলো চলবে
                    print("walton spec:", r["url"], e)
            sp = sp or {}
            results.append(offer(name=make_name(r["model"], sp, kind), url=r["url"], price=r["price"],
                                 regular=r["regular"], in_stock=bool(r["price"]), status="ok" if r["price"] else "no_price",
                                 image=r["image"], brand="Walton"))
        if not rows or not nxt or len(rows) < 100:
            break
    brand_specs.save("walton", specs)
    return results
