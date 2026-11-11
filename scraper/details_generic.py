"""Star Tech ছাড়া অন্য স্টোরের প্রোডাক্ট পাতা থেকে স্পেক (PC House, Creatus, Smart, Diamu, Apple Gadgets, Four Star…)।

শুধু তথ্য (স্পেক টেবিল, "কী: মান" ফিচার লাইন) নেওয়া হয়; স্টোরের লেখা বিবরণ বা ছবি নয়।
ফেরত Star Tech-এর মতো একই আকারে: {"specs": {অংশ: {কী: মান}}, "key_features": [...], "model", "mpn"}
"""
import json
import re

from bs4 import BeautifulSoup

# প্রতিটা স্টোরের স্পেক টেবিল কোথায় (না মিললে পাতার সব টেবিল দেখা হয়)
TABLE_SEL = {
    "pchouse": "#specification table",
    "creatus": ".table-responsive table.table-bordered",
    "smartbd": "#tabs-list-description table",
    "applegadgets": "table.table-auto",
    "fourstar": ".specification-table table, .specification-table",
    "ultratech": "#tab-specification table, table.table-bordered",
}
FEAT_SEL = ".short-description li, .product-short-description li, .short-desc li, .key-features li, .product-highlights li"
JUNK_KEY = re.compile(r"^(stock|status|price|regular price|special price|product id|customer care|sku|tenure|emi|"
                      r"availability|category|categories|tags?|share|quantity|delivery|shipping|reward points?|"
                      r"cash discount price|product code|brand|product|image|rating|summary|review|reviews|description)$", re.I)
KV = re.compile(r"^\s*([A-Za-z][\w /&().,+-]{0,38}?)\s*:\s*(.+)$")


def short(v):
    """ফিচারের মান, বাক্য নয় (স্টোরের লেখা অনুচ্ছেদ বাদ)"""
    return len(v) <= 120 and len(v.split()) <= 16 and not re.match(r"^(the|with|this|it|enjoy|our)\b", v.strip(), re.I)


def _lines(el):
    for br in el.find_all("br"):
        br.replace_with("\n")
    return [ln.strip() for ln in el.get_text("\n").splitlines() if ln.strip()]


def _tables(soup, store):
    sel = TABLE_SEL.get(store)
    found = soup.select(sel) if sel else []
    found = [t for t in found if t.name == "table"] or found
    if not found:
        found = soup.find_all("table")
    return found


def parse(html: str, store: str = "") -> dict:
    soup = BeautifulSoup(html, "html.parser")
    out = {"specs": {}, "key_features": []}
    for t in _tables(soup, store):
        if "emi" in t.get_text(" ", strip=True)[:200].lower() and "tenure" in t.get_text(" ", strip=True)[:200].lower():
            continue
        h = t.find_previous(["h2", "h3", "h4"])
        section = (h.get_text(" ", strip=True) if h else "") or "Specification"
        if len(section) > 40 or "emi" in section.lower():
            section = "Specification"
        rows = t.find_all("tr") or []
        for tr in rows:
            cells = tr.find_all(["th", "td"], recursive=False) or tr.find_all(["th", "td"])
            texts = [c.get_text(" ", strip=True) for c in cells]
            if len(cells) == 1 or (len(cells) >= 1 and all(not x for x in texts[1:])):
                if texts and texts[0] and len(texts[0]) <= 40:  # শিরোনাম সারি
                    section = texts[0].title() if texts[0].isupper() else texts[0]
                continue
            if len(cells) < 2:
                continue
            key, val_el = texts[0], cells[1]
            if not key or JUNK_KEY.match(key) or len(key) > 50:
                continue
            lines = _lines(val_el)
            kvs = [KV.match(ln) for ln in lines]
            if len(lines) >= 2 and sum(1 for m in kvs if m) >= max(2, len(lines) - 1):
                # "Display" -> "Display Size: 14 Inch / Display Type: LCD ..." : ঘরটাই একটা অংশ
                sec = out["specs"].setdefault(key, {})
                for m in kvs:
                    if m and not JUNK_KEY.match(m.group(1).strip()):
                        sec[m.group(1).strip()] = m.group(2).strip()
                continue
            val = "\n".join(lines).strip()
            if val and len(val) <= 300:  # লম্বা অনুচ্ছেদ (স্টোরের লেখা বিবরণ) নেওয়া হয় না
                out["specs"].setdefault(section, {})[key] = val
    # মূল ফিচার: সংক্ষিপ্ত বিবরণের "কী: মান" লাইন (লম্বা বাক্য বাদ)
    feats = []
    for li in soup.select(FEAT_SEL) or []:
        t = " ".join(li.get_text(" ", strip=True).split())
        m = KV.match(t)
        if m and not JUNK_KEY.match(m.group(1).strip()) and short(m.group(2)) and t not in feats:
            feats.append(t)
    if not feats:  # নির্দিষ্ট ঘর না মিললে: পাতার প্রথম তালিকা যার অন্তত ৩টা লাইন "কী: মান"
        for ul in soup.find_all("ul"):
            if ul.find_parent(["nav", "header", "footer"]):
                continue
            items = [" ".join(li.get_text(" ", strip=True).split()) for li in ul.find_all("li", recursive=False)]
            good = [t for t in items if (m := KV.match(t)) and not JUNK_KEY.match(m.group(1).strip())
                    and short(m.group(2)) and m.group(1).strip().lower() not in ("model", "mpn", "customer care")]
            if len(good) >= 3:
                feats = good
                break
    if not out["specs"] and not feats:  # কোনো টেবিল নেই (যেমন Diamu): বিবরণের "কী: মান" লাইনগুলোই স্পেক
        for li in soup.find_all("li"):
            t = " ".join(li.get_text(" ", strip=True).split())
            m = KV.match(t)
            if m and not JUNK_KEY.match(m.group(1).strip()) and short(m.group(2)):
                out["specs"].setdefault("Specification", {}).setdefault(m.group(1).strip(), m.group(2).strip())
    out["key_features"] = feats[:12]
    for sec in out["specs"].values():
        for k, v in sec.items():
            kl = k.lower()
            if kl in ("model", "model code", "product model", "model no", "model number") and "model" not in out:
                out["model"] = v
            if kl in ("mpn", "part number", "part no") and "mpn" not in out:
                out["mpn"] = v
    # ওয়ারেন্টি
    for sec in out["specs"].values():
        for k, v in sec.items():
            if "warrant" in k.lower() and "warranty" not in out:
                out["warranty"] = v.split("\n")[0][:80]
    out["specs"] = {s: r for s, r in out["specs"].items() if r}
    return out


