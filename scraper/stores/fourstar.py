"""Four Star IT (fourstarit.com.bd) — পেজের schema.org ItemList (JSON-LD) থেকে দাম পড়ে।

robots.txt '?' যুক্ত সব লিংক (পরের পাতা সহ) নিষেধ করে, তাই শুধু প্রথম পাতা তোলা হয়।
"""
import json

from bs4 import BeautifulSoup

from scraper.common import fetch, offer, parse_price

AVAIL = {"InStock": "ok", "OutOfStock": "out", "PreOrder": "pre", "SoldOut": "out", "Discontinued": "out"}


def parse_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for sc in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(sc.string or "")
        except json.JSONDecodeError:
            continue
        nodes = data.get("@graph", [data]) if isinstance(data, dict) else data
        for node in nodes:
            if not isinstance(node, dict) or node.get("@type") != "ItemList":
                continue
            for el in node.get("itemListElement", []):
                prod = el.get("item") or {}
                off = prod.get("offers") or {}
                if isinstance(off, list):
                    off = off[0] if off else {}
                avail = str(off.get("availability", "")).rsplit("/", 1)[-1]
                status = AVAIL.get(avail, "ok")
                price = parse_price(str(off.get("price", "")))
                brand = prod.get("brand", {}).get("name") if isinstance(prod.get("brand"), dict) else None
                items.append(offer(
                    name=prod.get("name") or el.get("name", ""),
                    url=prod.get("url") or el.get("url"),
                    price=price, in_stock=status == "ok", status=status,
                    image=prod.get("image"), brand=brand,
                ))
    return items


def scrape(url: str, max_pages: int = 1, delay: float = 10) -> list[dict]:
    return parse_page(fetch(url, delay))
