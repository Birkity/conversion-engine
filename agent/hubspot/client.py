"""
HubSpot CRM client using the private app token.
Writes contacts and enrichment properties.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

_TOKEN = os.getenv("HUBSPOT_PRIVATE_APP_TOKEN", "")
_BASE = "https://api.hubapi.com"


def _request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def upsert_contact(
    email: str,
    first_name: str,
    last_name: str,
    company: str,
    phone: str = "",
    enrichment: dict | None = None,
) -> dict:
    """Create or update a HubSpot contact with enrichment metadata."""
    ts = datetime.now(timezone.utc).isoformat()
    properties: dict = {
        "email": email,
        "firstname": first_name,
        "lastname": last_name,
        "company": company,
        "phone": phone,
        "enrichment_timestamp": ts,
    }
    if enrichment:
        properties["hs_lead_status"] = "NEW"
        ai_score = enrichment.get("hiring_signal_brief", {}).get("ai_maturity_score")
        if ai_score is not None:
            properties["ai_maturity_score"] = str(ai_score)
        segment = enrichment.get("hiring_signal_brief", {}).get("icp_segment", "")
        if segment:
            properties["icp_segment"] = segment
        confidence = enrichment.get("hiring_signal_brief", {}).get("confidence")
        if confidence is not None:
            properties["enrichment_confidence"] = str(confidence)

    try:
        result = _request("POST", "/crm/v3/objects/contacts", {"properties": properties})
        return {"status": "created", "id": result.get("id"), "email": email}
    except urllib.error.HTTPError as e:
        if e.code == 409:
            # Contact exists — update instead
            error_body = json.loads(e.read())
            existing_id = error_body.get("message", "").split(":")[-1].strip()
            if existing_id:
                result = _request(
                    "PATCH",
                    f"/crm/v3/objects/contacts/{existing_id}",
                    {"properties": properties},
                )
                return {"status": "updated", "id": result.get("id"), "email": email}
        raise


def log_enrichment_note(contact_id: str, enrichment: dict) -> dict:
    """Attach enrichment JSON as a HubSpot note on the contact."""
    brief = enrichment.get("hiring_signal_brief", {})
    note_body = (
        f"Signal Brief — {brief.get('company', 'unknown')}\n"
        f"AI Maturity: {brief.get('ai_maturity_score', '?')}/3\n"
        f"Confidence: {brief.get('confidence', '?')}\n"
        f"ICP Segment: {brief.get('icp_segment', '?')}\n"
        f"Pitch: {brief.get('recommended_pitch_angle', '')}\n"
        f"Enrichment TS: {enrichment.get('enrichment_ts', '')}"
    )
    body = {
        "properties": {"hs_note_body": note_body},
        "associations": [
            {
                "to": {"id": contact_id},
                "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}],
            }
        ],
    }
    result = _request("POST", "/crm/v3/objects/notes", body)
    return {"status": "note_created", "note_id": result.get("id")}
