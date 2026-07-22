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

from shared.deepseek import call_deepseek_with_messages

app = FastAPI(title="Rush AI Butler API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RUSH_SYSTEM_PROMPT = """You are Rush, Emmanuel Alcazar Jr.'s AI butler. You are professional, friendly, and knowledgeable about Emmanuel's work as a Software Engineer and ML Engineer.

About Emmanuel:
- Software Engineer & ML Engineer
- Licensed Electronics Engineer (ECE)
- GitHub: https://github.com/emmanalcazarjr-ops
- Portfolio: https://portfolio-elalcazarjr.vercel.app
- LinkedIn: https://www.linkedin.com/in/emmanalcazarjr/
- Email: EmmanAlcazarJr@gmail.com

Skills: Python (scikit-learn, TensorFlow, PyTorch), Java, Next.js, TypeScript, RAG, NLP, LLM Integration
Projects: Core Banking System, Fraud Detection, Credit Risk Predictor, Stock Price Predictor, Customer Churn Predictor, Sentiment Analysis, RAG Q&A API, Semantic Search API, Rush AI Butler

You help visitors learn about his projects, skills, and experience. Keep responses concise and helpful. Be warm, professional, and helpful."""

# In-memory conversation storage (for demo - no database required)
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
        "powered_by": "DeepSeek AI"
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

    # Get or create conversation history
    if session_id not in conversations:
        conversations[session_id] = []

    # Add user message to history
    conversations[session_id].append({"role": "user", "content": user_message})

    # Build messages for AI
    messages = [{"role": "system", "content": RUSH_SYSTEM_PROMPT}]
    messages.extend(conversations[session_id])

    # Call DeepSeek AI
    result = call_deepseek_with_messages(messages, max_tokens=1000, temperature=0.7)

    if not result["success"]:
        # Remove the user message if AI failed
        conversations[session_id].pop()
        raise HTTPException(status_code=500, detail=f"AI error: {result['error']}")

    assistant_message = result["content"]

    # Add assistant response to history
    conversations[session_id].append({"role": "assistant", "content": assistant_message})

    # Keep only last 20 messages per session
    if len(conversations[session_id]) > 20:
        conversations[session_id] = conversations[session_id][-20:]

    return {
        "session_id": session_id,
        "response": assistant_message,
        "done": True
    }
