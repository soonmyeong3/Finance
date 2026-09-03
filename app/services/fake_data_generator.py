"""Synthetic card-transaction generator.

Real card data is out of scope (마이데이터 카드 연동은 사업자 라이선스가
필요해 못 씀) — we only ever generate fake transactions, anchored
to a persona scenario so demos are reproducible (e.g. "a user whose spend
suggests they just got a pet").
"""

import random
from datetime import datetime, timedelta

from faker import Faker

fake = Faker("ko_KR")

# Each persona: a weighted list of (merchant_category, weight) that shapes
# the fake spend mix.
PERSONAS: dict[str, dict] = {
    "industrial_area_worker": {
        "categories": [
            ("편의점", 5),
            ("구내식당", 4),
            ("병원", 3),
            ("약국", 3),
            ("산업용품", 2),
            ("주유소", 2),
        ],
    },
    "new_pet_owner": {
        "categories": [
            ("동물병원", 4),
            ("반려동물용품", 4),
            ("카페", 3),
            ("마트", 3),
            ("편의점", 2),
        ],
    },
    "frequent_dental": {
        "categories": [
            ("치과", 4),
            ("약국", 3),
            ("카페", 3),
            ("마트", 2),
            ("편의점", 2),
        ],
    },
}

AMOUNT_RANGE_BY_CATEGORY = {
    "편의점": (3000, 15000),
    "구내식당": (5000, 9000),
    "병원": (10000, 80000),
    "약국": (5000, 30000),
    "산업용품": (10000, 200000),
    "주유소": (30000, 80000),
    "동물병원": (30000, 300000),
    "반려동물용품": (10000, 100000),
    "카페": (4000, 12000),
    "마트": (10000, 100000),
    "치과": (20000, 500000),
}


def generate_fake_transactions(persona: str, months: int = 3, count: int = 60) -> list[dict]:
    """Return a list of plain dicts ready to build CardTransaction rows."""
    if persona not in PERSONAS:
        raise ValueError(f"unknown persona: {persona}")

    categories, weights = zip(*PERSONAS[persona]["categories"])
    now = datetime.utcnow()

    transactions = []
    for _ in range(count):
        category = random.choices(categories, weights=weights, k=1)[0]
        lo, hi = AMOUNT_RANGE_BY_CATEGORY.get(category, (5000, 50000))
        occurred_at = now - timedelta(days=random.uniform(0, months * 30))
        transactions.append(
            {
                "merchant_category": category,
                "amount": round(random.uniform(lo, hi), -2),
                "occurred_at": occurred_at,
            }
        )
    return transactions
