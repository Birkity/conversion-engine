"""
Act III — Reply Interpreter Test Suite.

Runs 14 realistic fake prospect replies through interpret_reply() and prints
the returned JSON for each.  Uses real trace data from traces/arcana/ to
build the hiring_signal_brief, competitor_gap_brief, and prospect_info context.

Prerequisites:
  - OPENROUTER_API_KEY set in .env
  - (Optional) Langfuse credentials for tracing

Usage:
    cd <repo-root>
    python scripts/act3_reply_tests.py
"""

import json
import os
import sys
import time
from pathlib import Path

# Force UTF-8 output on Windows to avoid cp1252 encoding errors
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure repo root is on the path so we can import agent.*
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

load_dotenv(REPO_ROOT / ".env")

from agent.reply_interpreter import interpret_reply

# ---------------------------------------------------------------------------
# Load real trace data for grounding context
# ---------------------------------------------------------------------------

TRACES_DIR = REPO_ROOT / "traces" / "arcana"


def _load_json(filename: str) -> dict:
    path = TRACES_DIR / filename
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    print(f"  [WARN] {path} not found, using empty dict")
    return {}


HSB = _load_json("hiring_signal_brief.json")
CGB = _load_json("competitor_gap_brief.json")
PROSPECT = _load_json("prospect_info.json")

BRIEFS = {
    "hiring_signal_brief": HSB,
    "competitor_gap_brief": CGB,
}

PROSPECT_INFO = {
    "name": PROSPECT.get("name", "Jordan Osei"),
    "role": PROSPECT.get("role", "CTO"),
    "company": PROSPECT.get("company", "Arcana Analytics"),
    "email": PROSPECT.get("email", "jordan.osei@sink.example.com"),
}

# Simulated last email (what we sent to the prospect)
LAST_EMAIL = {
    "subject": "Context: Series A and ML hiring velocity at Arcana Analytics",
    "body": (
        "Jordan,\n\n"
        "Arcana Analytics closed a $14M Series A in March and your open "
        "engineering roles doubled in the last 60 days — the typical bottleneck "
        "for teams at that stage is recruiting velocity, not budget.\n\n"
        "We have Python and ML engineers available to deploy next week. "
        "Would a 15-minute call on Thursday make sense?\n\n"
        "Birkity\n"
        "Research Partner, Tenacious Intelligence Corporation\n"
        "gettenacious.com"
    ),
}

# ---------------------------------------------------------------------------
# Test replies — 14 realistic scenarios covering all 5 intent classes
# ---------------------------------------------------------------------------

TEST_REPLIES = [
    # --- INTERESTED / SCHEDULE ---
    {
        "id": 1,
        "reply": "Sounds interesting, can you send times?",
        "expected_intent": "INTERESTED or SCHEDULE",
    },
    {
        "id": 2,
        "reply": "Sure, let's chat. Thursday works.",
        "expected_intent": "INTERESTED",
    },
    {
        "id": 3,
        "reply": "Send calendar",
        "expected_intent": "SCHEDULE",
    },
    {
        "id": 4,
        "reply": "Call me at 3pm — I have 15 minutes.",
        "expected_intent": "INTERESTED",
    },
    # --- NOT_INTERESTED ---
    {
        "id": 5,
        "reply": "Not interested.",
        "expected_intent": "NOT_INTERESTED",
    },
    {
        "id": 6,
        "reply": "Stop emailing me.",
        "expected_intent": "NOT_INTERESTED",
    },
    {
        "id": 7,
        "reply": "We already have a data team, thanks.",
        "expected_intent": "NOT_INTERESTED",
    },
    # --- QUESTION ---
    {
        "id": 8,
        "reply": "What exactly do you guys do?",
        "expected_intent": "QUESTION",
    },
    {
        "id": 9,
        "reply": "Who are you? I don't recognize this address.",
        "expected_intent": "QUESTION",
    },
    {
        "id": 10,
        "reply": "Can you explain more about the ML engineers? What's their experience with PyTorch and inference pipelines?",
        "expected_intent": "QUESTION",
    },
    # --- UNKNOWN ---
    {
        "id": 11,
        "reply": "Maybe later this quarter.",
        "expected_intent": "UNKNOWN",
    },
    {
        "id": 12,
        "reply": "This feels generic. Do you actually know what we do?",
        "expected_intent": "UNKNOWN or QUESTION",
    },
    {
        "id": 13,
        "reply": "lol another offshore body shop. hard pass buddy",
        "expected_intent": "NOT_INTERESTED or UNKNOWN",
    },
    {
        "id": 14,
        "reply": "k",
        "expected_intent": "UNKNOWN",
    },
]

# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

SEPARATOR = "=" * 80


