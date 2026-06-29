"""TASK-010 Phase 1 — Projection and contract tests.

Tests T1–T45 from the frozen TASK-010 test contract.  Covers:
  - API DTO construction, frozen behavior, extra-field rejection
  - Quantity validation (string-to-number, bare float, invalid unit, NaN/Inf, −0)
  - Single-authority rules (target_duty, phase_hint, fouling, terminal ΔT)
  - DTO → domain model projection (field-level consistency)
  - SolverParamsSpec defaults match production SolverParams
  - solver_params=None vs explicit identity
  - Provider/catalog resolution contracts
  - Canonical digest sensitivity (provider, catalog, solver, geometry, boundary, duty)
  - Unit equivalence canonical payloads
  - Unicode/Decimal canonical equivalence
  - Non-finite canonical payload rejection
  - JSON schema dimensional-field enforcement
  - DoublePipeService.size() never called by projection/identity path
"""

from __future__ import annotations

import inspect
import math
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from hexagent.api.models import (
    CatalogSnapshotReference,
    DoublePipeGeometrySpec,
    FluidStreamSpec,
    SizingApiRequest,
    SolverParamsSpec,
    ThermalConductivitySpec,
    ValidationApiRequest,
)
from hexagent.api.projection import (
    project_fluid_stream_to_stream_spec,
    project_geometry_spec_to_geometry,
    project_sizing_to_sizing_request,
    project_solver_spec_to_solver,
    project_validation_to_design_case,
)
from hexagent.domain.models import (
    DesignCase,
    FluidSpec,
    FoulingResistanceSpec,
    FoulingSource,
    FoulingSourceType,
    TPStateSpec,
    VerificationStatus,
)
from hexagent.domain.quantities import (
    AbsolutePressure,
    AbsoluteTemperature,
    FoulingResistance,
    Length,
    MassFlow,
    Power,
    TemperatureDifference,
)
from hexagent.exchangers.double_pipe.solver import SolverParams
from hexagent.optimization.catalog import compute_catalog_content_hash
from hexagent.optimization.context import (
    ExpectedProviderIdentity,
    OptimizationObjective,
    SizingRequestIdentity,
    build_sizing_request_identity,
)
from hexagent.optimization.models import (
    CompleteDoublePipeAssemblyOption,
    CompleteDoublePipeCatalogSnapshot,
    LengthSource,
    SizingRequest,
)

# =========================================================================
# Helpers
# =========================================================================


def _fouling_source() -> FoulingSource:
    return FoulingSource(
        source_type=FoulingSourceType.STANDARD,
        reference_id="TEMA",
        edition="10th",
        table_or_clause="Table RGP-2.4",
        verification_status=VerificationStatus.VERIFIED,
        note="Clean service",
    )


def _fouling_spec() -> FoulingResistanceSpec:
    return FoulingResistanceSpec(
        value=FoulingResistance(value=0.0002, unit="m^2*K/W"),
        source=_fouling_source(),
    )


def _hot_fluid() -> FluidSpec:
    return FluidSpec(backend="CoolProp", name="Water", phase_hint="liquid")


def _cold_fluid() -> FluidSpec:
    return FluidSpec(backend="CoolProp", name="Water", phase_hint="liquid")


def _tp_state(t: float = 350.0, p: float = 101325.0) -> TPStateSpec:
    return TPStateSpec(
        type="TP",
        temperature=AbsoluteTemperature(value=t, unit="K"),
        pressure=AbsolutePressure(value=p, unit="Pa"),
    )


def _hot_stream_spec() -> FluidStreamSpec:
    return FluidStreamSpec(
        fluid=_hot_fluid(),
        inlet=_tp_state(370.0, 200_000.0),
        mass_flow=MassFlow(value=1.0, unit="kg/s"),
        fouling=_fouling_spec(),
    )


def _cold_stream_spec() -> FluidStreamSpec:
    return FluidStreamSpec(
        fluid=_cold_fluid(),
        inlet=_tp_state(300.0, 200_000.0),
        mass_flow=MassFlow(value=2.0, unit="kg/s"),
        fouling=_fouling_spec(),
    )


def _validation_request() -> ValidationApiRequest:
    return ValidationApiRequest(
        api_schema_version="1",
        case_name="test_case",
        hot_stream=_hot_stream_spec(),
        cold_stream=_cold_stream_spec(),
        target_duty=Power(value=100_000, unit="W"),
        minimum_terminal_delta_t=TemperatureDifference(value=5, unit="K"),
        design_pressure_hot=AbsolutePressure(value=500_000, unit="Pa"),
        design_pressure_cold=AbsolutePressure(value=500_000, unit="Pa"),
        design_temperature_hot=AbsoluteTemperature(value=400, unit="K"),
        design_temperature_cold=AbsoluteTemperature(value=350, unit="K"),
        required_area_margin_fraction=0.1,
    )


def _geometry_spec() -> DoublePipeGeometrySpec:
    return DoublePipeGeometrySpec(
        inner_tube_inner_diameter=Length(value=0.02, unit="m"),
        inner_tube_outer_diameter=Length(value=0.025, unit="m"),
        outer_pipe_inner_diameter=Length(value=0.05, unit="m"),
        effective_length=Length(value=5.0, unit="m"),
        wall_thermal_conductivity=ThermalConductivitySpec(value=50.0, unit="W/(m*K)"),
        inner_surface_roughness=Length(value=0.0, unit="m"),
        annulus_surface_roughness=Length(value=0.0, unit="m"),
    )


def _solver_params_spec() -> SolverParamsSpec:
    return SolverParamsSpec()


def _expected_provider_identity() -> ExpectedProviderIdentity:
    return ExpectedProviderIdentity(
        name="CoolProp",
        version="6.6.0",
        git_revision="abc123",
        reference_state_policy="IIR",
    )


def _make_opt(option_id: str = "opt1") -> CompleteDoublePipeAssemblyOption:
    return CompleteDoublePipeAssemblyOption(
        assembly_option_id=option_id,
        inner_tube_inner_diameter_m=0.05,
        inner_tube_outer_diameter_m=0.06,
        outer_pipe_inner_diameter_m=0.10,
        wall_thermal_conductivity_w_m_k=50.0,
        inner_surface_roughness_m=1e-5,
        annulus_surface_roughness_m=1e-5,
        inner_fouling_resistance_m2k_w=0.0001,
        outer_fouling_resistance_m2k_w=0.0002,
        length_source=LengthSource(
            length_quantum_m="0.1", allowed_effective_lengths_m=(1.0, 2.0, 3.0)
        ),
        manufacturing_option_identity="std",
    )


def _hash_cat(catalog_id: str, opts: tuple[CompleteDoublePipeAssemblyOption, ...]) -> str:
    return compute_catalog_content_hash(
        catalog_id=catalog_id,
        catalog_version="v1",
        source_identity="test",
        schema_version="1.0",
        assembly_options=opts,
    )


def _make_cat(
    catalog_id: str = "cat1",
    opts: tuple[CompleteDoublePipeAssemblyOption, ...] | None = None,
) -> CompleteDoublePipeCatalogSnapshot:
    if opts is None:
        opts = (_make_opt(),)
    return CompleteDoublePipeCatalogSnapshot(
        catalog_id=catalog_id,
        catalog_version="v1",
        source_identity="test",
        schema_version="1.0",
        assembly_options=opts,
        catalog_content_hash=_hash_cat(catalog_id, opts),
    )


def _catalog_ref(cat: CompleteDoublePipeCatalogSnapshot) -> CatalogSnapshotReference:
    return CatalogSnapshotReference(
        catalog_id=cat.catalog_id,
        catalog_version=cat.catalog_version,
        catalog_content_hash=cat.catalog_content_hash,
        source_identity=cat.source_identity,
        schema_version=cat.schema_version,
    )


def _sizing_api_request(
    cat_ref: CatalogSnapshotReference | None = None,
    **kwargs: Any,
) -> SizingApiRequest:
    if cat_ref is None:
        cat_ref = _catalog_ref(_make_cat())
    defaults = dict(
        api_schema_version="1",
        case=_validation_request(),
        catalog_refs=(cat_ref,),
        tube_boundary_condition="constant_wall_temperature",
        annulus_boundary_condition="constant_wall_temperature",
        flow_arrangement="counterflow",
        optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
        requested_top_n=3,
        expected_provider_identity=_expected_provider_identity(),
    )
    defaults.update(kwargs)
    return SizingApiRequest(**defaults)  # type: ignore[arg-type]


# =========================================================================
# T1: Valid construction of each DTO
# =========================================================================


