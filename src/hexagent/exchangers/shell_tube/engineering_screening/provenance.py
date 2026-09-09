"""Acyclic TASK-167 provenance semantic hashes and graph assembly."""

from __future__ import annotations

from dataclasses import fields

from . import authority
from .canonical import (
    applicability_projection,
    configuration_projection,
    fiv_projection,
    provenance_hash,
    requirements_projection,
    screen_projection,
    sha256_domain_hex,
    task166_identity_projection,
    tube_side_identity_projection,
)
from .models import (
    ApplicabilityLedger,
    CompletenessLedger,
    FIVScreen,
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    ScreenRecord,
    Task167Request,
    Task167Result,
)

SEMANTIC_HASH_FIELDS: tuple[str, ...] = (
    "source_definition_payload_hash",
    "task020_configuration_payload_hash",
    "task166_result_payload_hash",
    "tube_side_result_payload_hash",
    "screening_requirements_payload_hash",
    "screening_property_payload_hash",
    "screen_records_payload_hash",
    "fiv_payload_hash",
    "applicability_payload_hash",
    "completeness_payload_hash",
    "calculation_run_payload_hash",
)


def semantic_input_hashes(
    request: Task167Request,
    *,
    velocity_screens: tuple[ScreenRecord, ...] = (),
    erosion_screen: ScreenRecord | None = None,
    fouling_screen: ScreenRecord | None = None,
    thermal_screen: ScreenRecord | None = None,
    construction_screen: ScreenRecord | None = None,
    fiv_screen: FIVScreen | None = None,
    applicability: ApplicabilityLedger | None = None,
    completeness: CompletenessLedger | None = None,
    request_hash_value: str = "",
) -> tuple[tuple[str, str], ...]:
    all_screens = velocity_screens + tuple(
        item
        for item in (erosion_screen, fouling_screen, thermal_screen, construction_screen)
        if item is not None
    )
    source_payload = {
        "source_definition_id": authority.SOURCE_DEFINITION_ID,
        "screening_sources": (
            authority.SOURCE_PETTIGREW_TAYLOR_PART1,
            authority.SOURCE_PETTIGREW_TAYLOR_PART2,
            authority.SOURCE_NIST_THERMAL_EXPANSION,
            authority.SOURCE_BELL_GOSSETT_UTUBE,
            authority.SOURCE_CHEMICAL_ENGINEER_CONSTRUCTION,
            authority.SOURCE_ELSEVIER_SHELL_TUBE_OVERVIEW,
        ),
        "standard_boundary": "TASK012_TASK020_APPROVED_RULE_PACK_ONLY",
    }
    semantic: list[tuple[str, str]] = [
        (
            "source_definition_payload_hash",
            sha256_domain_hex("task167.source-definition.v1", source_payload),
        ),
        (
            "task020_configuration_payload_hash",
            sha256_domain_hex(
                "task167.task020.v1",
                configuration_projection(request.task020_configuration),
            ),
        ),
        (
            "task166_result_payload_hash",
            sha256_domain_hex(
                "task167.task166.v1", task166_identity_projection(request.task166_result)
            ),
        ),
        (
            "tube_side_result_payload_hash",
            sha256_domain_hex(
                "task167.tube-side.v1",
                tube_side_identity_projection(request.tube_side_result),
            ),
        ),
        (
            "screening_requirements_payload_hash",
            sha256_domain_hex(
                "task167.requirements.v1",
                requirements_projection(request.screening_requirements),
            ),
        ),
        (
            "screening_property_payload_hash",
            sha256_domain_hex(
                "task167.properties.v1",
                tuple(
                    (item.name, getattr(request.screening_property_snapshot, item.name))
                    for item in fields(request.screening_property_snapshot)
                ),
            ),
        ),
        (
            "screen_records_payload_hash",
            sha256_domain_hex(
                "task167.screens.v1",
                tuple(screen_projection(item) for item in all_screens),
            ),
        ),
        ("fiv_payload_hash", sha256_domain_hex("task167.fiv.v1", fiv_projection(fiv_screen))),
        (
            "applicability_payload_hash",
            sha256_domain_hex("task167.applicability.v1", applicability_projection(applicability)),
        ),
        (
            "completeness_payload_hash",
            sha256_domain_hex(
                "task167.completeness.v1",
                None
                if completeness is None
                else (
                    completeness.required_fields,
                    completeness.present_fields,
                    completeness.status,
                ),
            ),
        ),
    ]
    semantic.append(
        (
            "calculation_run_payload_hash",
            sha256_domain_hex(
                "task167.calculation-run.v1",
                {
                    "request_hash": request_hash_value,
                    "semantic_hash_fields": SEMANTIC_HASH_FIELDS[:-1],
                    "software_version": authority.IMPLEMENTATION_SOFTWARE_VERSION,
                },
            ),
        )
    )
    return tuple(semantic)


