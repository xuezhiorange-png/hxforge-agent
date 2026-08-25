"""TASK-034 upstream replay and authority bindings."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any

from .blocker_registry import BlockerCode, make_blocker
from .canonical import (
    mass_flow_authority_hash,
    property_snapshot_hash,
    task031_geometry_hash,
    task031_geometry_id,
    task032_request_hash,
    task033_request_hash,
    task033_result_hash,
    task033_result_id,
)
from .canonical import (
    task031_request_hash as canonical_task031_request_hash,
)
from .engineering_authority_snapshot import (
    CORRELATION_ID,
    ENGINEERING_SOURCE_AUTHORITY_RECORD_ID,
    SUPPORTED_BAFFLE_CUT,
    SUPPORTED_BAFFLE_TYPE,
    SUPPORTED_PHASE,
    SUPPORTED_RHEOLOGY,
    SUPPORTED_SHELL_PASS_COUNT,
    SUPPORTED_SHELL_TYPE,
    SUPPORTED_TUBE_LAYOUT,
)
from .models import Task034Request


class AuthorityFailure(ValueError):
    def __init__(self, stage: str, *blockers: Any) -> None:
        super().__init__(stage)
        self.stage = stage
        self.blockers = tuple(blockers)


@dataclass(frozen=True)
class ReplayIdentity:
    task033_request_hash: str | None
    task033_result_hash: str | None
    task033_result_id: str | None
    task032_request_hash: str | None
    task032_result_hash: str | None
    task032_result_id: str | None
    task031_request_hash: str | None
    task031_geometry_hash: str | None
    task031_geometry_id: str | None
    property_hash: str | None
    mass_flow_hash: str | None
    flow: dict[str, Any]
    task032_request_evidence: dict[str, Any]
    task031_request_evidence: dict[str, Any]


def _nested(mapping: Any, *keys: str) -> Any:
    value = mapping
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _upstream_parts(
    upstream: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    flow = upstream.get("task032_flow_state", upstream.get("flow_state", {}))
    request_evidence = upstream.get(
        "task032_request_evidence", upstream.get("request_evidence", {})
    )
    task031_evidence = (
        request_evidence.get("task031_result", {}).get("request_evidence", {})
        if isinstance(request_evidence, dict)
        else {}
    )
    return (
        flow if isinstance(flow, dict) else {},
        request_evidence if isinstance(request_evidence, dict) else {},
        task031_evidence if isinstance(task031_evidence, dict) else {},
    )


def _fail(stage: str, code: str, field: str) -> AuthorityFailure:
    return AuthorityFailure(stage, make_blocker(code, stage=stage, field_path=field))


def validate_task033_upstream_boundary(
    request: Task034Request,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Validate the S03 accepted TASK033 upstream boundary."""
    upstream = request.task033_upstream_evidence
    if upstream is None:
        raise _fail("S03", BlockerCode.SSPD_TASK033_UPSTREAM_MISSING, "task033_upstream_evidence")
    if type(upstream) is not dict:
        raise _fail("S03", BlockerCode.SSPD_TASK033_UPSTREAM_INVALID, "task033_upstream_evidence")
    if (
        upstream.get("engineering_source_authority_record_id")
        != ENGINEERING_SOURCE_AUTHORITY_RECORD_ID
    ):
        raise _fail(
            "S03",
            BlockerCode.SSPD_SOURCE_AUTHORITY_MISMATCH,
            "task033_upstream_evidence.engineering_source_authority_record_id",
        )
    if "status" not in upstream or upstream["status"] != "SUCCESS":
        raise _fail(
            "S03", BlockerCode.SSPD_TASK033_UPSTREAM_INVALID, "task033_upstream_evidence.status"
        )
    flow, request_evidence, _ = _upstream_parts(upstream)
    if not flow or not request_evidence:
        raise _fail("S03", BlockerCode.SSPD_TASK033_UPSTREAM_INVALID, "task033_upstream_evidence")
    return upstream, flow, request_evidence


