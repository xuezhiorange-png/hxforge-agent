"""Tests for TASK-017 Slice B — MassCalculator.

Scope (Slice B only, per design §14.2 + §11):

* Covers every §6 mass formula (inner_tube, outer_pipe, hairpin_bend,
  fittings) with PASS / boundary / error scenarios.
* Covers every Slice B-reachable §7 error code.
* Covers §10 JSON / hash / ordering determinism + provenance.
* Includes guard tests asserting that no Slice C / D / Closeout
  behavior, no pressure-drop code, and no cost code appears in the
  TASK-017 mass calculator code path.

Out of scope (explicit, design §14.2 + §3.2):

* No Slice C preliminary mechanical checks.
* No Slice D preliminary mechanical checks (minimum-wall / span).
* No Slice C/D/Closeout behavior tests.
* No TASK-018+ content.
"""

from __future__ import annotations

import importlib
import json
import math
from decimal import Decimal
from typing import Any

import pytest

from hexagent.canonical_json import canonical_sha256
from hexagent.geometry_catalogs.models import (
    GeometryCatalog,
    HairpinGeometryRecord,
    PipeGeometryRecord,
    SourceBinding,
    TubeGeometryRecord,
)
from hexagent.material_mass_mechanical.mass_calculator import (
    COMPONENT_ROLES_FROZEN_ORDER,
    ERROR_GEOMETRY_CATALOG_INCONSISTENT,
    ERROR_GEOMETRY_CATALOG_UNAPPROVED,
    ERROR_HAIRPIN_BEND_INPUT_INCOMPLETE,
    ERROR_INPUT_DIMENSIONAL_INCONSISTENT,
    MassBreakdown,
    MassCalculationRequest,
    MassProvenance,
    calculate_mass_breakdown,
)
from hexagent.material_mass_mechanical.material_selector import (
    ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
    ERROR_MATERIAL_RESOLUTION_MISSING_ROLE,
    FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA,
    PROPERTY_NAME_ALLOWABLE_STRESS,
    PROPERTY_NAME_DENSITY,
    PROPERTY_NAME_YOUNGS_MODULUS,
    MaterialResolutionRequest,
    MaterialSelectorError,
    resolve_material,
)

_SLICE_B_CODE_PATH = "hexagent.material_mass_mechanical.mass_calculator"
DEFAULT_LENGTH_M = 6.0


# ----------------- Fixtures -----------------


def _property_value(
    *,
    name: str,
    value_si: str,
    unit_si: str,
    source_pointer: str = "internal://task-013/handbook",
) -> dict[str, Any]:
    """Build a TASK-013 ``property_values[]`` entry matching §5.5."""
    return {
        "property_name": name,
        "value_si": value_si,
        "unit_si": unit_si,
        "source_pointer": source_pointer,
        "quality_flags": ["assumed_value"],
    }


def _cast_to_material_record(d: dict[str, Any]) -> Any:
    """Cast a dict fixture to a MaterialRecord-typed object."""
    return d


def _base_material_record(
    *,
    approval_state: str = "approved",
    include_youngs_modulus: bool = True,
    include_allowable_stress: bool = True,
    density_value_si: str = "7850",
    allowable_table_json: str | None = None,
    record_id: str = "mat:astm-sa-106-b:rev:2026-Q2",
    grade: str = "SA-106-B",
) -> dict[str, Any]:
    """Return a TASK-013 material record fixture suitable for resolving
    via ``resolve_material`` (consumed by Slice B as the per-role
    MaterialResolutionResult source)."""
    if allowable_table_json is None:
        allowable_table_json = '{"20": "137.895", "200": "103.421", "400": "68.947"}'
    record: dict[str, Any] = {
        "material_record_id": record_id,
        "material_record_version": "1.0.0",
        "material_family": "carbon_steel",
        "material_grade_or_designation": grade,
        "form_factor": "pipe",
        "region": "US",
        "effective_date": "2026-01-01T00:00:00Z",
        "source_class": "internal_engineering_assumption",
        "source_reference": "internal://handbook/SA-106-B",
        "license_evidence": "project_internal_authority",
        "dimensional_units": {"density": "kg/m^3", "youngs_modulus": "GPa"},
        "quality_flags": ["assumed_value"],
        "approval_state": approval_state,
        "provenance_edges": ["edge:internal-handbook/SA-106-B"],
        "property_values": [
            _property_value(
                name=PROPERTY_NAME_DENSITY,
                value_si=density_value_si,
                unit_si="kg/m^3",
            ),
        ],
    }
    if include_youngs_modulus:
        record["property_values"].append(
            _property_value(
                name=PROPERTY_NAME_YOUNGS_MODULUS,
                value_si="200",
                unit_si="GPa",
            )
        )
    if include_allowable_stress:
        record["property_values"].append(
            _property_value(
                name=PROPERTY_NAME_ALLOWABLE_STRESS,
                value_si=allowable_table_json,
                unit_si="MPa",
            )
        )
    return record


