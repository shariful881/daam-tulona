"""Star Tech প্রোডাক্ট পাতা থেকে বিস্তারিত তথ্য: স্পেক টেবিল, ওয়ারেন্টি, ব্র্যান্ড, মডেল, অপশন।

শুধু তথ্য (স্পেক, ওয়ারেন্টি) নেওয়া হয়। Star Tech-এর লেখা বিবরণ বা ছবি সংরক্ষণ করা হয় না।
"""
import re

from bs4 import BeautifulSoup

from scraper.common import parse_price


def _text(el) -> str:
    if el is None:
        return ""
    for br in el.find_all("br"):
        br.replace_with("\n")
    return "\n".join(line.strip() for line in el.get_text().splitlines() if line.strip())


def parse(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    out: dict = {"specs": {}, "key_features": [], "options": {}}

    # স্পেক টেবিল: প্রতিটা thead একটা অংশ (Key Features, Display, Warranty Information...)
    table = soup.select_one("table.data-table")
    if table:
        section = "General"
        for child in table.find_all(["thead", "tbody"], recursive=False):
            if child.name == "thead":
                section = _text(child) or section
                continue
            for tr in child.find_all("tr"):
                name, value = tr.select_one("td.name"), tr.select_one("td.value")
                if name and value and _text(name):
                    out["specs"].setdefault(section, {})[_text(name)] = _text(value)

    # উপরের সারাংশ টেবিল
    info = {}
    for tr in soup.select("table.product-info-table tr"):
        label, data = tr.select_one(".product-info-label"), tr.select_one(".product-info-data")
        if label and data:
            info[_text(label).lower()] = _text(data)
    out["price"] = parse_price(info.get("price"))
    out["regular"] = parse_price(info.get("regular price"))
    out["status"] = info.get("status")
    out["code"] = info.get("product code")
    out["brand"] = info.get("brand")

    # সংক্ষিপ্ত মূল বৈশিষ্ট্য (Model:, MPN: ইত্যাদি এখান থেকে)
    for li in soup.select(".short-description li"):
        t = li.get_text(" ", strip=True)
        if not t or t.lower().startswith("view more"):
            continue
        m = re.match(r"(MPN|Model)\s*:\s*(.+)", t, re.I)
        if m:
            out[m.group(1).lower()] = m.group(2).strip()
        else:
            out["key_features"].append(t)

    # ওয়ারেন্টি: স্পেক টেবিলের Warranty অংশ থেকে
    for sec, rows in out["specs"].items():
        for k, v in rows.items():
            if "warranty" in k.lower() or "warranty" in sec.lower():
                out["warranty"] = v
                break
        if out.get("warranty"):
            break

    # অপশন/ভ্যারিয়েন্ট (রং, স্টোরেজ ইত্যাদি) — থাকলে
    for grp in soup.select(".product-options .option, .product-option, .variant-group"):
        label = grp.select_one("label, .option-label, .title")
        values = [v.get_text(" ", strip=True) for v in grp.select("li, option, .option-value, a") if v.get_text(strip=True)]
        if label and values:
            out["options"][_text(label).rstrip(":")] = sorted(set(values))[:20]

    h1 = soup.select_one("h1")
    out["name"] = h1.get_text(" ", strip=True) if h1 else None
    crumbs = [a.get_text(" ", strip=True) for a in soup.select(".breadcrumb a, ul.breadcrumb li a")]
    out["breadcrumb"] = [c for c in crumbs if c and c.lower() not in ("home",) and not c.startswith("home")][:4]
    return {k: v for k, v in out.items() if v not in (None, "", [], {})}
