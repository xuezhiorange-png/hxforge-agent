"""Destructive tests: tampered artifacts must fail closed."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import R11_RESULT_HASH
from prototypes.v07_fast_solver_rating_authority_admission_r11.compact_rating import (
    compact_rating_hash,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalCandidateRatingResult,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_rate_candidate import (
    experimental_rating_result_hash,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.verification import (
    verify_task174_binding,
)
from prototypes.v07_fast_solver_rating_contract_live_bridge_r12.r11_artifact_verify import (
    _model_roundtrip_pass,
)


@pytest.fixture(scope="module")
def r11_model() -> ExperimentalCandidateRatingResult:
    from pathlib import Path

    from prototypes.v07_fast_solver_evidence_gate.trusted_constants import R11_RATING_JSON_REL

    root = Path(__file__).resolve().parents[2]
    return ExperimentalCandidateRatingResult.model_validate_json(
        (root / R11_RATING_JSON_REL).read_text(encoding="utf-8"),
        strict=True,
    )


def test_result_hash_changes_if_duty_tampered(r11_model: ExperimentalCandidateRatingResult) -> None:
    tampered = r11_model.model_copy(update={"total_duty_w": r11_model.total_duty_w + 1})
    assert experimental_rating_result_hash(tampered) != R11_RESULT_HASH


def test_compact_hash_changes_if_geometry_tampered(
    r11_model: ExperimentalCandidateRatingResult,
) -> None:
    import importlib.util
    import json

    from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
        CandidateRatingRequest,
    )
    from prototypes.v07_fast_solver_evidence_gate.trusted_constants import (
        CANDIDATE_B_ID,
        R11_RATING_JSON_REL,
        R11_RATING_JSON_SHA256,
    )
    from prototypes.v07_fast_solver_rating_authority_admission_r11.compact_rating import (
        build_compact_from_full,
        geometry_summary_from_request,
    )

    runner = (
        Path(__file__).resolve().parents[2]
        / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
    )
    spec = importlib.util.spec_from_file_location("q13", runner)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    _c, req_raw = mod._build_candidate_requests()[CANDIDATE_B_ID]
    if type(req_raw) is not CandidateRatingRequest:
        req_raw = CandidateRatingRequest.model_validate_json(
            json.dumps(req_raw, separators=(",", ":"), ensure_ascii=False),
            strict=True,
        )
    geom = geometry_summary_from_request(req_raw)
    compact = build_compact_from_full(
        r11_model,
        trajectory_artifact_path=R11_RATING_JSON_REL,
        trajectory_file_sha256=R11_RATING_JSON_SHA256,
        geometry_summary=geom,
    )
    base_hash = compact_rating_hash(compact)
    bad_geom = geom.model_copy(update={"interval_count": geom.interval_count + 1})
    bad = compact.model_copy(update={"geometry_summary": bad_geom})
    assert compact_rating_hash(bad) != base_hash


def test_task174_binding_rejects_bad_hash(
    r11_model: ExperimentalCandidateRatingResult,
) -> None:
    import importlib.util
    import json
    from pathlib import Path

    from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
        CandidateRatingRequest,
    )
    from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID

    runner = (
        Path(__file__).resolve().parents[2]
        / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
    )
    spec = importlib.util.spec_from_file_location("q13", runner)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    _c, req_raw = mod._build_candidate_requests()[CANDIDATE_B_ID]
    if type(req_raw) is not CandidateRatingRequest:
        req_raw = CandidateRatingRequest.model_validate_json(
            json.dumps(req_raw, separators=(",", ":"), ensure_ascii=False),
            strict=True,
        )
    payload = copy.deepcopy(req_raw.model_dump(mode="json"))
    payload["task174_result"]["result_hash"] = "0" * 64
    bad = CandidateRatingRequest.model_validate(payload, strict=True)
    assert verify_task174_binding(bad) is False


def test_model_roundtrip_detects_corrupt_result_id(
    r11_model: ExperimentalCandidateRatingResult,
) -> None:
    corrupt = r11_model.model_copy(update={"result_id": "corrupt"})
    assert _model_roundtrip_pass(corrupt) == "PASS"
    assert experimental_rating_result_hash(corrupt) != R11_RESULT_HASH