def _source_binding() -> SourceBinding:
    """Return a minimal SourceBinding for fixture geometry records."""
    return SourceBinding(
        source_id="src:internal-handbook",
        source_type="internal_engineering_handbook",
        source_revision="2026-Q2",
        source_location="internal://handbook/SA-106-B",
        evidence_ref="evidence:internal/2026-Q2",
        approved_by="internal_engineer",
        approved_at="2026-01-01T00:00:00Z",
    )


def _make_tube_record(
    *,
    geometry_id: str = "tube:dn15-sch40:rev:2026-Q2",
    approval_state: str = "approved",
    outer_diameter_m: float = 0.0213,
    inner_diameter_m: float = 0.0159,
    wall_thickness_m: float | None = None,
) -> TubeGeometryRecord:
    """Construct a TubeGeometryRecord fixture."""
    if wall_thickness_m is None:
        wall_thickness_m = (outer_diameter_m - inner_diameter_m) / 2.0
    cross_section_area = math.pi * ((outer_diameter_m / 2.0) ** 2 - (inner_diameter_m / 2.0) ** 2)
    inner_radius = inner_diameter_m / 2.0
    flow_area = math.pi * inner_radius**2
    hydraulic_diameter = 4.0 * flow_area / cross_section_area if cross_section_area > 0 else 0.0
    return TubeGeometryRecord(
        geometry_id=geometry_id,
        approval_state=approval_state,
        nominal_label="DN15 Sch40",
        outer_diameter_m=outer_diameter_m,
        inner_diameter_m=inner_diameter_m,
        wall_thickness_m=wall_thickness_m,
        cross_section_area_m2=cross_section_area,
        flow_area_m2=flow_area,
        hydraulic_diameter_m=hydraulic_diameter,
        source_binding=_source_binding(),
        revision="2026-Q2",
        tags=("inner_tube",),
    )


def _make_pipe_record(
    *,
    geometry_id: str = "pipe:dn50-sch40:rev:2026-Q2",
    approval_state: str = "approved",
    outer_diameter_m: float = 0.0603,
    inner_diameter_m: float = 0.0539,
    wall_thickness_m: float | None = None,
) -> PipeGeometryRecord:
    """Construct a PipeGeometryRecord fixture."""
    if wall_thickness_m is None:
        wall_thickness_m = (outer_diameter_m - inner_diameter_m) / 2.0
    cross_section_area = math.pi * ((outer_diameter_m / 2.0) ** 2 - (inner_diameter_m / 2.0) ** 2)
    inner_radius = inner_diameter_m / 2.0
    flow_area = math.pi * inner_radius**2
    hydraulic_diameter = 4.0 * flow_area / cross_section_area if cross_section_area > 0 else 0.0
    return PipeGeometryRecord(
        geometry_id=geometry_id,
        approval_state=approval_state,
        nominal_label="DN50 Sch40",
        nominal_pipe_size_label="DN50",
        schedule_label="Sch40",
        outer_diameter_m=outer_diameter_m,
        inner_diameter_m=inner_diameter_m,
        wall_thickness_m=wall_thickness_m,
        flow_area_m2=flow_area,
        hydraulic_diameter_m=hydraulic_diameter,
        source_binding=_source_binding(),
        revision="2026-Q2",
        tags=("outer_pipe",),
    )


def _make_hairpin_record(
    *,
    geometry_id: str = "hairpin:dn15-dn50:rev:2026-Q2",
    approval_state: str = "approved",
    tube_geometry_id: str = "tube:dn15-sch40:rev:2026-Q2",
    pipe_geometry_id: str = "pipe:dn50-sch40:rev:2026-Q2",
    number_of_tubes: int = 1,
    effective_length_m: float = 6.0,
    bend_radius_m: float = 0.075,
    centerline_spacing_m: float = 0.0853,
    flow_path_descriptor: str = "U-bend",
) -> HairpinGeometryRecord:
    """Construct a HairpinGeometryRecord fixture."""
    return HairpinGeometryRecord(
        geometry_id=geometry_id,
        hairpin_id="hairpin:dn15-dn50",
        approval_state=approval_state,
        nominal_label="DN15/DN50 hairpin",
        tube_geometry_id=tube_geometry_id,
        pipe_geometry_id=pipe_geometry_id,
        number_of_tubes=number_of_tubes,
        effective_length_m=effective_length_m,
        bend_radius_m=bend_radius_m,
        centerline_spacing_m=centerline_spacing_m,
        flow_path_descriptor=flow_path_descriptor,
        source_binding=_source_binding(),
        revision="2026-Q2",
        tags=("hairpin_bend",),
    )


def _make_catalog(*records: Any) -> GeometryCatalog:
    """Build a GeometryCatalog fixture from the supplied records."""
    return GeometryCatalog(
        catalog_id="catalog:task017-test",
        catalog_version="2026-Q2",
        authority="task017_test_fixtures",
        source_revision="2026-Q2",
        records=tuple(records),
        content_hash="0" * 64,
    )


