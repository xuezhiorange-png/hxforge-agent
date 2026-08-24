"""TASK033-owned replay of frozen TASK032 upstream evidence."""

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
)
from .engineering_authority_snapshot import (
    ENGINEERING_AUTHORITY_HASH,
    ENGINEERING_AUTHORITY_ID,
    recompute_engineering_authority_hash,
)
from .models import (
    ShellSideHeatTransferRequest,
)


class AuthorityFailure(Exception):
    def __init__(self, stage: str, blockers: tuple[Any, ...]) -> None:
        super().__init__(stage)
        self.stage = stage
        self.blockers = blockers


@dataclass(frozen=True)
class ReplayIdentity:
    request_hash: str
    result_hash: str
    result_id: str
    geometry_hash: str
    geometry_id: str
    property_hash: str
    mass_flow_hash: str


def _fail(code: BlockerCode, stage: str, field: str) -> AuthorityFailure:
    return AuthorityFailure(stage, (make_blocker(code, stage=stage, field_path=field),))


def _positive_decimal(value: Any) -> Decimal:
    parsed = Decimal(str(value))
    if not parsed.is_finite() or parsed <= 0:
        raise ValueError(value)
    return parsed


def replay_task032_identity(
    request: ShellSideHeatTransferRequest,
) -> ReplayIdentity:
    flow = request.task032_flow_state
    evidence = request.task032_request_evidence
    try:
        expected_request_hash = task032_request_hash(evidence)
    except Exception as exc:
        raise _fail(
            BlockerCode.SSHT_TASK032_REQUEST_HASH_MISMATCH, "S04", "task032_request_evidence"
        ) from exc
    if expected_request_hash != flow.request_hash:
        raise _fail(
            BlockerCode.SSHT_TASK032_REQUEST_HASH_MISMATCH, "S04", "task032_flow_state.request_hash"
        )
    try:
        expected_result_hash = task032_success_hash(flow)
        expected_result_id = task032_result_id(expected_result_hash)
    except Exception as exc:
        raise _fail(
            BlockerCode.SSHT_TASK032_RESULT_HASH_MISMATCH, "S03", "task032_flow_state.result_hash"
        ) from exc
    blockers: list[Any] = []
    if expected_result_hash != flow.result_hash:
        blockers.append(
            make_blocker(
                BlockerCode.SSHT_TASK032_RESULT_HASH_MISMATCH,
                stage="S03",
                field_path="task032_flow_state.result_hash",
            )
        )
    if expected_result_id != flow.result_id:
        blockers.append(
            make_blocker(
                BlockerCode.SSHT_TASK032_RESULT_ID_MISMATCH,
                stage="S03",
                field_path="task032_flow_state.result_id",
            )
        )
    if blockers:
        raise AuthorityFailure("S03", tuple(blockers))
    try:
        geometry = evidence.task031_result["geometry"]
        expected_geometry_hash = task031_geometry_hash(geometry)
        expected_geometry_id = task031_geometry_id(expected_geometry_hash)
    except Exception as exc:
        raise _fail(
            BlockerCode.SSHT_TASK031_GEOMETRY_REPLAY_MISMATCH,
            "S05",
            "task032_request_evidence.task031_result.geometry",
        ) from exc
    if (
        evidence.task031_result.get("status") != "VALID"
        or evidence.task031_result.get("blockers")
        or not isinstance(geometry, dict)
        or expected_geometry_hash != geometry.get("geometry_hash")
        or expected_geometry_id != geometry.get("geometry_id")
        or expected_geometry_hash != flow.task031_geometry_hash
        or expected_geometry_id != flow.task031_geometry_id
    ):
        raise _fail(
            BlockerCode.SSHT_TASK031_GEOMETRY_REPLAY_MISMATCH,
            "S05",
            "task032_request_evidence.task031_result.geometry",
        )
    try:
        expected_property_hash = property_snapshot_hash(evidence.property_snapshot)
    except Exception as exc:
        raise _fail(
            BlockerCode.SSHT_PROPERTY_SNAPSHOT_HASH_MISMATCH, "S06", "property_snapshot"
        ) from exc
    if (
        expected_property_hash != evidence.property_snapshot.get("property_snapshot_hash")
        or expected_property_hash != evidence.property_snapshot_hash
        or expected_property_hash != flow.property_snapshot_hash
    ):
        raise _fail(
            BlockerCode.SSHT_PROPERTY_SNAPSHOT_HASH_MISMATCH,
            "S06",
            "property_snapshot.property_snapshot_hash",
        )
    try:
        expected_mass_hash = mass_flow_authority_hash(evidence.mass_flow_authority)
    except Exception as exc:
        raise _fail(
            BlockerCode.SSHT_MASS_FLOW_AUTHORITY_HASH_MISMATCH,
            "S07",
            "mass_flow_authority.authority_hash",
        ) from exc
    if (
        expected_mass_hash != evidence.mass_flow_authority.get("authority_hash")
        or expected_mass_hash != flow.mass_flow_authority_hash
    ):
        raise _fail(
            BlockerCode.SSHT_MASS_FLOW_AUTHORITY_HASH_MISMATCH,
            "S07",
            "mass_flow_authority.authority_hash",
        )
    return ReplayIdentity(
        request_hash=expected_request_hash,
        result_hash=expected_result_hash,
        result_id=expected_result_id,
        geometry_hash=expected_geometry_hash,
        geometry_id=expected_geometry_id,
        property_hash=expected_property_hash,
        mass_flow_hash=expected_mass_hash,
    )


