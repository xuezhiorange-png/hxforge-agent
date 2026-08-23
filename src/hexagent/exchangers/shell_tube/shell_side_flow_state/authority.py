"""TASK-032 upstream replay, cross-binding, and applicability gates."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import (
    canonical as task031_canonical,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import models as task031_models
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    PhaseRegion,
    recompute_property_snapshot_hash,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.canonical import (
    KIND_STRING,
    composite_hash,
    string_payload,
)

from .blocker_registry import make_blocker
from .canonical import mass_flow_authority_hash, primitive
from .engineering_authority_snapshot import (
    ENGINEERING_AUTHORITY_HASH,
    ENGINEERING_AUTHORITY_ID,
    authority_canonical_projection,
    recompute_engineering_authority_hash,
)
from .models import (
    FIRST_SLICE_PROFILE_ID,
    FLOW_REGION_IDENTITY,
    PROPERTY_STATE_ROLE,
    RHEOLOGY_MODEL,
    BlockerCode,
    ShellSideFlowStateRequest,
    Task031GeometryBinding,
    Task031ResultBinding,
)


class AuthorityFailure(Exception):
    def __init__(self, stage: str, blockers: tuple[Any, ...]) -> None:
        super().__init__(stage)
        self.stage = stage
        self.blockers = blockers


def _blocker(
    code: BlockerCode,
    *,
    stage: str,
    field_path: str | None,
) -> Any:
    return make_blocker(code, stage=stage, field_path=field_path)


def _message_from_fragment(value: Any) -> task031_models.MessageEntry:
    item = primitive(value)
    if not isinstance(item, dict):
        return task031_models.MessageEntry(
            code="",
            field_path=None,
            message_key="",
            evidence_refs=(),
            details=(),
        )
    details_raw = item.get("details", [])
    details = tuple(
        (pair[0], pair[1])
        for pair in details_raw
        if isinstance(pair, list) and len(pair) == 2 and all(isinstance(part, str) for part in pair)
    )
    refs = tuple(ref for ref in item.get("evidence_refs", []) if isinstance(ref, str))
    return task031_models.MessageEntry(
        code=str(item.get("code", "")),
        field_path=item.get("field_path") if isinstance(item.get("field_path"), str) else None,
        message_key=str(item.get("message_key", "")),
        evidence_refs=refs,
        details=details,
    )


def _task031_geometry_model(
    geometry: Task031GeometryBinding,
) -> task031_models.ShellSideHydraulicGeometry:
    return task031_models.ShellSideHydraulicGeometry(
        schema_version=geometry.schema_version,
        geometry_id=geometry.geometry_id,
        geometry_hash=geometry.geometry_hash,
        request_hash=geometry.request_hash,
        task020_configuration_id=geometry.task020_configuration_id,
        task020_configuration_hash=geometry.task020_configuration_hash,
        task021_layout_id=geometry.task021_layout_id,
        task021_layout_hash=geometry.task021_layout_hash,
        task022_geometry_id=geometry.task022_geometry_id,
        task022_geometry_hash=geometry.task022_geometry_hash,
        task024_geometry_id=geometry.task024_geometry_id,
        task024_geometry_hash=geometry.task024_geometry_hash,
        engineering_authority_id=geometry.engineering_authority_id,
        engineering_authority_hash=geometry.engineering_authority_hash,
        formula_a_id=geometry.formula_a_id,
        formula_b_id=geometry.formula_b_id,
        pattern_family=geometry.pattern_family,
        flow_region_identity=geometry.flow_region_identity,
        central_inter_baffle_spacing_m=geometry.central_inter_baffle_spacing_m,
        central_crossflow_flow_area_m2=geometry.central_crossflow_flow_area_m2,
        shell_side_equivalent_hydraulic_diameter_m=geometry.shell_side_equivalent_hydraulic_diameter_m,
        warnings=tuple(_message_from_fragment(item) for item in geometry.warnings),
        blockers=tuple(_message_from_fragment(item) for item in geometry.blockers),
        deferred_capabilities=geometry.deferred_capabilities,
        provenance=tuple((key, primitive(value)) for key, value in geometry.provenance),
    )


def verify_task031_result(result: Task031ResultBinding) -> Task031GeometryBinding:
    blockers: list[Any] = []
    if result.status != "VALID":
        blockers.append(
            _blocker(
                BlockerCode.SSFS_TASK031_RESULT_INVALID,
                stage="S02",
                field_path="task031_result.status",
            )
        )
    if result.blockers:
        blockers.append(
            _blocker(
                BlockerCode.SSFS_TASK031_RESULT_HAS_BLOCKERS,
                stage="S02",
                field_path="task031_result.blockers",
            )
        )
    if result.geometry is None:
        blockers.append(
            _blocker(
                BlockerCode.SSFS_TASK031_GEOMETRY_MISSING,
                stage="S02",
                field_path="task031_result.geometry",
            )
        )
    if blockers:
        raise AuthorityFailure("S02", tuple(blockers))
    assert result.geometry is not None
    geometry = result.geometry
    try:
        model = _task031_geometry_model(geometry)
        expected_hash = task031_canonical.sha256_hex(
            task031_canonical.success_geometry_canonical_projection(model)
        )
        expected_id = task031_canonical.geometry_id(expected_hash)
    except Exception:
        raise AuthorityFailure(
            "S02",
            (
                _blocker(
                    BlockerCode.SSFS_TASK031_IDENTITY_MISMATCH,
                    stage="S02",
                    field_path="task031_result.geometry",
                ),
            ),
        ) from None
    if expected_hash != geometry.geometry_hash or expected_id != geometry.geometry_id:
        raise AuthorityFailure(
            "S02",
            (
                _blocker(
                    BlockerCode.SSFS_TASK031_IDENTITY_MISMATCH,
                    stage="S02",
                    field_path="task031_result.geometry",
                ),
            ),
        )
    return geometry


def _property_snapshot_hash_for_raw(snapshot: Any) -> str:
    if isinstance(snapshot.phase_region, PhaseRegion):
        return recompute_property_snapshot_hash(snapshot)
    fields = (
        ("density_kg_m3", KIND_STRING, string_payload(str(snapshot.density_kg_m3))),
        (
            "dynamic_viscosity_pa_s",
            KIND_STRING,
            string_payload(str(snapshot.dynamic_viscosity_pa_s)),
        ),
        (
            "thermal_conductivity_w_m_k",
            KIND_STRING,
            string_payload(str(snapshot.thermal_conductivity_w_m_k)),
        ),
        (
            "specific_heat_capacity_j_kg_k",
            KIND_STRING,
            string_payload(str(snapshot.specific_heat_capacity_j_kg_k)),
        ),
        ("bulk_temperature_k", KIND_STRING, string_payload(str(snapshot.bulk_temperature_k))),
        ("bulk_pressure_pa", KIND_STRING, string_payload(str(snapshot.bulk_pressure_pa))),
        ("phase_region", KIND_STRING, string_payload(str(snapshot.phase_region))),
        ("property_source_id", KIND_STRING, string_payload(snapshot.property_source_id)),
        ("property_source_version", KIND_STRING, string_payload(snapshot.property_source_version)),
    )
    return composite_hash("task026.property-snapshot.v1", fields)


def verify_property_snapshot(request: ShellSideFlowStateRequest) -> None:
    snapshot = request.property_snapshot
    blockers: list[Any] = []
    try:
        expected_hash = _property_snapshot_hash_for_raw(snapshot)
    except Exception:
        expected_hash = ""
    if (
        expected_hash != snapshot.property_snapshot_hash
        or expected_hash != request.property_snapshot_hash
    ):
        blockers.append(
            _blocker(
                BlockerCode.SSFS_PROPERTY_SNAPSHOT_HASH_MISMATCH,
                stage="S03",
                field_path="property_snapshot.property_snapshot_hash",
            )
        )
    if blockers:
        raise AuthorityFailure("S03", tuple(blockers))


def verify_mass_flow_authority(request: ShellSideFlowStateRequest) -> None:
    authority = request.mass_flow_authority
    blockers: list[Any] = []
    try:
        expected_hash = mass_flow_authority_hash(authority)
    except Exception:
        expected_hash = ""
    if expected_hash != authority.authority_hash:
        blockers.append(
            _blocker(
                BlockerCode.SSFS_MASS_FLOW_AUTHORITY_HASH_MISMATCH,
                stage="S04",
                field_path="mass_flow_authority.authority_hash",
            )
        )
    if not authority.mass_flow_rate_kg_s.is_finite() or authority.mass_flow_rate_kg_s <= 0:
        blockers.append(
            _blocker(
                BlockerCode.SSFS_MASS_FLOW_NON_POSITIVE,
                stage="S04",
                field_path="mass_flow_authority.mass_flow_rate_kg_s",
            )
        )
    if blockers:
        raise AuthorityFailure("S04", tuple(blockers))


def verify_same_case(request: ShellSideFlowStateRequest, geometry: Task031GeometryBinding) -> None:
    authority = request.mass_flow_authority
    blockers: list[Any] = []
    equalities = (
        (
            authority.task031_geometry_id,
            geometry.geometry_id,
            "mass_flow_authority.task031_geometry_id",
        ),
        (
            authority.task031_geometry_hash,
            geometry.geometry_hash,
            "mass_flow_authority.task031_geometry_hash",
        ),
        (
            authority.task020_configuration_id,
            geometry.task020_configuration_id,
            "mass_flow_authority.task020_configuration_id",
        ),
        (
            authority.task020_configuration_hash,
            geometry.task020_configuration_hash,
            "mass_flow_authority.task020_configuration_hash",
        ),
        (
            authority.property_snapshot_hash,
            request.property_snapshot.property_snapshot_hash,
            "mass_flow_authority.property_snapshot_hash",
        ),
    )
    for left, right, field_path in equalities:
        if left != right:
            blockers.append(
                _blocker(
                    BlockerCode.SSFS_SAME_CASE_BINDING_MISMATCH, stage="S05", field_path=field_path
                )
            )
    if blockers:
        raise AuthorityFailure("S05", tuple(blockers))


def verify_applicability(
    request: ShellSideFlowStateRequest,
    geometry: Task031GeometryBinding,
) -> None:
    authority = request.mass_flow_authority
    snapshot = request.property_snapshot
    blockers: list[Any] = []
    phase = (
        snapshot.phase_region.value
        if isinstance(snapshot.phase_region, PhaseRegion)
        else snapshot.phase_region
    )
    if phase not in {"SINGLE_PHASE_LIQUID", "SINGLE_PHASE_GAS"}:
        blockers.append(
            _blocker(
                BlockerCode.SSFS_PHASE_UNSUPPORTED,
                stage="S06",
                field_path="property_snapshot.phase_region",
            )
        )
    if authority.rheology_model != RHEOLOGY_MODEL:
        blockers.append(
            _blocker(
                BlockerCode.SSFS_RHEOLOGY_MODEL_UNSUPPORTED,
                stage="S06",
                field_path="mass_flow_authority.rheology_model",
            )
        )
    if authority.property_state_role != PROPERTY_STATE_ROLE:
        blockers.append(
            _blocker(
                BlockerCode.SSFS_PROPERTY_STATE_ROLE_UNSUPPORTED,
                stage="S06",
                field_path="mass_flow_authority.property_state_role",
            )
        )
    if authority.authority_profile_id != FIRST_SLICE_PROFILE_ID:
        blockers.append(
            _blocker(
                BlockerCode.SSFS_FLOW_MODEL_UNSUPPORTED,
                stage="S06",
                field_path="mass_flow_authority.authority_profile_id",
            )
        )
    values: tuple[Any, ...] = ()
    try:
        area = Decimal(geometry.central_crossflow_flow_area_m2)
        diameter = Decimal(geometry.shell_side_equivalent_hydraulic_diameter_m)
        properties = (
            snapshot.density_kg_m3,
            snapshot.dynamic_viscosity_pa_s,
            snapshot.specific_heat_capacity_j_kg_k,
            snapshot.thermal_conductivity_w_m_k,
        )
        values = (area, diameter, *properties)
    except Exception:
        pass
    if not values or any(not value.is_finite() or value <= 0 for value in values):
        blockers.append(
            _blocker(
                BlockerCode.SSFS_FORMULA_DOMAIN_VIOLATION,
                stage="S06",
                field_path="engineering_inputs",
            )
        )
    if geometry.flow_region_identity != FLOW_REGION_IDENTITY:
        blockers.append(
            _blocker(
                BlockerCode.SSFS_FORMULA_DOMAIN_VIOLATION,
                stage="S06",
                field_path="task031_result.geometry.flow_region_identity",
            )
        )
    if blockers:
        raise AuthorityFailure("S06", tuple(blockers))


def verify_engineering_authority() -> None:
    if recompute_engineering_authority_hash() != ENGINEERING_AUTHORITY_HASH:
        raise AuthorityFailure(
            "S07",
            (
                _blocker(
                    BlockerCode.SSFS_ENGINEERING_AUTHORITY_IDENTITY_MISMATCH,
                    stage="S07",
                    field_path="engineering_authority",
                ),
            ),
        )


__all__ = [
    "AuthorityFailure",
    "ENGINEERING_AUTHORITY_HASH",
    "ENGINEERING_AUTHORITY_ID",
    "authority_canonical_projection",
    "verify_applicability",
    "verify_engineering_authority",
    "verify_mass_flow_authority",
    "verify_property_snapshot",
    "verify_same_case",
    "verify_task031_result",
]
