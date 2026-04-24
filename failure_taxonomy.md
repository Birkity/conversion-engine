# Failure Taxonomy — Conversion Engine Act III

Probe run date: 2026-04-24  
Model: google/gemini-2.0-flash-001  
Total probes: 32 | Passed: 24 | Failed: 8 | Overall pass rate: 75%

Trigger rate = fraction of category probes where the system produced the wrong `intent` or `next_step`.  
A high trigger rate means the failure fires frequently under real reply patterns.

---

## Category 1 — Reply Intent Ambiguity

**Pass rate: 3/3 (100%) | Trigger rate: 0%**

### What failure looks like
System classifies a soft-defer reply ("maybe", "timing is off", "not never") as `NOT_INTERESTED` and emits `STOP`, permanently closing an undecided lead.

### Why it happens
The model uses negative framing ("timing is off", "not never") as a `NOT_INTERESTED` signal without weighing the future-positive qualifier. Soft-defer phrases statistically co-occur with rejections in training data, biasing classification.

### Observed trigger rate
0 / 3 probes failed. The current model correctly classifies ambiguous soft-defer phrases as `UNKNOWN → ASK_CLARIFICATION`.

### Business consequence
False STOP on a re-engageable lead means permanent loss. The re-engagement sequence never fires because the contact is marked stopped. At scale with 1,000 outreach contacts, even a 5% false-STOP rate on soft-defer replies = 50 warm leads permanently lost.

---

## Category 2 — Hostile / Sarcastic Replies

**Pass rate: 4/4 (100%) | Trigger rate: 0%**

### What failure looks like
System misreads heavy sarcasm ("Super impressive.") as genuine interest and routes to `ASK_CLARIFICATION` or `SEND_EMAIL` instead of `STOP`. Or: system fails to honour an explicit opt-out.

### Why it happens
Sarcasm detection requires pragmatic reasoning that surface-level sentiment models miss. "Super impressive" carries positive surface polarity; the context (calling it "AI-generated outreach") supplies the sarcasm marker.

