# Conversion Engine — Tenacious Consulting Edition

Automated lead generation and conversion system for B2B engineering consulting outreach. Finds high-signal prospects from public data, qualifies them against four ICP segments, and runs multi-channel nurture sequences (email → SMS → Cal.com booking) while writing every interaction to HubSpot.

> **Kill switch:** `LIVE_OUTBOUND_ENABLED=false` (default). All outbound routes to a staff sink — no real prospects contacted unless explicitly enabled.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Enrichment Pipeline                       │
│  Crunchbase ODM → Jobs (LinkedIn) → Layoffs.fyi             │
│  → AI Maturity Score (rule-based pre-score 0–3)             │
│  → LLM Signal Brief (OpenRouter · qwen/qwen3-30b-a3b)       │
│  → hiring_signal_brief.json + competitor_gap_brief.json     │
└──────────────────────┬──────────────────────────────────────┘
                       │
     ┌─────────────────▼──────────────────┐
     │        Brief Generator Module       │
     │  agent/brief_generator/             │
     │  Input:  traces/<co>/signals.json   │
     │  Model:  google/gemini-2.0-flash    │
     │  Output: hiring_signal_brief.json   │
     │          competitor_gap_brief.json  │
     └─────────────────┬──────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │      Outbound Channels      │
        │  Email: Resend SMTP relay   │
        │  SMS:   Africa's Talking    │
        │  Cal:   Cal.com booking     │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │       CRM + Tracing         │
        │  HubSpot: contact + notes   │
        │  Langfuse: auto-traced via  │
        │  langfuse.openai wrapper    │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │     Webhook Hub (Render)    │
        │  /webhooks/resend           │
        │  /webhooks/africastalking   │
        │  /webhooks/cal              │
        │  /webhooks/hubspot          │
        └─────────────────────────────┘
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/Birkity/conversion-engine.git
cd conversion-engine
pip install -r requirements.txt
playwright install chromium
```

### 2. Seed data

```bash
# Crunchbase ODM (1,513 company records, Apache 2.0)
git clone https://github.com/luminati-io/Crunchbase-dataset-samples seeds/crunchbase

# τ²-Bench evaluation harness
git clone https://github.com/sierra-research/tau2-bench eval/tau2
cd eval/tau2 && uv sync && cd ../..
```

### 3. Environment

```bash
cp .env.example .env
# Fill in all keys — see .env.example for required vars
```

Required variables:

| Variable | Purpose |
| --- | --- |
| `OPENROUTER_API_KEY` | LLM inference for enrichment + brief generation |
| `BRIEF_GENERATOR_MODEL` | Model for brief_generator (default: `google/gemini-2.0-flash-001`) |
| `RESEND_API_KEY` + `RESEND_WEBHOOK_SECRET` | Email via Resend SMTP |
| `AT_USERNAME` + `AT_API_KEY` | SMS via Africa's Talking |
| `HUBSPOT_PRIVATE_APP_TOKEN` | HubSpot CRM |
| `CALCOM_API_KEY` + `CALCOM_EVENT_URL` | Cal.com calendar booking |
| `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` | Observability (Langfuse US region) |
| `LANGFUSE_BASE_URL` | `https://us.cloud.langfuse.com` |
| `LIVE_OUTBOUND_ENABLED` | `false` (safe default) / `true` for live sends |

### 4. Smoke tests

```bash
# Verify individual external services
python scripts/africastalking_smoketest.py
python scripts/hubspot_smoketest.py
python scripts/langfuse_smoketest.py
python scripts/resend_smoketest.py

# Verify all four channels in one shot (enrichment → email → HubSpot → Cal.com)
python scripts/integration_smoketest.py SnapTrade

# Verify webhook hub locally
uvicorn webhook.main:app --reload &
python scripts/webhook_smoketest.py
```

---

## Usage

### Generate briefs for a company

Each company lives in `traces/<company>/`. Create a `signals.json` there, then run:

```bash
python scripts/test_brief.py snaptrade
python scripts/test_brief.py wiseitech
```

This reads `traces/<company>/signals.json`, calls the LLM, and writes:

- `traces/<company>/hiring_signal_brief.json`
- `traces/<company>/competitor_gap_brief.json`

**`signals.json` schema:**

```json
{
  "company_name": "Acme Corp",
  "industries": ["SaaS", "FinTech"],
  "headcount": "51-200",
  "description": "One-line description.",
  "funding_info": "Series A $12M in 2023.",
  "layoffs": "No layoff events found in last 120 days.",
  "jobs_now": 8,
  "jobs_60_days": 3,
  "tech_stack": ["Python", "AWS", "Kubernetes"],
  "ai_roles": ["ML Engineer"],
  "competitor_signals": [
    {
      "name": "Competitor A",
      "funding": "Series C $80M",
      "tech_stack": ["Python", "TensorFlow", "GCP"],
      "ai_maturity_score": 2
    }
  ]
}
```

### Run the full enrichment pipeline

```bash
python -m agent.enrichment.pipeline "Stripe"
```

Returns the full enrichment dict including both briefs.

### Use the brief generator as a module

```python
from agent.brief_generator import generate
import json

signals = json.load(open("traces/snaptrade/signals.json"))
result = generate(signals)
print(result["hiring_signal_brief"])
print(result["competitor_gap_brief"])
```

### Start the webhook server

```bash
uvicorn webhook.main:app --host 0.0.0.0 --port 8000
```

