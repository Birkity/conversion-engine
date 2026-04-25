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
                            ← inbound SMS reply → lead status IN_PROGRESS + note
                            ← inbound SMS reply → consultant sink email alert
                            ← BOOKING_CANCELLED → lead status OPEN + note
                            ← BOOKING_RESCHEDULED → note on contact (with time)
                            ← BOOKING_CREATED → detailed booking note + lead status IN_PROGRESS
Langfuse cloud free tier    ← per-call cost + latency traces

Webhook Hub (deployed on Render)
──────────────────────────────────────────────
POST /webhooks/resend           ← email reply events → on_email_reply()
POST /webhooks/africastalking   ← SMS delivery + inbound → on_sms_reply()
                                  → searches HubSpot by phone → updates status + note
POST /webhooks/cal              ← BOOKING_CREATED → HubSpot upsert
                                  + detailed note (title/time/link) + status=IN_PROGRESS
                                  BOOKING_CANCELLED → status=OPEN + note
                                  BOOKING_RESCHEDULED → note on contact (+time when available)
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

### Demo — End-to-end conversation simulator

```bash
# Run all 4 scenarios (email + HubSpot + SMS all routed to sinks)
python scripts/demo_runner.py

# Single scenario
python scripts/demo_runner.py arcana_skeptic    # skeptic → clarification → Cal link
python scripts/demo_runner.py pulsesight_sms   # bench question → email → SMS Cal link
python scripts/demo_runner.py novaspark_fast   # Segment 3 fast close (1 turn → Cal link)
python scripts/demo_runner.py coraltech_stop   # NOT_INTERESTED → STOP → HubSpot UNQUALIFIED

# No sends (generate emails + interpret replies only)
python scripts/demo_runner.py --dry-run
```

Runs 4 synthetic companies through the full pipeline: outbound email generation → prospect reply → `interpret_reply()` → `route_decision()` → HubSpot update. One scenario (PulseSight) includes an SMS warm-lead leg after the Cal link is sent. All outbound routes to sinks (kill switch active). Conversation log saved to `demo/demo_log.json`.

| Scenario | Company | Turns | Expected routing | SMS |
| --- | --- | --- | --- | --- |
| `arcana_skeptic` | Arcana Analytics (Seg 1) | 2 | QUESTION → SEND_EMAIL, INTERESTED → SEND_CAL_LINK | — |
| `pulsesight_sms` | PulseSight (Seg 1/4) | 2 | QUESTION → SEND_EMAIL, SCHEDULE → SEND_CAL_LINK | ✓ |
| `novaspark_fast` | NovaSpark (Seg 3) | 1 | INTERESTED → SEND_CAL_LINK | — |
| `coraltech_stop` | CoralTech (disqualified) | 1 | NOT_INTERESTED → STOP | — |

### Act III — Reply interpretation (offline probe suite)

```bash
# Run all 32 adversarial probes against the reply interpreter
python scripts/act3_reply_tests.py

# Run against a specific company's context
python scripts/act3_reply_tests.py --company kinanalytics

# Save full results to probes/probe_results.json
python scripts/act3_reply_tests.py --save-results
```

Loads `probes/probe_cases.json` (32 probes across 10 categories) and runs each through `interpret_reply()` with real brief context from `traces/{company}/` and the persisted `artifacts/{company}/last_email.json`. No emails sent, no CRM writes, no webhooks called.

Current pass rate: **31/32 (97%)** — see `probe_library.md`, `failure_taxonomy.md`, `target_failure_mode.md`.

Output includes:

- Per-probe pass/fail with actual vs. expected intent and next_step
- Per-category pass rate with bar chart
- Schema validation (determinism check: intent always maps to correct next_step)
- Full reasoning and grounding facts from the LLM for every failed probe

### Act I — Brief validation (intelligence layer)

```bash
# Validate that raw signals produce structured briefs
python scripts/act1_brief_validation.py
python scripts/act1_brief_validation.py traces/arcana/signals.json
python scripts/act1_brief_validation.py traces/snaptrade/signals.json
python scripts/act1_brief_validation.py traces/wiseitech/signals.json --outdir out/wiseitech
```

