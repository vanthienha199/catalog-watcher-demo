"""Command line entry point: crawl, store, compare and report."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from .report import build as build_report
from .scrape import crawl
from .store import Store

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = "https://books.toscrape.com/catalogue/category/books/mystery_3/index.html"

GREEN = "\033[32m"
DIM = "\033[2m"
BOLD = "\033[1m"
OFF = "\033[0m"


def run(args: argparse.Namespace) -> int:
    store = Store(Path(args.db))
    started = time.perf_counter()
    pages = {"n": 0}

    print(f"{BOLD}Catalogue watcher{OFF} {DIM}(sample project){OFF}")
    print(f"  source   {args.source}")
    print(f"  engine   {args.engine}")
    print(f"  database {args.db}\n")

    def on_page(index: int, url: str, found: int) -> None:
        pages["n"] = index
        short = url.split("/")[-1] or url
        print(f"  {GREEN}page {index}{OFF}  {found:>3} products  {DIM}{short}{OFF}")

    products = crawl(
        args.source,
        category=args.category,
        max_pages=args.max_pages,
        delay=args.delay,
        engine=args.engine,
        on_page=on_page,
    )
    seconds = time.perf_counter() - started

    run_id = store.save_run([p.as_dict() for p in products], args.source, args.engine)
    previous = [r["id"] for r in store.runs(limit=5) if r["id"] != run_id]
    changes = store.compare(previous[0], run_id) if previous else []

    csv_path = store.export_csv(run_id, Path(args.out_dir) / f"run-{run_id}.csv")
    report_path = build_report(
        store.observations(run_id),
        changes,
        {
            "title": "Catalogue watch report",
            "subtitle": "Prices, ratings and stock pulled from a public practice store, compared against the previous run.",
            "pages": pages["n"],
            "seconds": seconds,
            "engine": args.engine,
            "source": args.source,
        },
        Path(args.out_dir) / f"report-{run_id}.html",
    )

    drops = sum(1 for c in changes if c.kind == "price_drop")
    print(f"\n  {BOLD}{len(products)} products{OFF} stored as run {run_id} in {seconds:.1f}s")
    if previous:
        print(f"  {len(changes)} changes against run {previous[0]}, including {drops} price drops")
    else:
        print("  first run, nothing to compare against yet")
    print(f"  csv      {csv_path}")
    print(f"  report   {report_path}")
    return 0


def history(args: argparse.Namespace) -> int:
    store = Store(Path(args.db))
    print(f"{BOLD}run  when                  products  engine  source{OFF}")
    for row in store.runs():
        print(f"{row['id']:>3}  {row['started_at']}  {row['products']:>8}  {row['engine']:<7} {row['source'][:48]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="watcher", description="Crawl a catalogue, store it, report what changed.")
    sub = parser.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="crawl and build a report")
    r.add_argument("--source", default=DEFAULT_SOURCE)
    r.add_argument("--category", default="Mystery")
    r.add_argument("--engine", choices=["http", "browser"], default="http")
    r.add_argument("--max-pages", type=int, default=3)
    r.add_argument("--delay", type=float, default=0.5)
    r.add_argument("--db", default=str(ROOT / "data" / "catalog.db"))
    r.add_argument("--out-dir", default=str(ROOT / "data"))
    r.set_defaults(func=run)

    h = sub.add_parser("history", help="list previous runs")
    h.add_argument("--db", default=str(ROOT / "data" / "catalog.db"))
    h.set_defaults(func=history)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
