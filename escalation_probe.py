"""a1 — Early escalation detection probe.

Sharpened question (per the 2026 market reality where reactive frustration/keyword triggers
are commoditized): not "can it detect escalation" but "does the copilot flag escalation EARLIER
than a reactive keyword baseline, and carry a usable handoff package at the moment it fires."

Cross-family, like the rest of the harness: Claude predicts (blind, early window), GPT judges the
handoff package. Truth = ground_truth.resolution_type in {escalated, handoff}. This is a probe that
reads ground_truth, so it lives outside voice_eval and does not affect the early-prediction
boundary test.

Metrics:
  A. precision / recall / F1 of will_escalate at each early window (6/10/14).
  B. head start vs gold: turns between the model's first fire and the gold escalation turn.
  C. head start vs a reactive keyword baseline (the differentiated claim).
  D. handoff-package usefulness at fire time (GPT-judged).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from anthropic import Anthropic
from openai import OpenAI

from voice_eval.llmio import parse_json
from voice_eval.loader import exports_dir, list_cases, load_ground_truth, load_transcript
from voice_eval.windows import render_turns

WINDOWS = [6, 10, 14]
OUT = Path("runs/latest/escalation_probe.json")

# Reactive baseline: a customer-side cue a keyword/sentiment trigger would fire on. Deliberately
# generous so the baseline is a fair (not strawman) comparison — these are the things commodity
# triggers already catch.
BASELINE_CUES = [
    "speak to a human", "talk to a human", "real person", "manager", "supervisor",
    "escalate", "escalation", "ridiculous", "unacceptable", "frustrat", "angry",
    "cancel", "refund", "this is a joke", "fed up", "losing patience", "deadline",
    "urgent", "asap", "not good enough", "waste of time", "disappointed",
]

ANNOTATE_SYS = """You are a blind support-call analyst. You see only an early fragment of a B2B \
SaaS support call. From this fragment alone, predict whether this call will END UP escalated or \
handed off to a human agent (tier-2 / engineering / a specialist), and produce the handoff brief a \
human would need if it were escalated right now. You have NOT seen the rest of the call or any \
answer key. Return only valid JSON, no markdown fences."""

ANNOTATE_PROMPT = """Opening fragment of a support call:
{transcript}

Return JSON with exactly:
{{
  "will_escalate": true/false,
  "escalation_confidence": 0.0,
  "escalation_reason": "one sentence on why it will or will not escalate",
  "current_hypothesis": "best root-cause guess so far, one sentence",
  "what_been_tried": ["troubleshooting steps already attempted in the fragment"],
  "customer_state": "one sentence on the customer's current state / sentiment"
}}"""

JUDGE_SYS = """You grade the handoff brief an AI produced mid-call, judging whether a human agent \
picking up the call cold could actually use it. Be conservative. Return only valid JSON, no \
markdown fences."""

JUDGE_PROMPT = """A human agent is about to take over this escalated call. The AI handed them this brief:
- current_hypothesis: {hyp}
- what_been_tried: {tried}
- customer_state: {state}

For reference, the true root cause (hidden from the AI) was: {actual}

