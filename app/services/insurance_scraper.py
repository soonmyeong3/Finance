"""Scrapes real insurance product listings into InsuranceProduct rows.

IMPORTANT: the CSS selectors below are placeholders, not verified against a
live page. Before running this against a real target (e.g. an insurer's
direct-product page or a comparison site like 보험다모아), inspect the
current page's actual HTML and update SourceConfig accordingly. Always check
the target site's robots.txt / terms of use first — some comparison sites
disallow scraping and expect API partnership instead.
"""

from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup


@dataclass
class SourceConfig:
    name: str
    list_url: str
    category: str
    row_selector: str
    field_selectors: dict[str, str] = field(default_factory=dict)
    # field_selectors keys should match InsuranceProduct's synced fields:
    # name, insurer, product_version, sale_status


def fetch_products(config: SourceConfig, *, timeout: float = 10.0) -> list[dict]:
    response = httpx.get(config.list_url, timeout=timeout, headers={"User-Agent": "bobi-poc-bot/0.1"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    products = []
    for row in soup.select(config.row_selector):
        product = {"category": config.category, "source_url": config.list_url}
        for field_name, selector in config.field_selectors.items():
            node = row.select_one(selector)
            product[field_name] = node.get_text(strip=True) if node else ""
        products.append(product)
    return products


# Fill these in once you've inspected the real target pages.
SOURCE_CONFIGS: list[SourceConfig] = [
    # SourceConfig(
    #     name="pet_insurance_example",
    #     list_url="https://example-insurer.com/products/pet",
    #     category="펫보험",
    #     row_selector=".product-list .product-card",
    #     field_selectors={
    #         "name": ".product-name",
    #         "insurer": ".insurer-name",
    #         "product_version": ".version",
    #     },
    # ),
]
