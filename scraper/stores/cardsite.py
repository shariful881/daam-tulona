"""সাধারণ "ক্যাটাগরি পাতার প্রোডাক্ট কার্ড" স্ক্র্যাপার — নতুন ছোট স্টোরগুলোর জন্য (Computer Vision, Eerna, PQS, BME, Selltech)।
প্রতিটা স্টোরের মডিউল শুধু CONF (কোন ঘরে নাম/দাম) দেয়। শুধু নাম, লিংক, দাম, স্টক নেওয়া হয়; ছবি বা লেখা নয়।"""
import re

from bs4 import BeautifulSoup

from scraper.common import fetch_page, offer, parse_price

STATUS_WORDS = {"out of stock": "out", "stock out": "out", "pre order": "pre", "pre-order": "pre", "up coming": "upcoming",
                "upcoming": "upcoming", "coming soon": "upcoming", "call for price": "no_price"}


def parse_page(html, conf):
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select(conf["card"]):
        link = card.select_one(conf["link"])
        if not link or not link.get("href"):
            continue
        name = " ".join(link.get_text(" ", strip=True).split())
        if not name:
            continue
        new = card.select_one(conf["new"]) if conf.get("new") else None
        old = card.select_one(conf["old"]) if conf.get("old") else None
        price = parse_price(new.get_text(" ", strip=True)) if new else None
        regular = parse_price(old.get_text(" ", strip=True)) if old else None
        if price is None and conf.get("plain"):
            el = card.select_one(conf["plain"])
            price = parse_price(el.get_text(" ", strip=True)) if el else None
        if price is None and regular:  # ছাড় নেই: পুরনো দামের ঘরেই আসল দাম
            price, regular = regular, None
        if not price:  # ৳0 = দাম নেই (আপকামিং/কল ফর প্রাইস)
            price = None
        if regular and price and regular <= price:
            regular = None
        text = card.get_text(" ", strip=True).lower()
        status = next((code for word, code in STATUS_WORDS.items() if word in text), "ok" if price else "no_price")
        in_stock = status == "ok" and price is not None
        url = link["href"].strip()
        if "?" in url and not re.search(r"[?&](product_id|id)=", url):  # ট্র্যাকিং বাদ, কিন্তু id-ওয়ালা লিংক রাখা
            url = url.split("?")[0]
        items.append(offer(name=name, url=url, price=price, regular=regular,
                           in_stock=in_stock, status=status, image=None))
    nxt = [a for a in soup.select(conf.get("pager", "ul.pagination a, .pagination a"))
           if a.get_text(strip=True) in (">", "›", "»", "Next", "NEXT", "next")]
    return items, bool(nxt)


def scrape(url, max_pages, delay, conf, skip_page=None):
    results, seen = [], set()
    for page in range(1, max_pages + 1):
        if skip_page and skip_page(page):  # robots.txt যে পাতা নিষেধ করে
            continue
        html = fetch_page(url if page == 1 else f"{url}{'&' if '?' in url else '?'}page={page}", delay, page, results)
        if html is None:
            break
        items, has_next = parse_page(html, conf)
        new = [i for i in items if i["url"] not in seen]
        seen.update(i["url"] for i in new)
        results.extend(new)
        if not new or not has_next:
            break
    return results
