"""
Tenacious-Bench v0.1 — Scoring Evaluator

Implements D1–D5 scoring. D2–D5 are fully programmatic (no model calls).
D1 (ICP-Pitch Alignment) requires a dev-tier LLM call; pass llm_judge_fn to enable it.

Usage:
    python scoring_evaluator.py          # runs against 3 example tasks from schema.json
    python scoring_evaluator.py task.json  # score a single task file
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Callable, Optional

# ── Banned phrases from agent/email/generator.py ──────────────────────────────

BANNED_PHRASES: list[str] = [
    "top talent", "world-class", "rockstar", "ninja", "aggressive hiring",
    "cost savings of", "guaranteed roi", "proven track record",
    "falling behind", "you're behind", "you lack", "you're missing",
    "you need to catch up", "left behind",
    "https://cal.com", "schedule a", "book a",
    "quick ", "just ", "hey there", "hope this finds",
]

# ── D2: Signal Directionality ──────────────────────────────────────────────────

_GROWTH_FRAME_RE = re.compile(
    r"\bbottleneck\b|\bscaling\b|\baccelerati|\brapid growth\b|"
    r"\bincreased demand\b|\bneed to augment\b|\baugment\b",
    re.IGNORECASE,
)


def score_d2_directionality(
    brief: dict, email_body: str
) -> tuple[int, Optional[str]]:
    """
    FAIL if: velocity_delta < -20% AND email uses a growth-frame keyword.
    Evidence: snaptrade-2026-04-28 (delta=-60%, body="bottlenecks"),
              wiseitech-2026-04-27 (delta=-100%, body="augment").
    """
    delta = brief.get("hiring_velocity", {}).get("delta_pct", 0.0) / 100.0
    if delta < -0.20 and _GROWTH_FRAME_RE.search(email_body):
        return 0, f"contraction signal ({delta:.0%}) with growth-frame pitch"
    return 1, None


# ── D3: Grounding Completeness ─────────────────────────────────────────────────

_NUMERIC_RE = re.compile(r"\$[\d,.]+[MBmk]?|\d+%|\b\d{4}\b")


def score_d3_grounding(
    email_body: str, brief: dict
) -> tuple[int, Optional[str]]:
    """
    FAIL if any numeric token in the email body cannot be found in the brief.
    Catches: wrong funding amounts, invented percentages, fabricated years.

    Corpus includes the full JSON representation of the brief PLUS derived
    percentage strings from hiring_velocity.delta_pct, so that "60%" in the
    email is verified against delta_pct=-60.0 in the brief.
    """
    brief_text = json.dumps(brief)
    # Derive percentage string from delta_pct so "60%" matches "-60.0"
    delta = brief.get("hiring_velocity", {}).get("delta_pct", 0.0)
    derived_pct = f"{abs(int(delta))}%"
    corpus = brief_text + " " + derived_pct

    tokens = _NUMERIC_RE.findall(email_body)
    unverified = [t for t in tokens if t not in corpus]
    if unverified:
        return 0, f"unverified numeric tokens: {unverified}"
    return 1, None


# ── D4: Tone Compliance ────────────────────────────────────────────────────────


def score_d4_tone(email_body: str) -> tuple[int, Optional[str]]:
    """
    FAIL if any banned phrase from the Tenacious style guide appears in the body.
    List mirrors agent/email/generator.py.
    """
    body_lower = email_body.lower()
    hits = [p for p in BANNED_PHRASES if p in body_lower]
    if hits:
        return 0, f"banned phrases detected: {hits}"
    return 1, None


# ── D5: Format Compliance ──────────────────────────────────────────────────────

_URL_RE = re.compile(r"https?://")


def score_d5_format(subject: str, email_body: str) -> tuple[int, Optional[str]]:
    """
    FAIL if: body > 120 words, subject > 60 chars, or URL present in cold outreach.
    """
    word_count = len(email_body.split())
    if word_count > 120:
        return 0, f"body too long: {word_count} words (max 120)"
    if len(subject) > 60:
        return 0, f"subject too long: {len(subject)} chars (max 60)"
    if _URL_RE.search(email_body):
        return 0, "external URL in cold outreach body"
    return 1, None


# ── D1: ICP-Pitch Alignment (LLM gate) ────────────────────────────────────────

SEGMENT_VALID_FRAMES: dict[str, list[str]] = {
    "segment 1": ["bottleneck", "scaling", "accelerat", "post-fund", "integrat", "headcount"],
    "segment 2": ["re-staff", "after layoff", "continuity", "gap", "project", "reduction"],
    "segment 3": ["new leader", "moderniz", "stack", "rebuild", "uplift", "cto"],
    "segment 4": ["ai gap", "ai capability", "ml tooling", "maturity", "dedicated ai"],
    "ambiguous": [],
}

D1_SYSTEM_PROMPT = """You are a sales quality judge for Tenacious Intelligence Corporation.

Given a hiring signal brief (JSON) and a generated outreach email, evaluate:
Does the email's primary pitch frame match the valid frames for the ICP segment?

Segment rules:
- Segment 1: valid = scaling bottleneck, integration speed, headcount gap post-funding
- Segment 2: valid = re-staffing after reduction, project continuity, skills gap
- Segment 3: valid = new leader building stack, modernization, capability uplift
- Segment 4: valid = specific AI capability gap, ML maturity uplift, AI tooling
- Ambiguous: valid = qualifying question ONLY; any product claim = FAIL

