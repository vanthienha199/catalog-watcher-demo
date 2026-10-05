"""Build 30 days of price history from the practice store, then run the watcher once a day.

books.toscrape.com never changes its prices, so a watcher pointed at it would
never find anything. This script copies the two Mystery pages fetched from the
live site (fixtures/original/) into one local folder per day and moves prices
the way a real shop does: small drifts, a few markdowns, a price rise and one
book selling out. Each day's copy is served over HTTP and crawled by the real
watcher with a back-dated run date. Day 1 is a crawl of the live site itself.
One day (day 17) the "site" is unreachable, so the run history also shows how
a failed run is recorded and reported.

    python fixtures/make_history.py            # writes data/catalog.db, reports, alerts
"""

from __future__ import annotations

import http.server
import random
import re
import shutil
import socketserver
import sys
import threading
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from watcher.cli import main as watcher  # noqa: E402

ORIG = HERE / "original"
DAYS = HERE / "days"
PAGES = ("index.html", "page-2.html")
FIRST_DAY = date(2026, 9, 1)
N_DAYS = 30
FAILED_DAY = 17
PRICE = re.compile(r'(<p class="price_color">£)([0-9]+\.[0-9]{2})(</p>)')
IN_STOCK = '<i class="icon-ok"></i>\n    \n        In stock\n    \n</p>'
OUT_STOCK = '<i class="icon-remove"></i>\n    \n        Out of stock\n    \n</p>'

# scripted events: (day, product position 0..31, kind, value)
EVENTS = [
    (4, 0, "set", 1.04),      # the lead book creeps up, dips, then drops hard on day 30
    (11, 0, "set", 1.06),
    (19, 0, "set", 0.97),
    (25, 0, "set", 1.01),
    (30, 0, "set", 0.836),
    (5, 14, "set", 1.03),
    (16, 14, "set", 0.98),
    (30, 14, "set", 0.886),
    (8, 22, "set", 0.97),
    (22, 22, "set", 1.02),
    (30, 22, "set", 0.903),
    (6, 3, "set", 0.88),      # a markdown of 12 percent
    (12, 3, "set", 0.80),     # deeper markdown on the same book
    (9, 11, "set", 1.07),     # a price rise
    (14, 20, "set", 0.91),
    (13, 9, "set", 0.96),
    (30, 9, "set", 1.12),     # day 30 rise
    (21, 7, "set", 0.93),
    (24, 26, "set", 1.05),
    (30, 5, "soldout", None),  # day 30 sells out
]


def originals() -> list[tuple[str, list[float]]]:
    out = []
    for name in PAGES:
        html = (ORIG / name).read_text(encoding="utf-8")
        out.append((name, [float(m.group(2)) for m in PRICE.finditer(html)]))
    return out


def build_day(day: int, rng: random.Random, state: dict) -> Path:
    """Write day N's pages and return the folder."""
    folder = DAYS / f"day-{day:02d}" / "catalogue/category/books/mystery_3"
    folder.mkdir(parents=True, exist_ok=True)
    for kind_day, pos, kind, value in EVENTS:
        if kind_day == day:
            if kind == "set":
                state["factor"][pos] = value
            else:
                state["soldout"].add(pos)
    # a little background drift on a few books, the way real shops reprice
    if day > 1 and day % 4 == 0:
        pos = rng.randrange(32)
        state["factor"][pos] = round(state["factor"].get(pos, 1.0) * rng.choice([0.97, 0.98, 1.02, 1.03]), 4)
    offset = 0
    for name, base_prices in state["originals"]:
        html = (ORIG / name).read_text(encoding="utf-8")
        idx = {"i": 0}

        def repl(m):
            i = offset + idx["i"]
            idx["i"] += 1
            price = round(float(m.group(2)) * state["factor"].get(i, 1.0), 2)
            return f"{m.group(1)}{price:.2f}{m.group(3)}"

        html = PRICE.sub(repl, html)
        # sold out: flip the availability line of that product card
        cards = html.split('<article class="product_pod">')
        for k in range(1, len(cards)):
            if offset + k - 1 in state["soldout"]:
                cards[k] = cards[k].replace(IN_STOCK, OUT_STOCK, 1)
        html = '<article class="product_pod">'.join(cards)
        (folder / name).write_text(html, encoding="utf-8")
        offset += len(base_prices)
    return DAYS / f"day-{day:02d}"


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main() -> None:
    rng = random.Random(11)
    shutil.rmtree(DAYS, ignore_errors=True)
    data = ROOT / "data"
    for f in list(data.glob("*.db")) + list(data.glob("run-*.csv")) + list(data.glob("report-*.html")) + list((data / "alerts").glob("*") if (data / "alerts").exists() else []):
        f.unlink()
    state = {"factor": {}, "soldout": set(), "originals": originals()}

    handler = lambda *a, **k: Quiet(*a, directory=str(DAYS), **k)  # noqa: E731
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(("127.0.0.1", 8099), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    label = "The Mystery shelf at books.toscrape.com"
    try:
        for day in range(1, N_DAYS + 1):
            build_day(day, rng, state)
            when = (FIRST_DAY + timedelta(days=day - 1)).isoformat() + "T07:02:00-05:00"
            if day == 1:
                src = "https://books.toscrape.com/catalogue/category/books/mystery_3/index.html"
            elif day == FAILED_DAY:
                src = "http://127.0.0.1:8098/catalogue/category/books/mystery_3/index.html"  # nothing listens here
            else:
                src = f"http://127.0.0.1:8099/day-{day:02d}/catalogue/category/books/mystery_3/index.html"
            watcher(["run", "--source", src, "--source-label", label, "--max-pages", "2",
                     "--delay", "0.2", "--as-of", when, "--quiet", "--retries", "1", "--retry-wait", "0.2"])
    finally:
        srv.shutdown()
    print(f"built {N_DAYS} days of history in data/catalog.db")


if __name__ == "__main__":
    main()
