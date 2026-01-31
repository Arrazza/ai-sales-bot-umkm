from fastapi import FastAPI
from app.schemas import ChatRequest, ChatResponse
from app.chat_logic import handle_chat

app = FastAPI(title="HoodieBot API")


@app.get("/")
def health_check():
    return {"status": "ok", "message": "HoodieBot API is running"}


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    reply = handle_chat(request.message, request.session_id)
    return ChatResponse(reply=reply)
