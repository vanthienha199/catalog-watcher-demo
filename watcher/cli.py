"""Command line entry point: crawl, store, compare and report."""

from __future__ import annotations

import argparse
import os
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


def _short(path) -> str:
    """Paths relative to the working directory, so logs never expose a home folder."""
    try:
        return os.path.relpath(path)
    except ValueError:
        return str(path)


def run(args: argparse.Namespace) -> int:
    store = Store(Path(args.db))
    started = time.perf_counter()
    pages = {"n": 0}

    print(f"{BOLD}Catalogue watcher{OFF} {DIM}(sample project){OFF}")
    print(f"  source   {args.source_label or args.source}")
    print(f"  engine   {args.engine}")
    print(f"  database {_short(args.db)}\n")

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

    run_id = store.save_run([p.as_dict() for p in products], args.source, args.engine,
                            pages=pages["n"], seconds=seconds, source_label=args.source_label)
    prev_id = store.previous_run_id(run_id)
    previous = [prev_id] if prev_id else []
    changes = store.compare(prev_id, run_id) if prev_id else []

    csv_path = store.export_csv(run_id, Path(args.out_dir) / f"run-{run_id}.csv")
    report_path = write_report(store, run_id, Path(args.out_dir), args.theme)

    drops = sum(1 for c in changes if c.kind == "price_drop")
    print(f"\n  {BOLD}{len(products)} products{OFF} stored as run {run_id} in {seconds:.1f}s")
    if previous:
        print(f"  {len(changes)} changes against run {previous[0]}, including {drops} price drops")
    else:
        print("  first run, nothing to compare against yet")
    print(f"  csv      {_short(csv_path)}")
    print(f"  report   {_short(report_path)}")
    return 0


def write_report(store: Store, run_id: int, out_dir: Path, theme: str = "dark") -> Path:
    row = store.run(run_id)
    if row is None:
        raise SystemExit(f"no run {run_id} in the database")
    prev_id = store.previous_run_id(run_id)
    changes = store.compare(prev_id, run_id) if prev_id else []
    keys = row.keys()
    return build_report(
        store.observations(run_id),
        changes,
        {
            "title": "Catalogue watch",
            "run_id": run_id,
            "previous_run_id": prev_id,
            "started_at": row["started_at"],
            "pages": row["pages"] if "pages" in keys else None,
            "seconds": row["seconds"] if "seconds" in keys else None,
            "engine": row["engine"],
            "source": row["source"],
            "source_label": row["source_label"] if "source_label" in keys else None,
            "theme": theme,
        },
        out_dir / f"report-{run_id}.html",
        previous_rows=store.observations(prev_id) if prev_id else None,
    )


def report(args: argparse.Namespace) -> int:
    store = Store(Path(args.db))
    run_id = args.run or store.runs(limit=1)[0]["id"]
    path = write_report(store, run_id, Path(args.out_dir), args.theme)
    print(f"  report   {_short(path)}")
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
    r.add_argument("--source-label", default=None, help="friendly source name shown in the report")
    r.add_argument("--theme", choices=["dark", "light"], default="dark")
    r.set_defaults(func=run)

    rp = sub.add_parser("report", help="rebuild the HTML report for a stored run")
    rp.add_argument("--run", type=int, default=None, help="run id, default the latest")
    rp.add_argument("--theme", choices=["dark", "light"], default="dark")
    rp.add_argument("--db", default=str(ROOT / "data" / "catalog.db"))
    rp.add_argument("--out-dir", default=str(ROOT / "data"))
    rp.set_defaults(func=report)

    h = sub.add_parser("history", help="list previous runs")
    h.add_argument("--db", default=str(ROOT / "data" / "catalog.db"))
    h.set_defaults(func=history)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
