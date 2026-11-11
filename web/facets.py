"""ক্যাটাগরি অনুযায়ী ফিল্টার (ফ্যাসেট): প্রোডাক্টের নাম, স্টোরের ফিচার লাইন আর স্পেক থেকে মান বের করা।

প্রতিটা ফ্যাসেট: id, বাংলা নাম, মান বের করার ফাংশন। মান = (দেখানোর লেখা, সাজানোর সংখ্যা)।
সংখ্যা থাকলে ওই ফ্যাসেট দিয়ে সাজানোও যায় (যেমন "বেশি ক্যাপাসিটি আগে")।
নতুন ক্যাটাগরি যোগ করতে নিচের CATS-এ এক লাইন যোগ করুন।
"""
import re

I = re.I


def _num(x):
    return float(x) if "." in x else int(x)


def _fmt(x):
    return f"{x:g}" if isinstance(x, float) else str(x)


def capacity(text, specs):
    """স্টোরেজ/মেমোরি: 512GB, 1TB …  (সাজানো GB-তে)"""
    v = specs.get("capacity")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(TB|GB)\b", v or text, I)
    if not m:
        return None
    n, u = _num(m.group(1)), m.group(2).upper()
    return f"{_fmt(n)}{u}", n * (1024 if u == "TB" else 1)


def ram_type(text, specs):
    v = specs.get("type") or (re.search(r"\bDDR\s?([3-5])L?\b", text, I) and "DDR" + re.search(r"\bDDR\s?([3-5])", text, I).group(1))
    return (v, int(re.sub(r"\D", "", v)[:1] or 0)) if v else None


def ram_speed(text, specs):
    m = re.search(r"(\d{4})\s*MHz", specs.get("speed") or text, I)
    if not m or not 1066 <= int(m.group(1)) <= 9600:
        return None
    return f"{m.group(1)}MHz", int(m.group(1))


def ssd_iface(text, specs):
    t = (specs.get("interface") or "") + " " + text
    if re.search(r"nvme|pcie|m\.2\s*2280\s*nvme", t, I):
        g = re.search(r"(?:pcie|gen)\s*([345])(?:\.0)?", t, I)
        return (f"NVMe Gen{g.group(1)}" if g else "NVMe"), 2 + (int(g.group(1)) if g else 0)
    if re.search(r"sata", t, I):
        return "SATA", 1
    return None


def screen(lo, hi):
    def f(text, specs):
        for m in re.finditer(r"(\d{2}(?:\.\d)?)\s*(?:-?\s*inch(?:es)?|\"|”|''|′′|in\b)", text, I):
            n = _num(m.group(1))
            if lo <= n <= hi:
                return f"{_fmt(n)} ইঞ্চি", n
        return None
    return f


def refresh(text, specs):
    m = re.search(r"\b(\d{2,3})\s*Hz\b", text, I)
    if m and 50 <= int(m.group(1)) <= 540:
        return f"{m.group(1)}Hz", int(m.group(1))
    return None


def resolution(text, specs):
    for rx, lab, n in ((r"\b(8K)\b", "8K", 8), (r"\b(4K|UHD|2160p)\b", "4K", 4), (r"\b(QHD|2K|1440p|WQHD)\b", "2K (QHD)", 3),
                       (r"\b(FHD|Full\s*HD|1080p)\b", "Full HD", 2), (r"\b(HD|720p)\b", "HD", 1)):
        if re.search(rx, text, I):
            return lab, n
    return None


def unit(rx, label, lo=0, hi=10**9):
    def f(text, specs):
        m = re.search(rx, text, I)
        if not m:
            return None
        n = _num(m.group(1))
        return (f"{_fmt(n)} {label}", n) if lo <= n <= hi else None
    return f


def bucket(fn, edges, lab):
    """খুব বেশি আলাদা মান (যেমন ২৪৩ লিটার, ২৫২ লিটার…) রেঞ্জে ভাগ: "২৫১-৩০০ লিটার"।"""
    def f(text, specs):
        v = fn(text, specs)
        if not v:
            return None
        n = v[1]
        for i in range(1, len(edges)):
            if n <= edges[i]:
                lo, hi = edges[i - 1], edges[i]
                if i == 1:
                    return f"{hi:,} {lab} পর্যন্ত", hi
                if i == len(edges) - 1:
                    return f"{lo:,}+ {lab}", lo + 1
                return f"{lo + 1:,}-{hi:,} {lab}", hi
        return None
    return f


