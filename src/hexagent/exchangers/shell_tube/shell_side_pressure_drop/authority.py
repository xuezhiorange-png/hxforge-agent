"""TASK-034 upstream replay and authority bindings."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any

from .blocker_registry import BlockerCode, make_blocker
from .canonical import (
    mass_flow_authority_hash,
    property_snapshot_hash,
    shell_type_authority_hash,
    task031_geometry_hash,
    task031_geometry_id,
    task032_request_hash,
    task033_request_hash,
    task033_result_hash,
    task033_result_id,
)
from .canonical import task031_request_hash as canonical_task031_request_hash
from .engineering_authority_snapshot import (
    CORRELATION_ID,
    ENGINEERING_SOURCE_AUTHORITY_RECORD_ID,
    SUPPORTED_BAFFLE_TYPE,
    SUPPORTED_PHASE,
    SUPPORTED_RHEOLOGY,
    SUPPORTED_SHELL_PASS_COUNT,
    SUPPORTED_SHELL_TYPE,
    SUPPORTED_TUBE_LAYOUT,
)
from .models import SHELL_TYPE_AUTHORITY_FIELDS, Task034Request

SHELL_TYPE_AUTHORITY_SCHEMA_VERSION = "task034.shell-type-authority.v2"


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
    shell_type: str | None
    shell_type_authority_hash: str | None
    shell_type_authority_record_id: str | None
    shell_type_authority_source_id: str | None
    shell_type_authority_source_version: str | None
    flow: dict[str, Any]
    task032_request_evidence: dict[str, Any]
    task031_request_evidence: dict[str, Any]


def _fail(stage: str, code: str, field: str) -> AuthorityFailure:
    return AuthorityFailure(stage, make_blocker(code, stage=stage, field_path=field))


def _task033_success_result(upstream: dict[str, Any]) -> dict[str, Any]:
    validation_result = upstream.get("task033_validation_result")
    if type(validation_result) is not dict:
        return {}
    result = validation_result.get("heat_transfer")
    return result if type(result) is dict else {}


def _upstream_parts(
    upstream: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Extract the public TASK033 request's TASK032 evidence without reshaping it."""
    task033_request_evidence = upstream.get("task033_request_evidence")
    if type(task033_request_evidence) is not dict:
        return {}, {}, {}
    flow = task033_request_evidence.get("task032_flow_state")
    request_evidence = task033_request_evidence.get("task032_request_evidence")
    task031_evidence = (
        request_evidence.get("task031_request_evidence", {})
        if type(request_evidence) is dict
        else {}
    )
    return (
        flow if type(flow) is dict else {},
        request_evidence if type(request_evidence) is dict else {},
        task031_evidence if type(task031_evidence) is dict else {},
    )