def _identity(
    request: Task034Request,
    upstream: dict[str, Any],
    flow: dict[str, Any],
    request_evidence: dict[str, Any],
    *,
    task033_result_hash_value: str | None,
    task033_result_id_value: str | None,
    task031_request_hash_value: str | None = None,
    task031_geometry_hash_value: str | None = None,
    task031_geometry_id_value: str | None = None,
    property_hash_value: str | None = None,
    mass_flow_hash_value: str | None = None,
) -> ReplayIdentity:
    return ReplayIdentity(
        task033_request_hash=request.task033_request_hash,
        task033_result_hash=task033_result_hash_value,
        task033_result_id=task033_result_id_value,
        task032_request_hash=flow.get("request_hash"),
        task032_result_hash=flow.get("result_hash"),
        task032_result_id=flow.get("result_id"),
        task031_request_hash=task031_request_hash_value,
        task031_geometry_hash=task031_geometry_hash_value,
        task031_geometry_id=task031_geometry_id_value,
        property_hash=property_hash_value,
        mass_flow_hash=mass_flow_hash_value,
        flow=flow,
        task032_request_evidence=request_evidence,
        task031_request_evidence=request.task031_request_evidence
        if isinstance(request.task031_request_evidence, dict)
        else {},
    )


def validate_task033_result_identity(
    request: Task034Request,
    upstream_parts: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
) -> ReplayIdentity:
    """Validate S04 TASK033 and accepted TASK032 result identities."""
    upstream, flow, request_evidence = upstream_parts

    expected_task033_result_hash = task033_result_hash(upstream)
    task033_result_hash_value = upstream.get("result_hash", upstream.get("task033_result_hash"))
    task033_result_id_value = upstream.get("result_id", upstream.get("task033_result_id"))
    if (
        task033_result_id_value is None
        or request.task033_result_id != task033_result_id_value
        or task033_result_id(str(task033_result_hash_value)) != task033_result_id_value
    ):
        raise _fail("S04", BlockerCode.SSPD_TASK033_RESULT_ID_MISMATCH, "task033_result_id")
    if (
        task033_result_hash_value is None
        or request.task033_result_hash != task033_result_hash_value
        or expected_task033_result_hash != task033_result_hash_value
    ):
        raise _fail("S04", BlockerCode.SSPD_TASK033_RESULT_HASH_MISMATCH, "task033_result_hash")

    return _identity(
        request,
        upstream,
        flow,
        request_evidence,
        task033_result_hash_value=task033_result_hash_value,
        task033_result_id_value=task033_result_id_value,
    )


def validate_task033_request_identity(
    request: Task034Request, identity: ReplayIdentity
) -> ReplayIdentity:
    """Validate S05 TASK033 request identity."""
    expected_task033_request = task033_request_hash(request.task033_upstream_evidence)
    if expected_task033_request != request.task033_request_hash:
        raise _fail("S05", BlockerCode.SSPD_TASK033_REQUEST_HASH_MISMATCH, "task033_request_hash")
    return identity


def replay_task031_request(request: Task034Request, identity: ReplayIdentity) -> ReplayIdentity:
    """Replay S06 TASK031 request and nested TASK032 request identities."""
    if type(request.task031_request_evidence) is not dict:
        raise _fail(
            "S06", BlockerCode.SSPD_TASK031_REQUEST_EVIDENCE_MISSING, "task031_request_evidence"
        )
    try:
        task031_request_hash_value = _task031_request_hash(request.task031_request_evidence)
    except Exception as exc:
        raise _fail(
            "S06", BlockerCode.SSPD_TASK031_REQUEST_HASH_MISMATCH, "task031_request_hash"
        ) from exc
    if task031_request_hash_value != request.task031_request_hash:
        raise _fail("S06", BlockerCode.SSPD_TASK031_REQUEST_HASH_MISMATCH, "task031_request_hash")

    try:
        expected_task032_request_hash = task032_request_hash(identity.task032_request_evidence)
    except Exception as exc:
        raise _fail(
            "S06", BlockerCode.SSPD_TASK032_RESULT_HASH_MISMATCH, "task032_request_hash"
        ) from exc
    if expected_task032_request_hash != identity.flow.get(
        "request_hash"
    ) or request.task032_request_hash != identity.flow.get("request_hash"):
        raise _fail("S06", BlockerCode.SSPD_TASK032_RESULT_HASH_MISMATCH, "task032_request_hash")
    return replace(identity, task031_request_hash=task031_request_hash_value)


