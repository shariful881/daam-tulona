"""নতুন সাইট পরীক্ষা: robots.txt অনুমতি দেয় কিনা, পাতা খোলে কিনা, Cloudflare আছে কিনা।
ফলাফল probe/ ফোল্ডারে (summary.json + প্রতিটা পাতার HTML), workflow সেটা probe-data ব্রাঞ্চে রাখে।
চালানো: python -m tools.probe URL1 URL2 ...
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests

from scraper.common import USER_AGENT

OUT = Path("probe")


def main(urls):
    OUT.mkdir(exist_ok=True)
    robots, res = {}, []
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en,bn;q=0.8"})
    for i, url in enumerate(urls):
        host = "{0.scheme}://{0.netloc}".format(urlsplit(url))
        if host not in robots:
            rp, txt = RobotFileParser(), ""
            try:
                r = s.get(host + "/robots.txt", timeout=30)
                txt = r.text if r.ok else f"HTTP {r.status_code}"
                rp.parse(txt.splitlines() if r.ok else [])
            except Exception as e:
                txt = f"ERR {e}"
                rp.parse([])
            robots[host] = (rp, txt[:3000])
        rp, txt = robots[host]
        allowed = rp.can_fetch(USER_AGENT, url) if not url.endswith("/robots.txt") else True
        row = {"url": url, "allowed": allowed, "robots": txt}
        if allowed:
            try:
                r = s.get(url, timeout=40)
                h = r.text
                row.update(status=r.status_code, final=r.url, size=len(h),
                           title=(re.search(r"<title[^>]*>(.*?)</title>", h, re.S | re.I) or [None, ""])[1].strip()[:150],
                           cloudflare=("cf-ray" in r.headers) and ("Just a moment" in h or r.status_code in (403, 503)),
                           server=r.headers.get("server"))
                if not ("<urlset" in h[:3000] or "<sitemapindex" in h[:3000]):  # sitemap পুরোটা
                    # স্টাইল/স্ক্রিপ্ট/svg বাদ দিয়ে রাখা (বড় থিমে প্রোডাক্ট কার্ড ৬০০KB-এর পরে পড়ে)
                    h = re.sub(r"<(style|script|svg)\b[^>]*>.*?</\1>", "", h, flags=re.S | re.I)[:1500000]
                (OUT / f"{i:02d}.html").write_text(h)
                row["file"] = f"{i:02d}.html"
            except Exception as e:
                row["error"] = str(e)[:300]
        res.append(row)
        print(row.get("status"), allowed, url, row.get("title", row.get("error", "")), flush=True)
        time.sleep(3)
    (OUT / "summary.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
