"""স্বয়ংক্রিয় মিল: আলাদা স্টোরে আলাদা নামে থাকা একই প্রোডাক্ট মডেল নম্বর দিয়ে জোড়া লাগানো।

নিশ্চিত মিল (নিজে থেকে জোড়া লাগে), সব শর্ত একসাথে:
- একই ক্যাটাগরি
- একই ব্র্যান্ড (বানান-ভেদ সহ: "1st" = "1STPLAYER", "A4tech" = "A4Tech"; এক দিকে ব্র্যান্ড না থাকলেও চলে)
- নামে একই "মডেল কোড" (অক্ষর+সংখ্যা মেশানো, ৪+ অক্ষর; যেমন SN850X, PS-600AX, CY12LD)। ব্র্যান্ডের নাম নিজে
  (1MORE, 1STPLAYER) মডেল কোড নয়।
- ক্যাপাসিটি/সাইজ (GB, TB, mAh, লিটার, কেজি, টন, ইঞ্চি, VA) দুই নামেই থাকলে হুবহু এক; অন্য সংখ্যা (W, Hz…) ভিন্ন নয়
- রং: দুই নামেই রং লেখা থাকলে একই রং (Black আর White আলাদা প্রোডাক্ট)
- ল্যাপটপ/ফোন/পিসি/টিভির মতো ক্যাটাগরিতে (একই মডেলে র‍্যাম/প্রসেসর ভেদ থাকে) দুই নামের সব মডেল কোড আর সব
  ক্যাপাসিটি হুবহু এক হতে হবে
- জোড়া লাগানোর পর এক প্রোডাক্টে একই দোকান দুইবার আসা চলবে না; সবচেয়ে মেলা জোড়া আগে লাগে

সম্ভাব্য মিল (অ্যাডমিনের "মিল যাচাই"-এ যায়, মানুষ হ্যাঁ/না বলে): মডেল কোড মেলে কিন্তু ওপরের কোনো একটা
শর্ত নিশ্চিত নয় (এক নামে র‍্যাম/স্টোরেজ লেখা নেই, একই বিভাগের ভিন্ন ক্যাটাগরি, ব্র্যান্ডের নাম ভিন্ন)।
অ্যাডমিনে "আলাদা" চাপলে (manual_matches.json-এর not_same) সেই জোড়া আর মিলবে না, প্রস্তাবেও আসবে না।
"""
import re
from collections import Counter, defaultdict

UNIT = re.compile(r"(\d+(?:\.\d+)?)\s*(gb|tb|mah|ltr|litre|liter|l|kg|ton|inch|va|w|hz|lumens?|mp|mm)\b", re.I)
STRICT = {"gb", "tb", "mah", "l", "kg", "ton", "inch", "va"}
NORM = {"ltr": "l", "litre": "l", "liter": "l", "lumen": "lumens"}
GENERIC = re.compile(r"(gen|pcie|usb|ddr|gddr|wifi|wi|ax|ac|be|rtx|gtx|rx|hdmi|ipx?|bt|v)\d", re.I)
SKIP = re.compile(r"\d+(gb|tb|mb|w|hz|mah|l|kg|va|mm|th|nd|rd|st|gen|mhz|k|p|x|m|cm|ft|v|a|ah|pcs|in1)$", re.I)
COLORS = {"black", "white", "red", "blue", "green", "pink", "silver", "gold", "grey", "gray", "purple", "yellow",
          "orange", "brown", "beige", "titanium", "graphite", "midnight", "starlight", "cream", "navy", "violet",
          "lavender", "mint", "rose", "copper", "bronze"}
COLOR_ALIAS = {"gray": "grey"}
# এক মডেলে র‍্যাম/প্রসেসর/স্টোরেজ ভেদ থাকে, তাই নাম পুরোপুরি মিলতে হয়
STRICT_CATS = {"gaming-laptop", "ultrabook", "laptop", "gaming-pc", "ai-pc", "brand-pc", "all-in-one-pc", "mini-pc",
               "mac-desktop", "desktop-pc", "smartphone", "feature-phone", "tablet", "tv", "workstation", "server"}
STOPWORDS = {"the", "and", "with", "for", "of", "in", "new", "original", "official", "edition", "version", "bd"}


def units(name):
    out = defaultdict(set)
    for n, u in UNIT.findall(name):
        u = NORM.get(u.lower(), u.lower())
        out[u].add(float(n))
    return out


def bare_numbers(name):
    """৩+ অঙ্কের খালি সংখ্যা (RTX 3060, Core 7 155H-এর 155 নয়): দুই নামে ভিন্ন হলে আলাদা প্রোডাক্ট।"""
    return set(re.findall(r"(?<![\w.])(\d{3,5})(?![\w.])", name))


def numbers_ok(a, b):
    na, nb = bare_numbers(a), bare_numbers(b)
    return not na or not nb or na <= nb or nb <= na


