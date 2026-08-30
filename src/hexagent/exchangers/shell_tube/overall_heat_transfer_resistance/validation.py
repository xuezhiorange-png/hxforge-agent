"""Fail-closed TASK-037 validation and identity-finalization pipeline."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any, cast

from hexagent.exchangers.shell_tube.tube_layout.models import TubeLayout
from hexagent.exchangers.shell_tube.tube_side import Task025BlockedResult, Task025ValidResult

from .authority import (
    build_surface_projection,
    build_wall_projection,
    geometry_decimals,
    is_sha256_hex,
    replay_task025_valid_result,
    validate_conductivity_authority,
    validate_fouling_authority,
    validate_material_authority,
    validate_task021_layout,
    validate_task021_task025_binding,
)
from .blocker_registry import BlockerCode, make_blocker, sort_blockers
from .canonical import (
    producer_area_precision_policy_hash,
    raw_boundary_blocked_result_hash,
    request_hash,
    result_id_from_hash,
    success_result_hash,
    surface_transform_authority_hash,
    typed_blocked_result_hash,
    wall_resistance_authority_hash,
)
from .engineering import compute_outer_to_inner_area_ratio, compute_wall_resistance
from .models import (
    BlockerEntry,
    FrozenIdentity,
    InsideFoulingResistanceAuthority,
    OutsideFoulingResistanceAuthority,
    Task037RawBoundaryBlockedResult,
    Task037Request,
    Task037SuccessResult,
    Task037TypedBlockedResult,
    Task037ValidationResult,
)
from .provenance import build_provenance, producer_edges, verify_provenance
from .raw_projection import project_raw_request
from .schema import (
    APPLICABILITY_ROWS,
    DEFERRED_CAPABILITIES,
    DESIGN_ISSUE,
    DESIGN_REVISION,
    ENGINEERING_SOURCE_ID,
    ENGINEERING_SOURCE_LOCATION_WALL,
    ENGINEERING_SOURCE_LOCATIONS,
    IMPLEMENTATION_SOFTWARE_VERSION,
    OVERALL_U_REFERENCE_SURFACE,
    PRODUCER_AREA_PRECISION_POLICY_HASH,
    REQUEST_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
    SOURCE_DEFINITION_ISSUE,
    SOURCE_DEFINITION_REVIEW_AUDIT_COMMENT,
    SOURCE_DEFINITION_REVISION,
    SOURCE_FORMULA_IDENTITY,
    TASK025_AREA_QUANTUM_M2,
    TASK025_AREA_ROUNDING_MODE,
    TASK025_PUBLIC_AREA_PRECISION_POLICY_ID,
    TASK025_PUBLIC_AREA_QUANTUM_M2,
    TASK025_PUBLIC_AREA_ROUNDING_MODE,
    TASK037_VERSION,
    TUBE_SIDE_FILM_REFERENCE_SURFACE,
    WALL_BUNDLE_NUMERICAL_BASIS,
)


def _details(reason: str) -> tuple[tuple[str, str], ...]:
    return (("reason", reason),)


def _typed_blocked(
    *,
    blockers: list[BlockerEntry],
    request_hash_value: str | None = None,
    task021_identity: FrozenIdentity | None = None,
    task025_identity: FrozenIdentity | None = None,
    task025_hydraulic_authority_hash: str | None = None,
    tube_geometry_snapshot_hash: str | None = None,
    heat_transfer_length_hash: str | None = None,
    failure_stage: str,
) -> Task037ValidationResult:
    ordered = sort_blockers(blockers)
    provisional = Task037TypedBlockedResult(
        schema_version="task037.typed-blocked-result.v1",
        task037_version=TASK037_VERSION,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        failure_stage=failure_stage,
        request_hash=request_hash_value,
        task021_identity=task021_identity,
        task025_identity=task025_identity,
        task025_hydraulic_authority_hash=task025_hydraulic_authority_hash,
        tube_geometry_snapshot_hash=tube_geometry_snapshot_hash,
        heat_transfer_length_hash=heat_transfer_length_hash,
        blockers=ordered,
        warnings=(),
        deferred_capabilities=DEFERRED_CAPABILITIES,
        provenance=None,
        blocked_result_hash="0" * 64,
    )
    return Task037ValidationResult(
        status="BLOCKED",
        blocked_result=replace(
            provisional, blocked_result_hash=typed_blocked_result_hash(provisional)
        ),
    )


def _raw_boundary_blocked(value: object) -> Task037ValidationResult:
    projection = project_raw_request(value)
    blockers = (
        make_blocker(
            BlockerCode.RAW_INPUT_TYPE_INVALID,
            field_path="raw_input",
            message_key="top_level_exact_production_types_required",
        ),
    )
    provisional = Task037RawBoundaryBlockedResult(
        schema_version="task037.raw-boundary-blocked-result.v1",
        task037_version=TASK037_VERSION,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        raw_request_projection=projection,
        blockers=blockers,
        warnings=(),
        deferred_capabilities=DEFERRED_CAPABILITIES,
        blocked_result_hash="0" * 64,
    )
    return Task037ValidationResult(
        status="BLOCKED",
        raw_boundary_blocked_result=replace(
            provisional, blocked_result_hash=raw_boundary_blocked_result_hash(provisional)
        ),
    )


def _request_hash_or_none(request: Any) -> str | None:
    if type(request) is not Task037Request:
        return None
    try:
        return request_hash(request)
    except Exception:
        return None


def _block(code: BlockerCode, field: str, reason: str) -> BlockerEntry:
    return make_blocker(code, field_path=field, message_key=reason, details=_details(reason))


def evaluate_task037(
    request: Task037Request,
    task021_layout: TubeLayout,
    task025_result: Task025ValidResult | Task025BlockedResult,
) -> Task037ValidationResult:
    """Evaluate TASK037 from exact typed public producer values.

    The S00 exact-type boundary runs before any downstream attribute access.
    Stages S02/S03 replay public producer identities; S08/S09 run only after
    all authority gates pass.
    """

    # S00: exact production type identity for all top-level arguments.  A
    # Task025BlockedResult is an accepted typed upstream and is handled at S03.
    if (
        type(request) is not Task037Request
        or type(task021_layout) is not TubeLayout
        or type(task025_result) not in {Task025ValidResult, Task025BlockedResult}
    ):
        return _raw_boundary_blocked((request, task021_layout, task025_result))

    request_hash_value = _request_hash_or_none(request)

    # S01: the frozen request dataclass normally enforces this at construction;
    # object-level mutation is still treated as a runtime blocker.
    if (
        request.schema_version != REQUEST_SCHEMA_VERSION
        or request.task037_version != TASK037_VERSION
        or request.implementation_software_version != IMPLEMENTATION_SOFTWARE_VERSION
    ):
        return _typed_blocked(
            blockers=[
                _block(BlockerCode.REQUEST_SCHEMA_INVALID, "request", "request_schema_invalid")
            ],
            request_hash_value=request_hash_value,
            failure_stage="S01_TYPED_REQUEST_SCHEMA_VALIDATION",
        )

    # S02: TASK021 public layout identity and geometry snapshot admission.
    ok, reason = validate_task021_layout(task021_layout)
    if not ok:
        return _typed_blocked(
            blockers=[_block(BlockerCode.TASK021_INVALID, "task021_layout", reason)],
            request_hash_value=request_hash_value,
            failure_stage="S02_TASK021_UPSTREAM_VALIDATION",
        )
    task021_identity = FrozenIdentity(
        identity_type="task021.tube-layout.v1",
        identity_id=task021_layout.layout_id,
        identity_hash=task021_layout.layout_hash,
    )

    # S03: a typed Task025 blocked result remains a typed blocked path and
    # cannot be converted to a synthetic success or zero-area result.
    if type(task025_result) is Task025BlockedResult:
        return _typed_blocked(
            blockers=[_block(BlockerCode.TASK025_BLOCKED, "task025_result", "task025_blocked")],
            request_hash_value=request_hash_value,
            task021_identity=task021_identity,
            failure_stage="S03_TASK025_UPSTREAM_VALIDATION",
        )
    task025_result = cast(Task025ValidResult, task025_result)
    ok, reason = replay_task025_valid_result(task025_result)
    if not ok:
        code = (
            BlockerCode.TASK025_AREA_QUANTUM_NONCANONICAL
            if reason == "task025_public_area_noncanonical"
            else BlockerCode.TASK025_RESULT_HASH_MISMATCH
            if reason == "task025_result_hash_mismatch"
            else BlockerCode.TASK025_RESULT_ID_MISMATCH
            if reason == "task025_result_id_mismatch"
            else BlockerCode.TASK025_INVALID
        )
        field_path = (
            "task025_result.internal_heat_transfer_surface_area_m2"
            if reason == "task025_public_area_noncanonical"
            else "task025_result"
        )
        return _typed_blocked(
            blockers=[_block(code, field_path, reason)],
            request_hash_value=request_hash_value,
            task021_identity=task021_identity,
            failure_stage="S03_TASK025_UPSTREAM_VALIDATION",
        )
    task025_identity = FrozenIdentity(
        identity_type="task025.tube-side.v1",
        identity_id=task025_result.result_id,
        identity_hash=task025_result.result_hash,
    )

    # S04: prove TASK021/TASK025 identity continuity without reconstructing
    # the producer hydraulic authority.
    ok, reason = validate_task021_task025_binding(task021_layout, task025_result)
    if not ok:
        code = (
            BlockerCode.TASK025_HYDRAULIC_AUTHORITY_INVALID
            if "hydraulic" in reason or "provenance" in reason
            else BlockerCode.TASK021_TASK025_MISMATCH
        )
        return _typed_blocked(
            blockers=[_block(code, "task021_task025_binding", reason)],
            request_hash_value=request_hash_value,
            task021_identity=task021_identity,
            task025_identity=task025_identity,
            task025_hydraulic_authority_hash=task025_result.hydraulic_authority_hash,
            tube_geometry_snapshot_hash=task021_layout.tube_geometry.snapshot_hash,
            heat_transfer_length_hash=task025_result.heat_transfer_authority.length_hash,
            failure_stage="S04_TASK021_TASK025_CROSS_BINDING",
        )

    # S05: geometry and semantic surface admission.
    try:
        inner, outer, _ = geometry_decimals(task021_layout)
        ratio = compute_outer_to_inner_area_ratio(inner, outer)
        surface_projection = build_surface_projection(task021_layout, task025_result)
        surface_projection["outer_to_inner_area_ratio"] = ratio
    except (TypeError, ValueError, ArithmeticError) as exc:
        return _typed_blocked(
            blockers=[
                _block(BlockerCode.GEOMETRY_INVALID, "task021_layout.tube_geometry", str(exc))
            ],
            request_hash_value=request_hash_value,
            task021_identity=task021_identity,
            task025_identity=task025_identity,
            task025_hydraulic_authority_hash=task025_result.hydraulic_authority_hash,
            tube_geometry_snapshot_hash=task021_layout.tube_geometry.snapshot_hash,
            heat_transfer_length_hash=task025_result.heat_transfer_authority.length_hash,
            failure_stage="S05_GEOMETRY_AND_SURFACE_SEMANTIC_VALIDATION",
        )

    # S06: explicit wall material/conductivity admission; no hidden defaults.
    material_ok, material_reason = validate_material_authority(request.wall_material_authority)
    conductivity_ok, conductivity_reason = validate_conductivity_authority(
        request.wall_thermal_conductivity_authority, request.wall_material_authority
    )
    if not material_ok or not conductivity_ok:
        blockers: list[BlockerEntry] = []
        if not material_ok:
            blockers.append(
                _block(
                    BlockerCode.MATERIAL_AUTHORITY_INVALID,
                    "wall_material_authority",
                    material_reason,
                )
            )
        if not conductivity_ok:
            blockers.append(
                _block(
                    BlockerCode.CONDUCTIVITY_AUTHORITY_INVALID,
                    "wall_thermal_conductivity_authority",
                    conductivity_reason,
                )
            )
        return _typed_blocked(
            blockers=blockers,
            request_hash_value=request_hash_value,
            task021_identity=task021_identity,
            task025_identity=task025_identity,
            task025_hydraulic_authority_hash=task025_result.hydraulic_authority_hash,
            tube_geometry_snapshot_hash=task021_layout.tube_geometry.snapshot_hash,
            heat_transfer_length_hash=task025_result.heat_transfer_authority.length_hash,
            failure_stage="S06_WALL_MATERIAL_AND_CONDUCTIVITY_AUTHORITY_ADMISSIBILITY_VALIDATION",
        )

    # S07: inside and outside fouling are independent explicit authorities.
    inside_ok, inside_reason = validate_fouling_authority(
        request.inside_fouling_authority, side="INSIDE"
    )
    outside_ok, outside_reason = validate_fouling_authority(
        request.outside_fouling_authority, side="OUTSIDE"
    )
    if not inside_ok or not outside_ok:
        blockers = []
        if not inside_ok:
            blockers.append(
                _block(
                    BlockerCode.FOULING_AUTHORITY_INVALID, "inside_fouling_authority", inside_reason
                )
            )
        if not outside_ok:
            blockers.append(
                _block(
                    BlockerCode.FOULING_AUTHORITY_INVALID,
                    "outside_fouling_authority",
                    outside_reason,
                )
            )
        return _typed_blocked(
            blockers=blockers,
            request_hash_value=request_hash_value,
            task021_identity=task021_identity,
            task025_identity=task025_identity,
            task025_hydraulic_authority_hash=task025_result.hydraulic_authority_hash,
            tube_geometry_snapshot_hash=task021_layout.tube_geometry.snapshot_hash,
            heat_transfer_length_hash=task025_result.heat_transfer_authority.length_hash,
            failure_stage="S07_FOULING_AUTHORITY_ADMISSIBILITY_VALIDATION",
        )

    # S08: compute the surface transform from accepted public upstream values.
    try:
        surface_hash = surface_transform_authority_hash(surface_projection)
    except Exception as exc:
        return _typed_blocked(
            blockers=[_block(BlockerCode.SURFACE_AUTHORITY_INVALID, "surface_transform", str(exc))],
            request_hash_value=request_hash_value,
            task021_identity=task021_identity,
            task025_identity=task025_identity,
            task025_hydraulic_authority_hash=task025_result.hydraulic_authority_hash,
            tube_geometry_snapshot_hash=task021_layout.tube_geometry.snapshot_hash,
            heat_transfer_length_hash=task025_result.heat_transfer_authority.length_hash,
            failure_stage="S08_SURFACE_TRANSFORM_COMPUTATION",
        )

    # S09: wall engineering is the only TASK037 numerical realization.  It
    # consumes the Task025 public area and never consumes L_ht/N_active.
    try:
        outputs = compute_wall_resistance(
            inner,
            outer,
            request.wall_thermal_conductivity_authority.thermal_conductivity_w_m_k,
            task025_result.internal_heat_transfer_surface_area_m2,
        )
        wall_projection = build_wall_projection(
            surface_hash=surface_hash,
            result=task025_result,
            material=request.wall_material_authority,
            conductivity=request.wall_thermal_conductivity_authority,
            wall_bundle_conduction_resistance_k_w=outputs.wall_bundle_conduction_resistance_k_w,
            wall_resistance_outer_surface_m2_k_w=outputs.wall_resistance_outer_surface_m2_k_w,
        )
        wall_hash = wall_resistance_authority_hash(wall_projection)
    except (TypeError, ValueError, ArithmeticError) as exc:
        return _typed_blocked(
            blockers=[_block(BlockerCode.DECIMAL_FAILURE, "wall_resistance", str(exc))],
            request_hash_value=request_hash_value,
            task021_identity=task021_identity,
            task025_identity=task025_identity,
            task025_hydraulic_authority_hash=task025_result.hydraulic_authority_hash,
            tube_geometry_snapshot_hash=task021_layout.tube_geometry.snapshot_hash,
            heat_transfer_length_hash=task025_result.heat_transfer_authority.length_hash,
            failure_stage="S09_CYLINDRICAL_WALL_RESISTANCE_COMPUTATION",
        )

    # S10: all fixed ledgers are explicit and deterministic.
    inside = request.inside_fouling_authority
    outside = request.outside_fouling_authority
    fouling_ledger = (
        f"inside=PASS:{inside.reference_surface}:{inside.fouling_resistance_m2_k_w}",
        f"outside=PASS:{outside.reference_surface}:{outside.fouling_resistance_m2_k_w}",
    )
    applicability_ledger = tuple(f"{row}=PASS" for row in APPLICABILITY_ROWS)
    completeness_ledger = (
        "C01_SURFACE_BASIS_AUTHORITY_COMPLETE=PASS",
        "C02_WALL_RESISTANCE_AUTHORITY_COMPLETE=PASS",
        "C03_INSIDE_FOULING_AUTHORITY_COMPLETE=PASS",
        "C04_OUTSIDE_FOULING_AUTHORITY_COMPLETE=PASS",
        "C05_FOULING_AUTHORITY_LEDGER_COMPLETE=PASS",
        "C06_TASK038_FORWARD_CONSUMER_CONTRACT_COMPLETE=PASS",
    )

    # S11: build the self-edge-free provenance node, then result and UUID.
    try:
        provenance = build_provenance(
            {
                "request_hash": request_hash_value,
                "task021_layout_hash": task021_layout.layout_hash,
                "task025_result_hash": task025_result.result_hash,
                "task025_hydraulic_authority_hash": task025_result.hydraulic_authority_hash,
                "tube_geometry_snapshot_hash": task021_layout.tube_geometry.snapshot_hash,
                "heat_transfer_length_hash": task025_result.heat_transfer_authority.length_hash,
                "task025_internal_heat_transfer_surface_area_m2": (
                    task025_result.internal_heat_transfer_surface_area_m2
                ),
                "task025_area_quantum_m2": Decimal("1E-10"),
                "task025_area_rounding_mode": "ROUND_HALF_EVEN",
                "producer_area_precision_policy_id": (
                    "task037.task025-public-area-authority.accept-positive-v1"
                ),
                "producer_area_precision_policy_hash": PRODUCER_AREA_PRECISION_POLICY_HASH,
                "producer_precision_limitation_disclosed": True,
                "producer_precision_threshold_defined": False,
                "wall_material_authority_hash": request.wall_material_authority.authority_hash,
                "wall_conductivity_authority_hash": (
                    request.wall_thermal_conductivity_authority.authority_hash
                ),
                "inside_fouling_authority_hash": inside.authority_hash,
                "outside_fouling_authority_hash": outside.authority_hash,
                "surface_transform_authority_hash": surface_hash,
                "wall_resistance_authority_hash": wall_hash,
                "source_identity_hashes": (
                    PRODUCER_AREA_PRECISION_POLICY_HASH,
                    request.wall_material_authority.authority_hash,
                    request.wall_thermal_conductivity_authority.authority_hash,
                    inside.authority_hash,
                    outside.authority_hash,
                ),
                "producer_edges": producer_edges(),
                "evidence_refs": request.evidence_refs,
                "deferred_capabilities": DEFERRED_CAPABILITIES,
            }
        )
        provisional = Task037SuccessResult(
            schema_version=RESULT_SCHEMA_VERSION,
            task037_version=TASK037_VERSION,
            implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
            request_hash=request_hash_value or "0" * 64,
            task021_identity=task021_identity,
            task025_identity=task025_identity,
            task025_hydraulic_authority_hash=task025_result.hydraulic_authority_hash,
            tube_geometry_snapshot_hash=task021_layout.tube_geometry.snapshot_hash,
            heat_transfer_length_hash=task025_result.heat_transfer_authority.length_hash,
            tube_side_film_reference_surface=TUBE_SIDE_FILM_REFERENCE_SURFACE,
            overall_u_reference_surface=OVERALL_U_REFERENCE_SURFACE,
            outer_to_inner_area_ratio=outputs.outer_to_inner_area_ratio,
            surface_transform_authority_hash=surface_hash,
            wall_material_authority_hash=request.wall_material_authority.authority_hash,
            wall_conductivity_authority_hash=request.wall_thermal_conductivity_authority.authority_hash,
            wall_bundle_conduction_resistance_k_w=outputs.wall_bundle_conduction_resistance_k_w,
            wall_resistance_outer_surface_m2_k_w=outputs.wall_resistance_outer_surface_m2_k_w,
            inside_fouling_authority=inside,
            outside_fouling_authority=outside,
            fouling_authority_ledger=fouling_ledger,
            applicability_ledger=applicability_ledger,
            completeness_ledger=completeness_ledger,
            warnings=(),
            blockers=(),
            deferred_capabilities=DEFERRED_CAPABILITIES,
            provenance=provenance,
            result_hash="0" * 64,
            result_id="00000000-0000-5000-8000-000000000000",
        )
        result_digest = success_result_hash(provisional)
        final_result = replace(
            provisional,
            result_hash=result_digest,
            result_id=result_id_from_hash(result_digest),
        )
        # Verification must replay the admitted geometry projection.  It must
        # never infer dimensions from an area ratio or another downstream
        # result field.  These private provenance-free caches are not part of
        # any public hash projection.
        object.__setattr__(final_result, "_surface_projection", dict(surface_projection))
        object.__setattr__(final_result, "_wall_projection", dict(wall_projection))
    except Exception as exc:
        return _typed_blocked(
            blockers=[_block(BlockerCode.CANONICALIZATION_FAILED, "identity", str(exc))],
            request_hash_value=request_hash_value,
            task021_identity=task021_identity,
            task025_identity=task025_identity,
            task025_hydraulic_authority_hash=task025_result.hydraulic_authority_hash,
            tube_geometry_snapshot_hash=task021_layout.tube_geometry.snapshot_hash,
            heat_transfer_length_hash=task025_result.heat_transfer_authority.length_hash,
            failure_stage="S11_CANONICAL_HASH_UUID_PROVENANCE",
        )
    return Task037ValidationResult(status="VALID", success_result=final_result)


def _surface_from_result(result: Task037SuccessResult) -> dict[str, Any]:
    projection = getattr(result, "_surface_projection", None)
    if not isinstance(projection, dict):
        raise ValueError("success result has no admitted surface projection")
    return projection


def verify_task037_success_identity(result: Any) -> bool:
    """Replay frozen identities without rerunning engineering arithmetic."""

    if type(result) is not Task037SuccessResult:
        return False
    try:
        if result.schema_version != RESULT_SCHEMA_VERSION:
            return False
        if result.task037_version != TASK037_VERSION:
            return False
        if result.implementation_software_version != IMPLEMENTATION_SOFTWARE_VERSION:
            return False
        if type(result.task021_identity) is not FrozenIdentity:
            return False
        if type(result.task025_identity) is not FrozenIdentity:
            return False
        if (
            result.task021_identity.identity_type != "task021.tube-layout.v1"
            or not result.task021_identity.identity_id
            or not is_sha256_hex(result.task021_identity.identity_hash)
            or result.task025_identity.identity_type != "task025.tube-side.v1"
            or not result.task025_identity.identity_id
            or not is_sha256_hex(result.task025_identity.identity_hash)
        ):
            return False
        if type(result.inside_fouling_authority) is not InsideFoulingResistanceAuthority:
            return False
        if type(result.outside_fouling_authority) is not OutsideFoulingResistanceAuthority:
            return False
        if result.inside_fouling_authority.side != "INSIDE":
            return False
        if result.outside_fouling_authority.side != "OUTSIDE":
            return False
        if result.fouling_authority_ledger != (
            f"inside=PASS:{result.inside_fouling_authority.reference_surface}:"
            f"{result.inside_fouling_authority.fouling_resistance_m2_k_w}",
            f"outside=PASS:{result.outside_fouling_authority.reference_surface}:"
            f"{result.outside_fouling_authority.fouling_resistance_m2_k_w}",
        ):
            return False
        if result.applicability_ledger != tuple(f"{row}=PASS" for row in APPLICABILITY_ROWS):
            return False
        if result.completeness_ledger != (
            "C01_SURFACE_BASIS_AUTHORITY_COMPLETE=PASS",
            "C02_WALL_RESISTANCE_AUTHORITY_COMPLETE=PASS",
            "C03_INSIDE_FOULING_AUTHORITY_COMPLETE=PASS",
            "C04_OUTSIDE_FOULING_AUTHORITY_COMPLETE=PASS",
            "C05_FOULING_AUTHORITY_LEDGER_COMPLETE=PASS",
            "C06_TASK038_FORWARD_CONSUMER_CONTRACT_COMPLETE=PASS",
        ):
            return False
        if result.warnings != () or result.blockers != ():
            return False
        if result.deferred_capabilities != DEFERRED_CAPABILITIES:
            return False

        provenance = result.provenance
        if provenance.design_revision != DESIGN_REVISION:
            return False
        if provenance.source_definition_revision != SOURCE_DEFINITION_REVISION:
            return False
        if provenance.source_definition_issue != SOURCE_DEFINITION_ISSUE:
            return False
        if (
            provenance.source_definition_review_audit_comment
            != SOURCE_DEFINITION_REVIEW_AUDIT_COMMENT
        ):
            return False
        if provenance.design_issue != DESIGN_ISSUE:
            return False
        if provenance.task_id != "TASK037":
            return False
        if provenance.implementation_software_version != IMPLEMENTATION_SOFTWARE_VERSION:
            return False
        if provenance.request_hash != result.request_hash:
            return False
        if provenance.task021_layout_hash != result.task021_identity.identity_hash:
            return False
        if provenance.task025_result_hash != result.task025_identity.identity_hash:
            return False
        if provenance.task025_hydraulic_authority_hash != result.task025_hydraulic_authority_hash:
            return False
        if provenance.tube_geometry_snapshot_hash != result.tube_geometry_snapshot_hash:
            return False
        if provenance.heat_transfer_length_hash != result.heat_transfer_length_hash:
            return False
        if provenance.wall_material_authority_hash != result.wall_material_authority_hash:
            return False
        if provenance.wall_conductivity_authority_hash != result.wall_conductivity_authority_hash:
            return False
        if (
            provenance.inside_fouling_authority_hash
            != result.inside_fouling_authority.authority_hash
        ):
            return False
        if (
            provenance.outside_fouling_authority_hash
            != result.outside_fouling_authority.authority_hash
        ):
            return False
        if provenance.surface_transform_authority_hash != result.surface_transform_authority_hash:
            return False
        if provenance.deferred_capabilities != DEFERRED_CAPABILITIES:
            return False
        if provenance.producer_edges != producer_edges():
            return False
        if provenance.source_identity_hashes != (
            PRODUCER_AREA_PRECISION_POLICY_HASH,
            result.wall_material_authority_hash,
            result.wall_conductivity_authority_hash,
            result.inside_fouling_authority.authority_hash,
            result.outside_fouling_authority.authority_hash,
        ):
            return False
        if (
            provenance.task025_area_quantum_m2 != TASK025_AREA_QUANTUM_M2
            or provenance.task025_area_rounding_mode != TASK025_AREA_ROUNDING_MODE
            or provenance.producer_area_precision_policy_id
            != TASK025_PUBLIC_AREA_PRECISION_POLICY_ID
            or provenance.producer_area_precision_policy_hash != PRODUCER_AREA_PRECISION_POLICY_HASH
            or provenance.producer_precision_limitation_disclosed is not True
            or provenance.producer_precision_threshold_defined is not False
        ):
            return False

        surface_projection = _surface_from_result(result)
        if set(surface_projection) != {
            "task021_layout_hash",
            "task025_result_hash",
            "task025_hydraulic_authority_hash",
            "tube_geometry_snapshot_hash",
            "tube_inner_diameter_m",
            "tube_outer_diameter_m",
            "tube_side_film_reference_surface",
            "overall_u_reference_surface",
            "outer_to_inner_area_ratio",
            "engineering_source_id",
            "engineering_source_locations",
        }:
            return False
        if (
            surface_projection["task021_layout_hash"] != result.task021_identity.identity_hash
            or surface_projection["task025_result_hash"] != result.task025_identity.identity_hash
            or surface_projection["task025_hydraulic_authority_hash"]
            != result.task025_hydraulic_authority_hash
            or surface_projection["tube_geometry_snapshot_hash"]
            != result.tube_geometry_snapshot_hash
            or surface_projection["tube_side_film_reference_surface"]
            != TUBE_SIDE_FILM_REFERENCE_SURFACE
            or surface_projection["overall_u_reference_surface"] != OVERALL_U_REFERENCE_SURFACE
            or surface_projection["outer_to_inner_area_ratio"] != result.outer_to_inner_area_ratio
            or surface_projection["engineering_source_id"] != ENGINEERING_SOURCE_ID
            or surface_projection["engineering_source_locations"] != ENGINEERING_SOURCE_LOCATIONS
        ):
            return False
        for field in ("tube_inner_diameter_m", "tube_outer_diameter_m"):
            value = surface_projection[field]
            if type(value) is not Decimal or not value.is_finite() or value <= 0:
                return False
        if (
            surface_projection["tube_outer_diameter_m"]
            <= surface_projection["tube_inner_diameter_m"]
        ):
            return False
        if (
            surface_transform_authority_hash(surface_projection)
            != result.surface_transform_authority_hash
        ):
            return False
        if producer_area_precision_policy_hash() != PRODUCER_AREA_PRECISION_POLICY_HASH:
            return False
        wall_projection = getattr(result, "_wall_projection", None)
        if not isinstance(wall_projection, dict):
            return False
        if set(wall_projection) != {
            "surface_transform_authority_hash",
            "task025_result_hash",
            "task025_hydraulic_authority_hash",
            "task025_internal_heat_transfer_surface_area_m2",
            "task025_area_quantum_m2",
            "task025_area_rounding_mode",
            "producer_area_precision_policy_id",
            "producer_area_precision_policy_hash",
            "producer_precision_limitation_disclosed",
            "producer_precision_threshold_defined",
            "wall_bundle_numerical_basis",
            "wall_material_authority_hash",
            "wall_conductivity_authority_hash",
            "wall_bundle_conduction_resistance_k_w",
            "wall_resistance_outer_surface_m2_k_w",
            "engineering_source_id",
            "engineering_source_location",
            "source_formula_identity",
            "thin_wall_approximation_used",
        }:
            return False
        if (
            wall_projection["surface_transform_authority_hash"]
            != result.surface_transform_authority_hash
            or wall_projection["task025_result_hash"] != result.task025_identity.identity_hash
            or wall_projection["task025_hydraulic_authority_hash"]
            != result.task025_hydraulic_authority_hash
            or wall_projection["task025_internal_heat_transfer_surface_area_m2"]
            != provenance.task025_internal_heat_transfer_surface_area_m2
            or wall_projection["task025_area_quantum_m2"] != Decimal(TASK025_PUBLIC_AREA_QUANTUM_M2)
            or wall_projection["task025_area_rounding_mode"] != TASK025_PUBLIC_AREA_ROUNDING_MODE
            or wall_projection["producer_area_precision_policy_id"]
            != TASK025_PUBLIC_AREA_PRECISION_POLICY_ID
            or wall_projection["producer_area_precision_policy_hash"]
            != PRODUCER_AREA_PRECISION_POLICY_HASH
            or wall_projection["producer_precision_limitation_disclosed"] is not True
            or wall_projection["producer_precision_threshold_defined"] is not False
            or wall_projection["wall_bundle_numerical_basis"] != WALL_BUNDLE_NUMERICAL_BASIS
            or wall_projection["wall_material_authority_hash"]
            != result.wall_material_authority_hash
            or wall_projection["wall_conductivity_authority_hash"]
            != result.wall_conductivity_authority_hash
            or wall_projection["wall_bundle_conduction_resistance_k_w"]
            != result.wall_bundle_conduction_resistance_k_w
            or wall_projection["wall_resistance_outer_surface_m2_k_w"]
            != result.wall_resistance_outer_surface_m2_k_w
            or wall_projection["engineering_source_id"] != ENGINEERING_SOURCE_ID
            or wall_projection["engineering_source_location"] != ENGINEERING_SOURCE_LOCATION_WALL
            or wall_projection["source_formula_identity"] != SOURCE_FORMULA_IDENTITY
            or wall_projection["thin_wall_approximation_used"] is not False
        ):
            return False
        if (
            type(wall_projection["task025_internal_heat_transfer_surface_area_m2"]) is not Decimal
            or not wall_projection["task025_internal_heat_transfer_surface_area_m2"].is_finite()
            or wall_projection["task025_internal_heat_transfer_surface_area_m2"] <= 0
            or type(wall_projection["wall_bundle_conduction_resistance_k_w"]) is not Decimal
            or type(wall_projection["wall_resistance_outer_surface_m2_k_w"]) is not Decimal
            or wall_projection["wall_bundle_conduction_resistance_k_w"] <= 0
            or wall_projection["wall_resistance_outer_surface_m2_k_w"] <= 0
        ):
            return False
        if (
            wall_resistance_authority_hash(wall_projection)
            != provenance.wall_resistance_authority_hash
        ):
            return False
        if not verify_provenance(provenance):
            return False
        if success_result_hash(result) != result.result_hash:
            return False
        return result_id_from_hash(result.result_hash) == result.result_id
    except Exception:
        return False


validate_request = evaluate_task037


__all__ = [
    "evaluate_task037",
    "validate_request",
    "verify_task037_success_identity",
]
