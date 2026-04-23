"""
Parse a TAU2 results.json and update root logs:
    - score_log.json
    - trace_log.jsonl

Usage:
        python scripts/update_score_log.py <path-to-results.json>

If no path is provided, the newest simulation folder in
eval/tau2/data/simulations is used automatically.
"""
import json
import math
import os
import sys
from datetime import datetime, timezone


def ci95(rewards: list[float]) -> tuple[float, float]:
    n = len(rewards)
    if n < 2:
        return (0.0, 0.0)
    mean = sum(rewards) / n
    variance = sum((r - mean) ** 2 for r in rewards) / (n - 1)
    se = math.sqrt(variance / n)
    z = 1.96
    return (max(0.0, mean - z * se), min(1.0, mean + z * se))


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = (p / 100) * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (idx - lo) * (s[hi] - s[lo])


def is_read_action(action_check: dict) -> bool:
    return action_check.get("tool_type") == "read"


def compute_action_accuracy(sims: list[dict]) -> tuple[int, int, int, int]:
    read_ok = sum_r = write_ok = sum_w = 0
    for s in sims:
        for ac in s.get("reward_info", {}).get("action_checks", []):
            ok = bool(ac.get("action_match", False))
            if is_read_action(ac):
                read_ok += int(ok)
                sum_r += 1
            else:
                write_ok += int(ok)
                sum_w += 1
    return read_ok, sum_r, write_ok, sum_w


def build_score_entry(results_path: str, info: dict, sims: list[dict]) -> dict:
    rewards = [float(s["reward_info"]["reward"]) for s in sims if s.get("reward_info")]
    passed = [r for r in rewards if r >= 1.0]
    durations = [float(s["duration"]) for s in sims if s.get("duration")]
    agent_costs = [float(s.get("agent_cost", 0) or 0.0) for s in sims]
    user_costs = [float(s.get("user_cost", 0) or 0.0) for s in sims]
    db_matches = [
        bool(s.get("reward_info", {}).get("db_check", {}).get("db_match", False))
        for s in sims
    ]
    read_ok, sum_r, write_ok, sum_w = compute_action_accuracy(sims)

    n = len(rewards)
    pass_at_1 = len(passed) / n if n else 0.0
    mean_reward = sum(rewards) / n if n else 0.0
    lo, hi = ci95(rewards)
    p50 = percentile(durations, 50)
    p95 = percentile(durations, 95)
    total_cost = sum(agent_costs) + sum(user_costs)
    avg_cost_per_conversation = total_cost / n if n else 0.0
    db_match_rate = sum(1 for x in db_matches if x) / n if n else 0.0

    agent_llm = info.get("agent_info", {}).get("llm", "unknown")
    user_llm = info.get("user_info", {}).get("llm", "unknown")
    now = datetime.now(timezone.utc)

    return {
        "run_id": f"tau2-retail-{now.strftime('%Y%m%d-%H%M%S')}",
        "label": f"retail sanity run ({n} tasks)",
        "model_agent": agent_llm,
        "model_user": user_llm,
        "domain": info.get("domain", "retail"),
        "split": "dev",
        "num_tasks_attempted": n,
        "num_tasks_evaluated": n,
        "num_infra_errors": 0,
        "num_trials": info.get("num_trials", 1),
        "pass_at_1": round(pass_at_1, 4),
        "mean_reward": round(mean_reward, 4),
        "ci_95_lower": round(lo, 4),
        "ci_95_upper": round(hi, 4),
        "read_action_accuracy": round(read_ok / sum_r, 4) if sum_r else None,
        "write_action_accuracy": round(write_ok / sum_w, 4) if sum_w else None,
        "db_match_rate": round(db_match_rate, 4),
        "cost_per_run_usd": round(total_cost, 4),
        "avg_cost_per_conversation_usd": round(avg_cost_per_conversation, 6),
        "wall_clock_p50_s": round(p50, 1),
        "wall_clock_p95_s": round(p95, 1),
        "results_path": results_path.replace("\\", "/"),
        "timestamp": now.isoformat(),
        "notes": (
            f"TAU2 sanity run. {n} simulations evaluated. "
            f"Pass@1={pass_at_1:.3f} (95% CI [{lo:.3f}, {hi:.3f}]). "
            f"Total cost ${total_cost:.4f}. p50={p50:.1f}s p95={p95:.1f}s."
        ),
    }


def main(results_path: str) -> None:
    with open(results_path) as f:
        data = json.load(f)

    sims = data.get("simulations", [])
    info = data.get("info", {})
    entry = build_score_entry(results_path, info, sims)

    score_log_path = "score_log.json"
    with open(score_log_path) as f:
        log = json.load(f)

    log.append(entry)

    with open(score_log_path, "w") as f:
        json.dump(log, f, indent=2)
    print(
        "Updated "
        f"{score_log_path} — pass@1={entry['pass_at_1']:.3f}, "
        f"CI=[{entry['ci_95_lower']:.3f},{entry['ci_95_upper']:.3f}]"
    )

    # Append run traces to root trace log for auditability.
    trace_path = "trace_log.jsonl"
    with open(trace_path, "a", encoding="utf-8") as f:
        for s in sims:
            f.write(json.dumps(s) + "\n")
    print(f"Appended {len(sims)} traces to {trace_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sim_base = "eval/tau2/data/simulations"
        dirs = sorted(os.listdir(sim_base), reverse=True)
        if not dirs:
            print("No simulation folders found.")
            sys.exit(1)
        path = os.path.join(sim_base, dirs[0], "results.json")
        print(f"Auto-detected: {path}")
    else:
        path = sys.argv[1]
    main(path)
