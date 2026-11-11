"""ব্র্যান্ডের লোগো আর অফিসিয়াল সোশ্যাল লিংক (ফেসবুক, ইউটিউব, ইনস্টাগ্রাম, লিংকডইন)।

লোগোর উৎস (আগেরটা না পেলে পরেরটা):
  ১. উইকিপিডিয়ায় কোম্পানির পাতার তথ্যবাক্সের লোগো — শুধু তখনই, যখন সেই পাতার "Website" ব্র্যান্ডের অফিসিয়াল সাইটের সাথে মেলে
     (তাই একই নামের অন্য কিছুর লোগো আসে না)
  ২. ব্র্যান্ডের নিজের সাইটের apple-touch-icon / হেডারের লোগো
প্রতিটা ছবি যাচাই হয়: খোলে কিনা, যথেষ্ট বড় কিনা, সাদা কার্ডে দেখা যায় কিনা, ব্যানার/স্ক্রিনশট নয় তো।
সোশ্যাল লিংক শুধু ব্র্যান্ডের নিজের সাইটে দেওয়া লিংক থেকে, তাই ভুয়া পেজ আসে না।

ফল: web/static/brands/<ব্র্যান্ড>.png|svg, meta.json, report.json (অ্যাডমিন প্যানেলে দেখায়)
চালানো:
  python -m tools.fetch_brand_meta            সব ব্র্যান্ড নতুন করে
  python -m tools.fetch_brand_meta asus hp    নির্দিষ্ট ব্র্যান্ড
  python -m tools.fetch_brand_meta --check    মাসিক পরীক্ষা: যার লোগো নেই/ভাঙা শুধু সেগুলো ঠিক করার চেষ্টা, বাকিগুলো ছোঁয় না
"""
import io
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup
from PIL import Image

from scraper.common import USER_AGENT, allowed, fetch
from tools.fetch_logos import candidates

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web/static/brands"
BD = timezone(timedelta(hours=6))
SOCIAL = {
    "facebook": re.compile(r"^https?://(www\.|m\.|web\.)?facebook\.com/(?!sharer|share|dialog|plugins|tr\b|groups/|events/)[A-Za-z0-9.\-_]{3,}/?$"),
    "youtube": re.compile(r"^https?://(www\.)?youtube\.com/(@[\w.\-]+|c/[\w.\-]+|channel/[\w\-]+|user/[\w.\-]+)/?$"),
    "instagram": re.compile(r"^https?://(www\.)?instagram\.com/[A-Za-z0-9._]{2,}/?$"),
    "linkedin": re.compile(r"^https?://([a-z]{2,3}\.)?linkedin\.com/company/[\w\-]+/?$"),
}
# উইকিপিডিয়ার পাতার নাম যেখানে ব্র্যান্ডের নাম থেকে আলাদা
WIKI_TITLE = {"tp-link": "TP-Link", "hp": "HP Inc.", "lg": "LG Electronics", "amd": "AMD", "jbl": "JBL", "dji": "DJI", "benq": "BenQ",
              "a4tech": "A4Tech", "g-skill": "G.Skill", "western-digital": "Western Digital", "cooler-master": "Cooler Master",
              "zkteco": "ZKTeco", "msi": "Micro-Star International", "apple": "Apple Inc.", "samsung": "Samsung", "toshiba": "Toshiba", "g-skill": "G.Skill", "vention": "Vention",
              "canon": "Canon Inc.", "epson": "Seiko Epson", "walton": "Walton Group", "sony": "Sony", "team": "TeamGroup",
              "adata": "ADATA", "uniview": "Uniview", "hikvision": "Hikvision", "dahua": "Dahua Technology", "haier": "Haier",
              "hisense": "Hisense", "sandisk": "SanDisk", "viewsonic": "ViewSonic", "gigabyte": "Gigabyte Technology",
              "corsair": "Corsair Gaming", "kingston": "Kingston Technology", "transcend": "Transcend Information",
              "brother": "Brother Industries", "tenda": "Tenda (company)", "lexar": "Lexar", "razer": "Razer Inc.",
              "seagate": "Seagate Technology", "asus": "Asus", "dell": "Dell", "lenovo": "Lenovo", "xiaomi": "Xiaomi",
              "intel": "Intel", "microsoft": "Microsoft", "logitech": "Logitech", "philips": "Philips", "casio": "Casio",
              "anker": "Anker Innovations", "edifier": "Edifier", "baseus": "Baseus", "ugreen": "Ugreen", "deepcool": "DeepCool",
              "netac": "Netac", "apacer": "Apacer", "oraimo": "Oraimo", "redragon": "Redragon", "vention": "Vention",
              "grandstream": "Grandstream Networks", "antec": "Antec", "gamdias": "Gamdias", "minister": "Minister Hi-Tech Park"}


