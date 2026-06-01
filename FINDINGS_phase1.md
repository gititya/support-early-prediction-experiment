---
title: Phase 1 Findings — Predictability Validation
project: support-voice
date: 2026-05-31
status: complete
gate_result: FAIL (first-6-turns premise) → REFRAMED (mid-call signal is real)
---

# Phase 1 Findings — Predictability Validation Harness

This document is the authoritative record of the Phase 1 validation run for the Voice Support
Intelligence Copilot (PRD: `PRD_1st.md`). It is written to be re-readable by a future LLM session
with no prior context. All numbers are from the run on 2026-05-31. Artifacts live in
`runs/latest/` (`summary.md`, `scores.csv`, `scores.json`, `predictions.json`, `curve.csv`).

---

## 1. The question being tested

PRD first product gate (PRD_1st.md §"Validation-First Development", lines 262–269):

> **"Are support interactions predictable early enough for realtime speculative assistance to be
> genuinely useful?"**

Operationalized (per `VOICEAGENT_ARCHITECTURE_NOTE.md` §"Validation Gate" and
`initial_research/MARS-adverserial.md` c2/c7) as:

- **Gate metric:** specific *root cause* (not broad category) correctly predicted from the call's
  opening, blind-scored, on ≥ **60%** of calls. Threshold lives in `metrics.GATE_THRESHOLD = 0.60`.
- "Opening" = first **6 turns** (`VE_EARLY_TURNS`, the "first 60–90 seconds" proxy).
- **Category ≠ the test.** The scenario type (permissions / migration / workspace setup) is obvious
  from turn 1; predicting *that* is trivial and not the gate.

---

## 2. Method (and why it is trustworthy)

- **Dataset:** 51 synthetic B2B SaaS support calls from the `support-call-generator` dependency
  (GPT-authored, `gpt-5.4-mini`). 50 from one `generate-batch --count 50` + 1 smoke call. Each call
  ships a hidden `ground_truth.json` (true root cause), a gold `expected_timeline.json`
  (turn-by-turn hypothesis trajectory), and a `leakage_report.json`.
- **Cross-family separation (anti-self-confirmation):**
  - **GPT** authored the calls.
  - **Claude** (`claude-sonnet-4-6`) is the **blind annotator** — sees transcript turns only,
    never ground truth. Enforced by the export boundary + `test_boundary`.
  - **GPT** (`gpt-5.4-mini`) is the **match judge** — compares prediction vs hidden answer key for
    semantic equivalence.
  - Hard rule (CLAUDE.md): predictor and judge are never the same model. Satisfied
    (Claude predicts, GPT judges).
- **Leakage gating:** the generator flags calls where the customer reveals root-cause-specific
  terms too early. 51 calls = **29 PASS** (clean) + **22 WARNING** + **0 FAIL**. We report metrics
  on both all-51 and the clean PASS-only-29 subset as a sensitivity check.

