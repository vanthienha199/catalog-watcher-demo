"""Render the morning report as one standalone HTML page, laid out like a
mail-order catalog: what changed is the hero, the biggest markdown gets the
biggest tile, and the rest of the shelf follows as a price list.

The page has no outside requests: fonts are embedded and the sparklines are
inline SVG. Red is used for price drops and nothing else.
"""

from __future__ import annotations

import base64
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from jinja2 import Template

FONTS = Path(__file__).parent / "assets" / "fonts"


@lru_cache(maxsize=1)
def font_css() -> str:
    faces = [("Bodoni", "bodoni-600", 600), ("Karla", "karla-400", 400), ("Karla", "karla-500", 500), ("Karla", "karla-700", 700)]
    out = []
    for family, name, weight in faces:
        path = FONTS / f"{name}.woff2"
        if path.exists():
            data = base64.b64encode(path.read_bytes()).decode()
            out.append(f'@font-face{{font-family:"{family}";font-weight:{weight};font-display:block;'
                       f'src:url(data:font/woff2;base64,{data}) format("woff2")}}')
    return "\n".join(out)


def when(iso: str, fmt: str = "%a %-d %b %Y") -> str:
    return datetime.fromisoformat(iso).strftime(fmt)


def sparkline(points: list[float], width: int = 132, height: int = 34, drop: bool = False) -> str:
    """30-day price line as inline SVG. The last point is marked."""
    if len(points) < 2:
        return ""
    lo, hi = min(points), max(points)
    span = (hi - lo) or 1.0
    step = width / (len(points) - 1)
    xy = [(i * step, height - 4 - (p - lo) / span * (height - 8)) for i, p in enumerate(points)]
    path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f} {y:.1f}" for i, (x, y) in enumerate(xy))
    lx, ly = xy[-1]
    dot = "var(--red)" if drop else "var(--ink)"
    return (f'<svg class="spark" viewBox="0 0 {width} {height}" width="{width}" height="{height}" aria-hidden="true">'
            f'<path d="{path}" fill="none" stroke="var(--rule)" stroke-width="1.4" stroke-linejoin="round"/>'
            f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="2.6" fill="{dot}"/></svg>')


TEMPLATE = Template(
    """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Catalogue Watch, {{ issue_date }}</title>
<style>
{{ fonts }}
:root{--paper:#F3EFE6;--sheet:#FBF9F4;--ink:#1A1A1A;--soft:#5B574F;--faint:#8A857B;--rule:#9C978D;--hair:#DCD5C8;--red:#C8102E}
*{box-sizing:border-box}
html,body{background:var(--paper)}
body{margin:0;color:var(--ink);font-family:"Karla",system-ui,sans-serif;font-size:16px;line-height:1.5;font-variant-numeric:tabular-nums lining-nums;-webkit-font-smoothing:antialiased}
.sheet{max-width:1160px;margin:0 auto;padding:44px 56px 40px}
.mast{display:grid;grid-template-columns:1fr auto;align-items:end;gap:24px;border-bottom:3px double var(--ink);padding-bottom:16px}
h1{font-family:"Bodoni",Didot,serif;font-weight:600;font-size:64px;line-height:.95;letter-spacing:-.01em;margin:0}
.shelf{color:var(--soft);margin-top:10px;font-size:16px}
.issue{text-align:right;font-size:15px;color:var(--soft)}
.issue b{display:block;color:var(--ink);font-weight:700;font-size:17px}
.lede{font-family:"Bodoni",Didot,serif;font-weight:600;font-size:30px;line-height:1.2;margin:28px 0 24px;max-width:28ch}
.alert{background:var(--sheet);border:1px solid var(--ink);padding:18px 22px;margin:28px 0 8px}
.alert b{display:block;font-size:18px;margin-bottom:2px}
.alert p{margin:0;color:var(--soft)}
.grid{display:grid;grid-template-columns:repeat(4,1fr);grid-auto-rows:minmax(190px,auto);gap:0;border-top:1px solid var(--ink);border-left:1px solid var(--hair)}
.tile{background:var(--sheet);border-right:1px solid var(--hair);border-bottom:1px solid var(--hair);padding:18px 18px 16px;display:flex;flex-direction:column;gap:6px;min-width:0}
.tile.lead{grid-column:span 2;grid-row:span 2;padding:26px 28px 24px}
.sku{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:12px;color:var(--faint)}
.tile h3{font-family:"Bodoni",Didot,serif;font-weight:600;font-size:19px;line-height:1.15;margin:0;overflow-wrap:anywhere}
.tile.lead h3{font-size:44px;line-height:1.05;max-width:16ch}
.save{margin:10px 0 0;font-size:18px;line-height:1.45;color:var(--soft);max-width:30ch}
.was{position:relative;display:inline-block;align-self:flex-start;color:var(--soft);font-size:15px;margin-top:auto}
.drop .was::after{content:"";position:absolute;left:-2px;right:-2px;top:52%;height:2px;background:var(--red);transform:scaleX(0);transform-origin:left;animation:strike .22s cubic-bezier(.2,.8,.2,1) .25s forwards}
.now{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.price{font-family:"Bodoni",Didot,serif;font-weight:600;font-size:34px;line-height:1}
.tile.lead .price{font-size:72px}
.drop .price{color:var(--red)}
.pct{font-weight:700;font-size:15px}
.drop .pct{color:var(--red)}
.tile.lead .pct{font-size:20px}
.spark{opacity:0;animation:fade .25s ease-out .5s forwards;margin-top:6px}
.tile.lead .spark{width:100%;height:auto;max-width:420px}
.spark-cap{font-size:12px;color:var(--faint)}
.sold .price{text-decoration:none}
.tag{font-size:13px;font-weight:700;border:1px solid var(--ink);padding:1px 7px;align-self:flex-start}
@keyframes strike{to{transform:scaleX(1)}}
@keyframes fade{to{opacity:1}}
@media (prefers-reduced-motion:reduce){.drop .was::after{animation:none;transform:none}.spark{animation:none;opacity:1}}
.quiet{background:var(--sheet);border-top:1px solid var(--ink);border-bottom:1px solid var(--hair);padding:30px 28px;margin-bottom:8px}
.quiet b{font-family:"Bodoni",Didot,serif;font-weight:600;font-size:26px;display:block;margin-bottom:6px}
.quiet p{margin:0;color:var(--soft);max-width:60ch}
h2{font-family:"Bodoni",Didot,serif;font-weight:600;font-size:26px;margin:40px 0 4px}
.h2note{color:var(--soft);margin:0 0 14px;font-size:15px}
.list{columns:2;column-gap:48px;border-top:1px solid var(--ink);padding-top:10px}
.item{break-inside:avoid;display:flex;align-items:baseline;gap:8px;padding:5px 0;font-size:15px}
.item .t{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:70%}
.item .dots{flex:1;border-bottom:1px dotted var(--rule);transform:translateY(-4px)}
.item .p{font-weight:500}
.item.out .p{color:var(--faint)}
.runs{width:100%;border-collapse:collapse;font-size:15px;border-top:1px solid var(--ink)}
.runs th{text-align:left;font-weight:500;color:var(--soft);padding:10px 12px 8px;border-bottom:1px solid var(--hair)}
.runs td{padding:9px 12px;border-bottom:1px solid var(--hair)}
.runs .r{text-align:right}
.runs tr.failed td{background:var(--sheet)}
.runs tr.failed .st{font-weight:700}
.runs tr.this td{font-weight:700}
footer{margin-top:40px;padding-top:14px;border-top:1px solid var(--hair);color:var(--faint);font-size:14px}
@media (max-width:820px){.sheet{padding:28px 18px}h1{font-size:44px}.grid{grid-template-columns:1fr 1fr}.tile.lead{grid-column:span 2;grid-row:span 1}.tile.lead .price{font-size:52px}.list{columns:1}.mast{grid-template-columns:1fr}.issue{text-align:left}}
</style></head><body><main class="sheet">
<header class="mast">
  <div><h1>Catalogue Watch</h1><div class="shelf">{{ shelf }}, checked every morning.</div></div>
  <div class="issue"><b>{{ issue_date }}</b>Run {{ run_id }}{% if seconds %}, {{ '%.1f'|format(seconds) }} seconds{% endif %}</div>
</header>

{% if failed %}
<div class="alert" role="alert">
  <b>This morning's check failed.</b>
  <p>{{ error }} Nothing was overwritten: the prices below are from {{ shown_date }}, the last good run, and the next run tries again as usual.</p>
</div>
{% elif tiles %}
<p class="lede">{{ headline }}</p>
{% endif %}

{% if tiles %}
<section class="grid" aria-label="Changed since the last run">
{% for t in tiles %}
  <article class="tile {{ t.cls }}{% if loop.first and t.cls == 'drop' %} lead{% endif %}">
    <span class="sku">SKU {{ t.sku }}</span>
    <h3>{{ t.title }}</h3>
    {% if loop.first and t.cls == 'drop' and t.save %}<p class="save">{{ t.save }}</p>{% endif %}
    {% if t.kind == 'out_of_stock' %}
      <span class="tag">Sold out</span>
      <div class="now"><span class="price">{{ t.new }}</span></div>
    {% elif t.kind in ('price_drop', 'price_rise') %}
      <span class="was">was {{ t.old }}</span>
      <div class="now"><span class="price">{{ t.new }}</span><span class="pct">{{ t.pct_text }}</span></div>
    {% else %}
      <div class="now"><span class="price">{{ t.new or t.old }}</span><span class="pct">{{ t.kind_text }}</span></div>
    {% endif %}
    {{ t.spark|safe }}
    {% if t.spark %}<span class="spark-cap">{{ t.note }}</span>{% endif %}
  </article>
{% endfor %}
</section>
{% elif not failed %}
<section class="quiet">
  <b>Nothing moved since yesterday.</b>
  <p>{{ total }} books checked. Every price and stock line matched the run on {{ prev_date }}, so no alert went out this morning.</p>
</section>
{% endif %}

<h2>{{ 'The shelf at the last good run' if failed else 'The rest of the shelf' }}</h2>
<p class="h2note">{{ shelf_note }}</p>
<section class="list">
{% for p in rest %}
  <div class="item{% if not p.in_stock %} out{% endif %}"><span class="t">{{ p.title }}</span><span class="dots"></span><span class="p">{% if p.in_stock %}{{ currency }}{{ '%.2f'|format(p.price) }}{% else %}Sold out{% endif %}</span></div>
{% endfor %}
</section>

<h2>Recent runs</h2>
<p class="h2note">Every run is kept, so a price can be traced back day by day.</p>
<table class="runs">
  <thead><tr><th>Date</th><th class="r">Books</th><th class="r">Changes</th><th class="r">Time</th><th>Status</th></tr></thead>
  <tbody>
  {% for r in runs %}
    <tr class="{{ 'failed' if r.failed }}{{ ' this' if r.this }}"><td>{{ r.date }}</td><td class="r">{{ r.books }}</td><td class="r">{{ r.changes }}</td><td class="r">{{ r.time }}</td><td class="st">{{ r.status }}</td></tr>
  {% endfor %}
  </tbody>
</table>

<footer>{{ footer }}</footer>
</main></body></html>"""
)

KIND_TEXT = {"back_in_stock": "Back in stock", "new": "New on the shelf", "removed": "Gone from the shelf"}


def money(cur: str, v: float | None) -> str:
    return "" if v is None else f"{cur}{v:.2f}"


def headline(changes) -> str:
    drops = sum(1 for c in changes if c.kind == "price_drop")
    rises = sum(1 for c in changes if c.kind == "price_rise")
    sold = sum(1 for c in changes if c.kind == "out_of_stock")
    other = len(changes) - drops - rises - sold
    words = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight", 9: "Nine"}
    parts = []
    if drops:
        parts.append(f"{words.get(drops, drops)} {'price' if drops == 1 else 'prices'} fell")
    if rises:
        parts.append(f"{'one' if rises == 1 else words.get(rises, rises).lower()} rose")
    if sold:
        parts.append(f"{'one book' if sold == 1 else str(sold) + ' books'} sold out")
    if other:
        parts.append(f"{other} other {'change' if other == 1 else 'changes'}")
    if not parts:
        return "Nothing moved since yesterday."
    text = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    text = text[0].upper() + text[1:]
    return text + " since yesterday."


def build(store, run_id: int, out_path: Path, footer: str | None = None) -> Path:
    run = store.run(run_id)
    failed = run["status"] == "failed"
    shown_id = store.last_ok_run_id(run_id) if failed else run_id
    shown = store.run(shown_id) if shown_id else None
    products = [dict(r) for r in store.observations(shown_id)] if shown_id else []
    currency = products[0]["currency"] if products else "£"
    prev_id = store.previous_run_id(run_id) if not failed else None
    changes = store.compare(prev_id, run_id) if prev_id else []
    history = store.price_history(shown_id, days=30) if shown_id else {}

    def pct_text(c):
        p = c.pct or 0
        arrow = "↓" if p < 0 else "↑"
        return f"{arrow} {abs(p) * 100:.0f}%"

    tiles = []
    drops = sorted([c for c in changes if c.kind == "price_drop"], key=lambda c: c.pct)
    others = [c for c in changes if c.kind != "price_drop"]
    for c in drops + others:
        series = [p for _, p in history.get(c.sku, [])]
        tiles.append({
            "sku": c.sku.rsplit("_", 1)[-1].zfill(4), "title": c.title, "kind": c.kind,
            "cls": "drop" if c.kind == "price_drop" else ("sold" if c.kind == "out_of_stock" else "rise" if c.kind == "price_rise" else "other"),
            "old": money(currency, c.old_price), "new": money(currency, c.new_price),
            "pct_text": pct_text(c) if c.kind in ("price_drop", "price_rise") else "",
            "kind_text": KIND_TEXT.get(c.kind, ""),
            "spark": sparkline(series, drop=c.kind == "price_drop") if c.kind in ("price_drop", "price_rise") else "",
            "days": len(series),
            "save": ((f"{money(currency, c.old_price - c.new_price)} off since yesterday."
                      + (f" None of the last {len(series) - 1} checks found it lower." if len(series) > 1 and c.new_price < min(series[:-1]) else ""))
                     if c.kind == "price_drop" else ""),
            "note": (("Lowest price in 30 days. " if c.kind == "price_drop" and series and c.new_price <= min(series) else "")
                     + f"{len(series)} checks since {when(history[c.sku][0][0], '%-d %b')}") if series else "",
        })
    changed = {c.sku for c in changes}
    rest = [p for p in products if p["sku"] not in changed]

    runs = []
    for r in store.runs(limit=14):
        ok = r["status"] == "ok"
        pid = store.previous_run_id(r["id"]) if ok else None
        n = len(store.compare(pid, r["id"])) if pid else 0
        runs.append({
            "date": when(r["started_at"], "%a %-d %b, %-I:%M %p").replace("AM", "am").replace("PM", "pm"),
            "books": r["products"] if ok else "",
            "changes": (n if pid else "First run") if ok else "",
            "time": f"{r['seconds']:.1f} s" if r["seconds"] is not None else "",
            "status": "Done" if ok else f"Failed. {r['error']}",
            "failed": not ok, "this": r["id"] == run_id,
        })

    label = run["source_label"] or run["source"]
    html = TEMPLATE.render(
        fonts=font_css(), run_id=run_id, issue_date=when(run["started_at"]), seconds=run["seconds"],
        shelf=label,
        failed=failed, error=(run["error"] or "").rstrip(".") + "." if failed else "",
        shown_date=when(shown["started_at"]) if shown else "",
        headline=headline(changes), tiles=tiles, total=len(products),
        prev_date=when(store.run(prev_id)["started_at"]) if prev_id else "",
        rest=rest, currency=currency,
        shelf_note=f"{len(rest)} books with no change today, A to Z." if not failed else f"{len(rest)} books, as of {when(shown['started_at']) if shown else ''}.",
        runs=runs,
        footer=footer or "Practice store data from books.toscrape.com, with price moves simulated on a local copy.",
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path