def gpu(text, specs):
    m = re.search(r"\b(RTX\s?\d{4}\s?(?:Ti)?\s?(?:SUPER)?|GTX\s?\d{3,4}\s?(?:Ti|SUPER)?|RX\s?\d{3,4}\s?(?:XTX|XT|GRE)?|Arc\s?[AB]\d{3})", text, I)
    if not m:
        return None
    v = re.sub(r"\s+", " ", m.group(1).upper().replace("RTX", "RTX ").replace("GTX", "GTX ").replace("RX", "RX ")).strip()
    v = v.replace("ARC", "Arc").replace(" TI", " Ti").replace("TI", " Ti").replace(" SUPER", " Super").replace("  ", " ")
    n = int(re.sub(r"\D", "", v) or 0)
    return v, n


def cpu_family(text, specs):
    for rx, lab, n in ((r"core\s*ultra\s*9", "Core Ultra 9", 19), (r"core\s*ultra\s*7", "Core Ultra 7", 17), (r"core\s*ultra\s*5", "Core Ultra 5", 15),
                       (r"core\s*ultra\s*3", "Core Ultra 3", 13), (r"\bi9\b|core\s*i9", "Core i9", 9), (r"\bi7\b|core\s*i7", "Core i7", 7),
                       (r"\bi5\b|core\s*i5", "Core i5", 5), (r"\bi3\b|core\s*i3", "Core i3", 3), (r"ryzen\s*ai\s*(?:max\+?\s*)?9", "Ryzen AI 9", 9.7), (r"ryzen\s*ai\s*(?:max\+?\s*)?7", "Ryzen AI 7", 7.7),
                       (r"ryzen\s*ai\s*(?:max\+?\s*)?5", "Ryzen AI 5", 5.7), (r"ryzen\s*9", "Ryzen 9", 9.5),
                       (r"ryzen\s*7", "Ryzen 7", 7.5), (r"ryzen\s*5", "Ryzen 5", 5.5), (r"ryzen\s*3", "Ryzen 3", 3.5),
                       (r"threadripper", "Threadripper", 20), (r"xeon", "Xeon", 18), (r"celeron", "Celeron", 1), (r"pentium", "Pentium", 2),
                       (r"athlon", "Athlon", 1.5), (r"\bapple\s*m(\d)|\bm([1-5])\s*(?:pro|max|chip)", "Apple M", 10)):
        m = re.search(rx, text, I)
        if m:
            if lab == "Apple M":
                d = next(g for g in m.groups() if g)
                return f"Apple M{d}", 10 + int(d)
            return lab, n
    return None


def cpu_gen(text, specs):
    m = re.search(r"\b(\d{1,2})(?:th|st|nd|rd)\s*gen", text, I)
    return (f"{m.group(1)}th Gen", int(m.group(1))) if m and 2 <= int(m.group(1)) <= 20 else None


def cpu_brand(text, specs):
    if re.search(r"\bintel\b|core\s*i\d|core\s*ultra|celeron|pentium|xeon", text, I):
        return "Intel", 1
    if re.search(r"\bamd\b|ryzen|athlon|threadripper", text, I):
        return "AMD", 2
    return None


def phone_ram(text, specs):
    m = re.search(r"\b(\d{1,2})\s*(?:GB)?\s*/\s*(\d{2,4})\s*(?:GB|TB)?\b", text, I) or re.search(r"\b(\d{1,2})\s*GB\s*RAM", text, I)
    if m and 1 <= int(m.group(1)) <= 24:
        return f"{m.group(1)}GB RAM", int(m.group(1))
    return None


def phone_storage(text, specs):
    m = re.search(r"\b\d{1,2}\s*(?:GB)?\s*/\s*(\d{1,4})\s*(GB|TB)?\b", text, I)
    if m:
        n = int(m.group(1)); u = (m.group(2) or ("TB" if n <= 2 else "GB")).upper()
        if u == "GB" and 16 <= n <= 1024 or u == "TB":
            return f"{n}{u}", n * (1024 if u == "TB" else 1)
    m = re.search(r"\b(\d{2,4})\s*GB\s*(?:ROM|storage)", text, I)
    return (f"{m.group(1)}GB", int(m.group(1))) if m else None


