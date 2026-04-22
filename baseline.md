# τ²-Bench Retail Baseline — Dev Tier

**Date:** 2026-04-22  
**Model (agent):** `openrouter/qwen/qwen3-30b-a3b`  
**Model (user):** `openrouter/meta-llama/llama-3.2-3b-instruct`  
**Domain:** retail | **Dev slice:** 3 tasks (smoke) | **Trials:** 1

## What Reproduced

The τ²-Bench retail harness runs cleanly on Windows via `uv run` with `PYTHONIOENCODING=utf-8 NO_COLOR=1`. All 3 tasks loaded. 2/3 tasks evaluated to completion; 1 hit a recoverable infrastructure error (resolved — see below).

**Pass@1 = 0.000** (0/2 tasks passed). This is expected for a 30B-parameter MoE dev model against retail tasks whose SOTA is ~42% with GPT-5-class models.

## Per-Task Results

| Task | Duration | Read accuracy | Write accuracy | Reward | Termination |
|------|----------|---------------|----------------|--------|-------------|
| 0 | 48s | 0/4 (0%) | 0/1 (0%) | 0.0 | USER_STOP |
| 1 | 75s | 2/4 (50%) | 0/1 (0%) | 0.0 | USER_STOP |
| 2 | 847s | 1/10 (10%) | 0/1 (0%) | 0.0 | USER_STOP |

Task 1 shows the agent correctly calling `find_user_id_by_name_zip` and `get_order_details` (50% read accuracy) but failing to select the correct product IDs and never executing the write action (`exchange_delivered_order_items`). This is the canonical τ²-Bench failure mode: reasoning chain breaks before the write step.

## Cost and Latency

- **Cost per run:** $0.00 reported (LiteLLM pricing table does not yet include `qwen/qwen3-30b-a3b-04-28` alias — actual tokens were consumed at OpenRouter rates).
- **Wall-clock p50:** ~61s | **p95:** ~847s (task 2 ran multiple retries).
- **Concurrency:** 1 (sequential).

## Unexpected Behavior

1. **Empty assistant messages:** `qwen3-30b-a3b` occasionally returned responses with neither content nor tool_calls on task 2, triggering tau2's retry loop (3 retries → infra error). Root cause: new model alias routing. Fixed by also setting `OPENAI_BASE_URL=https://openrouter.ai/api/v1` and `OPENAI_API_KEY=<openrouter key>` in `eval/tau2/.env` so tau2's internal evaluation calls route through OpenRouter rather than failing against a placeholder key.

2. **Model alias resolution:** OpenRouter resolved `qwen/qwen3-30b-a3b` → `qwen/qwen3-30b-a3b-04-28`. LiteLLM did not recognize this as a mapped model, so cost tracking returned $0. Token usage was real.

## Plan for Act I Completion

Full 30-task, 5-trial dev baseline requires eval-tier model (`claude-sonnet-4-6` or pinned staff model). Command:

```bash
cd eval/tau2
PYTHONIOENCODING=utf-8 NO_COLOR=1 uv run tau2 run \
  --domain retail \
  --agent-llm "openrouter/qwen/qwen3-30b-a3b" \
  --user-llm "openrouter/meta-llama/llama-3.2-3b-instruct" \
  --num-tasks 30 --num-trials 5 \
  --max-concurrency 3 --auto-resume
```