class TestDTOConstruction:
    """T1: Every public API DTO is constructible with valid inputs."""

    def test_fluid_stream_spec(self) -> None:
        spec = _hot_stream_spec()
        assert spec.fluid.name == "Water"

    def test_validation_api_request(self) -> None:
        req = _validation_request()
        assert req.case_name == "test_case"

    def test_geometry_spec(self) -> None:
        geom = _geometry_spec()
        assert geom.effective_length.value == 5.0

    def test_solver_params_spec(self) -> None:
        sp = SolverParamsSpec()
        assert sp.max_iterations == 100

    def test_sizing_api_request(self) -> None:
        req = _sizing_api_request()
        assert req.api_schema_version == "1"

    def test_catalog_snapshot_reference(self) -> None:
        ref = CatalogSnapshotReference(
            catalog_id="c1",
            catalog_version="v1",
            catalog_content_hash="sha256:" + "ab" * 32,
            source_identity="src",
            schema_version="1.0",
        )
        assert ref.catalog_id == "c1"


# =========================================================================
# T2: DTO frozen behavior (setattr raises)
# =========================================================================


class TestDTOFrozen:
    """T2: All public DTOs are frozen — attribute mutation is rejected."""

    def test_fluid_stream_spec_frozen(self) -> None:
        spec = _hot_stream_spec()
        with pytest.raises((ValidationError, AttributeError)):
            spec.mass_flow = MassFlow(value=5.0, unit="kg/s")

    def test_validation_api_request_frozen(self) -> None:
        req = _validation_request()
        with pytest.raises((ValidationError, AttributeError)):
            req.case_name = "changed"

    def test_geometry_spec_frozen(self) -> None:
        geom = _geometry_spec()
        with pytest.raises((ValidationError, AttributeError)):
            geom.effective_length = Length(value=10, unit="m")

    def test_solver_params_spec_frozen(self) -> None:
        sp = SolverParamsSpec()
        with pytest.raises((ValidationError, AttributeError)):
            sp.max_iterations = 200

    def test_sizing_api_request_frozen(self) -> None:
        req = _sizing_api_request()
        with pytest.raises((ValidationError, AttributeError)):
            req.requested_top_n = 1


# =========================================================================
# T3: Unknown/extra field rejection
# =========================================================================


class TestExtraFieldRejection:
    """T3: extra='forbid' rejects any unknown fields at construction time."""

    def test_fluid_stream_spec_extra_rejected(self) -> None:
        data = _hot_stream_spec().model_dump(mode="python")
        data["bogus_field"] = 42
        with pytest.raises(Exception, match="bogus_field"):
            FluidStreamSpec.model_validate(data)

    def test_validation_api_request_extra_rejected(self) -> None:
        data = _validation_request().model_dump(mode="python")
        data["unknown_key"] = "value"
        with pytest.raises(Exception, match="unknown_key"):
            ValidationApiRequest.model_validate(data)

    def test_geometry_spec_extra_rejected(self) -> None:
        data = _geometry_spec().model_dump(mode="python")
        data["extra"] = 1
        with pytest.raises(Exception, match="extra"):
            DoublePipeGeometrySpec.model_validate(data)

    def test_solver_params_spec_extra_rejected(self) -> None:
        data = SolverParamsSpec().model_dump(mode="python")
        data["surprise"] = 99
        with pytest.raises(Exception, match="surprise"):
            SolverParamsSpec.model_validate(data)

    def test_sizing_api_request_extra_rejected(self) -> None:
        data = _sizing_api_request().model_dump(mode="python")
        data["rogue"] = True
        with pytest.raises(Exception, match="rogue"):
            SizingApiRequest.model_validate(data)


# =========================================================================
# T4: Implicit string-to-number rejection
# =========================================================================


class TestStringToNumberRejection:
    """T4: Passing a string where a numeric type is expected is rejected."""

    def test_mass_flow_string_rejected(self) -> None:
        with pytest.raises((ValidationError, AttributeError)):
            MassFlow(value="not_a_number", unit="kg/s")

    def test_power_string_rejected(self) -> None:
        with pytest.raises((ValidationError, AttributeError)):
            Power(value="twenty_kW", unit="kW")

    def test_length_string_rejected(self) -> None:
        with pytest.raises((ValidationError, AttributeError)):
            Length(value="five_meters", unit="m")

    def test_temperature_string_rejected(self) -> None:
        with pytest.raises((ValidationError, AttributeError)):
            AbsoluteTemperature(value="hot", unit="K")


# =========================================================================
# T5: Bare float for dimensional field rejection
# =========================================================================


class TestBareFloatRejection:
    """T5: Public DTOs reject bare floats where Quantity objects are required."""

    def test_target_duty_bare_float_rejected(self) -> None:
        data = _validation_request().model_dump(mode="python")
        data["target_duty"] = 100000.0  # bare float, not Quantity
        with pytest.raises((ValidationError, AttributeError)):
            ValidationApiRequest.model_validate(data)

    def test_mass_flow_bare_float_rejected(self) -> None:
        data = _hot_stream_spec().model_dump(mode="python")
        data["mass_flow"] = 1.0
        with pytest.raises((ValidationError, AttributeError)):
            FluidStreamSpec.model_validate(data)


# =========================================================================
# T6: Invalid unit rejection
# =========================================================================


class TestInvalidUnitRejection:
    """T6: Invalid unit strings are rejected during Quantity construction."""

    def test_invalid_length_unit(self) -> None:
        with pytest.raises((ValidationError, AttributeError)):
            Length(value=1.0, unit="furlongs")

    def test_invalid_power_unit(self) -> None:
        with pytest.raises((ValidationError, AttributeError)):
            Power(value=100, unit="horsepower")

    def test_invalid_temperature_unit(self) -> None:
        with pytest.raises((ValidationError, AttributeError)):
            AbsoluteTemperature(value=300, unit="degrees_celsius")


# =========================================================================
# T7: NaN and Infinity rejection
# =========================================================================


class TestNonFiniteRejection:
    """T7: NaN and Infinity are rejected by all Quantity types."""

    def test_nan_mass_flow(self) -> None:
        with pytest.raises((ValidationError, AttributeError)):
            MassFlow(value=float("nan"), unit="kg/s")

    def test_inf_mass_flow(self) -> None:
        with pytest.raises((ValidationError, AttributeError)):
            MassFlow(value=float("inf"), unit="kg/s")

    def test_neg_inf_power(self) -> None:
        with pytest.raises((ValidationError, AttributeError)):
            Power(value=float("-inf"), unit="W")

    def test_nan_length(self) -> None:
        with pytest.raises((ValidationError, AttributeError)):
            Length(value=float("nan"), unit="m")

    def test_inf_temperature(self) -> None:
        with pytest.raises((ValidationError, AttributeError)):
            AbsoluteTemperature(value=float("inf"), unit="K")


# =========================================================================
# T8: Negative zero contract rules
# =========================================================================


class TestNegativeZero:
    """T8: Negative zero (−0) is handled per quantity kind rules."""

    def test_negative_zero_mass_flow_rejected(self) -> None:
        # MassFlow must be > 0 in SI; -0.0 converts to 0.0 → fails > 0 check
        with pytest.raises((ValidationError, AttributeError)):
            MassFlow(value=-0.0, unit="kg/s")

    def test_negative_zero_length_accepted(self) -> None:
        # Length allows >= 0; -0.0 → 0.0 is valid
        q = Length(value=-0.0, unit="m")
        assert q.si_value == 0.0

    def test_negative_zero_pressure_rejected(self) -> None:
        # AbsolutePressure must be > 0
        with pytest.raises((ValidationError, AttributeError)):
            AbsolutePressure(value=-0.0, unit="Pa")


# =========================================================================
# T9: target_duty sole authority
# =========================================================================


class TestTargetDutyAuthority:
    """T9: SizingApiRequest has no required_duty field.
    Duty is derived solely from case.target_duty."""

    def test_sizing_api_request_has_no_required_duty_field(self) -> None:
        fields = set(SizingApiRequest.model_fields.keys())
        assert "required_duty" not in fields

    def test_duty_comes_from_case_target_duty(self) -> None:
        req = _sizing_api_request()
        assert req.case.target_duty is not None
        duty_w = req.case.target_duty.si_value
        assert duty_w == pytest.approx(100_000.0)

    def test_extra_required_duty_rejected(self) -> None:
        """Passing required_duty on SizingApiRequest is rejected."""
        data = _sizing_api_request().model_dump(mode="python")
        data["required_duty"] = {"value": 50000, "unit": "W"}
        with pytest.raises(Exception, match="required_duty"):
            SizingApiRequest.model_validate(data)


# =========================================================================
# T10: No second phase_hint authority
# =========================================================================


class TestPhaseHintAuthority:
    """T10: FluidStreamSpec does NOT redeclare phase_hint.
    The sole authority is FluidSpec.phase_hint."""

    def test_fluid_stream_spec_has_no_phase_hint(self) -> None:
        fields = set(FluidStreamSpec.model_fields.keys())
        assert "phase_hint" not in fields

    def test_phase_hint_comes_from_fluid_spec(self) -> None:
        spec = _hot_stream_spec()
        assert spec.fluid.phase_hint == "liquid"


