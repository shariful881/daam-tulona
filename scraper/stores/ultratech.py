"""UltraTech (ultratech.com.bd) — OpenCart ক্যাটাগরি পেজ। robots.txt-এ Crawl-Delay 20 সেকেন্ড।"""
from bs4 import BeautifulSoup

from scraper.common import fetch, offer, parse_price


def parse_page(html: str) -> tuple[list[dict], bool]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select(".product-layout"):
        link = card.select_one(".name a")
        if not link:
            continue
        pbox = card.select_one(".price")
        new = pbox.select_one(".price-new") if pbox else None
        old = pbox.select_one(".price-old") if pbox else None
        normal = pbox.select_one(".price-normal") if pbox else None
        if new:
            price, regular = parse_price(new.get_text()), parse_price(old.get_text() if old else None)
        else:
            price, regular = parse_price(normal.get_text() if normal else None), None

        text = card.get_text(" ", strip=True).lower()
        classes = " ".join(card.get("class", []))
        status = "ok"
        if "out of stock" in text or "out-of-stock" in classes:
            status = "out"
        elif "pre order" in text or "pre-order" in text:
            status = "pre"
        elif "has-zero-price" in classes or not price:
            status = "no_price"
        img = card.select_one("img")
        items.append(offer(
            name=link.get_text(" ", strip=True),
            url=link["href"].split("?")[0],
            price=price, regular=regular, in_stock=status == "ok", status=status,
            image=img.get("src") if img else None,
        ))
    nxt = [a for a in soup.select("ul.pagination a") if a.get_text(strip=True) in (">", "›", "Next")]
    return items, bool(nxt)


def scrape(url: str, max_pages: int = 3, delay: float = 20) -> list[dict]:
    results = []
    for page in range(1, max_pages + 1):
        page_url = url if page == 1 else f"{url}?page={page}"
        items, has_next = parse_page(fetch(page_url, delay))
        results.extend(items)
        if not items or not has_next:
            break
    return results
