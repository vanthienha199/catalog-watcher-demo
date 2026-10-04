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
