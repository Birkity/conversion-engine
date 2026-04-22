"""
Local webhook smoke test.
Hits all four endpoints against a local uvicorn instance.

Usage:
    # Terminal 1: start server
    uvicorn webhook.main:app --reload --port 8000

    # Terminal 2: run this script
    python scripts/webhook_smoketest.py
    python scripts/webhook_smoketest.py https://conversion-engine.onrender.com  # against Render
"""
import json
import sys
import urllib.request
import urllib.error

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")


def post(path: str, body: dict, headers: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, {}


def get(path: str) -> tuple[int, dict]:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=10) as resp:
        return resp.status, json.loads(resp.read())


def check(label: str, status: int, body: dict, expect_status: int = 200) -> bool:
    ok = status == expect_status
    marker = "✓" if ok else "✗"
    print(f"  {marker} {label}: HTTP {status} → {body}")
    return ok


results = []

print(f"\nWebhook smoke test -> {BASE_URL}\n")

# Health
s, b = get("/health")
results.append(check("GET /health", s, b, 200))

# Resend
s, b = post("/webhooks/resend", {"type": "email.delivered", "data": {"email_id": "test-123"}})
results.append(check("POST /webhooks/resend", s, b, 202))

# Africa's Talking inbound SMS
s, b = post(
    "/webhooks/africastalking",
    {"data": {"Message": {"From": "+2547XXXXXXXX", "Text": "Hello"}}},
)
results.append(check("POST /webhooks/africastalking (JSON)", s, b, 200))

# Cal.com booking
s, b = post(
    "/webhooks/cal",
    {
        "triggerEvent": "BOOKING_CREATED",
        "payload": {"attendees": [{"email": "prospect@example.com"}]},
    },
)
results.append(check("POST /webhooks/cal", s, b, 200))

# HubSpot
s, b = post(
    "/webhooks/hubspot",
    [{"subscriptionType": "contact.creation", "objectId": 12345}],
)
results.append(check("POST /webhooks/hubspot", s, b, 200))

passed = sum(results)
total = len(results)
print(f"\n{'All' if passed == total else passed}/{total} checks passed")
if passed < total:
    raise SystemExit(1)
