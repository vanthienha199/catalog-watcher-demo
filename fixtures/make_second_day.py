"""Create the 'next day' version of the mirrored catalogue.

The practice store never changes its prices, so the change report would always be
empty. This script edits a handful of prices and one availability line in the
local copy, which gives the comparison something real to find. Nothing here
touches the live site, and the edits are listed below so the demo stays honest.
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE1 = HERE / "catalogue/category/books/mystery_3/index.html"
PAGE2 = HERE / "catalogue/category/books/mystery_3/page-2.html"

PRICE_EDITS = [
    ("£47.82", "£39.99"),   # price drop
    ("£56.50", "£51.00"),   # price drop
    ("£19.63", "£24.95"),   # price rise
    ("£54.21", "£48.75"),   # price drop
]


def main() -> None:
    page1 = PAGE1.read_text(encoding="utf-8")
    for old, new in PRICE_EDITS:
        page1 = page1.replace(f'price_color">{old}', f'price_color">{new}', 1)

    # One product goes out of stock.
    page1 = page1.replace(
        '<i class="icon-ok"></i>\n    \n        In stock\n    \n</p>',
        '<i class="icon-remove"></i>\n    \n        Out of stock\n    \n</p>',
        1,
    )
    PAGE1.write_text(page1, encoding="utf-8")

    page2 = PAGE2.read_text(encoding="utf-8")
    first = re.search(r'price_color">£([0-9.]+)', page2)
    if first:
        old = f'price_color">£{first.group(1)}'
        lowered = f'price_color">£{float(first.group(1)) - 6.4:.2f}'
        page2 = page2.replace(old, lowered, 1)
    PAGE2.write_text(page2, encoding="utf-8")
    print("second day fixture written")


if __name__ == "__main__":
    main()
