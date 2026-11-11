"""প্রতিটা ব্র্যান্ডের অফিসিয়াল ওয়েবসাইট থেকে লোগো আর সোশ্যাল লিংক (ফেসবুক, ইউটিউব, ইনস্টাগ্রাম, লিংকডইন)।

সোশ্যাল লিংক শুধু ব্র্যান্ডের নিজের সাইটে দেওয়া লিংক থেকে নেওয়া হয়, তাই ভুয়া পেজ আসে না।
ফল: web/static/brands/<ব্র্যান্ড>.png|svg আর web/static/brands/meta.json
চালানো: python -m tools.fetch_brand_meta [ব্র্যান্ড ...]
"""
import io
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup
from PIL import Image

from scraper.common import USER_AGENT, allowed, fetch
from tools.fetch_logos import candidates

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web/static/brands"
SOCIAL = {
    "facebook": re.compile(r"^https?://(www\.|m\.|web\.)?facebook\.com/(?!sharer|share|dialog|plugins|tr\b|groups/|events/)[A-Za-z0-9.\-_]{3,}/?$"),
    "youtube": re.compile(r"^https?://(www\.)?youtube\.com/(@[\w.\-]+|c/[\w.\-]+|channel/[\w\-]+|user/[\w.\-]+)/?$"),
    "instagram": re.compile(r"^https?://(www\.)?instagram\.com/[A-Za-z0-9._]{2,}/?$"),
    "linkedin": re.compile(r"^https?://([a-z]{2,3}\.)?linkedin\.com/company/[\w\-]+/?$"),
}


def socials(home, html):
    soup = BeautifulSoup(html, "html.parser")
    found = {}
    for a in soup.find_all("a", href=True):
        h = urljoin(home, a["href"].strip()).split("?")[0]
        for k, rx in SOCIAL.items():
            if k not in found and rx.match(h):
                found[k] = h.rstrip("/")
    return found


WIKI = "https://en.wikipedia.org/api/rest_v1/page/summary/"
WIKI_TITLE = {"tp-link": "TP-Link", "hp": "HP Inc.", "lg": "LG Electronics", "amd": "AMD", "jbl": "JBL", "dji": "DJI", "benq": "BenQ",
              "a4tech": "A4Tech", "g-skill": "G.Skill", "western-digital": "Western Digital", "cooler-master": "Cooler Master",
              "zkteco": "ZKTeco", "msi": "Micro-Star International", "apple": "Apple Inc.", "samsung": "Samsung Electronics",
              "canon": "Canon Inc.", "epson": "Seiko Epson", "walton": "Walton Group", "sony": "Sony", "team": "Team Group",
              "adata": "ADATA", "uniview": "Uniview", "hikvision": "Hikvision", "dahua": "Dahua Technology", "haier": "Haier",
              "hisense": "Hisense", "sandisk": "SanDisk", "viewsonic": "ViewSonic", "gigabyte": "Gigabyte Technology",
              "corsair": "Corsair Gaming", "kingston": "Kingston Technology", "transcend": "Transcend Information",
              "brother": "Brother Industries", "tenda": "Tenda (company)", "lexar": "Lexar", "razer": "Razer Inc.", "seagate": "Seagate Technology"}


def wiki_logo(name):
    """উইকিপিডিয়ার কোম্পানি পাতার লোগো (ফাইলের নামে 'logo' থাকলে) — সবচেয়ে নির্ভরযোগ্য উৎস।"""
    for title in (name, f"{name} (company)", f"{name} Inc.", f"{name} Corporation"):
        try:
            if not allowed(WIKI + title):
                return None
            r = requests.get(WIKI + requests.utils.quote(title.replace(" ", "_")), headers={"User-Agent": USER_AGENT}, timeout=30)
            if not r.ok:
                continue
            d = r.json()
            if d.get("type") == "disambiguation":
                continue
            img = (d.get("originalimage") or {}).get("source") or ""
            if "logo" in img.lower() or "wordmark" in img.lower():
                return img
        except Exception:
            continue
    return None


def visible(im):
    """সাদা বা প্রায় স্বচ্ছ লোগো সাদা কার্ডে দেখা যায় না -> বাদ"""
    px = [p for p in im.convert("RGBA").resize((64, 64)).getdata() if p[3] > 60]
    if len(px) < 40:
        return False
    dark = sum(1 for r, g, b, a in px if (r + g + b) / 3 < 200)
    return dark / len(px) > 0.08


def save_logo(slug, home, html, name=""):
    urls = []
    w = wiki_logo(name or slug)
    if w:
        urls.append(w)
    soup = BeautifulSoup(html, "html.parser")  # বড় apple-touch-icon (ব্র্যান্ডের নিজস্ব চিহ্ন), তারপর হেডারের লোগো
    urls += [urljoin(home, l["href"]) for l in soup.find_all("link", rel=lambda r: r and "apple-touch-icon" in " ".join(r).lower()) if l.get("href")]
    for url in list(dict.fromkeys(urls + candidates(home, html))):
        try:
            if not allowed(url):
                continue
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
            if not r.ok or len(r.content) < 200:
                continue
            if url.lower().split("?")[0].endswith(".svg") or b"<svg" in r.content[:600]:
                if len(r.content) > 200_000:
                    continue
                if "wikipedia" not in url and "wikimedia" not in url:
                    continue  # সাইটের svg প্রায়ই CSS-এ রং পায়, আলাদা করলে সাদা/ফাঁকা দেখায়
                (OUT / f"{slug}.svg").write_bytes(r.content)
                return f"{slug}.svg"
            im = Image.open(io.BytesIO(r.content)).convert("RGBA")
            if im.width < 48 or im.height < 20 or not visible(im):
                continue
            if im.width / im.height > 6 or ("logo" not in url.lower() and "icon" not in url.lower() and "wiki" not in url):
                continue  # ব্যানার/স্ক্রিনশট নয়
            im.thumbnail((256, 256))
            im.save(OUT / f"{slug}.png", optimize=True)
            return f"{slug}.png"
        except Exception:
            continue
    return None


def main(only):
    info = json.loads((ROOT / "config/brands.json").read_text()).get("info", {})
    OUT.mkdir(parents=True, exist_ok=True)
    mf = OUT / "meta.json"
    meta = json.loads(mf.read_text()) if mf.exists() else {}
    for slug, inf in info.items():
        if only and slug not in only:
            continue
        home = (inf.get("website") or "").rstrip("/")
        if not home:
            continue
        try:
            html = fetch(home + "/", 3, cache=False)
        except Exception as e:
            print(f"{slug:14} হোমপেজ খোলেনি ({type(e).__name__}), শুধু উইকিপিডিয়া", flush=True)
            html = ""
        m = meta.get(slug, {})
        for old_ in OUT.glob(f"{slug}.*"):
            old_.unlink()
        m.pop("logo", None)
        logo = save_logo(slug, home + "/", html, WIKI_TITLE.get(slug) or inf.get("name") or slug.replace("-", " ").title())
        if logo:
            m["logo"] = logo
        m.update(socials(home + "/", html))
        meta[slug] = m
        print(f"{slug:14} লোগো: {m.get('logo', '—'):14} | " + ", ".join(k for k in SOCIAL if k in m), flush=True)
    mf.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(f"মোট {len(meta)} ব্র্যান্ড | লোগো {sum(1 for v in meta.values() if v.get('logo'))} | ফেসবুক {sum(1 for v in meta.values() if v.get('facebook'))}")


if __name__ == "__main__":
    main(sys.argv[1:])
