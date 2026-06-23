"""RatingResult model for double-pipe exchanger rating.

The immutable, hash-verified result of a double-pipe rating calculation.
Follows the same structural patterns as HeatBalanceResult in
hexagent.core.heat_balance.
"""

from __future__ import annotations

import dataclasses
import math
from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, PrivateAttr, model_validator

from hexagent.core.canonical import sha256_digest
from hexagent.core.heat_balance import (
    ExecutionContextSnapshot,
    PropertyCallRecord,
    ProviderIdentitySnapshot,
)
from hexagent.domain.messages import EngineeringMessage, RunFailure
from hexagent.domain.provenance import (
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    ProvenanceNodeType,
)
from hexagent.exchangers.double_pipe.thermal import FlowArrangement

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

_SOFTWARE_VERSION: str = "0.1.0"

# Module-level UUID5 namespace for deterministic provenance node IDs.
_PROVENANCE_NAMESPACE: UUID = uuid5(
    UUID("00000000-0000-0000-0000-000000000000"),
    "hexagent:double_pipe_rating:provenance",
)

# ---------------------------------------------------------------------------
# Status enum
# ---------------------------------------------------------------------------


class RatingStatus(StrEnum):
    """Outcome status of a double-pipe rating calculation.

    - SUCCEEDED: solver converged AND energy balance accepted.
    - BLOCKED: a structural precondition failed (geometry, property, flow).
    - FAILED: the root-finding solver did not converge.
    """

    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Snapshot dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PropertyProvenanceSnapshot:
    """Deeply immutable snapshot of property-provider provenance metadata."""

    fluid_identifier: str = ""
    backend_name: str = ""
    backend_version: str = ""
    backend_git_revision: str = ""
    reference_state_policy: str = ""
    configuration_fingerprint: str = ""
    validation_level: str = ""
    cache_policy_version: str = ""


@dataclass(frozen=True)
class FluidStateSnapshot:
    """Immutable snapshot of a fluid thermodynamic state point."""

    temperature_k: float
    pressure_pa: float
    enthalpy_j_kg: float
    density_kg_m3: float | None = None
    cp_j_kg_k: float | None = None
    viscosity_pa_s: float | None = None
    conductivity_w_m_k: float | None = None
    phase: str = ""
    quality: float | None = None
    property_provenance: PropertyProvenanceSnapshot | None = None


@dataclass(frozen=True)
class SelectedCorrelationSnapshot:
    """Immutable snapshot of a selected heat-transfer correlation."""

    correlation_id: str = ""
    version: str = ""
    definition_hash: str = ""
    source_title: str = ""
    source_authors: str = ""
    source_year: int = 0
    source_reference: str = ""
    source_verification_status: str = "unverified"
    nusselt_basis: str = "hydraulic_diameter"
    is_adaptation: bool = False
    adaptation_limitation: str = ""


@dataclass(frozen=True)
class ApplicabilitySnapshot:
    """Immutable snapshot of a correlation applicability assessment."""

    status: str = ""
    assessment_hash: str = ""
    reynolds_min: float | None = None
    reynolds_max: float | None = None
    prandtl_min: float | None = None
    prandtl_max: float | None = None
    geometry_type: str = ""
    notes: str = ""
    raw_assessment: tuple[tuple[str, Any], ...] = ()


# ---------------------------------------------------------------------------
# Local helper models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RatingRequestIdentity:
    """Frozen, serializable snapshot of all original rating request fields.

    Stored inside RatingResult so that verify_hash() can rebuild the
    canonical payload without circular dependencies.
    """

    # Fluid identity
    hot_fluid_name: str
    hot_fluid_backend: str
    hot_fluid_components: tuple[tuple[str, float], ...]
    cold_fluid_name: str
    cold_fluid_backend: str
    cold_fluid_components: tuple[tuple[str, float], ...]
    # Stream inputs
    hot_mass_flow_kg_s: float
    cold_mass_flow_kg_s: float
    hot_inlet_pressure_pa: float
    cold_inlet_pressure_pa: float
    hot_inlet_temperature_k: float
    cold_inlet_temperature_k: float
    # Flow arrangement
    flow_arrangement: str  # FlowArrangement.value
    # Geometry (all 9 fields from DoublePipeGeometry)
    geometry: dict[str, object]
    # Solver controls
    solver_absolute_residual_w: float
    solver_relative_residual_fraction: float
    solver_bracket_temperature_tolerance_k: float
    solver_max_iterations: int
    # Boundary conditions
    tube_boundary_condition: str = "constant_wall_temperature"
    annulus_boundary_condition: str = "inner_wall_heated"
    minimum_terminal_delta_t: float = 0.5


class ResistanceBreakdownModel(BaseModel):
    """Pydantic frozen model for the thermal resistance breakdown."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    r_conv_inner: float
    r_foul_inner: float
    r_wall: float
    r_foul_outer: float
    r_conv_outer: float
    total_resistance: float
    ua_w_k: float


class SolverDetailsModel(BaseModel):
    """Pydantic frozen model for solver diagnostics."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    iterations: int
    residual_w: float
    function_evaluations: int
    termination_reason: str
    # Bracket tracking
    initial_bracket_low_w: float = 0.0
    initial_bracket_high_w: float = 0.0
    final_bracket_low_w: float = 0.0
    final_bracket_high_w: float = 0.0
    final_bracket_width_w: float = 0.0
    final_bracket_temperature_effect_k: float = 0.0
    residual_tolerance_w: float = 0.0


# ---------------------------------------------------------------------------
# RatingResult
# ---------------------------------------------------------------------------


