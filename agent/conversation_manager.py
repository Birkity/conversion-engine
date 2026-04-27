"""
Conversation manager — stateful pipeline logic for the live UI.

Manages artifacts/{slug}/conversation_state.json and orchestrates
the full Act II → Act III pipeline in response to UI actions.

Policy compliance (data_handling_policy.md):
  Rule 2: synthetic prospect emails only
  Rule 5: kill switch enforced via agent.email.handler.send()
  Rule 6: draft header added automatically by email handler
  Rule 7: only first name + email logged, no full PII to stdout
"""
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]

_BUILTIN_SLUGS = [
    "arcana", "brightpath", "coraltech", "kinanalytics",
    "novaspark", "pulsesight", "snaptrade", "streamlineops", "wiseitech",
]

_REAL_DOMAINS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "icloud.com", "protonmail.com", "live.com",
}

_SLUG_CHARS_RE = re.compile(r"[^a-z0-9]+")

_PROSPECT_INFO_FILE = "prospect_info.json"
_HIRING_BRIEF_FILE = "hiring_signal_brief.json"
_COMPETITOR_GAP_FILE = "competitor_gap_brief.json"


def _custom_registry_path() -> Path:
    return ROOT / "artifacts" / "custom_companies.json"


def get_all_slugs() -> list[str]:
    """Return all known slugs: builtins + any user-created companies."""
    try:
        data = _load_json(_custom_registry_path())
        custom = data if isinstance(data, list) else []
    except Exception:
        custom = []
    return _BUILTIN_SLUGS + [s for s in custom if s not in _BUILTIN_SLUGS]


# Backward-compatible alias — call get_all_slugs() for the live list
KNOWN_SLUGS = _BUILTIN_SLUGS


# ─────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("_load_json failed for %s: %s", path, exc)
        return None


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _state_path(slug: str) -> Path:
    return ROOT / "artifacts" / slug / "conversation_state.json"


def _last_email_path(slug: str) -> Path:
    return ROOT / "artifacts" / slug / "last_email.json"


def _traces_path(slug: str) -> Path:
    return ROOT / "traces" / slug


def _default_company_name(slug: str) -> str:
    parts = [p for p in slug.replace("_", "-").split("-") if p]
    return " ".join(p.capitalize() for p in parts) or slug


def _build_synthetic_prospect(slug: str, company: str) -> dict:
    return {
        "name": f"{company} Contact",
        "role": "Engineering Lead",
        "email": f"{slug}.prospect@sink.example.com",
        "company": company,
        "_policy_note": "Synthetic prospect generated automatically for pipeline safety.",
    }


def _generate_briefs_from_signals(slug: str, signals: dict) -> tuple[dict | None, dict | None]:
    try:
        from agent.brief_generator import generate
        result = generate(signals)
        log.info("ensure_trace_context regenerated briefs from signals slug=%s", slug)
        return result.get("hiring_signal_brief"), result.get("competitor_gap_brief")
    except Exception as exc:
        log.warning("ensure_trace_context brief generation failed slug=%s: %s", slug, exc)
        return None, None


def _generate_briefs_from_enrichment(slug: str) -> tuple[dict | None, dict | None]:
    try:
        from agent.enrichment.pipeline import enrich
        company_name = _default_company_name(slug)
        result = enrich(company_name)
        log.info("ensure_trace_context enrichment fallback generated briefs slug=%s", slug)
        return result.get("hiring_signal_brief"), result.get("competitor_gap_brief")
    except Exception as exc:
        log.warning("ensure_trace_context enrichment fallback failed slug=%s: %s", slug, exc)
        return None, None


