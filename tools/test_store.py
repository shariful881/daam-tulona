"""একটা স্টোরের একটা (বা সব) ক্যাটাগরি পরীক্ষা করে দেখা (দামের রান না চালিয়ে)।
চালানো: python -m tools.test_store walton fridge   অথবা   python -m tools.test_store pchouse all  → probe/test.json"""
import importlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_match(store_id, store, pages):
    """শুধু-মিল দোকান: বড় পাতাগুলো থেকে (প্রতিটার প্রথম কয়েক পাতা) তুলে আমাদের তালিকার সাথে কতগুলো মেলে।"""
    from matcher.match import MatchOnly
    mod = importlib.import_module(f"scraper.stores.{store_id}")
    products = json.loads((ROOT / "data/products.json").read_text())
    offers = json.loads((ROOT / "data/offers.json").read_text())
    mo = MatchOnly(products, list(offers))
    report, rows = {}, []
    for url in store["match_pages"]:
        t0, err, got = time.time(), None, []
        try:
            got = mod.scrape(url, pages, store["delay"])
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
        hit = 0
        for g in got:
            pid = mo.find(g["name"], g["name"].split()[0])
            if pid:
                hit += 1
                rows.append({"store_name": g["name"], "our": products[pid]["name"], "price": g["price"],
                             "ours": sorted(o["price"] for o in offers[pid].values() if o.get("price"))[:3]})
        report[url] = {"n": len(got), "priced": sum(1 for g in got if g.get("price")), "matched": hit, "err": err,
                       "sec": round(time.time() - t0), "sample": [g["name"] for g in got[:3]]}
        print(url, len(got), hit, err or "", flush=True)
    Path("probe").mkdir(exist_ok=True)
    Path("probe/report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    Path("probe/matches.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))


def main(store_id, cat_slug):
    store = json.loads((ROOT / "config/stores.json").read_text())["stores"][store_id]
    if store.get("match_pages"):
        return test_match(store_id, store, int(cat_slug) if cat_slug.isdigit() else 2)
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
