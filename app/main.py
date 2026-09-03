from fastapi import FastAPI

from app.api.routes import cards, chat, insurance, notifications, users

app = FastAPI(title="Bobi Backend")

app.include_router(users.router)
app.include_router(cards.router)
app.include_router(insurance.router)
app.include_router(notifications.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}