Deployed at: `https://conversion-engine.onrender.com`

| Endpoint | Service |
| --- | --- |
| `POST /webhooks/resend` | Resend email events (Svix-signed) |
| `POST /webhooks/africastalking` | Africa's Talking SMS callbacks |
| `POST /webhooks/cal` | Cal.com booking events |
| `POST /webhooks/hubspot` | HubSpot CRM events |
| `GET /health` | Liveness check |

---

## Evaluation (τ²-Bench)

Run a fresh trial (starts new simulation folder):

```powershell
$env:PYTHONIOENCODING="utf-8"; $env:NO_COLOR="1"
uv run --project eval/tau2 tau2 run `
  --domain retail `
  --agent-llm "openrouter/google/gemini-2.0-flash-001" `
  --user-llm "openrouter/meta-llama/llama-3.2-3b-instruct" `
  --num-tasks 30 --num-trials 1 `
  --max-concurrency 2
```

Resume a stopped run (skips already-completed simulations):

```powershell
$env:PYTHONIOENCODING="utf-8"; $env:NO_COLOR="1"
uv run --project eval/tau2 tau2 run `
  --domain retail `
  --agent-llm "openrouter/google/gemini-2.0-flash-001" `
  --user-llm "openrouter/meta-llama/llama-3.2-3b-instruct" `
  --num-tasks 30 --num-trials 5 `
  --max-concurrency 2 --auto-resume
```

After any run, update the score log:

```bash
python scripts/update_score_log.py
```

See `score_log.json` for recorded run summaries and
`eval/tau2/data/simulations/<run_id>/results.json` for full raw evaluation outputs.

---

## Project Structure

```
conversion-engine/
├── agent/
│   ├── brief_generator/        ← Standalone brief generator module (NEW)
│   │   ├── __init__.py         ← Exports generate()
│   │   ├── brief_generator.py  ← Main logic: generate(signals) -> dict
│   │   ├── llm_client.py       ← OpenRouter call + Langfuse auto-tracing
│   │   └── prompts.py          ← SYSTEM_PROMPT + USER_TEMPLATE
│   ├── enrichment/             ← Full enrichment pipeline
│   │   ├── pipeline.py         ← Orchestrator: Crunchbase→Jobs→Layoffs→LLM
│   │   ├── signal_brief.py     ← LLM prompt + OpenRouter call (Langfuse traced)
│   │   ├── crunchbase.py       ← Seed data loader + field extractors
│   │   ├── jobs.py             ← LinkedIn job post velocity
│   │   ├── layoffs.py          ← layoffs.fyi CSV lookup
│   │   └── maturity.py         ← Rule-based AI maturity pre-scorer (0–3)
│   ├── email/handler.py        ← Resend SMTP outbound + signal-grounded template
│   ├── sms/handler.py          ← Africa's Talking send + nurture SMS
│   ├── hubspot/client.py       ← Contact upsert + enrichment note
│   └── calendar/client.py      ← Cal.com booking link generator
├── webhook/main.py             ← FastAPI webhook hub (deployed on Render)
├── eval/
│   └── tau2/                   ← τ²-Bench checkout (gitignored)
├── scripts/
│   ├── test_brief.py           ← Run brief generator per company (NEW)
│   ├── integration_smoketest.py← End-to-end: enrich→email→HubSpot→Cal (NEW)
│   ├── update_score_log.py     ← Parse tau2 results → score_log.json
│   ├── africastalking_smoketest.py
│   ├── hubspot_smoketest.py
│   ├── langfuse_smoketest.py
│   ├── resend_smoketest.py
│   └── webhook_smoketest.py
├── seeds/
│   ├── crunchbase/             ← 1,513 company records (gitignored, clone locally)
│   ├── layoffs/                ← layoffs.fyi CSV
│   └── job_posts/              ← LinkedIn job postings (gitignored — 493 MB)
├── traces/
│   ├── snaptrade/
│   │   ├── signals.json        ← Brief generator input
│   │   ├── hiring_signal_brief.json
│   │   ├── competitor_gap_brief.json
│   │   └── enrichment_sample.json
│   ├── wiseitech/
│   │   ├── signals.json        ← Brief generator input
│   │   ├── hiring_signal_brief.json
│   │   ├── competitor_gap_brief.json
│   │   └── enrichment_sample.json
│   └── README.md
├── score_log.json              ← τ²-Bench run summary history
├── trace_log.jsonl             ← Appended simulation traces
├── Procfile                    ← Render start command
├── render.yaml                 ← Render service config
└── requirements.txt
```

---

## ICP Segments (Tenacious)

| Segment | Description | Signal |
| --- | --- | --- |
| 1 | Recently-funded Series A/B | $5–30M in last 6 months, 15–80 employees |
| 2 | Mid-market cost restructuring | 200–2,000 employees, post-layoff |
| 3 | Engineering leadership transition | New CTO/VP Eng in last 90 days |
| 4 | Specialized capability gap | ML/agentic/data project needing external skills, AI maturity ≥ 2 |

---

## Data Handling

- All prospect data during challenge week is synthetic (public Crunchbase + fictitious contacts)
- `LIVE_OUTBOUND_ENABLED=false` by default — all outbound routes to `OUTBOUND_SINK_EMAIL` / `AT_SMOKE_TEST_PHONE`
- No real Tenacious customer data used
- Seed materials (sales deck, pricing, case studies) deleted at week end per license; code kept
