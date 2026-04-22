"""
SMS handler via Africa's Talking SDK.
Outbound routed to sink when LIVE_OUTBOUND_ENABLED=false.
"""
import os

import africastalking
from dotenv import load_dotenv

load_dotenv()

AT_USERNAME = os.getenv("AT_USERNAME", "sandbox")
AT_API_KEY = os.getenv("AT_API_KEY", "")
AT_SHORTCODE = os.getenv("AT_SHORTCODE", "")

KILL_SWITCH = os.getenv("LIVE_OUTBOUND_ENABLED", "false").lower() == "true"
SINK_PHONE = os.getenv("AT_SMOKE_TEST_PHONE", "")

africastalking.initialize(AT_USERNAME, AT_API_KEY)
_sms = africastalking.SMS


def send(to: str, message: str) -> dict:
    """
    Send SMS. Routes to SINK_PHONE when LIVE_OUTBOUND_ENABLED=false.
    Returns AT response dict.
    """
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
    """Send a signal-grounded nurture SMS."""
    msg = (
        f"Hi {prospect_name}, saw {company} is scaling engineering. "
        f"{pitch_angle[:80]} — Tenacious can help. Reply to connect."
    )
    return send(to, msg)
