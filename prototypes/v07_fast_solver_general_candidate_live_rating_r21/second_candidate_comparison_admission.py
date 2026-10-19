"""Admit pinned R21C comparison receipts without recomputing history."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_comparison_persistence as scp,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_discovery as scd,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_stage_admission as scsa,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.comparison_history_admission import (
    comparison_canonical_sha256,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.mesh_sequence import (
    validate_adjacent_mesh_pair,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.rolling_mesh_sequence import (
    RollingMeshState,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.stage_admission import (
    file_sha256,
)

R21C_EVIDENCE_REL = (
    "docs/tasks/evidence/V07-FAST-SOLVER-general-candidate-continuation-r21c-20261019T043957Z"
)
R21D_EVIDENCE_REL = (
    "docs/tasks/evidence/V07-FAST-SOLVER-general-candidate-continuation-r21d-20261019T075818Z"
)


@dataclass(frozen=True)
class ComparisonAdmissionPin:
    coarse_mesh_n: int
    fine_mesh_n: int
    rel_path: str
    file_sha256: str
    comparison_canonical_sha256: str
    expected_overall_status: str


R21C_HISTORICAL_COMPARISON_PINS: tuple[ComparisonAdmissionPin, ...] = (
    ComparisonAdmissionPin(
        1,
        2,
        f"{R21C_EVIDENCE_REL}/comparisons/live-mesh-n1-to-n2-comparison.json",
        "97b87a55be19c2f451585e89e8f93ffb2723329b9f25e3c34284156c0ab88c31",
        "49456b2f835e671dfa9466cb9d4c5b7b1cf84379eb36533f1d1cb99130677930",
        "FAIL",
    ),
    ComparisonAdmissionPin(
        2,
        4,
        f"{R21C_EVIDENCE_REL}/comparisons/live-mesh-n2-to-n4-comparison.json",
        "1c3e1fc1e8a6f9e0b6489db5fa9f4079884cade616681547dcb84bbe630e42a9",
        "3373c69fca7ee0ffd14782aaea7555c82b8d4118addd44d51f357ec350a528b1",
        "FAIL",
    ),
    ComparisonAdmissionPin(
        4,
        8,
        f"{R21C_EVIDENCE_REL}/comparisons/live-mesh-n4-to-n8-comparison.json",
        "d2c794ac1a45bb63e5bec35dcae31a091c0e43bd0ea0202f346aa80850dd2246",
        "3494f7ce496cf5ade27ec55a7e6831e95fa651745ce143d6bac55e38ef20f23f",
        "FAIL",
    ),
    ComparisonAdmissionPin(
        8,
        16,
        f"{R21C_EVIDENCE_REL}/comparisons/live-mesh-n8-to-n16-comparison.json",
        "d1b1903fd2b4eb2f09400a1f43055bfebb485527ae2e99cb183ec2693355fc10",
        "9873a99090c7d3876707d34b3828760ea2c9d877fb5f868aec7ea9bfa660fc75",
        "PASS",
    ),
)

R21D_N16_TO_N32_COMPARISON_PIN = ComparisonAdmissionPin(
    16,
    32,
    f"{R21D_EVIDENCE_REL}/comparisons/live-mesh-n16-to-n32-comparison.json",
    "389d94e80a3b903d2c19ad6acadd2b8280d898034f927564e98c34fa2b8cf905",
    "03557aae354d92ef3021c1cc02bcc66fe44556fb346f5a5bbfded0e360dd923c",
    "PASS",
)

R21E_HISTORICAL_COMPARISON_PINS: tuple[ComparisonAdmissionPin, ...] = (
    *R21C_HISTORICAL_COMPARISON_PINS,
    R21D_N16_TO_N32_COMPARISON_PIN,
)


class ComparisonAdmissionError(RuntimeError):
    def __init__(self, code: str, *diagnostics: str) -> None:
        self.code = code
        self.diagnostics = diagnostics
        super().__init__(code)


def _validate_comparison_consistency(comparison: dict[str, Any]) -> None:
    overall = str(comparison.get("overall_status"))
    duty_s = str(comparison.get("duty_status"))
    wall_s = str(comparison.get("wall_status"))
    if overall == "PASS" and (duty_s != "PASS" or wall_s != "PASS"):
        raise ComparisonAdmissionError("OVERALL_PASS_REQUIRES_DUTY_WALL_PASS")
    if overall == "FAIL" and duty_s == "PASS" and wall_s == "PASS":
        raise ComparisonAdmissionError("OVERALL_FAIL_INCONSISTENT_WITH_METRICS")


def admit_pinned_comparison(
    root: Path,
    pin: ComparisonAdmissionPin,
    *,
    stages_by_mesh: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    path = root / pin.rel_path
    digest = file_sha256(path)
    if digest != pin.file_sha256:
        raise ComparisonAdmissionError(
            "COMPARISON_FILE_SHA256_MISMATCH",
            pin.rel_path,
            digest,
            pin.file_sha256,
        )
    envelope = json.loads(path.read_text(encoding="utf-8"))
    if envelope.get("schema_version") != scp.COMPARISON_RECEIPT_SCHEMA:
        raise ComparisonAdmissionError("COMPARISON_SCHEMA_MISMATCH")
    if int(envelope.get("coarse_mesh_n", 0)) != pin.coarse_mesh_n:
        raise ComparisonAdmissionError("COMPARISON_COARSE_MESH_N_MISMATCH")
    if int(envelope.get("fine_mesh_n", 0)) != pin.fine_mesh_n:
        raise ComparisonAdmissionError("COMPARISON_FINE_MESH_N_MISMATCH")
    comparison = dict(envelope["comparison"])
    canonical = comparison_canonical_sha256(comparison)
    if canonical != pin.comparison_canonical_sha256:
        raise ComparisonAdmissionError("COMPARISON_CANONICAL_HASH_MISMATCH")
    stored = envelope.get("comparison_canonical_sha256")
    if stored != pin.comparison_canonical_sha256:
        raise ComparisonAdmissionError("COMPARISON_STORED_CANONICAL_MISMATCH")
    if str(comparison.get("overall_status")) != pin.expected_overall_status:
        raise ComparisonAdmissionError(
            "COMPARISON_OVERALL_STATUS_MISMATCH",
            pin.expected_overall_status,
            str(comparison.get("overall_status")),
        )
    _validate_comparison_consistency(comparison)
    validate_adjacent_mesh_pair(pin.coarse_mesh_n, pin.fine_mesh_n)
    coarse_stage = stages_by_mesh.get(pin.coarse_mesh_n)
    fine_stage = stages_by_mesh.get(pin.fine_mesh_n)
    if coarse_stage is None or fine_stage is None:
        raise ComparisonAdmissionError("COMPARISON_STAGE_RECEIPT_MISSING")
    if int(comparison["coarse_subdivisions"]) != pin.coarse_mesh_n:
        raise ComparisonAdmissionError("COMPARISON_COARSE_SUBDIVISION_MISMATCH")
    if int(comparison["fine_subdivisions"]) != pin.fine_mesh_n:
        raise ComparisonAdmissionError("COMPARISON_FINE_SUBDIVISION_MISMATCH")
    if coarse_stage.get("candidate_id") != scd.SECOND_CANDIDATE_ID:
        raise ComparisonAdmissionError("COARSE_CANDIDATE_ID_MISMATCH")
    if fine_stage.get("candidate_id") != scd.SECOND_CANDIDATE_ID:
        raise ComparisonAdmissionError("FINE_CANDIDATE_ID_MISMATCH")
    if coarse_stage.get("rating_request_hash") != scd.EXPECTED_SECOND_RATING_REQUEST_HASH:
        raise ComparisonAdmissionError("COARSE_REQUEST_HASH_MISMATCH")
    if fine_stage.get("rating_request_hash") != scd.EXPECTED_SECOND_RATING_REQUEST_HASH:
        raise ComparisonAdmissionError("FINE_REQUEST_HASH_MISMATCH")
    if coarse_stage.get("request_snapshot_sha256") != scsa.SNAPSHOT_CONTENT_SHA256:
        raise ComparisonAdmissionError("COARSE_SNAPSHOT_IDENTITY_MISMATCH")
    if fine_stage.get("request_snapshot_sha256") != scsa.SNAPSHOT_CONTENT_SHA256:
        raise ComparisonAdmissionError("FINE_SNAPSHOT_IDENTITY_MISMATCH")
    comparison["admission"] = {
        "source_rel_path": pin.rel_path,
        "source_file_sha256": digest,
        "comparison_canonical_sha256": canonical,
    }
    return comparison


def admit_r21c_historical_comparisons(
    root: Path,
    *,
    stages_by_mesh: dict[int, dict[str, Any]],
) -> tuple[list[dict[str, Any]], RollingMeshState]:
    comparisons: list[dict[str, Any]] = []
    rolling = RollingMeshState()
    for mesh_n in (1, 2, 4, 8, 16):
        rolling.record_mesh_accepted(mesh_n)
    for pin in R21C_HISTORICAL_COMPARISON_PINS:
        item = admit_pinned_comparison(root, pin, stages_by_mesh=stages_by_mesh)
        comparisons.append(item)
        rolling.record_comparison(item)
        rolling.after_comparison_recorded(pin.fine_mesh_n)
    return comparisons, rolling


def admit_r21e_historical_comparisons(
    root: Path,
    *,
    stages_by_mesh: dict[int, dict[str, Any]],
) -> tuple[list[dict[str, Any]], RollingMeshState]:
    comparisons: list[dict[str, Any]] = []
    rolling = RollingMeshState()
    for mesh_n in (1, 2, 4, 8, 16, 32):
        rolling.record_mesh_accepted(mesh_n)
    for pin in R21E_HISTORICAL_COMPARISON_PINS:
        item = admit_pinned_comparison(root, pin, stages_by_mesh=stages_by_mesh)
        comparisons.append(item)
        rolling.record_comparison(item)
        rolling.after_comparison_recorded(pin.fine_mesh_n)
    return comparisons, rolling
