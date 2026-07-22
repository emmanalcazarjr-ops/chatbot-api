import os
import sys
from datetime import datetime, date, time, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from shared.auth import validate_api_key
from shared.database import execute_query, init_database
from shared.deepseek import call_deepseek
from shared.rate_limit import check_rate_limit
from shared.webhooks import parse_webhook_payload, format_webhook_response

app = FastAPI(title="Appointment Booking API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVICES = {
    "Technical Interview": 60,
    "Project Discussion": 30,
    "Consultation Call": 45,
    "Business Meeting": 60,
}

CONFIRMATION_SYSTEM_PROMPT = (
    "Generate a professional appointment confirmation message. "
    "Include: client name, service, date, time, duration. "
    "Be warm and professional. Keep it to 2-3 sentences."
)


class BookAppointmentRequest(BaseModel):
    client_name: str
    client_email: str
    service: str
    date: str
    time: str
    notes: Optional[str] = None


class UpdateAppointmentRequest(BaseModel):
    date: Optional[str] = None
    time: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


def create_tables():
    init_database("""
        CREATE TABLE IF NOT EXISTS appointments (
            id SERIAL PRIMARY KEY,
            client_name VARCHAR(200) NOT NULL,
            client_email VARCHAR(200) NOT NULL,
            service VARCHAR(200) NOT NULL,
            appointment_date DATE NOT NULL,
            appointment_time TIME NOT NULL,
            duration_minutes INTEGER DEFAULT 60,
            status VARCHAR(50) DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


@app.on_event("startup")
async def startup():
    create_tables()


@app.get("/api")
async def api_info():
    return {
        "name": "Appointment Booking API",
        "version": "1.0.0",
        "description": "Book and manage appointments with AI-powered confirmations",
        "services": list(SERVICES.keys()),
        "endpoints": [
            "GET /api",
            "GET /api/health",
            "POST /api/appointments",
            "GET /api/appointments",
            "GET /api/appointments/{id}",
            "PUT /api/appointments/{id}",
            "DELETE /api/appointments/{id}",
            "GET /api/availability",
            "POST /api/webhook",
        ],
    }


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "appointment-api", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/appointments")
async def book_appointment(
    request: BookAppointmentRequest,
    x_api_key: Optional[str] = Header(None),
):
    validate_api_key(x_api_key)
    check_rate_limit(x_api_key)

    if request.service not in SERVICES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service. Available services: {list(SERVICES.keys())}",
        )

    try:
        appointment_date = datetime.strptime(request.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    try:
        appointment_time = datetime.strptime(request.time, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM")

    duration = SERVICES[request.service]

    existing = execute_query(
        """SELECT id FROM appointments
           WHERE appointment_date = %s AND appointment_time = %s AND status != 'cancelled'""",
        (appointment_date, appointment_time),
    )
    if existing:
        raise HTTPException(status_code=409, detail="Time slot is already booked")

    result = execute_query(
        """INSERT INTO appointments (client_name, client_email, service, appointment_date, appointment_time, duration_minutes, status, notes)
           VALUES (%s, %s, %s, %s, %s, %s, 'confirmed', %s)
           RETURNING id, client_name, client_email, service, appointment_date, appointment_time, duration_minutes, status, notes, created_at""",
        (request.client_name, request.client_email, request.service, appointment_date, appointment_time, duration, request.notes),
    )
    appointment = result[0]

    prompt = (
        f"Client: {request.client_name}\n"
        f"Service: {request.service}\n"
        f"Date: {request.date}\n"
        f"Time: {request.time}\n"
        f"Duration: {duration} minutes"
    )
    ai_result = call_deepseek(prompt, CONFIRMATION_SYSTEM_PROMPT, max_tokens=200, temperature=0.7)
    confirmation = ai_result.get("content", f"Your {request.service} appointment on {request.date} at {request.time} has been confirmed.") if ai_result.get("success") else f"Your {request.service} appointment on {request.date} at {request.time} has been confirmed."

    return {
        "appointment": format_appointment(appointment),
        "confirmation_message": confirmation,
    }


@app.get("/api/appointments")
async def list_appointments(
    status: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    x_api_key: Optional[str] = Header(None),
):
    validate_api_key(x_api_key)
    check_rate_limit(x_api_key)

    query = "SELECT id, client_name, client_email, service, appointment_date, appointment_time, duration_minutes, status, notes, created_at FROM appointments WHERE 1=1"
    params = []

    if status:
        query += " AND status = %s"
        params.append(status)

    if date:
        try:
            filter_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        query += " AND appointment_date = %s"
        params.append(filter_date)

    query += " ORDER BY appointment_date ASC, appointment_time ASC"

    results = execute_query(query, tuple(params))
    return {"appointments": [format_appointment(r) for r in results], "total": len(results)}


@app.get("/api/appointments/{appointment_id}")
async def get_appointment(
    appointment_id: int,
    x_api_key: Optional[str] = Header(None),
):
    validate_api_key(x_api_key)
    check_rate_limit(x_api_key)

    result = execute_query(
        "SELECT id, client_name, client_email, service, appointment_date, appointment_time, duration_minutes, status, notes, created_at FROM appointments WHERE id = %s",
        (appointment_id,),
    )
    if not result:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return {"appointment": format_appointment(result[0])}


@app.put("/api/appointments/{appointment_id}")
async def update_appointment(
    appointment_id: int,
    request: UpdateAppointmentRequest,
    x_api_key: Optional[str] = Header(None),
):
    validate_api_key(x_api_key)
    check_rate_limit(x_api_key)

    existing = execute_query(
        "SELECT id, appointment_date, appointment_time, status FROM appointments WHERE id = %s",
        (appointment_id,),
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Appointment not found")

    updates = []
    params = []

    if request.date is not None:
        try:
            new_date = datetime.strptime(request.date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        updates.append("appointment_date = %s")
        params.append(new_date)

    if request.time is not None:
        try:
            new_time = datetime.strptime(request.time, "%H:%M").time()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM")
        updates.append("appointment_time = %s")
        params.append(new_time)

    if request.status is not None:
        updates.append("status = %s")
        params.append(request.status)

    if request.notes is not None:
        updates.append("notes = %s")
        params.append(request.notes)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    params.append(appointment_id)
    query = f"UPDATE appointments SET {', '.join(updates)} WHERE id = %s RETURNING id, client_name, client_email, service, appointment_date, appointment_time, duration_minutes, status, notes, created_at"
    result = execute_query(query, tuple(params))

    return {"appointment": format_appointment(result[0])}


@app.delete("/api/appointments/{appointment_id}")
async def cancel_appointment(
    appointment_id: int,
    x_api_key: Optional[str] = Header(None),
):
    validate_api_key(x_api_key)
    check_rate_limit(x_api_key)

    existing = execute_query("SELECT id FROM appointments WHERE id = %s", (appointment_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Appointment not found")

    result = execute_query(
        """UPDATE appointments SET status = 'cancelled'
           WHERE id = %s
           RETURNING id, client_name, client_email, service, appointment_date, appointment_time, duration_minutes, status, notes, created_at""",
        (appointment_id,),
    )

    return {"appointment": format_appointment(result[0]), "message": "Appointment cancelled"}


@app.get("/api/availability")
async def get_availability(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
):
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    booked = execute_query(
        "SELECT appointment_time, duration_minutes FROM appointments WHERE appointment_date = %s AND status != 'cancelled'",
        (target_date,),
    )

    booked_slots = set()
    for row in booked:
        start = datetime.combine(target_date, row["appointment_time"])
        for minute in range(0, row["duration_minutes"], 30):
            slot = (start + timedelta(minutes=minute)).time()
            booked_slots.add(slot)

    available = []
    current = datetime.combine(target_date, time(9, 0))
    end = datetime.combine(target_date, time(17, 0))

    while current < end:
        slot_time = current.time()
        if slot_time not in booked_slots:
            available.append(slot_time.strftime("%H:%M"))
        current += timedelta(minutes=30)

    return {"date": date, "available_slots": available, "total_available": len(available)}


@app.post("/api/webhook")
async def receive_webhook(
    payload: dict,
    x_api_key: Optional[str] = Header(None),
):
    validate_api_key(x_api_key)
    check_rate_limit(x_api_key)

    data = parse_webhook_payload(payload)

    client_name = data.get("client_name", "")
    client_email = data.get("client_email", "")
    service = data.get("service", "")
    appointment_date = data.get("date", "")
    appointment_time = data.get("time", "")
    notes = data.get("notes")

    if not all([client_name, client_email, service, appointment_date, appointment_time]):
        raise HTTPException(status_code=400, detail="Missing required fields: client_name, client_email, service, date, time")

    if service not in SERVICES:
        raise HTTPException(status_code=400, detail=f"Invalid service. Available: {list(SERVICES.keys())}")

    try:
        parsed_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    try:
        parsed_time = datetime.strptime(appointment_time, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM")

    duration = SERVICES[service]

    existing = execute_query(
        "SELECT id FROM appointments WHERE appointment_date = %s AND appointment_time = %s AND status != 'cancelled'",
        (parsed_date, parsed_time),
    )
    if existing:
        raise HTTPException(status_code=409, detail="Time slot is already booked")

    result = execute_query(
        """INSERT INTO appointments (client_name, client_email, service, appointment_date, appointment_time, duration_minutes, status, notes)
           VALUES (%s, %s, %s, %s, %s, %s, 'confirmed', %s)
           RETURNING id, client_name, client_email, service, appointment_date, appointment_time, duration_minutes, status, notes, created_at""",
        (client_name, client_email, service, parsed_date, parsed_time, duration, notes),
    )

    return format_webhook_response({"appointment": format_appointment(result[0]), "status": "booked"})


def format_appointment(row):
    return {
        "id": row["id"],
        "client_name": row["client_name"],
        "client_email": row["client_email"],
        "service": row["service"],
        "date": str(row["appointment_date"]),
        "time": str(row["appointment_time"])[:5],
        "duration_minutes": row["duration_minutes"],
        "status": row["status"],
        "notes": row["notes"],
        "created_at": str(row["created_at"]),
    }
