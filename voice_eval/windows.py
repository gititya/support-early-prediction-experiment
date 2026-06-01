from __future__ import annotations

import os
from typing import Any


def early_turns(override: int | None = None) -> int:
    """Early-window size in turns: the 'first 60-90 seconds' proxy."""
    if override is not None:
        return override
    return int(os.getenv("VE_EARLY_TURNS", "6"))


def early_window(turns: list[dict[str, Any]], n: int | None = None) -> list[dict[str, Any]]:
    return turns[: early_turns(n)]


def full_window(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return turns


def render_turns(turns: list[dict[str, Any]]) -> str:
    return "\n".join(f"{t['turn']} {t['speaker']}: {t['text']}" for t in turns)
