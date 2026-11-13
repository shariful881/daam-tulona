"""প্রতিদিনের রান: সব চালু স্টোর আর ক্যাটাগরি থেকে দাম তুলে data/raw/ এ রাখে।

চালানো: python -m scraper.run
"""
import importlib
import json
import os
import os
import re
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from scraper.common import Blocked

ROOT = Path(__file__).resolve().parent.parent
BD = timezone(timedelta(hours=6))


STORE_MINUTES = int(os.environ.get("STORE_MINUTES", "240"))  # প্রতিটা স্টোরের সর্বোচ্চ সময় (daily.yml-এর সীমা ৩৩০ মিনিট)


def main() -> int:
    stores = json.loads((ROOT / "config/stores.json").read_text())["stores"]
    tax = ROOT / "config/taxonomy.json"
    if tax.exists():  # নতুন কাঠামো: সব গ্রুপের সব পাতা
        cats = [leaf for g in json.loads(tax.read_text())["groups"] for leaf in g["leaves"]]
    else:
        cats = json.loads((ROOT / "config/categories.json").read_text())["categories"]
    today = datetime.now(BD).strftime("%Y-%m-%d")
    out = {"date": today, "scraped_at": datetime.now(BD).isoformat(timespec="minutes"), "offers": [], "health": {}}

    # শুধু কিছু স্টোর চালানো (পরীক্ষা/হাতে চালানো রান): ONLY_STORES=ryans,techland
    # বাকি স্টোরের আগের দাম যেমন ছিল তেমনই থাকে (matcher 'skipped' দেখে রাখে)
    only = {x.strip() for x in os.environ.get("ONLY_STORES", "").split(",") if x.strip()}
    prev_health = {}
    if only and (ROOT / "data/health.json").exists():
        prev_health = json.loads((ROOT / "data/health.json").read_text()).get("stores", {})

    def run_store(store_id, store, sink):
        """একটা স্টোরের সব ক্যাটাগরি; প্রতিটা স্টোর আলাদা থ্রেডে নিজের গতিতে (ভিন্ন সাইট, তাই একসাথে চালালেও কারও ওপর বাড়তি চাপ নেই)।"""
        health = {"enabled": store["enabled"], "items": 0, "errors": [], "seconds": 0, "failed_cats": []}
        out["health"][store_id] = health
        if only and store_id not in only:
            out["health"][store_id] = dict(prev_health.get(store_id) or health, skipped=True)
            return
        if not store["enabled"]:
            health["errors"].append(store.get("disabled_reason", "বন্ধ"))
            return
        module = importlib.import_module(f"scraper.stores.{store_id}")
        t0 = time.time()
        if store.get("match_pages"):  # শুধু-মিল দোকান: বড় ক্যাটাগরি পাতাগুলো, ক্যাটাগরি "_any" (matcher মিলিয়ে বসায়)
            for url in store["match_pages"]:
                if time.time() - t0 > STORE_MINUTES * 60:
                    health["errors"].append(f"সময় শেষ ({STORE_MINUTES} মিনিট)")
                    break
                try:
                    items = module.scrape(url, store.get("max_pages", 30), store["delay"])
                except Blocked as e:
                    items = getattr(e, "partial", None) or []
                    health["errors"].append(f"{url}: স্টোর ব্লক করেছে ({e}); আজ বাকি পাতা বাদ")
                    for it in items:
                        it["store"], it["category"] = store_id, "_any"
                    sink.extend(items)
                    health["items"] += len(items)
                    break
                except Exception as e:
                    items = getattr(e, "partial", None) or []
                    health["errors"].append(f"{url}: {type(e).__name__}: {e}")
                for it in items:
                    it["store"], it["category"] = store_id, "_any"
                sink.extend(items)
                health["items"] += len(items)
                print(f"{store_id:10} {url.rsplit('/', 1)[-1][:24]:24} {len(items):4} টি", flush=True)
            health["seconds"] = round(time.time() - t0)
            return
        mine = [c["slug"] for c in cats if c["stores"].get(store_id)]
        for cat in cats:
            conf = cat["stores"].get(store_id)
            if not conf:
                continue
            if time.time() - t0 > STORE_MINUTES * 60:  # বড় স্টোর সময়ের মধ্যে শেষ না হলে বাকিগুলোর আগের দাম থাকে
                health["errors"].append(f"সময় শেষ ({STORE_MINUTES} মিনিট): বাকি ক্যাটাগরির আগের দাম রাখা হলো")
                health["failed_cats"] += mine[mine.index(cat["slug"]):]
                break
            extra = {"limit": conf["limit"]} if conf.get("limit") else {}
            items, blocked = [], False
            try:
                for src in conf.get("sources") or [conf]:
                    items += module.scrape(src["url"], src.get("max_pages", 1), store["delay"], **extra)
            except Blocked as e:  # স্টোর না বললে আজ আর ওই স্টোরে যাই না
                items += getattr(e, "partial", None) or []
                health["errors"].append(f"{cat['slug']}: স্টোর ব্লক করেছে ({e}); আজ এই স্টোরের বাকি ক্যাটাগরি বাদ")
                blocked = True
                health["failed_cats"] += mine[mine.index(cat["slug"]):]  # এটা আর বাকিগুলো
            except Exception as e:  # একটা ক্যাটাগরি ভাঙলে বাকিগুলো চলবে; আগের পাতাগুলো রাখা হয়
                items += getattr(e, "partial", None) or []
                health["errors"].append(f"{cat['slug']}: {type(e).__name__}: {e}")
                health["failed_cats"].append(cat["slug"])
            if conf.get("filter"):  # একই পাতায় ল্যাপটপ ও ডেস্কটপ মেশানো থাকলে নাম দেখে ভাগ
                pat = re.compile(r"so-?dimm|laptop|notebook", re.I)
                items = [i for i in items if bool(pat.search(i["name"])) == (conf["filter"] == "laptop")]
            for it in items:
                it["store"] = store_id
                it["category"] = cat["slug"]
            sink.extend(items)
            health["items"] += len(items)
            print(f"{store_id:10} {cat['slug']:12} {len(items):4} টি", flush=True)
            if blocked:
                break
        health["seconds"] = round(time.time() - t0)

    sinks = {sid: [] for sid in stores}
    threads = [threading.Thread(target=run_store, args=(sid, st, sinks[sid]), daemon=True) for sid, st in stores.items()]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    for sid in stores:  # স্টোরের ক্রম ঠিক রেখে (Star Tech আগে), ফল প্রতিবার একই রকম
        out["offers"].extend(sinks[sid])
    out["health"] = {sid: out["health"][sid] for sid in stores if sid in out["health"]}

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
