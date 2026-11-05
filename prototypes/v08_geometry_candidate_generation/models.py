"""Result models for V08-02 geometry candidate generation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

V08_GEOMETRY_GENERATION_SCHEMA = "hxforge.v08-geometry-candidate-generation.v1"

V08GeometryGenerationStatus = Literal[
    "OK",
    "NO_STRUCTURAL_CANDIDATE",
    "BLOCKED_GEOMETRY_SOURCE",
]

ThermalRatingStatus = Literal["THERMAL_RATING_PENDING", "NOT_IN_SCOPE"]
FullPathDpStatus = Literal["FULL_PATH_DP_PENDING", "NOT_IN_SCOPE"]


class V08GeometryRejectionRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: str
    failure_stage: str
    reason_codes: tuple[str, ...]
    evidence: dict[str, str] = Field(default_factory=dict)


class V08GeometryCandidateRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rank: int
    candidate_id: str
    candidate_hash: str
    geometry_projection_hash: str
    shell_inside_diameter_m: str
    shell_geometry_id: str
    tube_outer_diameter_m: str
    tube_wall_thickness_m: str
    tube_pitch_m: str
    tube_length_m: str
    tube_pass_count: int
    physical_tube_count: int
    baffle_spacing_m: str
    baffle_count: int
    baffle_type: str
    thermal_rating_status: ThermalRatingStatus = "THERMAL_RATING_PENDING"
    full_path_dp_status: FullPathDpStatus = "FULL_PATH_DP_PENDING"
    geometry_validation: Literal["STRUCTURALLY_VALID"] = "STRUCTURALLY_VALID"
    source_authority_id: str
    source_content_hash: str


class V08GeometryGenerationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["hxforge.v08-geometry-candidate-generation.v1"] = (
        V08_GEOMETRY_GENERATION_SCHEMA
    )
    task_id: str = "V08_02_AUTOMATIC_GEOMETRY_GENERATION"
    status: V08GeometryGenerationStatus
    engineering_case_id: str
    normalized_input_hash: str
    geometry_source_authority: str
    geometry_source_content_hash: str
    user_geometry_required: bool = False
    downstream_readiness: str
    preserved_search_parameters: dict[str, str]
    envelope_filters_applied: tuple[str, ...] = ()
    candidate_space_hash: str | None = None
    candidates: tuple[V08GeometryCandidateRecord, ...] = ()
    rejections: tuple[V08GeometryRejectionRecord, ...] = ()
    distinct_valid_geometry_count: int = 0
    result_hash: str
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
