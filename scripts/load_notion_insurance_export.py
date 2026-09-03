"""Loads data/notion_export/*.json (a snapshot pulled from Notion's
보험상품/표준보장/상품-보장매핑 data sources) into Postgres.

Notion stays the source of truth. To refresh: re-export the three
data sources to data/notion_export/*.json, then re-run this script —
it's idempotent (upserts by natural key).

Usage: python scripts/load_notion_insurance_export.py
"""

import json
from pathlib import Path

from app.core.db import SessionLocal
from app.models.insurance import InsuranceProduct, ProductCoverageMapping, StandardCoverage

EXPORT_DIR = Path(__file__).resolve().parent.parent / "data" / "notion_export"


def load_products(db) -> dict[tuple[str, str, str | None], InsuranceProduct]:
    rows = json.loads((EXPORT_DIR / "products.json").read_text(encoding="utf-8"))
    by_key: dict[tuple[str, str, str | None], InsuranceProduct] = {}

    for row in rows:
        product = (
            db.query(InsuranceProduct)
            .filter(InsuranceProduct.notion_product_id == row["product_id"])
            .one_or_none()
        )
        if product is None:
            product = InsuranceProduct(notion_product_id=row["product_id"])
            db.add(product)

        product.insurer = row["insurer"]
        product.name = row["name"]
        product.category = row["category"]
        product.product_version = row.get("version")
        product.sale_status = row["sale_status"]
        product.source_url = row["source_url"]

        by_key[(row["insurer"], row["name"], row.get("version"))] = product

    db.flush()
    print(f"upserted {len(rows)} insurance products")
    return by_key


def load_standard_coverages(db) -> None:
    rows = json.loads((EXPORT_DIR / "standard_coverages.json").read_text(encoding="utf-8"))

    for row in rows:
        coverage = db.query(StandardCoverage).filter(StandardCoverage.code == row["code"]).one_or_none()
        if coverage is None:
            coverage = StandardCoverage(code=row["code"])
            db.add(coverage)

        coverage.notion_coverage_id = row["coverage_id"]
        coverage.name = row["name"]
        coverage.coverage_area = row["coverage_area"]
        coverage.risk_type = row["risk_type"]
        coverage.coverage_form = row["coverage_form"]

    db.flush()
    print(f"upserted {len(rows)} standard coverages")


def load_mappings(db, products_by_key: dict[tuple[str, str, str | None], InsuranceProduct]) -> None:
    rows = json.loads((EXPORT_DIR / "product_coverage_mapping.json").read_text(encoding="utf-8"))

    skipped = 0
    for row in rows:
        key = (row["insurer"], row["product_name"], row["product_version"])
        product = products_by_key.get(key)
        if product is None:
            skipped += 1
            continue

        mapping = (
            db.query(ProductCoverageMapping)
            .filter(
                ProductCoverageMapping.product_id == product.id,
                ProductCoverageMapping.original_coverage_name == row["original_coverage_name"],
                ProductCoverageMapping.coverage_code == row["standard_coverage_code"],
            )
            .one_or_none()
        )
        if mapping is None:
            mapping = ProductCoverageMapping(
                product_id=product.id,
                original_coverage_name=row["original_coverage_name"],
                coverage_code=row["standard_coverage_code"],
            )
            db.add(mapping)

        mapping.mapping_type = row["mapping_type"]
        mapping.key_attributes = row.get("key_attributes")
        mapping.source_type = row["source_type"]
        mapping.source_url = row["source_url"]

    db.flush()
    print(f"upserted {len(rows) - skipped} product-coverage mappings ({skipped} skipped, product not found)")


def run() -> None:
    db = SessionLocal()
    try:
        products_by_key = load_products(db)
        load_standard_coverages(db)
        load_mappings(db, products_by_key)
        db.commit()
        print("done")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
