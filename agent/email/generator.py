"""
LLM-based email composer for Tenacious outbound sequences.

Enforces every constraint from seeds/tenacious_sales_data/seed/style_guide.md:
  - Max 120 words in body (cold Email 1)
  - Subject line under 60 characters
  - Segment-specific subject-line patterns
  - Five tone markers: Direct, Grounded, Honest, Professional, Non-condescending
  - No clichés: "top talent", "world-class", "aggressive hiring", "cost savings"
  - Grounded claims only — every sentence traces to the brief

Policy compliance (data_handling_policy.md):
  - Rule 2: prospect_info must contain synthetic contact details only
  - Rule 6: X-Tenacious-Status: draft header is added by the email handler
  - Rule 7: only first name and email are passed; no PII beyond that
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
from langfuse.openai import OpenAI

load_dotenv()

_MODEL = os.getenv("BRIEF_GENERATOR_MODEL", "google/gemini-2.0-flash-001")

_SYSTEM_PROMPT = """\
You are a senior B2B outreach writer for Tenacious Intelligence Corporation.
You write cold outreach emails that are signal-grounded, direct, and honest.

=== STYLE GUIDE (non-negotiable) ===

Tone markers — every message must score 5/5:
1. DIRECT: No filler words. Subject line starts with "Context:", "Note on", "Congrats on", or "Question on". No "Quick", "Just", "Hey".
2. GROUNDED: Every claim cites a concrete fact from the brief. Never assert "aggressive hiring" if jobs_now < 5.
3. HONEST: If a signal is missing, do not invent one. Say "we don't see public signal of X" and ask instead.
4. PROFESSIONAL: No "top talent", "world-class", "rockstar", "ninja", "bench" (use "engineers available"), "cost savings of X%".
5. NON-CONDESCENDING: Gap findings are research observations, not failures. Never imply the prospect is behind.

=== FORMAT CONSTRAINTS ===

Subject line:
- Under 60 characters
- Pattern by ICP segment:
    Segment 1 → "Context: [specific funding event]"
    Segment 2 → "Note on [specific restructure or layoff]"
    Segment 3 → "Congrats on the [role] appointment"
    Segment 4 → "Question on [specific capability signal]"
    Ambiguous  → "Context: [strongest signal in the brief]"

Body (Email 1 — cold opener):
- MAX 120 words. Count carefully. Exceed this and the email is rejected.
- Structure:
    Line 1: [First name only],
    Line 2: [One concrete verifiable fact from the hiring signal brief]
    Line 3: [The typical bottleneck companies in this state hit — observation, not assertion]
    Line 4: [One specific Tenacious capability that matches — no service menu]
    Line 5: [The ask — 15 minutes, a day of the week, the Cal.com link]
    Blank line, then signature block:
    [Sender first name]
    Research Partner, Tenacious Intelligence Corporation
    gettenacious.com
- No emojis.
- No "I hope this finds you well", "just reaching out", "following up".
- No logos, case-study names, customer counts.

=== OUTPUT FORMAT ===

Return exactly this JSON (no markdown, no explanation):
{
  "subject": "<subject line under 60 chars>",
  "body": "<full email body>",
  "word_count": <integer word count of body>,
  "icp_segment_used": "<Segment 1|2|3|4|Ambiguous>",
  "grounding_facts": ["<fact 1 from brief>", "<fact 2 from brief>"]
}
"""

_USER_TEMPLATE = """\
=== PROSPECT ===
Name: {prospect_name}
Role: {prospect_role}
Company: {company}

=== HIRING SIGNAL BRIEF ===
ICP Segment: {icp_segment}
Confidence: {confidence}

Hiring Velocity:
  Direction: {velocity_direction}
  Delta: {velocity_delta}%
  Signal strength: {velocity_strength}
  Observation: {velocity_observation}

Budget Urgency:
  Level: {budget_level}
  Signal: {budget_signal}

Cost Pressure:
  Present: {cost_present}
  Signal: {cost_signal}

AI Maturity Score: {ai_score}/3
AI Maturity Rationale: {ai_rationale}

Recommended Pitch Angle:
{pitch_angle}

Honesty Flags:
  weak_hiring_velocity_signal: {flag_weak_hiring}
  bench_gap_detected: {flag_bench_gap}

=== COMPETITOR GAP BRIEF ===
Sector: {sector}
Prospect position: {sector_position}
Gaps:
{gaps_text}

=== CAL.COM BOOKING LINK ===
{cal_link}

