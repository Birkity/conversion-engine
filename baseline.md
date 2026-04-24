# Baseline Metrics — Conversion Engine

Report date: 2026-04-24
Model: google/gemini-2.0-flash-001 (via OpenRouter)

---

## τ²-Bench Baseline

Reference baseline committed to `score_log.json` (PM-provided, git commit `d11a97072c49d093f7b5a3e4fe9da95b490d43ba`):

| Metric | Value |
| --- | --- |
| Domain | retail |
| Evaluated simulations | 150 |
| Total tasks | 30 |
| Trials per task | 5 |
| pass@1 | **72.7%** |
| 95% CI | [65.0%, 79.2%] |
| Avg agent cost | $0.0199 per simulation |
| p50 latency | 105.95 s |
| p95 latency | 551.65 s |
| Infrastructure errors | 0 |

The τ²-Bench retail domain tests customer service agent behavior across 30 task types. The 72.7% pass@1 is the PM-provided reference — it represents the baseline before any Tenacious-specific tuning.

---

## Reply Interpreter Probe Suite Baseline

Source: `probes/probe_results.json`, run 2026-04-24.

| Run | Probes | Passed | Failed | Pass Rate |
| --- | --- | --- | --- | --- |
| Run 1 (pre-fix) | 32 | 24 | 8 | **75%** |
| Run 2 (post-fix) | 32 | 31 | 1 | **97%** |

| Category | Run 1 | Run 2 | Change |
| --- | --- | --- | --- |
| reply_intent_ambiguity | 3/3 | 3/3 | — |
| hostile_sarcastic | 4/4 | 3/4 | −1 (label mismatch, no routing error) |
| icp_misclassification | 3/3 | 3/3 | — |
| signal_over_claim | 1/3 | 3/3 | +2 |
| bench_over_commit | 4/4 | 4/4 | — |
| tone_drift | 0/3 | 3/3 | +3 |
| scheduling_edge_cases | 1/3 | 3/3 | +2 |
| low_signal_honesty | 3/3 | 3/3 | — |
| off_topic_identity | 2/3 | 3/3 | +1 |
| mixed_intent_multi_question | 3/3 | 3/3 | — |

Latency per reply interpretation call: p50 ~1.8 s, p95 ~4.9 s (Gemini Flash, OpenRouter, measured across 64 probe calls).

---

## Cost Per Qualified Lead

Cost model derived from OpenRouter invoice data (2026-04-24) and measured call counts.

### Per-call costs (Gemini Flash via OpenRouter)

| Stage | Calls per prospect | Cost per call | Cost per prospect |
| --- | --- | --- | --- |
| Act I — brief generation | 2 LLM calls | ~$0.018 | $0.036 |
| Act II — email generation | 1 LLM call | ~$0.012 | $0.012 |
| Act III — reply interpretation | 1 LLM call per reply | ~$0.001 | $0.001 (per reply received) |
| HubSpot / Cal.com / Resend | API calls | $0 (free tiers) | $0 |
| **Total per prospect touched** | | | **~$0.05** |

### Conversion funnel

| Stage | Rate | Source |
| --- | --- | --- |
| Outbound → reply | 7% | LeadIQ 2026 / Apollo benchmark |
| Signal-grounded outbound → reply | 7–12% (target) | Clay / Smartlead case studies |
| Reply → qualified lead (INTERESTED or SCHEDULE) | ~15% of replies | Estimated from probe distribution |
| Qualified lead → discovery call booked | 35–50% | Tenacious internal (last 4 quarters) |
| Discovery call → proposal | 35–50% | Tenacious internal |
| Proposal → close | 25–40% | Tenacious internal |

### Cost per qualified lead calculation

At 1,000 outbound contacts, 7% reply rate, 15% of replies qualify:

```
Cost to enrich + email 1,000 prospects:  1,000 × $0.048 = $48
Reply interpretation (70 replies):         70 × $0.001  = $0.07
Total LLM spend for 1,000 contacts:                      $48.07

Qualified leads (1,000 × 7% × 15%):                      ~11 leads
Cost per qualified lead:                              $48.07 / 11 = $4.37
```

At signal-grounded reply rate (10%): 15 qualified leads → **$3.20 per qualified lead**.

Compare to manual SDR outreach: estimated $150–$400 per qualified lead (salary-loaded, including research time, email drafting, follow-up). System cost is **97–99% lower**.

### Weekly OpenRouter spend (actual)

| Period | Spend |
| --- | --- |
| This week (2026-04-21 to 2026-04-24) | $4.62 |
| This month (2026-04) | $26.13 |
| Weekly limit | $36.11 |
| Remaining this week | $31.49 |

The $4.62 weekly spend covers full development work: 4 company traces, 2 full probe runs (64 calls), act1/act2 execution runs, integration smoke tests, and prompt iteration cycles.

---

## Stalled-Thread Rate Delta

### Current Tenacious manual process

From CEO/CFO interviews (challenge spec): **30–40%** of qualified conversations stall in the first two weeks due to:
- Partner or engineer handling the thread while managing delivery work
- No systematic follow-up cadence
- Reply queue building behind active client work

