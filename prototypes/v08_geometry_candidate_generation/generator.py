"""V08-02 geometry candidate enumeration and structural validation."""

# ruff: noqa: E501

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import candidate_space_hash
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import DIMENSION_ORDER
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.discrete_space import (
    DEFAULT_V08_DISCRETE_SPACE_PATH,
    V08_GEOMETRY_SOURCE_AUTHORITY,
    format_engineering_decimal,
    load_v08_discrete_space,
)
from prototypes.v08_geometry_candidate_generation.errors import V08GeometryGenerationBlocked
from prototypes.v08_geometry_candidate_generation.models import (
    V08GeometryCandidateRecord,
    V08GeometryGenerationResult,
    V08GeometryRejectionRecord,
)
from prototypes.v08_geometry_candidate_generation.task168_builder import (
    build_v08_task168_request,
    filter_discrete_space_by_envelope,
)

MAX_COMBINATIONS_TO_EVALUATE = 512
MAX_VALID_CANDIDATES = 32


def _geometry_projection_hash(
    *,
    shell_inside_diameter_m: str,
    tube_length_m: str,
    baffle_spacing_m: str,
    tube_pass_count: int,
    physical_tube_count: int,
) -> str:
    return canonical_sha256(
        {
            "shell_inside_diameter_m": shell_inside_diameter_m,
            "tube_length_m": tube_length_m,
            "baffle_spacing_m": baffle_spacing_m,
            "tube_pass_count": str(tube_pass_count),
            "physical_tube_count": str(physical_tube_count),
        }
    )


def _preserved_search_parameters(handoff: V08SolverHandoffV1) -> dict[str, str]:
    out = dict(handoff.consumable_parameters)
    out.update(handoff.pressure_limits_pa)
    return out


def generate_geometry_candidates(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    discrete_space_path: Path | None = None,
    max_combinations: int = MAX_COMBINATIONS_TO_EVALUATE,
    max_valid_candidates: int = MAX_VALID_CANDIDATES,
) -> V08GeometryGenerationResult:
    """Enumerate structurally valid shell-and-tube geometry candidates for a user case."""
    try:
        space = load_v08_discrete_space(discrete_space_path)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        blocked = V08GeometryGenerationBlocked(
            code="BLOCKED_GEOMETRY_SOURCE",
            message=str(exc),
            evidence={"path": str(discrete_space_path or DEFAULT_V08_DISCRETE_SPACE_PATH)},
        )
        return _blocked_result(normalized, handoff, blocked, space=None)

    filtered_space, envelope_msgs = filter_discrete_space_by_envelope(
        space, normalized.design_envelope
    )
    base_payload = _base_result_fields(normalized, handoff, filtered_space, envelope_msgs)

    if not filtered_space.shell_inside_diameters_m or not filtered_space.tube_baffle_ladder:
        result = V08GeometryGenerationResult(
            **base_payload,
            status="NO_STRUCTURAL_CANDIDATE",
            rejections=(
                V08GeometryRejectionRecord(
                    candidate_id="ENVELOPE_FILTER",
                    failure_stage="V08_ENVELOPE_FILTER",
                    reason_codes=("NO_AUTHORIZED_GEOMETRY_AFTER_ENVELOPE",),
                    evidence={
                        "shell_count": str(len(filtered_space.shell_inside_diameters_m)),
                        "ladder_steps": str(len(filtered_space.tube_baffle_ladder)),
                    },
                ),
            ),
            result_hash="",
        )
        return _finalize_hash(result)

    try:
        t168 = build_v08_task168_request(normalized, handoff, filtered_space)
    except ValueError as exc:
        blocked = V08GeometryGenerationBlocked(
            code="BLOCKED_GEOMETRY_SOURCE",
            message=str(exc),
            evidence={"authority": filtered_space.authority_id},
        )
        return _blocked_result(normalized, handoff, blocked, space=filtered_space)

    authorities = task168._authority_map(t168)
    dimensions = tuple(
        task168._sort_values(authorities[role].values)
        for role in DIMENSION_ORDER
        if role != "SHELL_GEOMETRY_ID"
    )
    space_hash = candidate_space_hash(t168, t168.discrete_candidate_set_authorities)
    allowed_ladder = filtered_space.allowed_ladder_keys

    valid: list[V08GeometryCandidateRecord] = []
    rejections: list[V08GeometryRejectionRecord] = []
    seen_geometry: set[str] = set()
    evaluated = 0

    for combination in itertools.product(t168.shell_geometry_catalog.records, *dimensions):
        if evaluated >= max_combinations:
            rejections.append(
                V08GeometryRejectionRecord(
                    candidate_id="SEARCH_BUDGET",
                    failure_stage="V08_SEARCH_BUDGET",
                    reason_codes=("MAX_COMBINATIONS_REACHED",),
                    evidence={"max_combinations": str(max_combinations)},
                )
            )
            break
        evaluated += 1
        candidate = task168._candidate(t168, authorities, combination[0], tuple(combination[1:]))
        ladder_key = (
            format_engineering_decimal(candidate.tube_length_m),
            format_engineering_decimal(candidate.baffle_spacing_m),
            int(candidate.baffle_count),
        )
        if ladder_key not in allowed_ladder:
            rejections.append(
                V08GeometryRejectionRecord(
                    candidate_id=candidate.candidate_id,
                    failure_stage="V08_LADDER_FILTER",
                    reason_codes=("UNAUTHORIZED_TUBE_BAFFLE_PAIR",),
                    evidence={
                        "tube_length_m": ladder_key[0],
                        "baffle_spacing_m": ladder_key[1],
                        "baffle_count": str(ladder_key[2]),
                    },
                )
            )
            continue

        shell_d = str(combination[0].shell_inside_diameter_m)
        structural = task168._structural_blockers(candidate)
        if structural:
            rejections.append(
                V08GeometryRejectionRecord(
                    candidate_id=candidate.candidate_id,
                    failure_stage="TASK168_STRUCTURAL",
                    reason_codes=tuple(str(item.code) for item in structural),
                    evidence={"shell_inside_diameter_m": shell_d},
                )
            )
            continue

        bundle, stage_failure, _ = task168._execute_candidate_chain(
            t168,
            candidate,
            combination[0],
            include_legacy_task162=False,
            include_legacy_task168_rating_dependencies=False,
            preserve_baffle_orientation_sequence=False,
        )
        if stage_failure is not None:
            rejections.append(
                V08GeometryRejectionRecord(
                    candidate_id=candidate.candidate_id,
                    failure_stage=str(stage_failure.stage.value),
                    reason_codes=(str(stage_failure.code),),
                    evidence={
                        "shell_inside_diameter_m": shell_d,
                        "message": stage_failure.message,
                    },
                )
            )
            continue

        tube_count = int(bundle.task021_layout.physical_tube_count)
        geom_hash = _geometry_projection_hash(
            shell_inside_diameter_m=shell_d,
            tube_length_m=format_engineering_decimal(candidate.tube_length_m),
            baffle_spacing_m=format_engineering_decimal(candidate.baffle_spacing_m),
            tube_pass_count=int(candidate.tube_pass_count),
            physical_tube_count=tube_count,
        )
        if geom_hash in seen_geometry:
            continue
        seen_geometry.add(geom_hash)
        valid.append(
            V08GeometryCandidateRecord(
                rank=0,
                candidate_id=candidate.candidate_id,
                candidate_hash=candidate.candidate_hash,
                geometry_projection_hash=geom_hash,
                shell_inside_diameter_m=shell_d,
                shell_geometry_id=combination[0].geometry_id,
                tube_outer_diameter_m=format_engineering_decimal(candidate.tube_outer_diameter_m),
                tube_wall_thickness_m=format_engineering_decimal(candidate.tube_wall_thickness_m),
                tube_pitch_m=format_engineering_decimal(candidate.tube_pitch_m),
                tube_length_m=format_engineering_decimal(candidate.tube_length_m),
                tube_pass_count=int(candidate.tube_pass_count),
                physical_tube_count=tube_count,
                baffle_spacing_m=format_engineering_decimal(candidate.baffle_spacing_m),
                baffle_count=int(candidate.baffle_count),
                baffle_type=str(candidate.baffle_type),
                source_authority_id=filtered_space.authority_id,
                source_content_hash=filtered_space.content_hash,
            )
        )
        if len(valid) >= max_valid_candidates:
            break

    valid_sorted = tuple(
        _with_rank(index + 1, row)
        for index, row in enumerate(
            sorted(
                valid,
                key=lambda row: (
                    row.shell_inside_diameter_m,
                    row.tube_length_m,
                    row.baffle_spacing_m,
                    row.physical_tube_count,
                    row.candidate_id,
                ),
            )
        )
    )

    status = "OK" if valid_sorted else "NO_STRUCTURAL_CANDIDATE"
    result = V08GeometryGenerationResult(
        **base_payload,
        status=status,
        candidate_space_hash=space_hash,
        candidates=valid_sorted,
        rejections=tuple(rejections),
        distinct_valid_geometry_count=len({c.geometry_projection_hash for c in valid_sorted}),
        result_hash="",
        warnings=handoff.warnings,
    )
    return _finalize_hash(result)


