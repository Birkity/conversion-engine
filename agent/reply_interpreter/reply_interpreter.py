"""
Act III — Reply Interpreter.

Pure reasoning module that interprets a prospect's reply and decides what
the system should do next.  Transport-independent: no webhooks, no email
sending, no CRM writes.  Returns a structured decision dict.

Usage:
    from agent.reply_interpreter import interpret_reply

    result = interpret_reply(
        reply_text="Sounds interesting, can you send times?",
        last_email={"subject": "Context: ...", "body": "..."},
        briefs={"hiring_signal_brief": {...}, "competitor_gap_brief": {...}},
        prospect_info={"name": "Jordan", "role": "CTO", "company": "Acme"},
    )
"""

import json
import logging
import os
import sys

sys.set_int_max_str_digits(0)

from dotenv import load_dotenv
from langfuse.openai import OpenAI

from .prompts import REPLY_INTERPRETER_SYSTEM_PROMPT, REPLY_INTERPRETER_USER_TEMPLATE

load_dotenv()

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPLY_MODEL = os.getenv(
    "REPLY_INTERPRETER_MODEL",
    os.getenv("BRIEF_GENERATOR_MODEL", "google/gemini-2.0-flash-001"),
)
REPLY_TEMPERATURE = float(os.getenv("REPLY_INTERPRETER_TEMPERATURE", "0.2"))

# ---------------------------------------------------------------------------
# Valid enumerations
# ---------------------------------------------------------------------------

VALID_INTENTS = {"INTERESTED", "NOT_INTERESTED", "QUESTION", "SCHEDULE", "UNKNOWN"}

VALID_NEXT_STEPS = {"SEND_EMAIL", "SEND_CAL_LINK", "ASK_CLARIFICATION", "STOP"}

# Deterministic mapping — enforced in Python regardless of LLM output
INTENT_TO_NEXT_STEP = {
    "INTERESTED": "SEND_CAL_LINK",
    "SCHEDULE": "SEND_CAL_LINK",
    "QUESTION": "SEND_EMAIL",
    "NOT_INTERESTED": "STOP",
    "UNKNOWN": "ASK_CLARIFICATION",
}

# ---------------------------------------------------------------------------
# LLM client (same pattern as brief_generator/llm_client.py)
# ---------------------------------------------------------------------------

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )
    return _client


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _safe_get(d: dict | None, *keys, default=""):
    """Walk a nested dict safely, returning *default* if any key is missing."""
    current = d or {}
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k, default)
        else:
            return default
    return current if current is not None else default


def _format_velocity(hsb: dict) -> str:
    v = hsb.get("hiring_velocity", {})
    if not v:
        return "No velocity data"
    direction = v.get("direction", "unknown")
    delta = v.get("delta_pct", "?")
    strength = v.get("signal_strength", "unknown")
    obs = v.get("observation", "")
    return f"{direction} ({delta}% delta, {strength} signal). {obs}"


def _format_budget(hsb: dict) -> str:
    b = hsb.get("budget_urgency", {})
    if not b:
        return "No budget data"
    level = b.get("level", "unknown")
    signal = b.get("signal", "none")
    return f"{level} — {signal}"


def _format_cost_pressure(hsb: dict) -> str:
    c = hsb.get("cost_pressure", {})
    if not c:
        return "No cost pressure data"
    present = c.get("present", False)
    signal = c.get("signal", "none")
    return f"Present={present}. {signal}" if signal else f"Present={present}"


def _format_gaps(cgb: dict) -> str:
    gaps = cgb.get("gaps", [])
    if not gaps:
        return "No gaps identified"
    lines = []
    for i, g in enumerate(gaps, 1):
        practice = g.get("practice", "unknown")
        insight = g.get("gap_insight", "")
        conf = g.get("confidence", 0)
        lines.append(f"  {i}. {practice} (confidence: {conf}): {insight}")
    return "\n".join(lines)


def _build_user_message(
    reply_text: str,
    last_email: dict,
    briefs: dict,
    prospect_info: dict,
) -> str:
    """Format the user message from the four context inputs."""
    hsb = briefs.get("hiring_signal_brief", {})
    cgb = briefs.get("competitor_gap_brief", {})

    return REPLY_INTERPRETER_USER_TEMPLATE.format(
        reply_text=reply_text.strip(),
        last_email_subject=last_email.get("subject", "(no subject)"),
        last_email_body=last_email.get("body", "(no body)"),
        prospect_name=prospect_info.get("name", "Unknown"),
        prospect_role=prospect_info.get("role", "Unknown"),
        prospect_company=prospect_info.get("company", "Unknown"),
        hsb_company=hsb.get("company", "Unknown"),
        hsb_segment=hsb.get("icp_segment", "Unknown"),
        hsb_confidence=hsb.get("confidence", 0),
        hsb_ai_score=hsb.get("ai_maturity_score", 0),
        hsb_velocity=_format_velocity(hsb),
        hsb_budget=_format_budget(hsb),
        hsb_cost_pressure=_format_cost_pressure(hsb),
        hsb_pitch=hsb.get("recommended_pitch_angle", ""),
        cgb_sector=cgb.get("sector", "Unknown"),
        cgb_position=cgb.get("prospect_position_in_sector", "Unknown"),
        cgb_gaps=_format_gaps(cgb),
        cgb_confidence=cgb.get("overall_confidence", 0),
    )


