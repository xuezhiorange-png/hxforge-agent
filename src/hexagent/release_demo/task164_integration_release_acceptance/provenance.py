"""Acyclic TASK164 semantic payload hashes and provenance graph."""

from __future__ import annotations

from uuid import UUID, uuid5

from hexagent.domain.provenance import (
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    ProvenanceNodeType,
)
from hexagent.exchangers.shell_tube.tube_side.canonical import (
    KIND_BOOL_FALSE,
    KIND_ENUM,
    KIND_INT,
    KIND_RECORD,
    KIND_STRING,
    frame_record,
    sha256_hex_from_framed_bytes,
)

from .canonical import (
    TASK164_PROVENANCE_NAMESPACE,
    acceptance_ledger_bytes,
    evidence_package_bytes,
    negative_demonstration_payload_bytes,
    positive_demonstration_payload_bytes,
    provenance_graph_bytes,
    python_parity_payload_bytes,
    repeat_run_payload_bytes,
    task163_applicability_payload_bytes,
    task163_completeness_payload_bytes,
    task163_identity_payload_bytes,
    task163_provenance_payload_bytes,
    task163_replay_payload_bytes,
)
from .models import (
    Task164AcceptanceLedger,
    Task164DeterminismEvidence,
    Task164EvidencePackage,
    Task164Provenance,
    Task164ProvenanceSemanticInputs,
    Task164Result,
    Task164Task163Evidence,
)

# These literals are stable graph labels, not engineering identities.
REL_AUTHORIZES = "AUTHORIZES"
REL_SUPPLIES = "SUPPLIES"
REL_PRODUCES = "PRODUCES"

_NODE_PREFIX = {
    "TASK164_SOURCE_AUTHORITY": "task164-provenance-source-authority-v1::",
    "TASK163_RESULT_EVIDENCE": "task164-provenance-task163-result-evidence-v1::",
    "TASK164_SCENARIO_EVIDENCE": "task164-provenance-scenario-evidence-v1::",
    "TASK164_DETERMINISM_EVIDENCE": "task164-provenance-determinism-evidence-v1::",
    "TASK164_ACCEPTANCE_LEDGER": "task164-provenance-acceptance-ledger-v1::",
    "TASK164_EVIDENCE_PACKAGE": "task164-provenance-evidence-package-v1::",
    "TASK164_CALCULATION_RUN": "task164-provenance-calculation-run-v1::",
}


def _hash(domain: str, fields: tuple[tuple[str, bytes, bytes], ...]) -> str:
    return sha256_hex_from_framed_bytes(frame_record(domain, fields))


def _s(name: str, value: str) -> tuple[str, bytes, bytes]:
    return name, KIND_STRING, value.encode("utf-8", "strict")


def source_authority_payload_hash() -> str:
    return _hash(
        "TASK164_SOURCE_AUTHORITY_PAYLOAD_V1",
        (
            ("namespace_issue", KIND_INT, b"219"),
            ("allocation_issue", KIND_INT, b"220"),
            ("lifecycle_issue", KIND_INT, b"242"),
            ("source_issue", KIND_INT, b"243"),
            _s("source_revision", "R1"),
            ("source_status", KIND_ENUM, b"FROZEN"),
            ("design_authority_issue", KIND_INT, b"244"),
            ("design_issue", KIND_INT, b"245"),
            _s("design_revision", "R6"),
            ("predecessor_task163_pr", KIND_INT, b"241"),
            _s("predecessor_task163_merge_commit", "66dabc275bcf1a35d97e4d57fc70c2ccf05697e9"),
            ("task165_authority_present", KIND_BOOL_FALSE, b""),
        ),
    )


def task163_evidence_payload_hash(
    value: Task164Task163Evidence,
    *,
    applicability: object | None = None,
    completeness: object | None = None,
) -> str:
    fields = [
        ("replay", KIND_RECORD, task163_replay_payload_bytes(value)),
        ("identity", KIND_RECORD, task163_identity_payload_bytes(value)),
        ("provenance", KIND_RECORD, task163_provenance_payload_bytes(value)),
    ]
    if applicability is not None:
        fields.append(
            ("applicability", KIND_RECORD, task163_applicability_payload_bytes(applicability))  # type: ignore[arg-type]
        )
    if completeness is not None:
        fields.append(
            ("completeness", KIND_RECORD, task163_completeness_payload_bytes(completeness))  # type: ignore[arg-type]
        )
    return sha256_hex_from_framed_bytes(
        frame_record(
            "TASK164_TASK163_EVIDENCE_AGGREGATE_V1",
            tuple(fields),
        )
    )


