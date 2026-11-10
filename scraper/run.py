"""প্রতিদিনের রান: সব চালু স্টোর আর ক্যাটাগরি থেকে দাম তুলে data/raw/ এ রাখে।

চালানো: python -m scraper.run
"""
import importlib
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from scraper.common import Blocked

ROOT = Path(__file__).resolve().parent.parent
BD = timezone(timedelta(hours=6))


def main() -> int:
    stores = json.loads((ROOT / "config/stores.json").read_text())["stores"]
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
                items = module.scrape(conf["url"], conf.get("max_pages", 1), store["delay"])
            except Blocked as e:
                health["errors"].append(f"{cat['slug']}: স্টোর ব্লক করেছে ({e})")
                continue
            except Exception as e:  # একটা ক্যাটাগরি ভাঙলে বাকিগুলো চলবে
                health["errors"].append(f"{cat['slug']}: {type(e).__name__}: {e}")
                continue
            for it in items:
                it["store"] = store_id
                it["category"] = cat["slug"]
            out["offers"].extend(items)
            health["items"] += len(items)
            print(f"{store_id:10} {cat['slug']:12} {len(items):4} টি", flush=True)
        health["seconds"] = round(time.time() - t0)

    raw_dir = ROOT / "data/raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "latest.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    total = len(out["offers"])
    print(f"মোট {total} টি অফার সংগ্রহ হয়েছে")
    return 0 if total else 1


if __name__ == "__main__":
    sys.exit(main())