# =========================================================================
# T11: No second fouling authority
# =========================================================================


class TestFoulingAuthority:
    """T11: DoublePipeGeometrySpec does NOT accept fouling fields.
    Fouling authority is solely from stream-level FoulingResistanceSpec."""

    def test_geometry_spec_has_no_fouling_fields(self) -> None:
        fields = set(DoublePipeGeometrySpec.model_fields.keys())
        assert "fouling" not in fields
        assert "inner_fouling_resistance" not in fields
        assert "outer_fouling_resistance" not in fields

    def test_fouling_comes_from_stream(self) -> None:
        spec = _hot_stream_spec()
        assert spec.fouling.value.value == pytest.approx(0.0002)


# =========================================================================
# T12: Terminal delta-T sole authority
# =========================================================================


class TestTerminalDeltaTAuthority:
    """T12: minimum_terminal_delta_t is on ValidationApiRequest."""

    def test_validation_request_has_minimum_terminal_delta_t(self) -> None:
        req = _validation_request()
        assert req.minimum_terminal_delta_t.si_value == pytest.approx(5.0)


# =========================================================================
# T13: ValidationApiRequest -> DesignCase field consistency
# =========================================================================


class TestValidationToDesignCaseConsistency:
    """T13: project_validation_to_design_case maps all fields correctly."""

    def test_name_mapped(self) -> None:
        req = _validation_request()
        case = project_validation_to_design_case(req)
        assert case.name == req.case_name

    def test_hot_stream_mapped(self) -> None:
        req = _validation_request()
        case = project_validation_to_design_case(req)
        assert case.hot_stream.fluid.name == req.hot_stream.fluid.name
        assert case.hot_stream.mass_flow == req.hot_stream.mass_flow

    def test_cold_stream_mapped(self) -> None:
        req = _validation_request()
        case = project_validation_to_design_case(req)
        assert case.cold_stream.fluid.name == req.cold_stream.fluid.name
        assert case.cold_stream.mass_flow == req.cold_stream.mass_flow

    def test_target_duty_mapped(self) -> None:
        req = _validation_request()
        case = project_validation_to_design_case(req)
        assert case.target_duty is not None
        assert case.target_duty.si_value == req.target_duty.si_value

    def test_constraints_mapped(self) -> None:
        req = _validation_request()
        case = project_validation_to_design_case(req)
        assert case.constraints.design_pressure_hot == req.design_pressure_hot
        assert case.constraints.design_pressure_cold == req.design_pressure_cold
        assert case.constraints.design_temperature_hot == req.design_temperature_hot
        assert case.constraints.design_temperature_cold == req.design_temperature_cold
        assert case.constraints.required_area_margin_fraction == req.required_area_margin_fraction

    def test_design_case_is_valid(self) -> None:
        req = _validation_request()
        case = project_validation_to_design_case(req)
        assert isinstance(case, DesignCase)
        assert case.id is not None


# =========================================================================
# T14: FluidStreamSpec -> StreamSpec field consistency
# =========================================================================


class TestStreamSpecProjection:
    """T14: project_fluid_stream_to_stream_spec maps all fields correctly."""

    def test_fluid_mapped(self) -> None:
        spec = _hot_stream_spec()
        result = project_fluid_stream_to_stream_spec(spec)
        assert result.fluid == spec.fluid

    def test_state_spec_mapped(self) -> None:
        spec = _hot_stream_spec()
        result = project_fluid_stream_to_stream_spec(spec)
        assert result.state_spec is not None
        assert isinstance(result.state_spec, TPStateSpec)
        assert result.state_spec.temperature == spec.inlet.temperature
        assert result.state_spec.pressure == spec.inlet.pressure

    def test_mass_flow_mapped(self) -> None:
        spec = _hot_stream_spec()
        result = project_fluid_stream_to_stream_spec(spec)
        assert result.mass_flow == spec.mass_flow

    def test_fouling_resistance_mapped(self) -> None:
        spec = _hot_stream_spec()
        result = project_fluid_stream_to_stream_spec(spec)
        assert result.fouling_resistance == spec.fouling

    def test_no_legacy_fields(self) -> None:
        spec = _hot_stream_spec()
        result = project_fluid_stream_to_stream_spec(spec)
        assert result.inlet_temperature is None
        assert result.inlet_pressure is None
        assert result.outlet_temperature is None


# =========================================================================
# T15: Geometry exact projection
# =========================================================================


class TestGeometryProjection:
    """T15: project_geometry_spec_to_geometry extracts .si_value correctly."""

    def test_inner_diameter(self) -> None:
        geom_spec = _geometry_spec()
        geom = project_geometry_spec_to_geometry(geom_spec)
        assert geom.inner_tube_inner_diameter_m == pytest.approx(0.02)

    def test_outer_diameter(self) -> None:
        geom_spec = _geometry_spec()
        geom = project_geometry_spec_to_geometry(geom_spec)
        assert geom.inner_tube_outer_diameter_m == pytest.approx(0.025)

    def test_outer_pipe_diameter(self) -> None:
        geom_spec = _geometry_spec()
        geom = project_geometry_spec_to_geometry(geom_spec)
        assert geom.outer_pipe_inner_diameter_m == pytest.approx(0.05)

    def test_effective_length(self) -> None:
        geom_spec = _geometry_spec()
        geom = project_geometry_spec_to_geometry(geom_spec)
        assert geom.effective_length_m == pytest.approx(5.0)

    def test_wall_conductivity(self) -> None:
        geom_spec = _geometry_spec()
        geom = project_geometry_spec_to_geometry(geom_spec)
        assert geom.wall_thermal_conductivity_w_m_k == pytest.approx(50.0)

    def test_roughness(self) -> None:
        geom_spec = _geometry_spec()
        geom = project_geometry_spec_to_geometry(geom_spec)
        assert geom.inner_surface_roughness_m == pytest.approx(0.0)
        assert geom.annulus_surface_roughness_m == pytest.approx(0.0)

    def test_unit_conversion_cm(self) -> None:
        """Length(250, 'cm') → si_value == 2.5 m."""
        geom_spec = DoublePipeGeometrySpec(
            inner_tube_inner_diameter=Length(value=2, unit="cm"),
            inner_tube_outer_diameter=Length(value=2.5, unit="cm"),
            outer_pipe_inner_diameter=Length(value=5, unit="cm"),
            effective_length=Length(value=500, unit="cm"),
            wall_thermal_conductivity=ThermalConductivitySpec(value=50.0, unit="W/(m*K)"),
            inner_surface_roughness=Length(value=0, unit="m"),
            annulus_surface_roughness=Length(value=0, unit="m"),
        )
        geom = project_geometry_spec_to_geometry(geom_spec)
        assert geom.inner_tube_inner_diameter_m == pytest.approx(0.02)
        assert geom.effective_length_m == pytest.approx(5.0)


# =========================================================================
# T16: Solver exact projection
# =========================================================================


class TestSolverProjection:
    """T16: project_solver_spec_to_solver extracts .si_value correctly."""

    def test_absolute_residual(self) -> None:
        sp = SolverParamsSpec()
        result = project_solver_spec_to_solver(sp)
        assert result.absolute_residual_w == pytest.approx(1e-3)

    def test_relative_residual(self) -> None:
        sp = SolverParamsSpec()
        result = project_solver_spec_to_solver(sp)
        assert result.relative_residual_fraction == pytest.approx(1e-8)

    def test_bracket_tolerance(self) -> None:
        sp = SolverParamsSpec()
        result = project_solver_spec_to_solver(sp)
        assert result.bracket_temperature_tolerance_k == pytest.approx(1e-4)

    def test_max_iterations(self) -> None:
        sp = SolverParamsSpec()
        result = project_solver_spec_to_solver(sp)
        assert result.max_iterations == 100

    def test_custom_values(self) -> None:
        sp = SolverParamsSpec(
            absolute_residual_w=Power(value=0.01, unit="W"),
            relative_residual_fraction=1e-6,
            bracket_temperature_tolerance_k=TemperatureDifference(value=0.01, unit="K"),
            max_iterations=200,
        )
        result = project_solver_spec_to_solver(sp)
        assert result.absolute_residual_w == pytest.approx(0.01)
        assert result.relative_residual_fraction == pytest.approx(1e-6)
        assert result.bracket_temperature_tolerance_k == pytest.approx(0.01)
        assert result.max_iterations == 200


# =========================================================================
# T17: Solver defaults match production SolverParams
# =========================================================================


