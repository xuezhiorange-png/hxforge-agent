"""Pinned second-candidate (R21) frozen stage and snapshot admission."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
    candidate_rating_request_hash,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_discovery as scd,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.request_snapshot import (
    load_request_from_snapshot_file,
    snapshot_content_digest,
    verify_snapshot_integrity,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.stage_admission import (
    PriorStagePin,
    file_sha256,
)
from prototypes.v07_fast_solver_live_rating_ladder_r13.stage_persistence import load_stage_receipt
from prototypes.v07_fast_solver_live_rating_result_r19.live_mesh_replay import (
    LiveMeshReplayError,
    replay_verified_prior_stage_mesh,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.verification import (
    verify_cell_closure,
    verify_energy_balance,
)

FROZEN_EVIDENCE_REL = (
    "docs/tasks/evidence/V07-FAST-SOLVER-general-candidate-live-rating-r21-20261018T162215Z"
)
SNAPSHOT_REL = (
    f"{FROZEN_EVIDENCE_REL}/snapshots/"
    "live-rating-request-adeab5b1-a339-5eb3-aa66-011ffe49bac0-1c1c98cb0ce30495.json"
)
SNAPSHOT_FILE_SHA256 = (
    "6ca098792d8e67381d205e9f9a6af20e84d6dd8fecfbcfb15a46abea28a970a8"
)
SNAPSHOT_CONTENT_SHA256 = (
    "2222d90aa1639f9f26f183d4816b97fa257ad861a4441c81bd496c3a7fef7a20"
)
N1_RECEIPT_REL = f"{FROZEN_EVIDENCE_REL}/stages/live-mesh-n1-receipt.json"
N2_RECEIPT_REL = f"{FROZEN_EVIDENCE_REL}/stages/live-mesh-n2-receipt.json"
N4_TIMEOUT_RECEIPT_REL = f"{FROZEN_EVIDENCE_REL}/stages/live-mesh-n4-receipt.json"
N1_RECEIPT_SHA256 = "f4a59f012cc83d83e8cf40bb4b14ab562ed635c4cc00ef8b8e38f3f4447b5270"
N2_RECEIPT_SHA256 = "e5c16c5241b2c0e3ac5c1954b0ca7a5d6d503b52b55ed864b5ffd1e11bc757ab"
N4_TIMEOUT_RECEIPT_SHA256 = (
    "1f6954ec310489e6323e19676d6809f6d728a34e9e514acd67b79b156030ce04"
)
N1_MESH_RESULT_HASH = "854b06ac829183f067992ac0b76806c2a5772bd3deab99a4c678fb45ff4da302"
N2_MESH_RESULT_HASH = "84f2491e89d57b7e470a4578ee4dcc43b810e03de93d5176fa8b57cc0297ae1c"
N1_SHOOTING_ENTHALPY = "107519.725252127586206614412367343902587890625"
N2_SHOOTING_ENTHALPY = "107519.11806278412140252590179443359375"
N1_OUTER_ITERATIONS = 29
N2_OUTER_ITERATIONS = 22

SECOND_CANDIDATE_PRIOR_PINS: tuple[PriorStagePin, ...] = (
    PriorStagePin(1, N1_RECEIPT_REL, N1_RECEIPT_SHA256),
    PriorStagePin(2, N2_RECEIPT_REL, N2_RECEIPT_SHA256),
)


class SecondCandidateAdmissionError(RuntimeError):
    def __init__(self, code: str, *diagnostics: str) -> None:
        self.code = code
        self.diagnostics = diagnostics
        super().__init__(code)


@dataclass(frozen=True)
class FrozenSnapshotAdmission:
    snapshot_rel_path: str
    snapshot_file_sha256: str
    snapshot_content_sha256: str
    request: CandidateRatingRequest
    rating_request_hash: str


def admit_frozen_second_candidate_snapshot(root: Path) -> FrozenSnapshotAdmission:
    path = root / SNAPSHOT_REL
    if not path.is_file():
        raise SecondCandidateAdmissionError("SNAPSHOT_FILE_MISSING", SNAPSHOT_REL)
    on_disk = file_sha256(path)
    if on_disk != SNAPSHOT_FILE_SHA256:
        raise SecondCandidateAdmissionError(
            "SNAPSHOT_FILE_SHA256_MISMATCH",
            on_disk,
            SNAPSHOT_FILE_SHA256,
        )
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    verify_snapshot_integrity(snapshot)
    content_digest = snapshot_content_digest(
        {k: v for k, v in snapshot.items() if k != "snapshot_sha256"}
    )
    if content_digest != SNAPSHOT_CONTENT_SHA256:
        raise SecondCandidateAdmissionError("SNAPSHOT_CONTENT_SHA256_MISMATCH")
    if snapshot.get("candidate_id") != scd.SECOND_CANDIDATE_ID:
        raise SecondCandidateAdmissionError("SNAPSHOT_CANDIDATE_ID_MISMATCH")
    if snapshot.get("rating_request_hash") != scd.EXPECTED_SECOND_RATING_REQUEST_HASH:
        raise SecondCandidateAdmissionError("SNAPSHOT_RATING_REQUEST_HASH_MISMATCH")
    request = load_request_from_snapshot_file(path)
    rating_hash = candidate_rating_request_hash(request)
    if rating_hash != scd.EXPECTED_SECOND_RATING_REQUEST_HASH:
        raise SecondCandidateAdmissionError("REQUEST_HASH_REPLAY_MISMATCH")
    return FrozenSnapshotAdmission(
        snapshot_rel_path=SNAPSHOT_REL,
        snapshot_file_sha256=on_disk,
        snapshot_content_sha256=SNAPSHOT_CONTENT_SHA256,
        request=request,
        rating_request_hash=rating_hash,
    )


def admit_second_candidate_prior_stage(
    root: Path,
    pin: PriorStagePin,
) -> dict[str, Any]:
    if pin.mesh_n not in (1, 2):
        raise SecondCandidateAdmissionError("PRIOR_STAGE_MESH_N_NOT_ADMITTED", str(pin.mesh_n))
    path = root / pin.rel_path
    digest = file_sha256(path)
    if digest != pin.expected_sha256:
        raise SecondCandidateAdmissionError(
            "PRIOR_STAGE_SHA256_MISMATCH",
            f"mesh_n={pin.mesh_n}",
        )
    receipt = load_stage_receipt(path)
    if receipt.get("candidate_id") != scd.SECOND_CANDIDATE_ID:
        raise SecondCandidateAdmissionError("PRIOR_CANDIDATE_ID_MISMATCH")
    if receipt.get("rating_request_hash") != scd.EXPECTED_SECOND_RATING_REQUEST_HASH:
        raise SecondCandidateAdmissionError("PRIOR_REQUEST_HASH_MISMATCH")
    if receipt.get("worker_status") != "TERMINAL_ACCEPTED":
        raise SecondCandidateAdmissionError("PRIOR_NOT_TERMINAL_ACCEPTED")
    if not receipt.get("terminal_tolerance_pass"):
        raise SecondCandidateAdmissionError("PRIOR_TERMINAL_TOLERANCE_FAIL")
    if not receipt.get("cell_closure_pass") or not receipt.get("energy_balance_pass"):
        raise SecondCandidateAdmissionError("PRIOR_PHYSICS_GATE_FAIL")
    expected_mesh = N1_MESH_RESULT_HASH if pin.mesh_n == 1 else N2_MESH_RESULT_HASH
    expected_shooting = N1_SHOOTING_ENTHALPY if pin.mesh_n == 1 else N2_SHOOTING_ENTHALPY
    expected_iters = N1_OUTER_ITERATIONS if pin.mesh_n == 1 else N2_OUTER_ITERATIONS
    if receipt.get("mesh_result_hash") != expected_mesh:
        raise SecondCandidateAdmissionError("PRIOR_MESH_HASH_MISMATCH")
    if receipt.get("shooting_enthalpy_for_rehydrate") != expected_shooting:
        raise SecondCandidateAdmissionError("PRIOR_SHOOTING_ENTHALPY_MISMATCH")
    if int(receipt.get("outer_iterations_for_rehydrate", 0)) != expected_iters:
        raise SecondCandidateAdmissionError("PRIOR_OUTER_ITERATIONS_MISMATCH")
    if receipt.get("request_snapshot_sha256") != SNAPSHOT_CONTENT_SHA256:
        raise SecondCandidateAdmissionError("PRIOR_SNAPSHOT_IDENTITY_MISMATCH")
    receipt["prior_stage_status"] = "VERIFIED_PRIOR_LIVE_STAGE"
    receipt["stage_receipt_rel_path"] = pin.rel_path
    receipt["stage_receipt_sha256"] = digest
    return receipt


def verify_n4_timeout_receipt_preserved(root: Path) -> None:
    path = root / N4_TIMEOUT_RECEIPT_REL
    digest = file_sha256(path)
    if digest != N4_TIMEOUT_RECEIPT_SHA256:
        raise SecondCandidateAdmissionError("N4_TIMEOUT_RECEIPT_SHA256_MISMATCH")
    receipt = load_stage_receipt(path)
    if receipt.get("worker_status") != "TIMEOUT":
        raise SecondCandidateAdmissionError("N4_NOT_TIMEOUT_RECORD")
    if receipt.get("blocked_code") != "OUTER_BOUNDARY_WALL_CLOCK_EXCEEDED":
        raise SecondCandidateAdmissionError("N4_BLOCKED_CODE_MISMATCH")


def replay_admitted_prior_mesh(
    request: CandidateRatingRequest,
    receipt: dict[str, Any],
    *,
    mesh_n: int,
    provider: CoolPropProvider | None = None,
) -> t173._MeshRun:
    context = t173._candidate_context(request)
    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    active = provider or CoolPropProvider(cache_size=2048)
    try:
        return replay_verified_prior_stage_mesh(
            mesh_n,
            shooting_enthalpy_j_kg=str(receipt["shooting_enthalpy_for_rehydrate"]),
            outer_iterations=int(receipt.get("outer_iterations_for_rehydrate", 0)),
            expected_mesh_hash=str(receipt["mesh_result_hash"]),
            provider=active,
            shell_authority=context.shell_authority,
        )
    except LiveMeshReplayError as exc:
        raise SecondCandidateAdmissionError(exc.code, *exc.diagnostics) from exc
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)


def verify_replay_physics(run: t173._MeshRun) -> None:
    if not verify_cell_closure(run) or not verify_energy_balance(run):
        raise SecondCandidateAdmissionError("REPLAY_PHYSICS_FAIL")
    if not t173._terminal_tolerance_pass(run):
        raise SecondCandidateAdmissionError("REPLAY_TERMINAL_TOLERANCE_FAIL")
