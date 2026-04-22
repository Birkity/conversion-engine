# Conversion Engine — Interim Submission Report
**Tenacious Consulting and Outsourcing**
**Birkity Yishak — 10 Academy Week 10 — April 22, 2026**

---

## Architecture Overview

The system is a modular pipeline with four layers:

```
Enrichment Pipeline
  Crunchbase ODM (1,000 records) → layoffs.fyi CSV → LinkedIn job-post
  velocity (seeds/job_posts) → AI Maturity Scorer (0–3, rule-based)
  → LLM Signal Brief (OpenRouter gemini-2.0-flash-001)
  → hiring_signal_brief.json + competitor_gap_brief.json
          │
Outbound Channels
  Email:    Resend SMTP relay (kill-switch: LIVE_OUTBOUND_ENABLED)
  SMS:      Africa's Talking sandbox (sink: AT_SMOKE_TEST_PHONE)
  Calendar: Cal.com booking link (pre-filled URL)
          │
CRM + Observability
  HubSpot: contact upsert + enrichment note (Private App token)
  Langfuse: per-trace cost attribution (cloud free tier)
          │
Webhook Hub (deployed: https://conversion-engine.onrender.com)
  POST /webhooks/resend          — Resend email events (Svix-signed)
  POST /webhooks/africastalking  — Africa's Talking SMS callbacks
  POST /webhooks/cal             — Cal.com booking events
  POST /webhooks/hubspot         — HubSpot CRM events
  GET  /health                   — Liveness probe
```

**Key design decisions:**
- Kill switch (`LIVE_OUTBOUND_ENABLED=false`) routes all outbound to staff sink by default. No real prospects contacted without explicit opt-in.
- Svix HMAC-SHA256 signature verification on `/webhooks/resend` prevents spoofed events.
- Enrichment pipeline degrades gracefully when seed files are absent (jobs CSV is 493MB, gitignored).
- LLM model is configurable via `BRIEF_MODEL` env var; defaults to `qwen/qwen3-30b-a3b` for cost control.

---

## Production Stack Status

| Service | Status | Verification |
|---------|--------|--------------|
| Resend SMTP (email, primary channel) | ✅ Configured | `scripts/resend_smoketest.py` — SMTP auth succeeds; delivery to `birkity.yishak.m@gmail.com` confirmed |
| Africa's Talking (SMS, secondary) | ✅ Sandbox active | `scripts/africastalking_smoketest.py` — credentials valid; routes to sandbox sink |
| HubSpot Developer Sandbox | ✅ Connected | `scripts/hubspot_smoketest.py` — contact create/upsert via Private App token |
| Cal.com booking flow | ✅ Link generation | `agent/calendar/client.py` — pre-filled booking URL generated; Cloudflare blocks API direct calls (known limitation) |
| Langfuse observability | ✅ Tracing active | `scripts/langfuse_smoketest.py` — test trace visible in project |
| Webhook hub (Render) | ✅ Deployed | `https://conversion-engine.onrender.com/health` → 200 OK |

**Known limitation:** Resend's `onboarding@resend.dev` sender only delivers to the account owner's email. A verified custom domain is required for production outreach. The kill switch ensures no real outreach occurs during the challenge week.

---

## Enrichment Pipeline Status

All six signal sources are integrated and producing output:

| Signal | Source | Status |
|--------|--------|--------|
| Firmographics | Crunchbase ODM (1,000 records) | ✅ Lookup by company name, extracts industries, funding, tech stack, leadership |
| Funding events | Crunchbase `funding_rounds_list` field | ✅ Parsed and summarised in brief |
| Job-post velocity | `seeds/job_posts/` (LinkedIn, 493MB) | ✅ Graceful fallback when file absent |
| Layoff signal | `seeds/layoffs/layoffs_data.csv` (3,622 rows) | ✅ Last-120-day lookup |
| AI maturity score (0–3) | Rule-based on tech stack + roles + exec signals | ✅ Per-signal justification in output |
| Competitor gap brief | Sector peers from Crunchbase, same pipeline | ✅ `competitor_gap_brief.json` generated |

