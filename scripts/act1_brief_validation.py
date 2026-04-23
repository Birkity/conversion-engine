"""
Act I Brief Validation — Conversion Engine.

Demonstrates that raw company signals are converted into two structured,
policy-compliant intelligence briefs by the brief_generator module.

Policy compliance:
  - Reads only signals derived from public Crunchbase, public job posts,
    and public layoffs.fyi data. No personal contact data is read or written.
  - All output files carry tenacious_status="draft" (Rule 5).
  - No outbound is triggered. This script is read-and-generate only.

Usage:
    python scripts/act1_brief_validation.py
    python scripts/act1_brief_validation.py traces/kinanalytics/signals.json
    python scripts/act1_brief_validation.py traces/snaptrade/signals.json --outdir out/snaptrade
"""
import argparse
import json
import sys
from pathlib import Path

# Ensure project root is importable regardless of working directory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Windows terminals default to cp1252; reconfigure stdout to UTF-8 so LLM
# output containing em-dashes and other Unicode prints cleanly.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

from agent.brief_generator import generate


# ─────────────────────────────────────────────────────────────────
# Required fields validation
# ─────────────────────────────────────────────────────────────────

_REQUIRED_SIGNAL_FIELDS = [
    "company_name", "industries", "headcount", "funding_info",
    "layoffs", "jobs_now", "jobs_60_days", "tech_stack", "ai_roles",
]

_REQUIRED_HSB_FIELDS = [
    "company", "hiring_velocity", "ai_maturity_score",
    "ai_maturity_rationale", "confidence", "icp_segment",
    "recommended_pitch_angle", "bench_match", "honesty_flags",
]

_REQUIRED_CGB_FIELDS = [
    "sector", "competitors_analyzed", "prospect_ai_score",
    "prospect_position_in_sector", "gaps", "overall_confidence",
]


def _validate_signals(signals: dict) -> list[str]:
    return [f for f in _REQUIRED_SIGNAL_FIELDS if f not in signals]


def _validate_hsb(hsb: dict) -> list[str]:
    return [f for f in _REQUIRED_HSB_FIELDS if f not in hsb]


def _validate_cgb(cgb: dict) -> list[str]:
    return [f for f in _REQUIRED_CGB_FIELDS if f not in cgb]


# ─────────────────────────────────────────────────────────────────
# Formatted printing helpers
# ─────────────────────────────────────────────────────────────────

def _section(title: str) -> None:
    print(f"\n{'-' * 60}")
    print(f"  {title}")
    print(f"{'-' * 60}")


def _print_hsb_summary(hsb: dict) -> None:
    velocity = hsb.get("hiring_velocity", {})
    budget = hsb.get("budget_urgency", {})
    cost = hsb.get("cost_pressure", {})
    eng = hsb.get("engineering_maturity", {})
    ai_r = hsb.get("ai_maturity_rationale", {})
    bench = hsb.get("bench_match", {})
    flags = hsb.get("honesty_flags", {})

    print(f"  Company            : {hsb.get('company')}")
    print(f"  ICP Segment        : {hsb.get('icp_segment')}")
    print(f"  Confidence         : {hsb.get('confidence')}")
    print(f"  AI Maturity Score  : {hsb.get('ai_maturity_score')}/3")
    print(f"  Draft status       : {hsb.get('tenacious_status', 'MISSING — policy violation')}")
    print()
    print(f"  Hiring velocity    : {velocity.get('direction')}  "
          f"(delta {velocity.get('delta_pct')}%, "
          f"strength: {velocity.get('signal_strength')})")
    print(f"    -> {velocity.get('observation')}")
    print()
    print(f"  Budget urgency     : {budget.get('level')}  —  {budget.get('signal')}")
    print(f"  Cost pressure      : present={cost.get('present')}  —  {cost.get('signal')}")
    print(f"  Stack sophistication: {eng.get('stack_sophistication')}")
    print(f"  Bench match        : available={bench.get('bench_available')}  "
          f"required={bench.get('required_stacks')}")
    print()
    print(f"  AI maturity inputs :")
    print(f"    AI roles found   : {ai_r.get('ai_roles_found')}")
    print(f"    ML stack signals : {ai_r.get('modern_ml_stack_signals')}")
    print(f"    Exec AI signals  : {ai_r.get('executive_ai_signals')}")
    print(f"    Named AI leader  : {ai_r.get('named_ai_leadership')}")
    print()
    print(f"  Honesty flags      : {flags}")
    print()
    print(f"  Pitch angle:")
    print(f"    {hsb.get('recommended_pitch_angle')}")


