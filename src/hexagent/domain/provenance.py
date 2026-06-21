from __future__ import annotations

import copy
import hashlib
import json
from enum import StrEnum
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Node types
# ---------------------------------------------------------------------------


class ProvenanceNodeType(StrEnum):
    """Stable node-type identifiers for provenance graphs."""

    CASE_REVISION = "CASE_REVISION"
    INPUT_FILE = "INPUT_FILE"
    CALCULATION_RUN = "CALCULATION_RUN"
    CORRELATION = "CORRELATION"
    PROPERTY_CALL = "PROPERTY_CALL"
    EXCHANGER_SERVICE = "EXCHANGER_SERVICE"
    OPTIMIZER = "OPTIMIZER"
    REPORT = "REPORT"
    EXTERNAL = "EXTERNAL"
    INTERMEDIATE = "INTERMEDIATE"
    RESULT = "RESULT"
    WARNING = "WARNING"
    BLOCKER = "BLOCKER"


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------


class ProvenanceNode(BaseModel):
    """A single node in a provenance graph.

    ``metadata`` is a frozen mapping.  ``payload_hash`` records the
    SHA-256 content hash of the node's engineering payload, enabling
    tamper-evident provenance chains.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: UUID
    node_type: ProvenanceNodeType
    label: str = Field(default="", min_length=0)
    metadata: tuple[tuple[str, Any], ...] = Field(default_factory=tuple)
    payload_hash: str

    @model_validator(mode="after")
    def _validate_payload_hash(self) -> Self:
        if not self.payload_hash.startswith("sha256:"):
            raise ValueError(
                f"payload_hash must start with 'sha256:', got {self.payload_hash!r}"
            )
        hex_part = self.payload_hash[7:]
        if len(hex_part) != 64:
            raise ValueError(
                f"payload_hash hex part must be 64 chars, got {len(hex_part)}"
            )
        try:
            int(hex_part, 16)
        except ValueError:
            raise ValueError(f"payload_hash contains invalid hex: {self.payload_hash!r}") from None
        return self

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> Self:
        return cls.model_validate_json(data)


# ---------------------------------------------------------------------------
# Edge
# ---------------------------------------------------------------------------


class ProvenanceEdge(BaseModel):
    """A directed edge in a provenance graph."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: UUID
    target_id: UUID
    relation: str = Field(default="", min_length=0)
    metadata: tuple[tuple[str, Any], ...] = Field(default_factory=tuple)

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> Self:
        return cls.model_validate_json(data)


# ---------------------------------------------------------------------------
# Graph with DAG validation
# ---------------------------------------------------------------------------


class ProvenanceGraph(BaseModel):
    """Directed acyclic graph of provenance nodes and edges.

    Nodes and edges are stored as **tuples** (deeply immutable).
    Validates on construction:
    * Unique node IDs.
    * All edge endpoints reference existing nodes.
    * No self-loops.
    * The graph is acyclic (DAG).
    * At least one ``CASE_REVISION`` node is present when nodes exist.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    nodes: tuple[ProvenanceNode, ...] = Field(default_factory=tuple)
    edges: tuple[ProvenanceEdge, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_graph(self) -> Self:
        # --- unique node IDs ---
        node_ids: list[UUID] = [n.node_id for n in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            dupes = [nid for nid in node_ids if node_ids.count(nid) > 1]
            raise ValueError(f"Duplicate node IDs: {set(dupes)}")

        node_set = set(node_ids)

        # --- edges reference existing nodes ---
        for edge in self.edges:
            if edge.source_id not in node_set:
                raise ValueError(f"Edge source {edge.source_id} not found in nodes")
            if edge.target_id not in node_set:
                raise ValueError(f"Edge target {edge.target_id} not found in nodes")

        # --- no self-loops ---
        for edge in self.edges:
            if edge.source_id == edge.target_id:
                raise ValueError(f"Self-loop on node {edge.source_id}")

        # --- DAG: topological sort via Kahn's algorithm ---
        adj: dict[UUID, list[UUID]] = {nid: [] for nid in node_set}
        in_degree: dict[UUID, int] = {nid: 0 for nid in node_set}
        for edge in self.edges:
            adj[edge.source_id].append(edge.target_id)
            in_degree[edge.target_id] += 1

        queue: list[UUID] = [nid for nid, deg in in_degree.items() if deg == 0]
        visited = 0
        while queue:
            current = queue.pop()
            visited += 1
            for neighbour in adj[current]:
                in_degree[neighbour] -= 1
                if in_degree[neighbour] == 0:
                    queue.append(neighbour)

        if visited != len(node_set):
            raise ValueError("Provenance graph contains a cycle")

        # --- when nodes exist, must contain CASE_REVISION and CALCULATION_RUN ---
        if self.nodes:
            node_types = {n.node_type for n in self.nodes}
            if ProvenanceNodeType.CASE_REVISION not in node_types:
                raise ValueError(
                    "Provenance graph must contain a CASE_REVISION node"
                )
            if ProvenanceNodeType.CALCULATION_RUN not in node_types:
                raise ValueError(
                    "Provenance graph must contain a CALCULATION_RUN node"
                )

        return self

    # --- canonical ordering for hashing ---

    def _canonical_node_key(self, node: ProvenanceNode) -> str:
        """Deterministic sort key for nodes."""
        return f"{node.node_type.value}:{node.node_id}"

    def _canonical_edge_key(self, edge: ProvenanceEdge) -> str:
        """Deterministic sort key for edges."""
        return f"{edge.source_id}:{edge.target_id}:{edge.relation}"

    def _canonical_payload(self) -> dict[str, Any]:
        """Return a canonical dict independent of insertion order."""
        sorted_nodes = sorted(self.nodes, key=self._canonical_node_key)
        sorted_edges = sorted(self.edges, key=self._canonical_edge_key)
        return {
            "schema_version": self.schema_version,
            "nodes": [n.model_dump() for n in sorted_nodes],
            "edges": [e.model_dump() for e in sorted_edges],
        }

    def compute_hash(self) -> str:
        """Return a deterministic SHA-256 hash of the graph structure."""
        payload = json.dumps(
            self._canonical_payload(),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        return f"sha256:{hashlib.sha256(payload).hexdigest()}"

    # --- serialisation helpers ---

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> Self:
        return cls.model_validate_json(data)


def deep_copy_graph(graph: ProvenanceGraph) -> ProvenanceGraph:
    """Return a deeply-copied snapshot of *graph*.

    This is the recommended way for repositories to hand out stored
    graphs — it guarantees the caller cannot mutate repository state.
    """
    return copy.deepcopy(graph)


__all__ = [
    "ProvenanceEdge",
    "ProvenanceGraph",
    "ProvenanceNode",
    "ProvenanceNodeType",
    "deep_copy_graph",
]
