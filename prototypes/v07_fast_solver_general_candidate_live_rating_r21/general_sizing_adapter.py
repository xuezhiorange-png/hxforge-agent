"""Experimental sizing adapter for general (non–pinned-R19) live compact ratings."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    candidate_rating_request_hash,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.models import (
    SizingRequirementAuthority,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.request_snapshot import (
    load_request_from_snapshot_file,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.geometry_summary import (
    geometry_summary_from_request,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.experimental_sizing_rating_adapter import (
    ExperimentalSizingAdapterBlocked,
    ExperimentalSizingAdapterOutcome,
    _production_rating_authority_gaps,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.live_compact_rating import (
    LiveCompactAuthorityError,
    LiveCompactCandidateRating,
    live_compact_rating_hash,
    verify_live_compact_against_full,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_full_file_audit import file_sha256
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalCandidateRatingResult,
)


def _blocked(code: str, *diag: str) -> ExperimentalSizingAdapterBlocked:
    return ExperimentalSizingAdapterBlocked(
        status="BLOCKED",
        blocked_code=code,
        blocked_diagnostics=diag,
    )


def experimental_general_sizing_rating_adapter(
    root: Path,
    compact: LiveCompactCandidateRating,
    requirement: SizingRequirementAuthority,
    *,
    full_rel_path: str,
) -> ExperimentalSizingAdapterOutcome | ExperimentalSizingAdapterBlocked:
    projection = requirement.model_dump(mode="json", exclude={"canonical_hash"})
    if requirement.canonical_hash != canonical_sha256(projection):
        return _blocked("SIZING_REQUIREMENT_CANONICAL_HASH_MISMATCH")

    if compact.compact_result_hash != live_compact_rating_hash(compact):
        return _blocked("COMPACT_HASH_REPLAY_MISMATCH")

    if compact.execution_mode != "LIVE_NUMERICAL_SOLVE":
        return _blocked("COMPACT_EXECUTION_MODE_NOT_LIVE")

    if compact.mesh_sequence_gate != "PASS" or not compact.strict_replay_pass:
        return _blocked("MESH_CONVERGENCE_GATE_FAILED")

    full_path = root / full_rel_path
    if not full_path.is_file():
        return _blocked("GENERAL_FULL_RATING_FILE_MISSING", full_rel_path)
    on_disk_sha = file_sha256(full_path)
    try:
        full = ExperimentalCandidateRatingResult.model_validate_json(
            full_path.read_text(encoding="utf-8"),
            strict=True,
        )
    except Exception as exc:  # noqa: BLE001
        return _blocked("GENERAL_FULL_RATING_PARSE_FAILED", str(exc))

    if full.result_hash != compact.full_result_hash:
        return _blocked("COMPACT_FULL_RESULT_HASH_MISMATCH")
    if compact.full_trajectory_artifact.path != full_rel_path:
        return _blocked("COMPACT_FULL_PATH_MISMATCH")
    if compact.full_trajectory_artifact.file_sha256 != on_disk_sha:
        return _blocked("COMPACT_FULL_FILE_SHA256_MISMATCH")

    try:
        snapshot_rel = dict(full.provenance).get("snapshot_rel_path")
        if not snapshot_rel:
            return _blocked("FULL_MISSING_SNAPSHOT_PROVENANCE")
        request = load_request_from_snapshot_file(root / snapshot_rel)
        if candidate_rating_request_hash(request) != full.rating_request_hash:
            return _blocked("SNAPSHOT_RATING_REQUEST_HASH_MISMATCH")
        geom = geometry_summary_from_request(request)
        verify_live_compact_against_full(
            compact,
            full,
            full_file_sha256=on_disk_sha,
            geometry_summary=geom,
        )
    except (LiveCompactAuthorityError, ValueError, OSError) as exc:
        return _blocked("COMPACT_FULL_AUTHORITY_INCONSISTENT", str(exc))

    if request.candidate_id != compact.candidate_id:
        return _blocked("SNAPSHOT_CANDIDATE_ID_MISMATCH")
    if request.task174_result.result_hash != compact.task174_result_hash:
        return _blocked("TASK174_BINDING_MISMATCH")

    production_gaps = _production_rating_authority_gaps(compact)
    task174 = request.task174_result
    tube_dp = task174.modeled_total_tube_side_pressure_drop_pa
    shell_dp = task174.bell_total_shell_pressure_drop_pa
    rated_duty = full.total_duty_w
    if rated_duty != compact.total_duty_w:
        return _blocked("COMPACT_DUTY_NOT_BOUND_TO_FULL")

    duty_pass = rated_duty >= requirement.required_duty_w
    tube_pass = tube_dp <= requirement.max_tube_dp_pa
    shell_pass = shell_dp <= requirement.max_shell_dp_pa
    blockers = tuple(
        code
        for code, passed in (
            ("DUTY_BELOW_REQUIRED", duty_pass),
            ("TUBE_DP_ABOVE_MAXIMUM", tube_pass),
            ("SHELL_DP_ABOVE_MAXIMUM", shell_pass),
        )
        if not passed
    )
    if blockers:
        return _blocked("SIZING_ENGINEERING_CONSTRAINTS_FAILED", *blockers)

    provenance: tuple[tuple[str, str], ...] = (
        ("adapter", "experimental_general_sizing_rating_adapter.v1"),
        ("rating_execution_mode", compact.execution_mode),
        ("experimental_rating_authority_id", compact.experimental_rating_authority_id),
        ("full_rating_result_hash", compact.full_result_hash),
        ("task174_result_hash", compact.task174_result_hash),
        ("production_rating_gaps", ";".join(production_gaps)),
        ("multi_candidate_sizing_verified", "false"),
    )
    return ExperimentalSizingAdapterOutcome(
        status="EXPERIMENTAL_EVALUATED",
        numerical_authority_status="CANDIDATE",
        production_integration=False,
        production_validate_candidate_rating_usable=False,
        candidate_id=compact.candidate_id,
        candidate_hash=compact.candidate_hash,
        geometry_task171_topology_id=compact.geometry_summary.task171_topology_id,
        rated_duty_w=rated_duty,
        tube_dp_pa=tube_dp,
        shell_dp_pa=shell_dp,
        minimum_approach_temperature_k=compact.minimum_approach_temperature_k,
        duty_constraint="PASS",
        tube_dp_constraint="PASS",
        shell_dp_constraint="PASS",
        mesh_sequence_gate=compact.mesh_sequence_gate,
        full_rating_result_hash=compact.full_result_hash,
        experimental_rating_authority_id=compact.experimental_rating_authority_id,
        task174_result_hash=compact.task174_result_hash,
        sizing_blockers=(),
        result_provenance=provenance,
    )