=== SENDER ===
First name: Birkity
Title: Research Partner
Company: Tenacious Intelligence Corporation
URL: gettenacious.com
"""


def _format_gaps(gaps: list) -> str:
    if not gaps:
        return "No competitor gaps identified."
    lines = []
    for i, g in enumerate(gaps, 1):
        lines.append(
            f"Gap {i}: {g.get('practice', 'unknown')}\n"
            f"  Top quartile shows: {g.get('evidence_in_top_quartile', '')}\n"
            f"  At prospect: {g.get('evidence_at_prospect', '')}\n"
            f"  Insight: {g.get('gap_insight', '')}\n"
            f"  Confidence: {g.get('confidence', 0)}"
        )
    return "\n".join(lines)


def generate_email(
    hsb: dict,
    cgb: dict,
    prospect_info: dict,
    cal_link: str = "",
) -> dict:
    """
    Compose a signal-grounded cold outreach email (Email 1).

    Args:
        hsb: hiring_signal_brief dict
        cgb: competitor_gap_brief dict
        prospect_info: {"name", "role", "email", "company"} — must be synthetic
        cal_link: pre-filled Cal.com booking URL

    Returns:
        dict with keys: subject, body, word_count, icp_segment_used,
                        grounding_facts, tone_warnings (list of any violations)
    """
    velocity = hsb.get("hiring_velocity", {})
    budget = hsb.get("budget_urgency", {})
    cost = hsb.get("cost_pressure", {})
    ai_r = hsb.get("ai_maturity_rationale", {})
    flags = hsb.get("honesty_flags", {})

    user_msg = _USER_TEMPLATE.format(
        prospect_name=prospect_info.get("name", ""),
        prospect_role=prospect_info.get("role", ""),
        company=prospect_info.get("company", ""),
        icp_segment=hsb.get("icp_segment", "Ambiguous"),
        confidence=hsb.get("confidence", 0),
        velocity_direction=velocity.get("direction", "unknown"),
        velocity_delta=velocity.get("delta_pct", "unknown"),
        velocity_strength=velocity.get("signal_strength", "unknown"),
        velocity_observation=velocity.get("observation", ""),
        budget_level=budget.get("level", "unknown"),
        budget_signal=budget.get("signal", "none"),
        cost_present=cost.get("present", False),
        cost_signal=cost.get("signal", "none"),
        ai_score=hsb.get("ai_maturity_score", 0),
        ai_rationale=str(ai_r),
        pitch_angle=hsb.get("recommended_pitch_angle", ""),
        flag_weak_hiring=flags.get("weak_hiring_velocity_signal", False),
        flag_bench_gap=flags.get("bench_gap_detected", False),
        sector=cgb.get("sector", "unknown"),
        sector_position=cgb.get("prospect_position_in_sector", "unknown"),
        gaps_text=_format_gaps(cgb.get("gaps", [])),
        cal_link=cal_link or os.getenv("CALCOM_EVENT_URL", "https://cal.com/booking/intro"),
    )

    import json
    client = OpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    )
    response = client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
        name="email_generator.generate_email",
        metadata={"company": prospect_info.get("company", "")},
    )
    raw = response.choices[0].message.content
    result = json.loads(raw)

    # Post-generation validation — all 5 tone markers from style_guide.md
    warnings = []
    body = result.get("body", "")
    subject = result.get("subject", "")
    word_count = len(body.split())

    # FORMAT constraints
    if word_count > 120:
        warnings.append(f"body_too_long: {word_count} words (max 120)")
    if len(subject) > 60:
        warnings.append(f"subject_too_long: {len(subject)} chars (max 60)")

    body_lower = body.lower()
    subject_lower = subject.lower()

    # Marker 1 — DIRECT: subject must use approved prefix patterns
    _approved_prefixes = ("context:", "note on", "congrats on", "question on")
    if not any(subject_lower.startswith(p) for p in _approved_prefixes):
        warnings.append(f"not_direct_subject_prefix: '{subject[:50]}'")
    for filler in ("quick ", "just ", "hey ", "hope this finds"):
        if filler in subject_lower or filler in body_lower:
            warnings.append(f"filler_word_detected: '{filler.strip()}'")

    # Marker 2 — GROUNDED: banned phrases + aggressive hiring gate
    for banned in ("top talent", "world-class", "rockstar", "ninja",
                   "aggressive hiring", "cost savings"):
        if banned.lower() in body_lower:
            warnings.append(f"banned_phrase_detected: '{banned}'")
    jobs_now = hsb.get("hiring_velocity", {}).get("delta_pct")
    try:
        if "aggressive" in body_lower and int(jobs_now or 0) < 5:
            warnings.append("grounded_violation: 'aggressive' used when jobs_now < 5")
    except (TypeError, ValueError):
        pass

    # Marker 3 — HONEST: "bench" is jargon; should say "engineers available"
    if "bench" in body_lower:
        warnings.append("banned_jargon: 'bench' detected — use 'engineers available'")

    # Marker 4 — PROFESSIONAL: additional banned phrases
    for prof_banned in ("cost savings of", "guaranteed roi", "proven track record"):
        if prof_banned in body_lower:
            warnings.append(f"unprofessional_phrase: '{prof_banned}'")

    # Marker 5 — NON-CONDESCENDING: deficit framing
    for deficit in ("falling behind", "you're behind", "you lack", "you're missing",
                    "you need to catch up", "left behind"):
        if deficit in body_lower:
            warnings.append(f"condescending_framing: '{deficit}'")

    result["word_count"] = word_count
    result["tone_warnings"] = warnings
    return result
