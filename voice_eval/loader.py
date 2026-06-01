from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# The three candidate scenario categories the generator produces.
CATEGORIES = ["permissions_access", "onboarding_migration", "workspace_setup"]


def exports_dir(override: str | None = None) -> Path:
    """Resolve the generator export directory (transcripts + ground_truth)."""
    raw = override or os.getenv("VE_EXPORTS_DIR") or "../support-call-generator/exports/latest"
    path = Path(raw)
    if not path.is_absolute():
        # Resolve relative to the project root (parent of this package).
        path = (Path(__file__).resolve().parent.parent / path).resolve()
    return path


def load_manifest(exports: Path) -> dict[str, Any]:
    return json.loads((exports / "manifest.json").read_text())


def list_cases(exports: Path) -> list[dict[str, Any]]:
    """Case-level metadata from the transcript-only manifest. No ground truth."""
    return load_manifest(exports)["cases"]


def load_transcript(case_id: str, exports: Path) -> list[dict[str, Any]]:
    """Transcript turns ONLY. This is the boundary the annotator may cross."""
    data = json.loads((exports / "transcripts" / f"{case_id}.json").read_text())
    return data["turns"]


# --- Scoring-side loaders. Only the scorer may call these. ---

def load_ground_truth(case_id: str, exports: Path) -> dict[str, Any]:
    return json.loads((exports / "ground_truth" / f"{case_id}.ground_truth.json").read_text())


def load_leakage(case_id: str, exports: Path) -> dict[str, Any]:
    path = exports / "ground_truth" / f"{case_id}.leakage_report.json"
    if not path.exists():
        return {"status": "PASS", "failures": [], "warnings": []}
    return json.loads(path.read_text())
