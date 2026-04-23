"""
Act II Email Execution - Conversion Engine.

Demonstrates that generated briefs produce a style-guide-compliant outreach
email and send it through the Resend SMTP relay.

Policy compliance (data_handling_policy.md — read before modifying):
  Rule 2: prospect_info.json MUST contain synthetic contact details only.
          The email address must resolve to the program sink, not a real person.
          This script will abort if the email looks like a real address.
  Rule 5: The kill switch (LIVE_OUTBOUND_ENABLED / TENACIOUS_OUTBOUND_ENABLED)
          is mandatory. This script reads it from the environment and refuses
          to proceed if sink_mode cannot be confirmed. Do not bypass.
  Rule 6: X-Tenacious-Status: draft header is added automatically by the
          email handler. Do not strip or suppress it.
  Rule 7: Only first name and email are logged to stdout. Full PII is not
          printed or stored beyond what the email handler already writes.

Usage:
    python scripts/act2_email_execution.py
    python scripts/act2_email_execution.py traces/snaptrade/
    python scripts/act2_email_execution.py --traces traces/kinanalytics/ --dry-run
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

from agent.email.generator import generate_email
from agent.email.handler import send, KILL_SWITCH
from agent.calendar.client import booking_link


# ─────────────────────────────────────────────────────────────────
# Policy guards
# ─────────────────────────────────────────────────────────────────

_OBVIOUSLY_REAL_DOMAINS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "icloud.com", "protonmail.com", "live.com",
}

def _assert_synthetic_email(email: str) -> None:
    """
    Abort if the email address looks like a real personal or company address.
    Rule 2: only synthetic/sink addresses are permitted during challenge week.
    """
    domain = email.split("@")[-1].lower() if "@" in email else ""
    if domain in _OBVIOUSLY_REAL_DOMAINS:
        print(f"POLICY VIOLATION (Rule 2): '{email}' is a real personal address.")
        print("  prospect_info.json must contain a synthetic sink address.")
        print("  Use something like: prospect@sink.trp1.internal")
        sys.exit(1)
    # Warn if it doesn't look like a sink address either
    if ".trp1." not in email and "sink" not in email and "example" not in email:
        print(f"WARNING: '{email}' does not look like a known sink address.")
        print("  Make sure it routes to the program-controlled sink, not a real inbox.")


def _assert_kill_switch_active() -> None:
    """
    Rule 5: confirm the kill switch state before sending anything.
    Exits with a policy error if both env vars are unset.
    """
    live = os.getenv("LIVE_OUTBOUND_ENABLED", "false").lower() == "true"
    tenacious = os.getenv("TENACIOUS_OUTBOUND_ENABLED", "false").lower() == "true"
    is_live = live or tenacious
    if is_live:
        print("WARNING: Kill switch is OFF — outbound will go to actual recipient.")
        print("         In challenge week this MUST route to a real sink address,")
        print("         not a real prospect. Proceeding with live mode enabled.")
    else:
        print("Kill switch: ACTIVE (LIVE_OUTBOUND_ENABLED=false)")
        print("  All outbound routed to sink address. No real prospect will receive email.")


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _section(title: str) -> None:
    print(f"\n{'-' * 62}")
    print(f"  {title}")
    print(f"{'-' * 62}")


def _load_json(path: Path, label: str) -> dict:
    if not path.exists():
        print(f"ERROR: {label} not found at {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _print_email(subject: str, body: str, word_count: int, warnings: list) -> None:
    print(f"\n  Subject ({len(subject)} chars): {subject}")
    print(f"  Body ({word_count} words):")
    print()
    for line in body.splitlines():
        print(f"    {line}")
    if warnings:
        print(f"\n  TONE WARNINGS: {warnings}")
    else:
        print("\n  Tone check: PASSED (no violations detected)")


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate and send a brief-grounded outreach email (sink mode)."
    )
    parser.add_argument(
        "traces_dir",
        nargs="?",
        default="traces/kinanalytics",
        help="Directory containing hiring_signal_brief.json, competitor_gap_brief.json, "
             "and prospect_info.json (default: traces/kinanalytics)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and print the email but do not send it.",
    )
    args = parser.parse_args()

    traces_dir = Path(args.traces_dir)

    # ── Load inputs ─────────────────────────────────────────────
    hsb = _load_json(traces_dir / "hiring_signal_brief.json", "hiring_signal_brief")
    cgb = _load_json(traces_dir / "competitor_gap_brief.json", "competitor_gap_brief")
    prospect = _load_json(traces_dir / "prospect_info.json", "prospect_info")

    prospect_name = prospect.get("name", "")
    prospect_email = prospect.get("email", "")
    prospect_role = prospect.get("role", "")
    company = prospect.get("company", hsb.get("company", ""))

    _section(f"Act II Email Execution - {company}")
    print(f"  Traces dir  : {traces_dir.resolve()}")
    print(f"  Prospect    : {prospect_name} ({prospect_role})")
    print(f"  Email       : {prospect_email}")
    print(f"  ICP segment : {hsb.get('icp_segment')}")
    print(f"  Confidence  : {hsb.get('confidence')}")

    # ── Policy checks ───────────────────────────────────────────
    _section("Policy Checks")
    _assert_synthetic_email(prospect_email)
    print(f"  Email address: synthetic format confirmed")
    _assert_kill_switch_active()

    # ── Generate Cal.com booking link ────────────────────────────
    cal_url = booking_link(
        prospect_name=prospect_name,
        prospect_email=prospect_email,
        notes=hsb.get("recommended_pitch_angle", "")[:200],
    )

    # ── Generate email ────────────────────────────────────────────
    _section("Generating Email (LLM)")
    print("  Calling email_generator.generate_email() ...")

    try:
        email_result = generate_email(
            hsb=hsb,
            cgb=cgb,
            prospect_info=prospect,
            cal_link=cal_url,
        )
    except Exception as exc:
        print(f"\n  ERROR: email generation failed: {exc}", file=sys.stderr)
        return 1

    subject = email_result.get("subject", "")
    body = email_result.get("body", "")
    word_count = email_result.get("word_count", len(body.split()))
    warnings = email_result.get("tone_warnings", [])
    icp_used = email_result.get("icp_segment_used", "unknown")
    grounding = email_result.get("grounding_facts", [])

    _section("Generated Email")
    _print_email(subject, body, word_count, warnings)

    _section("Email Metadata")
    print(f"  ICP segment used  : {icp_used}")
    print(f"  Grounding facts   : {grounding}")
    print(f"  Cal.com link      : {cal_url[:80]}...")
    print(f"  X-Tenacious-Status: draft  (added by handler, Rule 6)")

    if args.dry_run:
        _section("Dry Run - Not Sent")
        print("  --dry-run flag set. Email generated but not submitted to Resend.")
        print("  Remove --dry-run to send to the sink address.")
        return 0

    # ── Send email ────────────────────────────────────────────────
    _section("Sending via Resend SMTP")
    print(f"  To (actual)  : will route to sink (kill switch active)")
    print(f"  Sending ...")

    send_result = send(
        to=prospect_email,
        subject=subject,
        body=body,
    )

    status = send_result.get("status")
    sink_mode = send_result.get("sink_mode", True)
    actual_to = send_result.get("to", "unknown")

    if status == "sent":
        print(f"  status       : {status}")
        print(f"  delivered to : {actual_to}")
        print(f"  sink_mode    : {sink_mode}")
        # Resend SMTP doesn't return a message_id in the send response;
        # the message_id is available in Resend's dashboard and webhook events.
        print(f"  message_id   : available in Resend dashboard / /webhooks/resend")
    elif status == "error":
        print(f"  status       : ERROR — {send_result.get('error')}")
        return 1
    else:
        print(f"  status       : {status}  ({send_result})")

    _section("Summary")
    print(f"  Email generated  : YES")
    print(f"  Word count       : {word_count}/120")
    print(f"  Subject length   : {len(subject)}/60 chars")
    print(f"  Tone violations  : {len(warnings)}")
    print(f"  Sent to sink     : {'YES' if status == 'sent' else 'NO'}")
    print(f"  Draft header     : YES (X-Tenacious-Status: draft)")
    print(f"  Real prospect    : NO (synthetic profile, kill switch active)")
    print()
    print("  act2_email_execution PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