def _resolve_material(
    *,
    component_role: str,
    record_id: str = "mat:astm-sa-106-b:rev:2026-Q2",
    approval_state: str = "approved",
    include_density: bool = True,
    density_value_si: str = "7850",
) -> Any:
    """Resolve a MaterialResolutionResult via Slice A for the given role."""
    record = _base_material_record(
        approval_state=approval_state,
        density_value_si=density_value_si if include_density else "0",
        record_id=record_id,
    )
    if not include_density:
        record["property_values"] = [
            pv for pv in record["property_values"] if pv["property_name"] != PROPERTY_NAME_DENSITY
        ]
    request = MaterialResolutionRequest(
        component_role=component_role,
        material_record_id=record_id,
        design_temperature_c=200.0,
        design_pressure_mpa=5.0,
        corrosion_allowance_mm=1.5,
        applicable_standard_id="ASME B31.3",
    )
    return resolve_material(
        request=request,
        material_record=_cast_to_material_record(record),
    )


def _four_role_resolutions(
    *,
    approval_state: str = "approved",
    include_density: bool = True,
    density_value_si: str = "7850",
    record_id: str = "mat:astm-sa-106-b:rev:2026-Q2",
) -> dict[str, Any]:
    """Build a four-role material resolutions mapping for Slice B tests.

    When ``include_density`` is False, the function constructs the
    MaterialResolutionResult objects directly with ``density_kg_m3=None``
    (bypassing Slice A's selector, which would itself raise
    MATERIAL_GOVERNANCE_INCOMPLETE on a density-missing record).
    This is the canonical way to exercise the Slice B
    "incomplete input" path.
    """
    if not include_density:
        # Build a MaterialResolutionResult with density_kg_m3 = None
        # directly. We construct a stub provenance + result and
        # replicate the Slice A result shape.
        from hexagent.material_mass_mechanical.material_selector import (
            MaterialProvenance,
            MaterialResolutionResult,
        )

        provenance = MaterialProvenance(
            geometry_record_id="geom:test",
            material_record_id=record_id,
            applicable_standard_id=None,
            design_pressure_mpa=None,
            design_temperature_c=None,
            correlation_ids=(),
            software_version="0.1.0",
            git_commit=FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA,
            result_hash="0" * 64,
        )
        result = MaterialResolutionResult(
            material_record_id=record_id,
            material_grade="SA-106-B",
            density_kg_m3=None,
            youngs_modulus_gpa=None,
            allowable_stress_mpa=None,
            provenance=provenance,
        )
        return {role: result for role in COMPONENT_ROLES_FROZEN_ORDER}
    return {
        role: _resolve_material(
            component_role=role,
            record_id=record_id,
            approval_state=approval_state,
            include_density=include_density,
            density_value_si=density_value_si,
        )
        for role in COMPONENT_ROLES_FROZEN_ORDER
    }


# ----------------- Tests: §5.2.1 closed-set guards -----------------


def test_component_roles_frozen_order_has_exactly_four_roles() -> None:
    """§5.2.1: closed set of exactly 4 component_role strings."""
    assert COMPONENT_ROLES_FROZEN_ORDER == (
        "inner_tube",
        "outer_pipe",
        "hairpin_bend",
        "fittings",
    )
    assert len(COMPONENT_ROLES_FROZEN_ORDER) == 4


def test_missing_role_in_resolutions_raises_missing_role_error() -> None:
    """§5.2.1: missing role -> MATERIAL_RESOLUTION_MISSING_ROLE."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions()
    del resolutions["fittings"]
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
    )
    with pytest.raises(MaterialSelectorError) as excinfo:
        calculate_mass_breakdown(request)
    assert excinfo.value.code == ERROR_MATERIAL_RESOLUTION_MISSING_ROLE
    assert "fittings" in excinfo.value.context["missing_roles"]


def test_extra_role_in_resolutions_raises_missing_role_error() -> None:
    """§5.2.1 closed set: extra (non-frozen) role keys rejected."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions()
    resolutions["unknown_role"] = resolutions["inner_tube"]
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
    )
    with pytest.raises(MaterialSelectorError) as excinfo:
        calculate_mass_breakdown(request)
    assert excinfo.value.code == ERROR_MATERIAL_RESOLUTION_MISSING_ROLE
    assert "unknown_role" in excinfo.value.context["extra_roles"]


# ----------------- Tests: §6.1 / §6.2 straight-pipe mass formulas -----------------


