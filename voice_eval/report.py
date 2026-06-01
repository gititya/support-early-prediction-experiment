from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

SCORE_FIELDS = [
    "case_id",
    "scenario_type",
    "difficulty",
    "leakage_status",
    "category_match",
    "early_specific_match",
    "full_specific_match",
    "next_question_useful",
    "early_confidence",
    "predicted_root_cause_early",
    "actual_root_cause",
    "early_specific_reason",
]


def write_scores_csv(rows: list[dict[str, Any]], run_dir: Path) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "scores.csv"
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SCORE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_summary_md(summary: dict[str, Any], rows: list[dict[str, Any]], run_dir: Path) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "summary.md"
    verdict = "PASS ✅" if summary["gate_pass"] else "FAIL ❌"
    lines: list[str] = []
    lines.append("# Predictability Validation Gate")
    lines.append("")
    lines.append(f"**Gate (early specific root-cause accuracy ≥ {summary['gate_threshold']:.0%}): {verdict}**")
    lines.append("")
    lines.append(f"- Calls scored: {summary['n_total']} (gate set, excl. leakage FAIL: {summary['n_gate']})")
    lines.append(f"- **Early specific-root-cause accuracy: {summary['early_specific_accuracy']:.0%}** ← the gate")
    lines.append(f"- Full-transcript specific accuracy: {summary['full_specific_accuracy']:.0%}")
    lines.append(f"- Early-vs-full delta (signal lost by going early): {summary['early_vs_full_delta']:.0%}")
    lines.append(f"- Broad-category accuracy (sanity check): {summary['broad_category_accuracy']:.0%}")
    lines.append(f"- Next-question usefulness rate: {summary['next_question_useful_rate']:.0%}")
    if summary["excluded_leakage_fail"]:
        lines.append(f"- Excluded (leakage FAIL): {', '.join(summary['excluded_leakage_fail'])}")
    if summary["flagged_leakage_warning"]:
        lines.append(f"- Flagged (leakage WARNING): {', '.join(summary['flagged_leakage_warning'])}")
    lines.append("")

    lines.append("## By difficulty")
    lines.append("")
    lines.append("| difficulty | n | early specific accuracy |")
    lines.append("| --- | --- | --- |")
    for name, stats in summary["by_difficulty"].items():
        lines.append(f"| {name} | {stats['n']} | {stats['early_specific_accuracy']:.0%} |")
    lines.append("")

    lines.append("## By scenario")
    lines.append("")
    lines.append("| scenario | n | early specific accuracy |")
    lines.append("| --- | --- | --- |")
    for name, stats in summary["by_scenario"].items():
        lines.append(f"| {name} | {stats['n']} | {stats['early_specific_accuracy']:.0%} |")
    lines.append("")

    misses = [r for r in rows if not r.get("early_specific_match") and r.get("leakage_status") != "FAIL"]
    if misses:
        lines.append("## Early misses (error analysis)")
        lines.append("")
        for r in misses:
            lines.append(f"- **{r['case_id']}** ({r.get('difficulty')}/{r.get('scenario_type')})")
            lines.append(f"  - predicted: {r.get('predicted_root_cause_early')}")
            lines.append(f"  - actual: {r.get('actual_root_cause')}")
            lines.append(f"  - judge: {r.get('early_specific_reason')}")
        lines.append("")

    path.write_text("\n".join(lines))
    return path
