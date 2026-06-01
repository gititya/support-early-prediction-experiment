"""Post-call record probe (PRD Output #2 / success state line 326: 'operational reasoning
beyond naive summarization'). For a sample of calls, Claude reads the FULL transcript and
produces a structured operational record; GPT judges it against the hidden ground truth on
three dimensions: final-hypothesis correctness, recall of failed/abandoned troubleshooting
paths, and correct escalation flagging. This is a probe, not a gate — runs on a small sample.

Boundary note: this deliberately operates on the FULL transcript and the ground_truth, i.e.
post-call analysis, not the blind early-prediction path. Kept separate from voice_eval so the
early-prediction boundary test is unaffected."""

from __future__ import annotations

import json
import os
from pathlib import Path

from anthropic import Anthropic
from openai import OpenAI

from voice_eval.loader import exports_dir, list_cases, load_ground_truth, load_transcript
from voice_eval.windows import render_turns

SAMPLE_PER_SCENARIO = 4
OUT = Path("runs/latest/postcall_probe.json")

RECORD_SYS = """You produce a structured post-call operational record for a B2B SaaS support call.
You are given the full transcript. Do not summarize narratively. Extract operational structure.
Return only valid JSON, no markdown fences."""

RECORD_PROMPT = """Full support-call transcript:
{transcript}

Return JSON with exactly:
{{
  "final_hypothesis": "single best root-cause statement, one sentence",
  "failed_or_abandoned_paths": ["troubleshooting directions that were tried and dropped"],
  "escalated": true/false,
  "escalation_reason": "one sentence or empty",
  "unresolved_blockers": ["operational blockers still open at call end"],
  "operational_unknowns": ["things still unknown that matter operationally"]
}}"""

JUDGE_SYS = """You grade a generated post-call record against a hidden ground-truth answer key.
Be conservative: only credit a match on genuine operational equivalence. Return only valid JSON."""

JUDGE_PROMPT = """ANSWER KEY (hidden ground truth):
- actual_root_cause: {actual}
- abandoned_troubleshooting_paths: {abandoned}
- escalation actually occurred: {esc_truth}

GENERATED RECORD:
- final_hypothesis: {fh}
- failed_or_abandoned_paths: {fp}
- escalated: {esc_pred}

Grade and return JSON:
{{
  "hypothesis_correct": true/false,
  "abandoned_paths_recall": 0.0,   // fraction of answer-key abandoned paths the record captured (0-1)
  "escalation_correct": true/false,
  "beyond_summary": true/false     // does the record show operational reasoning beyond naive summarization?
}}"""


def _claude_record(turns):
    c = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    r = c.messages.create(
        model=os.getenv("VE_ANNOTATOR_MODEL", "claude-sonnet-4-6"),
        max_tokens=1024,
        system=[{"type": "text", "text": RECORD_SYS}],
        messages=[{"role": "user", "content": RECORD_PROMPT.format(transcript=render_turns(turns))}],
    )
    text = "".join(b.text for b in r.content if b.type == "text")
    return json.loads(text)


def _gpt_judge(actual, abandoned, esc_truth, rec):
    c = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    prompt = JUDGE_PROMPT.format(
        actual=actual, abandoned=json.dumps(abandoned), esc_truth=esc_truth,
        fh=rec.get("final_hypothesis", ""), fp=json.dumps(rec.get("failed_or_abandoned_paths", [])),
        esc_pred=rec.get("escalated", False),
    )
    r = c.responses.create(
        model=os.getenv("VE_JUDGE_MODEL", "gpt-5.4-mini"),
        input=[{"role": "system", "content": JUDGE_SYS}, {"role": "user", "content": prompt}],
    )
    return json.loads(r.output_text)


def main():
    ex = exports_dir()
    cases = list_cases(ex)
    by_scen = {}
    for c in cases:
        by_scen.setdefault(c["scenario_type"], []).append(c)
    sample = [c for cs in by_scen.values() for c in cs[:SAMPLE_PER_SCENARIO]]

    results = []
    for c in sample:
        cid = c["case_id"]
        turns = load_transcript(cid, ex)
        gt = load_ground_truth(cid, ex)
        rec = _claude_record(turns)
        esc_truth = bool(gt.get("escalation_timeline"))
        verdict = _gpt_judge(gt["actual_root_cause"], gt.get("abandoned_troubleshooting_paths", []),
                             esc_truth, rec)
        results.append({"case_id": cid, "scenario": c["scenario_type"], **verdict})
        print(f"{cid} ({c['scenario_type']}): hypo={verdict['hypothesis_correct']} "
              f"recall={verdict['abandoned_paths_recall']:.2f} esc={verdict['escalation_correct']} "
              f"beyond_summary={verdict['beyond_summary']}")

    OUT.write_text(json.dumps(results, indent=2))
    n = len(results)
    print(f"\nwrote {OUT} (n={n})")
    hc = sum(r["hypothesis_correct"] for r in results) / n
    ar = sum(r["abandoned_paths_recall"] for r in results) / n
    ec = sum(r["escalation_correct"] for r in results) / n
    bs = sum(r["beyond_summary"] for r in results) / n
    print(f"hypothesis correct:        {hc:.0%}")
    print(f"abandoned-path recall:     {ar:.0%}")
    print(f"escalation flagged right:  {ec:.0%}")
    print(f"beyond naive summary:      {bs:.0%}")


if __name__ == "__main__":
    main()
