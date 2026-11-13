"""বাজেট অনুযায়ী পিসি বিল্ড: প্রতিদিনের সবচেয়ে কম দামে, একে অপরের সাথে চলে এমন পার্টস দিয়ে পূর্ণ বিল্ড।

নিয়ম (সাবধানী, যাতে ভুল বিল্ড না আসে):
  - প্রসেসর আর মাদারবোর্ডের সকেট এক (নামের চিপসেট/মডেল থেকে): AM4, AM5, LGA1200, LGA1700, LGA1851
  - র‍্যামের ধরন মাদারবোর্ডের সাথে এক (DDR4/DDR5); LGA1700 বোর্ডের নামে DDR লেখা না থাকলে বাদ
  - শুধু মাইক্রো-ATX (mATX) বোর্ড: প্রায় সব কেসিংয়ে ধরে; Mini-ITX কেসিং বাদ
  - গ্রাফিক্স কার্ড না থাকলে প্রসেসরে গ্রাফিক্স থাকতেই হবে (Intel-এ F নয়, AMD-তে G বা AM5-এর নন-F)
  - বক্সে কুলার নেই এমন প্রসেসর (Intel K, i9; AMD X/X3D) নিলে আলাদা কুলার যোগ হয়
  - পুরনো/ব্যবহৃত/সার্ভার/ল্যাপটপ পার্টস বাদ
"""
import re

BAD = re.compile(r"\b(used|refurb|open ?box|server|xeon|epyc|threadripper|laptop|notebook|so-?dimm|portable|external|usb|"
                 r"workstation|quadro|rtx pro|radeon pro|bundle|combo)\b", re.I)

MB_CHIP = {
    "AM4": r"A320|A520|B450|B550|X470|X570",
    "AM5": r"A620|B650E?|B840|B850|X670E?|X870E?",
    "LGA1200": r"H410|H510|B460|B560|H470|Z490|Z590",
    "LGA1700": r"H610|B660|B760|H670|H770|Z690|Z790",
    "LGA1851": r"B860|H810|Z890",
}
DEFAULT_DDR = {"AM4": "DDR4", "AM5": "DDR5", "LGA1200": "DDR4", "LGA1851": "DDR5"}


def mb_info(name):
    n = name.upper()
    for sock, rx in MB_CHIP.items():
        m = re.search(rf"\b({rx})(M)?(?:[-\s]|$)", n)
        if m:
            matx = bool(m.group(2)) or bool(re.search(r"MICRO[\s-]?ATX|\bM-?ATX\b|\bMATX\b", n))
            if re.search(r"MINI[\s-]?ITX|\bITX\b", n):
                return None
            ddr = re.search(r"DDR([45])", n)
            ddr = f"DDR{ddr.group(1)}" if ddr else DEFAULT_DDR.get(sock)
            return {"socket": sock, "ddr": ddr, "matx": matx} if ddr else None
    return None


def cpu_info(name):
    n = name.upper()
    if re.search(r"\bTRAY\b|\bOEM\b", n):
        return None
    m = re.search(r"RYZEN\s*([3579])\s*(?:PRO\s*)?(\d{4})\s*(X3D|XT|X|GT|GE|G|F|E)?\b", n)
    if m:
        num, suf = int(m.group(2)), (m.group(3) or "")
        series = num // 1000
        if series in (1, 2, 3, 4, 5):
            sock, igpu = "AM4", "G" in suf
        elif series in (7, 8, 9):
            sock = "AM5"
            igpu = "F" not in suf and not (series == 8 and "G" not in suf)
        else:
            return None
        cooler = "X" in suf and not (series == 5 and num in (5600,))  # 5600X-এ বক্স কুলার আছে
        return {"socket": sock, "igpu": igpu, "cooler": cooler}
    m = re.search(r"(?:CORE\s*)?I([3579])[\s-]*(\d{4,5})([A-Z]*)", n)
    if m:
        num, suf = m.group(2), m.group(3)
        gen = int(num[:2]) if len(num) == 5 else int(num[0])
        sock = {10: "LGA1200", 11: "LGA1200", 12: "LGA1700", 13: "LGA1700", 14: "LGA1700"}.get(gen)
        if not sock:
            return None
        return {"socket": sock, "igpu": "F" not in suf, "cooler": "K" in suf or m.group(1) == "9"}
    m = re.search(r"ULTRA\s*([579])\s*(2\d{2})([A-Z]*)", n)
    if m:
        return {"socket": "LGA1851", "igpu": "F" not in m.group(3), "cooler": "K" in m.group(3) or True}
    m = re.search(r"(PENTIUM|CELERON)[\w\s]*?G(\d{4})", n)
    if m:
        g = int(m.group(2))
        sock = "LGA1200" if 5900 <= g < 7000 else "LGA1700" if g >= 7000 else None
        return {"socket": sock, "igpu": True, "cooler": False} if sock else None
    return None


