"""computervision — ক্যাটাগরি পাতার কার্ড (cardsite)।"""
from scraper.stores import cardsite

CONF = {"card": ".product-wrap", "link": ".name a", "new": ".price-new", "old": ".price-old", "plain": ".price-wrap .price"}


def parse_page(html):
    return cardsite.parse_page(html, CONF)


def scrape(url, max_pages=1, delay=6):
    return cardsite.scrape(url, max_pages, delay, CONF)
