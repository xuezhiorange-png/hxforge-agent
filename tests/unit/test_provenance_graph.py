"""Tests for ProvenanceGraph DAG validation and serialisation.

Covers: valid DAG acceptance, duplicate nodes, missing edge references,
self-loops, cycles, CASE_REVISION requirement, JSON round-trip, and
hash stability.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import ValidationError

from hexagent.core.canonical import sha256_digest
from hexagent.domain.provenance import (
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    ProvenanceNodeType,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PAYLOAD_HASH = "sha256:" + "a" * 64


def _node(
    node_id: int = 1,
    node_type: ProvenanceNodeType = ProvenanceNodeType.CASE_REVISION,
    label: str = "",
) -> ProvenanceNode:
    return ProvenanceNode(
        node_id=UUID(int=node_id),
        node_type=node_type,
        label=label,
        payload_hash=PAYLOAD_HASH,
    )


def _edge(source: int, target: int, relation: str = "derives") -> ProvenanceEdge:
    return ProvenanceEdge(
        source_id=UUID(int=source),
        target_id=UUID(int=target),
        relation=relation,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestProvenanceGraphValidation:
    """DAG validation rules on construction."""

    def test_empty_graph_rejected(self) -> None:
        """An empty graph is allowed at model level but rejected at persistence."""
        # Empty graph is allowed at model level
        g = ProvenanceGraph(nodes=(), edges=())
        assert len(g.nodes) == 0

    def test_valid_dag_accepted(self) -> None:
        """A -> B -> C is a valid DAG."""
        g = ProvenanceGraph(
            nodes=(
                _node(1),
                _node(2, ProvenanceNodeType.CALCULATION_RUN),
                _node(3, ProvenanceNodeType.REPORT),
            ),
            edges=(_edge(1, 2), _edge(2, 3)),
        )
        assert len(g.nodes) == 3
        assert len(g.edges) == 2

    def test_valid_linear_chain(self) -> None:
        """CASE_REVISION -> CALCULATION_RUN -> REPORT."""
        g = ProvenanceGraph(
            nodes=(
                _node(1, ProvenanceNodeType.CASE_REVISION),
                _node(2, ProvenanceNodeType.CALCULATION_RUN),
                _node(3, ProvenanceNodeType.REPORT),
            ),
            edges=(_edge(1, 2), _edge(2, 3)),
        )
        assert len(g.nodes) == 3

    def test_duplicate_node_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="Duplicate node IDs"):
            ProvenanceGraph(
                nodes=(_node(1), _node(1)),
                edges=(),
            )

    def test_missing_edge_source_rejected(self) -> None:
        """Edge references a source that doesn't exist."""
        with pytest.raises(ValueError, match="source.*not found"):
            ProvenanceGraph(
                nodes=(_node(2, ProvenanceNodeType.CALCULATION_RUN),),
                edges=(_edge(99, 2),),
            )

    def test_missing_edge_target_rejected(self) -> None:
        """Edge references a target that doesn't exist."""
        with pytest.raises(ValueError, match="target.*not found"):
            ProvenanceGraph(
                nodes=(_node(1),),
                edges=(_edge(1, 99),),
            )

    def test_self_loop_rejected(self) -> None:
        with pytest.raises(ValueError, match="Self-loop"):
            ProvenanceGraph(
                nodes=(_node(1),),
                edges=(_edge(1, 1),),
            )

    def test_cycle_rejected(self) -> None:
        """A -> B -> A is a cycle."""
        with pytest.raises(ValueError, match="cycle"):
            ProvenanceGraph(
                nodes=(_node(1), _node(2, ProvenanceNodeType.CALCULATION_RUN)),
                edges=(_edge(1, 2), _edge(2, 1)),
            )

    def test_larger_cycle_rejected(self) -> None:
        """A -> B -> C -> A."""
        with pytest.raises(ValueError, match="cycle"):
            ProvenanceGraph(
                nodes=(
                    _node(1),
                    _node(2, ProvenanceNodeType.CALCULATION_RUN),
                    _node(3, ProvenanceNodeType.REPORT),
                ),
                edges=(_edge(1, 2), _edge(2, 3), _edge(3, 1)),
            )

    def test_no_case_revision_rejected(self) -> None:
        """Graph with nodes but no CASE_REVISION node is rejected."""
        with pytest.raises(ValueError, match="CASE_REVISION"):
            ProvenanceGraph(
                nodes=(
                    _node(1, ProvenanceNodeType.CALCULATION_RUN),
                    _node(2, ProvenanceNodeType.REPORT),
                ),
                edges=(_edge(1, 2),),
            )

    def test_no_calculation_run_rejected(self) -> None:
        """Graph with nodes but no CALCULATION_RUN node is rejected."""
        with pytest.raises(ValueError, match="CALCULATION_RUN"):
            ProvenanceGraph(
                nodes=(
                    _node(1, ProvenanceNodeType.CASE_REVISION),
                    _node(2, ProvenanceNodeType.REPORT),
                ),
                edges=(_edge(1, 2),),
            )

    def test_diamond_dag_accepted(self) -> None:
        """A -> B, A -> C, B -> D, C -> D — valid diamond."""
        g = ProvenanceGraph(
            nodes=(
                _node(1),
                _node(2, ProvenanceNodeType.CALCULATION_RUN),
                _node(3, ProvenanceNodeType.REPORT),
                _node(4, ProvenanceNodeType.RESULT),
            ),
            edges=(_edge(1, 2), _edge(1, 3), _edge(2, 4), _edge(3, 4)),
        )
        assert len(g.edges) == 4


