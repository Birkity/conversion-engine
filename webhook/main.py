import base64
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Resend uses Svix: whsec_<base64-secret>
_RESEND_RAW = os.getenv("RESEND_WEBHOOK_SECRET", "")
RESEND_WEBHOOK_SECRET_BYTES = (
    base64.b64decode(_RESEND_RAW.removeprefix("whsec_")) if _RESEND_RAW else b""
)
CALCOM_WEBHOOK_SECRET = os.getenv("CALCOM_WEBHOOK_SECRET", "")
HUBSPOT_CLIENT_SECRET = os.getenv("HUBSPOT_CLIENT_SECRET", "")

app = FastAPI(title="Conversion Engine Webhook Hub", version="0.1.0")


def _svix_verify(secret_bytes: bytes, msg_id: str, timestamp: str, body: bytes, sig_header: str) -> bool:
    signed = f"{msg_id}.{timestamp}.{body.decode()}".encode()
    mac = hmac.new(secret_bytes, signed, hashlib.sha256)
    expected = base64.b64encode(mac.digest()).decode()
    return any(
        part.split(",", 1)[-1] == expected
        for part in sig_header.split(" ")
        if part.startswith("v1,")
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "conversion-engine-webhook",
        "ts": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/webhooks/resend")
async def resend_webhook(request: Request):
    """Resend email events via Svix-signed webhook."""
    body = await request.body()

    sig = request.headers.get("svix-signature", "")
    if RESEND_WEBHOOK_SECRET_BYTES and sig:
        msg_id = request.headers.get("svix-id", "")
        msg_ts = request.headers.get("svix-timestamp", "")
        if not _svix_verify(RESEND_WEBHOOK_SECRET_BYTES, msg_id, msg_ts, body, sig):
            log.warning("resend svix signature mismatch — processing anyway in dev mode")

    payload = json.loads(body) if body else {}
    event_type = payload.get("type", "unknown")
    email_id = payload.get("data", {}).get("email_id", "")
    log.info("resend event=%s email_id=%s", event_type, email_id)

    return JSONResponse({"received": True, "type": event_type}, status_code=202)


@app.post("/webhooks/africastalking")
async def at_webhook(request: Request):
    """Africa's Talking delivery reports (form-encoded) and inbound SMS (JSON)."""
    content_type = request.headers.get("content-type", "")

    if "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        data = dict(form)
        log.info("at delivery_report id=%s status=%s", data.get("id"), data.get("status"))
    else:
        body = await request.body()
        data = json.loads(body) if body else {}
        sms = data.get("data", {})
        log.info(
            "at inbound from=%s text=%r",
            sms.get("Message", {}).get("From"),
            sms.get("Message", {}).get("Text", "")[:80],
        )

    return JSONResponse({"received": True}, status_code=200)


@app.post("/webhooks/cal")
async def cal_webhook(request: Request):
    """Cal.com booking events: BOOKING_CREATED, BOOKING_CANCELLED, BOOKING_RESCHEDULED."""
    body = await request.body()

    sig = request.headers.get("X-Cal-Signature-256", "")
    if CALCOM_WEBHOOK_SECRET and sig:
        expected = hmac.new(
            CALCOM_WEBHOOK_SECRET.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            log.warning("calcom signature mismatch — processing anyway in dev mode")

    payload = json.loads(body) if body else {}
    trigger = payload.get("triggerEvent", "unknown")
    attendee = payload.get("payload", {}).get("attendees", [{}])[0].get("email", "")
    log.info("calcom event=%s attendee=%s", trigger, attendee)

    return JSONResponse({"received": True, "triggerEvent": trigger}, status_code=200)


@app.post("/webhooks/hubspot")
async def hubspot_webhook(request: Request):
    """HubSpot CRM subscription events (JSON array)."""
    body = await request.body()

    sig = request.headers.get("X-HubSpot-Signature", "")
    if HUBSPOT_CLIENT_SECRET and sig:
        source = HUBSPOT_CLIENT_SECRET + body.decode()
        expected = hashlib.sha256(source.encode()).hexdigest()
        if not hmac.compare_digest(sig, expected):
            log.warning("hubspot signature mismatch — processing anyway in dev mode")

    events = json.loads(body) if body else []
    if not isinstance(events, list):
        events = [events]
    for ev in events:
        log.info(
            "hubspot event=%s objectId=%s",
            ev.get("subscriptionType"),
            ev.get("objectId"),
        )

    return JSONResponse({"received": True, "count": len(events)}, status_code=200)
