# Real-Time Support — Predictability Validation Harness

A blind, cross-family scorer that asks one question before any realtime infrastructure gets built:
**are support calls predictable early enough for a speculative AI copilot to be useful?** A kill-or-go
gate, not a product.

The answer it returned: **no.** That "no" is the deliverable.

---

## The One Idea

The pitch for a realtime support copilot is that an AI listening to the first 60–90 seconds of a call
can predict the *specific root cause* and start solving before the human agent does. Everything
downstream — the speculative UI, the realtime audio stack, the agent-assist layer — only matters if
that early signal actually exists.

So instead of building the stack and hoping, this harness tests the premise directly on synthetic
B2B SaaS support calls and scores it blind. The gate:

> **Specific root cause** (not broad category) correctly predicted from the call's opening,
> blind-scored, on ≥ **60%** of calls.

Category is not the test. The scenario type (permissions / migration / workspace setup) is obvious
from turn 1 — predicting *that* is trivial. The bet was always on the specific operational mechanism:
SCIM sync delay, stale entitlement cache, archived-team export filter, missing integration write
scope. That is what an agent would need early to be worth the realtime spend.

---

## The Verdict

**STOP. The realtime speculative-copilot premise is dead.**

| Metric | gpt-5.5 author (n=48) | gpt-5.4-mini author (n=51) |
|---|---|---|
| **Early specific root cause (THE GATE)** | **2%** | 14% (7% clean) |
| Full-transcript accuracy | 92% | 92% |
| Broad category accuracy | 94% | 90% |

Three things this settles:

1. **Early predictability is a small-model artifact.** A frontier author drops the gate from 14% to
   **2%**. The opening of a realistically-written call essentially never contains the specific cause.
   The premise isn't below threshold — it's *absent*.
2. **The one bright spot didn't survive.** Onboarding/migration looked predictable (~turn 10) under
   the weaker author; on frontier-authored migration calls it's **0% early**. It was a tell baked in
   by the weaker model, not a real signal.
3. **The harness is sound.** Full-transcript accuracy held at 92% and category at 94% — given enough
   of the call, the annotator and judge work fine. The 2% is genuinely missing early information.

The only capability that survived (post-call / handoff record) is the *least* differentiated piece —
post-call summaries are already commoditized — and it's unvalidated (n=12, uncalibrated judge,
synthetic). Not worth building on this evidence.

Authoritative writeup: [`FINDINGS_phase1.md`](FINDINGS_phase1.md) §11–13.

---

## Why You Can Trust the "No"

The failure mode of self-evaluation is a model grading its own homework. This harness is built to
prevent that with **cross-family separation**:

- **GPT** authors the calls (each ships a hidden `ground_truth.json` answer key).
- **Claude** is the **blind annotator** — sees transcript turns only, never the ground truth.
  Enforced by a sacred export boundary + a boundary test.
- **GPT** is the **match judge** — compares prediction vs hidden key for semantic equivalence.
- Hard rule: the predictor and the judge are never the same model.

Plus a leakage check (the generator flags calls where the customer reveals cause-specific terms too
early) and a clean PASS-only subset reported alongside the full set as a sensitivity check.

---

## What This Is NOT

- Not a realtime support copilot. It's the experiment that decided one shouldn't be built (yet).
- Not the call generator. The dataset comes from a separate dependency
  ([`gititya/support-call-generator`](https://github.com/gititya/support-call-generator)); this repo
  only *consumes* its exports.
- Not trained on real calls. Everything is synthetic — which is exactly why the frontier-author
  collapse matters, and why the survivors stay "unvalidated" until real transcripts appear.

---

## How to Run

```bash
source .venv/bin/activate
export OPENAI_API_KEY="..."      # match judge
export ANTHROPIC_API_KEY="..."   # blind annotator
python -m voice_eval run         # predict -> score -> report into runs/latest
pytest -q                        # boundary + scorer tests
```

Config via env: `VE_EXPORTS_DIR`, `VE_EARLY_TURNS` (6), `VE_ANNOTATOR_MODEL`
(`claude-sonnet-4-6`), `VE_JUDGE_MODEL` (`gpt-5.4-mini`). See `.env.example`.

---

## Contents

- `voice_eval/` — loader, windows, annotator, scorer, metrics, report, cli, llmio
- `curve.py` — sweeps the opening-window size to find *where* prediction becomes reliable (it's
  mid-to-late call, ~turn 12–13, not the opening)
- `escalation_probe.py`, `postcall_probe.py`, `model_robustness.py` — the follow-on probes
- `FINDINGS_phase1.md` — the authoritative findings record, written to be re-read with no prior context
- `tests/` — `test_boundary` (enforces the export boundary), `test_scorer`

---

## The Reusable Part

The headline finding is specific to this premise, but the *method* generalizes: a cheap, blind,
cross-family validation gate you run **before** building, to kill premises that won't survive contact
with a strong adversary. For ~$10 it prevented building a realtime copilot the data says wouldn't
work. That pattern is the lasting IP here.
