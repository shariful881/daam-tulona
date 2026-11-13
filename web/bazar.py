"""বাজার আপডেট: দামের ইতিহাস থেকে বিশ্লেষণধর্মী রিপোর্ট (আজকের বাজার, ক্যাটাগরির সাপ্তাহিক, সপ্তাহের ডিল, মাসিক)।

নিয়ম (সাইটে কোথাও প্রকাশ হয় না):
- সন্দেহজনক দাম (it["sus"]), বন্ধ দোকান, আর এক দিনে MAX_JUMP-এর বেশি লাফ কোনো হিসাবে ঢোকে না।
- যে রিপোর্টে বলার মতো খবর নেই (শর্ত WORTHY_*), সেটা তৈরিই হয় না: noindex খবর-পাতা বলে কিছু নেই।
- সাপ্তাহিক/মাসিক রিপোর্ট প্রথমে খসড়া (data/reports/<id>.json, একবার তৈরি হলে আর বদলায় না)।
  অ্যাডমিন → বাজার রিপোর্টে সম্পাদকের মন্তব্য লিখে "প্রকাশ" দিলে (data/report_status.json) তবেই পাতা হয়।
- আজকের বাজার (/bazar/aj/) একটাই পাতা, প্রতিদিন নতুন করে লেখা হয়।
"""
import json
from datetime import date, timedelta
from html import escape

MAX_JUMP = 0.4        # এর বেশি বদল ভুল দাম ধরে বাদ
MIN_PRICE = 300       # এর কম দামের জিনিস (কেবল, স্টিকার) খবরে আসে না
WORTHY_WEEK = 8       # ক্যাটাগরির সাপ্তাহিক রিপোর্ট: অন্তত এতগুলো প্রোডাক্টের দাম বদল
WORTHY_WEEK_ALT = (4, 5)  # অথবা: অন্তত ৪টা দাম বদল + ৫টা নতুন মডেল
WORTHY_DEALS = 6      # সপ্তাহের ডিল: অন্তত এতগুলো ভালো ডিল
MONTH_MIN_DAYS = 20   # মাসিক রিপোর্টে মাসের অন্তত এত দিনের ইতিহাস লাগবে
EDITOR = "শরীফুল ইসলাম"

REPORT_CATS = [
    ("ssd", "এসএসডি", ["ssd", "portable-ssd"]),
    ("ram", "র‍্যাম", ["desktop-ram", "laptop-ram"]),
    ("monitor", "মনিটর", ["monitor-all", "gaming-monitor", "portable-monitor"]),
    ("laptop", "ল্যাপটপ", ["laptop", "gaming-laptop"]),
    ("graphics-card", "গ্রাফিক্স কার্ড", ["graphics-card"]),
    ("processor", "প্রসেসর", ["processor"]),
]
DAILY_TABS = [("all", "সব", None)] + REPORT_CATS + [("mobile", "মোবাইল", ["smartphone", "feature-phone"])]
CAT_NAME = {k: n for k, n, _ in REPORT_CATS}
NO_GAP = {"smartphone", "feature-phone", "tablet"}  # অফিসিয়াল/আনঅফিসিয়াল দামে পার্থক্য স্বাভাবিক
BN = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
MONTHS = ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"]
POSS = {"ssd": "এসএসডির", "ram": "র‍্যামের", "monitor": "মনিটরের", "laptop": "ল্যাপটপের", "graphics-card": "গ্রাফিক্স কার্ডের",
        "processor": "প্রসেসরের", "mobile": "মোবাইলের"}


def bn(n):
    return f"{int(n):,}".translate(BN)


def tk(n):
    return "৳" + bn(abs(int(n)))


def pct_s(x, signed=False):
    s = f"{abs(x):.1f}".rstrip("0").rstrip(".") if abs(x) < 10 else f"{abs(x):.0f}"
    return (("+" if x > 0 else "−" if x < 0 else "") if signed else "") + s.translate(BN) + "%"


def dmy(d, year=True):
    d = date.fromisoformat(d) if isinstance(d, str) else d
    return f"{bn(d.day)} {MONTHS[d.month - 1]}" + (f" {str(d.year).translate(BN)}" if year else "")


def span_bn(a, b):
    a, b = date.fromisoformat(a), date.fromisoformat(b)
    if a.month == b.month:
        return f"{bn(a.day)}–{bn(b.day)} {MONTHS[b.month - 1]} {str(b.year).translate(BN)}"
    return f"{dmy(a, a.year != b.year)} – {dmy(b)}"


def short(s, k=42):
    return s if len(s) <= k else s[:k - 1].rstrip() + "…"


# ---------------- হিসাব ----------------

