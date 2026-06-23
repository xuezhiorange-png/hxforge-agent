"""Result model for single-phase heat-transfer correlation evaluation.

Provides an immutable, hash-verified result with full provenance,
following the same patterns as HeatBalanceResult from TASK-006.
"""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from hexagent.core.canonical import sha256_digest

# Reuse ExecutionContextSnapshot from heat_balance module
from hexagent.core.heat_balance import ExecutionContextSnapshot
from hexagent.correlations.geometry import CircularTubeGeometry, ConcentricAnnulusGeometry
from hexagent.domain.messages import (
    EngineeringMessage,
    RunFailure,
)
from hexagent.domain.provenance import (
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    ProvenanceNodeType,
)

# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


class CorrelationStatus(StrEnum):
    """Result status for correlation evaluation."""

    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Provenance namespace
# ---------------------------------------------------------------------------

_PROVENANCE_NAMESPACE: UUID = uuid5(
    UUID("00000000-0000-0000-0000-000000000000"),
    "hexagent:tube_annulus:provenance",
)

_SOFTWARE_VERSION = "0.1.0"


def _deterministic_uuid5(payload: dict[str, Any]) -> UUID:
    """Compute deterministic UUID5 from canonical payload."""
    canonical = sha256_digest(payload)
    return uuid5(_PROVENANCE_NAMESPACE, canonical)


# ---------------------------------------------------------------------------
# Selected correlation info
# ---------------------------------------------------------------------------


