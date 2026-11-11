"""প্রোডাক্টের বিস্তারিত তথ্য (স্পেক, ওয়ারেন্টি, মডেল) সংগ্রহ — সব স্টোর থেকে, একসাথে।

প্রতিটা প্রোডাক্টের তথ্য যে কোনো একটা স্টোর থেকে আনলেই চলে। তাই কাজ ভাগ করে দেওয়া হয়:
যে স্টোরে প্রোডাক্টটা আছে তাদের মধ্যে যার ভাগে কম কাজ, সে আনবে (Star Tech-এর টেবিল সবচেয়ে গোছানো, তাই সমান হলে আগে)।
প্রতিটা স্টোর আলাদা থ্রেডে নিজের গতিতে (বিরতি) আর নিজের দৈনিক সীমায় চলে; কোনো স্টোর ব্লক করলে শুধু সেটা থামে।
অগ্রাধিকার: যেগুলোর তথ্য নেই > একাধিক স্টোরে আছে > স্টকে আছে > কম্পিউটার/ল্যাপটপ/মোবাইল আগে; তারপর ৬০ দিনের পুরনো।
ফল: data/details/<আইডির প্রথম অক্ষর>/<আইডি>.json

চালানো: python -m tools.enrich          (ENRICH_SCALE=0.5 দিলে সব সীমা অর্ধেক)
"""
import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scraper.common import Blocked, fetch
from scraper import details_generic, details_startech

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BD = timezone(timedelta(hours=6))
MAX_MINUTES = int(os.environ.get("ENRICH_MINUTES", "150"))
SCALE = float(os.environ.get("ENRICH_SCALE", "1"))
PRIORITY = ["computer-parts", "laptop-desktop", "mobile-tablet", "monitor", "appliance", "accessories", "gadget", "networking"]
# স্টোর: (দিনে সর্বোচ্চ কয়টা পাতা, দুই পাতার মাঝে কত সেকেন্ড)
SOURCES = {
    "startech": (600, 8),       # দ্রুত অনেক পাতা খুললে 403 দেয়
    "pchouse": (500, 6),
    "creatus": (500, 6),
    "smartbd": (400, 6),
    "applegadgets": (300, 6),
    "diamu": (300, 6),
    "fourstar": (200, 10),
}
if os.environ.get("ENRICH_LIMIT"):  # অ্যাডমিন থেকে মোট সংখ্যা দিলে Star Tech-এর ভাগ সেটা, বাকিরা অনুপাতে
    SCALE = int(os.environ["ENRICH_LIMIT"]) / SOURCES["startech"][0]


def path_for(pid: str) -> Path:
    return DATA / "details" / pid[:1] / f"{pid}.json"


def parse(store, html):
    return details_startech.parse(html) if store == "startech" else details_generic.parse(html, store)


def plan(offers, products, group_of, today):
    todo = []
    for pid, so in offers.items():
        if pid not in products:
            continue
        cands = [s for s in SOURCES if so.get(s, {}).get("url")]
        if not cands:
            continue
        p, age = path_for(pid), None
        if p.exists():
            try:
                age = (today - datetime.fromisoformat(json.loads(p.read_text())["fetched"]).date()).days
            except Exception:
                age = 999
            if age < 60:
                continue
        g = group_of.get(products[pid]["category"], "")
        rank = PRIORITY.index(g) if g in PRIORITY else len(PRIORITY)
        multi = sum(1 for o in so.values() if o.get("price")) > 1
        stock = any(o.get("in_stock") for o in so.values())
        todo.append(((age is not None, not multi, not stock, rank, pid), pid, cands))
    todo.sort()
    quota = {s: max(1, int(n * SCALE)) for s, (n, _) in SOURCES.items()}
    queues = {s: [] for s in SOURCES}
    for _, pid, cands in todo:  # কম ভরা স্টোরকে দাও (তালিকার ক্রমে Star Tech আগে)
        free = [s for s in cands if len(queues[s]) < quota[s]]
        if free:
            s = min(free, key=lambda x: len(queues[x]) / quota[x])
            queues[s].append((pid, offers[pid][s]["url"]))
    return len(todo), queues


def worker(store, jobs, delay, deadline, stats, lock):
    done = failed = 0
    for pid, url in jobs:
        if time.time() > deadline:
            break
        try:
            d = parse(store, fetch(url, delay, cache=False))
        except Blocked as e:
            print(f"{store}: ব্লক ({e}), আজ এখানেই থামা", flush=True)
            break
        except Exception as e:
            failed += 1
            if failed >= 25 and done == 0:
                print(f"{store}: পরপর ব্যর্থ, থামা ({type(e).__name__})", flush=True)
                break
            continue
        if not d.get("specs") and not d.get("key_features"):
            failed += 1
            continue
        d["fetched"] = datetime.now(BD).isoformat(timespec="minutes")
        d["source"], d["store"] = url, store
        p = path_for(pid)
        with lock:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(d, ensure_ascii=False, indent=1))
        done += 1
        if done % 100 == 0:
            print(f"  {store}: {done} টি", flush=True)
    stats[store] = (done, failed, len(jobs))


def main():
    offers = json.loads((DATA / "offers.json").read_text())
    products = json.loads((DATA / "products.json").read_text())
    tax = json.loads((ROOT / "config/taxonomy.json").read_text())
    group_of = {l["slug"]: g["slug"] for g in tax["groups"] for l in g["leaves"]}
    total, queues = plan(offers, products, group_of, datetime.now(BD).date())
    print(f"তথ্য দরকার: {total} | এই রানে: " + ", ".join(f"{s} {len(q)}" for s, q in queues.items() if q), flush=True)
    deadline, stats, lock, threads = time.time() + MAX_MINUTES * 60, {}, threading.Lock(), []
    for s, q in queues.items():
        if q:
            t = threading.Thread(target=worker, args=(s, q, SOURCES[s][1], deadline, stats, lock), daemon=True)
            t.start()
            threads.append(t)
    for t in threads:
        t.join()
    for s, (d, f, n) in stats.items():
        print(f"{s:12} সম্পন্ন {d}/{n} | ব্যর্থ {f}")
    print(f"মোট সম্পন্ন: {sum(v[0] for v in stats.values())}")


if __name__ == "__main__":
    main()
