"""
Act III — Reply Interpreter Probe Suite.

Loads probes from probes/probe_cases.json and runs each through
interpret_reply() with real trace context from traces/<company>/ and the
last email artifact from artifacts/<company>/last_email.json.

OFFLINE REASONING TEST ONLY — this script must NOT:
  - Send any emails
  - Call any webhooks
  - Update HubSpot
  - Use real email addresses

Prerequisites:
  - OPENROUTER_API_KEY set in .env
  - Run act2_email_execution.py first to populate artifacts/<company>/last_email.json
  - (Optional) Langfuse credentials for tracing

Usage:
    python scripts/act3_reply_tests.py
    python scripts/act3_reply_tests.py --company kinanalytics
    python scripts/act3_reply_tests.py --save-results
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

load_dotenv(REPO_ROOT / ".env")

from agent.reply_interpreter import interpret_reply

# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------

_parser = argparse.ArgumentParser(description="Act III offline probe suite.")
_parser.add_argument(
    "--company",
    default="arcana",
    help="Company slug to load context from traces/<company>/ and artifacts/<company>/. "
         "Default: arcana",
)
_parser.add_argument(
    "--save-results",
    action="store_true",
    help="Write probe results to probes/probe_results.json for taxonomy analysis.",
)
_parser.add_argument(
    "--output",
    default=None,
    help="Override the output file path for --save-results (relative to repo root).",
)
_args = _parser.parse_args()
_COMPANY = _args.company

# ---------------------------------------------------------------------------
# Load context
# ---------------------------------------------------------------------------

TRACES_DIR = REPO_ROOT / "traces" / _COMPANY
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / _COMPANY
PROBES_DIR = REPO_ROOT / "probes"


def _load_json(path: Path, label: str = "") -> dict | list:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    print(f"  [WARN] {label or path} not found, using empty dict")
    return {} if path.suffix == ".json" and "probe" not in path.name else []


HSB = _load_json(TRACES_DIR / "hiring_signal_brief.json", "hiring_signal_brief")
CGB = _load_json(TRACES_DIR / "competitor_gap_brief.json", "competitor_gap_brief")
PROSPECT = _load_json(TRACES_DIR / "prospect_info.json", "prospect_info")

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

# Load last_email from artifact (written by act2_email_execution.py)
_last_email_path = ARTIFACTS_DIR / "last_email.json"
if _last_email_path.exists():
    LAST_EMAIL = json.loads(_last_email_path.read_text(encoding="utf-8"))
    print(f"  [OK]  Loaded last_email from {_last_email_path}")
else:
    print(f"  [WARN] {_last_email_path} not found — using fallback. Run act2 first:")
    print(f"         python scripts/act2_email_execution.py traces/{_COMPANY} --dry-run")
    LAST_EMAIL = {
        "subject": "Context: Series A and ML hiring velocity at Arcana Analytics",
        "body": (
            "Jordan,\n\n"
            "Arcana Analytics closed a $14M Series A in March and your open "
            "engineering roles doubled in the last 60 days — the typical bottleneck "
            "for teams at that stage is recruiting velocity, not budget.\n\n"
            "We have Python and ML engineers available to deploy. "
            "Are you thinking about this mostly as a hiring-speed problem "
            "or a skill-depth problem?\n\n"
            "Birkity\n"
            "Research Partner, Tenacious Intelligence Corporation\n"
            "gettenacious.com"
        ),
    }

# ---------------------------------------------------------------------------
# Load probes
# ---------------------------------------------------------------------------

_probes_path = PROBES_DIR / "probe_cases.json"
if not _probes_path.exists():
    print(f"ERROR: {_probes_path} not found. Cannot run probes.", file=sys.stderr)
    sys.exit(1)

TEST_CASES = json.loads(_probes_path.read_text(encoding="utf-8"))
print(f"  [OK]  Loaded {len(TEST_CASES)} probes from {_probes_path}")

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

VALID_INTENTS = {"INTERESTED", "NOT_INTERESTED", "QUESTION", "SCHEDULE", "UNKNOWN"}
VALID_NEXT_STEPS = {"SEND_EMAIL", "SEND_CAL_LINK", "ASK_CLARIFICATION", "STOP"}

INTENT_TO_NEXT_STEP = {
    "INTERESTED": "SEND_CAL_LINK",
    "SCHEDULE": "SEND_CAL_LINK",
    "QUESTION": "SEND_EMAIL",
    "NOT_INTERESTED": "STOP",
    "UNKNOWN": "ASK_CLARIFICATION",
}


def _intent_matches(actual: str, expected_str: str) -> bool:
    """Support 'A or B' syntax in expected_intent field."""
    parts = [p.strip().upper() for p in expected_str.replace(" or ", "|").split("|")]
    return actual.upper() in parts


def _step_matches(actual: str, expected_str: str) -> bool:
    parts = [p.strip().upper() for p in expected_str.replace(" or ", "|").split("|")]
    return actual.upper() in parts


# ---------------------------------------------------------------------------
# Run probes
# ---------------------------------------------------------------------------

SEPARATOR = "=" * 90


def run_probes() -> list[dict]:
    print()
    print(SEPARATOR)
    print("ACT III — REPLY INTERPRETER PROBE SUITE")
    print(f"Model     : {os.getenv('REPLY_INTERPRETER_MODEL', os.getenv('BRIEF_GENERATOR_MODEL', 'google/gemini-2.0-flash-001'))}")
    print(f"Probes    : {len(TEST_CASES)}")
    print(f"Company   : {PROSPECT_INFO['name']} ({PROSPECT_INFO['role']}, {PROSPECT_INFO['company']})")
    print(f"Last email: {LAST_EMAIL.get('subject', '(no subject)')}")
    print(SEPARATOR)
    print()

    results = []
    total_start = time.time()

    for probe in TEST_CASES:
        pid = probe["id"]
        category = probe["category"]
        reply_text = probe["reply"]
        exp_intent = probe["expected_intent"]
        exp_step = probe["expected_next_step"]

        print(f"--- Probe #{pid:02d} [{category}] ---")
        print(f"  Reply    : \"{reply_text}\"")
        print(f"  Expected : intent={exp_intent}  next_step={exp_step}")

        start = time.time()
        try:
            result = interpret_reply(
                reply_text=reply_text,
                last_email=LAST_EMAIL,
                briefs=BRIEFS,
                prospect_info=PROSPECT_INFO,
            )
        except Exception as exc:
            result = {
                "intent": "ERROR",
                "confidence": 0.0,
                "next_step": "ERROR",
                "reasoning": str(exc),
                "grounding_facts_used": [],
            }
        elapsed = round(time.time() - start, 2)

        actual_intent = result.get("intent", "ERROR")
        actual_step = result.get("next_step", "ERROR")
        intent_ok = _intent_matches(actual_intent, exp_intent)
        step_ok = _step_matches(actual_step, exp_step)
        passed = intent_ok and step_ok

        status = "PASS" if passed else "FAIL"
        flag = "[OK]  " if passed else "[FAIL]"
        print(f"  Got      : intent={actual_intent}  next_step={actual_step}  conf={result.get('confidence', 0):.2f}")
        print(f"  {flag} {status}  ({elapsed}s)")
        if not passed:
            print(f"  Mismatch : intent_ok={intent_ok} step_ok={step_ok}")
            print(f"  Reasoning: {result.get('reasoning', '')[:120]}")
        print()

        results.append({
            "id": pid,
            "category": category,
            "reply": reply_text,
            "expected_intent": exp_intent,
            "expected_next_step": exp_step,
            "actual_intent": actual_intent,
            "actual_next_step": actual_step,
            "confidence": result.get("confidence", 0),
            "reasoning": result.get("reasoning", ""),
            "grounding_facts_used": result.get("grounding_facts_used", []),
            "passed": passed,
            "intent_ok": intent_ok,
            "step_ok": step_ok,
            "elapsed_s": elapsed,
            "risk_explained": probe.get("risk_explained", ""),
        })

    total_elapsed = time.time() - total_start

    # ── Summary table ──────────────────────────────────────────────────────
    print(SEPARATOR)
    print("SUMMARY TABLE")
    print(SEPARATOR)
    print(f"{'#':>3} {'Category':<28} {'Reply (40ch)':<42} {'Intent':<16} {'Step':<20} {'OK':>2}")
    print("-" * 115)

    category_stats: dict[str, dict] = defaultdict(lambda: {"total": 0, "pass": 0, "failures": []})

    for r in results:
        tid = r["id"]
        cat = r["category"][:26]
        reply_short = r["reply"][:40]
        intent = r["actual_intent"]
        step = r["actual_next_step"]
        ok = "✓" if r["passed"] else "✗"
        print(f"{tid:>3} {cat:<28} {reply_short:<42} {intent:<16} {step:<20} {ok:>2}")
        category_stats[r["category"]]["total"] += 1
        if r["passed"]:
            category_stats[r["category"]]["pass"] += 1
        else:
            category_stats[r["category"]]["failures"].append(r)

    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = total - passed_count

    print("-" * 115)
    print(f"\nTotal: {total}  Passed: {passed_count}  Failed: {failed_count}  "
          f"Pass rate: {passed_count/total*100:.0f}%  Time: {total_elapsed:.1f}s")

    # ── Per-category breakdown ─────────────────────────────────────────────
    print()
    print(SEPARATOR)
    print("PER-CATEGORY PASS RATES")
    print(SEPARATOR)
    print(f"{'Category':<35} {'Pass/Total':>12} {'Rate':>8}")
    print("-" * 60)
    for cat, stats in sorted(category_stats.items()):
        p = stats["pass"]
        t = stats["total"]
        rate = p / t * 100
        bar = "█" * int(rate / 10) + "░" * (10 - int(rate / 10))
        print(f"  {cat:<33} {p}/{t:>5}      {rate:>5.0f}%  [{bar}]")
    print()

    # ── Schema validation ──────────────────────────────────────────────────
    print(SEPARATOR)
    print("SCHEMA VALIDATION")
    print(SEPARATOR)
    schema_pass = True
    for r in results:
        issues = []
        if r["actual_intent"] not in VALID_INTENTS and r["actual_intent"] != "ERROR":
            issues.append(f"invalid intent: {r['actual_intent']}")
        if r["actual_next_step"] not in VALID_NEXT_STEPS and r["actual_next_step"] != "ERROR":
            issues.append(f"invalid next_step: {r['actual_next_step']}")
        inferred_step = INTENT_TO_NEXT_STEP.get(r["actual_intent"], "")
        if inferred_step and r["actual_next_step"] != inferred_step and r["actual_next_step"] != "ERROR":
            issues.append(f"determinism broken: {r['actual_intent']}→{r['actual_next_step']} (expected {inferred_step})")
        if issues:
            print(f"  [FAIL] Probe #{r['id']}: {'; '.join(issues)}")
            schema_pass = False
        else:
            print(f"  [OK]   Probe #{r['id']}: schema valid")

    print()
    if passed_count == total and schema_pass:
        print("ALL PROBES PASSED.")
    else:
        print(f"RESULT: {passed_count}/{total} probes matched expected behavior.")
        print()
        print("Failures by category:")
        for cat, stats in sorted(category_stats.items(), key=lambda x: x[1]["pass"] / x[1]["total"]):
            if stats["failures"]:
                print(f"  {cat}:")
                for f in stats["failures"]:
                    print(f"    #{f['id']}: expected {f['expected_intent']}→{f['expected_next_step']}, "
                          f"got {f['actual_intent']}→{f['actual_next_step']}")
                    print(f"           Risk: {f['risk_explained'][:80]}")

    return results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    results = run_probes()

    if _args.save_results:
        out_path = REPO_ROOT / (_args.output if _args.output else "probes/probe_results.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n  Results saved to {out_path}")
        print("  Use this file to build failure_taxonomy.md and target_failure_mode.md.")