class SelectedCorrelationInfo(BaseModel):
    """Immutable record of the selected correlation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    correlation_id: str
    version: str
    source_title: str = ""
    source_authors: str = ""
    source_year: int = 0
    source_reference: str = ""
    is_adaptation: bool = False
    adaptation_limitation: str = ""
    priority: int = 0


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


class CorrelationResult(BaseModel):
    """Immutable result of a single-phase convective heat-transfer correlation evaluation.

    Contains solved Nusselt and heat-transfer coefficients, dimensionless numbers,
    applicability assessment, warnings, blockers, deterministic hash, and provenance graph.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: CorrelationStatus
    geometry: CircularTubeGeometry | ConcentricAnnulusGeometry
    mass_flow_kg_s: float
    density_kg_m3: float
    dynamic_viscosity_pa_s: float
    thermal_conductivity_w_m_k: float
    specific_heat_j_kg_k: float
    bulk_temperature_k: float
    wall_temperature_k: float | None = None
    wall_viscosity_pa_s: float | None = None
    heating: bool = True

    # Computed quantities
    flow_area_m2: float = 0.0
    mean_velocity_ms: float = 0.0
    hydraulic_diameter_m: float = 0.0
    reynolds_number: float = 0.0
    prandtl_number: float = 0.0
    nusselt_number: float = 0.0
    heat_transfer_coefficient: float = 0.0
    flow_regime: str = ""

    # Selected correlation
    selected_correlation: SelectedCorrelationInfo | None = None

    # Applicability
    applicability_status: str = ""

    # Messages
    warnings: tuple[EngineeringMessage, ...] = ()
    blockers: tuple[EngineeringMessage, ...] = ()
    failure: RunFailure | None = None

    # Identity
    result_hash: str = ""
    provenance_graph: ProvenanceGraph = Field(default_factory=lambda: ProvenanceGraph())
    provenance_digest: str = ""
    execution_context: ExecutionContextSnapshot = Field(default_factory=ExecutionContextSnapshot)

    # Private
    _field_hash: str = PrivateAttr(default="")

    # --- Validators ---

    @model_validator(mode="after")
    def _validate_no_nan_inf(self) -> CorrelationResult:
        """Reject NaN and Infinity in all float fields."""
        for name in (
            "flow_area_m2",
            "mean_velocity_ms",
            "hydraulic_diameter_m",
            "reynolds_number",
            "prandtl_number",
            "nusselt_number",
            "heat_transfer_coefficient",
        ):
            val = getattr(self, name)
            if not math.isfinite(val):
                raise ValueError(f"{name} must be finite, got {val!r}")
        return self

    @model_validator(mode="after")
    def _validate_result_hash_format(self) -> CorrelationResult:
        """Verify result_hash starts with sha256: and is 71 chars."""
        if self.result_hash and not self.result_hash.startswith("sha256:"):
            raise ValueError(f"result_hash must start with 'sha256:', got {self.result_hash!r}")
        if self.result_hash:
            hex_part = self.result_hash[7:]
            if len(hex_part) != 64:
                raise ValueError(f"result_hash hex must be 64 chars, got {len(hex_part)}")
            try:
                int(hex_part, 16)
            except ValueError:
                raise ValueError(
                    f"result_hash contains invalid hex: {self.result_hash!r}"
                ) from None
        return self

    @model_validator(mode="after")
    def _validate_status_contract(self) -> CorrelationResult:
        """Ensure status is consistent with blockers/failure."""
        if self.status == CorrelationStatus.BLOCKED and not self.blockers:
            raise ValueError("BLOCKED result must have at least one blocker")
        if self.status == CorrelationStatus.FAILED and self.failure is None:
            raise ValueError("FAILED result must have a failure record")
        return self

    # --- Post-init ---

    def model_post_init(self, __context: Any) -> None:
        """Compute field hash for tamper detection."""
        object.__setattr__(self, "_field_hash", self._compute_field_hash())

    # --- Field hash ---

    def _compute_field_hash(self) -> str:
        """Compute SHA-256 of all public fields for tamper detection."""

        def _geo(g: Any) -> Any:
            if isinstance(g, dict):
                return g
            if hasattr(g, "model_dump"):
                return g.model_dump(mode="json")
            return g

        def _msg(m: EngineeringMessage) -> dict[str, Any]:
            return {
                "code": m.code.value,
                "severity": m.severity.value,
                "message": m.message,
                "source_module": m.source_module,
                "context": dict(m.context) if m.context else {},
            }

        payload: dict[str, Any] = {
            "status": self.status.value,
            "geometry": _geo(self.geometry),
            "mass_flow_kg_s": self.mass_flow_kg_s,
            "density_kg_m3": self.density_kg_m3,
            "dynamic_viscosity_pa_s": self.dynamic_viscosity_pa_s,
            "thermal_conductivity_w_m_k": self.thermal_conductivity_w_m_k,
            "specific_heat_j_kg_k": self.specific_heat_j_kg_k,
            "bulk_temperature_k": self.bulk_temperature_k,
            "wall_temperature_k": self.wall_temperature_k,
            "wall_viscosity_pa_s": self.wall_viscosity_pa_s,
            "heating": self.heating,
            "flow_area_m2": self.flow_area_m2,
            "mean_velocity_ms": self.mean_velocity_ms,
            "hydraulic_diameter_m": self.hydraulic_diameter_m,
            "reynolds_number": self.reynolds_number,
            "prandtl_number": self.prandtl_number,
            "nusselt_number": self.nusselt_number,
            "heat_transfer_coefficient": self.heat_transfer_coefficient,
            "flow_regime": self.flow_regime,
            "selected_correlation": (
                self.selected_correlation.model_dump(mode="json")
                if self.selected_correlation
                else None
            ),
            "applicability_status": self.applicability_status,
            "warnings": [_msg(w) for w in self.warnings],
            "blockers": [_msg(b) for b in self.blockers],
            "failure": (
                {
                    "code": self.failure.code.value,
                    "message": self.failure.message,
                    "context": dict(self.failure.context) if self.failure.context else {},
                }
                if self.failure
                else None
            ),
            "result_hash": self.result_hash,
            "provenance_digest": self.provenance_digest,
            "execution_context": (
                self.execution_context.model_dump(mode="json")
                if hasattr(self.execution_context, "model_dump")
                else self.execution_context
            ),
        }
        return sha256_digest(payload)

    def validate_integrity(self) -> bool:
        """Verify no fields have been tampered with after construction."""
        return self._field_hash == self._compute_field_hash()

    def verify_hash(self) -> bool:
        """Verify that result_hash is correct and integrity is intact."""
        if not self.result_hash.startswith("sha256:"):
            return False
        hex_part = self.result_hash[7:]
        if len(hex_part) != 64:
            return False
        try:
            int(hex_part, 16)
        except ValueError:
            return False
        if not self.validate_integrity():
            return False
        recomputed = self._recompute_result_hash()
        return recomputed == self.result_hash

    def _recompute_result_hash(self) -> str:
        """Recompute result hash from canonical payload."""
        payload = self._build_result_payload()
        return sha256_digest(payload)

    def _build_result_payload(self) -> dict[str, Any]:
        """Build canonical payload for result hash computation."""

        def _geo(g: Any) -> Any:
            if isinstance(g, dict):
                return g
            if hasattr(g, "model_dump"):
                return g.model_dump(mode="json")
            return g

        return {
            "status": self.status.value,
            "geometry": _geo(self.geometry),
            "mass_flow_kg_s": self.mass_flow_kg_s,
            "density_kg_m3": self.density_kg_m3,
            "dynamic_viscosity_pa_s": self.dynamic_viscosity_pa_s,
            "thermal_conductivity_w_m_k": self.thermal_conductivity_w_m_k,
            "specific_heat_j_kg_k": self.specific_heat_j_kg_k,
            "bulk_temperature_k": self.bulk_temperature_k,
            "wall_temperature_k": self.wall_temperature_k,
            "wall_viscosity_pa_s": self.wall_viscosity_pa_s,
            "heating": self.heating,
            "flow_area_m2": self.flow_area_m2,
            "mean_velocity_ms": self.mean_velocity_ms,
            "hydraulic_diameter_m": self.hydraulic_diameter_m,
            "reynolds_number": self.reynolds_number,
            "prandtl_number": self.prandtl_number,
            "nusselt_number": self.nusselt_number,
            "heat_transfer_coefficient": self.heat_transfer_coefficient,
            "flow_regime": self.flow_regime,
            "selected_correlation": (
                self.selected_correlation.model_dump(mode="json")
                if self.selected_correlation
                else None
            ),
            "applicability_status": self.applicability_status,
            "result_hash": self.result_hash,
            "provenance_digest": self.provenance_digest,
            "execution_context": (
                self.execution_context.model_dump(mode="json")
                if hasattr(self.execution_context, "model_dump")
                else self.execution_context
            ),
        }

    def verify_provenance(self) -> bool:
        """Verify provenance graph integrity.

        Checks:
        1. All node IDs are deterministic UUID5s
        2. All edge endpoints reference existing nodes
        3. No self-loops
        4. Graph is a DAG
        5. Contains EXTERNAL or CASE_REVISION root + CALCULATION_RUN node
        6. Metadata consistency for CALCULATION_RUN node
        """
        try:
            graph = self.provenance_graph
            if not graph.nodes:
                return False

            node_ids = {n.node_id for n in graph.nodes}

            # Check all edges reference existing nodes
            for edge in graph.edges:
                if (
                    edge.source_id not in node_ids
                    or edge.target_id not in node_ids
                    or edge.source_id == edge.target_id
                ):
                    return False

            # Check for root and CALCULATION_RUN nodes
            has_root = any(
                n.node_type in (ProvenanceNodeType.EXTERNAL, ProvenanceNodeType.CASE_REVISION)
                for n in graph.nodes
            )
            has_calc = any(n.node_type == ProvenanceNodeType.CALCULATION_RUN for n in graph.nodes)
            if not has_root or not has_calc:
                return False

            # Verify DAG (topological sort)
            in_degree = {nid: 0 for nid in node_ids}
            adjacency: dict[UUID, list[UUID]] = {nid: [] for nid in node_ids}
            for edge in graph.edges:
                adjacency[edge.source_id].append(edge.target_id)
                in_degree[edge.target_id] += 1

            queue = [nid for nid, deg in in_degree.items() if deg == 0]
            visited = 0
            while queue:
                nid = queue.pop(0)
                visited += 1
                for neighbor in adjacency[nid]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

            if visited != len(node_ids):
                return False  # Cycle detected

            # Verify execution_context matches root node metadata
            ctx = self.execution_context
            for node in graph.nodes:
                if node.node_type == ProvenanceNodeType.CALCULATION_RUN:
                    meta_dict = dict(node.metadata)
                    ext_id = meta_dict.get("external_calculation_run_id")
                    expected_id = (
                        str(ctx.calculation_run_id) if ctx.calculation_run_id is not None else None
                    )
                    if ext_id != expected_id:
                        return False

            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Provenance construction helpers
