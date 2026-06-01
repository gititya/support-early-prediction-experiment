from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from voice_eval.annotator import annotate
from voice_eval.loader import exports_dir, list_cases, load_transcript
from voice_eval.metrics import aggregate
from voice_eval.report import write_scores_csv, write_summary_md
from voice_eval.scorer import score_case
from voice_eval.windows import early_window, full_window


def _run_dir(args) -> Path:
    return Path(args.run_dir)


def cmd_predict(args) -> None:
    """Blind annotation. Reads transcripts ONLY; never opens ground_truth."""
    exports = exports_dir(args.exports_dir)
    cases = list_cases(exports)
    predictions: dict[str, dict] = {}
    for case in cases:
        case_id = case["case_id"]
        turns = load_transcript(case_id, exports)
        predictions[case_id] = {
            "early": annotate(early_window(turns, args.early_turns)),
            "full": annotate(full_window(turns)),
        }
        print(f"predicted {case_id}", file=sys.stderr)
    run_dir = _run_dir(args)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "predictions.json").write_text(json.dumps(predictions, indent=2))
    print(f"wrote {run_dir / 'predictions.json'} ({len(predictions)} cases)")


def cmd_score(args) -> None:
    exports = exports_dir(args.exports_dir)
    run_dir = _run_dir(args)
    predictions = json.loads((run_dir / "predictions.json").read_text())
    rows = []
    for case_id, pred in predictions.items():
        rows.append(score_case(case_id, pred["early"], pred["full"], exports))
        print(f"scored {case_id}", file=sys.stderr)
    (run_dir / "scores.json").write_text(json.dumps(rows, indent=2))
    csv_path = write_scores_csv(rows, run_dir)
    print(f"wrote {csv_path} ({len(rows)} rows)")


def cmd_report(args) -> None:
    run_dir = _run_dir(args)
    rows = json.loads((run_dir / "scores.json").read_text())
    summary = aggregate(rows)
    summary_path = write_summary_md(summary, rows, run_dir)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    verdict = "PASS" if summary["gate_pass"] else "FAIL"
    print(f"wrote {summary_path}")
    print(
        f"GATE {verdict}: early specific accuracy "
        f"{summary['early_specific_accuracy']:.0%} (threshold {summary['gate_threshold']:.0%}, "
        f"n={summary['n_gate']})"
    )


def cmd_run(args) -> None:
    cmd_predict(args)
    cmd_score(args)
    cmd_report(args)


def main() -> None:
    parser = argparse.ArgumentParser(prog="voice_eval")
    parser.add_argument("--exports-dir", default=None, help="generator export dir (default: VE_EXPORTS_DIR)")
    parser.add_argument("--run-dir", default="runs/latest", help="output dir for this run")
    parser.add_argument("--early-turns", type=int, default=None, help="early-window size (default: VE_EARLY_TURNS=6)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("predict").set_defaults(func=cmd_predict)
    sub.add_parser("score").set_defaults(func=cmd_score)
    sub.add_parser("report").set_defaults(func=cmd_report)
    sub.add_parser("run").set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)
