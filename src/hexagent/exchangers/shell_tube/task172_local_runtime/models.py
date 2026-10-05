"""Strict value models for the TASK172 local constitutive runtime."""

from __future__ import annotations

from decimal import Decimal, localcontext
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.bell_delaware import canonical as task166_canonical
from hexagent.exchangers.shell_tube.bell_delaware.models import (
    ApplicabilityStatus,
    BellGeometry,
    Task166Result,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.engineering import (
    compute_outer_to_inner_area_ratio,
)
from hexagent.exchangers.shell_tube.segmented_thermal_state_topology.models import (
    Result as Task171Result,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import (
    canonical as task031_canonical,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.models import (
    AGGREGATE_AUTHORITY_PROFILE_ID as TASK031_AUTHORITY_PROFILE_ID,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.models import (
    ShellSideHydraulicGeometry,
)
from hexagent.exchangers.shell_tube.tube_side.valid_result import Task025ValidResult

TASK172_REQUEST_SCHEMA: Final = "task172.local-constitutive-request.v1"
TASK172_RESULT_SCHEMA: Final = "task172.local-constitutive-result.v1"
TASK172_BLOCKED_SCHEMA: Final = "task172.local-constitutive-blocked.v1"
TASK172_IMPLEMENTATION_VERSION: Final = "task172.local-runtime-v1"
TASK172_CANDIDATE_REQUEST_SCHEMA: Final = "task172.candidate-local-constitutive-request.v1"
TASK173_SIZING_AUTHORITY_PACKAGE_ID: Final = "V07-T173-SIZING-AUTHORITY-PACKAGE-R2"
TASK173_SIZING_AUTHORITY_PACKAGE_HASH: Final = (
    "750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9"
)
TASK173_SIZING_TASK172_AUTHORITY_HASH: Final = (
    "fc7afcc9c51ed5920e3258b2a5683f1274d45df6c7d7e624be29614f97691483"
)
TASK173_SIZING_JMU_TRANSFER_HASH: Final = (
    "6d716f541c44aeaa6911efe5919ed2f1474f4af93a4c06fcb01a672c56d234cc"
)

CASE_ID: Final = "V07-T172-PROJECT-ENGINEERING-REFERENCE-CASE-R1"
CASE_REVISION_ID: Final = "V07-T172-PROJECT-ENGINEERING-REFERENCE-CASE-R2"
PROFILE_ID: Final = "V07-T172-WATER-PROPERTY-PROFILE-R2"
PROPERTY_PROFILE_CANONICAL_HASH: Final = (
    "8407227452b519483fbccbc686d3e8fcb2ca54866a8a8f01114addb5ca5a37de"
)
R94_MODEL_PROFILE_CANONICAL_HASH: Final = (
    "81ae446af5e0009ce85c5fcb89d80534f9e2eaf36942b9d3a35aa0ff10a86aec"
)
R98_OVERLAY_CANONICAL_HASH: Final = (
    "54c63a6c1178650e3164dd9f6cd7417ba044f2ec4b2f6b1b6a28accc19955a78"
)
SHELL_JMU_MODEL_AUTHORITY_CANONICAL_HASH: Final = (
    "ea6041287c407afe735148e12866f02026d23ba6e9c881ba22c076c032b5cac6"
)
STAGE1_AUTHORITY_EVIDENCE_CANONICAL_HASH: Final = (
    "60d1270c52ea226df28634003b4beaf6a8d006915d6454fe7e55dfaaca8771c1"
)
THERMAL_ROLE_AUTHORITY_ID: Final = "V07-T172-R119C-THERMAL-ROLE-SELECTION-R1"
TUBE_FLOW_PATH_ID: Final = (
    "urn:hxforge:r119a:flow-path:tube:"
    "88243c8545466b6536a6101ac505f149b0fd6c6f3adaf562a3ceb77090d17e76"
)
SHELL_FLOW_PATH_ID: Final = (
    "urn:hxforge:r119a:flow-path:shell:"
    "7032f11f5e02a4547ab0c463ed22235db7b0779066f39887b79f66ac3abab3ed"
)
TOPOLOGY_ID: Final = (
    "urn:hxforge:task171:98b4bb0ce1d209b6e19ae313330b1a8d5692b2398967586d4edc1e368e9345a7"
)
TASK171_RESULT_HASH: Final = "98b4bb0ce1d209b6e19ae313330b1a8d5692b2398967586d4edc1e368e9345a7"
MESH_IDENTITY: Final = "ec4a01bbfe81cd6b12ede63c6f4e4aa05372414868cee54a54fb7c98aaffd607"
PHYSICAL_OWNERSHIP_HASH: Final = "63ea9cb1d10037dde273fc40746d6cf98604a40e41d91705f640031e5b6ec7fe"
DEFINITION_PROJECTION_HASH: Final = (
    "342c1865b8292050c472b6be822a5f86ba00b0cab5e654554d7f16458603d55c"
)
PRODUCTION_MESH_PROFILE_ID: Final = "V07-T172-REAL-CASE-PRODUCTION-MESH-PROFILE-R1"
TASK171_STRUCTURAL_MESH_AUTHORITY_ID: Final = "V07-T172-R119A-TASK171-MESH-R1"

TASK025_RESULT_ID: Final = "6ff54552-d44e-50d2-bdf2-fe5b766c6ff9"
TASK025_RESULT_HASH: Final = "b74a037507e525e1ec647ac6a594e3723f0de07965e916b7a2eb1bb9de4dfc2a"
TOTAL_INSIDE_AREA_M2 = Decimal("75.1107679584")
TOTAL_OUTSIDE_AREA_M2 = Decimal("90.848262197302892909889504")
TOTAL_PARALLEL_FLOW_AREA_M2 = Decimal("0.0492914415")
TUBE_ID_M = Decimal("0.01575")
TUBE_OD_M = Decimal("0.01905")
WALL_CONDUCTIVITY_W_M_K = Decimal("14.0")
MATERIAL_SOURCE_SHA256: Final = "eda6e84f95c4cc2a46bb8c902cf066c4f51b9108d951d5490222cb365219ac48"
CLEAN_WALL_AUTHORITY_HASH: Final = (
    "e493999a1a6f8e83140e62ed71755af877a451bb9525f1e0791cddf174150b29"
)
CYLINDRICAL_MAPPING_HASH: Final = "49f902ce096f57381057a6d3631ef4b30355526dae8187112ae04fa703dda63c"
COOLPROP_VERSION: Final = "8.0.0"
COOLPROP_GIT_REVISION: Final = "ae81610e7d23efc57f9d051c8e70a4d66e87537f"

PHYSICAL_INTERVALS: tuple[tuple[Decimal, Decimal], ...] = (
    (Decimal("0.0"), Decimal("1.2")),
    (Decimal("1.2"), Decimal("2.4")),
    (Decimal("2.4"), Decimal("3.6")),
    (Decimal("3.6"), Decimal("4.8")),
    (Decimal("4.8"), Decimal("6.0")),
)

TASK171_BASE_SUPPORT_IDS: Final = (
    (
        "urn:hxforge:r119a:physical-segment:7575ac6b556d764db3f7b8a1f81515055a872f3a84f84820427c15953f1286a0",
        "urn:hxforge:r119a:numerical-cell:1c028f15876625cc0a442e3bcc01e7c815abcacfb953316f6571a4855e1ccb5d",
        "urn:hxforge:r119a:numerical-cell:10327796363b028262320a7c6e1ef04c0423a05360e60133babd753a869745ed",
        "urn:hxforge:r119a:wall-interface:df4f611255619a3f93d88878fbe1468817e3773bbcc3f39af1cb9ef6025f7979",
    ),
    (
        "urn:hxforge:r119a:physical-segment:40ff00fbf966c7ae76296b6c8ac8e7e092702ef87e882eba65453e0602a3dc81",
        "urn:hxforge:r119a:numerical-cell:a16f17102928ef9cd99296847cec571d6989d5e0c1f5155ff7a3544f183c7a32",
        "urn:hxforge:r119a:numerical-cell:379c03488cbea7ea91ba9fde18fe826ee6c0ff160754fdee18bc87ea4200d357",
        "urn:hxforge:r119a:wall-interface:80feff81b47b435a6f4c5b6f31a97fa891a01fa756f13a1647d91b94407ab0cc",
    ),
    (
        "urn:hxforge:r119a:physical-segment:2b645e6520590b7dcddbba43983bfbdb60609e9944e8250b38d26bd5d6e16245",
        "urn:hxforge:r119a:numerical-cell:9d847c4e0fa998122d708f3a0c2f55674cef585de40971904e37b8f65e361014",
        "urn:hxforge:r119a:numerical-cell:8e70fe7d96ca0fc82c1bd4c63bff8c4fde56c1879e660f5696e3b74e4fa4da65",
        "urn:hxforge:r119a:wall-interface:161e41118cff41324674f64e7986bf77062d8d775f716b62832640c8d42b9f40",
    ),
    (
        "urn:hxforge:r119a:physical-segment:45e63641026ad06bba7d2ab1c7220b6f24d9d54d894eec3837f0188d70cbaf20",
        "urn:hxforge:r119a:numerical-cell:f555fe2c66213773a6aae4ff12c84f5306c5c35f36c6203a48adefe7b79fdd75",
        "urn:hxforge:r119a:numerical-cell:38e1ccbce2b4442911b80c258daaa1f43ae72b2cca995219a6255a530eb58ca6",
        "urn:hxforge:r119a:wall-interface:824812ab42761cfceaf681309cf344377383911855da4d38ec7268d57cf0d733",
    ),
    (
        "urn:hxforge:r119a:physical-segment:fe343c367b607316b9d70af3c1f3a0bac5e057d8e4d6362a48b1fe89e6700760",
        "urn:hxforge:r119a:numerical-cell:d9d22ac64a704ddfdb7ff2b931728153ed6d55f9536abea29205dc6b3a84c818",
        "urn:hxforge:r119a:numerical-cell:cbeeeeb5c694cc2b2a12f0962be69e0bef8f97be1cabc79665fe5cfb1b535e03",
        "urn:hxforge:r119a:wall-interface:8109450c6472418558bf583f09e953f6abc011e12078038964f832694cb4140c",
    ),
)
_ALLOWED_SUBDIVISIONS: Final = (1, 2, 4, 8, 16, 32, 64)


def mesh_level_identity(subdivisions_per_interval: int) -> str:
    """Return the native base identity or reviewed deterministic refinement identity."""
    if type(subdivisions_per_interval) is not int or subdivisions_per_interval not in (
        _ALLOWED_SUBDIVISIONS
    ):
        raise ValueError("subdivision level is outside the reviewed production sequence")
    if subdivisions_per_interval == 1:
        return MESH_IDENTITY
    return canonical_sha256(
        {
            "schema_version": "task172.real-case-mesh-level-identity.v1",
            "production_mesh_profile_id": PRODUCTION_MESH_PROFILE_ID,
            "task171_base_mesh_identity": MESH_IDENTITY,
            "subdivisions_per_physical_interval_per_side": subdivisions_per_interval,
            "physical_intervals_m": [[str(start), str(end)] for start, end in PHYSICAL_INTERVALS],
            "refinement_operator": "MIDPOINT_BISECTION_WITHIN_EACH_PHYSICAL_INTERVAL",
        }
    )


def _refined_id(kind: str, mesh_id: str, segment_id: str, index: int) -> str:
    digest = canonical_sha256(
        {
            "schema_version": "task172.real-case-refined-support-id.v1",
            "kind": kind,
            "mesh_level_identity": mesh_id,
            "physical_segment_id": segment_id,
            "subdivision_index": index,
        }
    )
    return f"urn:hxforge:task172:real-case-{kind}:{digest}"


class StrictModel(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, arbitrary_types_allowed=True
    )


class TopologyBinding(StrictModel):
    topology_id: str
    task171_result_hash: str
    mesh_identity: str
    physical_ownership_hash: str
    definition_projection_hash: str
    production_mesh_profile_authority_id: Literal[
        "V07-T172-REAL-CASE-PRODUCTION-MESH-PROFILE-R1"
    ] = PRODUCTION_MESH_PROFILE_ID
    structural_mesh_authority_id: Literal["V07-T172-R119A-TASK171-MESH-R1"] = (
        TASK171_STRUCTURAL_MESH_AUTHORITY_ID
    )
    selected_variant: Literal["TUBE_HOT_SHELL_COLD"]
    thermal_role_selection_authority_id: str
    tube_role: Literal["HOT"]
    shell_role: Literal["COLD"]
    tube_flow_path_id: str
    shell_flow_path_id: str

    @model_validator(mode="after")
    def reviewed_binding(self) -> TopologyBinding:
        expected = {
            "topology_id": TOPOLOGY_ID,
            "task171_result_hash": TASK171_RESULT_HASH,
            "mesh_identity": MESH_IDENTITY,
            "physical_ownership_hash": PHYSICAL_OWNERSHIP_HASH,
            "definition_projection_hash": DEFINITION_PROJECTION_HASH,
            "thermal_role_selection_authority_id": THERMAL_ROLE_AUTHORITY_ID,
            "tube_flow_path_id": TUBE_FLOW_PATH_ID,
            "shell_flow_path_id": SHELL_FLOW_PATH_ID,
        }
        for field_name, expected_value in expected.items():
            if getattr(self, field_name) != expected_value:
                raise ValueError(f"{field_name} does not match the reviewed TASK171 binding")
        return self


class LocalSupport(StrictModel):
    physical_segment_id: str = Field(min_length=1)
    physical_segment_start_m: Decimal
    physical_segment_end_m: Decimal
    support_start_m: Decimal
    support_end_m: Decimal
    subdivisions_per_physical_interval_per_side: int = Field(ge=1, le=64)
    subdivision_index: int = Field(ge=0, le=63)
    mesh_level_identity: str = Field(min_length=1)
    tube_cell_id: str = Field(min_length=1)
    shell_cell_id: str = Field(min_length=1)
    wall_interface_id: str = Field(min_length=1)
    inside_area_m2: Decimal
    outside_area_m2: Decimal

    @field_validator(
        "physical_segment_start_m",
        "physical_segment_end_m",
        "support_start_m",
        "support_end_m",
        "inside_area_m2",
        "outside_area_m2",
    )
    @classmethod
    def finite_decimal(cls, value: Decimal) -> Decimal:
        if type(value) is not Decimal or not value.is_finite():
            raise ValueError("support geometry and areas must be finite Decimal values")
        return value

    @model_validator(mode="after")
    def exact_physical_support(self) -> LocalSupport:
        segment_index = next(
            (
                index
                for index, segment in enumerate(PHYSICAL_INTERVALS)
                if segment == (self.physical_segment_start_m, self.physical_segment_end_m)
            ),
            None,
        )
        if segment_index is None:
            raise ValueError("support must bind exactly one reviewed TASK024 physical interval")
        n = self.subdivisions_per_physical_interval_per_side
        if type(n) is not int or n not in _ALLOWED_SUBDIVISIONS:
            raise ValueError("subdivision level is outside the reviewed production sequence")
        if type(self.subdivision_index) is not int or not 0 <= self.subdivision_index < n:
            raise ValueError("subdivision index is outside this physical interval")
        segment_id, base_tube_id, base_shell_id, base_wall_id = TASK171_BASE_SUPPORT_IDS[
            segment_index
        ]
        if self.physical_segment_id != segment_id:
            raise ValueError(
                "physical segment identity differs from the accepted TASK171 Definition"
            )
        expected_mesh_id = mesh_level_identity(n)
        if self.mesh_level_identity != expected_mesh_id:
            raise ValueError(
                "mesh level identity does not replay from the reviewed refinement profile"
            )
        segment_length = self.physical_segment_end_m - self.physical_segment_start_m
        child_length = segment_length / Decimal(n)
        expected_start = self.physical_segment_start_m + child_length * self.subdivision_index
        expected_end = expected_start + child_length
        if (self.support_start_m, self.support_end_m) != (expected_start, expected_end):
            raise ValueError("numerical support is not an aligned midpoint refinement child")
        if n == 1:
            expected_tube_id, expected_shell_id, expected_wall_id = (
                base_tube_id,
                base_shell_id,
                base_wall_id,
            )
        else:
            expected_tube_id = _refined_id(
                "cell-tube", expected_mesh_id, segment_id, self.subdivision_index
            )
            expected_shell_id = _refined_id(
                "cell-shell", expected_mesh_id, segment_id, self.subdivision_index
            )
            expected_wall_id = _refined_id(
                "wall-interface", expected_mesh_id, segment_id, self.subdivision_index
            )
        if (
            self.tube_cell_id != expected_tube_id
            or self.shell_cell_id != expected_shell_id
            or self.wall_interface_id != expected_wall_id
        ):
            raise ValueError("cell/wall identities do not replay from the bound mesh support")
        span = self.support_end_m - self.support_start_m
        with localcontext() as context:
            context.prec = 80
            expected_inside = TOTAL_INSIDE_AREA_M2 * span / Decimal("6.0")
            expected_outside = TOTAL_OUTSIDE_AREA_M2 * span / Decimal("6.0")
        if self.inside_area_m2 != expected_inside or self.outside_area_m2 != expected_outside:
            raise ValueError("wall areas must preserve the reviewed physical-support ownership")
        return self


def build_local_support(
    physical_interval_index: int,
    subdivisions_per_physical_interval_per_side: int,
    subdivision_index: int,
) -> LocalSupport:
    """Build one identity-checked support under the reviewed real-case mesh profile."""
    if type(physical_interval_index) is not int or not 0 <= physical_interval_index < 5:
        raise ValueError("physical interval index must identify one of the five reviewed intervals")
    n = subdivisions_per_physical_interval_per_side
    if type(n) is not int or n not in _ALLOWED_SUBDIVISIONS:
        raise ValueError("subdivision level is outside the reviewed production sequence")
    if type(subdivision_index) is not int or not 0 <= subdivision_index < n:
        raise ValueError("subdivision index is outside this physical interval")
    start, end = PHYSICAL_INTERVALS[physical_interval_index]
    segment_id, base_tube_id, base_shell_id, base_wall_id = TASK171_BASE_SUPPORT_IDS[
        physical_interval_index
    ]
    mesh_id = mesh_level_identity(n)
    child_length = (end - start) / Decimal(n)
    support_start = start + child_length * subdivision_index
    support_end = support_start + child_length
    if n == 1:
        tube_id, shell_id, wall_id = base_tube_id, base_shell_id, base_wall_id
    else:
        tube_id = _refined_id("cell-tube", mesh_id, segment_id, subdivision_index)
        shell_id = _refined_id("cell-shell", mesh_id, segment_id, subdivision_index)
        wall_id = _refined_id("wall-interface", mesh_id, segment_id, subdivision_index)
    with localcontext() as context:
        context.prec = 80
        inside_area = TOTAL_INSIDE_AREA_M2 * (support_end - support_start) / Decimal("6.0")
        outside_area = TOTAL_OUTSIDE_AREA_M2 * (support_end - support_start) / Decimal("6.0")
    return LocalSupport(
        physical_segment_id=segment_id,
        physical_segment_start_m=start,
        physical_segment_end_m=end,
        support_start_m=support_start,
        support_end_m=support_end,
        subdivisions_per_physical_interval_per_side=n,
        subdivision_index=subdivision_index,
        mesh_level_identity=mesh_id,
        tube_cell_id=tube_id,
        shell_cell_id=shell_id,
        wall_interface_id=wall_id,
        inside_area_m2=inside_area,
        outside_area_m2=outside_area,
    )


class LocalState(StrictModel):
    temperature_k: Decimal
    pressure_pa: Decimal

    @field_validator("temperature_k", "pressure_pa")
    @classmethod
    def finite_positive_decimal(cls, value: Decimal) -> Decimal:
        if type(value) is not Decimal or not value.is_finite() or value <= 0:
            raise ValueError("state coordinates must be finite positive Decimal values")
        return value


class ShellFlowAuthority(StrictModel):
    task031_geometry: ShellSideHydraulicGeometry
    task166_result: Task166Result

    @model_validator(mode="after")
    def native_source_binding(self) -> ShellFlowAuthority:
        geometry = self.task031_geometry
        task166 = self.task166_result
        if type(geometry) is not ShellSideHydraulicGeometry:
            raise ValueError("TASK172 shell authority requires exact native TASK031 geometry")
        if type(task166) is not Task166Result:
            raise ValueError("TASK172 shell authority requires exact successful TASK166 result")
        expected_upstream = (
            (geometry.task020_configuration_id, "96637b2b-3583-5fdd-8645-bb2b5526996a"),
            (
                geometry.task020_configuration_hash,
                "04fbacd4037e4740328dd76b01caa0e85f22569924308d74b35bb13f0beb9125",
            ),
            (geometry.task021_layout_id, "55b3085c-6a2a-5394-8617-7102e7eb66a8"),
            (
                geometry.task021_layout_hash,
                "1dabd4362cc0c446da892bfe92b48fc6066b01ab3ca037d31ff4213e91fcc550",
            ),
            (geometry.task022_geometry_id, "cbacec31-31fa-5e14-aa1b-be05e04b96dc"),
            (
                geometry.task022_geometry_hash,
                "2384f3b31b279dac696951372d4b4781c58b8594c4d09091ec1a5cdaab7049f4",
            ),
            (geometry.task024_geometry_id, "279ed479-378d-5ea5-b2f0-8926133bf4dd"),
            (
                geometry.task024_geometry_hash,
                "68efd0e8dc69f203d49b73b2a87106863725d9a1b4a9bf1282cc1f650942d994",
            ),
        )
        if any(actual != expected for actual, expected in expected_upstream):
            raise ValueError("TASK031 geometry is not bound to accepted R118-D identities")
        try:
            provenance = dict(geometry.provenance)
            provenance_bindings = (
                ("task020_configuration_id", geometry.task020_configuration_id),
                ("task020_configuration_hash", geometry.task020_configuration_hash),
                ("task021_layout_id", geometry.task021_layout_id),
                ("task021_layout_hash", geometry.task021_layout_hash),
                ("task022_geometry_id", geometry.task022_geometry_id),
                ("task022_geometry_hash", geometry.task022_geometry_hash),
                ("task024_geometry_id", geometry.task024_geometry_id),
                ("task024_geometry_hash", geometry.task024_geometry_hash),
                (
                    "engineering_authority_profile_id",
                    TASK031_AUTHORITY_PROFILE_ID,
                ),
                ("engineering_authority_hash", geometry.engineering_authority_hash),
                ("pattern_family", geometry.pattern_family),
                ("flow_region_identity", geometry.flow_region_identity),
                ("request_hash", geometry.request_hash),
            )
            if any(provenance.get(key) != value for key, value in provenance_bindings):
                raise ValueError("TASK031 provenance does not match its public identity fields")
            if geometry.engineering_authority_id != task031_canonical.ENGINEERING_AUTHORITY_ID:
                raise ValueError("TASK031 public authority identity does not replay")
            expected_geometry_hash = task031_canonical.sha256_hex(
                task031_canonical.success_geometry_canonical_projection(geometry)
            )
            expected_geometry_id = task031_canonical.geometry_id(expected_geometry_hash)
            expected_task166_hash = task166_canonical.result_hash(task166)
            expected_task166_id = task166_canonical.result_id(expected_task166_hash)
        except Exception as exc:
            raise ValueError("native TASK031/TASK166 identity replay failed") from exc
        if geometry.geometry_hash != expected_geometry_hash:
            raise ValueError("TASK031 geometry hash does not replay")
        if geometry.geometry_id != expected_geometry_id or geometry.blockers:
            raise ValueError("TASK031 geometry identity/status is invalid")
        if (
            task166.result_hash != expected_task166_hash
            or task166.result_id != expected_task166_id
            or task166.blockers
            or task166.warnings
            or task166.bell_geometry is None
            or type(task166.bell_geometry) is not BellGeometry
            or task166.applicability is None
            or task166.applicability.status is not ApplicabilityStatus.APPLICABLE
            or task166.completeness is None
            or task166.completeness.status != "COMPLETE"
            or task166.provenance is None
        ):
            raise ValueError("TASK166 result identity or native completeness is invalid")
        hydraulic_evidence = dict(task166.shell_side_hydraulic_evidence)
        task020_evidence = dict(task166.task020_evidence)
        layout_evidence = dict(task166.tube_layout_evidence)
        bundle_evidence = dict(task166.shell_bundle_evidence)
        baffle_evidence = dict(task166.baffle_evidence)
        evidence_bindings = (
            (task020_evidence, ("configuration_id",), "96637b2b-3583-5fdd-8645-bb2b5526996a"),
            (
                task020_evidence,
                ("configuration_hash",),
                "04fbacd4037e4740328dd76b01caa0e85f22569924308d74b35bb13f0beb9125",
            ),
            (
                layout_evidence,
                ("layout_id", "result_id"),
                "55b3085c-6a2a-5394-8617-7102e7eb66a8",
            ),
            (
                layout_evidence,
                ("layout_hash", "result_hash"),
                "1dabd4362cc0c446da892bfe92b48fc6066b01ab3ca037d31ff4213e91fcc550",
            ),
            (
                bundle_evidence,
                ("geometry_id", "result_id"),
                "cbacec31-31fa-5e14-aa1b-be05e04b96dc",
            ),
            (
                bundle_evidence,
                ("geometry_hash", "result_hash"),
                "2384f3b31b279dac696951372d4b4781c58b8594c4d09091ec1a5cdaab7049f4",
            ),
            (
                baffle_evidence,
                ("geometry_id", "result_id"),
                "279ed479-378d-5ea5-b2f0-8926133bf4dd",
            ),
            (
                baffle_evidence,
                ("geometry_hash", "result_hash"),
                "68efd0e8dc69f203d49b73b2a87106863725d9a1b4a9bf1282cc1f650942d994",
            ),
        )
        evidence_mismatch = tuple(
            "/".join(candidate_keys)
            for fragment, candidate_keys, expected in evidence_bindings
            if not any(fragment.get(key) == expected for key in candidate_keys)
        )
        if (
            hydraulic_evidence.get("geometry_id") != geometry.geometry_id
            or hydraulic_evidence.get("geometry_hash") != geometry.geometry_hash
            or evidence_mismatch
        ):
            raise ValueError(
                "TASK166 result does not bind TASK031 and all accepted R118-D inputs: "
                f"evidence_mismatch={evidence_mismatch}"
            )
        bell = task166.bell_geometry
        if (
            bell.layout_id != geometry.task021_layout_id
            or bell.tube_count != Decimal("253")
            or bell.tube_outer_diameter_m != Decimal("0.01905")
            or bell.tube_pitch_m != Decimal("0.0254")
            or bell.baffle_count != 4
            or bell.central_baffle_spacing_m != Decimal("1.2")
        ):
            raise ValueError("TASK166 Bell geometry differs from the accepted case geometry")
        return self


class Task172LocalRequest(StrictModel):
    schema_version: Literal["task172.local-constitutive-request.v1"] = TASK172_REQUEST_SCHEMA
    case_id: Literal["V07-T172-PROJECT-ENGINEERING-REFERENCE-CASE-R1"] = CASE_ID
    case_revision_id: Literal["V07-T172-PROJECT-ENGINEERING-REFERENCE-CASE-R2"] = CASE_REVISION_ID
    topology: TopologyBinding
    support: LocalSupport
    tube_bulk_state: LocalState
    shell_bulk_state: LocalState
    tube_mass_flow_kg_s: Decimal
    shell_mass_flow_kg_s: Decimal
    property_profile_id: Literal["V07-T172-WATER-PROPERTY-PROFILE-R2"] = PROFILE_ID
    property_profile_canonical_hash: Literal[
        "8407227452b519483fbccbc686d3e8fcb2ca54866a8a8f01114addb5ca5a37de"
    ] = PROPERTY_PROFILE_CANONICAL_HASH
    r94_model_profile_canonical_hash: Literal[
        "81ae446af5e0009ce85c5fcb89d80534f9e2eaf36942b9d3a35aa0ff10a86aec"
    ] = R94_MODEL_PROFILE_CANONICAL_HASH
    r98_overlay_canonical_hash: Literal[
        "54c63a6c1178650e3164dd9f6cd7417ba044f2ec4b2f6b1b6a28accc19955a78"
    ] = R98_OVERLAY_CANONICAL_HASH
    stage1_authority_evidence_canonical_hash: Literal[
        "60d1270c52ea226df28634003b4beaf6a8d006915d6454fe7e55dfaaca8771c1"
    ] = STAGE1_AUTHORITY_EVIDENCE_CANONICAL_HASH
    shell_jmu_model_authority_canonical_hash: Literal[
        "ea6041287c407afe735148e12866f02026d23ba6e9c881ba22c076c032b5cac6"
    ] = SHELL_JMU_MODEL_AUTHORITY_CANONICAL_HASH
    shell_flow_authority: ShellFlowAuthority
    material_source_sha256: Literal[
        "eda6e84f95c4cc2a46bb8c902cf066c4f51b9108d951d5490222cb365219ac48"
    ] = MATERIAL_SOURCE_SHA256
    clean_wall_authority_hash: Literal[
        "e493999a1a6f8e83140e62ed71755af877a451bb9525f1e0791cddf174150b29"
    ] = CLEAN_WALL_AUTHORITY_HASH
    cylindrical_mapping_hash: Literal[
        "49f902ce096f57381057a6d3631ef4b30355526dae8187112ae04fa703dda63c"
    ] = CYLINDRICAL_MAPPING_HASH
    tube_inside_fouling_m2_k_w: Decimal = Decimal("0")
    shell_outside_fouling_m2_k_w: Decimal = Decimal("0")

    @field_validator("tube_mass_flow_kg_s", "shell_mass_flow_kg_s")
    @classmethod
    def positive_mass_flow(cls, value: Decimal) -> Decimal:
        if type(value) is not Decimal or not value.is_finite() or value <= 0:
            raise ValueError("mass flow must be positive finite Decimal")
        return value

    @field_validator("tube_inside_fouling_m2_k_w", "shell_outside_fouling_m2_k_w")
    @classmethod
    def finite_fouling_resistance(cls, value: Decimal) -> Decimal:
        if type(value) is not Decimal or not value.is_finite():
            raise ValueError("fouling resistance must be a finite Decimal")
        return value

    @model_validator(mode="after")
    def reviewed_state_and_surface(self) -> Task172LocalRequest:
        if self.tube_mass_flow_kg_s != Decimal("12.000000"):
            raise ValueError("tube mass flow differs from the accepted Stage-2 case revision")
        if self.shell_mass_flow_kg_s != Decimal("20.000000"):
            raise ValueError("shell mass flow differs from the accepted reference-case input")
        if self.tube_inside_fouling_m2_k_w != 0 or self.shell_outside_fouling_m2_k_w != 0:
            raise ValueError("only the reviewed clean-surface profile is admitted")
        for state in (self.tube_bulk_state, self.shell_bulk_state):
            if not Decimal("298.15") <= state.temperature_k <= Decimal("300.00"):
                raise ValueError("bulk temperature is outside the reviewed case property domain")
            if not Decimal("100000") <= state.pressure_pa <= Decimal("101325"):
                raise ValueError("bulk pressure is outside the reviewed case property domain")
        return self


class CandidateTopologyBinding(StrictModel):
    """Candidate-owned TASK171 identities; never aliases the reference binding."""

    topology_id: str = Field(min_length=1)
    task171_result_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    mesh_identity: str = Field(pattern=r"^[0-9a-f]{64}$")
    physical_ownership_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    definition_projection_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    production_mesh_profile_authority_id: Literal[
        "V07-T172-REAL-CASE-PRODUCTION-MESH-PROFILE-R1"
    ] = PRODUCTION_MESH_PROFILE_ID
    structural_mesh_authority_id: Literal["V07-T172-R119A-TASK171-MESH-R1"] = (
        TASK171_STRUCTURAL_MESH_AUTHORITY_ID
    )
    selected_variant: Literal["TUBE_HOT_SHELL_COLD"]
    thermal_role_selection_authority_id: Literal["V07-T172-R119C-THERMAL-ROLE-SELECTION-R1"] = (
        THERMAL_ROLE_AUTHORITY_ID
    )
    tube_role: Literal["HOT"] = "HOT"
    shell_role: Literal["COLD"] = "COLD"
    tube_flow_path_id: str = Field(min_length=1)
    shell_flow_path_id: str = Field(min_length=1)


class CandidateLocalSupport(StrictModel):
    """One candidate-native physical support and one numerical refinement child."""

    candidate_id: str = Field(min_length=1)
    candidate_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    physical_segment_id: str = Field(min_length=1)
    physical_segment_start_m: Decimal
    physical_segment_end_m: Decimal
    support_start_m: Decimal
    support_end_m: Decimal
    subdivisions_per_physical_interval_per_side: int = Field(ge=1, le=64)
    subdivision_index: int = Field(ge=0, le=63)
    mesh_level_identity: str = Field(pattern=r"^[0-9a-f]{64}$")
    tube_cell_id: str = Field(min_length=1)
    shell_cell_id: str = Field(min_length=1)
    wall_interface_id: str = Field(min_length=1)
    inside_area_m2: Decimal
    outside_area_m2: Decimal

    @field_validator(
        "physical_segment_start_m",
        "physical_segment_end_m",
        "support_start_m",
        "support_end_m",
        "inside_area_m2",
        "outside_area_m2",
    )
    @classmethod
    def finite_candidate_decimal(cls, value: Decimal) -> Decimal:
        if type(value) is not Decimal or not value.is_finite():
            raise ValueError("candidate support fields must be finite Decimal values")
        return value

    @model_validator(mode="after")
    def valid_refinement_child(self) -> CandidateLocalSupport:
        n = self.subdivisions_per_physical_interval_per_side
        if n not in _ALLOWED_SUBDIVISIONS or not 0 <= self.subdivision_index < n:
            raise ValueError("candidate support is outside the reviewed mesh sequence")
        if self.physical_segment_end_m <= self.physical_segment_start_m:
            raise ValueError("candidate physical support must have positive length")
        if self.support_end_m <= self.support_start_m:
            raise ValueError("candidate numerical support must have positive length")
        with localcontext() as context:
            context.prec = 80
            length = self.physical_segment_end_m - self.physical_segment_start_m
            child_length = length / Decimal(n)
            expected_start = self.physical_segment_start_m + child_length * self.subdivision_index
            expected_end = expected_start + child_length
        if (self.support_start_m, self.support_end_m) != (expected_start, expected_end):
            raise ValueError("candidate numerical support is not an exact interval refinement")
        if self.inside_area_m2 <= 0 or self.outside_area_m2 <= 0:
            raise ValueError("candidate support areas must be positive")
        return self


class CandidateShellFlowAuthority(StrictModel):
    """Candidate-native TASK031/TASK166 pair, validated without reference IDs."""

    task031_geometry: ShellSideHydraulicGeometry
    task166_result: Task166Result

    @model_validator(mode="after")
    def native_candidate_binding(self) -> CandidateShellFlowAuthority:
        geometry = self.task031_geometry
        result = self.task166_result
        if type(geometry) is not ShellSideHydraulicGeometry or type(result) is not Task166Result:
            raise ValueError("candidate shell authority requires exact native TASK031/TASK166")
        if (
            geometry.blockers
            or result.blockers
            or result.warnings
            or result.applicability is None
            or result.applicability.status is not ApplicabilityStatus.APPLICABLE
            or result.completeness is None
            or result.completeness.status != "COMPLETE"
            or result.bell_geometry is None
        ):
            raise ValueError("candidate TASK031/TASK166 applicability is not complete")
        if (
            dict(result.task020_evidence).get("result_id") != geometry.task020_configuration_id
            or dict(result.task020_evidence).get("result_hash")
            != geometry.task020_configuration_hash
            or dict(result.tube_layout_evidence).get("result_id") != geometry.task021_layout_id
            or dict(result.tube_layout_evidence).get("result_hash") != geometry.task021_layout_hash
            or dict(result.shell_bundle_evidence).get("result_id") != geometry.task022_geometry_id
            or dict(result.shell_bundle_evidence).get("result_hash")
            != geometry.task022_geometry_hash
            or dict(result.baffle_evidence).get("result_id") != geometry.task024_geometry_id
            or dict(result.baffle_evidence).get("result_hash") != geometry.task024_geometry_hash
        ):
            raise ValueError("candidate TASK031 and TASK166 native geometry bindings disagree")
        if (
            geometry.geometry_hash
            != task031_canonical.sha256_hex(
                task031_canonical.success_geometry_canonical_projection(geometry)
            )
            or result.result_hash != task166_canonical.result_hash(result)
            or result.result_id != task166_canonical.result_id(result.result_hash)
        ):
            raise ValueError("candidate TASK031/TASK166 canonical identity replay failed")
        return self


class CandidateThermalBinding(StrictModel):
    """Producer-issued candidate lineage used to authorize the shared kernel."""

    candidate_id: str = Field(min_length=1)
    candidate_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_package_id: Literal["V07-T173-SIZING-AUTHORITY-PACKAGE-R2"] = (
        TASK173_SIZING_AUTHORITY_PACKAGE_ID
    )
    authority_package_hash: Literal[
        "750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9"
    ] = TASK173_SIZING_AUTHORITY_PACKAGE_HASH
    task172_candidate_authority_hash: Literal[
        "fc7afcc9c51ed5920e3258b2a5683f1274d45df6c7d7e624be29614f97691483"
    ] = TASK173_SIZING_TASK172_AUTHORITY_HASH
    jmu_transfer_authority_hash: Literal[
        "6d716f541c44aeaa6911efe5919ed2f1474f4af93a4c06fcb01a672c56d234cc"
    ] = TASK173_SIZING_JMU_TRANSFER_HASH
    task171_result: Task171Result
    task025_result: Task025ValidResult
    task166_result: Task166Result

    @model_validator(mode="after")
    def candidate_lineage_matches(self) -> CandidateThermalBinding:
        topology = self.task171_result
        area = self.task025_result
        bell = self.task166_result
        if (
            topology.status != "VALIDATED"
            or topology.topology_id is None
            or topology.result_hash is None
            or topology.mesh_identity is None
            or topology.physical_ownership_hash is None
            or topology.native_identity is None
            or area.result_hash != topology.native_identity.area_result_hash
            or area.result_id != topology.native_identity.area_result_id
            or bell.result_hash == ""
            or not area.heat_transfer_authority.length_m.is_finite()
        ):
            raise ValueError("candidate TASK171/TASK025/TASK166 producer lineage is incomplete")
        definition = topology.topology_definition
        if definition is None:
            raise ValueError("candidate TASK171 validated result must carry its Definition")
        native = topology.native_identity
        if native is None:
            raise ValueError("candidate TASK171 result must carry native identity")
        native_pairs = (
            (bell.task020_evidence, native.configuration_id, native.configuration_hash),
            (bell.tube_layout_evidence, native.layout_id, native.layout_hash),
            (bell.shell_bundle_evidence, native.bundle_id, native.bundle_hash),
            (bell.baffle_evidence, native.baffle_id, native.baffle_hash),
        )
        if any(
            dict(evidence).get("result_id") != expected_id
            or dict(evidence).get("result_hash") != expected_hash
            for evidence, expected_id, expected_hash in native_pairs
        ):
            raise ValueError(
                "candidate TASK166 result is bound to different TASK171 native geometry"
            )
        interval_inside = sum(Decimal(item.inside_area_m2) for item in definition.intervals)
        interval_outside = sum(Decimal(item.outside_area_m2) for item in definition.intervals)
        bell_geometry = bell.bell_geometry
        if bell_geometry is None:
            raise ValueError("candidate TASK166 result must carry native Bell geometry")
        expected_outside = area.internal_heat_transfer_surface_area_m2 * (
            compute_outer_to_inner_area_ratio(
                area.hydraulic_diameter_m, bell_geometry.tube_outer_diameter_m
            )
        )
        if (
            interval_inside != Decimal(area.internal_heat_transfer_surface_area_m2)
            or interval_outside != expected_outside
        ):
            raise ValueError("candidate TASK171 support areas do not reconcile to TASK025")
        return self


class CandidateTask172LocalRequest(StrictModel):
    """Strict candidate sibling; the existing reference request remains unchanged."""

    schema_version: Literal["task172.candidate-local-constitutive-request.v1"] = (
        TASK172_CANDIDATE_REQUEST_SCHEMA
    )
    case_id: str = Field(min_length=1)
    case_revision_id: str = Field(min_length=1)
    topology: CandidateTopologyBinding
    support: CandidateLocalSupport
    tube_bulk_state: LocalState
    shell_bulk_state: LocalState
    tube_mass_flow_kg_s: Decimal
    shell_mass_flow_kg_s: Decimal
    property_profile_id: Literal["V07-T172-WATER-PROPERTY-PROFILE-R2"] = PROFILE_ID
    property_profile_canonical_hash: Literal[
        "8407227452b519483fbccbc686d3e8fcb2ca54866a8a8f01114addb5ca5a37de"
    ] = PROPERTY_PROFILE_CANONICAL_HASH
    r94_model_profile_canonical_hash: Literal[
        "81ae446af5e0009ce85c5fcb89d80534f9e2eaf36942b9d3a35aa0ff10a86aec"
    ] = R94_MODEL_PROFILE_CANONICAL_HASH
    r98_overlay_canonical_hash: Literal[
        "54c63a6c1178650e3164dd9f6cd7417ba044f2ec4b2f6b1b6a28accc19955a78"
    ] = R98_OVERLAY_CANONICAL_HASH
    stage1_authority_evidence_canonical_hash: Literal[
        "60d1270c52ea226df28634003b4beaf6a8d006915d6454fe7e55dfaaca8771c1"
    ] = STAGE1_AUTHORITY_EVIDENCE_CANONICAL_HASH
    shell_jmu_model_authority_canonical_hash: Literal[
        "ea6041287c407afe735148e12866f02026d23ba6e9c881ba22c076c032b5cac6"
    ] = SHELL_JMU_MODEL_AUTHORITY_CANONICAL_HASH
    shell_flow_authority: CandidateShellFlowAuthority
    material_source_sha256: Literal[
        "eda6e84f95c4cc2a46bb8c902cf066c4f51b9108d951d5490222cb365219ac48"
    ] = MATERIAL_SOURCE_SHA256
    clean_wall_authority_hash: Literal[
        "e493999a1a6f8e83140e62ed71755af877a451bb9525f1e0791cddf174150b29"
    ] = CLEAN_WALL_AUTHORITY_HASH
    cylindrical_mapping_hash: Literal[
        "49f902ce096f57381057a6d3631ef4b30355526dae8187112ae04fa703dda63c"
    ] = CYLINDRICAL_MAPPING_HASH
    tube_inside_fouling_m2_k_w: Decimal = Decimal("0")
    shell_outside_fouling_m2_k_w: Decimal = Decimal("0")
    candidate_binding: CandidateThermalBinding

    @field_validator("tube_mass_flow_kg_s", "shell_mass_flow_kg_s")
    @classmethod
    def positive_candidate_mass_flow(cls, value: Decimal) -> Decimal:
        if type(value) is not Decimal or not value.is_finite() or value <= 0:
            raise ValueError("candidate mass flow must be positive finite Decimal")
        return value

    @field_validator("tube_inside_fouling_m2_k_w", "shell_outside_fouling_m2_k_w")
    @classmethod
    def finite_candidate_fouling(cls, value: Decimal) -> Decimal:
        if type(value) is not Decimal or not value.is_finite():
            raise ValueError("candidate fouling resistance must be finite Decimal")
        return value

    @model_validator(mode="after")
    def candidate_reviewed_service(self) -> CandidateTask172LocalRequest:
        if self.tube_mass_flow_kg_s != Decimal("12.000000") or self.shell_mass_flow_kg_s != Decimal(
            "20.000000"
        ):
            raise ValueError("candidate transfer is limited to the reviewed 12/20 kg/s service")
        if self.tube_inside_fouling_m2_k_w != 0 or self.shell_outside_fouling_m2_k_w != 0:
            raise ValueError("candidate transfer is limited to the reviewed clean-surface profile")
        for state in (self.tube_bulk_state, self.shell_bulk_state):
            if not Decimal("298.15") <= state.temperature_k <= Decimal("300.00"):
                raise ValueError("candidate bulk temperature leaves the reviewed domain")
            if not Decimal("100000") <= state.pressure_pa <= Decimal("101325"):
                raise ValueError("candidate bulk pressure leaves the reviewed domain")
        return self

    @model_validator(mode="after")
    def candidate_binding_is_exact(self) -> CandidateTask172LocalRequest:
        native = self.candidate_binding.task171_result
        definition = native.topology_definition
        if definition is None:
            raise ValueError("candidate topology Definition is required")
        if (
            self.case_id != self.candidate_binding.candidate_id
            or self.case_revision_id != self.candidate_binding.candidate_id
            or self.topology.topology_id != native.topology_id
            or self.topology.task171_result_hash != native.result_hash
            or self.topology.mesh_identity != native.mesh_identity
            or self.topology.physical_ownership_hash != native.physical_ownership_hash
            or self.topology.tube_flow_path_id
            not in {path.flow_path_id for path in definition.paths if path.side == "TUBE"}
            or self.topology.shell_flow_path_id
            not in {path.flow_path_id for path in definition.paths if path.side == "SHELL"}
            or self.support.candidate_id != self.candidate_binding.candidate_id
            or self.support.candidate_hash != self.candidate_binding.candidate_hash
            or self.support.mesh_level_identity
            != canonical_sha256(
                {
                    "profile_authority_id": self.topology.production_mesh_profile_authority_id,
                    "candidate_id": self.candidate_binding.candidate_id,
                    "candidate_hash": self.candidate_binding.candidate_hash,
                    "task171_mesh_identity": self.topology.mesh_identity,
                    "subdivisions_per_physical_interval_per_side": (
                        self.support.subdivisions_per_physical_interval_per_side
                    ),
                }
            )
            or self.shell_flow_authority.task166_result.result_hash
            != self.candidate_binding.task166_result.result_hash
        ):
            raise ValueError("candidate TASK172 identities do not match native producer outputs")
        intervals = {item.physical_segment_id: item for item in definition.intervals}
        interval = intervals.get(self.support.physical_segment_id)
        if (
            interval is None
            or Decimal(interval.start_m) != self.support.physical_segment_start_m
            or Decimal(interval.end_m) != self.support.physical_segment_end_m
        ):
            raise ValueError("candidate TASK172 support is not from the TASK171 Definition")
        return self


class Task172LocalResult(StrictModel):
    schema_version: Literal["task172.local-constitutive-result.v1"] = TASK172_RESULT_SCHEMA
    status: Literal["VALIDATED"]
    implementation_version: Literal["task172.local-runtime-v1"] = TASK172_IMPLEMENTATION_VERSION
    case_id: str
    case_revision_id: str
    topology_id: str
    task171_result_hash: str
    task171_mesh_identity: str
    physical_ownership_hash: str
    definition_projection_hash: str
    selected_thermal_role_variant: str
    thermal_role_selection_authority_id: str
    physical_support_id: str
    physical_segment_id: str
    mesh_level_identity: str
    subdivisions_per_physical_interval_per_side: int
    subdivision_index: int
    tube_cell_id: str
    shell_cell_id: str
    wall_interface_id: str
    tube_bulk_temperature_k: Decimal
    shell_bulk_temperature_k: Decimal
    tube_property_snapshot_identity: str
    shell_property_snapshot_identity: str
    tube_wall_property_snapshot_identity: str
    shell_wall_property_snapshot_identity: str
    tube_htc_w_m2_k: Decimal
    shell_htc_w_m2_k: Decimal
    wall_temperature_inner_k: Decimal
    wall_temperature_outer_k: Decimal
    signed_q_hot_to_cold_w: Decimal
    inner_film_resistance_k_w: Decimal
    wall_resistance_k_w: Decimal
    outer_film_resistance_k_w: Decimal
    residual_vector_w: tuple[Decimal, Decimal, Decimal]
    residual_acceptance_state: Literal["PASS_C_RESIDUAL_SPECIFIC_ULP_OPERATION_BOUND"]
    solver_status: str
    solver_nfev: int
    residual_callback_count: int
    tube_reynolds_number: Decimal
    tube_prandtl_number_bulk: Decimal
    shell_reynolds_number: Decimal
    shell_prandtl_number: Decimal
    shell_j_mu: Decimal
    tube_correlation_id: str
    tube_correlation_version: str
    shell_correlation_id: str
    property_profile_id: str
    property_profile_canonical_hash: str
    shell_jmu_model_authority_canonical_hash: str
    material_source_sha256: str
    clean_wall_authority_hash: str
    cylindrical_mapping_hash: str
    numerical_profile_id: str
    r94_model_profile_canonical_hash: str
    r98_overlay_canonical_hash: str
    stage1_authority_evidence_canonical_hash: str
    request_hash: str
    result_hash: str
    result_id: str
    provenance_refs: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()


class Task172BlockedResult(StrictModel):
    schema_version: Literal["task172.local-constitutive-blocked.v1"] = TASK172_BLOCKED_SCHEMA
    status: Literal["BLOCKED"]
    failure_code: str
    field_path: str
    request_hash: str | None
    diagnostic_last_iterate: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    blockers: tuple[str, ...]
    blocked_result_hash: str


Task172LocalOutcome = Task172LocalResult | Task172BlockedResult


__all__ = [
    "CASE_ID",
    "CLEAN_WALL_AUTHORITY_HASH",
    "COOLPROP_GIT_REVISION",
    "COOLPROP_VERSION",
    "CYLINDRICAL_MAPPING_HASH",
    "DEFINITION_PROJECTION_HASH",
    "MATERIAL_SOURCE_SHA256",
    "MESH_IDENTITY",
    "PRODUCTION_MESH_PROFILE_ID",
    "PHYSICAL_OWNERSHIP_HASH",
    "PROFILE_ID",
    "PROPERTY_PROFILE_CANONICAL_HASH",
    "R94_MODEL_PROFILE_CANONICAL_HASH",
    "R98_OVERLAY_CANONICAL_HASH",
    "SHELL_JMU_MODEL_AUTHORITY_CANONICAL_HASH",
    "SHELL_FLOW_PATH_ID",
    "STAGE1_AUTHORITY_EVIDENCE_CANONICAL_HASH",
    "TASK171_RESULT_HASH",
    "TASK172_IMPLEMENTATION_VERSION",
    "TASK172_REQUEST_SCHEMA",
    "TASK172_RESULT_SCHEMA",
    "TASK025_RESULT_HASH",
    "TASK025_RESULT_ID",
    "TOPOLOGY_ID",
    "TOTAL_INSIDE_AREA_M2",
    "TOTAL_OUTSIDE_AREA_M2",
    "TOTAL_PARALLEL_FLOW_AREA_M2",
    "TUBE_FLOW_PATH_ID",
    "TUBE_ID_M",
    "TUBE_OD_M",
    "WALL_CONDUCTIVITY_W_M_K",
    "LocalState",
    "LocalSupport",
    "ShellFlowAuthority",
    "Task172BlockedResult",
    "Task172LocalOutcome",
    "Task172LocalRequest",
    "Task172LocalResult",
    "TopologyBinding",
    "build_local_support",
    "mesh_level_identity",
]