def laptop_ram(text, specs):
    m = re.search(r"\b(\d{1,2})\s*GB\s*(?:(?:LP)?DDR\d\w*\s*)?(?:RAM|memory|unified)", text, I)
    return (f"{m.group(1)}GB", int(m.group(1))) if m and 2 <= int(m.group(1)) <= 128 else None


def laptop_ssd(text, specs):
    m = re.search(r"\b(\d+)\s*(GB|TB)\s*(?:(?:PCIe|NVMe|M\.2|Gen\s?\d)\s*)*SSD", text, I)
    if not m:
        return None
    n, u = int(m.group(1)), m.group(2).upper()
    return f"{n}{u}", n * (1024 if u == "TB" else 1)


def connection(text, specs):
    if re.search(r"wireless|bluetooth|\bbt\b|2\.4\s*g|tri-?mode|dual[\s-]?mode", text, I):
        return "ওয়্যারলেস", 2
    if re.search(r"\bwired\b|\busb\b|3\.5\s*mm|type-?c", text, I):
        return "তারযুক্ত", 1
    return None


def kb_type(text, specs):
    if re.search(r"mechanical|hot-?swap", text, I):
        return "মেকানিক্যাল", 2
    if re.search(r"membrane", text, I):
        return "মেমব্রেন", 1
    return None


def wifi(text, specs):
    for rx, lab, n in ((r"wi-?fi\s?7|\bBE\d{3,5}\b", "Wi-Fi 7", 7), (r"wi-?fi\s?6e|\bAXE\d{3,5}\b", "Wi-Fi 6E", 6.5),
                       (r"wi-?fi\s?6|\bAX\d{3,5}\b", "Wi-Fi 6", 6), (r"wi-?fi\s?5|\bAC\d{3,5}\b", "Wi-Fi 5", 5),
                       (r"\bN\d{3}\b|wi-?fi\s?4|300\s*mbps", "Wi-Fi 4", 4)):
        if re.search(rx, text, I):
            return lab, n
    return None


def inverter(text, specs):
    return ("ইনভার্টার", 2) if re.search(r"inverter", text, I) else ("নন-ইনভার্টার", 1)


def psu_rating(text, specs):
    m = re.search(r"80\s*\+?\s*(?:plus\s*)?(titanium|platinum|gold|silver|bronze|white|standard)", text, I)
    order = ["standard", "white", "bronze", "silver", "gold", "platinum", "titanium"]
    return (f"80+ {m.group(1).title()}", order.index(m.group(1).lower())) if m else None


def five_g(text, specs):
    return ("5G", 2) if re.search(r"\b5G\b", text) else None


SOCKET_ORDER = ["LGA1150", "LGA1151", "LGA1200", "LGA1700", "LGA1851", "AM4", "AM5"]
CHIPSET = {"AM4": "A320 B350 B450 X370 X470 A520 B550 X570", "AM5": "A620 B650 X670 B840 B850 X870",
           "LGA1700": "H610 B660 H670 Z690 B760 H770 Z790", "LGA1851": "H810 B860 Z890",
           "LGA1200": "H410 B460 H470 Z490 H510 B560 Z590", "LGA1151": "H110 B150 H170 Z170 B250 H270 Z270 H310 B360 B365 H370 Z370 Z390",
           "LGA1150": "H81 B85 H87 H97 Z87 Z97"}


def _sk(v):
    return (v, SOCKET_ORDER.index(v) if v in SOCKET_ORDER else 99) if v else None


def mb_socket(text, specs):
    u = text.upper()
    m = re.search(r"\b(AM4|AM5|LGA\s?1700|LGA\s?1851|LGA\s?1200|LGA\s?1151|LGA\s?1150)\b", u)
    if m:
        return _sk(m.group(1).replace(" ", ""))
    m = re.search(r"\b([ABHXZ]\d{2,3})[EMIT]?\b", u)
    if m:
        for k, v in CHIPSET.items():
            if m.group(1) in v.split():
                return _sk(k)
    return None


