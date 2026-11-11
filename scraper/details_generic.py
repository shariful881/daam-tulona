"""Star Tech ছাড়া অন্য স্টোরের প্রোডাক্ট পাতা থেকে স্পেক (PC House, Creatus, Smart, Diamu, Apple Gadgets, Four Star…)।

শুধু তথ্য (স্পেক টেবিল, "কী: মান" ফিচার লাইন) নেওয়া হয়; স্টোরের লেখা বিবরণ বা ছবি নয়।
ফেরত Star Tech-এর মতো একই আকারে: {"specs": {অংশ: {কী: মান}}, "key_features": [...], "model", "mpn"}
"""
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