def scenario_matrix_payload_hash(value: object) -> str:
    positive = positive_demonstration_payload_bytes(value)  # type: ignore[arg-type]
    negative = negative_demonstration_payload_bytes(value)  # type: ignore[arg-type]
    return sha256_hex_from_framed_bytes(
        frame_record(
            "TASK164_SCENARIO_MATRIX_AGGREGATE_V1",
            (
                ("positive", KIND_RECORD, positive),
                ("negative", KIND_RECORD, negative),
            ),
        )
    )


def determinism_payload_hash(value: Task164DeterminismEvidence) -> str:
    return sha256_hex_from_framed_bytes(
        frame_record(
            "TASK164_DETERMINISM_AGGREGATE_V1",
            (
                ("repeat", KIND_RECORD, repeat_run_payload_bytes(value)),
                ("python", KIND_RECORD, python_parity_payload_bytes(value)),
            ),
        )
    )


def acceptance_ledger_payload_hash(value: Task164AcceptanceLedger) -> str:
    return sha256_hex_from_framed_bytes(
        frame_record(
            "TASK164_ACCEPTANCE_LEDGER_PAYLOAD_V1",
            (("acceptance_ledger", KIND_RECORD, acceptance_ledger_bytes(value)),),
        )
    )


def evidence_package_payload_hash(value: Task164EvidencePackage) -> str:
    return sha256_hex_from_framed_bytes(
        frame_record(
            "TASK164_EVIDENCE_PACKAGE_PAYLOAD_V1",
            (("evidence_package", KIND_RECORD, evidence_package_bytes(value)),),
        )
    )


def build_provenance_semantic_inputs(
    *,
    task163_evidence: Task164Task163Evidence,
    scenario_matrix: object,
    determinism_evidence: Task164DeterminismEvidence,
    acceptance_ledger: Task164AcceptanceLedger,
    evidence_package: Task164EvidencePackage,
    applicability: object | None = None,
    completeness: object | None = None,
) -> Task164ProvenanceSemanticInputs:
    return Task164ProvenanceSemanticInputs(
        source_authority_payload_hash=source_authority_payload_hash(),
        task163_evidence_payload_hash=task163_evidence_payload_hash(
            task163_evidence,
            applicability=applicability,
            completeness=completeness,
        ),
        scenario_matrix_payload_hash=scenario_matrix_payload_hash(scenario_matrix),
        determinism_payload_hash=determinism_payload_hash(determinism_evidence),
        acceptance_ledger_payload_hash=acceptance_ledger_payload_hash(acceptance_ledger),
        evidence_package_payload_hash=evidence_package_payload_hash(evidence_package),
    )


def calculation_run_payload_hash(value: Task164ProvenanceSemanticInputs) -> str:
    fields = tuple(
        (name, KIND_STRING, getattr(value, name).encode("ascii"))
        for name in (
            "source_authority_payload_hash",
            "task163_evidence_payload_hash",
            "scenario_matrix_payload_hash",
            "determinism_payload_hash",
            "acceptance_ledger_payload_hash",
            "evidence_package_payload_hash",
        )
    )
    return _hash("TASK164_CALCULATION_RUN_PAYLOAD_V1", fields)


def _node_id(label: str, payload_hash: str) -> UUID:
    return uuid5(TASK164_PROVENANCE_NAMESPACE, _NODE_PREFIX[label] + payload_hash)


