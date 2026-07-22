import os
import sys
import json
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException, Header, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from shared.auth import validate_api_key
from shared.database import execute_query, init_database
from shared.deepseek import call_deepseek, parse_json_response
from shared.rate_limit import check_rate_limit
from shared.webhooks import parse_webhook_payload, format_webhook_response

app = FastAPI(title="Business Report Generation API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REPORT_TYPES = {
    "weekly_summary": "Weekly activity and progress summary",
    "project_status": "Project progress and milestone report",
    "meeting_notes": "Structured meeting notes with action items",
    "client_pipeline": "Client and lead pipeline summary",
    "custom": "Custom report with user-defined prompt",
}

SYSTEM_PROMPTS = {
    "weekly_summary": "Generate a professional weekly summary report in markdown. Include: Key Activities, Achievements, Blockers/Challenges, Next Steps. Use bullet points and be concise.",
    "project_status": "Generate a project status report in markdown. Include: Overview, Completed Milestones, In Progress, Blockers, Timeline, Recommendations.",
    "meeting_notes": "Generate structured meeting notes in markdown. Include: Attendees, Agenda, Discussion Points, Decisions Made, Action Items with owners.",
    "client_pipeline": "Generate a client pipeline report in markdown. Include: Summary Stats, New Leads, Active Prospects, Conversions, Revenue Impact, Recommendations.",
    "custom": "Generate a report based on the user's instructions. Be professional and well-structured.",
}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500),
    report_type VARCHAR(100),
    input_data TEXT,
    generated_content TEXT,
    format VARCHAR(20) DEFAULT 'markdown',
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


class GenerateReportRequest(BaseModel):
    type: str
    data: dict
    title: Optional[str] = None
    format: Optional[str] = "markdown"


class CustomReportRequest(BaseModel):
    prompt: str
    data: dict
    title: Optional[str] = None


@app.on_event("startup")
async def startup():
    await init_database()
    await execute_query(CREATE_TABLE_SQL)


