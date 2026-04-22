"""
Cal.com calendar client.
Reads event type info and generates booking link with pre-filled prospect details.
"""
import json
import os
import urllib.parse
import urllib.request

from dotenv import load_dotenv

load_dotenv()

_API_KEY = os.getenv("CALCOM_API_KEY", "")
_BASE_URL = os.getenv("CALCOM_BASE_URL", "https://cal.com").rstrip("/")
_EVENT_URL = os.getenv("CALCOM_EVENT_URL", "")
_API_BASE = "https://api.cal.com/v2"


def _api_get(path: str) -> dict:
    url = f"{_API_BASE}{path}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {_API_KEY}", "cal-api-version": "2026-02-25"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def booking_link(
    prospect_name: str,
    prospect_email: str,
    notes: str = "",
) -> str:
    """
    Return a pre-filled Cal.com booking URL for the prospect.
    Appends query params so the booking form is pre-populated.
    """
    base = _EVENT_URL or f"{_BASE_URL}/birkity-famsl2/intro-call-engineering-scaling"
    params = {
        "name": prospect_name,
        "email": prospect_email,
    }
    if notes:
        params["notes"] = notes[:200]
    return f"{base}?{urllib.parse.urlencode(params)}"


def get_upcoming_slots(event_type_slug: str = "", days: int = 7) -> dict:
    """Fetch upcoming available slots via Cal.com API v2."""
    try:
        data = _api_get("/event-types")
        event_types = data.get("data", {}).get("eventTypeGroups", [])
        return {"status": "ok", "event_types": event_types}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def send_booking_invite(
    prospect_name: str,
    prospect_email: str,
    hiring_brief: dict,
) -> str:
    """Generate a contextual booking link with signal-based notes."""
    pitch = hiring_brief.get("recommended_pitch_angle", "engineering scaling")
    ai_score = hiring_brief.get("ai_maturity_score", 0)
    notes = f"Signal-grounded: AI maturity {ai_score}/3. Topic: {pitch}"
    return booking_link(prospect_name, prospect_email, notes)
