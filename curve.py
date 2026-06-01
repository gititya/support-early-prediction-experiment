"""Predictability curve: specific root-cause accuracy as a function of how many
opening turns the blind annotator sees. Reuses the harness annotator (Claude) and
judge (GPT). Windows 6 and 'full' are reused from runs/latest; intermediate windows
are annotated + judged fresh. Boundary respected: annotate() reads transcripts only;
the judge compares against ground_truth via scorer._judge_root_cause."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from voice_eval.annotator import annotate
from voice_eval.loader import exports_dir, list_cases, load_ground_truth, load_transcript
from voice_eval.scorer import _judge_root_cause

WINDOWS = [10, 14, 18]  # 6 and full come from the existing run
RUN_DIR = Path("runs/latest")
OUT = Path("runs/latest/curve.csv")


def main() -> None:
    ex = exports_dir()
    cases = list_cases(ex)
    leak = {c["case_id"]: c["leakage_status"] for c in cases}

    # reuse the existing run for the 6-turn (early) and full endpoints
    scores = {r["case_id"]: r for r in json.loads((RUN_DIR / "scores.json").read_text())}

    rows = []  # one row per (case, window) with a boolean match
    for case in cases:
        cid = case["case_id"]
        turns = load_transcript(cid, ex)
        actual = load_ground_truth(cid, ex)["actual_root_cause"]
        n_turns = len(turns)

        # endpoint 6 (reuse)
        rows.append({"case_id": cid, "window": 6, "n_turns": n_turns,
                     "leakage_status": leak[cid], "match": bool(scores[cid]["early_specific_match"])})

        # intermediate windows (fresh)
        for w in WINDOWS:
            pred = annotate(turns[:w])
            verdict = _judge_root_cause(pred.get("predicted_root_cause", ""), actual, None, None)
            rows.append({"case_id": cid, "window": w, "n_turns": n_turns,
                         "leakage_status": leak[cid], "match": bool(verdict["match"])})
            print(f"{cid} w={w}: {'HIT' if verdict['match'] else 'miss'}")

        # endpoint full (reuse)
        rows.append({"case_id": cid, "window": n_turns, "window_label": "full", "n_turns": n_turns,
                     "leakage_status": leak[cid], "match": bool(scores[cid]["full_specific_match"])})

    with OUT.open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["case_id", "window", "window_label", "n_turns",
                                           "leakage_status", "match"])
        wr.writeheader()
        for r in rows:
            wr.writerow({"window_label": "", **r})
    print(f"\nwrote {OUT} ({len(rows)} rows)")

    # accuracy per window, all-51 and PASS-only
    points = [6] + WINDOWS + ["full"]
    print("\nwindow |  all-51        | PASS-only")
    for p in points:
        sub = [r for r in rows if (r.get("window_label") == "full" if p == "full" else r["window"] == p)]
        pas = [r for r in sub if r["leakage_status"] == "PASS"]
        def acc(s):
            return f"{sum(r['match'] for r in s)/len(s):.0%} ({sum(r['match'] for r in s)}/{len(s)})" if s else "n=0"
        print(f"{str(p):>6} | {acc(sub):>13} | {acc(pas)}")


if __name__ == "__main__":
    main()
