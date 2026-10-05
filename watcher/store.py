"""SQLite storage, run to run change detection, and price history."""

from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    source TEXT NOT NULL,
    engine TEXT NOT NULL,
    products INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS observations (
    run_id INTEGER NOT NULL REFERENCES runs(id),
    sku TEXT NOT NULL,
    title TEXT NOT NULL,
    price REAL NOT NULL,
    currency TEXT NOT NULL,
    rating INTEGER NOT NULL,
    in_stock INTEGER NOT NULL,
    category TEXT NOT NULL,
    url TEXT NOT NULL,
    PRIMARY KEY (run_id, sku)
);
"""
EXTRA_RUN_COLUMNS = (("pages", "INTEGER"), ("seconds", "REAL"), ("source_label", "TEXT"),
                     ("status", "TEXT NOT NULL DEFAULT 'ok'"), ("error", "TEXT"))


@dataclass
class Change:
    kind: str           # price_drop, price_rise, back_in_stock, out_of_stock, new, removed
    sku: str
    title: str
    before: str
    after: str
    delta: float
    url: str
    old_price: float | None = None
    new_price: float | None = None

    @property
    def pct(self) -> float | None:
        if self.old_price:
            return (self.new_price - self.old_price) / self.old_price
        return None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(runs)")}
        for name, kind in EXTRA_RUN_COLUMNS:
            if name not in cols:
                self.conn.execute(f"ALTER TABLE runs ADD COLUMN {name} {kind}")
        self.conn.commit()

    def save_run(self, products: list[dict], source: str, engine: str, pages: int | None = None,
                 seconds: float | None = None, source_label: str | None = None,
                 started_at: str | None = None) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO runs (started_at, source, engine, products, pages, seconds, source_label, status)"
            " VALUES (?,?,?,?,?,?,?, 'ok')",
            (started_at or now_iso(), source, engine, len(products), pages, seconds, source_label),
        )
        run_id = cur.lastrowid
        cur.executemany(
            """INSERT OR REPLACE INTO observations
               (run_id, sku, title, price, currency, rating, in_stock, category, url)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            [(run_id, p["sku"], p["title"], p["price"], p["currency"], p["rating"],
              int(p["in_stock"]), p["category"], p["url"]) for p in products],
        )
        self.conn.commit()
        return run_id

    def save_failed_run(self, source: str, engine: str, error: str, seconds: float | None = None,
                        source_label: str | None = None, started_at: str | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO runs (started_at, source, engine, products, seconds, source_label, status, error)"
            " VALUES (?,?,?,0,?,?, 'failed', ?)",
            (started_at or now_iso(), source, engine, seconds, source_label, error),
        )
        self.conn.commit()
        return cur.lastrowid

    def runs(self, limit: int = 20) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def run(self, run_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()

    def previous_run_id(self, run_id: int) -> int | None:
        """The last successful run before this one; failed runs hold no prices."""
        row = self.conn.execute(
            "SELECT MAX(id) AS id FROM runs WHERE id < ? AND status = 'ok'", (run_id,)).fetchone()
        return row["id"] if row and row["id"] is not None else None

    def last_ok_run_id(self, upto: int | None = None) -> int | None:
        q = "SELECT MAX(id) AS id FROM runs WHERE status = 'ok'" + (" AND id <= ?" if upto else "")
        row = self.conn.execute(q, (upto,) if upto else ()).fetchone()
        return row["id"] if row and row["id"] is not None else None

    def observations(self, run_id: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM observations WHERE run_id = ? ORDER BY title", (run_id,)).fetchall()

    def price_history(self, upto_run: int, days: int = 30) -> dict[str, list[tuple[str, float]]]:
        """Price per SKU over the last `days` successful runs up to `upto_run`."""
        rows = self.conn.execute(
            """SELECT r.started_at, o.sku, o.price FROM observations o JOIN runs r ON r.id = o.run_id
               WHERE r.status = 'ok' AND r.id IN (SELECT id FROM runs WHERE status = 'ok' AND id <= ?
                                                  ORDER BY id DESC LIMIT ?)
               ORDER BY r.id""", (upto_run, days)).fetchall()
        out: dict[str, list[tuple[str, float]]] = {}
        for r in rows:
            out.setdefault(r["sku"], []).append((r["started_at"], r["price"]))
        return out

    def compare(self, previous_run: int, current_run: int) -> list[Change]:
        before = {r["sku"]: r for r in self.observations(previous_run)}
        after = {r["sku"]: r for r in self.observations(current_run)}
        changes: list[Change] = []
        for sku, row in after.items():
            old = before.get(sku)
            if old is None:
                changes.append(Change("new", sku, row["title"], "", f"{row['currency']}{row['price']:.2f}", 0.0,
                                      row["url"], None, row["price"]))
                continue
            if abs(old["price"] - row["price"]) >= 0.01:
                delta = round(row["price"] - old["price"], 2)
                kind = "price_drop" if delta < 0 else "price_rise"
                changes.append(Change(kind, sku, row["title"], f"{old['currency']}{old['price']:.2f}",
                                      f"{row['currency']}{row['price']:.2f}", delta, row["url"], old["price"], row["price"]))
            if old["in_stock"] != row["in_stock"]:
                kind = "back_in_stock" if row["in_stock"] else "out_of_stock"
                changes.append(Change(kind, sku, row["title"], "in stock" if old["in_stock"] else "out of stock",
                                      "in stock" if row["in_stock"] else "out of stock", 0.0, row["url"],
                                      old["price"], row["price"]))
        for sku, row in before.items():
            if sku not in after:
                changes.append(Change("removed", sku, row["title"], f"{row['currency']}{row['price']:.2f}", "", 0.0,
                                      row["url"], row["price"], None))
        order = {"price_drop": 0, "back_in_stock": 1, "price_rise": 2, "out_of_stock": 3, "new": 4, "removed": 5}
        changes.sort(key=lambda c: (order.get(c.kind, 9), c.pct if c.pct is not None else 0))
        return changes

    def export_csv(self, run_id: int, path: Path) -> Path:
        rows = self.observations(run_id)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["sku", "title", "price", "currency", "rating", "in_stock", "category", "url"])
            for r in rows:
                writer.writerow([r["sku"], r["title"], f"{r['price']:.2f}", r["currency"],
                                 r["rating"], "yes" if r["in_stock"] else "no", r["category"], r["url"]])
        return path