def _ensure_trace_context(slug: str) -> tuple[dict | None, dict | None, dict | None]:
    """Ensure Act II input files exist; regenerate missing artifacts when possible."""
    traces = _traces_path(slug)
    traces.mkdir(parents=True, exist_ok=True)

    hsb_path = traces / _HIRING_BRIEF_FILE
    cgb_path = traces / _COMPETITOR_GAP_FILE
    prospect_path = traces / _PROSPECT_INFO_FILE
    signals = _load_json(traces / "signals.json")

    hsb = _load_json(hsb_path)
    cgb = _load_json(cgb_path)
    prospect = _load_json(prospect_path)

    if not hsb or not cgb:
        generated_hsb, generated_cgb = (
            _generate_briefs_from_signals(slug, signals)
            if signals else _generate_briefs_from_enrichment(slug)
        )
        if generated_hsb and not hsb:
            _save_json(hsb_path, generated_hsb)
            hsb = generated_hsb
        if generated_cgb and not cgb:
            _save_json(cgb_path, generated_cgb)
            cgb = generated_cgb

    if not prospect:
        company_name = (hsb or {}).get("company") or (signals or {}).get("company_name") or _default_company_name(slug)
        prospect = _build_synthetic_prospect(slug, company_name)
        _save_json(prospect_path, prospect)
        log.info("ensure_trace_context created synthetic prospect_info slug=%s", slug)

    return hsb, cgb, prospect


# ─────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────

def get_state(slug: str) -> dict:
    """Return conversation_state.json or idle sentinel dict."""
    data = _load_json(_state_path(slug))
    if not data:
        return {"slug": slug, "status": "idle", "turns": [], "company": slug,
                "prospect_email": None, "started_at": None, "last_updated": None,
                "outcome": None}
    return data


def slug_from_email(contact_email: str) -> str | None:
    """Resolve a slug by matching contact_email against prospect_info.json files."""
    for slug in get_all_slugs():
        prospect = _load_json(_traces_path(slug) / _PROSPECT_INFO_FILE)
        if prospect and prospect.get("email", "").lower() == contact_email.lower():
            return slug
        # Also check conversation_state.json in case prospect_info is unavailable
        state = _load_json(_state_path(slug))
        if state and state.get("prospect_email", "").lower() == contact_email.lower():
            return slug
    return None


