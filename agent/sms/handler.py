"""
SMS handler via Africa's Talking SDK.
Outbound routed to sink when LIVE_OUTBOUND_ENABLED=false.
SMS is a warm-lead-only channel: pass warm_lead=True for live sends.
"""
import logging
import os

import africastalking
from dotenv import load_dotenv

log = logging.getLogger(__name__)

load_dotenv()

AT_USERNAME = os.getenv("AT_USERNAME", "sandbox")
AT_API_KEY = os.getenv("AT_API_KEY", "")
AT_SHORTCODE = os.getenv("AT_SHORTCODE", "")

# OUTBOUND_ENABLED is True only when explicitly set in .env.
# Default is False — all SMS routes to the sink phone (Rule 5).
OUTBOUND_ENABLED = (
    os.getenv("TENACIOUS_OUTBOUND_ENABLED", "false").lower() == "true"
    or os.getenv("LIVE_OUTBOUND_ENABLED", "false").lower() == "true"
)
KILL_SWITCH = OUTBOUND_ENABLED  # legacy alias
SINK_PHONE = os.getenv("AT_SMOKE_TEST_PHONE", "")

africastalking.initialize(AT_USERNAME, AT_API_KEY)
_sms = africastalking.SMS


def send(to: str, message: str, warm_lead: bool = False) -> dict:
    """
    Send SMS. Routes to SINK_PHONE when LIVE_OUTBOUND_ENABLED=false.
    warm_lead=True required for live sends (SMS is warm-lead-only channel).
    Returns AT response dict.
    """
    if KILL_SWITCH and not warm_lead:
        log.warning("sms blocked — warm_lead=False; to=%s", to)
        return {"status": "skipped", "reason": "SMS requires warm_lead=True for live send"}

    actual_to = to if KILL_SWITCH else SINK_PHONE
    if not actual_to:
        return {"status": "skipped", "reason": "no sink phone configured; set AT_SMOKE_TEST_PHONE"}

    prefixed_msg = message if KILL_SWITCH else f"[SINK→{to}] {message}"
    sender = AT_SHORTCODE or None

    try:
        response = _sms.send(prefixed_msg, [actual_to], sender_id=sender)
        return {"status": "sent", "to": actual_to, "sink_mode": not KILL_SWITCH, "response": response}
    except Exception as exc:
        return {"status": "error", "error": str(exc), "to": actual_to}


def send_nurture_sms(to: str, prospect_name: str, company: str, pitch_angle: str) -> dict:
    """Send a signal-grounded nurture SMS to a confirmed warm lead."""
    msg = (
        f"Hi {prospect_name}, saw {company} is scaling engineering. "
        f"{pitch_angle[:80]} — Tenacious can help. Reply to connect."
    )
    return send(to, msg, warm_lead=True)


def on_sms_reply(from_number: str, text: str) -> None:
    """Route inbound SMS reply: log + update HubSpot lead status and add a note."""
    log.info("inbound_sms from=%s text=%r", from_number, text[:120])
    try:
        from agent.hubspot.client import search_contact, update_contact, add_note
        contact_id = search_contact("phone", from_number)
        if contact_id:
            update_contact(contact_id, {"hs_lead_status": "IN_PROGRESS"})
            add_note(contact_id, f"Inbound SMS reply from {from_number}:\n{text[:500]}")
            log.info("hubspot updated contact_id=%s status=IN_PROGRESS sms_reply", contact_id)

            # Alert consultant via email sink.
            try:
                from agent.email.handler import send as _send_email

                sink = os.getenv("OUTBOUND_SINK_EMAIL", "")
                if sink:
                    _send_email(
                        to=sink,
                        subject=f"[CONV-ENGINE] Inbound SMS reply from {from_number}",
                        body=(
                            "A prospect replied via SMS.\n\n"
                            f"From: {from_number}\n"
                            "Message:\n"
                            f"{text[:500]}"
                        ),
                    )
            except Exception as exc:
                log.error("failed to send inbound SMS consultant alert: %s", exc)
        else:
            log.warning("inbound_sms no hubspot contact matched phone=%s", from_number)
    except Exception as exc:
        log.error("hubspot sms reply routing failed: %s", exc)
