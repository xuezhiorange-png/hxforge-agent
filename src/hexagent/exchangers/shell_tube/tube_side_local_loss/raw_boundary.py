"""R00-R10 raw input boundary validation pipeline.

§26 — Raw-boundary validation order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hexagent.exchangers.shell_tube.tube_side_local_loss.blocker_registry import (
    Task028BlockerCode,
    Task028BlockerEntry,
    _Task028PendingBlocker,
    collapse_blockers,
    emit_blocker,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.enums import (
    KNOWN_UNSUPPORTED_RAW_COMPONENT_TOKENS,
    CoefficientPermissionStatus,
    LossCoefficientConvention,
    Task028ApplicabilityAssertion,
    Task028ComponentFlowDirectionAssertion,
    Task028ComponentType,
    Task028RequestFlowDirectionAssertion,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.raw_projection import (
    Task028RawProjection,
    encode_raw_projection,
)


@dataclass(frozen=True)
class RawBoundaryResult:
    """Result of raw boundary validation.

    Either blocked (non-None) or typed request data (None + typed data).
    """

    blocked: bool
    typed_data: dict[str, Any] | None
    blockers: tuple[Task028BlockerEntry, ...]
    raw_request_projection: Task028RawProjection | None


# R00-R10 required top-level fields
_REQUIRED_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "schema_version",
    "profile_id",
    "task025_valid_result",
    "task026_success_result",
    "property_snapshot",
    "property_snapshot_hash",
    "constant_density_path_assertion",
    "zero_net_elevation_change_assertion",
    "flow_direction_assertion",
    "component_authorities",
    "request_hash",
)


def validate_raw_boundary(
    raw_input: Any,
) -> RawBoundaryResult:
    """R00-R10 raw input boundary validation pipeline.

    Returns RawBoundaryResult with blocked=True if validation fails,
    blocked=False with typed_data if validation succeeds.
    """
    pending_blockers: list[_Task028PendingBlocker] = []
    typed_data: dict[str, Any] = {}

    # R00: Capture raw projection
    raw_request_projection = encode_raw_projection("REQUEST", raw_input)

    # R01: Validate top-level mapping
    if not isinstance(raw_input, dict):
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                "raw_input",
                "The TASK-028 raw input boundary is malformed.",
            )
        )
        return _finalize_blocked(pending_blockers, raw_request_projection)

    # R02: Scan unknown fields
    known_fields = set(_REQUIRED_TOP_LEVEL_FIELDS)
    unknown_fields = sorted([k for k in raw_input if k not in known_fields])
    if unknown_fields:
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_REQUEST_UNKNOWN_FIELD,
                "unknown_fields",
                "The TASK-028 raw request contains one or more unknown fields.",
            )
        )

    # R03: Scan required field presence
    missing_assertions: list[str] = []
    for field_name in _REQUIRED_TOP_LEVEL_FIELDS:
        if field_name not in raw_input:
            if field_name in (
                "constant_density_path_assertion",
                "zero_net_elevation_change_assertion",
            ):
                missing_assertions.append(field_name)
            elif field_name == "component_authorities":
                pending_blockers.append(
                    emit_blocker(
                        Task028BlockerCode.BL_T028_COMPONENT_AUTHORITY_SET_INVALID,
                        "component_authorities",
                        "The component authorities set is invalid (missing).",
                    )
                )
            elif field_name == "flow_direction_assertion":
                pending_blockers.append(
                    emit_blocker(
                        Task028BlockerCode.BL_T028_FLOW_DIRECTION_UNSUPPORTED,
                        "flow_direction_assertion",
                        "The supplied flow direction is not supported.",
                    )
                )
            else:
                pending_blockers.append(
                    emit_blocker(
                        Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                        f"raw_input.{field_name}",
                        "The TASK-028 raw input boundary is malformed.",
                    )
                )

    if missing_assertions:
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_APPLICABILITY_ASSERTION_MISSING,
                "constant_density_path_assertion",
                "A required TASK-028 applicability assertion is missing.",
            )
        )

    # R04: Validate raw scalar types for assertion fields
    # flow_direction_assertion
    if "flow_direction_assertion" in raw_input:
        fd_val = raw_input["flow_direction_assertion"]
        if not isinstance(fd_val, str):
            pending_blockers.append(
                emit_blocker(
                    Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                    "flow_direction_assertion",
                    "The TASK-028 raw input boundary is malformed.",
                )
            )
        elif fd_val != "START_TO_END":
            pending_blockers.append(
                emit_blocker(
                    Task028BlockerCode.BL_T028_FLOW_DIRECTION_UNSUPPORTED,
                    "flow_direction_assertion",
                    "The supplied flow direction is not supported.",
                )
            )
        else:
            typed_data["flow_direction_assertion"] = (
                Task028RequestFlowDirectionAssertion.START_TO_END
            )

    # constant_density_path_assertion
    if "constant_density_path_assertion" in raw_input:
        cd_val = raw_input["constant_density_path_assertion"]
        if cd_val not in ("TRUE", "FALSE"):
            pending_blockers.append(
                emit_blocker(
                    Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                    "constant_density_path_assertion",
                    "The TASK-028 raw input boundary is malformed.",
                )
            )
        else:
            typed_data["constant_density_path_assertion"] = Task028ApplicabilityAssertion(cd_val)

    # zero_net_elevation_change_assertion
    if "zero_net_elevation_change_assertion" in raw_input:
        ze_val = raw_input["zero_net_elevation_change_assertion"]
        if ze_val not in ("TRUE", "FALSE"):
            pending_blockers.append(
                emit_blocker(
                    Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                    "zero_net_elevation_change_assertion",
                    "The TASK-028 raw input boundary is malformed.",
                )
            )
        else:
            typed_data["zero_net_elevation_change_assertion"] = Task028ApplicabilityAssertion(
                ze_val
            )

    # R05: Validate component_authorities tuple shape
    if "component_authorities" in raw_input:
        ca = raw_input["component_authorities"]
        if not isinstance(ca, (list, tuple)):
            pending_blockers.append(
                emit_blocker(
                    Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                    "component_authorities",
                    "The component authorities set is invalid (not a sequence).",
                )
            )
        elif len(ca) == 0:
            pending_blockers.append(
                emit_blocker(
                    Task028BlockerCode.BL_T028_COMPONENT_AUTHORITY_SET_INVALID,
                    "component_authorities",
                    "The component authorities set is invalid (empty).",
                )
            )
        else:
            # R06: Validate nested component record shapes
            typed_authorities: list[dict[str, Any]] = []
            for i, comp in enumerate(ca):
                if not isinstance(comp, dict):
                    pending_blockers.append(
                        emit_blocker(
                            Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                            f"component_authorities[{i}]",
                            "The TASK-028 raw input boundary is malformed.",
                        )
                    )
                    continue

                typed_comp = _validate_component_record(comp, i, pending_blockers)
                if typed_comp is not None:
                    typed_authorities.append(typed_comp)

            typed_data["component_authorities"] = typed_authorities

    typed_data["raw_request_projection"] = raw_request_projection
    typed_data["raw_input"] = raw_input

    # R08-R10: Accumulate, deduplicate, sort blockers
    if pending_blockers:
        return _finalize_blocked(pending_blockers, raw_request_projection)

    return RawBoundaryResult(
        blocked=False,
        typed_data=typed_data,
        blockers=(),
        raw_request_projection=raw_request_projection,
    )


def _validate_component_record(
    comp: dict[str, Any],
    index: int,
    pending_blockers: list[_Task028PendingBlocker],
) -> dict[str, Any] | None:
    """Validate a single component authority record from raw input (R06)."""
    typed: dict[str, Any] = {}
    prefix = f"component_authorities[{index}]"

    # component_id
    cid = comp.get("component_id", "")
    if not isinstance(cid, str) or not cid:
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                f"{prefix}.component_id",
                "The TASK-028 raw input boundary is malformed.",
            )
        )
        return None
    typed["component_id"] = cid
    tiebreaker = cid

    # component_type
    ct = comp.get("component_type", "")
    if not isinstance(ct, str):
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                f"{prefix}.component_type",
                "The TASK-028 raw input boundary is malformed.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None
    if ct in KNOWN_UNSUPPORTED_RAW_COMPONENT_TOKENS:
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_COMPONENT_TYPE_UNSUPPORTED,
                f"{prefix}.component_type",
                f"Component type {ct} is not supported by TASK-028 V1.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None
    try:
        typed["component_type"] = Task028ComponentType(ct)
    except ValueError:
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                f"{prefix}.component_type",
                "The TASK-028 raw input boundary is malformed.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None

    # path_sequence_index (CR-06: MUST be explicit — never falls back to array index)
    psi = comp.get("path_sequence_index")
    if psi is None:
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                f"{prefix}.path_sequence_index",
                "path_sequence_index is required and must not be inferred from array position.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None
    if not isinstance(psi, int) or isinstance(psi, bool):
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                f"{prefix}.path_sequence_index",
                "path_sequence_index must be a non-negative integer.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None
    if psi < 0:
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                f"{prefix}.path_sequence_index",
                "path_sequence_index must be a non-negative integer.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None
    typed["path_sequence_index"] = psi

    # flow_direction_assertion
    fda = comp.get("flow_direction_assertion", "")
    if not isinstance(fda, str) or fda not in ("START_TO_END", "END_TO_START"):
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                f"{prefix}.flow_direction_assertion",
                "The TASK-028 raw input boundary is malformed.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None
    typed["flow_direction_assertion"] = Task028ComponentFlowDirectionAssertion(fda)

    # loss_coefficient
    lc = comp.get("loss_coefficient")
    from decimal import Decimal, InvalidOperation

    if isinstance(lc, (int, float)):
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                f"{prefix}.loss_coefficient",
                "loss_coefficient must be str or Decimal; "
                "float/int implicit conversion is forbidden.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None
    if not isinstance(lc, (str, Decimal)):
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                f"{prefix}.loss_coefficient",
                "loss_coefficient must be str or Decimal.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None
    try:
        typed["loss_coefficient"] = Decimal(lc) if isinstance(lc, str) else lc
    except (InvalidOperation, ValueError):
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                f"{prefix}.loss_coefficient",
                "The TASK-028 raw input boundary is malformed.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None

    # loss_coefficient_convention
    lcc = comp.get("loss_coefficient_convention", "")
    if not isinstance(lcc, str) or lcc != "K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2":
        if isinstance(lcc, str):
            pending_blockers.append(
                emit_blocker(
                    Task028BlockerCode.BL_T028_LOSS_COEFFICIENT_CONVENTION_UNSUPPORTED,
                    f"{prefix}.loss_coefficient_convention",
                    "The loss coefficient convention is not supported.",
                    component_id_tiebreaker=tiebreaker,
                )
            )
        else:
            pending_blockers.append(
                emit_blocker(
                    Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                    f"{prefix}.loss_coefficient_convention",
                    "The TASK-028 raw input boundary is malformed.",
                    component_id_tiebreaker=tiebreaker,
                )
            )
        return None
    typed["loss_coefficient_convention"] = LossCoefficientConvention(lcc)

    # reference_flow_area_m2
    rfa = comp.get("reference_flow_area_m2")
    if isinstance(rfa, (int, float)):
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                f"{prefix}.reference_flow_area_m2",
                "reference_flow_area_m2 must be str or Decimal; "
                "float/int implicit conversion is forbidden.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None
    if not isinstance(rfa, (str, Decimal)):
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                f"{prefix}.reference_flow_area_m2",
                "reference_flow_area_m2 must be str or Decimal.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None
    try:
        typed["reference_flow_area_m2"] = Decimal(rfa) if isinstance(rfa, str) else rfa
    except (InvalidOperation, ValueError):
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                f"{prefix}.reference_flow_area_m2",
                "The TASK-028 raw input boundary is malformed.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None

    # multiplicity
    mult = comp.get("multiplicity", 1)
    if not isinstance(mult, int) or isinstance(mult, bool):
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                f"{prefix}.multiplicity",
                "The TASK-028 raw input boundary is malformed.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None
    typed["multiplicity"] = mult

    # upstream_reference_plane
    urp = comp.get("upstream_reference_plane", "")
    if not isinstance(urp, str) or not urp:
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                f"{prefix}.upstream_reference_plane",
                "The TASK-028 raw input boundary is malformed.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None
    typed["upstream_reference_plane"] = urp

    # downstream_reference_plane
    drp = comp.get("downstream_reference_plane", "")
    if not isinstance(drp, str) or not drp:
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                f"{prefix}.downstream_reference_plane",
                "The TASK-028 raw input boundary is malformed.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None
    typed["downstream_reference_plane"] = drp

    # geometry_evidence_refs
    ger = comp.get("geometry_evidence_refs", ())
    if not isinstance(ger, (list, tuple)):
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                f"{prefix}.geometry_evidence_refs",
                "The TASK-028 raw input boundary is malformed.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None
    typed["geometry_evidence_refs"] = tuple(ger)

    # coefficient_source_id
    csi = comp.get("coefficient_source_id", "")
    if not isinstance(csi, str) or not csi:
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_COEFFICIENT_SOURCE_ID_MISSING,
                f"{prefix}.coefficient_source_id",
                "The coefficient source ID is missing.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None
    typed["coefficient_source_id"] = csi

    # coefficient_source_version
    csv = comp.get("coefficient_source_version", "")
    if not isinstance(csv, str) or not csv:
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_COEFFICIENT_SOURCE_VERSION_MISSING,
                f"{prefix}.coefficient_source_version",
                "The coefficient source version is missing.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None
    typed["coefficient_source_version"] = csv

    # coefficient_source_location
    csloc = comp.get("coefficient_source_location", "")
    if not isinstance(csloc, str) or not csloc:
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_COEFFICIENT_SOURCE_LOCATION_MISSING,
                f"{prefix}.coefficient_source_location",
                "The coefficient source location is missing.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None
    typed["coefficient_source_location"] = csloc

    # coefficient_permission_status
    cps = comp.get("coefficient_permission_status", "")
    if not isinstance(cps, str):
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                f"{prefix}.coefficient_permission_status",
                "The TASK-028 raw input boundary is malformed.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None
    if cps != "ADMITTED":
        pending_blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_COEFFICIENT_PERMISSION_NOT_ADMITTED,
                f"{prefix}.coefficient_permission_status",
                "The coefficient permission status is not ADMITTED.",
                component_id_tiebreaker=tiebreaker,
            )
        )
        return None
    typed["coefficient_permission_status"] = CoefficientPermissionStatus(cps)

    return typed


def _finalize_blocked(
    pending_blockers: list[_Task028PendingBlocker],
    raw_request_projection: Task028RawProjection | None,
) -> RawBoundaryResult:
    """R08-R10: Deduplicate and sort blockers, return blocked result."""
    collapsed = collapse_blockers(pending_blockers)
    return RawBoundaryResult(
        blocked=True,
        typed_data=None,
        blockers=collapsed,
        raw_request_projection=raw_request_projection,
    )


__all__ = [
    "RawBoundaryResult",
    "validate_raw_boundary",
]
