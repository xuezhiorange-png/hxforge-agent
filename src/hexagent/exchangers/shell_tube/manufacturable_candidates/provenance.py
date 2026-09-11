"""Acyclic TASK-168 provenance graph construction."""

from __future__ import annotations

from collections import defaultdict

from .canonical import provenance_graph_hash, sha256_domain_hex
from .models import (
    CandidateRecord,
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    Task168Request,
)


def _node(node_id: str, payload_hash: str) -> ProvenanceNode:
    return ProvenanceNode(node_id=node_id, payload_hash=payload_hash)


def _stable_hash(value: object) -> str:
    return "sha256:" + sha256_domain_hex("task168.provenance.payload.v1", value)


def _has_cycle(nodes: tuple[ProvenanceNode, ...], edges: tuple[ProvenanceEdge, ...]) -> bool:
    del nodes
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        adjacency[edge.source_node_id].append(edge.target_node_id)
    for values in adjacency.values():
        values.sort()
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in visiting:
            return True
        if node_id in visited:
            return False
        visiting.add(node_id)
        if any(visit(target) for target in adjacency.get(node_id, ())):
            return True
        visiting.remove(node_id)
        visited.add(node_id)
        return False

    return any(visit(node_id) for node_id in sorted(adjacency))


def build_batch_provenance(
    request: Task168Request,
    *,
    request_hash: str,
    candidate_space_hash: str,
    records: tuple[CandidateRecord, ...],
    result_id: str,
    result_hash: str,
) -> ProvenanceGraph:
    """Build the final graph after the result preimage is already hashed.

    The result hash is deliberately not an input to the preimage.  It is only
    attached to the terminal result node here, so provenance cannot feed back
    into result identity.
    """

    source_id = "TASK168_SOURCE_DEFINITION"
    requirement_id = (
        "TASK168_REQUIREMENT_AUTHORITY::" + request.requirement_authority.requirement_id
    )
    catalog_id = "TASK023_SHELL_CATALOG::" + request.shell_geometry_catalog.catalog_id
    space_id = "TASK168_CANDIDATE_SPACE::" + candidate_space_hash
    run_id = "TASK168_CALCULATION_RUN::" + request_hash
    result_node_id = result_id

    nodes: list[ProvenanceNode] = [
        _node(source_id, _stable_hash(request.source_definition_id)),
        _node(requirement_id, _stable_hash(request.requirement_authority.canonical_hash)),
        _node(catalog_id, _stable_hash(request.shell_geometry_catalog.catalog_hash)),
        _node(space_id, _stable_hash(candidate_space_hash)),
        _node(run_id, _stable_hash(request_hash)),
        _node(result_node_id, "sha256:" + result_hash),
    ]
    edges: list[ProvenanceEdge] = [
        ProvenanceEdge(source_id, "AUTHORIZES", run_id),
        ProvenanceEdge(requirement_id, "SUPPLIES", run_id),
        ProvenanceEdge(catalog_id, "SUPPLIES", run_id),
        ProvenanceEdge(space_id, "DEFINES", run_id),
        ProvenanceEdge(run_id, "PRODUCES", result_node_id),
    ]

    for record in records:
        candidate_node_id = "TASK168_CANDIDATE::" + record.candidate_id
        nodes.append(_node(candidate_node_id, "sha256:" + record.candidate_hash))
        edges.append(ProvenanceEdge(candidate_node_id, "SUPPLIES", run_id))
        configuration_evidence = dict(record.configuration_evidence)
        task020_node_id = ""
        if configuration_evidence.get("result_id"):
            task020_node_id = "TASK020::" + configuration_evidence["result_id"]
            nodes.append(
                _node(
                    task020_node_id,
                    _stable_hash(
                        (
                            "TASK020",
                            configuration_evidence.get("result_id"),
                            configuration_evidence.get("result_hash"),
                        )
                    ),
                )
            )
            edges.append(ProvenanceEdge(task020_node_id, "SUPPLIES", candidate_node_id))
        for binding in record.candidate.dimension_authority_bindings:
            role = binding.dimension_role.value
            authority_node_id = (
                "TASK168_DISCRETE_AUTHORITY::" + role + "::" + binding.canonical_hash
            )
            materialized_node_id = (
                "TASK168_MATERIALIZED_AUTHORITY::" + record.candidate_id + "::" + role
            )
            authority_payload = (
                role,
                binding.authority_id,
                binding.authority_version,
                binding.canonical_hash,
                binding.source_class,
                binding.source_id,
                binding.source_revision,
                binding.evidence_refs,
                binding.provenance_refs,
            )
            nodes.append(_node(authority_node_id, _stable_hash(authority_payload)))
            nodes.append(
                _node(
                    materialized_node_id,
                    _stable_hash((record.candidate_id, binding)),
                )
            )
            edges.extend(
                (
                    ProvenanceEdge(authority_node_id, "AUTHORIZES", candidate_node_id),
                    ProvenanceEdge(authority_node_id, "SUPPLIES", materialized_node_id),
                    ProvenanceEdge(materialized_node_id, "SUPPLIES", candidate_node_id),
                )
            )
            if task020_node_id:
                edges.append(ProvenanceEdge(authority_node_id, "AUTHORIZES", task020_node_id))
        for label, evidence in (
            ("TASK020", record.configuration_evidence),
            ("TASK021", record.tube_layout_evidence),
            ("TUBE_SIDE", record.tube_side_evidence),
            ("TASK166", record.bell_evidence),
            ("TASK038", record.overall_u_ua_evidence),
            ("TASK162", record.thermal_closure_evidence),
            ("TASK167", record.screening_evidence),
        ):
            for key, value in evidence:
                if key in {"result_id", "layout_id", "geometry_id"}:
                    # TASK-020 is emitted above with the paired configuration
                    # hash.  Do not emit the same node id again with the
                    # weaker generic ``(label, key, value)`` payload: two
                    # equal-id nodes make set iteration observable in the
                    # graph hash and break cross-process replay.
                    if label == "TASK020" and key == "result_id":
                        continue
                    producer_node_id = f"{label}::{value}"
                    nodes.append(_node(producer_node_id, _stable_hash((label, key, value))))
                    edges.append(ProvenanceEdge(producer_node_id, "SUPPLIES", candidate_node_id))

    ordered_nodes = tuple(sorted(set(nodes), key=lambda item: item.node_id))
    ordered_edges = tuple(
        sorted(
            set(edges),
            key=lambda item: (item.source_node_id, item.relation, item.target_node_id),
        )
    )
    self_edge_count = sum(edge.source_node_id == edge.target_node_id for edge in ordered_edges)
    cycle_count = int(_has_cycle(ordered_nodes, ordered_edges))
    provisional = ProvenanceGraph(
        nodes=ordered_nodes,
        edges=ordered_edges,
        graph_hash="",
        self_edge_count=self_edge_count,
        cycle_count=cycle_count,
    )
    return ProvenanceGraph(
        nodes=ordered_nodes,
        edges=ordered_edges,
        graph_hash=provenance_graph_hash(provisional),
        self_edge_count=self_edge_count,
        cycle_count=cycle_count,
    )


def verify_provenance_graph(value: ProvenanceGraph) -> bool:
    if type(value) is not ProvenanceGraph:
        return False
    if value.self_edge_count != 0 or value.cycle_count != 0:
        return False
    provisional = ProvenanceGraph(
        nodes=value.nodes,
        edges=value.edges,
        graph_hash="",
        self_edge_count=value.self_edge_count,
        cycle_count=value.cycle_count,
    )
    return value.graph_hash == provenance_graph_hash(provisional) and not _has_cycle(
        value.nodes, value.edges
    )


__all__ = ["build_batch_provenance", "verify_provenance_graph"]