def test_inner_tube_mass_formula_matches_design_section_6_1() -> None:
    """§6.1: density * pi * ((outer/2)^2 - (inner/2)^2) * length."""
    tube_record = _make_tube_record(
        outer_diameter_m=0.0213,
        inner_diameter_m=0.0159,
    )
    expected_density_kg_m3 = 7850.0
    expected_length_m = 6.0
    expected_outer_m = 0.0213
    expected_inner_m = 0.0159
    expected_inner_tube_kg = (
        expected_density_kg_m3
        * math.pi
        * ((expected_outer_m / 2.0) ** 2 - (expected_inner_m / 2.0) ** 2)
        * expected_length_m
    )
    expected_inner_tube_kg_q = float(
        Decimal(str(expected_inner_tube_kg)).quantize(Decimal("0.000001"))
    )
    resolutions = _four_role_resolutions(density_value_si="7850")
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=expected_length_m,
        material_resolutions_by_component_role=resolutions,
    )
    breakdown = calculate_mass_breakdown(request)
    assert breakdown.inner_tube_kg == pytest.approx(expected_inner_tube_kg_q, rel=1e-6)
    assert breakdown.inner_tube_kg > 0.0


def test_outer_pipe_mass_formula_matches_design_section_6_2() -> None:
    """§6.2: same formula as §6.1 applied to outer_pipe dimensions."""
    pipe_record = _make_pipe_record(
        outer_diameter_m=0.0603,
        inner_diameter_m=0.0539,
    )
    expected_density_kg_m3 = 7850.0
    expected_length_m = 6.0
    expected_outer_m = 0.0603
    expected_inner_m = 0.0539
    expected_outer_pipe_kg = (
        expected_density_kg_m3
        * math.pi
        * ((expected_outer_m / 2.0) ** 2 - (expected_inner_m / 2.0) ** 2)
        * expected_length_m
    )
    expected_outer_pipe_kg_q = float(
        Decimal(str(expected_outer_pipe_kg)).quantize(Decimal("0.000001"))
    )
    resolutions = _four_role_resolutions(density_value_si="7850")
    request = MassCalculationRequest(
        geometry_record=pipe_record,
        effective_length_m=expected_length_m,
        material_resolutions_by_component_role=resolutions,
    )
    breakdown = calculate_mass_breakdown(request)
    assert breakdown.outer_pipe_kg == pytest.approx(expected_outer_pipe_kg_q, rel=1e-6)


def test_straight_pipe_zero_length_produces_zero_mass() -> None:
    """Boundary: zero effective_length_m -> zero mass for inner/outer."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=0.0,
        material_resolutions_by_component_role=resolutions,
    )
    breakdown = calculate_mass_breakdown(request)
    assert breakdown.inner_tube_kg == 0.0
    assert breakdown.outer_pipe_kg == 0.0
    assert breakdown.hairpin_bend_kg == 0.0
    assert breakdown.fittings_kg == 0.0
    assert breakdown.total_kg == 0.0


def test_straight_pipe_negative_length_raises_dimension_inconsistent() -> None:
    """§7 INPUT_DIMENSIONAL_INCONSISTENT: negative effective_length_m."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=-1.0,
        material_resolutions_by_component_role=resolutions,
    )
    with pytest.raises(MaterialSelectorError) as excinfo:
        calculate_mass_breakdown(request)
    assert excinfo.value.code == ERROR_INPUT_DIMENSIONAL_INCONSISTENT


def test_straight_pipe_consistent_with_decimal_quantization() -> None:
    """§10.3: kg values quantized to 6 decimal places."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
    )
    breakdown = calculate_mass_breakdown(request)
    assert math.isfinite(breakdown.inner_tube_kg)
    quantized = breakdown.inner_tube_kg * 1e6
    assert quantized == pytest.approx(round(quantized), abs=1e-3)
    quantized_outer = breakdown.outer_pipe_kg * 1e6
    assert quantized_outer == pytest.approx(round(quantized_outer), abs=1e-3)


# ----------------- Tests: §6.3 hairpin bend formula -----------------


def test_hairpin_bend_mass_zero_when_include_hairpin_false() -> None:
    """§6.3: include_hairpin=False -> hairpin_bend_kg = 0."""
    tube_record = _make_tube_record()
    hairpin = _make_hairpin_record()
    catalog = _make_catalog(tube_record, hairpin)
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=hairpin,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
        include_hairpin=False,
    )
    breakdown = calculate_mass_breakdown(request, catalog=catalog)
    assert breakdown.hairpin_bend_kg == 0.0


def test_hairpin_bend_mass_zero_when_geometry_not_hairpin() -> None:
    """§6.3: TubeGeometryRecord is not a hairpin -> hairpin_bend_kg = 0."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
        include_hairpin=True,  # ignored for non-hairpin geometry
    )
    breakdown = calculate_mass_breakdown(request)
    assert breakdown.hairpin_bend_kg == 0.0