def cpu_socket(text, specs):
    u = text.upper()
    m = re.search(r"\b(AM4|AM5|LGA\s?1700|LGA\s?1851|LGA\s?1200|LGA\s?1151)\b", u)
    if m:
        return _sk(m.group(1).replace(" ", ""))
    m = re.search(r"RYZEN\s*[3579]\s*(?:PRO\s*)?(\d{4})", u)
    if m:
        return _sk("AM4" if int(m.group(1)[0]) <= 5 else "AM5")
    if re.search(r"ATHLON\s*(?:PRO\s*)?(3000G|200GE|300GE|220GE|240GE|320GE)", u):
        return _sk("AM4")
    if re.search(r"ULTRA\s*[3579]\s*2\d{2}", u):
        return _sk("LGA1851")
    m = re.search(r"\bI[3579][\s-]*(\d{4,5})", u)
    gen = None
    if m:
        gen = int(m.group(1)[:2]) if len(m.group(1)) == 5 else int(m.group(1)[0])
    else:
        g = re.search(r"\b(\d{1,2})(?:TH)\s*GEN", u)
        gen = int(g.group(1)) if g else None
    if gen:
        return _sk("LGA1700" if gen in (12, 13, 14) else "LGA1200" if gen in (10, 11) else "LGA1151" if gen in (6, 7, 8, 9) else None)
    return None


def mb_ddr(text, specs):
    u = text.upper()
    if "DDR5" in u:
        return "DDR5", 5
    if "DDR4" in u or re.search(r"\bD4\b", u):
        return "DDR4", 4
    sk = mb_socket(text, specs)
    if sk and sk[0] == "AM5":  # AM5 শুধু DDR5
        return "DDR5", 5
    if sk and sk[0] in ("AM4", "LGA1200", "LGA1151"):
        return "DDR4", 4
    return None


def form_factor(text, specs):
    u = text.upper()
    if re.search(r"MINI[\s-]?ITX|\bITX\b", u):
        return "Mini-ITX", 1
    if re.search(r"MICRO[\s-]?ATX|\bM-?ATX\b|\b[ABHXZ]\d{3}M\b", u):
        return "Micro-ATX", 2
    if re.search(r"E-?ATX", u):
        return "E-ATX", 4
    if re.search(r"\bATX\b", u):
        return "ATX", 3
    return None


CAP = ("cap", "ক্যাপাসিটি", capacity)
SIZE_TV = ("size", "স্ক্রিন সাইজ", screen(19, 100))
SIZE_MON = ("size", "স্ক্রিন সাইজ", screen(13, 57))
SIZE_LAP = ("size", "স্ক্রিন সাইজ", screen(10, 18.5))
CONN = ("conn", "সংযোগ", connection)

