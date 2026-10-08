"""Strict public v0.7 Sizing request and identity-bearing result models."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Final, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import Task168Request

SIZING_REQUEST_SCHEMA: Final = "task173.sizing-request.v1"
SIZING_RESULT_SCHEMA: Final = "task173.sizing-result.v1"
SIZING_BLOCKED_SCHEMA: Final = "task173.sizing-blocked.v1"
SIZING_PACKAGE_ID: Final = "V07-T173-SIZING-AUTHORITY-PACKAGE-R2"
SIZING_PACKAGE_HASH: Final = "750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9"
SIZING_SCOPE_HASH: Final = "7072db59a1f80609b0d502de7dc61a8d047d9cbe302c40b717a39f443440570b"
RANKING_POLICY_ID: Final = "V07-T173-SIZING-RANKING-POLICY-R1"
RANKING_POLICY_HASH: Final = "0d9f6c410414f5a556e92dad15b86fabc4c28c07416513a71645160a0349fba6"

if TYPE_CHECKING:
    _TubeMassFlow: TypeAlias = Decimal
    _ShellMassFlow: TypeAlias = Decimal
    _MinimumTemperature: TypeAlias = Decimal
    _MaximumTemperature: TypeAlias = Decimal
    _MinimumPressure: TypeAlias = Decimal
    _MaximumPressure: TypeAlias = Decimal
else:
    _TubeMassFlow: TypeAlias = Literal[Decimal("12.000000")]
    _ShellMassFlow: TypeAlias = Literal[Decimal("20.000000")]
    _MinimumTemperature: TypeAlias = Literal[Decimal("298.15")]
    _MaximumTemperature: TypeAlias = Literal[Decimal("300.00")]
    _MinimumPressure: TypeAlias = Literal[Decimal("100000")]
    _MaximumPressure: TypeAlias = Literal[Decimal("101325")]


class StrictModel(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, arbitrary_types_allowed=True
    )


class SizingServiceAuthority(StrictModel):
    authority_id: Literal["V07-T173-SIZING-AUTHORITY-PACKAGE-R2"]
    authority_hash: Literal["750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9"]
    construction_family: Literal["FIXED_TUBESHEET"]
    shell_family: Literal["E_SHELL"]
    shell_pass_count: Literal[1]
    tube_topology: Literal["ONE_DECLARED_STRAIGHT_THROUGH_TUBE_PASS"]
    countercurrent: Literal[True]
    steady_state: Literal[True]
    single_phase: Literal[True]
    newtonian: Literal[True]
    fluid: Literal["PURE_ORDINARY_WATER"]
    property_profile_id: Literal["V07-T172-WATER-PROPERTY-PROFILE-R2"]
    clean_surface_only: Literal[True]
    tube_mass_flow_kg_s: _TubeMassFlow
    shell_mass_flow_kg_s: _ShellMassFlow
    minimum_temperature_k: _MinimumTemperature
    maximum_temperature_k: _MaximumTemperature
    minimum_pressure_pa: _MinimumPressure
    maximum_pressure_pa: _MaximumPressure
    production_mesh_profile_id: Literal["V07-T172-REAL-CASE-PRODUCTION-MESH-PROFILE-R1"]


class SizingRequirementAuthority(StrictModel):
    requirement_id: str = Field(min_length=1)
    authority_version: str = Field(min_length=1)
    source_class: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    approval_status: Literal["APPROVED"]
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    provenance_refs: tuple[str, ...] = Field(min_length=1)
    required_duty_w: Decimal
    max_tube_dp_pa: Decimal
    max_shell_dp_pa: Decimal
    allowed_construction_families: tuple[Literal["FIXED_TUBESHEET"], ...]
    required_screening_policy_id: Literal["V07-T173-SIZING-MANDATORY-SCREENING-R1"]
    discrete_candidate_authority_ids_and_hashes: tuple[tuple[str, str], ...] = Field(min_length=1)
    canonical_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("required_duty_w", "max_tube_dp_pa", "max_shell_dp_pa")
    @classmethod
    def positive_finite_decimal(cls, value: Decimal) -> Decimal:
        if type(value) is not Decimal or not value.is_finite() or value <= 0:
            raise ValueError("Sizing requirement numerics must be positive finite Decimal")
        return value

    @model_validator(mode="after")
    def unique_authorities_and_hash(self) -> SizingRequirementAuthority:
        if len(dict(self.discrete_candidate_authority_ids_and_hashes)) != len(
            self.discrete_candidate_authority_ids_and_hashes
        ):
            raise ValueError("candidate authority IDs must be unique")
        if any(not item for item in (*self.evidence_refs, *self.provenance_refs)):
            raise ValueError("requirement evidence and provenance references must be nonempty")
        projection = self.model_dump(mode="json", exclude={"canonical_hash"})
        if self.canonical_hash != canonical_sha256(projection):
            raise ValueError("Sizing requirement authority hash does not replay")
        return self


class Task173SizingRequest(StrictModel):
    schema_version: Literal["task173.sizing-request.v1"] = SIZING_REQUEST_SCHEMA
    authority_package_id: Literal["V07-T173-SIZING-AUTHORITY-PACKAGE-R2"]
    authority_package_hash: Literal[
        "750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9"
    ]
    sizing_scope_projection_hash: Literal[
        "7072db59a1f80609b0d502de7dc61a8d047d9cbe302c40b717a39f443440570b"
    ]
    service_authority: SizingServiceAuthority
    requirement_authority: SizingRequirementAuthority
    task168_candidate_request: Task168Request
    ranking_policy_id: Literal["V07-T173-SIZING-RANKING-POLICY-R1"]
    ranking_policy_hash: Literal["0d9f6c410414f5a556e92dad15b86fabc4c28c07416513a71645160a0349fba6"]
    request_metadata: tuple[tuple[str, str], ...] = Field(min_length=1)

    @model_validator(mode="after")
    def request_scope_is_explicit(self) -> Task173SizingRequest:
        if type(self.task168_candidate_request) is not Task168Request:
            raise ValueError("candidate enumeration requires an exact native TASK168 request")
        if not self.request_metadata or len(dict(self.request_metadata)) != len(
            self.request_metadata
        ):
            raise ValueError("Sizing request metadata must have unique keys")
        return self


class CandidateLedgerEntry(StrictModel):
    candidate_id: str
    candidate_hash: str
    selected_dimensions: tuple[tuple[str, str], ...]
    dimension_authority_hashes: tuple[tuple[str, str], ...]
    disposition: Literal["EVALUATED", "BLOCKED"]
    stage: str
    status: Literal["PASS", "WARN", "BLOCKED"]
    native_identities: tuple[tuple[str, str], ...] = ()
    candidate_rating_request_hash: str | None = None
    candidate_rating_result_hash: str | None = None
    candidate_rating_result_id: str | None = None
    accepted_mesh_identity: str | None = None
    accepted_subdivisions_per_interval: int | None = None
    headroom_subdivisions_per_interval: int | None = None
    rated_duty_w: Decimal | None = None
    tube_dp_pa: Decimal | None = None
    shell_dp_pa: Decimal | None = None
    duty_constraint: Literal["PASS", "BLOCKED"] | None = None
    tube_dp_constraint: Literal["PASS", "BLOCKED"] | None = None
    shell_dp_constraint: Literal["PASS", "BLOCKED"] | None = None
    ranking_score: Decimal | None = None
    rank: int | None = None
    warnings: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    provenance_hash: str


class RankingTraceEntry(StrictModel):
    candidate_id: str
    candidate_hash: str
    source_status: Literal["PASS", "WARN"]
    objective_metric: Literal["shell_dp_pa"]
    objective_value: Decimal
    normalized_objective: Decimal
    warn_penalty: Decimal
    composite_score: Decimal
    rank: int = Field(ge=1)
    reason_codes: tuple[str, ...]


class Task173SizingSuccessResult(StrictModel):
    schema_version: Literal["task173.sizing-result.v1"] = SIZING_RESULT_SCHEMA
    status: Literal["VALIDATED"]
    selection_status: Literal["RECOMMENDATION_AVAILABLE", "NO_RECOMMENDABLE_CANDIDATE"]
    request_hash: str
    candidate_space_hash: str
    candidate_records: tuple[CandidateLedgerEntry, ...]
    candidate_count: int
    pass_count: int
    warn_count: int
    blocked_count: int
    recommendable_count: int
    excluded_count: int
    ranked_candidate_ids: tuple[str, ...]
    ranking_trace: tuple[RankingTraceEntry, ...]
    recommended_candidate_id: str | None
    alternative_candidate_ids: tuple[str, ...]
    exclusion_reason_codes: tuple[tuple[str, tuple[str, ...]], ...]
    ranking_policy_id: str
    ranking_policy_hash: str
    provenance_nodes: tuple[tuple[str, str], ...]
    provenance_edges: tuple[tuple[str, str], ...]
    provenance_cycle_count: Literal[0]
    provenance_self_edge_count: Literal[0]
    orphan_recommendation: Literal[False]
    stale_reference_binding: Literal[False]
    result_hash: str
    result_id: str


class Task173SizingBlockedResult(StrictModel):
    schema_version: Literal["task173.sizing-blocked.v1"] = SIZING_BLOCKED_SCHEMA
    status: Literal["BLOCKED"]
    failure_stage: str
    failure_code: str
    request_hash: str | None
    blockers: tuple[str, ...]
    result_hash: str
    result_id: str


Task173SizingOutcome = Task173SizingSuccessResult | Task173SizingBlockedResult
