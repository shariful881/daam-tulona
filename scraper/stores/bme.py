"""BME (bme.com.bd) — ক্যাটাগরি পাতার কার্ড (cardsite)।"""
from scraper.stores import cardsite

CONF = {"card": ".product-box-2", "link": ".product-title a", "plain": ".product-price"}


def parse_page(html):
    return cardsite.parse_page(html, CONF)


def scrape(url, max_pages=1, delay=6):
    return cardsite.scrape(url, max_pages, delay, CONF)
