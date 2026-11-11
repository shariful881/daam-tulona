"""সব স্টোরের স্ক্র্যাপারের জন্য সাধারণ কাজ: ভদ্রভাবে পেজ আনা, robots.txt মানা, দাম পড়া।"""
import re
import time
import urllib.robotparser
from urllib.parse import urlparse

import requests

USER_AGENT = (
    "Mozilla/5.0 (compatible; DaamTulonaBot/1.0; "
    "+https://github.com/shariful881/daam-tulona)"
)

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en,bn;q=0.8"})
_robots: dict[str, urllib.robotparser.RobotFileParser] = {}
_last_hit: dict[str, float] = {}
_cache: dict[str, str] = {}


class Blocked(Exception):
    """স্টোর রিকোয়েস্ট আটকে দিয়েছে (403/429 বা বট-যাচাই পেজ)।"""


def _robots_for(url: str) -> urllib.robotparser.RobotFileParser:
    host = urlparse(url).netloc
    if host not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = _session.get(f"https://{host}/robots.txt", timeout=30)
            rp.parse(r.text.splitlines() if r.ok else [])
        except requests.RequestException:
            rp.parse([])
        _robots[host] = rp
    return _robots[host]


def allowed(url: str) -> bool:
    return _robots_for(url).can_fetch(USER_AGENT, url)


def fetch(url: str, delay: float, cache: bool = True) -> str:
    """robots.txt মেনে, স্টোরভিত্তিক বিরতি রেখে পেজ আনে।"""
    if url in _cache:
        return _cache[url]
    if not allowed(url):
        raise PermissionError(f"robots.txt অনুমতি দেয় না: {url}")
    host = urlparse(url).netloc
    wait = _last_hit.get(host, 0) + delay - time.time()
    if wait > 0:
        time.sleep(wait)
    for attempt in range(3):  # ধীর সার্ভার বা সাময়িক 502/504-এর জন্য আবার চেষ্টা
        try:
            r = _session.get(url, timeout=(20, 90))
            if r.status_code in (500, 502, 504) and attempt < 2:
                time.sleep(30 * (attempt + 1))
                continue
            break
        except (requests.Timeout, requests.ConnectionError, requests.exceptions.ChunkedEncodingError):
            if attempt == 2:
                raise
            time.sleep(15 * (attempt + 1))
    _last_hit[host] = time.time()
    if r.status_code in (403, 429, 503) or "Just a moment..." in r.text[:3000]:
        raise Blocked(f"{r.status_code} {url}")
    r.raise_for_status()
    if (r.encoding or "").lower() in ("iso-8859-1", "latin-1") and "charset" not in r.headers.get("content-type", "").lower():
        r.encoding = "utf-8"  # charset না বললে requests ভুল করে latin-1 ধরে (×, ″ ভেঙে যায়)
    if cache:
        _cache[url] = r.text
    return r.text


def parse_price(text: str | None) -> int | None:
    """'7,200৳' বা '৳ 7200' থেকে 7200। শূন্য বা খালি হলে None।"""
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text.split(".")[0])
    if not digits:
        return None
    value = int(digits)
    return value if value > 0 else None


def offer(name, url, price, regular=None, in_stock=True, status="ok", image=None, brand=None, features=None):
    """সব স্টোরের ফলাফল একই আকারে।"""
    if regular is not None and price is not None and regular <= price:
        regular = None
    return {
        "name": " ".join(name.split()),
        "url": url,
        "price": price,
        "regular": regular,
        "in_stock": bool(in_stock and price),
        "status": status if price else ("no_price" if status == "ok" else status),
        "image": image,
        "brand": brand,
        **({"features": features} if features else {}),
    }


def fetch_page(url: str, delay: float, page: int, results: list):
    """পাতা-ধরে-ধরে তোলার জন্য: শেষ পাতার পরে 404 এলে None (থামো); মাঝপথে ব্লক হলে
    আগের পাতাগুলোর প্রোডাক্ট হারায় না, Blocked-এর সাথে partial হিসেবে যায়।"""
    try:
        return fetch(url, delay)
    except requests.HTTPError as e:
        if page > 1 and e.response is not None and e.response.status_code == 404:
            return None
        e.partial = results
        raise
    except Exception as e:
        e.partial = results
        raise