def replay_task031_geometry(request: Task034Request, identity: ReplayIdentity) -> ReplayIdentity:
    """Replay S07 TASK031 geometry identity without recomputing geometry values."""
    task031_result = identity.task032_request_evidence.get("task031_result")
    if type(task031_result) is not dict or task031_result.get("status") != "VALID":
        raise _fail(
            "S06", BlockerCode.SSPD_TASK031_REQUEST_EVIDENCE_MISSING, "task031_request_evidence"
        )
    geometry = task031_result.get("geometry")
    if type(geometry) is not dict:
        raise _fail(
            "S06", BlockerCode.SSPD_TASK031_REQUEST_EVIDENCE_MISSING, "task031_request_evidence"
        )
    try:
        geometry_hash = task031_geometry_hash(geometry)
    except Exception as exc:
        raise _fail(
            "S07", BlockerCode.SSPD_TASK031_GEOMETRY_HASH_MISMATCH, "task031_geometry_hash"
        ) from exc
    if (
        geometry_hash != geometry.get("geometry_hash")
        or geometry_hash != identity.flow.get("task031_geometry_hash")
        or geometry_hash != request.task031_geometry_hash
    ):
        raise _fail("S07", BlockerCode.SSPD_TASK031_GEOMETRY_HASH_MISMATCH, "task031_geometry_hash")
    geometry_id = task031_geometry_id(geometry_hash)
    if (
        geometry_id != geometry.get("geometry_id")
        or geometry_id != identity.flow.get("task031_geometry_id")
        or geometry_id != request.task031_geometry_id
    ):
        raise _fail("S07", BlockerCode.SSPD_TASK031_GEOMETRY_ID_MISMATCH, "task031_geometry_id")
    return replace(
        identity,
        task031_geometry_hash=geometry_hash,
        task031_geometry_id=geometry_id,
    )


def validate_task032_identity_join(
    request: Task034Request,
    identity: ReplayIdentity,
    *,
    validate_result_identity: bool = True,
) -> ReplayIdentity:
    """Validate accepted TASK032 result identity at its frozen owner."""
    if validate_result_identity:
        upstream = request.task033_upstream_evidence
        result_payload = upstream.get("result")
        result_payload = result_payload if type(result_payload) is dict else {}
        task032_result_hash_value = identity.flow.get("result_hash")
        task032_result_id_value = identity.flow.get("result_id")
        if (
            task032_result_id_value is None
            or task032_result_id_value != result_payload.get("task032_result_id")
            or request.task032_result_id != task032_result_id_value
        ):
            raise _fail("S04", BlockerCode.SSPD_TASK032_RESULT_ID_MISMATCH, "task032_result_id")
        if (
            task032_result_hash_value is None
            or task032_result_hash_value != result_payload.get("task032_result_hash")
            or request.task032_result_hash != task032_result_hash_value
        ):
            raise _fail("S04", BlockerCode.SSPD_TASK032_RESULT_HASH_MISMATCH, "task032_result_hash")
    return identity


def replay_task032_and_upstreams(request: Task034Request) -> ReplayIdentity:
    """Compatibility facade executing the frozen S03-S08 sequence."""
    upstream_parts = validate_task033_upstream_boundary(request)
    identity = validate_task033_result_identity(request, upstream_parts)
    identity = validate_task032_identity_join(request, identity)
    identity = validate_task033_request_identity(request, identity)
    identity = replay_task031_request(request, identity)
    identity = replay_task031_geometry(request, identity)
    return validate_task032_identity_join(request, identity, validate_result_identity=False)