def test_hairpin_bend_mass_formula_matches_design_section_6_3() -> None:
    """§6.3 hairpin formula: density * area * pi*R * number_of_tubes."""
    tube_record = _make_tube_record(
        outer_diameter_m=0.0213,
        inner_diameter_m=0.0159,
    )
    bend_radius_m = 0.075
    number_of_tubes = 2
    hairpin = _make_hairpin_record(
        tube_geometry_id=tube_record.geometry_id,
        bend_radius_m=bend_radius_m,
        number_of_tubes=number_of_tubes,
        effective_length_m=6.0,
    )
    catalog = _make_catalog(tube_record, hairpin)
    resolutions = _four_role_resolutions(density_value_si="7850")
    request = MassCalculationRequest(
        geometry_record=hairpin,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
        include_hairpin=True,
    )
    breakdown = calculate_mass_breakdown(request, catalog=catalog)
    expected_area = math.pi * (
        (tube_record.outer_diameter_m / 2.0) ** 2 - (tube_record.inner_diameter_m / 2.0) ** 2
    )
    expected_arc = math.pi * bend_radius_m
    expected_volume = expected_area * expected_arc * number_of_tubes
    expected_kg = 7850.0 * expected_volume
    expected_kg_q = float(Decimal(str(expected_kg)).quantize(Decimal("0.000001")))
    assert breakdown.hairpin_bend_kg == pytest.approx(expected_kg_q, rel=1e-6)
    assert breakdown.hairpin_bend_kg > 0.0


def test_hairpin_bend_incomplete_when_tube_reference_missing() -> None:
    """§7: HAIRPIN_BEND_INPUT_INCOMPLETE — tube_geometry_id not in catalog."""
    hairpin = _make_hairpin_record(tube_geometry_id="tube:DOES-NOT-EXIST")
    catalog = _make_catalog()  # empty
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=hairpin,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
        include_hairpin=True,
    )
    with pytest.raises(MaterialSelectorError) as excinfo:
        calculate_mass_breakdown(request, catalog=catalog)
    assert excinfo.value.code == ERROR_HAIRPIN_BEND_INPUT_INCOMPLETE


def test_hairpin_bend_incomplete_when_catalog_not_supplied() -> None:
    """§6.3: hairpin computation requires a catalog to resolve tube_geometry_id."""
    tube_record = _make_tube_record()
    hairpin = _make_hairpin_record(tube_geometry_id=tube_record.geometry_id)
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=hairpin,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
        include_hairpin=True,
    )
    with pytest.raises(MaterialSelectorError) as excinfo:
        calculate_mass_breakdown(request)
    assert excinfo.value.code == ERROR_HAIRPIN_BEND_INPUT_INCOMPLETE


def test_hairpin_bend_incomplete_when_number_of_tubes_invalid() -> None:
    """§7: HAIRPIN_BEND_INPUT_INCOMPLETE — number_of_tubes must be positive int."""
    tube_record = _make_tube_record()
    hairpin = _make_hairpin_record(
        tube_geometry_id=tube_record.geometry_id,
        number_of_tubes=0,
    )
    catalog = _make_catalog(tube_record, hairpin)
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=hairpin,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
        include_hairpin=True,
    )
    with pytest.raises(MaterialSelectorError) as excinfo:
        calculate_mass_breakdown(request, catalog=catalog)
    assert excinfo.value.code == ERROR_HAIRPIN_BEND_INPUT_INCOMPLETE


def test_hairpin_inconsistent_when_length_less_than_pi_r() -> None:
    """§6.3 sanity: effective_length_m < pi*bend_radius_m -> GEOMETRY_CATALOG_INCONSISTENT."""
    tube_record = _make_tube_record()
    hairpin = _make_hairpin_record(
        tube_geometry_id=tube_record.geometry_id,
        bend_radius_m=0.075,
        effective_length_m=0.05,  # < pi * 0.075
    )
    catalog = _make_catalog(tube_record, hairpin)
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=hairpin,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
        include_hairpin=True,
    )
    with pytest.raises(MaterialSelectorError) as excinfo:
        calculate_mass_breakdown(request, catalog=catalog)
    assert excinfo.value.code == ERROR_GEOMETRY_CATALOG_INCONSISTENT


# ----------------- Tests: §6.4 fittings formula -----------------


def test_fittings_mass_zero_when_no_overrides() -> None:
    """§6.4: no overrides -> fittings_kg = 0."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
        fitting_overrides_kg=(),
    )
    breakdown = calculate_mass_breakdown(request)
    assert breakdown.fittings_kg == 0.0


def test_fittings_mass_density_normalization_default() -> None:
    """§6.4 default: fittings_kg = sum(overrides) * (density / 7850.0)."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions(density_value_si="7850")
    overrides = (1.0, 2.0, 3.5)
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
        fitting_overrides_kg=overrides,
        fitting_density_normalization=True,
    )
    breakdown = calculate_mass_breakdown(request)
    expected = (1.0 + 2.0 + 3.5) * (7850.0 / 7850.0)
    expected_q = float(Decimal(str(expected)).quantize(Decimal("0.000001")))
    assert breakdown.fittings_kg == pytest.approx(expected_q, rel=1e-6)