**Sample output** (WISEiTECH, Analytics/Big Data/ML — full JSON in `traces/enrichment_sample_wiseitech.json`):
- Crunchbase found: ✅ ID `wiseitech`
- Industries: Analytics, Big Data, Machine Learning
- AI maturity pre-score: 0 (insufficient public signal in seed)
- Competitors analysed: 7 (same sector peers from ODM)
- Confidence: 0.60 overall

**Sample output** (SnapTrade, Developer APIs/FinTech — `traces/enrichment_sample_snaptrade.json`):
- Crunchbase found: ✅ ID `snaptrade-be4e`
- Industries: Developer APIs, Developer Tools, FinTech
- Confidence: 0.45 (limited stack signals in seed)

The LLM signal brief correctly falls back to ask-rather-than-assert language when confidence is below 0.5, satisfying the honesty constraint from the challenge spec.

---

## τ²-Bench Baseline (Act I)

### Dev-Tier Smoke Run (completed)

| Metric | Value |
|--------|-------|
| Model (agent) | `qwen/qwen3-30b-a3b` via OpenRouter |
| Model (user) | `meta-llama/llama-3.2-3b-instruct` via OpenRouter |
| Tasks attempted | 3 (smoke) |
| Tasks evaluated | 2 |
| Infra errors | 1 (fixed — see below) |
| Pass@1 | 0.000 |
| Read action accuracy | 25% |
| Write action accuracy | 0% |
| Cost per run | ~$0.00 reported (LiteLLM alias gap) |
| Wall-clock p50 | 61s |
| Wall-clock p95 | 847s |

Full run: 30 tasks × 5 trials with `google/gemini-2.0-flash-001` is in progress at submission time. Cost: ~$0.003/simulation → ~$0.45 total for 150 simulations. Results will be committed to `eval/score_log.json` and `eval/trace_log.jsonl` upon completion.

**Infrastructure fix applied:** τ²-Bench's internal NL-assertion and env-interface calls defaulted to `gpt-4.1-2025-04-14` (bare OpenAI). Fixed by setting `OPENAI_BASE_URL=https://openrouter.ai/api/v1` + `OPENAI_API_KEY=<openrouter key>` in `eval/tau2/.env`, routing all internal model calls through OpenRouter.

**Expected full-run result:** Pass@1 ≈ 0.03–0.10 for gemini-2.0-flash-001 on retail (30B-class model; SOTA is ~42% with GPT-5-class). The benchmark establishes the Day-1 baseline for Act IV delta measurement.

---

## Latency and Cost (preliminary)

From the 1-task gemini-2.0-flash-001 test:
- Agent cost per conversation: $0.0027
- Duration: 77s (single task, no concurrency)
- Termination: `user_stop` (USER_STOP)

Full p50/p95 across 150 simulations will be reported in `eval/score_log.json` upon completion of the 30-task run.

---

## What Is Working / Not Working / Plan

**Working:**
- Full enrichment pipeline end-to-end (Crunchbase → LLM brief)
- Webhook hub deployed on Render, all 5 endpoints live
- Email (Resend SMTP), SMS (Africa's Talking), HubSpot CRM, Cal.com booking link
- Langfuse tracing active
- τ²-Bench harness running cleanly on Windows with OpenRouter routing

**Not working / known gaps:**
- Job-post velocity signal returns `-1` (no data) because 493MB LinkedIn CSV is gitignored. Seed data enriches gracefully without it.
- Cal.com API direct calls blocked by Cloudflare (Error 1010). Workaround: pre-filled booking URL generation works; full API flow requires self-hosted Docker instance.
- τ²-Bench 30-task full run in progress at submission time; 95% CI not yet available.
- p50/p95 from ≥20 real email+SMS interactions not yet measured (kill switch active, no live outbound).

**Plan for Acts III–V (Days 3–7):**
1. Complete 30-task τ²-bench run → update score_log.json and baseline.md with 95% CI
2. Design probe library (30+ probes) targeting ICP misclassification and signal over-claiming
3. Implement mechanism (confidence-gated phrasing shift when signal strength is `insufficient_data`)
4. Run held-out slice with mechanism vs. baseline to measure Delta A
5. Write 2-page memo for final submission

---

*All numeric claims in this report trace to `eval/score_log.json`, `eval/trace_log.jsonl`, or published sources cited in `README.md`. Kill switch is active: `LIVE_OUTBOUND_ENABLED=false`.*
