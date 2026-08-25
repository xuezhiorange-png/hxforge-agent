"""TASK-034 upstream replay and authority bindings."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .blocker_registry import BlockerCode, make_blocker
from .canonical import (
    mass_flow_authority_hash,
    property_snapshot_hash,
    task031_geometry_hash,
    task031_geometry_id,
    task032_request_hash,
    task032_result_id,
    task032_success_hash,
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


def replay_task032_and_upstreams(request: Task034Request) -> ReplayIdentity:
    upstream = request.task033_upstream_evidence
    if upstream is None:
        raise _fail("S03", BlockerCode.SSPD_TASK033_UPSTREAM_MISSING, "task033_upstream_evidence")
    if not isinstance(upstream, dict):
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
    if upstream.get("status", "SUCCESS") != "SUCCESS":
        raise _fail(
            "S03", BlockerCode.SSPD_TASK033_UPSTREAM_INVALID, "task033_upstream_evidence.status"
        )
    flow, request_evidence, _ = _upstream_parts(upstream)
    if not flow or not request_evidence:
        raise _fail("S03", BlockerCode.SSPD_TASK033_UPSTREAM_INVALID, "task033_upstream_evidence")

    if request.task031_request_evidence is None:
        raise _fail(
            "S06", BlockerCode.SSPD_TASK031_REQUEST_EVIDENCE_MISSING, "task031_request_evidence"
        )

    expected_task033_request = task033_request_hash(upstream)
    task033_request = request.task033_request_hash
    if expected_task033_request != task033_request:
        raise _fail("S05", BlockerCode.SSPD_TASK033_REQUEST_HASH_MISMATCH, "task033_request_hash")
    expected_task033_result = task033_result_hash(upstream)
    upstream_result_hash = upstream.get("result_hash", upstream.get("task033_result_hash"))
    if (
        upstream_result_hash != request.task033_result_hash
        or expected_task033_result != upstream_result_hash
    ):
        raise _fail("S04", BlockerCode.SSPD_TASK033_RESULT_HASH_MISMATCH, "task033_result_hash")
    upstream_result_id = upstream.get("result_id", upstream.get("task033_result_id"))
    if (
        upstream_result_id != request.task033_result_id
        or task033_result_id(str(upstream_result_hash)) != upstream_result_id
    ):
        raise _fail("S04", BlockerCode.SSPD_TASK033_RESULT_ID_MISMATCH, "task033_result_id")

    try:
        expected_request_hash = task032_request_hash(request_evidence)
    except Exception as exc:
        raise _fail(
            "S06", BlockerCode.SSPD_TASK031_REQUEST_HASH_MISMATCH, "task032_request_evidence"
        ) from exc
    if expected_request_hash != flow.get(
        "request_hash"
    ) or request.task032_request_hash != flow.get("request_hash"):
        raise _fail("S06", BlockerCode.SSPD_TASK032_RESULT_HASH_MISMATCH, "task032_request_hash")
    expected_result_hash = task032_success_hash(flow)
    if expected_result_hash != flow.get("result_hash") or task032_result_id(
        expected_result_hash
    ) != flow.get("result_id"):
        code = (
            BlockerCode.SSPD_TASK032_RESULT_HASH_MISMATCH
            if expected_result_hash != flow.get("result_hash")
            else BlockerCode.SSPD_TASK032_RESULT_ID_MISMATCH
        )
        raise _fail("S04", code, "task032_flow_state.result_hash")
    if request.task032_result_hash != flow.get(
        "result_hash"
    ) or request.task032_result_id != flow.get("result_id"):
        code = (
            BlockerCode.SSPD_TASK032_RESULT_HASH_MISMATCH
            if request.task032_result_hash != flow.get("result_hash")
            else BlockerCode.SSPD_TASK032_RESULT_ID_MISMATCH
        )
        raise _fail("S04", code, "task032_result_identity")

    snapshot = request_evidence.get("property_snapshot")
    if not isinstance(snapshot, dict):
        raise _fail("S08", BlockerCode.SSPD_PROPERTY_SNAPSHOT_HASH_MISMATCH, "property_snapshot")
    expected_property_hash = property_snapshot_hash(snapshot)
    if (
        expected_property_hash != snapshot.get("property_snapshot_hash")
        or expected_property_hash != request_evidence.get("property_snapshot_hash")
        or expected_property_hash != flow.get("property_snapshot_hash")
    ):
        raise _fail(
            "S08", BlockerCode.SSPD_PROPERTY_SNAPSHOT_HASH_MISMATCH, "property_snapshot_hash"
        )
    mass_flow = request_evidence.get("mass_flow_authority")
    if (
        not isinstance(mass_flow, dict)
        or mass_flow_authority_hash(mass_flow) != mass_flow.get("authority_hash")
        or mass_flow.get("authority_hash") != flow.get("mass_flow_authority_hash")
    ):
        raise _fail(
            "S08", BlockerCode.SSPD_MASS_FLOW_AUTHORITY_HASH_MISMATCH, "mass_flow_authority_hash"
        )

    task031_result = request_evidence.get("task031_result")
    if (
        not isinstance(task031_result, dict)
        or task031_result.get("status") != "VALID"
        or not isinstance(task031_result.get("geometry"), dict)
    ):
        raise _fail(
            "S06", BlockerCode.SSPD_TASK031_REQUEST_EVIDENCE_MISSING, "task031_request_evidence"
        )
    geometry = task031_result["geometry"]
    geometry_hash = task031_geometry_hash(geometry)
    geometry_id = task031_geometry_id(geometry_hash)
    if (
        geometry_hash != geometry.get("geometry_hash")
        or geometry_hash != flow.get("task031_geometry_hash")
        or geometry_hash != request.task031_geometry_hash
    ):
        raise _fail("S07", BlockerCode.SSPD_TASK031_GEOMETRY_HASH_MISMATCH, "task031_geometry_hash")
    if (
        geometry_id != geometry.get("geometry_id")
        or geometry_id != flow.get("task031_geometry_id")
        or geometry_id != request.task031_geometry_id
    ):
        raise _fail("S07", BlockerCode.SSPD_TASK031_GEOMETRY_ID_MISMATCH, "task031_geometry_id")
    try:
        task031_request_hash = _task031_request_hash(request.task031_request_evidence)
    except Exception as exc:
        raise _fail(
            "S06",
            BlockerCode.SSPD_TASK031_REQUEST_HASH_MISMATCH,
            "task031_request_hash",
        ) from exc
    if task031_request_hash != request.task031_request_hash:
        raise _fail("S06", BlockerCode.SSPD_TASK031_REQUEST_HASH_MISMATCH, "task031_request_hash")

    return ReplayIdentity(
        task033_request_hash=task033_request,
        task033_result_hash=upstream_result_hash,
        task033_result_id=upstream_result_id,
        task032_request_hash=flow.get("request_hash"),
        task032_result_hash=flow.get("result_hash"),
        task032_result_id=flow.get("result_id"),
        task031_request_hash=task031_request_hash,
        task031_geometry_hash=geometry_hash,
        task031_geometry_id=geometry_id,
        property_hash=expected_property_hash,
        mass_flow_hash=mass_flow.get("authority_hash"),
        flow=flow,
        task032_request_evidence=request_evidence,
        task031_request_evidence=request.task031_request_evidence,
    )


def _task031_request_hash(evidence: dict[str, Any]) -> str:
    return canonical_task031_request_hash(evidence)


def task031_request_hash(evidence: dict[str, Any]) -> str:
    """Replay the frozen TASK-031 request evidence projection."""
    return _task031_request_hash(evidence)


def verify_auxiliary_bindings(request: Task034Request, identity: ReplayIdentity) -> None:
    geometry = identity.task032_request_evidence.get("task031_result", {}).get("geometry", {})
    design = (
        request.task031_request_evidence.get("baffle_geometry_result", {})
        .get("geometry", {})
        .get("design_authority", {})
    )
    tube = request.task031_request_evidence.get("tube_layout", {})
    expected = (
        (
            request.shell_inside_diameter_m,
            __import__("decimal").Decimal(str(geometry.get("shell_inside_diameter_m"))),
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
            tuple(
                __import__("decimal").Decimal(str(v)) for v in design.get("spacing_sequence_m", ())
            ),
            BlockerCode.SSPD_SPACING_SEQUENCE_MISMATCH,
            "uniform_spacing_sequence_m",
        ),
        (
            request.tube_pitch_m,
            __import__("decimal").Decimal(
                str(tube.get("layout_rule_authority", {}).get("pitch_m"))
            ),
            BlockerCode.SSPD_TUBE_PITCH_MISMATCH,
            "tube_pitch_m",
        ),
        (
            request.tube_outer_diameter_m,
            __import__("decimal").Decimal(
                str(tube.get("tube_geometry", {}).get("outer_diameter_m"))
            ),
            BlockerCode.SSPD_TUBE_OUTER_DIAMETER_MISMATCH,
            "tube_outer_diameter_m",
        ),
        (
            request.pattern_family,
            tube.get("layout_rule_authority", {}).get("pattern_family"),
            BlockerCode.SSPD_PATTERN_FAMILY_MISMATCH,
            "pattern_family",
        ),
    )
    for actual, expected_value, code, field in expected:
        if expected_value is not None and actual != expected_value:
            raise _fail("S08", code, field)


def verify_wall_property(request: Task034Request) -> None:
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
            upstream.get("pattern_family", request.pattern_family),
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
        if actual is not None and actual != expected:
            raise _fail("S11", code, field)
    spacing = request.uniform_spacing_sequence_m
    if len(spacing) < 1 or any(item != spacing[0] for item in spacing):
        raise _fail(
            "S11", BlockerCode.SSPD_UNSUPPORTED_BAFFLE_SPACING, "uniform_spacing_sequence_m"
        )
    reynolds = Decimal(str(flow.get("shell_side_reynolds_number")))
    if not Decimal("400") < reynolds < Decimal("1000000"):
        raise _fail("S11", BlockerCode.SSPD_REYNOLDS_OUTSIDE_DOMAIN, "shell_side_reynolds_number")


def verify_engineering_authority(request: Task034Request) -> None:
    if request.correlation_id != CORRELATION_ID:
        raise _fail("S11", BlockerCode.SSPD_SOURCE_AUTHORITY_MISMATCH, "correlation_id")


__all__ = [
    "AuthorityFailure",
    "ReplayIdentity",
    "replay_task032_and_upstreams",
    "task031_request_hash",
    "verify_auxiliary_bindings",
    "verify_wall_property",
    "verify_same_case",
    "verify_applicability",
    "verify_engineering_authority",
]
