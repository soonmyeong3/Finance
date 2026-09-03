from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.card_transaction import CardTransaction
from app.models.user import User
from app.services.card_statement_parser import parse_statement
from app.services.fake_data_generator import PERSONAS, generate_fake_transactions

router = APIRouter(prefix="/users/{user_id}/cards", tags=["cards"])


class LinkFakeCardRequest(BaseModel):
    persona: str = "industrial_area_worker"
    months: int = 3
    count: int = 60


@router.post("/link-fake")
def link_fake_cards(user_id: int, payload: LinkFakeCardRequest, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    if payload.persona not in PERSONAS:
        raise HTTPException(status_code=400, detail=f"unknown persona, choose one of {list(PERSONAS)}")

    rows = generate_fake_transactions(payload.persona, months=payload.months, count=payload.count)
    for row in rows:
        db.add(
            CardTransaction(
                user_id=user_id,
                merchant_category=row["merchant_category"],
                amount=row["amount"],
                occurred_at=row["occurred_at"],
                source="fake",
            )
        )
    user.cards_linked = True
    db.commit()
    return {"linked": True, "transaction_count": len(rows)}


@router.post("/statements")
async def upload_statement(user_id: int, file: UploadFile, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    content = await file.read()
    try:
        rows = parse_statement(file.filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    source = "csv_upload" if file.filename.lower().endswith(".csv") else "pdf_upload"
    for row in rows:
        db.add(
            CardTransaction(
                user_id=user_id,
                merchant_category=row["merchant_category"],
                merchant_name=row["merchant_name"],
                amount=row["amount"],
                occurred_at=row["occurred_at"],
                source=source,
            )
        )
    user.cards_linked = True
    db.commit()
    return {"linked": True, "transaction_count": len(rows)}


@router.get("/transactions")
def list_transactions(user_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(CardTransaction)
        .filter(CardTransaction.user_id == user_id)
        .order_by(CardTransaction.occurred_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "merchant_category": r.merchant_category,
            "merchant_name": r.merchant_name,
            "amount": float(r.amount),
            "occurred_at": r.occurred_at,
            "source": r.source,
        }
        for r in rows
    ]