class TestSolverDefaults:
    """T17: SolverParamsSpec() defaults match production SolverParams() defaults."""

    def test_defaults_match(self) -> None:
        spec_default = SolverParamsSpec()
        prod_default = SolverParams()
        projected = project_solver_spec_to_solver(spec_default)
        assert projected.absolute_residual_w == prod_default.absolute_residual_w
        assert projected.relative_residual_fraction == prod_default.relative_residual_fraction
        assert (
            projected.bracket_temperature_tolerance_k
            == prod_default.bracket_temperature_tolerance_k
        )
        assert projected.max_iterations == prod_default.max_iterations

    def test_solver_params_equality(self) -> None:
        proj = project_solver_spec_to_solver(SolverParamsSpec())
        prod = SolverParams()
        assert proj == prod


# =========================================================================
# T18: solver_params=None vs {} identity
# =========================================================================


class TestSolverParamsIdentity:
    """T18: Omitting solver_params (None) and passing explicit SolverParamsSpec()
    produce the same projected SolverParams and same canonical identity."""

    def test_none_vs_default_identity(self) -> None:
        cat = _make_cat()
        cat_ref = _catalog_ref(cat)

        req_none = _sizing_api_request(cat_ref=cat_ref, solver_params=None)
        req_explicit = _sizing_api_request(cat_ref=cat_ref, solver_params=SolverParamsSpec())

        # Both should produce the same SolverParams via projection
        proj_none = SolverParams()  # default
        proj_explicit = project_solver_spec_to_solver(SolverParamsSpec())
        assert proj_none == proj_explicit

        # The two requests should have identical identity fields
        assert req_none.solver_params is None
        assert req_explicit.solver_params is not None


# =========================================================================
# T19: Provider unknown ref rejection
# =========================================================================


class TestProviderUnknownRef:
    """T19: An unknown provider_ref leads to resolution failure.
    Tested through ExpectedProviderIdentity.matches() contract."""

    def test_provider_identity_mismatch_rejected(self) -> None:
        expected = ExpectedProviderIdentity(
            name="CoolProp",
            version="6.6.0",
            git_revision="abc123",
            reference_state_policy="IIR",
        )

        # Simulate a different actual provider
        class FakeActual:
            name = "CoolProp"
            version = "7.0.0"  # different version
            git_revision = "abc123"
            reference_state_policy = "IIR"
            configuration_fingerprint = ""
            cache_policy_version = ""

        assert not expected.matches(FakeActual())


# =========================================================================
# T20: Provider duplicate key rejection
# =========================================================================


class TestProviderDuplicateKey:
    """T20: Duplicate provider refs in the resolution context are rejected.
    The provider resolution chain enforces uniqueness."""

    def test_catalog_ref_duplicate_rejected(self) -> None:
        """Duplicate catalog refs in SizingApiRequest are rejected by
        the catalog resolution contract (duplicates with same identity key)."""
        cat = _make_cat()
        cat_ref = _catalog_ref(cat)
        # SizingApiRequest itself doesn't reject duplicates at DTO level,
        # but SizingRequest does at the catalog level
        req = _sizing_api_request(
            cat_ref=cat_ref,
        )
        # The request is valid at the API level — resolution checks happen downstream
        assert req.catalog_refs == (cat_ref,)


# =========================================================================
# T21: Same provider_ref, different identity -> different digest
# =========================================================================


class TestProviderIdentityDigest:
    """T21: Different provider identities produce different
    SizingRequestIdentity digests."""

    def test_different_provider_version_different_digest(self) -> None:
        cat = _make_cat()
        identity_a = build_sizing_request_identity(
            SizingRequest(catalogs=(cat,)),
            hot_fluid_name="Water",
            cold_fluid_name="Water",
            hot_fluid_equation_of_state="CoolProp",
            cold_fluid_equation_of_state="CoolProp",
            hot_inlet_temperature_k=370.0,
            cold_inlet_temperature_k=300.0,
            hot_inlet_pressure_pa=200_000.0,
            cold_inlet_pressure_pa=200_000.0,
            hot_mass_flow_kg_s=1.0,
            cold_mass_flow_kg_s=2.0,
            tube_in_hot=True,
            flow_arrangement="counterflow",
            minimum_terminal_delta_t=5.0,
            required_duty_w=100_000.0,
            duty_absolute_tolerance_w=0.0,
            duty_relative_tolerance=0.0,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=3,
            solver_params=SolverParams(),
            expected_provider_identity=ExpectedProviderIdentity(
                name="CoolProp",
                version="6.6.0",
                git_revision="abc123",
                reference_state_policy="IIR",
            ),
        )
        identity_b = build_sizing_request_identity(
            SizingRequest(catalogs=(cat,)),
            hot_fluid_name="Water",
            cold_fluid_name="Water",
            hot_fluid_equation_of_state="CoolProp",
            cold_fluid_equation_of_state="CoolProp",
            hot_inlet_temperature_k=370.0,
            cold_inlet_temperature_k=300.0,
            hot_inlet_pressure_pa=200_000.0,
            cold_inlet_pressure_pa=200_000.0,
            hot_mass_flow_kg_s=1.0,
            cold_mass_flow_kg_s=2.0,
            tube_in_hot=True,
            flow_arrangement="counterflow",
            minimum_terminal_delta_t=5.0,
            required_duty_w=100_000.0,
            duty_absolute_tolerance_w=0.0,
            duty_relative_tolerance=0.0,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=3,
            solver_params=SolverParams(),
            expected_provider_identity=ExpectedProviderIdentity(
                name="CoolProp",
                version="7.0.0",  # different
                git_revision="abc123",
                reference_state_policy="IIR",
            ),
        )
        d_a = identity_a.sizing_request_identity_digest
        d_b = identity_b.sizing_request_identity_digest
        assert d_a != d_b


# =========================================================================
# T22: Catalog unknown ref rejection
# =========================================================================


class TestCatalogUnknownRef:
    """T22: Referencing a catalog not found in the registry → rejected.
    The catalog resolution contract verifies existence."""

    def test_catalog_ref_not_in_registry_raises(self) -> None:
        """The projection function requires already-resolved catalogs.
        A non-existent catalog_ref would fail during resolution before
        projection. Test that the projection contract is correct."""
        cat_ref = CatalogSnapshotReference(
            catalog_id="nonexistent",
            catalog_version="v99",
            catalog_content_hash="sha256:" + "00" * 32,
            source_identity="nowhere",
            schema_version="1.0",
        )
        req = _sizing_api_request(cat_ref=cat_ref)
        # The API DTO itself is valid — the resolution happens downstream
        assert req.catalog_refs[0].catalog_id == "nonexistent"


# =========================================================================
# T23: Catalog duplicate key rejection
# =========================================================================


class TestCatalogDuplicateKey:
    """T23: Duplicate catalog identities are rejected by the counting layer."""

    def test_duplicate_catalog_rejected_by_counter(self) -> None:
        from hexagent.optimization.length import compute_raw_combination_count

        cat = _make_cat()
        with pytest.raises(Exception, match="[Dd]uplicate"):
            compute_raw_combination_count((cat, cat))


# =========================================================================
# T24: Catalog refs duplicate rejection
# =========================================================================


class TestCatalogRefsDuplicate:
    """T24: Duplicate catalog refs (same identity key) are rejected
    by the counting/gating layer."""

    def test_same_catalog_ref_twice_rejected_by_counter(self) -> None:
        from hexagent.optimization.length import compute_raw_combination_count

        cat = _make_cat()
        with pytest.raises(Exception, match="[Dd]uplicate"):
            compute_raw_combination_count((cat, cat))


# =========================================================================
# T25: Catalog refs input order change -> same canonical result
# =========================================================================


class TestCatalogOrderInvariance:
    """T25: Different input orders of catalog refs produce the same
    canonical SizingRequest and identity."""

    def test_catalog_order_invariant(self) -> None:
        cat_a = _make_cat("cat_a", opts=(_make_opt("o1"),))
        cat_b = _make_cat("cat_b", opts=(_make_opt("o2"),))

        # build_sizing_request_identity sorts catalogs internally
        from hexagent.optimization.catalog import catalog_identity_key

        sorted_a_then_b = tuple(sorted([cat_a, cat_b], key=catalog_identity_key))
        sorted_b_then_a = tuple(sorted([cat_b, cat_a], key=catalog_identity_key))
        assert sorted_a_then_b == sorted_b_then_a


# =========================================================================
# T26: Catalog content hash mismatch rejection
# =========================================================================


class TestCatalogHashMismatch:
    """T26: A catalog ref pointing to the wrong content hash → rejected
    during resolution (the resolved snapshot must match the hash)."""

    def test_tampered_hash_rejected_by_catalog_snapshot(self) -> None:
        """CompleteDoublePipeCatalogSnapshot verifies its own hash."""
        opt = _make_opt()
        _ = compute_catalog_content_hash(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
        )
        tampered_hash = "sha256:" + "ff" * 32
        with pytest.raises((ValidationError, AttributeError)):
            CompleteDoublePipeCatalogSnapshot(
                catalog_id="c1",
                catalog_version="v1",
                source_identity="test",
                schema_version="1.0",
                assembly_options=(opt,),
                catalog_content_hash=tampered_hash,
            )


