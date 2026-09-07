"""TASK162 canonical framing, identity projections, and UUID construction."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid5

from hexagent.exchangers.shell_tube.flow_arrangement_performance_method_authority.models import (
    Task161Result,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.models import (
    Task038SuccessResult,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.models import Task160Result
from hexagent.exchangers.shell_tube.tube_side.canonical import (
    KIND_BOOL_FALSE,
    KIND_BOOL_TRUE,
    KIND_DECIMAL,
    KIND_ENUM,
    KIND_INT,
    KIND_NONE,
    KIND_RECORD,
    KIND_STRING,
    KIND_TUPLE,
    frame_record,
    frame_tuple,
    frame_value,
    sha256_hex_from_framed_bytes,
)

from .models import (
    IntervalDecimal,
    Task038ResultIdentityProjection,
    Task160ResultIdentityProjection,
    Task161ResultIdentityProjection,
    Task162Applicability,
    Task162Blocker,
    Task162CaseAuthority,
    Task162CompatibilityDimension,
    Task162CompatibilityEvidence,
    Task162Completeness,
    Task162CrossProducerBindingAuthority,
    Task162EnergyBalanceEvidence,
    Task162NormalizedCaseBinding,
    Task162NumericalFoundation,
    Task162PreResultIdentityInputs,
    Task162ProvenanceSemanticInputs,
    Task162RawBoundaryBlockedResult,
    Task162RawProjectionNode,
    Task162RawRequestProjection,
    Task162Request,
    Task162SelectedMethodIdentity,
    Task162TerminalClosureEvidence,
    Task162TypedBlockedResult,
    Task162ValidationResult,
    Task162Warning,
)

TASK162_REQUEST_HASH_DOMAIN = "TASK162_REQUEST_HASH_V1"
TASK162_SUCCESS_HASH_DOMAIN = "TASK162_SUCCESS_RESULT_HASH_V1"
TASK162_TYPED_BLOCKED_HASH_DOMAIN = "TASK162_TYPED_BLOCKED_RESULT_HASH_V1"
TASK162_RAW_BLOCKED_HASH_DOMAIN = "TASK162_RAW_BOUNDARY_BLOCKED_RESULT_HASH_V1"
TASK162_RAW_PROJECTION_DOMAIN = "TASK162_RAW_REQUEST_PROJECTION_V1"
TASK162_RAW_PROJECTION_NODE_DOMAIN = "TASK162_RAW_PROJECTION_NODE_V1"

TASK162_SUCCESS_ID_PREFIX = "task162-result-v1::"
TASK162_TYPED_BLOCKED_ID_PREFIX = "task162-typed-blocked-v1::"
TASK162_RAW_BLOCKED_ID_PREFIX = "task162-raw-boundary-blocked-v1::"

TASK162_RESULT_ID_NAMESPACE = UUID("a1620000-0000-5000-8000-000000000162")
TASK162_PROVENANCE_NAMESPACE = UUID("a1620000-0000-5001-8000-000000000162")

TASK162_COMPATIBILITY_DIMENSION_ORDER: tuple[Task162CompatibilityDimension, ...] = (
    Task162CompatibilityDimension.RESULT_IDENTITY_BINDING,
    Task162CompatibilityDimension.PHYSICAL_CASE_BINDING,
    Task162CompatibilityDimension.TUBE_SIDE_SERVICE_BINDING,
    Task162CompatibilityDimension.SHELL_SIDE_SERVICE_BINDING,
)

TASK162_REQUEST_FIELD_ORDER: tuple[str, ...] = (
    "schema_version",
    "task162_version",
    "source_definition_id",
    "task160_result",
    "task161_result",
    "task038_result",
    "cross_producer_binding_authority",
    "case_authority",
    "request_metadata",
)

TASK162_SUCCESS_PREIMAGE_FIELD_ORDER: tuple[str, ...] = (
    "schema_version",
    "task162_version",
    "implementation_software_version",
    "source_definition_id",
    "request_hash",
    "task160_evidence",
    "task161_evidence",
    "task038_evidence",
    "cross_producer_binding_evidence",
    "case_binding_evidence",
    "numerical_foundation",
    "selected_method_identity",
    "selected_baffle_relation",
    "ntu",
    "r_source",
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
    "completeness",
    "warnings_normalized",
    "blockers_normalized",
    "provenance_semantic_inputs",
)


def _string(value: str) -> bytes:
    if type(value) is not str:
        raise TypeError("canonical string requires exact str")
    return value.encode("utf-8")


def _enum(value: Enum | str) -> bytes:
    token = value.value if isinstance(value, Enum) else value
    return _string(token)


def _decimal(value: Decimal) -> bytes:
    if type(value) is not Decimal or not value.is_finite():
        raise ValueError("canonical Decimal must be finite")
    return str(value).encode("ascii")


def _integer(value: int) -> bytes:
    if type(value) is not int:
        raise TypeError("canonical integer requires exact int")
    return str(value).encode("ascii")


def _result_id_text(value: object) -> str:
    if type(value) is UUID:
        return str(value).lower()
    if type(value) is str:
        return value.lower()
    return "INVALID_RESULT_ID"


def _boolean(value: bool) -> tuple[bytes, bytes]:
    if type(value) is not bool:
        raise TypeError("canonical boolean requires exact bool")
    return KIND_BOOL_TRUE if value else KIND_BOOL_FALSE, b""


def _none_or_string(value: str | None) -> tuple[bytes, bytes]:
    if value is None:
        return KIND_NONE, b""
    return KIND_STRING, _string(value)


def _field(name: str, kind: bytes, payload: bytes) -> tuple[str, bytes, bytes]:
    return name, kind, payload


def _record(namespace: str, fields: Sequence[tuple[str, bytes, bytes]]) -> bytes:
    return frame_record(namespace, fields)


def _nested(name: str, value: bytes) -> tuple[str, bytes, bytes]:
    return _field(name, KIND_RECORD, value)


def _tuple_values(values: Iterable[bytes]) -> bytes:
    return frame_tuple(tuple(values))


def _tuple_strings(values: Iterable[str]) -> bytes:
    return _tuple_values(frame_value(KIND_STRING, _string(value)) for value in values)


def _tuple_records(values: Iterable[bytes]) -> bytes:
    return _tuple_values(frame_value(KIND_RECORD, value) for value in values)


def _tuple_pairs(values: Iterable[tuple[str, str]]) -> bytes:
    return _tuple_records(
        _record(
            "TASK162_STRING_PAIR_V1",
            (
                _field("key", KIND_STRING, _string(key)),
                _field("value", KIND_STRING, _string(value)),
            ),
        )
        for key, value in values
    )


def _warnings_bytes(values: Iterable[Task162Warning]) -> bytes:
    return _tuple_records(
        _record("TASK162_WARNING_V1", (_field("code", KIND_STRING, _string(value.code)),))
        for value in values
    )


def _blockers_bytes(values: Iterable[Task162Blocker]) -> bytes:
    return _tuple_records(
        _record(
            "TASK162_BLOCKER_V1",
            (
                _field("code", KIND_STRING, _string(value.code)),
                _field("stage", KIND_ENUM, _enum(value.stage)),
                _field("evidence_refs", KIND_TUPLE, _tuple_strings(value.evidence_refs)),
            ),
        )
        for value in values
    )


def task160_result_identity_projection(result: Task160Result) -> Task160ResultIdentityProjection:
    return Task160ResultIdentityProjection(
        schema_version=result.schema_version,
        task160_version=result.task160_version,
        request_hash=result.request_hash,
        result_hash=result.result_hash,
        result_id=_result_id_text(result.result_id),
        provenance_hash=result.provenance.provenance_hash,
    )


def task161_result_identity_projection(result: Task161Result) -> Task161ResultIdentityProjection:
    return Task161ResultIdentityProjection(
        schema_version=result.schema_version,
        task161_version=result.task161_version,
        source_definition_id=result.source_definition_id,
        request_hash=result.request_hash,
        result_hash=result.result_hash,
        result_id=_result_id_text(result.result_id),
        provenance_hash=result.provenance.provenance_hash,
    )


def task038_result_identity_projection(
    result: Task038SuccessResult,
) -> Task038ResultIdentityProjection:
    return Task038ResultIdentityProjection(
        schema_version=result.schema_version,
        task038_version=result.task038_version,
        profile_id=result.profile_id,
        request_hash=result.request_hash,
        result_hash=result.result_hash,
        result_id=_result_id_text(result.result_id),
        provenance_hash=result.provenance.provenance_hash,
    )


def _task160_evidence_bytes(value: Task160ResultIdentityProjection) -> bytes:
    return _record(
        "TASK162_TASK160_RESULT_EVIDENCE_V1",
        (
            _field("schema_version", KIND_STRING, _string(value.schema_version)),
            _field("task160_version", KIND_STRING, _string(value.task160_version)),
            _field("request_hash", KIND_STRING, _string(value.request_hash)),
            _field("result_hash", KIND_STRING, _string(value.result_hash)),
            _field("result_id", KIND_STRING, _string(value.result_id)),
            _field("provenance_hash", KIND_STRING, _string(value.provenance_hash)),
        ),
    )


def _task161_evidence_bytes(value: Task161ResultIdentityProjection) -> bytes:
    return _record(
        "TASK162_TASK161_RESULT_EVIDENCE_V1",
        (
            _field("schema_version", KIND_STRING, _string(value.schema_version)),
            _field("task161_version", KIND_STRING, _string(value.task161_version)),
            _field("source_definition_id", KIND_STRING, _string(value.source_definition_id)),
            _field("request_hash", KIND_STRING, _string(value.request_hash)),
            _field("result_hash", KIND_STRING, _string(value.result_hash)),
            _field("result_id", KIND_STRING, _string(value.result_id)),
            _field("provenance_hash", KIND_STRING, _string(value.provenance_hash)),
        ),
    )


def _task038_evidence_bytes(value: Task038ResultIdentityProjection) -> bytes:
    return _record(
        "TASK162_TASK038_RESULT_EVIDENCE_V1",
        (
            _field("schema_version", KIND_STRING, _string(value.schema_version)),
            _field("task038_version", KIND_STRING, _string(value.task038_version)),
            _field("profile_id", KIND_STRING, _string(value.profile_id)),
            _field("request_hash", KIND_STRING, _string(value.request_hash)),
            _field("result_hash", KIND_STRING, _string(value.result_hash)),
            _field("result_id", KIND_STRING, _string(value.result_id)),
            _field("provenance_hash", KIND_STRING, _string(value.provenance_hash)),
        ),
    )


def compatibility_evidence_bytes(value: Task162CompatibilityEvidence) -> bytes:
    return _record(
        "TASK162_COMPATIBILITY_EVIDENCE_V1",
        (
            _field("dimension", KIND_ENUM, _enum(value.dimension)),
            _field("status", KIND_ENUM, _enum(value.status)),
            _field(
                "evidence_refs",
                KIND_TUPLE,
                _tuple_strings(sorted(value.evidence_refs, key=lambda item: item.encode("utf-8"))),
            ),
            _field("failure_code_or_none", *_none_or_string(value.failure_code_or_none)),
        ),
    )


def cross_producer_binding_bytes(value: Task162CrossProducerBindingAuthority) -> bytes:
    dimension_order = {
        dimension: index for index, dimension in enumerate(TASK162_COMPATIBILITY_DIMENSION_ORDER)
    }
    ordered_compatibility = tuple(
        sorted(value.compatibility_evidence, key=lambda item: dimension_order[item.dimension])
    )
    return _record(
        "TASK162_CROSS_PRODUCER_BINDING_V1",
        (
            _field("binding_authority_id", KIND_STRING, _string(value.binding_authority_id)),
            _field("task160_result_hash", KIND_STRING, _string(value.task160_result_hash)),
            _field("task160_result_id", KIND_STRING, _string(value.task160_result_id)),
            _field("task161_result_hash", KIND_STRING, _string(value.task161_result_hash)),
            _field("task161_result_id", KIND_STRING, _string(value.task161_result_id)),
            _field("task038_result_hash", KIND_STRING, _string(value.task038_result_hash)),
            _field("task038_result_id", KIND_STRING, _string(value.task038_result_id)),
            _field(
                "physical_exchanger_case_id",
                KIND_STRING,
                _string(value.physical_exchanger_case_id),
            ),
            _field("binding_status", KIND_ENUM, _enum(value.binding_status)),
            _field(
                "evidence_refs",
                KIND_TUPLE,
                _tuple_strings(sorted(value.evidence_refs, key=lambda item: item.encode("utf-8"))),
            ),
            _field(
                "compatibility_evidence",
                KIND_TUPLE,
                _tuple_records(
                    compatibility_evidence_bytes(item) for item in ordered_compatibility
                ),
            ),
        ),
    )


def case_authority_bytes(value: Task162CaseAuthority) -> bytes:
    return _record(
        "TASK162_CASE_AUTHORITY_V1",
        (
            _field("case_authority_id", KIND_STRING, _string(value.case_authority_id)),
            _field("shell_type", KIND_ENUM, _enum(value.shell_type)),
            _field("overall_flow_orientation", KIND_ENUM, _enum(value.overall_flow_orientation)),
            _field("baffle_count", KIND_INT, _integer(value.baffle_count)),
            _field(
                "physical_sthe_tube_side_mixing",
                KIND_ENUM,
                _enum(value.physical_sthe_tube_side_mixing),
            ),
            _field(
                "physical_sthe_shell_side_mixing_model",
                KIND_ENUM,
                _enum(value.physical_sthe_shell_side_mixing_model),
            ),
            _field("steady_state", *_boolean(value.steady_state)),
            _field(
                "ambient_heat_loss_assumption",
                KIND_ENUM,
                _enum(value.ambient_heat_loss_assumption),
            ),
            _field(
                "internal_source_sink_assumption",
                KIND_ENUM,
                _enum(value.internal_source_sink_assumption),
            ),
            _field(
                "constant_wall_material_property",
                KIND_ENUM,
                _enum(value.constant_wall_material_property),
            ),
            _field(
                "constant_heat_transfer_coefficient",
                KIND_ENUM,
                _enum(value.constant_heat_transfer_coefficient),
            ),
            _field(
                "axial_heat_transfer_assumption",
                KIND_ENUM,
                _enum(value.axial_heat_transfer_assumption),
            ),
            _field(
                "leakage_model_assumption",
                KIND_ENUM,
                _enum(value.leakage_model_assumption),
            ),
            _field("bypass_model_assumption", KIND_ENUM, _enum(value.bypass_model_assumption)),
            _field(
                "evidence_refs",
                KIND_TUPLE,
                _tuple_strings(sorted(value.evidence_refs, key=lambda item: item.encode("utf-8"))),
            ),
        ),
    )


def normalized_case_binding_bytes(value: Task162NormalizedCaseBinding) -> bytes:
    fields = (
        _field(
            "physical_configuration_authority",
            KIND_STRING,
            _string(value.physical_configuration_authority),
        ),
        _field("shell_pass_count_authority", KIND_INT, _integer(value.shell_pass_count_authority)),
        _field("tube_pass_count_authority", KIND_INT, _integer(value.tube_pass_count_authority)),
        _field("shell_type_authority", KIND_ENUM, _enum(value.shell_type_authority)),
        _field(
            "overall_flow_orientation_authority",
            KIND_ENUM,
            _enum(value.overall_flow_orientation_authority),
        ),
        _field("baffle_count_authority", KIND_INT, _integer(value.baffle_count_authority)),
        _field(
            "physical_sthe_tube_side_mixing_authority",
            KIND_ENUM,
            _enum(value.physical_sthe_tube_side_mixing_authority),
        ),
        _field(
            "physical_sthe_shell_side_mixing_model_authority",
            KIND_ENUM,
            _enum(value.physical_sthe_shell_side_mixing_model_authority),
        ),
        _field("steady_state_authority", *_boolean(value.steady_state_authority)),
        _field(
            "ambient_heat_loss_assumption_authority",
            KIND_ENUM,
            _enum(value.ambient_heat_loss_assumption_authority),
        ),
        _field(
            "internal_source_sink_assumption_authority",
            KIND_ENUM,
            _enum(value.internal_source_sink_assumption_authority),
        ),
        _field(
            "constant_wall_material_property_authority",
            KIND_ENUM,
            _enum(value.constant_wall_material_property_authority),
        ),
        _field(
            "constant_heat_transfer_coefficient_authority",
            KIND_ENUM,
            _enum(value.constant_heat_transfer_coefficient_authority),
        ),
        _field(
            "axial_heat_transfer_assumption_authority",
            KIND_ENUM,
            _enum(value.axial_heat_transfer_assumption_authority),
        ),
        _field(
            "leakage_model_assumption_authority",
            KIND_ENUM,
            _enum(value.leakage_model_assumption_authority),
        ),
        _field(
            "bypass_model_assumption_authority",
            KIND_ENUM,
            _enum(value.bypass_model_assumption_authority),
        ),
    )
    return _record("TASK162_NORMALIZED_CASE_BINDING_V1", fields)


def numerical_foundation_bytes(value: Task162NumericalFoundation) -> bytes:
    return _record(
        "TASK162_NUMERICAL_FOUNDATION_V1",
        tuple(
            _field(name, KIND_DECIMAL, _decimal(getattr(value, name)))
            for name in (
                "ua_w_k",
                "c_min_w_k",
                "c_dot_hot_w_k",
                "c_dot_cold_w_k",
                "t_hot_in_k",
                "t_cold_in_k",
                "delta_t_in_k",
                "q_max_w",
            )
        ),
    )


def selected_method_identity_bytes(value: Task162SelectedMethodIdentity) -> bytes:
    return _record(
        "TASK162_SELECTED_METHOD_IDENTITY_V1",
        (
            _field("method_authority_id", KIND_STRING, _string(value.method_authority_id)),
            _field("method_family", KIND_STRING, _string(value.method_family)),
            _field(
                "flow_arrangement_catalog_id",
                KIND_STRING,
                _string(value.flow_arrangement_catalog_id),
            ),
            _field("engineering_source_id", KIND_STRING, _string(value.engineering_source_id)),
            _field("relation_id", KIND_STRING, _string(value.relation_id)),
            _field(
                "selected_baffle_relation", KIND_STRING, _string(value.selected_baffle_relation)
            ),
            _field("baffle_count", KIND_INT, _integer(value.baffle_count)),
        ),
    )


def interval_bytes(value: IntervalDecimal) -> bytes:
    return _record(
        "TASK162_INTERVAL_DECIMAL_V1",
        (
            _field("lower", KIND_DECIMAL, _decimal(value.lower)),
            _field("upper", KIND_DECIMAL, _decimal(value.upper)),
        ),
    )


def energy_balance_bytes(value: Task162EnergyBalanceEvidence) -> bytes:
    return _record(
        "TASK162_ENERGY_BALANCE_EVIDENCE_V1",
        (
            _field("policy_id", KIND_STRING, _string(value.policy_id)),
            _field("q_method", KIND_DECIMAL, _decimal(value.q_method)),
            _field("q_cold_nominal", KIND_DECIMAL, _decimal(value.q_cold_nominal)),
            _field("q_hot_nominal", KIND_DECIMAL, _decimal(value.q_hot_nominal)),
            _field("cold_residual_nominal", KIND_DECIMAL, _decimal(value.cold_residual_nominal)),
            _field("hot_residual_nominal", KIND_DECIMAL, _decimal(value.hot_residual_nominal)),
            _nested("cold_increment_interval", interval_bytes(value.cold_increment_interval)),
            _nested("hot_decrement_interval", interval_bytes(value.hot_decrement_interval)),
            _nested("cold_outlet_interval", interval_bytes(value.cold_outlet_interval)),
            _nested("hot_outlet_interval", interval_bytes(value.hot_outlet_interval)),
            _nested("q_cold_interval", interval_bytes(value.q_cold_interval)),
            _nested("q_hot_interval", interval_bytes(value.q_hot_interval)),
            _nested("cold_residual_interval", interval_bytes(value.cold_residual_interval)),
            _nested("hot_residual_interval", interval_bytes(value.hot_residual_interval)),
            _field("status", KIND_ENUM, _enum(value.status)),
        ),
    )


def terminal_closure_bytes(value: Task162TerminalClosureEvidence) -> bytes:
    return _record(
        "TASK162_TERMINAL_CLOSURE_EVIDENCE_V1",
        (
            _field(
                "delta_t_hot_in_cold_out", KIND_DECIMAL, _decimal(value.delta_t_hot_in_cold_out)
            ),
            _field(
                "delta_t_hot_out_cold_in", KIND_DECIMAL, _decimal(value.delta_t_hot_out_cold_in)
            ),
        ),
    )


def applicability_bytes(value: Task162Applicability) -> bytes:
    return _record(
        "TASK162_APPLICABILITY_V1",
        (
            _field("status", KIND_ENUM, _enum(value.status)),
            _field(
                "checks",
                KIND_TUPLE,
                _tuple_records(
                    _record(
                        "TASK162_APPLICABILITY_CHECK_V1",
                        (
                            _field("name", KIND_STRING, _string(name)),
                            _field("status", KIND_ENUM, _enum(status)),
                        ),
                    )
                    for name, status in value.checks
                ),
            ),
        ),
    )


def completeness_bytes(value: Task162Completeness) -> bytes:
    return _record(
        "TASK162_COMPLETENESS_V1",
        (
            _field("status", KIND_ENUM, _enum(value.status)),
            _field("required_fields", KIND_TUPLE, _tuple_strings(value.required_fields)),
        ),
    )


def provenance_semantic_inputs_bytes(value: Task162ProvenanceSemanticInputs) -> bytes:
    return _record(
        "TASK162_PROVENANCE_SEMANTIC_INPUTS_V1",
        tuple(
            _field(name, KIND_STRING, _string(getattr(value, name)))
            for name in (
                "source_authority_payload_hash",
                "task160_result_evidence_payload_hash",
                "task161_result_evidence_payload_hash",
                "task161_method_catalog_payload_hash",
                "task038_result_evidence_payload_hash",
                "cross_producer_binding_payload_hash",
                "case_authority_payload_hash",
                "magazoni_source_payload_hash",
                "nasa_source_payload_hash",
                "calculation_run_payload_hash",
            )
        ),
    )


def _pre_result_fields(
    value: Task162PreResultIdentityInputs,
) -> tuple[tuple[str, bytes, bytes], ...]:
    return (
        _field("schema_version", KIND_STRING, _string(value.schema_version)),
        _field("task162_version", KIND_STRING, _string(value.task162_version)),
        _field(
            "implementation_software_version",
            KIND_STRING,
            _string(value.implementation_software_version),
        ),
        _field("source_definition_id", KIND_STRING, _string(value.source_definition_id)),
        _field("request_hash", KIND_STRING, _string(value.request_hash)),
        _nested("task160_evidence", _task160_evidence_bytes(value.task160_evidence)),
        _nested("task161_evidence", _task161_evidence_bytes(value.task161_evidence)),
        _nested("task038_evidence", _task038_evidence_bytes(value.task038_evidence)),
        _nested(
            "cross_producer_binding_evidence",
            cross_producer_binding_bytes(value.cross_producer_binding_evidence),
        ),
        _nested(
            "case_binding_evidence", normalized_case_binding_bytes(value.case_binding_evidence)
        ),
        _nested("numerical_foundation", numerical_foundation_bytes(value.numerical_foundation)),
        _nested(
            "selected_method_identity",
            selected_method_identity_bytes(value.selected_method_identity),
        ),
        _field("selected_baffle_relation", KIND_STRING, _string(value.selected_baffle_relation)),
        _field("ntu", KIND_DECIMAL, _decimal(value.ntu)),
        _field("r_source", KIND_DECIMAL, _decimal(value.r_source)),
        _field("p_source", KIND_DECIMAL, _decimal(value.p_source)),
        _field("epsilon", KIND_DECIMAL, _decimal(value.epsilon)),
        _field("q_max", KIND_DECIMAL, _decimal(value.q_max)),
        _field("q_method", KIND_DECIMAL, _decimal(value.q_method)),
        _field("hot_outlet_temperature", KIND_DECIMAL, _decimal(value.hot_outlet_temperature)),
        _field("cold_outlet_temperature", KIND_DECIMAL, _decimal(value.cold_outlet_temperature)),
        _field("q_hot", KIND_DECIMAL, _decimal(value.q_hot)),
        _field("q_cold", KIND_DECIMAL, _decimal(value.q_cold)),
        _nested("energy_balance_evidence", energy_balance_bytes(value.energy_balance_evidence)),
        _nested(
            "terminal_closure_evidence", terminal_closure_bytes(value.terminal_closure_evidence)
        ),
        _nested("applicability", applicability_bytes(value.applicability)),
        _nested("completeness", completeness_bytes(value.completeness)),
        _field("warnings_normalized", KIND_TUPLE, _warnings_bytes(value.warnings_normalized)),
        _field("blockers_normalized", KIND_TUPLE, _blockers_bytes(value.blockers_normalized)),
        _nested(
            "provenance_semantic_inputs",
            provenance_semantic_inputs_bytes(value.provenance_semantic_inputs),
        ),
    )


def success_canonical_bytes(value: Task162PreResultIdentityInputs) -> bytes:
    return _record(TASK162_SUCCESS_HASH_DOMAIN, _pre_result_fields(value))


def success_hash_from_inputs(value: Task162PreResultIdentityInputs) -> str:
    return sha256_hex_from_framed_bytes(success_canonical_bytes(value))


def result_id(result_hash: str) -> UUID:
    return uuid5(TASK162_RESULT_ID_NAMESPACE, TASK162_SUCCESS_ID_PREFIX + result_hash)


def request_canonical_bytes(value: Task162Request) -> bytes:
    task160 = task160_result_identity_projection(value.task160_result)
    task161 = task161_result_identity_projection(value.task161_result)
    task038 = task038_result_identity_projection(value.task038_result)
    return _record(
        TASK162_REQUEST_HASH_DOMAIN,
        (
            _field("schema_version", KIND_STRING, _string(value.schema_version)),
            _field("task162_version", KIND_STRING, _string(value.task162_version)),
            _field("source_definition_id", KIND_STRING, _string(value.source_definition_id)),
            _nested("task160_result", _task160_evidence_bytes(task160)),
            _nested("task161_result", _task161_evidence_bytes(task161)),
            _nested("task038_result", _task038_evidence_bytes(task038)),
            _nested(
                "cross_producer_binding_authority",
                cross_producer_binding_bytes(value.cross_producer_binding_authority),
            ),
            _nested("case_authority", case_authority_bytes(value.case_authority)),
            _field("request_metadata", KIND_TUPLE, _tuple_pairs(value.request_metadata)),
        ),
    )


def request_hash(value: Task162Request) -> str:
    return sha256_hex_from_framed_bytes(request_canonical_bytes(value))


def typed_blocked_canonical_bytes(value: Task162TypedBlockedResult) -> bytes:
    return _record(
        TASK162_TYPED_BLOCKED_HASH_DOMAIN,
        (
            _field("schema_version", KIND_STRING, _string(value.schema_version)),
            _field("task162_version", KIND_STRING, _string(value.task162_version)),
            _field(
                "implementation_software_version",
                KIND_STRING,
                _string(value.implementation_software_version),
            ),
            _field("failure_stage", KIND_ENUM, _enum(value.failure_stage)),
            _field("request_hash", KIND_STRING, _string(value.request_hash)),
            _field("task160_result_id_or_none", *_none_or_string(value.task160_result_id_or_none)),
            _field("blockers_normalized", KIND_TUPLE, _blockers_bytes(value.blockers)),
            _field("warnings_normalized", KIND_TUPLE, _warnings_bytes(value.warnings)),
        ),
    )


def typed_blocked_hash(value: Task162TypedBlockedResult) -> str:
    return sha256_hex_from_framed_bytes(typed_blocked_canonical_bytes(value))


def typed_blocked_id(blocked_hash: str) -> UUID:
    return uuid5(TASK162_RESULT_ID_NAMESPACE, TASK162_TYPED_BLOCKED_ID_PREFIX + blocked_hash)


def raw_request_projection_bytes(value: Task162RawRequestProjection) -> bytes:
    return _record(
        TASK162_RAW_PROJECTION_DOMAIN,
        (
            _field("schema_version", KIND_STRING, _string(value.schema_version)),
            _field("root", KIND_RECORD, raw_projection_node_bytes(value.root)),
        ),
    )


def raw_request_projection_hash(value: Task162RawRequestProjection) -> str:
    return sha256_hex_from_framed_bytes(raw_request_projection_bytes(value))


def _raw_children(value: Task162RawProjectionNode) -> tuple[Task162RawProjectionNode, ...]:
    if value.kind.value == "RECORD":
        return tuple(
            sorted(
                value.children,
                key=lambda item: (item.field_name.encode("utf-8"), raw_projection_node_bytes(item)),
            )
        )
    return value.children


def raw_projection_node_bytes(value: Task162RawProjectionNode) -> bytes:
    type_kind, type_payload = _none_or_string(value.type_identity)
    scalar_kind, scalar_payload = _none_or_string(value.scalar_payload)
    return _record(
        TASK162_RAW_PROJECTION_NODE_DOMAIN,
        (
            _field("field_name", KIND_STRING, _string(value.field_name)),
            _field("kind", KIND_ENUM, _enum(value.kind)),
            _field("type_identity", type_kind, type_payload),
            _field("scalar_payload", scalar_kind, scalar_payload),
            _field(
                "children",
                KIND_TUPLE,
                _tuple_records(raw_projection_node_bytes(item) for item in _raw_children(value)),
            ),
        ),
    )


canonical_projected_node_bytes = raw_projection_node_bytes


def raw_blocked_canonical_bytes(value: Task162RawBoundaryBlockedResult) -> bytes:
    return _record(
        TASK162_RAW_BLOCKED_HASH_DOMAIN,
        (
            _field("schema_version", KIND_STRING, _string(value.schema_version)),
            _field("task162_version", KIND_STRING, _string(value.task162_version)),
            _field(
                "implementation_software_version",
                KIND_STRING,
                _string(value.implementation_software_version),
            ),
            _field("failure_stage", KIND_ENUM, _enum(value.failure_stage)),
            _field(
                "raw_request_projection",
                KIND_RECORD,
                raw_request_projection_bytes(value.raw_request_projection),
            ),
            _field(
                "raw_request_projection_hash",
                KIND_STRING,
                _string(value.raw_request_projection_hash),
            ),
            _field("blockers_normalized", KIND_TUPLE, _blockers_bytes(value.blockers)),
            _field("warnings_normalized", KIND_TUPLE, _warnings_bytes(value.warnings)),
        ),
    )


def raw_blocked_hash(value: Task162RawBoundaryBlockedResult) -> str:
    return sha256_hex_from_framed_bytes(raw_blocked_canonical_bytes(value))


def raw_blocked_id(blocked_hash: str) -> UUID:
    return uuid5(TASK162_RESULT_ID_NAMESPACE, TASK162_RAW_BLOCKED_ID_PREFIX + blocked_hash)


def validation_result_status(value: Task162ValidationResult) -> str:
    return value.status.value


__all__ = [
    "TASK162_REQUEST_HASH_DOMAIN",
    "TASK162_SUCCESS_HASH_DOMAIN",
    "TASK162_TYPED_BLOCKED_HASH_DOMAIN",
    "TASK162_RAW_BLOCKED_HASH_DOMAIN",
    "TASK162_RAW_PROJECTION_DOMAIN",
    "TASK162_RAW_PROJECTION_NODE_DOMAIN",
    "TASK162_COMPATIBILITY_DIMENSION_ORDER",
    "TASK162_SUCCESS_ID_PREFIX",
    "TASK162_TYPED_BLOCKED_ID_PREFIX",
    "TASK162_RAW_BLOCKED_ID_PREFIX",
    "TASK162_RESULT_ID_NAMESPACE",
    "TASK162_PROVENANCE_NAMESPACE",
    "TASK162_REQUEST_FIELD_ORDER",
    "TASK162_SUCCESS_PREIMAGE_FIELD_ORDER",
    "task160_result_identity_projection",
    "task161_result_identity_projection",
    "task038_result_identity_projection",
    "cross_producer_binding_bytes",
    "case_authority_bytes",
    "success_canonical_bytes",
    "success_hash_from_inputs",
    "result_id",
    "request_canonical_bytes",
    "request_hash",
    "typed_blocked_canonical_bytes",
    "typed_blocked_hash",
    "typed_blocked_id",
    "raw_request_projection_bytes",
    "raw_request_projection_hash",
    "raw_projection_node_bytes",
    "canonical_projected_node_bytes",
    "raw_blocked_canonical_bytes",
    "raw_blocked_hash",
    "raw_blocked_id",
    "sha256_hex_from_framed_bytes",
]
