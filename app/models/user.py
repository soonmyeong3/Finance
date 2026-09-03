from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # 1인가구 / 신혼예비부부 / 자녀있음 / 기타
    work_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # 직장인 / 프리랜서자영업 / 학생 / 기타
    cards_linked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