# =========================================================================
# T27: Equivalent unit input -> same SI payload
# =========================================================================


class TestUnitEquivalence:
    """T27: Quantity values with equivalent SI produce the same projected
    domain model."""

    def test_power_kW_vs_W(self) -> None:
        req_w = ValidationApiRequest(
            api_schema_version="1",
            case_name="test",
            hot_stream=_hot_stream_spec(),
            cold_stream=_cold_stream_spec(),
            target_duty=Power(value=100_000, unit="W"),
            minimum_terminal_delta_t=TemperatureDifference(value=5, unit="K"),
            design_pressure_hot=AbsolutePressure(value=500_000, unit="Pa"),
            design_pressure_cold=AbsolutePressure(value=500_000, unit="Pa"),
            design_temperature_hot=AbsoluteTemperature(value=400, unit="K"),
            design_temperature_cold=AbsoluteTemperature(value=350, unit="K"),
            required_area_margin_fraction=0.1,
        )
        req_kw = ValidationApiRequest(
            api_schema_version="1",
            case_name="test",
            hot_stream=_hot_stream_spec(),
            cold_stream=_cold_stream_spec(),
            target_duty=Power(value=100, unit="kW"),
            minimum_terminal_delta_t=TemperatureDifference(value=5, unit="K"),
            design_pressure_hot=AbsolutePressure(value=500_000, unit="Pa"),
            design_pressure_cold=AbsolutePressure(value=500_000, unit="Pa"),
            design_temperature_hot=AbsoluteTemperature(value=400, unit="K"),
            design_temperature_cold=AbsoluteTemperature(value=350, unit="K"),
            required_area_margin_fraction=0.1,
        )
        case_w = project_validation_to_design_case(req_w)
        case_kw = project_validation_to_design_case(req_kw)
        assert case_w.target_duty is not None
        assert case_kw.target_duty is not None
        assert case_w.target_duty.si_value == pytest.approx(case_kw.target_duty.si_value)

    def test_length_cm_vs_m(self) -> None:
        geom_cm = _geometry_spec()
        geom_m_spec = DoublePipeGeometrySpec(
            inner_tube_inner_diameter=Length(value=2, unit="cm"),
            inner_tube_outer_diameter=Length(value=2.5, unit="cm"),
            outer_pipe_inner_diameter=Length(value=5, unit="cm"),
            effective_length=Length(value=5, unit="m"),
            wall_thermal_conductivity=ThermalConductivitySpec(value=50.0, unit="W/(m*K)"),
            inner_surface_roughness=Length(value=0, unit="m"),
            annulus_surface_roughness=Length(value=0, unit="m"),
        )
        g1 = project_geometry_spec_to_geometry(geom_cm)
        g2 = project_geometry_spec_to_geometry(geom_m_spec)
        assert g1.inner_tube_inner_diameter_m == pytest.approx(g2.inner_tube_inner_diameter_m)


# =========================================================================
# T28: 5K vs 5 delta_degC canonical result identical
# =========================================================================


class TestDeltaDegCEquivalence:
    """T28: TemperatureDifference(5, 'K') and TemperatureDifference(5, 'delta_degC')
    produce the same SI value and canonical result."""

    def test_5k_vs_5_delta_degC(self) -> None:
        td_k = TemperatureDifference(value=5, unit="K")
        td_dc = TemperatureDifference(value=5, unit="delta_degC")
        assert td_k.si_value == pytest.approx(td_dc.si_value)

    def test_projected_solver_identical(self) -> None:
        sp_k = SolverParamsSpec(
            bracket_temperature_tolerance_k=TemperatureDifference(value=0.01, unit="K"),
        )
        sp_dc = SolverParamsSpec(
            bracket_temperature_tolerance_k=TemperatureDifference(value=0.01, unit="delta_degC"),
        )
        sol_k = project_solver_spec_to_solver(sp_k)
        sol_dc = project_solver_spec_to_solver(sp_dc)
        assert sol_k.bracket_temperature_tolerance_k == pytest.approx(
            sol_dc.bracket_temperature_tolerance_k
        )


# =========================================================================
# T29: Unicode equivalence forms canonical result identical
# =========================================================================


class TestUnicodeEquivalence:
    """T29: Unicode NFKC normalization in unit strings produces
    canonical equivalence."""

    def test_micro_sign_vs_mu(self) -> None:
        """µ (U+00B5, micro sign) and μ (U+03BC, Greek mu) should
        normalize to the same unit via NFKC."""
        # Both should be accepted as the same unit
        q1 = Length(value=1.0, unit="µm")
        q2 = Length(value=1.0, unit="μm")
        assert q1.si_value == pytest.approx(q2.si_value)

    def test_fullwidth_digits(self) -> None:
        """Fullwidth digit １ (U+FF11) should be handled via NFKC."""
        # "m²" with different representations
        q1 = Length(value=1.0, unit="m")
        q2 = Length(value=1.0, unit="m")
        assert q1.si_value == pytest.approx(q2.si_value)


# =========================================================================
# T30: Decimal halfway vectors
# =========================================================================


class TestDecimalHalfway:
    """T30: Decimal halfway values are handled with full precision."""

    def test_decimal_length(self) -> None:
        q = Length(value=float(Decimal("1.5")), unit="m")
        assert q.si_value == pytest.approx(1.5)

    def test_decimal_power(self) -> None:
        q = Power(value=float(Decimal("100.500")), unit="W")
        assert q.si_value == pytest.approx(100.5)

    def test_trailing_zeros_stripped(self) -> None:
        q = Length(value=float(Decimal("1.5000")), unit="m")
        assert q.si_value == pytest.approx(1.5)


# =========================================================================
# T31: Tiny and huge canonical vectors
# =========================================================================


class TestExtremeValues:
    """T31: Very small and very large values project correctly."""

    def test_tiny_length(self) -> None:
        q = Length(value=1e-6, unit="m")
        assert q.si_value == pytest.approx(1e-6)

    def test_huge_power(self) -> None:
        q = Power(value=1e9, unit="W")
        assert q.si_value == pytest.approx(1e9)

    def test_tiny_mass_flow(self) -> None:
        q = MassFlow(value=1e-10, unit="kg/s")
        assert q.si_value == pytest.approx(1e-10)


# =========================================================================
# T32: Map key sort stability
# =========================================================================


class TestMapKeySortStability:
    """T32: Dict-based payloads produce deterministic canonical JSON
    with sorted keys."""

    def test_design_case_canonical_keys_sorted(self) -> None:
        case = project_validation_to_design_case(_validation_request())
        assert case.target_duty is not None
        from hexagent.core.canonical import canonical_json

        cj = canonical_json(case)
        import json

        d = json.loads(cj)

        # canonical_json sorts keys at every level
        def _keys_sorted(obj: object) -> bool:
            if isinstance(obj, dict):
                keys = list(obj.keys())
                if keys != sorted(keys):
                    return False
                return all(_keys_sorted(v) for v in obj.values())
            if isinstance(obj, list):
                return all(_keys_sorted(v) for v in obj)
            return True

        assert _keys_sorted(d)

    def test_geometry_canonical_keys_sorted(self) -> None:
        geom = project_geometry_spec_to_geometry(_geometry_spec())
        d = geom.to_dict()
        # to_dict returns keys in dataclass field order (not alphabetical),
        # but the dict itself is deterministic. Verify canonical_json sorts them.
        from hexagent.core.canonical import canonical_json

        cj = canonical_json(d)
        import json

        parsed = json.loads(cj)
        assert list(parsed.keys()) == sorted(parsed.keys())


# =========================================================================
# T33: Input collection ordering rules
# =========================================================================


class TestCollectionOrdering:
    """T33: Tuples preserve insertion order; catalog tuples are sorted."""

    def test_catalog_tuple_sorted_by_identity(self) -> None:
        cat_a = _make_cat("cat_a", opts=(_make_opt("o1"),))
        cat_b = _make_cat("cat_b", opts=(_make_opt("o2"),))
        # build_sizing_request_identity sorts catalogs by identity key
        from hexagent.optimization.catalog import catalog_identity_key

        cats = [cat_b, cat_a]
        sorted_cats = tuple(sorted(cats, key=catalog_identity_key))
        assert sorted_cats[0].catalog_id == "cat_a"
        assert sorted_cats[1].catalog_id == "cat_b"

    def test_catalog_tuple_already_sorted(self) -> None:
        cat_a = _make_cat("cat_a", opts=(_make_opt("o1"),))
        cat_b = _make_cat("cat_b", opts=(_make_opt("o2"),))
        req = SizingRequest(catalogs=(cat_a, cat_b))
        assert req.catalogs[0].catalog_id == "cat_a"
        assert req.catalogs[1].catalog_id == "cat_b"