def _cycle_count(nodes: tuple[ProvenanceNode, ...], edges: tuple[ProvenanceEdge, ...]) -> int:
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
        for child in adjacency.get(node_id, ()):
            visit(child)
        active.remove(node_id)
        complete.add(node_id)

    for node in nodes:
        visit(node.node_id)
    return cycles


def build_provenance(
    request: Task167Request,
    result: Task167Result,
    *,
    velocity_screens: tuple[ScreenRecord, ...],
    erosion_screen: ScreenRecord,
    fouling_screen: ScreenRecord,
    thermal_screen: ScreenRecord,
    construction_screen: ScreenRecord,
    fiv_screen: FIVScreen,
    applicability: ApplicabilityLedger,
    completeness: CompletenessLedger,
    request_hash_value: str,
) -> tuple[tuple[tuple[str, str], ...], ProvenanceGraph]:
    semantic = semantic_input_hashes(
        request,
        velocity_screens=velocity_screens,
        erosion_screen=erosion_screen,
        fouling_screen=fouling_screen,
        thermal_screen=thermal_screen,
        construction_screen=construction_screen,
        fiv_screen=fiv_screen,
        applicability=applicability,
        completeness=completeness,
        request_hash_value=request_hash_value,
    )
    smap = dict(semantic)
    calc = smap["calculation_run_payload_hash"]
    nodes = (
        ProvenanceNode("TASK167_SOURCE_AUTHORITY", smap["source_definition_payload_hash"]),
        ProvenanceNode("TASK020_CONFIGURATION", smap["task020_configuration_payload_hash"]),
        ProvenanceNode("TASK166_RESULT", smap["task166_result_payload_hash"]),
        ProvenanceNode("TUBE_SIDE_RESULT", smap["tube_side_result_payload_hash"]),
        ProvenanceNode(
            "TASK167_SCREENING_REQUIREMENTS", smap["screening_requirements_payload_hash"]
        ),
        ProvenanceNode("TASK167_SCREENING_PROPERTIES", smap["screening_property_payload_hash"]),
        ProvenanceNode("TASK167_SCREEN_RECORDS", smap["screen_records_payload_hash"]),
        ProvenanceNode("TASK167_FIV_SCREEN", smap["fiv_payload_hash"]),
        ProvenanceNode("TASK167_APPLICABILITY", smap["applicability_payload_hash"]),
        ProvenanceNode("TASK167_COMPLETENESS", smap["completeness_payload_hash"]),
        ProvenanceNode("TASK167_CALCULATION_RUN", calc),
        ProvenanceNode("TASK167_RESULT", "sha256:" + result.result_hash),
    )
    edges = tuple(
        ProvenanceEdge(node.node_id, "SUPPLIES", "TASK167_CALCULATION_RUN") for node in nodes[:-2]
    ) + (
        ProvenanceEdge("TASK167_SOURCE_AUTHORITY", "AUTHORIZES", "TASK167_CALCULATION_RUN"),
        ProvenanceEdge("TASK167_CALCULATION_RUN", "PRODUCES", "TASK167_RESULT"),
    )
    # The source node appears in the first tuple and the explicit AUTHORIZES
    # edge; duplicate edges are semantic duplicates, not graph cycles.
    edges = tuple(dict.fromkeys(edges))
    self_edges = sum(edge.source_node_id == edge.target_node_id for edge in edges)
    graph_payload = {
        "nodes": tuple((node.node_id, node.payload_hash) for node in nodes),
        "edges": tuple((edge.source_node_id, edge.relation, edge.target_node_id) for edge in edges),
    }
    graph = ProvenanceGraph(
        nodes=nodes,
        edges=edges,
        graph_hash=provenance_hash(graph_payload),
        self_edge_count=self_edges,
        cycle_count=_cycle_count(nodes, edges),
    )
    return semantic, graph


__all__ = ["SEMANTIC_HASH_FIELDS", "build_provenance", "semantic_input_hashes"]