def build_success_provenance(
    *,
    semantic_inputs: Task164ProvenanceSemanticInputs,
    result: Task164Result,
) -> Task164Provenance:
    payloads = {
        "TASK164_SOURCE_AUTHORITY": semantic_inputs.source_authority_payload_hash,
        "TASK163_RESULT_EVIDENCE": semantic_inputs.task163_evidence_payload_hash,
        "TASK164_SCENARIO_EVIDENCE": semantic_inputs.scenario_matrix_payload_hash,
        "TASK164_DETERMINISM_EVIDENCE": semantic_inputs.determinism_payload_hash,
        "TASK164_ACCEPTANCE_LEDGER": semantic_inputs.acceptance_ledger_payload_hash,
        "TASK164_EVIDENCE_PACKAGE": semantic_inputs.evidence_package_payload_hash,
        "TASK164_CALCULATION_RUN": calculation_run_payload_hash(semantic_inputs),
    }
    ids = {label: _node_id(label, payload) for label, payload in payloads.items()}
    nodes = (
        ProvenanceNode(
            node_id=ids["TASK164_SOURCE_AUTHORITY"],
            node_type=ProvenanceNodeType.EXTERNAL,
            label="TASK164_SOURCE_AUTHORITY",
            payload_hash="sha256:" + payloads["TASK164_SOURCE_AUTHORITY"],
        ),
        ProvenanceNode(
            node_id=ids["TASK163_RESULT_EVIDENCE"],
            node_type=ProvenanceNodeType.EXTERNAL,
            label="TASK163_RESULT_EVIDENCE",
            payload_hash="sha256:" + payloads["TASK163_RESULT_EVIDENCE"],
        ),
        ProvenanceNode(
            node_id=ids["TASK164_SCENARIO_EVIDENCE"],
            node_type=ProvenanceNodeType.INTERMEDIATE,
            label="TASK164_SCENARIO_EVIDENCE",
            payload_hash="sha256:" + payloads["TASK164_SCENARIO_EVIDENCE"],
        ),
        ProvenanceNode(
            node_id=ids["TASK164_DETERMINISM_EVIDENCE"],
            node_type=ProvenanceNodeType.INTERMEDIATE,
            label="TASK164_DETERMINISM_EVIDENCE",
            payload_hash="sha256:" + payloads["TASK164_DETERMINISM_EVIDENCE"],
        ),
        ProvenanceNode(
            node_id=ids["TASK164_ACCEPTANCE_LEDGER"],
            node_type=ProvenanceNodeType.INTERMEDIATE,
            label="TASK164_ACCEPTANCE_LEDGER",
            payload_hash="sha256:" + payloads["TASK164_ACCEPTANCE_LEDGER"],
        ),
        ProvenanceNode(
            node_id=ids["TASK164_EVIDENCE_PACKAGE"],
            node_type=ProvenanceNodeType.INTERMEDIATE,
            label="TASK164_EVIDENCE_PACKAGE",
            payload_hash="sha256:" + payloads["TASK164_EVIDENCE_PACKAGE"],
        ),
        ProvenanceNode(
            node_id=ids["TASK164_CALCULATION_RUN"],
            node_type=ProvenanceNodeType.CALCULATION_RUN,
            label="TASK164_CALCULATION_RUN",
            payload_hash="sha256:" + payloads["TASK164_CALCULATION_RUN"],
        ),
        ProvenanceNode(
            node_id=result.result_id,
            node_type=ProvenanceNodeType.RESULT,
            label="TASK164_RESULT",
            payload_hash="sha256:" + result.result_hash,
        ),
    )
    run_id = ids["TASK164_CALCULATION_RUN"]
    result_id = result.result_id
    edges = (
        ProvenanceEdge(
            source_id=ids["TASK164_SOURCE_AUTHORITY"],
            target_id=run_id,
            relation=REL_AUTHORIZES,
        ),
        ProvenanceEdge(
            source_id=ids["TASK163_RESULT_EVIDENCE"],
            target_id=run_id,
            relation=REL_SUPPLIES,
        ),
        ProvenanceEdge(
            source_id=ids["TASK164_SCENARIO_EVIDENCE"],
            target_id=run_id,
            relation=REL_SUPPLIES,
        ),
        ProvenanceEdge(
            source_id=ids["TASK164_DETERMINISM_EVIDENCE"],
            target_id=run_id,
            relation=REL_SUPPLIES,
        ),
        ProvenanceEdge(
            source_id=ids["TASK164_ACCEPTANCE_LEDGER"],
            target_id=run_id,
            relation=REL_SUPPLIES,
        ),
        ProvenanceEdge(
            source_id=ids["TASK164_EVIDENCE_PACKAGE"],
            target_id=run_id,
            relation=REL_SUPPLIES,
        ),
        ProvenanceEdge(source_id=run_id, target_id=result_id, relation=REL_PRODUCES),
    )
    graph = ProvenanceGraph(nodes=nodes, edges=edges)
    return Task164Provenance(
        provenance_hash=sha256_hex_from_framed_bytes(provenance_graph_bytes(graph)), graph=graph
    )


def verify_provenance(value: Task164Provenance) -> bool:
    if type(value) is not Task164Provenance:
        return False
    try:
        if any(edge.source_id == edge.target_id for edge in value.graph.edges):
            return False
        return value.provenance_hash == sha256_hex_from_framed_bytes(
            provenance_graph_bytes(value.graph)
        )
    except BaseException:
        return False


__all__ = [
    "REL_AUTHORIZES",
    "REL_PRODUCES",
    "REL_SUPPLIES",
    "build_provenance_semantic_inputs",
    "build_success_provenance",
    "calculation_run_payload_hash",
    "verify_provenance",
]
