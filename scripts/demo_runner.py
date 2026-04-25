"""
Demo runner — Conversion Engine.

Executes multi-turn conversation scenarios through the real
interpret_reply() + route_decision() pipeline. Demonstrates 4 scenarios:

  arcana_skeptic   — Skeptical signal challenge → clarification → Cal link (2 turns)
  pulsesight_sms   — Bench question → SEND_EMAIL, then SMS scheduling (2 turns + SMS)
  novaspark_fast   — Segment 3 leadership transition, immediate Cal link (1 turn)
  coraltech_stop   — Explicit NOT_INTERESTED → STOP → HubSpot UNQUALIFIED (1 turn)

All outbound (email + SMS) routes to configured sinks (LIVE_OUTBOUND_ENABLED=false).

Usage:
  python scripts/demo_runner.py                   # all 4 scenarios
  python scripts/demo_runner.py arcana_skeptic    # single scenario by ID
  python scripts/demo_runner.py pulsesight_sms    # single scenario
  python scripts/demo_runner.py --dry-run         # no sends, no HubSpot writes
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

from agent.reply_interpreter.reply_interpreter import interpret_reply
from agent.reply_interpreter.router import route_decision
from agent.email.generator import generate_email
from agent.email.handler import send as send_email
from agent.sms.handler import send as send_sms
import agent.hubspot.client as hs

# ── ANSI colours ──────────────────────────────────────────────────────────────
C = "\033[96m"   # cyan
G = "\033[92m"   # green
Y = "\033[93m"   # yellow
R = "\033[91m"   # red
B = "\033[1m"    # bold
X = "\033[0m"    # reset


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_briefs(traces_dir: Path) -> dict:
    hsb = json.loads((traces_dir / "hiring_signal_brief.json").read_text(encoding="utf-8"))
    cgb_path = traces_dir / "competitor_gap_brief.json"
    cgb = json.loads(cgb_path.read_text(encoding="utf-8")) if cgb_path.exists() else {}
    return {"hiring_signal_brief": hsb, "competitor_gap_brief": cgb}


def _load_prospect(traces_dir: Path) -> dict:
    return json.loads((traces_dir / "prospect_info.json").read_text(encoding="utf-8"))


def _generate_and_send_email(
    traces_dir: Path,
    briefs: dict,
    prospect_info: dict,
    dry_run: bool,
) -> dict:
    """Generate outbound email, optionally send + upsert HubSpot. Returns last_email dict."""
    artifact_dir = ROOT / "artifacts" / traces_dir.name
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "last_email.json"

    # Reuse existing artifact to skip the LLM generation call on re-runs,
    # but always send + upsert HubSpot when not in dry_run mode.
    if artifact_path.exists():
        existing = json.loads(artifact_path.read_text(encoding="utf-8"))
        if existing.get("company") == prospect_info["company"]:
            last_email = {"subject": existing["subject"], "body": existing["body"]}
            if not dry_run:
                send_email(
                    to=prospect_info["email"],
                    subject=existing["subject"],
                    body=existing["body"],
                )
                hs.upsert_contact(
                    email=prospect_info["email"],
                    first_name=prospect_info["name"].split()[0],
                    last_name=prospect_info["name"].split()[-1],
                    company=prospect_info["company"],
                    phone=prospect_info.get("phone", ""),
                    enrichment=briefs,
                )
            return last_email

    hsb = briefs["hiring_signal_brief"]
    cgb = briefs.get("competitor_gap_brief", {})
    result = generate_email(hsb, cgb, prospect_info)
    last_email = {"subject": result["subject"], "body": result["body"]}

    if not dry_run:
        send_email(
            to=prospect_info["email"],
            subject=result["subject"],
            body=result["body"],
        )
        hs.upsert_contact(
            email=prospect_info["email"],
            first_name=prospect_info["name"].split()[0],
            last_name=prospect_info["name"].split()[-1],
            company=prospect_info["company"],
            phone=prospect_info.get("phone", ""),
            enrichment=briefs,
        )

    artifact_path.write_text(
        json.dumps(
            {
                **last_email,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "company": prospect_info["company"],
                "icp_segment_used": result.get("icp_segment_used", ""),
                "word_count": result.get("word_count", 0),
                "tone_warnings": result.get("tone_warnings", []),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return last_email


# ── Core scenario runner ──────────────────────────────────────────────────────

def run_scenario(scenario: dict, dry_run: bool) -> list[dict]:
    """Run all reply turns for one scenario. Returns conversation log entries."""
    traces_dir = ROOT / scenario["traces_dir"]
    briefs = _load_briefs(traces_dir)
    prospect_info = _load_prospect(traces_dir)
    conversation: list[dict] = []

    print(f"\n{'=' * 72}")
    print(f"{B}SCENARIO: {scenario['id']}{X}  |  {scenario['company']}")
    print(f"  Segment : {scenario.get('segment', '—')}")
    print(f"  {scenario['description']}")
    print(f"{'=' * 72}")

    # ── Step 0: outbound email ─────────────────────────────────────────────────
    print(f"\n{C}[OUTBOUND EMAIL]{X}")
    last_email = _generate_and_send_email(traces_dir, briefs, prospect_info, dry_run)
    print(f"  Subject : {last_email['subject']}")
    body_preview = last_email["body"].replace("\n", " ").strip()[:140]
    print(f"  Body    : {body_preview}…")
    print(f"  → {'(dry-run) not sent' if dry_run else 'Sent to sink (kill switch active)'}")
    conversation.append({
        "turn": 0,
        "from": "agent",
        "type": "outbound_email",
        "subject": last_email["subject"],
        "body": last_email["body"],
    })

    # ── Steps 1-N: reply turns ────────────────────────────────────────────────
    for reply_def in scenario["replies"]:
        turn = reply_def["turn"]
        reply_text = reply_def["text"]

        print(f"\n{Y}[PROSPECT REPLY — Turn {turn}]{X}")
        print(f"  \"{reply_text}\"")

        # Interpret
        decision = interpret_reply(reply_text, last_email, briefs, prospect_info)

        intent_color = G if decision["intent"] in ("INTERESTED", "SCHEDULE") else (
            R if decision["intent"] == "NOT_INTERESTED" else Y
        )
        match_mark = (
            "✓" if decision["intent"] == reply_def.get("expected_intent")
            and decision["next_step"] == reply_def.get("expected_next_step")
            else "~"
        )
        print(f"\n{C}[AGENT INTERPRETATION]  {match_mark}{X}")
        print(f"  {intent_color}Intent   : {decision['intent']}{X}")
        print(f"  Next step: {decision['next_step']}   Confidence: {decision['confidence']:.0%}")
        print(f"  Reasoning: {decision['reasoning'][:220].strip()}")
        if decision.get("grounding_facts_used"):
            for fact in decision["grounding_facts_used"][:3]:
                print(f"    · {fact}")

        # Route
        route_result: dict = {}
        if not dry_run:
            route_result = route_decision(decision, prospect_info, briefs, last_email)
            print(f"\n{C}[ROUTING ACTIONS]{X}")
            for action in route_result.get("actions", []):
                print(f"  ✓ {action}")
            if route_result.get("errors"):
                for err in route_result["errors"]:
                    print(f"  {R}✗ {err}{X}")
            if route_result.get("cal_link"):
                print(f"  Cal link : {route_result['cal_link']}")
        else:
            print(f"\n{C}[ROUTING ACTIONS]{X}  (dry-run — skipped)")

        # SMS warm-lead leg
        if reply_def.get("also_send_sms") and not dry_run:
            cal_url = route_result.get("cal_link") or os.getenv("CALCOM_EVENT_URL", "[cal link]")
            first_name = prospect_info["name"].split()[0]
            sms_body = f"Hi {first_name}, scheduling link as requested: {cal_url}"
            sms_result = send_sms(
                to=prospect_info.get("phone", ""),
                message=sms_body,
                warm_lead=True,
            )
            print(f"\n{C}[SMS — warm-lead leg]{X}")
            print(f"  To     : {prospect_info.get('phone')} (AT sandbox → smoke-test sink)")
            print(f"  Message: {sms_body[:120]}")
            print(f"  Status : {sms_result.get('status')}")
            if sms_result.get("error"):
                print(f"  {R}Error  : {sms_result['error']}{X}")
        elif reply_def.get("also_send_sms") and dry_run:
            print(f"\n{C}[SMS — warm-lead leg]{X}  (dry-run — skipped)")

        # Persist log entry
        conversation.append({
            "turn": turn,
            "from": "prospect",
            "reply_text": reply_text,
            "expected_intent": reply_def.get("expected_intent"),
            "expected_next_step": reply_def.get("expected_next_step"),
            "interpretation": {
                "intent": decision["intent"],
                "next_step": decision["next_step"],
                "confidence": decision["confidence"],
                "reasoning": decision["reasoning"],
                "grounding_facts_used": decision.get("grounding_facts_used", []),
            },
            "routing": {
                "actions": route_result.get("actions", []),
                "errors": route_result.get("errors", []),
                "cal_link": route_result.get("cal_link"),
            } if route_result else {},
            "sms_sent": reply_def.get("also_send_sms", False) and not dry_run,
        })

        # Advance last_email context for next turn
        if decision["next_step"] in ("SEND_EMAIL", "ASK_CLARIFICATION"):
            last_email = {
                "subject": f"Re: {last_email.get('subject', '')}",
                "body": f"[Tenacious follow-up — {decision['next_step']} — turn {turn}]",
            }

    return conversation


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Run demo conversation scenarios.")
    parser.add_argument(
        "scenario_id",
        nargs="?",
        help="ID of a single scenario to run (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate emails but skip all sends and HubSpot writes.",
    )
    args = parser.parse_args()

    scenarios_path = ROOT / "demo" / "scenarios.json"
    all_scenarios: list[dict] = json.loads(scenarios_path.read_text(encoding="utf-8"))["scenarios"]

    if args.scenario_id:
        selected = [s for s in all_scenarios if s["id"] == args.scenario_id]
        if not selected:
            print(f"No scenario with id '{args.scenario_id}'")
            print(f"Available: {[s['id'] for s in all_scenarios]}")
            sys.exit(1)
    else:
        selected = all_scenarios

    all_logs: list[dict] = []
    for scenario in selected:
        conv = run_scenario(scenario, dry_run=args.dry_run)
        all_logs.append({
            "scenario_id": scenario["id"],
            "company": scenario["company"],
            "segment": scenario.get("segment", ""),
            "description": scenario["description"],
            "conversation": conv,
            "ran_at": datetime.now(timezone.utc).isoformat(),
        })

    # Save log
    log_path = ROOT / "demo" / "demo_log.json"
    log_path.write_text(json.dumps(all_logs, indent=2, default=str), encoding="utf-8")

    # Summary table
    print(f"\n{'=' * 72}")
    print(f"{B}DEMO SUMMARY{X}")
    for entry in all_logs:
        turns = [t for t in entry["conversation"] if t["from"] == "prospect"]
        routing = [t["interpretation"]["next_step"] for t in turns if "interpretation" in t]
        sms_flags = [t.get("sms_sent", False) for t in turns]
        sms_note = "  📱 SMS sent" if any(sms_flags) else ""
        print(f"  {entry['scenario_id']:<22} → {routing}{sms_note}")
    print(f"\n  Log saved : demo/demo_log.json")
    print(f"  Scenarios : {len(all_logs)}")


if __name__ == "__main__":
    main()
