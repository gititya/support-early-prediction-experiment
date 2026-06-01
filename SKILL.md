# SKILL.md — support-voice

Project status and phase state. Append-only.

## What this is

`support-voice` = **Phase 1: Predictability Validation Harness** for the Voice Support
Intelligence Copilot (PRD in `PRD_1st.md`). It answers the PRD's first product gate —
*"Are support interactions predictable early enough for realtime speculative assistance to be
useful?"* — **before** any live copilot is built. Gate bar (MARS c2/c7): **early specific
root-cause prediction ≥ 60%** on blind-scored calls.

## Phase state (as of 2026-05-31)

- **Phase 0 — generator: DONE.** Lives at `../support-call-generator` (GitHub:
  `gititya/support-call-generator`, Python, GPT-`gpt-5.4-mini`). Installed as a **dependency**
  (git) — do **not** reimplement it. Emits transcripts + hidden ground_truth + gold
  expected_timeline + leakage_report, with a strict transcript/ground_truth export boundary.
- **Phase 1 — harness: BUILT.** `voice_eval/` package: loader (boundary-enforced), windows
  (early = first 6 turns), annotator (Claude blind), scorer (GPT judge + deterministic category),
  metrics (gate), report, cli (`predict`/`score`/`report`/`run`). 6 tests pass. Offline smoke
  on the 10 existing calls: exit 0, wrote `runs/latest/{predictions,scores,summary}`.
  Cross-family by design: **GPT authored → Claude reads blind → GPT judges**.

## BLOCKER (resume here 2026-06-01)

OpenAI key fails generation with `401 invalid_api_key`. The Keychain entry
`my-openai-key` (account `aditya`) holds a **dead key** (verified live). Anthropic key
(`my-anthropic-key`, account `aditya`, `sk-ant-…`) looks valid.

**Fix found from the MARS project** (`../MARS/mars/keys.py`): the working key lives under
Keychain **account `mars`, service `OPENAI_API_KEY`**; MARS `.strip()`s it and lets it override
stale shell vars. Decision left to user:
- **A)** read keys from account `mars` (services `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`), like MARS, or
- **B)** re-store a valid key into `my-openai-key` (`security delete-…` then `add-…`).

**RESOLVED 2026-05-31 (option B).** Chose B: copied the live `mars/OPENAI_API_KEY` (164-char
`sk-proj-…`) into `my-openai-key` (account `aditya`). Verified `HTTP 200`. The old dead key was
128 chars (truncated/revoked); re-pasting it twice failed before the copy fixed it. Documented
run path now works unchanged. Unblocked — proceed to "Next steps" (generate 50 calls).

## Next steps (once key works)

1. Generate 50 calls: from `../support-call-generator`, with `OPENAI_API_KEY` exported inline
   from Keychain, run the support-voice venv python: `python -m support_call_generator
   generate-batch --count 50` (writes `data/cases/`, auto-validates + leakage-gates each).
2. Validate distribution: scenario balance, difficulty spread, resolution types, PASS/WARNING
   leakage rate; spot-read 2–3 transcripts.
3. Export: `export-reviewed --status all --export-dir exports/latest`.
4. Re-run harness offline smoke to confirm manifest ingests.
5. Run the **real gate** with both keys: `python -m voice_eval run` → read
   `runs/latest/summary.md`. ≥60% early specific accuracy = proceed to copilot replay pipeline;
   below = narrow domain first.

Est. cost: ~$1.5–3 for dataset + first gate run. ~$1–2 per re-run (Claude annotator dominates;
`--no-full` knob could halve it — not yet built).

## GATE RESULT — 2026-05-31: FAIL ❌ (decisive)

Ran the real gate on 51 generated calls (50 batch + 1 smoke), exported `--status all`.
`runs/latest/summary.md`:

- **Early specific root-cause accuracy = 14%** (gate 60%) → **FAIL**.
- Full-transcript specific accuracy = **92%** → annotator + judge work; failure is genuinely
  about early-window information, not a broken harness or over-strict judge.
