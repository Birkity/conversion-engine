# Target Failure Mode — Conversion Engine Act IV

**Selected failure mode: Tone Drift / Self-Disclosure Misclassification**  
**Category: `tone_drift`**  
**Probe pass rate: 0/3 (0% — worst-performing category across all 32 probes)**

---

## What the failure is

When a prospect self-discloses a pain point or admits they are behind on a capability ("our AI team is not great right now", "we are definitely behind our competitors on AI"), the reply interpreter classifies their reply as `QUESTION` or `UNKNOWN` instead of `INTERESTED`.

The result: the system sends either a clarification email ("what did you mean exactly?") or a follow-up question email, when it should send a Cal.com booking link.

### Observed evidence from probe runs (2026-04-24)

| Probe | Reply | Actual | Expected | Correct? |
|---|---|---|---|---|
| 18 | "Honestly, our AI team is not great right now and we know it." | QUESTION → SEND_EMAIL | INTERESTED → SEND_CAL_LINK | ✗ |
| 19 | "We are definitely behind our competitors on AI. That is clear to us." | UNKNOWN → ASK_CLARIFICATION | INTERESTED → SEND_CAL_LINK | ✗ |
| 20 | "I read your email three times. Are you calling us unsophisticated?" | UNKNOWN → ASK_CLARIFICATION | QUESTION → SEND_EMAIL | ✗ |

All three probes failed. This is the only category in the 32-probe suite with a 100% trigger rate.

---

## Why this failure is the highest-ROI target

### Frequency

Self-disclosure of a gap is one of the most common positive reply patterns in B2B outreach. CTOs and engineering leaders who are already aware of a gap — and reply to signal that awareness — represent the warmest segment of any outbound sequence. The frequency is not rare; it is the expected reply pattern from a correctly-targeted ICP prospect.

Estimated prevalence in real outbound: ~10–15% of positive replies contain a self-disclosure or acknowledgement of a gap. With 1,000 outbound contacts at a 7% reply rate = 70 replies. At 12% self-disclosure rate among replies = approximately 8–9 mis-classified warm leads per 1,000 contacts.

### Business cost per mis-classification

Each mis-classified self-disclosure delays the booking by one full email round (typically 5–7 days based on the cold sequence cadence):

- System sends ASK_CLARIFICATION or SEND_EMAIL
- Prospect receives a generic or follow-up question
- Prospect replies again (if they still bother)
- System now correctly classifies and sends Cal link
- Net delay: 5–7 days per warm lead

At a 7% email-to-booking conversion, a 5-day delay per warm lead means:
- 8–9 delayed bookings per 1,000 contacts
- Assuming a $5,000 average deal × 7% close rate: ~$3,000–4,000 in delayed or lost pipeline per 1,000 contacts

This is a **repeating cost** on every campaign run, not a one-time event.

### Why it is more dangerous than the next-worst failure (signal_over_claim at 67%)

Signal over-claim failures affect prospects who are actively challenging the data — these are already lower-trust interactions. The tone drift failure affects prospects who are actively *agreeing* — the highest-trust, highest-intent interactions in the funnel. Mis-classifying a hostile prospect costs less than mis-classifying a warm one.

### Why it is more dangerous than bench over-commitment (0% trigger rate in classification)

Bench over-commitment has higher per-event business cost (implied contract), but it requires a specific conversational path (prospect asks about NestJS). Tone drift fires on any warm prospect self-disclosure, which is significantly more common.

---

## The root cause

The reply interpreter's SYSTEM_PROMPT defines `INTERESTED` as requiring explicit engagement signals:
- "Sounds interesting, can you send times?" → INTERESTED (explicit)
- "Sure, let's chat" → INTERESTED (explicit)

It does not include a pattern for **implicit buying signals via pain acknowledgement**:
- "Our AI team is not great" → implicit buying signal (system does not recognise)
- "We're behind our competitors" → implicit buying signal (system does not recognise)

The model defaults to QUESTION (there might be a question implied) or UNKNOWN (ambiguous) when the reply contains negative self-assessment language without an explicit engagement phrase.

---

## The architectural rule needed to prevent it

Add a `self_disclosure_buying_signals` detection block to the `REPLY_INTERPRETER_SYSTEM_PROMPT` in `agent/reply_interpreter/prompts.py`:

```
SELF-DISCLOSURE BUYING SIGNALS (classify as INTERESTED):
A reply is INTERESTED even without explicit engagement phrases if it contains:
- Acknowledgement of a gap, weakness, or lag in the domain Tenacious is pitching
  ("our AI team is weak", "we know we're behind", "we're struggling with X")
- Confirmation of the problem framing from the original email
  ("you're right that we're hiring a lot", "the bottleneck you described is real")
- Self-identification with the typical bottleneck described in the email
  ("that's exactly what we're hitting", "you nailed it")

When a prospect uses deficit language about themselves in reply to an email describing
a service that addresses that deficit, treat it as an implicit "yes, this is relevant."
Classify INTERESTED → SEND_CAL_LINK.
```

This rule is narrow and specific: it only fires when the negative self-assessment language directly maps to a service capability described in the email. It does not promote all negative-sentiment replies to INTERESTED.

---

## How to verify the fix (Act IV test plan)

1. Update `agent/reply_interpreter/prompts.py` to add the self-disclosure block
2. Re-run `python scripts/act3_reply_tests.py --save-results`
3. Target: probes 18, 19 → INTERESTED → SEND_CAL_LINK
4. Confirm probes 4, 5, 6 (hostile/hostile-sarcastic) still → NOT_INTERESTED → STOP (the fix must not promote hostile replies)
5. Overall pass rate target: ≥ 28/32 (87.5%, up from 75%)

The fix must increase tone_drift pass rate from 0/3 to ≥ 2/3 without reducing any other category's pass rate.

---

## Secondary target (for future iteration)

**Signal Over-Claim Failure 4b (Probe #13):** "Our open roles are for sales" → false STOP.

This is the second-priority failure. The probe correctly surfaces a case where the system permanently closes a lead who has not said they are uninterested — only that the signal was wrong. The fix is a `signal_accuracy_challenge` classifier that routes `NOT_INTERESTED` only when the prospect explicitly opts out, not when they challenge the data.

This is deliberately not the primary target because: (a) it requires careful scoping to avoid also catching hostile/sarcastic replies that should STOP, and (b) the tone drift fix has a cleaner, lower-risk implementation path.