def run_tests():
    print(SEPARATOR)
    print("ACT III — REPLY INTERPRETER TEST SUITE")
    print(f"Model: {os.getenv('REPLY_INTERPRETER_MODEL', os.getenv('BRIEF_GENERATOR_MODEL', 'google/gemini-2.0-flash-001'))}")
    print(f"Temperature: {os.getenv('REPLY_INTERPRETER_TEMPERATURE', '0.2')}")
    print(f"Prospect: {PROSPECT_INFO['name']} ({PROSPECT_INFO['role']}, {PROSPECT_INFO['company']})")
    print(SEPARATOR)
    print()

    results = []
    total_start = time.time()

    for test in TEST_REPLIES:
        test_id = test["id"]
        reply_text = test["reply"]
        expected = test["expected_intent"]

        print(f"--- Test #{test_id} ---")
        print(f"  Reply:    \"{reply_text}\"")
        print(f"  Expected: {expected}")

        start = time.time()
        try:
            result = interpret_reply(
                reply_text=reply_text,
                last_email=LAST_EMAIL,
                briefs=BRIEFS,
                prospect_info=PROSPECT_INFO,
            )
        except Exception as exc:
            result = {"error": str(exc)}
        elapsed = time.time() - start

        result["_test_id"] = test_id
        result["_reply"] = reply_text
        result["_expected"] = expected
        result["_elapsed_s"] = round(elapsed, 2)
        results.append(result)

        print(f"  Result:   {json.dumps(result, indent=2, default=str)}")
        print(f"  Time:     {elapsed:.2f}s")
        print()

    # -- Summary table --
    total_elapsed = time.time() - total_start
    print(SEPARATOR)
    print("SUMMARY")
    print(SEPARATOR)
    print(f"{'#':<4} {'Reply (truncated)':<45} {'Intent':<18} {'Conf':>5} {'Next Step':<20} {'Time':>6}")
    print("-" * 100)

    intent_counts = {}
    confidences = []

    for r in results:
        tid = r.get("_test_id", "?")
        reply_short = r.get("_reply", "")[:42]
        intent = r.get("intent", "ERROR")
        conf = r.get("confidence", 0)
        step = r.get("next_step", "ERROR")
        elapsed = r.get("_elapsed_s", 0)

        print(f"{tid:<4} {reply_short:<45} {intent:<18} {conf:>5.2f} {step:<20} {elapsed:>5.1f}s")

        intent_counts[intent] = intent_counts.get(intent, 0) + 1
        if isinstance(conf, (int, float)):
            confidences.append(conf)

    print("-" * 100)
    print(f"\nTotal time: {total_elapsed:.1f}s | Avg per reply: {total_elapsed / len(results):.1f}s")
    print(f"\nIntent distribution: {json.dumps(intent_counts, indent=2)}")

    if confidences:
        avg_conf = sum(confidences) / len(confidences)
        min_conf = min(confidences)
        max_conf = max(confidences)
        print(f"Confidence — avg: {avg_conf:.3f}, min: {min_conf:.3f}, max: {max_conf:.3f}")

    # ── Validation checks ──
    print("\n" + "VALIDATION CHECKS".ljust(80, "="))
    all_pass = True

    for r in results:
        tid = r.get("_test_id", "?")
        intent = r.get("intent", "")
        step = r.get("next_step", "")
        facts = r.get("grounding_facts_used", [])
        reasoning = r.get("reasoning", "")

        issues = []
        if intent not in {"INTERESTED", "NOT_INTERESTED", "QUESTION", "SCHEDULE", "UNKNOWN"}:
            issues.append(f"invalid intent: {intent}")
        if step not in {"SEND_EMAIL", "SEND_CAL_LINK", "ASK_CLARIFICATION", "STOP"}:
            issues.append(f"invalid next_step: {step}")
        if not facts or (len(facts) == 1 and "no" in facts[0].lower() and "error" in facts[0].lower()):
            issues.append("empty or error grounding_facts")
        if not reasoning:
            issues.append("empty reasoning")

        # Check intent→step consistency
        expected_step = {
            "INTERESTED": "SEND_CAL_LINK",
            "SCHEDULE": "SEND_CAL_LINK",
            "QUESTION": "SEND_EMAIL",
            "NOT_INTERESTED": "STOP",
            "UNKNOWN": "ASK_CLARIFICATION",
        }.get(intent, "")
        if expected_step and step != expected_step:
            issues.append(f"step mismatch: {intent}->{step} (expected {expected_step})")

        if issues:
            print(f"  [FAIL] Test #{tid}: {', '.join(issues)}")
            all_pass = False
        else:
            print(f"  [OK]   Test #{tid}: PASS")

    print()
    if all_pass:
        print("ALL TESTS PASSED -- schema valid, next_step consistent, grounding present.")
    else:
        print("SOME TESTS HAD ISSUES -- see above for details.")

    return results


if __name__ == "__main__":
    run_tests()