def verify_same_case(request: ShellSideHeatTransferRequest, identity: ReplayIdentity) -> None:
    flow = request.task032_flow_state
    evidence = request.task032_request_evidence
    authority = evidence.mass_flow_authority
    geometry = evidence.task031_result.get("geometry")
    snapshot = evidence.property_snapshot
    equalities = (
        (flow.shell_side_case_id, authority.get("shell_side_case_id")),
        (flow.shell_side_stream_id, authority.get("shell_side_stream_id")),
        (flow.shell_side_fluid_id, authority.get("shell_side_fluid_id")),
        (flow.task020_configuration_id, authority.get("task020_configuration_id")),
        (flow.task020_configuration_hash, authority.get("task020_configuration_hash")),
        (
            flow.task020_configuration_id,
            geometry.get("task020_configuration_id") if isinstance(geometry, dict) else None,
        ),
        (
            flow.task020_configuration_hash,
            geometry.get("task020_configuration_hash") if isinstance(geometry, dict) else None,
        ),
        (flow.task031_geometry_id, authority.get("task031_geometry_id")),
        (flow.task031_geometry_hash, authority.get("task031_geometry_hash")),
        (flow.property_snapshot_hash, authority.get("property_snapshot_hash")),
        (flow.property_snapshot_hash, snapshot.get("property_snapshot_hash")),
    )
    if any(left != right for left, right in equalities):
        raise _fail(BlockerCode.SSHT_SAME_CASE_BINDING_MISMATCH, "S08", "same_case_identity")
    if (
        authority.get("task031_geometry_id") != identity.geometry_id
        or authority.get("task031_geometry_hash") != identity.geometry_hash
    ):
        raise _fail(
            BlockerCode.SSHT_SAME_CASE_BINDING_MISMATCH,
            "S08",
            "mass_flow_authority.task031_geometry_id",
        )


