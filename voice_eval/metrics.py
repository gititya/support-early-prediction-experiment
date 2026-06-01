from __future__ import annotations

from collections import defaultdict
from typing import Any

GATE_THRESHOLD = 0.60


def _rate(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return sum(1 for r in rows if r.get(key)) / len(rows)


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute gate metrics. Leakage=FAIL calls are excluded from the gate set."""
    gate_rows = [r for r in rows if r.get("leakage_status") != "FAIL"]
    excluded = [r["case_id"] for r in rows if r.get("leakage_status") == "FAIL"]
    warned = [r["case_id"] for r in rows if r.get("leakage_status") == "WARNING"]

    early = _rate(gate_rows, "early_specific_match")
    full = _rate(gate_rows, "full_specific_match")

    summary: dict[str, Any] = {
        "n_total": len(rows),
        "n_gate": len(gate_rows),
        "excluded_leakage_fail": excluded,
        "flagged_leakage_warning": warned,
        "early_specific_accuracy": early,
        "full_specific_accuracy": full,
        "early_vs_full_delta": full - early,
        "broad_category_accuracy": _rate(gate_rows, "category_match"),
        "next_question_useful_rate": _rate(gate_rows, "next_question_useful"),
        "gate_threshold": GATE_THRESHOLD,
        "gate_pass": early >= GATE_THRESHOLD,
        "by_difficulty": _breakdown(gate_rows, "difficulty"),
        "by_scenario": _breakdown(gate_rows, "scenario_type"),
    }
    return summary


def _breakdown(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[str(r.get(key))].append(r)
    return {
        name: {"n": len(group), "early_specific_accuracy": _rate(group, "early_specific_match")}
        for name, group in sorted(groups.items())
    }
