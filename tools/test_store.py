"""একটা স্টোরের একটা (বা সব) ক্যাটাগরি পরীক্ষা করে দেখা (দামের রান না চালিয়ে)।
চালানো: python -m tools.test_store walton fridge   অথবা   python -m tools.test_store pchouse all  → probe/test.json"""
import importlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(store_id, cat_slug):
    store = json.loads((ROOT / "config/stores.json").read_text())["stores"][store_id]
    leaves = [l for g in json.loads((ROOT / "config/taxonomy.json").read_text())["groups"] for l in g["leaves"]
              if store_id in l["stores"] and (cat_slug == "all" or l["slug"] == cat_slug)]
    mod = importlib.import_module(f"scraper.stores.{store_id}")
    items, report = [], {}
    for leaf in leaves:
        conf = leaf["stores"][store_id]
        got, err, t0 = [], None, time.time()
        try:
            for src in conf.get("sources") or [conf]:
                mp = 1 if cat_slug == "all" else src.get("max_pages", 1)  # সব ক্যাটাগরির পরীক্ষায় শুধু প্রথম পাতা
                got += mod.scrape(src["url"], mp, store["delay"])
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
        for g in got:
            g["category"] = leaf["slug"]
        items += got
        report[leaf["slug"]] = {"n": len(got), "err": err, "sec": round(time.time() - t0),
                                "sample": [g["name"] for g in got[:3]], "priced": sum(1 for g in got if g.get("price"))}
        print(leaf["slug"], len(got), err or "", flush=True)
    Path("probe").mkdir(exist_ok=True)
    Path("probe/test.json").write_text(json.dumps(items, ensure_ascii=False, indent=1))
    Path("probe/report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(len(items), "টি পাওয়া গেছে")


if __name__ == "__main__":
    main(*sys.argv[1:3])