def compatible(a, b):
    if not numbers_ok(a, b):
        return False
    ua, ub = units(a), units(b)
    for u in set(ua) | set(ub):
        if u in STRICT:
            if ua.get(u) != ub.get(u):
                return False
        elif u in ua and u in ub and ua[u] != ub[u]:
            return False
    return True


def soft_compatible(a, b):
    """এক নামে ক্যাপাসিটি লেখা নেই, কিন্তু যা দুই দিকে আছে তাতে কোনো অমিল নেই।"""
    if not numbers_ok(a, b):
        return False
    ua, ub = units(a), units(b)
    return all(ua[u] == ub[u] for u in set(ua) & set(ub))


def brand_key(b):
    return re.sub(r"[^a-z0-9]", "", (b or "").lower())


def same_brand(a, b):
    a, b = brand_key(a), brand_key(b)
    if not a or not b or a in ("others", "other", "generic") or b in ("others", "other", "generic"):
        return True
    return a == b or (min(len(a), len(b)) >= 3 and (a.startswith(b) or b.startswith(a)))


def colors(name):
    return {COLOR_ALIAS.get(w, w) for w in re.findall(r"[a-z]+", name.lower()) if w in COLORS}


def models(name, brand=None):
    out = set()
    bk = brand_key(brand)
    for t in re.split(r"[\s,()/\[\]|#]+", name):
        t = t.strip(".-").lower()
        if (len(t) >= 4 and re.search(r"\d", t) and re.search(r"[a-z]", t)
                and not SKIP.fullmatch(t) and not GENERIC.match(t)):
            k = t.replace("-", "")
            if bk and (k == bk or (len(bk) >= 3 and bk.startswith(k))):
                continue  # ব্র্যান্ডের নাম (1MORE, 1STPLAYER) মডেল নয়
            out.add(k)
    return out


def words(name):
    return {w for w in re.findall(r"[a-z0-9]+", name.lower()) if w not in STOPWORDS and len(w) > 1}


FILLER = {"gaming", "wireless", "with", "price", "bd", "original", "official", "new", "edition", "version", "series",
          "model", "genuine", "the", "and", "for"}


def signature(name):
    """নামের অর্থবহ শব্দের সেট: ক্রম, বড়-ছোট হাতের অক্ষর, রং আর ফালতু শব্দ বাদ; সংখ্যা+একক এক শব্দ।"""
    n = re.sub(r"(\d+(?:\.\d+)?)\s*(gb|tb|mah|w|hz|inch|mm|l|kg|va|mp)\b", r"\1\2", name.lower())
    return frozenset(w for w in re.findall(r"[a-z0-9.]+", n) if w.strip(".") and w not in FILLER and w not in COLORS)


def _score(a, b):
    wa, wb = words(a), words(b)
    return len(wa & wb) / max(1, len(wa | wb))