**Distribution of the 51 calls:**
- Scenario: permissions_access 18, onboarding_migration 17, workspace_setup 16 (balanced).
- Difficulty: hard 24, medium 24, easy 3 (deliberately hard-skewed — easy calls don't test the gate).
- Resolution: probable_cause 20, resolved 13, escalated 8, handoff 6, unresolved 4.
- Call length: 18–25 turns, median 20.

---

## 3. Result A — the gate (first 6 turns)

`runs/latest/summary.md`:

| Metric | All 51 | Clean (PASS-only 29) |
|---|---|---|
| **Early specific root-cause accuracy (THE GATE)** | **14%** | **7%** |
| Full-transcript specific accuracy | 92% | 97% |
| Broad-category accuracy (sanity) | 90% | — |
| Next-diagnostic-question usefulness | 33% | — |
| Early→full delta | 78 pts | 90 pts |

**Verdict: GATE FAIL.** 14% (7% clean) vs a 60% bar.

**Why this is a real "no", not a broken harness:**
1. Full-transcript accuracy is 92–97% → the annotator and judge work; given the whole call,
   Claude nails the cause almost every time. The judge is not too strict.
2. Broad-category accuracy is 90% → the scenario type *is* obvious early, as expected. Never the question.
3. **Leakage inverts the worry:** leaked calls scored *higher* early (23%), clean calls *lower* (7%).
   Leakage was inflating the gate, not undermining a pass. The honest early number is the clean 7%.

**Error pattern (44 misses, from `summary.md`):** early on, Claude predicts a plausible *generic*
cause (template misconfig, dropped role, dedup, session issue) while the true cause is a *specific
operational mechanism* surfaced only later — SCIM sync delay, stale entitlement cache, archived-team
export filter, missing integration write scope, region mismatch, admin-approval dependency,
inherited-role conflict.

---

## 4. Result B — the predictability curve (the reframe)

The gate tests one snapshot (6 turns). To find *where* prediction becomes reliable, `curve.py`
sweeps the opening-window size and re-annotates+re-judges at each. Windows 6 and full are reused
from `runs/latest`; 10/14/18 annotated fresh. Output: `runs/latest/curve.csv`.

**Accuracy vs opening turns seen:**

| Turns seen | All 51 | Clean (PASS-only 29) |
|---|---|---|
| 6  | 14% | 7%  |
| 10 | 37% | 34% |
| **14** | **78%** | **76%** |
| 18 | 88% | 90% |
| full (~20) | 92% | 97% |

The curve is a clean S-shape. **It crosses the 60% bar at ~turn 12–13** (between windows 10 and 14).
So the AI *does* identify the cause reliably — just at mid-to-late call, not in the opening.

---

## 5. Result C — head start vs the gold timeline (does it predict, or just transcribe?)

A late-but-correct guess is only valuable if it *beats* the moment the cause becomes obvious in the
call. The generator's gold `expected_timeline.json` records, per call, when the correct hypothesis
becomes credible and when it is confirmed. Computed across all 51:

| Gold milestone | Median turn | (of median-20-turn call) |
|---|---|---|
| Correct cause first reaches 0.5 confidence ("credible") | **15** | ~75% through |
| Correct cause **confirmed** (high confidence) | **18** | ~90% through |

**Side-by-side:**

| Turn | AI accuracy (clean) | Gold state of the true cause |
|---|---|---|
| 6  | 7%  | not credible anywhere |
| 10 | 34% | just starting to surface (earliest credible = turn 11) |
| 14 | 76% | crossing "credible" (median turn 15) |
| 18 | 90% | being **confirmed** (median turn 18) |

**Two conclusions:**
1. **The 6-turn gate was unanswerable by construction.** The gold says the true cause is not
   credibly present until ~turn 15. Asking for it at turn 6 asks the model to name information that
   is not yet in the transcript. The 14%/7% reflects *absent information*, not poor reasoning.
2. **The AI predicts modestly AHEAD.** It reaches ~76% by turn 14 — at/just before the gold
   "credible" point (turn 15) and **~4 turns before in-call confirmation (turn 18)**. It is locking
   on slightly early, not merely echoing the answer once stated.

---

## 5b. Narrow-domain curve (computed 2026-05-31, from existing `curve.csv`, no new spend)

Re-sliced the curve by `scenario_type` (joined from the manifest). Narrowing the domain helps,
and one domain is markedly more predictable earlier:

| Scenario | t6 | t10 | t14 | t18 | full | n | Crosses 60% |
|---|---|---|---|---|---|---|---|
| ALL | 14% | 37% | 78% | 88% | 92% | 51 | ~turn 13 |
| permissions_access | 11% | 17% | 72% | 89% | 94% | 18 | ~turn 13 |
| **onboarding_migration** | 12% | **65%** | 88% | 88% | 88% | 17 | **~turn 10** |
| workspace_setup | 19% | 31% | 75% | 88% | 94% | 16 | ~turn 13 |

**Finding:** onboarding/migration becomes reliable at the call midpoint (~turn 10 of ~20),
plateauing by turn 14 — roughly an **8-turn head start** before in-call confirmation (gold ~turn 18),
~double the aggregate's ~4 turns. This revives the realtime case *for that domain specifically*.
**Caveats:** (1) first-6-turns premise stays dead in all three domains — narrowing doesn't rescue
"predict from hello"; (2) n=17, so 65% = 11/17 — real signal, wide confidence band, wants a
dedicated larger migration-only run to confirm.

## 5c. Post-call record probe (2026-05-31, `postcall_probe.py`, n=12 sample, 4/scenario)

Tests PRD Output #2 + success-state line 326 ("operational reasoning beyond naive summarization").
Claude reads the FULL transcript → structured record; GPT judges vs ground truth. Output
`runs/latest/postcall_probe.json`.

| Dimension | Score |
|---|---|
| Final hypothesis correct | 92% (11/12) |
| Failed/abandoned-path recall | 81% |
| "Beyond naive summarization" (judge) | 100% |
| Escalation flagged correctly | 50% — **artifact, disregard** |

**Finding:** the post-call record is strong on its core — reproduces the final cause (92%, matches
full-window), recovers most failed troubleshooting paths (81%), and is judged "beyond summarization"
on all 12. Satisfies the PRD success criterion. Combined with the thin realtime head start, this
supports the PRD's own risk (line 367): **post-call may be the higher-value first deliverable.**

**Known bug in this probe:** the escalation truth used `bool(escalation_timeline)`, but all 51
calls have escalation-timeline entries (they log moments like early trust-degradation, not actual
escalation). The correct truth is `resolution_type` (escalated 8 + handoff 6 = ~14/51 actually
escalated). So the 50% is against a broken yardstick — **escalation detection is unmeasured, not
weak.** To fix: re-judge `escalated` against `resolution_type`.

## 6. Revised verdict

- **DEAD:** the literal premise *"predict the specific cause in the first 60–90 seconds."* Both the
  AI (7% clean) and the generator's own gold timeline agree the information is not present that
  early. Do **not** build on first-seconds speculation.
- **ALIVE, but smaller:** a **mid-call copilot** that tracks the conversation and locks onto the
  cause around turn 13–14 — a handful of turns before the agent/customer confirm it. Value prop is
  not "speculate from hello" but "confirm the likely cause a few turns early and track how the
  hypothesis shifts."
  - For **onboarding/migration specifically**, the head start is bigger (~turn 10, ~8 turns; §5b) —
    the strongest realtime candidate domain.
- **STRONGEST near-term bet — post-call record (§5c):** reproduces the cause 92%, recovers 81% of
  failed paths, judged "beyond summarization" 100%. Needs no early-prediction premise to hold.
  Aligns with the PRD's own risk (line 367) that the product may be more valuable post-call than
  realtime.
- **The open product decision (now grounded in data, not a guess):** three viable paths, in rough
  order of evidence strength — (a) ship the **post-call record** first; (b) a **migration-only
  realtime copilot** with an ~8-turn head start; (c) a **broad mid-call copilot** with only a
  ~4-turn head start (weakest). All three should pass an **OOD check first** (§8.2).

**Caveats:**
- The gold timeline is the generator's own (GPT-authored) model of identifiability — a
  self-consistent reference, not observed human behavior.
- All 51 calls are synthetic and in-distribution. No real or out-of-distribution calls yet.
- Cross-family split holds (Claude predicted, GPT/gold are the reference), so it is not grading its
  own homework — but the gold and the judge share GPT lineage.

---

## 7. Did we do what the PRD asked? (compliance map)

The PRD only mandates the **validation gate** before any realtime build ("the system should earn
the right to become realtime", line 313). Everything else is gated behind it. Mapping our work to
the PRD's validation requirements:

| PRD requirement (section / line) | Status | Notes |
|---|---|---|
| First gate: "predictable early enough?" (§Validation-First, 266) | ✅ Done + exceeded | Answered, and the curve sharpened "early" into a turn-by-turn answer |
| 30–50 realistic interactions (§Validation Dataset, 276) | ✅ 51 | Top of the range |
| Synthetic conversations allowed (288–291) | ✅ | `support-call-generator` |
| Separate authorship from scoring (293–294) | ✅ | GPT authors → Claude predicts → GPT judges; predictor≠judge |
| Blind scoring (296) | ✅ | Annotator sees transcripts only; boundary test enforces |
| Out-of-distribution / more-realistic checks (296; arch note "5–10 OOD") | ❌ **Gap** | All 51 are in-distribution synthetic. No OOD or real calls. |
| Dataset includes ambiguity, repeated troubleshooting, changing hypotheses, customer confusion, operational twists (278–287) | ✅ Done (audited 2026-05-31) | All seven PRD traits present in 51/51 calls (read from `scenario_spec` + `ground_truth`): customer unreliability, hypothesis reversals (median 3), false leads (2), abandoned troubleshooting (3), late-reveal facts (3), conflicting observations (3), escalation trajectory. Ambiguity spread high 21 / med 11 / low 19. Only rigidity: `customer_unreliability` always exactly 2 cues. The gate's 7% is not a too-clean-data artifact. |
| Eval goal: early issue predictability (302) | ✅ | The gate + curve |
| Eval goal: usefulness of next diagnostic questions (303) | ✅ Measured — weak | 33% useful. Below where a live-nudge premise feels strong. |
| Eval goal: hypothesis stability (304) | ⛔ Deferred | Requires the realtime state tracker (not built) |
| Eval goal: escalation prediction (305) | ⛔ Deferred | Not built; data has escalation markers to support it later |
| Eval goal: false-positive / missed nudges, nudge fatigue (306–311) | ⛔ Deferred | No nudge system yet |
| Eval goal: time-to-stable-hypothesis (308) | ⚠️ Adjacent | The curve + gold confirm-turn approximate this; the system's *own* stability not measured |
| Eval goal: operational coherence (310) | ⛔ Deferred | Requires the realtime build |

**Key risk the PRD itself flagged that our data now speaks to:**
> "The product may ultimately be more valuable **post-call** than realtime" (line 367).

Our finding (the reliable signal arrives at ~turn 13–14, only ~4 turns before confirmation) is
direct evidence toward this risk: the realtime head start is thin. A structured **post-call
operational record** (PRD §Core MVP Outputs #2) may be the higher-value first deliverable.

**Summary:** we completed the one thing the PRD required before building (the gate) and went beyond
it (the curve + gold comparison). The remaining eval goals are correctly deferred behind the gate —
*except* two real gaps the PRD explicitly asked for and we have not done: **(a) out-of-distribution /
real-call checks**, and **(b) an explicit audit that the dataset contains the ambiguity / repeated-
troubleshooting / confusion traits**, rather than just scenario-type balance.

---

## 7b. Coverage vs `first_proposal.md` (what the broader vision claims vs what we tested)

The first proposal is far broader than the PRD. We validated the root-cause-prediction spine and a
few adjacent things; most claimed capabilities are untested.

| Capability (first_proposal.md) | Tested? | Evidence |
|---|---|---|
| Identify issue category | ✅ | 90% |
| Identify root cause early | ✅ | gate + curve |
| Next diagnostic question | ✅ weak | 33% |
| Hypothesis stability over the call | ✅ (2026-05-31) | 88% monotonic; 12% regress; 10% >1 flip; 2% never right (from `curve.csv`) |
| Troubleshooting progress / failed paths | ⚠️ partial | post-call recall 81% |
| Detect escalation early | ❌ | only the broken-proxy probe; testable now via `escalation_timeline` turns + `resolution_type` |
| Predict troubleshooting branches | ❌ | untested (`issue_path`, `wrong_paths` available) |
| Track confusion/trust/frustration trajectory | ❌ | entirely untested |
| Churn indicators | ❌ | untested |
| Resolution-confidence monitoring | ❌ | untested |
| Repeat-contact probability / unresolved risk | ❌ | untested |
| Repeated-loop detection | ❌ | untested |
| Communication/expectation breakdowns | ❌ | untested |
| Cross-call org pattern layer | ❌ | untested — PRD explicitly defers (Long-Term Direction), so OK |

**Two untested pillars the proposal leans on:**
1. **Early escalation detection** — named repeatedly; fully testable now with existing data; highest-
   value untested capability. Our only attempt used a broken proxy (§5c).
2. **Emotional / trust / frustration trajectory** — proposal centers it (line 38 arc); we tested
   none of it. **Conflict:** `VOICEAGENT_ARCHITECTURE_NOTE.md` explicitly says to REJECT soft
   emotional scoring beyond explicit escalation markers. Proposal vs architecture note disagree on
   whether this pillar should exist — a product decision, not just a test.

## 8. Recommended next experiments (not yet done)

1. ~~**Narrow-domain curve**~~ — DONE 2026-05-31 (§5b). Migration predictable at ~turn 10; wants a
   dedicated larger migration-only run (n was 17) to firm up the 65%.
2. **Out-of-distribution set (HIGHEST-VALUE OPEN GAP):** generate or source 5–10 calls outside the
   training distribution (or real anonymized calls) and re-run gate + curve. The migration
   head-start and post-call recall are exactly the signals most at risk of being synthetic
   artifacts — this is the gate before trusting any of the positive findings. Closes PRD OOD gap.
3. ~~**Dataset trait audit**~~ — DONE 2026-05-31. All seven PRD traits present in 51/51 calls (§7).
4. ~~**Post-call value probe**~~ — DONE 2026-05-31 (§5c). Strong (92%/81%/100%); supports post-call
   as the likely higher-value MVP.
5. **Escalation re-judge (cheap fix):** re-score the post-call probe's `escalated` flag against
   `resolution_type` instead of the broken `escalation_timeline` proxy (§5c).
6. **Larger migration-only run + post-call on full 51:** if pursuing the migration realtime path,
   confirm the ~turn-10 crossover at higher n; run the post-call probe on all 51, not 12.
7. **Early escalation-detection test (high value, data ready):** add an `will_escalate` field to the
   early annotation; truth = `resolution_type ∈ {escalated, handoff}`; measure early-window
   precision/recall and how many turns ahead of the gold `escalation_timeline` moment it fires.
   This is the biggest untested capability from `first_proposal.md` (§7b).
8. **Decide the emotion/trust pillar (product call, not a test):** proposal centers trust/frustration
   trajectory; architecture note says reject soft emotional scoring. Resolve the conflict before
   testing — if kept, the data has `stressors`, `customer_persona`, and trust-degradation markers in
   `escalation_timeline` to score against.

---

## 9. How to reproduce

```bash
source .venv/bin/activate
export OPENAI_API_KEY="$(security find-generic-password -a aditya -s my-openai-key -w)"
export ANTHROPIC_API_KEY="$(security find-generic-password -a aditya -s my-anthropic-key -w)"
python -m voice_eval run     # gate → runs/latest/{predictions,scores,summary}
python curve.py              # predictability curve → runs/latest/curve.csv
```

Dataset regeneration (from `../support-call-generator`, key exported inline):
`python -m support_call_generator generate-batch --count 50` then
`export-reviewed --status all --export-dir exports/latest`.

---

## 10. Follow-ups — 2026-06-01 (model robustness + early escalation)

Two tests run after the user reviewed Phase 1. Both are decisive and both push the same way:
early speculation is weaker than Phase 1's optimistic reframe, and the durable value is the
structured record, not realtime.

### 10a. Generator-model robustness (`model_robustness.py`) — ARTIFACT RISK

Concern: the whole dataset *and* the gold timeline were authored by the small model
(`gpt-5.4-mini`). The predictor (Claude) is not the gate bottleneck — the author is, because a
weaker author may write calls that telegraph their cause too early. Test: regenerate 15 calls with a
frontier author (`SCG_MODEL=gpt-5.5`, balanced 5/5/5, all leakage-PASS) and recompute the curve.

| window | gpt-5.5 author | 5.4-mini (all-51) | 5.4-mini (PASS-only) |
|---|---|---|---|
| 6  | 0%  | 14% | 7%  |
| 10 | 0%  | 37% | 34% |
| 14 | 7%  | 78% | 76% |
| 18 | 60% | 90% | 90% |
| full | 80% | 92% | 97% |

Crossover slid **~turn 12 → ~turn 18**; full accuracy dropped **92% → 80%**. A spot-read confirms
the 5.5 calls are realistic and *coherently* ambiguous (e.g. a workspace-setup call floating
billing-hold, EU region, and trial-expiry branches before the true cause — a DNS record added at the
registrar instead of the authoritative zone — surfaces late), not incoherent. So harder ≠ broken;
harder = more realistic.

**Conclusion:** the Phase-1 positive findings — the mid-call ~turn-13 crossover (§4) and especially
the onboarding/migration ~turn-10, ~8-turn head start (§5b) — are **substantially an artifact of the
small author model.** With a frontier author, reliable identification moves to ~turn 18, i.e. essentially
call-end, erasing the realtime head start. Real calls are likely at least this hard. **Any realtime
build must be gated on re-running the curve against frontier-authored or real calls first.** Caveat:
n=15, wide confidence bands — but the effect is large and monotonic across every window.

### 10b. Early escalation detection (`escalation_probe.py`, a1) — NEGATIVE

Sharpened per the 2026 market (reactive keyword/sentiment triggers are commoditized; the open
problems are firing *earlier* than reactive and the *handoff package*). Truth =
`resolution_type ∈ {escalated, handoff}` (14/51). Claude predicts blind at windows 6/10/14; GPT
judges the package.

| window | precision | recall | F1 | fired |
|---|---|---|---|---|
| 6  | 27% | 100% | 43% | 51 |
| 10 | 27% | 100% | 43% | 51 |
| 14 | 28% | 100% | 44% | 50 |

The model fires `will_escalate` on **essentially every call** → precision = the 27% base rate, recall
100%, F1 ~43%. It is uniformly **alarmist with no discrimination.** Confidence does not separate
escalators from non-escalators (escalated mean 0.83 vs 0.81, gap **+0.02**; ranking **AUC 0.58**), so
no threshold rescues it. The head-start figures (median 11 turns vs gold, median 3 vs a reactive
keyword baseline, baseline misses 5/14 outright) are **meaningless given no precision** — firing on
everything trivially "beats" any later trigger.

**Conclusion:** early escalation prediction fails for the same reason the root-cause gate failed —
the discriminating signal is not in the early window. Note the inversion of the original worry: the
failure mode is not *under*-escalating, it is an early predictor that flags everything. **Salvageable
piece:** the handoff *package* is judged **75% usable**, though hypothesis-on-track is only **45%** at
the early fire window. That usable-record value belongs to the post-call / mid-call record (§5c), not
to early prediction.

### 10c. Net effect on the recommendation

Both follow-ups reinforce §6/§7's direction and harden it: early speculation (cause or escalation)
does not hold up, and it is *worse* than the Phase-1 reframe once a frontier model authors the data.
The 5.5 probe doubles as a mini-OOD check (§8.2) and it already broke the optimistic findings.
Therefore: **(1) OOD / real-call validation is now the hard gate before any realtime build**, and
**(2) the recommended first deliverable is the structured post-call / handoff record on a chat
surface** (the only capability that survived both follow-ups: 75% usable handoff package here,
92%/81% post-call). Voice-specific signal (prosody) stays out of scope per the chat decision.

---

## 11. The decisive frontier-author gate — 2026-06-01 (PROJECT CONCLUSION)

Ran the full gate on **48 calls authored by `gpt-5.5`** (the frontier model), balanced 16/16/16,
45 PASS + 3 WARNING. This is the definitive version of the §10a probe — the real test of whether
early predictability survives a strong author. Output in `runs/gpt55_full/` (kept separate; the
5.4-mini baseline in `runs/latest` is untouched).

| Metric | gpt-5.5 (n=48) | gpt-5.4-mini (n=51) |
|---|---|---|
| **Early specific root cause (THE GATE)** | **2%** | 14% (7% PASS-only) |
| Full-transcript accuracy | 92% | 92% |
| Broad category accuracy | 94% | 90% |
| Next-question useful | 25% | 33% |

**By scenario (early specific):**

| Scenario | gpt-5.5 | Phase-1 (5.4-mini) |
|---|---|---|
| onboarding_migration | **0%** (n=16) | 12% → claimed "predictable at ~turn 10" |
| permissions_access | 6% (n=16) | 11% |
| workspace_setup | 0% (n=16) | 19% |

### What this settles (definitively)

1. **Early predictability is a small-model artifact.** A frontier author drops the gate from 14% to
   **2%**. The opening of a realistically-written support call essentially never contains the
   specific root cause. The premise is not "below threshold" — it is **absent**.
2. **The migration head start does not exist.** Phase-1's single realtime bright spot
   (onboarding_migration predictable ~turn 10, ~8-turn lead, §5b) was entirely a tell baked in by the
   weaker author. On frontier-authored migration calls it is **0% early**. There is no salvageable
   narrow realtime domain in this data.
3. **The harness is sound; the result is real.** Full-transcript accuracy held at 92% and category
   at 94% — Claude and the GPT judge work fine given enough of the call. The 2% is genuinely absent
   early information, now confirmed independently of author-model size. Cross-family integrity held
   (GPT authored → Claude predicted → GPT judged).

### Project conclusion — STOP (recommend not building)

Combining everything (gate FAIL, curve, a1 escalation NEGATIVE, frontier-author collapse), the
honest, unbiased verdict is that **the project has delivered its highest-value output — a rigorous
"no" on the realtime premise — and continuing to a build is not justified on this evidence:**

- **The differentiated bet (realtime speculative solving) is dead.** Not narrowable; the information
  is not present early. Confirmed across two author models and the escalation probe.
- **The only capability that survived (post-call / handoff record, 92%/81%/75%) is the *least*
  differentiated piece.** Per the 2026 market scan, AI handoff summaries and post-call records are
  already commoditized across support platforms. Building it is a me-too feature, minus the live
  predictive layer that would have made it special — and that layer is exactly what failed.
- **The test that matters cannot be run.** Everything is synthetic; the one reality-check (a stronger
  author) collapsed the optimistic findings. No real-call access exists to validate the survivors,
  and there is a strong prior they would also soften.
- **Fit:** this is enterprise support tooling, not a daily-use personal tool; there is no usage pull
  to carry it past weak evidence.

**Decision:** treat Phase 1 as complete and successful — for ~$10 it prevented building a realtime
support copilot that the data says would not work. Do **not** proceed to a build unless an
independent reason appears (genuine intent to be in support tooling **and** a concrete path to real
call data). Bank the harness as reusable IP (see project notes on extraction). Artifacts:
`runs/gpt55_full/{summary.md,scores.csv,summary.json}`, generator export
`../support-call-generator/exports/gpt55`.

---

## 12. Adversarial review correction — 2026-06-01 (Codex challenge)

A Codex adversarial review (verdict: needs-attention) accepted the realtime STOP but flagged that
this document **overstates the post-call/handoff record as a "surviving capability."** The
correction is accepted and supersedes the relevant wording in §5c, §10b, §10c, and §11.

**What was overstated:** the post-call probe is n=12, drawn from the *same* synthetic generator
distribution, judged by an **uncalibrated** GPT judge (never checked against a human), and one of its
four dimensions used an acknowledged-broken escalation truth. The 92% / 81% / 100% / 75% numbers are
therefore **a weak synthetic smoke-test signal, not validation.** Calling post-call/handoff the
"durable asset" or "the product" is not supported by the evidence and risks the same mistake the
project just avoided on realtime — building a me-too feature on flimsy data.

**Corrected status of post-call / handoff record:** demoted from *survived / validated* to
**unvalidated fallback**. It would need, at minimum: full-51 scoring (not n=12), a human-calibrated
judge check, and **real or production-derived transcripts** before any "validated" claim. As of May
2026 it is also commercially undifferentiated — post-call summaries and agent-assist/handoff tooling
are already broadly shipped by contact-center vendors, independently supporting the commoditization
concern.

**Net corrected conclusion (authoritative):**
- **Realtime speculative copilot — DEAD.** Early specific root-cause prediction collapses under
  frontier-authored synthetic calls (2%, migration 0%); escalation prediction is degenerate
  (fires on all). High-confidence STOP. *This is the valuable, defensible insight.*
- **Post-call / handoff record — UNPROVEN and undifferentiated.** Not a validated survivor; a weak
  hint at best, and a commodity even if real. Do not build on current evidence.
- **The single valuable takeaway:** *early specific root-cause and escalation prediction collapse
  under frontier-authored synthetic calls, while post-call records remain unproven and commercially
  undifferentiated.* Plus the reusable validation method (see vault note).

## 13. What's worth doing next (on resume — your call)

Ordered by value. Default is **do nothing** — Phase 1 is complete and the answer is STOP.

1. **(Default) Stop. Bank the harness + method.** Nothing more is worth spending on synthetic data;
   the result won't change. The reusable IP is the method note (Obsidian
   `methods/predictability-validation-pattern.md`).
2. **Only if real calls appear:** re-run the gate + post-call probe on **real/production-derived
   transcripts** with a **human-calibrated judge** check. This is the only test that could move any
   conclusion. Without real calls, skip.
3. **The one genuinely open door (needs audio):** voice-specific early *escalation* via prosody —
   the only place audio could plausibly beat text (tone carries frustration before words do). Out of
   scope until there's real audio; would not rescue root-cause prediction.
4. **Housekeeping if reusing the generator:** harden its prompt for frontier authors — `gpt-5.5`
   produced an ~89-attempt malformed-output streak generating the 48-call set.
