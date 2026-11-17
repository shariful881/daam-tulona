"""মালিকের Telegram-এ সতর্কবার্তা পাঠানো (দামের রান ব্যর্থ/শুরু হয়নি/দোকান থেকে দাম আসেনি)।

দরকার: GitHub Secrets-এ TELEGRAM_BOT_TOKEN (বটের টোকেন) আর TELEGRAM_ALERT_CHAT (মালিকের chat id)।
সেট না থাকলে চুপচাপ কিছু করে না, রান কখনো আটকায় না।

ব্যবহার:
  python tools/tg_alert.py "বার্তা"
  python tools/tg_alert.py --stores      # data/health.json দেখে যে দোকান থেকে আজ দাম আসেনি তার তালিকা পাঠায়
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def send(text):
    tok, chat = os.environ.get("TG_TOKEN", "").strip(), os.environ.get("TG_ALERT_CHAT", "").strip()
    if not tok or not chat:
        print("Telegram সতর্কবার্তা সেট করা নেই, বাদ:", text)
        return
    data = urllib.parse.urlencode({"chat_id": chat, "text": text, "disable_web_page_preview": "true"}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data=data, timeout=20).read()
        print("Telegram-এ পাঠানো হয়েছে")
    except Exception as e:  # সতর্কবার্তা না গেলেও রান চলবে
        print("Telegram পাঠানো যায়নি:", type(e).__name__)


def store_problems():
    root = Path(__file__).resolve().parent.parent
    h = json.loads((root / "data" / "health.json").read_text())
    stores = json.loads((root / "config" / "stores.json").read_text())["stores"]
    bad = []
    for sid, s in (h.get("stores") or {}).items():
        if not isinstance(s, dict) or s.get("skipped") or not (stores.get(sid) or {}).get("enabled", True):
            continue
        name = (stores.get(sid) or {}).get("name", sid)
        errs = " ".join(s.get("errors") or [])
        if "ব্লক" in errs or "403" in errs:
            bad.append(f"• {name}: আমাদের আটকে দিয়েছে (ব্লক)")
        elif not s.get("items"):
            bad.append(f"• {name}: একটাও দাম আসেনি")
        elif s.get("partial_fail"):
            bad.append(f"• {name}: অর্ধেকের কম দাম এসেছে, আগের দাম রাখা হয়েছে")
        elif s.get("failed_cats"):
            bad.append(f"• {name}: {len(s['failed_cats'])}টি ক্যাটাগরি আসেনি")
    return bad


if __name__ == "__main__":
    if sys.argv[1:] == ["--stores"]:
        bad = store_problems()
        if bad:
            send("⚠️ দামতুলনা: আজ এই দোকানগুলো থেকে ঠিকমতো দাম আসেনি\n" + "\n".join(bad))
        else:
            print("সব দোকান ঠিক আছে")
    else:
        send(" ".join(sys.argv[1:]))