def create_company(
    company_name: str,
    prospect_name: str,
    prospect_email: str,
    prospect_role: str,
    pitch_angle: str = "",
) -> dict:
    """
    Register a new company so it can be run through the pipeline.

    Creates minimal trace files under traces/{slug}/ and registers the slug
    in artifacts/custom_companies.json.

    Policy compliance:
      Rule 2: prospect_email must NOT be a real personal address domain.
      Rule 7: only first name + email logged.

    Returns: {"slug": str, "company": str}
    Raises: ValueError on policy violation or invalid input.
    """
    if not company_name.strip():
        raise ValueError("company_name is required.")
    if not prospect_name.strip():
        raise ValueError("prospect_name is required.")
    if not prospect_email.strip() or "@" not in prospect_email:
        raise ValueError("prospect_email must be a valid email address.")
    if not prospect_role.strip():
        raise ValueError("prospect_role is required.")

    # Rule 2: reject real personal domains
    domain = prospect_email.split("@")[-1].lower()
    if domain in _REAL_DOMAINS:
        raise ValueError(
            f"Policy violation (Rule 2): {prospect_email!r} uses a real personal domain "
            f"(@{domain}). Use a synthetic address such as "
            f"{prospect_name.split()[0].lower()}@sink.example.com."
        )

    # Derive slug: lowercase, strip specials, collapse hyphens
    slug = _SLUG_CHARS_RE.sub("-", company_name.strip().lower()).strip("-")
    if not slug:
        raise ValueError("Could not derive a valid slug from the company name.")

    # Prevent clobbering built-in companies
    if slug in _BUILTIN_SLUGS:
        raise ValueError(
            f"Slug {slug!r} conflicts with a built-in company. "
            "Use a more specific company name."
        )

    traces_dir = ROOT / "traces" / slug
    artifacts_dir = ROOT / "artifacts" / slug
    traces_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    company = company_name.strip()
    first_name = prospect_name.strip().split()[0]
    log.info("create_company slug=%s prospect=%s email=%s", slug, first_name, prospect_email)

    # Minimal prospect_info.json
    _save_json(traces_dir / _PROSPECT_INFO_FILE, {
        "name": prospect_name.strip(),
        "role": prospect_role.strip(),
        "email": prospect_email.strip(),
        "company": company,
    })

    # Minimal hiring_signal_brief.json (used by email generator)
    _save_json(traces_dir / _HIRING_BRIEF_FILE, {
        "company": company,
        "hiring_velocity": {
            "direction": "unknown",
            "delta_pct": None,
            "signal_strength": "low",
            "observation": "No signal data — manually added company.",
        },
        "budget_urgency": {"level": "unknown", "signal": None, "runway_pressure": None},
        "cost_pressure": {"present": False, "signal": None, "icp_segment_implication": None},
        "engineering_maturity": {
            "stack_sophistication": "unknown",
            "detected_stack": [],
            "bench_match_notes": "No data available.",
        },
        "ai_maturity_score": 0,
        "ai_maturity_rationale": {
            "ai_roles_found": [],
            "modern_ml_stack_signals": [],
            "executive_ai_signals": "unknown",
            "named_ai_leadership": False,
        },
        "confidence": 0.5,
        "icp_segment": "Segment 3",
        "recommended_pitch_angle": pitch_angle.strip() if pitch_angle.strip()
            else f"Outreach to {first_name} at {company} — personalise before sending.",
        "bench_match": {"required_stacks": [], "bench_available": True},
        "honesty_flags": {"weak_hiring_velocity_signal": True, "bench_gap_detected": False},
    })

    # Minimal competitor_gap_brief.json (required by start_pipeline)
    _save_json(traces_dir / _COMPETITOR_GAP_FILE, {
        "sector": "unknown",
        "competitors_analyzed": 0,
        "prospect_ai_score": 0,
        "prospect_position_in_sector": "unknown",
        "gaps": [],
        "overall_confidence": 0.5,
        "tenacious_status": "CUSTOM_ENTRY",
    })

    # Register slug in custom_companies.json
    registry_path = _custom_registry_path()
    existing: list = []
    try:
        data = _load_json(registry_path)
        existing = data if isinstance(data, list) else []
    except Exception:
        pass
    if slug not in existing:
        existing.append(slug)
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    return {"slug": slug, "company": company}


