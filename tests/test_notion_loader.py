from app.models.insurance import InsuranceProduct, ProductCoverageMapping, StandardCoverage
from scripts.load_notion_insurance_export import load_mappings, load_products, load_standard_coverages


def _load_all(db_session):
    products_by_key = load_products(db_session)
    load_standard_coverages(db_session)
    load_mappings(db_session, products_by_key)
    db_session.commit()


def test_load_matches_export_counts(db_session):
    _load_all(db_session)

    assert db_session.query(InsuranceProduct).count() == 19
    assert db_session.query(StandardCoverage).count() == 65
    assert db_session.query(ProductCoverageMapping).count() == 122


def test_load_is_idempotent(db_session):
    _load_all(db_session)
    _load_all(db_session)  # re-run against the same DB

    assert db_session.query(InsuranceProduct).count() == 19
    assert db_session.query(StandardCoverage).count() == 65
    assert db_session.query(ProductCoverageMapping).count() == 122