Reads `signals.json` → runs ICP disqualifier pre-screen → displays per-source signal quality bars → calls `brief_generator.generate()` → saves and prints both briefs with confidence scores. Validates all required output fields. No outbound triggered.

Output includes:

- Per-source signal confidence bars (crunchbase / job_velocity / layoffs / ai_maturity)
- ICP disqualifier warnings if headcount >5000, consumer app, or anti-offshore stance detected
- `bench_match` — which stacks are required vs. available on the Tenacious bench
- `honesty_flags` — explicit flags when hiring signal is weak or a bench gap exists

### Act II — Email execution (outbound layer)

```bash
# Generate + send to sink (kill switch active — never reaches real prospect)
python scripts/act2_email_execution.py traces/arcana

# Dry run — generate only, do not send
python scripts/act2_email_execution.py traces/arcana --dry-run

# Other companies
python scripts/act2_email_execution.py traces/kinanalytics --dry-run
python scripts/act2_email_execution.py traces/snaptrade
python scripts/act2_email_execution.py traces/wiseitech
```

Loads `hiring_signal_brief.json` + `competitor_gap_brief.json` + `prospect_info.json` → applies abstention path (confidence < 0.6 forces `icp_segment=Ambiguous`) → generates a style-guide-compliant cold email via LLM → sends to `OUTBOUND_SINK_EMAIL` (never the prospect). Validates all five tone markers before sending. Reports `Email gen latency` and `Total run latency` in the summary.

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

Chains: Crunchbase → Jobs (Playwright first, CSV fallback) → Layoffs.fyi → AI maturity score → LLM brief. Returns `signal_confidence` dict with per-source confidence scores (crunchbase, job_velocity, layoffs, ai_maturity) and `disqualifiers` list.

Disqualifier pre-screen runs before any LLM call. If a company fires a disqualifier (headcount >5000, consumer app industry, anti-offshore stance in description), the pipeline returns stub briefs with `icp_segment="disqualified"` and skips the LLM call entirely.

Signal confidence propagates into both brief paths:

- `agent/enrichment/pipeline.py` passes the computed per-source confidence map into `generate_briefs()`.
- `agent/brief_generator/brief_generator.py` derives per-source confidence from `signals.json` for the Act I path and injects it into the LLM prompt.

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
  "email": "prospect@sink.example.com",
  "phone": "+15559999001",
  "company": "Acme Corp",
  "_policy_note": "Synthetic prospect. Rule 2: email resolves to program sink."
}
```

> **Rule 2:** `email` and `phone` must be synthetic/sink contact details — never real contact info.
>
> **Email domain:** Use `@sink.example.com` (RFC 2606 reserved — non-routable, but accepted by HubSpot's email validator). The `.internal` TLD is rejected by HubSpot even though it is also non-routable.
>
> **HubSpot custom properties:** The sandbox requires these five custom contact properties to be created before the first upsert: `enrichment_timestamp`, `tenacious_status`, `ai_maturity_score`, `icp_segment`, `enrichment_confidence`. Run `python scripts/hubspot_smoketest.py` after sandbox setup to verify.

---

## Project Structure

```text
conversion-engine/
├── agent/
│   ├── reply_interpreter/         ← Act III: reply classification + routing
│   │   ├── reply_interpreter.py   ← interpret_reply() → intent/next_step/confidence
│   │   ├── router.py              ← route_decision() → send email/cal/stop + bench guard
│   │   └── prompts.py             ← System prompt with self-disclosure + tone rules
│   ├── brief_generator/           ← Intelligence layer
│   │   ├── bench.py               ← Dynamic bench loader (reads bench_summary.json at import)
│   │   ├── brief_generator.py     ← generate(signals) → {hiring_brief, gap_brief, disqualifiers}
│   │   ├── llm_client.py          ← OpenRouter + Langfuse auto-tracing
│   │   └── prompts.py             ← SYSTEM_PROMPT (dynamic bench + ICP + tone constraints)
│   ├── enrichment/                ← Signal collection
│   │   ├── pipeline.py            ← Orchestrator: disqualifier check → signals → briefs
│   │   ├── crunchbase.py          ← Crunchbase ODM loader
│   │   ├── jobs.py                ← Job velocity (Playwright first, CSV fallback)
│   │   ├── jobs_playwright.py     ← Public LinkedIn job scraper (no login)
│   │   ├── layoffs.py             ← layoffs.fyi CSV lookup
│   │   ├── maturity.py            ← Rule-based AI maturity scorer (0–3)
│   │   └── signal_brief.py        ← LLM brief call (Langfuse traced, synced schema)
│   ├── email/
│   │   ├── handler.py             ← Resend SMTP + kill switch + draft header
│   │   └── generator.py           ← LLM email composer (all 5 tone markers validated)
│   ├── sms/handler.py             ← Africa's Talking + warm-lead gate + inbound CRM routing
│   ├── hubspot/client.py          ← Contact upsert, enrichment note, search, add_note, update_contact
│   └── calendar/client.py         ← Cal.com booking link generator
├── webhook/main.py                ← FastAPI hub: 5 endpoints, HMAC verified
├── scripts/
│   ├── act1_brief_validation.py   ← Validate briefs + signal quality display + disqualifier check
│   ├── act2_email_execution.py    ← Generate + send outreach email (abstention path + latency)
│   ├── act3_reply_tests.py        ← 32-probe adversarial suite (97% pass rate)
│   ├── test_brief.py              ← Per-company brief generation
│   ├── integration_smoketest.py   ← Full chain smoke test
│   ├── update_score_log.py        ← τ²-Bench results → score_log.json
│   └── *_smoketest.py             ← Per-service smoke tests
├── probes/
│   ├── probe_cases.json           ← 32 adversarial test cases (10 categories)
│   └── probe_results.json         ← Latest run results (31/32 passed, 97%)
├── traces/
│   ├── arcana/                    ← Segment 1 (clean): FinTech Series A, 42 hc, 6 open roles
│   │   ├── signals.json
│   │   ├── hiring_signal_brief.json
│   │   ├── competitor_gap_brief.json
│   │   └── prospect_info.json     ← Synthetic prospect (Rule 2)
│   ├── kinanalytics/              ← Segment 1: Series A, 35 hc, 7 open roles
│   ├── pulsesight/                ← Segment 1/4: Series A $9M, ML Infrastructure, 31 hc
│   ├── novaspark/                 ← Segment 3: Series B $22M, new VP Eng (Feb 2026), 85 hc
│   ├── coraltech/                 ← Disqualified: B2C e-commerce, anti-offshore CEO stance
│   ├── snaptrade/                 ← Ambiguous: decelerating hiring, no funding
│   └── wiseitech/                 ← Ambiguous: zero jobs, weak signal flagged
├── demo/
│   ├── scenarios.json             ← 4 demo scenario definitions with expected routing
│   └── demo_log.json              ← Output from last demo_runner.py run
├── policy/
│   └── acknowledgement_signed.txt ← Rule 5 compliance acknowledgement
├── probe_library.md               ← All 32 probes documented by category + business impact
├── failure_taxonomy.md            ← Per-category pass rates, trigger rates, fixes applied
├── target_failure_mode.md         ← Primary failure (tone_drift) — root cause + resolution
├── baseline.md                    ← τ²-Bench baseline, cost-per-lead, stalled-thread delta
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
| 8 | No internal Tenacious data in public repo | Bench capacity loaded at runtime from gitignored `seeds/` — only stack names in committed code |

Full policy: `seeds/tenacious_sales_data/tenacious_sales_data/policy/data_handling_policy.md` (gitignored)

---

## Signal Quality Improvements (April 24, 2026)

The following improvements were made to the brief generation pipeline and output validation:

