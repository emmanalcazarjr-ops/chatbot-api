import os
import sys
import json
import uuid
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from shared.auth import validate_api_key
from shared.database import execute_query, init_database
from shared.deepseek import call_deepseek_with_messages
from shared.rate_limit import check_rate_limit
from shared.webhooks import parse_webhook_payload, format_webhook_response

app = FastAPI(title="Rush AI Butler API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RUSH_SYSTEM_PROMPT = """You are Rush, Emmanuel Alcazar Jr.'s AI butler for today. You are professional, friendly, and knowledgeable about Emmanuel's work as a Software Engineer and ML Engineer.

About Emmanuel:
- Software Engineer & ML Engineer
- GitHub: https://github.com/emmanalcazarjr-ops
- Portfolio: https://portfolio-elalcazarjr.vercel.app
- LinkedIn: https://www.linkedin.com/in/emmanalcazarjr/
- Email: EmmanAlcazarJr@gmail.com

Skills: Java (Maven, MySQL), Python (scikit-learn, TensorFlow, PyTorch), Next.js, Tailwind CSS, FastAPI
Projects: Core Banking System, Fraud Detection, Credit Risk Predictor, Stock Price Predictor, Customer Churn Predictor, Sentiment Analysis, Spam Email Detector, and multiple ML APIs deployed on Vercel.

You help visitors learn about his projects, skills, and experience. You can also help schedule interviews or answer business inquiries. Keep responses concise and helpful. If asked about scheduling, guide them to use the appointment booking feature.

Be warm, professional, and helpful. Respond as a knowledgeable butler would."""


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class WebhookMessage(BaseModel):
    event: Optional[str] = "message.received"
    session_id: Optional[str] = None
    message: str = ""
    metadata: Optional[dict] = {}


@app.on_event("startup")
async def startup():
    init_database()


@app.get("/api")
async def api_info():
    return {
        "name": "Rush AI Butler API",
        "version": "1.0.0",
        "description": "AI-powered customer support butler by Emmanuel Alcazar Jr.",
        "endpoints": {
            "POST /api/chat": "Send a message to Rush",
            "GET /api/chat/history/{session_id}": "Get conversation history",
            "DELETE /api/chat/{session_id}": "Clear conversation",
            "POST /api/webhook": "Webhook for n8n/Zapier/Make/GHL",
            "GET /api/health": "Health check"
        },
        "powered_by": "DeepSeek AI"
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "chatbot-api", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/chat")
async def chat(request: Request, body: ChatRequest):
    client_ip = request.client.host
    allowed, retry_after = check_rate_limit(client_ip, "chat")
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Retry after {retry_after}s")

    auth_header = request.headers.get("Authorization")
    valid, error = validate_api_key(auth_header)
    if not valid:
        raise HTTPException(status_code=401, detail=error)

    session_id = body.session_id or str(uuid.uuid4())
    user_message = body.message.strip()

    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    execute_query(
        "INSERT INTO messages (session_id, role, content, created_at) VALUES (%s, %s, %s, %s)",
        (session_id, "user", user_message, datetime.utcnow())
    )

    history_rows = execute_query(
        "SELECT role, content FROM messages WHERE session_id = %s ORDER BY created_at ASC",
        (session_id,),
        fetch=True
    )

    messages = [{"role": "system", "content": RUSH_SYSTEM_PROMPT}]
    for row in (history_rows or []):
        messages.append({"role": row["role"], "content": row["content"]})

    result = call_deepseek_with_messages(messages, max_tokens=1000, temperature=0.7)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=f"AI error: {result['error']}")

    assistant_message = result["content"]

    execute_query(
        "INSERT INTO messages (session_id, role, content, created_at) VALUES (%s, %s, %s, %s)",
        (session_id, "assistant", assistant_message, datetime.utcnow())
    )

    return {
        "session_id": session_id,
        "response": assistant_message,
        "done": True
    }


@app.get("/api/chat/history/{session_id}")
async def get_history(session_id: str, request: Request):
    auth_header = request.headers.get("Authorization")
    valid, error = validate_api_key(auth_header)
    if not valid:
        raise HTTPException(status_code=401, detail=error)

    rows = execute_query(
        "SELECT role, content, created_at FROM messages WHERE session_id = %s ORDER BY created_at ASC",
        (session_id,),
        fetch=True
    )

    return {
        "session_id": session_id,
        "messages": rows or [],
        "count": len(rows or [])
    }


@app.delete("/api/chat/{session_id}")
async def clear_history(session_id: str, request: Request):
    auth_header = request.headers.get("Authorization")
    valid, error = validate_api_key(auth_header)
    if not valid:
        raise HTTPException(status_code=401, detail=error)

    execute_query("DELETE FROM messages WHERE session_id = %s", (session_id,))
    return {"session_id": session_id, "cleared": True}


@app.post("/api/webhook")
async def webhook(request: Request):
    client_ip = request.client.host
    allowed, retry_after = check_rate_limit(client_ip, "webhook")
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Retry after {retry_after}s")

    body = await request.body()
    payload, error = parse_webhook_payload(body)
    if error:
        raise HTTPException(status_code=400, detail=error)

    message = payload["data"].get("message", "")
    session_id = payload["data"].get("session_id", str(uuid.uuid4()))

    if not message:
        raise HTTPException(status_code=400, detail="No message in webhook payload")

    execute_query(
        "INSERT INTO messages (session_id, role, content, created_at) VALUES (%s, %s, %s, %s)",
        (session_id, "user", message, datetime.utcnow())
    )

    history_rows = execute_query(
        "SELECT role, content FROM messages WHERE session_id = %s ORDER BY created_at ASC",
        (session_id,),
        fetch=True
    )

    messages = [{"role": "system", "content": RUSH_SYSTEM_PROMPT}]
    for row in (history_rows or []):
        messages.append({"role": row["role"], "content": row["content"]})

    result = call_deepseek_with_messages(messages, max_tokens=1000, temperature=0.7)

    assistant_message = result["content"] if result["success"] else "I apologize, I'm having trouble responding right now."

    execute_query(
        "INSERT INTO messages (session_id, role, content, created_at) VALUES (%s, %s, %s, %s)",
        (session_id, "assistant", assistant_message, datetime.utcnow())
    )

    return format_webhook_response({
        "session_id": session_id,
        "response": assistant_message,
        "source": payload["source"]
    })
