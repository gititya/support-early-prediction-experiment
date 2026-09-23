from __future__ import annotations

import json
import os
import subprocess
from typing import Any


def parse_json(text: str) -> dict[str, Any]:
    """Parse model output that should be a single JSON object, tolerating fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip().rstrip("`").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


KEYCHAIN_ACCOUNT = "aditya"
KEYCHAIN_SERVICES = {
    "ANTHROPIC_API_KEY": "Anthropic:voice",
    "OPENAI_API_KEY": "OpenAI:voice",
}


def ensure_provider_key(env_name: str) -> str | None:
    value = os.getenv(env_name)
    if value:
        return value

    service = KEYCHAIN_SERVICES.get(env_name)
    if not service:
        return None

    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-a", KEYCHAIN_ACCOUNT, "-s", service, "-w"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None

    value = result.stdout.strip() if result.returncode == 0 else ""
    if value:
        os.environ[env_name] = value
        return value
    return None
