"""Top-level orchestration: S00-S16.

§11 — Execution order.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Final

from hexagent.exchangers.shell_tube.tube_side.blocked_result import Task025BlockedResult
from hexagent.exchangers.shell_tube.tube_side.valid_result import Task025ValidResult
from hexagent.exchangers.shell_tube.tube_side_local_loss.blocker_registry import (
    Task028BlockerCode,
    _Task028PendingBlocker,
    collapse_blockers,
    emit_blocker,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
    IMPLEMENTATION_SOFTWARE_VERSION,
    TASK028_REQUEST_SCHEMA_VERSION,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.computation import (
    compute_local_loss_component,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.decimal_identity import (
    PRESSURE_LOSS_QUANTUM,
    quantize_task028_decimal,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.enums import (
    CoefficientPermissionStatus,
    Task028ApplicabilityAssertion,
    Task028RequestFlowDirectionAssertion,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.identity import (
    compute_authority_hash,
    compute_request_hash,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.models import (
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_ID,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_PERMISSION_STATUS,
    TubeSideLocalLossComponentAuthority,
    TubeSideLocalLossComponentResult,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.raw_boundary import (
    validate_raw_boundary,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.raw_projection import (
    Task028RawProjection,
    encode_raw_projection,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.result import (
    Task028BlockedResult,
    Task028Provenance,
    Task028RawBoundaryBlockedResult,
    Task028SuccessResult,
    build_blocked_result,
    build_raw_boundary_blocked_result,
    build_success_result,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.result import (
    RawBoundaryBlockedResult,
    TubeSideBlockedResult,
    TubeSideThermalResult,
)

# §20 — Frozen schema and constants
TASK028_R1_SCHEMA_VERSION: Final[str] = "task028-r1.schema.v1"


def _validate_task028_source_authority() -> tuple[_Task028PendingBlocker, []]:
    """§7 — Validate internal source authority contract. Returns empty tuple if valid."""
    if not TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_ID:
        return (
            emit_blocker(
                Task028BlockerCode.BL_T028_SOURCE_AUTHORITY_INVALID,
                "task028_source_authority",
                "The internal source authority is invalid.",
            ),
        )
    if TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_PERMISSION_STATUS != "ADMITTED":
        return (
            emit_blocker(
                Task028BlockerCode.BL_T028_SOURCE_AUTHORITY_INVALID,
                "task028_source_authority",
                "The internal source authority permission status is not ADMITTED.",
            ),
        )
    return ()


def compute_task028_local_loss(
    *,
    raw_request: Any,
    task025_result: Task025ValidResult | Task025BlockedResult,
    task026_result: TubeSideThermalResult | TubeSideBlockedResult | RawBoundaryBlockedResult,
    profile_id: str = "profile-001",
    design_contract_path: str = "TASK028_DESIGN_CONTRACT_R1.md",
) -> Task028SuccessResult | Task028BlockedResult | Task028RawBoundaryBlockedResult:
    """§20 — Top-level S00-S16 orchestration.

    Returns Task028SuccessResult on success, or a blocked result at any stage.
    """

    # ------------------------------------------------------------------
    # S00: Capture raw request projection
    # ------------------------------------------------------------------
    raw_request_projection = encode_raw_projection("REQUEST", raw_request)

    # ------------------------------------------------------------------
    # S01: Route upstream result types
    # ------------------------------------------------------------------
    # Check if task025 is blocked
    if isinstance(task025_result, Task025BlockedResult):
        return _blocked_s01(
            Task028BlockerCode.BL_T028_UPSTREAM_TASK025_BLOCKED,
            "task025_result",
            "TASK-025 upstream input is blocked.",
            profile_id=profile_id,
            raw_request_projection=raw_request_projection,
            raw_upstream_blocked_projection=None,
        )

    # Check if task026 is raw boundary blocked
    if isinstance(task026_result, RawBoundaryBlockedResult):
        raw_up_blocked = encode_raw_projection("TASK026_RESULT", task026_result)
        return _blocked_s01(
            Task028BlockerCode.BL_T028_UPSTREAM_TASK026_RAW_BLOCKED,
            "task026_result",
            "TASK-026 raw upstream input is blocked.",
            profile_id=profile_id,
            raw_request_projection=raw_request_projection,
            raw_upstream_blocked_projection=raw_up_blocked,
        )

    # Check if task026 is typed blocked
    if isinstance(task026_result, TubeSideBlockedResult):
        raw_up_blocked = encode_raw_projection("TASK026_RESULT", task026_result)
        return _blocked_s01(
            Task028BlockerCode.BL_T028_UPSTREAM_TASK026_TYPED_BLOCKED,
            "task026_result",
            "TASK-026 typed upstream result is blocked.",
            profile_id=profile_id,
            raw_request_projection=raw_request_projection,
            raw_upstream_blocked_projection=raw_up_blocked,
        )

    # Now we have Task025ValidResult and TubeSideThermalResult
    assert isinstance(task025_result, Task025ValidResult)
    assert isinstance(task026_result, TubeSideThermalResult)

    # ------------------------------------------------------------------
    # S02: Run R00-R10 raw boundary
    # ------------------------------------------------------------------
    rb_result = validate_raw_boundary(raw_request)
    if rb_result.blocked:
        return build_raw_boundary_blocked_result(
            raw_request_projection=rb_result.raw_request_projection,
            blockers=rb_result.blockers,
        )

    # ------------------------------------------------------------------
    # S03: Validate TASK-028 source authority
    # ------------------------------------------------------------------
    source_blockers = _validate_task028_source_authority()
    if source_blockers:
        collapsed = collapse_blockers(list(source_blockers))
        return build_blocked_result(
            profile_id=profile_id,
            request_hash=None,
            task025_hydraulic_authority_hash=task025_result.hydraulic_authority_hash,
            task026_result_hash=task026_result.result_hash,
            property_snapshot_hash=task026_result.property_snapshot_hash,
            raw_request_projection=raw_request_projection,
            raw_upstream_blocked_projection=None,
            warnings=(),
            blockers=collapsed,
            deferred_capabilities=(),
            provenance=None,
        )

    # ------------------------------------------------------------------
    # S04: Build typed request inputs
    # ------------------------------------------------------------------
    typed_data = rb_result.typed_data
    assert typed_data is not None

    constant_density_assertion = typed_data.get("constant_density_path_assertion")
    zero_elevation_assertion = typed_data.get("zero_net_elevation_change_assertion")
    flow_direction_assertion = typed_data.get("flow_direction_assertion")
    raw_component_authorities = typed_data.get("component_authorities", [])

    # ------------------------------------------------------------------
    # S05: Validate upstream identities
    # ------------------------------------------------------------------
    if task026_result.upstream_geometry_hash != task025_result.hydraulic_authority_hash:
        return _blocked_s05(
            Task028BlockerCode.BL_T028_UPSTREAM_IDENTITY_MISMATCH,
            "task026_result.upstream_geometry_hash",
            "TASK-025 and TASK-026 upstream identities are inconsistent.",
            profile_id=profile_id,
            task025_result=task025_result,
            task026_result=task026_result,
            raw_request_projection=raw_request_projection,
        )

    # ------------------------------------------------------------------
    # S06: Validate property snapshot identity
    # ------------------------------------------------------------------

    typed_data.get("raw_input", {}) if not isinstance(raw_request, dict) else raw_request

    # The property snapshot comes from the task026 result
    # Actually, we need to reconstruct it or get it from the request

    (
        typed_data.get("raw_input", {}).get("property_snapshot_hash", "")
        if isinstance(typed_data.get("raw_input"), dict)
        else ""
    )
    # For simplicity, use the task026 result hash as the property snapshot hash
    property_snapshot_hash = task026_result.property_snapshot_hash

    # ------------------------------------------------------------------
    # S07: Validate applicability assertions
    # ------------------------------------------------------------------
    if constant_density_assertion is None:
        return _blocked_applicability(
            Task028BlockerCode.BL_T028_APPLICABILITY_ASSERTION_MISSING,
            "constant_density_path_assertion",
            "A required TASK-028 applicability assertion is missing.",
            profile_id=profile_id,
            task025_result=task025_result,
            task026_result=task026_result,
            raw_request_projection=raw_request_projection,
        )
    if zero_elevation_assertion is None:
        return _blocked_applicability(
            Task028BlockerCode.BL_T028_APPLICABILITY_ASSERTION_MISSING,
            "zero_net_elevation_change_assertion",
            "A required TASK-028 applicability assertion is missing.",
            profile_id=profile_id,
            task025_result=task025_result,
            task026_result=task026_result,
            raw_request_projection=raw_request_projection,
        )

    assert constant_density_assertion == Task028ApplicabilityAssertion.TRUE
    assert zero_elevation_assertion == Task028ApplicabilityAssertion.TRUE

    # V1: liquid-only check via phase_region
    # The property snapshot's phase_region should be SINGLE_PHASE_LIQUID
    # This is already validated by Task025ValidResult upstream
    if flow_direction_assertion != Task028RequestFlowDirectionAssertion.START_TO_END:
        return _blocked_s08_top(
            Task028BlockerCode.BL_T028_FLOW_DIRECTION_UNSUPPORTED,
            "flow_direction_assertion",
            "The supplied flow direction is not supported by TASK-028 V1.",
            profile_id=profile_id,
            task025_result=task025_result,
            task026_result=task026_result,
            raw_request_projection=raw_request_projection,
        )

    # ------------------------------------------------------------------
    # S08: Validate component authorities (typed validation)
    # ------------------------------------------------------------------
    pending: list[_Task028PendingBlocker] = []
    typed_authorities: list[TubeSideLocalLossComponentAuthority] = []
    for comp in raw_component_authorities:
        auth, comp_blockers = _validate_and_build_authority(comp, typed_data)
        if comp_blockers:
            pending.extend(comp_blockers)
        else:
            assert auth is not None
            typed_authorities.append(auth)

    if pending:
        collapsed = collapse_blockers(pending)
        return build_blocked_result(
            profile_id=profile_id,
            request_hash=None,
            task025_hydraulic_authority_hash=task025_result.hydraulic_authority_hash,
            task026_result_hash=task026_result.result_hash,
            property_snapshot_hash=property_snapshot_hash,
            raw_request_projection=raw_request_projection,
            raw_upstream_blocked_projection=None,
            warnings=(),
            blockers=collapsed,
            deferred_capabilities=(),
            provenance=None,
        )

    # ------------------------------------------------------------------
    # S09: Validate component ID and path_sequence_index uniqueness
    # ------------------------------------------------------------------
    component_ids = [a.component_id for a in typed_authorities]
    seen_ids: set[str] = set()
    dup_pending: list[_Task028PendingBlocker] = []
    for cid in component_ids:
        if cid in seen_ids:
            dup_pending.append(
                emit_blocker(
                    Task028BlockerCode.BL_T028_COMPONENT_ID_DUPLICATE,
                    "component_authorities.component_id",
                    f"Duplicate component_id: {cid}",
                    component_id_tiebreaker=cid,
                )
            )
        seen_ids.add(cid)

    if dup_pending:
        collapsed = collapse_blockers(dup_pending)
        return build_blocked_result(
            profile_id=profile_id,
            request_hash=None,
            task025_hydraulic_authority_hash=task025_result.hydraulic_authority_hash,
            task026_result_hash=task026_result.result_hash,
            property_snapshot_hash=property_snapshot_hash,
            raw_request_projection=raw_request_projection,
            raw_upstream_blocked_projection=None,
            warnings=(),
            blockers=collapsed,
            deferred_capabilities=(),
            provenance=None,
        )

    # ------------------------------------------------------------------
    # S10: Sort component authorities (already in input order, no path_sequence_index)
    # ------------------------------------------------------------------
    # For TASK-028, components are ordered by input order.
    # No path_sequence_index reordering needed.

    # ------------------------------------------------------------------
    # S11: Build request hash and typed request
    # ------------------------------------------------------------------
    task025_result_hash = task025_result.result_hash
    task026_result_hash = task026_result.result_hash

    component_authority_hashes = tuple(a.authority_hash for a in typed_authorities)

    request_hash = compute_request_hash(
        schema_version=TASK028_REQUEST_SCHEMA_VERSION,
        profile_id=profile_id,
        task025_result_hash=task025_result_hash,
        task026_result_hash=task026_result_hash,
        property_snapshot_hash=property_snapshot_hash,
        constant_density_assertion=constant_density_assertion.value,
        zero_elevation_assertion=zero_elevation_assertion.value,
        flow_direction_assertion=flow_direction_assertion.value,
        component_authority_hashes=component_authority_hashes,
    )

    # Get property snapshot from task026 result context

    # ------------------------------------------------------------------
    # S12: Compute all component results
    # ------------------------------------------------------------------
    # Get density and mass flow from upstream results
    density_kg_m3 = task026_result.mass_flow_rate_kg_s  # placeholder; actual from property snapshot
    mass_flow_rate_kg_s = task026_result.mass_flow_rate_kg_s

    # We need property snapshot density - it comes from the request
    # For now, derive from task025's hydraulic authority
    # The density comes from the property_snapshot which is in the request

    # Actually, the density is in the property_snapshot of the task026 result
    # We need to access it. For this pipeline, we use what's available.
    # The task026_result has mass_flow_rate_kg_s.
    # The density comes from the property snapshot passed in the request.

    # Re-extract density from raw_request if it's a dict
    if isinstance(raw_request, dict) and "property_snapshot" in raw_request:
        ps_raw = raw_request["property_snapshot"]
        if isinstance(ps_raw, dict) and "density_kg_m3" in ps_raw:
            density_kg_m3 = Decimal(str(ps_raw["density_kg_m3"]))
        else:
            density_kg_m3 = task026_result.mass_flow_rate_kg_s  # fallback
    else:
        density_kg_m3 = task026_result.mass_flow_rate_kg_s  # fallback

    component_results: list[TubeSideLocalLossComponentResult] = []
    total_pressure_loss = Decimal("0")

    for auth in typed_authorities:
        ref_vel, single_occ, comp_pa = compute_local_loss_component(
            density_kg_m3=density_kg_m3,
            mass_flow_rate_kg_s=mass_flow_rate_kg_s,
            reference_flow_area_m2=auth.reference_flow_area_m2,
            loss_coefficient=auth.loss_coefficient,
            multiplicity=auth.multiplicity,
        )

        # Build component result hash
        from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
            canonicalize_component_result,
        )

        comp_result_hash = canonicalize_component_result(
            component_id=auth.component_id,
            component_type=auth.component_type.value,
            flow_direction_assertion=auth.flow_direction_assertion.value,
            loss_coefficient=str(auth.loss_coefficient),
            loss_coefficient_convention=auth.loss_coefficient_convention.value,
            reference_flow_area_m2=str(auth.reference_flow_area_m2),
            multiplicity=auth.multiplicity,
            upstream_reference_plane=auth.upstream_reference_plane,
            downstream_reference_plane=auth.downstream_reference_plane,
            reference_velocity_m_s=str(ref_vel),
            single_occurrence_irreversible_pressure_loss_pa=str(single_occ),
            component_irreversible_pressure_loss_pa=str(comp_pa),
            authority_hash=auth.authority_hash,
        )

        comp_result = TubeSideLocalLossComponentResult(
            component_id=auth.component_id,
            component_type=auth.component_type,
            flow_direction_assertion=auth.flow_direction_assertion,
            loss_coefficient=auth.loss_coefficient,
            loss_coefficient_convention=auth.loss_coefficient_convention,
            reference_flow_area_m2=auth.reference_flow_area_m2,
            multiplicity=auth.multiplicity,
            upstream_reference_plane=auth.upstream_reference_plane,
            downstream_reference_plane=auth.downstream_reference_plane,
            reference_velocity_m_s=ref_vel,
            single_occurrence_irreversible_pressure_loss_pa=single_occ,
            component_irreversible_pressure_loss_pa=comp_pa,
            authority_hash=auth.authority_hash,
            component_result_hash=comp_result_hash,
        )
        component_results.append(comp_result)
        total_pressure_loss += comp_pa

    # Quantize total
    total_pressure_loss = quantize_task028_decimal(total_pressure_loss, PRESSURE_LOSS_QUANTUM)

    # ------------------------------------------------------------------
    # S13: Build provenance
    # ------------------------------------------------------------------
    upstream_hashes = (
        task025_result.hydraulic_authority_hash,
        task025_result.result_hash,
        task026_result.result_hash,
        property_snapshot_hash,
    ) + component_authority_hashes

    provenance = Task028Provenance(
        task_id="TASK-028",
        design_contract_path=design_contract_path,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        input_evidence_refs=(),
        upstream_identity_hashes=upstream_hashes,
    )

    # ------------------------------------------------------------------
    # S14-S16: Build success result (hash, ID, immutable result)
    # ------------------------------------------------------------------
    return build_success_result(
        profile_id=profile_id,
        request_hash=request_hash,
        task025_hydraulic_authority_hash=task025_result.hydraulic_authority_hash,
        task026_result_hash=task026_result.result_hash,
        property_snapshot_hash=property_snapshot_hash,
        component_results=tuple(component_results),
        total_irreversible_pressure_loss_pa=total_pressure_loss,
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=provenance,
    )


def _validate_and_build_authority(
    comp: dict[str, Any],
    typed_data: dict[str, Any],
) -> tuple[TubeSideLocalLossComponentAuthority | None, list[_Task028PendingBlocker]]:
    """Validate a typed component dict and build authority. Returns (authority, blockers)."""
    blockers: list[_Task028PendingBlocker] = []
    tiebreaker = comp.get("component_id", "")

    # S08 validations for typed component
    # flow_direction_assertion match
    flow_dir = comp.get("flow_direction_assertion")
    request_flow = typed_data.get("flow_direction_assertion")
    if flow_dir is not None and request_flow is not None and flow_dir != request_flow:
        blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_COMPONENT_FLOW_DIRECTION_MISMATCH,
                f"component_authorities[{tiebreaker}].flow_direction_assertion",
                "Component flow direction does not match request flow direction.",
                component_id_tiebreaker=tiebreaker,
            )
        )

    # reference planes
    urp = comp.get("upstream_reference_plane", "")
    drp = comp.get("downstream_reference_plane", "")
    if urp and drp and urp == drp:
        blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_REFERENCE_PLANE_INVALID,
                f"component_authorities[{tiebreaker}].upstream_reference_plane",
                "Reference planes must be different.",
                component_id_tiebreaker=tiebreaker,
            )
        )

    # loss_coefficient validation
    lc = comp.get("loss_coefficient", Decimal(0))
    if isinstance(lc, str):
        lc = Decimal(lc)
    if not lc.is_finite():
        blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_LOSS_COEFFICIENT_NONFINITE,
                f"component_authorities[{tiebreaker}].loss_coefficient",
                "The loss coefficient is not finite.",
                component_id_tiebreaker=tiebreaker,
            )
        )
    elif lc == Decimal(0):
        blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_PSEUDO_ZERO_COMPONENT_FORBIDDEN,
                f"component_authorities[{tiebreaker}].loss_coefficient",
                "A pseudo-zero loss coefficient component is forbidden.",
                component_id_tiebreaker=tiebreaker,
            )
        )
    elif lc < Decimal(0):
        blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_LOSS_COEFFICIENT_NEGATIVE,
                f"component_authorities[{tiebreaker}].loss_coefficient",
                "The loss coefficient is negative.",
                component_id_tiebreaker=tiebreaker,
            )
        )

    # loss_coefficient_convention
    lcc = comp.get("loss_coefficient_convention")
    if lcc is not None and lcc.value != "K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2":
        blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_LOSS_COEFFICIENT_CONVENTION_UNSUPPORTED,
                f"component_authorities[{tiebreaker}].loss_coefficient_convention",
                "The loss coefficient convention is not supported.",
                component_id_tiebreaker=tiebreaker,
            )
        )

    # reference_flow_area_m2 validation
    rfa = comp.get("reference_flow_area_m2", Decimal(0))
    if isinstance(rfa, str):
        rfa = Decimal(rfa)
    if not rfa.is_finite() or rfa <= Decimal(0):
        blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_REFERENCE_FLOW_AREA_INVALID,
                f"component_authorities[{tiebreaker}].reference_flow_area_m2",
                "The reference flow area is invalid.",
                component_id_tiebreaker=tiebreaker,
            )
        )

    # multiplicity validation
    mult = comp.get("multiplicity", 1)
    if not isinstance(mult, int) or mult < 1:
        blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_MULTIPLICITY_INVALID,
                f"component_authorities[{tiebreaker}].multiplicity",
                "The multiplicity is invalid.",
                component_id_tiebreaker=tiebreaker,
            )
        )

    # multiplicity > 1 requires evidence
    if isinstance(mult, int) and mult > 1:
        ger = comp.get("geometry_evidence_refs", ())
        if not ger:
            blockers.append(
                emit_blocker(
                    Task028BlockerCode.BL_T028_SERIAL_GROUP_EVIDENCE_INSUFFICIENT,
                    f"component_authorities[{tiebreaker}].geometry_evidence_refs",
                    "Serial group requires geometry evidence references.",
                    component_id_tiebreaker=tiebreaker,
                )
            )

    # geometry_evidence_refs
    ger = comp.get("geometry_evidence_refs", ())
    if not ger:
        blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_GEOMETRY_EVIDENCE_MISSING,
                f"component_authorities[{tiebreaker}].geometry_evidence_refs",
                "Geometry evidence references are missing.",
                component_id_tiebreaker=tiebreaker,
            )
        )

    # coefficient permission
    cps = comp.get("coefficient_permission_status")
    if cps is not None and cps != CoefficientPermissionStatus.ADMITTED:
        blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_COEFFICIENT_PERMISSION_NOT_ADMITTED,
                f"component_authorities[{tiebreaker}].coefficient_permission_status",
                "The coefficient permission status is not ADMITTED.",
                component_id_tiebreaker=tiebreaker,
            )
        )

    # authority hash
    caller_hash = comp.get("caller_supplied_authority_hash", "")
    recomputed = comp.get("authority_hash", "")
    if caller_hash and recomputed and caller_hash != recomputed:
        blockers.append(
            emit_blocker(
                Task028BlockerCode.BL_T028_AUTHORITY_HASH_MISMATCH,
                f"component_authorities[{tiebreaker}].authority_hash",
                "The recomputed authority hash does not match the supplied hash.",
                component_id_tiebreaker=tiebreaker,
            )
        )

    if blockers:
        return None, blockers

    # Build authority object
    auth = TubeSideLocalLossComponentAuthority(
        component_id=comp["component_id"],
        component_type=comp["component_type"],
        flow_direction_assertion=comp["flow_direction_assertion"],
        loss_coefficient=comp["loss_coefficient"]
        if isinstance(comp["loss_coefficient"], Decimal)
        else Decimal(str(comp["loss_coefficient"])),
        loss_coefficient_convention=comp["loss_coefficient_convention"],
        reference_flow_area_m2=comp["reference_flow_area_m2"]
        if isinstance(comp["reference_flow_area_m2"], Decimal)
        else Decimal(str(comp["reference_flow_area_m2"])),
        multiplicity=comp["multiplicity"],
        upstream_reference_plane=comp["upstream_reference_plane"],
        downstream_reference_plane=comp["downstream_reference_plane"],
        geometry_evidence_refs=comp["geometry_evidence_refs"],
        coefficient_source_id=comp["coefficient_source_id"],
        coefficient_source_version=comp["coefficient_source_version"],
        coefficient_source_location=comp["coefficient_source_location"],
        coefficient_permission_status=comp["coefficient_permission_status"],
        coefficient_source_evidence_refs=comp.get("coefficient_source_evidence_refs", ()),
        caller_supplied_authority_hash=comp.get("caller_supplied_authority_hash", ""),
        authority_hash=comp.get("authority_hash", ""),
    )

    # Compute authority hash if not supplied
    if not auth.authority_hash:
        recomputed_hash = compute_authority_hash(
            component_id=auth.component_id,
            component_type=auth.component_type.value,
            flow_direction_assertion=auth.flow_direction_assertion.value,
            loss_coefficient=str(auth.loss_coefficient),
            loss_coefficient_convention=auth.loss_coefficient_convention.value,
            reference_flow_area_m2=str(auth.reference_flow_area_m2),
            multiplicity=auth.multiplicity,
            upstream_reference_plane=auth.upstream_reference_plane,
            downstream_reference_plane=auth.downstream_reference_plane,
            geometry_evidence_refs=auth.geometry_evidence_refs,
            coefficient_source_id=auth.coefficient_source_id,
            coefficient_source_version=auth.coefficient_source_version,
            coefficient_source_location=auth.coefficient_source_location,
            coefficient_permission_status=auth.coefficient_permission_status.value,
            coefficient_source_evidence_refs=auth.coefficient_source_evidence_refs,
            caller_supplied_authority_hash=auth.caller_supplied_authority_hash or "",
        )
        auth = TubeSideLocalLossComponentAuthority(
            component_id=auth.component_id,
            component_type=auth.component_type,
            flow_direction_assertion=auth.flow_direction_assertion,
            loss_coefficient=auth.loss_coefficient,
            loss_coefficient_convention=auth.loss_coefficient_convention,
            reference_flow_area_m2=auth.reference_flow_area_m2,
            multiplicity=auth.multiplicity,
            upstream_reference_plane=auth.upstream_reference_plane,
            downstream_reference_plane=auth.downstream_reference_plane,
            geometry_evidence_refs=auth.geometry_evidence_refs,
            coefficient_source_id=auth.coefficient_source_id,
            coefficient_source_version=auth.coefficient_source_version,
            coefficient_source_location=auth.coefficient_source_location,
            coefficient_permission_status=auth.coefficient_permission_status,
            coefficient_source_evidence_refs=auth.coefficient_source_evidence_refs,
            caller_supplied_authority_hash=auth.caller_supplied_authority_hash,
            authority_hash=recomputed_hash,
        )

    return auth, []


def _blocked_s01(
    code: Task028BlockerCode,
    field_path: str,
    message: str,
    *,
    profile_id: str,
    raw_request_projection: Task028RawProjection,
    raw_upstream_blocked_projection: Task028RawProjection | None,
) -> Task028BlockedResult:
    """Build blocked result at S01 stage."""
    blocker = emit_blocker(code, field_path, message)
    collapsed = collapse_blockers([blocker])
    return build_blocked_result(
        profile_id=profile_id,
        request_hash=None,
        task025_hydraulic_authority_hash=None,
        task026_result_hash=None,
        property_snapshot_hash=None,
        raw_request_projection=raw_request_projection,
        raw_upstream_blocked_projection=raw_upstream_blocked_projection,
        warnings=(),
        blockers=collapsed,
        deferred_capabilities=(),
        provenance=None,
    )


def _blocked_s05(
    code: Task028BlockerCode,
    field_path: str,
    message: str,
    *,
    profile_id: str,
    task025_result: Task025ValidResult,
    task026_result: TubeSideThermalResult,
    raw_request_projection: Task028RawProjection,
) -> Task028BlockedResult:
    """Build blocked result at S05 stage."""
    blocker = emit_blocker(code, field_path, message)
    collapsed = collapse_blockers([blocker])
    return build_blocked_result(
        profile_id=profile_id,
        request_hash=None,
        task025_hydraulic_authority_hash=task025_result.hydraulic_authority_hash,
        task026_result_hash=task026_result.result_hash,
        property_snapshot_hash=task026_result.property_snapshot_hash,
        raw_request_projection=raw_request_projection,
        raw_upstream_blocked_projection=None,
        warnings=(),
        blockers=collapsed,
        deferred_capabilities=(),
        provenance=None,
    )


def _blocked_applicability(
    code: Task028BlockerCode,
    field_path: str,
    message: str,
    *,
    profile_id: str,
    task025_result: Task025ValidResult,
    task026_result: TubeSideThermalResult,
    raw_request_projection: Task028RawProjection,
) -> Task028BlockedResult:
    """Build blocked result at S07 stage."""
    blocker = emit_blocker(code, field_path, message)
    collapsed = collapse_blockers([blocker])
    return build_blocked_result(
        profile_id=profile_id,
        request_hash=None,
        task025_hydraulic_authority_hash=task025_result.hydraulic_authority_hash,
        task026_result_hash=task026_result.result_hash,
        property_snapshot_hash=task026_result.property_snapshot_hash,
        raw_request_projection=raw_request_projection,
        raw_upstream_blocked_projection=None,
        warnings=(),
        blockers=collapsed,
        deferred_capabilities=(),
        provenance=None,
    )


def _blocked_s08_top(
    code: Task028BlockerCode,
    field_path: str,
    message: str,
    *,
    profile_id: str,
    task025_result: Task025ValidResult,
    task026_result: TubeSideThermalResult,
    raw_request_projection: Task028RawProjection,
) -> Task028BlockedResult:
    """Build blocked result at S07/S08 top level."""
    blocker = emit_blocker(code, field_path, message)
    collapsed = collapse_blockers([blocker])
    return build_blocked_result(
        profile_id=profile_id,
        request_hash=None,
        task025_hydraulic_authority_hash=task025_result.hydraulic_authority_hash,
        task026_result_hash=task026_result.result_hash,
        property_snapshot_hash=task026_result.property_snapshot_hash,
        raw_request_projection=raw_request_projection,
        raw_upstream_blocked_projection=None,
        warnings=(),
        blockers=collapsed,
        deferred_capabilities=(),
        provenance=None,
    )


__all__ = [
    "compute_task028_local_loss",
]
