import json
import hmac
import hashlib
import os

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")


def verify_webhook_signature(payload, signature):
    if not WEBHOOK_SECRET:
        return True
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature or "")


def parse_webhook_payload(body, source="auto"):
    try:
        data = json.loads(body) if isinstance(body, str) else body
    except json.JSONDecodeError:
        return None, "Invalid JSON payload"

    if source == "auto":
        if "event" in data and "data" in data:
            source = "n8n"
        elif "hook" in data and "data" in data:
            source = "zapier"
        elif "trigger" in data:
            source = "make"
        else:
            source = "generic"

    normalized = {
        "source": source,
        "event": data.get("event", data.get("trigger", "unknown")),
        "data": data.get("data", data),
        "metadata": data.get("metadata", {}),
        "raw": data
    }

    return normalized, None


def format_webhook_response(data, status="success"):
    return {
        "status": status,
        "received": True,
        "data": data
    }