def gb_of(name):
    n = name.upper()
    m = re.search(r"(\d+)\s*GB\s*\(?\s*(\d)\s*X\s*(\d+)\s*GB", n) or re.search(r"\(?\s*(\d)\s*X\s*(\d+)\s*GB", n)
    if m and len(m.groups()) == 2:
        return int(m.group(1)) * int(m.group(2))
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*GB", n)
    return int(m.group(1)) if m else None


def ssd_info(name):
    n = name.upper()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(TB|GB)", n)
    if not m:
        return None
    cap = float(m.group(1)) * (1024 if m.group(2) == "TB" else 1)
    return {"gb": cap, "nvme": bool(re.search(r"NVME|PCIE", n)), "m2": bool(re.search(r"M\.2", n))}


def psu_watt(name):
    m = re.search(r"(\d{3,4})\s*W\b", name.upper())
    return int(m.group(1)) if m else None


# ভালো ব্র্যান্ড (অচেনা ব্র্যান্ডের সস্তা পাওয়ার সাপ্লাই/বোর্ড বিল্ডে ঝুঁকি)
OK_BRAND = {
    "motherboard": r"\b(ASUS|MSI|GIGABYTE|ASROCK|BIOSTAR|COLORFUL)\b",
    "desktop-ram": r"\b(CORSAIR|G\.?SKILL|KINGSTON|ADATA|XPG|TEAM|TEAMGROUP|T-FORCE|TRANSCEND|LEXAR|CRUCIAL|PNY|PATRIOT|HIKSEMI|TWINMOS|APACER|NETAC)\b",
    "ssd": r"\b(SAMSUNG|WD|WESTERN DIGITAL|KINGSTON|CRUCIAL|ADATA|XPG|LEXAR|TRANSCEND|TEAM|TEAMGROUP|GIGABYTE|APACER|HIKSEMI|HIKVISION|NETAC|PNY|SANDISK|CORSAIR|MSI|WALTON)\b",
    "power-supply": r"\b(ANTEC|CORSAIR|THERMALTAKE|DEEPCOOL|COOLER MASTER|MSI|GIGABYTE|ASUS|SEASONIC|XIGMATEK|1ST ?PLAYER|MONTECH|LIAN LI|BE QUIET|NZXT|FSP|SUPER FLOWER|SILVERSTONE|GAMDIAS|AEROCOOL|ARESGAME|CHIEFTEC)\b",
    "casing": r".",
    "cpu-cooler": r"\b(DEEPCOOL|COOLER MASTER|THERMALRIGHT|ID-COOLING|ARCTIC|NOCTUA|THERMALTAKE|LIAN LI|PCCOOLER|MONTECH|XIGMATEK|CORSAIR|NZXT|JONSBO|GAMDIAS|ANTEC)\b",
}
MIN_PRICE = {"power-supply": 2800, "casing": 2200, "cpu-cooler": 1200}