def start_pipeline(slug: str) -> dict:
    """
    Act II: generate and send the outbound email, initialise conversation state.

    Loads briefs + prospect_info from traces/{slug}/, generates a signal-grounded
    email, sends it via Resend SMTP (respecting kill switch), saves artifacts, and
    writes a fresh conversation_state.json with status=waiting_for_reply.

    Returns: updated ConversationState dict.
    Raises: ValueError on policy violation, RuntimeError on send failure.
    """
    hsb, cgb, prospect = _ensure_trace_context(slug)

    if not hsb or not cgb or not prospect:
        raise ValueError(
            f"Missing trace files for slug={slug!r}. "
            f"Expected: traces/{slug}/hiring_signal_brief.json, "
            f"competitor_gap_brief.json, prospect_info.json"
        )

    # Rule 2: synthetic email addresses only
    email_addr = prospect.get("email", "")
    domain = email_addr.split("@")[-1].lower() if "@" in email_addr else ""
    if domain in _REAL_DOMAINS:
        raise ValueError(
            f"Policy violation (Rule 2): {email_addr!r} is a real personal address. "
            "prospect_info.json must use a synthetic sink address "
            "(e.g. name@sink.example.com)."
        )

    company = prospect.get("company", hsb.get("company", slug))
    prospect_name = prospect.get("name", "")
    log.info("start_pipeline slug=%s company=%s prospect=%s",
             slug, company, prospect_name.split()[0] if prospect_name else "?")

    # Optional HubSpot contact upsert for SMS routing
    if prospect.get("phone"):
        try:
            from agent.hubspot.client import upsert_contact
            name_parts = prospect_name.split(" ", 1)
            upsert_contact(
                email=email_addr,
                first_name=name_parts[0] if name_parts else "",
                last_name=name_parts[1] if len(name_parts) > 1 else "",
                company=company,
                phone=prospect.get("phone", ""),
            )
        except Exception as exc:
            log.warning("hubspot upsert skipped (non-fatal): %s", exc)

    # Abstention: downgrade to generic pitch when confidence is low
    brief_confidence = float(hsb.get("confidence", 1.0))
    if brief_confidence < 0.6:
        log.info("start_pipeline: confidence=%.2f < 0.6 — using Ambiguous segment", brief_confidence)
        hsb = dict(hsb)
        hsb["icp_segment"] = "Ambiguous"

    # Generate email
    from agent.email.generator import generate_email
    try:
        email_result = generate_email(hsb=hsb, cgb=cgb, prospect_info=prospect)
    except Exception as exc:
        raise RuntimeError(f"Email generation failed for slug={slug!r}: {exc}") from exc

    subject = email_result["subject"]
    body = email_result["body"]
    grounding = email_result.get("grounding_facts", [])
    icp_used = email_result.get("icp_segment_used", "unknown")
    word_count = email_result.get("word_count", len(body.split()))
    tone_warnings = email_result.get("tone_warnings", [])

    # Send via Resend SMTP (kill switch enforced inside handler)
    from agent.email.handler import send
    send_result = send(to=email_addr, subject=subject, body=body)
    if send_result.get("status") == "error":
        raise RuntimeError(
            f"Email send failed for slug={slug!r}: {send_result.get('error')}"
        )

    now = datetime.now(timezone.utc).isoformat()
    artifacts_dir = ROOT / "artifacts" / slug
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Save last_email.json + append to email_log.jsonl (same as act2_email_execution.py)
    last_email_record = {
        "subject": subject,
        "body": body,
        "grounding_facts": grounding,
        "icp_segment_used": icp_used,
        "timestamp": now,
        "company": company,
        "prospect_email": email_addr,
    }
    _save_json(_last_email_path(slug), last_email_record)
    with open(artifacts_dir / "email_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({
            **last_email_record,
            "word_count": word_count,
            "tone_warnings": tone_warnings,
        }) + "\n")

    state = {
        "slug": slug,
        "company": company,
        "prospect_email": email_addr,
        "status": "waiting_for_reply",
        "turns": [
            {
                "turn": 0,
                "from": "agent",
                "type": "outbound_email",
                "subject": subject,
                "body": body,
                "grounding_facts": grounding,
                "icp_segment_used": icp_used,
                "sink_mode": send_result.get("sink_mode", True),
                "timestamp": now,
            }
        ],
        "started_at": now,
        "last_updated": now,
        "outcome": None,
    }
    _save_json(_state_path(slug), state)
    log.info("start_pipeline complete slug=%s status=waiting_for_reply sink_mode=%s",
             slug, send_result.get("sink_mode"))
    return state


