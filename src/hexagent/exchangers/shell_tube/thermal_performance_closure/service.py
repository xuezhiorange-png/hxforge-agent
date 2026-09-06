"""TASK162 validation and thermal-performance closure service."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from hexagent.exchangers.shell_tube.flow_arrangement_performance_method_authority.canonical import (
    result_id as task161_result_id,
)
from hexagent.exchangers.shell_tube.flow_arrangement_performance_method_authority.canonical import (
    success_hash_from_inputs as task161_success_hash_from_inputs,
)
from hexagent.exchangers.shell_tube.flow_arrangement_performance_method_authority.models import (
    Task161PreResultIdentityInputs,
    Task161Result,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.canonical import (
    result_id_from_hash as task038_result_id_from_hash,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.canonical import (
    success_result_hash as task038_success_result_hash,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.models import (
    Task038SuccessResult,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.provenance import (
    verify_provenance as verify_task038_provenance,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.validation import (
    verify_task038_success_identity,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.canonical import (
    result_id as task160_result_id,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.canonical import (
    sha256_hex_from_framed_bytes as task160_hash,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.canonical import (
    success_canonical_bytes as task160_success_canonical_bytes,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.models import (
    Task160Result,
    ThermalRole,
)

from .canonical import (
    raw_blocked_hash,
    raw_blocked_id,
    raw_request_projection_hash,
    request_hash,
    result_id,
    success_hash_from_inputs,
    task038_result_identity_projection,
    task160_result_identity_projection,
    task161_result_identity_projection,
    typed_blocked_hash,
    typed_blocked_id,
)
from .decimal_math import (
    TASK162_ENERGY_BALANCE_POLICY_ID,
    DecimalArithmeticError,
    decimal_add,
    decimal_divide,
    decimal_multiply,
    decimal_subtract,
    exact_interval,
    interval_add,
    interval_contains,
    interval_divide,
    interval_multiply,
    interval_subtract,
    table7_relation,
)
from .errors import Task162FailureCode, blocker, normalized_blockers
from .models import (
    TASK162_IMPLEMENTATION_SOFTWARE_VERSION,
    TASK162_RAW_BOUNDARY_SCHEMA_VERSION,
    TASK162_SCHEMA_VERSION,
    TASK162_SOURCE_DEFINITION_ID,
    TASK162_TYPED_BLOCKED_SCHEMA_VERSION,
    TASK162_VERSION,
    Task162AmbientHeatLossAssumption,
    Task162Applicability,
    Task162AxialHeatTransferAssumption,
    Task162BindingStatus,
    Task162Blocker,
    Task162BypassAssumption,
    Task162CaseAuthority,
    Task162CompatibilityDimension,
    Task162CompatibilityEvidence,
    Task162CompatibilityStatus,
    Task162Completeness,
    Task162CrossProducerBindingAuthority,
    Task162EnergyBalanceEvidence,
    Task162EnergyBalanceStatus,
    Task162FailureStage,
    Task162FlowOrientation,
    Task162HeatTransferCoefficientAssumption,
    Task162InternalSourceSinkAssumption,
    Task162LeakageAssumption,
    Task162NormalizedCaseBinding,
    Task162NumericalFoundation,
    Task162ProvenanceSemanticInputs,
    Task162RawBoundaryBlockedResult,
    Task162RawRequestProjection,
    Task162Request,
    Task162Result,
    Task162SelectedMethodIdentity,
    Task162ShellSideMixingModel,
    Task162ShellType,
    Task162TerminalClosureEvidence,
    Task162TubeSideMixing,
    Task162TypedBlockedResult,
    Task162ValidationResult,
    Task162ValidationStatus,
    Task162WallPropertyAssumption,
)
from .provenance import build_success_provenance
from .raw_projection import project_raw_request_with_diagnostics

TASK162_METHOD_AUTHORITY_ID = "MAGAZONI_1X1_COUNTERFLOW_SECTIONAL_P_MODEL_V1"
TASK162_METHOD_FAMILY = "BOUNDED_TEMA_E_SECTIONAL_COUNTERFLOW"
TASK162_FLOW_ARRANGEMENT_CATALOG_ID = "TEMA_E_1X1_OVERALL_COUNTERFLOW_SECTIONAL_MIXING"
TASK162_ENGINEERING_SOURCE_ID = "MAGAZONI_2019"
TASK162_RELATION_ID = "MAGAZONI_1X1_MIXING_MODEL_2_P_RELATION_TABLE_7"

REQUIRED_RAW_FIELDS = frozenset(
    {
        "schema_version",
        "task162_version",
        "source_definition_id",
        "task160_result",
        "task161_result",
        "task038_result",
        "cross_producer_binding_authority",
        "case_authority",
        "request_metadata",
    }
)


def _metadata(raw: object) -> tuple[tuple[str, str], ...]:
    if type(raw) is tuple:
        items: tuple[object, ...] | list[object] = cast(tuple[object, ...], raw)
    elif type(raw) is list:
        items = cast(list[object], raw)
    else:
        raise ValueError("metadata schema")
    pairs: list[tuple[str, str]] = []
    for item in items:
        pair: tuple[object, ...] | list[object]
        if type(item) is tuple:
            pair = cast(tuple[object, ...], item)
        elif type(item) is list:
            pair = cast(list[object], item)
        else:
            raise ValueError("metadata schema")
        if len(pair) != 2:
            raise ValueError("metadata schema")
        key, value = pair
        if type(key) is not str or type(value) is not str:
            raise ValueError("metadata schema")
        pairs.append((key, value))
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError("metadata duplicate")
    return tuple(sorted(pairs, key=lambda pair: (pair[0].encode("utf-8"), pair[1].encode("utf-8"))))


def _raw_blocked(
    projection: Task162RawRequestProjection,
    projection_hash: str,
    blockers: tuple[Task162Blocker, ...],
) -> Task162ValidationResult:
    preliminary = Task162RawBoundaryBlockedResult(
        schema_version=TASK162_RAW_BOUNDARY_SCHEMA_VERSION,
        task162_version=TASK162_VERSION,
        implementation_software_version=TASK162_IMPLEMENTATION_SOFTWARE_VERSION,
        failure_stage=Task162FailureStage.RAW_BOUNDARY,
        raw_request_projection=projection,
        raw_request_projection_hash=projection_hash,
        blockers=normalized_blockers(blockers),
        warnings=(),
        blocked_result_hash="",
        blocked_result_id=raw_blocked_id("0" * 64),
    )
    blocked_hash = raw_blocked_hash(preliminary)
    blocked = replace(
        preliminary,
        blocked_result_hash=blocked_hash,
        blocked_result_id=raw_blocked_id(blocked_hash),
    )
    return Task162ValidationResult(
        status=Task162ValidationStatus.RAW_BOUNDARY_BLOCKED,
        raw_boundary_blocked=blocked,
    )


def _typed_blocked(
    request_hash_value: str,
    blockers: tuple[Task162Blocker, ...],
    *,
    stage: Task162FailureStage,
    task160_id: str | None = None,
) -> Task162ValidationResult:
    preliminary = Task162TypedBlockedResult(
        schema_version=TASK162_TYPED_BLOCKED_SCHEMA_VERSION,
        task162_version=TASK162_VERSION,
        implementation_software_version=TASK162_IMPLEMENTATION_SOFTWARE_VERSION,
        failure_stage=stage,
        request_hash=request_hash_value,
        task160_result_id_or_none=task160_id,
        blockers=normalized_blockers(blockers),
        warnings=(),
        blocked_result_hash="",
        blocked_result_id=typed_blocked_id("0" * 64),
    )
    blocked_hash = typed_blocked_hash(preliminary)
    blocked = replace(
        preliminary,
        blocked_result_hash=blocked_hash,
        blocked_result_id=typed_blocked_id(blocked_hash),
    )
    return Task162ValidationResult(
        status=Task162ValidationStatus.TYPED_BLOCKED, typed_blocked=blocked
    )


def _code_blocker(code: Task162FailureCode, stage: Task162FailureStage) -> Task162Blocker:
    return blocker(code, stage)


def _task160_id_or_none(value: Task160Result) -> str | None:
    result_id = value.result_id
    if type(result_id) is UUID:
        return str(result_id).lower()
    return None


def _replay_task160(value: Task160Result) -> Task162FailureCode | None:
    try:
        expected_hash = task160_hash(task160_success_canonical_bytes(result=value))
        expected_id = task160_result_id(expected_hash)
        if value.result_hash != expected_hash or value.result_id != expected_id:
            return Task162FailureCode.TASK160_IDENTITY_REPLAY_FAILED
        if value.provenance.provenance_hash != value.provenance.graph.compute_hash():
            return Task162FailureCode.TASK160_IDENTITY_REPLAY_FAILED
        if value.applicability.status.value != "APPLICABLE":
            return Task162FailureCode.TASK160_NOT_APPLICABLE
        if value.completeness.status.value != "COMPLETE":
            return Task162FailureCode.TASK160_NOT_COMPLETE
        if value.warnings != () or value.blockers != ():
            return Task162FailureCode.INVALID_TASK160_RESULT
    except BaseException:
        return Task162FailureCode.TASK160_IDENTITY_REPLAY_FAILED
    return None


def _replay_task161(value: Task161Result) -> Task162FailureCode | None:
    try:
        pre = Task161PreResultIdentityInputs(
            schema_version=value.schema_version,
            task161_version=value.task161_version,
            implementation_software_version=value.implementation_software_version,
            source_definition_id=value.source_definition_id,
            request_hash=value.request_hash,
            task160_evidence=value.task160_evidence,
            capacity_foundation=value.capacity_foundation,
            flow_arrangement_catalog=value.flow_arrangement_catalog,
            performance_method_catalog=value.performance_method_catalog,
            physical_sthe_mixing=value.physical_sthe_mixing,
            cfhe_surrogate_mixing=value.cfhe_surrogate_mixing,
            sthe_cfhe_identity_mapping=value.sthe_cfhe_identity_mapping,
            source_assumptions=value.source_assumptions,
            required_case_inputs=value.required_case_inputs,
            required_runtime_inputs=value.required_runtime_inputs,
            method_output_semantics=value.method_output_semantics,
            case_binding_state=value.case_binding_state,
            applicability=value.applicability,
            completeness=value.completeness,
            warnings_normalized=value.warnings,
            blockers_normalized=value.blockers,
            provenance_semantic_inputs=value.provenance_semantic_inputs,
        )
        expected_hash = task161_success_hash_from_inputs(pre)
        expected_id = task161_result_id(expected_hash)
        if value.result_hash != expected_hash or value.result_id != expected_id:
            return Task162FailureCode.TASK161_IDENTITY_REPLAY_FAILED
        if value.provenance.provenance_hash != value.provenance.graph.compute_hash():
            return Task162FailureCode.TASK161_IDENTITY_REPLAY_FAILED
        if value.warnings != () or value.blockers != ():
            return Task162FailureCode.INVALID_TASK161_RESULT
        if value.applicability.status.value != "COMPLETE":
            return Task162FailureCode.TASK161_NOT_APPLICABLE
        if value.completeness.status.value != "COMPLETE":
            return Task162FailureCode.TASK161_NOT_COMPLETE
    except BaseException:
        return Task162FailureCode.TASK161_IDENTITY_REPLAY_FAILED
    return None


def _replay_task038(value: Task038SuccessResult) -> Task162FailureCode | None:
    try:
        if not verify_task038_success_identity(value):
            return Task162FailureCode.TASK038_IDENTITY_REPLAY_FAILED
        expected_hash = task038_success_result_hash(value)
        expected_id = task038_result_id_from_hash(expected_hash)
        if value.result_hash != expected_hash or value.result_id != expected_id:
            return Task162FailureCode.TASK038_IDENTITY_REPLAY_FAILED
        if not verify_task038_provenance(value.provenance):
            return Task162FailureCode.TASK038_IDENTITY_REPLAY_FAILED
        if value.warnings != () or value.blockers != ():
            return Task162FailureCode.INVALID_TASK038_RESULT
    except BaseException:
        return Task162FailureCode.TASK038_IDENTITY_REPLAY_FAILED
    return None


def _projection_matches(left: object, right: object, names: tuple[str, ...]) -> bool:
    return all(getattr(left, name) == getattr(right, name) for name in names)


def _prove_task161_task160(task160: Task160Result, task161: Task161Result) -> bool:
    expected = task160_result_identity_projection(task160)
    embedded = task161.task160_evidence
    return _projection_matches(
        embedded,
        expected,
        (
            "schema_version",
            "task160_version",
            "request_hash",
            "result_hash",
            "result_id",
            "provenance_hash",
        ),
    )


def _prove_binding(
    binding: Task162CrossProducerBindingAuthority,
    task160: Task160Result,
    task161: Task161Result,
    task038: Task038SuccessResult,
    case: Task162CaseAuthority,
) -> Task162FailureCode | None:
    if (
        type(binding) is not Task162CrossProducerBindingAuthority
        or type(case) is not Task162CaseAuthority
    ):
        return Task162FailureCode.CROSS_PRODUCER_BINDING_INVALID
    identity_fields = (
        binding.binding_authority_id,
        binding.task160_result_hash,
        binding.task160_result_id,
        binding.task161_result_hash,
        binding.task161_result_id,
        binding.task038_result_hash,
        binding.task038_result_id,
        binding.physical_exchanger_case_id,
        case.case_authority_id,
    )
    if any(type(value) is not str or not value for value in identity_fields):
        return Task162FailureCode.CROSS_PRODUCER_BINDING_INVALID
    if type(binding.binding_status) is not Task162BindingStatus:
        return Task162FailureCode.CROSS_PRODUCER_BINDING_INVALID
    if type(binding.evidence_refs) is not tuple or not binding.evidence_refs:
        return Task162FailureCode.CROSS_PRODUCER_BINDING_INVALID
    if any(type(value) is not str or not value for value in binding.evidence_refs):
        return Task162FailureCode.CROSS_PRODUCER_BINDING_INVALID
    if len(set(binding.evidence_refs)) != len(binding.evidence_refs):
        return Task162FailureCode.CROSS_PRODUCER_BINDING_INVALID
    if binding.binding_status is not Task162BindingStatus.MATCHED:
        return Task162FailureCode.CROSS_PRODUCER_BINDING_INVALID
    if binding.physical_exchanger_case_id != case.case_authority_id:
        return Task162FailureCode.CROSS_PRODUCER_CASE_MISMATCH
    t160 = task160_result_identity_projection(task160)
    t161 = task161_result_identity_projection(task161)
    t038 = task038_result_identity_projection(task038)
    expected = (
        (binding.task160_result_hash, t160.result_hash),
        (binding.task160_result_id.lower(), t160.result_id.lower()),
        (binding.task161_result_hash, t161.result_hash),
        (binding.task161_result_id.lower(), t161.result_id.lower()),
        (binding.task038_result_hash, t038.result_hash),
        (binding.task038_result_id.lower(), t038.result_id.lower()),
    )
    if any(left != right for left, right in expected):
        return Task162FailureCode.CROSS_PRODUCER_CASE_MISMATCH
    if type(binding.compatibility_evidence) is not tuple:
        return Task162FailureCode.CROSS_PRODUCER_BINDING_INVALID
    expected_dimensions = tuple(Task162CompatibilityDimension)
    if len(binding.compatibility_evidence) != len(expected_dimensions):
        return Task162FailureCode.CROSS_PRODUCER_BINDING_INVALID
    if any(
        type(item) is not Task162CompatibilityEvidence
        or type(item.dimension) is not Task162CompatibilityDimension
        or type(item.status) is not Task162CompatibilityStatus
        or type(item.evidence_refs) is not tuple
        or not item.evidence_refs
        or any(type(ref) is not str or not ref for ref in item.evidence_refs)
        or len(set(item.evidence_refs)) != len(item.evidence_refs)
        or item.status is not Task162CompatibilityStatus.PROVEN
        or item.failure_code_or_none is not None
        for item in binding.compatibility_evidence
    ):
        return Task162FailureCode.CROSS_PRODUCER_BINDING_INVALID
    seen = tuple(item.dimension for item in binding.compatibility_evidence)
    if set(seen) != set(expected_dimensions) or len(seen) != len(expected_dimensions):
        return Task162FailureCode.CROSS_PRODUCER_BINDING_INVALID
    return None


def _case_binding(
    case: Task162CaseAuthority,
    task160: Task160Result,
) -> tuple[Task162NormalizedCaseBinding | None, Task162FailureCode | None]:
    if type(case) is not Task162CaseAuthority:
        return None, Task162FailureCode.CASE_AUTHORITY_INVALID
    if type(case.baffle_count) is not int or not 1 <= case.baffle_count <= 5:
        return None, Task162FailureCode.UNSUPPORTED_BAFFLE_COUNT
    if type(case.steady_state) is not bool:
        return None, Task162FailureCode.CASE_AUTHORITY_INVALID
    if type(case.case_authority_id) is not str or not case.case_authority_id:
        return None, Task162FailureCode.CASE_AUTHORITY_INVALID
    expected_enums = (
        (case.shell_type, Task162ShellType.TEMA_E),
        (case.overall_flow_orientation, Task162FlowOrientation.COUNTER_FLOW),
        (case.physical_sthe_tube_side_mixing, Task162TubeSideMixing.UNMIXED),
        (case.physical_sthe_shell_side_mixing_model, Task162ShellSideMixingModel.MODEL_2),
        (
            case.ambient_heat_loss_assumption,
            Task162AmbientHeatLossAssumption.NEGLIGIBLE_AMBIENT_HEAT_LOSS,
        ),
        (
            case.internal_source_sink_assumption,
            Task162InternalSourceSinkAssumption.NO_INTERNAL_THERMAL_SOURCE_SINK,
        ),
        (
            case.constant_wall_material_property,
            Task162WallPropertyAssumption.CONSTANT_WALL_MATERIAL_PROPERTIES,
        ),
        (
            case.constant_heat_transfer_coefficient,
            Task162HeatTransferCoefficientAssumption.CONSTANT_HEAT_TRANSFER_COEFFICIENT,
        ),
        (
            case.axial_heat_transfer_assumption,
            Task162AxialHeatTransferAssumption.NEGLIGIBLE_AXIAL_HEAT_TRANSFER,
        ),
        (
            case.leakage_model_assumption,
            Task162LeakageAssumption.SOURCE_MODEL_ZERO_LEAKAGE_ASSUMPTION_ADOPTED,
        ),
        (
            case.bypass_model_assumption,
            Task162BypassAssumption.SOURCE_MODEL_ZERO_BYPASS_ASSUMPTION_ADOPTED,
        ),
    )
    if (
        any(actual is not expected for actual, expected in expected_enums)
        or case.steady_state is not True
    ):
        return None, Task162FailureCode.CASE_BINDING_VALUE_MISMATCH
    if type(case.evidence_refs) is not tuple or not case.evidence_refs:
        return None, Task162FailureCode.CASE_BINDING_INCOMPLETE
    if any(type(value) is not str or not value for value in case.evidence_refs):
        return None, Task162FailureCode.CASE_AUTHORITY_INVALID
    if len(set(case.evidence_refs)) != len(case.evidence_refs):
        return None, Task162FailureCode.CASE_AUTHORITY_INVALID
    try:
        envelope = task160.envelope_authority
        if envelope.construction_family.value != "FIXED_TUBESHEET":
            return None, Task162FailureCode.CASE_BINDING_VALUE_MISMATCH
        if envelope.shell_pass_count != 1 or envelope.tube_pass_count != 1:
            return None, Task162FailureCode.CASE_BINDING_VALUE_MISMATCH
    except BaseException:
        return None, Task162FailureCode.INVALID_TASK160_RESULT
    return (
        Task162NormalizedCaseBinding(
            physical_configuration_authority="FIXED_TUBESHEET",
            shell_pass_count_authority=1,
            tube_pass_count_authority=1,
            shell_type_authority=case.shell_type,
            overall_flow_orientation_authority=case.overall_flow_orientation,
            baffle_count_authority=case.baffle_count,
            physical_sthe_tube_side_mixing_authority=case.physical_sthe_tube_side_mixing,
            physical_sthe_shell_side_mixing_model_authority=case.physical_sthe_shell_side_mixing_model,
            steady_state_authority=case.steady_state,
            ambient_heat_loss_assumption_authority=case.ambient_heat_loss_assumption,
            internal_source_sink_assumption_authority=case.internal_source_sink_assumption,
            constant_wall_material_property_authority=case.constant_wall_material_property,
            constant_heat_transfer_coefficient_authority=case.constant_heat_transfer_coefficient,
            axial_heat_transfer_assumption_authority=case.axial_heat_transfer_assumption,
            leakage_model_assumption_authority=case.leakage_model_assumption,
            bypass_model_assumption_authority=case.bypass_model_assumption,
        ),
        None,
    )


def _method_applicable(task161: Task161Result, case: Task162CaseAuthority) -> bool:
    flow = task161.flow_arrangement_catalog
    method = task161.performance_method_catalog
    return (
        flow.catalog_id == TASK162_FLOW_ARRANGEMENT_CATALOG_ID
        and flow.source_shell_type == "TEMA_E"
        and flow.source_shell_pass_count == 1
        and flow.source_tube_pass_count == 1
        and flow.overall_flow_orientation == "COUNTER_FLOW"
        and method.method_authority_id == TASK162_METHOD_AUTHORITY_ID
        and method.method_family == TASK162_METHOD_FAMILY
        and method.flow_arrangement_catalog_id == TASK162_FLOW_ARRANGEMENT_CATALOG_ID
        and method.engineering_source_id == TASK162_ENGINEERING_SOURCE_ID
        and method.relation_id == TASK162_RELATION_ID
        and case.shell_type is Task162ShellType.TEMA_E
        and case.overall_flow_orientation is Task162FlowOrientation.COUNTER_FLOW
        and case.physical_sthe_tube_side_mixing is Task162TubeSideMixing.UNMIXED
        and case.physical_sthe_shell_side_mixing_model is Task162ShellSideMixingModel.MODEL_2
        and method.supported_baffle_count_domain == "INTEGER_1_THROUGH_5"
        and tuple(method.supported_mixing_model_domain) == ("MODEL_2",)
    )


def _streams(task160: Task160Result) -> tuple[Decimal, Decimal, Decimal, Decimal] | None:
    hot = [item for item in task160.stream_records if item.thermal_role is ThermalRole.HOT]
    cold = [item for item in task160.stream_records if item.thermal_role is ThermalRole.COLD]
    if len(hot) != 1 or len(cold) != 1:
        return None
    return (
        hot[0].heat_capacity_rate_W_K,
        cold[0].heat_capacity_rate_W_K,
        hot[0].input_state.inlet_temperature_K,
        cold[0].input_state.inlet_temperature_K,
    )


def _energy_closure(
    *,
    q_method: Decimal,
    c_hot: Decimal,
    c_cold: Decimal,
    t_hot_in: Decimal,
    t_cold_in: Decimal,
) -> tuple[Task162EnergyBalanceEvidence | None, Decimal | None, Decimal | None]:
    try:
        cold_increment_nominal = decimal_divide(q_method, c_cold)
        cold_out_nominal = decimal_add(t_cold_in, cold_increment_nominal)
        hot_decrement_nominal = decimal_divide(q_method, c_hot)
        hot_out_nominal = decimal_subtract(t_hot_in, hot_decrement_nominal)
        cold_increment_interval = interval_divide(exact_interval(q_method), exact_interval(c_cold))
        hot_decrement_interval = interval_divide(exact_interval(q_method), exact_interval(c_hot))
        cold_outlet_interval = interval_add(exact_interval(t_cold_in), cold_increment_interval)
        hot_outlet_interval = interval_subtract(exact_interval(t_hot_in), hot_decrement_interval)
        q_cold_interval = interval_multiply(
            exact_interval(c_cold),
            interval_subtract(cold_outlet_interval, exact_interval(t_cold_in)),
        )
        q_hot_interval = interval_multiply(
            exact_interval(c_hot),
            interval_subtract(exact_interval(t_hot_in), hot_outlet_interval),
        )
        q_cold_nominal = decimal_multiply(c_cold, decimal_subtract(cold_out_nominal, t_cold_in))
        q_hot_nominal = decimal_multiply(c_hot, decimal_subtract(t_hot_in, hot_out_nominal))
        cold_residual_nominal = decimal_subtract(q_cold_nominal, q_method)
        hot_residual_nominal = decimal_subtract(q_hot_nominal, q_method)
        cold_residual_interval = interval_subtract(q_cold_interval, exact_interval(q_method))
        hot_residual_interval = interval_subtract(q_hot_interval, exact_interval(q_method))
        if not interval_contains(cold_outlet_interval, cold_out_nominal) or not interval_contains(
            hot_outlet_interval, hot_out_nominal
        ):
            return None, None, None
        if not interval_contains(q_cold_interval, q_method) or not interval_contains(
            q_hot_interval, q_method
        ):
            return None, None, None
        if not interval_contains(cold_residual_interval, Decimal("0")) or not interval_contains(
            hot_residual_interval, Decimal("0")
        ):
            return None, None, None
        status = (
            Task162EnergyBalanceStatus.EXACT
            if q_cold_nominal == q_method and q_hot_nominal == q_method
            else Task162EnergyBalanceStatus.DIRECTED_INTERVAL_ENCLOSED
        )
        evidence = Task162EnergyBalanceEvidence(
            policy_id=TASK162_ENERGY_BALANCE_POLICY_ID,
            q_method=q_method,
            q_cold_nominal=q_cold_nominal,
            q_hot_nominal=q_hot_nominal,
            cold_residual_nominal=cold_residual_nominal,
            hot_residual_nominal=hot_residual_nominal,
            cold_increment_interval=cold_increment_interval,
            hot_decrement_interval=hot_decrement_interval,
            cold_outlet_interval=cold_outlet_interval,
            hot_outlet_interval=hot_outlet_interval,
            q_cold_interval=q_cold_interval,
            q_hot_interval=q_hot_interval,
            cold_residual_interval=cold_residual_interval,
            hot_residual_interval=hot_residual_interval,
            status=status,
        )
        return evidence, hot_out_nominal, cold_out_nominal
    except (DecimalArithmeticError, ArithmeticError, ValueError):
        return None, None, None


def _make_applicability() -> Task162Applicability:
    names = (
        "TASK160_ACCEPTED",
        "TASK161_ACCEPTED",
        "TASK038_ACCEPTED",
        "SAME_CASE_BINDING_MATCHED",
        "CASE_BINDING_COMPLETE",
        "SOURCE_METHOD_APPLICABLE",
        "NUMERICAL_DOMAIN_VALID",
        "ENERGY_BALANCE_CLOSED",
        "TERMINAL_CLOSURE_POSITIVE",
    )
    return Task162Applicability(status="APPLICABLE", checks=tuple((name, "PASS") for name in names))


def _make_completeness() -> Task162Completeness:
    fields = (
        "ntu",
        "p_source",
        "epsilon",
        "q_max",
        "q_method",
        "hot_outlet_temperature",
        "cold_outlet_temperature",
        "q_hot",
        "q_cold",
        "energy_balance_evidence",
        "terminal_closure_evidence",
        "applicability",
        "provenance",
    )
    return Task162Completeness(status="COMPLETE", required_fields=fields)


def _success(
    request: Task162Request,
    request_hash_value: str,
    task160: Task160Result,
    task161: Task161Result,
    task038: Task038SuccessResult,
    case: Task162CaseAuthority,
    binding: Task162CrossProducerBindingAuthority,
    normalized_case: Task162NormalizedCaseBinding,
) -> Task162ValidationResult:
    streams = _streams(task160)
    if streams is None:
        return _typed_blocked(
            request_hash_value,
            (
                _code_blocker(
                    Task162FailureCode.INVALID_TASK160_RESULT,
                    Task162FailureStage.NUMERICAL_EVALUATION,
                ),
            ),
            stage=Task162FailureStage.NUMERICAL_EVALUATION,
            task160_id=_task160_id_or_none(task160),
        )
    c_hot, c_cold, t_hot_in, t_cold_in = streams
    if type(t_hot_in) is not Decimal or type(t_cold_in) is not Decimal or t_hot_in <= t_cold_in:
        return _typed_blocked(
            request_hash_value,
            (
                _code_blocker(
                    Task162FailureCode.INVALID_INLET_TEMPERATURE_ORDER,
                    Task162FailureStage.NUMERICAL_EVALUATION,
                ),
            ),
            stage=Task162FailureStage.NUMERICAL_EVALUATION,
            task160_id=_task160_id_or_none(task160),
        )
    ua = task038.modeled_ua_w_k
    c_min = task161.capacity_foundation.c_min
    r_source = task161.capacity_foundation.r_source
    if type(ua) is not Decimal or not ua.is_finite() or ua < 0:
        return _typed_blocked(
            request_hash_value,
            (
                _code_blocker(
                    Task162FailureCode.INVALID_UA, Task162FailureStage.NUMERICAL_EVALUATION
                ),
            ),
            stage=Task162FailureStage.NUMERICAL_EVALUATION,
            task160_id=_task160_id_or_none(task160),
        )
    if type(c_min) is not Decimal or not c_min.is_finite() or c_min <= 0:
        return _typed_blocked(
            request_hash_value,
            (
                _code_blocker(
                    Task162FailureCode.INVALID_C_MIN, Task162FailureStage.NUMERICAL_EVALUATION
                ),
            ),
            stage=Task162FailureStage.NUMERICAL_EVALUATION,
            task160_id=_task160_id_or_none(task160),
        )
    if type(r_source) is not Decimal or not r_source.is_finite() or r_source <= 0:
        return _typed_blocked(
            request_hash_value,
            (
                _code_blocker(
                    Task162FailureCode.INVALID_R_SOURCE, Task162FailureStage.NUMERICAL_EVALUATION
                ),
            ),
            stage=Task162FailureStage.NUMERICAL_EVALUATION,
            task160_id=_task160_id_or_none(task160),
        )
    try:
        ntu = decimal_divide(ua, c_min)
        p_source = table7_relation(ntu, r_source, case.baffle_count)
        if not p_source.is_finite():
            raise DecimalArithmeticError("nonfinite P")
        epsilon = decimal_multiply(p_source, decimal_divide(c_cold, c_min))
        delta_t_in = decimal_subtract(t_hot_in, t_cold_in)
        q_max = decimal_multiply(c_min, delta_t_in)
        q_method = decimal_multiply(decimal_multiply(p_source, c_cold), delta_t_in)
        if not all(value.is_finite() for value in (ntu, p_source, epsilon, q_max, q_method)):
            raise DecimalArithmeticError("nonfinite performance output")
    except (DecimalArithmeticError, ArithmeticError, ValueError):
        return _typed_blocked(
            request_hash_value,
            (
                _code_blocker(
                    Task162FailureCode.PERFORMANCE_RELATION_NONFINITE,
                    Task162FailureStage.NUMERICAL_EVALUATION,
                ),
            ),
            stage=Task162FailureStage.NUMERICAL_EVALUATION,
            task160_id=_task160_id_or_none(task160),
        )
    energy, t_hot_out, t_cold_out = _energy_closure(
        q_method=q_method,
        c_hot=c_hot,
        c_cold=c_cold,
        t_hot_in=t_hot_in,
        t_cold_in=t_cold_in,
    )
    if energy is None or t_hot_out is None or t_cold_out is None:
        return _typed_blocked(
            request_hash_value,
            (
                _code_blocker(
                    Task162FailureCode.ENERGY_BALANCE_CLOSURE_FAILED,
                    Task162FailureStage.ENERGY_BALANCE,
                ),
            ),
            stage=Task162FailureStage.ENERGY_BALANCE,
            task160_id=_task160_id_or_none(task160),
        )
    try:
        delta_one = decimal_subtract(t_hot_in, t_cold_out)
        delta_two = decimal_subtract(t_hot_out, t_cold_in)
    except (DecimalArithmeticError, ArithmeticError):
        return _typed_blocked(
            request_hash_value,
            (
                _code_blocker(
                    Task162FailureCode.TERMINAL_TEMPERATURE_CLOSURE_FAILED,
                    Task162FailureStage.TERMINAL_CLOSURE,
                ),
            ),
            stage=Task162FailureStage.TERMINAL_CLOSURE,
            task160_id=_task160_id_or_none(task160),
        )
    if delta_one <= 0 or delta_two <= 0:
        return _typed_blocked(
            request_hash_value,
            (
                _code_blocker(
                    Task162FailureCode.TERMINAL_TEMPERATURE_CLOSURE_FAILED,
                    Task162FailureStage.TERMINAL_CLOSURE,
                ),
            ),
            stage=Task162FailureStage.TERMINAL_CLOSURE,
            task160_id=_task160_id_or_none(task160),
        )
    terminal = Task162TerminalClosureEvidence(delta_one, delta_two)
    method = task161.performance_method_catalog
    selected_method = Task162SelectedMethodIdentity(
        method_authority_id=method.method_authority_id,
        method_family=method.method_family,
        flow_arrangement_catalog_id=method.flow_arrangement_catalog_id,
        engineering_source_id=method.engineering_source_id,
        relation_id=method.relation_id,
        selected_baffle_relation=f"P_{case.baffle_count}",
        baffle_count=case.baffle_count,
    )
    foundation = Task162NumericalFoundation(
        ua_w_k=ua,
        c_min_w_k=c_min,
        c_dot_hot_w_k=c_hot,
        c_dot_cold_w_k=c_cold,
        t_hot_in_k=t_hot_in,
        t_cold_in_k=t_cold_in,
        delta_t_in_k=decimal_subtract(t_hot_in, t_cold_in),
        q_max_w=q_max,
    )
    applicability = _make_applicability()
    completeness = _make_completeness()
    _, semantic = build_success_provenance(
        request_hash=request_hash_value,
        task160_result=task160,
        task161_result=task161,
        task038_result=task038,
        method_catalog=method,
        binding_authority=binding,
        case_authority=case,
        selected_baffle_relation=f"P_{case.baffle_count}",
        result_hash="0" * 64,
        result_id=result_id("0" * 64),
    )
    pre = _build_pre(
        request=request,
        request_hash_value=request_hash_value,
        task160=task160,
        task161=task161,
        task038=task038,
        binding=binding,
        normalized_case=normalized_case,
        foundation=foundation,
        selected_method=selected_method,
        ntu=ntu,
        r_source=r_source,
        p_source=p_source,
        epsilon=epsilon,
        q_max=q_max,
        q_method=q_method,
        t_hot_out=t_hot_out,
        t_cold_out=t_cold_out,
        q_hot=energy.q_hot_nominal,
        q_cold=energy.q_cold_nominal,
        energy=energy,
        terminal=terminal,
        applicability=applicability,
        completeness=completeness,
        semantic=semantic,
    )
    final_hash = success_hash_from_inputs(pre)
    final_id = result_id(final_hash)
    provenance, replayed_semantic = build_success_provenance(
        request_hash=request_hash_value,
        task160_result=task160,
        task161_result=task161,
        task038_result=task038,
        method_catalog=method,
        binding_authority=binding,
        case_authority=case,
        selected_baffle_relation=f"P_{case.baffle_count}",
        result_hash=final_hash,
        result_id=final_id,
    )
    if replayed_semantic != semantic or success_hash_from_inputs(pre) != final_hash:
        return _typed_blocked(
            request_hash_value,
            (_code_blocker(Task162FailureCode.PROVENANCE_INVALID, Task162FailureStage.PROVENANCE),),
            stage=Task162FailureStage.PROVENANCE,
            task160_id=_task160_id_or_none(task160),
        )
    result = Task162Result(
        schema_version=TASK162_SCHEMA_VERSION,
        task162_version=TASK162_VERSION,
        implementation_software_version=TASK162_IMPLEMENTATION_SOFTWARE_VERSION,
        source_definition_id=TASK162_SOURCE_DEFINITION_ID,
        request_hash=request_hash_value,
        task160_evidence=task160_result_identity_projection(task160),
        task161_evidence=task161_result_identity_projection(task161),
        task038_evidence=task038_result_identity_projection(task038),
        cross_producer_binding_evidence=binding,
        case_binding_evidence=normalized_case,
        numerical_foundation=foundation,
        selected_method_identity=selected_method,
        selected_baffle_relation=f"P_{case.baffle_count}",
        ntu=ntu,
        r_source=r_source,
        p_source=p_source,
        epsilon=epsilon,
        q_max=q_max,
        q_method=q_method,
        hot_outlet_temperature=t_hot_out,
        cold_outlet_temperature=t_cold_out,
        q_hot=energy.q_hot_nominal,
        q_cold=energy.q_cold_nominal,
        energy_balance_evidence=energy,
        terminal_closure_evidence=terminal,
        applicability=applicability,
        completeness=completeness,
        warnings=(),
        blockers=(),
        provenance_semantic_inputs=semantic,
        provenance=provenance,
        result_hash=final_hash,
        result_id=final_id,
    )
    if (
        result.result_id != result_id(final_hash)
        or result.provenance.provenance_hash != result.provenance.graph.compute_hash()
    ):
        return _typed_blocked(
            request_hash_value,
            (
                _code_blocker(
                    Task162FailureCode.IDENTITY_REPLAY_FAILED, Task162FailureStage.IDENTITY
                ),
            ),
            stage=Task162FailureStage.IDENTITY,
            task160_id=_task160_id_or_none(task160),
        )
    return Task162ValidationResult(status=Task162ValidationStatus.VALID, valid=result)


def _build_pre(
    *,
    request: Task162Request,
    request_hash_value: str,
    task160: Task160Result,
    task161: Task161Result,
    task038: Task038SuccessResult,
    binding: Task162CrossProducerBindingAuthority,
    normalized_case: Task162NormalizedCaseBinding,
    foundation: Task162NumericalFoundation,
    selected_method: Task162SelectedMethodIdentity,
    ntu: Decimal,
    r_source: Decimal,
    p_source: Decimal,
    epsilon: Decimal,
    q_max: Decimal,
    q_method: Decimal,
    t_hot_out: Decimal,
    t_cold_out: Decimal,
    q_hot: Decimal,
    q_cold: Decimal,
    energy: Task162EnergyBalanceEvidence,
    terminal: Task162TerminalClosureEvidence,
    applicability: Task162Applicability,
    completeness: Task162Completeness,
    semantic: Task162ProvenanceSemanticInputs,
) -> Any:
    from .models import Task162PreResultIdentityInputs

    return Task162PreResultIdentityInputs(
        schema_version=TASK162_SCHEMA_VERSION,
        task162_version=TASK162_VERSION,
        implementation_software_version=TASK162_IMPLEMENTATION_SOFTWARE_VERSION,
        source_definition_id=TASK162_SOURCE_DEFINITION_ID,
        request_hash=request_hash_value,
        task160_evidence=task160_result_identity_projection(task160),
        task161_evidence=task161_result_identity_projection(task161),
        task038_evidence=task038_result_identity_projection(task038),
        cross_producer_binding_evidence=binding,
        case_binding_evidence=normalized_case,
        numerical_foundation=foundation,
        selected_method_identity=selected_method,
        selected_baffle_relation=selected_method.selected_baffle_relation,
        ntu=ntu,
        r_source=r_source,
        p_source=p_source,
        epsilon=epsilon,
        q_max=q_max,
        q_method=q_method,
        hot_outlet_temperature=t_hot_out,
        cold_outlet_temperature=t_cold_out,
        q_hot=q_hot,
        q_cold=q_cold,
        energy_balance_evidence=energy,
        terminal_closure_evidence=terminal,
        applicability=applicability,
        completeness=completeness,
        warnings_normalized=(),
        blockers_normalized=(),
        provenance_semantic_inputs=semantic,
    )


def validate_request(raw: object) -> Task162ValidationResult:
    """Admit, validate, evaluate, and identify one TASK162 request."""

    raw_outcome = project_raw_request_with_diagnostics(raw)
    projection = raw_outcome.projection
    unsupported = raw_outcome.unsupported_object_present
    projection_hash = raw_request_projection_hash(projection)
    raw_blockers: list[Task162Blocker] = []
    if unsupported:
        raw_blockers.append(
            _code_blocker(
                Task162FailureCode.UNSUPPORTED_RAW_VALUE, Task162FailureStage.RAW_BOUNDARY
            )
        )
    if type(raw) is not dict:
        raw_blockers.append(
            _code_blocker(Task162FailureCode.INVALID_REQUEST_TYPE, Task162FailureStage.RAW_BOUNDARY)
        )
        return _raw_blocked(projection, projection_hash, tuple(raw_blockers))
    if any(type(key) is not str for key in raw):
        raw_blockers.append(
            _code_blocker(
                Task162FailureCode.INVALID_REQUEST_SCHEMA, Task162FailureStage.RAW_BOUNDARY
            )
        )
        return _raw_blocked(projection, projection_hash, tuple(raw_blockers))
    keys = frozenset(raw)
    if keys != REQUIRED_RAW_FIELDS:
        raw_blockers.append(
            _code_blocker(
                Task162FailureCode.INVALID_REQUEST_SCHEMA, Task162FailureStage.RAW_BOUNDARY
            )
        )
    schema_version = raw.get("schema_version")
    task162_version = raw.get("task162_version")
    if (
        type(schema_version) is not str
        or type(task162_version) is not str
        or schema_version != TASK162_SCHEMA_VERSION
        or task162_version != TASK162_VERSION
    ):
        raw_blockers.append(
            _code_blocker(
                Task162FailureCode.UNSUPPORTED_TASK162_VERSION, Task162FailureStage.RAW_BOUNDARY
            )
        )
    source_definition_id = raw.get("source_definition_id")
    if (
        type(source_definition_id) is not str
        or source_definition_id != TASK162_SOURCE_DEFINITION_ID
    ):
        raw_blockers.append(
            _code_blocker(
                Task162FailureCode.SOURCE_DEFINITION_ID_MISMATCH, Task162FailureStage.RAW_BOUNDARY
            )
        )
    if raw_blockers:
        return _raw_blocked(projection, projection_hash, tuple(raw_blockers))
    try:
        metadata = _metadata(raw["request_metadata"])
        request = Task162Request(
            schema_version=raw["schema_version"],
            task162_version=raw["task162_version"],
            source_definition_id=raw["source_definition_id"],
            task160_result=raw["task160_result"],
            task161_result=raw["task161_result"],
            task038_result=raw["task038_result"],
            cross_producer_binding_authority=raw["cross_producer_binding_authority"],
            case_authority=raw["case_authority"],
            request_metadata=metadata,
        )
    except (UnicodeError, ValueError, TypeError):
        return _raw_blocked(
            projection,
            projection_hash,
            (
                _code_blocker(
                    Task162FailureCode.INVALID_REQUEST_SCHEMA, Task162FailureStage.RAW_BOUNDARY
                ),
            ),
        )
    try:
        request_hash_value = request_hash(request)
    except BaseException:
        # The raw projection has already admitted the object graph.  A
        # malformed typed authority must therefore reach typed validation;
        # its stable projection hash is the deterministic fallback request
        # identity for the blocked branch.
        request_hash_value = projection_hash
    exact_types = (
        (request.task160_result, Task160Result, Task162FailureCode.INVALID_TASK160_RESULT),
        (request.task161_result, Task161Result, Task162FailureCode.INVALID_TASK161_RESULT),
        (request.task038_result, Task038SuccessResult, Task162FailureCode.INVALID_TASK038_RESULT),
    )
    if any(type(value) is not expected for value, expected, _ in exact_types):
        code = next(code for value, expected, code in exact_types if type(value) is not expected)
        return _typed_blocked(
            request_hash_value,
            (_code_blocker(code, Task162FailureStage.TYPED_VALIDATION),),
            stage=Task162FailureStage.TYPED_VALIDATION,
            task160_id=None,
        )
    task160 = request.task160_result
    task161 = request.task161_result
    task038 = request.task038_result
    assert isinstance(task160, Task160Result)
    assert isinstance(task161, Task161Result)
    assert isinstance(task038, Task038SuccessResult)
    replay_code = _replay_task160(task160)
    if replay_code is not None:
        return _typed_blocked(
            request_hash_value,
            (_code_blocker(replay_code, Task162FailureStage.TASK160_REPLAY),),
            stage=Task162FailureStage.TASK160_REPLAY,
            task160_id=_task160_id_or_none(task160),
        )
    replay_code = _replay_task161(task161)
    if replay_code is not None:
        return _typed_blocked(
            request_hash_value,
            (_code_blocker(replay_code, Task162FailureStage.TASK161_REPLAY),),
            stage=Task162FailureStage.TASK161_REPLAY,
            task160_id=_task160_id_or_none(task160),
        )
    replay_code = _replay_task038(task038)
    if replay_code is not None:
        return _typed_blocked(
            request_hash_value,
            (_code_blocker(replay_code, Task162FailureStage.TASK038_REPLAY),),
            stage=Task162FailureStage.TASK038_REPLAY,
            task160_id=_task160_id_or_none(task160),
        )
    if not _prove_task161_task160(task160, task161):
        return _typed_blocked(
            request_hash_value,
            (
                _code_blocker(
                    Task162FailureCode.TASK161_TASK160_IDENTITY_MISMATCH,
                    Task162FailureStage.CROSS_PRODUCER_BINDING,
                ),
            ),
            stage=Task162FailureStage.CROSS_PRODUCER_BINDING,
            task160_id=_task160_id_or_none(task160),
        )
    binding_code = _prove_binding(
        request.cross_producer_binding_authority,
        task160,
        task161,
        task038,
        request.case_authority,
    )
    if binding_code is not None:
        return _typed_blocked(
            request_hash_value,
            (_code_blocker(binding_code, Task162FailureStage.CROSS_PRODUCER_BINDING),),
            stage=Task162FailureStage.CROSS_PRODUCER_BINDING,
            task160_id=_task160_id_or_none(task160),
        )
    normalized_case, case_code = _case_binding(request.case_authority, task160)
    if case_code is not None or normalized_case is None:
        return _typed_blocked(
            request_hash_value,
            (
                _code_blocker(
                    case_code or Task162FailureCode.CASE_BINDING_INCOMPLETE,
                    Task162FailureStage.CASE_BINDING,
                ),
            ),
            stage=Task162FailureStage.CASE_BINDING,
            task160_id=_task160_id_or_none(task160),
        )
    if not _method_applicable(task161, request.case_authority):
        return _typed_blocked(
            request_hash_value,
            (
                _code_blocker(
                    Task162FailureCode.CATALOG_AUTHORITY_INVALID, Task162FailureStage.APPLICABILITY
                ),
            ),
            stage=Task162FailureStage.APPLICABILITY,
            task160_id=_task160_id_or_none(task160),
        )
    return _success(
        request,
        request_hash_value,
        task160,
        task161,
        task038,
        request.case_authority,
        request.cross_producer_binding_authority,
        normalized_case,
    )


__all__ = ["validate_request"]
