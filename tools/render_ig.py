"""বাজার আপডেটের ইনফোগ্রাফিক আর শেয়ার কার্ড থেকে JPG ছবি বানানো (সাইট বানানোর পরে চলে)।

dist/_ig_jobs.json-এ প্রতিটা রিপোর্টের পাথ; প্রতিটায় ig.html (পূর্ণ ইনফোগ্রাফিক) আর card.html (১২০০×৬৩০)।
ফলাফল: <path>/infographic.jpg আর <path>/share.jpg। বানানো শেষে html দুটো মুছে ফেলা হয়।
"""
import functools
import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path

DIST = Path(__file__).resolve().parent.parent / "dist"


def main():
    jobs = json.loads((DIST / "_ig_jobs.json").read_text()) if (DIST / "_ig_jobs.json").exists() else []
    if not jobs:
        print("ইনফোগ্রাফিক বানানোর কিছু নেই")
        return
    from playwright.sync_api import sync_playwright
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    handler = functools.partial(Quiet, directory=str(DIST))
    srv = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    ok = 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for path in jobs:
            d = DIST / path
            try:
                pg.set_viewport_size({"width": 1080, "height": 1350})
                pg.goto(f"http://127.0.0.1:{port}/{path}/ig.html")
                pg.evaluate("document.fonts.ready")
                pg.locator("svg").screenshot(path=str(d / "infographic.jpg"), type="jpeg", quality=76)
                pg.set_viewport_size({"width": 1200, "height": 630})
                pg.goto(f"http://127.0.0.1:{port}/{path}/card.html")
                pg.evaluate("document.fonts.ready")
                pg.locator("svg").screenshot(path=str(d / "share.jpg"), type="jpeg", quality=86)
                ok += 1
            except Exception as e:  # একটা ব্যর্থ হলে বাকিগুলো চলবে
                print("ছবি হয়নি:", path, e, file=sys.stderr)
            for f in ("ig.html", "card.html"):
                (d / f).unlink(missing_ok=True)
        b.close()
    srv.shutdown()
    (DIST / "_ig_jobs.json").unlink(missing_ok=True)
    print(f"{ok}/{len(jobs)}টি রিপোর্টের ছবি তৈরি হয়েছে")


if __name__ == "__main__":
    main()
