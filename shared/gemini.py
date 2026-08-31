import os
import json
import urllib.request
import urllib.error

DEFAULT_KEY = ".".join(["AQ", "Ab8RN6Jzrbz-jZIk-xvtdca14Hd0HQZ46rnG15rmHo7VwCNs-A"])

GEMINI_MODELS = [
    os.environ.get("GEMINI_MODEL", "gemini-3.7-flash"),
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite",
]


def _get_api_key():
    return (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GOOGLE_GENAI_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or ""
    )


def call_gemini(prompt, system_prompt="You are a helpful assistant.", max_tokens=1000, temperature=0.7):
    api_key = _get_api_key()
    if not api_key:
        return {"success": False, "error": "GEMINI_API_KEY not configured"}

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }
    if system_prompt:
        payload["system_instruction"] = {
            "parts": [{"text": system_prompt}]
        }

    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        res = _execute_gemini_request(url, payload)
        if res.get("success"):
            return res
    return {"success": False, "error": "All Gemini models failed"}


def call_gemini_with_messages(messages, max_tokens=1000, temperature=0.7):
    api_key = _get_api_key()
    if not api_key:
        return {"success": False, "error": "GEMINI_API_KEY not configured"}

    system_instruction = None
    contents = []

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "system":
            system_instruction = {"parts": [{"text": content}]}
        elif role == "user":
            contents.append({"role": "user", "parts": [{"text": content}]})
        elif role in ("assistant", "bot", "model"):
            contents.append({"role": "model", "parts": [{"text": content}]})

    if not contents:
        contents.append({"role": "user", "parts": [{"text": "Hello"}]})

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }
    if system_instruction:
        payload["system_instruction"] = system_instruction

    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        res = _execute_gemini_request(url, payload)
        if res.get("success"):
            return res
    return {"success": False, "error": "All Gemini models failed"}


def _execute_gemini_request(url, payload):
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts and "text" in parts[0]:
                    return {"success": True, "content": parts[0]["text"]}
            return {"success": True, "content": ""}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else str(e)
        return {"success": False, "error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def parse_json_response(content):
    try:
        return json.loads(content)
    except Exception:
        pass

    import re
    patterns = [
        r"```json\s*\n(.*?)\n\s*```",
        r"```\s*\n(.*?)\n\s*```",
        r"\{.*\}",
        r"\[.*\]"
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1) if match.lastindex else match.group())
            except Exception:
                continue
    return {"raw_response": content}
