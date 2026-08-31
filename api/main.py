import os
import sys
import json
import uuid
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from shared.gemini import call_gemini_with_messages
from shared import supabase

app = FastAPI(title="Rush AI Butler API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RUSH_SYSTEM_PROMPT = """You are Rush, Emmanuel Alcazar Jr.'s AI butler. You are professional, friendly, and knowledgeable about Emmanuel's work as an AI Automation & ML Developer.

About Emmanuel:
- AI Automation & Machine Learning Developer
- Licensed Electronics Engineer (ECE) & Electronics Technician (ECT)
- GitHub: https://github.com/emmanalcazarjr-ops
- Portfolio: https://portfolio-elalcazarjr.vercel.app
- LinkedIn: https://www.linkedin.com/in/emmanalcazarjr/
- Email: EmmanAlcazarJr@gmail.com

Skills: Python (FastAPI, pandas, NumPy, scikit-learn), TypeScript, Node.js, Next.js, grammY, Tailwind CSS, n8n, Supabase, PostgreSQL, Google Gemini AI, Git, GitHub Actions, Vercel
Projects: Automated Report Generator, Water Station Telegram Bots, Rush Personal AI Assistant, AI Chatbot API, Shared Backend

You help visitors learn about his projects, skills, and experience. Keep responses concise, sharp, and helpful. Be warm, professional, and confident."""

# In-memory fallback used only when Supabase is not configured
conversations = {}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


@app.get("/api")
async def api_info():
    return {
        "name": "Rush AI Butler API",
        "version": "1.0.0",
        "description": "AI-powered customer support butler by Emmanuel Alcazar Jr.",
        "endpoints": {
            "POST /api/chat": "Send a message to Rush",
            "GET /api/health": "Health check"
        },
        "powered_by": "Google Gemini"
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "chatbot-api", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/chat")
async def chat(request: Request, body: ChatRequest):
    session_id = body.session_id or str(uuid.uuid4())
    user_message = body.message.strip()

    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Load conversation history (Supabase-backed, with in-memory fallback)
    stored = supabase.get_messages(session_id)
    if stored is None:
        history = conversations.get(session_id, [])
    else:
        history = stored

    history = list(history)
    history.append({"role": "user", "content": user_message})

    # Build messages for AI
    messages = [{"role": "system", "content": RUSH_SYSTEM_PROMPT}]
    messages.extend(history)

    # Call Google Gemini AI
    result = call_gemini_with_messages(messages, max_tokens=1000, temperature=0.7)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=f"AI error: {result['error']}")

    assistant_message = result["content"]

    # Persist both turns
    if supabase.is_configured():
        supabase.append_message(session_id, "user", user_message)
        supabase.append_message(session_id, "assistant", assistant_message)
    else:
        conversations.setdefault(session_id, []).extend(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_message},
            ]
        )
        # Keep only last 20 messages per session
        conversations[session_id] = conversations[session_id][-20:]

    return {
        "session_id": session_id,
        "response": assistant_message,
        "done": True
    }
