"""Admit full R13–R18 live mesh evidence chain for R19 rating."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
)
from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_live_ladder_continuation_r14.comparison_history_admission import (
    admit_prior_comparison_history,
    build_rolling_state_from_admitted_history,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.request_snapshot import (
    load_request_from_snapshot_file,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.stage_admission import (
    R18_TRIALS_JSONL_REL,
    R18_TRIALS_JSONL_SHA256,
    R19_PRIOR_PINS,
    admit_pinned_r17_snapshot,
    admit_prior_stage,
    file_sha256,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.verification import (
    verify_task174_binding,
)

RATING_REQUEST_HASH = "56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8"


@dataclass(frozen=True)
class LiveMeshEvidenceChain:
    request: CandidateRatingRequest
    rating_request_hash: str
    snapshot_rel_path: str
    mesh_comparisons: tuple[dict[str, Any], ...]
    mesh_stages: tuple[dict[str, Any], ...]
    evidence_chain_hashes: tuple[tuple[str, str], ...]
    ladder_status: str
    headroom_status: str


class LiveEvidenceAdmissionError(RuntimeError):
    def __init__(self, code: str, *diagnostics: str) -> None:
        self.code = code
        self.diagnostics = diagnostics
        super().__init__(code)


def admit_full_live_mesh_evidence(
    root: Path,
    *,
    candidate_id: str,
) -> LiveMeshEvidenceChain:
    if candidate_id != CANDIDATE_B_ID:
        raise LiveEvidenceAdmissionError("CANDIDATE_ID_NOT_ADMITTED", candidate_id)

    trials_path = root / R18_TRIALS_JSONL_REL
    if not trials_path.is_file():
        raise LiveEvidenceAdmissionError("R18_TRIALS_JSONL_MISSING", R18_TRIALS_JSONL_REL)
    if file_sha256(trials_path) != R18_TRIALS_JSONL_SHA256:
        raise LiveEvidenceAdmissionError("R18_TRIALS_JSONL_SHA256_MISMATCH")

    snapshot_rel = admit_pinned_r17_snapshot(
        root,
        candidate_id=candidate_id,
        rating_request_hash=RATING_REQUEST_HASH,
    )
    snapshot_path = root / snapshot_rel
    request = load_request_from_snapshot_file(snapshot_path)
    if request.candidate_id != candidate_id:
        raise LiveEvidenceAdmissionError("CANDIDATE_ID_MISMATCH")
    if not verify_task174_binding(request):
        raise LiveEvidenceAdmissionError("TASK174_BINDING_FAILED")

    comparisons = admit_prior_comparison_history(root)
    if len(comparisons) < 6:
        raise LiveEvidenceAdmissionError("INCOMPLETE_COMPARISON_HISTORY")
    rolling = build_rolling_state_from_admitted_history(comparisons)
    rolling.after_comparison_recorded(64)
    if rolling.ladder_status != "HEADROOM_PASS":
        raise LiveEvidenceAdmissionError(
            "LADDER_NOT_HEADROOM_PASS",
            f"status={rolling.ladder_status}",
        )

    stages: list[dict[str, Any]] = []
    chain_hashes: list[tuple[str, str]] = []
    for pin in R19_PRIOR_PINS:
        receipt = admit_prior_stage(
            root,
            pin,
            expected_request_hash=RATING_REQUEST_HASH,
            expected_candidate_id=candidate_id,
        )
        stages.append(receipt)
        chain_hashes.append((f"stage_mesh_n{pin.mesh_n}", pin.expected_sha256))

    headroom_cmp = comparisons[-1]
    if int(headroom_cmp.get("coarse_subdivisions", 0)) != 32:
        raise LiveEvidenceAdmissionError("HEADROOM_COMPARISON_COARSE_MISMATCH")
    if headroom_cmp.get("overall_status") != "PASS":
        raise LiveEvidenceAdmissionError("HEADROOM_COMPARISON_NOT_PASS")

    return LiveMeshEvidenceChain(
        request=request,
        rating_request_hash=RATING_REQUEST_HASH,
        snapshot_rel_path=snapshot_rel,
        mesh_comparisons=tuple(comparisons),
        mesh_stages=tuple(stages),
        evidence_chain_hashes=tuple(sorted(chain_hashes)),
        ladder_status=rolling.ladder_status,
        headroom_status="PASS",
    )
