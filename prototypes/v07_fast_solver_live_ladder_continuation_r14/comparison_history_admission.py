"""Pinned live mesh comparison history admission (R13–R16)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_live_ladder_continuation_r14.rolling_mesh_sequence import (
    RollingMeshState,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.stage_admission import (
    R13_CANDIDATE_ID,
    R13_RESULT_SHA256,
)

R14_RESULT_PATH = (
    "docs/tasks/evidence/V07-FAST-SOLVER-live-ladder-continuation-r14-20261015T063207Z.json"
)
R14_ORCHESTRATOR_PATH = (
    "docs/tasks/evidence/V07-FAST-SOLVER-live-ladder-continuation-r14-20261015T063207Z"
    ".live-orchestrator.json"
)
R14_RESULT_SHA256 = "5f952d2f02929b18ffa90ba22e79adf087b326dd2399d44e1a96eb2e216a2781"

R15_RESULT_PATH = "docs/tasks/evidence/V07-FAST-SOLVER-live-n8-continuation-r15-20261015T075153Z.json"
R15_ORCHESTRATOR_PATH = (
    "docs/tasks/evidence/V07-FAST-SOLVER-live-n8-continuation-r15-20261015T075153Z"
    ".live-orchestrator.json"
)
R15_RESULT_SHA256 = "ce904b79d133f7f3624b64d40458f55c9bfc066a7f5635574cadf75314b549de"

R16_RESULT_PATH = (
    "docs/tasks/evidence/V07-FAST-SOLVER-live-n16-continuation-r16-20261015T141846Z.json"
)
R16_ORCHESTRATOR_PATH = (
    "docs/tasks/evidence/V07-FAST-SOLVER-live-n16-continuation-r16-20261015T141846Z"
    ".live-orchestrator.json"
)
R16_RESULT_SHA256 = "3b5d2eb4183e247a15436d7906a6641825c98f61719827dcf2cef8164186bad2"
R16_RESULT_COMMIT = "0d4c4b50d2ee1bfed9fe11d709365571fe1aa7cf"

R13_RESULT_PATH = (
    "docs/tasks/evidence/V07-FAST-SOLVER-live-rating-ladder-r13-20261015T042649Z.json"
)
R13_ORCHESTRATOR_PATH = (
    "docs/tasks/evidence/V07-FAST-SOLVER-live-rating-ladder-r13-20261015T042649Z"
    ".live-orchestrator.json"
)

PRIOR_MESH_SEQUENCE = (1, 2, 4, 8, 16)


@dataclass(frozen=True)
class ComparisonSourcePin:
    coarse_n: int
    fine_n: int
    orchestrator_rel_path: str
    result_envelope_rel_path: str
    result_sha256: str
    comparison_index: int


COMPARISON_SOURCE_PINS: tuple[ComparisonSourcePin, ...] = (
    ComparisonSourcePin(1, 2, R13_ORCHESTRATOR_PATH, R13_RESULT_PATH, R13_RESULT_SHA256, 0),
    ComparisonSourcePin(2, 4, R14_ORCHESTRATOR_PATH, R14_RESULT_PATH, R14_RESULT_SHA256, 1),
    ComparisonSourcePin(4, 8, R15_ORCHESTRATOR_PATH, R15_RESULT_PATH, R15_RESULT_SHA256, 2),
    ComparisonSourcePin(8, 16, R16_ORCHESTRATOR_PATH, R16_RESULT_PATH, R16_RESULT_SHA256, 0),
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_orchestrator(root: Path, rel_path: str) -> dict[str, Any]:
    path = root / rel_path
    if not path.is_file():
        raise FileNotFoundError(rel_path)
    return json.loads(path.read_text(encoding="utf-8"))


def admit_comparison_at_pin(root: Path, pin: ComparisonSourcePin) -> dict[str, Any]:
    envelope_path = root / pin.result_envelope_rel_path
    if envelope_path.is_file():
        digest = file_sha256(envelope_path)
        if digest != pin.result_sha256:
            raise ValueError(
                f"comparison source result SHA256 mismatch coarse={pin.coarse_n} fine={pin.fine_n}"
            )
    orchestrator = _load_orchestrator(root, pin.orchestrator_rel_path)
    comparisons = orchestrator.get("mesh_comparisons") or []
    if pin.comparison_index >= len(comparisons):
        raise ValueError("comparison index out of range")
    item = dict(comparisons[pin.comparison_index])
    if int(item.get("coarse_subdivisions", 0)) != pin.coarse_n:
        raise ValueError("coarse subdivisions mismatch")
    if int(item.get("fine_subdivisions", 0)) != pin.fine_n:
        raise ValueError("fine subdivisions mismatch")
    if orchestrator.get("candidate_id") != R13_CANDIDATE_ID:
        raise ValueError("orchestrator candidate_id mismatch")
    item["admission"] = {
        "source_orchestrator_rel_path": pin.orchestrator_rel_path,
        "source_result_sha256": pin.result_sha256,
        "source_result_rel_path": pin.result_envelope_rel_path,
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


def verify_r16_result_admission(root: Path) -> None:
    path = root / R16_RESULT_PATH
    if file_sha256(path) != R16_RESULT_SHA256:
        raise ValueError("R16 result envelope SHA256 mismatch")
