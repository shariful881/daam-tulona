"""'এক নজরে': প্রোডাক্টের ধরন অনুযায়ী দরকারি তথ্যগুলো বেছে, বাংলা নামে, ঠিক ক্রমে সাজানো।

তথ্যের উৎস (আগেরটা পেলে পরেরটা লাগে না):
  ১. স্টোরের পূর্ণ স্পেক টেবিল (details)      ২. তালিকার কার্ডের মূল ফিচার লাইন
  ৩. ব্র্যান্ড স্টোরের স্পেক (Walton/Minister)  ৪. প্রোডাক্টের নাম থেকে বের করা
কোন ধরনের প্রোডাক্টে কোন ঘর: config/spec_schema.json (tools/make_spec_schema.py বানায়)
"""
import json
import re
from functools import lru_cache
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "config/spec_schema.json"
SKIP_IDS = {"warranty"}  # ওয়ারেন্টি পাতায় আলাদা করে দেখানো হয়
KEY_SPLIT = re.compile(r",\s*(?=[A-Za-z][\w /&().-]{1,28}:)")


@lru_cache(maxsize=1)
def schema():
    s = json.loads(SCHEMA_PATH.read_text())
    comp = {}
    for name, fields in list(s["profiles"].items()) + [("_generic", s["generic"])]:
        comp[name] = [dict(f, _k=[re.compile(r) for r in f["k"]], _x=[re.compile(r) for r in f.get("x", [])],
                           _n=re.compile(f["n"], re.I) if f.get("n") else None) for f in fields]
    return comp, s["category_profile"]


def feature_pairs(feats):
    """'RAM: 8GB DDR4, Storage: 256GB SSD' -> [('RAM','8GB DDR4'), ('Storage','256GB SSD')]; কোলন ছাড়া লাইন -> (None, লাইন)"""
    out = []
    for f in feats or []:
        for part in KEY_SPLIT.split(f):
            k, sep, v = part.partition(":")
            if sep and v.strip() and 0 < len(k.strip()) <= 30:
                out.append((k.strip(), v.strip()))
            elif part.strip():
                out.append((None, part.strip()))
    return out


def clean(v):
    v = re.sub(r"\s*\n\s*", ", ", str(v)).strip(" ,")
    v = re.sub(r"\s{2,}", " ", v)
    return v if len(v) <= 160 else v[:157].rsplit(" ", 1)[0] + "…"


def key_specs(category, name, det_specs=None, feats=None, brand_spec=None, key_bn=None):
    """ফেরত: [(বাংলা নাম, মান), ...] — প্রোফাইলের ক্রমে, তারপর কোনো ঘরে না পড়া ফিচার লাইন।"""
    comp, cat_prof = schema()
    fields = comp.get(cat_prof.get(category), comp["_generic"])
    rows = []  # (মেলানোর লেখা, মূল কী, মান)
    for sec, kv in (det_specs or {}).items():
        for k, v in (kv or {}).items():
            if v not in (None, ""):
                rows.append((f"{sec} > {k}".lower(), k, v))
    loose = []
    for k, v in feature_pairs(feats):
        if k is None:
            loose.append(v)
        else:
            rows.append((f" > {k}".lower(), k, v))
    feat_text = " | ".join(v for _, _, v in rows if not str(v).startswith("http")) + " | " + " | ".join(loose)
    used, out, have = set(), [], set()
    for f in fields:
        if f["id"] in SKIP_IDS:
            continue
        vals = []
        for rx in f["_k"]:  # আগের রেজেক্সের অগ্রাধিকার বেশি
            for i, (lab, _, v) in enumerate(rows):
                if len(vals) >= f.get("m", 1):
                    break
                if i in used or not rx.search(lab) or any(r.search(lab) for r in f["_x"]):
                    continue
                used.add(i)
                cv = clean(v)
                toks = set(re.findall(r"\w+", cv.lower()))
                if not any(cv.lower() in x.lower() or x.lower() in cv.lower() or toks == set(re.findall(r"\w+", x.lower()))
                           for x in vals):
                    vals.append(cv)
        val = " · ".join(vals)
        if not val and brand_spec and f.get("b") and brand_spec.get(f["b"]) not in (None, ""):
            bv = brand_spec[f["b"]]
            val = ("হ্যাঁ" if bv else "না") if isinstance(bv, bool) else f.get("bf", "{}").format(clean(bv))
        if not val and f["_n"]:  # নাম থেকে, না পেলে ফিচার লাইনের লেখা থেকে
            for text in (name, feat_text):
                m = f["_n"].search(text or "")
                if m:
                    g = next((x for x in m.groups() if x), m.group(0)).strip()
                    val = f.get("f", "{}").format(g)
                    break
        if val and f["bn"] not in have:
            have.add(f["bn"])
            out.append((f["bn"], val))
    # কোনো ঘরে পড়েনি এমন ফিচার লাইন (স্পেক টেবিলের বাকিগুলো পূর্ণ স্পেসিফিকেশনে আছে)
    extra = 0
    shown = " ".join(v for _, v in out).lower()
    for i, (lab, k, v) in enumerate(rows):
        if det_specs or i in used or not lab.startswith(" > ") or extra >= 4:  # পূর্ণ স্পেক থাকলে বাকিটা নিচের টেবিলে
            continue
        kb = (key_bn or {}).get(k.lower(), k)
        if kb not in have and "warrant" not in lab and clean(v).lower() not in shown:
            out.append((kb, clean(v)))
            have.add(kb)
            extra += 1
    return out, ([] if det_specs else loose[:4])
