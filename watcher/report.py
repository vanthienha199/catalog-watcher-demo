"""Render a standalone HTML report from a run and its comparison.

The report is a single file with no external requests: fonts are embedded,
and it ships a dark and a light theme with a toggle.
"""

from __future__ import annotations

import base64
import statistics
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from jinja2 import Template

FONTS = Path(__file__).parent / "assets" / "fonts"


@lru_cache(maxsize=1)
def font_css() -> str:
    faces = [("Bricolage", "bricolage-700", 700), ("Plex", "plex-400", 400), ("Plex", "plex-500", 500),
             ("Plex", "plex-600", 600), ("Mono", "mono-500", 500)]
    out = []
    for family, name, weight in faces:
        path = FONTS / f"{name}.woff2"
        if path.exists():
            data = base64.b64encode(path.read_bytes()).decode()
            out.append(f'@font-face{{font-family:"{family}";font-weight:{weight};'
                       f'src:url(data:font/woff2;base64,{data}) format("woff2")}}')
    return "\n".join(out)


TEMPLATE = Template(
    """<!doctype html>
<html lang="en" data-theme="{{ theme }}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}, run {{ run_id }}</title>
<style>
{{ fonts }}
:root{--canvas:#15171B;--surface:#1E2126;--raised:#262A30;--line:#2F333A;--ink:#F3EFE7;--muted:#A7A39B;--faint:#77736C;
--accent:#F2994A;--good:#7CBA8C;--bad:#E8806E;--good-bg:rgba(124,186,140,.14);--bad-bg:rgba(232,128,110,.14);--bar:#3A3F47;--r:10px}
[data-theme="light"]{--canvas:#F6F3EE;--surface:#FFFFFF;--raised:#F1EDE6;--line:#E4DED4;--ink:#1B1A17;--muted:#6E6A62;--faint:#9A958C;
--accent:#D9782A;--good:#3F8A55;--bad:#C2543F;--good-bg:#E6F1E8;--bad-bg:#F7E4DE;--bar:#D9D3C8}
*{box-sizing:border-box}
html,body{background:var(--canvas)}
body{margin:0;color:var(--ink);font-family:"Plex",system-ui,sans-serif;font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:40px 48px 56px}
.mono,.num,td.r,th.r{font-family:"Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}
header{display:flex;justify-content:space-between;align-items:flex-start;gap:24px;margin-bottom:32px}
.brand{display:flex;gap:16px;align-items:center}
.logo{width:44px;height:44px;border-radius:var(--r);background:var(--surface);border:1px solid var(--line);display:grid;place-items:center}
h1{font-family:"Bricolage","Plex",sans-serif;font-weight:700;font-size:34px;line-height:1.05;letter-spacing:-.02em;margin:0}
.run{font-family:"Mono",monospace;font-size:12px;color:var(--muted);margin-top:8px}
.run b{color:var(--accent);font-weight:500}
.right{display:flex;gap:8px;align-items:center}
.badge{font-family:"Mono",monospace;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);border:1px solid color-mix(in srgb,var(--accent) 45%,transparent);border-radius:999px;padding:4px 12px;white-space:nowrap}
.toggle{all:unset;cursor:pointer;font-size:12px;color:var(--muted);border:1px solid var(--line);border-radius:var(--r);padding:6px 12px;background:var(--surface)}
.toggle:hover{color:var(--ink)}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:32px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:20px 24px}
.kpi .label{font-family:"Mono",monospace;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--faint)}
.kpi .value{font-family:"Mono",monospace;font-size:30px;font-weight:500;line-height:1.2;margin-top:8px;letter-spacing:-.01em}
.kpi .delta{font-family:"Mono",monospace;font-size:12px;margin-top:6px;color:var(--muted)}
.kpi .delta .up{color:var(--bad)} .kpi .delta .down{color:var(--good)} .kpi .delta .flat{color:var(--faint)}
.kpi.hot{border-color:color-mix(in srgb,var(--accent) 55%,var(--line))}
.kpi.hot .value{color:var(--accent)}
h2{font-family:"Bricolage","Plex",sans-serif;font-weight:700;letter-spacing:-.01em;font-size:21px;margin:0}
.sec-head{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px}
.sec-head span{font-family:"Mono",monospace;font-size:12px;color:var(--faint)}
section{margin-bottom:32px}
.grid2{display:grid;grid-template-columns:1fr 1.25fr;gap:24px}
table{width:100%;border-collapse:separate;border-spacing:0;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);overflow:hidden}
th,td{text-align:left;padding:12px 16px;border-bottom:1px solid var(--line);font-size:14px}
th{font-family:"Mono",monospace;font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--faint);background:var(--raised)}
tbody tr:last-child td{border-bottom:0}
td.r,th.r{text-align:right;font-size:13.5px}
td.title{max-width:340px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chip{display:inline-block;border-radius:6px;padding:2px 9px;font-size:12px;font-weight:600;white-space:nowrap}
.chip.drop{background:var(--good-bg);color:var(--good)}
.chip.rise{background:var(--bad-bg);color:var(--bad)}
.chip.stock{background:var(--raised);color:var(--muted)}
.d-down{color:var(--good);font-weight:500} .d-up{color:var(--bad);font-weight:500}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:24px}
.bars{display:flex;flex-direction:column;gap:12px}
.bar{display:grid;grid-template-columns:96px 1fr 72px;align-items:center;gap:12px;font-size:13px;color:var(--muted)}
.bar .track{height:18px;border-radius:6px;overflow:hidden;background:var(--raised)}
.bar .fill{height:100%;background:var(--bar);border-radius:6px}
.bar.top .fill{background:var(--accent)} .bar.top{color:var(--ink)}
.bar .v{text-align:right;font-family:"Mono",monospace;font-variant-numeric:tabular-nums;color:var(--ink)}
.legend{font-family:"Mono",monospace;font-size:11px;color:var(--faint);margin-top:16px}
.stock-no{color:var(--bad)}
.empty{text-align:center;color:var(--muted);background:var(--surface);border:1px dashed var(--line);border-radius:var(--r);padding:32px 24px}
.empty b{display:block;color:var(--ink);font-size:16px;margin-bottom:4px}
footer{font-family:"Mono",monospace;color:var(--faint);font-size:12px;border-top:1px solid var(--line);padding-top:16px;display:flex;justify-content:space-between;gap:16px}
</style></head><body><div class="wrap">
<header>
  <div class="brand">
    <div class="logo"><svg width="22" height="22" viewBox="0 0 22 22" fill="none"><path d="M3 17l5-6 4 3 7-9" stroke="#F2994A" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="19" cy="5" r="2" fill="#F2994A"/></svg></div>
    <div>
      <h1>{{ title }}</h1>
      <div class="run">Run <b>{{ run_id }}</b> · {{ when }} · {{ engine }} engine · {{ pages }} pages in {{ '%.1f'|format(seconds) }}s</div>
    </div>
  </div>
  <div class="right"><button class="toggle" id="toggle">Light / dark</button><span class="badge">Sample project</span></div>
</header>

<div class="kpis">
  <div class="kpi"><div class="label">Products tracked</div><div class="value">{{ total }}</div>
    <div class="delta">{{ k_total|safe }}</div></div>
  <div class="kpi"><div class="label">Average price</div><div class="value">{{ currency }}{{ '%.2f'|format(avg) }}</div>
    <div class="delta">{{ k_avg|safe }}</div></div>
  <div class="kpi"><div class="label">In stock</div><div class="value">{{ '%.1f'|format(stock_pct) }}%</div>
    <div class="delta">{{ k_stock|safe }}</div></div>
  <div class="kpi{{ ' hot' if changes }}"><div class="label">Changes found</div><div class="value">{{ changes|length }}</div>
    <div class="delta">{% if prev_id %}{{ drops }} price {{ 'drop' if drops == 1 else 'drops' }} vs run {{ prev_id }}{% else %}first run, no baseline{% endif %}</div></div>
</div>

<section>
  <div class="sec-head"><h2>What changed since the last run</h2><span>{% if prev_id %}run {{ prev_id }} → run {{ run_id }}{% endif %}</span></div>
  {% if changes %}
  <table>
    <thead><tr><th>Change</th><th>Product</th><th class="r">Before</th><th class="r">After</th><th class="r">Difference</th></tr></thead>
    <tbody>
    {% for c in changes %}
      <tr>
        <td>{% if c.kind == 'price_drop' %}<span class="chip drop">Price drop</span>{% elif c.kind == 'price_rise' %}<span class="chip rise">Price rise</span>{% else %}<span class="chip stock">{{ c.kind.replace('_',' ')|capitalize }}</span>{% endif %}</td>
        <td class="title">{{ c.title }}</td>
        <td class="r">{{ c.before }}</td>
        <td class="r">{{ c.after }}</td>
        <td class="r">{% if c.delta %}<span class="{{ 'd-down' if c.delta < 0 else 'd-up' }}">{{ '%+.2f'|format(c.delta) }}</span>{% else %}<span class="flat">·</span>{% endif %}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}
  <div class="empty"><b>No changes since the last run</b>{% if prev_id %}Every price and stock status matches run {{ prev_id }}. On a normal day this is the result, and no alert is sent.{% else %}This is the first run, so there is nothing to compare against yet.{% endif %}</div>
  {% endif %}
</section>

<div class="grid2">
<section class="card">
  <div class="sec-head"><h2>Average price by rating</h2></div>
  <div class="bars">
  {% for b in buckets %}
    <div class="bar{{ ' top' if b.top }}"><div>{{ b.label }}</div><div class="track"><div class="fill" style="width: {{ b.pct }}%"></div></div><div class="v">{{ currency }}{{ '%.2f'|format(b.value) }}</div></div>
  {% endfor %}
  </div>
  <div class="legend">Highlighted: the rating with the most products ({{ top_count }})</div>
</section>

<section>
  <div class="sec-head"><h2>Cheapest right now</h2><span>{{ cheapest|length }} of {{ total }}</span></div>
  <table>
    <thead><tr><th>Product</th><th class="r">Rating</th><th class="r">Price</th><th>Stock</th></tr></thead>
    <tbody>
    {% for p in cheapest %}
      <tr><td class="title">{{ p.title }}</td><td class="r">{{ p.rating }}/5</td><td class="r">{{ currency }}{{ '%.2f'|format(p.price) }}</td>
      <td>{% if p.in_stock %}In stock{% else %}<span class="stock-no">Out of stock</span>{% endif %}</td></tr>
    {% endfor %}
    </tbody>
  </table>
</section>
</div>

<footer><span>Source: {{ source }}</span><span>Catalogue watcher, a sample project by Ha Le</span></footer>
</div>
<script>
(function(){
  var root=document.documentElement, key="watcher-theme";
  try{var saved=localStorage.getItem(key); if(saved) root.dataset.theme=saved;}catch(e){}
  document.getElementById("toggle").onclick=function(){
    root.dataset.theme = root.dataset.theme==="light" ? "dark" : "light";
    try{localStorage.setItem(key, root.dataset.theme);}catch(e){}
  };
})();
</script>
</body></html>"""
)