Return JSON exactly: {"score": 0 or 1, "reason": "one sentence"}
Score 0 = FAIL (wrong pitch frame or product claim on Ambiguous segment).
Score 1 = PASS (pitch matches segment, or email asks a qualifying question).
"""


def score_d1_icp_alignment(
    brief: dict,
    email: dict,
    llm_judge_fn: Optional[Callable[[str, str], dict]] = None,
) -> tuple[Optional[int], Optional[str]]:
    """
    Programmatic pre-check first (fast path). LLM judge only if ambiguous.
    Returns (None, None) if llm_judge_fn is not provided.
    """
    segment = (brief.get("icp_segment") or "").lower().strip()
    body_lower = email.get("body", "").lower()

    # Fast-path: Ambiguous + any product claim = immediate FAIL.
    # Use substring matching (case-insensitive) rather than word-boundary regex
    # to avoid plural/inflection misses (provides, engineers, augments, etc.).
    PRODUCT_CLAIM_PHRASES = [
        "tenacious can", "tenacious provides", "tenacious will",
        "tenacious offers", "tenacious gives", "we provide", "we can augment",
        "our engineers", "our team can", "augment your team", "augment your",
        "pre-vetted", "project-ready", "available on-demand",
    ]
    if segment == "ambiguous":
        body_lower_check = email.get("body", "").lower()
        if any(phrase in body_lower_check for phrase in PRODUCT_CLAIM_PHRASES):
            return 0, "segment=Ambiguous but email makes a product claim"

    if llm_judge_fn is None:
        return None, None

    prompt = (
        f"Brief:\n{json.dumps(brief, indent=2)}\n\n"
        f"Email subject: {email.get('subject', '')}\n"
        f"Email body:\n{email.get('body', '')}"
    )
    try:
        result = llm_judge_fn(D1_SYSTEM_PROMPT, prompt)
        score = int(result.get("score", 1))
        reason = result.get("reason", "")
        return score, reason if score == 0 else None
    except Exception as exc:
        return None, f"D1 judge error: {exc}"


# ── Main scorer ────────────────────────────────────────────────────────────────


def score_task(
    task: dict,
    llm_judge_fn: Optional[Callable[[str, str], dict]] = None,
) -> dict:
    """
    Score a task dict against D1–D5.

    Args:
        task: Task dict matching schema.json
        llm_judge_fn: Optional callable(system_prompt, user_prompt) -> {"score": int, "reason": str}
                      Required for D1. If None, D1 is skipped (scored as null).

    Returns:
        {dimension_scores, verdict, primary_failure_dimension, reject_reason}
    """
    brief = task["input"]["hiring_signal_brief"]
    email = task["input"]["generated_email"]
    body = email.get("body", "")
    subject = email.get("subject", "")

    # Score all dimensions
    d1, d1_reason = score_d1_icp_alignment(brief, email, llm_judge_fn)
    d2, d2_reason = score_d2_directionality(brief, body)
    d3, d3_reason = score_d3_grounding(body, brief)
    d4, d4_reason = score_d4_tone(body)
    d5, d5_reason = score_d5_format(subject, body)

    scores = {"D1": d1, "D2": d2, "D3": d3, "D4": d4, "D5": d5}
    reasons = {
        "D1": d1_reason, "D2": d2_reason, "D3": d3_reason,
        "D4": d4_reason, "D5": d5_reason,
    }

    # Verdict: REJECT if any scored dimension is 0
    verdict = "PASS"
    primary = "none"
    reject_reason = None

    # Priority order: D2 → D1 → D3 → D4 → D5
    for dim in ["D2", "D1", "D3", "D4", "D5"]:
        if scores[dim] == 0:
            verdict = "REJECT"
            primary = {
                "D1": "D1_icp_pitch_alignment",
                "D2": "D2_signal_directionality",
                "D3": "D3_grounding_completeness",
                "D4": "D4_tone_compliance",
                "D5": "D5_format_compliance",
            }[dim]
            reject_reason = reasons[dim]
            break

    return {
        "dimension_scores": scores,
        "verdict": verdict,
        "primary_failure_dimension": primary,
        "reject_reason": reject_reason,
    }


# ── CLI ────────────────────────────────────────────────────────────────────────


def _run_examples() -> None:
    """Run the 3 example tasks from schema.json and print results."""
    schema_path = Path(__file__).parent / "schema.json"
    if not schema_path.exists():
        print("schema.json not found — run from week11/ directory")
        sys.exit(1)

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    examples = schema.get("examples", [])

    print(f"Running {len(examples)} example tasks...\n")
    all_passed = True

    for task in examples:
        result = score_task(task)
        expected = task["ground_truth"]

        # Compare programmatic dimensions only (D2–D5; D1 needs LLM)
        prog_match = all(
            result["dimension_scores"].get(d) == expected["dimension_scores"].get(d)
            for d in ["D2", "D3", "D4", "D5"]
        )
        verdict_match = result["verdict"] == expected["verdict"]
        ok = prog_match and verdict_match

        status = "PASS" if ok else "FAIL"
        if not ok:
            all_passed = False

        print(f"[{status}] {task['task_id']} ({task['difficulty']})")
        print(f"  Expected verdict : {expected['verdict']}")
        print(f"  Got verdict      : {result['verdict']}")
        print(f"  Dimension scores : {result['dimension_scores']}")
        if result["reject_reason"]:
            print(f"  Reject reason    : {result['reject_reason']}")
        print()

    if all_passed:
        print("All example tasks scored correctly.")
    else:
        print("One or more tasks did not match expected output.")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        task_path = Path(sys.argv[1])
        task = json.loads(task_path.read_text(encoding="utf-8"))
        result = score_task(task)
        print(json.dumps(result, indent=2))
    else:
        _run_examples()
