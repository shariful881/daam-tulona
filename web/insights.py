"""'দামের বিশ্লেষণ': আমাদের নিজেদের ডাটা (দোকানের দাম, ইতিহাস, স্টক, ক্যাটাগরির অন্য প্রোডাক্ট) থেকে
প্রতিটা প্রোডাক্টের জন্য আলাদা বাক্য। প্রতিদিন রাতের রানের পর নতুন করে তৈরি হয়।

নিয়ম:
  - ডাটা না থাকলে সেই বাক্য বাদ (অনুমান বা ভরাট লেখা নয়)
  - ভবিষ্যদ্বাণী বা "এখনই কিনুন" নয়, শুধু যা ঘটেছে
  - প্রতিটা ধরনের কয়েকটা ভিন্ন গঠন; কোনটা যাবে প্রোডাক্ট ধরে ঠিক হয় (প্রতিদিন একই থাকে)
"""
import re
import zlib
from collections import Counter
from datetime import date, timedelta

BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def bn(n):
    return f"{int(n):,}".translate(BN_DIGITS)


def tk(n):
    return "৳" + bn(n)


def pick(pid, kind, options):
    """একই প্রোডাক্টে প্রতিদিন একই গঠন, ভিন্ন প্রোডাক্টে ভিন্ন"""
    return options[zlib.crc32(f"{pid}|{kind}".encode()) % len(options)]


# ---- একই দামের অন্য প্রোডাক্টের সাথে তুলনার ঘর: প্রোফাইল -> [(এক নজরের ঘর, একক, বিশেষ্য)] ----
def _num(rx, scale=None):
    r = re.compile(rx, re.I)

    def f(v):
        m = r.search(v or "")
        if not m:
            return None
        x = float(m.group(1))
        if scale:
            x *= scale(m)
        return x
    return f


_gb = _num(r"(\d+(?:\.\d+)?)\s*(?:GB|TB)\b", lambda m: 1024 if "tb" in m.group(0).lower() else 1)
_ram = _num(r"(\d+)\s*GB")
COMPARE = {
    "laptop": [("র‍্যাম", _ram, "GB", "র‍্যাম"), ("স্টোরেজ", _gb, "GB", "স্টোরেজ")],
    "phone": [("র‍্যাম", _ram, "GB", "র‍্যাম"), ("স্টোরেজ", _gb, "GB", "স্টোরেজ"),
              ("ব্যাটারি", _num(r"(\d{3,5})\s*mAh"), "mAh", "ব্যাটারি")],
    "monitor": [("স্ক্রিন সাইজ", _num(r"(\d{2}(?:\.\d)?)\s*(?:\"|inch|ইঞ্চি|-inch|”)"), "ইঞ্চি", "স্ক্রিন"),
                ("রিফ্রেশ রেট", _num(r"(\d{2,3})\s*Hz"), "Hz", "রিফ্রেশ রেট")],
    "tv": [("স্ক্রিন সাইজ", _num(r"(\d{2,3})\s*(?:\"|inch|ইঞ্চি|-inch|”)"), "ইঞ্চি", "স্ক্রিন")],
    "fridge": [("মোট ক্ষমতা", _num(r"(\d{2,4})\s*(?:L\b|Ltr|Liter|Litre|লিটার)"), "লিটার", "ক্ষমতা")],
    "power_bank": [("ক্যাপাসিটি", _num(r"(\d{4,6})\s*mAh"), "mAh", "ক্যাপাসিটি")],
    "ssd": [("ক্যাপাসিটি", _gb, "GB", "ক্যাপাসিটি")],
    "gpu": [("ভিডিও মেমরি", _ram, "GB", "ভিডিও মেমরি")],
    "ups": [("ক্ষমতা", _num(r"(\d{3,5})\s*VA"), "VA", "ক্ষমতা")],
    "ram": [("ক্যাপাসিটি", _ram, "GB", "ক্যাপাসিটি")],
}


def fmt_val(x, unit):
    if unit == "GB" and x >= 1024 and x % 1024 == 0:
        return f"{bn(x // 1024)}TB"
    s = (f"{x:g}").translate(BN_DIGITS) if x != int(x) else bn(x)
    return f"{s}{unit}" if unit in ("GB", "mAh", "Hz", "VA") else f"{s} {unit}"


def spec_numbers(profile, feat_rows, name=""):
    """এক নজরের সারি থেকে তুলনার সংখ্যা: {ঘর: সংখ্যা}; নামে সংখ্যাটা লেখা থাকলে সেটাই আগে (নাম সাধারণত নির্ভুল)"""
    fr = dict(feat_rows or [])
    out = {}
    for label, fn, unit, _ in COMPARE.get(profile, []):
        v = fn(name) if unit != "GB" else None  # নামের "8GB" র‍্যাম না স্টোরেজ, বোঝা যায় না
        if not v and fr.get(label):
            v = fn(fr[label])
        if v:
            if v and v > 0:
                out[label] = v
    return out


