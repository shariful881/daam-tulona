"""Tech Land BD (techlandbd.com) — ক্যাটাগরি পেজের প্রোডাক্ট কার্ড থেকে দাম, স্টক আর মূল ফিচার (প্রতি পাতায় ২০টা)।
robots.txt সব পাতা খোলা রাখে; ধীরে আর প্রতি ক্যাটাগরিতে কয়েক পাতা মাত্র।"""
from bs4 import BeautifulSoup

from scraper.common import fetch_page, offer, parse_price

STATUS_WORDS = {"out of stock": "out", "stock out": "out", "pre-order": "pre", "pre order": "pre", "up coming": "upcoming",
                "upcoming": "upcoming", "call for price": "no_price"}


def parse_page(html: str) -> tuple[list[dict], bool]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for title in soup.select("h2.v2-card-title"):
        link = title.find_parent("a")
        card = None
        for p in title.parents:
            if p.name == "div" and p.find("img") and p.select_one(".text-red-600, .line-through, button"):
                card = p
                break
        if not link or not link.get("href") or card is None:
            continue
        new = card.select_one(".text-red-600")
        old = card.select_one(".line-through")
        price = parse_price(new.get_text() if new else None)
        regular = parse_price(old.get_text() if old else None)
        if price is None and regular is not None:
            price, regular = regular, None
        low = card.get_text(" ", strip=True).lower()
        status = next((code for word, code in STATUS_WORDS.items() if word in low), "ok")
        img = card.find("img")
        feats = [li.get_text(" ", strip=True) for li in card.select("ul li")][:6]
        items.append(offer(
            name=title.get_text(" ", strip=True), url=link["href"].split("?")[0], price=price, regular=regular,
            in_stock=status == "ok" and price is not None, status=status,
            image=(img.get("src") or img.get("data-src")) if img else None,
            features=[f for f in feats if f] or None,
        ))
    has_next = "nextPage" in html
    return items, has_next


def scrape(url: str, max_pages: int = 3, delay: float = 6) -> list[dict]:
    results, seen = [], set()
    for page in range(1, max_pages + 1):
        html = fetch_page(url if page == 1 else f"{url}?page={page}", delay, page, results)
        if html is None:
            break
        items, has_next = parse_page(html)
        new = [i for i in items if i["url"] not in seen]
        seen.update(i["url"] for i in new)
        results.extend(new)
        if not new or not has_next:
            break
    return results
