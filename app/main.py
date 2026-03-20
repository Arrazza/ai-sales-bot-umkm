import os
import json
import httpx
from fastapi import FastAPI, Request
from app.schemas import ChatRequest, ChatResponse
from app.chat_logic import handle_chat
from dotenv import load_dotenv

load_dotenv(override=False)

FONNTE_TOKEN = os.getenv("FONNTE_TOKEN", "")
NAMA_TOKO = "Wijaya Store"

app = FastAPI(title=f"{NAMA_TOKO} Bot API")


# ===== HEALTH CHECK =====
@app.get("/")
def health_check():
    return {"status": "ok", "message": f"{NAMA_TOKO} Bot is running 🏪"}


# ===== DEBUG ENV (hapus setelah fix) =====
@app.get("/debug-env")
def debug_env():
    client_email = os.getenv("GOOGLE_CLIENT_EMAIL", "")
    private_key = os.getenv("GOOGLE_PRIVATE_KEY", "")
    return {
        "GOOGLE_CLIENT_EMAIL_ada": bool(client_email),
        "GOOGLE_CLIENT_EMAIL_value": client_email[:40] if client_email else "KOSONG",
        "GOOGLE_PRIVATE_KEY_ada": bool(private_key),
        "GOOGLE_PRIVATE_KEY_awal": private_key[:50] if private_key else "KOSONG",
        "SPREADSHEET_ID_ada": bool(os.getenv("SPREADSHEET_ID")),
    }


# ===== CHAT ENDPOINT (untuk testing via Swagger) =====
@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    reply = handle_chat(request.message, request.session_id)
    return ChatResponse(reply=reply)


# ===== WEBHOOK FONNTE =====
@app.get("/webhook")
def webhook_verify():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook_fonnte(request: Request):
    try:
        body = await request.body()
        print("WEBHOOK RAW BODY:", body[:500])

        try:
            data = json.loads(body)
        except Exception:
            form = await request.form()
            data = dict(form)

        print("WEBHOOK DATA:", data)

        # Ambil sender dan message dari payload Fonnte
        sender = str(data.get("sender", "")).strip()
        message = str(data.get("message", "")).strip()

        print(f"SENDER: {sender} | MESSAGE: {message}")

        if not sender or not message:
            return {"status": "ignored", "reason": "no sender or message"}

        # Abaikan pesan dari diri sendiri (bot)
        device = str(data.get("device", "")).strip()
        if sender == device:
            return {"status": "ignored", "reason": "self message"}

        # Proses pesan — gunakan nomor WA sebagai session_id
        reply = handle_chat(message, session_id=sender, no_wa=sender)

        if not reply:
            return {"status": "ignored", "reason": "no reply generated"}

        # Kirim balasan via Fonnte
        async with httpx.AsyncClient() as client:
            fonnte_res = await client.post(
                "https://api.fonnte.com/send",
                headers={"Authorization": FONNTE_TOKEN},
                data={"target": sender, "message": reply},
                timeout=10,
            )
            print("FONNTE SEND STATUS:", fonnte_res.status_code, fonnte_res.text[:200])

        return {"status": "ok", "reply_sent": True}

    except Exception as e:
        print("WEBHOOK ERROR:", e)
        return {"status": "error", "detail": str(e)}
