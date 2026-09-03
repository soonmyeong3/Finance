from app.models.insurance import InsuranceProduct, UserInsurance
from app.models.notification import Notification
from app.models.user import User
from app.services.coverage_gap import analyze_coverage_gaps
from scripts.load_notion_insurance_export import load_mappings, load_products, load_standard_coverages


def _load_catalog(db_session):
    products_by_key = load_products(db_session)
    load_standard_coverages(db_session)
    load_mappings(db_session, products_by_key)
    db_session.commit()


def test_area_with_no_registered_insurance_is_fully_missing(db_session):
    _load_catalog(db_session)
    user = User()
    db_session.add(user)
    db_session.commit()

    gaps = analyze_coverage_gaps(db_session, user.id)

    pet_gap = next(g for g in gaps if g["coverage_area"] == "반려동물")
    assert pet_gap["covered_coverages"] == 0
    assert pet_gap["total_coverages"] == 4  # PET_* codes in standard_coverages.json
    assert len(pet_gap["missing_coverage_names"]) == pet_gap["total_coverages"]


def test_registering_a_product_closes_some_of_its_area_gap(db_session):
    _load_catalog(db_session)
    user = User()
    db_session.add(user)
    db_session.commit()

    dental_product = (
        db_session.query(InsuranceProduct).filter(InsuranceProduct.name == "KB The건강한 치아보험").one()
    )
    db_session.add(UserInsurance(user_id=user.id, product_id=dental_product.id, status="가입중"))
    db_session.commit()

    dental_gaps = [g for g in analyze_coverage_gaps(db_session, user.id) if g["coverage_area"] == "치아"]
    # dental area should now be partially covered, not fully missing (or
    # closed entirely if this one product happens to cover every 치아 code)
    if dental_gaps:
        assert dental_gaps[0]["covered_coverages"] > 0


def test_planned_insurance_does_not_close_the_gap(db_session):
    """가입예정 isn't in effect yet, so it shouldn't count as covering the
    area — only 가입중 should."""
    _load_catalog(db_session)
    user = User()
    db_session.add(user)
    db_session.commit()

    dental_product = (
        db_session.query(InsuranceProduct).filter(InsuranceProduct.name == "KB The건강한 치아보험").one()
    )
    db_session.add(UserInsurance(user_id=user.id, product_id=dental_product.id, status="가입예정"))
    db_session.commit()

    gaps = analyze_coverage_gaps(db_session, user.id)

    dental_gap = next(g for g in gaps if g["coverage_area"] == "치아")
    assert dental_gap["covered_coverages"] == 0


def test_gap_flagged_when_recent_notification_matches_category(db_session):
    _load_catalog(db_session)
    user = User()
    db_session.add(user)
    db_session.commit()

    db_session.add(
        Notification(
            user_id=user.id,
            kind="생애주기 변화",
            title="새로운 가족을 맞이하셨나요?",
            reason="최근 동물병원 결제가 새로 보여요.",
            cta_label="펫보험을 살펴봐요",
            cta_product_category="반려동물",
        )
    )
    db_session.commit()

    gaps = analyze_coverage_gaps(db_session, user.id)

    pet_gap = next(g for g in gaps if g["coverage_area"] == "반려동물")
    assert pet_gap["flagged_by_recent_event"] is True
    assert pet_gap["related_notification_title"] == "새로운 가족을 맞이하셨나요?"
    # flagged gaps sort first
    assert gaps[0]["coverage_area"] == "반려동물"


def test_fully_covered_area_is_excluded_from_gaps(db_session):
    _load_catalog(db_session)
    user = User()
    db_session.add(user)
    db_session.commit()

    # register every product so every coverage code is reachable
    for product in db_session.query(InsuranceProduct).all():
        db_session.add(UserInsurance(user_id=user.id, product_id=product.id, status="가입중"))
    db_session.commit()

    gaps = analyze_coverage_gaps(db_session, user.id)

    assert gaps == []