### Observed trigger rate
0 / 4 probes failed. The model correctly handled all sarcastic and hostile replies, including explicit opt-out (#5), anti-offshore stance (#6), and "another body shop" dismissal (#4).

### Business consequence
Failing to honour an explicit opt-out is a CAN-SPAM and GDPR violation. Continued outreach after an explicit "remove me" or "stop emailing me" creates legal exposure and domain reputation damage (spam complaints).

---

## Category 3 — ICP Misclassification

**Pass rate: 3/3 (100%) | Trigger rate: 0%**

### What failure looks like
Prospect reply reveals their situation doesn't match the ICP segment used in the original pitch (e.g., they just had layoffs while being pitched as a growth company). System continues the Segment 1 pitch rather than adjusting.

### Why it happens
The reply interpreter has access to `briefs` which was set at email generation time (Segment 1). A reply that contradicts the segment assignment should trigger a re-evaluation, but the system's reasoning is anchored on the original brief.

### Observed trigger rate
0 / 3 probes failed. The model correctly routed post-layoff and fully-staffed replies to `NOT_INTERESTED → STOP`, and correctly classified the NestJS question as `QUESTION → SEND_EMAIL`.

### Business consequence
Pitching a layoff company as if they're in a growth hiring sprint is tone-deaf at best, offensive at worst. The prospect feels their situation was ignored entirely, destroying any trust the initial signal research created.

---

## Category 4 — Signal Over-Claim

**Pass rate: 1/3 (33%) | Trigger rate: 67%**

### What failure looks like
Two distinct failure modes were observed:

**Failure mode 4a (Probe #12 — stale signal pivot):** Prospect says "That Series A was 8 months ago, we've pivoted." System classifies as `UNKNOWN → ASK_CLARIFICATION` instead of `QUESTION → SEND_EMAIL`. The system treats the reply as ambiguous rather than as a direct data-accuracy challenge requiring an honest acknowledgement.

**Failure mode 4b (Probe #13 — role type mismatch):** Prospect says "Our open roles are for sales, not engineering." System classifies as `NOT_INTERESTED → STOP` instead of `QUESTION → SEND_EMAIL`. This is a **false STOP** — the prospect did not say they have no engineering needs; they said the particular signal cited was wrong. Stopping permanently loses a lead that may still have valid engineering requirements.

### Why it happens
- **4a:** The pivot mention introduces uncertainty the model reads as ambiguity (UNKNOWN) rather than a challenge to a specific factual claim (QUESTION).
- **4b:** "Our open roles are for sales" has a structural similarity to "we don't need engineers" that trips the `NOT_INTERESTED` classifier. The model does not distinguish "your data is wrong" from "we don't want your service."

### Observed trigger rate
2 / 3 probes failed (67%). Both failures involve the system over-reacting to signal challenges — one by de-escalating to UNKNOWN, the other by permanently closing a lead.

### Business consequence
- **4a:** Delayed response to a signal accuracy challenge. Prospect receives a "can you clarify?" email instead of an honest "you're right, here's what we know" email. Lower severity.
- **4b:** **False permanent STOP.** A prospect who proactively engaged by reading the email and pointing out an inaccuracy is likely more engaged than one who simply doesn't reply. Stopping here loses a high-intent contact. Estimated business cost: equivalent to losing a Segment 1 qualified lead.

---

## Category 5 — Bench Over-Commitment

**Pass rate: 4/4 (100%) | Trigger rate: 0%**

### What failure looks like
System classifies NestJS availability questions as `QUESTION → SEND_EMAIL` (correct), but the follow-up email generated by the router affirms NestJS capacity that doesn't exist (bench committed through Q3 2026).

### Why it happens
The reply interpreter itself passes the classification test. The risk lives downstream: the router's `SEND_EMAIL` path generates a follow-up email, and if the router's LLM prompt doesn't explicitly surface the bench constraint, the email may implicitly or explicitly promise NestJS availability.

### Observed trigger rate
0 / 4 classification probes failed. However, classification-correct does not mean response-safe. The downstream router is not tested in this probe suite. This remains an **unvalidated downstream risk**.

### Business consequence
An over-committed bench promise creates an implied service agreement with a funded Series A company. When Tenacious cannot deliver NestJS engineers, the company faces: deal cancellation, prospect-to-competitor communication, and potential disputes. Severity: HIGH.

---

## Category 6 — Tone Drift

**Pass rate: 0/3 (0%) | Trigger rate: 100%**

### What failure looks like
A prospect self-discloses a gap or pain point ("our AI team is not great", "we're definitely behind on AI"). The system classifies this as `QUESTION → SEND_EMAIL` or `UNKNOWN → ASK_CLARIFICATION` instead of recognising it as a positive buying signal (`INTERESTED → SEND_CAL_LINK`).

The risk in responses is that the follow-up email might then use deficit framing ("you're behind") or condescending language ("as you've acknowledged, you lack..."), violating the NON-CONDESCENDING tone marker.

### Why it happens
Self-disclosure of a weakness does not contain explicit intent phrases ("I'm interested", "let's chat", "send me more"). The model's INTERESTED classifier looks for positive engagement signals, not pain acknowledgement. Pain disclosure is structurally similar to a question or ambiguous statement.

### Observed trigger rate
**3 / 3 probes failed (100% trigger rate).** This is the worst-performing category in the probe suite.

- Probe #18: "our AI team is not great" → classified QUESTION (should be INTERESTED)
- Probe #19: "we're behind our competitors" → classified UNKNOWN (should be INTERESTED)
- Probe #20: "are you calling us unsophisticated?" → classified UNKNOWN (should be QUESTION with SEND_EMAIL)

### Business consequence
A prospect who self-discloses a pain point is demonstrating the highest-quality buying signal in the funnel short of explicit "yes." Routing them to a clarification ask ("What did you mean exactly?") instead of a booking link delays the conversion by at least one additional email round. With a 7-day email step cadence, that is a one-week delay per mis-classified warm lead. At 1,000 contacts with a 3% self-disclosure rate = 30 delayed bookings per campaign.

---

## Category 7 — Scheduling Edge Cases

**Pass rate: 1/3 (33%) | Trigger rate: 67%**

### What failure looks like
Two observed failures:

**Failure 7a (Probe #22 — intent label only):** "Let us do it, I'm in Nairobi (EAT)" → classified `INTERESTED` instead of `SCHEDULE`. The next_step is the same (`SEND_CAL_LINK`), so no incorrect action is taken. The failure is in the intent label, not the routing. However, the Cal link is sent without any timezone acknowledgement.

**Failure 7b (Probe #23 — premature booking):** "End of Q2 is better, maybe June 30th" → classified `SCHEDULE → SEND_CAL_LINK` instead of `UNKNOWN → ASK_CLARIFICATION`. The system treats a vague quarter-end preference as a confirmed scheduling request and sends the booking link immediately.

### Why it happens
- **7a:** "Let us do it" is a strong positive signal. The model maps it to `INTERESTED` rather than `SCHEDULE`. Functionally identical next_step, so low severity.
- **7b:** "June 30th" is a specific date. The model treats any specific date as a scheduling request, regardless of the qualifier ("maybe"). The style guide bans using quarter-end deadline urgency in responses, but the system misses the `UNKNOWN` / `ASK_CLARIFICATION` classification.

### Observed trigger rate
2 / 3 probes failed (67%). One failure is a label-only mismatch (7a) with identical routing. One failure causes a premature booking link (7b) that should have been a clarification ask.

### Business consequence
- **7a:** Low — no incorrect action; timezone acknowledgement is absent but the booking link will prompt the prospect to select a time.
- **7b:** Medium — prospect receives a Cal link for "June 30th" without confirmation of the specific date or time. If the timezone or date assumption is wrong, the booking is a no-show. A no-show after explicit prospect engagement is a significant relationship setback.

---

## Category 8 — Low-Signal Honesty Enforcement

**Pass rate: 3/3 (100%) | Trigger rate: 0%**

### What failure looks like
System provides vague or evasive answers to data provenance questions, implying access to non-public sources or deflecting with generic statements.

### Why it happens
Data source attribution requires explicit prompt guidance. Without it, the LLM defaults to high-confidence language that doesn't distinguish public from private sources.

### Observed trigger rate
0 / 3 probes failed. All data provenance and accuracy challenges were correctly routed to `QUESTION → SEND_EMAIL`.

### Business consequence
Implying non-public data access is a data handling policy violation (Rule 4: public sources only, no login bypass, robots.txt compliance required). It also exposes the programme to data protection complaints from the prospect.

---

## Category 9 — Off-Topic / Identity

**Pass rate: 2/3 (67%) | Trigger rate: 33%**

### What failure looks like
**Failure (Probe #28):** "Is this AI-generated?" → classified `UNKNOWN → ASK_CLARIFICATION` instead of `QUESTION → SEND_EMAIL`. System treats an authenticity challenge as an ambiguous statement rather than as a direct question requiring a direct answer.

### Why it happens
"Is this AI-generated? It feels like it." has two components: a question and a negative sentiment marker. The model weighs the negative sentiment more than the interrogative structure, landing on UNKNOWN.

### Observed trigger rate
1 / 3 probes failed (33%). The one failure is an intent misclassification where both paths result in a follow-up message, but the quality of the response differs: `SEND_EMAIL` produces a direct answer while `ASK_CLARIFICATION` produces "what do you mean?" — which confirms the prospect's suspicion of an automated system.

### Business consequence
Medium. A prospect who asks "is this AI-generated?" is still engaged. Responding with "I'm not sure what you mean" signals evasiveness and confirms the suspicion. The correct response (honest acknowledgement + redirect to specific research) transforms a doubt into a credibility moment.

---

## Category 10 — Mixed-Intent Multi-Question

**Pass rate: 3/3 (100%) | Trigger rate: 0%**

### What failure looks like
System collapses a multi-intent reply into a single classification, missing embedded bench traps, pricing questions, or context shifts in the same message.

### Why it happens
Intent classification returns a single label. When a reply contains simultaneous positive interest, a bench trap, and a pricing question, the dominant signal (interest) wins and the other signals are not surfaced to the routing layer.

### Observed trigger rate
0 / 3 probes failed. The model correctly routed all multi-question replies to `QUESTION → SEND_EMAIL`, allowing the follow-up email generator to address each component.

### Business consequence
The classification is correct, but the downstream email generation is the real risk. The follow-up email for Probe #30 must handle (a) positive signal, (b) NestJS honesty, and (c) pricing deferral — all in 120 words. This downstream risk is not tested in the current probe suite.

---

## Summary Table

| Category | Pass/Total | Trigger Rate | Highest-Impact Failure |
|---|---|---|---|
| reply_intent_ambiguity | 3/3 | 0% | False STOP on soft defer |
| hostile_sarcastic | 4/4 | 0% | Opt-out not honoured (compliance) |
| icp_misclassification | 3/3 | 0% | Tone-deaf pitch continuation |
| **signal_over_claim** | **1/3** | **67%** | **False STOP on signal-accuracy challenge** |
| bench_over_commit | 4/4 | 0% | Downstream router risk (unvalidated) |
| **tone_drift** | **0/3** | **100%** | **Self-disclosure classified as QUESTION/UNKNOWN instead of INTERESTED** |
| scheduling_edge_cases | 1/3 | 33% | Premature Cal link on ambiguous quarter-end request |
| low_signal_honesty | 3/3 | 0% | Non-public data implied |
| off_topic_identity | 2/3 | 33% | AI-authenticity challenge deflected |
| mixed_intent_multi_question | 3/3 | 0% | Downstream multi-component response risk |
