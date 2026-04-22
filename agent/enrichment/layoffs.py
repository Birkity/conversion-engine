"""
layoffs.fyi CSV signal extractor.
Reads seeds/layoffs/layoffs_data.csv.
"""
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

_LAYOFFS_PATH = Path(__file__).parents[2] / "seeds" / "layoffs" / "layoffs_data.csv"

_WINDOW_DAYS = 120


def _within_window(date_str: str, days: int = _WINDOW_DAYS) -> bool:
    if not date_str:
        return False
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return dt >= cutoff
    except ValueError:
        return False


def lookup(company_name: str) -> list[dict]:
    """Return all layoff events for company_name within the last 120 days."""
    if not _LAYOFFS_PATH.exists():
        return []
    name_lower = company_name.lower().strip()
    matches = []
    with open(_LAYOFFS_PATH, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Company", "").lower().strip() == name_lower:
                if _within_window(row.get("Date", "")):
                    matches.append(row)
    return matches


def summary(company_name: str) -> str:
    """Human-readable layoff summary for signal brief."""
    events = lookup(company_name)
    if not events:
        return "No layoff events found in last 120 days"
    parts = []
    for ev in events:
        count = ev.get("Laid_Off_Count", "unknown")
        pct = ev.get("Percentage", "")
        date = ev.get("Date", "unknown date")
        stage = ev.get("Stage", "")
        pct_str = f" ({float(pct)*100:.0f}%)" if pct else ""
        parts.append(f"{count} employees laid off{pct_str} on {date} [{stage}]")
    return "; ".join(parts)