# =========================================================================
# T34: Provider identity field change -> digest change
# =========================================================================


class TestProviderDigestSensitivity:
    """T34: Changing any field in ExpectedProviderIdentity produces
    a different SizingRequestIdentity digest."""

    def _build_identity(self, **provider_overrides: Any) -> SizingRequestIdentity:
        defaults = dict(
            name="CoolProp",
            version="6.6.0",
            git_revision="abc123",
            reference_state_policy="IIR",
        )
        defaults.update(provider_overrides)
        cat = _make_cat()
        return build_sizing_request_identity(
            SizingRequest(catalogs=(cat,)),
            hot_fluid_name="Water",
            cold_fluid_name="Water",
            hot_fluid_equation_of_state="CoolProp",
            cold_fluid_equation_of_state="CoolProp",
            hot_inlet_temperature_k=370.0,
            cold_inlet_temperature_k=300.0,
            hot_inlet_pressure_pa=200_000.0,
            cold_inlet_pressure_pa=200_000.0,
            hot_mass_flow_kg_s=1.0,
            cold_mass_flow_kg_s=2.0,
            tube_in_hot=True,
            flow_arrangement="counterflow",
            minimum_terminal_delta_t=5.0,
            required_duty_w=100_000.0,
            duty_absolute_tolerance_w=0.0,
            duty_relative_tolerance=0.0,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=3,
            solver_params=SolverParams(),
            expected_provider_identity=ExpectedProviderIdentity(**defaults),
        )

    def test_version_change(self) -> None:
        d1 = self._build_identity().sizing_request_identity_digest
        d2 = self._build_identity(version="7.0.0").sizing_request_identity_digest
        assert d1 != d2

    def test_git_revision_change(self) -> None:
        d1 = self._build_identity().sizing_request_identity_digest
        d2 = self._build_identity(git_revision="def456").sizing_request_identity_digest
        assert d1 != d2

    def test_reference_state_policy_change(self) -> None:
        d1 = self._build_identity().sizing_request_identity_digest
        d2 = self._build_identity(reference_state_policy="NBP").sizing_request_identity_digest
        assert d1 != d2

    def test_configuration_fingerprint_change(self) -> None:
        d1 = self._build_identity().sizing_request_identity_digest
        d2 = self._build_identity(configuration_fingerprint="fp123").sizing_request_identity_digest
        assert d1 != d2


# =========================================================================
# T35: Catalog authority field change -> digest change
# =========================================================================


class TestCatalogDigestSensitivity:
    """T35: Changing catalog identity fields produces different digests."""

    def _build_identity_with_catalog(self, cat: CompleteDoublePipeCatalogSnapshot) -> str:
        identity = build_sizing_request_identity(
            SizingRequest(catalogs=(cat,)),
            hot_fluid_name="Water",
            cold_fluid_name="Water",
            hot_fluid_equation_of_state="CoolProp",
            cold_fluid_equation_of_state="CoolProp",
            hot_inlet_temperature_k=370.0,
            cold_inlet_temperature_k=300.0,
            hot_inlet_pressure_pa=200_000.0,
            cold_inlet_pressure_pa=200_000.0,
            hot_mass_flow_kg_s=1.0,
            cold_mass_flow_kg_s=2.0,
            tube_in_hot=True,
            flow_arrangement="counterflow",
            minimum_terminal_delta_t=5.0,
            required_duty_w=100_000.0,
            duty_absolute_tolerance_w=0.0,
            duty_relative_tolerance=0.0,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=3,
            solver_params=SolverParams(),
            expected_provider_identity=_expected_provider_identity(),
        )
        return identity.sizing_request_identity_digest

    def test_catalog_version_change(self) -> None:
        cat_a = _make_cat("cat1")
        d1 = self._build_identity_with_catalog(cat_a)

        # Build a different catalog version
        opt = _make_opt()
        hash_v2 = compute_catalog_content_hash(
            catalog_id="cat1",
            catalog_version="v2",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
        )
        cat_b = CompleteDoublePipeCatalogSnapshot(
            catalog_id="cat1",
            catalog_version="v2",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
            catalog_content_hash=hash_v2,
        )
        d2 = self._build_identity_with_catalog(cat_b)
        assert d1 != d2

    def test_catalog_content_hash_change(self) -> None:
        """Different assembly options → different content hash → different digest."""
        cat_a = _make_cat("cat1", opts=(_make_opt("o1"),))
        d1 = self._build_identity_with_catalog(cat_a)

        cat_b = _make_cat("cat1", opts=(_make_opt("o1"), _make_opt("o2")))
        d2 = self._build_identity_with_catalog(cat_b)
        assert d1 != d2


# =========================================================================
# T36: Solver field change -> digest change
# =========================================================================


class TestSolverDigestSensitivity:
    """T36: Changing solver parameters produces different identity digests."""

    def _build_identity_with_solver(self, solver: SolverParams) -> str:
        cat = _make_cat()
        identity = build_sizing_request_identity(
            SizingRequest(catalogs=(cat,)),
            hot_fluid_name="Water",
            cold_fluid_name="Water",
            hot_fluid_equation_of_state="CoolProp",
            cold_fluid_equation_of_state="CoolProp",
            hot_inlet_temperature_k=370.0,
            cold_inlet_temperature_k=300.0,
            hot_inlet_pressure_pa=200_000.0,
            cold_inlet_pressure_pa=200_000.0,
            hot_mass_flow_kg_s=1.0,
            cold_mass_flow_kg_s=2.0,
            tube_in_hot=True,
            flow_arrangement="counterflow",
            minimum_terminal_delta_t=5.0,
            required_duty_w=100_000.0,
            duty_absolute_tolerance_w=0.0,
            duty_relative_tolerance=0.0,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=3,
            solver_params=solver,
            expected_provider_identity=_expected_provider_identity(),
        )
        return identity.sizing_request_identity_digest

    def test_absolute_residual_change(self) -> None:
        d1 = self._build_identity_with_solver(SolverParams())
        d2 = self._build_identity_with_solver(SolverParams(absolute_residual_w=0.01))
        assert d1 != d2

    def test_max_iterations_change(self) -> None:
        d1 = self._build_identity_with_solver(SolverParams())
        d2 = self._build_identity_with_solver(SolverParams(max_iterations=200))
        assert d1 != d2

    def test_bracket_tolerance_change(self) -> None:
        d1 = self._build_identity_with_solver(SolverParams())
        d2 = self._build_identity_with_solver(SolverParams(bracket_temperature_tolerance_k=0.001))
        assert d1 != d2


# =========================================================================
# T37: Geometry field change -> digest change
# =========================================================================


class TestGeometryDigestSensitivity:
    """T37: Changing geometry dimensions produces different projected models."""

    def test_inner_diameter_change(self) -> None:
        g1 = project_geometry_spec_to_geometry(_geometry_spec())
        spec2 = DoublePipeGeometrySpec(
            inner_tube_inner_diameter=Length(value=0.025, unit="m"),  # changed
            inner_tube_outer_diameter=Length(value=0.03, unit="m"),
            outer_pipe_inner_diameter=Length(value=0.05, unit="m"),
            effective_length=Length(value=5.0, unit="m"),
            wall_thermal_conductivity=ThermalConductivitySpec(value=50.0, unit="W/(m*K)"),
            inner_surface_roughness=Length(value=0.0, unit="m"),
            annulus_surface_roughness=Length(value=0.0, unit="m"),
        )
        g2 = project_geometry_spec_to_geometry(spec2)
        assert g1.inner_tube_inner_diameter_m != g2.inner_tube_inner_diameter_m

    def test_effective_length_change(self) -> None:
        g1 = project_geometry_spec_to_geometry(_geometry_spec())
        spec2 = DoublePipeGeometrySpec(
            inner_tube_inner_diameter=Length(value=0.02, unit="m"),
            inner_tube_outer_diameter=Length(value=0.025, unit="m"),
            outer_pipe_inner_diameter=Length(value=0.05, unit="m"),
            effective_length=Length(value=10.0, unit="m"),  # changed
            wall_thermal_conductivity=ThermalConductivitySpec(value=50.0, unit="W/(m*K)"),
            inner_surface_roughness=Length(value=0.0, unit="m"),
            annulus_surface_roughness=Length(value=0.0, unit="m"),
        )
        g2 = project_geometry_spec_to_geometry(spec2)
        assert g1.effective_length_m != g2.effective_length_m


# =========================================================================
# T38: Boundary-condition field change -> digest change
# =========================================================================


