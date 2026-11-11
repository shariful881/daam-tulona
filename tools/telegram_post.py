"""আজকের সবচেয়ে বেশি দাম কমা প্রোডাক্টগুলো Telegram চ্যানেলে পোস্ট করে।

চালু করতে (একবারই):
  ১) Telegram-এ @BotFather → /newbot → যে টোকেন দেয় সেটা রিপোর Settings → Secrets and variables → Actions →
     Secrets-এ TELEGRAM_BOT_TOKEN নামে রাখুন।
  ২) নিজের চ্যানেল বানিয়ে বটকে অ্যাডমিন করুন। চ্যানেলের ঠিকানা (যেমন @daamtulona) Variables-এ TELEGRAM_CHANNEL নামে রাখুন।
টোকেন বা চ্যানেল না থাকলে কিছুই করে না। প্রতিদিনের দাম আপডেটের পরে নিজে থেকে চলে।
চালানো: python tools/telegram_post.py dist/drops.json
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BN = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def taka(n):
    return "৳" + f"{int(n):,}"


def main(path):
    token, chat = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHAT")
    if not token or not chat:
        print("Telegram টোকেন/চ্যানেল সেট নেই, পোস্ট বাদ")
        return
    drops = json.load(open(path, encoding="utf-8"))[:8]
    if not drops:
        print("আজ দাম কমেনি, পোস্ট নেই")
        return
    day = datetime.now(timezone(timedelta(hours=6))).strftime("%d/%m/%Y").translate(BN)
    lines = [f"<b>আজ দাম কমেছে</b> ({day})", ""]
    for d in drops:
        name = d["name"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lines.append(f"▼ <a href=\"{d['url']}\">{name}</a>\n   {taka(d['new'])} (আগে {taka(d['old'])}, {taka(d['old'] - d['new'])} কম) · {d['store']}")
    lines += ["", "সব দোকানের দাম মিলিয়ে দেখুন: দামতুলনা"]
    body = urllib.parse.urlencode({"chat_id": chat, "text": "\n".join(lines), "parse_mode": "HTML",
                                   "disable_web_page_preview": "true"}).encode()
    with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", body, timeout=30) as r:
        print("পোস্ট হয়েছে" if json.load(r).get("ok") else "পোস্ট হয়নি")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dist/drops.json")
