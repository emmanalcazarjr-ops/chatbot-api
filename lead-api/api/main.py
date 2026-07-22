import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from shared.auth import validate_api_key
from shared.database import execute_query, init_database
from shared.deepseek import call_deepseek, call_deepseek_with_messages
from shared.rate_limit import check_rate_limit
from shared.webhooks import parse_webhook_payload, format_webhook_response

app = FastAPI(title="Lead Follow-up Automation API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FOLLOWUP_SYSTEM_PROMPT = "You are an AI email assistant. Generate a professional, personalized follow-up email for this lead. Be concise, friendly, and include a clear call to action. Return JSON with 'subject' and 'body' fields."


class CreateLeadRequest(BaseModel):
    name: str
    email: str
    source: str
    notes: Optional[str] = None


class UpdateLeadRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class FollowupRequest(BaseModel):
    context: Optional[str] = None


class WebhookLead(BaseModel):
    name: str = ""
    email: str = ""
    source: str = "webhook"
    notes: Optional[str] = None


@app.on_event("startup")
async def startup():
    init_database()


@app.get("/api")
async def api_info():
    return {
        "name": "Lead Follow-up Automation API",
        "version": "1.0.0",
        "description": "AI-powered lead management and follow-up automation.",
        "endpoints": {
            "POST /api/leads": "Create a new lead",
            "GET /api/leads": "List leads (optional status filter)",
            "GET /api/leads/{id}": "Get lead by ID",
            "PUT /api/leads/{id}": "Update a lead",
            "POST /api/leads/{id}/followup": "Generate AI follow-up email",
            "POST /api/webhook": "Receive leads from external systems",
            "GET /api/health": "Health check"
        },
        "powered_by": "DeepSeek AI"
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "lead-api", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/leads")
async def create_lead(request: Request, body: CreateLeadRequest):
    client_ip = request.client.host
    allowed, retry_after = check_rate_limit(client_ip, "leads")
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Retry after {retry_after}s")

    auth_header = request.headers.get("Authorization")
    valid, error = validate_api_key(auth_header)
    if not valid:
        raise HTTPException(status_code=401, detail=error)

    result = execute_query(
        "INSERT INTO leads (name, email, source, notes, created_at) VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (body.name, body.email, body.source, body.notes, datetime.utcnow()),
        fetch=True
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to create lead")

    return {"id": result[0]["id"], "name": body.name, "email": body.email, "source": body.source, "status": "new", "notes": body.notes}


@app.get("/api/leads")
async def list_leads(request: Request, status: Optional[str] = None):
    client_ip = request.client.host
    allowed, retry_after = check_rate_limit(client_ip, "leads")
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Retry after {retry_after}s")

    auth_header = request.headers.get("Authorization")
    valid, error = validate_api_key(auth_header)
    if not valid:
        raise HTTPException(status_code=401, detail=error)

    if status:
        rows = execute_query(
            "SELECT id, name, email, source, status, notes, created_at FROM leads WHERE status = %s ORDER BY created_at DESC",
            (status,),
            fetch=True
        )
    else:
        rows = execute_query(
            "SELECT id, name, email, source, status, notes, created_at FROM leads ORDER BY created_at DESC",
            fetch=True
        )

    return {"leads": rows or [], "count": len(rows or [])}


@app.get("/api/leads/{lead_id}")
async def get_lead(lead_id: int, request: Request):
    client_ip = request.client.host
    allowed, retry_after = check_rate_limit(client_ip, "leads")
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Retry after {retry_after}s")

    auth_header = request.headers.get("Authorization")
    valid, error = validate_api_key(auth_header)
    if not valid:
        raise HTTPException(status_code=401, detail=error)

    rows = execute_query(
        "SELECT id, name, email, source, status, notes, created_at FROM leads WHERE id = %s",
        (lead_id,),
        fetch=True
    )

    if not rows:
        raise HTTPException(status_code=404, detail="Lead not found")

    return rows[0]


@app.put("/api/leads/{lead_id}")
async def update_lead(lead_id: int, request: Request, body: UpdateLeadRequest):
    client_ip = request.client.host
    allowed, retry_after = check_rate_limit(client_ip, "leads")
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Retry after {retry_after}s")

    auth_header = request.headers.get("Authorization")
    valid, error = validate_api_key(auth_header)
    if not valid:
        raise HTTPException(status_code=401, detail=error)

    existing = execute_query(
        "SELECT id FROM leads WHERE id = %s",
        (lead_id,),
        fetch=True
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Lead not found")

    fields = []
    values = []
    if body.name is not None:
        fields.append("name = %s")
        values.append(body.name)
    if body.email is not None:
        fields.append("email = %s")
        values.append(body.email)
    if body.status is not None:
        fields.append("status = %s")
        values.append(body.status)
    if body.notes is not None:
        fields.append("notes = %s")
        values.append(body.notes)

    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    values.append(lead_id)
    query = f"UPDATE leads SET {', '.join(fields)} WHERE id = %s"
    execute_query(query, tuple(values))

    rows = execute_query(
        "SELECT id, name, email, source, status, notes, created_at FROM leads WHERE id = %s",
        (lead_id,),
        fetch=True
    )

    return rows[0]


@app.post("/api/leads/{lead_id}/followup")
async def generate_followup(lead_id: int, request: Request, body: FollowupRequest):
    client_ip = request.client.host
    allowed, retry_after = check_rate_limit(client_ip, "followup")
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Retry after {retry_after}s")

    auth_header = request.headers.get("Authorization")
    valid, error = validate_api_key(auth_header)
    if not valid:
        raise HTTPException(status_code=401, detail=error)

    rows = execute_query(
        "SELECT id, name, email, source, status, notes FROM leads WHERE id = %s",
        (lead_id,),
        fetch=True
    )

    if not rows:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead = rows[0]

    prompt = f"Generate a follow-up email for this lead:\nName: {lead['name']}\nEmail: {lead['email']}\nSource: {lead['source']}\nStatus: {lead['status']}\nNotes: {lead.get('notes', 'N/A')}"
    if body.context:
        prompt += f"\nAdditional context: {body.context}"

    result = call_deepseek(prompt, system_prompt=FOLLOWUP_SYSTEM_PROMPT, max_tokens=500, temperature=0.7)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=f"AI error: {result['error']}")

    content = result["content"]
    parsed = None
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
            except json.JSONDecodeError:
                pass

    if not parsed:
        parsed = {"subject": "Follow-up", "body": content}

    subject = parsed.get("subject", "Follow-up")
    message_body = parsed.get("body", content)

    execute_query(
        "INSERT INTO lead_followups (lead_id, channel, subject, message, status, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
        (lead_id, "email", subject, message_body, "draft", datetime.utcnow())
    )

    return {
        "lead_id": lead_id,
        "subject": subject,
        "body": message_body,
        "channel": "email",
        "status": "draft"
    }


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

    data = payload["data"]
    name = data.get("name", "")
    email = data.get("email", "")
    source = data.get("source", payload["source"])
    notes = data.get("notes", None)

    if not name or not email:
        raise HTTPException(status_code=400, detail="Name and email are required")

    result = execute_query(
        "INSERT INTO leads (name, email, source, notes, created_at) VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (name, email, source, notes, datetime.utcnow()),
        fetch=True
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to create lead")

    return format_webhook_response({
        "lead_id": result[0]["id"],
        "name": name,
        "email": email,
        "source": source,
        "status": "new"
    })
