from __future__ import annotations

import inspect

from voice_eval import annotator
from voice_eval.annotator import build_prompt
from voice_eval.windows import early_window

GROUND_TRUTH_FIELDS = [
    "actual_root_cause",
    "false_leads",
    "best_diagnostic_questions",
    "issue_path",
    "late_reveal_facts",
    "expected_timeline",
    "misleading_evidence",
]


def test_annotator_prompt_contains_no_ground_truth_fields():
    turns = [
        {"turn": 1, "speaker": "customer", "text": "Two users lost access after our migration."},
        {"turn": 2, "speaker": "agent", "text": "Is it all users or some?"},
    ]
    prompt = build_prompt(early_window(turns, 6))
    lowered = prompt.lower()
    for field in GROUND_TRUTH_FIELDS:
        assert field not in lowered


def test_annotator_module_never_imports_ground_truth_loader():
    src = inspect.getsource(annotator)
    assert "load_ground_truth" not in src
    assert "ground_truth" not in src


def test_offline_annotation_runs_without_keys():
    turns = [{"turn": 1, "speaker": "customer", "text": "We can't log in after enabling SSO."}]
    result = annotator.annotate(turns, use_llm=False)
    assert result["predicted_category"] == "permissions_access"
    assert set(result) == {
        "predicted_category",
        "predicted_root_cause",
        "confidence",
        "earliest_identifiable_turn",
        "next_diagnostic_question",
    }
