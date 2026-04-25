# Competitor Gap Selection & Scoring Methodology

*Source of truth for `agent/enrichment/pipeline.py` functions `_build_competitor_signals()` and `_compute_sector_ai_distribution()`.*

---

## 1. Peer Selection

**Input:** A Crunchbase ODM record for the prospect company.

**Algorithm:**

1. Extract the prospect's **primary industry** (first element of `industries` array, normalised to lowercase) using `crunchbase.extract_industries()`.
2. Scan all 1,513 Crunchbase ODM rows. For each row:
   - Skip if `row.name == prospect.name` (exclude the prospect itself).
   - Include if any element of `row.industries` (lowercased) exactly matches the prospect's primary industry.
3. Stop after collecting **up to 10 peers** (`limit=10` default in `_find_sector_peers()`).

**Exclusions not yet applied at selection time (applied at confidence calibration):**
- Companies with headcount > 5,000 are included as peers but receive a note in the gap brief that they represent a different scale tier.
- Consumer app industries are not excluded from the peer pool (they may legitimately be in a mixed-industry sector). The prospect disqualifier is applied separately in `_check_disqualifiers()`.

**Sparse sector threshold:** `_SPARSE_SECTOR_THRESHOLD = 5`. When fewer than 5 peers are found, all downstream distribution statistics are flagged as indicative rather than statistically significant. This warning propagates into the LLM prompt and into `competitor_gap_brief.statistical_note`.

---

## 2. AI Maturity Scoring for Each Peer

Each peer is scored using the **same 0–3 integer rubric** as the prospect, applied via `maturity.score()` from `agent/enrichment/maturity.py`.

**Signals used per peer (from Crunchbase ODM only — no live job scrape for peers):**

| Signal | Source | Weight |
|---|---|---|
| ML/AI tech stack hits | `crunchbase.extract_tech_stack()` | High |
| Industry signals (AI, ML, data platform) | `crunchbase.extract_industries()` | Medium |
| Named AI/ML leadership | Crunchbase `team` field (if present) | High |
| Funding/description keywords | `description` field | Low |

**Important limitation:** Peers are scored from Crunchbase ODM data only — no job post scraping, no GitHub activity lookup, no exec commentary lookup. This means peer AI maturity scores have lower precision than the prospect's score, which incorporates all six signal sources. Peer scores are used only for relative positioning (quartile placement), not for absolute claims.

**Score rubric (0–3):**
- `0` — No public AI signal
- `1` — Some AI roles or stack indicators, no clear commitment
- `2` — Dedicated AI roles + modern ML stack OR exec AI commentary
- `3` — Active AI function with recent exec commitment + multiple AI roles + modern ML stack

---

## 3. Distribution Computation (`_compute_sector_ai_distribution`)

**Input:** List of up to 10 peer records.

**Steps:**
1. Score each peer → list of integers `[0, 0, 1, 2, 2, 3, ...]`
2. Sort scores ascending.
3. **Median:** `statistics.median(scores_sorted)`
4. **75th-percentile threshold (p75):** `scores_sorted[max(0, int(len * 0.75) - 1)]`
   - This is a conservative floor p75 using index-based approximation (not interpolated).
5. **Output string** embedded in the LLM competitor gap prompt:

   ```
   Sector AI maturity distribution (n=7): median=2.0/3, top-quartile threshold≥2/3, all scores=[0, 1, 2, 2, 2, 3, 3]
   ```

**Sparse sector annotation** (appended when `n < 5`):
```
 (sparse sector: only 3 peers found — benchmarks are indicative, not statistically significant)
```

---

## 4. Prospect Positioning

The LLM receives the distribution string and the prospect's own maturity score, and classifies the prospect's position:

| Position label | Condition |
|---|---|
| `top_quartile` | prospect score ≥ p75 AND prospect score is the maximum or tied-maximum |
| `above_median` | prospect score > median |
| `at_median` | prospect score == median (within integer rounding) |
| `below_median` | prospect score < median |

The LLM is instructed to use these labels and to cite the distribution numbers in its output. The position label populates `competitor_gap_brief.prospect_position_in_sector`.

---

## 5. Gap Identification

The LLM prompt instructs the model to:

1. List **up to 3 gaps** where top-quartile peers demonstrate a practice the prospect does not.
2. For each gap:
   - `practice` — the capability or tooling gap (e.g., "Kubernetes adoption", "MLflow experiment tracking")
   - `evidence_in_top_quartile` — cite the specific competitor and the evidence
   - `evidence_at_prospect` — what the prospect uses instead (from their tech stack or signals)
   - `gap_insight` — a neutral, non-condescending framing of the gap
   - `confidence` — a float 0–1 based on evidence quality

3. The prompt explicitly **prohibits**:
   - Condescending framing ("you are behind", "you lack capability")
   - Gaps unsupported by the brief data (hallucinated practices)
   - Claiming certainty about practices not mentioned in the Crunchbase or job data

---

## 6. Confidence Calibration

| Condition | Confidence cap |
|---|---|
| `n < _SPARSE_SECTOR_THRESHOLD` (sparse sector) | `overall_confidence ≤ 0.50` |
| Any individual gap has zero verifiable evidence in the brief | `gap.confidence ≤ 0.40` |
| Peer AI score was inferred from description keywords only (no tech stack) | `gap.confidence ≤ 0.55` |
| All evidence from direct tech stack + role data | No cap; up to 1.0 |

These caps are enforced in the LLM system prompt via explicit instruction: *"Set confidence to at most 0.5 if fewer than 5 sector peers were analysed."*

---

## 7. Output Schema

The function populates `traces/{company}/competitor_gap_brief.json`:

```json
{
  "sector": "FinTech",
  "competitors_analyzed": 3,
  "prospect_ai_score": 2,
  "prospect_position_in_sector": "above_median",
  "gaps": [
    {
      "practice": "Kubernetes adoption",
      "evidence_in_top_quartile": "Ocrolus uses Kubernetes for orchestration (Crunchbase stack)",
      "evidence_at_prospect": "Arcana uses AWS Lambda, no Kubernetes in detected stack",
      "gap_insight": "Kubernetes is common in top-quartile FinTech AI teams for model serving at scale",
      "confidence": 0.6
    }
  ],
  "overall_confidence": 0.7,
  "statistical_note": null
}
```

`statistical_note` is non-null when `n < _SPARSE_SECTOR_THRESHOLD`.

---

## 8. Known Limitations

1. **Peers scored from Crunchbase only.** Peer AI maturity scores do not include live job post velocity, GitHub activity, or exec commentary — all of which are used for the prospect. Peer scores are systematically underestimated for companies that are active on GitHub or have strong exec AI commentary but minimal Crunchbase presence.

2. **Single-industry matching.** Peers are matched on the primary industry label only. A company with "FinTech, AI" as industries will only match peers with "FinTech" as primary. Cross-industry niche segments (e.g., "FinTech + Healthcare AI") are undersupported.

3. **Stale Crunchbase data.** The ODM snapshot used (1,513 records, Apache 2.0) is 30–60 days stale. Companies that pivoted away from a sector or raised new rounds not yet in the snapshot will be mis-positioned.

4. **No disqualifier exclusion in peer pool.** Consumer-app companies may appear as peers if they share a primary industry (e.g., a gaming company tagged under "Mobile Technology" alongside a B2B SaaS prospect). This inflates peer scores in mixed-industry sectors.