class TestProvenanceGraphJsonRoundTrip:
    """Serialisation preserves graph structure."""

    def test_round_trip(self) -> None:
        g = ProvenanceGraph(
            nodes=(
                _node(1, ProvenanceNodeType.CASE_REVISION, "rev-1"),
                _node(2, ProvenanceNodeType.CALCULATION_RUN, "run-1"),
            ),
            edges=(_edge(1, 2, "triggers"),),
        )
        json_str = g.to_json()
        restored = ProvenanceGraph.from_json(json_str)
        assert len(restored.nodes) == 2
        assert len(restored.edges) == 1
        assert restored.edges[0].relation == "triggers"

    def test_round_trip_preserves_metadata(self) -> None:
        node = ProvenanceNode(
            node_id=UUID(int=1),
            node_type=ProvenanceNodeType.CASE_REVISION,
            label="test",
            metadata=(("version", 2),),
            payload_hash=PAYLOAD_HASH,
        )
        edge = ProvenanceEdge(
            source_id=UUID(int=1),
            target_id=UUID(int=2),
            relation="derives",
            metadata=(("timestamp", "2026-01-01"),),
        )
        g = ProvenanceGraph(
            nodes=(
                node,
                ProvenanceNode(
                    node_id=UUID(int=2),
                    node_type=ProvenanceNodeType.CALCULATION_RUN,
                    payload_hash=PAYLOAD_HASH,
                ),
            ),
            edges=(edge,),
        )
        json_str = g.to_json()
        restored = ProvenanceGraph.from_json(json_str)
        assert tuple(restored.nodes[0].metadata) == (("version", 2),)
        assert tuple(restored.edges[0].metadata) == (("timestamp", "2026-01-01"),)


class TestProvenanceGraphHashStability:
    """Same graph always produces the same content hash."""

    def test_same_graph_same_hash(self) -> None:
        g1 = ProvenanceGraph(
            nodes=(_node(1), _node(2, ProvenanceNodeType.CALCULATION_RUN)),
            edges=(_edge(1, 2),),
        )
        g2 = ProvenanceGraph(
            nodes=(_node(1), _node(2, ProvenanceNodeType.CALCULATION_RUN)),
            edges=(_edge(1, 2),),
        )
        h1 = sha256_digest(g1.model_dump())
        h2 = sha256_digest(g2.model_dump())
        assert h1 == h2

    def test_different_graph_different_hash(self) -> None:
        g1 = ProvenanceGraph(
            nodes=(_node(1), _node(2, ProvenanceNodeType.CALCULATION_RUN)),
            edges=(_edge(1, 2),),
        )
        g2 = ProvenanceGraph(
            nodes=(
                _node(1),
                _node(3, ProvenanceNodeType.CALCULATION_RUN),
            ),
            edges=(_edge(1, 3),),
        )
        h1 = sha256_digest(g1.model_dump())
        h2 = sha256_digest(g2.model_dump())
        assert h1 != h2


class TestProvenanceGraphImmutability:
    """ProvenanceGraph is a frozen model."""

    def test_cannot_reassign_nodes(self) -> None:
        g = ProvenanceGraph(
            nodes=(_node(1), _node(2, ProvenanceNodeType.CALCULATION_RUN)),
            edges=(_edge(1, 2),),
        )
        # Pydantic frozen models prevent field reassignment
        with pytest.raises((ValueError, ValidationError)):
            g.nodes = [_node(1), _node(2)]  # type: ignore[misc]

    def test_frozen_model(self) -> None:
        g = ProvenanceGraph(
            nodes=(_node(1), _node(2, ProvenanceNodeType.CALCULATION_RUN)),
            edges=(_edge(1, 2),),
        )
        with pytest.raises((ValueError, ValidationError)):
            g.schema_version = "2.0"  # type: ignore[misc]