def verify_applicability(request: ShellSideHeatTransferRequest, identity: ReplayIdentity) -> None:
    flow = request.task032_flow_state
    evidence = request.task032_request_evidence
    geometry = evidence.task031_result.get("geometry")
    authority = evidence.mass_flow_authority
    snapshot = evidence.property_snapshot
    blockers: list[Any] = []
    if snapshot.get("phase_region") not in {"SINGLE_PHASE_LIQUID", "SINGLE_PHASE_GAS"}:
        blockers.append(
            make_blocker(
                BlockerCode.SSHT_PHASE_UNSUPPORTED,
                stage="S09",
                field_path="property_snapshot.phase_region",
            )
        )
    if authority.get("rheology_model") != "NEWTONIAN" or flow.rheology_model != "NEWTONIAN":
        blockers.append(
            make_blocker(
                BlockerCode.SSHT_RHEOLOGY_MODEL_UNSUPPORTED,
                stage="S09",
                field_path="mass_flow_authority.rheology_model",
            )
        )
    if authority.get("property_state_role") != "BULK_SHELL_SIDE_STATE":
        blockers.append(
            make_blocker(
                BlockerCode.SSHT_PROPERTY_STATE_ROLE_UNSUPPORTED,
                stage="S09",
                field_path="mass_flow_authority.property_state_role",
            )
        )
    if (
        authority.get("authority_profile_id")
        != "SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_BULK_FLOW_STATE_SCREENING_V1"
    ):
        blockers.append(
            make_blocker(
                BlockerCode.SSHT_FLOW_REGION_UNSUPPORTED,
                stage="S09",
                field_path="mass_flow_authority.authority_profile_id",
            )
        )
    if flow.flow_model != "SINGLE_BULK_PROPERTY_SNAPSHOT_ALGEBRAIC_FLOW_STATE_SCREENING":
        blockers.append(
            make_blocker(
                BlockerCode.SSHT_FLOW_REGION_UNSUPPORTED,
                stage="S09",
                field_path="task032_flow_state.flow_model",
            )
        )
    if (
        not isinstance(geometry, dict)
        or geometry.get("flow_region_identity") != "CENTRAL_CROSSFLOW_SCREENING"
    ):
        blockers.append(
            make_blocker(
                BlockerCode.SSHT_FLOW_REGION_UNSUPPORTED,
                stage="S09",
                field_path="task031_result.geometry.flow_region_identity",
            )
        )
    try:
        reynolds = _positive_decimal(flow.shell_side_reynolds_number)
        prandtl = _positive_decimal(flow.shell_side_prandtl_number)
        conductivity = _positive_decimal(snapshot["thermal_conductivity_w_m_k"])
        if not isinstance(geometry, dict):
            raise TypeError("geometry must be a dictionary")
        diameter = _positive_decimal(geometry["shell_side_equivalent_hydraulic_diameter_m"])
    except Exception:
        blockers.append(
            make_blocker(
                BlockerCode.SSHT_FORMULA_INPUT_DOMAIN_VIOLATION,
                stage="S10",
                field_path="engineering_inputs",
            )
        )
    else:
        if not (Decimal("2e3") < reynolds < Decimal("1e6")):
            blockers.append(
                make_blocker(
                    BlockerCode.SSHT_REYNOLDS_OUTSIDE_CORRELATION_DOMAIN,
                    stage="S09",
                    field_path="task032_flow_state.shell_side_reynolds_number",
                )
            )
        if not all(value.is_finite() and value > 0 for value in (prandtl, conductivity, diameter)):
            blockers.append(
                make_blocker(
                    BlockerCode.SSHT_FORMULA_INPUT_DOMAIN_VIOLATION,
                    stage="S10",
                    field_path="engineering_inputs",
                )
            )
    if blockers:
        raise AuthorityFailure("S09", tuple(blockers))


def verify_engineering_authority() -> None:
    if ENGINEERING_AUTHORITY_ID != "TASK033_KERN_KHARAJI_2021_EQ58_NO_WALL_CORRECTION_V1":
        raise _fail(
            BlockerCode.SSHT_CORRELATION_AUTHORITY_IDENTITY_MISMATCH, "S09", "correlation_id"
        )
    if recompute_engineering_authority_hash() != ENGINEERING_AUTHORITY_HASH:
        raise _fail(
            BlockerCode.SSHT_CORRELATION_AUTHORITY_IDENTITY_MISMATCH,
            "S09",
            "engineering_authority_hash",
        )


__all__ = [
    "AuthorityFailure",
    "ReplayIdentity",
    "replay_task032_identity",
    "verify_applicability",
    "verify_engineering_authority",
    "verify_same_case",
]
