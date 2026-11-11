"""ক্যাটাগরি আইকনের স্প্রাইট বানায়: config/category_icons.json → web/static/cat-icons.svg

আইকনগুলো Tabler Icons (MIT লাইসেন্স, https://tabler.io/icons) থেকে নেওয়া।
আইকন বদলাতে: config/category_icons.json-এ নাম বদলান, তারপর চালান:
    npm i @tabler/icons   (যেকোনো ফোল্ডারে)
    python tools/build_icons.py <সেই-ফোল্ডার>/node_modules/@tabler/icons/icons/outline
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(src: str) -> None:
    src_dir = Path(src)
    cfg = json.loads((ROOT / "config/category_icons.json").read_text())
    names = sorted({v for sec in ("groups", "leaves") for v in cfg[sec].values()} | {"box"})
    out, missing = [], []
    for n in names:
        f = src_dir / f"{n}.svg"
        if not f.exists():
            missing.append(n)
            continue
        body = re.search(r"<svg[^>]*>(.*)</svg>", f.read_text(), re.S).group(1)
        body = re.sub(r'<path stroke="none" d="M0 0h24v24H0z" fill="none"\s*/>', "", body)
        body = re.sub(r"\s+", " ", body).strip()
        out.append(f'<symbol id="i-{n}" viewBox="0 0 24 24">{body}</symbol>')
    if missing:
        sys.exit("এই আইকনগুলো পাওয়া যায়নি: " + ", ".join(missing))
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" style="display:none">'
           "<!-- Tabler Icons, MIT License, https://tabler.io/icons -->" + "".join(out) + "</svg>\n")
    (ROOT / "web/static/cat-icons.svg").write_text(svg)
    print(f"{len(out)}টি আইকন লেখা হয়েছে, {len(svg) // 1024} KB")


if __name__ == "__main__":
    main(sys.argv[1])
