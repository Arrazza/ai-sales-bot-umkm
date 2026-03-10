from fastapi import FastAPI, Request
from app.schemas import ChatRequest, ChatResponse
from app.chat_logic import handle_chat
import httpx
import os

app = FastAPI(title="HoodieBot API")

FONNTE_TOKEN = os.getenv("FONNTE_TOKEN", "")


@app.get("/")
def health_check():
    return {"status": "ok", "message": "HoodieBot API is running"}


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    reply = handle_chat(request.message, request.session_id)
    return ChatResponse(reply=reply)


@app.get("/webhook")
def webhook_verify():
    """GET handler untuk verifikasi Fonnte"""
    return {"status": "ok"}


@app.post("/webhook")
async def webhook_fonnte(request: Request):
    """
    Endpoint untuk menerima pesan masuk dari Fonnte.
    Fonnte akan POST ke sini setiap ada pesan WA masuk.
    """
    try:
        data = await request.json()
    except Exception:
        data = await request.form()
        data = dict(data)

    # Ambil data dari payload Fonnte
    sender = data.get("sender", "")
    message = data.get("message", "")

    if not sender or not message:
        return {"status": "ignored"}

    # Gunakan sender sebagai session_id (unik per nomor WA)
    reply = handle_chat(message, sender)

    # Kirim balik reply ke WA sender via Fonnte API
    if FONNTE_TOKEN and reply:
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.fonnte.com/send",
                headers={"Authorization": FONNTE_TOKEN},
                data={
                    "target": sender,
                    "message": reply,
                },
            )

    return {"status": "ok"}