def validate_task033_upstream_boundary(
    request: Task034Request,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Validate the S03 accepted TASK033 public validation-result envelope."""
    upstream = request.task033_upstream_evidence
    if upstream is None:
        raise _fail("S03", BlockerCode.SSPD_TASK033_UPSTREAM_MISSING, "task033_upstream_evidence")
    if type(upstream) is not dict:
        raise _fail("S03", BlockerCode.SSPD_TASK033_UPSTREAM_INVALID, "task033_upstream_evidence")
    task033_request_evidence = upstream.get("task033_request_evidence")
    validation_result = upstream.get("task033_validation_result")
    result = _task033_success_result(upstream)
    if (
        type(task033_request_evidence) is not dict
        or type(validation_result) is not dict
        or validation_result.get("status") != "VALID"
        or not result
    ):
        raise _fail(
            "S03",
            BlockerCode.SSPD_TASK033_UPSTREAM_INVALID,
            "task033_upstream_evidence.task033_validation_result",
        )
    if (
        result.get("engineering_source_authority_record_id")
        != ENGINEERING_SOURCE_AUTHORITY_RECORD_ID
    ):
        raise _fail(
            "S03",
            BlockerCode.SSPD_SOURCE_AUTHORITY_MISMATCH,
            "task033_upstream_evidence.task033_validation_result.heat_transfer.engineering_source_authority_record_id",
        )
    flow, request_evidence, task031_evidence = _upstream_parts(upstream)
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
        shell_type=None,
        shell_type_authority_hash=None,
        shell_type_authority_record_id=None,
        shell_type_authority_source_id=None,
        shell_type_authority_source_version=None,
        flow=flow,
        task032_request_evidence=request_evidence,
        task031_request_evidence=request.task031_request_evidence
        if type(request.task031_request_evidence) is dict
        else {},
    )


def validate_task033_result_identity(
    request: Task034Request,
    upstream_parts: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
) -> ReplayIdentity:
    """Validate S04 against the actual TASK033 success-result projection."""
    upstream, flow, request_evidence = upstream_parts
    result = _task033_success_result(upstream)
    try:
        expected_hash = task033_result_hash(result)
    except Exception as exc:
        raise _fail(
            "S04", BlockerCode.SSPD_TASK033_RESULT_HASH_MISMATCH, "task033_result_hash"
        ) from exc
    result_hash_value = result.get("result_hash")
    result_id_value = result.get("result_id")
    if (
        type(result_hash_value) is not str
        or type(result_id_value) is not str
        or request.task033_result_id != result_id_value
        or task033_result_id(result_hash_value) != result_id_value
    ):
        raise _fail("S04", BlockerCode.SSPD_TASK033_RESULT_ID_MISMATCH, "task033_result_id")
    if request.task033_result_hash != result_hash_value or expected_hash != result_hash_value:
        raise _fail("S04", BlockerCode.SSPD_TASK033_RESULT_HASH_MISMATCH, "task033_result_hash")
    return _identity(
        request,
        upstream,
        flow,
        request_evidence,
        task033_result_hash_value=result_hash_value,
        task033_result_id_value=result_id_value,
    )


def validate_task033_request_identity(
    request: Task034Request, identity: ReplayIdentity
) -> ReplayIdentity:
    """Validate S05 against the actual public TASK033 request evidence."""
    task033_request_evidence = request.task033_upstream_evidence.get("task033_request_evidence")
    if type(task033_request_evidence) is not dict:
        raise _fail("S05", BlockerCode.SSPD_TASK033_REQUEST_HASH_MISMATCH, "task033_request_hash")
    try:
        expected_hash = task033_request_hash(task033_request_evidence)
    except Exception as exc:
        raise _fail(
            "S05", BlockerCode.SSPD_TASK033_REQUEST_HASH_MISMATCH, "task033_request_hash"
        ) from exc
    task033_result = _task033_success_result(request.task033_upstream_evidence)
    actual_result_request_hash = task033_result.get("request_hash")
    if (
        type(actual_result_request_hash) is not str
        or expected_hash != actual_result_request_hash
        or actual_result_request_hash != request.task033_request_hash
    ):
        raise _fail("S05", BlockerCode.SSPD_TASK033_REQUEST_HASH_MISMATCH, "task033_request_hash")
    return identity


def replay_task031_request(request: Task034Request, identity: ReplayIdentity) -> ReplayIdentity:
    """Replay S06 from the original public TASK031 request shape."""
    if type(request.task031_request_evidence) is not dict:
        raise _fail(
            "S06", BlockerCode.SSPD_TASK031_REQUEST_EVIDENCE_MISSING, "task031_request_evidence"
        )
    try:
        task031_request_hash_value = canonical_task031_request_hash(
            request.task031_request_evidence
        )
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
    """Replay S07 TASK031 geometry identity from accepted TASK032 evidence."""
    task033_result = _task033_success_result(request.task033_upstream_evidence)
    task031_result = identity.task032_request_evidence.get("task031_result")
    if type(task031_result) is not dict or task031_result.get("status") != "VALID":
        raise _fail(
            "S07", BlockerCode.SSPD_TASK031_REQUEST_EVIDENCE_MISSING, "task031_request_evidence"
        )
    geometry = task031_result.get("geometry")
    if type(geometry) is not dict:
        raise _fail(
            "S07", BlockerCode.SSPD_TASK031_REQUEST_EVIDENCE_MISSING, "task031_request_evidence"
        )
    try:
        geometry_hash = task031_geometry_hash(geometry)
    except Exception as exc:
        raise _fail(
            "S07", BlockerCode.SSPD_TASK031_GEOMETRY_HASH_MISMATCH, "task031_geometry_hash"
        ) from exc
    geometry_id = task031_geometry_id(geometry_hash)
    if (
        geometry_id != geometry.get("geometry_id")
        or geometry_id != identity.flow.get("task031_geometry_id")
        or geometry_id != request.task031_geometry_id
        or geometry_id != task033_result.get("task031_geometry_id")
    ):
        raise _fail("S07", BlockerCode.SSPD_TASK031_GEOMETRY_ID_MISMATCH, "task031_geometry_id")
    if (
        geometry_hash != geometry.get("geometry_hash")
        or geometry_hash != identity.flow.get("task031_geometry_hash")
        or geometry_hash != request.task031_geometry_hash
        or geometry_hash != task033_result.get("task031_geometry_hash")
    ):
        raise _fail("S07", BlockerCode.SSPD_TASK031_GEOMETRY_HASH_MISMATCH, "task031_geometry_hash")
    return replace(identity, task031_geometry_hash=geometry_hash, task031_geometry_id=geometry_id)


def validate_task032_identity_join(
    request: Task034Request,
    identity: ReplayIdentity,
    *,
    validate_result_identity: bool = True,
) -> ReplayIdentity:
    """Validate TASK032 result identity carried by the actual TASK033 result."""
    if validate_result_identity:
        result = _task033_success_result(request.task033_upstream_evidence)
        flow = identity.flow
        if (
            type(flow.get("result_id")) is not str
            or flow.get("result_id") != result.get("task032_result_id")
            or request.task032_result_id != flow.get("result_id")
        ):
            raise _fail("S04", BlockerCode.SSPD_TASK032_RESULT_ID_MISMATCH, "task032_result_id")
        if (
            type(flow.get("result_hash")) is not str
            or flow.get("result_hash") != result.get("task032_result_hash")
            or request.task032_result_hash != flow.get("result_hash")
        ):
            raise _fail("S04", BlockerCode.SSPD_TASK032_RESULT_HASH_MISMATCH, "task032_result_hash")
    return identity


def replay_task032_and_upstreams(request: Task034Request) -> ReplayIdentity:
    """Execute the frozen S03-S07 upstream replay sequence."""
    upstream_parts = validate_task033_upstream_boundary(request)
    identity = validate_task033_result_identity(request, upstream_parts)
    identity = validate_task032_identity_join(request, identity)
    identity = validate_task033_request_identity(request, identity)
    identity = replay_task031_request(request, identity)
    return replay_task031_geometry(request, identity)


def task031_request_hash(evidence: dict[str, Any]) -> str:
    """Replay the frozen TASK-031 public request hash projection."""
    return canonical_task031_request_hash(evidence)


def _decimal_value(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        converted = Decimal(str(value))
    except (ArithmeticError, TypeError, ValueError):
        return None
    return converted if converted.is_finite() else None


def verify_auxiliary_bindings(request: Task034Request, identity: ReplayIdentity) -> ReplayIdentity:
    """Verify S08 authorities, including the frozen TASK031 request-evidence diameter path."""
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

    task031_request = request.task031_request_evidence
    if type(task031_request) is not dict:
        raise _fail(
            "S08", BlockerCode.SSPD_SHELL_INSIDE_DIAMETER_MISMATCH, "shell_inside_diameter_m"
        )
    baffle_result = task031_request.get("baffle_geometry_result")
    baffle_geometry = baffle_result.get("geometry") if type(baffle_result) is dict else None
    design = baffle_geometry.get("design_authority") if type(baffle_geometry) is dict else None
    tube = task031_request.get("tube_layout")
    layout_rule_authority = tube.get("layout_rule_authority") if type(tube) is dict else None
    tube_geometry = tube.get("tube_geometry") if type(tube) is dict else None
    if type(baffle_geometry) is not dict:
        baffle_geometry = {}
    if type(design) is not dict:
        design = {}
    if type(layout_rule_authority) is not dict:
        layout_rule_authority = {}
    if type(tube_geometry) is not dict:
        tube_geometry = {}

    spacing_value = design.get("spacing_sequence_m")
    expected_spacing: tuple[Decimal, ...] | None
    if isinstance(spacing_value, (list, tuple)):
        try:
            values = tuple(Decimal(str(value)) for value in spacing_value)
            expected_spacing = values if all(value.is_finite() for value in values) else None
        except (ArithmeticError, TypeError, ValueError):
            expected_spacing = None
    else:
        expected_spacing = None

    expected = (
        (
            request.shell_inside_diameter_m,
            _decimal_value(baffle_geometry.get("shell_inside_diameter_m")),
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
            _decimal_value(layout_rule_authority.get("pitch_m")),
            BlockerCode.SSPD_TUBE_PITCH_MISMATCH,
            "tube_pitch_m",
        ),
        (
            request.tube_outer_diameter_m,
            _decimal_value(tube_geometry.get("outer_diameter_m")),
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
        identity, property_hash=expected_property_hash, mass_flow_hash=expected_mass_flow_hash
    )


def verify_wall_property_authority(request: Task034Request) -> None:
    """Replay the v2 wall-property authority before accepting viscosity."""
    if request.wall_property_authority_hash is None:
        raise _fail(
            "S09", BlockerCode.SSPD_WALL_PROPERTY_AUTHORITY_MISSING, "wall_property_authority_hash"
        )
    from .canonical import wall_property_authority_hash

    if wall_property_authority_hash(request) != request.wall_property_authority_hash:
        raise _fail(
            "S09", BlockerCode.SSPD_WALL_PROPERTY_AUTHORITY_MISMATCH, "wall_property_authority_hash"
        )
    if (
        not isinstance(request.shell_side_wall_dynamic_viscosity_pa_s, Decimal)
        or not request.shell_side_wall_dynamic_viscosity_pa_s.is_finite()
        or request.shell_side_wall_dynamic_viscosity_pa_s <= 0
    ):
        raise _fail(
            "S09", BlockerCode.SSPD_WALL_VISCOSITY_INVALID, "shell_side_wall_dynamic_viscosity_pa_s"
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


def _validate_shell_type_authority(request: Task034Request) -> dict[str, Any]:
    authority = request.shell_type_authority
    if authority is None:
        raise _fail("S11", BlockerCode.SSPD_SHELL_TYPE_AUTHORITY_MISSING, "shell_type_authority")
    if type(authority) is not dict or set(authority) != set(SHELL_TYPE_AUTHORITY_FIELDS):
        raise _fail("S11", BlockerCode.SSPD_SHELL_TYPE_AUTHORITY_INVALID, "shell_type_authority")
    if authority.get("schema_version") != SHELL_TYPE_AUTHORITY_SCHEMA_VERSION:
        raise _fail(
            "S11",
            BlockerCode.SSPD_SHELL_TYPE_AUTHORITY_INVALID,
            "shell_type_authority.schema_version",
        )
    for field in (
        "shell_type",
        "task020_configuration_id",
        "task020_configuration_hash",
        "authority_source_id",
        "authority_source_version",
        "authority_record_id",
    ):
        if type(authority.get(field)) is not str or not authority[field]:
            raise _fail(
                "S11",
                BlockerCode.SSPD_SHELL_TYPE_AUTHORITY_INVALID,
                f"shell_type_authority.{field}",
            )
    for field in ("task020_configuration_hash", "authority_hash"):
        value = authority.get(field)
        if (
            type(value) is not str
            or len(value) != 64
            or any(char not in "0123456789abcdef" for char in value)
        ):
            raise _fail(
                "S11",
                BlockerCode.SSPD_SHELL_TYPE_AUTHORITY_INVALID,
                f"shell_type_authority.{field}",
            )
    refs = authority.get("evidence_refs")
    if (
        type(refs) not in (list, tuple)
        or not refs
        or any(type(ref) is not str or not ref for ref in refs)
        or len(set(refs)) != len(refs)
    ):
        raise _fail(
            "S11",
            BlockerCode.SSPD_SHELL_TYPE_AUTHORITY_INVALID,
            "shell_type_authority.evidence_refs",
        )
    try:
        expected_hash = shell_type_authority_hash(authority)
    except Exception as exc:
        raise _fail(
            "S11", BlockerCode.SSPD_SHELL_TYPE_AUTHORITY_INVALID, "shell_type_authority"
        ) from exc
    if expected_hash != authority.get("authority_hash"):
        raise _fail(
            "S11",
            BlockerCode.SSPD_SHELL_TYPE_AUTHORITY_REPLAY_MISMATCH,
            "shell_type_authority.authority_hash",
        )
    if (
        authority["task020_configuration_id"] != request.task020_configuration_id
        or authority["task020_configuration_hash"] != request.task020_configuration_hash
    ):
        raise _fail(
            "S11",
            BlockerCode.SSPD_SHELL_TYPE_AUTHORITY_CONFIGURATION_MISMATCH,
            "shell_type_authority.task020_configuration_id",
        )
    return authority


def verify_applicability(request: Task034Request, identity: ReplayIdentity) -> ReplayIdentity:
    """Verify explicit shell-type authority and frozen applicability predicates at S11."""
    authority = _validate_shell_type_authority(request)
    if authority["shell_type"] != SUPPORTED_SHELL_TYPE:
        raise _fail(
            "S11", BlockerCode.SSPD_UNSUPPORTED_SHELL_TYPE, "shell_type_authority.shell_type"
        )

    task031_request = request.task031_request_evidence
    baffle_result = (
        task031_request.get("baffle_geometry_result") if type(task031_request) is dict else None
    )
    baffle_geometry = baffle_result.get("geometry") if type(baffle_result) is dict else None
    design = baffle_geometry.get("design_authority") if type(baffle_geometry) is dict else None
    tube = task031_request.get("tube_layout") if type(task031_request) is dict else None
    layout_rule_authority = tube.get("layout_rule_authority") if type(tube) is dict else None
    if type(baffle_geometry) is not dict:
        baffle_geometry = {}
    if type(design) is not dict:
        design = {}
    if type(layout_rule_authority) is not dict:
        layout_rule_authority = {}

    checks = (
        (
            identity.flow.get("phase_region"),
            SUPPORTED_PHASE,
            BlockerCode.SSPD_UNSUPPORTED_PHASE,
            "phase_region",
        ),
        (
            identity.flow.get("rheology_model"),
            SUPPORTED_RHEOLOGY,
            BlockerCode.SSPD_UNSUPPORTED_RHEOLOGY,
            "rheology_model",
        ),
        (
            baffle_geometry.get("shell_pass_count"),
            SUPPORTED_SHELL_PASS_COUNT,
            BlockerCode.SSPD_UNSUPPORTED_SHELL_PASS_COUNT,
            "shell_pass_count",
        ),
        (
            design.get("baffle_type"),
            SUPPORTED_BAFFLE_TYPE,
            BlockerCode.SSPD_UNSUPPORTED_BAFFLE_TYPE,
            "baffle_type",
        ),
        (
            layout_rule_authority.get("pattern_family"),
            SUPPORTED_TUBE_LAYOUT,
            BlockerCode.SSPD_UNSUPPORTED_TUBE_LAYOUT,
            "pattern_family",
        ),
        (
            design.get("baffle_cut_fraction"),
            "0.25",
            BlockerCode.SSPD_UNSUPPORTED_BAFFLE_CUT,
            "baffle_cut",
        ),
    )
    for actual, expected, code, field in checks:
        if field == "baffle_cut":
            if actual != "0.25":
                raise _fail("S11", code, field)
        elif field == "pattern_family":
            # TASK-031's public PatternFamily token is TRIANGULAR.  The
            # TASK-034 authority names the same supported semantic as
            # TRIANGULAR_PITCH; preserve the upstream token at S08 and admit
            # only that exact public producer token at S11.
            if actual not in {expected, "TRIANGULAR"}:
                raise _fail("S11", code, field)
        elif actual != expected:
            raise _fail("S11", code, field)

    spacing = request.uniform_spacing_sequence_m
    if (
        type(spacing) is not tuple
        or not spacing
        or any(
            not isinstance(item, Decimal) or not item.is_finite() or item <= 0 for item in spacing
        )
        or any(item != spacing[0] for item in spacing)
    ):
        raise _fail(
            "S11", BlockerCode.SSPD_UNSUPPORTED_BAFFLE_SPACING, "uniform_spacing_sequence_m"
        )
    try:
        reynolds = Decimal(str(identity.flow["shell_side_reynolds_number"]))
    except (ArithmeticError, KeyError, TypeError, ValueError):
        raise _fail(
            "S11", BlockerCode.SSPD_REYNOLDS_OUTSIDE_DOMAIN, "shell_side_reynolds_number"
        ) from None
    if not reynolds.is_finite() or not Decimal("400") < reynolds < Decimal("1000000"):
        raise _fail("S11", BlockerCode.SSPD_REYNOLDS_OUTSIDE_DOMAIN, "shell_side_reynolds_number")
    return replace(
        identity,
        shell_type=authority["shell_type"],
        shell_type_authority_hash=authority["authority_hash"],
        shell_type_authority_record_id=authority["authority_record_id"],
        shell_type_authority_source_id=authority["authority_source_id"],
        shell_type_authority_source_version=authority["authority_source_version"],
    )


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
