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


def save_logo(slug, home, html):
    for url in candidates(home, html):
        try:
            if not allowed(url):
                continue
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
            if not r.ok or len(r.content) < 200:
                continue
            if url.lower().split("?")[0].endswith(".svg") or b"<svg" in r.content[:600]:
                if len(r.content) > 200_000:
                    continue
                (OUT / f"{slug}.svg").write_bytes(r.content)
                return f"{slug}.svg"
            im = Image.open(io.BytesIO(r.content)).convert("RGBA")
            if im.width < 48 or im.height < 20:
                continue
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
            print(f"{slug:14} হোমপেজ খোলেনি ({type(e).__name__})", flush=True)
            continue
        m = meta.get(slug, {})
        logo = save_logo(slug, home + "/", html)
        if logo:
            m["logo"] = logo
        m.update(socials(home + "/", html))
        meta[slug] = m
        print(f"{slug:14} লোগো: {m.get('logo', '—'):14} | " + ", ".join(k for k in SOCIAL if k in m), flush=True)
    mf.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(f"মোট {len(meta)} ব্র্যান্ড | লোগো {sum(1 for v in meta.values() if v.get('logo'))} | ফেসবুক {sum(1 for v in meta.values() if v.get('facebook'))}")


if __name__ == "__main__":
    main(sys.argv[1:])
