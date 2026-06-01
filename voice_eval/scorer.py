from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from voice_eval.llmio import parse_json
from voice_eval.loader import load_ground_truth, load_leakage

JUDGE_SYSTEM = """You are a strict evaluation judge for a support-call predictability study. \
You compare a prediction against a hidden answer key and decide semantic equivalence, not exact \
wording. Be conservative: only call it a match if the prediction captures the same operational \
root cause. Return only valid JSON. Do not include markdown fences."""


def score_case(
    case_id: str,
    pred_early: dict[str, Any],
    pred_full: dict[str, Any],
    exports: Path,
    judge_model: str | None = None,
    use_llm: bool | None = None,
) -> dict[str, Any]:
    gt = load_ground_truth(case_id, exports)
    leakage = load_leakage(case_id, exports)
    actual = gt["actual_root_cause"]
    gold_questions = gt.get("best_diagnostic_questions", [])

    category_match = pred_early.get("predicted_category") == gt.get("root_cause_category")
    early_specific = _judge_root_cause(pred_early.get("predicted_root_cause", ""), actual, judge_model, use_llm)
    full_specific = _judge_root_cause(pred_full.get("predicted_root_cause", ""), actual, judge_model, use_llm)
    question_useful = _judge_question(
        pred_early.get("next_diagnostic_question", ""), gold_questions, judge_model, use_llm
    )

    return {
        "case_id": case_id,
        "scenario_type": gt.get("root_cause_category"),
        "difficulty": gt.get("difficulty_metadata", {}).get("difficulty"),
        "leakage_status": leakage.get("status", "PASS"),
        "category_match": category_match,
        "early_specific_match": early_specific["match"],
        "full_specific_match": full_specific["match"],
        "next_question_useful": question_useful["match"],
        "early_confidence": pred_early.get("confidence"),
        "predicted_root_cause_early": pred_early.get("predicted_root_cause"),
        "actual_root_cause": actual,
        "early_specific_reason": early_specific.get("reason", ""),
    }


def _judge_root_cause(prediction: str, actual: str, model: str | None, use_llm: bool | None) -> dict[str, Any]:
    if not prediction:
        return {"match": False, "reason": "empty prediction"}
    if use_llm is None:
        use_llm = bool(os.getenv("OPENAI_API_KEY"))
    if not use_llm:
        return _overlap_match(prediction, actual)
    prompt = f"""Hidden answer-key root cause:
{actual}

Prediction made from only the opening of the call:
{prediction}

Does the prediction identify the same operational root cause as the answer key?
Return JSON: {{"match": true/false, "reason": "one sentence"}}"""
    return _judge_call(prompt, model)


def _judge_question(prediction: str, gold_questions: list[str], model: str | None, use_llm: bool | None) -> dict[str, Any]:
    if not prediction:
        return {"match": False, "reason": "empty question"}
    if use_llm is None:
        use_llm = bool(os.getenv("OPENAI_API_KEY"))
    if not use_llm:
        joined = " ".join(gold_questions)
        return _overlap_match(prediction, joined)
    listed = "\n".join(f"- {q}" for q in gold_questions)
    prompt = f"""Gold list of useful next diagnostic questions for this call:
{listed}

Question the analyst proposed early in the call:
{prediction}

Is the proposed question operationally equivalent to, or clearly among, the gold useful questions?
Return JSON: {{"match": true/false, "reason": "one sentence"}}"""
    return _judge_call(prompt, model)


def _judge_call(prompt: str, model: str | None) -> dict[str, Any]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install openai with: pip install -e .") from exc

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.responses.create(
        model=model or os.getenv("VE_JUDGE_MODEL", "gpt-5.4-mini"),
        input=[
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
    text = getattr(response, "output_text", None) or _extract_text(response)
    raw = parse_json(text)
    return {"match": bool(raw.get("match", False)), "reason": str(raw.get("reason", ""))}


def _extract_text(response: Any) -> str:
    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                chunks.append(text)
    return "\n".join(chunks)


def _overlap_match(prediction: str, reference: str) -> dict[str, Any]:
    """Offline heuristic judge: content-word overlap. Coarse, for keyless runs only."""
    pred_terms = _terms(prediction)
    ref_terms = _terms(reference)
    if not pred_terms or not ref_terms:
        return {"match": False, "reason": "insufficient content"}
    overlap = len(pred_terms & ref_terms) / len(pred_terms)
    return {"match": overlap >= 0.5, "reason": f"offline overlap {overlap:.2f}"}


_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "into", "after", "before",
    "their", "were", "your", "have", "has", "had", "not", "are", "was", "but",
    "a", "an", "of", "to", "in", "on", "is", "it", "be", "or", "as", "at",
}


def _terms(text: str) -> set[str]:
    cleaned = text.lower().replace("-", " ").replace("/", " ")
    return {w for w in cleaned.split() if len(w) > 3 and w not in _STOP}
