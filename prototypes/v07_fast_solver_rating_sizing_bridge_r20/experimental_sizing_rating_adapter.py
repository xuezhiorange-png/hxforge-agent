"""Experimental Task173 sizing consumer for verified LIVE compact ratings."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

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
from prototypes.v07_fast_solver_live_rating_result_r19.live_result_hash import (
    LIVE_RATING_RESULT_R19_AUTHORITY_ID,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.geometry_summary import (
    geometry_summary_from_request,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.live_compact_rating import (
    LiveCompactAuthorityError,
    LiveCompactCandidateRating,
    live_compact_rating_hash,
    verify_live_compact_against_full,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.pinned_r19_full_gate import (
    PinnedR19FullGateError,
    assert_compact_matches_pinned_r19_full,
    load_and_verify_pinned_r19_full,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_pinned_identity import (
    RATING_REQUEST_HASH as PINNED_R19_RATING_REQUEST_HASH,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class ExperimentalSizingAdapterBlocked(StrictModel):
    status: Literal["BLOCKED"]
    blocked_code: str
    blocked_diagnostics: tuple[str, ...] = ()
    numerical_authority_status: Literal["CANDIDATE"] = "CANDIDATE"
    production_integration: Literal[False] = False


class ExperimentalSizingAdapterOutcome(StrictModel):
    status: Literal["EXPERIMENTAL_EVALUATED"]
    numerical_authority_status: Literal["CANDIDATE"]
    production_integration: Literal[False] = False
    production_validate_candidate_rating_usable: Literal[False]
    candidate_id: str
    candidate_hash: str
    geometry_task171_topology_id: str
    rated_duty_w: Decimal
    tube_dp_pa: Decimal
    shell_dp_pa: Decimal
    minimum_approach_temperature_k: Decimal
    duty_constraint: Literal["PASS", "BLOCKED"]
    tube_dp_constraint: Literal["PASS", "BLOCKED"]
    shell_dp_constraint: Literal["PASS", "BLOCKED"]
    mesh_sequence_gate: str
    full_rating_result_hash: str
    experimental_rating_authority_id: str
    task174_result_hash: str
    sizing_blockers: tuple[str, ...]
    result_provenance: tuple[tuple[str, str], ...]


def _blocked(code: str, *diag: str) -> ExperimentalSizingAdapterBlocked:
    return ExperimentalSizingAdapterBlocked(
        status="BLOCKED",
        blocked_code=code,
        blocked_diagnostics=diag,
    )


def _production_rating_authority_gaps(
    compact: LiveCompactCandidateRating,
) -> tuple[str, ...]:
    """Document why production sizing cannot consume this rating (no full mesh re-solve)."""
    return (
        "PRODUCTION_VALIDATE_CANDIDATE_RATING_NOT_INVOKED_FOR_LIVE_EXPERIMENTAL",
        "PRODUCTION_RATING_REQUIRES_R2A_MESH_SEQUENCE_AND_VALIDATED_AUTHORITY",
        f"experimental_rating_authority_id={compact.experimental_rating_authority_id}",
        "numerical_authority_status=CANDIDATE",
    )


def _verify_sizing_requirement_canonical_hash(
    requirement: SizingRequirementAuthority,
) -> ExperimentalSizingAdapterBlocked | None:
    projection = requirement.model_dump(mode="json", exclude={"canonical_hash"})
    if requirement.canonical_hash != canonical_sha256(projection):
        return _blocked("SIZING_REQUIREMENT_CANONICAL_HASH_MISMATCH")
    return None


def experimental_sizing_rating_adapter(
    root: Path,
    compact: LiveCompactCandidateRating,
    requirement: SizingRequirementAuthority,
) -> ExperimentalSizingAdapterOutcome | ExperimentalSizingAdapterBlocked:
    req_gate = _verify_sizing_requirement_canonical_hash(requirement)
    if req_gate is not None:
        return req_gate

    if compact.compact_result_hash != live_compact_rating_hash(compact):
        return _blocked("COMPACT_HASH_REPLAY_MISMATCH")

    if compact.experimental_rating_authority_id != LIVE_RATING_RESULT_R19_AUTHORITY_ID:
        return _blocked("COMPACT_AUTHORITY_NOT_LIVE_R19")

    if compact.execution_mode != "LIVE_NUMERICAL_SOLVE":
        return _blocked("COMPACT_EXECUTION_MODE_NOT_LIVE")

    if compact.mesh_sequence_gate != "PASS" or not compact.strict_replay_pass:
        return _blocked("MESH_CONVERGENCE_GATE_FAILED")

    try:
        full, audit, full_sha = load_and_verify_pinned_r19_full(root)
        assert_compact_matches_pinned_r19_full(compact, audit)
    except PinnedR19FullGateError as exc:
        return _blocked("SIZING_ADAPTER_PINNED_FULL_GATE_FAILED", exc.code, *exc.diagnostics)

    try:
        snapshot_rel = dict(full.provenance).get("snapshot_rel_path")
        if not snapshot_rel:
            return _blocked("FULL_MISSING_SNAPSHOT_PROVENANCE")
        request = load_request_from_snapshot_file(root / snapshot_rel)
        snapshot_rating_hash = candidate_rating_request_hash(request)
        if snapshot_rating_hash != PINNED_R19_RATING_REQUEST_HASH:
            return _blocked(
                "SNAPSHOT_RATING_REQUEST_HASH_NOT_PINNED_R19",
                snapshot_rating_hash,
                PINNED_R19_RATING_REQUEST_HASH,
            )
        geom = geometry_summary_from_request(request)
        verify_live_compact_against_full(
            compact,
            full,
            full_file_sha256=full_sha,
            geometry_summary=geom,
        )
    except (LiveCompactAuthorityError, ValueError) as exc:
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
        return _blocked("COMPACT_DUTY_NOT_BOUND_TO_PINNED_FULL")
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
        ("adapter", "experimental_sizing_rating_adapter.v1"),
        ("rating_execution_mode", compact.execution_mode),
        ("experimental_rating_authority_id", compact.experimental_rating_authority_id),
        ("full_rating_result_hash", compact.full_result_hash),
        ("task174_result_hash", compact.task174_result_hash),
        ("production_rating_gaps", ";".join(production_gaps)),
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


def authority_open_items() -> tuple[dict[str, Any], ...]:
    """Explicit list of authority gaps (not production VALIDATED)."""
    return (
        {
            "item": "NUMERICAL_AUTHORITY_STATUS",
            "state": "CANDIDATE",
            "note": "Live rating is experimental; not promoted to production VALIDATED.",
        },
        {
            "item": "PRODUCTION_VALIDATE_CANDIDATE_RATING",
            "state": "NOT_USABLE_FOR_LIVE_RATING",
            "note": "Sizing orchestrator requires production CandidateRatingSuccessResult.",
        },
        {
            "item": "SIZING_RESULT_VALIDATED",
            "state": "NOT_CLAIMED",
            "note": "Adapter outcome is EXPERIMENTAL_EVALUATED only.",
        },
        {
            "item": "R19_LEGACY_COMPACT_AUTHORITY",
            "state": "R11_AUTHORITY_ID_ON_DISK",
            "note": "Legacy COMPACT_LIVE_RATING.json retained; use live compact v1 for sizing.",
        },
    )


def load_verified_live_compact_from_r19_audit(
    root: Path,
) -> tuple[LiveCompactCandidateRating, dict[str, Any]]:
    from prototypes.v07_fast_solver_rating_sizing_bridge_r20.live_compact_rating import (
        build_live_compact_from_full,
    )
    from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_pinned_identity import (
        R19_FULL_JSON_REL,
    )

    full, audit, full_sha = load_and_verify_pinned_r19_full(root)
    snapshot_rel = dict(full.provenance).get("snapshot_rel_path")
    if not snapshot_rel:
        raise LiveCompactAuthorityError("FULL_MISSING_SNAPSHOT_PROVENANCE")
    request = load_request_from_snapshot_file(root / snapshot_rel)
    geom = geometry_summary_from_request(request)
    compact = build_live_compact_from_full(
        full,
        trajectory_artifact_path=R19_FULL_JSON_REL,
        trajectory_file_sha256=full_sha,
        geometry_summary=geom,
    )
    verify_live_compact_against_full(
        compact,
        full,
        full_file_sha256=full_sha,
        geometry_summary=geom,
    )
    return compact, audit