class Hist:
    def __init__(self, history, items, enabled):
        self.items, self.enabled = items, enabled
        self.h = {pid: {s: sorted(ch) for s, ch in ss.items()} for pid, ss in history.items() if pid in items}
        self.dates = sorted({d for ss in self.h.values() for ch in ss.values() for d, _ in ch})

    @staticmethod
    def at(ch, d):
        v = None
        for ds, p in ch:
            if ds > d:
                break
            v = p
        return v

    def changes(self, d0, d1, cats=None):
        """d0 → d1: প্রতিটা প্রোডাক্টের সবচেয়ে বড় (একই দোকানের) দাম বদল।"""
        out = []
        for pid, ss in self.h.items():
            it = self.items[pid]
            if cats is not None and it["category"] not in cats:
                continue
            best = None
            for s, ch in ss.items():
                if s not in self.enabled or s in it["sus"] or ch[-1][0] <= d0:
                    continue
                p0, p1 = self.at(ch, d0), self.at(ch, d1)
                if not p0 or not p1 or p0 == p1 or p0 < MIN_PRICE or abs(p1 - p0) / p0 > MAX_JUMP:
                    continue
                if best is None or abs(p1 - p0) > abs(best[2] - best[1]):
                    best = (s, p0, p1)
            if best:
                s, p0, p1 = best
                out.append({"id": pid, "name": it["name"], "category": it["category"], "cat_name": it["cat_name"], "store": s,
                            "old": p0, "new": p1, "diff": p1 - p0, "pct": (p1 - p0) / p0 * 100})
        return out

    def index(self, d0, d1, cats):
        """ক্যাটাগরির গড় দাম পরিবর্তন (%): দুই দিনই স্টকে থাকা সব জোড়া (না বদলালে ০)।"""
        per = []
        for pid, ss in self.h.items():
            it = self.items[pid]
            if it["category"] not in cats:
                continue
            r = []
            for s, ch in ss.items():
                if s not in self.enabled or s in it["sus"]:
                    continue
                p0, p1 = self.at(ch, d0), self.at(ch, d1)
                if p0 and p1 and p0 >= MIN_PRICE and abs(p1 - p0) / p0 <= MAX_JUMP:
                    r.append((p1 - p0) / p0)
            if r:
                per.append(sum(r) / len(r))
        return (sum(per) / len(per) * 100 if per else 0.0), len(per)


def gaps(items, cats=None, n=5):
    out = []
    for it in items.values():
        if not it["best"] or not it["worst"] or it["live_count"] < 2 or it["category"] in NO_GAP or "software" in it["category"]:
            continue
        if cats is not None and it["category"] not in cats:
            continue
        lo, hi = it["best"]["price"], it["worst"]["price"]
        if lo >= 3000 and hi <= lo * 1.3 and hi - lo >= 500:
            out.append({"id": it["id"], "name": it["name"], "cat_name": it["cat_name"], "lo": lo, "los": it["best"]["store"],
                        "hi": hi, "his": it["worst"]["store"], "diff": hi - lo, "n": it["live_count"]})
    return sorted(out, key=lambda g: -g["diff"])[:n]


def new_models(items, d0, d1, cats=None, n=8, min_price=0):
    allnew = [it for it in items.values() if d0 < it["created"] <= d1 and it["best"] and (cats is None or it["category"] in cats)]
    out = [it for it in allnew if it["best"]["price"] >= min_price]
    out.sort(key=lambda it: (-it["live_count"], -it["best"]["price"]))
    return [{"id": it["id"], "name": it["name"], "cat_name": it["cat_name"], "price": it["best"]["price"],
             "store": it["best"]["store"], "n": it["live_count"]} for it in out[:n]], len(allnew)


def advice(key, cname, idx, n_dn, n_up):
    if idx <= -0.5 or n_dn >= 2 * max(1, n_up):
        return [f"{cname} কেনার পরিকল্পনা থাকলে সময়টা ভালো: দাম কমার দিকে। তবু কেনার আগে প্রোডাক্ট পাতায় সব দোকানের দাম মিলিয়ে নিন।",
                "যে মডেল চান তার দাম আরও কমবে কিনা দেখতে প্রোডাক্ট পাতায় \"দাম কমলে জানান\" চালু রাখুন।"]
    if idx >= 0.5 or n_up >= 2 * max(1, n_dn):
        return [f"{POSS[key]} দাম বাড়ার দিকে। জরুরি দরকার হলে দেরি না করে কম দামের দোকান থেকে কিনে নেওয়া ভালো।",
                "জরুরি না হলে প্রোডাক্ট পাতায় \"দাম কমলে জানান\" চালু রেখে অপেক্ষা করতে পারেন।"]
    return [f"{POSS[key]} দাম মোটামুটি স্থির। এখন কেনা আর কিছুদিন পরে কেনায় বড় পার্থক্য হওয়ার সম্ভাবনা কম।",
            "একই মডেল দোকানভেদে আলাদা দামে বিক্রি হয়, তাই কেনার আগে প্রোডাক্ট পাতায় দাম মিলিয়ে নিন।"]


# ---------------- ইনফোগ্রাফিক (SVG) ----------------

C = {"ink": "#12302c", "mu": "#5b706c", "dn": "#1d7a52", "up": "#b4472f", "ac": "#c97a12", "acd": "#8a520a", "bg": "#f7faf9",
     "hd": "#12302c", "gold": "#f3c98a", "pale": "#cfe0dc", "line": "#d6e0dd", "note": "#fbefdc"}