class RatingResult(BaseModel):
    """Immutable result of a double-pipe rating calculation.

    Contains thermal performance, resistance breakdown, ε-NTU fields,
    solver diagnostics, property call trace, warnings, blockers,
    deterministic hash, and provenance graph.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # --- Status & arrangement ---
    status: RatingStatus
    flow_arrangement: FlowArrangement

    # --- Primary results ---
    heat_duty_w: float | None
    hot_outlet_temperature_k: float | None
    cold_outlet_temperature_k: float | None

    # --- Tube-side convection ---
    tube_reynolds: float | None = None
    tube_prandtl: float | None = None
    tube_nusselt: float | None = None
    tube_h: float | None = None
    tube_selected_correlation_id: str | None = None
    tube_selected_correlation_version: str | None = None
    tube_applicability_status: str | None = None

    # --- Annulus-side convection ---
    annulus_reynolds: float | None = None
    annulus_prandtl: float | None = None
    annulus_nusselt: float | None = None
    annulus_h: float | None = None
    annulus_selected_correlation_id: str | None = None
    annulus_selected_correlation_version: str | None = None
    annulus_applicability_status: str | None = None

    # --- Areas ---
    area_inner_m2: float
    area_outer_m2: float

    # --- Resistance breakdown ---
    resistance_breakdown: ResistanceBreakdownModel

    # --- Overall heat transfer coefficients ---
    U_inner_basis: float | None = None
    U_outer_basis: float | None = None
    UA_w_k: float | None = None

    # --- ε-NTU fields ---
    C_hot_w_k: float | None = None
    C_cold_w_k: float | None = None
    C_min_w_k: float | None = None
    C_max_w_k: float | None = None
    capacity_ratio: float | None = None
    NTU: float | None = None
    effectiveness: float | None = None

    # --- LMTD ---
    LMTD_k: float | None = None

    # --- Residuals ---
    energy_residual_w: float | None = None
    ua_lmtd_residual_w: float | None = None

    # --- Closure diagnostics ---
    Q_hot_w: float | None = None
    Q_cold_w: float | None = None
    relative_energy_residual: float | None = None
    energy_tolerance_w: float | None = None
    relative_ua_lmtd_residual: float | None = None
    ua_lmtd_tolerance_w: float | None = None

    # --- Solver ---
    iterations: int
    converged: bool
    solver_termination_reason: str
    solver_details: SolverDetailsModel

    # --- Messages ---
    warnings: tuple[EngineeringMessage, ...]
    blockers: tuple[EngineeringMessage, ...]
    failure: RunFailure | None = None

    # --- Property trace ---
    property_calls: tuple[PropertyCallRecord, ...]

    # --- Identity & provenance ---
    provider_identity: ProviderIdentitySnapshot
    request_identity: RatingRequestIdentity
    execution_context: ExecutionContextSnapshot = ExecutionContextSnapshot()
    result_hash: str
    provenance_graph: ProvenanceGraph
    provenance_digest: str = ""

    # --- Fluid state snapshots ---
    hot_inlet_state: FluidStateSnapshot | None = None
    cold_inlet_state: FluidStateSnapshot | None = None
    hot_outlet_state: FluidStateSnapshot | None = None
    cold_outlet_state: FluidStateSnapshot | None = None
    tube_side_inlet_state: FluidStateSnapshot | None = None
    tube_side_outlet_state: FluidStateSnapshot | None = None
    annulus_side_inlet_state: FluidStateSnapshot | None = None
    annulus_side_outlet_state: FluidStateSnapshot | None = None
    tube_bulk_state: FluidStateSnapshot | None = None
    annulus_bulk_state: FluidStateSnapshot | None = None

    # --- Correlation & applicability snapshots ---
    tube_selected_correlation: SelectedCorrelationSnapshot | None = None
    annulus_selected_correlation: SelectedCorrelationSnapshot | None = None
    tube_applicability: ApplicabilitySnapshot | None = None
    annulus_applicability: ApplicabilitySnapshot | None = None

    # --- Core provenance digest ---
    core_provenance_digest: str = ""

    # --- Private field hash for tamper detection ---
    _field_hash: str = PrivateAttr(default="")

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def _validate_no_nan_inf(self) -> RatingResult:
        """Reject NaN and Infinity in all float fields."""
        float_fields = [
            "heat_duty_w",
            "hot_outlet_temperature_k",
            "cold_outlet_temperature_k",
            "tube_reynolds",
            "tube_prandtl",
            "tube_nusselt",
            "tube_h",
            "annulus_reynolds",
            "annulus_prandtl",
            "annulus_nusselt",
            "annulus_h",
            "area_inner_m2",
            "area_outer_m2",
            "U_inner_basis",
            "U_outer_basis",
            "UA_w_k",
            "C_hot_w_k",
            "C_cold_w_k",
            "C_min_w_k",
            "C_max_w_k",
            "capacity_ratio",
            "NTU",
            "effectiveness",
            "LMTD_k",
            "energy_residual_w",
            "ua_lmtd_residual_w",
            # Closure diagnostics
            "Q_hot_w",
            "Q_cold_w",
            "relative_energy_residual",
            "energy_tolerance_w",
            "relative_ua_lmtd_residual",
            "ua_lmtd_tolerance_w",
        ]
        for name in float_fields:
            val = getattr(self, name)
            if val is not None and not math.isfinite(val):
                raise ValueError(f"{name} must be finite, got {val!r}")
        return self

    @model_validator(mode="after")
    def _validate_status_contract(self) -> RatingResult:
        """Ensure status is consistent with blockers/failure."""
        if self.status == RatingStatus.BLOCKED and not self.blockers:
            raise ValueError("BLOCKED result must have at least one blocker")
        if self.status == RatingStatus.FAILED:
            if self.failure is None:
                raise ValueError("FAILED result must have a failure record")
            if self.converged:
                raise ValueError("FAILED result must not claim solver convergence")
        if self.status == RatingStatus.SUCCEEDED:
            if self.blockers:
                raise ValueError("SUCCEEDED result must not have any blockers")
            if not self.converged:
                raise ValueError("SUCCEEDED result must claim solver convergence")
            if self.failure is not None:
                raise ValueError("SUCCEEDED result must not have a failure record")
        return self

    @model_validator(mode="after")
    def _validate_flow_arrangement_consistency(self) -> RatingResult:
        """Ensure top-level flow_arrangement matches request_identity."""
        if self.flow_arrangement.value != self.request_identity.flow_arrangement:
            raise ValueError(
                f"flow_arrangement mismatch: top-level={self.flow_arrangement.value!r} "
                f"!= request_identity.flow_arrangement={self.request_identity.flow_arrangement!r}"
            )
        return self

    @model_validator(mode="after")
    def _validate_result_hash(self) -> RatingResult:
        """Verify result_hash starts with sha256: and is 71 chars."""
        if not self.result_hash.startswith("sha256:"):
            raise ValueError(f"result_hash must start with 'sha256:', got {self.result_hash!r}")
        hex_part = self.result_hash[7:]
        if len(hex_part) != 64:
            raise ValueError(f"result_hash hex must be 64 chars, got {len(hex_part)}")
        try:
            int(hex_part, 16)
        except ValueError:
            raise ValueError(f"result_hash contains invalid hex: {self.result_hash!r}") from None
        return self

    # ------------------------------------------------------------------
    # Post-init
    # ------------------------------------------------------------------

    def model_post_init(self, __context: Any) -> None:
        """Compute field hash for tamper detection."""
        object.__setattr__(self, "_field_hash", self._compute_field_hash())

    def _compute_field_hash(self) -> str:
        """Compute SHA-256 of all public fields for tamper detection."""
        payload: dict[str, Any] = {
            "status": self.status.value,
            "flow_arrangement": self.flow_arrangement.value,
            "heat_duty_w": self.heat_duty_w,
            "hot_outlet_temperature_k": self.hot_outlet_temperature_k,
            "cold_outlet_temperature_k": self.cold_outlet_temperature_k,
            "tube_reynolds": self.tube_reynolds,
            "tube_prandtl": self.tube_prandtl,
            "tube_nusselt": self.tube_nusselt,
            "tube_h": self.tube_h,
            "tube_selected_correlation_id": self.tube_selected_correlation_id,
            "tube_selected_correlation_version": self.tube_selected_correlation_version,
            "tube_applicability_status": self.tube_applicability_status,
            "annulus_reynolds": self.annulus_reynolds,
            "annulus_prandtl": self.annulus_prandtl,
            "annulus_nusselt": self.annulus_nusselt,
            "annulus_h": self.annulus_h,
            "annulus_selected_correlation_id": self.annulus_selected_correlation_id,
            "annulus_selected_correlation_version": self.annulus_selected_correlation_version,
            "annulus_applicability_status": self.annulus_applicability_status,
            "area_inner_m2": self.area_inner_m2,
            "area_outer_m2": self.area_outer_m2,
            "resistance_breakdown": self.resistance_breakdown.model_dump(),
            "U_inner_basis": self.U_inner_basis,
            "U_outer_basis": self.U_outer_basis,
            "UA_w_k": self.UA_w_k,
            "C_hot_w_k": self.C_hot_w_k,
            "C_cold_w_k": self.C_cold_w_k,
            "C_min_w_k": self.C_min_w_k,
            "C_max_w_k": self.C_max_w_k,
            "capacity_ratio": self.capacity_ratio,
            "NTU": self.NTU,
            "effectiveness": self.effectiveness,
            "LMTD_k": self.LMTD_k,
            "energy_residual_w": self.energy_residual_w,
            "ua_lmtd_residual_w": self.ua_lmtd_residual_w,
            "iterations": self.iterations,
            "converged": self.converged,
            "solver_termination_reason": self.solver_termination_reason,
            "solver_details": {
                k: (None if isinstance(v, float) and math.isnan(v) else v)
                for k, v in self.solver_details.model_dump().items()
            },
            "warnings": [_message_to_dict(m) for m in self.warnings],
            "blockers": [_message_to_dict(m) for m in self.blockers],
            "property_calls": [_property_call_record_to_dict(pc) for pc in self.property_calls],
            "result_hash": self.result_hash,
            "request_identity": (
                dataclasses.asdict(self.request_identity)
                if dataclasses.is_dataclass(self.request_identity)
                else self.request_identity
            ),
            "provider_identity": (
                self.provider_identity.model_dump(mode="json")
                if hasattr(self.provider_identity, "model_dump")
                else dataclasses.asdict(self.provider_identity)
            ),
            "execution_context": (
                self.execution_context.model_dump(mode="json")
                if hasattr(self.execution_context, "model_dump")
                else self.execution_context
            ),
            "failure": (
                {
                    "code": self.failure.code.value,
                    "message": self.failure.message,
                    "context": dict(self.failure.context) if self.failure.context else {},
                }
                if self.failure is not None
                else None
            ),
            "provenance_graph_digest": _provenance_graph_digest(self.provenance_graph),
            # Fluid state snapshots
            "hot_inlet_state": (
                dataclasses.asdict(self.hot_inlet_state)
                if self.hot_inlet_state is not None
                else None
            ),
            "cold_inlet_state": (
                dataclasses.asdict(self.cold_inlet_state)
                if self.cold_inlet_state is not None
                else None
            ),
            "hot_outlet_state": (
                dataclasses.asdict(self.hot_outlet_state)
                if self.hot_outlet_state is not None
                else None
            ),
            "cold_outlet_state": (
                dataclasses.asdict(self.cold_outlet_state)
                if self.cold_outlet_state is not None
                else None
            ),
            "tube_side_inlet_state": (
                dataclasses.asdict(self.tube_side_inlet_state)
                if self.tube_side_inlet_state is not None
                else None
            ),
            "tube_side_outlet_state": (
                dataclasses.asdict(self.tube_side_outlet_state)
                if self.tube_side_outlet_state is not None
                else None
            ),
            "annulus_side_inlet_state": (
                dataclasses.asdict(self.annulus_side_inlet_state)
                if self.annulus_side_inlet_state is not None
                else None
            ),
            "annulus_side_outlet_state": (
                dataclasses.asdict(self.annulus_side_outlet_state)
                if self.annulus_side_outlet_state is not None
                else None
            ),
            "tube_bulk_state": (
                dataclasses.asdict(self.tube_bulk_state)
                if self.tube_bulk_state is not None
                else None
            ),
            "annulus_bulk_state": (
                dataclasses.asdict(self.annulus_bulk_state)
                if self.annulus_bulk_state is not None
                else None
            ),
            # Correlation snapshots
            "tube_selected_correlation": (
                dataclasses.asdict(self.tube_selected_correlation)
                if self.tube_selected_correlation is not None
                else None
            ),
            "annulus_selected_correlation": (
                dataclasses.asdict(self.annulus_selected_correlation)
                if self.annulus_selected_correlation is not None
                else None
            ),
            # Applicability snapshots
            "tube_applicability": (
                dataclasses.asdict(self.tube_applicability)
                if self.tube_applicability is not None
                else None
            ),
            "annulus_applicability": (
                dataclasses.asdict(self.annulus_applicability)
                if self.annulus_applicability is not None
                else None
            ),
            # Core provenance digest
            "core_provenance_digest": self.core_provenance_digest,
        }
        return sha256_digest(payload)

    def validate_integrity(self) -> tuple[bool, list[str]]:
        """Verify no fields have been tampered with after construction.

        Returns (is_valid, list_of_issues).
        """
        issues: list[str] = []
        if self._field_hash != self._compute_field_hash():
            issues.append("Field hash mismatch: fields may have been tampered with")
        if not self.verify_provenance():
            issues.append("Provenance graph verification failed")
        return (len(issues) == 0, issues)

    def verify_hash(self) -> bool:
        """Verify that result_hash is correct."""
        if not self.result_hash.startswith("sha256:"):
            return False
        hex_part = self.result_hash[7:]
        if len(hex_part) != 64:
            return False
        try:
            int(hex_part, 16)
        except ValueError:
            return False
        recomputed = self._recompute_result_hash()
        return recomputed == self.result_hash

    def verify_provenance(self) -> bool:
        """Comprehensive provenance graph identity verification.

        Verifies every node's canonical identity (UUID5, label,
        payload_hash, metadata) and all structural invariants.
        Returns False if any check fails; never raises.
        """
        try:
            graph = self.provenance_graph

            # Reject empty graphs
            if not graph.nodes:
                return False

            # Index nodes by type
            nodes_by_type: dict[ProvenanceNodeType, list[ProvenanceNode]] = {}
            for n in graph.nodes:
                nodes_by_type.setdefault(n.node_type, []).append(n)

            # 1. RESULT node identity
            result_nodes = nodes_by_type.get(ProvenanceNodeType.RESULT, [])
            if len(result_nodes) != 1:
                return False
            result_node = result_nodes[0]

            result_payload: dict[str, Any] = {"result_hash": self.result_hash}
            expected_result_id = _deterministic_uuid5(result_payload)
            if result_node.node_id != expected_result_id:
                return False
            if result_node.label != "double_pipe_rating_result":
                return False
            if result_node.metadata != (((("result_hash", self.result_hash)),)):
                return False
            if result_node.payload_hash != sha256_digest(result_payload):
                return False

            # 2. RESULT linkage
            result_in_edges = [e for e in graph.edges if e.target_id == result_node.node_id]
            # Expect: 1 produces + N property_call supports + M correlation supports
            expected_result_in = 1 + len(self.property_calls)
            if self.tube_selected_correlation is not None:
                expected_result_in += 1
            if self.annulus_selected_correlation is not None:
                expected_result_in += 1
            if len(result_in_edges) != expected_result_in:
                return False
            result_produces_edges = [e for e in result_in_edges if e.relation == "produces"]
            if len(result_produces_edges) != 1:
                return False
            result_edge = result_produces_edges[0]

            calc_nodes = nodes_by_type.get(ProvenanceNodeType.CALCULATION_RUN, [])
            if len(calc_nodes) != 1:
                return False
            calc_node = calc_nodes[0]

            if result_edge.source_id != calc_node.node_id:
                return False
            if result_edge.relation != "produces":
                return False
            if result_edge.metadata:
                return False
            # RESULT must have no outgoing edges
            result_out_edges = [e for e in graph.edges if e.source_id == result_node.node_id]
            if result_out_edges:
                return False

            # 3. EXTERNAL or CASE_REVISION root node
            root_nodes = nodes_by_type.get(ProvenanceNodeType.EXTERNAL, []) + nodes_by_type.get(
                ProvenanceNodeType.CASE_REVISION, []
            )
            if len(root_nodes) != 1:
                return False
            root_node = root_nodes[0]

            # Rebuild expected root from execution_context
            _rid = (
                str(self.execution_context.request_id)
                if self.execution_context.request_id is not None
                else None
            )
            if self.execution_context.design_case_revision_id is not None:
                if root_node.node_type != ProvenanceNodeType.CASE_REVISION:
                    return False
                _dcr = str(self.execution_context.design_case_revision_id)
                expected_payload = {
                    "design_case_revision_id": _dcr,
                    "request_id": _rid,
                }
                expected_metadata: tuple[tuple[str, Any], ...] = (
                    ("design_case_revision_id", _dcr),
                    ("request_id", _rid),
                )
                expected_label = "case_revision"
            else:
                if root_node.node_type != ProvenanceNodeType.EXTERNAL:
                    return False
                expected_payload = {
                    "root_type": "EXTERNAL",
                    "request_id": _rid,
                    "flow_arrangement": self.flow_arrangement.value,
                }
                expected_metadata = (
                    ("request_id", _rid),
                    ("flow_arrangement", self.flow_arrangement.value),
                )
                expected_label = "calculation_request"
            expected_root_id = _deterministic_uuid5(expected_payload)
            if root_node.node_id != expected_root_id:
                return False
            if root_node.label != expected_label:
                return False
            if root_node.payload_hash != sha256_digest(expected_payload):
                return False
            if root_node.metadata != expected_metadata:
                return False

            # 4. CALCULATION_RUN node identity
            if calc_node.node_type != ProvenanceNodeType.CALCULATION_RUN:
                return False
            if calc_node.label != "double_pipe_rating_run":
                return False

            # Rebuild expected payload
            expected_calc_payload = _build_calculation_run_payload(
                flow_arrangement=self.flow_arrangement,
                request_identity=self.request_identity,
                iterations=self.iterations,
                converged=self.converged,
            )
            expected_calc_id = _deterministic_uuid5(expected_calc_payload)
            if calc_node.node_id != expected_calc_id:
                return False
            if calc_node.payload_hash != sha256_digest(expected_calc_payload):
                return False

            calc_meta = dict(calc_node.metadata)
            expected_calc_keys: set[str] = {
                "flow_arrangement",
                "iterations",
                "converged",
                "software_version",
                "external_calculation_run_id",
            }
            if set(calc_meta.keys()) != expected_calc_keys:
                return False
            if calc_meta["flow_arrangement"] != self.flow_arrangement.value:
                return False
            if calc_meta["iterations"] != self.iterations:
                return False
            if calc_meta["converged"] != self.converged:
                return False
            if calc_meta["software_version"] != _SOFTWARE_VERSION:
                return False
            expected_ext_calc_id = (
                str(self.execution_context.calculation_run_id)
                if self.execution_context.calculation_run_id is not None
                else None
            )
            if calc_meta.get("external_calculation_run_id") != expected_ext_calc_id:
                return False

            # 5. PROPERTY_CALL nodes
            pc_nodes = nodes_by_type.get(ProvenanceNodeType.PROPERTY_CALL, [])
            if len(pc_nodes) != len(self.property_calls):
                return False

            pc_node_map: dict[UUID, ProvenanceNode] = {n.node_id: n for n in pc_nodes}
            for idx, pc in enumerate(self.property_calls):
                prop_payload = _property_call_record_to_dict(pc)
                prop_payload["occurrence_index"] = idx
                expected_pc_id = _deterministic_uuid5(prop_payload)
                pc_node = pc_node_map.pop(expected_pc_id, None)
                if pc_node is None:
                    return False
                expected_label = f"property_{pc.fluid}_{pc.query_type}"
                if pc_node.label != expected_label:
                    return False
                if pc_node.payload_hash != sha256_digest(prop_payload):
                    return False
                expected_meta = (
                    ("fluid", pc.fluid),
                    ("query_type", pc.query_type),
                    ("backend_name", pc.backend_name),
                    ("backend_version", pc.backend_version),
                    ("reference_state_policy", pc.reference_state_policy),
                    ("stage", pc.stage),
                    ("success", pc.success),
                    ("error_code", pc.error_code),
                    ("stream_role", pc.stream_role),
                    ("sequence_index", pc.sequence_index),
                    ("evaluation_index", pc.evaluation_index),
                    ("evaluation_role", pc.evaluation_role),
                    ("call_index_within_evaluation", pc.call_index_within_evaluation),
                    ("trial_q_w", pc.trial_q_w),
                )
                if pc_node.metadata != expected_meta:
                    return False
            if pc_node_map:
                return False

            # 5b. CORRELATION nodes
            corr_nodes = nodes_by_type.get(ProvenanceNodeType.CORRELATION, [])
            expected_corr_nodes = 0
            if self.tube_selected_correlation is not None:
                expected_corr_nodes += 1
            if self.annulus_selected_correlation is not None:
                expected_corr_nodes += 1
            if len(corr_nodes) != expected_corr_nodes:
                return False

            corr_node_map: dict[UUID, ProvenanceNode] = {n.node_id: n for n in corr_nodes}
            for side, corr_snap, appl_snap in (
                (
                    "tube",
                    self.tube_selected_correlation,
                    self.tube_applicability,
                ),
                (
                    "annulus",
                    self.annulus_selected_correlation,
                    self.annulus_applicability,
                ),
            ):
                if corr_snap is None:
                    continue
                corr_payload: dict[str, Any] = _build_correlation_payload(
                    side=side,
                    correlation_info=corr_snap,
                    applicability_info=appl_snap,
                )
                expected_corr_id = _deterministic_uuid5(corr_payload)
                corr_node = corr_node_map.pop(expected_corr_id, None)
                if corr_node is None:
                    return False
                expected_corr_label = f"correlation_{side}"
                if corr_node.label != expected_corr_label:
                    return False
                if corr_node.payload_hash != sha256_digest(corr_payload):
                    return False
                expected_corr_meta: tuple[tuple[str, Any], ...] = (
                    ("side", side),
                    ("correlation_id", corr_snap.correlation_id),
                    ("version", corr_snap.version),
                )
                if corr_node.metadata != expected_corr_meta:
                    return False
            if corr_node_map:
                return False

            # 6. WARNING nodes
            warn_nodes = nodes_by_type.get(ProvenanceNodeType.WARNING, [])
            if len(warn_nodes) != len(self.warnings):
                return False
            warn_node_map: dict[UUID, ProvenanceNode] = {n.node_id: n for n in warn_nodes}
            for idx, w in enumerate(self.warnings):
                warn_payload: dict[str, Any] = {
                    "code": w.code.value,
                    "severity": w.severity.value,
                    "message": w.message,
                    "source_module": w.source_module,
                    "context": dict(w.context) if w.context else {},
                    "occurrence_index": idx,
                }
                expected_warn_id = _deterministic_uuid5(warn_payload)
                warn_node = warn_node_map.pop(expected_warn_id, None)
                if warn_node is None:
                    return False
                expected_label = f"warning_{w.code.value}"
                if warn_node.label != expected_label:
                    return False
                if warn_node.payload_hash != sha256_digest(warn_payload):
                    return False
                expected_warn_meta = (
                    ("code", w.code.value),
                    ("severity", w.severity.value),
                    ("message", w.message),
                    ("source_module", w.source_module),
                )
                if warn_node.metadata != expected_warn_meta:
                    return False
            if warn_node_map:
                return False

            # 7. BLOCKER nodes
            blocker_nodes = nodes_by_type.get(ProvenanceNodeType.BLOCKER, [])
            if len(blocker_nodes) != len(self.blockers):
                return False
            blocker_node_map: dict[UUID, ProvenanceNode] = {n.node_id: n for n in blocker_nodes}
            for idx, b in enumerate(self.blockers):
                block_payload: dict[str, Any] = {
                    "code": b.code.value,
                    "severity": b.severity.value,
                    "message": b.message,
                    "source_module": b.source_module,
                    "context": dict(b.context) if b.context else {},
                    "occurrence_index": idx,
                }
                expected_block_id = _deterministic_uuid5(block_payload)
                blocker_node = blocker_node_map.pop(expected_block_id, None)
                if blocker_node is None:
                    return False
                expected_label = f"blocker_{b.code.value}"
                if blocker_node.label != expected_label:
                    return False
                if blocker_node.payload_hash != sha256_digest(block_payload):
                    return False
                expected_block_meta = (
                    ("code", b.code.value),
                    ("severity", b.severity.value),
                    ("message", b.message),
                    ("source_module", b.source_module),
                )
                if blocker_node.metadata != expected_block_meta:
                    return False
            if blocker_node_map:
                return False

            # 8. core_provenance_digest from core graph (without RESULT node)
            core_node_ids = {
                n.node_id for n in graph.nodes if n.node_type != ProvenanceNodeType.RESULT
            }
            core_nodes = [n for n in graph.nodes if n.node_type != ProvenanceNodeType.RESULT]
            core_edges = [e for e in graph.edges if e.target_id in core_node_ids]
            try:
                core_graph = ProvenanceGraph(
                    nodes=tuple(core_nodes),
                    edges=tuple(core_edges),
                )
                recomputed_digest = _provenance_graph_digest(core_graph)
            except Exception:
                return False
            if recomputed_digest != self.core_provenance_digest:
                return False

            # 9. Reject unsupported node types
            allowed_types = {
                ProvenanceNodeType.EXTERNAL,
                ProvenanceNodeType.CASE_REVISION,
                ProvenanceNodeType.CALCULATION_RUN,
                ProvenanceNodeType.PROPERTY_CALL,
                ProvenanceNodeType.CORRELATION,
                ProvenanceNodeType.WARNING,
                ProvenanceNodeType.BLOCKER,
                ProvenanceNodeType.RESULT,
            }
            for n in graph.nodes:
                if n.node_type not in allowed_types:
                    return False

            # 10. Verify complete edge topology
            expected_edge_counts: Counter[tuple[str, str, str]] = Counter()
            # root → CALCULATION_RUN (triggers)
            expected_edge_counts[(str(root_node.node_id), str(calc_node.node_id), "triggers")] += 1
            # CALCULATION_RUN → each PROPERTY_CALL (calls)
            for pc_n in pc_nodes:
                expected_edge_counts[(str(calc_node.node_id), str(pc_n.node_id), "calls")] += 1
            # CALCULATION_RUN → each CORRELATION (selects)
            for corr_n in corr_nodes:
                expected_edge_counts[(str(calc_node.node_id), str(corr_n.node_id), "selects")] += 1
            # CALCULATION_RUN → each WARNING (emits)
            for w_n in warn_nodes:
                expected_edge_counts[(str(calc_node.node_id), str(w_n.node_id), "emits")] += 1
            # CALCULATION_RUN → each BLOCKER (emits)
            for b_n in blocker_nodes:
                expected_edge_counts[(str(calc_node.node_id), str(b_n.node_id), "emits")] += 1
            # CALCULATION_RUN → RESULT (produces)
            expected_edge_counts[
                (str(calc_node.node_id), str(result_node.node_id), "produces")
            ] += 1
            # PROPERTY_CALL → RESULT (supports)
            for pc_n in pc_nodes:
                expected_edge_counts[(str(pc_n.node_id), str(result_node.node_id), "supports")] += 1
            # CORRELATION → RESULT (supports)
            for corr_n in corr_nodes:
                corr_src = str(corr_n.node_id)
                corr_tgt = str(result_node.node_id)
                expected_edge_counts[(corr_src, corr_tgt, "supports")] += 1

            actual_edge_counts: Counter[tuple[str, str, str]] = Counter()
            for e in graph.edges:
                if e.metadata:
                    return False
                actual_edge_counts[(str(e.source_id), str(e.target_id), e.relation)] += 1

            if actual_edge_counts != expected_edge_counts:
                return False

            # 11. All payload hashes are valid SHA-256
            for node in graph.nodes:
                if not node.payload_hash.startswith("sha256:"):
                    return False
                hex_part = node.payload_hash[7:]
                if len(hex_part) != 64:
                    return False
                try:
                    int(hex_part, 16)
                except ValueError:
                    return False

            return True

        except Exception:
            return False

    def _recompute_result_hash(self) -> str:
        """Recompute result_hash from the stored field values.

        Builds the canonical payload identical to _build_identity_payload
        but using the result object's own stored fields.  Does NOT include
        result_hash itself in the payload (no circular dependency).
        """
        payload = _build_identity_payload(
            request_identity=self.request_identity,
            provider_identity=self.provider_identity,
            flow_arrangement=self.flow_arrangement,
            heat_duty_w=self.heat_duty_w,
            hot_outlet_temperature_k=self.hot_outlet_temperature_k,
            cold_outlet_temperature_k=self.cold_outlet_temperature_k,
            tube_reynolds=self.tube_reynolds,
            tube_prandtl=self.tube_prandtl,
            tube_nusselt=self.tube_nusselt,
            tube_h=self.tube_h,
            tube_selected_correlation_id=self.tube_selected_correlation_id,
            tube_selected_correlation_version=self.tube_selected_correlation_version,
            tube_applicability_status=self.tube_applicability_status,
            annulus_reynolds=self.annulus_reynolds,
            annulus_prandtl=self.annulus_prandtl,
            annulus_nusselt=self.annulus_nusselt,
            annulus_h=self.annulus_h,
            annulus_selected_correlation_id=self.annulus_selected_correlation_id,
            annulus_selected_correlation_version=self.annulus_selected_correlation_version,
            annulus_applicability_status=self.annulus_applicability_status,
            area_inner_m2=self.area_inner_m2,
            area_outer_m2=self.area_outer_m2,
            resistance_breakdown=self.resistance_breakdown,
            U_inner_basis=self.U_inner_basis,
            U_outer_basis=self.U_outer_basis,
            UA_w_k=self.UA_w_k,
            C_hot_w_k=self.C_hot_w_k,
            C_cold_w_k=self.C_cold_w_k,
            C_min_w_k=self.C_min_w_k,
            C_max_w_k=self.C_max_w_k,
            capacity_ratio=self.capacity_ratio,
            NTU=self.NTU,
            effectiveness=self.effectiveness,
            LMTD_k=self.LMTD_k,
            energy_residual_w=self.energy_residual_w,
            ua_lmtd_residual_w=self.ua_lmtd_residual_w,
            iterations=self.iterations,
            converged=self.converged,
            solver_termination_reason=self.solver_termination_reason,
            solver_details=self.solver_details,
            property_calls=self.property_calls,
            warnings=self.warnings,
            blockers=self.blockers,
            failure=self.failure,
            status=self.status,
            # New snapshot fields
            hot_inlet_state=self.hot_inlet_state,
            cold_inlet_state=self.cold_inlet_state,
            hot_outlet_state=self.hot_outlet_state,
            cold_outlet_state=self.cold_outlet_state,
            tube_side_inlet_state=self.tube_side_inlet_state,
            tube_side_outlet_state=self.tube_side_outlet_state,
            annulus_side_inlet_state=self.annulus_side_inlet_state,
            annulus_side_outlet_state=self.annulus_side_outlet_state,
            tube_bulk_state=self.tube_bulk_state,
            annulus_bulk_state=self.annulus_bulk_state,
            tube_selected_correlation_snap=self.tube_selected_correlation,
            annulus_selected_correlation_snap=self.annulus_selected_correlation,
            tube_applicability_snap=self.tube_applicability,
            annulus_applicability_snap=self.annulus_applicability,
            core_provenance_digest=self.core_provenance_digest,
            # Closure diagnostics
            Q_hot_w=self.Q_hot_w,
            Q_cold_w=self.Q_cold_w,
            relative_energy_residual=self.relative_energy_residual,
            energy_tolerance_w=self.energy_tolerance_w,
            relative_ua_lmtd_residual=self.relative_ua_lmtd_residual,
            ua_lmtd_tolerance_w=self.ua_lmtd_tolerance_w,
        )
        return sha256_digest(payload)


# ---------------------------------------------------------------------------
# Canonical payload builders (module-level, single source of truth)
# ---------------------------------------------------------------------------


def _build_identity_payload(
    *,
    request_identity: RatingRequestIdentity,
    provider_identity: ProviderIdentitySnapshot,
    flow_arrangement: FlowArrangement,
    heat_duty_w: float | None,
    hot_outlet_temperature_k: float | None,
    cold_outlet_temperature_k: float | None,
    tube_reynolds: float | None,
    tube_prandtl: float | None,
    tube_nusselt: float | None,
    tube_h: float | None,
    tube_selected_correlation_id: str | None,
    tube_selected_correlation_version: str | None,
    tube_applicability_status: str | None,
    annulus_reynolds: float | None,
    annulus_prandtl: float | None,
    annulus_nusselt: float | None,
    annulus_h: float | None,
    annulus_selected_correlation_id: str | None,
    annulus_selected_correlation_version: str | None,
    annulus_applicability_status: str | None,
    area_inner_m2: float,
    area_outer_m2: float,
    resistance_breakdown: ResistanceBreakdownModel,
    U_inner_basis: float | None,
    U_outer_basis: float | None,
    UA_w_k: float | None,
    C_hot_w_k: float | None,
    C_cold_w_k: float | None,
    C_min_w_k: float | None,
    C_max_w_k: float | None,
    capacity_ratio: float | None,
    NTU: float | None,
    effectiveness: float | None,
    LMTD_k: float | None,
    energy_residual_w: float | None,
    ua_lmtd_residual_w: float | None,
    iterations: int,
    converged: bool,
    solver_termination_reason: str,
    solver_details: SolverDetailsModel,
    property_calls: tuple[PropertyCallRecord, ...],
    warnings: tuple[EngineeringMessage, ...],
    blockers: tuple[EngineeringMessage, ...],
    failure: RunFailure | None,
    status: RatingStatus,
    # New snapshot fields
    hot_inlet_state: FluidStateSnapshot | None = None,
    cold_inlet_state: FluidStateSnapshot | None = None,
    hot_outlet_state: FluidStateSnapshot | None = None,
    cold_outlet_state: FluidStateSnapshot | None = None,
    tube_side_inlet_state: FluidStateSnapshot | None = None,
    tube_side_outlet_state: FluidStateSnapshot | None = None,
    annulus_side_inlet_state: FluidStateSnapshot | None = None,
    annulus_side_outlet_state: FluidStateSnapshot | None = None,
    tube_bulk_state: FluidStateSnapshot | None = None,
    annulus_bulk_state: FluidStateSnapshot | None = None,
    tube_selected_correlation_snap: SelectedCorrelationSnapshot | None = None,
    annulus_selected_correlation_snap: SelectedCorrelationSnapshot | None = None,
    tube_applicability_snap: ApplicabilitySnapshot | None = None,
    annulus_applicability_snap: ApplicabilitySnapshot | None = None,
    core_provenance_digest: str = "",
    # Closure diagnostics
    Q_hot_w: float | None = None,
    Q_cold_w: float | None = None,
    relative_energy_residual: float | None = None,
    energy_tolerance_w: float | None = None,
    relative_ua_lmtd_residual: float | None = None,
    ua_lmtd_tolerance_w: float | None = None,
) -> dict[str, Any]:
    """Build the canonical payload dict used for result hashing.

    This is the single source of truth for the result-hash payload.
    Both _compute_result_hash (construction) and
    RatingResult._recompute_result_hash (verification) call this.
    """
    failure_dict: dict[str, Any] | None = None
    if failure is not None:
        failure_dict = {
            "code": failure.code.value,
            "message": failure.message,
            "context": dict(failure.context) if failure.context else {},
        }

    return {
        # Request identity (original inputs)
        "hot_fluid_name": request_identity.hot_fluid_name,
        "hot_fluid_backend": request_identity.hot_fluid_backend,
        "hot_fluid_components": request_identity.hot_fluid_components,
        "cold_fluid_name": request_identity.cold_fluid_name,
        "cold_fluid_backend": request_identity.cold_fluid_backend,
        "cold_fluid_components": request_identity.cold_fluid_components,
        "hot_mass_flow_kg_s": request_identity.hot_mass_flow_kg_s,
        "cold_mass_flow_kg_s": request_identity.cold_mass_flow_kg_s,
        "hot_inlet_pressure_pa": request_identity.hot_inlet_pressure_pa,
        "cold_inlet_pressure_pa": request_identity.cold_inlet_pressure_pa,
        "hot_inlet_temperature_k": request_identity.hot_inlet_temperature_k,
        "cold_inlet_temperature_k": request_identity.cold_inlet_temperature_k,
        "flow_arrangement": request_identity.flow_arrangement,
        "geometry": request_identity.geometry,
        "solver_absolute_residual_w": request_identity.solver_absolute_residual_w,
        "solver_relative_residual_fraction": request_identity.solver_relative_residual_fraction,
        "solver_bracket_temperature_tolerance_k": (
            request_identity.solver_bracket_temperature_tolerance_k
        ),
        "solver_max_iterations": request_identity.solver_max_iterations,
        "tube_boundary_condition": request_identity.tube_boundary_condition,
        "annulus_boundary_condition": request_identity.annulus_boundary_condition,
        "minimum_terminal_delta_t": request_identity.minimum_terminal_delta_t,
        # Provider identity
        "provider_name": provider_identity.name,
        "provider_version": provider_identity.version,
        "provider_git_revision": provider_identity.git_revision,
        "reference_state_policy": provider_identity.reference_state_policy,
        "configuration_fingerprint": provider_identity.configuration_fingerprint,
        "cache_policy_version": provider_identity.cache_policy_version,
        # Flow arrangement (from request identity)
        "flow_arrangement_top_level": flow_arrangement.value,
        # Thermal results
        "heat_duty_w": heat_duty_w,
        "hot_outlet_temperature_k": hot_outlet_temperature_k,
        "cold_outlet_temperature_k": cold_outlet_temperature_k,
        # Tube-side convection
        "tube_reynolds": tube_reynolds,
        "tube_prandtl": tube_prandtl,
        "tube_nusselt": tube_nusselt,
        "tube_h": tube_h,
        "tube_selected_correlation_id": tube_selected_correlation_id,
        "tube_selected_correlation_version": tube_selected_correlation_version,
        "tube_applicability_status": tube_applicability_status,
        # Annulus-side convection
        "annulus_reynolds": annulus_reynolds,
        "annulus_prandtl": annulus_prandtl,
        "annulus_nusselt": annulus_nusselt,
        "annulus_h": annulus_h,
        "annulus_selected_correlation_id": annulus_selected_correlation_id,
        "annulus_selected_correlation_version": annulus_selected_correlation_version,
        "annulus_applicability_status": annulus_applicability_status,
        # Areas
        "area_inner_m2": area_inner_m2,
        "area_outer_m2": area_outer_m2,
        # Resistance breakdown
        "resistance_breakdown": resistance_breakdown.model_dump(),
        # Overall coefficients
        "U_inner_basis": U_inner_basis,
        "U_outer_basis": U_outer_basis,
        "UA_w_k": UA_w_k,
        # Capacity rates
        "C_hot_w_k": C_hot_w_k,
        "C_cold_w_k": C_cold_w_k,
        "C_min_w_k": C_min_w_k,
        "C_max_w_k": C_max_w_k,
        "capacity_ratio": capacity_ratio,
        # ε-NTU
        "NTU": NTU,
        "effectiveness": effectiveness,
        # LMTD
        "LMTD_k": LMTD_k,
        # Residuals
        "energy_residual_w": energy_residual_w,
        "ua_lmtd_residual_w": ua_lmtd_residual_w,
        # Solver (sanitize NaN → None for canonical hashing)
        "iterations": iterations,
        "converged": converged,
        "solver_termination_reason": solver_termination_reason,
        "solver_details": {
            k: (None if isinstance(v, float) and math.isnan(v) else v)
            for k, v in solver_details.model_dump().items()
        },
        # Property calls
        "property_calls": [_property_call_record_to_dict(pc) for pc in property_calls],
        # Messages
        "warnings": [_message_to_dict(m) for m in warnings],
        "blockers": [_message_to_dict(m) for m in blockers],
        # Status
        "status": status.value,
        # Failure
        "failure": failure_dict,
        # Software version
        "software_version": _SOFTWARE_VERSION,
        # Fluid state snapshots
        "hot_inlet_state": (
            dataclasses.asdict(hot_inlet_state) if hot_inlet_state is not None else None
        ),
        "cold_inlet_state": (
            dataclasses.asdict(cold_inlet_state) if cold_inlet_state is not None else None
        ),
        "hot_outlet_state": (
            dataclasses.asdict(hot_outlet_state) if hot_outlet_state is not None else None
        ),
        "cold_outlet_state": (
            dataclasses.asdict(cold_outlet_state) if cold_outlet_state is not None else None
        ),
        "tube_side_inlet_state": (
            dataclasses.asdict(tube_side_inlet_state) if tube_side_inlet_state is not None else None
        ),
        "tube_side_outlet_state": (
            dataclasses.asdict(tube_side_outlet_state)
            if tube_side_outlet_state is not None
            else None
        ),
        "annulus_side_inlet_state": (
            dataclasses.asdict(annulus_side_inlet_state)
            if annulus_side_inlet_state is not None
            else None
        ),
        "annulus_side_outlet_state": (
            dataclasses.asdict(annulus_side_outlet_state)
            if annulus_side_outlet_state is not None
            else None
        ),
        "tube_bulk_state": (
            dataclasses.asdict(tube_bulk_state) if tube_bulk_state is not None else None
        ),
        "annulus_bulk_state": (
            dataclasses.asdict(annulus_bulk_state) if annulus_bulk_state is not None else None
        ),
        # Correlation snapshots
        "tube_selected_correlation": (
            dataclasses.asdict(tube_selected_correlation_snap)
            if tube_selected_correlation_snap is not None
            else None
        ),
        "annulus_selected_correlation": (
            dataclasses.asdict(annulus_selected_correlation_snap)
            if annulus_selected_correlation_snap is not None
            else None
        ),
        # Applicability snapshots
        "tube_applicability": (
            dataclasses.asdict(tube_applicability_snap)
            if tube_applicability_snap is not None
            else None
        ),
        "annulus_applicability": (
            dataclasses.asdict(annulus_applicability_snap)
            if annulus_applicability_snap is not None
            else None
        ),
        # Closure diagnostics
        "Q_hot_w": Q_hot_w,
        "Q_cold_w": Q_cold_w,
        "relative_energy_residual": relative_energy_residual,
        "energy_tolerance_w": energy_tolerance_w,
        "relative_ua_lmtd_residual": relative_ua_lmtd_residual,
        "ua_lmtd_tolerance_w": ua_lmtd_tolerance_w,
        # Core provenance digest
        "core_provenance_digest": core_provenance_digest,
    }


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _property_call_record_to_dict(pc: PropertyCallRecord | dict[str, Any]) -> dict[str, Any]:
    """Convert PropertyCallRecord to a canonical dict for hashing."""
    if isinstance(pc, dict):
        return pc
    return {
        "fluid": pc.fluid,
        "query_type": pc.query_type,
        "inputs": dict(pc.inputs),
        "backend_name": pc.backend_name,
        "backend_version": pc.backend_version,
        "reference_state_policy": pc.reference_state_policy,
        "stage": pc.stage,
        "result_temperature_k": pc.result_temperature_k,
        "result_pressure_pa": pc.result_pressure_pa,
        "result_enthalpy_j_kg": pc.result_enthalpy_j_kg,
        "result_phase": pc.result_phase,
        "result_density_kg_m3": pc.result_density_kg_m3,
        "result_cp_j_kg_k": pc.result_cp_j_kg_k,
        "result_viscosity_pa_s": pc.result_viscosity_pa_s,
        "result_conductivity_w_m_k": pc.result_conductivity_w_m_k,
        "result_entropy_j_kg_k": pc.result_entropy_j_kg_k,
        "result_quality": pc.result_quality,
        "success": pc.success,
        "error_code": pc.error_code,
        "error_message": pc.error_message,
        "stream_role": pc.stream_role,
        "sequence_index": pc.sequence_index,
        "backend_git_revision": pc.backend_git_revision,
        "configuration_fingerprint": pc.configuration_fingerprint,
        "validation_level": pc.validation_level,
        "validation_dataset_id": pc.validation_dataset_id,
        "cache_policy_version": pc.cache_policy_version,
        # Evaluation identity fields
        "evaluation_index": pc.evaluation_index,
        "evaluation_role": pc.evaluation_role,
        "call_index_within_evaluation": pc.call_index_within_evaluation,
        "trial_q_w": pc.trial_q_w,
    }


def _message_to_dict(msg: EngineeringMessage | dict[str, Any]) -> dict[str, Any]:
    """Convert EngineeringMessage to a canonical dict for hashing."""
    if isinstance(msg, dict):
        return msg
    return {
        "schema_version": msg.schema_version,
        "code": msg.code.value,
        "severity": msg.severity.value,
        "message": msg.message,
        "source_module": msg.source_module,
        "affected_paths": msg.affected_paths,
        "context": dict(msg.context) if msg.context else {},
        "allows_continuation": msg.allows_continuation,
    }


def _snapshot_to_dict(
    snap: FluidStateSnapshot | SelectedCorrelationSnapshot | ApplicabilitySnapshot | None,
) -> dict[str, Any] | None:
    """Convert a frozen snapshot dataclass to a plain dict for hashing."""
    if snap is None:
        return None
    return dataclasses.asdict(snap)


# ---------------------------------------------------------------------------
# Provenance helpers
# ---------------------------------------------------------------------------


def _deterministic_uuid5(payload: dict[str, Any]) -> UUID:
    """Compute a deterministic UUID5 from a canonical payload dict."""
    canonical = sha256_digest(payload)
    return uuid5(_PROVENANCE_NAMESPACE, canonical)


def _provenance_graph_digest(graph: ProvenanceGraph | dict[str, Any]) -> str:
    """Compute a deterministic SHA-256 digest of a ProvenanceGraph.

    Serializes nodes and edges canonically.  Excludes the result_hash
    reference inside CALCULATION_RUN metadata to avoid circular
    dependency with the result hash that includes this digest.
    """
    if isinstance(graph, dict):
        graph = ProvenanceGraph.model_validate(graph)
    nodes_payload = []
    for node in graph.nodes:
        meta = dict(node.metadata)
        meta.pop("result_hash", None)
        nodes_payload.append(
            {
                "node_id": str(node.node_id),
                "node_type": node.node_type.value,
                "label": node.label,
                "metadata": meta,
                "payload_hash": node.payload_hash,
            }
        )
    edges_payload = [
        {
            "source_id": str(e.source_id),
            "target_id": str(e.target_id),
            "relation": e.relation,
        }
        for e in graph.edges
    ]
    return sha256_digest({"nodes": nodes_payload, "edges": edges_payload})


def _build_calculation_run_payload(
    *,
    flow_arrangement: FlowArrangement,
    request_identity: RatingRequestIdentity,
    iterations: int,
    converged: bool,
) -> dict[str, Any]:
    """Build the canonical CALCULATION_RUN payload dict."""
    return {
        "flow_arrangement": flow_arrangement.value,
        "hot_fluid_name": request_identity.hot_fluid_name,
        "hot_fluid_backend": request_identity.hot_fluid_backend,
        "cold_fluid_name": request_identity.cold_fluid_name,
        "cold_fluid_backend": request_identity.cold_fluid_backend,
        "hot_mass_flow_kg_s": request_identity.hot_mass_flow_kg_s,
        "cold_mass_flow_kg_s": request_identity.cold_mass_flow_kg_s,
        "hot_inlet_pressure_pa": request_identity.hot_inlet_pressure_pa,
        "cold_inlet_pressure_pa": request_identity.cold_inlet_pressure_pa,
        "hot_inlet_temperature_k": request_identity.hot_inlet_temperature_k,
        "cold_inlet_temperature_k": request_identity.cold_inlet_temperature_k,
        "solver_absolute_residual_w": request_identity.solver_absolute_residual_w,
        "solver_relative_residual_fraction": request_identity.solver_relative_residual_fraction,
        "solver_bracket_temperature_tolerance_k": (
            request_identity.solver_bracket_temperature_tolerance_k
        ),
        "solver_max_iterations": request_identity.solver_max_iterations,
        "iterations": iterations,
        "converged": converged,
        "software_version": _SOFTWARE_VERSION,
    }


def _build_correlation_payload(
    *,
    side: str,
    correlation_info: SelectedCorrelationSnapshot,
    applicability_info: ApplicabilitySnapshot | None,
) -> dict[str, Any]:
    """Build the canonical CORRELATION node payload dict."""
    appl_status = applicability_info.status if applicability_info is not None else ""
    assess_hash = applicability_info.assessment_hash if applicability_info is not None else ""
    return {
        "side": side,
        "correlation_id": correlation_info.correlation_id,
        "version": correlation_info.version,
        "definition_hash": correlation_info.definition_hash,
        "source_title": correlation_info.source_title,
        "source_authors": correlation_info.source_authors,
        "source_year": correlation_info.source_year,
        "source_reference": correlation_info.source_reference,
        "source_verification_status": correlation_info.source_verification_status,
        "nusselt_basis": correlation_info.nusselt_basis,
        "applicability_status": appl_status,
        "assessment_hash": assess_hash,
        "is_adaptation": correlation_info.is_adaptation,
        "adaptation_limitation": correlation_info.adaptation_limitation,
    }


# ---------------------------------------------------------------------------
# Provenance graph construction
# ---------------------------------------------------------------------------


def build_provenance_core(
    flow_arrangement: FlowArrangement,
    property_calls: list[PropertyCallRecord],
    iterations: int,
    converged: bool,
    warnings: list[EngineeringMessage],
    blockers: list[EngineeringMessage],
    *,
    execution_context: ExecutionContextSnapshot | None = None,
    request_identity: RatingRequestIdentity | None = None,
    tube_correlation_info: SelectedCorrelationSnapshot | None = None,
    annulus_correlation_info: SelectedCorrelationSnapshot | None = None,
    tube_applicability: ApplicabilitySnapshot | None = None,
    annulus_applicability: ApplicabilitySnapshot | None = None,
) -> tuple[ProvenanceGraph, list[ProvenanceNode], list[ProvenanceEdge]]:
    """Build the core provenance graph WITHOUT the RESULT node.

    Returns (core_graph, nodes, edges) where nodes/edges are mutable
    lists so the caller can append the RESULT node.
    """
    nodes: list[ProvenanceNode] = []
    edges: list[ProvenanceEdge] = []
    ctx = execution_context or ExecutionContextSnapshot()

    # --- Root node ---
    root_id: UUID
    if ctx.design_case_revision_id is not None:
        case_rev_payload: dict[str, Any] = {
            "design_case_revision_id": str(ctx.design_case_revision_id),
            "request_id": str(ctx.request_id) if ctx.request_id is not None else None,
        }
        root_id = _deterministic_uuid5(case_rev_payload)
        nodes.append(
            ProvenanceNode(
                node_id=root_id,
                node_type=ProvenanceNodeType.CASE_REVISION,
                label="case_revision",
                metadata=(
                    ("design_case_revision_id", str(ctx.design_case_revision_id)),
                    ("request_id", str(ctx.request_id) if ctx.request_id is not None else None),
                ),
                payload_hash=sha256_digest(case_rev_payload),
            )
        )
    else:
        ext_payload: dict[str, Any] = {
            "root_type": "EXTERNAL",
            "request_id": str(ctx.request_id) if ctx.request_id is not None else None,
            "flow_arrangement": flow_arrangement.value,
        }
        root_id = _deterministic_uuid5(ext_payload)
        nodes.append(
            ProvenanceNode(
                node_id=root_id,
                node_type=ProvenanceNodeType.EXTERNAL,
                label="calculation_request",
                metadata=(
                    ("request_id", str(ctx.request_id) if ctx.request_id is not None else None),
                    ("flow_arrangement", flow_arrangement.value),
                ),
                payload_hash=sha256_digest(ext_payload),
            )
        )

    # --- Calculation run node ---
    assert request_identity is not None, "request_identity is required"
    calc_payload = _build_calculation_run_payload(
        flow_arrangement=flow_arrangement,
        request_identity=request_identity,
        iterations=iterations,
        converged=converged,
    )
    calc_id = _deterministic_uuid5(calc_payload)
    nodes.append(
        ProvenanceNode(
            node_id=calc_id,
            node_type=ProvenanceNodeType.CALCULATION_RUN,
            label="double_pipe_rating_run",
            metadata=(
                ("flow_arrangement", flow_arrangement.value),
                ("iterations", iterations),
                ("converged", converged),
                ("software_version", _SOFTWARE_VERSION),
                (
                    "external_calculation_run_id",
                    str(ctx.calculation_run_id) if ctx.calculation_run_id is not None else None,
                ),
            ),
            payload_hash=sha256_digest(calc_payload),
        )
    )
    edges.append(
        ProvenanceEdge(
            source_id=root_id,
            target_id=calc_id,
            relation="triggers",
        )
    )

    # --- Property call nodes ---
    for _pc_idx, pc in enumerate(property_calls):
        prop_payload: dict[str, Any] = _property_call_record_to_dict(pc)
        prop_payload["occurrence_index"] = _pc_idx
        prop_id = _deterministic_uuid5(prop_payload)
        nodes.append(
            ProvenanceNode(
                node_id=prop_id,
                node_type=ProvenanceNodeType.PROPERTY_CALL,
                label=f"property_{pc.fluid}_{pc.query_type}",
                metadata=(
                    ("fluid", pc.fluid),
                    ("query_type", pc.query_type),
                    ("backend_name", pc.backend_name),
                    ("backend_version", pc.backend_version),
                    ("reference_state_policy", pc.reference_state_policy),
                    ("stage", pc.stage),
                    ("success", pc.success),
                    ("error_code", pc.error_code),
                    ("stream_role", pc.stream_role),
                    ("sequence_index", pc.sequence_index),
                    ("evaluation_index", pc.evaluation_index),
                    ("evaluation_role", pc.evaluation_role),
                    ("call_index_within_evaluation", pc.call_index_within_evaluation),
                    ("trial_q_w", pc.trial_q_w),
                ),
                payload_hash=sha256_digest(prop_payload),
            )
        )
        edges.append(
            ProvenanceEdge(
                source_id=calc_id,
                target_id=prop_id,
                relation="calls",
            )
        )

    # --- Correlation nodes ---
    for side, corr_info, appl_info in (
        ("tube", tube_correlation_info, tube_applicability),
        ("annulus", annulus_correlation_info, annulus_applicability),
    ):
        if corr_info is None:
            continue
        corr_payload: dict[str, Any] = _build_correlation_payload(
            side=side,
            correlation_info=corr_info,
            applicability_info=appl_info,
        )
        corr_id = _deterministic_uuid5(corr_payload)
        nodes.append(
            ProvenanceNode(
                node_id=corr_id,
                node_type=ProvenanceNodeType.CORRELATION,
                label=f"correlation_{side}",
                metadata=(
                    ("side", side),
                    ("correlation_id", corr_info.correlation_id),
                    ("version", corr_info.version),
                ),
                payload_hash=sha256_digest(corr_payload),
            )
        )
        edges.append(
            ProvenanceEdge(
                source_id=calc_id,
                target_id=corr_id,
                relation="selects",
            )
        )

    # --- Warning nodes ---
    for _w_idx, w in enumerate(warnings):
        warn_payload: dict[str, Any] = {
            "code": w.code.value,
            "severity": w.severity.value,
            "message": w.message,
            "source_module": w.source_module,
            "context": dict(w.context) if w.context else {},
            "occurrence_index": _w_idx,
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
                    ("source_module", w.source_module),
                ),
                payload_hash=sha256_digest(warn_payload),
            )
        )
        edges.append(
            ProvenanceEdge(
                source_id=calc_id,
                target_id=warn_id,
                relation="emits",
            )
        )

    # --- Blocker nodes ---
    for _b_idx, b in enumerate(blockers):
        block_payload: dict[str, Any] = {
            "code": b.code.value,
            "severity": b.severity.value,
            "message": b.message,
            "source_module": b.source_module,
            "context": dict(b.context) if b.context else {},
            "occurrence_index": _b_idx,
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
                    ("source_module", b.source_module),
                ),
                payload_hash=sha256_digest(block_payload),
            )
        )
        edges.append(
            ProvenanceEdge(
                source_id=calc_id,
                target_id=block_id,
                relation="emits",
            )
        )

    core_graph = ProvenanceGraph(nodes=tuple(nodes), edges=tuple(edges))
    return core_graph, nodes, edges


def build_provenance(
    flow_arrangement: FlowArrangement,
    property_calls: list[PropertyCallRecord],
    iterations: int,
    converged: bool,
    warnings: list[EngineeringMessage],
    blockers: list[EngineeringMessage],
    result_hash: str,
    *,
    execution_context: ExecutionContextSnapshot | None = None,
    request_identity: RatingRequestIdentity | None = None,
    tube_correlation_info: SelectedCorrelationSnapshot | None = None,
    annulus_correlation_info: SelectedCorrelationSnapshot | None = None,
    tube_applicability: ApplicabilitySnapshot | None = None,
    annulus_applicability: ApplicabilitySnapshot | None = None,
) -> ProvenanceGraph:
    """Build a deterministic provenance graph for the double-pipe rating.

    1. Build core provenance (without RESULT node)
    2. Compute provenance_digest from core
    3. Compute result_hash (includes provenance_digest)
    4. Add RESULT node with the result_hash
    """
    core_graph, nodes, edges = build_provenance_core(
        flow_arrangement=flow_arrangement,
        property_calls=property_calls,
        iterations=iterations,
        converged=converged,
        warnings=warnings,
        blockers=blockers,
        execution_context=execution_context,
        request_identity=request_identity,
        tube_correlation_info=tube_correlation_info,
        annulus_correlation_info=annulus_correlation_info,
        tube_applicability=tube_applicability,
        annulus_applicability=annulus_applicability,
    )

    # Find the CALCULATION_RUN node for the RESULT edge
    calc_id: UUID | None = None
    for node in nodes:
        if node.node_type == ProvenanceNodeType.CALCULATION_RUN:
            calc_id = node.node_id
            break
    assert calc_id is not None

    # Add RESULT node
    result_payload = {"result_hash": result_hash}
    result_id = _deterministic_uuid5(result_payload)
    nodes.append(
        ProvenanceNode(
            node_id=result_id,
            node_type=ProvenanceNodeType.RESULT,
            label="double_pipe_rating_result",
            metadata=(("result_hash", result_hash),),
            payload_hash=sha256_digest(result_payload),
        )
    )
    edges.append(
        ProvenanceEdge(
            source_id=calc_id,
            target_id=result_id,
            relation="produces",
        )
    )
    # Add PROPERTY_CALL → RESULT (supports) edges
    for node in nodes:
        if node.node_type == ProvenanceNodeType.PROPERTY_CALL:
            edges.append(
                ProvenanceEdge(
                    source_id=node.node_id,
                    target_id=result_id,
                    relation="supports",
                )
            )
    # Add CORRELATION → RESULT (supports) edges
    for node in nodes:
        if node.node_type == ProvenanceNodeType.CORRELATION:
            edges.append(
                ProvenanceEdge(
                    source_id=node.node_id,
                    target_id=result_id,
                    relation="supports",
                )
            )

    return ProvenanceGraph(
        nodes=tuple(nodes),
        edges=tuple(edges),
    )


def compute_result_hash(
    *,
    request_identity: RatingRequestIdentity,
    provider_identity: ProviderIdentitySnapshot,
    flow_arrangement: FlowArrangement,
    heat_duty_w: float | None,
    hot_outlet_temperature_k: float | None,
    cold_outlet_temperature_k: float | None,
    tube_reynolds: float | None,
    tube_prandtl: float | None,
    tube_nusselt: float | None,
    tube_h: float | None,
    tube_selected_correlation_id: str | None,
    tube_selected_correlation_version: str | None,
    tube_applicability_status: str | None,
    annulus_reynolds: float | None,
    annulus_prandtl: float | None,
    annulus_nusselt: float | None,
    annulus_h: float | None,
    annulus_selected_correlation_id: str | None,
    annulus_selected_correlation_version: str | None,
    annulus_applicability_status: str | None,
    area_inner_m2: float,
    area_outer_m2: float,
    resistance_breakdown: ResistanceBreakdownModel,
    U_inner_basis: float | None,
    U_outer_basis: float | None,
    UA_w_k: float | None,
    C_hot_w_k: float | None,
    C_cold_w_k: float | None,
    C_min_w_k: float | None,
    C_max_w_k: float | None,
    capacity_ratio: float | None,
    NTU: float | None,
    effectiveness: float | None,
    LMTD_k: float | None,
    energy_residual_w: float | None,
    ua_lmtd_residual_w: float | None,
    iterations: int,
    converged: bool,
    solver_termination_reason: str,
    solver_details: SolverDetailsModel,
    property_calls: tuple[PropertyCallRecord, ...],
    warnings: tuple[EngineeringMessage, ...],
    blockers: tuple[EngineeringMessage, ...],
    failure: RunFailure | None = None,
    status: RatingStatus = RatingStatus.SUCCEEDED,
    # New snapshot fields
    hot_inlet_state: FluidStateSnapshot | None = None,
    cold_inlet_state: FluidStateSnapshot | None = None,
    hot_outlet_state: FluidStateSnapshot | None = None,
    cold_outlet_state: FluidStateSnapshot | None = None,
    tube_side_inlet_state: FluidStateSnapshot | None = None,
    tube_side_outlet_state: FluidStateSnapshot | None = None,
    annulus_side_inlet_state: FluidStateSnapshot | None = None,
    annulus_side_outlet_state: FluidStateSnapshot | None = None,
    tube_bulk_state: FluidStateSnapshot | None = None,
    annulus_bulk_state: FluidStateSnapshot | None = None,
    tube_selected_correlation_snap: SelectedCorrelationSnapshot | None = None,
    annulus_selected_correlation_snap: SelectedCorrelationSnapshot | None = None,
    tube_applicability_snap: ApplicabilitySnapshot | None = None,
    annulus_applicability_snap: ApplicabilitySnapshot | None = None,
    core_provenance_digest: str = "",
    # Closure diagnostics
    Q_hot_w: float | None = None,
    Q_cold_w: float | None = None,
    relative_energy_residual: float | None = None,
    energy_tolerance_w: float | None = None,
    relative_ua_lmtd_residual: float | None = None,
    ua_lmtd_tolerance_w: float | None = None,
) -> str:
    """Compute deterministic SHA-256 hash of the result."""
    payload = _build_identity_payload(
        request_identity=request_identity,
        provider_identity=provider_identity,
        flow_arrangement=flow_arrangement,
        heat_duty_w=heat_duty_w,
        hot_outlet_temperature_k=hot_outlet_temperature_k,
        cold_outlet_temperature_k=cold_outlet_temperature_k,
        tube_reynolds=tube_reynolds,
        tube_prandtl=tube_prandtl,
        tube_nusselt=tube_nusselt,
        tube_h=tube_h,
        tube_selected_correlation_id=tube_selected_correlation_id,
        tube_selected_correlation_version=tube_selected_correlation_version,
        tube_applicability_status=tube_applicability_status,
        annulus_reynolds=annulus_reynolds,
        annulus_prandtl=annulus_prandtl,
        annulus_nusselt=annulus_nusselt,
        annulus_h=annulus_h,
        annulus_selected_correlation_id=annulus_selected_correlation_id,
        annulus_selected_correlation_version=annulus_selected_correlation_version,
        annulus_applicability_status=annulus_applicability_status,
        area_inner_m2=area_inner_m2,
        area_outer_m2=area_outer_m2,
        resistance_breakdown=resistance_breakdown,
        U_inner_basis=U_inner_basis,
        U_outer_basis=U_outer_basis,
        UA_w_k=UA_w_k,
        C_hot_w_k=C_hot_w_k,
        C_cold_w_k=C_cold_w_k,
        C_min_w_k=C_min_w_k,
        C_max_w_k=C_max_w_k,
        capacity_ratio=capacity_ratio,
        NTU=NTU,
        effectiveness=effectiveness,
        LMTD_k=LMTD_k,
        energy_residual_w=energy_residual_w,
        ua_lmtd_residual_w=ua_lmtd_residual_w,
        iterations=iterations,
        converged=converged,
        solver_termination_reason=solver_termination_reason,
        solver_details=solver_details,
        property_calls=property_calls,
        warnings=warnings,
        blockers=blockers,
        failure=failure,
        status=status,
        # New snapshot fields
        hot_inlet_state=hot_inlet_state,
        cold_inlet_state=cold_inlet_state,
        hot_outlet_state=hot_outlet_state,
        cold_outlet_state=cold_outlet_state,
        tube_side_inlet_state=tube_side_inlet_state,
        tube_side_outlet_state=tube_side_outlet_state,
        annulus_side_inlet_state=annulus_side_inlet_state,
        annulus_side_outlet_state=annulus_side_outlet_state,
        tube_bulk_state=tube_bulk_state,
        annulus_bulk_state=annulus_bulk_state,
        tube_selected_correlation_snap=tube_selected_correlation_snap,
        annulus_selected_correlation_snap=annulus_selected_correlation_snap,
        tube_applicability_snap=tube_applicability_snap,
        annulus_applicability_snap=annulus_applicability_snap,
        core_provenance_digest=core_provenance_digest,
        # Closure diagnostics
        Q_hot_w=Q_hot_w,
        Q_cold_w=Q_cold_w,
        relative_energy_residual=relative_energy_residual,
        energy_tolerance_w=energy_tolerance_w,
        relative_ua_lmtd_residual=relative_ua_lmtd_residual,
        ua_lmtd_tolerance_w=ua_lmtd_tolerance_w,
    )
    return sha256_digest(payload)
