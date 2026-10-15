"""Pinned prior live stage admission (VERIFIED_PRIOR_LIVE_STAGE)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_live_ladder_continuation_r14.request_snapshot import (
    snapshot_content_digest,
    verify_snapshot_integrity,
)
from prototypes.v07_fast_solver_live_rating_ladder_r13.stage_persistence import load_stage_receipt

R13_STAGE_DIR_REL = (
    "docs/tasks/evidence/V07-FAST-SOLVER-live-rating-ladder-r13-stages-20261015T042649Z"
)
R13_N1_STAGE_SHA256 = "8c4e18c0f8286d356acb6a5502f09c68a42e242ded7c41838cbfc76fadd1fe95"
R13_N2_STAGE_SHA256 = "1cb23fc1805f7946c453eb546a9e41df52d1c1c12e17ec8ea80360487f8c593c"
R13_RATING_REQUEST_HASH = "56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8"
R13_CANDIDATE_ID = "e152cca9-fd5d-59ca-9b46-1df574eee841"
R13_RESULT_SHA256 = "4464e7c8d70d3338a484e42e5b53a1babe39f2943c4f687aa6ff1600037f69dd"

R14_STAGE_DIR_REL = "docs/tasks/evidence/V07-FAST-SOLVER-live-ladder-r14-stages-20261015T063207Z"
R14_N4_STAGE_SHA256 = "0e5ff519545c16b2d9f16616b382c9894cc6eb60a3e5a9ebbe021f58a0ac18a2"
R14_SNAPSHOT_DIR_REL = (
    "docs/tasks/evidence/V07-FAST-SOLVER-live-ladder-r14-snapshot-20261015T063207Z"
)
R14_SNAPSHOT_CONTENT_SHA256 = "eff11f541e1a6a3f3bc93cb3c11ac5255b2e270ca9bf9a64a6271e253d4b5641"
R14_SNAPSHOT_FILE_SHA256 = "4f8535667ff7c85c3044e45aff623c68dc3cad0aebca3fd9e0f4dcf83f7fa86e"
R14_N4_MESH_HASH = "6b20ea36786e817fe83b92876e8b3768d703e2262f68a913243d2196d4c43f2e"
R14_N4_SHOOTING_ENTHALPY = "107515.23962914693046195797622203826904296875"
R14_N4_OUTER_ITERATIONS = 28


@dataclass(frozen=True)
class PriorStagePin:
    mesh_n: int
    rel_path: str
    expected_sha256: str


DEFAULT_PRIOR_PINS: tuple[PriorStagePin, ...] = (
    PriorStagePin(1, f"{R13_STAGE_DIR_REL}/live-mesh-n1-receipt.json", R13_N1_STAGE_SHA256),
    PriorStagePin(2, f"{R13_STAGE_DIR_REL}/live-mesh-n2-receipt.json", R13_N2_STAGE_SHA256),
)

R15_STAGE_DIR_REL = "docs/tasks/evidence/V07-FAST-SOLVER-live-n8-r15-stages-20261015T075153Z"
R15_N8_STAGE_SHA256 = "89ef7d54c3df0d4e7eca9089b3c33e0ecff42acaaed541c98af80bb23c083718"
R15_SNAPSHOT_DIR_REL = "docs/tasks/evidence/V07-FAST-SOLVER-live-n8-r15-snapshot-20261015T075153Z"
R15_SNAPSHOT_CONTENT_SHA256 = "9e59a4606e794b4968e541bef42b66a85766ed6d189bf78aaf2425f167daff57"
R15_N8_MESH_HASH = "6de283cf8249b228db00a7404c4c5fc0bab08c61c6c2ee2a4cbfd145433fcb9c"
R15_N8_SHOOTING_ENTHALPY = "107515.2019112278133458800613880157470703125"
R15_N8_OUTER_ITERATIONS = 27

R15_PRIOR_PINS: tuple[PriorStagePin, ...] = (
    *DEFAULT_PRIOR_PINS,
    PriorStagePin(4, f"{R14_STAGE_DIR_REL}/live-mesh-n4-receipt.json", R14_N4_STAGE_SHA256),
)

R16_PRIOR_PINS: tuple[PriorStagePin, ...] = (
    *R15_PRIOR_PINS,
    PriorStagePin(8, f"{R15_STAGE_DIR_REL}/live-mesh-n8-receipt.json", R15_N8_STAGE_SHA256),
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def admit_prior_stage(
    root: Path,
    pin: PriorStagePin,
    *,
    expected_request_hash: str,
    expected_candidate_id: str,
) -> dict[str, Any]:
    path = root / pin.rel_path
    if not path.is_file():
        raise FileNotFoundError(pin.rel_path)
    digest = file_sha256(path)
    if digest != pin.expected_sha256:
        raise ValueError(
            "EVIDENCE_HASH_MISMATCH "
            f"mesh_n={pin.mesh_n} expected={pin.expected_sha256} actual={digest}"
        )
    receipt = load_stage_receipt(path)
    if receipt.get("mesh_n") != pin.mesh_n:
        raise ValueError("stage mesh_n mismatch")
    if receipt.get("candidate_id") != expected_candidate_id:
        raise ValueError("prior stage candidate_id mismatch")
    if receipt.get("rating_request_hash") != expected_request_hash:
        raise ValueError("prior stage rating_request_hash mismatch")
    if receipt.get("worker_status") != "TERMINAL_ACCEPTED":
        raise ValueError("prior stage not TERMINAL_ACCEPTED")
    if not receipt.get("terminal_tolerance_pass"):
        raise ValueError("prior stage terminal_tolerance_pass false")
    if not receipt.get("cell_closure_pass"):
        raise ValueError("prior stage cell_closure_pass false")
    if not receipt.get("energy_balance_pass"):
        raise ValueError("prior stage energy_balance_pass false")
    if pin.mesh_n == 4:
        if receipt.get("mesh_result_hash") != R14_N4_MESH_HASH:
            raise ValueError("R14 n4 mesh_result_hash mismatch")
        if receipt.get("shooting_enthalpy_for_rehydrate") != R14_N4_SHOOTING_ENTHALPY:
            raise ValueError("R14 n4 shooting enthalpy mismatch")
        if int(receipt.get("outer_iterations_for_rehydrate", 0)) != R14_N4_OUTER_ITERATIONS:
            raise ValueError("R14 n4 outer iterations mismatch")
    if pin.mesh_n == 8:
        if receipt.get("mesh_result_hash") != R15_N8_MESH_HASH:
            raise ValueError("R15 n8 mesh_result_hash mismatch")
        if receipt.get("shooting_enthalpy_for_rehydrate") != R15_N8_SHOOTING_ENTHALPY:
            raise ValueError("R15 n8 shooting enthalpy mismatch")
        if int(receipt.get("outer_iterations_for_rehydrate", 0)) != R15_N8_OUTER_ITERATIONS:
            raise ValueError("R15 n8 outer iterations mismatch")
    receipt["prior_stage_status"] = "VERIFIED_PRIOR_LIVE_STAGE"
    receipt["stage_receipt_rel_path"] = pin.rel_path
    receipt["stage_receipt_sha256"] = digest
    return receipt


def admit_pinned_r14_snapshot(root: Path, *, candidate_id: str, rating_request_hash: str) -> str:
    """Return relative snapshot path after content/file SHA256 admission."""
    safe_id = candidate_id.replace("/", "_")
    pattern = f"live-rating-request-{safe_id}-{rating_request_hash[:16]}.json"
    path = root / R14_SNAPSHOT_DIR_REL / pattern
    if not path.is_file():
        legacy = root / R14_SNAPSHOT_DIR_REL / "candidate-b-live-request-snapshot.json"
        if legacy.is_file():
            path = legacy
        else:
            raise FileNotFoundError(str(path.relative_to(root)))
    file_digest = file_sha256(path)
    if file_digest != R14_SNAPSHOT_FILE_SHA256:
        raise ValueError("R14 snapshot file SHA256 mismatch")
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    verify_snapshot_integrity(snapshot)
    body = {k: v for k, v in snapshot.items() if k != "snapshot_sha256"}
    if snapshot_content_digest(body) != R14_SNAPSHOT_CONTENT_SHA256:
        raise ValueError("R14 snapshot content SHA256 mismatch")
    if snapshot.get("candidate_id") != candidate_id:
        raise ValueError("snapshot candidate_id mismatch")
    if snapshot.get("rating_request_hash") != rating_request_hash:
        raise ValueError("snapshot rating_request_hash mismatch")
    return str(path.relative_to(root))


def admit_pinned_r15_snapshot(root: Path, *, candidate_id: str, rating_request_hash: str) -> str:
    safe_id = candidate_id.replace("/", "_")
    pattern = f"live-rating-request-{safe_id}-{rating_request_hash[:16]}.json"
    path = root / R15_SNAPSHOT_DIR_REL / pattern
    if not path.is_file():
        raise FileNotFoundError(str(path.relative_to(root)))
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    verify_snapshot_integrity(snapshot)
    body = {k: v for k, v in snapshot.items() if k != "snapshot_sha256"}
    if snapshot_content_digest(body) != R15_SNAPSHOT_CONTENT_SHA256:
        raise ValueError("R15 snapshot content SHA256 mismatch")
    if snapshot.get("candidate_id") != candidate_id:
        raise ValueError("snapshot candidate_id mismatch")
    if snapshot.get("rating_request_hash") != rating_request_hash:
        raise ValueError("snapshot rating_request_hash mismatch")
    return str(path.relative_to(root))
