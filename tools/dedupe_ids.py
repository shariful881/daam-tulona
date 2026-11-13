"""সাইটের নিয়ম: একই প্রোডাক্টের একটাই পাতা, আর প্রোডাক্টের লিংকের শেষে কখনো -2, -3 ধরনের সংখ্যা নয়।

এই টুল (একবার চালালেই হয়, আবার চালালে ক্ষতি নেই) ডাটা থেকে পুরনো ডুপ্লিকেট সরায়:
  ১. হুবহু একই নামের (বড়/ছোট হাতের অক্ষর আর চিহ্ন বাদে) সব প্রোডাক্ট এক আইডিতে মেলায়।
     মূল = যেটায় বেশি দোকানের দাম আছে; অন্যগুলোর দোকানের দাম মূলটায় যায় (একই দোকান দুইবার হলে কম দাম/স্টকেরটা)।
  ২. যে আইডির শেষে মিলের কারণে সংখ্যা বসেছিল (asus-...-laptop-2), সেটা নাম থেকে নতুন আইডি পায়। নাম ৮০ অক্ষরের পরে
     আলাদা হলে আরও শব্দ যোগ হয়, সংখ্যা নয়।
  ৩. offers, products, history.csv, stock_state, manual_matches, manual_prices, suggestions, details/brand_details ফাইল,
     আর config-এর যেখানে প্রোডাক্ট আইডি আছে — সব জায়গায় নতুন আইডি বসায়।
পুরনো লিংক রিডাইরেক্ট হয় না (মালিকের সিদ্ধান্ত): মিলিয়ে দেওয়া/নাম বদলানো পুরনো লিংক আর থাকে না।

ব্যবহার: python -m tools.dedupe_ids          (পরিবর্তন লেখে)
         python -m tools.dedupe_ids --dry    (শুধু হিসাব দেখায়)"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT))
from matcher.match import bad_id, full_slug, slugify, unique_slug  # noqa: E402


def load(p, default):
    return json.loads(p.read_text()) if p.exists() else default


def offer_better(a, b):
    """দুইটা একই দোকানের অফার: কোনটা রাখব (স্টকে + দাম আছে + কম দাম)।"""
    def rank(o):
        return (bool(o.get("in_stock") and o.get("price")), bool(o.get("price")), -(o.get("price") or 10**9))
    return a if rank(a) >= rank(b) else b


def plan(products, offers):
    """{পুরনো আইডি: নতুন আইডি} — শুধু যেগুলো বদলাবে।"""
    groups = defaultdict(list)
    for pid, p in products.items():
        groups[full_slug(p["name"])].append(pid)

    def strength(pid):
        o = offers.get(pid, {})
        return (len([v for v in o.values() if v.get("price")]), len(o), not bad_id(pid, products[pid]["name"]),
                -len(pid), products[pid].get("created", ""))

    change, keep_of = {}, {}
    for f, ids in groups.items():
        keep = max(ids, key=strength)
        keep_of[f] = keep
        if len(ids) > 1 or bad_id(keep, products[keep]["name"]):
            change[f] = ids
    # যেগুলো বদলাবে না, তাদের আইডি সংরক্ষিত
    taken = {pid for f, ids in groups.items() if f not in change for pid in ids}
    mapping = {}
    # ছোট নাম আগে (যার পুরো নামই ভিত্তি), তারপর পুরনো প্রোডাক্ট
    for f in sorted(change, key=lambda f: (len(f) > 80, min(products[i].get("created", "") for i in change[f]), f)):
        ids, keep = change[f], keep_of[f]
        own = [i for i in ids if i == slugify(products[i]["name"]) and not bad_id(i, products[i]["name"]) and i not in taken]
        new = own[0] if own else unique_slug(products[keep]["name"], taken)
        taken.add(new)
        for i in ids:
            if i != new:
                mapping[i] = new
    return mapping


def rename_json(x, m):
    """JSON-এর ভেতরে যেখানে হুবহু পুরনো আইডি (কী, মান, বা a|b জোড়ার অংশ) — নতুন আইডি।"""
    if isinstance(x, dict):
        return {rename_json(k, m) if isinstance(k, str) else k: rename_json(v, m) for k, v in x.items()}
    if isinstance(x, list):
        return [rename_json(v, m) for v in x]
    if isinstance(x, str):
        if x in m:
            return m[x]
        if "|" in x:
            parts = x.split("|")
            if any(p in m for p in parts):
                return "|".join(m.get(p, p) for p in parts)
    return x


def main(dry=False):
    products = load(DATA / "products.json", {})
    offers = load(DATA / "offers.json", {})
    m = plan(products, offers)
    merged = sum(1 for o, n in m.items() if n in products and n not in m)
    print(f"বদলাবে: {len(m)}টি আইডি ({merged}টি অন্য প্রোডাক্টে মিলবে, বাকিগুলো সংখ্যা ছাড়া নতুন নামে)")
    if dry or not m:
        for o, n in list(m.items())[:15]:
            print("  ", o, "→", n)
        return m

    # products: প্রতিটা নতুন আইডিতে সবচেয়ে বেশি দোকানওয়ালা সদস্যের তথ্য থাকে
    newp = {}
    members = defaultdict(list)
    for pid in products:
        members[m.get(pid, pid)].append(pid)
    for tgt, ids in members.items():
        best = max(ids, key=lambda i: (len([v for v in offers.get(i, {}).values() if v.get("price")]), i == tgt))
        p = dict(products[best])
        if "#" in p.get("key", ""):  # একই দোকানে দুইবার থাকার আলাদা চিহ্ন আর লাগে না
            p["key"] = p["key"].split("#", 1)[0]
        p["created"] = min(products[i].get("created", "9") for i in ids)
        newp[tgt] = p

    newo = defaultdict(dict)
    for pid, st in offers.items():
        tgt = m.get(pid, pid)
        for s, o in st.items():
            newo[tgt][s] = offer_better(newo[tgt][s], o) if s in newo[tgt] else o

    # দামের ইতিহাস: একই দিন/দোকান দুই সারি হলে কম দাম (স্টকেরটা আগে)
    hp = DATA / "history.csv"
    rows = {}
    with hp.open() as f:
        for r in csv.DictReader(f):
            r["product"] = m.get(r["product"], r["product"])
            k = (r["date"], r["product"], r["store"])
            if k not in rows or (int(r["in_stock"]), -int(r["price"])) > (int(rows[k]["in_stock"]), -int(rows[k]["price"])):
                rows[k] = r
    with hp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "product", "store", "price", "in_stock"])
        w.writeheader()
        w.writerows(sorted(rows.values(), key=lambda r: (r["date"], r["product"], r["store"])))

    ss = load(DATA / "stock_state.json", {})
    nss = {}
    for pid, v in ss.items():
        t = m.get(pid, pid)
        if t not in nss or v[0] > nss[t][0]:
            nss[t] = v
    (DATA / "stock_state.json").write_text(json.dumps(nss, separators=(",", ":"), sort_keys=True))

    mp = load(DATA / "manual_prices.json", {})
    nmp = {}
    for pid, v in mp.items():
        t = m.get(pid, pid)
        nmp[t] = {**nmp.get(t, {}), **v} if isinstance(v, dict) else v
    (DATA / "manual_prices.json").write_text(json.dumps(nmp, ensure_ascii=False, indent=1))

    mm = rename_json(load(DATA / "manual_matches.json", {}), m)
    seen, merges = set(), []
    for e in mm.get("merge", []):
        rest = sorted({x for x in e.get("merge", []) if x != e["keep"]})
        k = (e["keep"], tuple(rest))
        if rest and k not in seen:
            seen.add(k)
            merges.append({"keep": e["keep"], "merge": rest})
    mm["merge"] = merges
    for key in ("ignore", "sugg_hidden", "not_same", "keep_listed", "drop_offer", "price_ok"):
        if isinstance(mm.get(key), list):
            mm[key] = sorted({x for x in mm[key] if not (isinstance(x, str) and "|" in x and len(set(x.split("|"))) == 1)}, key=str)
    (DATA / "manual_matches.json").write_text(json.dumps(mm, ensure_ascii=False, indent=2) + "\n")

    sg = [s for s in rename_json(load(DATA / "suggestions.json", []), m) if s.get("a") != s.get("b")]
    (DATA / "suggestions.json").write_text(json.dumps(sg, ensure_ascii=False, indent=1))

    for sub in ("details", "brand_details"):
        for old, new in m.items():
            src = DATA / sub / old[:1] / f"{old}.json"
            if not src.exists():
                continue
            dst = DATA / sub / new[:1] / f"{new}.json"
            if dst.exists():  # মূলের ফাইল থাকলে সেটাই থাকে
                src.unlink()
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                src.rename(dst)

    for f in sorted((ROOT / "config").glob("*.json")):
        raw = f.read_text()
        new = rename_json(json.loads(raw), m)
        if new != json.loads(raw):
            f.write_text(json.dumps(new, ensure_ascii=False, indent=2) + ("\n" if raw.endswith("\n") else ""))
            print("  config বদলেছে:", f.name)

    (DATA / "products.json").write_text(json.dumps(newp, ensure_ascii=False, indent=1, sort_keys=True))
    (DATA / "offers.json").write_text(json.dumps(newo, ensure_ascii=False, indent=1, sort_keys=True))
    left = [p for p in newp if bad_id(p, newp[p]["name"])]
    dup = len(newp) - len({full_slug(p["name"]) for p in newp.values()})
    print(f"শেষে: {len(newp)} প্রোডাক্ট, {len(newo)}টিতে দাম; সংখ্যা-প্রত্যয় আইডি {len(left)}, একই নামের ডুপ্লিকেট {dup}")
    return m


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
