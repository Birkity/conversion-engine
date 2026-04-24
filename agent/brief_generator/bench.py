"""
Dynamic bench capacity loader.
Reads bench_summary.json and produces a prompt-ready block for both LLM paths.
Imported at module load time — safe because the bench file is static at runtime.
"""
import json
from pathlib import Path

_BENCH_PATH = (
    Path(__file__).resolve().parents[2]
    / "seeds"
    / "tenacious_sales_data"
    / "tenacious_sales_data"
    / "seed"
    / "bench_summary.json"
)

_FALLBACK = (
    "TENACIOUS BENCH (counts unavailable — seeds not present):\n"
    "Available stacks: Python, Go, Data, ML, Infra, Frontend.\n"
    "NestJS engineers are committed through Q3 2026 — treat as unavailable for new work.\n"
    "Set bench_match.bench_available=false if required stack is not in this list.\n"
    "Never promise capacity the bench does not show."
)


def bench_capacity_block() -> str:
    """
    Return a one-paragraph prompt block describing current bench capacity.
    Falls back to a conservative static string if the seed file is absent
    (e.g., CI environment without seeds/).
    """
    try:
        data = json.loads(_BENCH_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return _FALLBACK

    stacks = data.get("stacks", {})
    as_of = data.get("as_of", "unknown date")
    total = data.get("total_engineers_on_bench", "?")
    honesty = data.get("honesty_constraint", "")

    available_lines = []
    committed_lines = []

    for stack_key, meta in stacks.items():
        if not isinstance(meta, dict):
            continue
        count = meta.get("available_engineers", 0)
        note = meta.get("note", "")
        subsets = meta.get("skill_subsets", [])
        subset_str = f" ({', '.join(subsets[:4])})" if subsets else ""

        if note and ("committed" in note.lower() or "limited availability" in note.lower()):
            committed_lines.append(
                f"  - {stack_key}: {count} available BUT {note.split('.')[0].strip()}"
            )
        else:
            available_lines.append(f"  - {stack_key}: {count} engineers{subset_str}")

    available_block = "\n".join(available_lines) if available_lines else "  (none)"
    committed_block = (
        "\nCommitted / limited stacks (treat as unavailable for new engagements):\n"
        + "\n".join(committed_lines)
    ) if committed_lines else ""

    honesty_note = (
        f"\nHonesty constraint: {honesty[:300]}" if honesty else ""
    )

    return (
        f"TENACIOUS BENCH as of {as_of} (total on bench: {total}):\n"
        f"Available stacks:\n{available_block}"
        f"{committed_block}"
        f"{honesty_note}\n"
        "Set bench_match.bench_available=false if required stack is not in this list.\n"
        "Never promise capacity the bench does not show."
    )
