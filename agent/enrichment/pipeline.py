"""
Enrichment pipeline orchestrator.
Chains: Crunchbase -> Jobs -> Layoffs -> Maturity pre-score -> LLM signal brief.

Usage:
    from agent.enrichment.pipeline import enrich
    result = enrich("Acme Corp")
    # result contains: crunchbase_record, hiring_signal_brief, competitor_gap_brief
"""
import json
import statistics
from datetime import datetime, timezone

from dotenv import load_dotenv

from agent.enrichment import crunchbase, jobs, layoffs, maturity
from agent.enrichment.signal_brief import generate_briefs

load_dotenv()

# ── ICP disqualifier constants ─────────────────────────────────────────────────
_CONSUMER_INDUSTRY_KEYWORDS = {
    "gaming", "consumer", "social media", "dating", "entertainment",
    "fitness", "food delivery", "e-commerce", "retail consumer",
}
_ANTI_OFFSHORE_KEYWORDS = {
    "we don't work with offshore", "no offshore", "domestic only",
    "in-house only", "no contractors",
}


def _check_disqualifiers(
    industries: list[str],
    headcount_str: str,
    description: str,
) -> list[str]:
    """Return a list of disqualifier reasons; empty list means no disqualifiers."""
    disq: list[str] = []

    # Headcount gate (>5000 employees)
    try:
        hc = int(str(headcount_str).replace(",", "").split()[0])
        if hc > 5000:
            disq.append(f"headcount_exceeds_5000: {hc}")
    except (ValueError, IndexError, AttributeError):
        pass

    # Consumer app industries
    industry_text = " ".join(i.lower() for i in industries)
    if any(kw in industry_text for kw in _CONSUMER_INDUSTRY_KEYWORDS):
        disq.append("consumer_app_industry")

    # Anti-offshore stance in company description
    desc_lower = description.lower()
    if any(kw in desc_lower for kw in _ANTI_OFFSHORE_KEYWORDS):
        disq.append("anti_offshore_stance_in_description")

    return disq


def _compute_sector_ai_distribution(sector_companies: list[dict]) -> str:
    """Compute AI maturity score distribution across sector peers.

    Applies the same 0-3 maturity scoring rubric as agent/enrichment/maturity.py
    to each peer. Returns median, 75th-percentile threshold, and a sparse-sector
    warning when n < _SPARSE_SECTOR_THRESHOLD. Full methodology: docs/competitor_gap_methodology.md
    """
    scores: list[int] = []
    for comp in sector_companies[:10]:
        stack = crunchbase.extract_tech_stack(comp)
        ai_score, _ = maturity.score(stack, [])
        scores.append(ai_score)
    if not scores:
        return "insufficient_data"
    scores_sorted = sorted(scores)
    median_score = statistics.median(scores_sorted)
    p75_idx = max(0, int(len(scores_sorted) * 0.75) - 1)
    p75 = scores_sorted[p75_idx]
    return (
        f"Sector AI maturity distribution (n={len(scores)}): "
        f"median={median_score:.1f}/3, top-quartile threshold≥{p75}/3, "
        f"all scores={scores_sorted}"
    )


_SPARSE_SECTOR_THRESHOLD = 5  # fewer peers than this = sparse sector


def _build_competitor_signals(sector_companies: list[dict]) -> str:
    """Format competitor records into the template string, appending sector distribution.

    Peer selection: same primary industry from Crunchbase ODM; up to 10 companies;
    excludes the prospect itself; excludes companies matching ICP disqualifiers
    (consumer apps, >5000 headcount). Full scoring algorithm and confidence calibration
    rules documented in docs/competitor_gap_methodology.md.
    """
    if not sector_companies:
        return "No competitor data available. Sector benchmark is unavailable — treat AI maturity score as absolute, not relative."

    sparse = len(sector_companies) < _SPARSE_SECTOR_THRESHOLD
    sparse_note = (
        f" (sparse sector: only {len(sector_companies)} peers found — "
        "benchmarks are indicative, not statistically significant)"
        if sparse else ""
    )

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
    distribution = _compute_sector_ai_distribution(sector_companies)
    lines.append(f"\n{distribution}{sparse_note}")
    return "\n".join(lines)


def _find_sector_peers(record: dict, limit: int = 10) -> list[dict]:
    """
    Return up to `limit` companies from the same industry in the Crunchbase seed.

    Selection criteria: exact match on primary industry label (case-insensitive).
    When fewer than _SPARSE_SECTOR_THRESHOLD peers exist the caller should treat
    sector distribution statistics as indicative rather than significant.
    """
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
        if any(target_industry == i.lower() for i in row_industries):
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

    # 3b. ICP disqualifier pre-screen
    disqualifiers = _check_disqualifiers(industries, headcount, description)

    # 4. Rule-based AI maturity pre-score — extract exec keywords from free-text fields
    _exec_text = f"{description} {recent_news} {leadership_changes}".lower()
    exec_keywords = [kw for kw in maturity._EXEC_AI_KEYWORDS if kw in _exec_text]
    pre_score, pre_rationale = maturity.score(
        tech_stack, ai_roles,
        exec_commentary_keywords=exec_keywords,
        industries=industries,
    )

    # 5. Competitor signals
    peers = _find_sector_peers(record) if cb_found else []
    competitor_signals = _build_competitor_signals(peers)

    # 6. Per-source confidence used by downstream LLM prompt calibration.
    layoff_events = layoffs.lookup(company_name)
    if layoff_events:
        layoff_confidence = 1.0
    elif layoffs._LAYOFFS_PATH.exists():
        layoff_confidence = 0.5
    else:
        layoff_confidence = 0.0

    if pre_score > 0:
        maturity_confidence = round(min(pre_score / 3, 1.0) * 0.8 + 0.2, 2)
    else:
        maturity_confidence = 0.2

    signal_confidence_dict = {
        "crunchbase": 1.0 if cb_found else 0.0,
        "job_velocity": job_data.get("confidence", 0.0),
        "layoffs": layoff_confidence,
        "ai_maturity": maturity_confidence,
    }

    base_return = {
        "company": company_name,
        "enrichment_ts": started_at,
        "crunchbase_found": cb_found,
        "crunchbase_id": record.get("id", None),
        "industries": industries,
        "pre_score_ai_maturity": pre_score,
        "pre_score_rationale": pre_rationale,
        "signal_confidence": signal_confidence_dict,
        "disqualifiers": disqualifiers,
    }

    # Short-circuit LLM call if disqualified — return stub briefs
    if disqualifiers:
        stub_hsb = {
            "company": company_name,
            "icp_segment": "disqualified",
            "confidence": 0.0,
            "recommended_pitch_angle": "",
            "tenacious_status": "draft",
            "disqualified_reasons": disqualifiers,
        }
        stub_cgb = {
            "sector": "unknown",
            "competitors_analyzed": 0,
            "gaps": [],
            "overall_confidence": 0.0,
            "tenacious_status": "draft",
        }
        return {**base_return, "hiring_signal_brief": stub_hsb, "competitor_gap_brief": stub_cgb}

    # 7. LLM signal brief generation
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
        signal_confidence=signal_confidence_dict,
    )

    return {**base_return, **briefs}


if __name__ == "__main__":
    import sys

    name = sys.argv[1] if len(sys.argv) > 1 else "Stripe"
    result = enrich(name)
    print(json.dumps(result, indent=2))
