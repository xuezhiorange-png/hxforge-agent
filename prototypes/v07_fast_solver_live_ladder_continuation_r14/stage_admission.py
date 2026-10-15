"""Pinned prior live stage admission (VERIFIED_PRIOR_LIVE_STAGE)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_live_rating_ladder_r13.stage_persistence import load_stage_receipt

R13_STAGE_DIR_REL = (
    "docs/tasks/evidence/V07-FAST-SOLVER-live-rating-ladder-r13-stages-20261015T042649Z"
)
R13_N1_STAGE_SHA256 = "8c4e18c0f8286d356acb6a5502f09c68a42e242ded7c41838cbfc76fadd1fe95"
R13_N2_STAGE_SHA256 = "1cb23fc1805f7946c453eb546a9e41df52d1c1c12e17ec8ea80360487f8c593c"
R13_RATING_REQUEST_HASH = "56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8"
R13_CANDIDATE_ID = "e152cca9-fd5d-59ca-9b46-1df574eee841"
R13_RESULT_SHA256 = "4464e7c8d70d3338a484e42e5b53a1babe39f2943c4f687aa6ff1600037f69dd"


@dataclass(frozen=True)
class PriorStagePin:
    mesh_n: int
    rel_path: str
    expected_sha256: str


DEFAULT_PRIOR_PINS: tuple[PriorStagePin, ...] = (
    PriorStagePin(1, f"{R13_STAGE_DIR_REL}/live-mesh-n1-receipt.json", R13_N1_STAGE_SHA256),
    PriorStagePin(2, f"{R13_STAGE_DIR_REL}/live-mesh-n2-receipt.json", R13_N2_STAGE_SHA256),
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
    receipt["prior_stage_status"] = "VERIFIED_PRIOR_LIVE_STAGE"
    receipt["stage_receipt_rel_path"] = pin.rel_path
    receipt["stage_receipt_sha256"] = digest
    return receipt
