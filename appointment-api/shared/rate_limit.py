import time
from collections import defaultdict

request_counts = defaultdict(list)

RATE_LIMITS = {
    "default": {"requests": 100, "window": 3600},
    "chat": {"requests": 30, "window": 60},
    "webhook": {"requests": 500, "window": 3600}
}


def check_rate_limit(client_ip, limit_type="default"):
    config = RATE_LIMITS.get(limit_type, RATE_LIMITS["default"])
    max_requests = config["requests"]
    window = config["window"]

    now = time.time()
    key = f"{client_ip}:{limit_type}"

    request_counts[key] = [t for t in request_counts[key] if now - t < window]

    if len(request_counts[key]) >= max_requests:
        oldest = request_counts[key][0]
        retry_after = int(window - (now - oldest))
        return False, retry_after

    request_counts[key].append(now)
    return True, None
