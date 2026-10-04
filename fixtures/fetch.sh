#!/usr/bin/env bash
# Mirror two pages of the public practice catalogue so the change report has a
# second day to compare against. The practice site never changes its prices,
# so make_second_day.py edits a few of them in this local copy only.
set -e
cd "$(dirname "$0")"
base="https://books.toscrape.com/catalogue/category/books/mystery_3"
mkdir -p catalogue/category/books/mystery_3
curl -sS -A "catalog-watcher-demo/1.0 (portfolio sample)" "$base/index.html"  -o catalogue/category/books/mystery_3/index.html
curl -sS -A "catalog-watcher-demo/1.0 (portfolio sample)" "$base/page-2.html" -o catalogue/category/books/mystery_3/page-2.html
python3 make_second_day.py
echo "Serve it with: python3 -m http.server 8099"