def domain(u):
    h = urlsplit(u if "//" in u else "https://" + u).netloc.lower().split(":")[0]
    h = h[4:] if h.startswith("www.") else h
    parts = h.split(".")
    return ".".join(parts[-3:] if len(parts) > 2 and parts[-2] in ("com", "co", "net", "org") else parts[-2:])


def socials(home, html):
    soup = BeautifulSoup(html, "html.parser")
    found = {}
    for a in soup.find_all("a", href=True):
        h = urljoin(home, a["href"].strip()).split("?")[0]
        for k, rx in SOCIAL.items():
            if k not in found and rx.match(h):
                found[k] = h.rstrip("/")
    return found


def wiki_logo(titles, website, slug=""):
    """উইকিপিডিয়ার কোম্পানি পাতার তথ্যবাক্সের লোগো; পাতার Website অফিসিয়াল সাইটের সাথে না মিললে নেওয়া হয় না।"""
    if not website:
        return None
    want = domain(website)
    key = re.sub(r"[^a-z0-9]", "", slug)
    for title in dict.fromkeys(t for t in titles if t):
        try:
            html = fetch("https://en.wikipedia.org/wiki/" + quote(title.replace(" ", "_")), 2, cache=False)
        except Exception as e:
            print(f"    উইকি '{title}': খোলেনি ({type(e).__name__})")
            continue
        soup = BeautifulSoup(html, "html.parser")
        box = soup.select_one("table.infobox")
        if not box:
            print(f"    উইকি '{title}': তথ্যবাক্স নেই")
            continue
        doms = {domain(a.get("href", "")) for a in box.select("a[href^='http'], a[href^='//']") if "wiki" not in a.get("href", "")}
        if want not in doms and not (key and any(key in d.replace(".", "").replace("-", "") for d in doms)):
            print(f"    উইকি '{title}': ওয়েবসাইট মেলেনি ({', '.join(sorted(doms))[:80]})")
            continue
        imgs = box.find_all("img")
        first = [i for i in box.select(".infobox-image img, .infobox-above img")[:1]]
        for img in [i for i in imgs if re.search(r"logo|wordmark", i.get("src", ""), re.I)] + first:
            src = img.get("src") or ""
            src = "https:" + src if src.startswith("//") else src
            if re.search(r"headquarter|building|office|\.jpe?g", src, re.I):
                continue
            return re.sub(r"/(\d+)px-", "/330px-", src)
        print(f"    উইকি '{title}': লোগোর ছবি নেই")
    return None


def visible(im):
    """সাদা বা প্রায় স্বচ্ছ লোগো সাদা কার্ডে দেখা যায় না"""
    px = [p for p in im.convert("RGBA").resize((64, 64)).getdata() if p[3] > 60]
    if len(px) < 40:
        return False
    dark = sum(1 for r, g, b, a in px if (r + g + b) / 3 < 200)
    return dark / len(px) > 0.08


def check_file(slug, name):
    """লোগো ফাইল ঠিক আছে কিনা: (ঠিক, কারণ)"""
    f = OUT / name if name else None
    if not f or not f.exists():
        return False, "ফাইল নেই"
    if f.suffix == ".svg":
        t = f.read_text(errors="ignore")
        return ("<svg" in t[:2000] and len(t) > 200), "svg ভাঙা"
    try:
        im = Image.open(f)
        im.load()
    except Exception:
        return False, "ছবি খোলে না"
    if im.width < 48 or im.height < 20:
        return False, "খুব ছোট"
    if not visible(im):
        return False, "সাদা কার্ডে দেখা যায় না"
    return True, ""


