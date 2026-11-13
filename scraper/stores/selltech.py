"""Selltech (selltech.com.bd) — ক্যাটাগরি পাতার কার্ড (cardsite)।
robots.txt-এ "/*?page=1" নিষেধ: এটা ?page=1, ?page=10–19, ?page=100… সবই ধরে, তাই সেসব পাতা বাদ।"""
from scraper.stores import cardsite

CONF = {"card": ".product-layout", "link": ".name a", "new": ".price-new", "old": ".price-old", "plain": ".price-normal"}


def parse_page(html):
    return cardsite.parse_page(html, CONF)


def scrape(url, max_pages=1, delay=6):
    return cardsite.scrape(url, max_pages, delay, CONF, skip_page=lambda p: p > 1 and str(p).startswith("1"))
