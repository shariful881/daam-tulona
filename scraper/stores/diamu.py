"""Diamu (diamu.com.bd) — WooCommerce (Flatsome থিম) ক্যাটাগরি পেজ। পরের পাতা /page/2/ (robots.txt '?' নিষেধ করে, এটা নয়)।"""
from bs4 import BeautifulSoup

from scraper.common import fetch, offer, parse_price, fetch_page


def parse_page(html: str) -> tuple[list[dict], bool]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select("div.product-small.product, li.product"):
        link = card.select_one(".woocommerce-loop-product__title a, .product-title a")
        if not link:
            continue
        pe = card.select_one(".price")
        ins = pe.select_one("ins .woocommerce-Price-amount") if pe else None
        dl = pe.select_one("del .woocommerce-Price-amount") if pe else None
        amts = [parse_price(a.get_text()) for a in (pe.select(".woocommerce-Price-amount") if pe else [])]
        amts = [a for a in amts if a]
        if ins:
            price, regular = parse_price(ins.get_text()), parse_price(dl.get_text() if dl else None)
        else:
            price, regular = (min(amts) if amts else None), None  # ভ্যারিয়েশনে রেঞ্জ থাকলে কম দামটা
        cls = card.get("class") or []
        status = "out" if "outofstock" in cls else ("ok" if price else "no_price")
        img = card.select_one("img")
        items.append(offer(name=link.get_text(" ", strip=True), url=link["href"].split("?")[0], price=price, regular=regular,
                           in_stock=status == "ok", status=status,
                           image=(img.get("data-src") or img.get("src")) if img else None))
    has_next = soup.select_one("a.next.page-numbers") is not None or bool(soup.select('a.page-number[href*="/page/"]'))
    return items, has_next


def scrape(url: str, max_pages: int = 5, delay: float = 5) -> list[dict]:
    base = url.rstrip("/") + "/"
    results, seen = [], set()
    for page in range(1, max_pages + 1):
        html = fetch_page(base if page == 1 else f"{base}page/{page}/", delay, page, results)
        if html is None:
            break
        items, has_next = parse_page(html)
        new = [i for i in items if i["url"] not in seen]
        seen.update(i["url"] for i in new)
        results.extend(new)
        if not new or not has_next:
            break
    return results
