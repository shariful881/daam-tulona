"""হোম পেজের "বাজারের অবস্থা": দামের ইতিহাস থেকে সূচক, উঠানামা, ক্যাটাগরি হিটম্যাপ আর দোকানের খবর।

হিসাবের নিয়ম (শেয়ারবাজারের সূচকের মতো):
- একই দোকানের একই প্রোডাক্টের নিজের দাম দুই দিন মিলিয়ে বদল ধরা হয়। নতুন দোকান বা নতুন প্রোডাক্ট
  যোগ হলে, বা কোনো দোকান স্টক শেষ করলে সূচক লাফায় না।
- শুধু সেই জোড়া ধরা হয় যা আগের দিন ও আজ দুই দিনই স্টকে ছিল। "যাচাই চলছে" দাম আর ৪০%-এর বেশি
  লাফ (সাধারণত ভুল দাম) বাদ।
- প্রোডাক্টের বদল = তার দোকানগুলোর বদলের জ্যামিতিক গড়; দিনের বদল = সব প্রোডাক্টের জ্যামিতিক গড়।
- সূচক শুরু হয় ১০০ থেকে, প্রতিদিন আগের দিনের সূচক × দিনের বদল।
- তুলনাযোগ্য প্রোডাক্ট খুব কম হলে সংখ্যা দেখানো হয় না, "হিসাব শুরু হচ্ছে" লেখা আসে।
"""
import math
from collections import Counter, defaultdict

MIN_PRODUCTS = 50   # এর কম প্রোডাক্ট মিললে দিনের সূচক নির্ভরযোগ্য নয়
MIN_CAT = 5         # হিটম্যাপে ক্যাটাগরির % দেখাতে অন্তত এতগুলো প্রোডাক্ট মিলতে হবে
MIN_CHANGED = 10    # এর কম প্রোডাক্টের দাম বদলালে দিনটা হিসাবে ধরা হয় না (সাধারণত ডাটার সমস্যা)
MAX_JUMP = 0.4      # এর বেশি বদল ভুল দাম ধরে বাদ
TABS = [("all", "সব"), ("mobile", "মোবাইল"), ("laptop", "ল্যাপটপ"), ("parts", "পিসি পার্টস"), ("other", "অন্যান্য")]
TAB_OF_GROUP = {"mobile-tablet": "mobile", "laptop-desktop": "laptop", "computer-parts": "parts", "monitor": "parts"}


def _gmean(xs):
    return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else 1.0


def _state(changes, d):
    """d তারিখ শেষে (দাম বা None) — কোনো সারি না থাকলে KeyError-এর বদলে 'absent'।"""
    v = "absent"
    for d_, p in changes:
        if d_ > d:
            break
        v = p
    return v