- Broad-category accuracy = 90% (category obvious from turn 1, as expected — never the question).
- Early→full delta = 78 pts. Next-question usefulness = 33%.

**Leakage sensitivity check** (per user request, computed from `scores.csv` × manifest
`leakage_status`): leakage was *inflating* the gate, not undermining a pass.
- PASS-only (clean, n=29): early **7%**, full 97%.
- WARNING (leaked terms, n=22): early **23%**, full 86%.
On the cleanest data early prediction is *worse* (7%). No way above 60%.

Error pattern (44 misses): early on, Claude predicts a plausible *generic* cause (template
misconfig, dropped role, dedup, session issue) but the true cause is a *specific operational
mechanism* surfaced only later (SCIM sync delay, stale entitlement cache, archived-team export
filter, missing integration write scope, region mismatch, admin-approval dependency).

**Decision (PRD first gate, MARS c2/c7):** do NOT build the broad cross-scenario realtime
speculative copilot — the early-predictability premise does not hold. PRD fallback applies:
**narrow the domain first**; within one tight scenario the early signal may clear the bar (worth
a follow-up run filtered to a single `scenario_type`). Artifacts in `runs/latest/`.

## PREDICTABILITY CURVE — 2026-05-31 (reframes the gate FAIL)

Built `curve.py` (standalone, reuses harness annotator+judge; windows 6 & full reused from
`runs/latest`, windows 10/14/18 annotated+judged fresh). Output `runs/latest/curve.csv`.
Accuracy vs opening-turns seen (PASS-only / all-51):

- 6: 7% / 14%   ·   10: 34% / 37%   ·   14: 76% / 78%   ·   18: 90% / 88%   ·   full: 97% / 92%

Crosses 60% at **~turn 12-13** (between windows 10 and 14). Compared against the generator's gold
`expected_timeline.json` (per-call turn at which the correct hypothesis becomes credible):
gold cause hits 0.5 confidence at **median turn 15**, **confirmed at median turn 18** (~90% of a
median-20-turn call).

