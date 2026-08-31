import os

# Must run before any test imports api.main / shared.supabase:
# both modules snapshot env at import time. Force the in-memory fallback
# and the "AI key missing" branch for deterministic offline tests.
for _var in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY"):
    os.environ.pop(_var, None)
