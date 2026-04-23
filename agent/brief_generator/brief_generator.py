"""
Brief generator module.
Entry point: generate(signals: dict) -> dict

Input:  signals dict matching signals.json schema
Output: {"hiring_signal_brief": {...}, "competitor_gap_brief": {...}}
"""
import json

from .llm_client import call_llm
from .prompts import SYSTEM_PROMPT, USER_TEMPLATE

_HSB_FIELDS = {
    "hiring_velocity", "budget_urgency", "cost_pressure", "engineering_maturity",
    "ai_maturity_score", "ai_maturity_rationale", "confidence", "icp_segment",
    "recommended_pitch_angle",
}
_CGB_FIELDS = {
    "sector", "competitors_analyzed", "prospect_ai_score",
    "prospect_position_in_sector", "gaps", "overall_confidence",
}


def _derive_signal_confidence(signals: dict) -> dict:
    """Estimate per-source confidence from a signals dict."""
    # crunchbase: 1.0 if real funding data present, 0.3 otherwise
    funding_info = signals.get("funding_info", "")
    if funding_info and funding_info != "No funding data available":
        crunchbase_conf = 1.0
    else:
        crunchbase_conf = 0.3

    # job_velocity: 0.9 if jobs_now is a non-negative int, 0.0 if "data not available"
    jobs_now = signals.get("jobs_now", "data not available")
    if isinstance(jobs_now, int) and jobs_now >= 0:
        job_velocity_conf = 0.9
    else:
        job_velocity_conf = 0.0

    # layoffs: 1.0 if real event text, 0.5 if "No layoff events found", 0.0 if missing/empty
    layoffs = signals.get("layoffs", "")
    if not layoffs:
        layoff_conf = 0.0
    elif str(layoffs).strip().lower().startswith("no layoff events found"):
        layoff_conf = 0.5
    else:
        layoff_conf = 1.0

    # ai_maturity: 0.7 if ai_roles or tech_stack is non-empty, 0.3 otherwise
    ai_roles = signals.get("ai_roles", [])
    tech_stack = signals.get("tech_stack", [])
    has_ai_signal = bool(ai_roles) or bool(tech_stack)
    ai_maturity_conf = 0.7 if has_ai_signal else 0.3

    return {
        "crunchbase": crunchbase_conf,
        "job_velocity": job_velocity_conf,
        "layoffs": layoff_conf,
        "ai_maturity": ai_maturity_conf,
    }


def _format_competitor_signals(competitor_signals: list | str | None) -> str:
    if not competitor_signals:
        return "No competitor data available."
    if isinstance(competitor_signals, str):
        return competitor_signals
    lines = []
    for i, comp in enumerate(competitor_signals[:7], 1):
        name = comp.get("name", f"Competitor {i}")
        funding = comp.get("funding", "unknown")
        stack = comp.get("tech_stack", [])
        ai_score = comp.get("ai_maturity_score", "unknown")
        stack_str = ", ".join(stack[:8]) if stack else "unknown"
        lines.append(
            f"Competitor {i}: {name}\n"
            f"  Funding: {funding}\n"
            f"  Tech stack: {stack_str}\n"
            f"  AI maturity (pre-score): {ai_score}/3"
        )
    return "\n\n".join(lines)


def _normalize(parsed: dict, company_name: str) -> dict:
    hsb = parsed.get("hiring_signal_brief", {})
    cgb = parsed.get("competitor_gap_brief", {})
    for k in _HSB_FIELDS:
        if k not in hsb and k in parsed:
            hsb[k] = parsed[k]
    for k in _CGB_FIELDS:
        if k not in cgb and k in parsed:
            cgb[k] = parsed[k]
    if "company" not in hsb:
        hsb["company"] = company_name
    hsb.setdefault("tenacious_status", "draft")
    if not cgb:
        cgb = {"sector": "unknown", "competitors_analyzed": 0, "gaps": [], "overall_confidence": 0.0}
    cgb.setdefault("tenacious_status", "draft")
    return {"hiring_signal_brief": hsb, "competitor_gap_brief": cgb}


def generate(signals: dict) -> dict:
    """
    Generate hiring_signal_brief and competitor_gap_brief from a signals dict.

    Args:
        signals: dict matching the signals.json schema.
    Returns:
        dict with "hiring_signal_brief" and "competitor_gap_brief" keys.
    """
    company_name = signals.get("company_name", "Unknown")

    industries = signals.get("industries", [])
    if isinstance(industries, list):
        industries = ", ".join(industries) or "Unknown"

    tech_stack = signals.get("tech_stack", [])
    if isinstance(tech_stack, list):
        tech_stack = ", ".join(tech_stack) or "None detected"

    ai_roles = signals.get("ai_roles", [])
    if isinstance(ai_roles, list):
        ai_roles = ", ".join(ai_roles) or "None found"

    competitor_signals_str = _format_competitor_signals(signals.get("competitor_signals", []))

    conf = _derive_signal_confidence(signals)
    conf_str = " | ".join(f"{k}: {v:.2f}" for k, v in conf.items())

    user_msg = USER_TEMPLATE.format(
        company_name=company_name,
        industries=industries,
        headcount=signals.get("headcount", "Unknown"),
        description=(signals.get("description", "No description available"))[:400],
        funding_info=signals.get("funding_info", "No funding data available"),
        layoffs=signals.get("layoffs", "No layoff data found"),
        jobs_now=signals.get("jobs_now", "data not available"),
        jobs_60_days=signals.get("jobs_60_days", "data not available"),
        tech_stack=tech_stack,
        ai_roles=ai_roles,
        leadership_changes=signals.get("leadership_changes", "None detected"),
        recent_news=signals.get("recent_news", "None detected"),
        competitor_signals=competitor_signals_str,
        signal_confidence=conf_str,
    )

    raw = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_message=user_msg,
        trace_name="brief_generator.generate",
        trace_metadata={"company": company_name},
    )

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\nRaw: {raw[:500]}") from e

    return _normalize(parsed, company_name)