def infographic(title, subtitle, right, tiles, sections, note=None, foot_date=""):
    """১০৮০ চওড়া পোর্ট্রেট ইনফোগ্রাফিক। tiles: [(সংখ্যা/লেখা, লেবেল, রং, ছোট লেখা)];
    sections: [(শিরোনাম, [ {name, sub, val, frac, color} ])]"""
    W, y = 1080, 0
    parts, k = [], 0

    def nxt():
        nonlocal k
        k += 1
        return f"{0.1 + k * 0.09:.2f}s"
    parts.append(f'<rect width="{W}" height="150" fill="{C["hd"]}"/>'
                 f'<text x="70" y="78" class="brand">দামতুলনা</text>'
                 f'<text x="70" y="118" class="hsub">{escape(title)}</text>'
                 f'<text x="1010" y="98" text-anchor="end" class="hsub2">{escape(right)}</text>')
    y = 200
    if tiles:
        n = len(tiles)
        tw = (940 - (n - 1) * 20) / n
        for i, (num, lab, col, sub) in enumerate(tiles):
            x = 70 + i * (tw + 20)
            isnum = isinstance(num, int)
            parts.append(f'<g class="tile" style="--d:{nxt()}"><rect x="{x:.0f}" y="{y}" width="{tw:.0f}" height="190" rx="22" fill="{col}" opacity=".13"/>'
                         f'<text x="{x + tw / 2:.0f}" y="{y + 100}" text-anchor="middle" class="big" fill="{col}"'
                         + (f' data-n="{num}"' if isnum else "") + f'>{bn(num) if isnum else escape(str(num))}</text>'
                         f'<text x="{x + tw / 2:.0f}" y="{y + 145}" text-anchor="middle" class="lab">{escape(lab)}</text>'
                         f'<text x="{x + tw / 2:.0f}" y="{y + 173}" text-anchor="middle" class="sm">{escape(sub)}</text></g>')
        y += 190 + 70
    if subtitle:
        parts.append(f'<text x="70" y="{y - 20}" class="sm2">{escape(subtitle)}</text>')
        y += 20
    for head, rows in sections:
        if not rows:
            continue
        parts.append(f'<text x="70" y="{y}" class="sec">{escape(head)}</text>')
        y += 50
        for r in rows:
            w = max(36, 560 * r["frac"])
            parts.append(f'<g class="row" style="--d:{nxt()}"><text x="70" y="{y}" class="nm">{escape(short(r["name"], 44))}</text>'
                         f'<text x="70" y="{y + 26}" class="sm">{escape(r["sub"])}</text>'
                         f'<rect x="70" y="{y + 38}" width="{w:.0f}" height="20" rx="10" fill="{r["color"]}" class="bar"/>'
                         f'<text x="{70 + w + 14:.0f}" y="{y + 55}" class="val" fill="{r["color"]}">{escape(r["val"])}</text></g>')
            y += 88
        y += 30
    if note:
        parts.append(f'<g class="tile" style="--d:{nxt()}"><rect x="70" y="{y - 10}" width="940" height="110" rx="22" fill="{C["note"]}"/>'
                     f'<text x="110" y="{y + 37}" class="trend">{escape(note[0])}</text>'
                     f'<text x="110" y="{y + 72}" class="sm">{escape(note[1])}</text></g>')
        y += 140
    y += 10
    parts.append(f'<line x1="70" y1="{y}" x2="1010" y2="{y}" stroke="{C["line"]}" stroke-width="2"/>'
                 f'<text x="70" y="{y + 43}" class="foot">উৎস: দামতুলনা বিশ্লেষণ · {escape(foot_date)}</text>'
                 f'<text x="1010" y="{y + 43}" text-anchor="end" class="foot b">damtulona.com</text>')
    H = y + 80
    return (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="ig" role="img" aria-label="{escape(title)}">'
            f'<rect width="{W}" height="{H}" fill="{C["bg"]}"/>' + "".join(parts) + "</svg>")


def share_card(kicker, headline, sub, tiles):
    """১২০০×৬৩০ শেয়ার কার্ড (ফেসবুক/হোয়াটসঅ্যাপ প্রিভিউ)।"""
    out = [f'<svg viewBox="0 0 1200 630" width="1200" height="630" xmlns="http://www.w3.org/2000/svg" font-family="Hind Siliguri">',
           f'<rect width="1200" height="630" fill="{C["hd"]}"/><rect y="560" width="1200" height="70" fill="#0c2421"/>',
           f'<text x="70" y="100" font-size="32" font-weight="600" fill="{C["gold"]}">{escape(kicker)}</text>',
           f'<text x="70" y="180" font-size="{56 if len(headline) < 34 else 46}" font-weight="700" fill="#fff">{escape(headline)}</text>',
           f'<text x="70" y="245" font-size="34" font-weight="500" fill="{C["pale"]}">{escape(sub)}</text>']
    n = len(tiles)
    tw = (1060 - (n - 1) * 35) / max(1, n)
    for i, (num, lab, col) in enumerate(tiles):
        x = 70 + i * (tw + 35)
        out.append(f'<rect x="{x:.0f}" y="300" width="{tw:.0f}" height="200" rx="22" fill="{col}"/>'
                   f'<text x="{x + tw / 2:.0f}" y="410" font-size="{84 if len(str(num)) < 6 else 64}" font-weight="700" fill="#fff" text-anchor="middle">{escape(str(num))}</text>'
                   f'<text x="{x + tw / 2:.0f}" y="465" font-size="30" font-weight="600" fill="#fff" text-anchor="middle" opacity=".9">{escape(lab)}</text>')
    out.append(f'<text x="70" y="604" font-size="26" fill="{C["pale"]}">দামতুলনা বিশ্লেষণ</text>'
               f'<text x="1130" y="604" font-size="30" font-weight="700" fill="{C["gold"]}" text-anchor="end">damtulona.com</text></svg>')
    return "".join(out)


def bars(rows, color, sign, stores):
    if not rows:
        return []
    mx = max(abs(r["diff"]) for r in rows)
    return [{"name": r["name"], "sub": f'{r["cat_name"]} · {stores[r["store"]]["name"]} · {tk(r["old"])} → {tk(r["new"])}',
             "val": f'{sign}{tk(r["diff"])} ({pct_s(r["pct"])})', "frac": abs(r["diff"]) / mx, "color": color} for r in rows]


