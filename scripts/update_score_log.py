"""
Parse tau2 simulation results.json → update eval/score_log.json and eval/trace_log.jsonl.

Usage:
    python scripts/update_score_log.py <path-to-results.json>
    # e.g.:
    # python scripts/update_score_log.py eval/tau2/data/simulations/20260422_181511_.../results.json
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


def main(results_path: str) -> None:
    with open(results_path) as f:
        data = json.load(f)

    sims = data.get("simulations", [])
    info = data.get("info", {})

    rewards = [s["reward_info"]["reward"] for s in sims if s.get("reward_info")]
    passed = [r for r in rewards if r >= 1.0]
    durations = [s["duration"] for s in sims if s.get("duration")]
    agent_costs = [s.get("agent_cost", 0) for s in sims]

    read_ok = sum_r = write_ok = sum_w = 0
    for s in sims:
        for ac in s.get("reward_info", {}).get("action_checks", []):
            is_read = ac.get("action", {}).get("nam", "").lower() in (
                "get", "find", "search", "lookup", "list", "check"
            )
            ok = ac.get("result", {}).get("match", False)
            if is_read:
                read_ok += int(ok); sum_r += 1
            else:
                write_ok += int(ok); sum_w += 1

    n = len(rewards)
    pass_at_1 = len(passed) / n if n else 0.0
    mean_reward = sum(rewards) / n if n else 0.0
    lo, hi = ci95(rewards)
    p50 = percentile(durations, 50)
    p95 = percentile(durations, 95)
    cost_per_run = sum(agent_costs)

    agent_llm = info.get("agent_info", {}).get("llm", "unknown")
    user_llm = info.get("user_info", {}).get("llm", "unknown")

    entry = {
        "run_id": f"dev-baseline-{datetime.now(timezone.utc).strftime('%Y%m%d')}-gemini-flash",
        "label": "dev-tier 30-task 5-trial full baseline",
        "model_agent": agent_llm,
        "model_user": user_llm,
        "domain": "retail",
        "split": "dev",
        "num_tasks_attempted": info.get("num_trials", 5) * 30,
        "num_tasks_evaluated": n,
        "num_infra_errors": 0,
        "num_trials": info.get("num_trials", 5),
        "pass_at_1": round(pass_at_1, 4),
        "mean_reward": round(mean_reward, 4),
        "ci_95_lower": round(lo, 4),
        "ci_95_upper": round(hi, 4),
        "read_action_accuracy": round(read_ok / sum_r, 4) if sum_r else None,
        "write_action_accuracy": round(write_ok / sum_w, 4) if sum_w else None,
        "db_match_rate": None,
        "cost_per_run_usd": round(cost_per_run, 4),
        "wall_clock_p50_s": round(p50, 1),
        "wall_clock_p95_s": round(p95, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "notes": (
            f"Full 30-task 5-trial dev baseline. {n} simulations evaluated. "
            f"Pass@1={pass_at_1:.3f} (95% CI [{lo:.3f}, {hi:.3f}]). "
            f"Cost per run ${cost_per_run:.4f}. p50={p50:.0f}s p95={p95:.0f}s."
        ),
    }

    score_log_path = "eval/score_log.json"
    with open(score_log_path) as f:
        log = json.load(f)

    # Remove any previous full baseline entry with same label
    log = [e for e in log if e.get("label") != entry["label"]]
    log.append(entry)

    with open(score_log_path, "w") as f:
        json.dump(log, f, indent=2)
    print(f"Updated {score_log_path} — pass@1={pass_at_1:.3f}, CI=[{lo:.3f},{hi:.3f}]")

    # Write/overwrite trace_log.jsonl
    trace_path = "eval/trace_log.jsonl"
    with open(trace_path, "w") as f:
        for s in sims:
            f.write(json.dumps(s) + "\n")
    print(f"Wrote {len(sims)} traces to {trace_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Auto-detect newest gemini-2.0-flash-001 run
        sim_base = "eval/tau2/data/simulations"
        dirs = sorted(
            [d for d in os.listdir(sim_base) if "gemini-2.0-flash-001" in d],
            reverse=True,
        )
        if not dirs:
            print("No gemini-2.0-flash-001 simulation found.")
            sys.exit(1)
        path = os.path.join(sim_base, dirs[0], "results.json")
        print(f"Auto-detected: {path}")
    else:
        path = sys.argv[1]
    main(path)