# প্রতিটা বাজেটের পরীক্ষিত কাঠামো (বাংলাদেশের জনপ্রিয় বিল্ড ধরে)। তালিকায় আগেরটা ভালো; বাজেটে না ধরলে পরেরটা।
TIERS = [
    {"amt": 30000, "label": "অফিস ও পড়াশোনা", "use": "অফিসের কাজ, পড়াশোনা, ইন্টারনেট আর ভিডিও দেখা",
     "cpu": [r"RYZEN 5 (4600G|5500GT)", r"I3[\s-]*12100(?!F)", r"RYZEN 3 (3200G|4300G|5300G)", r"PENTIUM.*G7400|CELERON.*G6900"],
     "gpu": None, "ram": 8, "ssd": 256, "nvme": False, "watt": 400},
    {"amt": 40000, "label": "অফিস ও পড়াশোনা", "use": "অফিস, পড়াশোনা, অনলাইন ক্লাস আর হালকা ফটো এডিটিং",
     "cpu": [r"RYZEN 5 5600G(?!T)", r"I3[\s-]*1[234]100(?!F)", r"RYZEN 5 (4600G|5500GT)"],
     "gpu": None, "ram": 16, "ssd": 256, "nvme": False, "watt": 400, "ram_min": 8},
    {"amt": 50000, "label": "দৈনন্দিন কাজ ও ফ্রিল্যান্সিং", "use": "অফিস, ফ্রিল্যান্সিং, প্রোগ্রামিং আর হালকা ডিজাইন",
     "cpu": [r"I5[\s-]*1[234]400(?!F)", r"RYZEN 5 5600G(?!T)", r"RYZEN 7 5700G", r"I3[\s-]*1[34]100(?!F)"],
     "gpu": None, "ram": 16, "ssd": 512, "nvme": True, "watt": 450},
    {"amt": 60000, "label": "ডিজাইন ও হালকা গেম", "use": "গ্রাফিক ডিজাইন, ফ্রিল্যান্সিং আর হালকা গেম (প্রসেসরের গ্রাফিক্সে)",
     "cpu": [r"RYZEN 5 8600G", r"RYZEN 7 5700G", r"I5[\s-]*1[34]400(?!F)", r"I5[\s-]*12400(?!F)", r"RYZEN 5 5600G(?!T)"],
     "gpu": None, "ram": 16, "ssd": 512, "nvme": True, "watt": 450},
    {"amt": 80000, "label": "এন্ট্রি গেমিং", "use": "১০৮০পি-তে জনপ্রিয় গেম (মাঝারি সেটিংস) আর ভিডিও এডিটিং",
     "cpu": [r"RYZEN 5 5600(?![GT\d])|RYZEN 5 5600X\b", r"I5[\s-]*12400F", r"RYZEN 5 5500(?!G)"],
     "gpu": [r"RX\s*6600(?!\s*XT)|RTX\s*3060|ARC\s*B570", r"RTX\s*3050|ARC\s*A580"],
     "ram": 16, "ssd": 512, "nvme": True, "watt": 550},
    {"amt": 100000, "label": "গেমিং", "use": "১০৮০পি-তে বেশিরভাগ গেম ভালো সেটিংসে",
     "cpu": [r"I5[\s-]*1[34]400F", r"RYZEN 5 5600X\b|RYZEN 5 5600(?![GT\d])", r"I5[\s-]*12400F"],
     "gpu": [r"RTX\s*5060(?!\s*TI)|RX\s*9060(?!\s*XT)|ARC\s*B580", r"RTX\s*4060(?!\s*TI)|RX\s*7600(?!\s*XT)", r"RX\s*6600|RTX\s*3060"],
     "ram": 16, "ssd": 512, "nvme": True, "watt": 650},
    {"amt": 150000, "label": "গেমিং ও কনটেন্ট তৈরি", "use": "১০৮০পি/১৪৪০পি গেমিং, স্ট্রিমিং আর ভারী ভিডিও এডিটিং",
     "cpu": [r"RYZEN 5 (7600|9600)(?!X3D)", r"I5[\s-]*1[34]400F", r"RYZEN 7 5700X\b"],
     "gpu": [r"RTX\s*5060\s*TI|RX\s*9060\s*XT|RTX\s*4060\s*TI", r"RTX\s*5060(?!\s*TI)|RX\s*9060(?!\s*XT)|ARC\s*B580|RTX\s*4060"],
     "ram": 32, "ssd": 1024, "nvme": True, "watt": 650, "ram_min": 16},
]


