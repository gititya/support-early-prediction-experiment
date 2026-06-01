"""#1 — Generator-model robustness probe.

Question: are the Phase-1 findings (the predictability curve, ~turn-13 crossover) an artifact of
the small author model (gpt-5.4-mini), or do they hold when a frontier model authors the calls?

This computes a fresh predictability curve on whatever export VE_EXPORTS_DIR points at, then lays it
beside the baseline 5.4-mini curve (runs/latest/curve.csv) and applies the decision rule:

  ROBUST  -> crossover turn moves < 2 turns AND full accuracy stays >= 88%  -> no full retest.
  ARTIFACT-> otherwise -> regenerate the full set with the frontier model and re-run the suite.

Predictor stays Claude, judge stays GPT (cross-family rule unchanged). Unlike curve.py this reuses
nothing from runs/latest — every window is annotated + judged fresh, because the new export has no
cached gate run.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from voice_eval.annotator import annotate
from voice_eval.loader import exports_dir, list_cases, load_ground_truth, load_transcript
from voice_eval.scorer import _judge_root_cause

WINDOWS = [6, 10, 14, 18]  # plus 'full'
BASELINE_CURVE = Path("runs/latest/curve.csv")


def _curve_from_export(ex) -> tuple[list[dict], dict]:
    cases = list_cases(ex)
    rows = []
    for case in cases:
        cid = case["case_id"]
        turns = load_transcript(cid, ex)
        actual = load_ground_truth(cid, ex)["actual_root_cause"]
        n = len(turns)
        for w in WINDOWS:
            pred = annotate(turns[:w])
            v = _judge_root_cause(pred.get("predicted_root_cause", ""), actual, None, None)
            rows.append({"case_id": cid, "window": w, "match": bool(v["match"])})
            print(f"{cid} w={w}: {'HIT' if v['match'] else 'miss'}")
        predf = annotate(turns)
        vf = _judge_root_cause(predf.get("predicted_root_cause", ""), actual, None, None)
        rows.append({"case_id": cid, "window": "full", "match": bool(vf["match"])})
    acc = {}
    for p in WINDOWS + ["full"]:
        sub = [r for r in rows if r["window"] == p]
        acc[p] = sum(r["match"] for r in sub) / len(sub) if sub else 0.0
    return rows, acc


def _crossover(acc: dict) -> float | None:
    """Linear-interpolated turn where accuracy first crosses 0.60."""
    pts = [(w, acc[w]) for w in WINDOWS]
    for (w0, a0), (w1, a1) in zip(pts, pts[1:]):
        if a0 < 0.60 <= a1:
            return w0 + (0.60 - a0) / (a1 - a0) * (w1 - w0)
    return None if pts[-1][1] < 0.60 else float(WINDOWS[0])


def _baseline_acc() -> dict | None:
    if not BASELINE_CURVE.exists():
        return None
    rows = list(csv.DictReader(BASELINE_CURVE.open()))
    acc = {}
    for p in WINDOWS:
        sub = [r for r in rows if r["window"] == str(p)]
        if sub:
            acc[p] = sum(r["match"] == "True" for r in sub) / len(sub)
    full = [r for r in rows if r.get("window_label") == "full"]
    if full:
        acc["full"] = sum(r["match"] == "True" for r in full) / len(full)
    return acc


def main():
    tag = os.getenv("VE_RUN_TAG", "gpt55")
    out_dir = Path(f"runs/{tag}")
    out_dir.mkdir(parents=True, exist_ok=True)
    ex = exports_dir()

    rows, acc = _curve_from_export(ex)
    with (out_dir / "curve.csv").open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["case_id", "window", "match"])
        wr.writeheader()
        wr.writerows(rows)

    base = _baseline_acc()
    print(f"\n{'window':>7} | {'5.5 author':>11} | {'5.4-mini base':>13}")
    for p in WINDOWS + ["full"]:
        b = f"{base[p]:.0%}" if base and p in base else "n/a"
        print(f"{str(p):>7} | {acc[p]:>11.0%} | {b:>13}")

    new_x = _crossover(acc)
    base_x = _crossover(base) if base else None
    print(f"\ncrossover (60%):  5.5 author = {new_x}  |  5.4-mini base = {base_x}")

    # decision rule
    full_ok = acc["full"] >= 0.88
    shift_ok = (new_x is not None and base_x is not None and abs(new_x - base_x) < 2)
    verdict = "ROBUST — no full retest needed" if (full_ok and shift_ok) else \
        "ARTIFACT RISK — regenerate full set with frontier model and re-run the suite"
    print(f"\nfull accuracy >= 88%: {full_ok} ({acc['full']:.0%})")
    print(f"crossover shift < 2 turns: {shift_ok}")
    print(f"VERDICT: {verdict}")
    (out_dir / "robustness_verdict.txt").write_text(
        f"5.5 curve: {acc}\nbaseline: {base}\ncrossover 5.5={new_x} base={base_x}\nverdict: {verdict}\n")


if __name__ == "__main__":
    main()
