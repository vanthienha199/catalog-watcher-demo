"""Command line entry point: crawl, store, compare, report and alert."""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import httpx

from .alert import write_and_send
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


def _reason(exc: Exception) -> str:
    if isinstance(exc, httpx.ConnectError):
        return "The site did not answer (connection refused)."
    if isinstance(exc, httpx.TimeoutException):
        return "The site timed out."
    if isinstance(exc, httpx.HTTPStatusError):
        return f"The site returned HTTP {exc.response.status_code}."
    return f"{type(exc).__name__}: {exc}"


def run(args: argparse.Namespace) -> int:
    store = Store(Path(args.db))
    out_dir = Path(args.out_dir)
    say = (lambda *a, **k: None) if args.quiet else print
    started = time.perf_counter()
    pages = {"n": 0}

    say(f"{BOLD}Catalogue Watch{OFF}")
    say(f"  source   {args.source_label or args.source}")
    say(f"  engine   {args.engine}")
    say(f"  database {_short(args.db)}\n")

    def on_page(index: int, url: str, found: int) -> None:
        pages["n"] = index
        short = url.split("/")[-1] or url
        say(f"  {GREEN}page {index}{OFF}  {found:>3} products  {DIM}{short}{OFF}")

    products, error = None, None
    for attempt in range(1, args.retries + 2):
        try:
            products = crawl(args.source, category=args.category, max_pages=args.max_pages,
                             delay=args.delay, engine=args.engine, on_page=on_page)
            break
        except (httpx.HTTPError, OSError) as exc:
            error = _reason(exc)
            say(f"  attempt {attempt} failed: {error}")
            if attempt <= args.retries:
                time.sleep(args.retry_wait)
    seconds = time.perf_counter() - started

    if products is None:
        tries = args.retries + 1
        msg = f"{error.rstrip('.')} after {tries} {'try' if tries == 1 else 'tries'}."
        run_id = store.save_failed_run(args.source, args.engine, msg, seconds, args.source_label, args.as_of)
        report_path = build_report(store, run_id, out_dir / f"report-{run_id}.html")
        say(f"\n  run {run_id} failed: {msg}")
        say(f"  report   {_short(report_path)} (shows the last good prices)")
        return 1

    run_id = store.save_run([p.as_dict() for p in products], args.source, args.engine,
                            pages=pages["n"], seconds=seconds, source_label=args.source_label, started_at=args.as_of)
    prev_id = store.previous_run_id(run_id)
    changes = store.compare(prev_id, run_id) if prev_id else []
    csv_path = store.export_csv(run_id, out_dir / f"run-{run_id}.csv")
    report_path = build_report(store, run_id, out_dir / f"report-{run_id}.html")
    alert_path = write_and_send(store, run_id, changes, out_dir, report_path)

    drops = sum(1 for c in changes if c.kind == "price_drop")
    say(f"\n  {BOLD}{len(products)} products{OFF} stored as run {run_id} in {seconds:.1f}s")
    if prev_id:
        say(f"  {len(changes)} changes against run {prev_id}, including {drops} price drops")
    else:
        say("  first run, nothing to compare against yet")
    say(f"  csv      {_short(csv_path)}")
    say(f"  report   {_short(report_path)}")
    say(f"  alert    {_short(alert_path) if alert_path else 'none, nothing changed'}")
    return 0


def report(args: argparse.Namespace) -> int:
    store = Store(Path(args.db))
    run_id = args.run or store.runs(limit=1)[0]["id"]
    path = build_report(store, run_id, Path(args.out_dir) / f"report-{run_id}.html")
    print(f"  report   {_short(path)}")
    return 0


def history(args: argparse.Namespace) -> int:
    store = Store(Path(args.db))
    print(f"{BOLD}run  when                       products  status{OFF}")
    for row in store.runs():
        status = "ok" if row["status"] == "ok" else f"failed: {row['error']}"
        print(f"{row['id']:>3}  {row['started_at']:<25}  {row['products']:>8}  {status}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="watcher", description="Crawl a catalogue, store it, report what changed.")
    sub = parser.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="crawl, compare, report and alert")
    r.add_argument("--source", default=DEFAULT_SOURCE)
    r.add_argument("--category", default="Mystery")
    r.add_argument("--engine", choices=["http", "browser"], default="http")
    r.add_argument("--max-pages", type=int, default=3)
    r.add_argument("--delay", type=float, default=0.5)
    r.add_argument("--retries", type=int, default=2, help="extra attempts before the run is recorded as failed")
    r.add_argument("--retry-wait", type=float, default=0.5)
    r.add_argument("--db", default=str(ROOT / "data" / "catalog.db"))
    r.add_argument("--out-dir", default=str(ROOT / "data"))
    r.add_argument("--source-label", default=None, help="friendly source name shown in the report")
    r.add_argument("--as-of", default=None, help="ISO timestamp to record as the run time (backfills)")
    r.add_argument("--quiet", action="store_true")
    r.set_defaults(func=run)

    rp = sub.add_parser("report", help="rebuild the HTML report for a stored run")
    rp.add_argument("--run", type=int, default=None, help="run id, default the latest")
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
