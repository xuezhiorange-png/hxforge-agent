"""TASK163 semantic payload hashes and acyclic provenance graph."""

from __future__ import annotations

from uuid import UUID, uuid5

from hexagent.domain.provenance import (
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    ProvenanceNodeType,
)
from hexagent.exchangers.shell_tube.thermal_performance_closure.canonical import (
    energy_balance_bytes,
    terminal_closure_bytes,
)
from hexagent.exchangers.shell_tube.thermal_performance_closure.models import (
    Task162EnergyBalanceEvidence,
    Task162TerminalClosureEvidence,
)
from hexagent.exchangers.shell_tube.tube_side.canonical import (
    KIND_ENUM,
    KIND_INT,
    KIND_RECORD,
    KIND_STRING,
    KIND_TUPLE,
    frame_record,
    frame_tuple,
    frame_value,
    sha256_hex_from_framed_bytes,
)

from .canonical import (
    TASK163_PROVENANCE_NAMESPACE,
    _deferred_bytes,
    _heat_duty_bytes,
    _outlet_bytes,
    _rating_projection_bytes,
    _replay_evidence_identity_bytes,
    _task162_identity_bytes,
)
from .models import (
    TASK163_SOURCE_DEFINITION_ID,
    Task162ResultIdentityProjection,
    Task163Applicability,
    Task163Completeness,
    Task163DeferredCapabilities,
    Task163HeatDutyProjection,
    Task163OutletTemperatureProjection,
    Task163Provenance,
    Task163ProvenanceSemanticInputs,
    Task163RatingPerformanceProjection,
    Task163Result,
    Task163Task162Evidence,
)

REL_AUTHORIZES = "AUTHORIZES"
REL_SUPPLIES = "SUPPLIES"
REL_PRODUCES = "PRODUCES"

SOURCE_AUTHORITY_DOMAIN = "TASK163_PROVENANCE_SOURCE_AUTHORITY_PAYLOAD_V1"
TASK162_EVIDENCE_DOMAIN = "TASK163_PROVENANCE_TASK162_RESULT_EVIDENCE_PAYLOAD_V1"
RATING_DOMAIN = "TASK163_PROVENANCE_RATING_COMPOSITION_PAYLOAD_V1"
APPLICABILITY_DOMAIN = "TASK163_PROVENANCE_APPLICABILITY_PAYLOAD_V1"
COMPLETENESS_DOMAIN = "TASK163_PROVENANCE_COMPLETENESS_PAYLOAD_V1"

NODE_PREFIXES = {
    "TASK163_SOURCE_AUTHORITY": "task163-provenance-source-authority-v1::",
    "TASK162_RESULT_EVIDENCE": "task163-provenance-task162-result-evidence-v1::",
    "TASK163_RATING_COMPOSITION": "task163-provenance-rating-composition-v1::",
    "TASK163_APPLICABILITY": "task163-provenance-applicability-v1::",
    "TASK163_COMPLETENESS": "task163-provenance-completeness-v1::",
    "TASK163_RESULT": "task163-provenance-result-v1::",
}


def _hash(domain: str, fields: tuple[tuple[str, bytes, bytes], ...]) -> str:
    return sha256_hex_from_framed_bytes(frame_record(domain, fields))


def _s(name: str, value: str) -> tuple[str, bytes, bytes]:
    return name, KIND_STRING, value.encode("utf-8", "strict")


def source_authority_payload_hash() -> str:
    return _hash(
        SOURCE_AUTHORITY_DOMAIN,
        (
            _s("source_definition_id", TASK163_SOURCE_DEFINITION_ID),
            ("source_authority_issue", KIND_INT, b"234"),
            ("source_definition_revision", KIND_ENUM, b"R6"),
            ("source_definition_status", KIND_ENUM, b"FROZEN"),
            _s("work_package_id", "V05-SHT-04"),
            _s("work_package_name", "Thermal Rating Composition, Applicability and Completeness"),
        ),
    )


