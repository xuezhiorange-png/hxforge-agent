"""TASK160 provenance DAG composition."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID, uuid5

from hexagent.domain.provenance import (
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    ProvenanceNodeType,
)

from .canonical import (
    frame_record,
    sha256_hex_from_framed_bytes,
    to_provenance_payload_hash,
)
from .models import (
    CalculationRunScope,
    FailureStage,
    Task160AdapterEvidence,
    Task160Provenance,
    Task160ProvenanceInputs,
)

NAMESPACE = UUID("a1600000-0000-5000-8000-000000000160")
SOURCE_AUTHORITY_BARE_HASH = "58a4d9c8cb511ab4db00a25094fd2004af7a52b42ce4a5ba88e0f3f72cac75e1"
SOURCE_AUTHORITY_NODE_ID = UUID("bf2dcd7f-5fa3-5959-9e08-d9cf725dc364")

REL_AUTHORIZES = "AUTHORIZES"
REL_SUPPLIES = "SUPPLIES"
REL_ADAPTS = "ADAPTS"
REL_PRODUCES = "PRODUCES"
REL_PRODUCES_BLOCKED_RESULT = "PRODUCES_BLOCKED_RESULT"


def _payload(domain: str, fields: tuple[tuple[str, bytes, bytes], ...]) -> str:
    return sha256_hex_from_framed_bytes(frame_record(domain, fields))


def _node_id(prefix: str, payload_hash: str) -> UUID:
    return uuid5(NAMESPACE, prefix + payload_hash)


def _external_node(
    prefix: str,
    node_type: ProvenanceNodeType,
    label: str,
    payload_hash: str,
    node_id: UUID | None = None,
) -> ProvenanceNode:
    return ProvenanceNode(
        node_id=node_id or _node_id(prefix, payload_hash),
        node_type=node_type,
        label=label,
        metadata=(),
        payload_hash=to_provenance_payload_hash(payload_hash),
    )


def source_authority_node() -> ProvenanceNode:
    calculated = _payload(
        "TASK160_PROVENANCE_SOURCE_AUTHORITY_PAYLOAD_V1",
        (
            ("source_definition_id", b"STRING", b"TASK160-SOURCE-DEFINITION-R1-ISSUE-221"),
            ("source_issue_number", b"INT", b"221"),
            ("source_status", b"ENUM", b"FROZEN"),
        ),
    )
    if calculated != SOURCE_AUTHORITY_BARE_HASH:
        raise RuntimeError("frozen TASK160 source-authority payload changed")
    return _external_node(
        "task160-provenance-source-authority-v1::",
        ProvenanceNodeType.EXTERNAL,
        "TASK160_SOURCE_AUTHORITY",
        calculated,
        SOURCE_AUTHORITY_NODE_ID,
    )


def _producer_node(identity: str) -> ProvenanceNode:
    digest = _payload(
        "TASK160_PROVENANCE_PRODUCER_IDENTITY_PAYLOAD_V1",
        (("producer_identity", b"STRING", identity.encode("utf-8")),),
    )
    return _external_node(
        "task160-provenance-producer-identity-v1::",
        ProvenanceNodeType.EXTERNAL,
        "TASK160_PRODUCER_IDENTITY",
        digest,
    )


def _upstream_node(identity_hash: str) -> ProvenanceNode:
    digest = _payload(
        "TASK160_PROVENANCE_UPSTREAM_PAYLOAD_V1",
        (("upstream_identity_hash", b"STRING", identity_hash.encode("ascii")),),
    )
    return _external_node(
        "task160-provenance-upstream-identity-v1::",
        ProvenanceNodeType.EXTERNAL,
        "TASK160_UPSTREAM_IDENTITY",
        digest,
    )


def _source_evidence_node(ref: str) -> ProvenanceNode:
    digest = _payload(
        "TASK160_PROVENANCE_SOURCE_EVIDENCE_PAYLOAD_V1",
        (("source_evidence_ref", b"STRING", ref.encode("utf-8")),),
    )
    return _external_node(
        "task160-provenance-source-evidence-v1::",
        ProvenanceNodeType.EXTERNAL,
        "TASK160_SOURCE_EVIDENCE",
        digest,
    )


def _adapter_node(evidence: Task160AdapterEvidence) -> ProvenanceNode:
    digest = _payload(
        "TASK160_PROVENANCE_ADAPTER_PAYLOAD_V1",
        (
            ("adapter_id", b"STRING", evidence.adapter_id.encode("utf-8")),
            ("source_task_id", b"STRING", evidence.source_task_id.encode("utf-8")),
            (
                "source_result_identity",
                b"NONE" if evidence.source_result_identity is None else b"STRING",
                b""
                if evidence.source_result_identity is None
                else evidence.source_result_identity.encode("utf-8"),
            ),
            ("admitted_fields", b"TUPLE", _tuple_strings(evidence.admitted_fields)),
            ("rejected_fields", b"TUPLE", _tuple_strings(evidence.rejected_fields)),
            ("source_evidence_refs", b"TUPLE", _tuple_strings(evidence.source_evidence_refs)),
            ("evidence_hash", b"STRING", evidence.evidence_hash.encode("ascii")),
        ),
    )
    return _external_node(
        "task160-provenance-adapter-evidence-v1::",
        ProvenanceNodeType.INTERMEDIATE,
        "TASK160_ADAPTER_EVIDENCE",
        digest,
    )


def _tuple_strings(values: Iterable[str]) -> bytes:
    from hexagent.exchangers.shell_tube.tube_side.canonical import frame_tuple, frame_value

    return frame_tuple([frame_value(b"STRING", item.encode("utf-8")) for item in values])


def _calculation_node(
    *,
    schema_version: str,
    task160_version: str,
    implementation_software_version: str,
    input_hash: str,
    source_definition_id: str,
    failure_stage: FailureStage | None,
    provenance_inputs: Task160ProvenanceInputs,
    scope: CalculationRunScope,
) -> ProvenanceNode:
    from .canonical import _provenance_inputs_bytes  # task-local private encoder, no new framing

    fields = (
        ("task160_schema_version", b"STRING", schema_version.encode("utf-8")),
        ("task160_version", b"STRING", task160_version.encode("utf-8")),
        (
            "implementation_software_version",
            b"STRING",
            implementation_software_version.encode("utf-8"),
        ),
        ("request_or_blocked_input_hash", b"STRING", input_hash.encode("ascii")),
        ("source_definition_id", b"STRING", source_definition_id.encode("utf-8")),
        (
            "failure_stage",
            b"NONE" if failure_stage is None else b"ENUM",
            b"" if failure_stage is None else failure_stage.value.encode("ascii"),
        ),
        ("provenance_inputs", b"RECORD", _provenance_inputs_bytes(provenance_inputs)),
        ("scope", b"ENUM", scope.value.encode("ascii")),
    )
    digest = _payload("TASK160_PROVENANCE_CALCULATION_RUN_PAYLOAD_V1", fields)
    return _external_node(
        "task160-provenance-calculation-run-v1::",
        ProvenanceNodeType.CALCULATION_RUN,
        "TASK160_CALCULATION_RUN",
        digest,
    )


def build_provenance(
    *,
    schema_version: str,
    task160_version: str,
    implementation_software_version: str,
    input_hash: str,
    provenance_inputs: Task160ProvenanceInputs,
    adapter_evidence: Iterable[Task160AdapterEvidence],
    artifact_hash: str,
    artifact_id: UUID,
    scope: CalculationRunScope,
    failure_stage: FailureStage | None = None,
) -> Task160Provenance:
    """Build a lawful graph after the artifact hash is final."""
    source = source_authority_node()
    producers = tuple(_producer_node(item) for item in provenance_inputs.producer_identity)
    upstreams = tuple(_upstream_node(item) for item in provenance_inputs.upstream_identity_hashes)
    sources = tuple(_source_evidence_node(item) for item in provenance_inputs.source_evidence_refs)
    adapters = tuple(
        _adapter_node(item)
        for item in sorted(
            adapter_evidence, key=lambda x: (x.source_task_id, x.adapter_id, x.evidence_hash)
        )
    )
    calculation = _calculation_node(
        schema_version=schema_version,
        task160_version=task160_version,
        implementation_software_version=implementation_software_version,
        input_hash=input_hash,
        source_definition_id="TASK160-SOURCE-DEFINITION-R1-ISSUE-221",
        failure_stage=failure_stage,
        provenance_inputs=provenance_inputs,
        scope=scope,
    )
    artifact_type = (
        ProvenanceNodeType.RESULT
        if scope is CalculationRunScope.SUCCESS
        else ProvenanceNodeType.BLOCKER
    )
    artifact_label = (
        "TASK160_RESULT" if scope is CalculationRunScope.SUCCESS else "TASK160_BLOCKED_RESULT"
    )
    artifact_prefix = (
        "task160-provenance-result-v1::"
        if scope is CalculationRunScope.SUCCESS
        else "task160-provenance-blocked-result-v1::"
    )
    artifact = _external_node(
        artifact_prefix,
        artifact_type,
        artifact_label,
        artifact_hash,
        node_id=artifact_id,
    )
    nodes = (source, *producers, *upstreams, *sources, *adapters, calculation, artifact)
    edges: list[ProvenanceEdge] = []
    edges.append(
        ProvenanceEdge(
            source_id=source.node_id,
            target_id=calculation.node_id,
            relation=REL_AUTHORIZES,
            metadata=(),
        )
    )
    edges.extend(
        ProvenanceEdge(
            source_id=item.node_id,
            target_id=calculation.node_id,
            relation=REL_SUPPLIES,
            metadata=(),
        )
        for item in producers
    )
    edges.extend(
        ProvenanceEdge(
            source_id=item.node_id,
            target_id=calculation.node_id,
            relation=REL_SUPPLIES,
            metadata=(),
        )
        for item in upstreams
    )
    edges.extend(
        ProvenanceEdge(
            source_id=item.node_id,
            target_id=calculation.node_id,
            relation=REL_SUPPLIES,
            metadata=(),
        )
        for item in sources
    )
    edges.extend(
        ProvenanceEdge(
            source_id=item.node_id, target_id=calculation.node_id, relation=REL_ADAPTS, metadata=()
        )
        for item in adapters
    )
    edges.append(
        ProvenanceEdge(
            source_id=calculation.node_id,
            target_id=artifact.node_id,
            relation=REL_PRODUCES
            if scope is CalculationRunScope.SUCCESS
            else REL_PRODUCES_BLOCKED_RESULT,
            metadata=(),
        )
    )
    graph = ProvenanceGraph(schema_version="1.0", nodes=nodes, edges=tuple(edges))
    return Task160Provenance(
        producer_identity=provenance_inputs.producer_identity,
        upstream_identity_hashes=provenance_inputs.upstream_identity_hashes,
        source_evidence_refs=provenance_inputs.source_evidence_refs,
        adapter_evidence_refs=provenance_inputs.adapter_evidence_refs,
        graph=graph,
        provenance_hash=graph.compute_hash(),
    )


__all__ = [
    "REL_ADAPTS",
    "REL_AUTHORIZES",
    "REL_PRODUCES",
    "REL_PRODUCES_BLOCKED_RESULT",
    "REL_SUPPLIES",
    "SOURCE_AUTHORITY_BARE_HASH",
    "SOURCE_AUTHORITY_NODE_ID",
    "build_provenance",
    "source_authority_node",
]