def handle_reply(slug: str, reply_text: str, channel: str = "email") -> dict:
    """
    Act III: interpret a prospect reply, execute routing action, update state.

    Loads last_email + briefs, calls interpret_reply() + route_decision(),
    appends the prospect turn and (if sent) the agent follow-up turn, then
    writes the updated conversation_state.json.

    Returns: updated ConversationState dict.
    Raises: ValueError if pipeline is idle or already terminal.
    """
    if channel not in ("email", "sms"):
        raise ValueError(f"Invalid channel {channel!r}. Must be 'email' or 'sms'.")
    if not reply_text or not reply_text.strip():
        raise ValueError("reply_text must be non-empty.")

    state = get_state(slug)
    current_status = state.get("status", "idle")

    if current_status == "idle":
        raise ValueError(
            f"Pipeline not started for slug={slug!r}. Call start_pipeline first."
        )
    if current_status in ("booked", "stopped"):
        raise ValueError(
            f"Pipeline already terminal: status={current_status!r} for slug={slug!r}."
        )

    traces = _traces_path(slug)
    hsb = _load_json(traces / _HIRING_BRIEF_FILE)
    cgb = _load_json(traces / _COMPETITOR_GAP_FILE)
    prospect = _load_json(traces / _PROSPECT_INFO_FILE)
    last_email = _load_json(_last_email_path(slug))

    if not all([hsb, cgb, prospect, last_email]):
        raise ValueError(
            f"Missing context files for slug={slug!r}. "
            "Ensure traces/ and artifacts/ are populated."
        )

    briefs = {"hiring_signal_brief": hsb, "competitor_gap_brief": cgb}

    # Mark as processing while we run the LLM calls
    state["status"] = "processing"
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    _save_json(_state_path(slug), state)

    try:
        from agent.reply_interpreter.reply_interpreter import interpret_reply
        from agent.reply_interpreter.router import route_decision

        decision = interpret_reply(
            reply_text=reply_text.strip(),
            last_email=last_email,
            briefs=briefs,
            prospect_info=prospect,
        )
        log.info("handle_reply slug=%s intent=%s confidence=%s next_step=%s",
                 slug, decision.get("intent"), decision.get("confidence"),
                 decision.get("next_step"))

        route_result = route_decision(
            decision=decision,
            prospect_info=prospect,
            briefs=briefs,
            last_email=last_email,
        )
        log.info("handle_reply slug=%s actions=%s errors=%s",
                 slug, route_result.get("actions"), route_result.get("errors"))

    except Exception as exc:
        log.error("handle_reply failed slug=%s: %s", slug, exc)
        state["status"] = "waiting_for_reply"
        state["last_updated"] = datetime.now(timezone.utc).isoformat()
        _save_json(_state_path(slug), state)
        raise

    now = datetime.now(timezone.utc).isoformat()
    next_turn = len(state["turns"])

    # Append prospect turn
    state["turns"].append({
        "turn": next_turn,
        "from": "prospect",
        "reply_text": reply_text.strip(),
        "channel": channel,
        "interpretation": {
            "intent": decision.get("intent"),
            "next_step": decision.get("next_step"),
            "confidence": decision.get("confidence"),
            "reasoning": decision.get("reasoning", ""),
            "grounding_facts_used": decision.get("grounding_facts_used", []),
        },
        "routing": {
            "actions": route_result.get("actions", []),
            "errors": route_result.get("errors", []),
            "cal_link": route_result.get("cal_link"),
        },
        "sms": route_result.get("sms"),
        "timestamp": now,
    })
    next_turn += 1

    # If router sent a follow-up agent email, append that turn + update last_email.json
    agent_email = route_result.get("agent_email")
    if agent_email:
        state["turns"].append({
            "turn": next_turn,
            "from": "agent",
            "type": agent_email.get("type", "clarification_email"),
            "subject": agent_email.get("subject", ""),
            "body": agent_email.get("body", ""),
            "timestamp": now,
        })
        # Update last_email.json so the next handle_reply() call has correct context
        _save_json(_last_email_path(slug), {
            "subject": agent_email["subject"],
            "body": agent_email["body"],
            "grounding_facts": [],
            "timestamp": now,
            "company": state.get("company", ""),
            "prospect_email": state.get("prospect_email", ""),
        })

    # Determine terminal status from routing actions
    actions_str = " ".join(route_result.get("actions", []))
    if "outreach_stopped" in actions_str:
        new_status = "stopped"
    elif "cal_link_sent" in actions_str:
        new_status = "booked"
    else:
        new_status = "waiting_for_reply"

    state["status"] = new_status
    state["last_updated"] = now
    if new_status in ("booked", "stopped"):
        state["outcome"] = new_status

    _save_json(_state_path(slug), state)
    return state


def reset_pipeline(slug: str) -> None:
    """Delete conversation_state.json to reset the pipeline to idle."""
    path = _state_path(slug)
    if path.exists():
        path.unlink()
        log.info("reset_pipeline slug=%s — state deleted", slug)
