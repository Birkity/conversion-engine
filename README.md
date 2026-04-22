# Conversion Engine — Tenacious Consulting Edition

Automated lead generation and conversion system for B2B engineering consulting outreach. Finds high-signal prospects from public data, qualifies them against four ICP segments, and runs multi-channel nurture sequences (email → SMS → Cal.com booking) while writing every interaction to HubSpot.

> **Kill switch:** `LIVE_OUTBOUND_ENABLED=false` (default). All outbound routes to a staff sink — no real prospects contacted unless explicitly enabled.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Enrichment Pipeline                    │
│  Crunchbase ODM → Jobs (LinkedIn) → Layoffs.fyi         │
│  → AI Maturity Score (rule-based pre-score)             │
│  → LLM Signal Brief (OpenRouter qwen3-30b-a3b)         │
│  → hiring_signal_brief.json + competitor_gap_brief.json │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │     Outbound Channels       │
        │  Email: Resend SMTP relay   │
        │  SMS:   Africa's Talking    │
        │  Cal:   Cal.com booking     │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │        CRM + Tracing        │
        │  HubSpot: contact + notes   │
        │  Langfuse: trace per run    │
        └─────────────────────────────┘
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

Required:
- `OPENROUTER_API_KEY` — LLM inference (dev tier)
- `RESEND_API_KEY` + `RESEND_WEBHOOK_SECRET` — email
- `AT_USERNAME` + `AT_API_KEY` — SMS
- `HUBSPOT_PRIVATE_APP_TOKEN` — CRM
- `CALCOM_API_KEY` + `CALCOM_EVENT_URL` — calendar
- `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` — observability

### 4. Smoke tests

```bash
# Verify all external services
python scripts/africastalking_smoketest.py
python scripts/hubspot_smoketest.py
python scripts/langfuse_smoketest.py
python scripts/resend_smoketest.py

# Verify webhook hub locally
uvicorn webhook.main:app --reload &
python scripts/webhook_smoketest.py
```

---

## Usage

### Generate a signal brief

```bash
python -m agent.enrichment.pipeline "Stripe"
```

Returns `hiring_signal_brief` + `competitor_gap_brief` as JSON.

### Start the webhook server

```bash
uvicorn webhook.main:app --host 0.0.0.0 --port 8000
```

Deployed at: `https://conversion-engine.onrender.com`

| Endpoint | Service |
|----------|---------|
| `POST /webhooks/resend` | Resend email events (Svix-signed) |
| `POST /webhooks/africastalking` | Africa's Talking SMS callbacks |
| `POST /webhooks/cal` | Cal.com booking events |
| `POST /webhooks/hubspot` | HubSpot CRM events |
| `GET /health` | Liveness check |

---

## Evaluation (τ²-Bench)

```bash
# Dev-tier baseline (cheap, full 30-task run)
cd eval/tau2
PYTHONIOENCODING=utf-8 NO_COLOR=1 uv run tau2 run \
  --domain retail \
  --agent-llm "openrouter/qwen/qwen3-30b-a3b" \
  --user-llm "openrouter/meta-llama/llama-3.2-3b-instruct" \
  --num-tasks 30 --num-trials 5 \
  --max-concurrency 3 --auto-resume

# Eval-tier (sealed held-out, Days 5–7)
PYTHONIOENCODING=utf-8 NO_COLOR=1 uv run tau2 run \
  --domain retail \
  --agent-llm "openrouter/anthropic/claude-sonnet-4-6" \
  --user-llm "openrouter/meta-llama/llama-3.2-3b-instruct" \
  --num-tasks 20 --num-trials 5 \
  --max-concurrency 3 --auto-resume
```

See `baseline.md` for dev-tier results. See `eval/score_log.json` for all recorded runs.

---

## Project Structure

```
conversion-engine/
├── agent/
│   ├── enrichment/         ← Signal brief pipeline (core intelligence layer)
│   │   ├── pipeline.py     ← Orchestrator: Crunchbase→Jobs→Layoffs→LLM brief
│   │   ├── signal_brief.py ← LLM prompt + OpenRouter call
│   │   ├── crunchbase.py   ← Seed data loader + field extractors
│   │   ├── jobs.py         ← LinkedIn job post velocity
│   │   ├── layoffs.py      ← layoffs.fyi CSV lookup
│   │   └── maturity.py     ← Rule-based AI maturity pre-scorer (0–3)
│   ├── email/handler.py    ← Resend SMTP outbound + signal-grounded template
│   ├── sms/handler.py      ← Africa's Talking send + nurture SMS
│   ├── hubspot/client.py   ← Contact upsert + enrichment note
│   └── calendar/client.py  ← Cal.com booking link generator
├── webhook/main.py         ← FastAPI webhook hub (deployed on Render)
├── eval/
│   ├── score_log.json      ← τ²-Bench run history
│   └── tau2/               ← τ²-Bench checkout (gitignored)
├── scripts/                ← Smoke tests + local test utilities
├── seeds/
│   ├── crunchbase/         ← 1,513 company records (gitignored, clone locally)
│   ├── layoffs/            ← layoffs.fyi CSV
│   └── job_posts/          ← LinkedIn job postings (gitignored — 493MB)
├── traces/                 ← Runtime trace JSONL (gitignored)
├── baseline.md             ← τ²-Bench dev-tier baseline report
├── Procfile                ← Render start command
├── render.yaml             ← Render service config
└── requirements.txt
```

---

## ICP Segments (Tenacious)

| Segment | Description | Signal |
|---------|-------------|--------|
| 1 | Recently-funded Series A/B | $5–30M in last 6 months, 15–80 employees |
| 2 | Mid-market cost restructuring | 200–2,000 employees, post-layoff |
| 3 | Engineering leadership transition | New CTO/VP Eng in last 90 days |
| 4 | Specialized capability gap | ML/agentic/data project needing external skills, AI maturity ≥2 |

---

## Data Handling

- All prospect data during challenge week is synthetic (public Crunchbase + fictitious contacts)
- `LIVE_OUTBOUND_ENABLED=false` by default — all outbound routes to `OUTBOUND_SINK_EMAIL` / `AT_SMOKE_TEST_PHONE`
- No real Tenacious customer data used
- Seed materials (sales deck, pricing, case studies) deleted at week end per license; code kept
