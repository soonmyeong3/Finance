from datetime import datetime, timedelta

from app.models.card_transaction import CardTransaction
from app.models.user import User
from app.services.life_event_detector import detect_life_events


def _make_user(db_session) -> User:
    user = User()
    db_session.add(user)
    db_session.commit()
    return user


def _add_txn(db_session, user_id, category, amount, days_ago):
    db_session.add(
        CardTransaction(
            user_id=user_id,
            merchant_category=category,
            amount=amount,
            occurred_at=datetime.utcnow() - timedelta(days=days_ago),
        )
    )


def test_no_transactions_produces_no_events(db_session):
    user = _make_user(db_session)
    assert detect_life_events(db_session, user.id) == []


def test_new_pet_category_triggers_lifecycle_event(db_session):
    user = _make_user(db_session)
    for i in range(5):
        _add_txn(db_session, user.id, "동물병원", 50000, days_ago=i * 3)
    db_session.commit()

    events = detect_life_events(db_session, user.id)

    assert len(events) == 1
    assert events[0]["kind"] == "생애주기 변화"
    assert events[0]["cta_product_category"] == "반려동물"


def test_pet_category_in_both_periods_does_not_trigger(db_session):
    """New-appearance rule requires it to be absent from the prior window —
    if it was already showing up, it's not "new"."""
    user = _make_user(db_session)
    for i in range(3):
        _add_txn(db_session, user.id, "동물병원", 50000, days_ago=i * 3)
    for i in range(3):
        _add_txn(db_session, user.id, "동물병원", 50000, days_ago=40 + i * 3)
    db_session.commit()

    events = detect_life_events(db_session, user.id)

    assert all(e["cta_product_category"] != "반려동물" for e in events)


def test_repeated_dental_triggers_pattern_event(db_session):
    user = _make_user(db_session)
    for i in range(4):
        _add_txn(db_session, user.id, "치과", 100000, days_ago=i * 5)
    db_session.commit()

    events = detect_life_events(db_session, user.id)

    assert any(e["kind"] == "생활 패턴 변화" and e["cta_product_category"] == "치아" for e in events)


def test_two_dental_visits_do_not_trigger_below_threshold(db_session):
    user = _make_user(db_session)
    for i in range(2):
        _add_txn(db_session, user.id, "치과", 100000, days_ago=i * 5)
    db_session.commit()

    events = detect_life_events(db_session, user.id)

    assert all(e["cta_product_category"] != "치아" for e in events)


def test_medical_spend_spike_triggers_event(db_session):
    user = _make_user(db_session)
    _add_txn(db_session, user.id, "병원", 200000, days_ago=2)
    _add_txn(db_session, user.id, "약국", 100000, days_ago=3)
    _add_txn(db_session, user.id, "병원", 30000, days_ago=50)  # previous period baseline
    db_session.commit()

    events = detect_life_events(db_session, user.id)

    spike = next(e for e in events if e["kind"] == "지출 급증")
    assert "10.0배" in spike["reason"]