def save_from(slug, url, trusted):
    """একটা ঠিকানা থেকে লোগো নামিয়ে যাচাই করে রাখা; ফেরত ফাইলের নাম বা None"""
    try:
        if not allowed(url):
            return None
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        if not r.ok or len(r.content) < 200:
            return None
        if url.lower().split("?")[0].endswith(".svg") or b"<svg" in r.content[:600]:
            return None  # সাইটের svg সাধারণত CSS থেকে রং পায়, আলাদা করলে সাদা/ফাঁকা দেখায়
        im = Image.open(io.BytesIO(r.content)).convert("RGBA")
        if im.width < 48 or im.height < 20 or not visible(im):
            return None
        if im.width / im.height > 7:
            return None  # ব্যানার
        if not trusted and not re.search(r"logo|icon", url, re.I):
            return None  # সাইটের যেকোনো ছবি নয়
        im.thumbnail((330, 330))
        for old in OUT.glob(f"{slug}.*"):
            old.unlink()
        im.save(OUT / f"{slug}.png", optimize=True)
        return f"{slug}.png"
    except Exception:
        return None


def find_logo(slug, inf, html):
    home = (inf.get("website") or "").rstrip("/") + "/"
    nm = inf.get("name") or slug.replace("-", " ").title()
    w = wiki_logo([WIKI_TITLE.get(slug), nm, f"{nm} (company)", f"{nm} Corporation", f"{nm} Group"], inf.get("website"), slug)
    if w:
        got = save_from(slug, w, trusted=True)
        if got:
            return got, "উইকিপিডিয়া"
    if html:
        soup = BeautifulSoup(html, "html.parser")
        urls = [urljoin(home, l["href"]) for l in soup.find_all("link", rel=lambda r: r and "apple-touch-icon" in " ".join(r).lower()) if l.get("href")]
        for u in dict.fromkeys(urls + candidates(home, html)):
            got = save_from(slug, u, trusted=u in urls)
            if got:
                return got, "অফিসিয়াল সাইট"
    return None, None


def main(argv):
    check = "--check" in argv
    only = [a for a in argv if not a.startswith("--")]
    info = json.loads((ROOT / "config/brands.json").read_text()).get("info", {})
    OUT.mkdir(parents=True, exist_ok=True)
    mf = OUT / "meta.json"
    meta = json.loads(mf.read_text()) if mf.exists() else {}
    rep = {"date": datetime.now(BD).date().isoformat(), "mode": "check" if check else "full", "ok": [], "fixed": [], "missing": []}
    for slug, inf in info.items():
        if only and slug not in only:
            continue
        m = meta.setdefault(slug, {})
        if inf.get("logo"):  # config-এ হাতে বসানো লোগো
            ok, why = check_file(slug, inf["logo"]) if not inf["logo"].startswith("http") else (True, "")
            (rep["ok"] if ok else rep["missing"]).append({"slug": slug, "why": why, "src": "হাতে বসানো"})
            continue
        if check:
            ok, why = check_file(slug, m.get("logo"))
            if ok:
                rep["ok"].append({"slug": slug, "src": m.get("logo_src", "")})
                continue
        html = ""
        if inf.get("website"):
            try:
                html = fetch(inf["website"].rstrip("/") + "/", 3, cache=False)
            except Exception as e:
                print(f"{slug:14} হোমপেজ খোলেনি ({type(e).__name__})", flush=True)
        logo, src = find_logo(slug, inf, html)
        if logo:
            m["logo"], m["logo_src"] = logo, src
            rep["fixed" if check else "ok"].append({"slug": slug, "src": src, "was": "ভাঙা/ছিল না" if check else ""})
        else:
            if not check:
                m.pop("logo", None)
                m.pop("logo_src", None)
            ok, why = check_file(slug, m.get("logo"))
            if not ok:
                m.pop("logo", None)
                rep["missing"].append({"slug": slug, "why": "উইকিপিডিয়া বা অফিসিয়াল সাইটে ব্যবহারযোগ্য লোগো পাওয়া যায়নি"})
        if html:
            m.update(socials(inf["website"].rstrip("/") + "/", html))
        print(f"{slug:16} লোগো: {m.get('logo', '—'):20} {m.get('logo_src', '')}", flush=True)
    mf.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    rep["total"] = len(rep["ok"]) + len(rep["fixed"]) + len(rep["missing"])
    (OUT / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    print(f"মোট {rep['total']} | ঠিক আছে {len(rep['ok'])} | ঠিক করা হলো {len(rep['fixed'])} | পাওয়া যায়নি {len(rep['missing'])}")


if __name__ == "__main__":
    main(sys.argv[1:])
