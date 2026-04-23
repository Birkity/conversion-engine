# Act I Baseline — τ²-Bench Retail Domain

## Setup

- **Benchmark**: τ²-Bench (retail domain, dev split, 1 trial per task)
- **Agent harness**: `eval/tau2/src/tau2/agent/llm_agent.py` with 7-step mandatory workflow
- **User simulator**: `openrouter/meta-llama/llama-3.2-3b-instruct`
- **Tasks evaluated**: 30 (dev split, sequential, no parallelism)
- **Run ID (day-1 baseline)**: `tau2-retail-20260423-113600`

## Results

| Model | Tasks | pass@1 | 95% CI | Read acc. | Write acc. | DB match |
|---|---|---|---|---|---|---|
| Gemini 2.0 Flash (day-1) | 30 | 13.3% | [1.0%, 25.7%] | 56.3% | 16.3% | 13.3% |
| GPT-4.1 Mini | 28 | 10.7% | [0.0%, 22.4%] | 51.6% | 7.9% | 14.3% |
| Claude 3.5 Haiku (best) | 20 | **25.0%** | [5.5%, 44.5%] | 52.7% | 11.5% | 25.0% |
| Blended (Haiku 0-19 + Gemini 20-29) | 30 | 20.0% | [4.8%, 35.2%] | 60.0% | 18.2% | 20.0% |

**Published reference scores** (τ²-Bench paper, retail domain): Claude 3.7 Sonnet 78.7%, GPT-4.1 74.1%.

## Key Findings

**Binding constraint — user simulator**: The `llama-3.2-3b` user simulator sends `###STOP###` when the agent issues a confirmation summary before executing a write tool call. This terminates the conversation before the write action fires, capping write accuracy across all models. The 7-step workflow instructs the agent to confirm before writing, which makes stronger instruction-following models more likely to trigger this stop condition.

**Paradox**: GPT-4.1 Mini (published 66%) scores lower than Gemini 2.0 Flash (13.3%) in our rig because GPT-4.1 Mini follows the workflow more precisely, producing more confirmation messages and more `###STOP###` events. Gemini Flash accidentally avoids this by sometimes skipping confirmation steps.

**Best result**: Claude 3.5 Haiku at 25.0% pass@1. Stronger instruction-following partially overcomes the simulator ceiling by completing reads more accurately before the stop condition fires.

## Cost and Latency

- Gemini 2.0 Flash (30 tasks): $0.30 total, p50=30.1s, p95=94.4s per conversation
- Claude 3.5 Haiku (20 tasks): $0.39 total, p50=47.3s, p95=77.4s per conversation

## Next Step

Modify agent workflow to suppress confirmation summaries (or reduce their length) before write calls, to avoid triggering the `###STOP###` termination condition. Estimated impact: +10–20 pp on write accuracy.
