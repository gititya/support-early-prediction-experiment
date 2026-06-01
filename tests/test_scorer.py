from __future__ import annotations

from voice_eval.metrics import GATE_THRESHOLD, aggregate
from voice_eval.scorer import _overlap_match


def test_overlap_match_detects_shared_root_cause():
    result = _overlap_match(
        "SSO group membership required before app roles apply",
        "A policy now requires SSO group membership before app roles apply",
    )
    assert result["match"] is True


def test_overlap_match_rejects_unrelated():
    result = _overlap_match(
        "billing plan downgrade removed seats",
        "SSO group membership required before app roles apply",
    )
    assert result["match"] is False


def test_aggregate_gate_pass_excludes_leakage_fail():
    rows = [
        {"case_id": "a", "difficulty": "easy", "scenario_type": "permissions_access",
         "leakage_status": "PASS", "category_match": True, "early_specific_match": True,
         "full_specific_match": True, "next_question_useful": True},
        {"case_id": "b", "difficulty": "hard", "scenario_type": "permissions_access",
         "leakage_status": "FAIL", "category_match": True, "early_specific_match": False,
         "full_specific_match": True, "next_question_useful": False},
    ]
    summary = aggregate(rows)
    assert summary["n_gate"] == 1
    assert summary["excluded_leakage_fail"] == ["b"]
    assert summary["early_specific_accuracy"] == 1.0
    assert summary["gate_pass"] is (1.0 >= GATE_THRESHOLD)
