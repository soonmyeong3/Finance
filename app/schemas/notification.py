from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    title: str
    reason: str
    cta_label: str | None
    cta_product_category: str | None
    created_at: datetime