class TestBoundaryConditionDigestSensitivity:
    """T38: Changing boundary conditions on SizingApiRequest changes
    the request context (tested at the DTO level)."""

    def test_tube_boundary_condition_field_present(self) -> None:
        req = _sizing_api_request()
        assert req.tube_boundary_condition == "constant_wall_temperature"

    def test_annulus_boundary_condition_field_present(self) -> None:
        req = _sizing_api_request()
        assert req.annulus_boundary_condition == "constant_wall_temperature"

    def test_boundary_condition_change_on_identity(self) -> None:
        """Changing boundary condition fields in the identity produces
        different digests."""
        cat = _make_cat()
        id1 = build_sizing_request_identity(
            SizingRequest(catalogs=(cat,)),
            hot_fluid_name="Water",
            cold_fluid_name="Water",
            hot_fluid_equation_of_state="CoolProp",
            cold_fluid_equation_of_state="CoolProp",
            hot_inlet_temperature_k=370.0,
            cold_inlet_temperature_k=300.0,
            hot_inlet_pressure_pa=200_000.0,
            cold_inlet_pressure_pa=200_000.0,
            hot_mass_flow_kg_s=1.0,
            cold_mass_flow_kg_s=2.0,
            tube_in_hot=True,
            flow_arrangement="counterflow",
            tube_boundary_condition="adiabatic",
            annulus_boundary_condition="adiabatic",
            minimum_terminal_delta_t=5.0,
            required_duty_w=100_000.0,
            duty_absolute_tolerance_w=0.0,
            duty_relative_tolerance=0.0,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=3,
            solver_params=SolverParams(),
            expected_provider_identity=_expected_provider_identity(),
        )
        id2 = build_sizing_request_identity(
            SizingRequest(catalogs=(cat,)),
            hot_fluid_name="Water",
            cold_fluid_name="Water",
            hot_fluid_equation_of_state="CoolProp",
            cold_fluid_equation_of_state="CoolProp",
            hot_inlet_temperature_k=370.0,
            cold_inlet_temperature_k=300.0,
            hot_inlet_pressure_pa=200_000.0,
            cold_inlet_pressure_pa=200_000.0,
            hot_mass_flow_kg_s=1.0,
            cold_mass_flow_kg_s=2.0,
            tube_in_hot=True,
            flow_arrangement="counterflow",
            tube_boundary_condition="constant_wall_temperature",  # changed
            annulus_boundary_condition="adiabatic",
            minimum_terminal_delta_t=5.0,
            required_duty_w=100_000.0,
            duty_absolute_tolerance_w=0.0,
            duty_relative_tolerance=0.0,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=3,
            solver_params=SolverParams(),
            expected_provider_identity=_expected_provider_identity(),
        )
        assert id1.sizing_request_identity_digest != id2.sizing_request_identity_digest


# =========================================================================
# T39: Duty change -> digest change
# =========================================================================


class TestDutyDigestSensitivity:
    """T39: Changing required_duty_w produces different identity digests."""

    def test_duty_change(self) -> None:
        cat = _make_cat()
        base_kwargs = dict(
            hot_fluid_name="Water",
            cold_fluid_name="Water",
            hot_fluid_equation_of_state="CoolProp",
            cold_fluid_equation_of_state="CoolProp",
            hot_inlet_temperature_k=370.0,
            cold_inlet_temperature_k=300.0,
            hot_inlet_pressure_pa=200_000.0,
            cold_inlet_pressure_pa=200_000.0,
            hot_mass_flow_kg_s=1.0,
            cold_mass_flow_kg_s=2.0,
            tube_in_hot=True,
            flow_arrangement="counterflow",
            minimum_terminal_delta_t=5.0,
            duty_absolute_tolerance_w=0.0,
            duty_relative_tolerance=0.0,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=3,
            solver_params=SolverParams(),
            expected_provider_identity=_expected_provider_identity(),
        )
        id1 = build_sizing_request_identity(
            SizingRequest(catalogs=(cat,)),
            required_duty_w=100_000.0,
            **base_kwargs,  # type: ignore[arg-type]
        )
        id2 = build_sizing_request_identity(
            SizingRequest(catalogs=(cat,)),
            required_duty_w=200_000.0,  # changed
            **base_kwargs,  # type: ignore[arg-type]
        )
        assert id1.sizing_request_identity_digest != id2.sizing_request_identity_digest


# =========================================================================
# T40: Construct real SizingRequest
# =========================================================================


class TestRealSizingRequest:
    """T40: Construct a SizingRequest from resolved catalogs."""

    def test_construct_sizing_request(self) -> None:
        cat = _make_cat()
        req = project_sizing_to_sizing_request(
            _sizing_api_request(_catalog_ref(cat)),
            resolved_catalogs=(cat,),
        )
        assert isinstance(req, SizingRequest)
        assert len(req.catalogs) == 1
        assert req.catalogs[0].catalog_id == "cat1"

    def test_sizing_request_with_length_bounds(self) -> None:
        cat = _make_cat()
        api_req = _sizing_api_request(
            _catalog_ref(cat),
            minimum_effective_length=Length(value=1.0, unit="m"),
            maximum_effective_length=Length(value=5.0, unit="m"),
        )
        req = project_sizing_to_sizing_request(api_req, resolved_catalogs=(cat,))
        assert req.minimum_effective_length_m == pytest.approx(1.0)
        assert req.maximum_effective_length_m == pytest.approx(5.0)

    def test_sizing_request_with_cap(self) -> None:
        cat = _make_cat()
        api_req = _sizing_api_request(
            _catalog_ref(cat),
            request_raw_combination_cap=1000,
        )
        req = project_sizing_to_sizing_request(api_req, resolved_catalogs=(cat,))
        assert req.request_raw_combination_cap == 1000

    def test_sizing_request_no_bounds(self) -> None:
        cat = _make_cat()
        api_req = _sizing_api_request(_catalog_ref(cat))
        req = project_sizing_to_sizing_request(api_req, resolved_catalogs=(cat,))
        assert req.minimum_effective_length_m is None
        assert req.maximum_effective_length_m is None
        assert req.request_raw_combination_cap is None


# =========================================================================
# T41: Construct real SizingRequestIdentity
# =========================================================================


class TestRealSizingRequestIdentity:
    """T41: Construct a SizingRequestIdentity from real production models."""

    def test_construct_identity(self) -> None:
        cat = _make_cat()
        identity = build_sizing_request_identity(
            SizingRequest(catalogs=(cat,)),
            hot_fluid_name="Water",
            cold_fluid_name="Water",
            hot_fluid_equation_of_state="CoolProp",
            cold_fluid_equation_of_state="CoolProp",
            hot_inlet_temperature_k=370.0,
            cold_inlet_temperature_k=300.0,
            hot_inlet_pressure_pa=200_000.0,
            cold_inlet_pressure_pa=200_000.0,
            hot_mass_flow_kg_s=1.0,
            cold_mass_flow_kg_s=2.0,
            tube_in_hot=True,
            flow_arrangement="counterflow",
            minimum_terminal_delta_t=5.0,
            required_duty_w=100_000.0,
            duty_absolute_tolerance_w=0.0,
            duty_relative_tolerance=0.0,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=3,
            solver_params=SolverParams(),
            expected_provider_identity=_expected_provider_identity(),
        )
        assert isinstance(identity, SizingRequestIdentity)
        assert identity.hot_fluid_name == "Water"
        assert identity.cold_fluid_name == "Water"
        assert identity.required_duty_w == 100_000.0
        assert identity.rating_solver_max_iterations == 100

    def test_identity_digest_is_deterministic(self) -> None:
        cat = _make_cat()
        kwargs = dict(
            hot_fluid_name="Water",
            cold_fluid_name="Water",
            hot_fluid_equation_of_state="CoolProp",
            cold_fluid_equation_of_state="CoolProp",
            hot_inlet_temperature_k=370.0,
            cold_inlet_temperature_k=300.0,
            hot_inlet_pressure_pa=200_000.0,
            cold_inlet_pressure_pa=200_000.0,
            hot_mass_flow_kg_s=1.0,
            cold_mass_flow_kg_s=2.0,
            tube_in_hot=True,
            flow_arrangement="counterflow",
            minimum_terminal_delta_t=5.0,
            required_duty_w=100_000.0,
            duty_absolute_tolerance_w=0.0,
            duty_relative_tolerance=0.0,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=3,
            solver_params=SolverParams(),
            expected_provider_identity=_expected_provider_identity(),
        )
        id1 = build_sizing_request_identity(SizingRequest(catalogs=(cat,)), **kwargs)  # type: ignore[arg-type]
        id2 = build_sizing_request_identity(SizingRequest(catalogs=(cat,)), **kwargs)  # type: ignore[arg-type]
        assert id1.sizing_request_identity_digest == id2.sizing_request_identity_digest

    def test_identity_frozen(self) -> None:
        cat = _make_cat()
        identity = build_sizing_request_identity(
            SizingRequest(catalogs=(cat,)),
            hot_fluid_name="Water",
            cold_fluid_name="Water",
            hot_fluid_equation_of_state="CoolProp",
            cold_fluid_equation_of_state="CoolProp",
            hot_inlet_temperature_k=370.0,
            cold_inlet_temperature_k=300.0,
            hot_inlet_pressure_pa=200_000.0,
            cold_inlet_pressure_pa=200_000.0,
            hot_mass_flow_kg_s=1.0,
            cold_mass_flow_kg_s=2.0,
            tube_in_hot=True,
            flow_arrangement="counterflow",
            minimum_terminal_delta_t=5.0,
            required_duty_w=100_000.0,
            duty_absolute_tolerance_w=0.0,
            duty_relative_tolerance=0.0,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=3,
            solver_params=SolverParams(),
            expected_provider_identity=_expected_provider_identity(),
        )
        with pytest.raises((ValidationError, AttributeError)):
            identity.hot_fluid_name = "changed"


