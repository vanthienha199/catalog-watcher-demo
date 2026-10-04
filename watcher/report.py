"""Render a standalone HTML report from a run and its comparison."""

from __future__ import annotations

import statistics
from datetime import datetime
from pathlib import Path

from jinja2 import Template

TEMPLATE = Template(
    """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{--ink:#1b1a17;--soft:#56534c;--faint:#8a857c;--paper:#f6f3ed;--card:#fffdf9;--line:#e5dfd4;--accent:#9a3412;--up:#9a3412;--down:#15605a;--chip:#f0ece3}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:15px;line-height:1.55}
.wrap{max-width:1120px;margin:0 auto;padding:34px 40px 50px}
header{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;flex-wrap:wrap;margin-bottom:26px}
h1{font-family:"Fraunces",Georgia,serif;font-size:31px;line-height:1.1;letter-spacing:-.02em;margin:0 0 6px}
.sub{color:var(--soft);margin:0;max-width:60ch}
.badge{background:#fbf0df;color:#9a5b12;border:1px solid #efd9b4;border-radius:999px;padding:5px 13px;font-size:12px;font-weight:600;white-space:nowrap}
.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:26px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:15px 17px}
.kpi .label{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--faint);font-weight:600}
.kpi .value{font-family:"Fraunces",Georgia,serif;font-size:25px;line-height:1.2;margin-top:4px}
.kpi .note{font-size:12px;color:var(--faint)}
h2{font-family:"Fraunces",Georgia,serif;font-size:20px;margin:0 0 12px}
section{margin-bottom:28px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
th,td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--line);font-size:13.5px}
th{font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;color:var(--faint);background:var(--paper)}
tbody tr:last-child td{border-bottom:0}
td.r,th.r{text-align:right;font-variant-numeric:tabular-nums}
.chip{display:inline-block;border-radius:5px;padding:2px 8px;font-size:11.5px;font-weight:600}
.chip.drop{background:#dff0ee;color:var(--down)}
.chip.rise{background:#f7e4dc;color:var(--up)}
.chip.stock{background:var(--chip);color:var(--soft)}
.delta.down{color:var(--down);font-weight:600}
.delta.up{color:var(--up);font-weight:600}
.bars{display:flex;flex-direction:column;gap:7px}
.bar{display:grid;grid-template-columns:150px 1fr 52px;align-items:center;gap:12px;font-size:13px}
.bar .track{background:var(--chip);border-radius:5px;height:17px;overflow:hidden}
.bar .fill{height:100%;background:var(--down);border-radius:5px}
footer{color:var(--faint);font-size:12.5px;border-top:1px solid var(--line);padding-top:14px}
.empty{color:var(--faint);font-size:13.5px;background:var(--card);border:1px dashed var(--line);border-radius:12px;padding:16px}
</style></head><body><div class="wrap">
<header>
  <div>
    <h1>{{ title }}</h1>
    <p class="sub">{{ subtitle }}</p>
  </div>
  <div class="badge">Sample project, public practice site</div>
</header>

<div class="kpis">
  <div class="kpi"><div class="label">Products</div><div class="value">{{ total }}</div><div class="note">{{ pages }} pages crawled</div></div>
  <div class="kpi"><div class="label">Average price</div><div class="value">{{ currency }}{{ '%.2f'|format(avg) }}</div><div class="note">median {{ currency }}{{ '%.2f'|format(median) }}</div></div>
  <div class="kpi"><div class="label">In stock</div><div class="value">{{ in_stock }}</div><div class="note">{{ '%.0f'|format(stock_pct) }} percent of catalogue</div></div>
  <div class="kpi"><div class="label">Price drops</div><div class="value">{{ drops }}</div><div class="note">since the previous run</div></div>
  <div class="kpi"><div class="label">Crawl time</div><div class="value">{{ '%.1f'|format(seconds) }}s</div><div class="note">{{ engine }} engine</div></div>
</div>

<section>
  <h2>Changes since the previous run</h2>
  {% if changes %}
  <table>
    <thead><tr><th>Change</th><th>Product</th><th>Before</th><th>After</th><th class="r">Difference</th></tr></thead>
    <tbody>
    {% for c in changes %}
      <tr>
        <td>
          {% if c.kind == 'price_drop' %}<span class="chip drop">price drop</span>
          {% elif c.kind == 'price_rise' %}<span class="chip rise">price rise</span>
          {% else %}<span class="chip stock">{{ c.kind.replace('_',' ') }}</span>{% endif %}
        </td>
        <td>{{ c.title }}</td>
        <td>{{ c.before }}</td>
        <td>{{ c.after }}</td>
        <td class="r"><span class="delta {{ 'down' if c.delta < 0 else 'up' }}">{% if c.delta %}{{ '%+.2f'|format(c.delta) }}{% else %}&middot;{% endif %}</span></td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}
  <div class="empty">Nothing changed since the previous run. This is the normal result on most days, and it is why the watcher only sends an alert when this table is not empty.</div>
  {% endif %}
</section>

<section>
  <h2>Price spread by rating</h2>
  <div class="bars">
  {% for b in buckets %}
    <div class="bar">
      <div>{{ b.label }}</div>
      <div class="track"><div class="fill" style="width: {{ b.pct }}%"></div></div>
      <div class="r">{{ currency }}{{ '%.2f'|format(b.value) }}</div>
    </div>
  {% endfor %}
  </div>
</section>

<section>
  <h2>Cheapest products in this run</h2>
  <table>
    <thead><tr><th>Product</th><th>Category</th><th class="r">Rating</th><th class="r">Price</th><th>Availability</th></tr></thead>
    <tbody>
    {% for p in cheapest %}
      <tr>
        <td>{{ p.title }}</td>
        <td>{{ p.category }}</td>
        <td class="r">{{ p.rating }} of 5</td>
        <td class="r">{{ currency }}{{ '%.2f'|format(p.price) }}</td>
        <td>{{ 'In stock' if p.in_stock else 'Out of stock' }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</section>

<footer>Generated {{ generated }} from {{ source }}. Built by Ha Le as a portfolio sample, using a public site published for scraping practice.</footer>
</div></body></html>"""
)


def build(run_rows, changes, meta: dict, out_path: Path) -> Path:
    products = [dict(r) for r in run_rows]
    prices = [p["price"] for p in products] or [0]
    in_stock = sum(1 for p in products if p["in_stock"])

    buckets = []
    top = 0.0
    for rating in (5, 4, 3, 2, 1):
        group = [p["price"] for p in products if p["rating"] == rating]
        if not group:
            continue
        value = sum(group) / len(group)
        top = max(top, value)
        buckets.append({"label": f"{rating} star ({len(group)})", "value": value, "pct": 0})
    for b in buckets:
        b["pct"] = round(b["value"] / top * 100) if top else 0

    html = TEMPLATE.render(
        title=meta.get("title", "Catalogue watch report"),
        subtitle=meta.get("subtitle", ""),
        total=len(products),
        pages=meta.get("pages", 0),
        currency=products[0]["currency"] if products else "",
        avg=sum(prices) / len(prices),
        median=statistics.median(prices),
        in_stock=in_stock,
        stock_pct=(in_stock / len(products) * 100) if products else 0,
        drops=sum(1 for c in changes if c.kind == "price_drop"),
        seconds=meta.get("seconds", 0.0),
        engine=meta.get("engine", "http"),
        changes=changes,
        buckets=buckets,
        cheapest=sorted(products, key=lambda p: p["price"])[:8],
        generated=datetime.now().strftime("%d %B %Y at %H:%M"),
        source=meta.get("source", ""),
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path
