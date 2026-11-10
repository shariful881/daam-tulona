"""ব্র্যান্ডের নিজস্ব সাইটের প্রোডাক্ট পাতা থেকে পাওয়া স্পেক (সাইজ, ধরন, কম্প্রেসর ওয়ারেন্টি) জমা রাখা,
যাতে প্রতিদিন সব পাতা আবার খুলতে না হয়। ফাইল: data/brand_specs/<store>.json  {url: {...}}"""
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data/brand_specs"


def load(store: str) -> dict:
    f = DIR / f"{store}.json"
    return json.loads(f.read_text()) if f.exists() else {}


def save(store: str, data: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    (DIR / f"{store}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True))


def fresh(spec: dict | None, days: int = 30) -> bool:
    return bool(spec) and (date.today() - date.fromisoformat(spec.get("seen", "2000-01-01"))).days < days


def years(text: str | None) -> str | None:
    m = re.search(r"(\d+)\s*(year|yr)", text or "", re.I)
    return f"{m.group(1)} Years" if m else None
