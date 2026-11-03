"""Reload CandidateRatingRequest in worker processes (spawn-safe)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
    candidate_rating_request_hash,
)

ROOT = Path(__file__).resolve().parents[2]
FROZEN_RUNNER = (
    ROOT / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
)


def load_rating_request_by_id(candidate_id: str) -> CandidateRatingRequest:
    spec = importlib.util.spec_from_file_location("q13", FROZEN_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("frozen candidate runner missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _candidate, rating_request = mod._build_candidate_requests()[candidate_id]
    if type(rating_request) is not CandidateRatingRequest:
        encoded = json.dumps(rating_request, separators=(",", ":"), ensure_ascii=False)
        rating_request = CandidateRatingRequest.model_validate_json(encoded, strict=True)
    return rating_request


def verify_request_identity(request: CandidateRatingRequest) -> str:
    expected_hash = candidate_rating_request_hash(request)
    reloaded = load_rating_request_by_id(request.candidate_id)
    if candidate_rating_request_hash(reloaded) != expected_hash:
        raise ValueError("rating_request_hash mismatch vs frozen runner reload")
    if reloaded.candidate_hash != request.candidate_hash:
        raise ValueError("candidate_hash mismatch vs frozen runner reload")
    return expected_hash
