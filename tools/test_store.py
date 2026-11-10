"""একটা স্টোরের একটা ক্যাটাগরি পরীক্ষা করে দেখা (দামের রান না চালিয়ে)।
চালানো: python -m tools.test_store walton fridge  → probe/test.json"""
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(store_id, cat_slug):
    store = json.loads((ROOT / "config/stores.json").read_text())["stores"][store_id]
    leaf = next(l for g in json.loads((ROOT / "config/taxonomy.json").read_text())["groups"] for l in g["leaves"] if l["slug"] == cat_slug)
    conf = leaf["stores"][store_id]
    mod = importlib.import_module(f"scraper.stores.{store_id}")
    items = []
    for src in conf.get("sources") or [conf]:
        items += mod.scrape(src["url"], src.get("max_pages", 1), store["delay"])
    Path("probe").mkdir(exist_ok=True)
    Path("probe/test.json").write_text(json.dumps(items, ensure_ascii=False, indent=1))
    print(len(items), "টি পাওয়া গেছে")
    for i in items[:15]:
        print(i["price"], i["in_stock"], i["name"])


if __name__ == "__main__":
    main(*sys.argv[1:3])
