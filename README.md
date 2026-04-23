# Conversion Engine — Tenacious Consulting Edition

Automated lead generation and conversion system for B2B engineering consulting outreach. Finds high-signal prospects from public data, qualifies them against four ICP segments, generates intelligence briefs, composes style-guide-compliant outreach emails, and routes every interaction to HubSpot and Langfuse.

> **Kill switch — Rule 5 (mandatory):** `LIVE_OUTBOUND_ENABLED` defaults to `false`. All outbound (email + SMS) routes to the configured sink address. No real prospects are contacted unless explicitly enabled. This default must not be changed without Tenacious executive sign-off.

---

## Architecture

```text
Data Sources                Enrichment Pipeline
──────────────              ──────────────────────────────────────────────
Crunchbase ODM  ──┐
layoffs.fyi     ──┼──► Enrichment Pipeline ──► Brief Generator (LLM)
Job Posts       ──┘    (jobs, layoffs,          (Tenacious ICP + bench +
(Playwright/CSV)        maturity scorer)          tone constraints)
                                │                        │
                                ▼                        ▼
                         Langfuse traces       hiring_signal_brief.json
                                               competitor_gap_brief.json

Outbound Channels (all gated by kill switch)
──────────────────────────────────────────────
Email (primary)   ──► Resend SMTP ──► Sink / Prospect inbox
SMS (warm leads)  ──► Africa's Talking ──► Sink / Prospect phone
Voice (final)     ──► Human-delivered discovery call (not automated)

CRM + Observability
──────────────────────────────────────────────
HubSpot Developer Sandbox   ← contact upsert + enrichment note
Langfuse cloud free tier    ← per-call cost + latency traces

Webhook Hub (deployed on Render)
──────────────────────────────────────────────
POST /webhooks/resend           ← email reply events → on_email_reply()
POST /webhooks/africastalking   ← SMS delivery + inbound → on_sms_reply()
POST /webhooks/cal              ← BOOKING_CREATED → HubSpot upsert
POST /webhooks/hubspot          ← CRM subscription events
GET  /health                    ← liveness check
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/Birkity/conversion-engine.git
cd conversion-engine
pip install -r requirements.txt
playwright install chromium   # for job-post velocity scraping
```

### 2. Seed data (gitignored — clone locally)

```bash
# Crunchbase ODM (1,513 company records, Apache 2.0 license)
git clone https://github.com/luminati-io/Crunchbase-dataset-samples seeds/crunchbase

# tau2-bench evaluation harness
git clone https://github.com/sierra-research/tau2-bench eval/tau2
cd eval/tau2 && uv sync && cd ../..
```

### 3. Environment

```bash
cp .env.example .env
# Fill in all keys — see table below
```

| Variable | Purpose | Required |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | LLM inference (brief generator + email composer) | Yes |
| `BRIEF_GENERATOR_MODEL` | Model for LLM calls (default: `google/gemini-2.0-flash-001`) | No |
| `RESEND_API_KEY` | Resend SMTP authentication | Yes |
| `RESEND_FROM` | Sender address (default: `onboarding@resend.dev` on trial) | No |
| `RESEND_WEBHOOK_SECRET` | Svix signature verification for email webhooks | Yes |
| `OUTBOUND_SINK_EMAIL` | All outbound email routes here when kill switch is active | **Yes** |
| `AT_USERNAME` + `AT_API_KEY` | Africa's Talking SMS sandbox | Yes |
| `AT_SMOKE_TEST_PHONE` | All SMS routes here when kill switch is active | Yes |
| `HUBSPOT_PRIVATE_APP_TOKEN` | HubSpot CRM — contact upsert + notes | Yes |
| `CALCOM_API_KEY` + `CALCOM_EVENT_URL` | Cal.com booking link generation | Yes |
| `CALCOM_WEBHOOK_SECRET` | HMAC signature on Cal.com booking events | Yes |
| `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` | Langfuse observability | Yes |
| `LANGFUSE_BASE_URL` | `https://us.cloud.langfuse.com` | Yes |
| `LIVE_OUTBOUND_ENABLED` | `false` (safe default). Set `true` only with Tenacious approval. | No |

---

## Key Scripts

### Act I — Brief validation (intelligence layer)

