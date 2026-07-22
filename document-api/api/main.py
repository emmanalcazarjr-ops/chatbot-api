import os
import sys
import json
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from shared.auth import validate_api_key
from shared.database import execute_query, init_database
from shared.deepseek import call_deepseek, parse_json_response
from shared.rate_limit import check_rate_limit
from shared.webhooks import parse_webhook_payload, format_webhook_response

app = FastAPI(title="Document Processing API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(500),
    content TEXT,
    summary TEXT,
    key_points TEXT,
    document_type VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

ANALYSIS_SYSTEM_PROMPT = (
    "You are a document analysis AI. Analyze the provided document and return JSON with: "
    "'summary' (concise 2-3 sentence summary), "
    "'key_points' (array of key points), "
    "'document_type' (e.g., invoice, contract, report, meeting_notes, email, other). "
    "Be accurate and concise."
)

CUSTOM_ANALYSIS_PROMPT = (
    "Analyze this document based on the following instruction: {user_prompt}. "
    "Return JSON with 'analysis' field containing your findings."
)


class CreateDocumentRequest(BaseModel):
    filename: str
    text: str
    analysis_type: str = "all"


class CustomAnalysisRequest(BaseModel):
    prompt: str


@app.on_event("startup")
async def startup():
    init_database(DOCUMENTS_TABLE)


@app.get("/api")
async def api_info():
    return {
        "name": "Document Processing API",
        "version": "1.0.0",
        "description": "AI-powered document analysis and processing",
        "endpoints": {
            "POST /api/documents": "Submit document for processing",
            "GET /api/documents": "List all documents",
            "GET /api/documents/{id}": "Get document by ID",
            "POST /api/documents/{id}/analyze": "Run custom analysis",
            "POST /api/webhook": "Receive documents from external systems",
        },
    }


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "document-api", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/documents")
async def create_document(
    request: CreateDocumentRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    if not validate_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    check_rate_limit(x_api_key)

    summary = None
    key_points = None
    document_type = None
    status = "pending"

    if request.analysis_type in ("all", "summary", "extract", "classify"):
        prompt = f"Document filename: {request.filename}\n\nDocument content:\n{request.text}"
        result = call_deepseek(prompt, ANALYSIS_SYSTEM_PROMPT, max_tokens=1000, temperature=0.3)

        if result["success"]:
            parsed = parse_json_response(result["content"])
            if parsed:
                summary = parsed.get("summary")
                key_points = json.dumps(parsed.get("key_points", []))
                document_type = parsed.get("document_type")
                status = "completed"
            else:
                status = "analysis_failed"
        else:
            status = "analysis_failed"

    row = execute_query(
        """INSERT INTO documents (filename, content, summary, key_points, document_type, status)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING id, created_at""",
        (request.filename, request.text, summary, key_points, document_type, status),
        fetch_one=True,
    )

    return {
        "id": row["id"],
        "filename": request.filename,
        "summary": summary,
        "key_points": json.loads(key_points) if key_points else [],
        "document_type": document_type,
        "status": status,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


@app.get("/api/documents")
async def list_documents(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    if not validate_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    check_rate_limit(x_api_key)

    rows = execute_query(
        "SELECT id, filename, document_type, status, created_at FROM documents ORDER BY created_at DESC",
        fetch_all=True,
    )

    documents = []
    for row in rows:
        documents.append({
            "id": row["id"],
            "filename": row["filename"],
            "document_type": row["document_type"],
            "status": row["status"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        })

    return {"documents": documents, "total": len(documents)}


@app.get("/api/documents/{doc_id}")
async def get_document(
    doc_id: int,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    if not validate_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    check_rate_limit(x_api_key)

    row = execute_query(
        "SELECT * FROM documents WHERE id = %s",
        (doc_id,),
        fetch_one=True,
    )

    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": row["id"],
        "filename": row["filename"],
        "content": row["content"],
        "summary": row["summary"],
        "key_points": json.loads(row["key_points"]) if row["key_points"] else [],
        "document_type": row["document_type"],
        "status": row["status"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


@app.post("/api/documents/{doc_id}/analyze")
async def analyze_document(
    doc_id: int,
    request: CustomAnalysisRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    if not validate_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    check_rate_limit(x_api_key)

    row = execute_query(
        "SELECT * FROM documents WHERE id = %s",
        (doc_id,),
        fetch_one=True,
    )

    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    prompt = CUSTOM_ANALYSIS_PROMPT.format(user_prompt=request.prompt)
    full_prompt = f"{prompt}\n\nDocument filename: {row['filename']}\n\nDocument content:\n{row['content']}"

    result = call_deepseek(full_prompt, ANALYSIS_SYSTEM_PROMPT, max_tokens=1000, temperature=0.3)

    if not result["success"]:
        raise HTTPException(status_code=500, detail="Failed to analyze document")

    parsed = parse_json_response(result["content"])

    return {
        "document_id": doc_id,
        "filename": row["filename"],
        "user_prompt": request.prompt,
        "analysis": parsed.get("analysis") if parsed else result["content"],
    }


@app.post("/api/webhook")
async def webhook_receive(request: Request):
    payload = await parse_webhook_payload(request)

    filename = payload.get("filename", "webhook-document")
    text = payload.get("text") or payload.get("content") or payload.get("body", "")

    if not text:
        raise HTTPException(status_code=400, detail="No document text provided in webhook payload")

    prompt = f"Document filename: {filename}\n\nDocument content:\n{text}"
    result = call_deepseek(prompt, ANALYSIS_SYSTEM_PROMPT, max_tokens=1000, temperature=0.3)

    summary = None
    key_points = None
    document_type = None
    status = "pending"

    if result["success"]:
        parsed = parse_json_response(result["content"])
        if parsed:
            summary = parsed.get("summary")
            key_points = json.dumps(parsed.get("key_points", []))
            document_type = parsed.get("document_type")
            status = "completed"
        else:
            status = "analysis_failed"
    else:
        status = "analysis_failed"

    row = execute_query(
        """INSERT INTO documents (filename, content, summary, key_points, document_type, status)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING id, created_at""",
        (filename, text, summary, key_points, document_type, status),
        fetch_one=True,
    )

    response_data = {
        "id": row["id"],
        "filename": filename,
        "summary": summary,
        "key_points": json.loads(key_points) if key_points else [],
        "document_type": document_type,
        "status": status,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }

    return format_webhook_response(response_data)
