from datetime import datetime

from sqlalchemy import ForeignKey, String, Numeric, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CardTransaction(Base):
    """A card transaction — either synthetic (demo data, no real card
    linkage exists yet) or parsed from a user-uploaded CSV/PDF statement."""

    __tablename__ = "card_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    merchant_category: Mapped[str] = mapped_column(String(50))
    # e.g. 동물병원, 치과, 편의점, 산업용품 ...
    merchant_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # raw merchant name, only present for parsed statement uploads
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(20), default="fake")
    # fake / csv_upload / pdf_upload
