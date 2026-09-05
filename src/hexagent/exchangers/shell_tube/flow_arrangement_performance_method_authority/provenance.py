"""TASK161 success provenance payloads and deterministic graph composition."""

from __future__ import annotations

from uuid import UUID, uuid5

from hexagent.domain.provenance import (
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    ProvenanceNodeType,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.models import Task160Result
from hexagent.exchangers.shell_tube.tube_side.canonical import (
    KIND_ENUM,
    KIND_INT,
    KIND_STRING,
    frame_record,
    frame_tuple,
    frame_value,
    sha256_hex_from_framed_bytes,
)

from .canonical import (
    method_catalog_payload_hash,
    task160_result_identity_projection,
    to_provenance_payload_hash,
)
from .models import (
    TASK161_IMPLEMENTATION_SOFTWARE_VERSION,
    TASK161_PROVENANCE_NAMESPACE,
    TASK161_SCHEMA_VERSION,
    TASK161_SOURCE_DEFINITION_ID,
    TASK161_VERSION,
    PerformanceMethodCatalogAuthority,
    Task161Provenance,
    Task161ProvenanceSemanticInputs,
)

REL_AUTHORIZES = "AUTHORIZES"
REL_SUPPLIES = "SUPPLIES"
REL_DEFINES = "DEFINES"
REL_PRODUCES = "PRODUCES"

TASK161_PROVENANCE_SOURCE_AUTHORITY_PAYLOAD_DOMAIN = (
    "TASK161_PROVENANCE_SOURCE_AUTHORITY_PAYLOAD_V1"
)
TASK161_PROVENANCE_TASK160_RESULT_PAYLOAD_DOMAIN = "TASK161_PROVENANCE_TASK160_RESULT_PAYLOAD_V1"
TASK161_PROVENANCE_MAGAZONI_SOURCE_PAYLOAD_DOMAIN = "TASK161_PROVENANCE_MAGAZONI_SOURCE_PAYLOAD_V1"
TASK161_PROVENANCE_NASA_SOURCE_PAYLOAD_DOMAIN = "TASK161_PROVENANCE_NASA_SOURCE_PAYLOAD_V1"
TASK161_PROVENANCE_METHOD_CATALOG_PAYLOAD_DOMAIN = "TASK161_PROVENANCE_METHOD_CATALOG_PAYLOAD_V1"
TASK161_PROVENANCE_CALCULATION_RUN_PAYLOAD_DOMAIN = "TASK161_PROVENANCE_CALCULATION_RUN_PAYLOAD_V1"
TASK161_PROVENANCE_RESULT_PAYLOAD_DOMAIN = "TASK161_PROVENANCE_RESULT_PAYLOAD_V1"

SOURCE_AUTHORITY_NODE_PREFIX = "task161-provenance-source-authority-v1::"
TASK160_RESULT_NODE_PREFIX = "task161-provenance-task160-result-evidence-v1::"
MAGAZONI_SOURCE_NODE_PREFIX = "task161-provenance-magazoni-source-v1::"
NASA_SOURCE_NODE_PREFIX = "task161-provenance-nasa-source-v1::"
METHOD_CATALOG_NODE_PREFIX = "task161-provenance-method-catalog-v1::"
CALCULATION_RUN_NODE_PREFIX = "task161-provenance-calculation-run-v1::"
RESULT_NODE_PREFIX = "task161-provenance-result-v1::"


def _field(name: str, kind: bytes, payload: bytes) -> tuple[str, bytes, bytes]:
    return name, kind, payload


def _strings(values: tuple[str, ...]) -> bytes:
    return frame_tuple([frame_value(KIND_STRING, value.encode("utf-8")) for value in values])


def _payload_hash(domain: str, fields: tuple[tuple[str, bytes, bytes], ...]) -> str:
    return sha256_hex_from_framed_bytes(frame_record(domain, fields))


def source_authority_payload_fields() -> tuple[tuple[str, bytes, bytes], ...]:
    return (
        _field("source_definition_id", KIND_STRING, TASK161_SOURCE_DEFINITION_ID.encode("utf-8")),
        _field("source_issue_number", KIND_INT, b"225"),
        _field("source_revision", KIND_ENUM, b"R8"),
        _field("source_status", KIND_ENUM, b"FROZEN"),
    )


def source_authority_payload_hash() -> str:
    return _payload_hash(
        TASK161_PROVENANCE_SOURCE_AUTHORITY_PAYLOAD_DOMAIN,
        source_authority_payload_fields(),
    )


def task160_result_evidence_payload_fields(
    result: Task160Result,
) -> tuple[tuple[str, bytes, bytes], ...]:
    identity = task160_result_identity_projection(result)
    return (
        _field("schema_version", KIND_STRING, identity.schema_version.encode("utf-8")),
        _field("task160_version", KIND_STRING, identity.task160_version.encode("utf-8")),
        _field("request_hash", KIND_STRING, identity.request_hash.encode("ascii")),
        _field("result_hash", KIND_STRING, identity.result_hash.encode("ascii")),
        _field("result_id", KIND_STRING, identity.result_id.encode("ascii")),
        _field("provenance_hash", KIND_STRING, identity.provenance_hash.encode("utf-8")),
    )


def task160_result_evidence_payload_hash(result: Task160Result) -> str:
    return _payload_hash(
        TASK161_PROVENANCE_TASK160_RESULT_PAYLOAD_DOMAIN,
        task160_result_evidence_payload_fields(result),
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
        TASK161_PROVENANCE_MAGAZONI_SOURCE_PAYLOAD_DOMAIN,
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


def nasa_generic_definition_source_payload_hash() -> str:
    return _payload_hash(
        TASK161_PROVENANCE_NASA_SOURCE_PAYLOAD_DOMAIN,
        nasa_source_payload_fields(),
    )


def calculation_run_payload_fields(
    *,
    request_hash: str,
    task160_result_evidence_hash: str,
    source_authority_hash: str,
    magazoni_hash: str,
    nasa_hash: str,
    method_catalog_hash: str,
    schema_version: str = TASK161_SCHEMA_VERSION,
    task161_version: str = TASK161_VERSION,
    implementation_software_version: str = TASK161_IMPLEMENTATION_SOFTWARE_VERSION,
) -> tuple[tuple[str, bytes, bytes], ...]:
    """Return calculation-run fields; none contain final TASK161 identity."""
    return (
        _field("schema_version", KIND_STRING, schema_version.encode("utf-8")),
        _field("task161_version", KIND_STRING, task161_version.encode("utf-8")),
        _field(
            "implementation_software_version",
            KIND_STRING,
            implementation_software_version.encode("utf-8"),
        ),
        _field("request_hash", KIND_STRING, request_hash.encode("ascii")),
        _field(
            "task160_result_evidence_payload_hash",
            KIND_STRING,
            task160_result_evidence_hash.encode("ascii"),
        ),
        _field("source_authority_payload_hash", KIND_STRING, source_authority_hash.encode("ascii")),
        _field("magazoni_source_payload_hash", KIND_STRING, magazoni_hash.encode("ascii")),
        _field(
            "nasa_generic_definition_source_payload_hash",
            KIND_STRING,
            nasa_hash.encode("ascii"),
        ),
        _field("method_catalog_payload_hash", KIND_STRING, method_catalog_hash.encode("ascii")),
        _field("source_definition_id", KIND_STRING, TASK161_SOURCE_DEFINITION_ID.encode("utf-8")),
        _field("scope", KIND_ENUM, b"SUCCESS"),
    )


def calculation_run_payload_hash(
    *,
    request_hash: str,
    task160_result_evidence_hash: str,
    source_authority_hash: str,
    magazoni_hash: str,
    nasa_hash: str,
    method_catalog_hash: str,
    schema_version: str = TASK161_SCHEMA_VERSION,
    task161_version: str = TASK161_VERSION,
    implementation_software_version: str = TASK161_IMPLEMENTATION_SOFTWARE_VERSION,
) -> str:
    return _payload_hash(
        TASK161_PROVENANCE_CALCULATION_RUN_PAYLOAD_DOMAIN,
        calculation_run_payload_fields(
            request_hash=request_hash,
            task160_result_evidence_hash=task160_result_evidence_hash,
            source_authority_hash=source_authority_hash,
            magazoni_hash=magazoni_hash,
            nasa_hash=nasa_hash,
            method_catalog_hash=method_catalog_hash,
            schema_version=schema_version,
            task161_version=task161_version,
            implementation_software_version=implementation_software_version,
        ),
    )


def build_provenance_semantic_inputs(
    *,
    request_hash: str,
    task160_result: Task160Result,
    method_catalog: PerformanceMethodCatalogAuthority,
    schema_version: str = TASK161_SCHEMA_VERSION,
    task161_version: str = TASK161_VERSION,
    implementation_software_version: str = TASK161_IMPLEMENTATION_SOFTWARE_VERSION,
) -> Task161ProvenanceSemanticInputs:
    source_hash = source_authority_payload_hash()
    task160_hash = task160_result_evidence_payload_hash(task160_result)
    magazoni_hash = magazoni_source_payload_hash()
    nasa_hash = nasa_generic_definition_source_payload_hash()
    method_hash = method_catalog_payload_hash(method_catalog)
    calculation_hash = calculation_run_payload_hash(
        request_hash=request_hash,
        task160_result_evidence_hash=task160_hash,
        source_authority_hash=source_hash,
        magazoni_hash=magazoni_hash,
        nasa_hash=nasa_hash,
        method_catalog_hash=method_hash,
        schema_version=schema_version,
        task161_version=task161_version,
        implementation_software_version=implementation_software_version,
    )
    return Task161ProvenanceSemanticInputs(
        source_authority_payload_hash=source_hash,
        task160_result_evidence_payload_hash=task160_hash,
        magazoni_source_payload_hash=magazoni_hash,
        nasa_generic_definition_source_payload_hash=nasa_hash,
        method_catalog_payload_hash=method_hash,
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
    resolved_id = node_id or uuid5(UUID(TASK161_PROVENANCE_NAMESPACE), prefix + payload_hash)
    return ProvenanceNode(
        node_id=resolved_id,
        node_type=node_type,
        label=label,
        metadata=(),
        payload_hash=to_provenance_payload_hash(payload_hash),
    )


def build_success_provenance(
    *,
    request_hash: str,
    task160_result: Task160Result,
    method_catalog: PerformanceMethodCatalogAuthority,
    result_hash: str,
    result_id: UUID,
    schema_version: str = TASK161_SCHEMA_VERSION,
    task161_version: str = TASK161_VERSION,
    implementation_software_version: str = TASK161_IMPLEMENTATION_SOFTWARE_VERSION,
) -> tuple[Task161Provenance, Task161ProvenanceSemanticInputs]:
    semantic = build_provenance_semantic_inputs(
        request_hash=request_hash,
        task160_result=task160_result,
        method_catalog=method_catalog,
        schema_version=schema_version,
        task161_version=task161_version,
        implementation_software_version=implementation_software_version,
    )
    source = _node(
        prefix=SOURCE_AUTHORITY_NODE_PREFIX,
        node_type=ProvenanceNodeType.EXTERNAL,
        label="TASK161_SOURCE_AUTHORITY",
        payload_hash=semantic.source_authority_payload_hash,
    )
    task160 = _node(
        prefix=TASK160_RESULT_NODE_PREFIX,
        node_type=ProvenanceNodeType.EXTERNAL,
        label="TASK160_RESULT_EVIDENCE",
        payload_hash=semantic.task160_result_evidence_payload_hash,
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
        payload_hash=semantic.nasa_generic_definition_source_payload_hash,
    )
    method = _node(
        prefix=METHOD_CATALOG_NODE_PREFIX,
        node_type=ProvenanceNodeType.CORRELATION,
        label="TASK161_METHOD_CATALOG",
        payload_hash=semantic.method_catalog_payload_hash,
    )
    calculation = _node(
        prefix=CALCULATION_RUN_NODE_PREFIX,
        node_type=ProvenanceNodeType.CALCULATION_RUN,
        label="TASK161_CALCULATION_RUN",
        payload_hash=semantic.calculation_run_payload_hash,
    )
    result = _node(
        prefix=RESULT_NODE_PREFIX,
        node_type=ProvenanceNodeType.RESULT,
        label="TASK161_RESULT",
        payload_hash=result_hash,
        node_id=result_id,
    )
    nodes = (source, task160, magazoni, nasa, method, calculation, result)
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
            source_id=method.node_id,
            target_id=calculation.node_id,
            relation=REL_DEFINES,
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
    return Task161Provenance(graph=graph, provenance_hash=graph.compute_hash()), semantic


def provenance_payload_field_audit() -> dict[str, tuple[str, ...]]:
    """Machine-readable audit summary for the six semantic payload domains."""
    return {
        TASK161_PROVENANCE_SOURCE_AUTHORITY_PAYLOAD_DOMAIN: tuple(
            field[0] for field in source_authority_payload_fields()
        ),
        TASK161_PROVENANCE_TASK160_RESULT_PAYLOAD_DOMAIN: (
            "schema_version",
            "task160_version",
            "request_hash",
            "result_hash",
            "result_id",
            "provenance_hash",
        ),
        TASK161_PROVENANCE_MAGAZONI_SOURCE_PAYLOAD_DOMAIN: tuple(
            field[0] for field in magazoni_source_payload_fields()
        ),
        TASK161_PROVENANCE_NASA_SOURCE_PAYLOAD_DOMAIN: tuple(
            field[0] for field in nasa_source_payload_fields()
        ),
        TASK161_PROVENANCE_METHOD_CATALOG_PAYLOAD_DOMAIN: (
            "method_catalog_fields_excluding_authority_hash",
        ),
        TASK161_PROVENANCE_CALCULATION_RUN_PAYLOAD_DOMAIN: tuple(
            field[0]
            for field in calculation_run_payload_fields(
                request_hash="0" * 64,
                task160_result_evidence_hash="1" * 64,
                source_authority_hash="2" * 64,
                magazoni_hash="3" * 64,
                nasa_hash="4" * 64,
                method_catalog_hash="5" * 64,
            )
        ),
    }


__all__ = [
    "CALCULATION_RUN_NODE_PREFIX",
    "MAGAZONI_SOURCE_NODE_PREFIX",
    "METHOD_CATALOG_NODE_PREFIX",
    "NASA_SOURCE_NODE_PREFIX",
    "REL_AUTHORIZES",
    "REL_DEFINES",
    "REL_PRODUCES",
    "REL_SUPPLIES",
    "RESULT_NODE_PREFIX",
    "SOURCE_AUTHORITY_NODE_PREFIX",
    "TASK160_RESULT_NODE_PREFIX",
    "TASK161_PROVENANCE_CALCULATION_RUN_PAYLOAD_DOMAIN",
    "TASK161_PROVENANCE_MAGAZONI_SOURCE_PAYLOAD_DOMAIN",
    "TASK161_PROVENANCE_METHOD_CATALOG_PAYLOAD_DOMAIN",
    "TASK161_PROVENANCE_NASA_SOURCE_PAYLOAD_DOMAIN",
    "TASK161_PROVENANCE_RESULT_PAYLOAD_DOMAIN",
    "TASK161_PROVENANCE_SOURCE_AUTHORITY_PAYLOAD_DOMAIN",
    "TASK161_PROVENANCE_TASK160_RESULT_PAYLOAD_DOMAIN",
    "build_provenance_semantic_inputs",
    "build_success_provenance",
    "calculation_run_payload_fields",
    "calculation_run_payload_hash",
    "magazoni_source_payload_fields",
    "magazoni_source_payload_hash",
    "nasa_generic_definition_source_payload_hash",
    "nasa_source_payload_fields",
    "provenance_payload_field_audit",
    "source_authority_payload_fields",
    "source_authority_payload_hash",
    "task160_result_evidence_payload_fields",
    "task160_result_evidence_payload_hash",
]
