"""TASK160 provenance graph and artifact-payload tests."""

from __future__ import annotations

from uuid import UUID

import pytest

from hexagent.domain.provenance import ProvenanceNodeType
from hexagent.exchangers.shell_tube.thermal_stream_state.models import (
    CalculationRunScope,
    Task160Provenance,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.provenance import (
    source_authority_node,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.service import validate_request

from .test_ingress_models import make_r607_raw


def test_success_graph_has_required_root_calculation_and_result_node() -> None:
    result = validate_request(make_r607_raw()).valid
    assert result is not None
    graph = result.provenance.graph
    assert any(node.node_type is ProvenanceNodeType.EXTERNAL for node in graph.nodes)
    assert any(node.node_type is ProvenanceNodeType.CALCULATION_RUN for node in graph.nodes)
    artifact_nodes = [node for node in graph.nodes if node.node_type is ProvenanceNodeType.RESULT]
    assert len(artifact_nodes) == 1
    assert artifact_nodes[0].node_id == result.result_id
    assert artifact_nodes[0].payload_hash == "sha256:" + result.result_hash
    assert all(edge.source_id != edge.target_id for edge in graph.edges)
    assert result.provenance.provenance_hash == graph.compute_hash()


def test_typed_blocked_graph_uses_blocker_node_payload_format() -> None:
    raw = make_r607_raw()
    raw["stream_records"][1]["inlet_temperature_K"] = "390.15"  # type: ignore[index]
    result = validate_request(raw).typed_blocked
    assert result is not None
    graph = result.provenance.graph
    assert any(node.node_type is ProvenanceNodeType.EXTERNAL for node in graph.nodes)
    assert any(node.node_type is ProvenanceNodeType.CALCULATION_RUN for node in graph.nodes)
    artifact_nodes = [node for node in graph.nodes if node.node_type is ProvenanceNodeType.BLOCKER]
    assert len(artifact_nodes) == 1
    assert artifact_nodes[0].node_id == result.blocked_result_id
    assert artifact_nodes[0].payload_hash == "sha256:" + result.blocked_result_hash
    assert all(edge.source_id != edge.target_id for edge in graph.edges)


def test_raw_boundary_blocked_result_has_no_fabricated_graph() -> None:
    result = validate_request(make_r607_raw(provenance=None)).raw_boundary_blocked
    assert result is not None
    assert not hasattr(result, "provenance")
    assert result.blockers


def test_source_authority_node_is_fixed_external_evidence() -> None:
    node = source_authority_node()
    assert node.node_type is ProvenanceNodeType.EXTERNAL
    assert node.node_id == UUID("bf2dcd7f-5fa3-5959-9e08-d9cf725dc364")
    assert (
        node.payload_hash
        == "sha256:58a4d9c8cb511ab4db00a25094fd2004af7a52b42ce4a5ba88e0f3f72cac75e1"
    )


def test_provenance_scope_is_explicit_for_success_and_blocked_artifacts() -> None:
    valid = validate_request(make_r607_raw()).valid
    assert valid is not None
    assert CalculationRunScope.SUCCESS.value == "SUCCESS"
    raw = make_r607_raw()
    raw["stream_records"][1]["inlet_temperature_K"] = "390.15"  # type: ignore[index]
    blocked = validate_request(raw).typed_blocked
    assert blocked is not None
    assert blocked.failure_stage.value == "STRICT_VALIDATION"


def test_provenance_hash_must_equal_graph_hash() -> None:
    valid = validate_request(make_r607_raw()).valid
    assert valid is not None
    current = valid.provenance.provenance_hash
    replacement = "sha256:" + ("0" * 64 if current != "sha256:" + "0" * 64 else "1" * 64)
    with pytest.raises(ValueError, match="provenance_hash must equal graph.compute_hash"):
        Task160Provenance(
            producer_identity=valid.provenance.producer_identity,
            upstream_identity_hashes=valid.provenance.upstream_identity_hashes,
            source_evidence_refs=valid.provenance.source_evidence_refs,
            adapter_evidence_refs=valid.provenance.adapter_evidence_refs,
            graph=valid.provenance.graph,
            provenance_hash=replacement,
        )
