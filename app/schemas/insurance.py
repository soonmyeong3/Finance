from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InsuranceProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    insurer: str
    name: str
    category: str
    product_version: str | None
    sale_status: str
    source_url: str


class StandardCoverageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    coverage_area: str
    risk_type: str
    coverage_form: str


class ProductCoverageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    original_coverage_name: str
    mapping_type: str
    key_attributes: str | None
    coverage: StandardCoverageOut


class UserInsuranceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product: InsuranceProductOut
    status: str
    created_at: datetime


class UserInsuranceCreate(BaseModel):
    product_id: int
    status: str