# ---------------- রিপোর্ট তৈরি ----------------

def make_daily(H, items, stores, today):
    prev = [d for d in H.dates if d < today]
    d0 = prev[-1] if prev else None
    allc = H.changes(d0, today) if d0 else []
    tabs = []
    for key, name, cats in DAILY_TABS:
        cs = set(cats) if cats else None
        ch = [c for c in allc if cs is None or c["category"] in cs]
        dn = sorted([c for c in ch if c["diff"] < 0], key=lambda c: c["diff"])
        up = sorted([c for c in ch if c["diff"] > 0], key=lambda c: -c["diff"])
        nw, n_new = new_models(items, d0 or today, today, cs, 8, 0 if cs else 3000)
        gp = gaps(items, cs, 5) if key != "mobile" else []
        if key != "all" and not (dn or up or nw):
            continue
        tabs.append({"key": key, "name": name, "dn": dn[:10], "up": up[:10], "n_dn": len(dn), "n_up": len(up),
                     "new": nw, "n_new": n_new, "gaps": gp})
    t0 = tabs[0]
    by_cat = sorted(tabs[1:], key=lambda t: -(t["n_dn"] + t["n_up"]))
    lead = by_cat[0] if by_cat and (by_cat[0]["n_dn"] + by_cat[0]["n_up"]) else None
    n_dn, n_up = t0["n_dn"], t0["n_up"]
    if n_dn or n_up:
        title = f"আজকের বাজার: {bn(n_dn)}টি প্রোডাক্টের দাম কমেছে, {bn(n_up)}টির বেড়েছে"
    else:
        title = f"আজকের বাজার: দাম মোটামুটি স্থির, {bn(t0['n_new'])}টি নতুন প্রোডাক্ট"
    key = []
    if n_dn or n_up:
        key.append(f"আগের দামের তুলনায় আজ {bn(n_dn)}টি প্রোডাক্টের দাম কমেছে আর {bn(n_up)}টির বেড়েছে।")
    if t0["dn"]:
        c = t0["dn"][0]
        key.append(f"সবচেয়ে বেশি কমেছে {short(c['name'], 60)}: {tk(c['diff'])} ({pct_s(c['pct'])})।")
    if t0["up"]:
        c = t0["up"][0]
        key.append(f"সবচেয়ে বেশি বেড়েছে {short(c['name'], 60)}: {tk(c['diff'])} ({pct_s(c['pct'])})।")
    if t0["n_new"]:
        key.append(f"দোকানগুলোতে আজ {bn(t0['n_new'])}টি নতুন প্রোডাক্ট এসেছে।")
    if lead:
        key.append(f"ক্যাটাগরির মধ্যে সবচেয়ে বেশি দাম বদলেছে {lead['name']}-এ: {bn(lead['n_dn'])}টি কমেছে, {bn(lead['n_up'])}টি বেড়েছে।")
    tot = n_dn + n_up
    note = None
    if lead:
        note = (f"আজকের ধারা: সবচেয়ে বেশি নড়াচড়া {lead['name']}-এ",
                f"{lead['name']}: {bn(lead['n_dn'])}টির দাম কমেছে, {bn(lead['n_up'])}টির বেড়েছে")
    svg = infographic(f"আজকের বাজার · {dmy(today)}", "", f"{bn(len(stores))} দোকান",
                      [(n_dn, "দাম কমেছে ▼", C["dn"], "আগের দামের তুলনায়"), (n_up, "দাম বেড়েছে ▲", C["up"], "আগের দামের তুলনায়"),
                       (t0["n_new"], "নতুন প্রোডাক্ট", C["ac"], "আজ দোকানে এসেছে")],
                      [("সবচেয়ে বেশি কমেছে", bars(t0["dn"][:3], C["dn"], "−", stores)),
                       ("সবচেয়ে বেশি বেড়েছে", bars(t0["up"][:3], C["up"], "+", stores))], note, dmy(today))
    card = share_card(f"আজকের বাজার · {dmy(today)}",
                      f"{bn(n_dn)}টির দাম কমেছে, {bn(n_up)}টির বেড়েছে" if tot else "আজ দাম মোটামুটি স্থির",
                      f"সবচেয়ে বেশি নড়াচড়া {lead['name']}-এ" if lead else "দোকানভেদে দাম মিলিয়ে কিনুন",
                      [(bn(n_dn), "দাম কমেছে ▼", C["dn"]), (bn(n_up), "দাম বেড়েছে ▲", C["up"]), (bn(t0["n_new"]), "নতুন প্রোডাক্ট", C["ac"])])
    adv = []
    if lead and lead["key"] in CAT_NAME:
        adv.append(f"{lead['name']} কিনতে চাইলে: আজ এখানে দাম সবচেয়ে বেশি বদলেছে। তালিকা দেখে নিন, আর কেনার আগে প্রোডাক্ট পাতায় সব দোকানের দাম মিলিয়ে নিন।")
    adv += ["দাম কমার অপেক্ষায় থাকলে: প্রোডাক্ট পাতায় \"দাম কমলে জানান\" চালু রাখুন।",
            "একই প্রোডাক্ট দোকানভেদে আলাদা দামে বিক্রি হয়। নিচের \"দোকানভেদে বড় পার্থক্য\" অংশে আজকের বড় উদাহরণগুলো আছে।"]
    desc = " ".join(key[:2])[:300]
    h1 = title + (f"; সবচেয়ে বেশি নড়াচড়া {lead['name']}-এ" if lead and (n_dn or n_up) else "")
    return {"id": "aj", "kind": "daily", "path": "bazar/aj", "title": title, "h1": h1, "date": today, "desc": desc, "key": key,
            "tabs": tabs, "svg": svg, "card": card, "advice": adv, "label": "আজকের বাজার"}


