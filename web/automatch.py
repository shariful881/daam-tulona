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

UNIT = re.compile(r"(\d+(?:\.\d+)?)[\s-]*(gb|tb|mah|ltr|litre|liter|l|kg|ton|inch|va|w|hz|lumens?|mp|mm|pack|pcs|users?)\b", re.I)
STRICT = {"gb", "tb", "mah", "l", "kg", "ton", "inch", "va", "pack", "user", "users"}
NORM = {"ltr": "l", "litre": "l", "liter": "l", "lumen": "lumens"}
GENERIC = re.compile(r"(gen|pcie|usb|ddr|gddr|wifi|wi|ax|ac|be|rtx|gtx|rx|hdmi|ipx?|bt|v)\d", re.I)
SKIP = re.compile(r"\d+(gb|tb|mb|w|hz|mah|l|kg|va|mm|th|nd|rd|st|gen|mhz|k|p|x|m|cm|ft|v|a|ah|pcs|in1)$", re.I)
COLORS = {"black", "white", "red", "blue", "green", "pink", "silver", "gold", "grey", "gray", "purple", "yellow",
          "orange", "brown", "beige", "titanium", "graphite", "midnight", "starlight", "cream", "navy", "violet",
          "lavender", "mint", "rose", "copper", "bronze", "cyan", "magenta", "ice", "snow"}
COLOR_ALIAS = {"gray": "grey"}
# এক মডেলে র‍্যাম/প্রসেসর/স্টোরেজ ভেদ থাকে, তাই নাম পুরোপুরি মিলতে হয়
STRICT_CATS = {"gaming-laptop", "ultrabook", "laptop", "gaming-pc", "ai-pc", "brand-pc", "all-in-one-pc", "mini-pc",
               "mac-desktop", "desktop-pc", "smartphone", "feature-phone", "tablet", "tv", "workstation", "server"}
STOPWORDS = {"the", "and", "with", "for", "of", "in", "new", "original", "official", "edition", "version", "bd"}


INCH = re.compile(r"(\d+(?:\.\d+)?)\s*(?:\"|″|''|”|-inch\b)")


def units(name):
    out = defaultdict(set)
    for n, u in UNIT.findall(INCH.sub(r"\1 inch", name)):
        u = NORM.get(u.lower(), u.lower())
        out[u].add(float(n))
    return out


def bare_numbers(name):
    """৩+ অঙ্কের খালি সংখ্যা (RTX 3060, Core 7 155H-এর 155 নয়): দুই নামে ভিন্ন হলে আলাদা প্রোডাক্ট।"""
    return set(re.findall(r"(?<![\w.])(\d{3,5})(?![\w.])", name))


def numbers_ok(a, b):
    na, nb = bare_numbers(a), bare_numbers(b)
    return not na or not nb or na <= nb or nb <= na


CONFLICT = [({"laptop", "notebook", "sodimm", "so-dimm"}, {"desktop", "udimm", "u-dimm"}), ({"tray", "oem", "bulk"}, {"box", "boxed"}),
            ({"refurbished", "used"}, {"brand-new"})]


def word_conflict(a, b):
    wa, wb = set(re.findall(r"[a-z-]+", a.lower())), set(re.findall(r"[a-z-]+", b.lower()))
    return any((wa & x and wb & y and not wa & y) or (wa & y and wb & x and not wa & x) for x, y in CONFLICT)


def compatible(a, b):
    if not numbers_ok(a, b) or word_conflict(a, b):
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
    n = re.sub(r"\b80\s*(\+|plus)", " 80plus ", name.lower())
    n = re.sub(r"(\d+(?:\.\d+)?)\s*(gb|tb|mah|w|hz|inch|mm|l|kg|va|mp)\b", r"\1\2", n)
    ws = {w for w in re.findall(r"[a-z0-9.]+", n) if w.strip(".") and w not in FILLER and w not in COLORS}
    # "850 850W" — খালি সংখ্যাটা একক-সহ সংখ্যার পুনরাবৃত্তি হলে বাদ
    return frozenset(w for w in ws if not (w.isdigit() and any(x != w and x.startswith(w) and not x[len(w)].isdigit() for x in ws)))