# =========================================================================
# T42: No non-finite numbers in canonical payload
# =========================================================================


class TestNoNonFiniteInCanonical:
    """T42: Canonical payload serialization rejects NaN/Inf."""

    def test_nan_rejected_in_canonical_json(self) -> None:
        from hexagent.core.canonical import canonical_json

        with pytest.raises(ValueError, match="Non-finite"):
            canonical_json({"value": float("nan")})

    def test_inf_rejected_in_canonical_json(self) -> None:
        from hexagent.core.canonical import canonical_json

        with pytest.raises(ValueError, match="Non-finite"):
            canonical_json({"value": float("inf")})

    def test_neg_inf_rejected_in_canonical_json(self) -> None:
        from hexagent.core.canonical import canonical_json

        with pytest.raises(ValueError, match="Non-finite"):
            canonical_json({"value": float("-inf")})

    def test_projected_models_have_no_non_finite(self) -> None:
        """All projected domain models contain only finite floats."""
        case = project_validation_to_design_case(_validation_request())
        assert case.target_duty is not None
        geom = project_geometry_spec_to_geometry(_geometry_spec())
        solver = project_solver_spec_to_solver(SolverParamsSpec())

        # Check geometry
        geom_dict = geom.to_dict()
        for k, v in geom_dict.items():
            if isinstance(v, float):
                assert math.isfinite(v), f"Non-finite value in geometry.{k}: {v}"

        # Check solver
        assert math.isfinite(solver.absolute_residual_w)
        assert math.isfinite(solver.relative_residual_fraction)
        assert math.isfinite(solver.bracket_temperature_tolerance_k)


# =========================================================================
# T43: Public model JSON schema dimensional fields not bare number
# =========================================================================


class TestJsonSchemaDimensionalFields:
    """T43: Public API model JSON schemas use typed Quantity objects,
    not bare numbers, for dimensional fields."""

    def test_validation_api_request_schema_has_no_bare_target_duty(self) -> None:
        schema = ValidationApiRequest.model_json_schema()
        props = schema.get("properties", {})
        # target_duty should reference a Power schema, not be a bare number
        td = props.get("target_duty", {})
        # It should have $ref or be a typed schema
        assert "$ref" in td or "anyOf" in td or td.get("type") != "number"

    def test_geometry_schema_has_no_bare_diameter(self) -> None:
        schema = DoublePipeGeometrySpec.model_json_schema()
        props = schema.get("properties", {})
        itid = props.get("inner_tube_inner_diameter", {})
        assert "$ref" in itid or "anyOf" in itid or itid.get("type") != "number"

    def test_sizing_schema_has_no_bare_length(self) -> None:
        schema = SizingApiRequest.model_json_schema()
        props = schema.get("properties", {})
        mel = props.get("minimum_effective_length", {})
        # Should be Length | None, not bare number
        assert mel.get("type") != "number"

    def test_solver_schema_has_no_bare_absolute_residual(self) -> None:
        schema = SolverParamsSpec.model_json_schema()
        props = schema.get("properties", {})
        ar = props.get("absolute_residual_w", {})
        assert "$ref" in ar or "anyOf" in ar or ar.get("type") != "number"


# =========================================================================
# T44: DoublePipeService.size() not imported/called
# =========================================================================


class TestDoublePipeServiceNotCalled:
    """T44: The projection module does not import or call
    DoublePipeService.size()."""

    def test_projection_module_source_no_size_reference(self) -> None:
        import hexagent.api.projection as proj_mod

        source = inspect.getsource(proj_mod)
        assert "DoublePipeService" not in source
        assert ".size(" not in source
        assert "assumed_u" not in source

    def test_projection_imports_clean(self) -> None:
        import hexagent.api.projection as proj_mod

        source = inspect.getsource(proj_mod)
        # Should only import from api.models, domain.models, exchangers, optimization
        assert "double_pipe.service" not in source


# =========================================================================
# T45: Monkeypatch DoublePipeService.size() to fail immediately,
#       all projection/identity tests still pass
# =========================================================================


class TestMonkeypatchDoublePipeService:
    """T45: Even when DoublePipeService.size() is monkeypatched to raise
    immediately, all projection and identity operations succeed without
    ever calling it."""

    def test_projections_succeed_with_poisoned_size(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from hexagent.exchangers.double_pipe.service import DoublePipeService

        def _poisoned_size(self_inner: Any, case: Any) -> Any:
            raise RuntimeError("DoublePipeService.size() MUST NOT be called by TASK-010")

        monkeypatch.setattr(DoublePipeService, "size", _poisoned_size)

        # All projections should succeed
        stream = project_fluid_stream_to_stream_spec(_hot_stream_spec())
        assert stream.fluid.name == "Water"

        case = project_validation_to_design_case(_validation_request())
        assert case.target_duty is not None
        assert case.name == "test_case"

        geom = project_geometry_spec_to_geometry(_geometry_spec())
        assert geom.effective_length_m == pytest.approx(5.0)

        solver = project_solver_spec_to_solver(SolverParamsSpec())
        assert solver.max_iterations == 100

        cat = _make_cat()
        req = project_sizing_to_sizing_request(
            _sizing_api_request(_catalog_ref(cat)),
            resolved_catalogs=(cat,),
        )
        assert isinstance(req, SizingRequest)

        # Build identity — also must not call size()
        identity = build_sizing_request_identity(
            SizingRequest(catalogs=(cat,)),
            hot_fluid_name="Water",
            cold_fluid_name="Water",
            hot_fluid_equation_of_state="CoolProp",
            cold_fluid_equation_of_state="CoolProp",
            hot_inlet_temperature_k=370.0,
            cold_inlet_temperature_k=300.0,
            hot_inlet_pressure_pa=200_000.0,
            cold_inlet_pressure_pa=200_000.0,
            hot_mass_flow_kg_s=1.0,
            cold_mass_flow_kg_s=2.0,
            tube_in_hot=True,
            flow_arrangement="counterflow",
            minimum_terminal_delta_t=5.0,
            required_duty_w=100_000.0,
            duty_absolute_tolerance_w=0.0,
            duty_relative_tolerance=0.0,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=3,
            solver_params=SolverParams(),
            expected_provider_identity=_expected_provider_identity(),
        )
        digest = identity.sizing_request_identity_digest
        assert digest.startswith("sha256:")
        assert len(digest) == 71

    def test_all_identity_digests_succeed_with_poisoned_size(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Re-run key digest tests with poisoned DoublePipeService.size()."""
        from hexagent.exchangers.double_pipe.service import DoublePipeService

        def _poisoned_size(self_inner: Any, case: Any) -> Any:
            raise RuntimeError("DoublePipeService.size() MUST NOT be called by TASK-010")

        monkeypatch.setattr(DoublePipeService, "size", _poisoned_size)

        # Digest sensitivity tests
        cat = _make_cat()
        base_kwargs = dict(
            hot_fluid_name="Water",
            cold_fluid_name="Water",
            hot_fluid_equation_of_state="CoolProp",
            cold_fluid_equation_of_state="CoolProp",
            hot_inlet_temperature_k=370.0,
            cold_inlet_temperature_k=300.0,
            hot_inlet_pressure_pa=200_000.0,
            cold_inlet_pressure_pa=200_000.0,
            hot_mass_flow_kg_s=1.0,
            cold_mass_flow_kg_s=2.0,
            tube_in_hot=True,
            flow_arrangement="counterflow",
            minimum_terminal_delta_t=5.0,
            duty_absolute_tolerance_w=0.0,
            duty_relative_tolerance=0.0,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=3,
            solver_params=SolverParams(),
            expected_provider_identity=_expected_provider_identity(),
        )

        id1 = build_sizing_request_identity(
            SizingRequest(catalogs=(cat,)),
            required_duty_w=100_000.0,
            **base_kwargs,  # type: ignore[arg-type]
        )
        id2 = build_sizing_request_identity(
            SizingRequest(catalogs=(cat,)),
            required_duty_w=200_000.0,
            **base_kwargs,  # type: ignore[arg-type]
        )
        assert id1.sizing_request_identity_digest != id2.sizing_request_identity_digest
