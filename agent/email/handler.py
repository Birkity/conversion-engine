"""
Outbound email handler via Resend SMTP relay.
Uses SMTP (not REST) — Resend REST is Cloudflare-blocked from ET.
"""
import os
import smtplib
import ssl
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("RESEND_SMTP_HOST", "smtp.resend.com")
SMTP_PORT = int(os.getenv("RESEND_SMTP_PORT", "587"))
SMTP_USER = "resend"
SMTP_PASS = os.getenv("RESEND_API_KEY", "")
FROM_ADDR = os.getenv("RESEND_FROM", "onboarding@resend.dev")

KILL_SWITCH = os.getenv("LIVE_OUTBOUND_ENABLED", "false").lower() == "true"
SINK_ADDRESS = os.getenv("OUTBOUND_SINK_EMAIL", "birkity.yishak.m@gmail.com")


def send(to: str, subject: str, body: str, html: bool = False) -> dict:
    """
    Send an email. Routes to SINK_ADDRESS when LIVE_OUTBOUND_ENABLED=false.
    Returns dict with status and delivery metadata.
    """
    actual_to = to if KILL_SWITCH else SINK_ADDRESS
    content_type = "html" if html else "plain"
    msg = MIMEText(body, content_type)
    msg["Subject"] = subject if KILL_SWITCH else f"[SINK TEST → {to}] {subject}"
    msg["From"] = FROM_ADDR
    msg["To"] = actual_to

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(FROM_ADDR, actual_to, msg.as_string())
        return {"status": "sent", "to": actual_to, "sink_mode": not KILL_SWITCH}
    except Exception as exc:
        return {"status": "error", "error": str(exc), "to": actual_to}


def send_signal_brief_intro(
    to: str,
    prospect_name: str,
    company: str,
    hiring_brief: dict,
    gap_brief: dict,
) -> dict:
    """Send a signal-grounded intro email using the hiring + gap briefs."""
    ai_score = hiring_brief.get("ai_maturity_score", 0)
    pitch = hiring_brief.get("recommended_pitch_angle", "")
    velocity = hiring_brief.get("hiring_velocity", {}).get("observation", "")
    gap = (gap_brief.get("gaps") or [{}])[0].get("gap_insight", "")

    subject = f"Engineering scaling signal — {company}"
    body = f"""Hi {prospect_name},

I came across {company} while researching engineering teams in your sector.

{velocity}

{gap}

{pitch} — that's where Tenacious can help.

Would a 20-minute call this week make sense?

Best,
Birkity
Tenacious Consulting and Outsourcing

---
[AI Maturity Score: {ai_score}/3 | Confidence: {hiring_brief.get('confidence', 'N/A')}]
[LIVE_OUTBOUND_ENABLED={KILL_SWITCH} — {'live send' if KILL_SWITCH else 'routed to sink'}]
"""
    return send(to, subject, body)
