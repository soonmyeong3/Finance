from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.insurance import InsuranceProduct, ProductCoverageMapping, UserInsurance
from app.schemas.insurance import (
    InsuranceProductOut,
    ProductCoverageOut,
    UserInsuranceCreate,
    UserInsuranceOut,
)
from app.services.coverage_gap import analyze_coverage_gaps

router = APIRouter(tags=["insurance"])


@router.get("/insurance/products", response_model=list[InsuranceProductOut])
def list_products(category: str | None = None, db: Session = Depends(get_db)):
    query = db.query(InsuranceProduct)
    if category:
        query = query.filter(InsuranceProduct.category == category)
    return query.all()


@router.get("/insurance/products/{product_id}/coverages", response_model=list[ProductCoverageOut])
def list_product_coverages(product_id: int, db: Session = Depends(get_db)):
    return (
        db.query(ProductCoverageMapping)
        .filter(ProductCoverageMapping.product_id == product_id)
        .all()
    )


@router.get("/users/{user_id}/insurance", response_model=list[UserInsuranceOut])
def list_vault(user_id: int, db: Session = Depends(get_db)):
    return db.query(UserInsurance).filter(UserInsurance.user_id == user_id).all()


@router.post("/users/{user_id}/insurance", response_model=UserInsuranceOut)
def add_to_vault(user_id: int, payload: UserInsuranceCreate, db: Session = Depends(get_db)):
    product = db.get(InsuranceProduct, payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="product not found")
    entry = UserInsurance(user_id=user_id, product_id=payload.product_id, status=payload.status)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/users/{user_id}/insurance/gaps")
def coverage_gaps(user_id: int, db: Session = Depends(get_db)):
    """Diagnostic diff, not a recommendation: which StandardCoverage areas
    the user's registered insurance doesn't reach, cross-referenced against
    their recent life-event notifications."""
    return analyze_coverage_gaps(db, user_id)
