import os
from typing import List, Optional

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

_client = None


def is_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def get_client():
    """Lazy Supabase client (service role). Returns None if not configured."""
    global _client
    if not is_configured():
        return None
    if _client is None:
        from supabase import create_client

        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _client


def get_messages(session_id: str, limit: int = 20) -> Optional[List[dict]]:
    """Return conversation history for a session.
    Returns None when Supabase is not configured (caller should fall back)."""
    client = get_client()
    if client is None:
        return None
    try:
        res = (
            client.table("chatbot_messages")
            .select("role,content")
            .eq("session_id", session_id)
            .order("created_at")
            .limit(limit)
            .execute()
        )
        return [{"role": r["role"], "content": r["content"]} for r in res.data]
    except Exception:
        return []


def append_message(session_id: str, role: str, content: str) -> bool:
    client = get_client()
    if client is None:
        return False
    try:
        client.table("chatbot_messages").insert(
            {"session_id": session_id, "role": role, "content": content}
        ).execute()
        return True
    except Exception:
        return False
