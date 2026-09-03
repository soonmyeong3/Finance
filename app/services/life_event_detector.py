"""Detects life-cycle / spending-pattern changes from a user's card
transactions and turns them into Notification rows.

Pure rule-based diffing over two time windows — no scoring or ranking of
insurance products, so this stays backend/data-pipeline territory rather
than recommendation-model territory. Whoever owns the recommendation model
can decide what to do with a detected event; this just detects it.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.card_transaction import CardTransaction
from app.models.notification import Notification

WINDOW_DAYS = 30


@dataclass
class SignalGroup:
    name: str
    categories: set[str]
    rule: str
    kind: str
    title: str
    action: str
    product_category: str
    reason: str | None = None
    min_count: int = 0
    min_ratio: float = 0.0


SIGNAL_GROUPS = [
    SignalGroup(
        name="반려동물",
        categories={"동물병원", "반려동물용품"},
        rule="new_appearance",
        kind="생애주기 변화",
        title="새로운 가족을 맞이하셨나요?",
        reason="최근 동물병원·반려동물 용품 결제가 새로 보여요. 반려동물과 함께하는 일상이 시작된 것 같아요.",
        action="가족이 된 반려동물을 위한 펫보험을 함께 살펴봐요",
        product_category="반려동물",
    ),
    SignalGroup(
        name="치과",
        categories={"치과"},
        rule="repeated",
        kind="생활 패턴 변화",
        title="치과 결제가 반복적으로 잡혀요",
        reason="최근 한 달간 치과 결제가 여러 번 나타났어요. 치료가 이어질 가능성이 있어요.",
        action="치아보험 보장 범위를 확인해보세요",
        product_category="치아",
        min_count=3,
    ),
    SignalGroup(
        name="의료비",
        categories={"병원", "약국"},
        rule="spend_spike",
        kind="지출 급증",
        title="의료비 지출이 평소보다 늘었어요",
        action="실손보험 청구 가능 항목을 확인해보세요",
        product_category="건강",
        min_ratio=1.5,
    ),
]


def _aggregate(transactions: list[CardTransaction]) -> tuple[Counter, dict[str, float]]:
    counts: Counter = Counter()
    totals: dict[str, float] = defaultdict(float)
    for t in transactions:
        counts[t.merchant_category] += 1
        totals[t.merchant_category] += float(t.amount)
    return counts, totals


def detect_life_events(db: Session, user_id: int, window_days: int = WINDOW_DAYS) -> list[dict]:
    now = datetime.utcnow()
    cutoff = now - timedelta(days=window_days)
    prev_cutoff = now - timedelta(days=window_days * 2)

    rows = db.query(CardTransaction).filter(CardTransaction.user_id == user_id).all()
    recent = [r for r in rows if r.occurred_at >= cutoff]
    previous = [r for r in rows if prev_cutoff <= r.occurred_at < cutoff]

    recent_counts, recent_totals = _aggregate(recent)
    prev_counts, prev_totals = _aggregate(previous)

    events: list[dict] = []
    for group in SIGNAL_GROUPS:
        recent_count = sum(recent_counts[c] for c in group.categories)
        prev_count = sum(prev_counts[c] for c in group.categories)
        recent_total = sum(recent_totals[c] for c in group.categories)
        prev_total = sum(prev_totals[c] for c in group.categories)

        if group.rule == "new_appearance":
            if recent_count > 0 and prev_count == 0:
                events.append(_event(group, group.reason))

        elif group.rule == "repeated":
            if recent_count >= group.min_count:
                events.append(_event(group, group.reason))

        elif group.rule == "spend_spike":
            if prev_total > 0 and recent_total / prev_total >= group.min_ratio:
                ratio = recent_total / prev_total
                reason = f"지난달 대비 {'·'.join(sorted(group.categories))} 결제가 {ratio:.1f}배 증가했어요."
                events.append(_event(group, reason))

    return events


def _event(group: SignalGroup, reason: str) -> dict:
    return {
        "kind": group.kind,
        "title": group.title,
        "reason": reason,
        "cta_label": group.action,
        "cta_product_category": group.product_category,
    }


def sync_notifications(db: Session, user_id: int) -> list[Notification]:
    """Re-runs detection and replaces the user's notifications with the
    current result. Simple full-replace for now — a real scheduled job
    would diff against what's already been sent instead."""
    events = detect_life_events(db, user_id)

    db.query(Notification).filter(Notification.user_id == user_id).delete()
    rows = [Notification(user_id=user_id, **event) for event in events]
    db.add_all(rows)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows
