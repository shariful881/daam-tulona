"""IndexNow: আজ নতুন বা বদলানো পাতার ঠিকানা Bing, Yandex, Seznam ইত্যাদি সার্চ ইঞ্জিনকে জানানো।

web.build যে .indexnow.json লেখে সেটা পড়ে api.indexnow.org-এ পাঠায় (একবারে সর্বোচ্চ ১০,০০০ ঠিকানা)।
সাইট প্রকাশের পরে চালাতে হয়, কারণ সার্চ ইঞ্জিন সাইটে রাখা চাবির ফাইল (<key>.txt) মিলিয়ে দেখে।
Google IndexNow ব্যবহার করে না; Google-এর জন্য সাইটম্যাপই যথেষ্ট।
"""
import json
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

f = Path(__file__).resolve().parent.parent / ".indexnow.json"
if not f.exists():
    print("IndexNow: বন্ধ বা কিছু পাঠানোর নেই")
    sys.exit(0)
d = json.loads(f.read_text())
if not d.get("urls"):
    print("IndexNow: আজ বদলানো পাতা নেই")
    sys.exit(0)
body = json.dumps({"host": urlparse(d["site"]).netloc, "key": d["key"], "keyLocation": d["keyLocation"],
                   "urlList": d["urls"][:10000]}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, method="POST",
                             headers={"Content-Type": "application/json; charset=utf-8"})
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        print(f"IndexNow: {len(d['urls'])}টি ঠিকানা পাঠানো হয়েছে (HTTP {r.status})")
except Exception as e:  # সার্চ ইঞ্জিন না নিলেও দামের রান থামবে না
    print(f"IndexNow: পাঠানো যায়নি ({e})")
