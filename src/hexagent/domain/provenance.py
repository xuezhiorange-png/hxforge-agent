from __future__ import annotations

from enum import StrEnum
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Node types
# ---------------------------------------------------------------------------


class ProvenanceNodeType(StrEnum):
    CASE_REVISION = "CASE_REVISION"
    INPUT_FILE = "INPUT_FILE"
    CALCULATION_RUN = "CALCULATION_RUN"
    CORRELATION = "CORRELATION"
    PROPERTY_CALL = "PROPERTY_CALL"
    EXCHANGER_SERVICE = "EXCHANGER_SERVICE"
    OPTIMIZER = "OPTIMIZER"
    REPORT = "REPORT"
    EXTERNAL = "EXTERNAL"


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------


class ProvenanceNode(BaseModel):
    """A single node in a provenance graph."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: UUID
    node_type: ProvenanceNodeType
    label: str = Field(default="", min_length=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

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
    metadata: dict[str, Any] = Field(default_factory=dict)

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

    Validates on construction:
    * Unique node IDs.
    * All edge endpoints reference existing nodes.
    * No self-loops.
    * The graph is acyclic (DAG).
    * At least one ``CASE_REVISION`` node is present.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    nodes: list[ProvenanceNode] = Field(default_factory=list)
    edges: list[ProvenanceEdge] = Field(default_factory=list)

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

        # --- at least one CASE_REVISION node (only when nodes exist) ---
        if self.nodes:
            has_case_revision = any(
                n.node_type == ProvenanceNodeType.CASE_REVISION for n in self.nodes
            )
            if not has_case_revision:
                raise ValueError(
                    "Provenance graph must contain at least one CASE_REVISION node"
                )

        return self

    # --- serialisation helpers ---

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> Self:
        return cls.model_validate_json(data)


__all__ = [
    "ProvenanceEdge",
    "ProvenanceGraph",
    "ProvenanceNode",
    "ProvenanceNodeType",
]
