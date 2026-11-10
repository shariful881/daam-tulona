"""Star Tech (startech.com.bd) — ক্যাটাগরি পেজের প্রোডাক্ট কার্ড থেকে দাম তোলে।"""
from bs4 import BeautifulSoup

from scraper.common import fetch, offer, parse_price

STATUS_WORDS = {
    "out of stock": "out",
    "pre order": "pre",
    "up coming": "upcoming",
    "upcoming": "upcoming",
    "call for price": "no_price",
}


def parse_page(html: str) -> tuple[list[dict], bool]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select(".p-item"):
        link = card.select_one(".p-item-name a")
        if not link:
            continue
        price_box = card.select_one(".p-item-price")
        new = price_box.select_one(".price-new") if price_box else None
        old = price_box.select_one(".price-old") if price_box else None
        if new:
            price, regular = parse_price(new.get_text()), parse_price(old.get_text() if old else None)
        else:
            price, regular = parse_price(price_box.get_text() if price_box else None), None

        actions = card.select_one(".actions")
        action_text = actions.get_text(" ", strip=True).lower() if actions else ""
        status = "ok"
        for word, code in STATUS_WORDS.items():
            if word in action_text or (price_box and word in price_box.get_text(" ", strip=True).lower()):
                status = code
                break
        in_stock = status == "ok" and card.select_one(".btn-add-cart") is not None

        img = card.select_one(".p-item-img img")
        items.append(offer(
            name=link.get_text(" ", strip=True),
            url=link["href"].split("?")[0],
            price=price, regular=regular, in_stock=in_stock, status=status,
            image=img.get("src") if img else None,
        ))
    has_next = any(a.get_text(strip=True).upper() == "NEXT" for a in soup.select("ul.pagination a"))
    return items, has_next


def scrape(url: str, max_pages: int = 5, delay: float = 3) -> list[dict]:
    results = []
    for page in range(1, max_pages + 1):
        page_url = url if page == 1 else f"{url}?page={page}"
        items, has_next = parse_page(fetch(page_url, delay))
        results.extend(items)
        if not has_next or not items:
            break
    return results