```bash
# Validate that raw signals produce structured briefs
python scripts/act1_brief_validation.py
python scripts/act1_brief_validation.py traces/snaptrade/signals.json
python scripts/act1_brief_validation.py traces/wiseitech/signals.json --outdir out/wiseitech
```

Reads `signals.json` → calls `brief_generator.generate()` → saves and prints both briefs with confidence scores. Validates all required output fields. No outbound triggered.

### Act II — Email execution (outbound layer)

```bash
# Generate + send to sink (kill switch active — never reaches real prospect)
python scripts/act2_email_execution.py traces/kinanalytics

# Dry run — generate only, do not send
python scripts/act2_email_execution.py traces/kinanalytics --dry-run

# Other companies
python scripts/act2_email_execution.py traces/snaptrade
python scripts/act2_email_execution.py traces/wiseitech
```

Loads `hiring_signal_brief.json` + `competitor_gap_brief.json` + `prospect_info.json` → generates a style-guide-compliant cold email via LLM → sends to `OUTBOUND_SINK_EMAIL` (never the prospect). Validates word count, subject length, and banned phrases before sending.

### Brief generation

```bash
# Generate briefs for any company in traces/
python scripts/test_brief.py kinanalytics
python scripts/test_brief.py snaptrade
python scripts/test_brief.py wiseitech
```

### Full enrichment pipeline

```bash
python -m agent.enrichment.pipeline "Stripe"
```

Chains: Crunchbase → Jobs (Playwright first, CSV fallback) → Layoffs.fyi → AI maturity score → LLM brief.

### Individual smoke tests

```bash
python scripts/resend_smoketest.py          # email
python scripts/africastalking_smoketest.py  # SMS
python scripts/hubspot_smoketest.py         # CRM
python scripts/langfuse_smoketest.py        # observability
python scripts/integration_smoketest.py     # full chain: enrich→email→HubSpot→Cal
```

### Webhook hub

```bash
# Local development
uvicorn webhook.main:app --host 0.0.0.0 --port 8000 --reload

# Deployed on Render
curl https://conversion-engine.onrender.com/health
```

---

## signals.json Schema

Each company lives in `traces/<company>/`. The `signals.json` feeds the brief generator:

```json
{
  "company_name": "Acme Corp",
  "industries": ["SaaS", "FinTech"],
  "headcount": "35",
  "description": "One-line public description.",
  "funding_info": "Series A $12M closed February 2026.",
  "layoffs": "No layoff events found in last 120 days.",
  "jobs_now": 7,
  "jobs_60_days": 4,
  "tech_stack": ["Python", "dbt", "Snowflake", "AWS"],
  "ai_roles": ["ML Engineer"],
  "leadership_changes": "No leadership changes detected in last 90 days.",
  "recent_news": "Series A announced February 2026.",
  "competitor_signals": [
    {
      "name": "Competitor A",
      "funding": "Series B $60M",
      "tech_stack": ["Python", "dbt", "Kubernetes"],
      "ai_maturity_score": 2
    }
  ]
}
```

Each company also needs a `prospect_info.json` for `act2_email_execution.py`:

```json
{
  "name": "Alex Rivera",
  "role": "CTO",
  "email": "prospect@sink.trp1.internal",
  "company": "Acme Corp",
  "_policy_note": "Synthetic prospect. Rule 2: email resolves to program sink."
}
```

> **Rule 2:** `email` must be a synthetic/sink address — never a real contact's email.

---

## Project Structure

