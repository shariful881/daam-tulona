"""প্রতিদিনের রান: সব চালু স্টোর আর ক্যাটাগরি থেকে দাম তুলে data/raw/ এ রাখে।

চালানো: python -m scraper.run
"""
import importlib
import json
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from scraper.common import Blocked

ROOT = Path(__file__).resolve().parent.parent
BD = timezone(timedelta(hours=6))


def main() -> int:
    stores = json.loads((ROOT / "config/stores.json").read_text())["stores"]
    tax = ROOT / "config/taxonomy.json"
    if tax.exists():  # নতুন কাঠামো: সব গ্রুপের সব পাতা
        cats = [leaf for g in json.loads(tax.read_text())["groups"] for leaf in g["leaves"]]
    else:
        cats = json.loads((ROOT / "config/categories.json").read_text())["categories"]
    today = datetime.now(BD).strftime("%Y-%m-%d")
    out = {"date": today, "scraped_at": datetime.now(BD).isoformat(timespec="minutes"), "offers": [], "health": {}}

    for store_id, store in stores.items():
        health = {"enabled": store["enabled"], "items": 0, "errors": [], "seconds": 0}
        out["health"][store_id] = health
        if not store["enabled"]:
            health["errors"].append(store.get("disabled_reason", "বন্ধ"))
            continue
        module = importlib.import_module(f"scraper.stores.{store_id}")
        t0 = time.time()
        for cat in cats:
            conf = cat["stores"].get(store_id)
            if not conf:
                continue
            try:
                extra = {"limit": conf["limit"]} if conf.get("limit") else {}
                items = []
                for src in conf.get("sources") or [conf]:
                    items += module.scrape(src["url"], src.get("max_pages", 1), store["delay"], **extra)
            except Blocked as e:
                health["errors"].append(f"{cat['slug']}: স্টোর ব্লক করেছে ({e})")
                continue
            except Exception as e:  # একটা ক্যাটাগরি ভাঙলে বাকিগুলো চলবে
                health["errors"].append(f"{cat['slug']}: {type(e).__name__}: {e}")
                continue
            if conf.get("filter"):  # একই পাতায় ল্যাপটপ ও ডেস্কটপ মেশানো থাকলে নাম দেখে ভাগ
                pat = re.compile(r"so-?dimm|laptop|notebook", re.I)
                items = [i for i in items if bool(pat.search(i["name"])) == (conf["filter"] == "laptop")]
            for it in items:
                it["store"] = store_id
                it["category"] = cat["slug"]
            out["offers"].extend(items)
            health["items"] += len(items)
            print(f"{store_id:10} {cat['slug']:12} {len(items):4} টি", flush=True)
        health["seconds"] = round(time.time() - t0)

    # একই প্রোডাক্ট একাধিক ক্যাটাগরি পাতায় এলে প্রথমটা রাখা, বাকিগুলো 'also'-তে
    seen, uniq = {}, []
    for o in out["offers"]:
        k = (o["store"], o["url"])
        if k in seen:
            seen[k].setdefault("also", []).append(o["category"])
        else:
            seen[k] = o
            uniq.append(o)
    out["offers"] = uniq

    raw_dir = ROOT / "data/raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "latest.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    total = len(out["offers"])
    print(f"মোট {total} টি অফার সংগ্রহ হয়েছে")
    return 0 if total else 1


if __name__ == "__main__":
    sys.exit(main())
