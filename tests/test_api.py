"""API contract tests for the Rush AI Butler API (FastAPI TestClient).

Runs fully offline: conftest.py strips SUPABASE_* (forcing the in-memory
fallback) and DEEPSEEK_API_KEY, and the DeepSeek call is monkeypatched.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from api import main as api_main  # noqa: E402


client = TestClient(api_main.app)


def test_api_info_endpoint():
    res = client.get("/api")
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Rush AI Butler API"
    assert "POST /api/chat" in body["endpoints"]


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "healthy"
    assert body["service"] == "chatbot-api"


def test_chat_rejects_blank_message():
    res = client.post("/api/chat", json={"message": "   "})
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()


def test_chat_returns_response_and_persists_history(monkeypatch):
    sent = []

    def fake(messages, max_tokens=1000, temperature=0.7):
        sent.append(messages)
        return {"success": True, "content": "I am Rush, sir."}

    monkeypatch.setattr(api_main, "call_deepseek_with_messages", fake)

    first = client.post("/api/chat", json={"message": "Who are you?"})
    assert first.status_code == 200
    body = first.json()
    assert body["response"] == "I am Rush, sir."
    assert body["done"] is True
    session_id = body["session_id"]

    # Follow-up on the same session must include prior turns in the AI payload
    second = client.post("/api/chat", json={"message": "What did I just ask?", "session_id": session_id})
    assert second.status_code == 200
    assert second.json()["session_id"] == session_id

    roles = [m["role"] for m in sent[1]]
    assert roles.count("user") == 2  # both user turns present
    assert any(m["role"] == "assistant" for m in sent[1])  # assistant reply remembered


def test_chat_surfaces_ai_failure_as_500(monkeypatch):
    def fake(messages, max_tokens=1000, temperature=0.7):
        return {"success": False, "error": "DEEPSEEK_API_KEY not configured"}

    monkeypatch.setattr(api_main, "call_deepseek_with_messages", fake)
    res = client.post("/api/chat", json={"message": "hello"})
    assert res.status_code == 500
