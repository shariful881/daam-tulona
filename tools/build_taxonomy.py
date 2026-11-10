"""config/taxonomy_spec.json (নিজস্ব ক্যাটাগরি) + data/catalog/startech.json (Star Tech-এর লিংক ও সংখ্যা)
থেকে config/taxonomy.json বানায়, যেটা প্রতিদিনের রান ব্যবহার করে।

চালানো: python -m tools.build_taxonomy
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    spec = json.loads((ROOT / "config/taxonomy_spec.json").read_text())
    cat = json.loads((ROOT / "data/catalog/startech.json").read_text())
    legacy = json.loads((ROOT / "config/categories.json").read_text())["categories"]
    legacy = {c["slug"]: c for c in legacy}
    ef = ROOT / "config/store_categories.json"
    extra = json.loads(ef.read_text()) if ef.exists() else {}

    src = {}
    for top in cat["categories"]:
        src[top["name"]] = (top["url"], top["total"] or 0)
        for s in top["subcategories"]:
            src[f"{top['name']}/{s['name']}"] = (s["url"], s["total"] or 0)

    groups = []
    for g in spec["groups"]:
        leaves = []
        for l in g["leaves"]:
            sources = []
            for ref in l["sources"]:
                url, n = src[ref]
                if n:
                    sources.append({"url": url, "max_pages": n // 90 + 2})
            if not sources:
                continue
            stores = {"startech": {"sources": sources, "limit": 90}}
            for sid, conf in legacy.get(l["slug"], {}).get("stores", {}).items():
                if sid != "startech":
                    stores[sid] = conf
            for sid, cats in extra.items():  # config/store_categories.json (অন্য স্টোরের ক্যাটাগরি)
                if not sid.startswith("_") and l["slug"] in cats and sid not in stores:
                    stores[sid] = cats[l["slug"]]
            leaves.append({"slug": l["slug"], "name_bn": l["bn"], "name_en": l["en"], "group": g["slug"],
                           "count": sum(src[r][1] for r in l["sources"]), "stores": stores})
        if leaves:
            groups.append({"slug": g["slug"], "name_bn": g["bn"], "name_en": g["en"], "leaves": leaves})

    out = {"_নোট": "স্বয়ংক্রিয়ভাবে তৈরি (tools/build_taxonomy.py) — হাতে এডিট করবেন না। বদল করুন config/taxonomy_spec.json-এ।",
           "groups": groups}
    (ROOT / "config/taxonomy.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    pages = sum(s["max_pages"] for g in groups for l in g["leaves"] for s in l["stores"]["startech"]["sources"])
    print(f"গ্রুপ: {len(groups)} | ক্যাটাগরি: {sum(len(g['leaves']) for g in groups)} | Star Tech সর্বোচ্চ পাতা: {pages}")


if __name__ == "__main__":
    main()
