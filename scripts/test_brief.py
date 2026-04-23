"""
CLI test for agent/brief_generator.
Signals live at traces/<company>/signals.json.
Briefs are saved to traces/<company>/hiring_signal_brief.json
                  and traces/<company>/competitor_gap_brief.json.

Usage:
    python scripts/test_brief.py snaptrade
    python scripts/test_brief.py wiseitech
    python scripts/test_brief.py path/to/any/signals.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from dotenv import load_dotenv
load_dotenv()

from agent.brief_generator import generate


def resolve_signals_path(arg: str) -> Path:
    """Accept a company name or an explicit file path."""
    p = Path(arg)
    # If it's an existing file, use it directly
    if p.suffix == ".json" and p.exists():
        return p
    # Otherwise treat as a company name → traces/<company>/signals.json
    candidate = Path("traces") / arg.lower().replace(" ", "_") / "signals.json"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"No signals.json found for '{arg}'.\n"
        f"Expected: {candidate.resolve()}\n"
        f"Create it or pass an explicit path."
    )


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else "snaptrade"
    try:
        signals_path = resolve_signals_path(arg)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    with open(signals_path, encoding="utf-8") as f:
        signals = json.load(f)

    company = signals.get("company_name", arg)
    print(f"Running brief generator for: {company}", file=sys.stderr)
    print(f"Signals file: {signals_path}", file=sys.stderr)

    result = generate(signals)

    hsb = result.get("hiring_signal_brief", {})
    cgb = result.get("competitor_gap_brief", {})

    # Save to the same traces/<company>/ folder as the signals
    out_dir = signals_path.parent
    hsb_path = out_dir / "hiring_signal_brief.json"
    cgb_path = out_dir / "competitor_gap_brief.json"

    with open(hsb_path, "w", encoding="utf-8") as f:
        json.dump(hsb, f, indent=2)
    with open(cgb_path, "w", encoding="utf-8") as f:
        json.dump(cgb, f, indent=2)

    print(json.dumps(result, indent=2))

    # Assertions
    assert "hiring_velocity" in hsb, "hiring_signal_brief missing hiring_velocity"
    assert "ai_maturity_score" in hsb, "hiring_signal_brief missing ai_maturity_score"
    assert "confidence" in hsb, "hiring_signal_brief missing confidence"
    assert "gaps" in cgb, "competitor_gap_brief missing gaps"
    assert "overall_confidence" in cgb, "competitor_gap_brief missing overall_confidence"

    print(f"\nAI maturity : {hsb.get('ai_maturity_score')}/3", file=sys.stderr)
    print(f"Confidence  : {hsb.get('confidence')}", file=sys.stderr)
    print(f"ICP segment : {hsb.get('icp_segment')}", file=sys.stderr)
    print(f"Gaps found  : {len(cgb.get('gaps', []))}", file=sys.stderr)
    print(f"Saved       : {hsb_path}", file=sys.stderr)
    print(f"            : {cgb_path}", file=sys.stderr)
    print("test_brief.py PASSED", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
