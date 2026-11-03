"""Pinned frozen mesh stage receipts for R19 Candidate B and R21E second candidate."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.r22_pinned_identity import (
    SECOND_CANDIDATE_ID,
    SECOND_RATING_REQUEST_HASH,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21.second_candidate_stage_admission import (
    N32_ACCEPTED_RECEIPT_REL,
    N32_ACCEPTED_RECEIPT_SHA256,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.stage_admission import (
    R17_N32_STAGE_SHA256,
    R17_STAGE_DIR_REL,
    R18_N64_STAGE_SHA256,
    R18_STAGE_DIR_REL,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_pinned_identity import (
    ACCEPTED_MESH_RESULT_HASH,
    HEADROOM_MESH_RESULT_HASH,
    RATING_REQUEST_HASH,
)

R21E_EVIDENCE_REL = (
    "docs/tasks/evidence/V07-FAST-SOLVER-general-candidate-continuation-r21e-20261019T111947Z"
)
R21E_N32_RECEIPT_REL = N32_ACCEPTED_RECEIPT_REL
R21E_N32_RECEIPT_SHA256 = N32_ACCEPTED_RECEIPT_SHA256
R21E_N32_MESH_HASH = "3e4618eb8144cfa8156ff5fe08c11ecf64a734de6ffcbd44f19cac39a11c646e"
R21E_N64_RECEIPT_REL = f"{R21E_EVIDENCE_REL}/stages/live-mesh-n64-receipt.json"
R21E_N64_RECEIPT_SHA256 = "41a2f671a6b50c7c98c55bcd8e00d3336d893b19e7bdc216964e08a5d1285725"
R21E_N64_MESH_HASH = "27232b3dd78bf9c21ed0543d104ff1cfd76d4a68f29f979d2b36079cff0d4556"
R21E_N32_PROVIDER_AUTHORITY_ID = "V07-FAST-SOLVER-GENERAL-CANDIDATE-CONTINUATION-R21D"
R21E_N64_PROVIDER_AUTHORITY_ID = "V07-FAST-SOLVER-GENERAL-CANDIDATE-CONTINUATION-R21E"


@dataclass(frozen=True)
class FrozenMeshStagePin:
    label: str
    candidate_id: str
    rating_request_hash: str
    mesh_n: int
    mesh_role: str
    receipt_rel: str
    receipt_sha256: str
    expected_mesh_result_hash: str


R19_CANDIDATE_B_PINS: tuple[FrozenMeshStagePin, ...] = (
    FrozenMeshStagePin(
        label="CANDIDATE_B_R19",
        candidate_id=CANDIDATE_B_ID,
        rating_request_hash=RATING_REQUEST_HASH,
        mesh_n=32,
        mesh_role="ACCEPTED",
        receipt_rel=f"{R17_STAGE_DIR_REL}/live-mesh-n32-receipt.json",
        receipt_sha256=R17_N32_STAGE_SHA256,
        expected_mesh_result_hash=ACCEPTED_MESH_RESULT_HASH,
    ),
    FrozenMeshStagePin(
        label="CANDIDATE_B_R19",
        candidate_id=CANDIDATE_B_ID,
        rating_request_hash=RATING_REQUEST_HASH,
        mesh_n=64,
        mesh_role="HEADROOM",
        receipt_rel=f"{R18_STAGE_DIR_REL}/live-mesh-n64-receipt.json",
        receipt_sha256=R18_N64_STAGE_SHA256,
        expected_mesh_result_hash=HEADROOM_MESH_RESULT_HASH,
    ),
)

R21E_SECOND_CANDIDATE_PINS: tuple[FrozenMeshStagePin, ...] = (
    FrozenMeshStagePin(
        label="SECOND_CANDIDATE_R21E",
        candidate_id=SECOND_CANDIDATE_ID,
        rating_request_hash=SECOND_RATING_REQUEST_HASH,
        mesh_n=32,
        mesh_role="ACCEPTED",
        receipt_rel=R21E_N32_RECEIPT_REL,
        receipt_sha256=R21E_N32_RECEIPT_SHA256,
        expected_mesh_result_hash=R21E_N32_MESH_HASH,
    ),
    FrozenMeshStagePin(
        label="SECOND_CANDIDATE_R21E",
        candidate_id=SECOND_CANDIDATE_ID,
        rating_request_hash=SECOND_RATING_REQUEST_HASH,
        mesh_n=64,
        mesh_role="HEADROOM",
        receipt_rel=R21E_N64_RECEIPT_REL,
        receipt_sha256=R21E_N64_RECEIPT_SHA256,
        expected_mesh_result_hash=R21E_N64_MESH_HASH,
    ),
)

ALL_FROZEN_MESH_PINS: tuple[FrozenMeshStagePin, ...] = (
    *R19_CANDIDATE_B_PINS,
    *R21E_SECOND_CANDIDATE_PINS,
)


def mesh_pin_for(label: str, mesh_n: int, mesh_role: str) -> FrozenMeshStagePin | None:
    for pin in ALL_FROZEN_MESH_PINS:
        if pin.label == label and pin.mesh_n == mesh_n and pin.mesh_role == mesh_role:
            return pin
    return None


def receipt_path(root: Path, pin: FrozenMeshStagePin) -> Path:
    return root / pin.receipt_rel
