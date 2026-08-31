"""Fail-closed TASK-038 public validation and composition pipeline."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.models import (
    Task037RawBoundaryBlockedResult,
    Task037SuccessResult,
    Task037TypedBlockedResult,
)
from hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition.models import (
    Task035RawBoundaryBlockedResult,
    Task035SuccessResult,
    Task035TypedBlockedResult,
)
from hexagent.exchangers.shell_tube.tube_side import Task025BlockedResult, Task025ValidResult
from hexagent.exchangers.shell_tube.tube_side_thermal.result import (
    RawBoundaryBlockedResult as Task026RawBoundaryBlockedResult,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.result import (
    TubeSideBlockedResult,
    TubeSideThermalResult,
)

from .authority import (
    build_cross_producer_projection,
    validate_cross_producer_joins,
    validate_service_binding,
)
from .blocker_registry import blocker
from .canonical import (
    cross_producer_compatibility_hash,
    engineering_source_identity_hash,
    outer_area_projection_hash,
    raw_boundary_blocked_result_hash,
    request_hash,
    resistance_composition_hash,
    result_id_from_hash,
    success_result_hash,
    typed_blocked_result_hash,
    ua_composition_hash,
)
from .engineering import (
    build_thermal_resistance_ledger,
    compute_outer_area,
    compute_resistance_composition,
    compute_ua,
)
from .models import (
    BlockerEntry,
    EngineeringSourceIdentity,
    LedgerRow,
    Task038Provenance,
    Task038RawBoundaryBlockedResult,
    Task038Request,
    Task038SuccessResult,
    Task038TypedBlockedResult,
    Task038ValidationResult,
    ThermalResistanceLedgerRow,
)
from .producer_replay import (
    producer_identity_envelope,
    replay_task025,
    replay_task026,
    replay_task035,
    replay_task037,
)
from .provenance import build_provenance, verify_provenance
from .raw_projection import FrozenRawProjection
from .schema import (
    APPLICABILITY_ROWS,
    BASE_MAIN_SHA,
    BASE_MAIN_TREE,
    BASELINE_REPAIR_GOVERNANCE_COMMENT_ID,
    COMPLETENESS_ROWS,
    DEFERRED_CAPABILITIES,
    DESIGN_ISSUE,
    DESIGN_REVISION,
    ENGINEERING_SOURCE_S01_CLASS,
    ENGINEERING_SOURCE_S01_ID,
    ENGINEERING_SOURCE_S01_LOCATIONS,
    ENGINEERING_SOURCE_S01_PERMISSION,
    ENGINEERING_SOURCE_S01_VERSION,
    ENGINEERING_SOURCE_S02_CLASS,
    ENGINEERING_SOURCE_S02_ID,
    ENGINEERING_SOURCE_S02_LOCATIONS,
    ENGINEERING_SOURCE_S02_PERMISSION,
    ENGINEERING_SOURCE_S02_VERSION,
    IMPLEMENTATION_SOFTWARE_VERSION,
    OVERALL_U_REFERENCE_SURFACE,
    PRODUCER_AREA_PRECISION_POLICY_HASH,
    PROFILE_ID,
    REQUEST_SCHEMA_VERSION,
    SOURCE_DEFINITION_ISSUE,
    SOURCE_DEFINITION_REVISION,
    SUCCESS_RESULT_SCHEMA_VERSION,
    TASK025_AREA_QUANTUM_M2,
    TASK025_AREA_ROUNDING_MODE,
    TASK025_PRODUCER_AREA_PRECISION_POLICY_ID,
    TASK038_VERSION,
    TASK_ID,
    THERMAL_RESISTANCE_TERM_IDS,
)

_TASK025_TYPES = (Task025ValidResult, Task025BlockedResult)
_TASK026_TYPES = (TubeSideThermalResult, TubeSideBlockedResult, Task026RawBoundaryBlockedResult)
_TASK035_TYPES = (Task035SuccessResult, Task035TypedBlockedResult, Task035RawBoundaryBlockedResult)
_TASK037_TYPES = (Task037SuccessResult, Task037TypedBlockedResult, Task037RawBoundaryBlockedResult)


def _frozen_thermal_ledger_semantics(
    provenance: Task038Provenance,
) -> tuple[tuple[str, str, str, str, str, str | None], ...]:
    transform_hash = provenance.task037_surface_transform_authority_hash
    return (
        (
            "R01_TUBE_SIDE_FILM_OUTER_REFERENCE",
            "TASK026",
            "TASK026.tube_side_heat_transfer_coefficient_w_m2_k",
            "INNER_TUBE_SURFACE",
            OVERALL_U_REFERENCE_SURFACE,
            transform_hash,
        ),
        (
            "R02_INSIDE_FOULING_OUTER_REFERENCE",
            "TASK037",
            "TASK037.inside_fouling_authority.fouling_resistance_m2_k_w",
            "INNER_TUBE_SURFACE",
            OVERALL_U_REFERENCE_SURFACE,
            transform_hash,
        ),
        (
            "R03_TUBE_WALL_CONDUCTION_OUTER_REFERENCE",
            "TASK037",
            "TASK037.wall_resistance_outer_surface_m2_k_w",
            OVERALL_U_REFERENCE_SURFACE,
            OVERALL_U_REFERENCE_SURFACE,
            None,
        ),
        (
            "R04_OUTSIDE_FOULING_OUTER_REFERENCE",
            "TASK037",
            "TASK037.outside_fouling_authority.fouling_resistance_m2_k_w",
            OVERALL_U_REFERENCE_SURFACE,
            OVERALL_U_REFERENCE_SURFACE,
            None,
        ),
        (
            "R05_SHELL_SIDE_FILM_OUTER_REFERENCE",
            "TASK035",
            "TASK035.modeled_shell_side_heat_transfer_coefficient_w_m2_k",
            OVERALL_U_REFERENCE_SURFACE,
            OVERALL_U_REFERENCE_SURFACE,
            None,
        ),
    )


def _ledger_rows_have_frozen_status(
    rows: Any,
    expected_ids: tuple[str, ...],
) -> bool:
    return (
        type(rows) is tuple
        and tuple(row.row_id for row in rows) == expected_ids
        and all(type(row) is LedgerRow and row.status == "PASS" for row in rows)
    )


def _success_semantics_are_frozen(
    result: Task038SuccessResult,
    provenance: Task038Provenance,
) -> bool:
    if (
        result.schema_version != SUCCESS_RESULT_SCHEMA_VERSION
        or result.task038_version != TASK038_VERSION
        or result.profile_id != PROFILE_ID
        or result.implementation_software_version != IMPLEMENTATION_SOFTWARE_VERSION
        or result.overall_u_reference_surface != OVERALL_U_REFERENCE_SURFACE
        or provenance.overall_u_reference_surface != OVERALL_U_REFERENCE_SURFACE
        or result.warnings != ()
        or result.blockers != ()
        or result.deferred_capabilities != DEFERRED_CAPABILITIES
        or provenance.deferred_capabilities != DEFERRED_CAPABILITIES
        or provenance.modeled_overall_heat_transfer_coefficient_w_m2_k
        != result.modeled_overall_heat_transfer_coefficient_w_m2_k
        or provenance.outer_tube_surface_effective_area_m2
        != result.outer_tube_surface_effective_area_m2
        or provenance.modeled_ua_w_k != result.modeled_ua_w_k
    ):
        return False

    expected_rows = _frozen_thermal_ledger_semantics(provenance)
    rows = result.full_thermal_resistance_composition_ledger
    if type(rows) is not tuple or len(rows) != len(expected_rows):
        return False
    for row, expected in zip(rows, expected_rows, strict=True):
        if type(row) is not ThermalResistanceLedgerRow:
            return False
        if (
            row.term_id,
            row.producer_owner,
            row.source_field_or_projection,
            row.native_reference_surface,
            row.composed_reference_surface,
            row.transformation_authority_hash_or_none,
        ) != expected:
            return False
        if row.status != "PRESENT_APPLICABLE_COMPATIBLE":
            return False
        if row.value_m2_k_w < Decimal("0"):
            return False

    return _ledger_rows_have_frozen_status(result.applicability_ledger, APPLICABILITY_ROWS) and (
        _ledger_rows_have_frozen_status(result.completeness_ledger, COMPLETENESS_ROWS)
    )


def _details(reason: str) -> tuple[tuple[str, str], ...]:
    return (("reason", reason),)


def _block(code: str, stage: str, field_path: str, reason: str) -> BlockerEntry:
    return blocker(code, stage, field_path=field_path, message_key=reason, details=_details(reason))


def _raw_boundary_blocked(raw: object) -> Task038RawBoundaryBlockedResult:
    projection = FrozenRawProjection("RAW_PROJECTION", "")
    provisional = Task038RawBoundaryBlockedResult(
        schema_version="task038.raw-boundary-blocked-result.v1",
        task038_version=TASK038_VERSION,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        raw_request_projection=projection,
        blockers=(
            _block(
                "BL_RAW_INPUT_BOUNDARY_MALFORMED",
                "S00_RAW_INPUT_BOUNDARY",
                "raw_input",
                f"raw_input_type_invalid:{type(raw).__name__}",
            ),
        ),
        warnings=(),
        deferred_capabilities=DEFERRED_CAPABILITIES,
        blocked_result_hash="0" * 64,
    )
    return replace(provisional, blocked_result_hash=raw_boundary_blocked_result_hash(provisional))


def _typed_blocked(
    *,
    request_hash_value: str | None,
    identities: tuple[Any, ...],
    stage: str,
    blocker_entries: tuple[BlockerEntry, ...],
) -> Task038TypedBlockedResult:
    provisional = Task038TypedBlockedResult(
        schema_version="task038.typed-blocked-result.v1",
        task038_version=TASK038_VERSION,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        failure_stage=stage,
        request_hash=request_hash_value,
        producer_result_identities=identities,
        blockers=blocker_entries,
        warnings=(),
        deferred_capabilities=DEFERRED_CAPABILITIES,
        provenance_or_none=None,
        blocked_result_hash="0" * 64,
    )
    return replace(provisional, blocked_result_hash=typed_blocked_result_hash(provisional))


def build_raw_overall_u_ua_request(
    raw: object,
) -> Task038Request | Task038RawBoundaryBlockedResult:
    """Admit only a built-in mapping with the exact eight request fields."""

    if type(raw) is not dict:
        return _raw_boundary_blocked(raw)
    required = {
        "schema_version",
        "profile_id",
        "task025_result",
        "task026_result",
        "task035_result",
        "task037_result",
        "tube_side_service_binding_authority",
        "evidence_refs",
    }
    if set(raw) != required:
        return _raw_boundary_blocked(raw)
    try:
        return Task038Request(
            schema_version=raw["schema_version"],
            profile_id=raw["profile_id"],
            task025_result=raw["task025_result"],
            task026_result=raw["task026_result"],
            task035_result=raw["task035_result"],
            task037_result=raw["task037_result"],
            tube_side_service_binding_authority=raw["tube_side_service_binding_authority"],
            evidence_refs=tuple(raw["evidence_refs"]),
        )
    except (TypeError, ValueError, KeyError):
        return _raw_boundary_blocked(raw)


def _request_hash_or_none(request: Any) -> str | None:
    if type(request) is not Task038Request:
        return None
    try:
        return request_hash(request)
    except (AttributeError, TypeError, ValueError):
        return None


def _replay_all(request: Task038Request) -> tuple[bool, tuple[Any, ...], str, str | None]:
    replayers = (
        ("task025_result", replay_task025, "BL_TASK025_RESULT_INVALID"),
        ("task026_result", replay_task026, "BL_TASK026_RESULT_INVALID"),
        ("task035_result", replay_task035, "BL_TASK035_RESULT_INVALID"),
        ("task037_result", replay_task037, "BL_TASK037_RESULT_INVALID"),
    )
    envelopes: list[Any] = []
    for field, replayer, code in replayers:
        result = getattr(request, field)
        ok, branch, native_id, native_hash, evidence_hash = replayer(result)
        if not ok:
            return False, tuple(envelopes), field, code
        try:
            envelope = producer_identity_envelope(result)
        except (AttributeError, TypeError, ValueError, ArithmeticError):
            return False, tuple(envelopes), field, code
        envelopes.append(envelope)
        if branch != "SUCCESS":
            return False, tuple(envelopes), field, code
        if native_hash != evidence_hash or native_hash is None:
            return False, tuple(envelopes), field, code
    return True, tuple(envelopes), "", None


def _source_identities() -> tuple[EngineeringSourceIdentity, EngineeringSourceIdentity]:
    return (
        EngineeringSourceIdentity(
            ENGINEERING_SOURCE_S01_ID,
            ENGINEERING_SOURCE_S01_VERSION,
            ENGINEERING_SOURCE_S01_CLASS,
            ENGINEERING_SOURCE_S01_LOCATIONS,
            ENGINEERING_SOURCE_S01_PERMISSION,
        ),
        EngineeringSourceIdentity(
            ENGINEERING_SOURCE_S02_ID,
            ENGINEERING_SOURCE_S02_VERSION,
            ENGINEERING_SOURCE_S02_CLASS,
            ENGINEERING_SOURCE_S02_LOCATIONS,
            ENGINEERING_SOURCE_S02_PERMISSION,
        ),
    )


def _success_result(request: Task038Request, envelopes: tuple[Any, ...]) -> Task038SuccessResult:
    task025 = request.task025_result
    task026 = request.task026_result
    task035 = request.task035_result
    task037 = request.task037_result
    binding = request.tube_side_service_binding_authority
    request_hash_value = request_hash(request)
    cross_projection = build_cross_producer_projection(task025, task026, task035, task037, binding)
    cross_hash = cross_producer_compatibility_hash(cross_projection)
    sources = _source_identities()
    source_hashes = tuple(engineering_source_identity_hash(source) for source in sources)
    resistance_projection = {
        "cross_producer_compatibility_hash": cross_hash,
        "engineering_source_identity_hashes": source_hashes,
        "overall_u_reference_surface": OVERALL_U_REFERENCE_SURFACE,
        "outer_to_inner_area_ratio": task037.outer_to_inner_area_ratio,
        "tube_side_heat_transfer_coefficient_w_m2_k": (
            task026.tube_side_heat_transfer_coefficient_w_m2_k
        ),
        "shell_side_heat_transfer_coefficient_w_m2_k": (
            task035.modeled_shell_side_heat_transfer_coefficient_w_m2_k
        ),
        "inside_fouling_resistance_inner_surface_m2_k_w": (
            task037.inside_fouling_authority.fouling_resistance_m2_k_w
        ),
        "wall_resistance_outer_surface_m2_k_w": task037.wall_resistance_outer_surface_m2_k_w,
        "outside_fouling_resistance_outer_surface_m2_k_w": (
            task037.outside_fouling_authority.fouling_resistance_m2_k_w
        ),
        "overall_u_quantum_w_m2_k": Decimal("1E-9"),
        "rounding_mode": "ROUND_HALF_EVEN",
    }
    resistance_hash = resistance_composition_hash(resistance_projection)
    resistance = compute_resistance_composition(
        gamma=task037.outer_to_inner_area_ratio,
        h_i=task026.tube_side_heat_transfer_coefficient_w_m2_k,
        h_o=task035.modeled_shell_side_heat_transfer_coefficient_w_m2_k,
        inside_fouling=task037.inside_fouling_authority.fouling_resistance_m2_k_w,
        wall_resistance=task037.wall_resistance_outer_surface_m2_k_w,
        outside_fouling=task037.outside_fouling_authority.fouling_resistance_m2_k_w,
    )
    area_projection = {
        "task025_result_hash": task025.result_hash,
        "task025_internal_heat_transfer_surface_area_m2": (
            task025.internal_heat_transfer_surface_area_m2
        ),
        "task037_result_hash": task037.result_hash,
        "task037_surface_transform_authority_hash": task037.surface_transform_authority_hash,
        "outer_to_inner_area_ratio": task037.outer_to_inner_area_ratio,
        "task025_area_quantum_m2": TASK025_AREA_QUANTUM_M2,
        "task025_area_rounding_mode": TASK025_AREA_ROUNDING_MODE,
        "producer_area_precision_policy_id": TASK025_PRODUCER_AREA_PRECISION_POLICY_ID,
        "producer_area_precision_policy_hash": PRODUCER_AREA_PRECISION_POLICY_HASH,
        "producer_precision_limitation_disclosed": True,
        "producer_precision_threshold_defined": False,
        "outer_area_quantum_m2": Decimal("1E-10"),
        "rounding_mode": "ROUND_HALF_EVEN",
    }
    area_authority_hash = outer_area_projection_hash(area_projection)
    area = compute_outer_area(
        published_inner_area=task025.internal_heat_transfer_surface_area_m2,
        gamma=task037.outer_to_inner_area_ratio,
    )
    ua_projection = {
        "resistance_composition_authority_hash": resistance_hash,
        "outer_area_projection_authority_hash": area_authority_hash,
        "modeled_overall_heat_transfer_coefficient_w_m2_k": resistance.overall_u,
        "outer_tube_surface_effective_area_m2": area.outer_area,
        "ua_quantum_w_k": Decimal("1E-9"),
        "rounding_mode": "ROUND_HALF_EVEN",
    }
    ua_authority_hash = ua_composition_hash(ua_projection)
    ua = compute_ua(public_overall_u=resistance.overall_u, public_outer_area_value=area.outer_area)
    thermal_ledger = build_thermal_resistance_ledger(
        task026_transform_hash=task037.surface_transform_authority_hash,
        task037_transform_hash=task037.surface_transform_authority_hash,
        r01=resistance.r01,
        r02=resistance.r02,
        r03=resistance.r03,
        r04=resistance.r04,
        r05=resistance.r05,
    )
    applicability = tuple(LedgerRow(row_id, "PASS") for row_id in APPLICABILITY_ROWS)
    completeness = tuple(LedgerRow(row_id, "PASS") for row_id in COMPLETENESS_ROWS)
    provenance = build_provenance(
        request_hash=request_hash_value,
        task025_result_hash=task025.result_hash,
        task025_result_id=task025.result_id,
        task025_hydraulic_authority_hash=task025.hydraulic_authority_hash,
        task026_result_hash=task026.result_hash,
        task026_result_id=task026.result_id,
        task026_property_snapshot_hash=task026.property_snapshot_hash,
        task035_result_hash=task035.result_hash,
        task035_result_id=task035.result_id,
        task035_shell_side_fluid_id=task035.shell_side_fluid_id,
        task037_result_hash=task037.result_hash,
        task037_result_id=task037.result_id,
        task037_surface_transform_authority_hash=task037.surface_transform_authority_hash,
        task037_inside_fouling_authority_hash=task037.inside_fouling_authority.authority_hash,
        task037_outside_fouling_authority_hash=task037.outside_fouling_authority.authority_hash,
        tube_side_service_binding_authority_hash=binding.authority_hash,
        engineering_source_identity_hashes=source_hashes,
        cross_producer_compatibility_hash=cross_hash,
        resistance_composition_authority_hash=resistance_hash,
        outer_area_projection_authority_hash=area_authority_hash,
        ua_composition_authority_hash=ua_authority_hash,
        overall_u_reference_surface=OVERALL_U_REFERENCE_SURFACE,
        modeled_overall_heat_transfer_coefficient_w_m2_k=resistance.overall_u,
        outer_tube_surface_effective_area_m2=area.outer_area,
        modeled_ua_w_k=ua.ua,
        evidence_refs=request.evidence_refs,
    )
    provisional = Task038SuccessResult(
        schema_version="task038.success-result.v1",
        task038_version=TASK038_VERSION,
        profile_id="hxforge.shell_tube.overall_u_ua.v1",
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        request_hash=request_hash_value,
        overall_u_reference_surface=OVERALL_U_REFERENCE_SURFACE,
        full_thermal_resistance_composition_ledger=thermal_ledger,
        modeled_overall_heat_transfer_coefficient_w_m2_k=resistance.overall_u,
        outer_tube_surface_effective_area_m2=area.outer_area,
        modeled_ua_w_k=ua.ua,
        applicability_ledger=applicability,
        completeness_ledger=completeness,
        warnings=(),
        blockers=(),
        deferred_capabilities=DEFERRED_CAPABILITIES,
        provenance=provenance,
        result_hash="0" * 64,
        result_id=result_id_from_hash("0" * 64),
    )
    digest = success_result_hash(provisional)
    return replace(provisional, result_hash=digest, result_id=result_id_from_hash(digest))


def evaluate_task038(request: Task038Request) -> Task038ValidationResult:
    """Execute the frozen S00-S19 fail-closed pipeline."""

    if type(request) is not Task038Request:
        return Task038ValidationResult(
            status="BLOCKED", raw_boundary_blocked_result=_raw_boundary_blocked(request)
        )
    if request.schema_version != REQUEST_SCHEMA_VERSION:
        blocked = _typed_blocked(
            request_hash_value=None,
            identities=(),
            stage="S01_REQUEST_AND_AUTHORITY_SCHEMA",
            blocker_entries=(
                _block(
                    "BL_REQUEST_SCHEMA_INVALID",
                    "S01_REQUEST_AND_AUTHORITY_SCHEMA",
                    "request",
                    "request_schema_invalid",
                ),
            ),
        )
        return Task038ValidationResult(status="BLOCKED", blocked_result=blocked)
    request_hash_value = _request_hash_or_none(request)
    if not all(
        type(value) in allowed
        for value, allowed in (
            (request.task025_result, _TASK025_TYPES),
            (request.task026_result, _TASK026_TYPES),
            (request.task035_result, _TASK035_TYPES),
            (request.task037_result, _TASK037_TYPES),
        )
    ):
        blocked = _typed_blocked(
            request_hash_value=request_hash_value,
            identities=(),
            stage="S01_REQUEST_AND_AUTHORITY_SCHEMA",
            blocker_entries=(
                _block(
                    "BL_REQUEST_SCHEMA_INVALID",
                    "S01_REQUEST_AND_AUTHORITY_SCHEMA",
                    "request",
                    "producer_branch_type_invalid",
                ),
            ),
        )
        return Task038ValidationResult(status="BLOCKED", blocked_result=blocked)
    binding_ok, binding_reason = validate_service_binding(
        request.tube_side_service_binding_authority
    )
    if not binding_ok:
        blocked = _typed_blocked(
            request_hash_value=request_hash_value,
            identities=(),
            stage="S01_REQUEST_AND_AUTHORITY_SCHEMA",
            blocker_entries=(
                _block(
                    "BL_SERVICE_BINDING_INVALID",
                    "S01_REQUEST_AND_AUTHORITY_SCHEMA",
                    "tube_side_service_binding_authority",
                    binding_reason,
                ),
            ),
        )
        return Task038ValidationResult(status="BLOCKED", blocked_result=blocked)
    replay_ok, envelopes, field, code = _replay_all(request)
    if not replay_ok:
        stage = {
            "task025_result": "S02_TASK025_RESULT_REPLAY",
            "task026_result": "S03_TASK026_RESULT_REPLAY",
            "task035_result": "S04_TASK035_RESULT_REPLAY",
            "task037_result": "S05_TASK037_RESULT_REPLAY",
        }[field]
        blocked = _typed_blocked(
            request_hash_value=request_hash_value,
            identities=envelopes,
            stage=stage,
            blocker_entries=(
                _block(code or "BL_REQUEST_SCHEMA_INVALID", stage, field, "producer_replay_failed"),
            ),
        )
        return Task038ValidationResult(status="BLOCKED", blocked_result=blocked)
    if not all(envelope.branch == "SUCCESS" for envelope in envelopes):
        blocked = _typed_blocked(
            request_hash_value=request_hash_value,
            identities=envelopes,
            stage="S02_TASK025_RESULT_REPLAY",
            blocker_entries=(
                _block(
                    "BL_TASK025_RESULT_INVALID",
                    "S02_TASK025_RESULT_REPLAY",
                    "producer_result",
                    "blocked_producer_fail_closed",
                ),
            ),
        )
        return Task038ValidationResult(status="BLOCKED", blocked_result=blocked)
    joins_ok, join_reason = validate_cross_producer_joins(
        request.task025_result,
        request.task026_result,
        request.task035_result,
        request.task037_result,
        request.tube_side_service_binding_authority,
    )
    if not joins_ok:
        blocked = _typed_blocked(
            request_hash_value=request_hash_value,
            identities=envelopes,
            stage="S06_HYDRAULIC_AND_TASK025_JOIN",
            blocker_entries=(
                _block(
                    "BL_HYDRAULIC_AUTHORITY_MISMATCH",
                    "S06_HYDRAULIC_AND_TASK025_JOIN",
                    "cross_producer",
                    join_reason,
                ),
            ),
        )
        return Task038ValidationResult(status="BLOCKED", blocked_result=blocked)
    try:
        result = _success_result(request, envelopes)
    except (AttributeError, TypeError, ValueError, ArithmeticError):
        blocked = _typed_blocked(
            request_hash_value=request_hash_value,
            identities=envelopes,
            stage="S12_FULL_RESISTANCE_COMPOSITION",
            blocker_entries=(
                _block(
                    "BL_RESISTANCE_COMPOSITION_INVALID",
                    "S12_FULL_RESISTANCE_COMPOSITION",
                    "engineering",
                    "composition_input_invalid",
                ),
            ),
        )
        return Task038ValidationResult(status="BLOCKED", blocked_result=blocked)
    return Task038ValidationResult(status="VALID", success_result=result)


def compute_overall_heat_transfer_coefficient_and_ua(
    request: Task038Request,
) -> Task038SuccessResult | Task038TypedBlockedResult:
    result = evaluate_task038(request).result
    if isinstance(result, Task038RawBoundaryBlockedResult):
        raise TypeError("raw boundary input must be admitted by build_raw_overall_u_ua_request")
    return result


def verify_task038_success_identity(result: Any) -> bool:
    if type(result) is not Task038SuccessResult:
        return False
    try:
        provenance = result.provenance
        if type(provenance) is not Task038Provenance:
            return False
        if not _success_semantics_are_frozen(result, provenance):
            return False
        source_hashes = tuple(
            engineering_source_identity_hash(source) for source in _source_identities()
        )
        return (
            verify_provenance(provenance)
            and provenance.task_id == TASK_ID
            and provenance.source_definition_issue == SOURCE_DEFINITION_ISSUE
            and provenance.source_definition_revision == SOURCE_DEFINITION_REVISION
            and provenance.design_issue == DESIGN_ISSUE
            and provenance.design_revision == DESIGN_REVISION
            and provenance.implementation_software_version == IMPLEMENTATION_SOFTWARE_VERSION
            and provenance.base_main_sha == BASE_MAIN_SHA
            and provenance.base_main_tree == BASE_MAIN_TREE
            and provenance.baseline_repair_governance_comment_id
            == BASELINE_REPAIR_GOVERNANCE_COMMENT_ID
            and provenance.request_hash == result.request_hash
            and provenance.engineering_source_identity_hashes == source_hashes
            and provenance.task037_task025_area_quantum_m2 == TASK025_AREA_QUANTUM_M2
            and provenance.task037_task025_area_rounding_mode == TASK025_AREA_ROUNDING_MODE
            and provenance.task037_producer_area_precision_policy_id
            == TASK025_PRODUCER_AREA_PRECISION_POLICY_ID
            and provenance.task037_producer_area_precision_policy_hash
            == PRODUCER_AREA_PRECISION_POLICY_HASH
            and provenance.task037_producer_precision_limitation_disclosed is True
            and provenance.task037_producer_precision_threshold_defined is False
            and provenance.overall_u_reference_surface == result.overall_u_reference_surface
            and provenance.modeled_overall_heat_transfer_coefficient_w_m2_k
            == result.modeled_overall_heat_transfer_coefficient_w_m2_k
            and provenance.outer_tube_surface_effective_area_m2
            == result.outer_tube_surface_effective_area_m2
            and provenance.modeled_ua_w_k == result.modeled_ua_w_k
            and provenance.deferred_capabilities == DEFERRED_CAPABILITIES
            and success_result_hash(result) == result.result_hash
            and result_id_from_hash(result.result_hash) == result.result_id
            and len(result.full_thermal_resistance_composition_ledger) == 5
            and tuple(row.term_id for row in result.full_thermal_resistance_composition_ledger)
            == THERMAL_RESISTANCE_TERM_IDS
            and all(
                row.status == "PRESENT_APPLICABLE_COMPATIBLE"
                for row in result.full_thermal_resistance_composition_ledger
            )
            and tuple(row.row_id for row in result.applicability_ledger) == APPLICABILITY_ROWS
            and tuple(row.row_id for row in result.completeness_ledger) == COMPLETENESS_ROWS
        )
    except (AttributeError, TypeError, ValueError, ArithmeticError):
        return False


__all__ = [
    "build_raw_overall_u_ua_request",
    "compute_overall_heat_transfer_coefficient_and_ua",
    "evaluate_task038",
    "verify_task038_success_identity",
]
