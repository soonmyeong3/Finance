from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.chat import ChatMessage
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/users/{user_id}/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def send_message(user_id: int, payload: ChatRequest, db: Session = Depends(get_db)):
    db.add(ChatMessage(user_id=user_id, role="user", content=payload.message))

    # TODO: replace with real LLM call, RAG'd over InsuranceProduct rows.
    reply = "보비의 답변은 참고용이에요. 정확한 보장 여부는 보험사에 확인해 주세요."
    db.add(ChatMessage(user_id=user_id, role="assistant", content=reply))
    db.commit()

    return ChatResponse(reply=reply)
