"""স্বয়ংক্রিয় মিল: আলাদা স্টোরে আলাদা নামে থাকা একই প্রোডাক্ট মডেল নম্বর দিয়ে জোড়া লাগানো।

নিয়ম (সব শর্ত একসাথে):
- একই ক্যাটাগরি, একই ব্র্যান্ড
- নামে একই "মডেল কোড" (অক্ষর+সংখ্যা মেশানো, ৪+ অক্ষর; যেমন SN850X, WFB-2B6-GDEH-SC, B135N)
- ক্যাপাসিটি/সাইজ (GB, TB, mAh, লিটার, কেজি, টন, ইঞ্চি, VA) দুই নামেই থাকতে হবে আর হুবহু এক
- অন্য সংখ্যা (W, Hz, lumens, MP…) এক নামে থাকলে আরেকটায় ভিন্ন হতে পারবে না
- দুইটার একই স্টোরে দাম থাকা চলবে না (একই স্টোরে দুইটা = আলাদা জিনিস)
- একটা মডেল কোড ৬টার বেশি প্রোডাক্টে থাকলে সেটা সিরিজের নাম, মডেল নয় — বাদ
অ্যাডমিনে "আলাদা" চাপলে (manual_matches.json-এর not_same) সেই জোড়া আর মিলবে না।
"""
import re
from collections import defaultdict

UNIT = re.compile(r"(\d+(?:\.\d+)?)\s*(gb|tb|mah|ltr|litre|liter|l|kg|ton|inch|va|w|hz|lumens?|mp|mm)\b", re.I)
STRICT = {"gb", "tb", "mah", "l", "kg", "ton", "inch", "va"}
NORM = {"ltr": "l", "litre": "l", "liter": "l", "lumen": "lumens"}
GENERIC = re.compile(r"(gen|pcie|usb|ddr|gddr|wifi|wi|ax|ac|be|rtx|gtx|rx|hdmi|ipx?|bt|v)\d", re.I)
SKIP = re.compile(r"\d+(gb|tb|mb|w|hz|mah|l|kg|va|mm|th|nd|rd|st|gen|mhz|k|p|x|m|cm|ft|v|a|ah|pcs|in1)$", re.I)


def units(name):
    out = defaultdict(set)
    for n, u in UNIT.findall(name):
        u = NORM.get(u.lower(), u.lower())
        out[u].add(float(n))
    return out


def compatible(a, b):
    ua, ub = units(a), units(b)
    for u in set(ua) | set(ub):
        if u in STRICT:
            if ua.get(u) != ub.get(u):
                return False
        elif u in ua and u in ub and ua[u] != ub[u]:
            return False
    return True


def models(name):
    out = set()
    for t in re.split(r"[\s,()/\[\]|#]+", name):
        t = t.strip(".-").lower()
        if (len(t) >= 4 and re.search(r"\d", t) and re.search(r"[a-z]", t)
                and not SKIP.fullmatch(t) and not GENERIC.match(t)):
            out.add(t.replace("-", ""))
    return out


def auto_merges(products, offers, not_same=()):
    """ফেরত: {বাদ-যাওয়া id: রাখা id}"""
    blocked = set(not_same)
    by = defaultdict(list)
    for pid in offers:
        p = products.get(pid)
        if not p:
            continue
        for m in models(p["name"]):
            by[(p["category"], (p.get("brand") or "").lower(), m)].append(pid)
    par = {}

    def find(x):
        par.setdefault(x, x)
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    for ids in by.values():
        if len(ids) < 2 or len(ids) > 6:
            continue
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                if "|".join(sorted((a, b))) in blocked or set(offers[a]) & set(offers[b]):
                    continue
                if compatible(products[a]["name"], products[b]["name"]):
                    par[find(a)] = find(b)
    groups = defaultdict(list)
    for x in list(par):
        groups[find(x)].append(x)
    out = {}
    for g in groups.values():
        if len(g) < 2:
            continue
        stores = [s for x in g for s in offers[x]]
        if len(stores) != len(set(stores)):  # গ্রুপে একই স্টোর দুইবার = সন্দেহজনক, পুরো গ্রুপ বাদ
            continue
        if any("|".join(sorted((a, b))) in blocked for a in g for b in g if a < b):
            continue
        keep = sorted(g, key=lambda x: (-len(offers[x]), products[x]["created"], len(x)))[0]
        for x in g:
            if x != keep:
                out[x] = keep
    return out