def _delta(cur: float, prev: float | None, fmt: str, good_when_down: bool = True, unit: str = "") -> str:
    if prev is None:
        return "no previous run"
    diff = cur - prev
    if abs(diff) < 1e-9:
        return '<span class="flat">no change</span> vs last run'
    cls = ("down" if diff < 0 else "up") if good_when_down else ("down" if diff > 0 else "up")
    return f'<span class="{cls}">{format(diff, fmt)}{unit}</span> vs last run'


def _money_delta(cur: float, prev: float | None, currency: str) -> str:
    if prev is None:
        return "no previous run"
    diff = round(cur - prev, 2)
    if abs(diff) < 0.005:
        return '<span class="flat">no change</span> vs last run'
    sign = "-" if diff < 0 else "+"
    cls = "down" if diff < 0 else "up"
    return f'<span class="{cls}">{sign}{currency}{abs(diff):.2f}</span> vs last run'


def _stats(rows):
    prices = [r["price"] for r in rows] or [0.0]
    stock = sum(1 for r in rows if r["in_stock"])
    return {"n": len(rows), "avg": sum(prices) / len(prices),
            "stock_pct": (stock / len(rows) * 100) if rows else 0.0}


def build(run_rows, changes, meta: dict, out_path: Path, previous_rows=None) -> Path:
    products = [dict(r) for r in run_rows]
    prices = [p["price"] for p in products] or [0]
    cur = _stats(products)
    prev = _stats([dict(r) for r in previous_rows]) if previous_rows else None
    currency = products[0]["currency"] if products else ""

    buckets = []
    for rating in (5, 4, 3, 2, 1):
        group = [p["price"] for p in products if p["rating"] == rating]
        if group:
            buckets.append({"label": f"{rating} star · {len(group)}", "value": sum(group) / len(group), "n": len(group)})
    top_value = max((b["value"] for b in buckets), default=0)
    top_n = max((b["n"] for b in buckets), default=0)
    for b in buckets:
        b["pct"] = round(b["value"] / top_value * 100) if top_value else 0
        b["top"] = b["n"] == top_n

    started = meta.get("started_at")
    when = (datetime.fromisoformat(started).astimezone().strftime("%d %b %Y, %H:%M")
            if started else datetime.now().strftime("%d %b %Y, %H:%M"))

    html = TEMPLATE.render(
        fonts=font_css(),
        theme=meta.get("theme", "dark"),
        title=meta.get("title", "Catalogue watch"),
        run_id=meta.get("run_id", "?"),
        prev_id=meta.get("previous_run_id"),
        when=when,
        total=cur["n"],
        pages=meta.get("pages") or 0,
        seconds=meta.get("seconds") or 0.0,
        engine=meta.get("engine", "http"),
        currency=currency,
        avg=cur["avg"],
        median=statistics.median(prices),
        stock_pct=cur["stock_pct"],
        k_total=_delta(cur["n"], prev["n"] if prev else None, "+d", good_when_down=False),
        k_avg=_money_delta(cur["avg"], prev["avg"] if prev else None, currency),
        k_stock=_delta(cur["stock_pct"], prev["stock_pct"] if prev else None, "+.1f", good_when_down=False, unit=" pts"),
        drops=sum(1 for c in changes if c.kind == "price_drop"),
        changes=changes,
        buckets=buckets,
        top_count=top_n,
        cheapest=sorted(products, key=lambda p: p["price"])[:7],
        source=meta.get("source_label") or meta.get("source", ""),
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path