def build_all(items, pick_ok=lambda i: True):
    """ফেরত: [{amt, label, use, parts: [(ভূমিকা, item)], total, socket, ddr, igpu}]"""
    def pool(cat):
        rx = re.compile(OK_BRAND.get(cat, "."), re.I)
        return [i for i in items.values() if i["category"] == cat and i["best"] and not i["sus"] and pick_ok(i)
                and not BAD.search(i["name"]) and rx.search(i["name"]) and not re.search(r"DEMO|BULK", i["name"].upper())
                and i["best"]["price"] >= MIN_PRICE.get(cat, 0)]

    pr = lambda i: i["best"]["price"]
    rank = lambda i: (pr(i), -i["live_count"])  # সমান দামে বেশি দোকানেরটা
    cpus = [(i, cpu_info(i["name"])) for i in pool("processor")]
    cpus = [(i, c) for i, c in cpus if c]
    mbs = [(i, mb_info(i["name"])) for i in pool("motherboard")]
    mbs = [(i, m) for i, m in mbs if m and m["matx"]]
    rams = []
    for i in pool("desktop-ram"):
        d = re.search(r"DDR([45])", i["name"].upper())
        g = gb_of(i["name"])
        if d and g and not re.search(r"SODIMM|LAPTOP|NOTEBOOK", i["name"].upper()):
            rams.append((i, g, f"DDR{d.group(1)}"))
    ssds = [(i, ssd_info(i["name"])) for i in pool("ssd")]
    ssds = [(i, s_) for i, s_ in ssds if s_ and s_["nvme"] or (s_ and re.search(r"M\.2", i["name"].upper()))]
    psus = [(i, psu_watt(i["name"])) for i in pool("power-supply")]
    psus = [(i, w) for i, w in psus if w]
    cases = [i for i in pool("casing") if not re.search(r"MINI[\s-]?ITX|\bITX\b|PSU|POWER SUPPLY|\bWITH\s+\d{3}\s?W", i["name"].upper())]
    coolers = [i for i in pool("cpu-cooler") if not re.search(r"LIQUID|AIO|\b(240|280|360)\b|PASTE|HUB|CONTROLLER|LAPTOP", i["name"].upper())]
    gpus = [i for i in pool("graphics-card")]

    def first(lst, ok):
        c = [x for x in lst if ok(x)]
        return min(c, key=lambda x: rank(x[0] if isinstance(x, tuple) else x)) if c else None

    out = []
    for t in TIERS:
        case = first(cases, lambda x: True)
        if not case:
            continue
        gpu_rx = t["gpu"] or [None]
        done = None
        # পছন্দের ক্রমে (GPU আগে, তারপর CPU) প্রথম যেটা বাজেটে ধরে
        combos = sorted(((g, c) for g in range(len(gpu_rx)) for c in range(len(t["cpu"]))), key=lambda x: (x[0] + x[1], x[0]))
        for gi, ci_ in combos:
            grx, crx = gpu_rx[gi], t["cpu"][ci_]
            gpu = first(gpus, lambda x: re.search(grx, x["name"].upper())) if grx else None
            if grx and not gpu:
                continue
            for need_ram in [t["ram"]] + ([t["ram_min"]] if t.get("ram_min") else []):
                cands = [(i, c) for i, c in cpus if re.search(crx, i["name"].upper()) and (gpu or c["igpu"])]
                cpu = min(cands, key=lambda x: rank(x[0])) if cands else None
                if not cpu:
                    break
                mb = first(mbs, lambda x: x[1]["socket"] == cpu[1]["socket"])
                if not mb:
                    break
                ram = first(rams, lambda x: x[2] == mb[1]["ddr"] and x[1] >= need_ram)
                ssd = first(ssds, lambda x: x[1]["gb"] >= t["ssd"] * 0.9 and (x[1]["nvme"] or not t["nvme"]))
                psu = first(psus, lambda x: x[1] >= t["watt"] and (not gpu or re.search(r"80\s*\+|80\s*PLUS|BRONZE|GOLD", x[0]["name"].upper())))
                if not (ram and ssd and psu):
                    continue
                parts = [("প্রসেসর", cpu[0]), ("মাদারবোর্ড", mb[0]), ("র‍্যাম", ram[0]), ("SSD", ssd[0])]
                if gpu:
                    parts.append(("গ্রাফিক্স কার্ড", gpu))
                if cpu[1]["cooler"]:
                    cool = first(coolers, lambda x: True)
                    if not cool:
                        continue
                    parts.append(("সিপিইউ কুলার", cool))
                parts += [("পাওয়ার সাপ্লাই", psu[0]), ("কেসিং", case)]
                total = sum(pr(p) for _, p in parts)
                if total <= t["amt"]:
                    done = {"amt": t["amt"], "label": t["label"], "use": t["use"], "parts": parts, "total": total,
                            "socket": cpu[1]["socket"], "ddr": mb[1]["ddr"], "igpu": not gpu}
                    break
            if done:
                break
        if done:
            out.append(done)
    return out