def _with_rank(rank: int, row: V08GeometryCandidateRecord) -> V08GeometryCandidateRecord:
    return row.model_copy(update={"rank": rank})


def _base_result_fields(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    space: Any,
    envelope_msgs: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "engineering_case_id": normalized.engineering_case_id,
        "normalized_input_hash": handoff.normalized_input_hash,
        "geometry_source_authority": space.authority_id,
        "geometry_source_content_hash": space.content_hash,
        "downstream_readiness": handoff.downstream_readiness,
        "preserved_search_parameters": _preserved_search_parameters(handoff),
        "envelope_filters_applied": envelope_msgs,
    }


def _blocked_result(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    blocked: V08GeometryGenerationBlocked,
    *,
    space: Any | None,
) -> V08GeometryGenerationResult:
    authority = space.authority_id if space is not None else V08_GEOMETRY_SOURCE_AUTHORITY
    content_hash = space.content_hash if space is not None else ""
    result = V08GeometryGenerationResult(
        engineering_case_id=normalized.engineering_case_id,
        normalized_input_hash=handoff.normalized_input_hash,
        geometry_source_authority=authority,
        geometry_source_content_hash=content_hash,
        downstream_readiness=handoff.downstream_readiness,
        preserved_search_parameters=_preserved_search_parameters(handoff),
        status="BLOCKED_GEOMETRY_SOURCE",
        rejections=(
            V08GeometryRejectionRecord(
                candidate_id="GEOMETRY_SOURCE",
                failure_stage="V08_GEOMETRY_SOURCE",
                reason_codes=(blocked.code,),
                evidence={"message": blocked.message, **blocked.evidence},
            ),
        ),
        result_hash="",
        warnings=handoff.warnings,
    )
    return _finalize_hash(result)


def _finalize_hash(result: V08GeometryGenerationResult) -> V08GeometryGenerationResult:
    payload = result.model_dump(mode="json")
    payload.pop("result_hash", None)
    digest = canonical_sha256(payload)
    return result.model_copy(update={"result_hash": digest})