VARIANT = {"pro", "max", "plus", "ultra", "mini", "lite", "se", "air", "neo", "prime", "fe", "he", "slim", "nano",
           "turbo", "elite", "evo", "edge", "fold", "flip", "note", "go", "x", "s", "t", "e", "v2", "v3", "gen2", "ii",
           "iii", "iv", "anc", "enc", "ti", "super", "ex", "xt", "xtx", "oc", "hd", "fhd", "qhd", "uhd", "4k", "oled", "tkl", "rgb", "argb", "digital"}


def _category_words(products, offers):
    """প্রতিটা ক্যাটাগরির নামে খুব বেশি আসে এমন বর্ণনার শব্দ (মডেল/ভেরিয়েন্ট নয়)।"""
    by = defaultdict(list)
    for pid in offers:
        p = products.get(pid)
        if p:
            by[p["category"]].append(signature(p["name"]))
    out = {}
    for c, sigs in by.items():
        if len(sigs) < 20:
            continue
        df = Counter(w for sg in sigs for w in sg)
        out[c] = frozenset(w for w, n in df.items() if n >= 0.08 * len(sigs) and not re.search(r"\d", w) and w not in VARIANT)
    return out


def _score(a, b):
    wa, wb = words(a), words(b)
    return len(wa & wb) / max(1, len(wa | wb))