CATS = {
    "desktop-ram": [CAP, ("type", "টাইপ", ram_type), ("speed", "স্পিড", ram_speed)],
    "laptop-ram": [CAP, ("type", "টাইপ", ram_type), ("speed", "স্পিড", ram_speed)],
    "ssd": [CAP, ("iface", "ইন্টারফেস", ssd_iface)],
    "portable-ssd": [CAP], "hdd": [CAP], "portable-hdd": [CAP], "pen-drive": [CAP], "memory-card": [CAP],
    "graphics-card": [("gpu", "চিপসেট", gpu), ("vram", "মেমোরি", capacity)],
    "processor": [("brand", "ব্র্যান্ড", cpu_brand), ("sk", "সকেট", cpu_socket), ("fam", "সিরিজ", cpu_family), ("gen", "জেনারেশন", cpu_gen)],
    "motherboard": [("sk", "সকেট", mb_socket), ("mt", "মেমোরি", mb_ddr), ("ff", "সাইজ", form_factor)],
    # "pt" (অফিসিয়াল/আনঅফিসিয়াল) build.py বসায় স্টোরের তথ্য থেকে, এখানে শুধু নাম
    "smartphone": [("pt", "ধরন", lambda t, s: None), ("net", "নেটওয়ার্ক", five_g)],
    "tablet": [("pt", "ধরন", lambda t, s: None), ("ram", "RAM", phone_ram), ("rom", "স্টোরেজ", phone_storage)],
    "feature-phone": [("pt", "ধরন", lambda t, s: None)],
    "laptop": [("cpu", "প্রসেসর", cpu_family), ("ram", "RAM", laptop_ram), ("ssd", "SSD", laptop_ssd), SIZE_LAP],
    "gaming-laptop": [("gpu", "গ্রাফিক্স", gpu), ("cpu", "প্রসেসর", cpu_family), ("ram", "RAM", laptop_ram), SIZE_LAP],
    "ultrabook": [("cpu", "প্রসেসর", cpu_family), ("ram", "RAM", laptop_ram), ("ssd", "SSD", laptop_ssd), SIZE_LAP],
    "brand-pc": [("cpu", "প্রসেসর", cpu_family), ("ram", "RAM", laptop_ram)],
    "monitor-all": [SIZE_MON, ("hz", "রিফ্রেশ রেট", refresh), ("res", "রেজোলিউশন", resolution)],
    "gaming-monitor": [SIZE_MON, ("hz", "রিফ্রেশ রেট", refresh), ("res", "রেজোলিউশন", resolution)],
    "portable-monitor": [SIZE_MON, ("hz", "রিফ্রেশ রেট", refresh)],
    "tv": [SIZE_TV, ("res", "রেজোলিউশন", resolution)],
    "fridge": [("ltr", "ক্যাপাসিটি", bucket(unit(r"(\d{2,3})\s*(?:L|Ltr|Litre|Liter|Liters|Litres)\b", "লিটার", 40, 900),
                                          [0, 150, 200, 250, 300, 350, 400, 500, 10**6], "লিটার"))],
    "ac": [("ton", "টন", unit(r"(\d(?:\.\d{1,2})?)\s*Ton", "টন", 0.5, 5)), ("inv", "ধরন", inverter)],
    "washing-machine": [("kg", "ক্যাপাসিটি", unit(r"(\d{1,2}(?:\.\d)?)\s*KG\b", "কেজি", 2, 25))],
    "power-bank": [("mah", "ক্যাপাসিটি", bucket(unit(r"(\d{4,5})\s*mAh", "mAh", 1000, 60000), [0, 5000, 10000, 20000, 30000, 10**6], "mAh"))],
    "ups": [("va", "ক্যাপাসিটি", bucket(unit(r"(\d{3,5})\s*VA\b", "VA", 300, 20000), [0, 650, 1000, 1500, 2000, 3000, 10**6], "VA"))],
    "ips": [("va", "ক্যাপাসিটি", bucket(unit(r"(\d{3,5})\s*VA\b", "VA", 300, 20000), [0, 650, 1000, 1500, 2000, 3000, 10**6], "VA"))],
    "power-supply": [("w", "ওয়াট", bucket(unit(r"\b(\d{3,4})\s*W(?:att)?\b", "W", 200, 2500), [0, 500, 650, 750, 850, 1000, 10**6], "W")),
                     ("eff", "সার্টিফিকেশন", psu_rating)],
    "mouse": [CONN], "keyboard": [CONN, ("kt", "ধরন", kb_type)], "headphone": [CONN], "speaker": [CONN],
    "router": [("wifi", "Wi-Fi", wifi)], "gaming-router": [("wifi", "Wi-Fi", wifi)], "access-point": [("wifi", "Wi-Fi", wifi)],
    "range-extender": [("wifi", "Wi-Fi", wifi)], "wifi-adapter": [("wifi", "Wi-Fi", wifi)],
}


def facets_for(category, name, specs, feats=None):
    """{id: [লেখা, সংখ্যা]} — যা পাওয়া গেল শুধু তা।"""
    rules = CATS.get(category)
    if not rules:
        return {}
    text = name + " | " + " | ".join(feats or [])
    out = {}
    for fid, _, fn in rules:
        try:
            v = fn(text, specs or {})
        except Exception:
            v = None
        if v:
            out[fid] = [v[0], v[1]]
    return out


def facet_defs(category):
    return [{"id": fid, "name": nm} for fid, nm, _ in CATS.get(category, [])]