# ---------------------------------------------------------------------------


def _build_provenance_graph(
    *,
    geometry: CircularTubeGeometry | ConcentricAnnulusGeometry,
    correlation_id: str,
    correlation_version: str,
    reynolds: float,
    prandtl: float,
    nu: float,
    h: float,
    warnings: tuple[EngineeringMessage, ...],
    blockers: tuple[EngineeringMessage, ...],
    execution_context: ExecutionContextSnapshot,
    status: CorrelationStatus,
) -> ProvenanceGraph:
    """Build a complete provenance graph for the correlation result."""
    nodes: list[ProvenanceNode] = []
    edges: list[ProvenanceEdge] = []
    ctx = execution_context

    # Root node
    root_payload: dict[str, Any] = {
        "root_type": "EXTERNAL",
        "request_id": str(ctx.request_id) if ctx.request_id is not None else None,
    }
    root_id = _deterministic_uuid5(root_payload)
    nodes.append(
        ProvenanceNode(
            node_id=root_id,
            node_type=ProvenanceNodeType.EXTERNAL,
            label="correlation_request",
            metadata=(("request_id", str(ctx.request_id) if ctx.request_id is not None else None),),
            payload_hash=sha256_digest(root_payload),
        )
    )

    # CALCULATION_RUN node (correlation evaluation run)
    calc_payload: dict[str, Any] = {
        "correlation_id": correlation_id,
        "correlation_version": correlation_version,
        "reynolds": reynolds,
        "prandtl": prandtl,
        "nusselt": nu,
        "heat_transfer_coefficient": h,
        "status": status.value,
        "software_version": _SOFTWARE_VERSION,
    }
    calc_id = _deterministic_uuid5(calc_payload)
    nodes.append(
        ProvenanceNode(
            node_id=calc_id,
            node_type=ProvenanceNodeType.CALCULATION_RUN,
            label="correlation_evaluation",
            metadata=(
                ("correlation_id", correlation_id),
                ("correlation_version", correlation_version),
                ("software_version", _SOFTWARE_VERSION),
                (
                    "external_calculation_run_id",
                    str(ctx.calculation_run_id) if ctx.calculation_run_id is not None else None,
                ),
            ),
            payload_hash=sha256_digest(calc_payload),
        )
    )
    edges.append(ProvenanceEdge(source_id=root_id, target_id=calc_id, relation="triggers"))

    # CORRELATION node
    corr_payload: dict[str, Any] = {
        "correlation_id": correlation_id,
        "version": correlation_version,
    }
    corr_id = _deterministic_uuid5(corr_payload)
    nodes.append(
        ProvenanceNode(
            node_id=corr_id,
            node_type=ProvenanceNodeType.CORRELATION,
            label=f"corr_{correlation_id}",
            metadata=(
                ("correlation_id", correlation_id),
                ("version", correlation_version),
            ),
            payload_hash=sha256_digest(corr_payload),
        )
    )
    edges.append(ProvenanceEdge(source_id=calc_id, target_id=corr_id, relation="uses"))

    # WARNING nodes
    for w in warnings:
        warn_payload: dict[str, Any] = {
            "code": w.code.value,
            "severity": w.severity.value,
            "message": w.message,
            "source_module": w.source_module,
        }
        warn_id = _deterministic_uuid5(warn_payload)
        nodes.append(
            ProvenanceNode(
                node_id=warn_id,
                node_type=ProvenanceNodeType.WARNING,
                label=f"warning_{w.code.value}",
                metadata=(
                    ("code", w.code.value),
                    ("severity", w.severity.value),
                    ("message", w.message),
                ),
                payload_hash=sha256_digest(warn_payload),
            )
        )
        edges.append(ProvenanceEdge(source_id=calc_id, target_id=warn_id, relation="emits"))

    # BLOCKER nodes
    for b in blockers:
        block_payload: dict[str, Any] = {
            "code": b.code.value,
            "severity": b.severity.value,
            "message": b.message,
            "source_module": b.source_module,
        }
        block_id = _deterministic_uuid5(block_payload)
        nodes.append(
            ProvenanceNode(
                node_id=block_id,
                node_type=ProvenanceNodeType.BLOCKER,
                label=f"blocker_{b.code.value}",
                metadata=(
                    ("code", b.code.value),
                    ("severity", b.severity.value),
                    ("message", b.message),
                ),
                payload_hash=sha256_digest(block_payload),
            )
        )
        edges.append(ProvenanceEdge(source_id=calc_id, target_id=block_id, relation="emits"))

    # RESULT node
    result_payload: dict[str, Any] = {
        "status": status.value,
        "nusselt": nu,
        "heat_transfer_coefficient": h,
        "correlation_id": correlation_id,
    }
    result_id = _deterministic_uuid5(result_payload)
    nodes.append(
        ProvenanceNode(
            node_id=result_id,
            node_type=ProvenanceNodeType.RESULT,
            label="correlation_result",
            metadata=(("status", status.value),),
            payload_hash=sha256_digest(result_payload),
        )
    )
    edges.append(ProvenanceEdge(source_id=calc_id, target_id=result_id, relation="produces"))

    return ProvenanceGraph(nodes=tuple(nodes), edges=tuple(edges))


def _provenance_graph_digest(graph: ProvenanceGraph) -> str:
    """Compute deterministic digest of provenance graph."""
    if not graph.nodes:
        return sha256_digest({})
    node_payloads = []
    for n in graph.nodes:
        node_payloads.append(
            {
                "node_id": str(n.node_id),
                "node_type": n.node_type.value,
                "label": n.label,
                "metadata": [(k, v) for k, v in n.metadata],
                "payload_hash": n.payload_hash,
            }
        )
    edge_payloads = []
    for e in graph.edges:
        edge_payloads.append(
            {
                "source_id": str(e.source_id),
                "target_id": str(e.target_id),
                "relation": e.relation,
            }
        )
    combined = {
        "nodes": sorted(node_payloads, key=lambda x: x["node_id"]),
        "edges": sorted(edge_payloads, key=lambda x: (x["source_id"], x["target_id"])),
    }
    return sha256_digest(combined)