def match_pairs(products, offers, not_same=(), group_of=None):
    """ফেরত: (নিশ্চিত জোড়া [(score, a, b)], সম্ভাব্য জোড়া [(score, a, b, কারণ)])"""
    blocked = set(not_same)
    group_of = group_of or {}
    by = defaultdict(list)
    for pid in offers:
        p = products.get(pid)
        if not p:
            continue
        for m in models(p["name"], p.get("brand")):
            by[m].append(pid)
    sure, maybe, seen = [], [], set()
    for m, ids in by.items():
        if len(ids) < 2 or len(ids) > 12:  # ১২টার বেশি প্রোডাক্টে থাকা কোড আসলে সিরিজের নাম
            continue
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                key = "|".join(sorted((a, b)))
                if key in seen or key in blocked:
                    continue
                seen.add(key)
                if set(offers[a]) & set(offers[b]):
                    continue
                pa, pb = products[a], products[b]
                na, nb = pa["name"], pb["name"]
                ca, cb = colors(na), colors(nb)
                if ca and cb and not (ca & cb):
                    continue
                if not same_brand(pa.get("brand"), pb.get("brand")):
                    # ব্র্যান্ড ভিন্ন লেখা: নামের প্রথম শব্দ মিললে শুধু প্রস্তাব
                    if na.split()[0].lower() == nb.split()[0].lower() and compatible(na, nb):
                        maybe.append((_score(na, nb), a, b, "ব্র্যান্ডের নাম ভিন্ন"))
                    continue
                sc = _score(na, nb)
                same_cat = pa["category"] == pb["category"]
                if not same_cat:
                    if group_of.get(pa["category"]) == group_of.get(pb["category"]) and soft_compatible(na, nb) and sc >= 0.35:
                        maybe.append((sc, a, b, "ভিন্ন ক্যাটাগরি"))
                    continue
                if pa["category"] in STRICT_CATS:
                    if models(na, pa.get("brand")) == models(nb, pb.get("brand")) and compatible(na, nb):
                        sure.append((sc, a, b))
                    elif soft_compatible(na, nb) and sc >= 0.4:
                        maybe.append((sc, a, b, "কনফিগারেশন যাচাই দরকার"))
                    continue
                if compatible(na, nb):
                    sure.append((sc, a, b))
                elif soft_compatible(na, nb):
                    maybe.append((sc, a, b, "এক নামে সাইজ/ক্যাপাসিটি লেখা নেই"))
    # মডেল কোড নেই এমন নাম (Galaxy A16, Freezer 36): একই ক্যাটাগরি ও ব্র্যান্ডে অর্থবহ শব্দ হুবহু এক হলে নিশ্চিত,
    # অনেকটা কাছাকাছি হলে প্রস্তাব
    bucket = defaultdict(list)
    for pid in offers:
        p = products.get(pid)
        if p:
            bucket[(p["category"], brand_key(p.get("brand"))[:3])].append(pid)
    for ids in bucket.values():
        if len(ids) < 2:
            continue
        sig = {x: signature(products[x]["name"]) for x in ids}
        inv = defaultdict(list)
        for x in ids:
            for w in sig[x]:
                inv[w].append(x)
        for a in ids:
            pa = products[a]
            cand = Counter()
            for w in sig[a]:
                if len(inv[w]) <= 200:
                    cand.update(inv[w])
            for b, _n in cand.most_common(20):
                if b <= a:
                    continue
                key = "|".join(sorted((a, b)))
                if key in seen or key in blocked:
                    continue
                pb = products[b]
                if set(offers[a]) & set(offers[b]) or not same_brand(pa.get("brand"), pb.get("brand")):
                    continue
                sa, sb = sig[a], sig[b]
                j = len(sa & sb) / max(1, len(sa | sb))
                if j < 0.7:
                    continue
                ca, cb = colors(pa["name"]), colors(pb["name"])
                if ca and cb and not (ca & cb):
                    continue
                seen.add(key)
                if sa == sb and compatible(pa["name"], pb["name"]):
                    sure.append((1.0, a, b))
                elif soft_compatible(pa["name"], pb["name"]):
                    maybe.append((j, a, b, "নাম প্রায় এক"))
    return sure, maybe


def auto_merges(products, offers, not_same=(), group_of=None, with_suggestions=False):
    """ফেরত: {বাদ-যাওয়া id: রাখা id} (with_suggestions হলে সাথে সম্ভাব্য জোড়ার তালিকা)"""
    sure, maybe = match_pairs(products, offers, not_same, group_of)
    blocked = set(not_same)
    par, members = {}, {}

    def find(x):
        par.setdefault(x, x)
        members.setdefault(x, {x})
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    # সবচেয়ে মেলা জোড়া আগে; জোড়া লাগালে এক প্রোডাক্টে একই দোকান দুইবার বা দুই রং এলে সেই জোড়া বাদ
    for sc, a, b in sorted(sure, key=lambda x: -x[0]):
        ra, rb = find(a), find(b)
        if ra == rb:
            continue
        ga, gb = members[ra], members[rb]
        if {s for x in ga for s in offers[x]} & {s for x in gb for s in offers[x]}:
            continue
        cl = [colors(products[x]["name"]) for x in ga | gb]
        cl = [c for c in cl if c]
        if cl and any(not (c & cl[0]) for c in cl[1:]):
            continue
        if any("|".join(sorted((x, y))) in blocked for x in ga for y in gb):
            continue
        par[ra] = rb
        members[rb] = ga | gb
    out = {}
    for r, g in members.items():
        if find(r) != r or len(g) < 2:
            continue
        keep = sorted(g, key=lambda x: (-len(offers[x]), products[x]["created"], len(x)))[0]
        for x in g:
            if x != keep:
                out[x] = keep
    if not with_suggestions:
        return out
    # প্রস্তাব: যা নিজে থেকে জোড়া লাগেনি আর জোড়া লাগালে দোকান দুইবার আসে না
    grp = defaultdict(set)
    for k, v in out.items():
        grp[v].add(k)
    sugg, used = [], set()
    for sc, a, b, why in sorted(maybe, key=lambda x: -x[0]):
        ka, kb = out.get(a, a), out.get(b, b)
        if ka == kb or "|".join(sorted((ka, kb))) in used:
            continue
        used.add("|".join(sorted((ka, kb))))
        sa = {s for x in grp[ka] | {ka} for s in offers[x]}
        sb = {s for x in grp[kb] | {kb} for s in offers[x]}
        if sa & sb:
            continue
        sugg.append({"a": ka, "b": kb, "score": round(sc, 2), "why": why,
                     "a_name": products[ka]["name"], "b_name": products[kb]["name"]})
    return out, sugg
