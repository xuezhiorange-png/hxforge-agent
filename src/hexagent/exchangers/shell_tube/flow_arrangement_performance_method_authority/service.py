"""TASK161 catalog-authority service.

The service consumes one already accepted TASK160 result.  It publishes
capacity-rate and catalog authority, but deliberately does not evaluate a
heat-exchanger performance relation.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import ROUND_HALF_EVEN, Context, Decimal, DecimalException, localcontext
from typing import cast

from hexagent.exchangers.shell_tube.thermal_stream_state.canonical import (
    result_id as task160_result_id,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.canonical import (
    sha256_hex_from_framed_bytes,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.canonical import (
    success_canonical_bytes as task160_success_canonical_bytes,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.models import Task160Result

from .canonical import (
    RawProjectionOutcome,
    project_raw_request_with_diagnostics,
    raw_blocked_hash,
    raw_blocked_result_id,
    raw_request_projection_hash,
    request_hash,
    result_id,
    success_hash,
    task160_result_identity_projection,
    typed_blocked_hash,
    typed_blocked_result_id,
)
from .errors import Task161FailureCode, make_blocker, sort_blockers
from .models import (
    TASK161_IMPLEMENTATION_SOFTWARE_VERSION,
    TASK161_RAW_BOUNDARY_SCHEMA_VERSION,
    TASK161_REQUIRED_CASE_INPUTS,
    TASK161_REQUIRED_RUNTIME_INPUTS,
    TASK161_SCHEMA_VERSION,
    TASK161_SOURCE_DEFINITION_ID,
    TASK161_VERSION,
    AssumptionAuthorityClass,
    CapacityFoundation,
    CapacitySideRelation,
    CaseBindingState,
    CatalogApplicability,
    CatalogBindingState,
    CatalogCompleteness,
    CatalogStatus,
    CfheSurrogateMixingAuthority,
    FlowArrangementCatalogAuthority,
    MethodOutputSemantics,
    PerformanceMethodCatalogAuthority,
    PhysicalStheMixingAuthority,
    SourceAssumption,
    StheCfheIdentityMapping,
    Task160ResultIdentityProjection,
    Task161BlockedResult,
    Task161Blocker,
    Task161FailureStage,
    Task161PreResultIdentityInputs,
    Task161ProvenanceSemanticInputs,
    Task161RawBoundaryBlockedResult,
    Task161Request,
    Task161Result,
    Task161ValidationResult,
    Task161ValidationStatus,
    Task161Warning,
)
from .provenance import build_success_provenance

TASK161_DECIMAL_CONTEXT = Context(
    prec=160,
    rounding=ROUND_HALF_EVEN,
    Emin=-999999,
    Emax=999999,
    capitals=1,
    clamp=0,
)
TASK161_ADDITIONAL_TRAP_OVERRIDES = False

TASK161_RAW_FIELDS: tuple[str, ...] = (
    "schema_version",
    "task161_version",
    "source_definition_id",
    "task160_result",
    "request_metadata",
)
TASK161_RAW_FIELD_SET = frozenset(TASK161_RAW_FIELDS)

TASK161_CASE_BINDING_REQUIRED_FOR_SUCCESS = False
TASK161_PERFORMANCE_METHOD_ROLE = "AUTHORITY_ONLY"
TASK161_METHOD_AUTHORITY_MODE = "CATALOG_ONLY"


def _metadata_pair(value: object) -> tuple[str, str] | None:
    if type(value) is list:
        pair_values: list[object] | tuple[object, ...] = cast(list[object], value)
    elif type(value) is tuple:
        pair_values = cast(tuple[object, ...], value)
    else:
        return None
    if len(pair_values) != 2 or type(pair_values[0]) is not str or type(pair_values[1]) is not str:
        return None
    return pair_values[0], pair_values[1]


def _raw_blocked(
    outcome: RawProjectionOutcome,
    blockers: tuple[Task161Blocker, ...],
) -> Task161ValidationResult:
    projection = outcome.projection
    projection_hash = raw_request_projection_hash(projection)
    ordered = sort_blockers(blockers)
    warnings: tuple[Task161Warning, ...] = ()
    blocked_hash = raw_blocked_hash(
        schema_version=TASK161_RAW_BOUNDARY_SCHEMA_VERSION,
        task161_version=TASK161_VERSION,
        implementation_software_version=TASK161_IMPLEMENTATION_SOFTWARE_VERSION,
        failure_stage=Task161FailureStage.RAW_BOUNDARY,
        raw_request_projection_hash_value=projection_hash,
        blockers=ordered,
        warnings=warnings,
    )
    blocked_id = raw_blocked_result_id(blocked_hash)
    result = Task161RawBoundaryBlockedResult(
        schema_version=TASK161_RAW_BOUNDARY_SCHEMA_VERSION,
        task161_version=TASK161_VERSION,
        implementation_software_version=TASK161_IMPLEMENTATION_SOFTWARE_VERSION,
        failure_stage=Task161FailureStage.RAW_BOUNDARY,
        raw_request_projection=projection,
        raw_request_projection_hash=projection_hash,
        blockers=ordered,
        warnings=warnings,
        blocked_result_hash=blocked_hash,
        blocked_result_id=blocked_id,
    )
    return Task161ValidationResult(
        Task161ValidationStatus.RAW_BOUNDARY_BLOCKED,
        result,
        None,
        None,
    )


def _typed_blocked(
    *,
    request_hash_value: str,
    task160_result_id_or_none: str | None,
    blockers: tuple[Task161Blocker, ...],
    stage: Task161FailureStage,
) -> Task161ValidationResult:
    ordered = sort_blockers(blockers)
    warnings: tuple[Task161Warning, ...] = ()
    blocked_hash = typed_blocked_hash(
        schema_version=TASK161_SCHEMA_VERSION,
        task161_version=TASK161_VERSION,
        implementation_software_version=TASK161_IMPLEMENTATION_SOFTWARE_VERSION,
        failure_stage=stage,
        request_hash_value=request_hash_value,
        task160_result_id_or_none=task160_result_id_or_none,
        blockers=ordered,
        warnings=warnings,
    )
    blocked_id = typed_blocked_result_id(blocked_hash)
    result = Task161BlockedResult(
        schema_version=TASK161_SCHEMA_VERSION,
        task161_version=TASK161_VERSION,
        implementation_software_version=TASK161_IMPLEMENTATION_SOFTWARE_VERSION,
        failure_stage=stage,
        request_hash=request_hash_value,
        task160_result_id_or_none=task160_result_id_or_none,
        blockers=ordered,
        warnings=warnings,
        blocked_result_hash=blocked_hash,
        blocked_result_id=blocked_id,
    )
    return Task161ValidationResult(Task161ValidationStatus.TYPED_BLOCKED, None, result, None)


def _raw_schema_blockers(raw: object) -> tuple[Task161Blocker, ...]:
    blockers: list[Task161Blocker] = []
    if type(raw) is not dict:
        return (
            make_blocker(
                Task161FailureCode.INVALID_REQUEST_TYPE,
                stage=Task161FailureStage.RAW_BOUNDARY,
                field_path="request",
            ),
        )
    keys = tuple(dict.keys(raw))
    if any(type(key) is not str for key in keys) or any(
        key not in TASK161_RAW_FIELD_SET for key in keys if type(key) is str
    ):
        blockers.append(
            make_blocker(
                Task161FailureCode.INVALID_REQUEST_SCHEMA,
                stage=Task161FailureStage.RAW_BOUNDARY,
                field_path="request",
            )
        )
    missing = tuple(field for field in TASK161_RAW_FIELDS if field not in raw)
    if missing:
        blockers.append(
            make_blocker(
                Task161FailureCode.INVALID_REQUEST_SCHEMA,
                stage=Task161FailureStage.RAW_BOUNDARY,
                field_path="request",
                details=(("missing_fields", ",".join(missing)),),
            )
        )
    if raw.get("schema_version") != TASK161_SCHEMA_VERSION:
        blockers.append(
            make_blocker(
                Task161FailureCode.INVALID_REQUEST_SCHEMA,
                stage=Task161FailureStage.RAW_BOUNDARY,
                field_path="schema_version",
            )
        )
    if raw.get("task161_version") != TASK161_VERSION:
        blockers.append(
            make_blocker(
                Task161FailureCode.UNSUPPORTED_TASK161_VERSION,
                stage=Task161FailureStage.RAW_BOUNDARY,
                field_path="task161_version",
            )
        )
    if raw.get("source_definition_id") != TASK161_SOURCE_DEFINITION_ID:
        blockers.append(
            make_blocker(
                Task161FailureCode.SOURCE_DEFINITION_ID_MISMATCH,
                stage=Task161FailureStage.RAW_BOUNDARY,
                field_path="source_definition_id",
            )
        )
    metadata = raw.get("request_metadata")
    if type(metadata) not in (list, tuple):
        blockers.append(
            make_blocker(
                Task161FailureCode.INVALID_REQUEST_SCHEMA,
                stage=Task161FailureStage.RAW_BOUNDARY,
                field_path="request_metadata",
            )
        )
    else:
        keys_seen: list[str] = []
        metadata_items = cast(list[object] | tuple[object, ...], metadata)
        for pair in metadata_items:
            parsed_pair = _metadata_pair(pair)
            if parsed_pair is None:
                blockers.append(
                    make_blocker(
                        Task161FailureCode.INVALID_REQUEST_SCHEMA,
                        stage=Task161FailureStage.RAW_BOUNDARY,
                        field_path="request_metadata",
                    )
                )
                break
            keys_seen.append(parsed_pair[0])
        if len(keys_seen) != len(set(keys_seen)):
            blockers.append(
                make_blocker(
                    Task161FailureCode.INVALID_REQUEST_SCHEMA,
                    stage=Task161FailureStage.RAW_BOUNDARY,
                    field_path="request_metadata",
                    details=(("duplicate_policy", "reject_duplicates"),),
                )
            )
    return tuple(blockers)


def _metadata(raw: dict[str, object]) -> tuple[tuple[str, str], ...]:
    value = raw["request_metadata"]
    if type(value) not in (list, tuple):
        raise ValueError("request metadata is not a sequence")
    pairs: list[tuple[str, str]] = []
    metadata_items = cast(list[object] | tuple[object, ...], value)
    for pair in metadata_items:
        parsed_pair = _metadata_pair(pair)
        if parsed_pair is None:
            raise ValueError("request metadata contains an invalid pair")
        pairs.append(parsed_pair)
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError("request metadata contains duplicate keys")
    return tuple(sorted(pairs, key=lambda item: (item[0].encode("utf-8"), item[1].encode("utf-8"))))


def _fallback_request_hash(outcome: RawProjectionOutcome) -> str:
    return raw_request_projection_hash(outcome.projection)


def _task160_identity_or_none(task160_result: object) -> str | None:
    if type(task160_result) is not Task160Result:
        return None
    try:
        return str(task160_result.result_id)
    except BaseException:
        return None


def _replay_task160(task160_result: Task160Result) -> Task161FailureCode | None:
    try:
        expected_hash = sha256_hex_from_framed_bytes(
            task160_success_canonical_bytes(result=task160_result)
        )
        expected_id = task160_result_id(expected_hash)
        if task160_result.result_hash != expected_hash or task160_result.result_id != expected_id:
            return Task161FailureCode.TASK160_IDENTITY_REPLAY_FAILED
        if (
            task160_result.provenance.provenance_hash
            != task160_result.provenance.graph.compute_hash()
        ):
            return Task161FailureCode.TASK160_IDENTITY_REPLAY_FAILED
    except BaseException:
        return Task161FailureCode.TASK160_IDENTITY_REPLAY_FAILED
    return None


def _valid_task160_invariants(task160_result: Task160Result) -> Task161FailureCode | None:
    if task160_result.applicability.status.value != "APPLICABLE":
        return Task161FailureCode.TASK160_NOT_APPLICABLE
    if task160_result.completeness.status.value != "COMPLETE":
        return Task161FailureCode.TASK160_NOT_COMPLETE
    if task160_result.blockers != () or task160_result.warnings != ():
        return Task161FailureCode.INVALID_TASK160_RESULT
    return None


def _assumption(
    assumption_id: str,
    semantic_name: str,
    source_value: str,
    authority: AssumptionAuthorityClass,
    *,
    case_required: bool,
    runtime_validation: bool,
) -> SourceAssumption:
    return SourceAssumption(
        assumption_id=assumption_id,
        semantic_name=semantic_name,
        source_value=source_value,
        source_status="EXPLICIT",
        primary_authority_class=authority,
        case_authority_required=case_required,
        runtime_validation_required=runtime_validation,
        evidence_refs=("MAGAZONI_2019",),
    )


def _source_assumptions() -> tuple[SourceAssumption, ...]:
    inherited = AssumptionAuthorityClass.TASK160_INHERITED_AUTHORITY
    physical = AssumptionAuthorityClass.PHYSICAL_CASE_AUTHORITY_REQUIRED
    catalog = AssumptionAuthorityClass.CATALOG_FIXED_SOURCE_SEMANTIC
    return (
        _assumption(
            "A01_NO_PHASE_CHANGE",
            "NO_PHASE_CHANGE",
            "single_phase_operation_no_phase_change",
            inherited,
            case_required=False,
            runtime_validation=False,
        ),
        _assumption(
            "A02_CONSTANT_FLUID_THERMOPHYSICAL_PROPERTIES",
            "CONSTANT_FLUID_THERMOPHYSICAL_PROPERTIES",
            "constant_fluid_thermophysical_properties",
            inherited,
            case_required=False,
            runtime_validation=False,
        ),
        _assumption(
            "A03_TEMA_E_SHELL_TYPE",
            "TEMA_E_SHELL_TYPE",
            "TEMA_E",
            physical,
            case_required=True,
            runtime_validation=True,
        ),
        _assumption(
            "A04_OVERALL_COUNTER_FLOW",
            "OVERALL_COUNTER_FLOW",
            "COUNTER_FLOW",
            physical,
            case_required=True,
            runtime_validation=True,
        ),
        _assumption(
            "A05_BAFFLE_COUNT",
            "BAFFLE_COUNT",
            "INTEGER_1_THROUGH_5",
            physical,
            case_required=True,
            runtime_validation=True,
        ),
        _assumption(
            "A06_PHYSICAL_STHE_TUBE_SIDE_MIXING",
            "PHYSICAL_STHE_TUBE_SIDE_MIXING",
            "UNMIXED",
            physical,
            case_required=True,
            runtime_validation=True,
        ),
        _assumption(
            "A07_PHYSICAL_STHE_SHELL_SIDE_MIXING_MODEL",
            "PHYSICAL_STHE_SHELL_SIDE_MIXING_MODEL",
            "MODEL_2_MIXING_ACROSS_TUBE_BANK",
            physical,
            case_required=True,
            runtime_validation=True,
        ),
        _assumption(
            "A08_STEADY_STATE",
            "STEADY_STATE",
            "steady_state_operation",
            physical,
            case_required=True,
            runtime_validation=True,
        ),
        _assumption(
            "A09_NEGLIGIBLE_AMBIENT_HEAT_LOSS",
            "NEGLIGIBLE_AMBIENT_HEAT_LOSS",
            "negligible_heat_loss_to_surroundings",
            physical,
            case_required=True,
            runtime_validation=True,
        ),
        _assumption(
            "A10_NO_INTERNAL_THERMAL_SOURCE_SINK",
            "NO_INTERNAL_THERMAL_SOURCE_SINK",
            "no_internal_thermal_energy_source_or_sink",
            physical,
            case_required=True,
            runtime_validation=True,
        ),
        _assumption(
            "A11_CONSTANT_WALL_MATERIAL_PROPERTIES",
            "CONSTANT_WALL_MATERIAL_PROPERTIES",
            "constant_wall_material_transport_properties",
            physical,
            case_required=True,
            runtime_validation=True,
        ),
        _assumption(
            "A12_CONSTANT_HEAT_TRANSFER_COEFFICIENT",
            "CONSTANT_HEAT_TRANSFER_COEFFICIENT",
            "constant_heat_transfer_coefficients",
            physical,
            case_required=True,
            runtime_validation=True,
        ),
        _assumption(
            "A13_NEGLIGIBLE_AXIAL_HEAT_TRANSFER",
            "NEGLIGIBLE_AXIAL_HEAT_TRANSFER",
            "axial_heat_transfer_neglected_in_source_model",
            physical,
            case_required=True,
            runtime_validation=True,
        ),
        _assumption(
            "A14_CASE_ZERO_LEAKAGE_MODEL_ASSUMPTION",
            "CASE_ZERO_LEAKAGE_MODEL_ASSUMPTION",
            "source_supports_zero_leakage_assumption_but_does_not_prove_case",
            physical,
            case_required=True,
            runtime_validation=True,
        ),
        _assumption(
            "A15_CASE_ZERO_BYPASS_MODEL_ASSUMPTION",
            "CASE_ZERO_BYPASS_MODEL_ASSUMPTION",
            "source_supports_zero_bypass_assumption_but_does_not_prove_case",
            physical,
            case_required=True,
            runtime_validation=True,
        ),
        _assumption(
            "A16_CFHE_SURROGATE_EXTERNAL_FLUID_IDENTITY",
            "CFHE_SURROGATE_EXTERNAL_FLUID_IDENTITY",
            "PHYSICAL_STHE_TUBE_SIDE",
            catalog,
            case_required=False,
            runtime_validation=False,
        ),
        _assumption(
            "A17_CFHE_SURROGATE_INTERNAL_FLUID_IDENTITY",
            "CFHE_SURROGATE_INTERNAL_FLUID_IDENTITY",
            "PHYSICAL_STHE_SHELL_SIDE",
            catalog,
            case_required=False,
            runtime_validation=False,
        ),
        _assumption(
            "A18_CFHE_SURROGATE_EXTERNAL_FLUID_MIXING",
            "CFHE_SURROGATE_EXTERNAL_FLUID_MIXING",
            "UNMIXED",
            catalog,
            case_required=False,
            runtime_validation=False,
        ),
        _assumption(
            "A19_CFHE_SURROGATE_INTERNAL_FLUID_MIXING",
            "CFHE_SURROGATE_INTERNAL_FLUID_MIXING",
            "MODEL_2_FULLY_MIXED_IN_EACH_SURROGATE_PASS",
            catalog,
            case_required=False,
            runtime_validation=False,
        ),
        _assumption(
            "A20_SECTIONAL_SURROGATE_MODEL",
            "SECTIONAL_SURROGATE_MODEL",
            "CROSSFLOW_HEAT_EXCHANGER_PER_BAFFLE_REGION",
            catalog,
            case_required=False,
            runtime_validation=False,
        ),
        _assumption(
            "A21_SECTION_COUNT_RELATION",
            "SECTION_COUNT_RELATION",
            "BAFFLE_COUNT_PLUS_ONE",
            catalog,
            case_required=False,
            runtime_validation=False,
        ),
    )


def _catalogs() -> tuple[
    FlowArrangementCatalogAuthority,
    PerformanceMethodCatalogAuthority,
    PhysicalStheMixingAuthority,
    CfheSurrogateMixingAuthority,
    StheCfheIdentityMapping,
    tuple[SourceAssumption, ...],
    MethodOutputSemantics,
    CaseBindingState,
    CatalogApplicability,
    CatalogCompleteness,
]:
    assumptions = _source_assumptions()
    flow = FlowArrangementCatalogAuthority(
        catalog_id="TEMA_E_1X1_OVERALL_COUNTERFLOW_SECTIONAL_MIXING",
        source_shell_type="TEMA_E",
        source_shell_pass_count=1,
        source_tube_pass_count=1,
        overall_flow_orientation="COUNTER_FLOW",
        sectional_surrogate_model="CROSSFLOW_HEAT_EXCHANGER_PER_BAFFLE_REGION",
        section_count_relation="BAFFLE_COUNT_PLUS_ONE",
        hxforge_construction_intersection="FIXED_TUBESHEET",
        limitations=(
            "catalog_scope_only",
            "current_case_flow_arrangement_unbound",
            "TEMA_E_case_authority_required_for_case_use",
        ),
        evidence_refs=("MAGAZONI_2019", "NASA_TM_2020_220473"),
    )
    method = PerformanceMethodCatalogAuthority(
        method_authority_id="MAGAZONI_1X1_COUNTERFLOW_SECTIONAL_P_MODEL_V1",
        method_family="BOUNDED_TEMA_E_SECTIONAL_COUNTERFLOW",
        method_revision="V1",
        flow_arrangement_catalog_id=flow.catalog_id,
        engineering_source_id="MAGAZONI_2019",
        engineering_source_version="2019",
        engineering_source_location="page 873, Equations (1)-(4); page 880, Table 7",
        engineering_source_license="CC_BY_4_0",
        relation_id="MAGAZONI_1X1_MIXING_MODEL_2_P_RELATION_TABLE_7",
        source_variable_definitions=(
            ("P_source", "(T_c,out-T_c,in)/(T_h,in-T_c,in)"),
            ("R_source", "C_c/C_h"),
            ("C_c", "cold-side heat-capacity rate"),
            ("C_h", "hot-side heat-capacity rate"),
            ("NTU", "UA/C_min"),
            ("baffle_count", "integer 1 through 5"),
            ("mixing_model", "MODEL_2"),
        ),
        hxforge_variable_mapping=(
            ("C_min", "TASK161 capacity foundation"),
            ("C_max", "TASK161 capacity foundation"),
            ("C_r", "C_min/C_max"),
            ("R_source", "C_dot_cold/C_dot_hot"),
            ("NTU", "downstream runtime authority"),
            ("P_source", "Table 7 method output"),
        ),
        physical_configuration_scope=(
            ("source_shell_type", "TEMA_E"),
            ("source_shell_pass_count", "1"),
            ("source_tube_pass_count", "1"),
            ("hxforge_construction_intersection", "FIXED_TUBESHEET"),
        ),
        model_scope=(
            ("overall_flow_orientation", "COUNTER_FLOW"),
            ("sectional_flow_model", "CROSSFLOW_HEAT_EXCHANGER_PER_BAFFLE_REGION"),
            ("physical_sthe_tube_side_mixing", "UNMIXED"),
            ("physical_sthe_shell_side_mixing", "MODEL_2_MIXING_ACROSS_TUBE_BANK"),
            ("cfhe_surrogate_external_mixing", "UNMIXED"),
            ("cfhe_surrogate_internal_mixing", "MODEL_2_FULLY_MIXED_IN_EACH_SURROGATE_PASS"),
        ),
        required_case_inputs=TASK161_REQUIRED_CASE_INPUTS,
        required_runtime_inputs=TASK161_REQUIRED_RUNTIME_INPUTS,
        output_variables=("P_source",),
        parameter_authorities=(
            ("baffle_count", "explicit_case_authority_required; domain 1..5"),
            ("mixing_model", "explicit_case_authority_required; domain {2}"),
            ("flow_orientation", "explicit_case_authority_required; COUNTER_FLOW"),
            ("shell_type", "explicit_case_authority_required; TEMA_E"),
        ),
        supported_baffle_count_domain="INTEGER_1_THROUGH_5",
        supported_mixing_model_domain=("MODEL_2",),
        single_phase_requirement=True,
        constant_property_requirement=True,
        leakage_assumption=(
            "SOURCE_MODEL_ZERO_LEAKAGE_ASSUMPTION_SUPPORTED=true;"
            "EXPLICIT_LEAKAGE_STREAM_TERMS_PRESENT=false;"
            "IMPLICIT_U_CORRECTION_ALLOWED=true"
        ),
        bypass_assumption=(
            "SOURCE_MODEL_ZERO_BYPASS_ASSUMPTION_SUPPORTED=true;"
            "EXPLICIT_BYPASS_STREAM_TERMS_PRESENT=false;"
            "IMPLICIT_U_CORRECTION_ALLOWED=true"
        ),
        p_source_definition="(T_c,out-T_c,in)/(T_h,in-T_c,in)",
        r_source_definition="C_dot_cold/C_dot_hot",
        ntu_definition="UA/C_min",
        p_to_epsilon_mapping="epsilon=P_source*C_dot_cold/C_min",
        r_to_cr_mapping="C_r=min(R_source,1/R_source) for positive R_source",
        applicability=(
            "TEMA_E",
            "FIXED_TUBESHEET",
            "1_SHELL_PASS",
            "1_TUBE_PASS",
            "COUNTER_FLOW",
            "MODEL_2",
            "BAFFLE_COUNT_1_THROUGH_5",
            "SECTIONAL_CROSSFLOW",
        ),
        limitations=(
            "catalog_only",
            "case_binding_not_selected",
            "no_numeric_NTU_or_P_source_evaluation",
            "no_numeric_epsilon_or_effectiveness_evaluation",
        ),
        evidence_refs=("MAGAZONI_2019", "NASA_TM_2020_220473"),
        provenance=(
            "SOURCE_AUTHORITY_ISSUE_225",
            "MAGAZONI_2019_PAGE_873_EQUATIONS_1_4",
            "MAGAZONI_2019_PAGE_880_TABLE_7",
        ),
        authority_hash="0" * 64,
    )
    from .canonical import method_catalog_payload_hash

    method = replace(method, authority_hash=method_catalog_payload_hash(method))
    physical = PhysicalStheMixingAuthority(
        tube_side_mixing_assumption="UNMIXED",
        shell_side_mixing_assumption="MODEL_2_MIXING_ACROSS_TUBE_BANK",
        shell_side_mixing_model_id="MODEL_2",
    )
    surrogate = CfheSurrogateMixingAuthority(
        external_fluid_identity="PHYSICAL_STHE_TUBE_SIDE",
        internal_fluid_identity="PHYSICAL_STHE_SHELL_SIDE",
        external_fluid_mixing_assumption="UNMIXED",
        internal_fluid_mixing_assumption="MODEL_2_FULLY_MIXED_IN_EACH_SURROGATE_PASS",
    )
    mapping = StheCfheIdentityMapping(True, True, False, False)
    output = MethodOutputSemantics(
        direct_output="P_source",
        direct_output_definition="cold-side temperature effectiveness",
        direct_output_is_generic_epsilon=False,
        direct_output_is_magazoni_p=True,
        p_to_epsilon_mapping="epsilon=P_source*C_dot_cold/C_min",
    )
    binding = CaseBindingState(
        tema_e_binding=CatalogBindingState.UNBOUND,
        flow_arrangement_binding=CatalogBindingState.UNBOUND,
        method_selection=CatalogBindingState.UNBOUND,
        leakage_assumption_binding=CatalogBindingState.UNBOUND,
        bypass_assumption_binding=CatalogBindingState.UNBOUND,
    )
    applicability = CatalogApplicability(
        status=CatalogStatus.COMPLETE,
        catalog_source_applicable=True,
        case_binding_applicability="DEFERRED_UNBOUND",
        downstream_runtime_applicability="DEFERRED_TO_DOWNSTREAM",
        required_scope=(
            "TASK160_FIXED_TUBESHEET",
            "TEMA_E",
            "1_SHELL_PASS",
            "1_TUBE_PASS",
            "COUNTER_FLOW",
            "SECTIONAL_CROSSFLOW",
            "MODEL_2",
            "BAFFLE_COUNT_1_THROUGH_5",
            "SOURCE_ASSUMPTION_SET",
        ),
    )
    completeness = CatalogCompleteness(
        status=CatalogStatus.COMPLETE,
        required_case_inputs_declared=True,
        required_runtime_inputs_declared=True,
        output_contract_declared=True,
        source_assumptions_declared=True,
        provenance_declared=True,
    )
    return (
        flow,
        method,
        physical,
        surrogate,
        mapping,
        assumptions,
        output,
        binding,
        applicability,
        completeness,
    )


def _capacity_foundation(task160_result: Task160Result) -> CapacityFoundation:
    c_hot = task160_result.c_dot_hot_W_K
    c_cold = task160_result.c_dot_cold_W_K
    if type(c_hot) is not Decimal or type(c_cold) is not Decimal:
        raise ValueError(Task161FailureCode.INVALID_CAPACITY_RATE.value)
    if not c_hot.is_finite() or not c_cold.is_finite() or c_hot <= 0 or c_cold <= 0:
        raise ValueError(Task161FailureCode.INVALID_CAPACITY_RATE.value)
    c_min = min(c_hot, c_cold)
    c_max = max(c_hot, c_cold)
    with localcontext(TASK161_DECIMAL_CONTEXT):
        if c_hot == c_cold:
            c_r = Decimal("1")
            r_source = Decimal("1")
            relation = CapacitySideRelation.EQUAL_CAPACITY
        else:
            try:
                c_r = c_min / c_max
                r_source = c_cold / c_hot
            except DecimalException as exc:
                raise ValueError(Task161FailureCode.INVALID_CAPACITY_RATIO.value) from exc
            relation = (
                CapacitySideRelation.COLD_SIDE_IS_CMIN
                if c_cold < c_hot
                else CapacitySideRelation.HOT_SIDE_IS_CMIN
            )
    if (
        not c_r.is_finite()
        or not r_source.is_finite()
        or c_min <= 0
        or c_max <= 0
        or c_min > c_max
        or not Decimal(0) < c_r <= Decimal(1)
        or r_source <= 0
    ):
        raise ValueError(Task161FailureCode.INVALID_CAPACITY_RATIO.value)
    return CapacityFoundation(c_hot, c_cold, c_min, c_max, c_r, r_source, relation)


def _pre_result(
    *,
    request: Task161Request,
    request_hash_value: str,
    task160_evidence: Task160ResultIdentityProjection,
    capacity: CapacityFoundation,
    flow: FlowArrangementCatalogAuthority,
    method: PerformanceMethodCatalogAuthority,
    physical: PhysicalStheMixingAuthority,
    surrogate: CfheSurrogateMixingAuthority,
    mapping: StheCfheIdentityMapping,
    assumptions: tuple[SourceAssumption, ...],
    output: MethodOutputSemantics,
    binding: CaseBindingState,
    applicability: CatalogApplicability,
    completeness: CatalogCompleteness,
    provenance_semantic_inputs: Task161ProvenanceSemanticInputs,
) -> Task161PreResultIdentityInputs:
    return Task161PreResultIdentityInputs(
        schema_version=TASK161_SCHEMA_VERSION,
        task161_version=TASK161_VERSION,
        implementation_software_version=TASK161_IMPLEMENTATION_SOFTWARE_VERSION,
        source_definition_id=request.source_definition_id,
        request_hash=request_hash_value,
        task160_evidence=task160_evidence,
        capacity_foundation=capacity,
        flow_arrangement_catalog=flow,
        performance_method_catalog=method,
        physical_sthe_mixing=physical,
        cfhe_surrogate_mixing=surrogate,
        sthe_cfhe_identity_mapping=mapping,
        source_assumptions=assumptions,
        required_case_inputs=TASK161_REQUIRED_CASE_INPUTS,
        required_runtime_inputs=TASK161_REQUIRED_RUNTIME_INPUTS,
        method_output_semantics=output,
        case_binding_state=binding,
        applicability=applicability,
        completeness=completeness,
        warnings_normalized=(),
        blockers_normalized=(),
        provenance_semantic_inputs=provenance_semantic_inputs,
    )


def _valid_task161(
    request: Task161Request,
    request_hash_value: str,
) -> Task161ValidationResult:
    task160_result = request.task160_result
    replay_failure = _replay_task160(task160_result)
    if replay_failure is not None:
        return _typed_blocked(
            request_hash_value=request_hash_value,
            task160_result_id_or_none=_task160_identity_or_none(task160_result),
            blockers=(
                make_blocker(
                    replay_failure,
                    stage=Task161FailureStage.IDENTITY,
                    field_path="task160_result",
                ),
            ),
            stage=Task161FailureStage.IDENTITY,
        )
    invariant_failure = _valid_task160_invariants(task160_result)
    if invariant_failure is not None:
        stage = (
            Task161FailureStage.APPLICABILITY
            if invariant_failure is Task161FailureCode.TASK160_NOT_APPLICABLE
            else Task161FailureStage.COMPLETENESS
            if invariant_failure is Task161FailureCode.TASK160_NOT_COMPLETE
            else Task161FailureStage.STRICT_VALIDATION
        )
        return _typed_blocked(
            request_hash_value=request_hash_value,
            task160_result_id_or_none=_task160_identity_or_none(task160_result),
            blockers=(
                make_blocker(
                    invariant_failure,
                    stage=stage,
                    field_path="task160_result",
                ),
            ),
            stage=stage,
        )
    try:
        capacity = _capacity_foundation(task160_result)
    except ValueError as exc:
        code = (
            Task161FailureCode.INVALID_CAPACITY_RATE
            if str(exc) == Task161FailureCode.INVALID_CAPACITY_RATE.value
            else Task161FailureCode.INVALID_CAPACITY_RATIO
        )
        return _typed_blocked(
            request_hash_value=request_hash_value,
            task160_result_id_or_none=_task160_identity_or_none(task160_result),
            blockers=(
                make_blocker(
                    code,
                    stage=Task161FailureStage.STRICT_VALIDATION,
                    field_path="task160_result.c_dot",
                ),
            ),
            stage=Task161FailureStage.STRICT_VALIDATION,
        )
    try:
        (
            flow,
            method,
            physical,
            surrogate,
            mapping,
            assumptions,
            output,
            binding,
            applicability,
            completeness,
        ) = _catalogs()
        task160_evidence = task160_result_identity_projection(task160_result)
        from .provenance import build_provenance_semantic_inputs

        semantic_inputs = build_provenance_semantic_inputs(
            request_hash=request_hash_value,
            task160_result=task160_result,
            method_catalog=method,
        )
        pre = _pre_result(
            request=request,
            request_hash_value=request_hash_value,
            task160_evidence=task160_evidence,
            capacity=capacity,
            flow=flow,
            method=method,
            physical=physical,
            surrogate=surrogate,
            mapping=mapping,
            assumptions=assumptions,
            output=output,
            binding=binding,
            applicability=applicability,
            completeness=completeness,
            provenance_semantic_inputs=semantic_inputs,
        )
        final_hash = success_hash(pre)
        final_id = result_id(final_hash)
        provenance, replayed_semantic_inputs = build_success_provenance(
            request_hash=request_hash_value,
            task160_result=task160_result,
            method_catalog=method,
            result_hash=final_hash,
            result_id=final_id,
        )
        if replayed_semantic_inputs != semantic_inputs:
            raise ValueError(Task161FailureCode.PROVENANCE_INVALID.value)
        result = Task161Result(
            schema_version=TASK161_SCHEMA_VERSION,
            task161_version=TASK161_VERSION,
            implementation_software_version=TASK161_IMPLEMENTATION_SOFTWARE_VERSION,
            source_definition_id=request.source_definition_id,
            request_hash=request_hash_value,
            task160_evidence=task160_evidence,
            capacity_foundation=capacity,
            flow_arrangement_catalog=flow,
            performance_method_catalog=method,
            physical_sthe_mixing=physical,
            cfhe_surrogate_mixing=surrogate,
            sthe_cfhe_identity_mapping=mapping,
            source_assumptions=assumptions,
            required_case_inputs=TASK161_REQUIRED_CASE_INPUTS,
            required_runtime_inputs=TASK161_REQUIRED_RUNTIME_INPUTS,
            method_output_semantics=output,
            case_binding_state=binding,
            applicability=applicability,
            completeness=completeness,
            warnings=(),
            blockers=(),
            provenance_semantic_inputs=semantic_inputs,
            provenance=provenance,
            result_hash=final_hash,
            result_id=final_id,
        )
        if success_hash(pre) != result.result_hash:
            raise ValueError(Task161FailureCode.IDENTITY_REPLAY_FAILED.value)
        if result_id(result.result_hash) != result.result_id:
            raise ValueError(Task161FailureCode.IDENTITY_REPLAY_FAILED.value)
        if result.provenance.provenance_hash != result.provenance.graph.compute_hash():
            raise ValueError(Task161FailureCode.PROVENANCE_INVALID.value)
        return Task161ValidationResult(Task161ValidationStatus.VALID, None, None, result)
    except BaseException:
        return _typed_blocked(
            request_hash_value=request_hash_value,
            task160_result_id_or_none=_task160_identity_or_none(task160_result),
            blockers=(
                make_blocker(
                    Task161FailureCode.INTERNAL_INVARIANT_VIOLATION,
                    stage=Task161FailureStage.IDENTITY,
                    field_path="task161_result",
                ),
            ),
            stage=Task161FailureStage.IDENTITY,
        )


def validate_request(raw: object) -> Task161ValidationResult:
    """Validate a raw TASK161 catalog request and populate exactly one branch."""
    outcome = project_raw_request_with_diagnostics(raw)
    blockers = list(_raw_schema_blockers(raw))
    reasons = outcome.reasons
    if reasons or outcome.unsupported_object_present:
        blockers.append(
            make_blocker(
                Task161FailureCode.UNSUPPORTED_RAW_VALUE,
                stage=Task161FailureStage.RAW_BOUNDARY,
                field_path="request",
            )
        )
    if blockers:
        return _raw_blocked(outcome, tuple(blockers))
    assert type(raw) is dict
    raw_task160 = raw["task160_result"]
    request_hash_value = _fallback_request_hash(outcome)
    identity = _task160_identity_or_none(raw_task160)
    if type(raw_task160) is not Task160Result:
        return _typed_blocked(
            request_hash_value=request_hash_value,
            task160_result_id_or_none=identity,
            blockers=(
                make_blocker(
                    Task161FailureCode.INVALID_TASK160_RESULT,
                    stage=Task161FailureStage.STRICT_VALIDATION,
                    field_path="task160_result",
                ),
            ),
            stage=Task161FailureStage.STRICT_VALIDATION,
        )
    try:
        metadata = _metadata(raw)
        request = Task161Request(
            schema_version=raw["schema_version"],
            task161_version=raw["task161_version"],
            source_definition_id=raw["source_definition_id"],
            task160_result=raw_task160,
            request_metadata=metadata,
        )
        request_hash_value = request_hash(request)
    except BaseException:
        return _typed_blocked(
            request_hash_value=request_hash_value,
            task160_result_id_or_none=identity,
            blockers=(
                make_blocker(
                    Task161FailureCode.INVALID_REQUEST_SCHEMA,
                    stage=Task161FailureStage.STRICT_VALIDATION,
                    field_path="request",
                ),
            ),
            stage=Task161FailureStage.STRICT_VALIDATION,
        )
    return _valid_task161(request, request_hash_value)


__all__ = [
    "TASK161_ADDITIONAL_TRAP_OVERRIDES",
    "TASK161_CASE_BINDING_REQUIRED_FOR_SUCCESS",
    "TASK161_DECIMAL_CONTEXT",
    "TASK161_METHOD_AUTHORITY_MODE",
    "TASK161_PERFORMANCE_METHOD_ROLE",
    "validate_request",
]