def _task031_request_hash(evidence: dict[str, Any]) -> str:
    return canonical_task031_request_hash(evidence)


def task031_request_hash(evidence: dict[str, Any]) -> str:
    """Replay the frozen TASK-031 request evidence projection."""
    return _task031_request_hash(evidence)


def verify_auxiliary_bindings(request: Task034Request, identity: ReplayIdentity) -> ReplayIdentity:
    """Verify property/mass-flow hashes and auxiliary geometry bindings at S08."""
    snapshot = identity.task032_request_evidence.get("property_snapshot")
    if type(snapshot) is not dict:
        raise _fail("S08", BlockerCode.SSPD_PROPERTY_SNAPSHOT_HASH_MISMATCH, "property_snapshot")
    try:
        expected_property_hash = property_snapshot_hash(snapshot)
    except Exception as exc:
        raise _fail(
            "S08", BlockerCode.SSPD_PROPERTY_SNAPSHOT_HASH_MISMATCH, "property_snapshot_hash"
        ) from exc
    if (
        expected_property_hash != snapshot.get("property_snapshot_hash")
        or expected_property_hash != identity.task032_request_evidence.get("property_snapshot_hash")
        or expected_property_hash != identity.flow.get("property_snapshot_hash")
        or expected_property_hash != request.property_snapshot_hash
    ):
        raise _fail(
            "S08", BlockerCode.SSPD_PROPERTY_SNAPSHOT_HASH_MISMATCH, "property_snapshot_hash"
        )

    mass_flow = identity.task032_request_evidence.get("mass_flow_authority")
    if type(mass_flow) is not dict:
        raise _fail(
            "S08", BlockerCode.SSPD_MASS_FLOW_AUTHORITY_HASH_MISMATCH, "mass_flow_authority_hash"
        )
    try:
        expected_mass_flow_hash = mass_flow_authority_hash(mass_flow)
    except Exception as exc:
        raise _fail(
            "S08", BlockerCode.SSPD_MASS_FLOW_AUTHORITY_HASH_MISMATCH, "mass_flow_authority_hash"
        ) from exc
    if (
        expected_mass_flow_hash != mass_flow.get("authority_hash")
        or expected_mass_flow_hash != identity.flow.get("mass_flow_authority_hash")
        or expected_mass_flow_hash != request.mass_flow_authority_hash
    ):
        raise _fail(
            "S08", BlockerCode.SSPD_MASS_FLOW_AUTHORITY_HASH_MISMATCH, "mass_flow_authority_hash"
        )

    geometry = identity.task032_request_evidence.get("task031_result", {}).get("geometry", {})
    if type(geometry) is not dict:
        geometry = {}
    design = (
        request.task031_request_evidence.get("baffle_geometry_result", {})
        .get("geometry", {})
        .get("design_authority", {})
    )
    tube = request.task031_request_evidence.get("tube_layout", {})
    if type(design) is not dict:
        design = {}
    if type(tube) is not dict:
        tube = {}

    def decimal_value(value: Any) -> Decimal | None:
        if value is None:
            return None
        try:
            converted = Decimal(str(value))
        except (ArithmeticError, TypeError, ValueError):
            return None
        return converted if converted.is_finite() else None

    spacing_value = design.get("spacing_sequence_m")
    if isinstance(spacing_value, (list, tuple)):
        try:
            expected_spacing: tuple[Decimal, ...] | None = tuple(
                Decimal(str(value)) for value in spacing_value
            )
            if expected_spacing is not None and not all(
                value.is_finite() for value in expected_spacing
            ):
                expected_spacing = None
        except (ArithmeticError, TypeError, ValueError):
            expected_spacing = None
    else:
        expected_spacing = None
    layout_rule_authority = tube.get("layout_rule_authority", {})
    tube_geometry = tube.get("tube_geometry", {})
    if type(layout_rule_authority) is not dict:
        layout_rule_authority = {}
    if type(tube_geometry) is not dict:
        tube_geometry = {}
    expected = (
        (
            request.shell_inside_diameter_m,
            decimal_value(geometry.get("shell_inside_diameter_m")),
            BlockerCode.SSPD_SHELL_INSIDE_DIAMETER_MISMATCH,
            "shell_inside_diameter_m",
        ),
        (
            request.baffle_count,
            design.get("baffle_count"),
            BlockerCode.SSPD_BAFFLE_COUNT_MISMATCH,
            "baffle_count",
        ),
        (
            request.uniform_spacing_sequence_m,
            expected_spacing,
            BlockerCode.SSPD_SPACING_SEQUENCE_MISMATCH,
            "uniform_spacing_sequence_m",
        ),
        (
            request.tube_pitch_m,
            decimal_value(layout_rule_authority.get("pitch_m")),
            BlockerCode.SSPD_TUBE_PITCH_MISMATCH,
            "tube_pitch_m",
        ),
        (
            request.tube_outer_diameter_m,
            decimal_value(tube_geometry.get("outer_diameter_m")),
            BlockerCode.SSPD_TUBE_OUTER_DIAMETER_MISMATCH,
            "tube_outer_diameter_m",
        ),
        (
            request.pattern_family,
            layout_rule_authority.get("pattern_family"),
            BlockerCode.SSPD_PATTERN_FAMILY_MISMATCH,
            "pattern_family",
        ),
    )
    for actual, expected_value, code, field in expected:
        if expected_value is None or actual != expected_value:
            raise _fail("S08", code, field)
    return replace(
        identity,
        property_hash=expected_property_hash,
        mass_flow_hash=expected_mass_flow_hash,
    )


