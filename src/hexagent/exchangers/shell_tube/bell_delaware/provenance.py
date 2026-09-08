"""Acyclic TASK-166 provenance graph construction."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .authority import (
    BELL_ORIGIN_LOCATION,
    DESIGN_CONTRACT_PATH,
    GONCALVES_SOURCE_URL,
    JAMIL_PARAMETER_SOURCE_ID,
    JAMIL_SOURCE_LOCATION,
    JAMIL_SOURCE_SHA256,
    JS_SOURCE_LOCATION,
    METHOD_ORIGIN_SOURCE_ID,
    PRIMARY_IMPLEMENTATION_SOURCE_ID,
    PRIMARY_SOURCE_LOCATION,
    SAIF_TARIQ_JS_SOURCE_ID,
    SAIF_TARIQ_SOURCE_SHA256,
    SOURCE_DEFINITION_ID,
    TASK032_SOURCE_ID,
)
from .canonical import provenance_hash, sha256_domain_hex
from .models import ProvenanceEdge, ProvenanceGraph, ProvenanceNode


def semantic_input_hashes(request: Any, *, request_hash_value: str) -> tuple[tuple[str, str], ...]:
    return (
        (
            "source_authority_payload_hash",
            sha256_domain_hex(
                "task166.source-authority.v1",
                {
                    "source_definition_id": SOURCE_DEFINITION_ID,
                    "design_contract_path": DESIGN_CONTRACT_PATH,
                },
            ),
        ),
        (
            "task020_configuration_payload_hash",
            sha256_domain_hex("task166.task020.v1", request.task020_configuration),
        ),
        (
            "tube_layout_payload_hash",
            sha256_domain_hex("task166.tube-layout.v1", request.tube_layout),
        ),
        (
            "shell_bundle_geometry_payload_hash",
            sha256_domain_hex("task166.shell-bundle.v1", request.shell_bundle_geometry),
        ),
        (
            "baffle_geometry_payload_hash",
            sha256_domain_hex("task166.baffle.v1", request.baffle_geometry),
        ),
        (
            "task032_flow_state_payload_hash",
            sha256_domain_hex("task166.task032-flow.v1", request.shell_side_flow_state),
        ),
        (
            "task032_source_authority_payload_hash",
            sha256_domain_hex(
                "task166.task032-source-authority.v1",
                {"source_id": TASK032_SOURCE_ID, "role": "UPSTREAM_FLOW_STATE"},
            ),
        ),
        (
            "method_origin_source_payload_hash",
            sha256_domain_hex(
                "task166.method-origin-source.v1",
                {"id": METHOD_ORIGIN_SOURCE_ID, "location": BELL_ORIGIN_LOCATION},
            ),
        ),
        (
            "primary_source_payload_hash",
            sha256_domain_hex(
                "task166.primary-source.v1",
                {
                    "id": PRIMARY_IMPLEMENTATION_SOURCE_ID,
                    "location": PRIMARY_SOURCE_LOCATION,
                    "url": GONCALVES_SOURCE_URL,
                },
            ),
        ),
        (
            "jamil_source_payload_hash",
            sha256_domain_hex(
                "task166.jamil-source.v1",
                {
                    "id": JAMIL_PARAMETER_SOURCE_ID,
                    "location": JAMIL_SOURCE_LOCATION,
                    "sha256": JAMIL_SOURCE_SHA256,
                },
            ),
        ),
        (
            "saif_tariq_source_payload_hash",
            sha256_domain_hex(
                "task166.js-source.v1",
                {
                    "id": SAIF_TARIQ_JS_SOURCE_ID,
                    "location": JS_SOURCE_LOCATION,
                    "sha256": SAIF_TARIQ_SOURCE_SHA256,
                },
            ),
        ),
        (
            "calculation_run_payload_hash",
            sha256_domain_hex(
                "task166.calculation-run.v1",
                {
                    "request_hash": request_hash_value,
                    "software_version": "task166.bell-delaware-impl-v1",
                },
            ),
        ),
    )


def _graph_cycle_count(nodes: Sequence[ProvenanceNode], edges: Sequence[ProvenanceEdge]) -> int:
    adjacency: dict[str, list[str]] = {node.node_id: [] for node in nodes}
    for edge in edges:
        adjacency.setdefault(edge.source_node_id, []).append(edge.target_node_id)
    active: set[str] = set()
    complete: set[str] = set()
    cycles = 0

    def visit(node_id: str) -> None:
        nonlocal cycles
        if node_id in active:
            cycles += 1
            return
        if node_id in complete:
            return
        active.add(node_id)
        for child in adjacency.get(node_id, []):
            visit(child)
        active.remove(node_id)
        complete.add(node_id)

    for node in nodes:
        visit(node.node_id)
    return cycles


def build_provenance(
    request: Any,
    *,
    request_hash_value: str,
    result_hash_value: str,
) -> tuple[tuple[tuple[str, str], ...], ProvenanceGraph]:
    semantic = semantic_input_hashes(request, request_hash_value=request_hash_value)
    semantic_map = dict(semantic)
    calc_payload = semantic_map["calculation_run_payload_hash"]
    nodes = (
        ProvenanceNode("TASK166_SOURCE_AUTHORITY", semantic_map["source_authority_payload_hash"]),
        ProvenanceNode("TASK020_CONFIGURATION", semantic_map["task020_configuration_payload_hash"]),
        ProvenanceNode("TUBE_LAYOUT", semantic_map["tube_layout_payload_hash"]),
        ProvenanceNode("SHELL_BUNDLE_GEOMETRY", semantic_map["shell_bundle_geometry_payload_hash"]),
        ProvenanceNode("BAFFLE_GEOMETRY", semantic_map["baffle_geometry_payload_hash"]),
        ProvenanceNode("TASK032_FLOW_STATE", semantic_map["task032_flow_state_payload_hash"]),
        ProvenanceNode(
            "TASK032_SOURCE_AUTHORITY", semantic_map["task032_source_authority_payload_hash"]
        ),
        ProvenanceNode(
            "BELL_METHOD_ORIGIN_SOURCE", semantic_map["method_origin_source_payload_hash"]
        ),
        ProvenanceNode("GONCALVES_PRIMARY_SOURCE", semantic_map["primary_source_payload_hash"]),
        ProvenanceNode("JAMIL_PARAMETER_SOURCE", semantic_map["jamil_source_payload_hash"]),
        ProvenanceNode("SAIF_TARIQ_JS_SOURCE", semantic_map["saif_tariq_source_payload_hash"]),
        ProvenanceNode("TASK166_CALCULATION_RUN", calc_payload),
        ProvenanceNode("TASK166_RESULT", "sha256:" + result_hash_value),
    )
    supplying = (
        ProvenanceEdge("TASK166_SOURCE_AUTHORITY", "AUTHORIZES", "TASK166_CALCULATION_RUN"),
        ProvenanceEdge("TASK020_CONFIGURATION", "SUPPLIES", "TASK166_CALCULATION_RUN"),
        ProvenanceEdge("TUBE_LAYOUT", "SUPPLIES", "TASK166_CALCULATION_RUN"),
        ProvenanceEdge("SHELL_BUNDLE_GEOMETRY", "SUPPLIES", "TASK166_CALCULATION_RUN"),
        ProvenanceEdge("BAFFLE_GEOMETRY", "SUPPLIES", "TASK166_CALCULATION_RUN"),
        ProvenanceEdge("TASK032_FLOW_STATE", "SUPPLIES", "TASK166_CALCULATION_RUN"),
        ProvenanceEdge("TASK032_SOURCE_AUTHORITY", "AUTHORIZES", "TASK166_CALCULATION_RUN"),
        ProvenanceEdge("BELL_METHOD_ORIGIN_SOURCE", "SUPPLIES", "TASK166_CALCULATION_RUN"),
        ProvenanceEdge("GONCALVES_PRIMARY_SOURCE", "DEFINES", "TASK166_CALCULATION_RUN"),
        ProvenanceEdge("JAMIL_PARAMETER_SOURCE", "SUPPLIES", "TASK166_CALCULATION_RUN"),
        ProvenanceEdge("SAIF_TARIQ_JS_SOURCE", "SUPPLIES", "TASK166_CALCULATION_RUN"),
        ProvenanceEdge("TASK166_CALCULATION_RUN", "PRODUCES", "TASK166_RESULT"),
    )
    self_edges = sum(edge.source_node_id == edge.target_node_id for edge in supplying)
    cycle_count = _graph_cycle_count(nodes, supplying)
    graph_payload = {
        "nodes": [[node.node_id, node.payload_hash] for node in nodes],
        "edges": [[edge.source_node_id, edge.relation, edge.target_node_id] for edge in supplying],
    }
    graph = ProvenanceGraph(
        nodes=nodes,
        edges=supplying,
        graph_hash=provenance_hash(graph_payload),
        self_edge_count=self_edges,
        cycle_count=cycle_count,
    )
    return semantic, graph


__all__ = ["build_provenance", "semantic_input_hashes"]
