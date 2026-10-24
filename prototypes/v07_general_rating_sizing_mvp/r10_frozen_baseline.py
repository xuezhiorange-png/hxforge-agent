"""Read-only R10 frozen mesh rows for R12 comparison (no substitute for new ratings)."""

from __future__ import annotations

import json
import subprocess
from decimal import Decimal
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_R10_DIR = _REPO / "docs/tasks/evidence/V07-GENERAL-MULTI-CANDIDATE-LIVE-RATING-R10"
_R10_BRANCH = (
    "origin/cursor/v07-general-rating-sizing-e2e-mvp-r1-1201:"
    "docs/tasks/evidence/V07-GENERAL-MULTI-CANDIDATE-LIVE-RATING-R10"
)

R10_CANDIDATE_A_REFERENCE = {
    "candidate_id": "5a73903d-3325-5604-be3b-ba5950299893",
    "tube_length_m": "4.85",
    "baffle_spacing_m": "0.97",
    "total_duty_w": "38387.018185484473",
    "nominal_tube_outer_area_m2": "73.4356786094391222873825",
    "mesh_result_hash": "472249e43f6d722bc60023cc3cf1fbcc075c155d1e1c69bf35d4b70110feefe5",
}


def load_r10_candidate_rating_rows() -> list[dict[str, Any]]:
    path = _R10_DIR / "CANDIDATE_RATING_RESULTS.json"
    if path.is_file():
        doc = json.loads(path.read_text(encoding="utf-8"))
        return list(doc["candidates"])
    proc = subprocess.run(
        ["git", "show", f"{_R10_BRANCH}/CANDIDATE_RATING_RESULTS.json"],
        cwd=_REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return list(json.loads(proc.stdout)["candidates"])


def r10_reference_a_nominal_area_m2() -> Decimal:
    return Decimal(R10_CANDIDATE_A_REFERENCE["nominal_tube_outer_area_m2"])
