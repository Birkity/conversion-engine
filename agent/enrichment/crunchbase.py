"""
Crunchbase ODM seed data loader.
Reads seeds/crunchbase/crunchbase-companies-information.csv and supports
fuzzy name lookup + field extraction.
"""
import csv
import json
import os
from pathlib import Path

_SEED_PATH = Path(__file__).parents[2] / "seeds" / "crunchbase" / "crunchbase-companies-information.csv"

_cache: list[dict] | None = None


def _load() -> list[dict]:
    global _cache
    if _cache is not None:
        return _cache
    if not _SEED_PATH.exists():
        _cache = []
        return _cache
    with open(_SEED_PATH, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        _cache = list(reader)
    return _cache


def lookup(company_name: str) -> dict | None:
    """Return best-match Crunchbase record for company_name, or None."""
    rows = _load()
    name_lower = company_name.lower().strip()
    for row in rows:
        if row.get("name", "").lower().strip() == name_lower:
            return row
    # Partial match fallback
    for row in rows:
        if name_lower in row.get("name", "").lower():
            return row
    return None


def _parse_json_field(value: str) -> list | dict | None:
    if not value or value.strip() in ("", "[]", "{}"):
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return None


def extract_funding_summary(record: dict) -> str:
    """Human-readable funding summary from a Crunchbase record."""
    total = record.get("funds_total", "") or record.get("funding_rounds", "")
    rounds = _parse_json_field(record.get("funding_rounds_list", ""))
    if not rounds:
        if total:
            return f"Total funding: {total}"
        return "No funding data"
    latest = rounds[-1] if isinstance(rounds, list) and rounds else {}
    return (
        f"{len(rounds)} rounds; latest: {latest.get('funding_type','unknown')} "
        f"${latest.get('money_raised_usd','?')} on {latest.get('announced_on','?')}; "
        f"total: {total or 'unknown'}"
    )


def extract_tech_stack(record: dict) -> list[str]:
    """Return list of detected technologies from BuiltWith field."""
    raw = record.get("builtwith_tech", "")
    parsed = _parse_json_field(raw)
    if isinstance(parsed, list):
        return [str(t.get("name", t)) if isinstance(t, dict) else str(t) for t in parsed[:20]]
    if isinstance(raw, str) and raw:
        return [t.strip() for t in raw.split(",") if t.strip()][:20]
    return []


def extract_industries(record: dict) -> list[str]:
    raw = record.get("industries", "")
    parsed = _parse_json_field(raw)
    if isinstance(parsed, list):
        return [str(t.get("value", t)) if isinstance(t, dict) else str(t) for t in parsed]
    return [raw] if raw else []


def extract_layoff_signal(record: dict) -> str:
    raw = record.get("layoff", "")
    parsed = _parse_json_field(raw)
    if parsed:
        return str(parsed)
    return raw or "No layoff signal in Crunchbase record"


def extract_leadership_changes(record: dict) -> str:
    raw = record.get("leadership_hire", "")
    parsed = _parse_json_field(raw)
    if parsed:
        return str(parsed)
    return raw or "No leadership change signal detected"