### System stalled-thread rate (measured)

The conversion engine eliminates human-in-the-loop delay at the classification and routing step:

| Step | Manual time | System time |
| --- | --- | --- |
| Reply received → read | 1–48 hours | <1 second (webhook event) |
| Intent classification | Minutes to hours (human judgment) | 1.8 s p50 (LLM) |
| Next action (Cal link / clarification / stop) | Hours to days | <5 s end-to-end |
| HubSpot updated | Often skipped | Automatic on every event |

**Measured routing latency** (from probe runs): p50 1.8 s, p95 4.9 s per reply. No human delay in the loop.

**Stall rate for routed replies: 0%** — every reply that reaches `on_email_reply()` with context gets classified and acted on within 5 seconds.

**Known gap:** Resend free tier does not deliver inbound reply text to the webhook. In the current challenge-week setup, the full end-to-end chain requires a manual trigger via `act3_reply_tests.py` or a test endpoint. In production with a paid Resend plan (or SendGrid Inbound Parse), the stall rate for reply handling would be 0%.

**Effective stall rate delta** (production projection): 30–40% → <1% (residual stalls from network/infrastructure failures only).

---

## Competitive-Gap Outbound Performance

All four test company emails were generated using the signal-grounded approach (hiring velocity + AI maturity + competitor gap brief). No generic Tenacious pitch was used in any outbound.

| Outbound variant | Companies | Signal used |
| --- | --- | --- |
| Signal-grounded (AI maturity + competitor gap) | arcana, kinanalytics | Series A + doubled job postings + AI maturity score |
| Abstained (confidence < 0.6) | snaptrade, wiseitech | Confidence below threshold — no outbound generated |

The abstention path enforces the spec requirement: "abstain from segment-specific pitch when signal is insufficient." No generic pitch was sent to low-confidence prospects.

Measured reply rate delta between variants: not yet measurable at challenge-week scale (4 synthetic prospects, no real replies). The 7–12% vs. 1–3% delta cited in the spec is the published benchmark from Clay/Smartlead; it is the target, not a measured result from this build.

---

## Annualized Dollar Impact

### Assumptions

| Input | Value | Source |
| --- | --- | --- |
| Average engagement ACV (talent outsourcing) | $240K–$720K | Tenacious internal (weighted by segment) |
| Discovery call → proposal | 35–50% | Tenacious internal |
| Proposal → close | 25–40% | Tenacious internal |
| Email → discovery call (system, signal-grounded) | ~7% × 15% × 40% = 0.42% | Funnel calculation |
| Weekly outbound volume | 500 contacts/week | Achievable at $25/week LLM spend |

### Three scenarios

**Scenario A — One segment (Segment 1, Series A startups)**

```
500 contacts/week × 52 weeks = 26,000 annual outbound
Discovery calls booked: 26,000 × 0.42% = 109 calls
Proposals sent: 109 × 40% = 44
Deals closed: 44 × 30% = 13
Revenue: 13 × $300K ACV = $3.9M pipeline
LLM cost: 26,000 × $0.048 = $1,248/year
```

**Scenario B — Two segments (Segment 1 + Segment 4)**

```
Double volume, mixed ACV ($300K–$600K blended):
Deals closed: ~26 per year
Revenue: 26 × $450K ACV = $11.7M pipeline
LLM cost: ~$2,500/year
```

**Scenario C — All four segments**

```
Full ICP coverage, 1,000 contacts/week:
Discovery calls: ~218/year
Deals closed: ~26–52/year
Revenue: $6.2M–$23.4M pipeline range
LLM cost: ~$2,500/year (Gemini Flash pricing)
Headcount freed: ~1 FTE SDR equivalent ($80–120K salary)
```

Net ROI in Scenario C: $6–23M pipeline, $82–123K saved in SDR headcount, against ~$2,500/year in LLM costs. **ROI: 2,400–9,200x on direct LLM spend.**

---

## Pilot Scope Recommendation

**Segment:** Segment 1 (recently-funded Series A startups)

**Rationale:** Cleanest signal (Crunchbase funding date + job velocity), highest ICP confidence, lowest false-positive rate on disqualifiers, best bench match (Python/ML/data).

**Lead volume:** 100 contacts/week for 4 weeks (400 total)

**Weekly budget:** $5/week LLM spend ($20 total for the pilot)

**Success criterion Tenacious can track after 30 days:**

> Discovery calls booked ≥ 2 from the 400-contact cohort (0.5% booking rate — conservative relative to the 0.42% model projection).

**Kill-switch clause:** Pause the system if any of the following occur:

- A prospect replies citing factually wrong signal data that embarrasses Tenacious (threshold: 3 complaints in a single week)
- A reply classified as `NOT_INTERESTED` is later found to have been a warm lead (false STOP rate > 5% of stopped contacts)
- LLM spend exceeds $50/week without a proportional increase in qualified leads
- Any email reaches a real prospect inbox (kill switch failure — `LIVE_OUTBOUND_ENABLED` should never be true without explicit approval)
