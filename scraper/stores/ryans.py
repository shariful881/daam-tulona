"""Ryans Computers (ryans.com) — ক্যাটাগরি পেজের প্রোডাক্ট কার্ড থেকে দাম, স্টক আর মূল ফিচার।
robots.txt সব পাতা খোলা রাখে; ধীরে (store delay) আর প্রতি ক্যাটাগরিতে কয়েক পাতা মাত্র।"""
import re

from bs4 import BeautifulSoup

from scraper.common import fetch_page, offer, parse_price

STATUS_WORDS = {"out of stock": "out", "stock out": "out", "pre order": "pre", "pre-order": "pre", "up coming": "upcoming",
                "upcoming": "upcoming", "call for price": "no_price"}


def parse_page(html: str) -> tuple[list[dict], bool]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select(".category-single-product"):
        link = card.select_one(".list-view-text a") or card.select_one(".product-name a")
        if not link or not link.get("href"):
            continue
        name = link.get_text(" ", strip=True)
        name = re.sub(r"\s*Product Id:.*$", "", name).strip()
        pr = card.select_one(".pr-text")
        txt = pr.get_text(" ", strip=True) if pr else ""
        nums = [parse_price(x) for x in re.findall(r"Tk\.?\s?[\d,]+", txt)]
        nums = [n for n in nums if n]
        price = min(nums) if nums else None
        regular = max(nums) if len(nums) > 1 else None
        low = card.get_text(" ", strip=True).lower()
        status = next((code for word, code in STATUS_WORDS.items() if word in low), "ok")
        img = card.select_one("img.card-img-top") or card.find("img")
        feats = []
        for li in card.select(".category-info li"):
            k, sep, v = li.get_text(" ", strip=True).partition(" - ")
            if sep and v.strip():
                feats.append(f"{k.strip()}: {v.strip()}")
        items.append(offer(
            name=name, url=link["href"].split("?")[0], price=price, regular=regular,
            in_stock=status == "ok", status=status, image=img.get("src") if img else None,
            features=feats[:8] or None,
        ))
    has_next = bool(soup.select_one('a[rel="next"], ul.pagination a[aria-label*="Next"], li.page-item a[aria-label="Next »"]'))
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
        if not new:  # পাতার নম্বর-লিংক জাভাস্ক্রিপ্টে আসে, তাই নতুন প্রোডাক্ট না আসা পর্যন্ত পরের পাতা
            break
    return results
