#!/usr/bin/env bash
# Fetch the two Mystery pages of the public practice store into fixtures/original/.
# make_history.py builds 30 days of price history from these copies.
set -e
cd "$(dirname "$0")"
base="https://books.toscrape.com/catalogue/category/books/mystery_3"
mkdir -p original
curl -sS -A "catalog-watcher-demo/1.0 (portfolio sample)" "$base/index.html"  -o original/index.html
curl -sS -A "catalog-watcher-demo/1.0 (portfolio sample)" "$base/page-2.html" -o original/page-2.html
echo "Now run: python fixtures/make_history.py"
