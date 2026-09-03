from datetime import datetime

from sqlalchemy import String, Text, ForeignKey, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class InsuranceProduct(Base):
    """Mirrors Notion's "보험상품" data source (19 rows as of 2026-09-02).

    Loaded via scripts/load_notion_insurance_export.py from
    data/notion_export/products.json — Notion is the source of truth;
    this table is a synced copy, not independently edited.
    """

    __tablename__ = "insurance_products"

    id: Mapped[int] = mapped_column(primary_key=True)
    notion_product_id: Mapped[int | None] = mapped_column(unique=True, nullable=True)
    insurer: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50), index=True)
    # 건강 / 운전자 / 치아 / 여행 / 주택/재물 / 반려동물 / 기타 — Notion 상품분류 select 옵션과 동일
    product_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sale_status: Mapped[str] = mapped_column(String(20), default="미확인")
    # 판매중 / 미확인 / 종료
    source_url: Mapped[str] = mapped_column(String(500))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StandardCoverage(Base):
    """Mirrors Notion's "표준보장" data source (65 rows) — the cross-insurer
    comparison unit described in 보험 보장 표준 분류체계."""

    __tablename__ = "standard_coverages"

    id: Mapped[int] = mapped_column(primary_key=True)
    notion_coverage_id: Mapped[int | None] = mapped_column(unique=True, nullable=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    coverage_area: Mapped[str] = mapped_column(String(30))
    # 생명/실손의료/건강/상해/운전자/여행/재물/배상책임/간병/치아/반려동물
    risk_type: Mapped[str] = mapped_column(String(100))
    coverage_form: Mapped[str] = mapped_column(String(30))
    # 사망/진단/입원/통원/수술/치료/비용/배상/후유장해/기타


class ProductCoverageMapping(Base):
    """Mirrors Notion's "상품-보장매핑" data source (122 rows) — links an
    insurer's original coverage line item to a StandardCoverage code."""

    __tablename__ = "product_coverage_mappings"
    __table_args__ = (
        UniqueConstraint("product_id", "original_coverage_name", "coverage_code", name="uq_product_coverage"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("insurance_products.id"), index=True)
    coverage_code: Mapped[str] = mapped_column(ForeignKey("standard_coverages.code"), index=True)
    original_coverage_name: Mapped[str] = mapped_column(String(300))
    mapping_type: Mapped[str] = mapped_column(String(20))
    # EXACT / ATTRIBUTE / COMPOSITE
    key_attributes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(30))
    # 공식상품페이지 / 약관
    source_url: Mapped[str] = mapped_column(String(500))

    product: Mapped["InsuranceProduct"] = relationship()
    coverage: Mapped["StandardCoverage"] = relationship()


class UserInsurance(Base):
    """Entries in a user's 보험함."""

    __tablename__ = "user_insurance"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("insurance_products.id"))
    status: Mapped[str] = mapped_column(String(20))
    # 가입중 / 가입예정
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped["InsuranceProduct"] = relationship()
