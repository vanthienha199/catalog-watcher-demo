from pathlib import Path

from watcher.scrape import next_page, parse_listing
from watcher.store import Store

LISTING = """
<section>
  <article class="product_pod">
    <p class="star-rating Four"></p>
    <h3><a href="../../../a-test-book_123/index.html" title="A Test Book">A Test Book</a></h3>
    <div class="product_price">
      <p class="price_color">&pound;19.99</p>
      <p class="instock availability"><i class="icon-ok"></i> In stock </p>
    </div>
  </article>
  <article class="product_pod">
    <p class="star-rating Two"></p>
    <h3><a href="../../../another-book_9/index.html" title="Another Book">Another Book</a></h3>
    <div class="product_price">
      <p class="price_color">&pound;5.00</p>
      <p class="availability"><i class="icon-remove"></i> Out of stock </p>
    </div>
  </article>
</section>
<li class="next"><a href="page-2.html">next</a></li>
"""

PAGE_URL = "https://example.test/catalogue/category/books/mystery_3/index.html"


def test_parse_listing_reads_every_field():
    rows = parse_listing(LISTING, PAGE_URL, "Mystery")
    assert len(rows) == 2
    first = rows[0]
    assert first.title == "A Test Book"
    assert first.price == 19.99
    assert first.currency == "£"
    assert first.rating == 4
    assert first.in_stock is True
    assert first.sku == "a-test-book_123"
    assert first.url == "https://example.test/catalogue/a-test-book_123/index.html"


def test_out_of_stock_is_detected():
    rows = parse_listing(LISTING, PAGE_URL, "Mystery")
    assert rows[1].in_stock is False


def test_next_page_is_resolved_against_the_current_page():
    assert next_page(LISTING, PAGE_URL).endswith("/mystery_3/page-2.html")


def test_no_next_page_returns_none():
    assert next_page("<html><body>nothing</body></html>", PAGE_URL) is None


def _row(sku, price, in_stock=True):
    return {
        "sku": sku, "title": f"Book {sku}", "price": price, "currency": "£",
        "rating": 3, "in_stock": in_stock, "category": "Mystery",
        "url": f"https://example.test/{sku}",
    }


def test_compare_finds_drops_rises_stock_and_new_products(tmp_path: Path):
    store = Store(tmp_path / "test.db")
    first = store.save_run([_row("a", 20.0), _row("b", 10.0), _row("c", 5.0, in_stock=True)], "unit", "http")
    second = store.save_run([_row("a", 15.0), _row("b", 12.5), _row("c", 5.0, in_stock=False), _row("d", 9.0)], "unit", "http")

    kinds = {c.kind: c for c in store.compare(first, second)}
    assert kinds["price_drop"].sku == "a"
    assert kinds["price_drop"].delta == -5.0
    assert kinds["price_rise"].sku == "b"
    assert kinds["out_of_stock"].sku == "c"
    assert kinds["new"].sku == "d"


def test_unchanged_run_reports_nothing(tmp_path: Path):
    store = Store(tmp_path / "test.db")
    rows = [_row("a", 20.0), _row("b", 10.0)]
    first = store.save_run(rows, "unit", "http")
    second = store.save_run(rows, "unit", "http")
    assert store.compare(first, second) == []


def test_csv_export_has_a_header_and_every_row(tmp_path: Path):
    store = Store(tmp_path / "test.db")
    run_id = store.save_run([_row("a", 20.0), _row("b", 10.0)], "unit", "http")
    path = store.export_csv(run_id, tmp_path / "out.csv")
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0].startswith("sku,title,price")
    assert len(lines) == 3



def _rows(prices, stock=None):
    stock = stock or [True] * len(prices)
    return [{"sku": f"book_{i}", "title": f"Book {i}", "price": p, "currency": "£", "rating": 3,
             "in_stock": stock[i], "category": "Mystery", "url": f"https://example.test/b{i}"}
            for i, p in enumerate(prices)]


def _report(store, run_id, tmp_path):
    from watcher.report import build
    return build(store, run_id, tmp_path / f"report-{run_id}.html").read_text()


