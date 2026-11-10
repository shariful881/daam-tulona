"""প্রতিটা স্টোরের হোমপেজ থেকে তাদের লোগো খুঁজে web/static/logos/<id>.png হিসেবে রাখে।

খোঁজার ক্রম: 'logo' নামের <img> → og:image নয় (ওটা সাধারণত ব্যানার) → apple-touch-icon → favicon।
লোগো না পেলে সাইটে আগের মতো স্টোরের নামের আদ্যক্ষর দেখাবে।

চালানো: python -m tools.fetch_logos
"""
import io
import json
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from PIL import Image

from scraper.common import USER_AGENT, fetch

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web/static/logos"


def candidates(home: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for img in soup.find_all("img"):
        attrs = " ".join([img.get("src", ""), img.get("alt", ""), " ".join(img.get("class", [])), img.get("id", "")]).lower()
        src = img.get("src") or img.get("data-src")
        if src and "logo" in attrs and not src.startswith("data:"):
            urls.append(urljoin(home, src))
    for rel in ("apple-touch-icon", "icon", "shortcut icon"):
        for link in soup.find_all("link", rel=lambda r: r and rel in " ".join(r).lower()):
            if link.get("href"):
                urls.append(urljoin(home, link["href"]))
    urls.append(urljoin(home, "/favicon.ico"))
    return list(dict.fromkeys(urls))


def main():
    stores = json.loads((ROOT / "config/stores.json").read_text())["stores"]
    OUT.mkdir(parents=True, exist_ok=True)
    found = {}
    for sid, st in stores.items():
        if not st["enabled"]:
            continue
        try:
            html = fetch(st["home"] + "/", 3)
        except Exception as e:
            print(sid, "হোমপেজ খোলেনি:", e)
            continue
        for url in candidates(st["home"] + "/", html):
            try:
                r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
                if not r.ok or len(r.content) < 200:
                    continue
                if url.lower().endswith(".svg") or b"<svg" in r.content[:500]:
                    (OUT / f"{sid}.svg").write_bytes(r.content)
                    found[sid] = f"logos/{sid}.svg"
                    break
                im = Image.open(io.BytesIO(r.content))
                im = im.convert("RGBA")
                if im.width < 32 or im.height < 16:
                    continue
                im.thumbnail((240, 96))
                im.save(OUT / f"{sid}.png", optimize=True)
                found[sid] = f"logos/{sid}.png"
                break
            except Exception:
                continue
        print(sid, "→", found.get(sid, "পাওয়া যায়নি"), flush=True)
    (OUT / "logos.json").write_text(json.dumps(found, indent=1))


if __name__ == "__main__":
    main()
