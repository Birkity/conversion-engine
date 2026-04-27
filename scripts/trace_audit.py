#!/usr/bin/env python3
"""Scan traces/* and optionally bootstrap missing briefs/prospect_info.

Usage:
  python scripts/trace_audit.py [--bootstrap] [--report PATH]

The script enumerates all known slugs (builtins + custom), reports which
Act II files are present, and when --bootstrap is passed will call the
conversation_manager._ensure_trace_context(slug) helper to regenerate
missing briefs and a synthetic prospect safely.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from agent import conversation_manager as cm
except Exception as exc:  # pragma: no cover - best-effort import for repo context
    print("ERROR: failed to import agent.conversation_manager:", exc)
    sys.exit(2)


def check_slug(slug: str, bootstrap: bool = False) -> dict[str, Any]:
    traces = cm._traces_path(slug)
    traces.mkdir(parents=True, exist_ok=True)

    hsb_path = traces / cm._HIRING_BRIEF_FILE
    cgb_path = traces / cm._COMPETITOR_GAP_FILE
    prospect_path = traces / cm._PROSPECT_INFO_FILE

    present = {
        "hiring_signal_brief": hsb_path.exists(),
        "competitor_gap_brief": cgb_path.exists(),
        "prospect_info": prospect_path.exists(),
    }

    result: dict[str, Any] = {"slug": slug, "present": present, "bootstrapped": False, "notes": []}

    if all(present.values()):
        return result

    if not bootstrap:
        missing = [k for k, v in present.items() if not v]
        result["notes"].append(f"missing: {', '.join(missing)}")
        return result

    # Attempt to regenerate using conversation_manager helper.
    try:
        hsb, cgb, prospect = cm._ensure_trace_context(slug)
        result["bootstrapped"] = True
        result["present"] = {
            "hiring_signal_brief": bool(hsb),
            "competitor_gap_brief": bool(cgb),
            "prospect_info": bool(prospect),
        }
    except Exception as exc:
        result["notes"].append(f"bootstrap failed: {exc}")

    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Trace audit + optional bootstrap for conversion-engine.")
    p.add_argument("--bootstrap", action="store_true", help="Attempt to regenerate missing briefs/prospect_info.")
    p.add_argument("--report", default="scripts/trace_audit_report.json", help="Path to write JSON report.")
    args = p.parse_args(argv)

    slugs = []
    try:
        slugs = cm.get_all_slugs()
    except Exception:
        # Fallback: inspect traces/ directory directly
        root = Path(__file__).resolve().parents[1]
        traces_dir = root / "traces"
        if traces_dir.exists():
            slugs = [p.name for p in traces_dir.iterdir() if p.is_dir()]

    if not slugs:
        print("No slugs found to audit.")
        return 1

    report = []
    for slug in slugs:
        print(f"Checking {slug}...")
        r = check_slug(slug, bootstrap=args.bootstrap)
        report.append(r)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Summary
    total = len(report)
    missing = [r for r in report if not all(r["present"].values())]
    print("\nTrace audit complete:")
    print(f"  slugs checked: {total}")
    print(f"  slugs with missing files: {len(missing)}")
    print(f"  detailed report written to: {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