def task162_result_evidence_payload_hash(value: Task163Task162Evidence) -> str:
    projection = task162_result_identity_projection_from_evidence(value)
    return _hash(
        TASK162_EVIDENCE_DOMAIN,
        (
            (
                "task162_result_identity_projection",
                KIND_RECORD,
                _task162_identity_bytes(projection),
            ),
            (
                "task162_success_replay_evidence_identity_projection",
                KIND_RECORD,
                _replay_evidence_identity_bytes(
                    value.task162_success_replay_evidence_identity_projection
                ),
            ),
        ),
    )


def task162_result_identity_projection_from_evidence(
    value: Task163Task162Evidence,
) -> Task162ResultIdentityProjection:
    return value.task162_result_identity_projection


def rating_composition_payload_hash(
    performance: Task163RatingPerformanceProjection,
    duty: Task163HeatDutyProjection,
    outlet: Task163OutletTemperatureProjection,
    energy: Task162EnergyBalanceEvidence,
    terminal: Task162TerminalClosureEvidence,
    deferred: Task163DeferredCapabilities,
) -> str:
    return _hash(
        RATING_DOMAIN,
        (
            (
                "rating_performance_projection",
                KIND_RECORD,
                _rating_projection_bytes(performance),
            ),
            (
                "heat_duty_projection",
                KIND_RECORD,
                _heat_duty_bytes(duty),
            ),
            (
                "outlet_temperature_projection",
                KIND_RECORD,
                _outlet_bytes(outlet),
            ),
            (
                "energy_balance_evidence",
                KIND_RECORD,
                energy_balance_bytes(energy),
            ),
            (
                "terminal_temperature_evidence",
                KIND_RECORD,
                terminal_closure_bytes(terminal),
            ),
            ("deferred_capabilities", KIND_RECORD, _deferred_bytes(deferred)),
        ),
    )


def applicability_payload_hash(value: Task163Applicability) -> str:
    payload = frame_record(
        "TASK163_APPLICABILITY_V1",
        (
            ("status", KIND_ENUM, value.status.value.encode("utf-8")),
            (
                "checks",
                KIND_TUPLE,
                frame_tuple(
                    tuple(
                        frame_value(
                            KIND_RECORD,
                            frame_record(
                                "TASK163_APPLICABILITY_CHECK_V1",
                                (
                                    ("name", KIND_ENUM, name.value.encode("utf-8")),
                                    ("status", KIND_ENUM, status.value.encode("utf-8")),
                                ),
                            ),
                        )
                        for name, status in value.checks
                    )
                ),
            ),
        ),
    )
    return _hash(APPLICABILITY_DOMAIN, (("applicability", KIND_RECORD, payload),))


def completeness_payload_hash(value: Task163Completeness) -> str:
    payload = frame_record(
        "TASK163_COMPLETENESS_V1",
        (
            ("status", KIND_ENUM, value.status.value.encode("utf-8")),
            (
                "required_fields",
                KIND_TUPLE,
                frame_tuple(
                    tuple(
                        frame_value(KIND_ENUM, field.value.encode("utf-8"))
                        for field in value.required_fields
                    )
                ),
            ),
        ),
    )
    return _hash(COMPLETENESS_DOMAIN, (("completeness", KIND_RECORD, payload),))


def build_provenance_semantic_inputs(
    *,
    task162_evidence: Task163Task162Evidence,
    performance: Task163RatingPerformanceProjection,
    duty: Task163HeatDutyProjection,
    outlet: Task163OutletTemperatureProjection,
    energy: Task162EnergyBalanceEvidence,
    terminal: Task162TerminalClosureEvidence,
    deferred: Task163DeferredCapabilities,
    applicability: Task163Applicability,
    completeness: Task163Completeness,
) -> Task163ProvenanceSemanticInputs:
    return Task163ProvenanceSemanticInputs(
        source_authority_payload_hash=source_authority_payload_hash(),
        task162_result_evidence_payload_hash=task162_result_evidence_payload_hash(task162_evidence),
        rating_composition_payload_hash=rating_composition_payload_hash(
            performance, duty, outlet, energy, terminal, deferred
        ),
        applicability_payload_hash=applicability_payload_hash(applicability),
        completeness_payload_hash=completeness_payload_hash(completeness),
    )