# ---------------------------------------------------------------------------
# Output validation & repair
# ---------------------------------------------------------------------------


def _validate_and_repair(raw_result: dict) -> dict:
    """
    Ensure the LLM output conforms to the required schema.
    Missing or invalid fields are repaired with safe defaults — never crashes.
    The next_step is ALWAYS overridden by the deterministic mapping.
    """
    result = {}

    # --- intent ---
    intent = str(raw_result.get("intent", "UNKNOWN")).upper().strip()
    if intent not in VALID_INTENTS:
        log.warning("Invalid intent '%s' from LLM, defaulting to UNKNOWN", intent)
        intent = "UNKNOWN"
    result["intent"] = intent

    # --- confidence ---
    try:
        confidence = float(raw_result.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.5
    result["confidence"] = round(confidence, 3)

    # --- reasoning ---
    reasoning = raw_result.get("reasoning", "")
    if not reasoning or not isinstance(reasoning, str):
        reasoning = f"Intent classified as {intent} based on reply analysis."
    result["reasoning"] = reasoning.strip()

    # --- next_step (deterministic override) ---
    result["next_step"] = INTENT_TO_NEXT_STEP[intent]

    # --- grounding_facts_used ---
    facts = raw_result.get("grounding_facts_used", [])
    if not isinstance(facts, list):
        facts = [str(facts)] if facts else []
    # Filter out empty strings
    facts = [str(f).strip() for f in facts if str(f).strip()]
    if not facts:
        facts = ["No specific grounding facts extracted from briefs."]
    result["grounding_facts_used"] = facts

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def interpret_reply(
    reply_text: str,
    last_email: dict,
    briefs: dict,
    prospect_info: dict,
) -> dict:
    """
    Interpret a prospect's reply and decide what the system should do next.

    This is a pure reasoning function — it does not send emails, update CRM,
    or interact with any external service.  It returns a decision dict.

    Args:
        reply_text:    The prospect's reply text (can be messy, short, hostile).
        last_email:    Dict with "subject" and "body" of the last email we sent.
        briefs:        Dict with "hiring_signal_brief" and "competitor_gap_brief".
        prospect_info: Dict with "name", "role", "company" (and optionally "email").

    Returns:
        dict:
        {
            "intent": "INTERESTED | NOT_INTERESTED | QUESTION | SCHEDULE | UNKNOWN",
            "confidence": float (0.0-1.0),
            "reasoning": str,
            "next_step": "SEND_EMAIL | SEND_CAL_LINK | ASK_CLARIFICATION | STOP",
            "grounding_facts_used": [list of facts pulled from briefs]
        }
    """
    if not reply_text or not reply_text.strip():
        return {
            "intent": "UNKNOWN",
            "confidence": 0.0,
            "reasoning": "Empty reply text — cannot determine intent.",
            "next_step": "ASK_CLARIFICATION",
            "grounding_facts_used": ["No reply content to analyze."],
        }

    user_message = _build_user_message(reply_text, last_email, briefs, prospect_info)

    try:
        response = _get_client().chat.completions.create(
            model=REPLY_MODEL,
            messages=[
                {"role": "system", "content": REPLY_INTERPRETER_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=REPLY_TEMPERATURE,
            response_format={"type": "json_object"},
            name="reply_interpreter.interpret_reply",
            metadata={
                "company": prospect_info.get("company", ""),
                "prospect": prospect_info.get("name", ""),
            },
        )
        raw_text = response.choices[0].message.content
    except Exception as exc:
        log.error("LLM call failed in reply_interpreter: %s", exc)
        return {
            "intent": "UNKNOWN",
            "confidence": 0.0,
            "reasoning": f"LLM call failed: {exc}",
            "next_step": "ASK_CLARIFICATION",
            "grounding_facts_used": ["LLM error — no analysis performed."],
        }

    # Parse JSON
    try:
        raw_result = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        log.error("LLM returned invalid JSON: %s | Raw: %s", exc, raw_text[:300])
        return {
            "intent": "UNKNOWN",
            "confidence": 0.0,
            "reasoning": f"LLM returned unparseable output: {raw_text[:200]}",
            "next_step": "ASK_CLARIFICATION",
            "grounding_facts_used": ["JSON parse error — no analysis performed."],
        }

    # Validate, repair, and enforce deterministic next_step
    return _validate_and_repair(raw_result)
