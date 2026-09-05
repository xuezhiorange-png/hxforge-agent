"""TASK161 canonical framing, raw projection, and identity helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid5

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
    LIMIT_MARKER_FIELD_NAME,
    TASK161_RAW_BOUNDARY_SCHEMA_VERSION,
    TASK161_RAW_MAX_DEPTH,
    TASK161_RAW_MAX_NODES,
    TASK161_RAW_MAX_SCALAR_BYTES,
    TASK161_RAW_PROJECTION_SCHEMA_VERSION,
    TASK161_RESULT_ID_NAMESPACE,
    CapacityFoundation,
    CaseBindingState,
    CatalogApplicability,
    CatalogCompleteness,
    CfheSurrogateMixingAuthority,
    FlowArrangementCatalogAuthority,
    MethodOutputSemantics,
    PerformanceMethodCatalogAuthority,
    PhysicalStheMixingAuthority,
    RawProjectionKind,
    RawProjectionNode,
    SourceAssumption,
    StheCfheIdentityMapping,
    Task160ResultIdentityProjection,
    Task161Blocker,
    Task161PreResultIdentityInputs,
    Task161ProvenanceSemanticInputs,
    Task161RawRequestProjection,
    Task161Request,
    Task161Warning,
)

TASK161_REQUEST_HASH_DOMAIN = "TASK161_REQUEST_HASH_V1"
TASK161_SUCCESS_HASH_DOMAIN = "TASK161_SUCCESS_RESULT_HASH_V1"
TASK161_TYPED_BLOCKED_HASH_DOMAIN = "TASK161_TYPED_BLOCKED_RESULT_HASH_V1"
TASK161_RAW_BLOCKED_HASH_DOMAIN = "TASK161_RAW_BOUNDARY_BLOCKED_RESULT_HASH_V1"
TASK161_RAW_PROJECTION_DOMAIN = "TASK161_RAW_REQUEST_PROJECTION_V1"
TASK161_RAW_PROJECTION_NODE_DOMAIN = "TASK161_RAW_PROJECTION_NODE_V1"
TASK161_RAW_PROJECTION_SCHEMA_VERSION = TASK161_RAW_PROJECTION_SCHEMA_VERSION
TASK161_RAW_BOUNDARY_SCHEMA_VERSION = TASK161_RAW_BOUNDARY_SCHEMA_VERSION

SUCCESS_ID_PREFIX = "task161-result-v1::"
TYPED_BLOCKED_ID_PREFIX = "task161-typed-blocked-v1::"
RAW_BLOCKED_ID_PREFIX = "task161-raw-boundary-blocked-v1::"

# Compatibility aliases retained for callers using the shorter R1 names.
REQUEST_HASH_DOMAIN = TASK161_REQUEST_HASH_DOMAIN
SUCCESS_HASH_DOMAIN = TASK161_SUCCESS_HASH_DOMAIN

TASK161_REQUEST_FIELD_ORDER: tuple[str, ...] = (
    "schema_version",
    "task161_version",
    "source_definition_id",
    "task160_schema_version",
    "task160_version",
    "task160_request_hash",
    "task160_result_hash",
    "task160_result_id",
    "request_metadata_normalized",
)

TASK161_SUCCESS_PREIMAGE_FIELD_ORDER: tuple[str, ...] = (
    "schema_version",
    "task161_version",
    "implementation_software_version",
    "source_definition_id",
    "request_hash",
    "task160_evidence",
    "capacity_foundation",
    "flow_arrangement_catalog",
    "performance_method_catalog",
    "physical_sthe_mixing",
    "cfhe_surrogate_mixing",
    "sthe_cfhe_identity_mapping",
    "source_assumptions",
    "required_case_inputs",
    "required_runtime_inputs",
    "method_output_semantics",
    "case_binding_state",
    "applicability",
    "completeness",
    "warnings_normalized",
    "blockers_normalized",
    "provenance_semantic_inputs",
)


def _enum_payload(value: Enum | str) -> bytes:
    return (value.value if isinstance(value, Enum) else value).encode("ascii")


def _string(value: str) -> bytes:
    return frame_value(KIND_STRING, value.encode("utf-8"))


def _enum(value: Enum | str) -> bytes:
    return frame_value(KIND_ENUM, _enum_payload(value))


def _integer(value: int) -> bytes:
    return frame_value(KIND_INT, str(value).encode("ascii"))


def _decimal(value: Decimal) -> bytes:
    return frame_value(KIND_DECIMAL, str(value).encode("ascii"))


def _boolean(value: bool) -> bytes:
    return frame_value(KIND_BOOL_TRUE if value else KIND_BOOL_FALSE, b"")


def _none() -> bytes:
    return frame_value(KIND_NONE, b"")


def _tuple_payload(values: Iterable[bytes]) -> bytes:
    return frame_tuple(tuple(values))


def _record_field(name: str, kind: bytes, payload: bytes) -> tuple[str, bytes, bytes]:
    return (name, kind, payload)


def _tuple_strings(values: Iterable[str]) -> bytes:
    return _tuple_payload(_string(value) for value in values)


def _tuple_enums(values: Iterable[Enum | str]) -> bytes:
    return _tuple_payload(_enum(value) for value in values)


def _tuple_records(values: Iterable[bytes]) -> bytes:
    return _tuple_payload(values)


def _pairs(values: Iterable[tuple[str, str]]) -> bytes:
    return _tuple_records(
        frame_record(
            "TASK161_STRING_PAIR_V1",
            (
                _record_field("key", KIND_STRING, key.encode("utf-8")),
                _record_field("value", KIND_STRING, value.encode("utf-8")),
            ),
        )
        for key, value in values
    )


def task160_result_identity_projection(
    result: Task160Result,
) -> Task160ResultIdentityProjection:
    """Return the only Task160 representation admitted at the raw boundary."""
    return Task160ResultIdentityProjection(
        schema_version=result.schema_version,
        task160_version=result.task160_version,
        request_hash=result.request_hash,
        result_hash=result.result_hash,
        result_id=str(result.result_id),
        provenance_hash=result.provenance.provenance_hash,
    )


def _optional_string(value: str | None) -> tuple[bytes, bytes]:
    if value is None:
        return KIND_NONE, b""
    return KIND_STRING, value.encode("utf-8")


def _raw_child_sort_key(value: RawProjectionNode) -> tuple[bytes, bytes]:
    return (value.field_name.encode("utf-8"), raw_projection_node_bytes(value))


def _raw_children(value: RawProjectionNode) -> tuple[RawProjectionNode, ...]:
    if value.kind is RawProjectionKind.RECORD:
        return tuple(sorted(value.children, key=_raw_child_sort_key))
    return value.children


def raw_projection_node_bytes(value: RawProjectionNode) -> bytes:
    type_kind, type_payload = _optional_string(value.type_identity)
    scalar_kind, scalar_payload = _optional_string(value.scalar_payload)
    children = _raw_children(value)
    return frame_record(
        TASK161_RAW_PROJECTION_NODE_DOMAIN,
        (
            _record_field("field_name", KIND_STRING, value.field_name.encode("utf-8")),
            _record_field("kind", KIND_ENUM, _enum_payload(value.kind)),
            _record_field("type_identity", type_kind, type_payload),
            _record_field("scalar_payload", scalar_kind, scalar_payload),
            _record_field(
                "children",
                KIND_TUPLE,
                _tuple_records(raw_projection_node_bytes(child) for child in children),
            ),
        ),
    )


canonical_projected_node_bytes = raw_projection_node_bytes


def raw_request_projection_bytes(value: Task161RawRequestProjection) -> bytes:
    return frame_record(
        TASK161_RAW_PROJECTION_DOMAIN,
        (
            _record_field(
                "schema_version",
                KIND_STRING,
                value.schema_version.encode("utf-8"),
            ),
            _record_field("root", KIND_RECORD, raw_projection_node_bytes(value.root)),
        ),
    )


def raw_request_projection_hash(value: Task161RawRequestProjection) -> str:
    return sha256_hex_from_framed_bytes(raw_request_projection_bytes(value))


def _identity_projection_bytes(value: Task160ResultIdentityProjection) -> bytes:
    fields = (
        _record_field("schema_version", KIND_STRING, value.schema_version.encode("utf-8")),
        _record_field("task160_version", KIND_STRING, value.task160_version.encode("utf-8")),
        _record_field("request_hash", KIND_STRING, value.request_hash.encode("ascii")),
        _record_field("result_hash", KIND_STRING, value.result_hash.encode("ascii")),
        _record_field("result_id", KIND_STRING, value.result_id.encode("ascii")),
        _record_field("provenance_hash", KIND_STRING, value.provenance_hash.encode("utf-8")),
    )
    return frame_record("TASK161_TASK160_RESULT_IDENTITY_PROJECTION_V1", fields)


def _assumption_bytes(value: SourceAssumption) -> bytes:
    return frame_record(
        "TASK161_SOURCE_ASSUMPTION_V1",
        (
            _record_field("assumption_id", KIND_STRING, value.assumption_id.encode("utf-8")),
            _record_field("semantic_name", KIND_STRING, value.semantic_name.encode("utf-8")),
            _record_field("source_value", KIND_STRING, value.source_value.encode("utf-8")),
            _record_field("source_status", KIND_STRING, value.source_status.encode("utf-8")),
            _record_field(
                "primary_authority_class",
                KIND_ENUM,
                _enum_payload(value.primary_authority_class),
            ),
            _record_field(
                "case_authority_required",
                KIND_BOOL_TRUE if value.case_authority_required else KIND_BOOL_FALSE,
                b"",
            ),
            _record_field(
                "runtime_validation_required",
                KIND_BOOL_TRUE if value.runtime_validation_required else KIND_BOOL_FALSE,
                b"",
            ),
            _record_field("evidence_refs", KIND_TUPLE, _tuple_strings(value.evidence_refs)),
        ),
    )


def source_assumptions_bytes(values: Iterable[SourceAssumption]) -> bytes:
    return _tuple_records(_assumption_bytes(value) for value in values)


def _flow_catalog_bytes(value: FlowArrangementCatalogAuthority) -> bytes:
    return frame_record(
        "TASK161_FLOW_ARRANGEMENT_CATALOG_V1",
        (
            _record_field("catalog_id", KIND_STRING, value.catalog_id.encode("utf-8")),
            _record_field(
                "source_shell_type", KIND_STRING, value.source_shell_type.encode("utf-8")
            ),
            _record_field(
                "source_shell_pass_count", KIND_INT, str(value.source_shell_pass_count).encode()
            ),
            _record_field(
                "source_tube_pass_count", KIND_INT, str(value.source_tube_pass_count).encode()
            ),
            _record_field(
                "overall_flow_orientation",
                KIND_STRING,
                value.overall_flow_orientation.encode("utf-8"),
            ),
            _record_field(
                "sectional_surrogate_model",
                KIND_STRING,
                value.sectional_surrogate_model.encode("utf-8"),
            ),
            _record_field(
                "section_count_relation",
                KIND_STRING,
                value.section_count_relation.encode("utf-8"),
            ),
            _record_field(
                "hxforge_construction_intersection",
                KIND_STRING,
                value.hxforge_construction_intersection.encode("utf-8"),
            ),
            _record_field("limitations", KIND_TUPLE, _tuple_strings(value.limitations)),
            _record_field("evidence_refs", KIND_TUPLE, _tuple_strings(value.evidence_refs)),
        ),
    )


def _method_catalog_fields(
    value: PerformanceMethodCatalogAuthority,
    *,
    include_authority_hash: bool,
) -> tuple[tuple[str, bytes, bytes], ...]:
    fields: list[tuple[str, bytes, bytes]] = [
        _record_field(
            "method_authority_id", KIND_STRING, value.method_authority_id.encode("utf-8")
        ),
        _record_field("method_family", KIND_STRING, value.method_family.encode("utf-8")),
        _record_field("method_revision", KIND_STRING, value.method_revision.encode("utf-8")),
        _record_field(
            "flow_arrangement_catalog_id",
            KIND_STRING,
            value.flow_arrangement_catalog_id.encode("utf-8"),
        ),
        _record_field(
            "engineering_source_id", KIND_STRING, value.engineering_source_id.encode("utf-8")
        ),
        _record_field(
            "engineering_source_version",
            KIND_STRING,
            value.engineering_source_version.encode("utf-8"),
        ),
        _record_field(
            "engineering_source_location",
            KIND_STRING,
            value.engineering_source_location.encode("utf-8"),
        ),
        _record_field(
            "engineering_source_license",
            KIND_STRING,
            value.engineering_source_license.encode("utf-8"),
        ),
        _record_field("relation_id", KIND_STRING, value.relation_id.encode("utf-8")),
        _record_field(
            "source_variable_definitions",
            KIND_TUPLE,
            _pairs(value.source_variable_definitions),
        ),
        _record_field(
            "hxforge_variable_mapping", KIND_TUPLE, _pairs(value.hxforge_variable_mapping)
        ),
        _record_field(
            "physical_configuration_scope",
            KIND_TUPLE,
            _pairs(value.physical_configuration_scope),
        ),
        _record_field("model_scope", KIND_TUPLE, _pairs(value.model_scope)),
        _record_field(
            "required_case_inputs", KIND_TUPLE, _tuple_strings(value.required_case_inputs)
        ),
        _record_field(
            "required_runtime_inputs",
            KIND_TUPLE,
            _tuple_strings(value.required_runtime_inputs),
        ),
        _record_field("output_variables", KIND_TUPLE, _tuple_strings(value.output_variables)),
        _record_field("parameter_authorities", KIND_TUPLE, _pairs(value.parameter_authorities)),
        _record_field(
            "supported_baffle_count_domain",
            KIND_STRING,
            value.supported_baffle_count_domain.encode("utf-8"),
        ),
        _record_field(
            "supported_mixing_model_domain",
            KIND_TUPLE,
            _tuple_strings(value.supported_mixing_model_domain),
        ),
        _record_field(
            "single_phase_requirement",
            KIND_BOOL_TRUE if value.single_phase_requirement else KIND_BOOL_FALSE,
            b"",
        ),
        _record_field(
            "constant_property_requirement",
            KIND_BOOL_TRUE if value.constant_property_requirement else KIND_BOOL_FALSE,
            b"",
        ),
        _record_field("leakage_assumption", KIND_STRING, value.leakage_assumption.encode("utf-8")),
        _record_field("bypass_assumption", KIND_STRING, value.bypass_assumption.encode("utf-8")),
        _record_field(
            "p_source_definition", KIND_STRING, value.p_source_definition.encode("utf-8")
        ),
        _record_field(
            "r_source_definition", KIND_STRING, value.r_source_definition.encode("utf-8")
        ),
        _record_field("ntu_definition", KIND_STRING, value.ntu_definition.encode("utf-8")),
        _record_field(
            "p_to_epsilon_mapping",
            KIND_STRING,
            value.p_to_epsilon_mapping.encode("utf-8"),
        ),
        _record_field("r_to_cr_mapping", KIND_STRING, value.r_to_cr_mapping.encode("utf-8")),
        _record_field("applicability", KIND_TUPLE, _tuple_strings(value.applicability)),
        _record_field("limitations", KIND_TUPLE, _tuple_strings(value.limitations)),
        _record_field("evidence_refs", KIND_TUPLE, _tuple_strings(value.evidence_refs)),
        _record_field("provenance", KIND_TUPLE, _tuple_strings(value.provenance)),
    ]
    if include_authority_hash:
        fields.append(
            _record_field("authority_hash", KIND_STRING, value.authority_hash.encode("ascii"))
        )
    return tuple(fields)


def method_catalog_bytes(value: PerformanceMethodCatalogAuthority) -> bytes:
    return frame_record(
        "TASK161_METHOD_CATALOG_V1",
        _method_catalog_fields(value, include_authority_hash=True),
    )


def method_catalog_payload_bytes(value: PerformanceMethodCatalogAuthority) -> bytes:
    return frame_record(
        "TASK161_PROVENANCE_METHOD_CATALOG_PAYLOAD_V1",
        _method_catalog_fields(value, include_authority_hash=False),
    )


def method_catalog_payload_hash(value: PerformanceMethodCatalogAuthority) -> str:
    return sha256_hex_from_framed_bytes(method_catalog_payload_bytes(value))


def _capacity_bytes(value: CapacityFoundation) -> bytes:
    return frame_record(
        "TASK161_CAPACITY_FOUNDATION_V1",
        (
            _record_field("c_dot_hot", KIND_DECIMAL, str(value.c_dot_hot).encode("ascii")),
            _record_field("c_dot_cold", KIND_DECIMAL, str(value.c_dot_cold).encode("ascii")),
            _record_field("c_min", KIND_DECIMAL, str(value.c_min).encode("ascii")),
            _record_field("c_max", KIND_DECIMAL, str(value.c_max).encode("ascii")),
            _record_field("c_r", KIND_DECIMAL, str(value.c_r).encode("ascii")),
            _record_field("r_source", KIND_DECIMAL, str(value.r_source).encode("ascii")),
            _record_field(
                "capacity_side_relation",
                KIND_ENUM,
                _enum_payload(value.capacity_side_relation),
            ),
        ),
    )


def _mixing_bytes(value: PhysicalStheMixingAuthority) -> bytes:
    return frame_record(
        "TASK161_PHYSICAL_STHE_MIXING_V1",
        (
            _record_field(
                "tube_side_mixing_assumption",
                KIND_STRING,
                value.tube_side_mixing_assumption.encode("utf-8"),
            ),
            _record_field(
                "shell_side_mixing_assumption",
                KIND_STRING,
                value.shell_side_mixing_assumption.encode("utf-8"),
            ),
            _record_field(
                "shell_side_mixing_model_id",
                KIND_STRING,
                value.shell_side_mixing_model_id.encode("utf-8"),
            ),
        ),
    )


def _surrogate_mixing_bytes(value: CfheSurrogateMixingAuthority) -> bytes:
    return frame_record(
        "TASK161_CFHE_SURROGATE_MIXING_V1",
        (
            _record_field(
                "external_fluid_identity",
                KIND_STRING,
                value.external_fluid_identity.encode("utf-8"),
            ),
            _record_field(
                "internal_fluid_identity",
                KIND_STRING,
                value.internal_fluid_identity.encode("utf-8"),
            ),
            _record_field(
                "external_fluid_mixing_assumption",
                KIND_STRING,
                value.external_fluid_mixing_assumption.encode("utf-8"),
            ),
            _record_field(
                "internal_fluid_mixing_assumption",
                KIND_STRING,
                value.internal_fluid_mixing_assumption.encode("utf-8"),
            ),
        ),
    )


def _mapping_bytes(value: StheCfheIdentityMapping) -> bytes:
    return frame_record(
        "TASK161_STHE_CFHE_IDENTITY_MAPPING_V1",
        (
            _record_field(
                "sthe_tube_side_is_cfhe_external_fluid",
                KIND_BOOL_TRUE if value.sthe_tube_side_is_cfhe_external_fluid else KIND_BOOL_FALSE,
                b"",
            ),
            _record_field(
                "sthe_shell_side_is_cfhe_internal_fluid",
                KIND_BOOL_TRUE if value.sthe_shell_side_is_cfhe_internal_fluid else KIND_BOOL_FALSE,
                b"",
            ),
            _record_field(
                "sthe_tube_side_is_cfhe_internal_fluid",
                KIND_BOOL_TRUE if value.sthe_tube_side_is_cfhe_internal_fluid else KIND_BOOL_FALSE,
                b"",
            ),
            _record_field(
                "sthe_shell_side_is_cfhe_external_fluid",
                KIND_BOOL_TRUE if value.sthe_shell_side_is_cfhe_external_fluid else KIND_BOOL_FALSE,
                b"",
            ),
        ),
    )


def _output_bytes(value: MethodOutputSemantics) -> bytes:
    return frame_record(
        "TASK161_METHOD_OUTPUT_SEMANTICS_V1",
        (
            _record_field("direct_output", KIND_STRING, value.direct_output.encode("utf-8")),
            _record_field(
                "direct_output_definition",
                KIND_STRING,
                value.direct_output_definition.encode("utf-8"),
            ),
            _record_field(
                "direct_output_is_generic_epsilon",
                KIND_BOOL_TRUE if value.direct_output_is_generic_epsilon else KIND_BOOL_FALSE,
                b"",
            ),
            _record_field(
                "direct_output_is_magazoni_p",
                KIND_BOOL_TRUE if value.direct_output_is_magazoni_p else KIND_BOOL_FALSE,
                b"",
            ),
            _record_field(
                "p_to_epsilon_mapping",
                KIND_STRING,
                value.p_to_epsilon_mapping.encode("utf-8"),
            ),
        ),
    )


def _case_binding_bytes(value: CaseBindingState) -> bytes:
    return frame_record(
        "TASK161_CASE_BINDING_STATE_V1",
        (
            _record_field("tema_e_binding", KIND_ENUM, _enum_payload(value.tema_e_binding)),
            _record_field(
                "flow_arrangement_binding",
                KIND_ENUM,
                _enum_payload(value.flow_arrangement_binding),
            ),
            _record_field("method_selection", KIND_ENUM, _enum_payload(value.method_selection)),
            _record_field(
                "leakage_assumption_binding",
                KIND_ENUM,
                _enum_payload(value.leakage_assumption_binding),
            ),
            _record_field(
                "bypass_assumption_binding",
                KIND_ENUM,
                _enum_payload(value.bypass_assumption_binding),
            ),
        ),
    )


def _applicability_bytes(value: CatalogApplicability) -> bytes:
    return frame_record(
        "TASK161_CATALOG_APPLICABILITY_V1",
        (
            _record_field("status", KIND_ENUM, _enum_payload(value.status)),
            _record_field(
                "catalog_source_applicable",
                KIND_BOOL_TRUE if value.catalog_source_applicable else KIND_BOOL_FALSE,
                b"",
            ),
            _record_field(
                "case_binding_applicability",
                KIND_STRING,
                value.case_binding_applicability.encode("utf-8"),
            ),
            _record_field(
                "downstream_runtime_applicability",
                KIND_STRING,
                value.downstream_runtime_applicability.encode("utf-8"),
            ),
            _record_field("required_scope", KIND_TUPLE, _tuple_strings(value.required_scope)),
        ),
    )


def _completeness_bytes(value: CatalogCompleteness) -> bytes:
    return frame_record(
        "TASK161_CATALOG_COMPLETENESS_V1",
        (
            _record_field("status", KIND_ENUM, _enum_payload(value.status)),
            _record_field(
                "required_case_inputs_declared",
                KIND_BOOL_TRUE if value.required_case_inputs_declared else KIND_BOOL_FALSE,
                b"",
            ),
            _record_field(
                "required_runtime_inputs_declared",
                KIND_BOOL_TRUE if value.required_runtime_inputs_declared else KIND_BOOL_FALSE,
                b"",
            ),
            _record_field(
                "output_contract_declared",
                KIND_BOOL_TRUE if value.output_contract_declared else KIND_BOOL_FALSE,
                b"",
            ),
            _record_field(
                "source_assumptions_declared",
                KIND_BOOL_TRUE if value.source_assumptions_declared else KIND_BOOL_FALSE,
                b"",
            ),
            _record_field(
                "provenance_declared",
                KIND_BOOL_TRUE if value.provenance_declared else KIND_BOOL_FALSE,
                b"",
            ),
        ),
    )


def _blocker_bytes(value: Task161Blocker) -> bytes:
    return frame_record(
        "TASK161_BLOCKER_V1",
        (
            _record_field("code", KIND_STRING, value.code.encode("utf-8")),
            _record_field("stage", KIND_ENUM, _enum_payload(value.stage)),
            _record_field("field_path", KIND_STRING, value.field_path.encode("utf-8")),
            _record_field("evidence_refs", KIND_TUPLE, _tuple_strings(value.evidence_refs)),
            _record_field("details", KIND_TUPLE, _pairs(value.details)),
        ),
    )


def _warning_bytes(value: Task161Warning) -> bytes:
    return frame_record(
        "TASK161_WARNING_V1",
        (
            _record_field("code", KIND_STRING, value.code.encode("utf-8")),
            _record_field("field_path", KIND_STRING, value.field_path.encode("utf-8")),
            _record_field("evidence_refs", KIND_TUPLE, _tuple_strings(value.evidence_refs)),
        ),
    )


def provenance_semantic_inputs_bytes(value: Task161ProvenanceSemanticInputs) -> bytes:
    return frame_record(
        "TASK161_PROVENANCE_SEMANTIC_INPUTS_V1",
        (
            _record_field(
                "source_authority_payload_hash",
                KIND_STRING,
                value.source_authority_payload_hash.encode("ascii"),
            ),
            _record_field(
                "task160_result_evidence_payload_hash",
                KIND_STRING,
                value.task160_result_evidence_payload_hash.encode("ascii"),
            ),
            _record_field(
                "magazoni_source_payload_hash",
                KIND_STRING,
                value.magazoni_source_payload_hash.encode("ascii"),
            ),
            _record_field(
                "nasa_generic_definition_source_payload_hash",
                KIND_STRING,
                value.nasa_generic_definition_source_payload_hash.encode("ascii"),
            ),
            _record_field(
                "method_catalog_payload_hash",
                KIND_STRING,
                value.method_catalog_payload_hash.encode("ascii"),
            ),
            _record_field(
                "calculation_run_payload_hash",
                KIND_STRING,
                value.calculation_run_payload_hash.encode("ascii"),
            ),
        ),
    )


def success_preimage_fields(
    value: Task161PreResultIdentityInputs,
) -> tuple[tuple[str, bytes, bytes], ...]:
    return (
        _record_field("schema_version", KIND_STRING, value.schema_version.encode("utf-8")),
        _record_field("task161_version", KIND_STRING, value.task161_version.encode("utf-8")),
        _record_field(
            "implementation_software_version",
            KIND_STRING,
            value.implementation_software_version.encode("utf-8"),
        ),
        _record_field(
            "source_definition_id",
            KIND_STRING,
            value.source_definition_id.encode("utf-8"),
        ),
        _record_field("request_hash", KIND_STRING, value.request_hash.encode("ascii")),
        _record_field(
            "task160_evidence", KIND_RECORD, _identity_projection_bytes(value.task160_evidence)
        ),
        _record_field(
            "capacity_foundation", KIND_RECORD, _capacity_bytes(value.capacity_foundation)
        ),
        _record_field(
            "flow_arrangement_catalog",
            KIND_RECORD,
            _flow_catalog_bytes(value.flow_arrangement_catalog),
        ),
        _record_field(
            "performance_method_catalog",
            KIND_RECORD,
            method_catalog_bytes(value.performance_method_catalog),
        ),
        _record_field(
            "physical_sthe_mixing", KIND_RECORD, _mixing_bytes(value.physical_sthe_mixing)
        ),
        _record_field(
            "cfhe_surrogate_mixing",
            KIND_RECORD,
            _surrogate_mixing_bytes(value.cfhe_surrogate_mixing),
        ),
        _record_field(
            "sthe_cfhe_identity_mapping",
            KIND_RECORD,
            _mapping_bytes(value.sthe_cfhe_identity_mapping),
        ),
        _record_field(
            "source_assumptions",
            KIND_TUPLE,
            source_assumptions_bytes(value.source_assumptions),
        ),
        _record_field(
            "required_case_inputs",
            KIND_TUPLE,
            _tuple_strings(value.required_case_inputs),
        ),
        _record_field(
            "required_runtime_inputs",
            KIND_TUPLE,
            _tuple_strings(value.required_runtime_inputs),
        ),
        _record_field(
            "method_output_semantics",
            KIND_RECORD,
            _output_bytes(value.method_output_semantics),
        ),
        _record_field(
            "case_binding_state", KIND_RECORD, _case_binding_bytes(value.case_binding_state)
        ),
        _record_field("applicability", KIND_RECORD, _applicability_bytes(value.applicability)),
        _record_field("completeness", KIND_RECORD, _completeness_bytes(value.completeness)),
        _record_field(
            "warnings_normalized",
            KIND_TUPLE,
            _tuple_records(_warning_bytes(item) for item in value.warnings_normalized),
        ),
        _record_field(
            "blockers_normalized",
            KIND_TUPLE,
            _tuple_records(_blocker_bytes(item) for item in value.blockers_normalized),
        ),
        _record_field(
            "provenance_semantic_inputs",
            KIND_RECORD,
            provenance_semantic_inputs_bytes(value.provenance_semantic_inputs),
        ),
    )


def success_canonical_bytes(value: Task161PreResultIdentityInputs) -> bytes:
    return frame_record(TASK161_SUCCESS_HASH_DOMAIN, success_preimage_fields(value))


def success_hash(value: Task161PreResultIdentityInputs) -> str:
    return sha256_hex_from_framed_bytes(success_canonical_bytes(value))


def success_hash_from_inputs(value: Task161PreResultIdentityInputs) -> str:
    return success_hash(value)


def request_hash_fields(
    request: Task161Request,
) -> tuple[tuple[str, bytes, bytes], ...]:
    evidence = task160_result_identity_projection(request.task160_result)
    metadata = _pairs(request.request_metadata)
    return (
        _record_field("schema_version", KIND_STRING, request.schema_version.encode("utf-8")),
        _record_field("task161_version", KIND_STRING, request.task161_version.encode("utf-8")),
        _record_field(
            "source_definition_id", KIND_STRING, request.source_definition_id.encode("utf-8")
        ),
        _record_field(
            "task160_schema_version",
            KIND_STRING,
            evidence.schema_version.encode("utf-8"),
        ),
        _record_field("task160_version", KIND_STRING, evidence.task160_version.encode("utf-8")),
        _record_field("task160_request_hash", KIND_STRING, evidence.request_hash.encode("ascii")),
        _record_field("task160_result_hash", KIND_STRING, evidence.result_hash.encode("ascii")),
        _record_field("task160_result_id", KIND_STRING, evidence.result_id.encode("ascii")),
        _record_field("request_metadata_normalized", KIND_TUPLE, metadata),
    )


def request_canonical_bytes(request: Task161Request) -> bytes:
    return frame_record(TASK161_REQUEST_HASH_DOMAIN, request_hash_fields(request))


def request_hash(request: Task161Request) -> str:
    return sha256_hex_from_framed_bytes(request_canonical_bytes(request))


def typed_blocked_hash_fields(
    *,
    schema_version: str,
    task161_version: str,
    implementation_software_version: str,
    failure_stage: Enum | str,
    request_hash_value: str,
    task160_result_id_or_none: str | None,
    blockers: Iterable[Task161Blocker],
    warnings: Iterable[Task161Warning],
) -> tuple[tuple[str, bytes, bytes], ...]:
    result_kind, result_payload = _optional_string(task160_result_id_or_none)
    return (
        _record_field("schema_version", KIND_STRING, schema_version.encode("utf-8")),
        _record_field("task161_version", KIND_STRING, task161_version.encode("utf-8")),
        _record_field(
            "implementation_software_version",
            KIND_STRING,
            implementation_software_version.encode("utf-8"),
        ),
        _record_field("failure_stage", KIND_ENUM, _enum_payload(failure_stage)),
        _record_field("request_hash", KIND_STRING, request_hash_value.encode("ascii")),
        _record_field("task160_result_id_or_none", result_kind, result_payload),
        _record_field(
            "blockers_normalized",
            KIND_TUPLE,
            _tuple_records(_blocker_bytes(item) for item in blockers),
        ),
        _record_field(
            "warnings_normalized",
            KIND_TUPLE,
            _tuple_records(_warning_bytes(item) for item in warnings),
        ),
    )


def typed_blocked_hash(**kwargs: object) -> str:
    return sha256_hex_from_framed_bytes(
        frame_record(
            TASK161_TYPED_BLOCKED_HASH_DOMAIN,
            typed_blocked_hash_fields(**kwargs),  # type: ignore[arg-type]
        )
    )


def raw_blocked_hash_fields(
    *,
    schema_version: str,
    task161_version: str,
    implementation_software_version: str,
    failure_stage: Enum | str,
    raw_request_projection_hash_value: str,
    blockers: Iterable[Task161Blocker],
    warnings: Iterable[Task161Warning],
) -> tuple[tuple[str, bytes, bytes], ...]:
    return (
        _record_field("schema_version", KIND_STRING, schema_version.encode("utf-8")),
        _record_field("task161_version", KIND_STRING, task161_version.encode("utf-8")),
        _record_field(
            "implementation_software_version",
            KIND_STRING,
            implementation_software_version.encode("utf-8"),
        ),
        _record_field("failure_stage", KIND_ENUM, _enum_payload(failure_stage)),
        _record_field(
            "raw_request_projection_hash",
            KIND_STRING,
            raw_request_projection_hash_value.encode("ascii"),
        ),
        _record_field(
            "blockers_normalized",
            KIND_TUPLE,
            _tuple_records(_blocker_bytes(item) for item in blockers),
        ),
        _record_field(
            "warnings_normalized",
            KIND_TUPLE,
            _tuple_records(_warning_bytes(item) for item in warnings),
        ),
    )


def raw_blocked_hash(**kwargs: object) -> str:
    return sha256_hex_from_framed_bytes(
        frame_record(
            TASK161_RAW_BLOCKED_HASH_DOMAIN,
            raw_blocked_hash_fields(**kwargs),  # type: ignore[arg-type]
        )
    )


def result_id(result_hash: str) -> UUID:
    return uuid5(UUID(TASK161_RESULT_ID_NAMESPACE), SUCCESS_ID_PREFIX + result_hash)


def typed_blocked_result_id(blocked_result_hash: str) -> UUID:
    return uuid5(UUID(TASK161_RESULT_ID_NAMESPACE), TYPED_BLOCKED_ID_PREFIX + blocked_result_hash)


def raw_blocked_result_id(blocked_result_hash: str) -> UUID:
    return uuid5(UUID(TASK161_RESULT_ID_NAMESPACE), RAW_BLOCKED_ID_PREFIX + blocked_result_hash)


def _bounded_text(value: str) -> tuple[str, str | None]:
    """Count UTF-8 incrementally and stop at the first byte over the limit."""
    count = 0
    try:
        for character in value:
            try:
                encoded = character.encode("utf-8", "strict")
            except UnicodeEncodeError:
                return "UNICODE_ENCODING_FAILURE", None
            count += len(encoded)
            if count >= TASK161_RAW_MAX_SCALAR_BYTES + 1:
                return "SCALAR_BYTE_LIMIT_EXCEEDED", None
    except BaseException:
        return "UNICODE_ENCODING_FAILURE", None
    return "", value


@dataclass(frozen=True)
class RawProjectionOutcome:
    projection: Task161RawRequestProjection
    reasons: tuple[str, ...]
    unsupported_object_present: bool


class _ProjectionBuilder:
    def __init__(self) -> None:
        self.normal_nodes = 0
        self.reasons: set[str] = set()
        self.unsupported_object_present = False
        self.node_budget_exhausted = False

    def marker(self, reason: str) -> RawProjectionNode:
        self.reasons.add(reason)
        return RawProjectionNode(
            LIMIT_MARKER_FIELD_NAME,
            RawProjectionKind.LIMIT_MARKER,
            type_identity=None,
            scalar_payload=reason,
            children=(),
        )

    def reserve(self, depth: int, field_name: str) -> RawProjectionNode | None:
        if depth > TASK161_RAW_MAX_DEPTH:
            return self.marker("DEPTH_LIMIT_EXCEEDED")
        if self.normal_nodes >= TASK161_RAW_MAX_NODES:
            self.node_budget_exhausted = True
            return self.marker("NODE_LIMIT_EXCEEDED")
        field_status, safe_field = _bounded_text(field_name)
        if field_status:
            return self.marker(field_status)
        if safe_field is None or not safe_field:
            safe_field = "__TASK161_EMPTY_FIELD_NAME__"
        self.normal_nodes += 1
        return RawProjectionNode(
            safe_field,
            RawProjectionKind.NONE,
            type_identity=None,
            scalar_payload=None,
            children=(),
        )

    def scalar(
        self,
        depth: int,
        field_name: str,
        kind: RawProjectionKind,
        payload: str | None,
        *,
        type_identity: str | None = None,
    ) -> RawProjectionNode:
        reserved = self.reserve(depth, field_name)
        if reserved is not None and reserved.kind is RawProjectionKind.LIMIT_MARKER:
            return reserved
        assert reserved is not None
        if type_identity is not None:
            status, safe_type = _bounded_text(type_identity)
            if status:
                self.normal_nodes -= 1
                return self.marker(status)
            type_identity = safe_type
        if payload is not None:
            status, safe_payload = _bounded_text(payload)
            if status:
                self.normal_nodes -= 1
                return self.marker(status)
            payload = safe_payload
        return RawProjectionNode(
            reserved.field_name,
            kind,
            type_identity=type_identity,
            scalar_payload=payload,
            children=(),
        )


def _safe_type_identity(value: object) -> tuple[str | None, str | None]:
    try:
        python_type = type(value)
        module = type.__getattribute__(python_type, "__module__")
        qualname = type.__getattribute__(python_type, "__qualname__")
    except BaseException:
        return None, "TYPE_IDENTITY_UNAVAILABLE"
    if type(module) is not str or type(qualname) is not str:
        return None, "TYPE_IDENTITY_UNAVAILABLE"
    combined = module + "." + qualname
    status, identity = _bounded_text(combined)
    if status:
        return None, status
    return identity, None


def _project_identity(
    value: Task160Result,
    field_name: str,
    depth: int,
    builder: _ProjectionBuilder,
) -> RawProjectionNode:
    if depth > TASK161_RAW_MAX_DEPTH:
        return builder.marker("DEPTH_LIMIT_EXCEEDED")
    if depth + 1 > TASK161_RAW_MAX_DEPTH:
        return builder.marker("DEPTH_LIMIT_EXCEEDED")
    if builder.normal_nodes + 7 > TASK161_RAW_MAX_NODES:
        builder.node_budget_exhausted = True
        return builder.marker("NODE_LIMIT_EXCEEDED")
    parent = builder.reserve(depth, field_name)
    if parent is not None and parent.kind is RawProjectionKind.LIMIT_MARKER:
        return parent
    assert parent is not None
    identity = task160_result_identity_projection(value)
    values = (
        ("schema_version", identity.schema_version),
        ("task160_version", identity.task160_version),
        ("request_hash", identity.request_hash),
        ("result_hash", identity.result_hash),
        ("result_id", identity.result_id),
        ("provenance_hash", identity.provenance_hash),
    )
    for _, child_value in values:
        status, _ = _bounded_text(child_value)
        if status:
            builder.normal_nodes -= 1
            return builder.marker(status)
    children = tuple(
        RawProjectionNode(
            child_name,
            RawProjectionKind.STRING,
            type_identity=None,
            scalar_payload=child_value,
            children=(),
        )
        for child_name, child_value in values
    )
    builder.normal_nodes += 6
    return RawProjectionNode(
        parent.field_name,
        RawProjectionKind.TASK160_RESULT_IDENTITY,
        type_identity=None,
        scalar_payload=None,
        children=children,
    )


def _project_value(
    value: object,
    field_name: str,
    depth: int,
    builder: _ProjectionBuilder,
) -> RawProjectionNode:
    try:
        if type(value) is Task160Result:
            return _project_identity(value, field_name, depth, builder)
        if value is None:
            return builder.scalar(depth, field_name, RawProjectionKind.NONE, None)
        if type(value) is bool:
            return builder.scalar(
                depth,
                field_name,
                RawProjectionKind.BOOLEAN,
                "true" if value else "false",
            )
        if type(value) is str:
            return builder.scalar(depth, field_name, RawProjectionKind.STRING, value)
        if type(value) is int:
            return builder.scalar(depth, field_name, RawProjectionKind.INTEGER, str(value))
        if type(value) is Decimal:
            return builder.scalar(depth, field_name, RawProjectionKind.DECIMAL, str(value))
        if isinstance(value, Enum):
            literal = value.value
            if type(literal) is str:
                return builder.scalar(
                    depth,
                    field_name,
                    RawProjectionKind.ENUM_LITERAL,
                    literal,
                )
        if type(value) is list or type(value) is tuple:
            base = builder.reserve(depth, field_name)
            if base is not None and base.kind is RawProjectionKind.LIMIT_MARKER:
                return base
            assert base is not None
            sequence_children: list[RawProjectionNode] = []
            for index, item in enumerate(value):
                child = _project_value(item, f"item-{index:06d}", depth + 1, builder)
                sequence_children.append(child)
                if builder.node_budget_exhausted:
                    break
            return RawProjectionNode(
                base.field_name,
                RawProjectionKind.SEQUENCE,
                type_identity=None,
                scalar_payload=None,
                children=tuple(sequence_children),
            )
        if type(value) is dict:
            base = builder.reserve(depth, field_name)
            if base is not None and base.kind is RawProjectionKind.LIMIT_MARKER:
                return base
            assert base is not None
            record_children: list[RawProjectionNode] = []
            for key, item in dict.items(value):
                if type(key) is str:
                    child = _project_value(item, key, depth + 1, builder)
                else:
                    builder.unsupported_object_present = True
                    key_node = _project_value(key, "key", depth + 2, builder)
                    value_node = _project_value(item, "value", depth + 2, builder)
                    child = RawProjectionNode(
                        "__TASK161_UNSUPPORTED_KEY__",
                        RawProjectionKind.RECORD,
                        type_identity=None,
                        scalar_payload=None,
                        children=(key_node, value_node),
                    )
                record_children.append(child)
                if builder.node_budget_exhausted:
                    break
            record_children.sort(key=_raw_child_sort_key)
            return RawProjectionNode(
                base.field_name,
                RawProjectionKind.RECORD,
                type_identity=None,
                scalar_payload=None,
                children=tuple(record_children),
            )
        type_identity, failure = _safe_type_identity(value)
        if failure is not None:
            return builder.marker(failure)
        assert type_identity is not None
        builder.unsupported_object_present = True
        return builder.scalar(
            depth,
            field_name,
            RawProjectionKind.UNSUPPORTED_OBJECT,
            None,
            type_identity=type_identity,
        )
    except BaseException:
        builder.unsupported_object_present = True
        return builder.marker("TYPE_IDENTITY_UNAVAILABLE")


def project_raw_request_with_diagnostics(value: object) -> RawProjectionOutcome:
    builder = _ProjectionBuilder()
    root = _project_value(value, "__root__", 0, builder)
    try:
        projection = Task161RawRequestProjection(
            TASK161_RAW_PROJECTION_SCHEMA_VERSION,
            root,
        )
    except BaseException:
        builder.reasons.add("TYPE_IDENTITY_UNAVAILABLE")
        projection = Task161RawRequestProjection(
            TASK161_RAW_PROJECTION_SCHEMA_VERSION,
            builder.marker("TYPE_IDENTITY_UNAVAILABLE"),
        )
    return RawProjectionOutcome(
        projection=projection,
        reasons=tuple(sorted(builder.reasons)),
        unsupported_object_present=builder.unsupported_object_present,
    )


def project_raw_request(value: object) -> Task161RawRequestProjection:
    return project_raw_request_with_diagnostics(value).projection


def to_provenance_payload_hash(bare_sha256_hex: str) -> str:
    if (
        type(bare_sha256_hex) is not str
        or len(bare_sha256_hex) != 64
        or any(char not in "0123456789abcdef" for char in bare_sha256_hex)
    ):
        raise ValueError("payload hash must be 64 lowercase hexadecimal characters")
    return "sha256:" + bare_sha256_hex


__all__ = [
    "RAW_BLOCKED_ID_PREFIX",
    "REQUEST_HASH_DOMAIN",
    "SUCCESS_ID_PREFIX",
    "SUCCESS_HASH_DOMAIN",
    "TASK161_RAW_BOUNDARY_SCHEMA_VERSION",
    "TASK161_RAW_MAX_DEPTH",
    "TASK161_RAW_MAX_NODES",
    "TASK161_RAW_MAX_SCALAR_BYTES",
    "TASK161_RAW_PROJECTION_DOMAIN",
    "TASK161_RAW_PROJECTION_NODE_DOMAIN",
    "TASK161_RAW_PROJECTION_SCHEMA_VERSION",
    "TASK161_REQUEST_HASH_DOMAIN",
    "TASK161_SUCCESS_HASH_DOMAIN",
    "TASK161_SUCCESS_PREIMAGE_FIELD_ORDER",
    "TASK161_TYPED_BLOCKED_HASH_DOMAIN",
    "TYPED_BLOCKED_ID_PREFIX",
    "RawProjectionOutcome",
    "canonical_projected_node_bytes",
    "method_catalog_bytes",
    "method_catalog_payload_bytes",
    "method_catalog_payload_hash",
    "project_raw_request",
    "project_raw_request_with_diagnostics",
    "provenance_semantic_inputs_bytes",
    "raw_blocked_hash",
    "raw_blocked_hash_fields",
    "raw_blocked_result_id",
    "raw_projection_node_bytes",
    "raw_request_projection_bytes",
    "raw_request_projection_hash",
    "request_canonical_bytes",
    "request_hash",
    "request_hash_fields",
    "result_id",
    "sha256_hex_from_framed_bytes",
    "success_canonical_bytes",
    "success_hash",
    "success_hash_from_inputs",
    "success_preimage_fields",
    "task160_result_identity_projection",
    "to_provenance_payload_hash",
    "typed_blocked_hash",
    "typed_blocked_hash_fields",
    "typed_blocked_result_id",
]