def _node_id(label: str, payload_hash: str) -> UUID:
    return uuid5(TASK163_PROVENANCE_NAMESPACE, NODE_PREFIXES[label] + payload_hash)


def build_success_provenance(
    *,
    semantic_inputs: Task163ProvenanceSemanticInputs,
    result: Task163Result,
) -> Task163Provenance:
    source_id = _node_id("TASK163_SOURCE_AUTHORITY", semantic_inputs.source_authority_payload_hash)
    evidence_id = _node_id(
        "TASK162_RESULT_EVIDENCE", semantic_inputs.task162_result_evidence_payload_hash
    )
    rating_id = _node_id(
        "TASK163_RATING_COMPOSITION", semantic_inputs.rating_composition_payload_hash
    )
    applicability_id = _node_id("TASK163_APPLICABILITY", semantic_inputs.applicability_payload_hash)
    completeness_id = _node_id("TASK163_COMPLETENESS", semantic_inputs.completeness_payload_hash)
    result_id = result.result_id
    nodes = (
        ProvenanceNode(
            node_id=source_id,
            node_type=ProvenanceNodeType.EXTERNAL,
            label="TASK163_SOURCE_AUTHORITY",
            payload_hash="sha256:" + semantic_inputs.source_authority_payload_hash,
        ),
        ProvenanceNode(
            node_id=evidence_id,
            node_type=ProvenanceNodeType.EXTERNAL,
            label="TASK162_RESULT_EVIDENCE",
            payload_hash="sha256:" + semantic_inputs.task162_result_evidence_payload_hash,
        ),
        ProvenanceNode(
            node_id=rating_id,
            node_type=ProvenanceNodeType.CALCULATION_RUN,
            label="TASK163_RATING_COMPOSITION",
            payload_hash="sha256:" + semantic_inputs.rating_composition_payload_hash,
        ),
        ProvenanceNode(
            node_id=applicability_id,
            node_type=ProvenanceNodeType.INTERMEDIATE,
            label="TASK163_APPLICABILITY",
            payload_hash="sha256:" + semantic_inputs.applicability_payload_hash,
        ),
        ProvenanceNode(
            node_id=completeness_id,
            node_type=ProvenanceNodeType.INTERMEDIATE,
            label="TASK163_COMPLETENESS",
            payload_hash="sha256:" + semantic_inputs.completeness_payload_hash,
        ),
        ProvenanceNode(
            node_id=result_id,
            node_type=ProvenanceNodeType.RESULT,
            label="TASK163_RESULT",
            payload_hash="sha256:" + result.result_hash,
        ),
    )
    edges = (
        ProvenanceEdge(source_id=source_id, target_id=rating_id, relation=REL_AUTHORIZES),
        ProvenanceEdge(source_id=evidence_id, target_id=rating_id, relation=REL_SUPPLIES),
        ProvenanceEdge(source_id=rating_id, target_id=applicability_id, relation=REL_PRODUCES),
        ProvenanceEdge(source_id=rating_id, target_id=completeness_id, relation=REL_PRODUCES),
        ProvenanceEdge(source_id=rating_id, target_id=result_id, relation=REL_PRODUCES),
        ProvenanceEdge(source_id=applicability_id, target_id=result_id, relation=REL_SUPPLIES),
        ProvenanceEdge(source_id=completeness_id, target_id=result_id, relation=REL_SUPPLIES),
    )
    graph = ProvenanceGraph(nodes=nodes, edges=edges)
    return Task163Provenance(provenance_hash=graph.compute_hash(), graph=graph)


def verify_provenance(value: Task163Provenance) -> bool:
    if type(value) is not Task163Provenance:
        return False
    try:
        return value.provenance_hash == value.graph.compute_hash()
    except BaseException:
        return False


__all__ = [
    "REL_AUTHORIZES",
    "REL_PRODUCES",
    "REL_SUPPLIES",
    "applicability_payload_hash",
    "build_provenance_semantic_inputs",
    "build_success_provenance",
    "completeness_payload_hash",
    "rating_composition_payload_hash",
    "source_authority_payload_hash",
    "task162_result_evidence_payload_hash",
    "verify_provenance",
]