def match_pairs(products, offers, not_same=(), group_of=None):
    """ফেরত: (নিশ্চিত জোড়া [(score, a, b)], সম্ভাব্য জোড়া [(score, a, b, কারণ)])"""
    blocked = set(not_same)
    group_of = group_of or {}
    by, nocap = defaultdict(list), defaultdict(list)
    for pid in offers:
        p = products.get(pid)
        if not p:
            continue
        su = units(p["name"])
        cap = tuple(sorted((u, tuple(sorted(v))) for u, v in su.items() if u in STRICT))
        for m in models(p["name"], p.get("brand")):
            by[(m, cap)].append(pid)  # একই কোডের ভিন্ন ক্যাপাসিটি আলাদা দলে, তাই সিরিজ বড় হলেও মেলে
            if not cap:
                nocap[m].append(pid)
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
                    same_grp = group_of.get(pa["category"]) == group_of.get(pb["category"])
                    strict_any = pa["category"] in STRICT_CATS or pb["category"] in STRICT_CATS
                    hard = {"laptop-ram", "desktop-ram", "processor", "graphics-card", "ssd", "hdd", "portable-ssd", "portable-hdd", "motherboard"}
                    if same_grp and not strict_any and not ({pa["category"], pb["category"]} & hard) and compatible(na, nb) and sc >= 0.7:
                        sure.append((sc, a, b))  # দোকানভেদে ক্যাটাগরি আলাদা (neckband / earphone), নাম প্রায় হুবহু
                    elif same_grp and soft_compatible(na, nb) and sc >= 0.35:
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
    # এক নামে ক্যাপাসিটি লেখা নেই (Samsung T7 / Samsung T7 1TB): শুধু প্রস্তাব
    for (m, cap), ids in by.items():
        if not cap or not nocap.get(m) or len(nocap[m]) > 6 or len(ids) > 12:
            continue
        for a in nocap[m]:
            for b in ids:
                key = "|".join(sorted((a, b)))
                if key in seen or key in blocked or set(offers[a]) & set(offers[b]):
                    continue
                pa, pb = products[a], products[b]
                if pa["category"] != pb["category"] or not same_brand(pa.get("brand"), pb.get("brand")):
                    continue
                ca, cb = colors(pa["name"]), colors(pb["name"])
                if (ca and cb and not (ca & cb)) or not soft_compatible(pa["name"], pb["name"]):
                    continue
                seen.add(key)
                maybe.append((_score(pa["name"], pb["name"]), a, b, "এক নামে সাইজ/ক্যাপাসিটি লেখা নেই"))
    # মডেল কোড নেই বা ছোট (QCY T13 Pro, Onikuma G67, Amazfit Balance): ক্যাটাগরির সাধারণ বর্ণনার শব্দ (earbuds,
    # bluetooth, mechanical, keyboard…) বাদ দিলে বাকি "মূল নাম" হুবহু এক হলে নিশ্চিত। একই বিভাগে দোকানভেদে ক্যাটাগরি
    # আলাদা হলেও (neckband / earphone) চলে।
    common = _category_words(products, offers)
    bucket = defaultdict(list)
    for pid in offers:
        p = products.get(pid)
        if p:
            bucket[(group_of.get(p["category"], p["category"]), brand_key(p.get("brand"))[:3])].append(pid)
    for ids in bucket.values():
        if len(ids) < 2 or len(ids) > 4000:
            continue
        core = {x: signature(products[x]["name"]) - common.get(products[x]["category"], frozenset()) for x in ids}
        inv = defaultdict(list)
        for x in ids:
            for w in core[x]:
                inv[w].append(x)
        for a in ids:
            pa = products[a]
            cand = Counter()
            for w in core[a]:
                if len(inv[w]) <= 300:
                    cand.update(inv[w])
            for b, _n in cand.most_common(25):
                if b <= a:
                    continue
                key = "|".join(sorted((a, b)))
                if key in seen or key in blocked:
                    continue
                pb = products[b]
                if set(offers[a]) & set(offers[b]) or not same_brand(pa.get("brand"), pb.get("brand")):
                    continue
                na, nb = pa["name"], pb["name"]
                ca, cb = colors(na), colors(nb)
                if ca and cb and not (ca & cb):
                    continue
                cmn = common.get(pa["category"], frozenset()) | common.get(pb["category"], frozenset())
                sa, sb = core[a] - cmn, core[b] - cmn
                j = len(sa & sb) / max(1, len(sa | sb))
                if j < 0.5:
                    continue
                seen.add(key)
                strict_cat = pa["category"] in STRICT_CATS or pb["category"] in STRICT_CATS
                ok = compatible(na, nb)
                ma, mb = models(na, pa.get("brand")), models(nb, pb.get("brand"))
                if ma and mb and not (ma & mb):
                    ok = False  # দুই নামেই মডেল কোড আছে কিন্তু আলাদা (LMB-280U / DM-280U)
                da, db = {w for w in sa if re.search(r"\d", w)}, {w for w in sb if re.search(r"\d", w)}
                va, vb = sa & VARIANT, sb & VARIANT
                if ok and len(sa) >= 2 and sa == sb:
                    sure.append((1.0, a, b))
                elif (ok and not strict_cat and da and da == db and va == vb
                      and any(len(w) >= 3 and re.search(r"[a-z]", w) and not SKIP.fullmatch(w) and not GENERIC.match(w) for w in da)
                      and not (pa["category"] != pb["category"] and j < 0.6)):
                    sure.append((0.9, a, b))
                elif soft_compatible(na, nb) and j >= 0.6:
                    maybe.append((j, a, b, "নাম প্রায় এক" if pa["category"] == pb["category"] else "ভিন্ন ক্যাটাগরি"))
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
    # হুবহু একই নাম = একই প্রোডাক্ট (দোকান একই জিনিস দুইবার তুললে নামের শেষে -2, -3 হয়)।
    # একই দোকানে দুইবার থাকলে তখনই মেলে যখন দুইটার দাম এক বা একটার দাম নেই (ভিন্ন দাম = আলাদা ভ্যারিয়েন্ট);
    # ভিন্ন দোকানে দামের ফারাক ৩৫%-এর বেশি হলে মেলে না।
    by_name = defaultdict(list)
    for pid in offers:
        if pid in products:
            by_name[" ".join(re.sub(r"[^\w.]+", " ", products[pid]["name"].lower()).split())].append(pid)

    def prices(g):
        return [o.get("price") for x in g for o in offers[x].values() if o.get("price")]
    for ids in by_name.values():
        for a in ids[1:]:
            ra, rb = find(a), find(ids[0])
            if ra == rb:
                continue
            ga, gb = members[ra], members[rb]
            if any("|".join(sorted((x, y))) in blocked for x in ga for y in gb):
                continue
            clash = False
            for s in {s for x in ga for s in offers[x]} & {s for x in gb for s in offers[x]}:
                pa = {offers[x][s].get("price") for x in ga if s in offers[x]} - {None}
                pb = {offers[x][s].get("price") for x in gb if s in offers[x]} - {None}
                if pa and pb and pa != pb:
                    clash = True
            la, lb = prices(ga), prices(gb)
            if clash or (la and lb and max(min(la), min(lb)) > 1.35 * min(min(la), min(lb))):
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
