"""Star Tech-এর সব ক্যাটাগরি ও সাব-ক্যাটাগরিতে কতগুলো প্রোডাক্ট আছে তার হিসাব।

মেনু থেকে মূল ক্যাটাগরি আর তার নিচের সাব-ক্যাটাগরি (ব্র্যান্ড লেভেল বাদে) নেয়,
প্রতিটার প্রথম পাতার "Showing 1 to 20 of N" থেকে মোট সংখ্যা পড়ে।

চালানো: python -m tools.startech_catalog
আউটপুট: data/catalog/startech.json আর startech.csv
"""
import csv
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from scraper.common import fetch

ROOT = Path(__file__).resolve().parent.parent
HOME = "https://www.startech.com.bd/"
DELAY = 3


def count(url: str) -> int | None:
    try:
        text = BeautifulSoup(fetch(url, DELAY), "html.parser").get_text(" ")
    except Exception as e:  # একটা ভাঙলেও বাকিগুলো চলবে
        print("  ব্যর্থ:", url, e)
        return None
    m = re.search(r"Showing\s+\d+\s+to\s+\d+\s+of\s+([\d,]+)", text)
    return int(m.group(1).replace(",", "")) if m else 0


def main():
    soup = BeautifulSoup(fetch(HOME, DELAY), "html.parser")
    nav = soup.select_one("nav.navbar")
    tops = nav.select(":scope > div > ul > li, :scope > ul > li")
    result = []
    for li in tops:
        a = li.find("a", class_="nav-link", recursive=False)
        if not a or not a.get("href", "").startswith("http"):
            continue
        cat = {"name": a.get_text(strip=True), "url": a["href"], "total": count(a["href"]), "subcategories": []}
        print(f"{cat['name']}: {cat['total']}", flush=True)
        menu = li.select_one(".drop-menu-1")
        subs = (menu.select(":scope > li") or menu.select(":scope > ul > li")) if menu else []
        for sub in subs:
            sa = sub.find("a", class_="nav-link", recursive=False)
            if not sa or sa.get_text(strip=True).lower().startswith("show all") or "/tool/" in sa["href"]:
                continue
            n = count(sa["href"])
            cat["subcategories"].append({"name": sa.get_text(strip=True), "url": sa["href"], "total": n})
            print(f"   {sa.get_text(strip=True)}: {n}", flush=True)
        result.append(cat)

    out = ROOT / "data/catalog"
    out.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone(timedelta(hours=6))).isoformat(timespec="minutes")
    (out / "startech.json").write_text(json.dumps({"store": "Star Tech", "checked_at": now, "categories": result}, ensure_ascii=False, indent=1))
    with (out / "startech.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["মূল ক্যাটাগরি", "সাব-ক্যাটাগরি", "প্রোডাক্ট সংখ্যা", "লিংক"])
        for c in result:
            w.writerow([c["name"], "(সব)", c["total"], c["url"]])
            for s in c["subcategories"]:
                w.writerow([c["name"], s["name"], s["total"], s["url"]])
    print(f"মূল ক্যাটাগরি: {len(result)} | সাব-ক্যাটাগরি: {sum(len(c['subcategories']) for c in result)}")


if __name__ == "__main__":
    main()
