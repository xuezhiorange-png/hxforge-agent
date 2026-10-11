"""Strict candidate-bound TASK173 Rating request and result schemas."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.bell_delaware import canonical as task166_canonical
from hexagent.exchangers.shell_tube.bell_delaware.models import Task166Result
from hexagent.exchangers.shell_tube.segmented_thermal_state_topology.models import (
    Result as Task171Result,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import (
    canonical as task031_canonical,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.models import (
    ShellSideHydraulicGeometry,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration.models import (
    Task174SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side.valid_result import Task025ValidResult
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.identity import (
    compute_success_result_hash as task029_result_hash,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.identity import (
    derive_result_id as task029_result_id,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029SuccessResult,
)

TASK173_CANDIDATE_RATING_REQUEST_SCHEMA: Final = "task173.candidate-rating-request.v1"
TASK173_CANDIDATE_RATING_RESULT_SCHEMA: Final = "task173.candidate-rating-result.v1"
SIZING_PACKAGE_ID: Final = "V07-T173-SIZING-AUTHORITY-PACKAGE-R2"
SIZING_PACKAGE_HASH: Final = "750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9"
TASK171_CANDIDATE_HASH: Final = "bf014e7ca44eb5f9a3a2abec7c41f44b39a2590e7efaf31d77c70c892bcd1a9e"
TASK172_CANDIDATE_HASH: Final = "fc7afcc9c51ed5920e3258b2a5683f1274d45df6c7d7e624be29614f97691483"
TASK174_CANDIDATE_HASH: Final = "4d0f83b8ab1777ba6516dfc607c7accc814ef8a521d26c25c8cf0adc1b264023"
TASK173_CANDIDATE_HASH: Final = "a5536ba8e93dcf9a94f26a8c5274672494dd53b9391a9dad60553067967f49aa"
JMU_TRANSFER_HASH: Final = "6d716f541c44aeaa6911efe5919ed2f1474f4af93a4c06fcb01a672c56d234cc"
TASK174_TRANSFER_HASH: Final = "893a6c1644a940b27fbad85ef4d4fc402a7999971dc5e2ed3603fada0398b857"
TASK174_BELL_TRANSFER_HASH: Final = (
    "28c89b6c58fef6050f9a0f5d33b80ce686f875a4ba9350e254d43ff699dccc58"
)
TASK174_PRESSURE_TRANSFER_HASH: Final = (
    "7506d4217d27123cdec1a5d46813445a1a8b500ef24af39e10b7598ba163ce19"
)


class StrictModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class CandidateRatingRequest(StrictModel):
    schema_version: Literal["task173.candidate-rating-request.v1"] = (
        TASK173_CANDIDATE_RATING_REQUEST_SCHEMA
    )
    candidate_id: str = Field(min_length=1)
    candidate_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_dimensions: tuple[tuple[str, str], ...] = Field(min_length=1)
    dimension_authority_hashes: tuple[tuple[str, str], ...] = Field(min_length=1)
    candidate_space_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_package_id: Literal["V07-T173-SIZING-AUTHORITY-PACKAGE-R2"] = SIZING_PACKAGE_ID
    authority_package_hash: Literal[
        "750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9"
    ] = SIZING_PACKAGE_HASH
    task171_candidate_authority_hash: Literal[
        "bf014e7ca44eb5f9a3a2abec7c41f44b39a2590e7efaf31d77c70c892bcd1a9e"
    ] = TASK171_CANDIDATE_HASH
    task172_candidate_authority_hash: Literal[
        "fc7afcc9c51ed5920e3258b2a5683f1274d45df6c7d7e624be29614f97691483"
    ] = TASK172_CANDIDATE_HASH
    task174_candidate_authority_hash: Literal[
        "4d0f83b8ab1777ba6516dfc607c7accc814ef8a521d26c25c8cf0adc1b264023"
    ] = TASK174_CANDIDATE_HASH
    candidate_rating_authority_hash: Literal[
        "a5536ba8e93dcf9a94f26a8c5274672494dd53b9391a9dad60553067967f49aa"
    ] = TASK173_CANDIDATE_HASH
    jmu_transfer_authority_hash: Literal[
        "6d716f541c44aeaa6911efe5919ed2f1474f4af93a4c06fcb01a672c56d234cc"
    ] = JMU_TRANSFER_HASH
    task174_project_transfer_authority_hash: Literal[
        "893a6c1644a940b27fbad85ef4d4fc402a7999971dc5e2ed3603fada0398b857"
    ] = TASK174_TRANSFER_HASH
    task174_bell_event_transfer_authority_hash: Literal[
        "28c89b6c58fef6050f9a0f5d33b80ce686f875a4ba9350e254d43ff699dccc58"
    ] = TASK174_BELL_TRANSFER_HASH
    task174_pressure_transfer_authority_hash: Literal[
        "7506d4217d27123cdec1a5d46813445a1a8b500ef24af39e10b7598ba163ce19"
    ] = TASK174_PRESSURE_TRANSFER_HASH
    task020_configuration_id: str = Field(min_length=1)
    task020_configuration_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    task021_layout_id: str = Field(min_length=1)
    task021_layout_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    task022_geometry_id: str = Field(min_length=1)
    task022_geometry_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    task024_geometry_id: str = Field(min_length=1)
    task024_geometry_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    task025_result: Any
    task031_geometry: ShellSideHydraulicGeometry
    task166_result: Task166Result
    task029_result: Any
    task171_result: Task171Result
    task174_result: Task174SuccessResult
    request_metadata: tuple[tuple[str, str], ...] = ()

    @model_validator(mode="after")
    def exact_candidate_producer_chain(self) -> CandidateRatingRequest:
        if type(self.task025_result) is not Task025ValidResult:
            raise ValueError("candidate TASK025 result must be the exact native success type")
        if type(self.task029_result) is not Task029SuccessResult:
            raise ValueError("candidate TASK029 result must be the exact native success type")
        native = self.task171_result.native_identity
        if (
            self.task171_result.status != "VALIDATED"
            or native is None
            or self.task025_result.blockers
            or self.task025_result.warnings
            or self.task025_result.result_hash != native.area_result_hash
            or self.task025_result.result_id != native.area_result_id
            or native.configuration_id != self.task020_configuration_id
            or native.configuration_hash != self.task020_configuration_hash
            or native.layout_id != self.task021_layout_id
            or native.layout_hash != self.task021_layout_hash
            or native.bundle_id != self.task022_geometry_id
            or native.bundle_hash != self.task022_geometry_hash
            or native.baffle_id != self.task024_geometry_id
            or native.baffle_hash != self.task024_geometry_hash
        ):
            raise ValueError("candidate TASK171/TASK025/native geometry identity mismatch")
        bell = self.task166_result
        if (
            bell.result_hash != task166_canonical.result_hash(bell)
            or bell.result_id != task166_canonical.result_id(bell.result_hash)
            or bell.blockers
            or bell.warnings
            or bell.applicability is None
            or bell.applicability.status.value != "APPLICABLE"
            or bell.completeness is None
            or bell.completeness.status != "COMPLETE"
        ):
            raise ValueError("candidate TASK166 must be an applicable native result")
        if (
            self.task031_geometry.blockers
            or self.task031_geometry.geometry_hash
            != task031_canonical.sha256_hex(
                task031_canonical.success_geometry_canonical_projection(self.task031_geometry)
            )
        ):
            raise ValueError("candidate TASK031 geometry is blocked")
        if (
            self.task029_result.result_hash != task029_result_hash(self.task029_result)
            or self.task029_result.result_id != task029_result_id(self.task029_result.result_hash)
            or self.task029_result.task025_result_hash != self.task025_result.result_hash
            or self.task029_result.task025_hydraulic_authority_hash
            != self.task025_result.hydraulic_authority_hash
            or self.task029_result.completeness_ledger.completeness_status.value
            != "COMPLETE_WITHIN_EXPLICIT_MODELED_BOUNDARY"
        ):
            raise ValueError("candidate TASK029 is incomplete or stale")
        from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration.service import (
            recompute_task174_result_hash,
        )

        if (
            self.task174_result.status != "VALIDATED"
            or self.task174_result.result_hash != recompute_task174_result_hash(self.task174_result)
            or self.task174_result.task029_result_hash != self.task029_result.result_hash
            or self.task174_result.task166_result_hash != bell.result_hash
        ):
            raise ValueError("candidate TASK174 is not bound to its native TASK029/TASK166")
        if len(dict(self.selected_dimensions)) != len(self.selected_dimensions):
            raise ValueError("candidate selected dimension roles must be unique")
        if len(dict(self.dimension_authority_hashes)) != len(self.dimension_authority_hashes):
            raise ValueError("candidate dimension authority roles must be unique")
        if not self.request_metadata or len(dict(self.request_metadata)) != len(
            self.request_metadata
        ):
            raise ValueError("candidate rating request metadata must be explicit and unique")
        return self


class CandidateRatingSuccessResult(StrictModel):
    schema_version: Literal["task173.candidate-rating-result.v1"] = (
        TASK173_CANDIDATE_RATING_RESULT_SCHEMA
    )
    status: Literal["VALIDATED"]
    candidate_id: str
    candidate_hash: str
    authority_package_id: Literal["V07-T173-SIZING-AUTHORITY-PACKAGE-R2"]
    authority_package_hash: str
    task171_result_hash: str
    task171_topology_id: str
    task171_mesh_identity: str
    physical_ownership_hash: str
    task025_result_hash: str
    task166_result_hash: str
    task029_result_hash: str
    task174_result_hash: str
    accepted_mesh_result_hash: str
    accepted_subdivisions_per_interval: int
    headroom_subdivisions_per_interval: int
    total_duty_w: Decimal
    tube_outlet_temperature_k: Decimal
    shell_outlet_temperature_k: Decimal
    tube_outlet_pressure_pa: Decimal
    shell_outlet_pressure_pa: Decimal
    wall_inner_min_k: Decimal
    wall_inner_max_k: Decimal
    wall_outer_min_k: Decimal
    wall_outer_max_k: Decimal
    minimum_approach_temperature_k: Decimal
    energy_balance_residual_w: Decimal
    terminal_boundary_residual_k: Decimal
    terminal_boundary_residual_j_kg: Decimal
    mesh_levels: tuple[dict[str, object], ...]
    convergence_comparisons: tuple[dict[str, object], ...]
    request_hash: str
    provenance: tuple[tuple[str, str], ...]
    result_hash: str
    result_id: str


def candidate_rating_request_hash(request: CandidateRatingRequest) -> str:
    return canonical_sha256(
        {
            "schema_version": request.schema_version,
            "candidate_id": request.candidate_id,
            "candidate_hash": request.candidate_hash,
            "selected_dimensions": [list(item) for item in request.selected_dimensions],
            "dimension_authority_hashes": [
                list(item) for item in request.dimension_authority_hashes
            ],
            "candidate_space_hash": request.candidate_space_hash,
            "authority_package_id": request.authority_package_id,
            "authority_package_hash": request.authority_package_hash,
            "task171_candidate_authority_hash": request.task171_candidate_authority_hash,
            "task172_candidate_authority_hash": request.task172_candidate_authority_hash,
            "task174_candidate_authority_hash": request.task174_candidate_authority_hash,
            "candidate_rating_authority_hash": request.candidate_rating_authority_hash,
            "jmu_transfer_authority_hash": request.jmu_transfer_authority_hash,
            "task174_project_transfer_authority_hash": (
                request.task174_project_transfer_authority_hash
            ),
            "task174_bell_event_transfer_authority_hash": (
                request.task174_bell_event_transfer_authority_hash
            ),
            "task174_pressure_transfer_authority_hash": (
                request.task174_pressure_transfer_authority_hash
            ),
            "task020_configuration_id": request.task020_configuration_id,
            "task020_configuration_hash": request.task020_configuration_hash,
            "task021_layout_id": request.task021_layout_id,
            "task021_layout_hash": request.task021_layout_hash,
            "task022_geometry_id": request.task022_geometry_id,
            "task022_geometry_hash": request.task022_geometry_hash,
            "task024_geometry_id": request.task024_geometry_id,
            "task024_geometry_hash": request.task024_geometry_hash,
            "task025_result_id": request.task025_result.result_id,
            "task025_result_hash": request.task025_result.result_hash,
            "task031_geometry_id": request.task031_geometry.geometry_id,
            "task031_geometry_hash": request.task031_geometry.geometry_hash,
            "task166_result_id": request.task166_result.result_id,
            "task166_result_hash": request.task166_result.result_hash,
            "task029_result_id": request.task029_result.result_id,
            "task029_result_hash": request.task029_result.result_hash,
            "task171_result_hash": request.task171_result.result_hash,
            "task171_topology_id": request.task171_result.topology_id,
            "task171_mesh_identity": request.task171_result.mesh_identity,
            "physical_ownership_hash": request.task171_result.physical_ownership_hash,
            "task174_result_id": request.task174_result.result_id,
            "task174_result_hash": request.task174_result.result_hash,
            "service": {
                "fluid": "PURE_ORDINARY_WATER",
                "property_profile_id": "V07-T172-WATER-PROPERTY-PROFILE-R2",
                "tube_mass_flow_kg_s": "12.000000",
                "shell_mass_flow_kg_s": "20.000000",
                "clean_surface_only": True,
            },
            "request_metadata": [list(item) for item in request.request_metadata],
        }
    )


def candidate_rating_result_hash(result: CandidateRatingSuccessResult) -> str:
    return canonical_sha256(result.model_dump(mode="json", exclude={"result_hash", "result_id"}))


__all__ = [
    "CandidateRatingRequest",
    "CandidateRatingSuccessResult",
    "candidate_rating_request_hash",
    "candidate_rating_result_hash",
]
