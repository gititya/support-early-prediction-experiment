from __future__ import annotations

import os
from typing import Any

from voice_eval.llmio import parse_json
from voice_eval.loader import CATEGORIES
from voice_eval.windows import render_turns

SYSTEM_PROMPT = """You are a blind support-call analyst. You read only an early fragment of a \
B2B SaaS support call transcript and predict where it is heading. You have NOT seen the rest of \
the call, any answer key, or any hidden notes. Reason only from what is in the fragment.
Return only valid JSON. Do not include markdown fences."""


def build_prompt(turns: list[dict[str, Any]]) -> str:
    return f"""Here is the opening fragment of a support call.

Candidate issue categories: {", ".join(CATEGORIES)}

Transcript fragment:
{render_turns(turns)}

Predict the following from this fragment alone. Do not claim certainty you do not have.
Return JSON with exactly:
{{
  "predicted_category": "one of the candidate categories",
  "predicted_root_cause": "your single best specific root-cause hypothesis, one sentence",
  "confidence": 0.0,
  "earliest_identifiable_turn": 0,
  "next_diagnostic_question": "the single most useful question to ask next"
}}

earliest_identifiable_turn is the turn number in this fragment where the specific root cause first \
became identifiable, or 0 if it is not yet identifiable from this fragment.""".strip()


def annotate(
    turns: list[dict[str, Any]],
    model: str | None = None,
    use_llm: bool | None = None,
) -> dict[str, Any]:
    """Blind annotation of an early transcript fragment. Claude, with offline fallback."""
    if use_llm is None:
        use_llm = bool(os.getenv("ANTHROPIC_API_KEY"))
    if not use_llm:
        return _offline_annotation(turns)
    return _annotate_with_claude(turns, model)


def _annotate_with_claude(turns: list[dict[str, Any]], model: str | None) -> dict[str, Any]:
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError("Install anthropic with: pip install -e .") from exc

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=model or os.getenv("VE_ANNOTATOR_MODEL", "claude-sonnet-4-6"),
        max_tokens=1024,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": build_prompt(turns)}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return _coerce(parse_json(text))


def _coerce(raw: dict[str, Any]) -> dict[str, Any]:
    category = str(raw.get("predicted_category", "")).strip()
    if category not in CATEGORIES:
        category = _closest_category(category)
    return {
        "predicted_category": category,
        "predicted_root_cause": str(raw.get("predicted_root_cause", "")).strip(),
        "confidence": float(raw.get("confidence", 0.0) or 0.0),
        "earliest_identifiable_turn": int(raw.get("earliest_identifiable_turn", 0) or 0),
        "next_diagnostic_question": str(raw.get("next_diagnostic_question", "")).strip(),
    }


def _closest_category(value: str) -> str:
    value = value.lower()
    for category in CATEGORIES:
        if category in value or category.replace("_", " ") in value:
            return category
    return CATEGORIES[0]


def _offline_annotation(turns: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic keyword fallback so the harness runs without an API key."""
    text = " ".join(t["text"].lower() for t in turns)
    keywords = {
        "onboarding_migration": ["migration", "migrated", "onboard", "import", "moved over"],
        "workspace_setup": ["workspace", "setup", "configure", "provision", "integration"],
        "permissions_access": ["access", "permission", "role", "sso", "login", "denied"],
    }
    category = CATEGORIES[0]
    for cat, words in keywords.items():
        if any(w in text for w in words):
            category = cat
            break
    return {
        "predicted_category": category,
        "predicted_root_cause": "offline fallback: unable to infer specific root cause without an LLM",
        "confidence": 0.0,
        "earliest_identifiable_turn": 0,
        "next_diagnostic_question": "Can you describe exactly what changed right before the issue started?",
    }
