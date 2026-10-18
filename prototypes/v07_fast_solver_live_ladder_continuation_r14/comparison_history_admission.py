"""Pinned live mesh comparison history admission (R13–R17)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_live_ladder_continuation_r14.mesh_sequence import (
    validate_adjacent_mesh_pair,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.rolling_mesh_sequence import (
    RollingMeshState,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.stage_admission import (
    R13_CANDIDATE_ID,
    R13_RESULT_SHA256,
    R14_N4_MESH_HASH,
    R15_N8_MESH_HASH,
    R16_N16_MESH_HASH,
    R17_N32_MESH_HASH,
    R17_RESULT_SHA256,
)

RATING_REQUEST_HASH = "56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8"

R14_RESULT_PATH = (
    "docs/tasks/evidence/V07-FAST-SOLVER-live-ladder-continuation-r14-20261015T063207Z.json"
)
R14_ORCHESTRATOR_PATH = (
    "docs/tasks/evidence/V07-FAST-SOLVER-live-ladder-continuation-r14-20261015T063207Z"
    ".live-orchestrator.json"
)
R14_ORCHESTRATOR_SHA256 = "e738b582877e72666ef48e3ea36c67662b812f1cc881c29856672d6e13fc7ebc"
R14_RESULT_SHA256 = "5f952d2f02929b18ffa90ba22e79adf087b326dd2399d44e1a96eb2e216a2781"
R14_RESULT_COMMIT = "b2847801cefeb12443decc2c518f022772118737"

R15_RESULT_PATH = (
    "docs/tasks/evidence/V07-FAST-SOLVER-live-n8-continuation-r15-20261015T075153Z.json"
)
R15_ORCHESTRATOR_PATH = (
    "docs/tasks/evidence/V07-FAST-SOLVER-live-n8-continuation-r15-20261015T075153Z"
    ".live-orchestrator.json"
)
R15_ORCHESTRATOR_SHA256 = "59a1cbfa8d22caa6c8590001e59b5347d3cf4f9abbf53f4a881a5aa87cc5599b"
R15_RESULT_SHA256 = "ce904b79d133f7f3624b64d40458f55c9bfc066a7f5635574cadf75314b549de"
R15_RESULT_COMMIT = "8936019e8bd3f6b21ff3314ccaebac5be7cb471f"

R16_RESULT_PATH = (
    "docs/tasks/evidence/V07-FAST-SOLVER-live-n16-continuation-r16-20261015T141846Z.json"
)
R16_ORCHESTRATOR_PATH = (
    "docs/tasks/evidence/V07-FAST-SOLVER-live-n16-continuation-r16-20261015T141846Z"
    ".live-orchestrator.json"
)
R16_ORCHESTRATOR_SHA256 = "9c7589c7f9c6680253f428613d0e3738f1f2a3a8b36151db53ef6ca83fb9337e"
R16_RESULT_SHA256 = "3b5d2eb4183e247a15436d7906a6641825c98f61719827dcf2cef8164186bad2"
R16_RESULT_COMMIT = "7f26b466bc8eabc95334163c2442b85610a71265"

R13_RESULT_PATH = "docs/tasks/evidence/V07-FAST-SOLVER-live-rating-ladder-r13-20261015T042649Z.json"
R13_ORCHESTRATOR_PATH = (
    "docs/tasks/evidence/V07-FAST-SOLVER-live-rating-ladder-r13-20261015T042649Z"
    ".live-orchestrator.json"
)
R13_ORCHESTRATOR_SHA256 = "7c7895ab3363473df6d66becd0b0f1d85ece5302f32f0177e7ead4f20a83a50b"
R13_RESULT_COMMIT = "53617eaec29a0e9bc698179a6afe7030c878dc83"

R17_RESULT_PATH = "docs/tasks/evidence/V07-FAST-SOLVER-live-n32-candidate-r17-20261018T082904Z.json"
R17_ORCHESTRATOR_PATH = (
    "docs/tasks/evidence/V07-FAST-SOLVER-live-n32-candidate-r17-20261018T082904Z"
    ".live-orchestrator.json"
)
R17_ORCHESTRATOR_SHA256 = "402f875fa71e382e61611bfa476d3fda7daee8b1bb37eb9cf05f8d2d85479174"
R17_RESULT_COMMIT = "fa36cf7cf0ae2ed47bd30946a51123585fab959e"
R17_RESULT_SHA256_ORIGINAL = "938a1155d6ef04482fddf376abe00fe71a4b539599e5940681e1017d195d6006"

PINNED_MESH_RESULT_HASHES: dict[int, str] = {
    1: "5aebddd6094f9b037f68d57289d36afd8607ea75751d77cb6d74c4e4c01d55c2",
    2: "f408506a557f5ecd15910767156cfb2d75c30bb8f910a727365b750d2ea3adac",
    4: R14_N4_MESH_HASH,
    8: R15_N8_MESH_HASH,
    16: R16_N16_MESH_HASH,
    32: R17_N32_MESH_HASH,
}

PRIOR_MESH_SEQUENCE = (1, 2, 4, 8, 16, 32)
CANDIDATE_MESH_N = 32
HEADROOM_MESH_N = 64


class ComparisonAdmissionError(RuntimeError):
    def __init__(self, code: str, *diagnostics: str) -> None:
        self.code = code
        self.diagnostics = diagnostics
        super().__init__(code)


@dataclass(frozen=True)
class ComparisonSourcePin:
    coarse_n: int
    fine_n: int
    orchestrator_rel_path: str
    orchestrator_sha256: str
    result_envelope_rel_path: str
    result_sha256: str
    source_result_commit: str
    comparison_index: int


COMPARISON_SOURCE_PINS: tuple[ComparisonSourcePin, ...] = (
    ComparisonSourcePin(
        1,
        2,
        R13_ORCHESTRATOR_PATH,
        R13_ORCHESTRATOR_SHA256,
        R13_RESULT_PATH,
        R13_RESULT_SHA256,
        R13_RESULT_COMMIT,
        0,
    ),
    ComparisonSourcePin(
        2,
        4,
        R14_ORCHESTRATOR_PATH,
        R14_ORCHESTRATOR_SHA256,
        R14_RESULT_PATH,
        R14_RESULT_SHA256,
        R14_RESULT_COMMIT,
        1,
    ),
    ComparisonSourcePin(
        4,
        8,
        R15_ORCHESTRATOR_PATH,
        R15_ORCHESTRATOR_SHA256,
        R15_RESULT_PATH,
        R15_RESULT_SHA256,
        R15_RESULT_COMMIT,
        2,
    ),
    ComparisonSourcePin(
        8,
        16,
        R16_ORCHESTRATOR_PATH,
        R16_ORCHESTRATOR_SHA256,
        R16_RESULT_PATH,
        R16_RESULT_SHA256,
        R16_RESULT_COMMIT,
        0,
    ),
    ComparisonSourcePin(
        16,
        32,
        R17_ORCHESTRATOR_PATH,
        R17_ORCHESTRATOR_SHA256,
        R17_RESULT_PATH,
        R17_RESULT_SHA256,
        R17_RESULT_COMMIT,
        4,
    ),
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def comparison_canonical_sha256(comparison: dict[str, Any]) -> str:
    body = {k: v for k, v in comparison.items() if k != "admission"}
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _stage_mesh_hash_map(orchestrator: dict[str, Any]) -> dict[int, str]:
    out: dict[int, str] = {}
    for stage in orchestrator.get("mesh_stages") or []:
        mesh_n = int(stage.get("mesh_n", 0))
        mesh_hash = stage.get("mesh_result_hash")
        if mesh_n and mesh_hash:
            out[mesh_n] = str(mesh_hash)
    return out


def _validate_comparison_fields(item: dict[str, Any]) -> None:
    validate_adjacent_mesh_pair(
        int(item["coarse_subdivisions"]),
        int(item["fine_subdivisions"]),
    )
    threshold = Decimal(str(item.get("duty_metric_threshold", "0.01")))
    if threshold != Decimal("0.01"):
        raise ComparisonAdmissionError(
            "DUTY_METRIC_THRESHOLD_MISMATCH",
            f"expected=0.01 actual={threshold}",
        )
    for key in ("duty_status", "wall_status", "overall_status"):
        if key not in item:
            raise ComparisonAdmissionError("COMPARISON_FIELD_MISSING", key)
    overall = str(item["overall_status"])
    duty_s = str(item["duty_status"])
    wall_s = str(item["wall_status"])
    if overall == "PASS" and (duty_s != "PASS" or wall_s != "PASS"):
        raise ComparisonAdmissionError("OVERALL_PASS_REQUIRES_DUTY_WALL_PASS")
    if overall == "FAIL" and duty_s == "PASS" and wall_s == "PASS":
        raise ComparisonAdmissionError("OVERALL_FAIL_INCONSISTENT_WITH_METRICS")


def _validate_mesh_hashes_for_pair(
    coarse_n: int,
    fine_n: int,
    orchestrator: dict[str, Any],
) -> None:
    stage_hashes = _stage_mesh_hash_map(orchestrator)
    for mesh_n in (coarse_n, fine_n):
        expected = PINNED_MESH_RESULT_HASHES.get(mesh_n)
        if expected is None:
            raise ComparisonAdmissionError("PINNED_MESH_HASH_MISSING", f"mesh_n={mesh_n}")
        actual = stage_hashes.get(mesh_n)
        if actual is None:
            raise ComparisonAdmissionError(
                "ORCHESTRATOR_STAGE_MESH_HASH_MISSING",
                f"mesh_n={mesh_n}",
            )
        if actual != expected:
            raise ComparisonAdmissionError(
                "PINNED_MESH_HASH_MISMATCH",
                f"mesh_n={mesh_n}",
                f"expected={expected}",
                f"actual={actual}",
            )


def admit_comparison_at_pin(root: Path, pin: ComparisonSourcePin) -> dict[str, Any]:
    envelope_path = root / pin.result_envelope_rel_path
    if not envelope_path.is_file():
        raise ComparisonAdmissionError("RESULT_ENVELOPE_MISSING", pin.result_envelope_rel_path)
    digest = file_sha256(envelope_path)
    if digest != pin.result_sha256:
        raise ComparisonAdmissionError(
            "RESULT_ENVELOPE_SHA256_MISMATCH",
            pin.result_envelope_rel_path,
            f"expected={pin.result_sha256}",
            f"actual={digest}",
        )
    orch_path = root / pin.orchestrator_rel_path
    if not orch_path.is_file():
        raise ComparisonAdmissionError("ORCHESTRATOR_MISSING", pin.orchestrator_rel_path)
    orch_digest = file_sha256(orch_path)
    if orch_digest != pin.orchestrator_sha256:
        raise ComparisonAdmissionError(
            "ORCHESTRATOR_SHA256_MISMATCH",
            pin.orchestrator_rel_path,
            f"expected={pin.orchestrator_sha256}",
            f"actual={orch_digest}",
        )
    orchestrator = json.loads(orch_path.read_text(encoding="utf-8"))
    if orchestrator.get("candidate_id") != R13_CANDIDATE_ID:
        raise ComparisonAdmissionError("CANDIDATE_ID_MISMATCH")
    if orchestrator.get("rating_request_hash") not in (None, RATING_REQUEST_HASH):
        req = orchestrator.get("rating_request_hash")
        if req != RATING_REQUEST_HASH:
            raise ComparisonAdmissionError("RATING_REQUEST_HASH_MISMATCH", str(req))
    comparisons = orchestrator.get("mesh_comparisons") or []
    if pin.comparison_index >= len(comparisons):
        raise ComparisonAdmissionError("COMPARISON_INDEX_OUT_OF_RANGE")
    item = dict(comparisons[pin.comparison_index])
    if int(item.get("coarse_subdivisions", 0)) != pin.coarse_n:
        raise ComparisonAdmissionError("COARSE_SUBDIVISIONS_MISMATCH")
    if int(item.get("fine_subdivisions", 0)) != pin.fine_n:
        raise ComparisonAdmissionError("FINE_SUBDIVISIONS_MISMATCH")
    _validate_mesh_hashes_for_pair(pin.coarse_n, pin.fine_n, orchestrator)
    _validate_comparison_fields(item)
    item["admission"] = {
        "source_orchestrator_rel_path": pin.orchestrator_rel_path,
        "source_orchestrator_sha256": pin.orchestrator_sha256,
        "source_result_sha256": pin.result_sha256,
        "source_result_rel_path": pin.result_envelope_rel_path,
        "source_result_commit": pin.source_result_commit,
        "comparison_canonical_sha256": comparison_canonical_sha256(item),
    }
    return item


def admit_prior_comparison_history(root: Path) -> list[dict[str, Any]]:
    return [admit_comparison_at_pin(root, pin) for pin in COMPARISON_SOURCE_PINS]


def build_rolling_state_from_admitted_history(
    comparisons: list[dict[str, Any]],
) -> RollingMeshState:
    state = RollingMeshState()
    for mesh_n in PRIOR_MESH_SEQUENCE:
        state.record_mesh_accepted(mesh_n)
    for comparison in comparisons:
        state.record_comparison(comparison)
    return state


def require_candidate_identified_before_headroom(state: RollingMeshState) -> None:
    if state.ladder_status != "MESH_CANDIDATE_IDENTIFIED":
        raise ComparisonAdmissionError(
            "LADDER_NOT_CANDIDATE_IDENTIFIED",
            f"status={state.ladder_status}",
        )
    if state.candidate_index is None:
        raise ComparisonAdmissionError("CANDIDATE_INDEX_MISSING")
    candidate_n = state.runs_mesh_n[state.candidate_index]
    if candidate_n != CANDIDATE_MESH_N:
        raise ComparisonAdmissionError(
            "MESH_CANDIDATE_N_MISMATCH",
            f"expected={CANDIDATE_MESH_N}",
            f"actual={candidate_n}",
        )


def verify_r16_result_admission(root: Path) -> None:
    path = root / R16_RESULT_PATH
    if file_sha256(path) != R16_RESULT_SHA256:
        raise ComparisonAdmissionError("R16_RESULT_SHA256_MISMATCH")


def verify_r17_revised_result_admission(root: Path) -> None:
    path = root / R17_RESULT_PATH
    if file_sha256(path) != R17_RESULT_SHA256:
        raise ComparisonAdmissionError("R17_RESULT_SHA256_MISMATCH")
