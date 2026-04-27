import base64
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


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

    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return JSONResponse({"error": "malformed JSON"}, status_code=400)

    event_type = payload.get("type", "unknown")
    email_id = payload.get("data", {}).get("email_id", "")
    log.info("resend event=%s email_id=%s", event_type, email_id)

    from agent.email.handler import on_email_reply
    on_email_reply(email_id, event_type)

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
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return JSONResponse({"error": "malformed JSON"}, status_code=400)
        sms = data.get("data", {})
        msg = sms.get("Message", {})
        from_number = msg.get("From", "")
        text = msg.get("Text", "")
        log.info("at inbound from=%s text=%r", from_number, text[:80])

        from agent.sms.handler import on_sms_reply
        on_sms_reply(from_number, text)

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

    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return JSONResponse({"error": "malformed JSON"}, status_code=400)

    trigger = payload.get("triggerEvent", "unknown")
    booking = payload.get("payload", {})
    attendees = booking.get("attendees", [{}])
    attendee = attendees[0] if attendees else {}
    attendee_email = attendee.get("email", "")
    attendee_name = attendee.get("name", "")
    log.info("calcom event=%s attendee=%s", trigger, attendee_email)

    if trigger == "BOOKING_CREATED" and attendee_email:
        name_parts = attendee_name.split(" ", 1)
        first = name_parts[0]
        last = name_parts[1] if len(name_parts) > 1 else ""
        company = booking.get("organizer", {}).get("name", "")
        try:
            from agent.hubspot.client import upsert_contact
            result = upsert_contact(
                email=attendee_email,
                first_name=first,
                last_name=last,
                company=company,
            )
            log.info("hubspot upsert email=%s status=%s", attendee_email, result.get("status"))

            # Add booking context note + move status to in-progress.
            from agent.hubspot.client import search_contact, add_note, update_contact

            contact_id = search_contact("email", attendee_email)
            if contact_id:
                start_time = booking.get("startTime", "not specified")
                title = booking.get("title", "Discovery call")
                meeting_url = (booking.get("metadata") or {}).get("videoCallUrl", "")

                note_lines = [
                    "Cal.com BOOKING_CREATED",
                    f"Title: {title}",
                    f"Time: {start_time}",
                    f"Attendee: {attendee_name} ({attendee_email})",
                ]
                if meeting_url:
                    note_lines.append(f"Video link: {meeting_url}")

                add_note(contact_id, "\n".join(note_lines))
                update_contact(contact_id, {"hs_lead_status": "IN_PROGRESS"})
                log.info("hubspot booking note + status update contact_id=%s", contact_id)
        except Exception as exc:
            log.error("hubspot upsert failed: %s", exc)

    elif trigger in ("BOOKING_CANCELLED", "BOOKING_RESCHEDULED") and attendee_email:
        try:
            from agent.hubspot.client import search_contact, update_contact, add_note
            contact_id = search_contact("email", attendee_email)
            if contact_id:
                start_time = booking.get("startTime", "")
                note = f"Cal.com {trigger}: {attendee_name} ({attendee_email})"
                if start_time:
                    note += f"\nTime: {start_time}"
                add_note(contact_id, note)
                if trigger == "BOOKING_CANCELLED":
                    update_contact(contact_id, {"hs_lead_status": "OPEN"})
                log.info("hubspot cal event=%s contact_id=%s", trigger, contact_id)
            else:
                log.warning("cal event=%s no hubspot contact for email=%s", trigger, attendee_email)
        except Exception as exc:
            log.error("hubspot cal event routing failed: %s", exc)

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

    try:
        events = json.loads(body) if body else []
    except json.JSONDecodeError:
        return JSONResponse({"error": "malformed JSON"}, status_code=400)
    if not isinstance(events, list):
        events = [events]
    for ev in events:
        log.info(
            "hubspot event=%s objectId=%s",
            ev.get("subscriptionType"),
            ev.get("objectId"),
        )

    return JSONResponse({"received": True, "count": len(events)}, status_code=200)


# ─────────────────────────────────────────────────────────────────
# Pipeline API — used by the Next.js frontend
# ─────────────────────────────────────────────────────────────────

@app.post("/api/pipeline/run")
async def pipeline_run(request: Request):
    """Start the pipeline for a company: generate + send outbound email."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "malformed JSON"}, status_code=400)

    slug = (body.get("slug") or "").strip().lower()
    if not slug:
        return JSONResponse({"error": "slug is required"}, status_code=422)

    try:
        from agent.conversation_manager import start_pipeline
        state = start_pipeline(slug)
        return JSONResponse(state, status_code=200)
    except ValueError as exc:
        log.warning("pipeline_run policy/validation error slug=%s: %s", slug, exc)
        return JSONResponse({"error": str(exc)}, status_code=422)
    except Exception as exc:
        log.error("pipeline_run failed slug=%s: %s", slug, exc)
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/conversations/reply")
async def conversations_reply(request: Request):
    """
    Handle a prospect reply — interpret intent and execute routing action.

    Body: {"contact_email": str, "channel": "email"|"sms", "body": str}

    Compatible with the curl command:
      curl -X POST http://localhost:8000/conversations/reply \\
        -H "Content-Type: application/json" \\
        -d '{"contact_email":"...","channel":"email","body":"..."}'
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "malformed JSON"}, status_code=400)

    contact_email = (payload.get("contact_email") or "").strip()
    channel = (payload.get("channel") or "email").strip().lower()
    reply_body = (payload.get("body") or "").strip()

    if not contact_email:
        return JSONResponse({"error": "contact_email is required"}, status_code=422)
    if not reply_body:
        return JSONResponse({"error": "body is required"}, status_code=422)
    if channel not in ("email", "sms"):
        return JSONResponse({"error": "channel must be 'email' or 'sms'"}, status_code=422)

    try:
        from agent.conversation_manager import slug_from_email, handle_reply
        slug = slug_from_email(contact_email)
        if not slug:
            return JSONResponse(
                {"error": f"No pipeline found for contact_email={contact_email!r}. "
                          "Ensure the pipeline has been started first."},
                status_code=404,
            )
        state = handle_reply(slug=slug, reply_text=reply_body, channel=channel)
        return JSONResponse(state, status_code=200)
    except ValueError as exc:
        log.warning("conversations_reply validation error: %s", exc)
        return JSONResponse({"error": str(exc)}, status_code=422)
    except Exception as exc:
        log.error("conversations_reply failed: %s", exc)
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/api/conversations/{slug}")
async def get_conversation(slug: str):
    """Return current conversation state for a company slug."""
    try:
        from agent.conversation_manager import get_state
        state = get_state(slug.lower())
        return JSONResponse(state, status_code=200)
    except Exception as exc:
        log.error("get_conversation failed slug=%s: %s", slug, exc)
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/api/pipeline/reset/{slug}")
async def pipeline_reset(slug: str):
    """Delete conversation state to reset the pipeline to idle."""
    try:
        from agent.conversation_manager import reset_pipeline
        reset_pipeline(slug.lower())
        return JSONResponse({"reset": True, "slug": slug.lower()}, status_code=200)
    except Exception as exc:
        log.error("pipeline_reset failed slug=%s: %s", slug, exc)
        return JSONResponse({"error": str(exc)}, status_code=500)