def verify_wall_property_authority(request: Task034Request) -> None:
    if (
        not isinstance(request.shell_side_wall_dynamic_viscosity_pa_s, Decimal)
        or not request.shell_side_wall_dynamic_viscosity_pa_s.is_finite()
        or request.shell_side_wall_dynamic_viscosity_pa_s <= 0
    ):
        raise _fail(
            "S09", BlockerCode.SSPD_WALL_VISCOSITY_INVALID, "shell_side_wall_dynamic_viscosity_pa_s"
        )
    if request.wall_property_authority_hash is None:
        raise _fail(
            "S09", BlockerCode.SSPD_WALL_PROPERTY_AUTHORITY_MISSING, "wall_property_authority_hash"
        )
    from .canonical import wall_property_authority_hash

    if wall_property_authority_hash(request) != request.wall_property_authority_hash:
        raise _fail(
            "S09", BlockerCode.SSPD_WALL_PROPERTY_AUTHORITY_MISMATCH, "wall_property_authority_hash"
        )


verify_wall_property = verify_wall_property_authority


def verify_same_case(request: Task034Request, identity: ReplayIdentity) -> None:
    flow = identity.flow
    for field, code in (
        ("shell_side_case_id", BlockerCode.SSPD_CASE_ID_MISMATCH),
        ("shell_side_stream_id", BlockerCode.SSPD_STREAM_ID_MISMATCH),
        ("shell_side_fluid_id", BlockerCode.SSPD_FLUID_ID_MISMATCH),
        ("task020_configuration_id", BlockerCode.SSPD_CONFIGURATION_ID_MISMATCH),
    ):
        if getattr(request, field) != flow.get(field):
            raise _fail("S10", code, field)
    if request.task020_configuration_hash != flow.get("task020_configuration_hash"):
        raise _fail("S10", BlockerCode.SSPD_CONFIGURATION_ID_MISMATCH, "task020_configuration_hash")
    for field, expected in (
        ("task031_geometry_id", identity.task031_geometry_id),
        ("task031_geometry_hash", identity.task031_geometry_hash),
        ("property_snapshot_hash", identity.property_hash),
        ("mass_flow_authority_hash", identity.mass_flow_hash),
    ):
        if getattr(request, field) != expected:
            code = (
                BlockerCode.SSPD_PROPERTY_SNAPSHOT_HASH_MISMATCH
                if field == "property_snapshot_hash"
                else BlockerCode.SSPD_MASS_FLOW_AUTHORITY_HASH_MISMATCH
                if field == "mass_flow_authority_hash"
                else BlockerCode.SSPD_TASK031_GEOMETRY_ID_MISMATCH
                if field.endswith("_id")
                else BlockerCode.SSPD_TASK031_GEOMETRY_HASH_MISMATCH
            )
            raise _fail("S10", code, field)


