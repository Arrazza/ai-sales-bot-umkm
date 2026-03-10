from fastapi import FastAPI, Request
from app.schemas import ChatRequest, ChatResponse
from app.chat_logic import handle_chat
import httpx
import os
import json

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
    return {"status": "ok"}


@app.post("/webhook")
async def webhook_fonnte(request: Request):
    # Log raw payload untuk debug
    body = await request.body()
    print("WEBHOOK RAW BODY:", body.decode("utf-8"))

    try:
        data = json.loads(body)
    except Exception:
        from urllib.parse import parse_qs

        parsed = parse_qs(body.decode("utf-8"))
        data = {k: v[0] for k, v in parsed.items()}

    print("WEBHOOK PARSED DATA:", data)

    sender = data.get("sender", "")
    message = data.get("message", "")

    print(f"SENDER: {sender}, MESSAGE: {message}")

    if not sender or not message:
        return {"status": "ignored"}

    reply = handle_chat(message, sender)
    print(f"REPLY: {reply}")

    if FONNTE_TOKEN and reply:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.fonnte.com/send",
                headers={"Authorization": FONNTE_TOKEN},
                data={
                    "target": sender,
                    "message": reply,
                },
            )
            print(f"FONNTE SEND STATUS: {res.status_code}, BODY: {res.text}")

    return {"status": "ok"}