def test_fittings_mass_exact_sum_when_density_normalization_false() -> None:
    """§6.4 alternative: fittings_kg = sum(overrides) exactly."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions(density_value_si="7850")
    overrides = (1.5, 2.5)
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
        fitting_overrides_kg=overrides,
        fitting_density_normalization=False,
    )
    breakdown = calculate_mass_breakdown(request)
    assert breakdown.fittings_kg == pytest.approx(4.0, rel=1e-6)


def test_fittings_negative_override_raises_dimension_inconsistent() -> None:
    """§7 INPUT_DIMENSIONAL_INCONSISTENT: negative fitting override."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
        fitting_overrides_kg=(1.0, -0.5),
    )
    with pytest.raises(MaterialSelectorError) as excinfo:
        calculate_mass_breakdown(request)
    assert excinfo.value.code == ERROR_INPUT_DIMENSIONAL_INCONSISTENT


# ----------------- Tests: §7 error codes -----------------


def test_geometry_unapproved_raises_unapproved_error() -> None:
    """§7 GEOMETRY_CATALOG_UNAPPROVED: non-approved geometry rejected."""
    tube_record = _make_tube_record(approval_state="pending")
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
    )
    with pytest.raises(MaterialSelectorError) as excinfo:
        calculate_mass_breakdown(request)
    assert excinfo.value.code == ERROR_GEOMETRY_CATALOG_UNAPPROVED


def test_geometry_inconsistent_outer_less_than_inner_raises_inconsistent() -> None:
    """§7 GEOMETRY_CATALOG_INCONSISTENT: outer < inner rejected."""
    bad_tube = _make_tube_record(
        outer_diameter_m=0.01,
        inner_diameter_m=0.02,
    )
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=bad_tube,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
    )
    with pytest.raises(MaterialSelectorError) as excinfo:
        calculate_mass_breakdown(request)
    assert excinfo.value.code == ERROR_GEOMETRY_CATALOG_INCONSISTENT


def test_material_governance_incomplete_when_density_missing() -> None:
    """§7 MATERIAL_GOVERNANCE_INCOMPLETE: density missing for inner_tube."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions(include_density=False)
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
    )
    with pytest.raises(MaterialSelectorError) as excinfo:
        calculate_mass_breakdown(request)
    assert excinfo.value.code == ERROR_MATERIAL_GOVERNANCE_INCOMPLETE


def test_hairpin_referenced_tube_unapproved_raises_geometry_unapproved() -> None:
    """§7 GEOMETRY_CATALOG_UNAPPROVED: hairpin tube reference unapproved."""
    tube_record = _make_tube_record(approval_state="pending")
    hairpin = _make_hairpin_record(tube_geometry_id=tube_record.geometry_id)
    catalog = _make_catalog(tube_record, hairpin)
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=hairpin,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
        include_hairpin=True,
    )
    with pytest.raises(MaterialSelectorError) as excinfo:
        calculate_mass_breakdown(request, catalog=catalog)
    assert excinfo.value.code == ERROR_GEOMETRY_CATALOG_UNAPPROVED


# ----------------- Tests: §10 determinism / hash / ordering -----------------


def test_calculation_hash_is_64_char_sha256_hex() -> None:
    """§10.4: calculation_hash is the lowercase hex SHA-256."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
    )
    breakdown = calculate_mass_breakdown(request)
    assert isinstance(breakdown.calculation_hash, str)
    assert len(breakdown.calculation_hash) == 64
    int(breakdown.calculation_hash, 16)  # parses as hex


def test_determinism_two_invocations_produce_identical_breakdown() -> None:
    """§11.4: identical inputs -> byte-identical JSON + identical SHA-256."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
    )
    breakdown_a = calculate_mass_breakdown(request)
    breakdown_b = calculate_mass_breakdown(request)
    assert breakdown_a.calculation_hash == breakdown_b.calculation_hash
    assert breakdown_a.to_dict() == breakdown_b.to_dict()
    manual_payload = {
        "fittings_kg": repr(breakdown_a.fittings_kg),
        "hairpin_bend_kg": repr(breakdown_a.hairpin_bend_kg),
        "inner_tube_kg": repr(breakdown_a.inner_tube_kg),
        "outer_pipe_kg": repr(breakdown_a.outer_pipe_kg),
        "total_kg": repr(breakdown_a.total_kg),
    }
    assert breakdown_a.calculation_hash == canonical_sha256(manual_payload)


def test_breakdown_to_dict_is_json_serializable() -> None:
    """§10.1: every MassBreakdown is JSON-serializable via documented schema."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
    )
    breakdown = calculate_mass_breakdown(request)
    serialized = json.dumps(breakdown.to_dict(), sort_keys=True)
    parsed = json.loads(serialized)
    assert parsed["calculation_hash"] == breakdown.calculation_hash


# ----------------- Tests: §8 provenance -----------------