def week_end(today):
    d = date.fromisoformat(today)
    return (d - timedelta(days=(d.weekday() - 4) % 7)).isoformat()  # সবশেষ শুক্রবার (আজ শুক্রবার হলে আজ)


def make_week_cat(H, items, stores, end, key, cname, cats):
    start = (date.fromisoformat(end) - timedelta(days=7)).isoformat()
    if not H.dates or H.dates[0] > start:
        return None
    cs = set(cats)
    ch = H.changes(start, end, cs)
    dn = sorted([c for c in ch if c["diff"] < 0], key=lambda c: c["diff"])
    up = sorted([c for c in ch if c["diff"] > 0], key=lambda c: -c["diff"])
    nw, n_new = new_models(items, start, end, cs, 8)
    n = len(ch)
    if not (n >= WORTHY_WEEK or (n >= WORTHY_WEEK_ALT[0] and n_new >= WORTHY_WEEK_ALT[1])):
        return None
    idx, n_cmp = H.index(start, end, cs)
    poss = POSS[key]
    sp = span_bn((date.fromisoformat(start) + timedelta(days=1)).isoformat(), end)
    trend = "কমেছে" if idx <= -0.1 else "বেড়েছে" if idx >= 0.1 else "প্রায় একই আছে"
    title = f"এই সপ্তাহে {poss} দাম: {bn(len(dn))}টির কমেছে, {bn(len(up))}টির বেড়েছে ({sp})"
    key_l = [f"{sp} সপ্তাহে {bn(n)}টি {poss} দাম বদলেছে: {bn(len(dn))}টির কমেছে, {bn(len(up))}টির বেড়েছে।",
             f"দুই সপ্তাহেই স্টকে থাকা {bn(n_cmp)}টি {poss} গড় দাম {pct_s(idx)} {trend}।" if trend != "প্রায় একই আছে"
             else f"দুই সপ্তাহেই স্টকে থাকা {bn(n_cmp)}টি {poss} গড় দাম প্রায় একই আছে।"]
    if dn:
        key_l.append(f"সবচেয়ে বেশি কমেছে {short(dn[0]['name'], 60)}: {tk(dn[0]['diff'])} ({pct_s(dn[0]['pct'])})।")
    if up:
        key_l.append(f"সবচেয়ে বেশি বেড়েছে {short(up[0]['name'], 60)}: {tk(up[0]['diff'])} ({pct_s(up[0]['pct'])})।")
    if n_new:
        key_l.append(f"সপ্তাহে {bn(n_new)}টি নতুন {cname} দোকানে এসেছে।")
    idx_txt = pct_s(idx, True)
    col = C["dn"] if idx < -0.1 else C["up"] if idx > 0.1 else C["ac"]
    svg = infographic(f"এই সপ্তাহে {cname} · {sp}", "", f"{bn(n_cmp)}টি {poss} হিসাব",
                      [(idx_txt, "গড় দাম", col, "আগের সপ্তাহের তুলনায়"), (len(dn), "দাম কমেছে ▼", C["dn"], "প্রোডাক্ট"),
                       (len(up), "দাম বেড়েছে ▲", C["up"], "প্রোডাক্ট")],
                      [("সবচেয়ে বেশি কমেছে", bars(dn[:3], C["dn"], "−", stores)), ("সবচেয়ে বেশি বেড়েছে", bars(up[:3], C["up"], "+", stores))],
                      (f"নতুন এসেছে {bn(n_new)}টি {cname}", f"সবচেয়ে দামি নতুন মডেল: {short(nw[0]['name'], 50)}") if nw else None, sp)
    card = share_card(f"{cname} · সাপ্তাহিক রিপোর্ট · {sp}", f"এই সপ্তাহে {poss} গড় দাম {idx_txt}",
                      f"{bn(len(dn))}টির দাম কমেছে, {bn(len(up))}টির বেড়েছে",
                      [(idx_txt, "গড় দাম", col), (bn(len(dn)), "দাম কমেছে ▼", C["dn"]), (bn(len(up)), "দাম বেড়েছে ▲", C["up"])])
    return {"id": f"{key}-{end}", "kind": "week", "cat": key, "cat_name": cname, "path": f"bazar/{key}/{end}", "title": title, "h1": title,
            "date": end, "start": start, "span": sp, "desc": " ".join(key_l[:2])[:300], "key": key_l, "idx": idx, "n_cmp": n_cmp,
            "tabs": [{"key": key, "name": cname, "dn": dn[:12], "up": up[:12], "n_dn": len(dn), "n_up": len(up), "new": nw, "n_new": n_new,
                      "gaps": gaps(items, cs, 5)}],
            "svg": svg, "card": card, "advice": advice(key, cname, idx, len(dn), len(up)), "label": f"{cname} · সাপ্তাহিক"}