@app.get("/api")
async def root():
    return {
        "name": "Business Report Generation API",
        "version": "1.0.0",
        "description": "AI-powered business report generation using DeepSeek",
        "report_types": REPORT_TYPES,
        "endpoints": [
            {"method": "GET", "path": "/api", "description": "API info"},
            {"method": "GET", "path": "/api/health", "description": "Health check"},
            {"method": "POST", "path": "/api/reports", "description": "Generate a report"},
            {"method": "GET", "path": "/api/reports", "description": "List reports"},
            {"method": "GET", "path": "/api/reports/{id}", "description": "Get report by ID"},
            {"method": "POST", "path": "/api/reports/custom", "description": "Generate with custom prompt"},
            {"method": "POST", "path": "/api/webhook", "description": "Trigger report from external systems"},
        ],
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "report-api", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/reports")
async def generate_report(
    request: GenerateReportRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
):
    validate_api_key(x_api_key or authorization)
    check_rate_limit(x_api_key or authorization)

    if request.type not in REPORT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid report type. Valid types: {list(REPORT_TYPES.keys())}")

    title = request.title or f"{REPORT_TYPES[request.type]} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"

    result = await execute_query(
        "INSERT INTO reports (title, report_type, input_data, format, status) VALUES ($1, $2, $3, $4, 'generating') RETURNING id",
        title,
        request.type,
        json.dumps(request.data),
        request.format,
    )
    report_id = result[0]["id"]

    system_prompt = SYSTEM_PROMPTS[request.type]
    user_prompt = f"Report Type: {REPORT_TYPES[request.type]}\n\nData:\n{json.dumps(request.data, indent=2)}"

    ai_result = call_deepseek(user_prompt, system_prompt, max_tokens=2000, temperature=0.7)

    if ai_result["success"]:
        content = ai_result["content"]
        await execute_query(
            "UPDATE reports SET generated_content = $1, status = 'completed' WHERE id = $2",
            content,
            report_id,
        )
    else:
        content = f"Error generating report: {ai_result.get('error', 'Unknown error')}"
        await execute_query(
            "UPDATE reports SET generated_content = $1, status = 'failed' WHERE id = $2",
            content,
            report_id,
        )
        raise HTTPException(status_code=500, detail="Failed to generate report")

    return {
        "id": report_id,
        "title": title,
        "type": request.type,
        "format": request.format,
        "content": content,
        "status": "completed",
        "created_at": datetime.utcnow().isoformat(),
    }


@app.get("/api/reports")
async def list_reports(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
    type: Optional[str] = Query(None),
):
    validate_api_key(x_api_key or authorization)
    check_rate_limit(x_api_key or authorization)

    if type:
        rows = await execute_query(
            "SELECT id, title, report_type, format, status, created_at FROM reports WHERE report_type = $1 ORDER BY created_at DESC",
            type,
        )
    else:
        rows = await execute_query(
            "SELECT id, title, report_type, format, status, created_at FROM reports ORDER BY created_at DESC"
        )

    return {"reports": [dict(r) for r in rows], "count": len(rows)}


@app.get("/api/reports/{report_id}")
async def get_report(
    report_id: int,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
):
    validate_api_key(x_api_key or authorization)
    check_rate_limit(x_api_key or authorization)

    rows = await execute_query("SELECT * FROM reports WHERE id = $1", report_id)
    if not rows:
        raise HTTPException(status_code=404, detail="Report not found")

    return dict(rows[0])


@app.post("/api/reports/custom")
async def generate_custom_report(
    request: CustomReportRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
):
    validate_api_key(x_api_key or authorization)
    check_rate_limit(x_api_key or authorization)

    title = request.title or f"Custom Report - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"

    result = await execute_query(
        "INSERT INTO reports (title, report_type, input_data, format, status) VALUES ($1, 'custom', $2, 'markdown', 'generating') RETURNING id",
        title,
        json.dumps(request.data),
    )
    report_id = result[0]["id"]

    system_prompt = SYSTEM_PROMPTS["custom"]
    user_prompt = f"User Instructions: {request.prompt}\n\nData:\n{json.dumps(request.data, indent=2)}"

    ai_result = call_deepseek(user_prompt, system_prompt, max_tokens=2000, temperature=0.7)

    if ai_result["success"]:
        content = ai_result["content"]
        await execute_query(
            "UPDATE reports SET generated_content = $1, status = 'completed' WHERE id = $2",
            content,
            report_id,
        )
    else:
        content = f"Error generating report: {ai_result.get('error', 'Unknown error')}"
        await execute_query(
            "UPDATE reports SET generated_content = $1, status = 'failed' WHERE id = $2",
            content,
            report_id,
        )
        raise HTTPException(status_code=500, detail="Failed to generate custom report")

    return {
        "id": report_id,
        "title": title,
        "type": "custom",
        "format": "markdown",
        "content": content,
        "status": "completed",
        "created_at": datetime.utcnow().isoformat(),
    }


@app.post("/api/webhook")
async def webhook_trigger(request: Request):
    body = await request.body()
    payload = parse_webhook_payload(body)

    report_type = payload.get("type", "weekly_summary")
    data = payload.get("data", {})
    title = payload.get("title")

    if report_type not in REPORT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid report type. Valid types: {list(REPORT_TYPES.keys())}")

    title = title or f"{REPORT_TYPES[report_type]} (Webhook) - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"

    result = await execute_query(
        "INSERT INTO reports (title, report_type, input_data, format, status) VALUES ($1, $2, $3, 'markdown', 'generating') RETURNING id",
        title,
        report_type,
        json.dumps(data),
    )
    report_id = result[0]["id"]

    system_prompt = SYSTEM_PROMPTS[report_type]
    user_prompt = f"Report Type: {REPORT_TYPES[report_type]}\n\nData:\n{json.dumps(data, indent=2)}"

    ai_result = call_deepseek(user_prompt, system_prompt, max_tokens=2000, temperature=0.7)

    if ai_result["success"]:
        content = ai_result["content"]
        await execute_query(
            "UPDATE reports SET generated_content = $1, status = 'completed' WHERE id = $2",
            content,
            report_id,
        )
    else:
        content = f"Error generating report: {ai_result.get('error', 'Unknown error')}"
        await execute_query(
            "UPDATE reports SET generated_content = $1, status = 'failed' WHERE id = $2",
            content,
            report_id,
        )
        raise HTTPException(status_code=500, detail="Failed to generate report from webhook")

    return format_webhook_response(
        {
            "id": report_id,
            "title": title,
            "type": report_type,
            "status": "completed",
            "message": "Report generated successfully via webhook",
        }
    )
