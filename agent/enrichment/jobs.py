"""
Job post signal extractor.
Queries the LinkedIn job postings seed CSV for a given company.
Falls back gracefully when the 493MB file is not present (gitignored).
"""
import csv
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

_JOBS_PATH = Path(__file__).parents[2] / "seeds" / "job_posts" / "linkedinjobs_postings.csv"

_AI_TITLE_KEYWORDS = {
    "machine learning", "ml engineer", "ai engineer", "llm", "applied scientist",
    "data scientist", "nlp", "computer vision", "deep learning", "ai product",
    "ml platform", "model", "inference", "mlops", "generative", "foundation model",
}


def _is_ai_role(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in _AI_TITLE_KEYWORDS)


def _cutoff_ts(days_ago: int) -> float:
    """Unix milliseconds for N days ago."""
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.timestamp() * 1000


def count_jobs(company_name: str, days: int = 0) -> int:
    """
    Count job posts for company_name in the last `days` days.
    days=0 returns all-time count. Returns -1 if data file absent.
    """
    if not _JOBS_PATH.exists():
        return -1
    name_lower = company_name.lower().strip()
    cutoff = _cutoff_ts(days) if days else 0
    count = 0
    with open(_JOBS_PATH, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("company_name", "").lower().strip() != name_lower:
                continue
            if cutoff:
                try:
                    listed = float(row.get("listed_time") or 0)
                except ValueError:
                    listed = 0
                if listed < cutoff:
                    continue
            count += 1
    return count


def get_ai_roles(company_name: str, days: int = 90) -> list[str]:
    """Return distinct AI/ML-related job titles posted in the last `days` days."""
    if not _JOBS_PATH.exists():
        return []
    name_lower = company_name.lower().strip()
    cutoff = _cutoff_ts(days)
    titles: set[str] = set()
    with open(_JOBS_PATH, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("company_name", "").lower().strip() != name_lower:
                continue
            try:
                listed = float(row.get("listed_time") or 0)
            except ValueError:
                listed = 0
            if listed < cutoff:
                continue
            title = row.get("title", "")
            if _is_ai_role(title):
                titles.add(title)
    return sorted(titles)[:15]


def job_velocity_summary(company_name: str) -> dict:
    """
    Returns dict with jobs_now (last 30d), jobs_60_days (30-90d window),
    ai_roles (last 90d), data_available, and source.
    Tries Playwright public scrape first; falls back to seed CSV.
    """
    try:
        from agent.enrichment.jobs_playwright import scrape_job_velocity
        result = scrape_job_velocity(company_name)
        if result.get("data_available"):
            result["ai_roles"] = get_ai_roles(company_name, days=90)
            return result
    except Exception:
        pass

    # Fallback: seed CSV (gitignored; -1 when absent)
    jobs_now = count_jobs(company_name, days=30)
    jobs_90 = count_jobs(company_name, days=90)
    jobs_older = (jobs_90 - jobs_now) if jobs_now >= 0 else -1
    ai_roles = get_ai_roles(company_name, days=90)
    return {
        "jobs_now": jobs_now,
        "jobs_60_days": max(jobs_older, 0) if jobs_older >= 0 else -1,
        "ai_roles": ai_roles,
        "data_available": jobs_now >= 0,
        "source": "seed_csv",
        "confidence": 0.9 if jobs_now >= 0 else 0.0,
    }