def make_week_deals(H, items, stores, end):
    pool = []
    for it in items.values():
        if not it["best"] or not it["worst"] or it["live_count"] < 2 or it["category"] in NO_GAP or "software" in it["category"]:
            continue
        lo, hi = it["best"]["price"], it["worst"]["price"]
        if lo >= 3000 and hi <= lo * 1.35 and hi - lo >= 1000:
            pool.append({"id": it["id"], "name": it["name"], "cat_name": it["cat_name"], "lo": lo, "los": it["best"]["store"],
                         "hi": hi, "his": it["worst"]["store"], "diff": hi - lo, "n": it["live_count"]})
    pool.sort(key=lambda g: (-g["n"], -g["diff"]))
    top = sorted(pool[:40], key=lambda g: -g["diff"])[:10]
    if len(top) < WORTHY_DEALS:
        return None
    start = (date.fromisoformat(end) - timedelta(days=6)).isoformat()
    sp = span_bn(start, end)
    tot = sum(g["diff"] for g in top)
    title = f"সপ্তাহের সেরা ১০ ডিল: ঠিক দোকান বাছলে বাঁচবে সর্বোচ্চ {tk(top[0]['diff'])} ({sp})"
    mx = top[0]["diff"]
    rows = [{"name": g["name"], "sub": f"{g['cat_name']} · সবচেয়ে কম {tk(g['lo'])} {stores[g['los']]['name']}-এ",
             "val": f"বাঁচবে {tk(g['diff'])}", "frac": g["diff"] / mx, "color": C["dn"]} for g in top[:6]]
    svg = infographic(f"সপ্তাহের সেরা ডিল · {sp}", "", "একই প্রোডাক্ট, আলাদা দাম",
                      [(len(top), "বাছাই করা ডিল", C["ac"], "একাধিক দোকানে আছে"), (tk(mx), "সর্বোচ্চ সাশ্রয়", C["dn"], "একটি প্রোডাক্টে")],
                      [("দোকান বাছাইয়ে কত বাঁচবে", rows)], None, sp)
    card = share_card(f"সপ্তাহের সেরা ডিল · {sp}", f"ঠিক দোকান বাছলে বাঁচবে {tk(mx)} পর্যন্ত", "একই প্রোডাক্ট, দোকানভেদে আলাদা দাম",
                      [(bn(len(top)), "বাছাই করা ডিল", C["ac"]), (tk(mx), "সর্বোচ্চ সাশ্রয়", C["dn"])])
    key_l = [f"এই সপ্তাহে একাধিক দোকানে পাওয়া যায় এমন প্রোডাক্টের মধ্যে ১০টি বাছাই করেছি, যেখানে দোকান বাছাইয়ে সবচেয়ে বেশি টাকা বাঁচে।",
             f"সবচেয়ে বড় পার্থক্য {short(top[0]['name'], 60)}-এ: {tk(top[0]['diff'])}।",
             f"এই ১০টিতে মোট পার্থক্য {tk(tot)}।"]
    return {"id": f"deal-{end}", "kind": "deals", "path": f"bazar/deal/{end}", "title": title, "h1": title, "date": end, "span": sp,
            "desc": " ".join(key_l[:2])[:300], "key": key_l, "deals": top, "svg": svg, "card": card,
            "advice": ["দাম প্রতিদিন বদলায়। কেনার আগে প্রোডাক্ট পাতায় আজকের দাম দেখে নিন।",
                       "দামের পাশাপাশি ওয়ারেন্টি আর দোকানের রিটার্ন নীতিও মিলিয়ে নিন (প্রোডাক্ট পাতায় দেওয়া আছে)।"], "label": "সপ্তাহের ডিল"}


def make_month(H, items, stores, today):
    d = date.fromisoformat(today)
    last = d.replace(day=1) - timedelta(days=1)
    first = last.replace(day=1)
    if not H.dates or H.dates[-1] < last.isoformat():
        return None
    s0 = max(first - timedelta(days=1), date.fromisoformat(H.dates[0]))
    if (last - s0).days < MONTH_MIN_DAYS:
        return None
    a, b = s0.isoformat(), last.isoformat()
    rows, allc = [], H.changes(a, b)
    for key, cname, cats in REPORT_CATS:
        idx, n = H.index(a, b, set(cats))
        if n >= 20:
            rows.append({"key": key, "name": cname, "idx": idx, "n": n})
    if len(rows) < 3:
        return None
    mname = f"{MONTHS[last.month - 1]} {str(last.year).translate(BN)}"
    sp = span_bn((s0 + timedelta(days=1)).isoformat(), b)
    dn = sorted([c for c in allc if c["diff"] < 0], key=lambda c: c["diff"])
    up = sorted([c for c in allc if c["diff"] > 0], key=lambda c: -c["diff"])
    rows.sort(key=lambda r: r["idx"])
    title = f"{mname}: ইলেকট্রনিক্স বাজারে কী সস্তা হলো, কী দামি ({sp})"
    mx = max(abs(r["idx"]) for r in rows) or 1
    secs = [("ক্যাটাগরি অনুযায়ী গড় দাম", [{"name": r["name"], "sub": f"{bn(r['n'])}টি প্রোডাক্টের হিসাব", "val": pct_s(r["idx"], True),
                                           "frac": abs(r["idx"]) / mx, "color": C["dn"] if r["idx"] < 0 else C["up"]} for r in rows])]
    svg = infographic(f"{mname} · মাসিক বাজার রিপোর্ট", "", sp,
                      [(len(dn), "দাম কমেছে ▼", C["dn"], "প্রোডাক্ট"), (len(up), "দাম বেড়েছে ▲", C["up"], "প্রোডাক্ট")], secs, None, sp)
    card = share_card(f"মাসিক বাজার রিপোর্ট · {mname}", f"সবচেয়ে সস্তা হয়েছে {rows[0]['name']} ({pct_s(rows[0]['idx'], True)})",
                      f"সবচেয়ে দামি হয়েছে {rows[-1]['name']} ({pct_s(rows[-1]['idx'], True)})",
                      [(bn(len(dn)), "দাম কমেছে ▼", C["dn"]), (bn(len(up)), "দাম বেড়েছে ▲", C["up"])])
    key_l = [f"{sp} সময়ে {bn(len(dn))}টি প্রোডাক্টের দাম কমেছে, {bn(len(up))}টির বেড়েছে।",
             f"সবচেয়ে বেশি দাম কমেছে {rows[0]['name']}-এ (গড়ে {pct_s(rows[0]['idx'])})।" if rows[0]["idx"] < 0 else "",
             f"সবচেয়ে বেশি দাম বেড়েছে {rows[-1]['name']}-এ (গড়ে {pct_s(rows[-1]['idx'])})।" if rows[-1]["idx"] > 0 else ""]
    key_l = [k for k in key_l if k]
    return {"id": f"masik-{last.strftime('%Y-%m')}", "kind": "month", "path": f"bazar/masik/{last.strftime('%Y-%m')}", "title": title,
            "h1": title, "date": b, "span": sp, "desc": " ".join(key_l[:2])[:300], "key": key_l, "cats": rows,
            "tabs": [{"key": "all", "name": "সব", "dn": dn[:12], "up": up[:12], "n_dn": len(dn), "n_up": len(up), "new": [], "n_new": 0,
                      "gaps": []}],
            "svg": svg, "card": card, "advice": ["প্রতিটা ক্যাটাগরির বিস্তারিত সাপ্তাহিক রিপোর্টে দেখুন।",
                                                 "কেনার আগে প্রোডাক্ট পাতায় আজকের দাম মিলিয়ে নিন।"], "label": "মাসিক রিপোর্ট"}


