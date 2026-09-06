"""Acyclic TASK162 success provenance payloads and graph construction."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID, uuid5

from hexagent.domain.provenance import (
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    ProvenanceNodeType,
)
from hexagent.exchangers.shell_tube.flow_arrangement_performance_method_authority.models import (
    PerformanceMethodCatalogAuthority,
    Task161Result,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.models import (
    Task038SuccessResult,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.models import Task160Result
from hexagent.exchangers.shell_tube.tube_side.canonical import (
    KIND_BYTES,
    KIND_ENUM,
    KIND_INT,
    KIND_STRING,
    KIND_TUPLE,
    frame_record,
    frame_tuple,
    frame_value,
    sha256_hex_from_framed_bytes,
)

from .canonical import (
    TASK162_PROVENANCE_NAMESPACE,
    case_authority_bytes,
    cross_producer_binding_bytes,
    task038_result_identity_projection,
    task160_result_identity_projection,
    task161_result_identity_projection,
)
from .models import (
    TASK162_IMPLEMENTATION_SOFTWARE_VERSION,
    TASK162_SCHEMA_VERSION,
    TASK162_SOURCE_DEFINITION_ID,
    TASK162_VERSION,
    Task038ResultIdentityProjection,
    Task160ResultIdentityProjection,
    Task161ResultIdentityProjection,
    Task162CaseAuthority,
    Task162CrossProducerBindingAuthority,
    Task162Provenance,
    Task162ProvenanceSemanticInputs,
)

REL_AUTHORIZES = "AUTHORIZES"
REL_SUPPLIES = "SUPPLIES"
REL_DEFINES = "DEFINES"
REL_PRODUCES = "PRODUCES"

TASK162_PROVENANCE_SOURCE_AUTHORITY_PAYLOAD_DOMAIN = (
    "TASK162_PROVENANCE_SOURCE_AUTHORITY_PAYLOAD_V1"
)
TASK162_PROVENANCE_TASK160_RESULT_PAYLOAD_DOMAIN = "TASK162_PROVENANCE_TASK160_RESULT_PAYLOAD_V1"
TASK162_PROVENANCE_TASK161_RESULT_PAYLOAD_DOMAIN = "TASK162_PROVENANCE_TASK161_RESULT_PAYLOAD_V1"
TASK162_PROVENANCE_TASK161_METHOD_CATALOG_PAYLOAD_DOMAIN = (
    "TASK162_PROVENANCE_TASK161_METHOD_CATALOG_PAYLOAD_V1"
)
TASK162_PROVENANCE_TASK038_RESULT_PAYLOAD_DOMAIN = "TASK162_PROVENANCE_TASK038_RESULT_PAYLOAD_V1"
TASK162_PROVENANCE_CROSS_PRODUCER_BINDING_PAYLOAD_DOMAIN = (
    "TASK162_PROVENANCE_CROSS_PRODUCER_BINDING_PAYLOAD_V1"
)
TASK162_PROVENANCE_CASE_AUTHORITY_PAYLOAD_DOMAIN = "TASK162_PROVENANCE_CASE_AUTHORITY_PAYLOAD_V1"
TASK162_PROVENANCE_MAGAZONI_SOURCE_PAYLOAD_DOMAIN = "TASK162_PROVENANCE_MAGAZONI_SOURCE_PAYLOAD_V1"
TASK162_PROVENANCE_NASA_SOURCE_PAYLOAD_DOMAIN = "TASK162_PROVENANCE_NASA_SOURCE_PAYLOAD_V1"
TASK162_PROVENANCE_CALCULATION_RUN_PAYLOAD_DOMAIN = "TASK162_PROVENANCE_CALCULATION_RUN_PAYLOAD_V1"
TASK162_PROVENANCE_RESULT_PAYLOAD_DOMAIN = "TASK162_PROVENANCE_RESULT_PAYLOAD_V1"

TASK162_SOURCE_AUTHORITY_NODE_PREFIX = "task162-provenance-source-authority-v1::"
TASK160_RESULT_EVIDENCE_NODE_PREFIX = "task162-provenance-task160-result-evidence-v1::"
TASK161_RESULT_EVIDENCE_NODE_PREFIX = "task162-provenance-task161-result-evidence-v1::"
TASK162_METHOD_CATALOG_NODE_PREFIX = "task162-provenance-method-catalog-v1::"
TASK038_RESULT_EVIDENCE_NODE_PREFIX = "task162-provenance-task038-result-evidence-v1::"
TASK162_BINDING_AUTHORITY_NODE_PREFIX = "task162-provenance-cross-producer-binding-v1::"
TASK162_CASE_AUTHORITY_NODE_PREFIX = "task162-provenance-case-authority-v1::"
MAGAZONI_SOURCE_NODE_PREFIX = "task162-provenance-magazoni-source-v1::"
NASA_SOURCE_NODE_PREFIX = "task162-provenance-nasa-source-v1::"
TASK162_CALCULATION_RUN_NODE_PREFIX = "task162-provenance-calculation-run-v1::"
TASK162_RESULT_NODE_PREFIX = "task162-provenance-result-v1::"


def _field(name: str, kind: bytes, payload: bytes) -> tuple[str, bytes, bytes]:
    return name, kind, payload


def _payload_hash(domain: str, fields: tuple[tuple[str, bytes, bytes], ...]) -> str:
    return sha256_hex_from_framed_bytes(frame_record(domain, fields))


def _strings(values: Iterable[str]) -> bytes:
    return frame_tuple(tuple(frame_value(KIND_STRING, value.encode("utf-8")) for value in values))


def _identity_fields(
    value: Task160ResultIdentityProjection
    | Task161ResultIdentityProjection
    | Task038ResultIdentityProjection,
) -> tuple[tuple[str, bytes, bytes], ...]:
    fields: list[tuple[str, bytes, bytes]] = [
        _field("schema_version", KIND_STRING, value.schema_version.encode("utf-8")),
    ]
    if isinstance(value, Task160ResultIdentityProjection):
        fields.append(_field("task160_version", KIND_STRING, value.task160_version.encode("utf-8")))
    elif isinstance(value, Task161ResultIdentityProjection):
        fields.extend(
            (
                _field("task161_version", KIND_STRING, value.task161_version.encode("utf-8")),
                _field(
                    "source_definition_id", KIND_STRING, value.source_definition_id.encode("utf-8")
                ),
            )
        )
    else:
        fields.extend(
            (
                _field("task038_version", KIND_STRING, value.task038_version.encode("utf-8")),
                _field("profile_id", KIND_STRING, value.profile_id.encode("utf-8")),
            )
        )
    fields.extend(
        (
            _field("request_hash", KIND_STRING, value.request_hash.encode("ascii")),
            _field("result_hash", KIND_STRING, value.result_hash.encode("ascii")),
            _field("result_id", KIND_STRING, value.result_id.encode("ascii")),
            _field("provenance_hash", KIND_STRING, value.provenance_hash.encode("utf-8")),
        )
    )
    return tuple(fields)


def source_authority_payload_fields() -> tuple[tuple[str, bytes, bytes], ...]:
    return (
        _field("source_definition_id", KIND_STRING, TASK162_SOURCE_DEFINITION_ID.encode("utf-8")),
        _field("source_issue_number", KIND_INT, b"229"),
        _field("source_revision", KIND_ENUM, b"R1"),
        _field("source_status", KIND_ENUM, b"FROZEN"),
    )


def source_authority_payload_hash() -> str:
    return _payload_hash(
        TASK162_PROVENANCE_SOURCE_AUTHORITY_PAYLOAD_DOMAIN,
        source_authority_payload_fields(),
    )


def task160_result_evidence_payload_fields(
    result: Task160Result,
) -> tuple[tuple[str, bytes, bytes], ...]:
    return _identity_fields(task160_result_identity_projection(result))


def task160_result_evidence_payload_hash(result: Task160Result) -> str:
    return _payload_hash(
        TASK162_PROVENANCE_TASK160_RESULT_PAYLOAD_DOMAIN,
        task160_result_evidence_payload_fields(result),
    )


def task161_result_evidence_payload_fields(
    result: Task161Result,
) -> tuple[tuple[str, bytes, bytes], ...]:
    return _identity_fields(task161_result_identity_projection(result))


def task161_result_evidence_payload_hash(result: Task161Result) -> str:
    return _payload_hash(
        TASK162_PROVENANCE_TASK161_RESULT_PAYLOAD_DOMAIN,
        task161_result_evidence_payload_fields(result),
    )


def task038_result_evidence_payload_fields(
    result: Task038SuccessResult,
) -> tuple[tuple[str, bytes, bytes], ...]:
    return _identity_fields(task038_result_identity_projection(result))


def task038_result_evidence_payload_hash(result: Task038SuccessResult) -> str:
    return _payload_hash(
        TASK162_PROVENANCE_TASK038_RESULT_PAYLOAD_DOMAIN,
        task038_result_evidence_payload_fields(result),
    )


def method_catalog_payload_fields(
    method_catalog: PerformanceMethodCatalogAuthority,
) -> tuple[tuple[str, bytes, bytes], ...]:
    names = (
        "method_authority_id",
        "method_family",
        "method_revision",
        "flow_arrangement_catalog_id",
        "engineering_source_id",
        "engineering_source_version",
        "engineering_source_location",
        "engineering_source_license",
        "relation_id",
        "supported_baffle_count_domain",
        "p_source_definition",
        "r_source_definition",
        "ntu_definition",
        "p_to_epsilon_mapping",
        "r_to_cr_mapping",
    )
    fields = [
        _field(name, KIND_STRING, getattr(method_catalog, name).encode("utf-8")) for name in names
    ]
    fields.append(
        _field(
            "supported_mixing_model_domain",
            KIND_TUPLE,
            _strings(method_catalog.supported_mixing_model_domain),
        )
    )
    return tuple(fields)


def method_catalog_payload_hash(method_catalog: PerformanceMethodCatalogAuthority) -> str:
    return _payload_hash(
        TASK162_PROVENANCE_TASK161_METHOD_CATALOG_PAYLOAD_DOMAIN,
        method_catalog_payload_fields(method_catalog),
    )


def cross_producer_binding_payload_hash(value: Task162CrossProducerBindingAuthority) -> str:
    return _payload_hash(
        TASK162_PROVENANCE_CROSS_PRODUCER_BINDING_PAYLOAD_DOMAIN,
        (_field("binding_identity", KIND_BYTES, cross_producer_binding_bytes(value)),),
    )


def case_authority_payload_hash(value: Task162CaseAuthority) -> str:
    return _payload_hash(
        TASK162_PROVENANCE_CASE_AUTHORITY_PAYLOAD_DOMAIN,
        (_field("case_identity", KIND_BYTES, case_authority_bytes(value)),),
    )


def magazoni_source_payload_fields() -> tuple[tuple[str, bytes, bytes], ...]:
    return (
        _field("engineering_source_id", KIND_STRING, b"MAGAZONI_2019"),
        _field("relation_id", KIND_STRING, b"MAGAZONI_1X1_MIXING_MODEL_2_P_RELATION_TABLE_7"),
        _field("equations_location", KIND_STRING, b"page 873, Equations (1)-(4)"),
        _field("table_location", KIND_STRING, b"page 880, Table 7"),
        _field("license", KIND_STRING, b"CC_BY_4_0"),
    )


def magazoni_source_payload_hash() -> str:
    return _payload_hash(
        TASK162_PROVENANCE_MAGAZONI_SOURCE_PAYLOAD_DOMAIN,
        magazoni_source_payload_fields(),
    )


def nasa_source_payload_fields() -> tuple[tuple[str, bytes, bytes], ...]:
    return (
        _field("engineering_source_id", KIND_STRING, b"NASA_TM_2020_220473"),
        _field("report_number", KIND_STRING, b"NASA/TM-2020-220473"),
        _field(
            "title",
            KIND_STRING,
            b"Development of a Thermal Management System for Electrified Aircraft",
        ),
        _field("role", KIND_ENUM, b"GENERIC_HX_DEFINITION"),
    )


def nasa_source_payload_hash() -> str:
    return _payload_hash(
        TASK162_PROVENANCE_NASA_SOURCE_PAYLOAD_DOMAIN, nasa_source_payload_fields()
    )


def calculation_run_payload_fields(
    *,
    request_hash: str,
    task160_hash: str,
    task161_hash: str,
    task038_hash: str,
    method_hash: str,
    binding_hash: str,
    case_hash: str,
    magazoni_hash: str,
    nasa_hash: str,
    selected_baffle_relation: str,
) -> tuple[tuple[str, bytes, bytes], ...]:
    return (
        _field("schema_version", KIND_STRING, TASK162_SCHEMA_VERSION.encode("utf-8")),
        _field("task162_version", KIND_STRING, TASK162_VERSION.encode("utf-8")),
        _field(
            "implementation_software_version",
            KIND_STRING,
            TASK162_IMPLEMENTATION_SOFTWARE_VERSION.encode("utf-8"),
        ),
        _field("source_definition_id", KIND_STRING, TASK162_SOURCE_DEFINITION_ID.encode("utf-8")),
        _field("request_hash", KIND_STRING, request_hash.encode("ascii")),
        _field("task160_result_evidence_payload_hash", KIND_STRING, task160_hash.encode("ascii")),
        _field("task161_result_evidence_payload_hash", KIND_STRING, task161_hash.encode("ascii")),
        _field("task038_result_evidence_payload_hash", KIND_STRING, task038_hash.encode("ascii")),
        _field("method_catalog_payload_hash", KIND_STRING, method_hash.encode("ascii")),
        _field("cross_producer_binding_payload_hash", KIND_STRING, binding_hash.encode("ascii")),
        _field("case_authority_payload_hash", KIND_STRING, case_hash.encode("ascii")),
        _field("magazoni_source_payload_hash", KIND_STRING, magazoni_hash.encode("ascii")),
        _field("nasa_source_payload_hash", KIND_STRING, nasa_hash.encode("ascii")),
        _field("selected_baffle_relation", KIND_STRING, selected_baffle_relation.encode("ascii")),
        _field("scope", KIND_ENUM, b"SUCCESS"),
    )


def calculation_run_payload_hash(**kwargs: str) -> str:
    return _payload_hash(
        TASK162_PROVENANCE_CALCULATION_RUN_PAYLOAD_DOMAIN,
        calculation_run_payload_fields(**kwargs),
    )


def build_provenance_semantic_inputs(
    *,
    request_hash: str,
    task160_result: Task160Result,
    task161_result: Task161Result,
    task038_result: Task038SuccessResult,
    method_catalog: PerformanceMethodCatalogAuthority,
    binding_authority: Task162CrossProducerBindingAuthority,
    case_authority: Task162CaseAuthority,
    selected_baffle_relation: str,
) -> Task162ProvenanceSemanticInputs:
    source_hash = source_authority_payload_hash()
    task160_hash = task160_result_evidence_payload_hash(task160_result)
    task161_hash = task161_result_evidence_payload_hash(task161_result)
    method_hash = method_catalog_payload_hash(method_catalog)
    task038_hash = task038_result_evidence_payload_hash(task038_result)
    binding_hash = cross_producer_binding_payload_hash(binding_authority)
    case_hash = case_authority_payload_hash(case_authority)
    magazoni_hash = magazoni_source_payload_hash()
    nasa_hash = nasa_source_payload_hash()
    calculation_hash = calculation_run_payload_hash(
        request_hash=request_hash,
        task160_hash=task160_hash,
        task161_hash=task161_hash,
        task038_hash=task038_hash,
        method_hash=method_hash,
        binding_hash=binding_hash,
        case_hash=case_hash,
        magazoni_hash=magazoni_hash,
        nasa_hash=nasa_hash,
        selected_baffle_relation=selected_baffle_relation,
    )
    return Task162ProvenanceSemanticInputs(
        source_authority_payload_hash=source_hash,
        task160_result_evidence_payload_hash=task160_hash,
        task161_result_evidence_payload_hash=task161_hash,
        task161_method_catalog_payload_hash=method_hash,
        task038_result_evidence_payload_hash=task038_hash,
        cross_producer_binding_payload_hash=binding_hash,
        case_authority_payload_hash=case_hash,
        magazoni_source_payload_hash=magazoni_hash,
        nasa_source_payload_hash=nasa_hash,
        calculation_run_payload_hash=calculation_hash,
    )


def _node(
    *,
    prefix: str,
    node_type: ProvenanceNodeType,
    label: str,
    payload_hash: str,
    node_id: UUID | None = None,
) -> ProvenanceNode:
    return ProvenanceNode(
        node_id=node_id or uuid5(TASK162_PROVENANCE_NAMESPACE, prefix + payload_hash),
        node_type=node_type,
        label=label,
        metadata=(),
        payload_hash="sha256:" + payload_hash,
    )


def build_success_provenance(
    *,
    request_hash: str,
    task160_result: Task160Result,
    task161_result: Task161Result,
    task038_result: Task038SuccessResult,
    method_catalog: PerformanceMethodCatalogAuthority,
    binding_authority: Task162CrossProducerBindingAuthority,
    case_authority: Task162CaseAuthority,
    selected_baffle_relation: str,
    result_hash: str,
    result_id: UUID,
) -> tuple[Task162Provenance, Task162ProvenanceSemanticInputs]:
    semantic = build_provenance_semantic_inputs(
        request_hash=request_hash,
        task160_result=task160_result,
        task161_result=task161_result,
        task038_result=task038_result,
        method_catalog=method_catalog,
        binding_authority=binding_authority,
        case_authority=case_authority,
        selected_baffle_relation=selected_baffle_relation,
    )
    source = _node(
        prefix=TASK162_SOURCE_AUTHORITY_NODE_PREFIX,
        node_type=ProvenanceNodeType.EXTERNAL,
        label="TASK162_SOURCE_AUTHORITY",
        payload_hash=semantic.source_authority_payload_hash,
    )
    task160 = _node(
        prefix=TASK160_RESULT_EVIDENCE_NODE_PREFIX,
        node_type=ProvenanceNodeType.EXTERNAL,
        label="TASK160_RESULT_EVIDENCE",
        payload_hash=semantic.task160_result_evidence_payload_hash,
    )
    task161 = _node(
        prefix=TASK161_RESULT_EVIDENCE_NODE_PREFIX,
        node_type=ProvenanceNodeType.EXTERNAL,
        label="TASK161_RESULT_EVIDENCE",
        payload_hash=semantic.task161_result_evidence_payload_hash,
    )
    method = _node(
        prefix=TASK162_METHOD_CATALOG_NODE_PREFIX,
        node_type=ProvenanceNodeType.CORRELATION,
        label="TASK162_METHOD_CATALOG",
        payload_hash=semantic.task161_method_catalog_payload_hash,
    )
    task038 = _node(
        prefix=TASK038_RESULT_EVIDENCE_NODE_PREFIX,
        node_type=ProvenanceNodeType.EXTERNAL,
        label="TASK038_RESULT_EVIDENCE",
        payload_hash=semantic.task038_result_evidence_payload_hash,
    )
    binding = _node(
        prefix=TASK162_BINDING_AUTHORITY_NODE_PREFIX,
        node_type=ProvenanceNodeType.EXTERNAL,
        label="CROSS_PRODUCER_BINDING_AUTHORITY",
        payload_hash=semantic.cross_producer_binding_payload_hash,
    )
    case = _node(
        prefix=TASK162_CASE_AUTHORITY_NODE_PREFIX,
        node_type=ProvenanceNodeType.EXTERNAL,
        label="TASK162_CASE_AUTHORITY",
        payload_hash=semantic.case_authority_payload_hash,
    )
    magazoni = _node(
        prefix=MAGAZONI_SOURCE_NODE_PREFIX,
        node_type=ProvenanceNodeType.EXTERNAL,
        label="MAGAZONI_SOURCE",
        payload_hash=semantic.magazoni_source_payload_hash,
    )
    nasa = _node(
        prefix=NASA_SOURCE_NODE_PREFIX,
        node_type=ProvenanceNodeType.EXTERNAL,
        label="NASA_GENERIC_DEFINITION_SOURCE",
        payload_hash=semantic.nasa_source_payload_hash,
    )
    calculation = _node(
        prefix=TASK162_CALCULATION_RUN_NODE_PREFIX,
        node_type=ProvenanceNodeType.CALCULATION_RUN,
        label="TASK162_CALCULATION_RUN",
        payload_hash=semantic.calculation_run_payload_hash,
    )
    result = _node(
        prefix=TASK162_RESULT_NODE_PREFIX,
        node_type=ProvenanceNodeType.RESULT,
        label="TASK162_RESULT",
        payload_hash=result_hash,
        node_id=result_id,
    )
    nodes = (
        source,
        task160,
        task161,
        method,
        task038,
        binding,
        case,
        magazoni,
        nasa,
        calculation,
        result,
    )
    edges = (
        ProvenanceEdge(
            source_id=source.node_id,
            target_id=calculation.node_id,
            relation=REL_AUTHORIZES,
            metadata=(),
        ),
        ProvenanceEdge(
            source_id=task160.node_id,
            target_id=calculation.node_id,
            relation=REL_SUPPLIES,
            metadata=(),
        ),
        ProvenanceEdge(
            source_id=task161.node_id,
            target_id=calculation.node_id,
            relation=REL_SUPPLIES,
            metadata=(),
        ),
        ProvenanceEdge(
            source_id=method.node_id,
            target_id=calculation.node_id,
            relation=REL_DEFINES,
            metadata=(),
        ),
        ProvenanceEdge(
            source_id=task038.node_id,
            target_id=calculation.node_id,
            relation=REL_SUPPLIES,
            metadata=(),
        ),
        ProvenanceEdge(
            source_id=binding.node_id,
            target_id=calculation.node_id,
            relation=REL_SUPPLIES,
            metadata=(),
        ),
        ProvenanceEdge(
            source_id=case.node_id,
            target_id=calculation.node_id,
            relation=REL_SUPPLIES,
            metadata=(),
        ),
        ProvenanceEdge(
            source_id=magazoni.node_id,
            target_id=calculation.node_id,
            relation=REL_SUPPLIES,
            metadata=(),
        ),
        ProvenanceEdge(
            source_id=nasa.node_id,
            target_id=calculation.node_id,
            relation=REL_SUPPLIES,
            metadata=(),
        ),
        ProvenanceEdge(
            source_id=calculation.node_id,
            target_id=result.node_id,
            relation=REL_PRODUCES,
            metadata=(),
        ),
    )
    graph = ProvenanceGraph(schema_version="1.0", nodes=nodes, edges=edges)
    return Task162Provenance(provenance_hash=graph.compute_hash(), graph=graph), semantic


def provenance_payload_field_audit() -> dict[str, tuple[str, ...]]:
    """Return exact fields for review and cycle-audit tooling."""

    return {
        TASK162_PROVENANCE_SOURCE_AUTHORITY_PAYLOAD_DOMAIN: tuple(
            name for name, _, _ in source_authority_payload_fields()
        ),
        TASK162_PROVENANCE_TASK160_RESULT_PAYLOAD_DOMAIN: (
            "schema_version",
            "task160_version",
            "request_hash",
            "result_hash",
            "result_id",
            "provenance_hash",
        ),
        TASK162_PROVENANCE_TASK161_RESULT_PAYLOAD_DOMAIN: (
            "schema_version",
            "task161_version",
            "source_definition_id",
            "request_hash",
            "result_hash",
            "result_id",
            "provenance_hash",
        ),
        TASK162_PROVENANCE_TASK161_METHOD_CATALOG_PAYLOAD_DOMAIN: (
            "method_authority_id",
            "method_family",
            "method_revision",
            "flow_arrangement_catalog_id",
            "engineering_source_id",
            "engineering_source_version",
            "engineering_source_location",
            "engineering_source_license",
            "relation_id",
            "supported_baffle_count_domain",
            "p_source_definition",
            "r_source_definition",
            "ntu_definition",
            "p_to_epsilon_mapping",
            "r_to_cr_mapping",
            "supported_mixing_model_domain",
        ),
        TASK162_PROVENANCE_TASK038_RESULT_PAYLOAD_DOMAIN: (
            "schema_version",
            "task038_version",
            "profile_id",
            "request_hash",
            "result_hash",
            "result_id",
            "provenance_hash",
        ),
        TASK162_PROVENANCE_CROSS_PRODUCER_BINDING_PAYLOAD_DOMAIN: ("binding_identity",),
        TASK162_PROVENANCE_CASE_AUTHORITY_PAYLOAD_DOMAIN: ("case_identity",),
        TASK162_PROVENANCE_MAGAZONI_SOURCE_PAYLOAD_DOMAIN: tuple(
            name for name, _, _ in magazoni_source_payload_fields()
        ),
        TASK162_PROVENANCE_NASA_SOURCE_PAYLOAD_DOMAIN: tuple(
            name for name, _, _ in nasa_source_payload_fields()
        ),
        TASK162_PROVENANCE_CALCULATION_RUN_PAYLOAD_DOMAIN: tuple(
            name
            for name, _, _ in calculation_run_payload_fields(
                request_hash="0" * 64,
                task160_hash="1" * 64,
                task161_hash="2" * 64,
                task038_hash="3" * 64,
                method_hash="4" * 64,
                binding_hash="5" * 64,
                case_hash="6" * 64,
                magazoni_hash="7" * 64,
                nasa_hash="8" * 64,
                selected_baffle_relation="P_1",
            )
        ),
        TASK162_PROVENANCE_RESULT_PAYLOAD_DOMAIN: ("result_hash",),
    }


__all__ = [
    "REL_AUTHORIZES",
    "REL_SUPPLIES",
    "REL_DEFINES",
    "REL_PRODUCES",
    "TASK162_PROVENANCE_SOURCE_AUTHORITY_PAYLOAD_DOMAIN",
    "TASK162_PROVENANCE_TASK160_RESULT_PAYLOAD_DOMAIN",
    "TASK162_PROVENANCE_TASK161_RESULT_PAYLOAD_DOMAIN",
    "TASK162_PROVENANCE_TASK161_METHOD_CATALOG_PAYLOAD_DOMAIN",
    "TASK162_PROVENANCE_TASK038_RESULT_PAYLOAD_DOMAIN",
    "TASK162_PROVENANCE_CROSS_PRODUCER_BINDING_PAYLOAD_DOMAIN",
    "TASK162_PROVENANCE_CASE_AUTHORITY_PAYLOAD_DOMAIN",
    "TASK162_PROVENANCE_MAGAZONI_SOURCE_PAYLOAD_DOMAIN",
    "TASK162_PROVENANCE_NASA_SOURCE_PAYLOAD_DOMAIN",
    "TASK162_PROVENANCE_CALCULATION_RUN_PAYLOAD_DOMAIN",
    "TASK162_PROVENANCE_RESULT_PAYLOAD_DOMAIN",
    "build_provenance_semantic_inputs",
    "build_success_provenance",
    "provenance_payload_field_audit",
]
