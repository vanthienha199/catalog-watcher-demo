"""Collect product rows from a catalogue.

Two engines are available. The http engine is fast and is the right choice for
server rendered pages. The browser engine drives headless Chromium through
Playwright and is the right choice when the prices only appear after JavaScript
runs. Both return the same row shape, so everything downstream is unchanged.
"""

from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
STOCK = re.compile(r"\((\d+)\s+available\)")
USER_AGENT = "catalog-watcher-demo/1.0 (portfolio sample)"


@dataclass
class Product:
    sku: str
    title: str
    price: float
    currency: str
    rating: int
    in_stock: bool
    stock_count: int
    category: str
    url: str

    def as_dict(self) -> dict:
        return asdict(self)


def _text(node) -> str:
    return node.get_text(strip=True) if node else ""


def parse_listing(html: str, page_url: str, category: str) -> list[Product]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[Product] = []
    for card in soup.select("article.product_pod"):
        link = card.select_one("h3 a")
        href = urljoin(page_url, link["href"]) if link else page_url
        raw_price = _text(card.select_one(".price_color"))
        amount = re.sub(r"[^\d.]", "", raw_price) or "0"
        availability = _text(card.select_one(".instock.availability"))
        rating_class = card.select_one("p.star-rating")
        rating_word = ""
        if rating_class:
            rating_word = next((c for c in rating_class.get("class", []) if c in RATINGS), "")
        rows.append(
            Product(
                sku=href.rstrip("/").split("/")[-2] if "/" in href else href,
                title=link["title"].strip() if link and link.has_attr("title") else _text(link),
                price=float(amount),
                currency=raw_price[:1] if raw_price else "",
                rating=RATINGS.get(rating_word, 0),
                in_stock="in stock" in availability.lower(),
                stock_count=0,
                category=category,
                url=href,
            )
        )
    return rows


def next_page(html: str, page_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    link = soup.select_one("li.next a")
    return urljoin(page_url, link["href"]) if link else None


def fetch_http(url: str, client: httpx.Client) -> str:
    response = client.get(url, timeout=20)
    response.raise_for_status()
    return response.text


def crawl(
    start_url: str,
    category: str = "Catalogue",
    max_pages: int = 3,
    delay: float = 0.5,
    engine: str = "http",
    on_page=None,
) -> list[Product]:
    """Walk the pagination from start_url and return every product found."""
    products: list[Product] = []
    if engine == "browser":
        return _crawl_browser(start_url, category, max_pages, delay, on_page)

    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(headers=headers, follow_redirects=True) as client:
        url: str | None = start_url
        page = 0
        while url and page < max_pages:
            html = fetch_http(url, client)
            found = parse_listing(html, url, category)
            products.extend(found)
            page += 1
            if on_page:
                on_page(page, url, len(found))
            url = next_page(html, url)
            if url:
                time.sleep(delay)
    return products


def _crawl_browser(start_url, category, max_pages, delay, on_page) -> list[Product]:
    from playwright.sync_api import sync_playwright  # imported lazily

    products: list[Product] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page_obj = browser.new_page(user_agent=USER_AGENT)
        url = start_url
        count = 0
        while url and count < max_pages:
            page_obj.goto(url, wait_until="networkidle", timeout=45000)
            html = page_obj.content()
            found = parse_listing(html, url, category)
            products.extend(found)
            count += 1
            if on_page:
                on_page(count, url, len(found))
            url = next_page(html, url)
            if url:
                time.sleep(delay)
        browser.close()
    return products
