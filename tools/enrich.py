"""প্রোডাক্টের বিস্তারিত তথ্য (স্পেক, ওয়ারেন্টি, মডেল) Star Tech-এর প্রোডাক্ট পাতা থেকে সংগ্রহ।

প্রতি রানে সর্বোচ্চ ENRICH_LIMIT টা (ডিফল্ট ১৫০০), প্রথমে যেগুলোর তথ্য নেই, তারপর ৬০ দিনের পুরনোগুলো।
ফল: data/details/<আইডির প্রথম অক্ষর>/<আইডি>.json

চালানো: python -m tools.enrich
"""
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scraper.common import Blocked, fetch
from scraper.details_startech import parse

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BD = timezone(timedelta(hours=6))
LIMIT = int(os.environ.get("ENRICH_LIMIT", "1500"))
MAX_MINUTES = int(os.environ.get("ENRICH_MINUTES", "150"))
PRIORITY = ["computer-parts", "laptop-desktop", "mobile-tablet", "monitor", "accessories", "gadget", "networking"]


def path_for(pid: str) -> Path:
    return DATA / "details" / pid[:1] / f"{pid}.json"


def main():
    offers = json.loads((DATA / "offers.json").read_text())
    products = json.loads((DATA / "products.json").read_text())
    tax = json.loads((ROOT / "config/taxonomy.json").read_text())
    group_of = {l["slug"]: g["slug"] for g in tax["groups"] for l in g["leaves"]}
    today = datetime.now(BD).date()

    todo = []
    for pid, so in offers.items():
        st = so.get("startech")
        if not st or pid not in products:
            continue
        p = path_for(pid)
        age = None
        if p.exists():
            age = (today - datetime.fromisoformat(json.loads(p.read_text())["fetched"]).date()).days
            if age < 60:
                continue
        g = group_of.get(products[pid]["category"], "")
        rank = PRIORITY.index(g) if g in PRIORITY else len(PRIORITY)
        todo.append((age is not None, rank, pid, st["url"]))
    todo.sort()
    print(f"বাকি: {len(todo)} | এই রানে: {min(LIMIT, len(todo))}", flush=True)

    t0, done, failed = time.time(), 0, 0
    for _, _, pid, url in todo[:LIMIT]:
        if time.time() - t0 > MAX_MINUTES * 60:
            print("সময় শেষ, বাকিগুলো পরের রানে")
            break
        try:
            d = parse(fetch(url, 3))
        except Blocked as e:
            print("ব্লক:", e)
            break
        except Exception as e:
            failed += 1
            print("ব্যর্থ:", pid, type(e).__name__)
            continue
        d["fetched"] = datetime.now(BD).isoformat(timespec="minutes")
        d["source"] = url
        p = path_for(pid)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=1))
        done += 1
        if done % 100 == 0:
            print(f"  {done} টি সম্পন্ন", flush=True)
    print(f"সম্পন্ন: {done} | ব্যর্থ: {failed}")


if __name__ == "__main__":
    main()