def compute(history, items, offers, enabled, today):
    """history: pid → store → [(date, price|None)]; items: build.py-র items (sus/best/category/group সহ)।"""
    dates = sorted({d for ss in history.values() for ch in ss.values() for d, _ in ch if d <= today})
    if not dates:
        return {"ready": False, "days": 0}
    last = dates[-1]
    days = dates[-31:]
    # জোড়া (pid, store) → তারিখ অনুযায়ী সাজানো বদল
    pairs = []
    for pid, ss in history.items():
        it = items.get(pid)
        if not it:
            continue
        for s, ch in ss.items():
            if s in it["sus"] or s not in enabled:
                continue
            pairs.append((pid, s, sorted(ch)))

    def day_ratios(d0, d1):
        """d0→d1: pid → [(store, পুরনো দাম, নতুন দাম)] (দুই দিনই স্টকে থাকা জোড়া)।"""
        out = defaultdict(list)
        for pid, s, ch in pairs:
            if ch[-1][0] <= d0:
                # d0-এর পরে কোনো বদল নেই → দাম একই (দ্রুত পথ)
                a = ch[-1][1]
                if a:
                    out[pid].append((s, a, a))
                continue
            a, b = _state(ch, d0), _state(ch, d1)
            if a in ("absent", None) or b in ("absent", None):
                continue
            if abs(b / a - 1) > MAX_JUMP:
                continue
            out[pid].append((s, a, b))
        return out

    # সূচক (চেইন): প্রতিটা দিনের বদল
    index, steps = [100.0], []
    for d0, d1 in zip(days, days[1:]):
        r = day_ratios(d0, d1)
        prod = {pid: _gmean([b / a for _, a, b in v]) for pid, v in r.items()}
        ok = len(prod) >= MIN_PRODUCTS
        steps.append({"date": d1, "ok": ok, "prod": prod, "pairs": r})
        index.append(index[-1] * (_gmean(list(prod.values())) if ok else 1.0))
    M = {"ready": False, "days": len(days), "last": last, "first": days[0]}
    if not steps or not steps[-1]["ok"]:
        return M
    td = steps[-1]
    prod = td["prod"]
    changed = {pid: r for pid, r in prod.items() if abs(r - 1) >= 0.0005}
    if len(changed) < MIN_CHANGED:  # প্রথম দিন বা দাম আনা ঠিকমতো হয়নি: শূন্য বদলকে "বাজার স্থির" বলা ঠিক নয়
        return M
    n_dn = sum(1 for r in changed.values() if r < 1)
    n_up = sum(1 for r in changed.values() if r > 1)
    M.update(ready=True, index=round(index[-1], 1), chg=round((index[-1] / index[-2] - 1) * 100, 2),
             series=[(d, round(v, 2)) for d, v in zip(days, index)][-8:],
             n_dn=n_dn, n_up=n_up, n_eq=len(prod) - n_dn - n_up, n_cmp=len(prod))

    # উঠানামা: প্রতিটা প্রোডাক্টের সবচেয়ে বড় বদল হওয়া দোকান
    movers_dn, movers_up = [], []
    for pid, v in td["pairs"].items():
        it = items[pid]
        lo = min(v, key=lambda x: x[2] / x[1])
        hi = max(v, key=lambda x: x[2] / x[1])
        if lo[2] / lo[1] <= 0.99 and lo[2] >= 300:
            movers_dn.append({"it": it, "store": lo[0], "old": lo[1], "new": lo[2], "pct": round((1 - lo[2] / lo[1]) * 100)})
        if hi[2] / hi[1] >= 1.01 and hi[2] >= 300:
            movers_up.append({"it": it, "store": hi[0], "old": hi[1], "new": hi[2], "pct": round((hi[2] / hi[1] - 1) * 100)})
    movers_dn.sort(key=lambda m: (m["new"] / m["old"], -m["it"]["live_count"]))
    movers_up.sort(key=lambda m: (-(m["new"] / m["old"]), -m["it"]["live_count"]))
    for m in movers_dn + movers_up:
        m["tab"] = TAB_OF_GROUP.get(m["it"]["group"], "other")
    M["movers"] = {"dn": movers_dn, "up": movers_up}

    # ক্যাটাগরি: আজকের বদল আর গত ৭ দিনের বদল (চেইন)
    cat_today, cat_week = {}, {}
    by_cat_today = defaultdict(list)
    for pid, r in prod.items():
        by_cat_today[items[pid]["category"]].append(r)
    for c, rs in by_cat_today.items():
        if len(rs) >= MIN_CAT:
            cat_today[c] = round((_gmean(rs) - 1) * 100, 1)
    wk = defaultdict(lambda: [1.0, 0])
    for st in steps[-7:]:
        if not st["ok"]:
            continue
        bc = defaultdict(list)
        for pid, r in st["prod"].items():
            bc[items[pid]["category"]].append(r)
        for c, rs in bc.items():
            if len(rs) >= MIN_CAT:
                wk[c][0] *= _gmean(rs)
                wk[c][1] = max(wk[c][1], len(rs))
    for c, (v, n) in wk.items():
        cat_week[c] = round((v - 1) * 100, 1)
    M["cat_today"], M["cat_week"] = cat_today, cat_week

    # দোকানের খবর: আজ কতগুলো দাম কমাল/বাড়াল, কতগুলো স্টক শেষ, কতগুলো নতুন
    prev = days[-2]
    sn = {s: Counter() for s in enabled}
    for pid, s, ch in pairs:
        if ch[-1][0] != last:
            continue
        a, b = _state(ch, prev), _state(ch, last)
        c = sn[s]
        if a == "absent":
            c["new"] += 1
        elif a and b:
            if b < a:
                c["dn"] += 1
            elif b > a:
                c["up"] += 1
        elif a and b is None:
            c["oos"] += 1
        elif a is None and b:
            c["back"] += 1
    M["store_news"] = sn
    return M


def summary_text(M, leaves, n_stores, n_prices):
    """গুগল ও শেয়ারের জন্য দিনের বাজারের ছোট লেখা।"""
    if not M.get("ready"):
        return (f"আজ {n_stores}টি দোকানের {n_prices:,}টি দাম যাচাই করা হয়েছে। দামের ইতিহাস জমা হচ্ছে; "
                "কয়েক দিনের মধ্যে এখানে প্রতিদিনের বাজারের উঠানামা, কোন ক্যাটাগরিতে দাম কমছে আর কোথায় বাড়ছে তা দেখা যাবে।")
    c = M["chg"]
    mood = "প্রায় স্থির ছিল" if abs(c) < 0.05 else (f"গতকালের চেয়ে {abs(c):.1f}% নেমেছে" if c < 0 else f"গতকালের চেয়ে {abs(c):.1f}% বেড়েছে")
    t = f"আজ {n_stores}টি দোকানের {n_prices:,}টি দাম যাচাই করা হয়েছে। সার্বিক ইলেকট্রনিক্স বাজার {mood}। "
    wk = sorted(((v, k) for k, v in M["cat_week"].items() if abs(v) >= 0.3), key=lambda x: x[0])
    dn = [f"{leaves[k]['name_bn']} ({abs(v):.1f}%)" for v, k in wk if v < 0][:2]
    up = [f"{leaves[k]['name_bn']} ({v:.1f}%)" for v, k in wk[::-1] if v > 0][:2]
    if dn:
        t += f"গত এক সপ্তাহে {' আর '.join(dn)}-এ দাম কমছে"
        t += f", অন্যদিকে {' আর '.join(up)}-এ বাড়ছে। " if up else "। "
    elif up:
        t += f"গত এক সপ্তাহে {' আর '.join(up)}-এ দাম বাড়ছে। "
    t += f"আজ {M['n_dn']:,}টি প্রোডাক্টের দাম কমেছে, {M['n_up']:,}টির বেড়েছে।"
    return t