```text
conversion-engine/
├── agent/
│   ├── brief_generator/           ← Intelligence layer
│   │   ├── brief_generator.py     ← generate(signals) → {hiring_brief, gap_brief}
│   │   ├── llm_client.py          ← OpenRouter + Langfuse auto-tracing
│   │   └── prompts.py             ← SYSTEM_PROMPT (ICP, bench, tone constraints)
│   ├── enrichment/                ← Signal collection
│   │   ├── pipeline.py            ← Orchestrator: all signals → briefs
│   │   ├── crunchbase.py          ← Crunchbase ODM loader
│   │   ├── jobs.py                ← Job velocity (Playwright first, CSV fallback)
│   │   ├── jobs_playwright.py     ← Public LinkedIn job scraper (no login)
│   │   ├── layoffs.py             ← layoffs.fyi CSV lookup
│   │   ├── maturity.py            ← Rule-based AI maturity scorer (0–3)
│   │   └── signal_brief.py        ← LLM brief call (Langfuse traced)
│   ├── email/
│   │   ├── handler.py             ← Resend SMTP + kill switch + draft header
│   │   └── generator.py           ← LLM email composer (style-guide enforced)
│   ├── sms/handler.py             ← Africa's Talking + warm-lead gate
│   ├── hubspot/client.py          ← Contact upsert + enrichment note
│   └── calendar/client.py         ← Cal.com booking link generator
├── webhook/main.py                ← FastAPI hub: 5 endpoints, HMAC verified
├── scripts/
│   ├── act1_brief_validation.py   ← Validate brief generation end-to-end
│   ├── act2_email_execution.py    ← Generate + send outreach email (sink)
│   ├── test_brief.py              ← Per-company brief generation
│   ├── integration_smoketest.py   ← Full chain smoke test
│   ├── update_score_log.py        ← τ²-Bench results → score_log.json
│   └── *_smoketest.py             ← Per-service smoke tests
├── traces/
│   ├── kinanalytics/              ← Segment 1: Series A, 35 hc, 7 open roles
│   │   ├── signals.json
│   │   ├── hiring_signal_brief.json
│   │   ├── competitor_gap_brief.json
│   │   └── prospect_info.json     ← Synthetic prospect (Rule 2)
│   ├── snaptrade/                 ← Ambiguous: decelerating hiring, no funding
│   └── wiseitech/                 ← Ambiguous: zero jobs, weak signal flagged
├── policy/
│   └── acknowledgement_signed.txt ← Rule 5 compliance acknowledgement
├── baseline.md                    ← τ²-Bench reference baseline (PM-provided)
├── score_log.json                 ← Official baseline: 72.7% pass@1
├── trace_log.jsonl                ← Simulation trace records
├── render.yaml                    ← Render deployment config
└── requirements.txt
```

---

## ICP Segments

| Segment | Target | Qualifying signals |
| --- | --- | --- |
| 1 | Recently-funded Series A/B | $5–30M in last 180 days, 15–80 employees, ≥5 open eng roles |
| 2 | Mid-market cost restructuring | 200–2,000 employees, layoff in last 120 days, ≥3 open roles post-layoff |
| 3 | Engineering leadership transition | New CTO/VP Eng in last 90 days, 50–500 employees |
| 4 | Specialized capability gap | AI maturity ≥2, specific ML/agentic build need, stack on bench |

Priority when multiple fire: Segment 2 > 3 > 4 > 1. Abstain if confidence < 0.6.

---

## τ²-Bench Evaluation

Reference baseline (PM-provided, committed to `score_log.json`):

| Metric | Value |
| --- | --- |
| Domain | retail |
| pass@1 | **72.7%** (95% CI: 0.65–0.79) |
| Tasks / Trials | 30 tasks × 5 trials = 150 simulations |
| p50 latency | 105.95 s |
| p95 latency | 551.65 s |

Run a fresh evaluation trial:

```powershell
$env:PYTHONIOENCODING="utf-8"; $env:NO_COLOR="1"
uv run --project eval/tau2 tau2 run `
  --domain retail `
  --agent-llm "openrouter/google/gemini-2.0-flash-001" `
  --user-llm "openrouter/meta-llama/llama-3.2-3b-instruct" `
  --num-tasks 30 --num-trials 1 `
  --max-concurrency 2
```

---

## Data Handling Policy Summary

| Rule | Requirement | Status |
| --- | --- | --- |
| 1 | No real Tenacious customer data | No CRM exports or live deal data received |
| 2 | All prospects are synthetic | `prospect_info.json` uses fake name + sink domain |
| 3 | Seed materials not redistributed | `seeds/` is gitignored |
| 4 | No hardcoded real emails in code | `OUTBOUND_SINK_EMAIL` required from `.env` only |
| 5 | Kill switch active by default | `OUTBOUND_ENABLED=False` when env vars unset |
| 6 | Tenacious output marked draft | `tenacious_status="draft"` + `X-Tenacious-Status: draft` header |
| 7 | Minimal PII in traces | First name + email only; no home address, payment info |
| 8 | No internal Tenacious data in public repo | Bench capacity as stack names only, no headcount |

Full policy: `seeds/tenacious_sales_data/tenacious_sales_data/policy/data_handling_policy.md` (gitignored)
