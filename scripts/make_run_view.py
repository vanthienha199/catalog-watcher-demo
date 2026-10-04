"""Render the real CLI output and the real CSV into one page for a screenshot.

Nothing is retyped. The terminal block is the captured stdout of the run, with
colour codes stripped, and the table is read straight from the exported CSV.
"""

from __future__ import annotations

import csv
import html
import re
import sys
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;]*m")
ROOT = Path(__file__).resolve().parent.parent

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>One command, a spreadsheet and a report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{{--ink:#1b1a17;--soft:#56534c;--faint:#8a857c;--paper:#f6f3ed;--card:#fffdf9;--line:#e5dfd4;--down:#15605a}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:15px;line-height:1.55}}
.wrap{{max-width:1120px;margin:0 auto;padding:30px 40px 36px}}
h1{{font-family:"Fraunces",Georgia,serif;font-size:29px;line-height:1.1;letter-spacing:-.02em;margin:0 0 6px}}
.sub{{color:var(--soft);margin:0 0 22px;max-width:70ch}}
.badge{{background:#fbf0df;color:#9a5b12;border:1px solid #efd9b4;border-radius:999px;padding:5px 13px;font-size:12px;font-weight:600;float:right}}
.term{{background:#15171a;border-radius:12px;padding:16px 20px;box-shadow:0 14px 30px -20px rgba(0,0,0,.6);margin-bottom:20px}}
.dots{{display:flex;gap:6px;margin-bottom:11px}}
.dots i{{width:11px;height:11px;border-radius:50%;display:block}}
.dots i:nth-child(1){{background:#ff5f57}} .dots i:nth-child(2){{background:#febc2e}} .dots i:nth-child(3){{background:#28c840}}
pre{{margin:0;color:#dfe5e2;font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12.5px;line-height:1.62;white-space:pre-wrap}}
pre b{{color:#fff;font-weight:600}} pre .g{{color:#6ddbb0}} pre .d{{color:#8b938f}} pre .y{{color:#f0c674}}
h2{{font-family:"Fraunces",Georgia,serif;font-size:19px;margin:0 0 10px}}
table{{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}}
th,td{{text-align:left;padding:9px 14px;border-bottom:1px solid var(--line);font-size:13px}}
th{{font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;color:var(--faint);background:var(--paper)}}
tbody tr:last-child td{{border-bottom:0}}
td.r,th.r{{text-align:right;font-variant-numeric:tabular-nums}}
td.mono{{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--soft)}}
.cap{{color:var(--faint);font-size:12.5px;margin-top:9px}}
</style></head><body><div class="wrap">
<div class="badge">Sample project, public practice site</div>
<h1>One command, a spreadsheet and a report</h1>
<p class="sub">The watcher crawls the catalogue, writes every row to SQLite, exports a CSV, and compares the run against the previous one. Put it on a schedule and it only speaks up when something actually changed.</p>

<div class="term"><div class="dots"><i></i><i></i><i></i></div><pre>{terminal}</pre></div>

<h2>data/run-1.csv, first rows</h2>
<table>
<thead><tr><th>Title</th><th>Category</th><th class="r">Rating</th><th class="r">Price</th><th>In stock</th><th>Source URL</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<p class="cap">Full file holds every product found in the run, ready for Excel, Google Sheets or a database load.</p>
</div></body></html>"""


def colourise(text: str) -> str:
    out = []
    for line in html.escape(text).splitlines():
        if line.startswith("Catalogue watcher"):
            line = f"<b>$ python -m watcher.cli run</b>\n{line}"
        line = re.sub(r"(page \d+)", r'<span class="g">\1</span>', line)
        line = re.sub(r"^(  \d+ products)", r'<b>\1</b>', line)
        line = re.sub(r"(\d+ changes against run \d+, including \d+ price drops)", r'<span class="y">\1</span>', line)
        out.append(line)
    return "\n".join(out)


def main() -> None:
    raw = Path(sys.argv[1]).read_text(encoding="utf-8")
    terminal = colourise(ANSI.sub("", raw).strip())

    rows_html = []
    with (ROOT / "data" / "run-1.csv").open(encoding="utf-8") as handle:
        for i, row in enumerate(csv.DictReader(handle)):
            if i >= 7:
                break
            rows_html.append(
                "<tr><td>{title}</td><td>{category}</td><td class='r'>{rating} of 5</td>"
                "<td class='r'>{currency}{price}</td><td>{stock}</td><td class='mono'>{url}</td></tr>".format(
                    title=html.escape(row["title"]),
                    category=html.escape(row["category"]),
                    rating=row["rating"],
                    currency=row["currency"],
                    price=row["price"],
                    stock="yes" if row["in_stock"] == "yes" else "no",
                    url=html.escape(row["url"].replace("https://books.toscrape.com", "")),
                )
            )

    out = ROOT / "data" / "run-view.html"
    out.write_text(PAGE.format(terminal=terminal, rows="".join(rows_html)), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
