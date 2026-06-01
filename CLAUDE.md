# CLAUDE.md — support-voice (project)

Project-level context. Append-only. Session phase state lives in `SKILL.md` (read it first).

## What this project is

Predictability validation harness (Python) for the Voice Support Intelligence Copilot.
Reads the support-call-generator's exports and runs a blind, cross-family scorer to decide
whether the copilot's core premise holds before building any realtime infra. See `PRD_1st.md`,
`VOICEAGENT_ARCHITECTURE_NOTE.md`, and `initial_research/MARS-adverserial.md`.

**OUTCOME (2026-06-01): Phase 1 COMPLETE → STOP.** The realtime speculative-copilot premise is DEAD:
early specific root-cause prediction collapses to 2% (migration 0%) on frontier-authored (`gpt-5.5`)
synthetic calls, and early escalation prediction is degenerate. This is the valuable, defensible
insight. The post-call/handoff record is **UNPROVEN + commercially undifferentiated** (Codex review
corrected it down from "survived" — n=12, uncalibrated judge, synthetic). Recommend not building
unless real-call data + real intent appear. Reusable method banked at Obsidian
`methods/predictability-validation-pattern.md`. Authoritative writeup: `FINDINGS_phase1.md` §11–13;
resume/next-steps in `SKILL.md`.

## Hard constraints

- **Do not reimplement the generator.** It is a dependency (GitHub `gititya/support-call-generator`,
  installed via git in `pyproject.toml`). Only consume its exports / CLI.
- **Export boundary is sacred.** The annotator path may load `transcripts/` only; only
  `scorer.py` may open `ground_truth/`. The boundary test enforces this.
- **Cross-family separation:** GPT authors calls, **Claude** is the blind annotator, **GPT** is
  the match judge. Never let the predictor and judge be the same model.
- **Gate metric = specific root cause, not broad category** (category ≈ scenario type, obvious
  from turn 1). Threshold 60% (`metrics.GATE_THRESHOLD`).
- Python, no TypeScript (global rule).

## How to run

```bash
source .venv/bin/activate
# keys loaded inline from Keychain so secrets never print — see SKILL.md BLOCKER for the
# current account/service to use (my-openai-key is dead; valid key under mars account).
export OPENAI_API_KEY="$(security find-generic-password -a <account> -s <service> -w)"
export ANTHROPIC_API_KEY="$(security find-generic-password -a <account> -s <service> -w)"
python -m voice_eval run            # predict -> score -> report into runs/latest
pytest -q                          # 6 tests
```

Env: `VE_EXPORTS_DIR` (default `../support-call-generator/exports/latest`),
`VE_EARLY_TURNS` (6), `VE_ANNOTATOR_MODEL` (`claude-sonnet-4-6`), `VE_JUDGE_MODEL`
(`gpt-5.4-mini`). See `.env.example`.

## Layout

`voice_eval/`: loader, windows, annotator, scorer, metrics, report, cli, llmio.
`tests/`: test_boundary, test_scorer. `runs/` (gitignored) holds outputs.
Generator sibling: `../support-call-generator` (exports the dataset; `exports/` is gitignored
there, so sample calls are local-only).

## Security notes

- Keys from macOS Keychain only; never written to disk or printed. `.env` is gitignored.
- No Firebase, no multi-user data, no secrets in code.