# ---------------- পাতা লেখা ----------------

IG_HEAD = """<!doctype html><html><head><meta charset="utf-8"><meta name="robots" content="noindex"><style>
@font-face{font-family:"Hind Siliguri";font-weight:400;src:url(/static/fonts/hs-400.woff2) format("woff2")}
@font-face{font-family:"Hind Siliguri";font-weight:500;src:url(/static/fonts/hs-500.woff2) format("woff2")}
@font-face{font-family:"Hind Siliguri";font-weight:600;src:url(/static/fonts/hs-600.woff2) format("woff2")}
@font-face{font-family:"Hind Siliguri";font-weight:700;src:url(/static/fonts/hs-700.woff2) format("woff2")}
@font-face{font-family:"Hind Siliguri";font-weight:400;src:url(/static/fonts/hsl-400.woff2) format("woff2");unicode-range:U+0000-00FF,U+2013-2026}
@font-face{font-family:"Hind Siliguri";font-weight:500;src:url(/static/fonts/hsl-500.woff2) format("woff2");unicode-range:U+0000-00FF,U+2013-2026}
@font-face{font-family:"Hind Siliguri";font-weight:600;src:url(/static/fonts/hsl-600.woff2) format("woff2");unicode-range:U+0000-00FF,U+2013-2026}
@font-face{font-family:"Hind Siliguri";font-weight:700;src:url(/static/fonts/hsl-700.woff2) format("woff2");unicode-range:U+0000-00FF,U+2013-2026}
html,body{margin:0;background:#f7faf9}svg{display:block}</style><link rel="stylesheet" href="/static/ig.css"></head><body>"""