def test_provenance_carries_all_eight_required_fields_plus_result_hash() -> None:
    """§8: 8 minimum fields + result_hash = 9 total."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
    )
    breakdown = calculate_mass_breakdown(request)
    provenance_dict = breakdown.provenance.to_dict()
    expected_fields = {
        "geometry_record_id",
        "material_record_id",
        "applicable_standard_id",
        "design_pressure_mpa",
        "design_temperature_c",
        "correlation_ids",
        "software_version",
        "git_commit",
        "result_hash",
    }
    assert set(provenance_dict.keys()) == expected_fields
    assert breakdown.provenance.git_commit == FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA
    assert breakdown.provenance.geometry_record_id == tube_record.geometry_id


def test_provenance_correlation_ids_is_empty_for_mass() -> None:
    """§8: correlation_ids is empty list for mass."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
    )
    breakdown = calculate_mass_breakdown(request)
    assert breakdown.provenance.correlation_ids == ()


# ----------------- Tests: forbidden-scope guards -----------------


def _slice_b_source_text() -> str:
    module = importlib.import_module(_SLICE_B_CODE_PATH)
    source_path = module.__file__
    assert source_path is not None
    with open(source_path, encoding="utf-8") as fh:
        return fh.read()


def test_module_does_not_import_pressure_drop_correlations() -> None:
    """Guard: no pressure-drop correlation id appears in Slice B code path."""
    source = _slice_b_source_text()
    forbidden_tokens = [
        "pressure_drop",
        "PressureDrop",
        "dp_correlation",
        "dp_calculator",
        "friction_factor",
        "reynolds",
    ]
    for token in forbidden_tokens:
        assert token not in source, f"forbidden pressure-drop token {token!r} found"


def test_module_does_not_import_cost_or_currency_code() -> None:
    """Guard: no cost / currency code appears in Slice B code path."""
    source = _slice_b_source_text()
    forbidden_tokens = [
        "CAPEX",
        "OPEX",
        "currency",
        "USD",
        "EUR",
        "CNY",
        "cost_calculator",
        "life_cycle",
        "lifecycle",
    ]
    for token in forbidden_tokens:
        assert token not in source, f"forbidden cost token {token!r} found"


def test_module_does_not_emit_slice_c_d_or_closeout_behavior() -> None:
    """Guard: Slice B must not implement Slice C / D / Closeout behavior."""
    source = _slice_b_source_text()
    forbidden_tokens = [
        "hoop_stress",
        "allowable_stress_check",
        "minimum_wall_check",
        "straight_pipe_span_check",
        "PreliminaryMechanicalChecker",
        "ALLOWABLE_STRESS_EXCEEDED",
        "MINIMUM_WALL_VIOLATED",
        "UNSUPPORTED_SPAN_EXCEEDED",
        "BLOCKED_FOR_DETAILED_DESIGN",
        "MECHANICAL_CHECK_UNSUPPORTED_ROLE",
    ]
    for token in forbidden_tokens:
        assert token not in source, f"forbidden Slice C/D token {token!r} found"


def test_module_does_not_mutate_geometry_catalog_or_material_records() -> None:
    """Guard: Slice B never mutates TASK-016 / TASK-013 inputs."""
    source = _slice_b_source_text()
    forbidden_mutations = [
        ".records.append",
        ".records.pop",
        ".records.remove",
        ".records[0] =",
        ".records[1] =",
        "property_values.append",
        "property_values.pop",
        "property_values.remove",
    ]
    for token in forbidden_mutations:
        assert token not in source, f"forbidden mutation token {token!r} found"


def test_module_does_not_depend_on_github_actions_or_ci() -> None:
    """Guard: Slice B code path is free of CI / GitHub coupling."""
    source = _slice_b_source_text()
    forbidden_tokens = [
        "github",
        "GITHUB_",
        "actions/",
        "workflow",
        ".github",
    ]
    for token in forbidden_tokens:
        assert token not in source, f"forbidden CI token {token!r} found"


# ----------------- Tests: dataclass shape -----------------


def test_mass_breakdown_dataclass_is_frozen() -> None:
    """MassBreakdown is a frozen dataclass (immutability)."""
    import dataclasses

    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
    )
    breakdown = calculate_mass_breakdown(request)
    # A frozen dataclass raises FrozenInstanceError on assignment.
    assert dataclasses.is_dataclass(breakdown) is True
    with pytest.raises(dataclasses.FrozenInstanceError):
        breakdown.total_kg = 999.0  # type: ignore[misc]


def test_mass_provenance_carries_nine_fields() -> None:
    """MassProvenance carries the 9 §8 fields and supports to_dict()."""
    provenance = MassProvenance(
        geometry_record_id="geom:test",
        material_record_id="mat:test",
        applicable_standard_id="ASME B31.3",
        design_pressure_mpa=5.0,
        design_temperature_c=200.0,
        correlation_ids=(),
        software_version="0.1.0",
        git_commit=FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA,
        result_hash="0" * 64,
    )
    payload = provenance.to_dict()
    assert payload["geometry_record_id"] == "geom:test"
    assert payload["git_commit"] == FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA


def test_mass_calculation_request_default_values() -> None:
    """MassCalculationRequest has safe defaults for optional fields."""
    tube_record = _make_tube_record()
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role={},
    )
    assert request.fitting_overrides_kg == ()
    assert request.include_hairpin is False
    assert request.fitting_density_normalization is True


def test_mass_breakdown_is_dataclass_instance() -> None:
    """MassBreakdown is a properly constructed dataclass instance."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
    )
    breakdown = calculate_mass_breakdown(request)
    assert isinstance(breakdown, MassBreakdown)
    assert isinstance(breakdown.provenance, MassProvenance)


def test_mass_breakdown_to_dict_keys_are_stable() -> None:
    """§10: to_dict() keys are deterministic across calls."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
    )
    breakdown = calculate_mass_breakdown(request)
    keys_a = sorted(breakdown.to_dict().keys())
    keys_b = sorted(breakdown.to_dict().keys())
    assert keys_a == keys_b
    expected = sorted(
        [
            "calculation_hash",
            "fittings_kg",
            "hairpin_bend_kg",
            "inner_tube_kg",
            "outer_pipe_kg",
            "provenance",
            "total_kg",
        ]
    )
    assert keys_a == expected


# ----------------- Tests: result_hash determinism -----------------


def test_result_hash_is_64_char_sha256_hex() -> None:
    """§8 / §10: provenance.result_hash is 64-char lowercase hex SHA-256."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
    )
    breakdown = calculate_mass_breakdown(request)
    result_hash = breakdown.provenance.result_hash
    assert isinstance(result_hash, str)
    assert len(result_hash) == 64
    int(result_hash, 16)


def test_result_hash_changes_when_input_changes() -> None:
    """Boundary: changing any input mass changes the result_hash."""
    tube_record_a = _make_tube_record(geometry_id="tube:a")
    tube_record_b = _make_tube_record(geometry_id="tube:b")
    resolutions = _four_role_resolutions()
    request_a = MassCalculationRequest(
        geometry_record=tube_record_a,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
    )
    request_b = MassCalculationRequest(
        geometry_record=tube_record_b,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
    )
    breakdown_a = calculate_mass_breakdown(request_a)
    breakdown_b = calculate_mass_breakdown(request_b)
    assert breakdown_a.provenance.result_hash != breakdown_b.provenance.result_hash


# ----------------- Tests: total_kg consistency -----------------


def test_total_kg_equals_sum_of_component_masses() -> None:
    """§5.2.2: total_kg = sum of the four component masses."""
    tube_record = _make_tube_record()
    resolutions = _four_role_resolutions(density_value_si="7850")
    request = MassCalculationRequest(
        geometry_record=tube_record,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
        fitting_overrides_kg=(1.0, 2.0),
    )
    breakdown = calculate_mass_breakdown(request)
    expected_total = (
        breakdown.inner_tube_kg
        + breakdown.outer_pipe_kg
        + breakdown.hairpin_bend_kg
        + breakdown.fittings_kg
    )
    assert breakdown.total_kg == pytest.approx(expected_total, rel=1e-6)


def test_calculation_hash_is_deterministic_across_two_invocations_with_hairpin() -> None:
    """§11.4: hairpin path also produces deterministic hashes."""
    tube_record = _make_tube_record()
    hairpin = _make_hairpin_record(tube_geometry_id=tube_record.geometry_id)
    catalog = _make_catalog(tube_record, hairpin)
    resolutions = _four_role_resolutions()
    request = MassCalculationRequest(
        geometry_record=hairpin,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
        include_hairpin=True,
    )
    breakdown_a = calculate_mass_breakdown(request, catalog=catalog)
    breakdown_b = calculate_mass_breakdown(request, catalog=catalog)
    assert breakdown_a.calculation_hash == breakdown_b.calculation_hash
    assert breakdown_a.hairpin_bend_kg > 0.0


def test_hairpin_density_missing_raises_governance_incomplete() -> None:
    """§7 MATERIAL_GOVERNANCE_INCOMPLETE: hairpin role density missing."""
    tube_record = _make_tube_record()
    hairpin = _make_hairpin_record(tube_geometry_id=tube_record.geometry_id)
    catalog = _make_catalog(tube_record, hairpin)
    # Build resolutions with no density for any role.
    resolutions = _four_role_resolutions(include_density=False)
    request = MassCalculationRequest(
        geometry_record=hairpin,
        effective_length_m=DEFAULT_LENGTH_M,
        material_resolutions_by_component_role=resolutions,
        include_hairpin=True,
    )
    with pytest.raises(MaterialSelectorError) as excinfo:
        calculate_mass_breakdown(request, catalog=catalog)
    assert excinfo.value.code == ERROR_MATERIAL_GOVERNANCE_INCOMPLETE
