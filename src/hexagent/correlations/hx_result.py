"""Result model for single-phase heat-transfer correlation evaluation.

Provides an immutable, hash-verified result with full provenance,
following the same patterns as HeatBalanceResult from TASK-006.

Key design decisions:
- result_hash does NOT enter its own canonical payload (no self-reference).
- _field_hash covers ALL public fields including provenance_graph.
- verify_provenance() is comprehensive: graph digest, node uniqueness,
  edge uniqueness, DAG, payload hash recomputation, UUID5 recomputation,
  root type, CALCULATION_RUN count, CORRELATION node existence,
  WARNING/BLOCKER consistency, RESULT consistency.
- SelectedCorrelationInfo carries full source identity from the definition.
"""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator, model_validator

from hexagent.core.canonical import sha256_digest

# Reuse ExecutionContextSnapshot from heat_balance module
from hexagent.core.heat_balance import ExecutionContextSnapshot
from hexagent.correlations.geometry import CircularTubeGeometry, ConcentricAnnulusGeometry
from hexagent.correlations.models import ApplicabilityAssessment
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
    """Immutable record of the selected correlation.

    All source fields are populated from the CorrelationDefinition
    in the registry — NOT hand-written in the service.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    correlation_id: str
    version: str
    priority: int = 0
    source_title: str = ""
    source_authors: str = ""
    source_year: int = 0
    source_reference: str = ""
    source_verification_status: str = "unverified"
    definition_hash: str = ""
    is_adaptation: bool = False
    adaptation_limitation: str = ""
    nusselt_basis: str = "hydraulic_diameter"


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
    applicability_assessment: ApplicabilityAssessment | None = None
    applicability_status: str = ""

    @field_validator("applicability_assessment", mode="before")
    @classmethod
    def _strip_allows_evaluation(cls, v: Any) -> Any:
        """Strip allows_evaluation from dict input for JSON round-trip."""
        if isinstance(v, dict) and "allows_evaluation" in v:
            v = {k: val for k, val in v.items() if k != "allows_evaluation"}
        return v

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
            "mass_flow_kg_s",
            "density_kg_m3",
            "dynamic_viscosity_pa_s",
            "thermal_conductivity_w_m_k",
            "specific_heat_j_kg_k",
            "bulk_temperature_k",
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

    # --- Identity payload builder (EXCLUDES result_hash) ---

    def _build_identity_payload(self) -> dict[str, Any]:
        """Build canonical payload for result hash computation.

        This payload does NOT include result_hash to avoid self-reference.
        It includes ALL identity fields that should affect the hash.
        """
        return {
            "status": self.status.value,
            "geometry": _canonicalize_geometry(self.geometry),
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
            "applicability_assessment": _canonicalize_assessment(self.applicability_assessment),
            "applicability_status": self.applicability_status,
            "warnings": [_canonicalize_message(w) for w in self.warnings],
            "blockers": [_canonicalize_message(b) for b in self.blockers],
            "failure": (
                {
                    "code": self.failure.code.value,
                    "message": self.failure.message,
                    "context": dict(self.failure.context) if self.failure.context else {},
                }
                if self.failure
                else None
            ),
            "provenance_digest": self.provenance_digest,
            "execution_context": (
                self.execution_context.model_dump(mode="json")
                if hasattr(self.execution_context, "model_dump")
                else self.execution_context
            ),
        }

    def _compute_result_hash(self) -> str:
        """Compute result hash from identity payload (excludes result_hash)."""
        return sha256_digest(self._build_identity_payload())

    # --- Field hash (covers ALL public fields including provenance_graph) ---

    def _compute_field_hash(self) -> str:
        """Compute SHA-256 of all public fields for tamper detection.

        Includes provenance_graph to detect tampering.
        """
        payload: dict[str, Any] = {
            "status": self.status.value,
            "geometry": _canonicalize_geometry(self.geometry),
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
            "applicability_assessment": _canonicalize_assessment(self.applicability_assessment),
            "applicability_status": self.applicability_status,
            "warnings": [_canonicalize_message(w) for w in self.warnings],
            "blockers": [_canonicalize_message(b) for b in self.blockers],
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
            "provenance_graph": _canonicalize_graph(self.provenance_graph),
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
        """Verify that result_hash is correct and integrity is intact.

        Rebuilds identity payload WITHOUT result_hash and compares.
        """
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
        recomputed = self._compute_result_hash()
        return recomputed == self.result_hash

    def verify_provenance(self) -> bool:
        """Comprehensive provenance graph verification.

        Checks:
        1. Graph digest matches provenance_digest
        2. Node IDs are unique
        3. Edge IDs are unique (by source-target-relation triple)
        4. Edge endpoints reference existing nodes
        5. No self-loops
        6. Graph is a DAG
        7. Each node's payload_hash can be recomputed and matches
        8. Each node's UUID5 can be recomputed and matches
        9. Root node type is correct (CASE_REVISION if design_case_revision_id, else EXTERNAL)
        10. Exactly one CALCULATION_RUN node
        11. CORRELATION node exists (if succeeded) or absent (if blocked with no selection)
        12. WARNING/BLOCKER nodes match result messages
        13. RESULT node matches result status and values
        14. No missing, extra, or duplicate nodes/edges
        """
        try:
            graph = self.provenance_graph

            # 1. Graph digest
            expected_digest = _provenance_graph_digest(graph)
            if expected_digest != self.provenance_digest:
                return False

            if not graph.nodes:
                return self.status == CorrelationStatus.BLOCKED

            # 2. Unique node IDs
            node_ids = [n.node_id for n in graph.nodes]
            if len(node_ids) != len(set(node_ids)):
                return False

            node_set = set(node_ids)

            # 3. Unique edges (by source-target-relation)
            edge_keys = [(e.source_id, e.target_id, e.relation) for e in graph.edges]
            if len(edge_keys) != len(set(edge_keys)):
                return False

            # 4. Edge endpoints exist
            for edge in graph.edges:
                if edge.source_id not in node_set or edge.target_id not in node_set:
                    return False

            # 5. No self-loops
            for edge in graph.edges:
                if edge.source_id == edge.target_id:
                    return False

            # 6. DAG
            in_degree: dict[UUID, int] = {nid: 0 for nid in node_set}
            adjacency: dict[UUID, list[UUID]] = {nid: [] for nid in node_set}
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

            if visited != len(node_set):
                return False  # Cycle detected

            # 7 & 8: Per-node-type semantic verification
            for node in graph.nodes:
                if not node.payload_hash.startswith("sha256:"):
                    return False

                # Rebuild canonical payload based on node type
                if node.node_type == ProvenanceNodeType.EXTERNAL:
                    payload = _build_external_root_payload(self.execution_context)
                elif node.node_type == ProvenanceNodeType.CASE_REVISION:
                    payload = _build_case_revision_root_payload(self.execution_context)
                elif node.node_type == ProvenanceNodeType.CALCULATION_RUN:
                    selected = self.selected_correlation
                    payload = _build_calculation_run_payload(
                        correlation_id=selected.correlation_id if selected else "",
                        version=selected.version if selected else "",
                        re=self.reynolds_number,
                        pr=self.prandtl_number,
                        nu=self.nusselt_number,
                        h=self.heat_transfer_coefficient,
                        status=self.status.value,
                        ctx=self.execution_context,
                    )
                elif node.node_type == ProvenanceNodeType.CORRELATION:
                    selected = self.selected_correlation
                    if selected is None:
                        return False
                    payload = _build_correlation_payload(
                        correlation_id=selected.correlation_id,
                        version=selected.version,
                        definition_hash=selected.definition_hash,
                        source_title=selected.source_title,
                        nusselt_basis=selected.nusselt_basis,
                    )
                elif node.node_type == ProvenanceNodeType.WARNING:
                    meta = dict(node.metadata)
                    code = meta.get("code", "")
                    message = meta.get("message", "")
                    source_module = "correlations.service"
                    payload = _build_warning_payload(code, message, source_module)
                elif node.node_type == ProvenanceNodeType.BLOCKER:
                    meta = dict(node.metadata)
                    code = meta.get("code", "")
                    message = meta.get("message", "")
                    source_module = "correlations.service"
                    payload = _build_blocker_payload(code, message, source_module)
                elif node.node_type == ProvenanceNodeType.RESULT:
                    assessment_hash = ""
                    if self.applicability_assessment is not None:
                        assessment_hash = self.applicability_assessment.assessment_hash
                    payload = _build_result_payload_for_provenance(
                        status=self.status.value,
                        nu=self.nusselt_number,
                        h=self.heat_transfer_coefficient,
                        correlation_id=(
                            self.selected_correlation.correlation_id
                            if self.selected_correlation
                            else ""
                        ),
                        assessment_hash=assessment_hash,
                    )
                else:
                    # Unknown node type — skip payload verification
                    continue

                # Verify payload_hash matches
                expected_hash = sha256_digest(payload)
                if expected_hash != node.payload_hash:
                    return False

                # Verify UUID5 matches
                expected_id = _deterministic_uuid5(payload)
                if expected_id != node.node_id:
                    return False

            # 9. Root node type
            ctx = self.execution_context
            node_types = {n.node_type for n in graph.nodes}
            has_external = ProvenanceNodeType.EXTERNAL in node_types
            has_case_rev = ProvenanceNodeType.CASE_REVISION in node_types
            if not (has_external or has_case_rev):
                return False
            if ctx.design_case_revision_id is not None and not has_case_rev:
                return False
            if ctx.design_case_revision_id is None and not has_external:
                return False

            # 10. Exactly one CALCULATION_RUN
            calc_nodes = [
                n for n in graph.nodes if n.node_type == ProvenanceNodeType.CALCULATION_RUN
            ]
            if len(calc_nodes) != 1:
                return False

            # Verify CALCULATION_RUN context
            calc_meta = dict(calc_nodes[0].metadata)
            expected_run_id = (
                str(ctx.calculation_run_id) if ctx.calculation_run_id is not None else None
            )
            if calc_meta.get("external_calculation_run_id") != expected_run_id:
                return False

            # 11. CORRELATION node consistency
            corr_nodes = [n for n in graph.nodes if n.node_type == ProvenanceNodeType.CORRELATION]
            if self.status == CorrelationStatus.SUCCEEDED:
                if len(corr_nodes) != 1:
                    return False
                corr_meta = dict(corr_nodes[0].metadata)
                if self.selected_correlation is None:
                    return False
                if corr_meta.get("correlation_id") != self.selected_correlation.correlation_id:
                    return False
                if corr_meta.get("version") != self.selected_correlation.version:
                    return False
            else:
                # BLOCKED: no correlation should be selected, no CORRELATION node
                if self.selected_correlation is not None:
                    return False
                if len(corr_nodes) != 0:
                    return False

            # 12. WARNING/BLOCKER nodes match result messages
            warn_nodes = [n for n in graph.nodes if n.node_type == ProvenanceNodeType.WARNING]
            blocker_nodes = [n for n in graph.nodes if n.node_type == ProvenanceNodeType.BLOCKER]
            if len(warn_nodes) != len(self.warnings):
                return False
            if len(blocker_nodes) != len(self.blockers):
                return False
            # Verify message content matches
            for wn in warn_nodes:
                wn_meta = dict(wn.metadata)
                found = any(
                    w.code.value == wn_meta.get("code") and w.message == wn_meta.get("message")
                    for w in self.warnings
                )
                if not found:
                    return False
            for bn in blocker_nodes:
                bn_meta = dict(bn.metadata)
                found = any(
                    b.code.value == bn_meta.get("code") and b.message == bn_meta.get("message")
                    for b in self.blockers
                )
                if not found:
                    return False

            # 13. RESULT node consistency
            result_nodes = [n for n in graph.nodes if n.node_type == ProvenanceNodeType.RESULT]
            if len(result_nodes) != 1:
                return False
            result_meta = dict(result_nodes[0].metadata)
            return result_meta.get("status") == self.status.value
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Canonicalization helpers
# ---------------------------------------------------------------------------


def _canonicalize_geometry(g: Any) -> Any:
    """Canonicalize geometry for hashing."""
    if isinstance(g, dict):
        return g
    if hasattr(g, "model_dump"):
        return g.model_dump(mode="json")
    return g


def _canonicalize_message(m: EngineeringMessage) -> dict[str, Any]:
    """Canonicalize an EngineeringMessage for hashing."""
    return {
        "code": m.code.value,
        "severity": m.severity.value,
        "message": m.message,
        "source_module": m.source_module,
        "context": [(k, v) for k, v in m.context],
        "allows_continuation": m.allows_continuation,
    }


def _canonicalize_assessment(assessment: ApplicabilityAssessment | None) -> dict[str, Any] | None:
    """Canonicalize an ApplicabilityAssessment for hashing.

    Produces a hashable dict that captures all identity-relevant fields.
    Returns None if assessment is None.
    """
    if assessment is None:
        return None
    sorted_vrs = sorted(assessment.variable_results, key=lambda vr: vr.variable.value)
    return {
        "correlation_key": {
            "correlation_id": assessment.correlation_key.correlation_id,
            "version": assessment.correlation_key.version,
        },
        "status": assessment.status.value
        if hasattr(assessment.status, "value")
        else str(assessment.status),
        "variable_results": [
            {
                "variable": vr.variable.value
                if hasattr(vr.variable, "value")
                else str(vr.variable),
                "supplied_value": vr.supplied_value,
                "absolute_minimum": vr.absolute_minimum,
                "absolute_maximum": vr.absolute_maximum,
                "recommended_minimum": vr.recommended_minimum,
                "recommended_maximum": vr.recommended_maximum,
                "status": vr.status.value if hasattr(vr.status, "value") else str(vr.status),
            }
            for vr in sorted_vrs
        ],
        "warnings": [_canonicalize_message(w) for w in assessment.warnings],
        "blockers": [_canonicalize_message(b) for b in assessment.blockers],
        "assessment_hash": assessment.assessment_hash,
    }


def _canonicalize_graph(graph: ProvenanceGraph) -> dict[str, Any]:
    """Canonicalize a ProvenanceGraph for field hash computation."""
    sorted_nodes = sorted(
        [n.model_dump() for n in graph.nodes],
        key=lambda x: str(x.get("node_id", "")),
    )
    sorted_edges = sorted(
        [e.model_dump() for e in graph.edges],
        key=lambda x: (str(x.get("source_id", "")), str(x.get("target_id", ""))),
    )
    return {"nodes": sorted_nodes, "edges": sorted_edges}


# ---------------------------------------------------------------------------
# Per-node-type payload builders (for provenance verification)
# ---------------------------------------------------------------------------


def _build_external_root_payload(execution_context: ExecutionContextSnapshot) -> dict[str, Any]:
    """Rebuild the canonical payload for an EXTERNAL root node."""
    ctx = execution_context
    return {
        "root_type": "EXTERNAL",
        "request_id": str(ctx.request_id) if ctx.request_id is not None else None,
    }


def _build_case_revision_root_payload(
    execution_context: ExecutionContextSnapshot,
) -> dict[str, Any]:
    """Rebuild the canonical payload for a CASE_REVISION root node."""
    ctx = execution_context
    return {
        "root_type": "CASE_REVISION",
        "design_case_revision_id": str(ctx.design_case_revision_id),
        "request_id": str(ctx.request_id) if ctx.request_id is not None else None,
    }


def _build_calculation_run_payload(
    correlation_id: str,
    version: str,
    re: float,
    pr: float,
    nu: float,
    h: float,
    status: str,
    ctx: ExecutionContextSnapshot,
) -> dict[str, Any]:
    """Rebuild the canonical payload for a CALCULATION_RUN node."""
    return {
        "correlation_id": correlation_id,
        "correlation_version": version,
        "reynolds": re,
        "prandtl": pr,
        "nusselt": nu,
        "heat_transfer_coefficient": h,
        "status": status,
        "software_version": _SOFTWARE_VERSION,
    }


def _build_correlation_payload(
    correlation_id: str,
    version: str,
    definition_hash: str,
    source_title: str,
    nusselt_basis: str = "",
) -> dict[str, Any]:
    """Rebuild the canonical payload for a CORRELATION node."""
    return {
        "correlation_id": correlation_id,
        "version": version,
        "definition_hash": definition_hash,
        "source_title": source_title,
        "nusselt_basis": nusselt_basis,
    }


def _build_warning_payload(
    code: str,
    message: str,
    source_module: str,
) -> dict[str, Any]:
    """Rebuild the canonical payload for a WARNING node."""
    return {
        "code": code,
        "severity": "warning",
        "message": message,
        "source_module": source_module,
    }


def _build_blocker_payload(
    code: str,
    message: str,
    source_module: str,
) -> dict[str, Any]:
    """Rebuild the canonical payload for a BLOCKER node."""
    return {
        "code": code,
        "severity": "blocker",
        "message": message,
        "source_module": source_module,
    }


def _build_result_payload_for_provenance(
    status: str,
    nu: float,
    h: float,
    correlation_id: str,
    assessment_hash: str,
) -> dict[str, Any]:
    """Rebuild the canonical payload for a RESULT node."""
    return {
        "status": status,
        "nusselt": nu,
        "heat_transfer_coefficient": h,
        "correlation_id": correlation_id,
        "assessment_hash": assessment_hash,
    }


# ---------------------------------------------------------------------------
# Provenance construction helpers
# ---------------------------------------------------------------------------


def _build_provenance_graph(
    *,
    geometry: CircularTubeGeometry | ConcentricAnnulusGeometry,
    correlation_id: str,
    correlation_version: str,
    definition_hash: str = "",
    source_title: str = "",
    source_authors: str = "",
    source_year: int = 0,
    nusselt_basis: str = "",
    assessment_hash: str = "",
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

    # Root node: CASE_REVISION if design_case_revision_id provided, else EXTERNAL
    if ctx.design_case_revision_id is not None:
        root_payload: dict[str, Any] = {
            "root_type": "CASE_REVISION",
            "design_case_revision_id": str(ctx.design_case_revision_id),
            "request_id": str(ctx.request_id) if ctx.request_id is not None else None,
        }
        root_type = ProvenanceNodeType.CASE_REVISION
    else:
        root_payload = {
            "root_type": "EXTERNAL",
            "request_id": str(ctx.request_id) if ctx.request_id is not None else None,
        }
        root_type = ProvenanceNodeType.EXTERNAL

    root_id = _deterministic_uuid5(root_payload)
    nodes.append(
        ProvenanceNode(
            node_id=root_id,
            node_type=root_type,
            label="correlation_request",
            metadata=(("request_id", str(ctx.request_id) if ctx.request_id is not None else None),),
            payload_hash=sha256_digest(root_payload),
        )
    )

    # CALCULATION_RUN node
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

    # CORRELATION node (only when a correlation is selected)
    if correlation_id:
        corr_payload: dict[str, Any] = {
            "correlation_id": correlation_id,
            "version": correlation_version,
            "definition_hash": definition_hash,
            "source_title": source_title,
            "nusselt_basis": nusselt_basis,
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
                    ("definition_hash", definition_hash),
                    ("source_title", source_title),
                    ("nusselt_basis", nusselt_basis),
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
        "assessment_hash": assessment_hash,
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
