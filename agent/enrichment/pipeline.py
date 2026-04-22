"""
Enrichment pipeline orchestrator.
Chains: Crunchbase → Jobs → Layoffs → Maturity pre-score → LLM signal brief.

Usage:
    from agent.enrichment.pipeline import enrich
    result = enrich("Acme Corp")
    # result contains: crunchbase_record, hiring_signal_brief, competitor_gap_brief
"""
import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from agent.enrichment import crunchbase, jobs, layoffs, maturity
from agent.enrichment.signal_brief import generate_briefs

load_dotenv()


def _build_competitor_signals(sector_companies: list[dict]) -> str:
    """Format competitor records into the template string."""
    if not sector_companies:
        return "No competitor data available."
    lines = []
    for i, comp in enumerate(sector_companies[:7], 1):
        name = comp.get("name", f"Competitor {i}")
        stack = crunchbase.extract_tech_stack(comp)
        funding = crunchbase.extract_funding_summary(comp)
        ai_score, _ = maturity.score(
            stack,
            [],  # no job data for competitors in quick pass
        )
        lines.append(
            f"Competitor {i}: {name}\n"
            f"  Funding: {funding}\n"
            f"  Tech stack: {', '.join(stack[:8]) or 'unknown'}\n"
            f"  AI maturity (pre-score): {ai_score}/3\n"
        )
    return "\n".join(lines)


def _find_sector_peers(record: dict, limit: int = 10) -> list[dict]:
    """Return up to `limit` companies from the same industry in the Crunchbase seed."""
    industries = crunchbase.extract_industries(record)
    if not industries:
        return []
    target_industry = industries[0].lower()
    all_rows = crunchbase._load()
    peers = []
    for row in all_rows:
        if row.get("name") == record.get("name"):
            continue
        row_industries = crunchbase.extract_industries(row)
        if any(target_industry in ind.lower() for ind in row_industries):
            peers.append(row)
        if len(peers) >= limit:
            break
    return peers


def enrich(company_name: str) -> dict:
    """
    Full enrichment run for a prospect company.
    Returns a dict with enrichment metadata and both signal briefs.
    """
    started_at = datetime.now(timezone.utc).isoformat()

    # 1. Crunchbase lookup
    record = crunchbase.lookup(company_name)
    cb_found = record is not None
    if not record:
        record = {}

    funding_summary = crunchbase.extract_funding_summary(record) if cb_found else "Not found in Crunchbase ODM"
    tech_stack = crunchbase.extract_tech_stack(record)
    industries = crunchbase.extract_industries(record)
    layoff_cb = crunchbase.extract_layoff_signal(record) if cb_found else ""
    leadership_changes = crunchbase.extract_leadership_changes(record) if cb_found else ""
    description = crunchbase.extract_description(record) if cb_found else ""
    headcount = crunchbase.extract_headcount(record) if cb_found else ""
    recent_news = crunchbase.extract_recent_news(record) if cb_found else ""

    # 2. Layoffs.fyi signal
    layoff_signal = layoffs.summary(company_name)
    combined_layoff = layoff_signal if layoff_signal != "No layoff events found in last 120 days" else layoff_cb

    # 3. Job post velocity
    job_data = jobs.job_velocity_summary(company_name)
    jobs_now = job_data["jobs_now"] if job_data["data_available"] else "data not available"
    jobs_60d = job_data["jobs_60_days"] if job_data["data_available"] else "data not available"
    ai_roles = job_data["ai_roles"]

    # 4. Rule-based AI maturity pre-score (now includes industries signal)
    pre_score, pre_rationale = maturity.score(tech_stack, ai_roles, industries=industries)

    # 5. Competitor signals
    peers = _find_sector_peers(record) if cb_found else []
    competitor_signals = _build_competitor_signals(peers)

    # 6. LLM signal brief generation
    briefs = generate_briefs(
        company_name=company_name,
        funding_info=funding_summary,
        layoff_info=combined_layoff,
        jobs_now=jobs_now,
        jobs_60_days=jobs_60d,
        tech_stack=tech_stack,
        ai_roles=ai_roles,
        competitor_signals=competitor_signals,
        industries=industries,
        headcount=headcount,
        description=description,
        leadership_changes=leadership_changes,
        recent_news=recent_news,
    )

    return {
        "company": company_name,
        "enrichment_ts": started_at,
        "crunchbase_found": cb_found,
        "crunchbase_id": record.get("id", None),
        "industries": industries,
        "pre_score_ai_maturity": pre_score,
        "pre_score_rationale": pre_rationale,
        **briefs,
    }


if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "Stripe"
    result = enrich(name)
    print(json.dumps(result, indent=2))
