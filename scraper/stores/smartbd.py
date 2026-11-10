"""Smart Technologies (smartbd.com) — WooCommerce ক্যাটাগরি পেজ। পরের পাতা /page/2/ আকারে।"""
from bs4 import BeautifulSoup

from scraper.common import fetch, offer, parse_price


def parse_page(html: str) -> tuple[list[dict], bool]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select(".product-block"):
        link = card.select_one("h3.name a")
        if not link:
            continue
        price_el = card.select_one(".price")
        ins = price_el.select_one("ins .woocommerce-Price-amount") if price_el else None
        dels = price_el.select_one("del .woocommerce-Price-amount") if price_el else None
        amt = price_el.select_one(".woocommerce-Price-amount") if price_el else None
        if ins:
            price, regular = parse_price(ins.get_text()), parse_price(dels.get_text() if dels else None)
        else:
            price, regular = parse_price(amt.get_text() if amt else None), None
        text = card.get_text(" ", strip=True).lower()
        status = "out" if ("sold out" in text or "out of stock" in text) else ("no_price" if "call for price" in text or not price else "ok")
        img = card.select_one("img")
        items.append(offer(
            name=link.get_text(" ", strip=True), url=link["href"],
            price=price, regular=regular, in_stock=status == "ok", status=status,
            image=(img.get("data-src") or img.get("src")) if img else None,
        ))
    has_next = soup.select_one("a.next.page-numbers") is not None
    return items, has_next


def scrape(url: str, max_pages: int = 5, delay: float = 5) -> list[dict]:
    base = url.rstrip("/") + "/"
    results = []
    for page in range(1, max_pages + 1):
        items, has_next = parse_page(fetch(base if page == 1 else f"{base}page/{page}/", delay))
        results.extend(items)
        if not items or not has_next:
            break
    return results