| Improvement | What changed |
| --- | --- |
| Dynamic bench loading | `agent/brief_generator/bench.py` reads `bench_summary.json` at import time. NestJS is correctly flagged as committed through Q3 2026 (unavailable for new work) rather than listed as available. Prompt fallback when seeds absent. |
| Prompt sync (both paths) | `signal_brief.py` (pipeline path) SYSTEM_PROMPT now matches `prompts.py` (act1 path): bench block, ICP priority order, tone rules, `bench_match` + `honesty_flags` in output schema. Both paths now produce identical output structure. |
| ICP disqualifier pre-screen | `_check_disqualifiers()` in both `pipeline.py` and `brief_generator.py` rejects companies with headcount >5000, consumer-app industry, or anti-offshore stance **before** the LLM is called. Returns `icp_segment="disqualified"` with reasons. |
| Exec commentary extraction | `pipeline.py` now extracts executive AI keywords from `recent_news`, `description`, and `leadership_changes` before calling `maturity.score()`, improving the rule-based pre-score for funded companies with AI announcements. |
| Sector AI distribution | `_compute_sector_ai_distribution()` computes median and p75 AI maturity scores from sector peers and appends them to the competitor signals block, giving the LLM quantitative context for `prospect_position_in_sector`. |
| Abstention path enforcement | `act2_email_execution.py` overrides `icp_segment` to `Ambiguous` when `confidence < 0.6`, enforcing the spec rule: "abstain from segment-specific pitch when signal is insufficient." |
| Signal quality display | `act1_brief_validation.py` prints per-source confidence bars before the LLM call and shows them again in the Confidence Summary alongside brief output confidence. |
| Latency measurement | `act2_email_execution.py` measures and reports `Email gen latency` and `Total run latency` in the Summary section. |
| 5-marker tone validation | `generator.py` now checks all five style-guide tone markers: DIRECT (subject prefix pattern), GROUNDED (aggressive-hiring gate), HONEST (`bench` jargon ban), PROFESSIONAL (extended phrase list), NON-CONDESCENDING (deficit framing detection). |
| Act II booking-link removal | `generator.py` system prompt Line 5 changed to "soft open question that invites a reply — no booking link, no specific times, no '15 minutes'." `=== CAL.COM BOOKING LINK ===` section removed from user template. Hard post-generation validator added for `http`, `cal.com`, `schedule`, `book a`, `15 minutes`. |
| Artifact persistence | `act2_email_execution.py` saves `artifacts/{company}/last_email.json` after each send + appends to `email_log.jsonl` (gitignored). Act III test harness loads real artifact for grounded probe context. |

---

## Outreach Email Sequence

The agent produces three emails per prospect following `seeds/.../email_sequences/cold.md`. Structure is enforced at the LLM prompt level; individual emails must be signal-grounded, not templated:

| Email | Timing | Purpose |
| --- | --- | --- |
| Email 1 | Day 0 | Signal-grounded opener (120 words max). Subject pattern varies by ICP segment. |
| Email 2 | Day 5 | New competitor-gap data point — not a follow-up nag. 100 words max. |
| Email 3 | Day 12 | Gracious close. 70 words max. Leaves a door open, stops the sequence. |

Sequence terminates immediately on prospect reply, opt-out, bounce, or later disqualification.

---

## HubSpot Integration

The HubSpot developer sandbox acts as the contact database and activity log for every prospect interaction. All writes use the private-app token (`HUBSPOT_PRIVATE_APP_TOKEN`). No OAuth flow or webhook subscription is required for write-path operations.

### Contact lifecycle

```text
Act II email sent
      │
      ▼
upsert_contact()  ──► NEW (hs_lead_status)
      │                + enrichment_timestamp, tenacious_status="draft",
      │                  ai_maturity_score, icp_segment, enrichment_confidence
      │
      ├── Cal.com BOOKING_CREATED ──► search_contact(email)
      │                               add_note(booking title / time / video link)
      │                               update_contact(hs_lead_status=IN_PROGRESS)
      │
      ├── Africa's Talking inbound SMS ──► search_contact(phone)
      │                                    add_note(SMS text + timestamp)
      │                                    update_contact(hs_lead_status=IN_PROGRESS)
      │
      └── Cal.com BOOKING_CANCELLED ──► search_contact(email)
                                        add_note(cancelled + original time)
                                        update_contact(hs_lead_status=OPEN)
```

