"""Apple Gadgets (applegadgetsbd.com) — ক্যাটাগরি পেজের প্রোডাক্ট কার্ড।
robots.txt '?' দেওয়া সব ঠিকানা নিষেধ করে, তাই শুধু প্রথম পাতা (সাধারণত ১৮টি জনপ্রিয় প্রোডাক্ট)।"""
from urllib.parse import unquote, urljoin

from bs4 import BeautifulSoup

from scraper.common import fetch, offer, parse_price

BASE = "https://www.applegadgetsbd.com"


def parse_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select("article"):
        a = card.select_one('a[href^="/product/"]')
        name = card.select_one("p")
        if not a or not name:
            continue
        spans = card.select("span")
        price = regular = None
        for sp in spans:
            t = sp.get_text("", strip=True)
            if "৳" not in t:
                continue
            v = parse_price(t)
            if not v:
                continue
            if "line-through" in " ".join(sp.get("class") or []):
                regular = v
            elif price is None:
                price = v
        text = card.get_text(" ", strip=True).lower()
        status = "out" if "out of stock" in text or "stock out" in text else ("upcoming" if "up coming" in text or "upcoming" in text
                                                                               else ("ok" if price else "no_price"))
        img = card.select_one("img")
        src = img.get("src") if img else None
        if src and "url=" in src:  # Next.js-এর ছবির ঠিকানা থেকে আসল ছবি
            src = unquote(src.split("url=", 1)[1].split("&", 1)[0])
        items.append(offer(name=name.get_text(" ", strip=True), url=urljoin(BASE, a["href"]), price=price,
                           regular=regular if regular and price and regular > price else None,
                           in_stock=status == "ok", status=status, image=src))
    return items


def scrape(url: str, max_pages: int = 1, delay: float = 5) -> list[dict]:
    return parse_page(fetch(url, delay))