def build(*, items, history, enabled, stores, today, write, crumbs_ld, SITE_URL, BASE, DIST, DATA, common):
    H = Hist(history, items, enabled)
    rep_dir = DATA / "reports"
    rep_dir.mkdir(exist_ok=True)
    st_file = DATA / "report_status.json"
    status = json.loads(st_file.read_text()) if st_file.exists() else {}
    status = {k: v for k, v in status.items() if not k.startswith("_")}

    # নতুন খসড়া (একবার তৈরি হলে আর বদলায় না)
    end = week_end(today)
    cands = [make_week_cat(H, items, stores, end, k, n, c) for k, n, c in REPORT_CATS] + [make_week_deals(H, items, stores, end),
                                                                                        make_month(H, items, stores, today)]
    for r in cands:
        if r and not (rep_dir / f"{r['id']}.json").exists():
            r["created"] = today
            (rep_dir / f"{r['id']}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1))
    reports = []
    for f in sorted(rep_dir.glob("*.json")):
        r = json.loads(f.read_text())
        s = status.get(r["id"]) or {}
        if s.get("publish") and (s.get("comment") or "").strip():
            r["comment"], r["context"], r["context_link"] = s["comment"].strip(), (s.get("context") or "").strip(), (s.get("context_link") or "").strip()
            r["published"] = s.get("at") or r["date"]
            reports.append(r)
    reports.sort(key=lambda r: (r["published"], r["date"]), reverse=True)

    daily = make_daily(H, items, stores, today)
    daily["published"] = today
    jobs = []
    site = SITE_URL or BASE
    org = {"@type": "Organization", "name": "দামতুলনা", "url": f"{site}/", "logo": {"@type": "ImageObject", "url": common["og_default"]}}
    author = {"@type": "Person", "name": EDITOR, "url": f"{site}/bazar/niti/#editor"}

    def page(r, crumbs):
        url = f"{SITE_URL}/{r['path']}/" if SITE_URL else None
        img = f"{site}/{r['path']}/share.jpg"
        ld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": r["title"][:110], "description": r["desc"],
              "datePublished": r["published"] + "T06:00:00+06:00", "dateModified": r["published"] + "T06:00:00+06:00",
              "author": [author], "publisher": org, "image": [img, f"{site}/{r['path']}/infographic.jpg"], "inLanguage": "bn-BD",
              "mainEntityOfPage": url or f"{site}/{r['path']}/", "isAccessibleForFree": True}
        others = [x for x in [daily] + reports if x["id"] != r["id"]][:6]
        write(r["path"], "bazar_report.html", r=r, others=others, editor=EDITOR, n_stores=len(enabled), share_url=url or f"{site}/{r['path']}/",
              title=r["title"][:95] + " | দামতুলনা", description=r["desc"], canonical=url, og_image=img, og_type="article", big_og=True,
              crumbs=crumbs_ld(*crumbs), lds=[json.dumps(ld, ensure_ascii=False)])
        d = DIST / r["path"]
        (d / "ig.html").write_text(IG_HEAD + r["svg"].replace('class="ig"', 'class="ig static"') + "</body></html>")
        (d / "card.html").write_text(IG_HEAD + r["card"] + "</body></html>")
        jobs.append(r["path"])

    page(daily, [("হোম", ""), ("বাজার আপডেট", "bazar/"), ("আজকের বাজার", "bazar/aj/")])
    for r in reports:
        if r["kind"] == "week":
            cr = [("হোম", ""), ("বাজার আপডেট", "bazar/"), (r["cat_name"], f"bazar/{r['cat']}/"), (r["span"], r["path"] + "/")]
        else:
            cr = [("হোম", ""), ("বাজার আপডেট", "bazar/"), (r["label"], r["path"] + "/")]
        page(r, cr)
    # ক্যাটাগরির রিপোর্ট তালিকা (অন্তত একটা প্রকাশিত রিপোর্ট থাকলে)
    for key, cname, _ in REPORT_CATS:
        mine = [r for r in reports if r.get("cat") == key]
        if mine:
            write(f"bazar/{key}", "bazar_hub.html", reports=mine, daily=None, cat_name=cname, poss=POSS[key],
                  title=f"{POSS[key]} দামের সাপ্তাহিক রিপোর্ট | দামতুলনা",
                  description=f"বাংলাদেশে {POSS[key]} দাম প্রতি সপ্তাহে কতটা কমল বা বাড়ল, কোন মডেলে কত পার্থক্য: দামতুলনার সাপ্তাহিক বিশ্লেষণ।",
                  canonical=f"{SITE_URL}/bazar/{key}/" if SITE_URL else None,
                  crumbs=crumbs_ld(("হোম", ""), ("বাজার আপডেট", "bazar/"), (cname, f"bazar/{key}/")))
    cat_links = [(k, n) for k, n, _ in REPORT_CATS if any(r.get("cat") == k for r in reports)]
    write("bazar", "bazar_hub.html", reports=reports, daily=daily, cat_name=None, cat_links=cat_links,
          title="বাজার আপডেট: ইলেকট্রনিক্সের দাম কমল না বাড়ল | দামতুলনা",
          description="বাংলাদেশে কম্পিউটার, ল্যাপটপ, মনিটর, র‍্যাম, এসএসডি ও মোবাইলের দাম কোথায় কমল, কোথায় বাড়ল: দামতুলনার প্রতিদিনের ও সাপ্তাহিক বিশ্লেষণ।",
          canonical=f"{SITE_URL}/bazar/" if SITE_URL else None, crumbs=crumbs_ld(("হোম", ""), ("বাজার আপডেট", "bazar/")))
    write("bazar/niti", "bazar_niti.html", editor=EDITOR, n_stores=len(enabled), title="আমাদের নীতি: বাজার আপডেট | দামতুলনা",
          description="দামতুলনার বাজার আপডেট কে লেখেন, কোন নীতিতে চলে, ভুল হলে কী হয়।",
          canonical=f"{SITE_URL}/bazar/niti/" if SITE_URL else None,
          crumbs=crumbs_ld(("হোম", ""), ("বাজার আপডেট", "bazar/"), ("আমাদের নীতি", "bazar/niti/")))
    (DIST / "_ig_jobs.json").write_text(json.dumps(jobs))

    # RSS
    def rss_item(r):
        u = f"{site}/{r['path']}/"
        y, m, d_ = (int(x) for x in r["published"].split("-"))
        pd = date(y, m, d_).strftime("%a, %d %b %Y") + " 06:00:00 +0600"
        return (f"<item><title>{escape(r['title'])}</title><link>{u}</link><guid isPermaLink=\"false\">{r['id']}-{r['published']}</guid>"
                f"<pubDate>{pd}</pubDate><description>{escape(r['desc'])}</description><author>{escape(EDITOR)}</author></item>")
    (DIST / "bazar" / "feed.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>দামতুলনা বাজার আপডেট</title>'
        f"<link>{site}/bazar/</link><description>বাংলাদেশে ইলেকট্রনিক্সের দাম কমল না বাড়ল</description><language>bn-BD</language>"
        + "".join(rss_item(r) for r in [daily] + reports[:30]) + "</channel></rss>\n")
    # Google News সাইটম্যাপ: শেষ ২ দিনের খবর
    recent = [r for r in [daily] + reports if (date.fromisoformat(today) - date.fromisoformat(r["published"])).days <= 2]
    return {"daily": daily, "reports": reports, "news": [(f"{SITE_URL}/{r['path']}/", r["published"], r["title"]) for r in recent]}
