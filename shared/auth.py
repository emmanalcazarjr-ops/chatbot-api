import os
import hashlib
import secrets

API_KEY = os.environ.get("API_KEY", "rush-key-2026")
EXPECTED_HASH = hashlib.sha256(API_KEY.encode()).hexdigest()


def validate_api_key(authorization_header):
    if not authorization_header:
        return False, "Missing Authorization header"

    parts = authorization_header.split(" ")
    if len(parts) != 2 or parts[0] != "Bearer":
        return False, "Invalid Authorization format. Use: Bearer <key>"

    key = parts[1]
    key_hash = hashlib.sha256(key.encode()).hexdigest()

    if secrets.compare_digest(key_hash, EXPECTED_HASH):
        return True, None
    return False, "Invalid API key"


def generate_api_key():
    return f"rush-{secrets.token_hex(16)}"
