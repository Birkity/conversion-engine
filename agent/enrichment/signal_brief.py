"""
LLM-powered signal brief generator.
Produces hiring_signal_brief and competitor_gap_brief from raw company signals.
"""
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

BRIEF_MODEL = os.getenv("BRIEF_MODEL", "qwen/qwen3-30b-a3b")

SYSTEM_PROMPT = """\
You are an AI system that generates structured intelligence briefs for B2B engineering consulting outreach.

You must ONLY use the signals provided. Do not invent data.

Your task is to produce TWO JSON outputs:

1) hiring_signal_brief
2) competitor_gap_brief

The goal is to derive insight from signals, not summarize them.

================= RULES =================

For Hiring Signal Brief:
- Infer hiring velocity from job post change (jobs_now vs jobs_60_days_ago)
- Infer budget/urgency from funding
- Infer cost pressure from layoffs
- Infer engineering maturity from tech stack
- Produce AI maturity score from 0-3 (integer)
- Produce confidence score 0-1

AI Maturity Score guide:
  0 = No public signal of AI engagement
  1 = Some AI roles or stack signals but no clear commitment
  2 = Dedicated AI roles + modern ML stack OR exec commentary on AI
  3 = Active AI function with recent exec commitment AND multiple open AI roles AND modern ML stack

For Competitor Gap Brief:
- Identify top quartile signals among competitors
- Identify which of those the prospect lacks
- Derive a gap insight as a neutral observation (NOT condescending)
- Produce per-gap confidence score

Do NOT write explanations. ONLY valid JSON.

================= OUTPUT FORMAT =================

Return exactly this structure (no markdown, no explanation, only valid JSON):

{
  "hiring_signal_brief": {
    "company": "<company_name>",
    "hiring_velocity": {
      "direction": "accelerating|decelerating|stable|unknown",
      "delta_pct": <number or null>,
      "signal_strength": "strong|moderate|weak|insufficient_data",
      "observation": "<one sentence>"
    },
    "budget_urgency": {
      "level": "high|medium|low|unknown",
      "signal": "<funding event or null>",
      "runway_pressure": "<observation or null>"
    },
    "cost_pressure": {
      "present": <true|false>,
      "signal": "<layoff event or null>",
      "icp_segment_implication": "<Segment 1|2|3|4 or null>"
    },
    "engineering_maturity": {
      "stack_sophistication": "high|medium|low|unknown",
      "detected_stack": ["<tech>"],
      "bench_match_notes": "<observation>"
    },
    "ai_maturity_score": <0|1|2|3>,
    "ai_maturity_rationale": {
      "ai_roles_found": ["<role>"],
      "modern_ml_stack_signals": ["<tech>"],
      "executive_ai_signals": "strong|moderate|weak|none",
      "named_ai_leadership": <true|false>
    },
    "confidence": <0.0-1.0>,
    "icp_segment": "<Segment 1|2|3|4|ambiguous>",
    "recommended_pitch_angle": "<one sentence pitch angle for Tenacious>"
  },
  "competitor_gap_brief": {
    "sector": "<inferred sector>",
    "competitors_analyzed": <count>,
    "prospect_ai_score": <0-3>,
    "prospect_position_in_sector": "top_quartile|above_median|below_median|bottom_quartile|insufficient_data",
    "gaps": [
      {
        "practice": "<specific practice top quartile shows>",
        "evidence_in_top_quartile": "<what competitors show>",
        "evidence_at_prospect": "<what prospect shows or lacks>",
        "gap_insight": "<neutral one-sentence research finding>",
        "confidence": <0.0-1.0>
      }
    ],
    "overall_confidence": <0.0-1.0>
  }
}
"""

USER_TEMPLATE = """\
================= PROSPECT SIGNALS =================

Company: {company_name}

Funding:
{funding_info}

Layoffs:
{layoff_info}

Job Posts Now:
{jobs_now}

Job Posts 60 Days Ago:
{jobs_60_days}

Tech Stack Detected:
{tech_stack}

AI/ML Related Roles Found:
{ai_roles}

================= COMPETITORS =================

For each competitor, signals are provided.

{competitor_signals}
"""


def generate_briefs(
    company_name: str,
    funding_info: str,
    layoff_info: str,
    jobs_now: int | str,
    jobs_60_days: int | str,
    tech_stack: list[str] | str,
    ai_roles: list[str] | str,
    competitor_signals: str,
) -> dict:
    """Call the LLM and return parsed hiring_signal_brief + competitor_gap_brief."""
    if isinstance(tech_stack, list):
        tech_stack = ", ".join(tech_stack) if tech_stack else "None detected"
    if isinstance(ai_roles, list):
        ai_roles = ", ".join(ai_roles) if ai_roles else "None found"

    user_msg = USER_TEMPLATE.format(
        company_name=company_name,
        funding_info=funding_info or "No funding data available",
        layoff_info=layoff_info or "No layoff data found",
        jobs_now=jobs_now,
        jobs_60_days=jobs_60_days,
        tech_stack=tech_stack,
        ai_roles=ai_roles,
        competitor_signals=competitor_signals or "No competitor data available",
    )

    response = _client.chat.completions.create(
        model=BRIEF_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    return json.loads(raw)
