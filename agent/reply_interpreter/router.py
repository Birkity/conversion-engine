"""
Act III -- Reply Router.

Takes the decision from interpret_reply() and executes the appropriate action:
  SEND_CAL_LINK     -> send Cal.com booking link via email
  SEND_EMAIL        -> send a grounded clarification email
  ASK_CLARIFICATION -> send a gentle follow-up email
  STOP              -> update HubSpot status, no further contact

All actions respect the data handling policy:
  Rule 2: synthetic prospects only during challenge week
  Rule 4: kill switch routes outbound to staff sink
  Rule 5: all Tenacious-branded content marked 'draft'
  Rule 6: X-Tenacious-Status header on every email
"""

import json
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)


def route_decision(
    decision: dict,
    prospect_info: dict,
    briefs: dict,
    last_email: dict | None = None,
) -> dict:
    """
    Execute the action recommended by interpret_reply().

    Args:
        decision:     Output from interpret_reply() with intent, next_step, etc.
        prospect_info: Dict with name, role, company, email, phone.
        briefs:       Dict with hiring_signal_brief and competitor_gap_brief.
        last_email:   Dict with subject and body of what we last sent.

    Returns:
        dict with action_taken, details, and any errors.
    """
    intent = decision.get("intent", "UNKNOWN")
    next_step = decision.get("next_step", "ASK_CLARIFICATION")
    confidence = decision.get("confidence", 0)
    reasoning = decision.get("reasoning", "")
    grounding = decision.get("grounding_facts_used", [])

    prospect_email = prospect_info.get("email", "")
    company = prospect_info.get("company", "")
    hsb = briefs.get("hiring_signal_brief", {})

    result = {
        "intent": intent,
        "next_step": next_step,
        "confidence": confidence,
        "actions": [],
        "errors": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # ── 1. Update HubSpot with the decision ─────────────────────────
    _hubspot_log(result, prospect_info, decision)

    # ── 2. Execute the next_step action ──────────────────────────────
    if next_step == "SEND_CAL_LINK":
        _action_send_cal_link(result, prospect_info, hsb, briefs=briefs, reasoning=reasoning, grounding=grounding)

    elif next_step == "SEND_EMAIL":
        _action_send_clarification(result, prospect_info, briefs, reasoning, grounding)

    elif next_step == "ASK_CLARIFICATION":
        _action_ask_clarification(result, prospect_info, briefs)

    elif next_step == "STOP":
        _action_stop(result, prospect_info)

    return result


# ─────────────────────────────────────────────────────────────────────
# HubSpot logging (every decision gets recorded)
# ─────────────────────────────────────────────────────────────────────

def _hubspot_log(result: dict, prospect_info: dict, decision: dict) -> None:
    """Log the reply interpretation to HubSpot as a note + status update."""
    try:
        from agent.hubspot.client import search_contact, update_contact, add_note

        email = prospect_info.get("email", "")
        phone = prospect_info.get("phone", "")

        contact_id = None
        if email:
            contact_id = search_contact("email", email)
        if not contact_id and phone:
            contact_id = search_contact("phone", phone)

        if not contact_id:
            log.warning("reply_router: no HubSpot contact found for %s", email or phone)
            result["actions"].append("hubspot_lookup: no contact found")
            return

        # Add decision note
        note_body = (
            f"Act III Reply Interpretation\n"
            f"Intent: {decision.get('intent')} (confidence: {decision.get('confidence')})\n"
            f"Next step: {decision.get('next_step')}\n"
            f"Reasoning: {decision.get('reasoning', '')}\n"
            f"Grounding: {', '.join(decision.get('grounding_facts_used', []))}"
        )
        add_note(contact_id, note_body)
        result["actions"].append(f"hubspot_note_added: contact_id={contact_id}")

        # Update lead status based on intent
        intent = decision.get("intent", "UNKNOWN")
        status_map = {
            "INTERESTED": "IN_PROGRESS",
            "SCHEDULE": "IN_PROGRESS",
            "QUESTION": "IN_PROGRESS",
            "NOT_INTERESTED": "UNQUALIFIED",
            "UNKNOWN": "OPEN",
        }
        new_status = status_map.get(intent, "OPEN")
        update_contact(contact_id, {"hs_lead_status": new_status})
        result["actions"].append(f"hubspot_status_updated: {new_status}")

    except Exception as exc:
        log.error("reply_router hubspot logging failed: %s", exc)
        result["errors"].append(f"hubspot_log: {exc}")


# ─────────────────────────────────────────────────────────────────────
# Action: SEND_CAL_LINK
# ─────────────────────────────────────────────────────────────────────

def _action_send_cal_link(result: dict, prospect_info: dict, hsb: dict, briefs: dict | None = None, reasoning: str = "", grounding: list | None = None) -> None:
    """Send a Cal.com booking link to the prospect.

    If the bench is unavailable for this prospect's required stack, downgrade
    to an honest SEND_EMAIL rather than booking a meeting we cannot staff.
    """
    bench_match = hsb.get("bench_match", {})
    if not bench_match.get("bench_available", True):
        log.info(
            "reply_router: bench_available=false for %s — downgrading SEND_CAL_LINK to SEND_EMAIL",
            prospect_info.get("company", ""),
        )
        result["actions"].append("bench_guard: bench unavailable — downgraded to SEND_EMAIL")
        _action_send_clarification(
            result,
            prospect_info,
            briefs or {"hiring_signal_brief": hsb},
            reasoning,
            grounding or [],
            bench_constrained=True,
        )
        return

    try:
        from agent.calendar.client import booking_link
        from agent.email.handler import send

        email = prospect_info.get("email", "")
        name = prospect_info.get("name", "")
        pitch = hsb.get("recommended_pitch_angle", "engineering scaling discussion")

        cal_url = booking_link(
            prospect_name=name,
            prospect_email=email,
            notes=pitch[:200],
        )

        subject = f"Re: Booking link - {prospect_info.get('company', '')}"
        body = (
            f"{name},\n\n"
            f"Great to hear from you. Here is a link to book a time:\n\n"
            f"{cal_url}\n\n"
            f"Pick any slot that works -- looking forward to the conversation.\n\n"
            f"Birkity\n"
            f"Research Partner, Tenacious Intelligence Corporation\n"
            f"gettenacious.com"
        )

        send_result = send(to=email, subject=subject, body=body)
        result["actions"].append(f"cal_link_sent: {send_result.get('status')}")
        result["cal_link"] = cal_url

    except Exception as exc:
        log.error("reply_router send_cal_link failed: %s", exc)
        result["errors"].append(f"send_cal_link: {exc}")


# ─────────────────────────────────────────────────────────────────────
# Action: SEND_EMAIL (clarification grounded in briefs)
# ─────────────────────────────────────────────────────────────────────

def _action_send_clarification(
    result: dict, prospect_info: dict, briefs: dict,
    reasoning: str, grounding: list,
    bench_constrained: bool = False,
) -> None:
    """Send a clarification email grounded in the briefs."""
    try:
        from agent.email.handler import send

        email = prospect_info.get("email", "")
        name = prospect_info.get("name", "")
        company = prospect_info.get("company", "")
        hsb = briefs.get("hiring_signal_brief", {})
        pitch = hsb.get("recommended_pitch_angle", "")

        subject = f"Re: More context on Tenacious - {company}"
        body = (
            f"{name},\n\n"
            f"Good question. Tenacious Intelligence Corporation provides "
            f"managed engineering teams and project-based consulting for "
            f"technology companies.\n\n"
            f"Based on our research, {company} "
        )

        # Ground the response in actual brief facts
        if grounding and len(grounding) > 0:
            body += f"recently {grounding[0].lower()}. "

        if bench_constrained:
            body += (
                f"\n\nI want to be upfront: our NestJS engineers are currently "
                f"committed through Q3 2026, so I cannot promise NestJS capacity "
                f"right now. We do have Python, ML, and Data engineers available. "
                f"Would it be worth a conversation about what that coverage could "
                f"solve for {company}?\n\n"
            )
        else:
            body += f"{pitch}\n\nWhat would be most useful to dig into first?\n\n"

        body += (
            f"Birkity\n"
            f"Research Partner, Tenacious Intelligence Corporation\n"
            f"gettenacious.com"
        )

        send_result = send(to=email, subject=subject, body=body)
        result["actions"].append(f"clarification_sent: {send_result.get('status')}")

    except Exception as exc:
        log.error("reply_router send_clarification failed: %s", exc)
        result["errors"].append(f"send_clarification: {exc}")


# ─────────────────────────────────────────────────────────────────────
# Action: ASK_CLARIFICATION
# ─────────────────────────────────────────────────────────────────────

def _action_ask_clarification(result: dict, prospect_info: dict, briefs: dict) -> None:
    """Send a gentle follow-up when intent is ambiguous."""
    try:
        from agent.email.handler import send

        email = prospect_info.get("email", "")
        name = prospect_info.get("name", "")
        company = prospect_info.get("company", "")

        subject = f"Re: Quick clarification - {company}"
        body = (
            f"{name},\n\n"
            f"Thanks for the reply. I want to make sure I understand correctly -- "
            f"would it be helpful if I shared more about what Tenacious does "
            f"for companies like {company}, or would you prefer I follow up "
            f"at a different time?\n\n"
            f"Either way, no pressure.\n\n"
            f"Birkity\n"
            f"Research Partner, Tenacious Intelligence Corporation\n"
            f"gettenacious.com"
        )

        send_result = send(to=email, subject=subject, body=body)
        result["actions"].append(f"clarification_asked: {send_result.get('status')}")

    except Exception as exc:
        log.error("reply_router ask_clarification failed: %s", exc)
        result["errors"].append(f"ask_clarification: {exc}")


# ─────────────────────────────────────────────────────────────────────
# Action: STOP
# ─────────────────────────────────────────────────────────────────────

def _action_stop(result: dict, prospect_info: dict) -> None:
    """Mark the prospect as unqualified. No further outbound."""
    result["actions"].append("outreach_stopped: prospect not interested")
    log.info(
        "reply_router STOP: no further outreach to %s (%s)",
        prospect_info.get("name", ""),
        prospect_info.get("email", ""),
    )
