"""The morning alert: one short email, sent only when something changed.

Writes the email to data/alerts/ as HTML and plain text. If SMTP settings are
in the environment (WATCHER_SMTP_HOST, WATCHER_SMTP_PORT, WATCHER_SMTP_USER,
WATCHER_SMTP_PASSWORD, WATCHER_ALERT_TO, WATCHER_ALERT_FROM) it is also sent.
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from html import escape
from pathlib import Path

from .report import headline, when


def compose(changes, run, currency: str, report_name: str) -> tuple[str, str, str]:
    """Return (subject, text, html)."""
    subject = headline(changes).rstrip(".") + f" ({when(run['started_at'], '%a %-d %b')})"
    lines, rows = [], []
    for c in changes:
        if c.kind in ("price_drop", "price_rise"):
            pct = (c.pct or 0) * 100
            what = f"{c.before} to {c.after} ({pct:+.0f}%)"
        elif c.kind == "out_of_stock":
            what = "sold out"
        else:
            what = c.kind.replace("_", " ")
        lines.append(f"- {c.title}: {what}")
        color = "#C8102E" if c.kind == "price_drop" else "#1A1A1A"
        old = f'<s style="color:#5B574F">{escape(c.before)}</s> ' if c.kind in ("price_drop", "price_rise") else ""
        new = escape(c.after) if c.kind in ("price_drop", "price_rise") else escape(what.capitalize())
        rows.append(
            f'<tr><td style="padding:10px 0;border-bottom:1px solid #DCD5C8;font:16px Georgia,serif">{escape(c.title)}</td>'
            f'<td style="padding:10px 0 10px 16px;border-bottom:1px solid #DCD5C8;text-align:right;white-space:nowrap;font:15px Arial,sans-serif">'
            f'{old}<b style="color:{color}">{new}</b></td></tr>')
    text = "\n".join([headline(changes), "", *lines, "", f"Full report: {report_name}", "",
                      "Catalogue Watch checks the shelf every morning and only writes when something moves."])
    html = (
        '<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#F3EFE6"><div style="background:#F3EFE6;padding:28px 0"><table role="presentation" width="600" align="center" cellspacing="0" cellpadding="0" '
        'style="background:#FBF9F4;border-top:3px double #1A1A1A;padding:24px 28px;font-family:Arial,sans-serif;color:#1A1A1A">'
        '<tr><td colspan="2" style="font:600 28px Georgia,serif;padding-bottom:4px">Catalogue Watch</td></tr>'
        f'<tr><td colspan="2" style="color:#5B574F;padding-bottom:18px;font-size:15px">{escape(headline(changes))}</td></tr>'
        + "".join(rows) +
        f'<tr><td colspan="2" style="padding-top:18px;font-size:14px;color:#5B574F">Full report and 30-day price history: {escape(report_name)}</td></tr>'
        '</table></div></body></html>')
    return subject, text, html


def write_and_send(store, run_id: int, changes, out_dir: Path, report_path: Path) -> Path | None:
    if not changes:
        return None
    run = store.run(run_id)
    obs = store.observations(run_id)
    currency = obs[0]["currency"] if obs else "£"
    subject, text, html = compose(changes, run, currency, Path(report_path).name)
    folder = Path(out_dir) / "alerts"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"run-{run_id}.txt").write_text(f"Subject: {subject}\n\n{text}\n", encoding="utf-8")
    path = folder / f"run-{run_id}.html"
    path.write_text(html, encoding="utf-8")
    host = os.environ.get("WATCHER_SMTP_HOST")
    to = os.environ.get("WATCHER_ALERT_TO")
    if host and to:
        msg = EmailMessage()
        msg["Subject"], msg["To"] = subject, to
        msg["From"] = os.environ.get("WATCHER_ALERT_FROM", "catalogue-watch@localhost")
        msg.set_content(text)
        msg.add_alternative(html, subtype="html")
        with smtplib.SMTP(host, int(os.environ.get("WATCHER_SMTP_PORT", "587"))) as s:
            s.starttls()
            if os.environ.get("WATCHER_SMTP_USER"):
                s.login(os.environ["WATCHER_SMTP_USER"], os.environ.get("WATCHER_SMTP_PASSWORD", ""))
            s.send_message(msg)
    return path