def band_text(lo, hi):
    """৳৩৩–৪৩ হাজার / ৳৯০ হাজার–১.২ লাখ / ৳৭,৫০০–৯,০০০"""
    g = lambda x: f"{x:g}".translate(BN_DIGITS)
    if hi < 10000:
        return f"৳{bn(lo)}–{bn(hi)}"
    if hi < 100000:
        return f"৳{g(lo / 1000)}–{g(hi / 1000)} হাজার"
    if lo >= 100000:
        return f"৳{g(lo / 100000)}–{g(hi / 100000)} লাখ"
    return f"৳{g(lo / 1000)} হাজার–{g(hi / 100000)} লাখ"


def peer_band(price):
    """দামের কাছাকাছি সীমা (গোল সংখ্যায়, মানুষ যেভাবে বলে)"""
    step = 500 if price < 10000 else 1000 if price < 50000 else 5000 if price < 200000 else 10000
    lo = int(price * 0.88 // step * step)
    hi = int(-(-price * 1.12 // step) * step)
    return max(lo, step), hi


def build(pid, it, so, stores, leaf, changes, today, peers=None, rank=None, profile=None, nums=None, hint=None):
    """ফেরত: (বাক্যের তালিকা [(ধরন, লেখা)], মেটা বিবরণের ছোট অংশ, ডাটা-নির্ভর FAQ)"""
    sus = it.get("sus") or set()
    name_cat = leaf["name_bn"]
    out, meta, faq = [], [], []
    priced = sorted([(s, o) for s, o in so.items() if o.get("price") and o.get("in_stock") and s not in sus],
                    key=lambda x: x[1]["price"])
    listed = [s for s, o in so.items() if o.get("price") or o.get("in_stock") is not None]
    sn = lambda s: stores[s]["name"]

    # ১. আজকের দাম
    if len(priced) >= 2:
        (bs, bo), (ws, wo) = priced[0], priced[-1]
        diff = wo["price"] - bo["price"]
        pct = round(diff * 100 / wo["price"])
        if diff > 0:
            t = pick(pid, "today", [
                f"আজ {bn(len(priced))}টা দোকানে এই {name_cat} স্টকে আছে। সবচেয়ে কম দাম {sn(bs)}-এ, {tk(bo['price'])}। "
                f"সবচেয়ে বেশি দাম {sn(ws)}-এ ({tk(wo['price'])}), অর্থাৎ ঠিক দোকান বাছলে {tk(diff)} ({bn(pct)}%) কম লাগে।",
                f"{bn(len(priced))}টা দোকানের মধ্যে আজকের সর্বনিম্ন দাম {tk(bo['price'])}, {sn(bs)}-এ। "
                f"সবচেয়ে বেশি দামের দোকান {sn(ws)}-এর ({tk(wo['price'])}) চেয়ে এটা {tk(diff)} কম।",
                f"আজকের হিসাবে {sn(bs)}-এ দাম সবচেয়ে কম: {tk(bo['price'])}। একই প্রোডাক্ট {sn(ws)}-এ {tk(wo['price'])}, "
                f"দুই দোকানের পার্থক্য {tk(diff)} ({bn(pct)}%)। মোট {bn(len(priced))}টা দোকানে স্টকে আছে।",
            ])
        else:
            t = f"আজ {bn(len(priced))}টা দোকানে এই {name_cat} একই দামে পাওয়া যাচ্ছে: {tk(bo['price'])}।"
        out.append(("today", t))
        meta.append(f"আজ {bn(len(priced))} দোকানে, সর্বনিম্ন {tk(bo['price'])} ({sn(bs)})")
        rest = ", ".join(f"{sn(s)} {tk(o['price'])}" for s, o in priced[:4])
        faq.append(("কোন দোকানে সবচেয়ে কম দাম?", f"আজকের হিসাবে কম থেকে বেশি: {rest}। দামের পাশাপাশি ওয়ারেন্টি আর ডেলিভারি খরচও মিলিয়ে নিন।"))
    elif len(priced) == 1:
        bs, bo = priced[0]
        t = pick(pid, "today1", [
            f"আজ আমাদের তালিকার দোকানগুলোর মধ্যে শুধু {sn(bs)}-এ এই {name_cat} স্টকে আছে, দাম {tk(bo['price'])}।",
            f"এই মুহূর্তে শুধু {sn(bs)}-এ পাওয়া যাচ্ছে ({tk(bo['price'])})। অন্য দোকানে স্টক এলে বা মিল পাওয়া গেলে এখানে যোগ হবে।",
        ])
        out.append(("today", t))
        meta.append(f"আজ {tk(bo['price'])} ({sn(bs)})")
    elif it.get("any_price") and not sus:
        out.append(("today", f"আজ আমাদের তালিকার কোনো দোকানে এটা স্টকে নেই। শেষ জানা দাম {tk(it['any_price'])}।"))

    # ২. দামের প্রবণতা (ইতিহাস অন্তত ৭ দিনের হলে)
    if changes and len(changes) >= 7:
        days = (date.fromisoformat(today) - date.fromisoformat(changes[0][0])).days
        win = 30 if days >= 30 else 7
        cut = (date.fromisoformat(today) - timedelta(days=win)).isoformat()
        before = [v for d, v in changes if d <= cut] or [changes[0][1]]
        start, now = before[-1], changes[-1][1]
        inwin = [v for d, v in changes if d > cut]
        flips = sum(1 for a, b in zip([start] + inwin, inwin) if a != b)
        lab = "গত ৩০ দিনে" if win == 30 else "গত ৭ দিনে"
        lo_all = min(v for _, v in changes)
        if now < start:
            t = f"{lab} সর্বনিম্ন দাম {tk(start - now)} কমেছে ({tk(start)} থেকে {tk(now)})।"
            meta.append(f"{lab} {tk(start - now)} কমেছে")
        elif now > start:
            t = f"{lab} সর্বনিম্ন দাম {tk(now - start)} বেড়েছে ({tk(start)} থেকে {tk(now)})।"
        else:
            t = f"{lab} সর্বনিম্ন দাম বদলায়নি, {tk(now)}-এই আছে।"
        if flips >= 2:
            t += f" এই সময়ে দাম {bn(flips)} বার ওঠানামা করেছে।"
        if now == lo_all and max(v for _, v in changes) > lo_all:
            t += f" আজকের দাম আমাদের রেকর্ডে ({bn(days + 1)} দিনের) সবচেয়ে কম।"
        out.append(("trend", t))
        faq.append(("দাম কি সম্প্রতি কমেছে?", t))

    # ৩. স্টক
    oos = [s for s in listed if not (so[s].get("in_stock")) and s not in sus]
    if priced and oos and len(listed) >= 2:
        names = ", ".join(sn(s) for s in oos[:3]) + (" সহ আরও কয়েকটায়" if len(oos) > 3 else "-এ")
        out.append(("stock", pick(pid, "stock", [
            f"{bn(len(listed))}টা দোকানের তালিকায় আছে, তার মধ্যে {bn(len(priced))}টায় এখন স্টকে। {names} এখন স্টক নেই।",
            f"স্টক: {bn(len(priced))}টা দোকানে আছে, {names} নেই।",
        ])))

    # ৪. একই দামের অন্য প্রোডাক্টের সাথে তুলনা
    if peers and nums:
        lo, hi, group = peers
        unitmap = {l: (u, noun) for l, _, u, noun in COMPARE.get(profile, [])}
        bits = []
        for label, mine in nums.items():
            vals = [g[label] for g in group if label in g]
            if len(vals) < 8:
                continue
            mode, cnt = Counter(vals).most_common(1)[0]
            if cnt / len(vals) < 0.35:
                continue
            u, noun = unitmap[label]
            if mine > mode:
                bits.append(f"বেশিরভাগে {noun} {fmt_val(mode, u)}, এটায় {fmt_val(mine, u)}")
            elif mine < mode:
                bits.append(f"বেশিরভাগে {noun} {fmt_val(mode, u)}, এটায় কম ({fmt_val(mine, u)})")
            else:
                bits.append(f"{noun} বেশিরভাগের মতোই {fmt_val(mine, u)}")
        if bits:
            out.append(("peers", f"{band_text(lo, hi)} দামের মধ্যে আমাদের তালিকায় ({name_cat}) আরও {bn(len(group))}টা আছে। এগুলোর "
                        + "; ".join(bits) + "।"))

    # ৫. ক্যাটাগরিতে অবস্থান
    if rank:
        cheaper_than, total, brank, btotal, brand = rank
        if total >= 10:
            pct = round(cheaper_than * 100 / (total - 1)) if total > 1 else 0
            if pct >= 50:
                t = f"এই ক্যাটাগরিতে ({name_cat}) আজ {bn(total)}টা প্রোডাক্ট স্টকে আছে; এর {bn(pct)}%-এর চেয়ে এটা সস্তা।"
            else:
                t = f"এই ক্যাটাগরিতে ({name_cat}) আজ {bn(total)}টা প্রোডাক্ট স্টকে আছে; এর {bn(100 - pct)}%-এর চেয়ে এটার দাম বেশি।"
            if brand and btotal >= 3:
                t += f" {brand}-এর {bn(btotal)}টা মডেলের মধ্যে দাম কম থেকে গুনলে এটা {bn(brank)} নম্বরে।"
            out.append(("rank", t))

    # ৬. ছাড়
    for s, o in priced[:1]:
        reg = o.get("regular")
        if reg and reg > o["price"]:
            pct = round((reg - o["price"]) * 100 / reg)
            if 1 <= pct <= 60:
                out.append(("discount", f"{sn(s)} নিয়মিত দাম {tk(reg)} দেখাচ্ছে, এখন {tk(reg - o['price'])} ({bn(pct)}%) ছাড়ে বিক্রি করছে।"))

    if hint and out:
        out.append(("tip", hint))
    return out, meta, faq