def verify_applicability(request: Task034Request, identity: ReplayIdentity) -> None:
    flow = identity.flow
    upstream = request.task033_upstream_evidence
    for actual, expected, code, field in (
        (
            flow.get("phase_region"),
            SUPPORTED_PHASE,
            BlockerCode.SSPD_UNSUPPORTED_PHASE,
            "phase_region",
        ),
        (
            flow.get("rheology_model"),
            SUPPORTED_RHEOLOGY,
            BlockerCode.SSPD_UNSUPPORTED_RHEOLOGY,
            "rheology_model",
        ),
        (
            upstream.get("construction_family"),
            SUPPORTED_SHELL_TYPE,
            BlockerCode.SSPD_UNSUPPORTED_SHELL_TYPE,
            "construction_family",
        ),
        (
            upstream.get("shell_pass_count"),
            SUPPORTED_SHELL_PASS_COUNT,
            BlockerCode.SSPD_UNSUPPORTED_SHELL_PASS_COUNT,
            "shell_pass_count",
        ),
        (
            upstream.get("baffle_type"),
            SUPPORTED_BAFFLE_TYPE,
            BlockerCode.SSPD_UNSUPPORTED_BAFFLE_TYPE,
            "baffle_type",
        ),
        (
            upstream.get("pattern_family"),
            SUPPORTED_TUBE_LAYOUT,
            BlockerCode.SSPD_UNSUPPORTED_TUBE_LAYOUT,
            "pattern_family",
        ),
        (
            upstream.get("baffle_cut"),
            SUPPORTED_BAFFLE_CUT,
            BlockerCode.SSPD_UNSUPPORTED_BAFFLE_CUT,
            "baffle_cut",
        ),
    ):
        if actual != expected:
            raise _fail("S11", code, field)
    spacing = request.uniform_spacing_sequence_m
    if (
        type(spacing) is not tuple
        or len(spacing) < 1
        or any(
            not isinstance(item, Decimal) or not item.is_finite() or item <= 0 for item in spacing
        )
        or any(item != spacing[0] for item in spacing)
    ):
        raise _fail(
            "S11", BlockerCode.SSPD_UNSUPPORTED_BAFFLE_SPACING, "uniform_spacing_sequence_m"
        )
    try:
        reynolds = Decimal(str(flow["shell_side_reynolds_number"]))
    except (ArithmeticError, KeyError, TypeError, ValueError):
        raise _fail(
            "S11", BlockerCode.SSPD_REYNOLDS_OUTSIDE_DOMAIN, "shell_side_reynolds_number"
        ) from None
    if not reynolds.is_finite() or not Decimal("400") < reynolds < Decimal("1000000"):
        raise _fail("S11", BlockerCode.SSPD_REYNOLDS_OUTSIDE_DOMAIN, "shell_side_reynolds_number")


def verify_engineering_authority(request: Task034Request) -> None:
    if request.correlation_id != CORRELATION_ID:
        raise _fail("S11", BlockerCode.SSPD_SOURCE_AUTHORITY_MISMATCH, "correlation_id")


__all__ = [
    "AuthorityFailure",
    "ReplayIdentity",
    "validate_task033_upstream_boundary",
    "validate_task033_result_identity",
    "validate_task033_request_identity",
    "replay_task031_request",
    "replay_task031_geometry",
    "validate_task032_identity_join",
    "replay_task032_and_upstreams",
    "task031_request_hash",
    "verify_auxiliary_bindings",
    "verify_wall_property_authority",
    "verify_wall_property",
    "verify_same_case",
    "verify_applicability",
    "verify_engineering_authority",
]
