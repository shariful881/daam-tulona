"""PC House (pchouse.com.bd) — ক্যাটাগরি পেজের প্রোডাক্ট কার্ড থেকে দাম তোলে।"""
from bs4 import BeautifulSoup

from scraper.common import fetch, offer, parse_price

STATUS_WORDS = {"out of stock": "out", "pre order": "pre", "up coming": "upcoming", "upcoming": "upcoming", "call for price": "no_price"}


def parse_page(html: str) -> tuple[list[dict], bool]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select(".single-product-item"):
        link = card.select_one(".product-item-info h4 a") or card.select_one("h4 a")
        if not link:
            continue
        buy = card.select_one(".product-buy-info")
        special = (buy.select_one("span.special-price") or buy.select_one("span.price")) if buy else None
        regular_el = buy.select_one("span.regular-price") if buy else None
        price = parse_price(special.get_text() if special else None)
        regular = parse_price(regular_el.get_text() if regular_el else None)
        if price is None and regular is not None:
            price, regular = regular, None
        text = buy.get_text(" ", strip=True).lower() if buy else ""
        status = next((code for word, code in STATUS_WORDS.items() if word in text), "ok")
        btn = card.select_one(".buy-btn")
        in_stock = status == "ok" and btn is not None and not btn.has_attr("disabled")
        img = card.select_one("img")
        items.append(offer(
            name=link.get_text(" ", strip=True), url=link["href"].split("?")[0],
            price=price, regular=regular, in_stock=in_stock, status=status,
            image=img.get("src") if img else None,
        ))
    has_next = any(a.get_text(strip=True) in (">", "›", "Next", "NEXT") for a in soup.select("ul.pagination a"))
    return items, has_next


def scrape(url: str, max_pages: int = 5, delay: float = 5) -> list[dict]:
    results = []
    for page in range(1, max_pages + 1):
        items, has_next = parse_page(fetch(url if page == 1 else f"{url}?page={page}", delay))
        results.extend(items)
        if not items or not has_next:
            break
    return results