def _print_cgb_summary(cgb: dict) -> None:
    gaps = cgb.get("gaps", [])
    print(f"  Sector             : {cgb.get('sector')}")
    print(f"  Competitors scored : {cgb.get('competitors_analyzed')}")
    print(f"  Prospect AI score  : {cgb.get('prospect_ai_score')}/3")
    print(f"  Sector position    : {cgb.get('prospect_position_in_sector')}")
    print(f"  Overall confidence : {cgb.get('overall_confidence')}")
    print(f"  Draft status       : {cgb.get('tenacious_status', 'MISSING — policy violation')}")
    print()
    for i, gap in enumerate(gaps, 1):
        print(f"  Gap {i}: {gap.get('practice')}")
        print(f"    Top quartile  : {gap.get('evidence_in_top_quartile')}")
        print(f"    At prospect   : {gap.get('evidence_at_prospect')}")
        print(f"    Insight       : {gap.get('gap_insight')}")
        print(f"    Confidence    : {gap.get('confidence')}")
        print()


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate brief generation from a signals.json file."
    )
    parser.add_argument(
        "signals_file",
        nargs="?",
        default="traces/kinanalytics/signals.json",
        help="Path to signals.json (default: traces/kinanalytics/signals.json)",
    )
    parser.add_argument(
        "--outdir",
        default=None,
        help="Directory to save output briefs (default: same folder as signals.json)",
    )
    args = parser.parse_args()

    signals_path = Path(args.signals_file)
    if not signals_path.exists():
        print(f"ERROR: signals file not found: {signals_path}", file=sys.stderr)
        return 1

    with open(signals_path, encoding="utf-8") as f:
        signals = json.load(f)

    company = signals.get("company_name", signals_path.parent.name)

    _section(f"Act I Brief Validation - {company}")
    print(f"  Signals file : {signals_path.resolve()}")
    print(f"  Policy       : public signals only; output marked tenacious_status=draft")

    # Validate input fields
    missing_input = _validate_signals(signals)
    if missing_input:
        print(f"\n  WARNING: signals.json is missing fields: {missing_input}")
        print(  "  Brief quality may be reduced.")

    print(f"\n  competitor_signals : {len(signals.get('competitor_signals', []))} records")
    print(f"  jobs_now           : {signals.get('jobs_now')}")
    print(f"  jobs_60_days       : {signals.get('jobs_60_days')}")
    print(f"  tech_stack         : {signals.get('tech_stack')}")
    print(f"  ai_roles           : {signals.get('ai_roles')}")
    print(f"\n  Calling brief_generator.generate() ...")

    # ── Generate ────────────────────────────────────────────────
    try:
        result = generate(signals)
    except Exception as exc:
        print(f"\nERROR: brief_generator failed: {exc}", file=sys.stderr)
        return 1

    hsb = result.get("hiring_signal_brief", {})
    cgb = result.get("competitor_gap_brief", {})

    # ── Validate outputs ────────────────────────────────────────
    hsb_missing = _validate_hsb(hsb)
    cgb_missing = _validate_cgb(cgb)

    # ── Save outputs ────────────────────────────────────────────
    out_dir = Path(args.outdir) if args.outdir else signals_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    hsb_path = out_dir / "hiring_signal_brief.json"
    cgb_path = out_dir / "competitor_gap_brief.json"

    with open(hsb_path, "w", encoding="utf-8") as f:
        json.dump(hsb, f, indent=2)
    with open(cgb_path, "w", encoding="utf-8") as f:
        json.dump(cgb, f, indent=2)

    # ── Print hiring signal brief summary ───────────────────────
    _section("Hiring Signal Brief")
    _print_hsb_summary(hsb)
    if hsb_missing:
        print(f"  VALIDATION FAILURES: missing fields {hsb_missing}")

    # ── Print competitor gap brief summary ───────────────────────
    _section("Competitor Gap Brief")
    _print_cgb_summary(cgb)
    if cgb_missing:
        print(f"  VALIDATION FAILURES: missing fields {cgb_missing}")

    # ── Confidence summary ───────────────────────────────────────
    _section("Confidence Summary")
    print(f"  hiring_signal_brief.confidence   : {hsb.get('confidence')}")
    print(f"  competitor_gap_brief.overall_confidence : {cgb.get('overall_confidence')}")
    gap_confidences = [g.get('confidence') for g in cgb.get('gaps', []) if 'confidence' in g]
    if gap_confidences:
        print(f"  per-gap confidence scores        : {gap_confidences}")

    # ── Output paths ─────────────────────────────────────────────
    _section("Output Files")
    print(f"  {hsb_path.resolve()}")
    print(f"  {cgb_path.resolve()}")
    print(f"\n  tenacious_status (hsb): {hsb.get('tenacious_status')}")
    print(f"  tenacious_status (cgb): {cgb.get('tenacious_status')}")

    # ── Pass / Fail ──────────────────────────────────────────────
    print()
    all_good = not hsb_missing and not cgb_missing
    if all_good:
        print("  act1_brief_validation PASSED — all required fields present")
        return 0
    else:
        print(f"  act1_brief_validation FAILED — missing fields in output")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