**Reframe:** the first-6-turns gate tested for info that isn't physically in the transcript yet
(gold says the cause isn't credible until ~turn 15), so 14% was the answer being absent, not the
model failing. The AI reaches ~76% by turn 14 — at/just before the gold "credible" point and
~4 turns before in-call confirmation (turn 18). So it predicts modestly AHEAD, not just
transcribes.

**Revised verdict:** DEAD = "predict cause in first 60-90s" (both AI and gold agree info absent
that early). ALIVE-but-smaller = a mid-call copilot that locks onto the cause ~turn 13-14, a few
turns before agent/customer confirm it. Product call now on real data: is a ~4-turn head start
near call-end worth a realtime build? Caveats: gold timeline is generator's own (GPT) model of
identifiability; real-call confirmation still pending. Cross-family split holds (Claude predicts).

## FOLLOW-UPS — 2026-05-31 (post-curve)

- **Dataset trait audit:** all 7 PRD-required traits present in 51/51 calls (reversals, false leads,
  abandoned paths, late reveals, conflicting obs, customer unreliability, escalation trajectory).
  The 7% early gate is NOT a too-clean-data artifact.
- **Narrow-domain curve** (`curve.py` re-sliced by scenario, no new spend): **onboarding_migration
  predictable at ~turn 10 (65%→88%)** = ~8-turn head start, double the aggregate. permissions/
  workspace cross ~turn 13. First-6-turns premise dead in all three. n=17 for migration — wants a
  larger run.
- **Post-call record probe** (`postcall_probe.py`, n=12): hypothesis 92%, failed-path recall 81%,
  "beyond summarization" 100%. Escalation metric (50%) is a broken-proxy artifact — used
  `escalation_timeline` (present in all 51) instead of `resolution_type`; disregard / re-judge.
- **Verdict shift:** strongest near-term bet = **post-call record** (no early-prediction premise
  needed). Realtime is viable only narrowly (migration, ~8-turn lead). **OOD/real-call check is the
  top open gap** before trusting any positive finding — these are the signals most likely to be
  synthetic artifacts.

## ▶ RESUME POINT — 2026-05-31 (READ THIS FIRST NEXT SESSION)

**Read in this order to continue cold:**
1. This `SKILL.md` top-to-bottom (phase state + every dated section below this one).
2. `FINDINGS_phase1.md` — the full Phase 1 writeup: method, gate, curve, gold comparison,
   post-call probe, stability, coverage-vs-proposal (§7b), PRD compliance (§7), next steps (§8).
3. Memory: `MEMORY.md` index → `project-support-voice-phase1.md` (state) +
   `openai-key-401-mars-fix.md` (key gotcha).
4. Source docs if needed: `PRD_1st.md`, `VOICEAGENT_ARCHITECTURE_NOTE.md`,
   `initial_research/first_proposal.md`.

**Where things stand:** Phase 1 validation COMPLETE. First-6-turns gate FAILED (7% clean / 14%
all) but the curve reframed it — info isn't in the transcript that early; the AI locks on at
~turn 13 (aggregate), ~turn 10 for onboarding_migration (~8-turn head start). Post-call record is
strong (92%/81%/100%). Hypothesis stability good (88% monotonic). Dataset traits fully present.

**Decisions waiting on you (no work happening until you choose):**
- **A. Run OOD/real-call validation?** Top open gap — every positive finding is on synthetic
  in-distribution data and could be an artifact. Recommended before building anything.
- **B. Build order:** post-call record first (strongest, no early-prediction needed) vs
  migration-only realtime (~8-turn lead, n=17 needs confirming) vs broad mid-call (~4-turn, weak).
- **C. Run the early-escalation test?** Cheap, data-ready, highest-value untested capability.
- **D. Keep or kill the emotion/trust pillar?** first_proposal centers it; architecture note says
  reject it. The two docs conflict — your call, not a test.

**Artifacts:** `runs/latest/{summary.md,scores.csv,scores.json,predictions.json,curve.csv,
postcall_probe.json}`. **Scripts added:** `curve.py`, `postcall_probe.py`. Keys working
(my-openai-key + my-anthropic-key, account aditya). Reproduce: see `FINDINGS_phase1.md` §9.

## COVERAGE GAP vs first_proposal.md — 2026-05-31

The first proposal claims far more than we tested. Validated: category (90%), root cause (gate+
curve), next question (33% weak), **hypothesis stability (88% monotonic, from curve.csv)**, failed-
path recall (81% partial). **Untested pillars:** (1) **early escalation detection** — highest-value,
data-ready (escalation_timeline turns + resolution_type), only a broken proxy tried so far; (2)
**emotion/trust/frustration trajectory** — entirely untested AND in conflict with the architecture
note (which says reject soft emotional scoring) → product decision, not just a test. Also untested:
troubleshooting-branch prediction, resolution confidence, repeat-contact/churn, loop detection. Org
pattern layer untested but PRD explicitly defers it. See `FINDINGS_phase1.md` §7b.

## Findings doc

Full Phase 1 writeup (method, gate, curve, gold comparison, PRD compliance map, next steps):
`FINDINGS_phase1.md`.

## Plan file

`/Users/aditya/.claude/plans/prd-1st-md-the-prd-graceful-lake.md`

## DECISIONS + IMPLEMENTATION — 2026-06-01

User reviewed the 4 open decisions + skepticism on model size / scope. Resolutions:

- **#1 generator model (resolved):** the predictor (Claude) is NOT the gate bottleneck — info is
  absent early, full accuracy already 92-97%. The model that can change a finding is the *author*
  (dataset + gold timeline are both gpt-5.4-mini artifacts). Plan: cheap robustness probe, not a
  full retest up front. `model_robustness.py` runs a fresh curve on a ~12-15 call slice authored by
  the frontier model (`SCG_MODEL` env in the generator) and applies a decision rule — ROBUST
  (crossover shifts <2 turns AND full ≥88%) → no full retest; ARTIFACT → regenerate full + re-run.
- **#2 science-experiment risk (resolved):** stop adding synthetic measurement. One more test (a1)
  then build a thin real slice. Decisions A (OOD) + B (build order) are the gate, not more probes.
- **a1 early escalation (BUILT):** `escalation_probe.py`. Truth = `resolution_type ∈
  {escalated,handoff}` (14/51). Sharpened claim per 2026 market: reactive keyword/sentiment
  triggers are commoditized; the open problems are (i) firing EARLIER than a reactive baseline and
  (ii) the handoff context package. Probe measures precision/recall/F1 at windows 6/10/14, head
  start vs gold escalation turn AND vs a reactive keyword baseline, + GPT-judged handoff-package
  usefulness. Cross-family preserved (Claude predicts, GPT judges).
- **a2 repeat-contact / b1 churn:** BLOCKED — need cross-call / account-level truth absent from
  current synthetic data. Park until real data or a generator follow-up-call feature.
- **D / voice-vs-chat (resolved → CHAT):** everything tested is modality-agnostic text reasoning;
  nothing voice-specific (ASR, latency, prosody) was touched. The only voice-only signal is
  prosodic emotion, which feeds the b2 trust pillar the architecture note rejects. **Decision: keep
  CHAT for now** — cheaper to ship + test on real conversations, and the evidence already supports a
  chat product. b2 emotion pillar stays parked with the voice question.

Run order this session: write scripts → 5.5 robustness probe → a1 escalation probe → record results.

## RESULTS — 2026-06-01 (both ran; ~$3 spend)

**#1 — generator-model robustness: ARTIFACT RISK (decisive).** `model_robustness.py` on 15
frontier-authored calls (`SCG_MODEL=gpt-5.5`, balanced 5/5/5, all PASS-clean). Curve vs the
5.4-mini baseline:

| window | gpt-5.5 author | 5.4-mini base (all-51) | 5.4-mini base (PASS-only) |
|---|---|---|---|
| 6  | 0%  | 14% | 7%  |
| 10 | 0%  | 37% | 34% |
| 14 | 7%  | 78% | 76% |
| 18 | 60% | 90% | 90% |
| full | 80% | 92% | 97% |

Crossover slid **~turn 12 → ~turn 18**; full accuracy **92% → 80%**. Decision rule fired ARTIFACT
(shift ≥2 turns, full <88%). Spot-read of a 5.5 call confirms they're **realistic and coherently
ambiguous** (multiple live branches — billing/region/trial — before the real DNS-host cause), not
broken. **Conclusion:** the Phase-1 positive findings (mid-call ~turn-13 crossover, migration
~turn-10 head start) are **substantially an artifact of the small author model**. A better author
collapses early predictability to near call-end. Real calls are likely ≥ this hard. Do NOT trust any
realtime head-start claim until re-run on frontier-authored or real data. n=15 (wide bands) but the
effect is large + monotonic. Artifacts: `runs/gpt55/{curve.csv,robustness_verdict.txt}`,
generator export `../support-call-generator/exports/gpt55`.

**a1 — early escalation detection: NEGATIVE (decisive).** `escalation_probe.py`, all 51 calls,
truth = `resolution_type ∈ {escalated,handoff}` (14/51). Model fires `will_escalate` on **~all 51
calls** → precision **27%** (= base rate), recall 100%, F1 ~43% at every window (6/10/14). Uniformly
**alarmist, no discrimination.** Confidence does NOT separate escalators (gap +0.02, ranking AUC
**0.58**) → no threshold rescues it. "Head start" numbers (median 11 vs gold, 3 vs keyword baseline)
are meaningless given no precision. **Inversion of the original worry:** the failure isn't
*under*-escalating, it's an early predictor that flags everything — same root cause as the gate, the
early window lacks the discriminating signal. **Salvageable piece:** the handoff *package* is 75%
usable (hypothesis-on-track only 45% early) — that value belongs to the post-call / mid-call record,
not early prediction. Artifact: `runs/latest/escalation_probe.json`.

**Net for the build decision (CHAT):** both results push the same way — early speculation (cause OR
escalation) does not work, and it's *worse* than Phase 1 thought once a frontier model authors the
calls. The durable asset is the **structured record / handoff package** (75% usable here, 92%/81%
post-call). The 5.5 probe doubled as a mini-OOD check and it already broke the optimistic findings,
so **OOD/real-call validation (decision A) is now the hard gate before any realtime build**, and the
recommended first deliverable is the **post-call / handoff record on chat**, not realtime.

## FINAL — 2026-06-01: DECISIVE 5.5 GATE → PROJECT COMPLETE, RECOMMEND STOP

Ran the full gate on **48 `gpt-5.5`-authored calls** (16/16/16, 45 PASS): **early specific = 2%**
(vs 14% on 5.4-mini), full 92%, category 94%. **By scenario: migration 0%, workspace 0%, permissions
6%.** The Phase-1 migration "head start" was entirely a small-model tell — gone at 0% on a frontier
author. Early predictability is **absent, not just below bar**, confirmed independent of author
model. Harness sound (full 92%, cross-family held). Artifacts `runs/gpt55_full/`.

**Conclusion (honest/unbiased, user asked):** Phase 1 is **complete and successful** — for ~$10 it
proved the realtime speculative-copilot premise does not hold. **Recommend STOP, do not build:**
(1) the differentiated bet (realtime) is dead and not narrowable; (2) the only survivor (post-call/
handoff record) is the *commoditized* piece per the 2026 market scan; (3) the test that matters
(real calls) can't be run and the one reality-check collapsed the optimistic findings; (4) it's
enterprise support tooling, not a daily-use personal tool. Do not proceed unless real intent +
real-call access appear. **Bank the harness as reusable IP.** Full writeup: `FINDINGS_phase1.md`
§11. Curve on the 48 was started then killed (gate already decisive; saved ~$1.5).

## CODEX ADVERSARIAL REVIEW + CORRECTION — 2026-06-01

Codex review (verdict needs-attention) **accepted the realtime STOP** but corrected an overstatement:
the **post-call/handoff record was oversold as a "surviving capability."** Accepted. The probe is
n=12, same synthetic distribution, **uncalibrated** judge, one broken dimension → it's a **weak
synthetic smoke-test signal, not validation**, and commercially commoditized as of May 2026.

**Corrected authoritative conclusion:**
- Realtime speculative copilot = **DEAD** (high-confidence STOP) — *the valuable, defensible insight.*
- Post-call/handoff record = **UNPROVEN + undifferentiated** (demoted from "survived"); needs full-51
  scoring + human-calibrated judge + real transcripts before any "validated" claim. Do not build now.
- One-line takeaway: *early specific root-cause and escalation prediction collapse under
  frontier-authored synthetic calls; post-call records remain unproven and commercially
  undifferentiated.*

## ▶ ON RESUME — WHAT'S WORTH DOING NEXT (your call; default = nothing)

1. **(Default) STOP.** Phase 1 complete; more synthetic testing won't change the answer. Reusable IP
   banked at Obsidian `methods/predictability-validation-pattern.md`.
2. **Only if real calls appear:** re-run gate + post-call probe on real/production transcripts with a
   human-calibrated judge — the only test that could move a conclusion.
3. **Open door (needs audio):** voice-specific early *escalation* via prosody — the one place audio
   could beat text; out of scope without real audio.
4. **Housekeeping:** harden the generator prompt for frontier authors (gpt-5.5 had ~89 malformed
   attempts on the 48-call run) — only if reusing the generator.

Pushed to GitHub `gititya/real-time_support` on 2026-06-01. Full detail: `FINDINGS_phase1.md` §12–13.