`BOOKING_RESCHEDULED` events also call `add_note()` with the new time but do not change `hs_lead_status`.

### Client functions (`agent/hubspot/client.py`)

| Function | When called | What it does |
| --- | --- | --- |
| `upsert_contact(email, first_name, last_name, company, phone, enrichment)` | Act II script, Cal.com BOOKING_CREATED | POST `/crm/v3/objects/contacts` — falls back to PATCH on 409 conflict |
| `search_contact(filter_property, value)` | Webhook handlers | POST `/crm/v3/objects/contacts/search` — returns contact ID or None |
| `update_contact(contact_id, properties)` | Webhook handlers | PATCH `/crm/v3/objects/contacts/{id}` — always sets `tenacious_status=draft` as default |
| `add_note(contact_id, note_body)` | Webhook handlers | POST `/crm/v3/objects/notes` with association to contact |
| `log_enrichment_note(contact_id, enrichment)` | Integration smoketest | Convenience wrapper — formats brief fields as a structured note body |

### Webhook-driven state machine

```text
Endpoint                    Trigger event          HubSpot side-effects
──────────────────────────  ─────────────────────  ──────────────────────────────────────────
POST /webhooks/cal          BOOKING_CREATED        upsert → add_note(booking details)
                                                   → status=IN_PROGRESS
POST /webhooks/cal          BOOKING_CANCELLED      search → add_note(cancelled)
                                                   → status=OPEN
POST /webhooks/cal          BOOKING_RESCHEDULED    search → add_note(new time only)
POST /webhooks/africastalking  inbound SMS         search by phone → add_note(text)
                                                   → status=IN_PROGRESS
POST /webhooks/resend       email.delivered etc.   on_email_reply() — logs event, no CRM write
POST /webhooks/hubspot      CRM subscription       logs event only (contact.propertyChange etc.)
```

All webhook endpoints verify HMAC signatures (Svix for Resend, SHA-256 for Cal.com, SHA-256 for HubSpot). Signature failures emit a `WARNING` log but do not block in dev mode.

### Custom properties (required in a fresh sandbox)

Five custom contact properties must be created before the first upsert. Run once per sandbox:

```python
# Via HubSpot Properties API (or the Sandbox UI: Contacts → Properties → Create)
properties = [
    ("enrichment_timestamp", "string"),
    ("tenacious_status",     "string"),   # always "draft"
    ("ai_maturity_score",    "string"),   # "0"–"3"
    ("icp_segment",          "string"),   # segment label from brief
    ("enrichment_confidence","string"),   # "0.0"–"1.0"
]
```

After creating the properties, verify with `python scripts/hubspot_smoketest.py`.

---

## Reply Interpreter (Act III)

The reply interpreter takes a prospect's reply and decides what happens next. It runs as a pure offline reasoning step — no email sent, no CRM written — until `route_decision()` is called with its output.

### Intent classification

`interpret_reply(reply_text, last_email, briefs, prospect_info)` returns:

```json
{
  "intent": "INTERESTED | NOT_INTERESTED | QUESTION | SCHEDULE | UNKNOWN",
  "confidence": 0.90,
  "next_step": "SEND_CAL_LINK | SEND_EMAIL | ASK_CLARIFICATION | STOP",
  "reasoning": "...",
  "grounding_facts_used": ["Series A $14M closed March 2026", "..."]
}
```

Intent → next_step mapping is deterministic (enforced at the router level):

| Intent | Next Step | Action |
| --- | --- | --- |
| INTERESTED | SEND_CAL_LINK | Cal.com booking link emailed to prospect |
| SCHEDULE | SEND_CAL_LINK | Cal.com booking link emailed to prospect |
| QUESTION | SEND_EMAIL | Grounded clarification email, no booking ask |
| NOT_INTERESTED | STOP | HubSpot status → UNQUALIFIED, no further contact |
| UNKNOWN | ASK_CLARIFICATION | Soft follow-up: "more detail or a different time?" |

### Key classifier rules

