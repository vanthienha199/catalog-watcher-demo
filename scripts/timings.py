"""Time each stage of the morning run on the stored history (for the proof image).

    python scripts/timings.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from watcher.alert import compose  # noqa: E402
from watcher.report import build  # noqa: E402
from watcher.store import Store  # noqa: E402

store = Store(ROOT / "data" / "catalog.db")
live = store.run(1)
last = store.runs(limit=1)[0]["id"]
prev = store.previous_run_id(last)
reps = 20
t = time.perf_counter()
for _ in range(reps):
    changes = store.compare(prev, last)
compare_s = (time.perf_counter() - t) / reps
with tempfile.TemporaryDirectory() as d:
    t = time.perf_counter()
    for _ in range(reps):
        build(store, last, Path(d) / "r.html")
    report_s = (time.perf_counter() - t) / reps
t = time.perf_counter()
for _ in range(reps):
    compose(changes, store.run(last), "£", "report.html")
alert_s = (time.perf_counter() - t) / reps
out = {"live_crawl_s": live["seconds"], "live_pages": live["pages"], "products": live["products"],
       "compare_ms": compare_s * 1000, "report_ms": report_s * 1000, "alert_ms": alert_s * 1000,
       "changes": len(changes)}
print(json.dumps(out, indent=1))
