# Forwarding wrapper for backward compatibility - powered by Google Gemini
from shared.gemini import (
    call_gemini as call_deepseek,
    call_gemini_with_messages as call_deepseek_with_messages,
    parse_json_response,
)

__all__ = ["call_deepseek", "call_deepseek_with_messages", "parse_json_response"]
