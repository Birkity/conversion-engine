# Tenacious-Bench v0.1 — Benchmark Dimensions

## Design Constraint

Every dimension must be machine-verifiable: a script reads a task plus an agent output and
returns a numerical score with no human in the loop. Dimensions D2–D5 are fully programmatic.
D1 requires a dev-tier LLM call (DeepSeek V3.2) with an explicit rubric.

## Scoring Priority

D2 → D1 → D3 → D4 → D5 (earlier = more fundamental failure).

The first failing dimension is the `primary_failure_dimension` in the task record.

## Overall Verdict

PASS = all scored dimensions pass. REJECT = any single dimension fails.

---

## Primary Dimensions

### D1 — ICP-Pitch Alignment

**What it measures:** Does the email's pitch frame match the ICP segment assigned in the
hiring signal brief?

**Why it matters:** SnapTrade and WiseiTech were assigned `segment=Ambiguous` but received
product pitches. An Ambiguous company has insufficient signal to justify a specific claim.
Segment 1 companies (Arcana, PulseSight, StreamlineOps) correctly received scaling pitches.

**Ground truth:** Lookup table — each segment maps to exactly one valid pitch family.

| Segment | Required pitch frame | Invalid pitch frames |
|---|---|---|
| Segment 1 | scaling bottleneck, integration speed, headcount gap post-funding | restructuring, cost-cutting, AI gap claim |
| Segment 2 | re-staffing after reduction, project continuity, skills gap | growth-bottleneck, scaling acceleration |
| Segment 3 | new leader building their stack, modernization, capability uplift | generic headcount, AI gap without evidence |
| Segment 4 | specific AI capability gap, ML maturity uplift, AI tooling | generic engineering shortage, scaling pitch |
| Ambiguous | qualifying question only — no product claim, no specific pitch | any product claim whatsoever |

**Verification:** Dev-tier LLM judge (DeepSeek V3.2 via OpenRouter) with this rubric:

```
Given the ICP segment and the email body, answer: does the email's primary pitch frame
match the valid frames for this segment? Return JSON: {"score": 0 or 1, "reason": "..."}
Score 0 if: (a) segment is Ambiguous and email makes any product claim; (b) pitch frame
is from the invalid list for this segment; (c) pitch is generic with no segment-specific angle.
Score 1 if: pitch frame is from the valid list, or email asks a qualifying question.
```

**Failure examples from Week 10 traces:**
- SnapTrade: segment=Ambiguous, email="Tenacious provides engineers who can augment your
  team" → D1 FAIL (product claim on Ambiguous)
- WiseiTech: segment=Ambiguous, email="Tenacious provides research-backed engineers
  available on-demand" → D1 FAIL (product claim on Ambiguous)

---

### D2 — Signal Directionality

**What it measures:** Does the email's pitch direction match the hiring velocity signal?

**Why it matters:** A company with -60% or -100% job velocity is shedding open roles.
Pitching "scaling bottleneck" or "augment capabilities" to a contracting company is
directionally wrong and not grounded in the evidence.

**Ground truth:** Arithmetic rule — fully programmatic, no LLM call.

```python
def score_d2_directionality(brief: dict, email_body: str) -> tuple[int, str | None]:
    delta = brief.get("hiring_velocity", {}).get("delta_pct", 0.0) / 100.0
    growth_re = re.compile(
        r'\bbottleneck\b|\bscaling\b|\baccelerati|\brapid growth\b|'
        r'\bincreased demand\b|\bneed to augment\b|\baugment\b', re.I
    )
    if delta < -0.20 and growth_re.search(email_body):
        return 0, f"contraction signal ({delta:.0%}) with growth-frame pitch"
    return 1, None
```

Threshold: `-0.20` (20% contraction). Below this the hiring direction is unambiguously
negative and a growth pitch is misaligned.

**Evidence from traces:**
- SnapTrade: `delta_pct=-60`, email body contains "bottlenecks integrating new APIs" → FAIL
- WiseiTech: `delta_pct=-100`, email body contains "needing to augment" → FAIL
- Arcana: `delta_pct=+100`, email body contains "bottlenecks integrating new engineers" → PASS
- PulseSight: `delta_pct=+133`, email body contains "scaling after Series A" → PASS

---

## Secondary Dimensions

### D3 — Grounding Completeness

**What it measures:** Are all numeric claims in the email body verifiable in the hiring
signal brief?

**Why it matters:** The template concatenation bug in `router.py` produces outputs like
"SnapTrade recently snaptrade ai maturity score: 0/3" — grounding facts pasted without
a verb. The honesty check in `reply_interpreter.py` uses token-matching but only fires
post-reply, not post-email-generation. D3 catches fabricated or misquoted numbers at
email-generation time.

**Verification:** Fully programmatic.

```python
def score_d3_grounding(email_body: str, brief_text: str) -> tuple[int, str | None]:
    nums = re.findall(r'\$[\d,.]+[MBK]?|\d+%|\b\d{4}\b', email_body)
    bad = [n for n in nums if n not in brief_text]
    return (1, None) if not bad else (0, f"unverified numeric tokens: {bad}")
```

Catches: invented dollar amounts, wrong percentages, fabricated years.
Does NOT penalize vague qualitative claims (those are D1's domain).

---

### D4 — Tone Compliance

**What it measures:** Does the email contain zero banned phrases from the Tenacious style
guide?

**Why it matters:** The existing `tone_warnings` system in `agent/email/generator.py`
already checks this but does not block sends. D4 makes the same check a hard gate in
the benchmark.

**Verification:** Fully programmatic. Banned phrase list lifted from `generator.py`.

```python
BANNED_PHRASES = [
    "top talent", "world-class", "rockstar", "ninja", "aggressive hiring",
    "cost savings of", "guaranteed roi", "proven track record",
    "falling behind", "you're behind", "you lack", "you're missing",
    "you need to catch up", "left behind",
    "http://", "https://cal.com", "schedule a", "book a",
    "quick ", "just ", "hey there", "hope this finds",
]
```

Note: "bench" is excluded from D4 here (the generator bans it) because some grounding
facts legitimately reference bench capabilities. This avoids false positives.

---

### D5 — Format Compliance

**What it measures:** Does the email meet the structural requirements of Tenacious outreach?

**Verification:** Fully programmatic.

```python
def score_d5_format(subject: str, email_body: str) -> tuple[int, str | None]:
    word_count = len(email_body.split())
    if word_count > 120:
        return 0, f"body too long: {word_count} words (max 120)"
    if len(subject) > 60:
        return 0, f"subject too long: {len(subject)} chars (max 60)"
    if re.search(r'https?://', email_body):
        return 0, "booking/external URL in cold outreach body"
    return 1, None
```

---

## Difficulty Stratification

| Level | Criteria |
|---|---|
| easy | Single dimension fails, failure is obvious (e.g., banned phrase present, URL in body) |
| medium | D1 or D2 fails with a subtly wrong pitch frame — passes surface checks |
| hard | All programmatic dimensions pass; only D1 LLM judge catches the semantic failure |

Target distribution: 20% easy, 50% medium, 30% hard.

## Dimension Coverage by Source Mode

| Source mode | Primary D targeted | Notes |
|---|---|---|
| trace_derived | D2, D1 | Real failures from SnapTrade, WiseiTech traces |
| programmatic | D2, D3 | Sweep velocity × segment combinations |
| synthesis | D1 | Hard semantic edge cases needing LLM judge |
| adversarial | D1, D2 | Emails that pass D3–D5 but fail semantically |