Grade and return JSON:
{{
  "usable_handoff": true/false,   // could the agent start working immediately without re-asking the basics?
  "hypothesis_on_track": true/false,  // is current_hypothesis pointing the right direction (need not be exact)?
  "reason": "one sentence"
}}"""


def _gold_escalation_turn(gt: dict) -> int | None:
    """Turn the gold timeline marks the actual escalation, if any."""
    for e in gt.get("escalation_timeline", []) or []:
        if e.get("type") == "escalation":
            return e.get("turn")
    return None


def _baseline_fire_turn(turns: list[dict]) -> int | None:
    """First customer turn carrying a frustration / human-request cue (reactive trigger)."""
    for t in turns:
        if t.get("speaker") == "customer" and any(c in t["text"].lower() for c in BASELINE_CUES):
            return t["turn"]
    return None


def _claude_annotate(turns):
    c = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    r = c.messages.create(
        model=os.getenv("VE_ANNOTATOR_MODEL", "claude-sonnet-4-6"),
        max_tokens=1024,
        system=[{"type": "text", "text": ANNOTATE_SYS}],
        messages=[{"role": "user", "content": ANNOTATE_PROMPT.format(transcript=render_turns(turns))}],
    )
    text = "".join(b.text for b in r.content if b.type == "text")
    return parse_json(text)


def _gpt_judge_package(actual, ann):
    c = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    prompt = JUDGE_PROMPT.format(
        hyp=ann.get("current_hypothesis", ""), tried=json.dumps(ann.get("what_been_tried", [])),
        state=ann.get("customer_state", ""), actual=actual,
    )
    r = c.responses.create(
        model=os.getenv("VE_JUDGE_MODEL", "gpt-5.4-mini"),
        input=[{"role": "system", "content": JUDGE_SYS}, {"role": "user", "content": prompt}],
    )
    return parse_json(r.output_text)


def main():
    ex = exports_dir()
    cases = list_cases(ex)
    results = []

    for c in cases:
        cid = c["case_id"]
        turns = load_transcript(cid, ex)
        gt = load_ground_truth(cid, ex)
        truth = gt.get("resolution_type") in ("escalated", "handoff")
        gold_turn = _gold_escalation_turn(gt)
        baseline_turn = _baseline_fire_turn(turns)

        per_window = {}
        fire_window = None
        for w in WINDOWS:
            ann = _claude_annotate(turns[:w])
            fired = bool(ann.get("will_escalate"))
            per_window[w] = {"fired": fired, "confidence": ann.get("escalation_confidence"),
                             "annotation": ann}
            if fired and fire_window is None:
                fire_window = w

        # Judge the handoff package at the fire window (only meaningful once it decides to escalate).
        package = None
        if fire_window is not None:
            package = _gpt_judge_package(gt["actual_root_cause"], per_window[fire_window]["annotation"])

        results.append({
            "case_id": cid, "scenario": c["scenario_type"], "resolution_type": gt.get("resolution_type"),
            "truth_escalated": truth, "gold_escalation_turn": gold_turn,
            "baseline_fire_turn": baseline_turn, "model_fire_window": fire_window,
            "per_window": {str(w): {"fired": v["fired"], "confidence": v["confidence"]}
                           for w, v in per_window.items()},
            "package": package,
        })
        flag = "ESC" if truth else "---"
        print(f"{cid} [{flag}] fire_window={fire_window} gold={gold_turn} baseline={baseline_turn}")

    OUT.write_text(json.dumps(results, indent=2))
    _report(results)


def _report(results):
    n = len(results)
    pos = [r for r in results if r["truth_escalated"]]
    print(f"\nwrote {OUT}  (n={n}, escalated truth={len(pos)})")

    # A. precision / recall / F1 per window
    print("\nwindow |  precision |  recall |    F1   | fired")
    for w in WINDOWS:
        tp = sum(1 for r in results if r["per_window"][str(w)]["fired"] and r["truth_escalated"])
        fp = sum(1 for r in results if r["per_window"][str(w)]["fired"] and not r["truth_escalated"])
        fn = sum(1 for r in results if not r["per_window"][str(w)]["fired"] and r["truth_escalated"])
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        print(f"{w:>6} | {prec:>9.0%} | {rec:>6.0%} | {f1:>6.0%} | {tp + fp}")

    # B+C. head start, on true escalations the model caught
    caught = [r for r in pos if r["model_fire_window"] is not None]
    vs_gold = [r["gold_escalation_turn"] - r["model_fire_window"]
               for r in caught if r["gold_escalation_turn"] is not None]
    vs_base = [r["baseline_fire_turn"] - r["model_fire_window"]
               for r in caught if r["baseline_fire_turn"] is not None]
    earlier_than_base = sum(1 for d in vs_base if d > 0)
    print(f"\ntrue escalations caught: {len(caught)}/{len(pos)}")
    if vs_gold:
        print(f"head start vs gold escalation turn: median {sorted(vs_gold)[len(vs_gold)//2]}, "
              f"mean {sum(vs_gold)/len(vs_gold):.1f} turns (n={len(vs_gold)})")
    if vs_base:
        print(f"head start vs reactive keyword baseline: median {sorted(vs_base)[len(vs_base)//2]}, "
              f"mean {sum(vs_base)/len(vs_base):.1f} turns; fired earlier than baseline in "
              f"{earlier_than_base}/{len(vs_base)} caught calls")
    base_never = sum(1 for r in pos if r["baseline_fire_turn"] is None)
    print(f"escalations the keyword baseline would entirely MISS (no cue): {base_never}/{len(pos)}")

    # D. handoff-package usefulness, among calls the model chose to escalate
    judged = [r for r in results if r["package"]]
    if judged:
        usable = sum(1 for r in judged if r["package"].get("usable_handoff")) / len(judged)
        ontrack = sum(1 for r in judged if r["package"].get("hypothesis_on_track")) / len(judged)
        print(f"\nhandoff package (n={len(judged)} fired): usable {usable:.0%}, hypothesis on track {ontrack:.0%}")


if __name__ == "__main__":
    main()
