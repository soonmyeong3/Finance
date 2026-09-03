"""Coverage-gap analysis: diffs what a user's registered insurance
actually covers (via ProductCoverageMapping) against the full 65-item
StandardCoverage catalog synced from Notion, grouped by coverage area.

This is set-diffing over already-synced data, not scoring or ranking
products — "여기 보장이 비어있어요" (diagnostic) rather than "이걸 사세요"
(prescriptive), so it stays out of the recommendation model's territory
the same way life_event_detector does.
"""

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.insurance import ProductCoverageMapping, StandardCoverage, UserInsurance
from app.models.notification import Notification


def _covered_codes(db: Session, user_id: int) -> set[str]:
    # 가입예정(planned) coverage isn't in effect yet, so it shouldn't close
    # a gap — only 가입중(active) counts. Otherwise registering everything
    # as "planned" would zero out every gap without actually covering it.
    rows = (
        db.query(ProductCoverageMapping.coverage_code)
        .join(UserInsurance, UserInsurance.product_id == ProductCoverageMapping.product_id)
        .filter(UserInsurance.user_id == user_id, UserInsurance.status == "가입중")
        .distinct()
        .all()
    )
    return {code for (code,) in rows}


def _recent_notification_by_category(db: Session, user_id: int) -> dict[str, Notification]:
    """Most recent notification per cta_product_category, for flagging a
    gap as "관련된 최근 변화가 있어요"."""
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.cta_product_category.isnot(None))
        .order_by(Notification.created_at.desc())
        .all()
    )
    by_category: dict[str, Notification] = {}
    for row in rows:
        by_category.setdefault(row.cta_product_category, row)
    return by_category


def analyze_coverage_gaps(db: Session, user_id: int) -> list[dict]:
    covered_codes = _covered_codes(db, user_id)
    notif_by_category = _recent_notification_by_category(db, user_id)

    by_area: dict[str, list[StandardCoverage]] = defaultdict(list)
    for coverage in db.query(StandardCoverage).all():
        by_area[coverage.coverage_area].append(coverage)

    gaps = []
    for area, coverages in by_area.items():
        missing = [c for c in coverages if c.code not in covered_codes]
        if not missing:
            continue

        related_notification = notif_by_category.get(area)
        gaps.append(
            {
                "coverage_area": area,
                "total_coverages": len(coverages),
                "covered_coverages": len(coverages) - len(missing),
                "missing_coverage_names": [c.name for c in missing],
                "flagged_by_recent_event": related_notification is not None,
                "related_notification_title": (
                    related_notification.title if related_notification else None
                ),
            }
        )

    # surface fully-uncovered areas with a recent life event first, then by
    # how incomplete the area is
    gaps.sort(
        key=lambda g: (
            not g["flagged_by_recent_event"],
            g["covered_coverages"] / g["total_coverages"],
        )
    )
    return gaps