def test_report_leads_with_the_biggest_drop_in_red_and_rises_in_ink(tmp_path):
    store = Store(tmp_path / "w.db")
    store.save_run(_rows([10.00, 20.00, 30.00, 40.00]), "https://example.test", "http", started_at="2026-09-01T07:00:00")
    run2 = store.save_run(_rows([9.50, 15.00, 33.00, 40.00]), "https://example.test", "http", started_at="2026-09-02T07:00:00")
    html = _report(store, run2, tmp_path)
    assert "Two prices fell and one rose since yesterday." in html
    lead = html.index('class="tile drop lead"')
    assert html.index("Book 1", lead) < html.index("Book 0", lead)   # -25% leads, -5% follows
    assert '<article class="tile rise">' in html
    assert "#C8102E" in html and html.count("var(--red)") >= 3
    assert "https://fonts" not in html   # no outside requests
    assert "uppercase" not in html


def test_report_quiet_day_is_an_empty_state(tmp_path):
    store = Store(tmp_path / "w.db")
    store.save_run(_rows([10.00, 20.00]), "https://example.test", "http", started_at="2026-09-01T07:00:00")
    run2 = store.save_run(_rows([10.00, 20.00]), "https://example.test", "http", started_at="2026-09-02T07:00:00")
    html = _report(store, run2, tmp_path)
    assert "Nothing moved since yesterday." in html
    assert 'class="grid"' not in html


def test_failed_run_is_recorded_skipped_for_compare_and_reported(tmp_path):
    store = Store(tmp_path / "w.db")
    good = store.save_run(_rows([10.00, 20.00]), "https://example.test", "http", started_at="2026-09-01T07:00:00")
    bad = store.save_failed_run("https://example.test", "http", "The site timed out after 3 tries.",
                                started_at="2026-09-02T07:00:00")
    after = store.save_run(_rows([8.00, 20.00]), "https://example.test", "http", started_at="2026-09-03T07:00:00")
    assert store.previous_run_id(after) == good
    assert [c.kind for c in store.compare(store.previous_run_id(after), after)] == ["price_drop"]
    html = _report(store, bad, tmp_path)
    assert "This morning&#39;s check failed." in html or "This morning's check failed." in html
    assert "timed out after 3 tries" in html and "Tue 1 Sep 2026" in html


def test_cli_records_a_failed_run_when_the_site_is_down(tmp_path):
    from watcher.cli import main
    code = main(["run", "--source", "http://127.0.0.1:9/nothing.html", "--db", str(tmp_path / "w.db"),
                 "--out-dir", str(tmp_path), "--retries", "1", "--retry-wait", "0", "--quiet"])
    assert code == 1
    row = Store(tmp_path / "w.db").runs()[0]
    assert row["status"] == "failed" and "2 tries" in row["error"]


def test_price_history_feeds_the_sparkline(tmp_path):
    store = Store(tmp_path / "w.db")
    for d, p in enumerate([10.00, 11.00, 10.50, 8.00], start=1):
        last = store.save_run(_rows([p]), "https://example.test", "http", started_at=f"2026-09-0{d}T07:00:00")
    assert [p for _, p in store.price_history(last)["book_0"]] == [10.00, 11.00, 10.50, 8.00]
    html = _report(store, last, tmp_path)
    assert '<svg class="spark"' in html and "Lowest price in 30 days." in html


def test_alert_is_written_only_when_something_changed(tmp_path):
    from watcher.alert import write_and_send
    store = Store(tmp_path / "w.db")
    a = store.save_run(_rows([10.00, 20.00]), "https://example.test", "http", started_at="2026-09-01T07:00:00")
    b = store.save_run(_rows([10.00, 20.00], [True, False]), "https://example.test", "http", started_at="2026-09-02T07:00:00")
    assert write_and_send(store, a, [], tmp_path, tmp_path / "r.html") is None
    path = write_and_send(store, b, store.compare(a, b), tmp_path, tmp_path / "r.html")
    text = (tmp_path / "alerts" / f"run-{b}.txt").read_text()
    assert path.exists() and "One book sold out since yesterday" in text and "Book 1: sold out" in text