**Self-disclosure buying signals → INTERESTED:**
A prospect admitting a gap in the domain being pitched counts as an implicit "yes, relevant":
- "our AI team is not great right now" → INTERESTED → SEND_CAL_LINK
- "we're definitely behind our competitors on AI" → INTERESTED → SEND_CAL_LINK

**Capacity requests → QUESTION (not INTERESTED):**
"We need 8 NestJS engineers in 3 weeks" asks about our capacity — it is not a self-disclosure. Route to SEND_EMAIL with honest bench disclosure.

**Signal challenges → QUESTION (not NOT_INTERESTED):**
"Your data was wrong" or "our roles are for sales, not engineering" challenges a fact but does not opt out. Route to SEND_EMAIL; never STOP.

**Authenticity challenges → QUESTION:**
"Is this AI-generated?" or "are you a real person?" are questions requiring a direct honest answer, not a clarification ask.

**Qualified dates → UNKNOWN:**
"Maybe June 30th" is UNKNOWN → ASK_CLARIFICATION. "Thursday 9am works" is SCHEDULE → SEND_CAL_LINK.

### Router bench guard

Before sending a Cal.com booking link, `_action_send_cal_link()` checks `hsb.bench_match.bench_available`. If `false`, it downgrades to `SEND_EMAIL` with an honest disclosure:

> "Our NestJS engineers are currently committed through Q3 2026. We do have Python, ML, and Data engineers available."

This prevents booking a discovery call that would set expectations for capacity we cannot fulfil.

### Probe suite results (2026-04-24)

| Run | Pass Rate | Notes |
| --- | --- | --- |
| Run 1 (pre-fix) | 75% (24/32) | tone_drift 0/3, signal_over_claim 1/3, scheduling 1/3 |
| Run 2 (post-fix) | **97% (31/32)** | One label mismatch remaining (probe #7, low business risk) |

Run the suite: `python scripts/act3_reply_tests.py --save-results`

---

## Security Audit (April 23, 2026)

A full data-leakage audit was run against the committed repository. Findings and dispositions:

| Finding | Severity | Disposition |
| --- | --- | --- |
| `.env` contains real API keys | Critical | `.env` is in `.gitignore` line 1 — **not tracked by git**. Keys are local only. |
| `Birkity@10academy.org` hardcoded as default in `scripts/resend_smoketest.py` | Medium | **Fixed** — default removed; script now requires `RESEND_SMOKE_TEST_EMAIL` in `.env` or exits with an error instead of silently emailing a real inbox. |
| Personal Cal.com slug as fallback in `agent/calendar/client.py` | Low | **Intentional** — this is the programme-specific booking link, not a data leak. Remains as-is. |
| `prospect_info.json` contact data | Check | All prospects use synthetic `@sink.example.com` addresses (RFC 2606 reserved). Rule 2 compliant. `.internal` TLD was changed after HubSpot rejected it. |
| `.env` contains real API keys | Check | `.env` is in `.gitignore` line 1 — **not tracked by git**. `git ls-files .env` returns nothing. |
| `seeds/` contains Tenacious bench data | Check | `seeds/` is gitignored — **not tracked by git**. `git ls-files seeds/` returns nothing. |
| `score_log.json` and `trace_log.jsonl` committed | Check | **Intentional** — required submission deliverables. No PII in either file. |
| `interim_report.tex` contains full name | Check | `*.tex` is in `.gitignore` — file is **not tracked by git**. |
| LLM prompts in `prompts.py` and `generator.py` | Check | All prompts use parametric templates. No real data embedded. |
| `policy/acknowledgement_signed.txt` contains full name | Check | **Intentional** — signed policy acknowledgement required by the programme. |

**Verdict (updated April 24, 2026):** No credentials, personal contact data, or real prospect PII are committed to the repository. `.env` and `seeds/` are gitignored and have never been tracked by git — audit tool false positives that scanned the local filesystem rather than git-tracked files. One medium-severity hardcoded email default was found and fixed (April 23). The `@sink.trp1.internal` email domain used in early `prospect_info.json` files was changed to `@sink.example.com` after HubSpot rejected the `.internal` TLD — both are RFC-reserved non-routable domains; the change is a technical fix, not a policy violation.