def parse_brand(html: str, brand: str = "") -> dict:
    """ব্র্যান্ডের নিজের সাইটের বিবরণ পাতা: টেবিল, dl তালিকা, ASUS-এর ঘর, JSON-LD — যেটা পাওয়া যায়।"""
    soup = BeautifulSoup(html, "html.parser")
    for bad in soup.select("script:not([type='application/ld+json']), style, nav, header, footer, noscript"):
        bad.decompose()
    specs = {}

    def add(sec, k, v):
        k = " ".join((k or "").split()).strip(" :")
        # লম্বা ব্যাখ্যার লাইন (বিপণনের লেখা) বাদ, সর্বোচ্চ ৫ লাইন
        v = "\n".join([ln.strip() for ln in (v or "").splitlines() if ln.strip() and len(ln.strip()) <= 90][:5])
        if not k or not v or len(k) > 60 or k[0].isdigit() or len(v) > 400 or k.lower() == v.lower() or JUNK_KEY.match(k):
            return
        specs.setdefault(sec or "Specification", {}).setdefault(k, v)

    def sec_of(el):
        h = el.find_previous(["h2", "h3", "h4"])
        t = h.get_text(" ", strip=True) if h else ""
        return t if 0 < len(t) <= 40 else "Specification"

    # ASUS: শিরোনাম ঘর + মান ঘর
    for title in soup.select(".rowTableTitle"):
        box = title.find_parent(class_=re.compile("rowTable___|rowTable$"))
        vals = box.select("[class*=rowTableItems]") if box else []
        add("Specification", title.get_text(" ", strip=True), "\n".join(_lines(v) and "\n".join(_lines(v)) for v in vals))
    # টেবিল (২ ঘর); দুটোই বড় হাতের শিরোনাম হলে বাদ (Corsair-এর পাশাপাশি শিরোনাম সারি)
    for t in soup.find_all("table"):
        sec = sec_of(t)
        for tr in t.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            if len(cells) != 2:
                continue
            a, b = cells[0].get_text(" ", strip=True), cells[1]
            if a.isupper() and b.get_text(strip=True).isupper():
                continue
            add(sec, a, "\n".join(_lines(b)))
    # dl: dt/dd জোড়া
    for dl in soup.find_all("dl"):
        sec = sec_of(dl)
        for dt in dl.find_all("dt"):
            dd = dt.find_next_sibling("dd")
            if dd:
                add(sec, dt.get_text(" ", strip=True), "\n".join(_lines(dd)))
    # JSON-LD additionalProperty
    for sc in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(sc.string or "")
        except Exception:
            continue
        for obj in data if isinstance(data, list) else [data]:
            for ap in (obj.get("additionalProperty") or []) if isinstance(obj, dict) else []:
                if isinstance(ap, dict):
                    add("Specification", ap.get("name"), str(ap.get("value") or ""))
    out = {"specs": {s_: r for s_, r in specs.items() if r}, "key_features": []}
    for r in out["specs"].values():
        for k, v in r.items():
            if k.lower() in ("model", "model number", "model name", "part number") and "model" not in out:
                out["model"] = v.split("\n")[0][:80]
    return out
