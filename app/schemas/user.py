from pydantic import BaseModel, ConfigDict


class UserProfileUpdate(BaseModel):
    household_type: str
    work_type: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    household_type: str | None
    work_type: str | None
    cards_linked: bool
