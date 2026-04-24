"""
Outbound email handler via Resend SMTP relay.
Uses SMTP (not REST) — Resend REST is Cloudflare-blocked from ET.
"""
import logging
import os
import smtplib
import ssl
from email.mime.text import MIMEText

log = logging.getLogger(__name__)

from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("RESEND_SMTP_HOST", "smtp.resend.com")
SMTP_PORT = int(os.getenv("RESEND_SMTP_PORT", "587"))
SMTP_USER = "resend"
SMTP_PASS = os.getenv("RESEND_API_KEY", "")
FROM_ADDR = os.getenv("RESEND_FROM", "onboarding@resend.dev")

# OUTBOUND_ENABLED is True only when explicitly set in .env.
# Default is False — all mail routes to the sink (Rule 5).
OUTBOUND_ENABLED = (
    os.getenv("TENACIOUS_OUTBOUND_ENABLED", "false").lower() == "true"
    or os.getenv("LIVE_OUTBOUND_ENABLED", "false").lower() == "true"
)
# Legacy alias kept for callers that imported KILL_SWITCH by name.
# KILL_SWITCH=True means live mode ON (outbound enabled) — see OUTBOUND_ENABLED.
KILL_SWITCH = OUTBOUND_ENABLED

# OUTBOUND_SINK_EMAIL must be set in .env — no hardcoded default (Rule 4).
SINK_ADDRESS = os.getenv("OUTBOUND_SINK_EMAIL", "")


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

    # Rule 6: all Tenacious-branded outbound must carry the draft header
    msg["X-Tenacious-Status"] = "draft"

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


def on_email_reply(
    email_id: str,
    event_type: str,
    reply_text: str = "",
    last_email: dict | None = None,
    briefs: dict | None = None,
    prospect_info: dict | None = None,
) -> dict | None:
    """
    Downstream hook for inbound email events from Resend webhook.

    When reply_text + context are provided, runs Act III interpretation
    and routes the decision (send cal link, clarification, or stop).

    Args:
        email_id:     Resend email ID for the event.
        event_type:   Resend event type (e.g., 'email.delivered', 'email.replied').
        reply_text:   The prospect's reply body text (if available).
        last_email:   Dict with 'subject' and 'body' of what we sent.
        briefs:       Dict with 'hiring_signal_brief' and 'competitor_gap_brief'.
        prospect_info: Dict with 'name', 'role', 'company', 'email'.

    Returns:
        dict with interpretation + routing result, or None for non-reply events.
    """
    log.info("email_event id=%s type=%s", email_id, event_type)

    # Only process if we have reply text and context to interpret
    if not reply_text or not briefs or not prospect_info:
        log.info("email_event id=%s: no reply context, logging only", email_id)
        return None

    try:
        from agent.reply_interpreter import interpret_reply
        from agent.reply_interpreter.router import route_decision

        decision = interpret_reply(
            reply_text=reply_text,
            last_email=last_email or {"subject": "", "body": ""},
            briefs=briefs,
            prospect_info=prospect_info,
        )

        log.info(
            "reply_interpreted email_id=%s intent=%s confidence=%s next_step=%s",
            email_id, decision.get("intent"), decision.get("confidence"),
            decision.get("next_step"),
        )

        route_result = route_decision(
            decision=decision,
            prospect_info=prospect_info,
            briefs=briefs,
            last_email=last_email,
        )

        log.info(
            "reply_routed email_id=%s actions=%s errors=%s",
            email_id, route_result.get("actions"), route_result.get("errors"),
        )

        return {"decision": decision, "routing": route_result}

    except Exception as exc:
        log.error("reply interpretation failed for email_id=%s: %s", email_id, exc)
        return {"error": str(exc)}

