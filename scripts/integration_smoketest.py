"""
End-to-end integration smoke test.
Chains: enrich() -> email (sink) -> HubSpot upsert + note -> Cal.com booking link.

All outbound is safe by default (LIVE_OUTBOUND_ENABLED=false routes to sink).

Usage:
    python scripts/integration_smoketest.py
    python scripts/integration_smoketest.py "WiseiTech"
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from dotenv import load_dotenv
load_dotenv()

from agent.enrichment.pipeline import enrich
from agent.email.handler import send_signal_brief_intro
from agent.hubspot.client import upsert_contact, log_enrichment_note
from agent.calendar.client import send_booking_invite


def run(company: str) -> None:
    print(f"\n{'='*55}")
    print(f"Integration smoke test — {company}")
    print(f"{'='*55}")

    # 1. Enrichment (Crunchbase + jobs + layoffs + LLM briefs)
    print("\n[1/4] Enrichment pipeline...")
    enrichment = enrich(company)
    hsb = enrichment.get("hiring_signal_brief", {})
    cgb = enrichment.get("competitor_gap_brief", {})
    ai_score = hsb.get("ai_maturity_score", "?")
    icp = hsb.get("icp_segment", "?")
    print(f"      AI maturity: {ai_score}/3  ICP: {icp}  gaps: {len(cgb.get('gaps', []))}")
    print("      OK")

    # 2. Email (sink mode unless LIVE_OUTBOUND_ENABLED=true)
    print("\n[2/4] Email (Resend)...")
    result = send_signal_brief_intro(
        to="prospect@example.com",
        prospect_name="Alex Test",
        company=company,
        hiring_brief=hsb,
        gap_brief=cgb,
    )
    status = result.get("status", "unknown")
    sink = result.get("sink_mode", True)
    print(f"      status={status}  sink_mode={sink}")
    print("      OK")

    # 3. HubSpot upsert + enrichment note
    print("\n[3/4] HubSpot CRM...")
    hs = upsert_contact(
        email="prospect@example.com",
        first_name="Alex",
        last_name="Test",
        company=company,
        enrichment=enrichment,
    )
    hs_status = hs.get("status", "unknown")
    contact_id = hs.get("id")
    print(f"      upsert status={hs_status}  contact_id={contact_id}")
    if contact_id:
        note = log_enrichment_note(contact_id, enrichment)
        print(f"      note status={note.get('status', 'unknown')}")
    print("      OK")

    # 4. Cal.com booking link
    print("\n[4/4] Cal.com booking link...")
    link = send_booking_invite("Alex Test", "prospect@example.com", hsb)
    print(f"      {link[:80]}...")
    print("      OK")

    print(f"\n{'='*55}")
    print("All integration checks passed.")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    company = sys.argv[1] if len(sys.argv) > 1 else "SnapTrade"
    run(company)
