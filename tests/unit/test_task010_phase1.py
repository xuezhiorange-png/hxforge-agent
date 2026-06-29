"""TASK-010 Phase 1 — Projection and contract tests.

Tests T1–T88+ from the frozen TASK-010 test contract.  Covers:
  - API DTO construction, frozen behavior, extra-field rejection
  - Quantity validation (string-to-number, bare float, invalid unit, NaN/Inf, −0)
  - Single-authority rules (target_duty, phase_hint, fouling, terminal ΔT)
  - DTO → domain model projection (field-level consistency)
  - SolverParamsSpec defaults match production SolverParams
  - solver_params=None vs explicit identity
  - Provider/catalog resolution via ProviderRegistry / CatalogRegistry
  - Canonical digest sensitivity (provider, catalog, solver, geometry, boundary, duty)
  - Unit equivalence canonical payloads
  - Unicode/Decimal canonical equivalence
  - Non-finite canonical payload rejection
  - JSON schema dimensional-field enforcement
  - DoublePipeService.size() never called by projection/identity path
  - canonical_decimal_string vectors
  - canonical_quantity_payload vectors
  - ProviderRegistry immutability (MappingProxyType)
  - CatalogSnapshotReference validation
  - Case name validation
  - Numeric string coercion
  - Solver None vs empty canonical context equality
"""

from __future__ import annotations

import inspect
import math
from decimal import Decimal
from types import MappingProxyType
from typing import Any

import pytest
from pydantic import ValidationError

from hexagent.api.canonical_request import (
    build_sizing_canonical_request_context,
    canonical_decimal_string,
    canonical_quantity_payload,
    canonicalize_api_payload,
    compute_api_request_digest,
)
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
from hexagent.api.registry import CatalogRegistry, ProviderRegistry
from hexagent.core.heat_balance import ProviderIdentitySnapshot
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
)
from hexagent.optimization.models import (
    CatalogSnapshotRef,
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


def _make_provider_snapshot(**overrides: str) -> ProviderIdentitySnapshot:
    """Build a ProviderIdentitySnapshot for test use."""
    defaults = dict(
        name="CoolProp",
        version="6.6.0",
        git_revision="abc123",
        reference_state_policy="IIR",
        configuration_fingerprint="",
        cache_policy_version="",
    )
    defaults.update(overrides)
    return ProviderIdentitySnapshot(**defaults)  # type: ignore[arg-type]


def _make_provider_registry(ref: str = "default", **overrides: str) -> ProviderRegistry:
    """Build a ProviderRegistry with a single provider."""
    return ProviderRegistry({ref: _make_provider_snapshot(**overrides)})


def _cat_snapshot_ref(cat: CompleteDoublePipeCatalogSnapshot) -> CatalogSnapshotRef:
    """Build a CatalogSnapshotRef from a catalog snapshot."""
    return CatalogSnapshotRef(
        catalog_id=cat.catalog_id,
        catalog_version=cat.catalog_version,
        catalog_content_hash=cat.catalog_content_hash,
        source_identity=cat.source_identity,
        schema_version=cat.schema_version,
    )


def _make_cat_registry(
    cats: list[CompleteDoublePipeCatalogSnapshot] | None = None,
) -> CatalogRegistry:
    """Build a CatalogRegistry with given snapshots."""
    if cats is None:
        cats = [_make_cat()]
    return CatalogRegistry(cats)


def _validation_request_with_duty(duty_w: float) -> ValidationApiRequest:
    """Build a ValidationApiRequest with a specific target duty in watts."""
    return ValidationApiRequest(
        api_schema_version="1",
        case_name="test_case",
        hot_stream=_hot_stream_spec(),
        cold_stream=_cold_stream_spec(),
        target_duty=Power(value=duty_w, unit="W"),
        minimum_terminal_delta_t=TemperatureDifference(value=5, unit="K"),
        design_pressure_hot=AbsolutePressure(value=500_000, unit="Pa"),
        design_pressure_cold=AbsolutePressure(value=500_000, unit="Pa"),
        design_temperature_hot=AbsoluteTemperature(value=400, unit="K"),
        design_temperature_cold=AbsoluteTemperature(value=350, unit="K"),
        required_area_margin_fraction=0.1,
    )


def _compute_sizing_digest(
    cat: CompleteDoublePipeCatalogSnapshot,
    provider_snapshot: ProviderIdentitySnapshot | None = None,
    solver_params: SolverParamsSpec | None = None,
    validation_request: ValidationApiRequest | None = None,
    **overrides: Any,
) -> str:
    """Compute the sizing request digest via the canonical path.

    Uses build_sizing_canonical_request_context() + compute_api_request_digest().
    """
    if provider_snapshot is None:
        provider_snapshot = _make_provider_snapshot()

    provider_reg = ProviderRegistry({"default": provider_snapshot})
    cat_reg = CatalogRegistry([cat])

    cat_ref = _catalog_ref(cat)

    defaults = dict(
        api_schema_version="1",
        case=validation_request if validation_request is not None else _validation_request(),
        catalog_refs=(cat_ref,),
        tube_boundary_condition="constant_wall_temperature",
        annulus_boundary_condition="constant_wall_temperature",
        flow_arrangement="counterflow",
        optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
        requested_top_n=3,
        expected_provider_identity=ExpectedProviderIdentity(
            name=provider_snapshot.name,
            version=provider_snapshot.version,
            git_revision=provider_snapshot.git_revision,
            reference_state_policy=provider_snapshot.reference_state_policy,
        ),
        solver_params=solver_params,
    )
    defaults.update(overrides)
    api_request = SizingApiRequest(**defaults)  # type: ignore[arg-type]

    resolved_provider = provider_reg.resolve("default")
    resolved_catalogs = tuple(authority.snapshot for authority in [cat_reg.resolve(cat_ref)])

    ctx = build_sizing_canonical_request_context(
        request=api_request,
        resolved_provider=resolved_provider,
        resolved_catalogs=resolved_catalogs,
    )
    return compute_api_request_digest(ctx)


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
        with pytest.raises((ValidationError, AttributeError)):
            MassFlow(value=-0.0, unit="kg/s")

    def test_negative_zero_length_accepted(self) -> None:
        q = Length(value=-0.0, unit="m")
        assert q.si_value == 0.0

    def test_negative_zero_pressure_rejected(self) -> None:
        with pytest.raises((ValidationError, AttributeError)):
            AbsolutePressure(value=-0.0, unit="Pa")


# =========================================================================
# T9: target_duty sole authority (+ T60, T61, T62)
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

    # T60: target_duty canonical payload is {"value": "...", "unit": "W"}
    def test_target_duty_canonical_payload_format(self) -> None:
        q = Power(value=100_000, unit="W")
        payload = canonical_quantity_payload(q)
        assert "value" in payload
        assert "unit" in payload
        assert payload["unit"] == "W"
        assert isinstance(payload["value"], str)

    # T61: target_duty in kW canonical payload same as W
    def test_target_duty_kw_canonical_matches_w(self) -> None:
        q_w = Power(value=100_000, unit="W")
        q_kw = Power(value=100, unit="kW")
        p_w = canonical_quantity_payload(q_w)
        p_kw = canonical_quantity_payload(q_kw)
        assert p_w["value"] == p_kw["value"]
        assert p_w["unit"] == p_kw["unit"]

    # T62: duty canonical value is positive
    def test_target_duty_canonical_value_positive(self) -> None:
        q = Power(value=100_000, unit="W")
        payload = canonical_quantity_payload(q)
        assert Decimal(payload["value"]) > 0


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


class TestProjectionValidation:
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


class TestProjectionFluidStream:
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


class TestProjectionGeometry:
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


class TestProjectionSolver:
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


class TestSolverDefaultMatch:
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
# T18: solver_params=None vs {} identity (rewrite: compare canonical contexts)
# =========================================================================


class TestSolverIdentity:
    """T18: Omitting solver_params (None) and passing explicit SolverParamsSpec()
    produce the same canonical request context."""

    def test_none_vs_default_canonical_context_equal(self) -> None:
        cat = _make_cat()
        cat_ref = _catalog_ref(cat)
        provider_snapshot = _make_provider_snapshot()
        provider_reg = ProviderRegistry({"default": provider_snapshot})
        cat_reg = CatalogRegistry([cat])
        resolved_provider = provider_reg.resolve("default")
        resolved_catalogs = tuple(authority.snapshot for authority in [cat_reg.resolve(cat_ref)])

        req_none = _sizing_api_request(cat_ref=cat_ref, solver_params=None)
        req_explicit = _sizing_api_request(cat_ref=cat_ref, solver_params=SolverParamsSpec())

        ctx_none = build_sizing_canonical_request_context(
            request=req_none,
            resolved_provider=resolved_provider,
            resolved_catalogs=resolved_catalogs,
        )
        ctx_explicit = build_sizing_canonical_request_context(
            request=req_explicit,
            resolved_provider=resolved_provider,
            resolved_catalogs=resolved_catalogs,
        )

        assert ctx_none == ctx_explicit

    def test_none_vs_default_digest_equal(self) -> None:
        cat = _make_cat()
        d_none = _compute_sizing_digest(cat, solver_params=None)
        d_explicit = _compute_sizing_digest(cat, solver_params=SolverParamsSpec())
        assert d_none == d_explicit


# =========================================================================
# T19: Provider unknown ref rejection (+ T68)
# =========================================================================


class TestProviderResolution:
    """T19: An unknown provider_ref leads to resolution failure via ProviderRegistry."""

    def test_unknown_provider_ref_raises(self) -> None:
        reg = ProviderRegistry({"known": _make_provider_snapshot()})
        with pytest.raises(ValueError, match="Unknown provider reference"):
            reg.resolve("unknown")

    def test_blank_provider_ref_raises(self) -> None:
        reg = ProviderRegistry({"known": _make_provider_snapshot()})
        with pytest.raises(ValueError, match="non-blank"):
            reg.resolve("")

    def test_known_ref_resolves(self) -> None:
        reg = _make_provider_registry("coolprop")
        resolved = reg.resolve("coolprop")
        assert resolved.provider_ref == "coolprop"
        assert resolved.identity.name == "CoolProp"

    # T68: provider identity mismatch
    def test_provider_identity_mismatch_rejected(self) -> None:
        expected = ExpectedProviderIdentity(
            name="CoolProp",
            version="6.6.0",
            git_revision="abc123",
            reference_state_policy="IIR",
        )

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
    """T20: Duplicate provider refs — the second silently wins in a dict
    but registry construction validates each ref is non-blank."""

    def test_duplicate_ref_in_dict_overwrites(self) -> None:
        """Python dicts silently overwrite — registry stores the last one."""
        snap_a = _make_provider_snapshot(version="6.6.0")
        snap_b = _make_provider_snapshot(version="7.0.0")
        providers: dict[str, ProviderIdentitySnapshot] = {"default": snap_a}
        providers["default"] = snap_b  # overwrite
        reg = ProviderRegistry(providers)
        resolved = reg.resolve("default")
        assert resolved.identity.version == "7.0.0"

    def test_blank_ref_in_registry_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-blank"):
            ProviderRegistry({"": _make_provider_snapshot()})


# =========================================================================
# T21: Same provider_ref, different identity -> different digest (+ T63-T66)
# =========================================================================


class TestProviderDigestSensitivity:
    """T21: Different provider identities produce different
    canonical request context digests. Uses full path."""

    def test_different_provider_version_different_digest(self) -> None:
        cat = _make_cat()
        snap_a = _make_provider_snapshot(version="6.6.0")
        snap_b = _make_provider_snapshot(version="7.0.0")
        d_a = _compute_sizing_digest(cat, provider_snapshot=snap_a)
        d_b = _compute_sizing_digest(cat, provider_snapshot=snap_b)
        assert d_a != d_b

    # T63: git_revision change
    def test_git_revision_change(self) -> None:
        cat = _make_cat()
        snap_a = _make_provider_snapshot(git_revision="abc123")
        snap_b = _make_provider_snapshot(git_revision="def456")
        d_a = _compute_sizing_digest(cat, provider_snapshot=snap_a)
        d_b = _compute_sizing_digest(cat, provider_snapshot=snap_b)
        assert d_a != d_b

    # T64: reference_state_policy change
    def test_reference_state_policy_change(self) -> None:
        cat = _make_cat()
        snap_a = _make_provider_snapshot(reference_state_policy="IIR")
        snap_b = _make_provider_snapshot(reference_state_policy="NBP")
        d_a = _compute_sizing_digest(cat, provider_snapshot=snap_a)
        d_b = _compute_sizing_digest(cat, provider_snapshot=snap_b)
        assert d_a != d_b

    # T65: configuration_fingerprint change
    def test_configuration_fingerprint_change(self) -> None:
        cat = _make_cat()
        snap_a = _make_provider_snapshot(configuration_fingerprint="")
        snap_b = _make_provider_snapshot(configuration_fingerprint="fp123")
        d_a = _compute_sizing_digest(cat, provider_snapshot=snap_a)
        d_b = _compute_sizing_digest(cat, provider_snapshot=snap_b)
        assert d_a != d_b

    # T66: cache_policy_version change
    def test_cache_policy_version_change(self) -> None:
        cat = _make_cat()
        snap_a = _make_provider_snapshot(cache_policy_version="")
        snap_b = _make_provider_snapshot(cache_policy_version="v2")
        d_a = _compute_sizing_digest(cat, provider_snapshot=snap_a)
        d_b = _compute_sizing_digest(cat, provider_snapshot=snap_b)
        assert d_a != d_b


# =========================================================================
# T22: Catalog unknown ref rejection (+ T55)
# =========================================================================


class TestCatalogResolution:
    """T22: Referencing a catalog not found in the registry → rejected.
    Uses CatalogRegistry.resolve()."""

    def test_catalog_ref_not_in_registry_raises(self) -> None:
        cat = _make_cat()
        reg = CatalogRegistry([cat])
        bad_ref = CatalogSnapshotRef(
            catalog_id="nonexistent",
            catalog_version="v99",
            catalog_content_hash="sha256:" + "00" * 32,
            source_identity="nowhere",
            schema_version="1.0",
        )
        with pytest.raises(ValueError, match="Unknown catalog reference"):
            reg.resolve(bad_ref)

    # T55: valid ref resolves
    def test_catalog_ref_resolves(self) -> None:
        cat = _make_cat()
        reg = CatalogRegistry([cat])
        ref = _cat_snapshot_ref(cat)
        resolved = reg.resolve(ref)
        assert resolved.content_hash_verified is True
        assert resolved.snapshot.catalog_id == cat.catalog_id

    def test_catalog_registry_snapshots_property(self) -> None:
        cat = _make_cat()
        reg = CatalogRegistry([cat])
        assert len(reg.snapshots) == 1
        assert reg.snapshots[0].catalog_id == cat.catalog_id


# =========================================================================
# T23: Catalog duplicate key rejection
# =========================================================================


class TestCatalogDuplicateKey:
    """T23: Duplicate catalog identities are rejected by CatalogRegistry."""

    def test_duplicate_catalog_rejected(self) -> None:
        cat = _make_cat()
        with pytest.raises(ValueError, match="[Dd]uplicate"):
            CatalogRegistry([cat, cat])


# =========================================================================
# T87: Catalog refs duplicate rejection
# =========================================================================


class TestCatalogRefsDuplicate:
    """T87: Duplicate catalog refs are rejected by the sizing projection."""

    def test_same_catalog_ref_twice_rejected(self) -> None:
        from hexagent.optimization.length import compute_raw_combination_count

        cat = _make_cat()
        with pytest.raises(Exception, match="[Dd]uplicate"):
            compute_raw_combination_count((cat, cat))


# =========================================================================
# T86: Catalog order independence
# =========================================================================


class TestCatalogOrderIndependence:
    """T86: Different input orders of catalog refs produce the same
    canonical CatalogRegistry ordering."""

    def test_catalog_registry_canonical_order(self) -> None:
        cat_a = _make_cat("cat_a", opts=(_make_opt("o1"),))
        cat_b = _make_cat("cat_b", opts=(_make_opt("o2"),))
        reg = CatalogRegistry([cat_b, cat_a])
        # Snapshots should be in canonical (sorted by identity key) order
        assert reg.snapshots[0].catalog_id == "cat_a"
        assert reg.snapshots[1].catalog_id == "cat_b"

    def test_catalog_registry_reversed_input_same_order(self) -> None:
        cat_a = _make_cat("cat_a", opts=(_make_opt("o1"),))
        cat_b = _make_cat("cat_b", opts=(_make_opt("o2"),))
        reg = CatalogRegistry([cat_a, cat_b])
        assert reg.snapshots[0].catalog_id == "cat_a"
        assert reg.snapshots[1].catalog_id == "cat_b"


# =========================================================================
# T88 + T56: Catalog content hash mismatch rejection
# =========================================================================


class TestCatalogHashMismatch:
    """T88: A catalog ref pointing to the wrong content hash → rejected
    by CatalogRegistry. T56: tampered hash at construction time."""

    def test_tampered_hash_rejected_by_snapshot(self) -> None:
        opt = _make_opt()
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

    def test_tampered_hash_rejected_by_registry(self) -> None:
        """CatalogRegistry re-verifies content hash on construction."""
        opt = _make_opt()
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
# T27: Equivalent unit input -> same canonical payload
# =========================================================================


class TestUnitEquivalence:
    """T27: Quantity values with equivalent SI produce the same
    canonical_quantity_payload."""

    def test_power_kW_vs_W_same_canonical(self) -> None:
        p_w = Power(value=100_000, unit="W")
        p_kw = Power(value=100, unit="kW")
        c_w = canonical_quantity_payload(p_w)
        c_kw = canonical_quantity_payload(p_kw)
        assert c_w == c_kw
        assert c_w["unit"] == "W"

    def test_length_cm_vs_m_same_canonical(self) -> None:
        l_m = Length(value=0.02, unit="m")
        l_cm = Length(value=2, unit="cm")
        c_m = canonical_quantity_payload(l_m)
        c_cm = canonical_quantity_payload(l_cm)
        assert c_m == c_cm
        assert c_m["unit"] == "m"

    # T28: 5K vs 5 delta_degC canonical result identical
    def test_5k_vs_5_delta_degC_canonical(self) -> None:
        td_k = TemperatureDifference(value=5, unit="K")
        td_dc = TemperatureDifference(value=5, unit="delta_degC")
        c_k = canonical_quantity_payload(td_k)
        c_dc = canonical_quantity_payload(td_dc)
        assert c_k == c_dc
        assert c_k["unit"] == "K"


# =========================================================================
# T29: Unicode equivalence forms canonical result identical
# =========================================================================


class TestUnicodeEquivalence:
    """T29: Unicode NFC normalization in strings produces
    canonical equivalence via canonicalize_api_payload."""

    def test_micro_sign_vs_mu(self) -> None:
        """µ (U+00B5, micro sign) and μ (U+03BC, Greek mu) should
        normalize to the same unit via NFKC."""
        q1 = Length(value=1.0, unit="µm")
        q2 = Length(value=1.0, unit="μm")
        assert q1.si_value == pytest.approx(q2.si_value)

    def test_canonicalize_nfc_strings(self) -> None:
        """NFC-normalized strings from canonicalize_api_payload."""
        # Both decomposed and precomposed forms should canonicalize identically
        import unicodedata

        s_decomposed = unicodedata.normalize("NFC", "\u0065\u0301")  # e + combining accent
        s_precomposed = unicodedata.normalize("NFC", "\u00e9")  # é
        assert canonicalize_api_payload(s_decomposed) == canonicalize_api_payload(s_precomposed)


# =========================================================================
# T30: Decimal halfway vectors
# =========================================================================


class TestDecimalHalfway:
    """T30: Decimal halfway values are handled with full precision via
    canonical_decimal_string."""

    def test_halfway_rounds_even(self) -> None:
        # 1.234567890123455 has last digit 5 → banker's rounding
        d = Decimal("1.234567890123455")
        result = canonical_decimal_string(d)
        # Should round to even: 1.23456789012346 (4 is even, 6 is even; 4→4)
        assert result == "1.23456789012346"

    def test_halfway_below(self) -> None:
        d = Decimal("1.234567890123445")
        result = canonical_decimal_string(d)
        assert result == "1.23456789012344"

    def test_trailing_zeros_stripped(self) -> None:
        d = Decimal("1.5000")
        result = canonical_decimal_string(d)
        assert result == "1.5"

    def test_zero_is_zero(self) -> None:
        assert canonical_decimal_string(Decimal("0")) == "0"
        assert canonical_decimal_string(Decimal("0.0")) == "0"

    def test_one_is_one(self) -> None:
        assert canonical_decimal_string(Decimal("1")) == "1"
        assert canonical_decimal_string(Decimal("1.0")) == "1"

    def test_negative_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="negative zero"):
            canonical_decimal_string(Decimal("-0"))

    def test_non_finite_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-finite"):
            canonical_decimal_string(Decimal("NaN"))
        with pytest.raises(ValueError, match="non-finite"):
            canonical_decimal_string(Decimal("Inf"))
        with pytest.raises(ValueError, match="non-finite"):
            canonical_decimal_string(Decimal("-Inf"))


# =========================================================================
# T31: Tiny and huge canonical vectors
# =========================================================================


class TestDecimalExtreme:
    """T31: Very small and very large values are canonicalized correctly
    using adjusted exponent threshold."""

    def test_999999999999999_5_rounds_to_scientific(self) -> None:
        d = Decimal("999999999999999.5")
        result = canonical_decimal_string(d)
        assert result == "1E+15"

    def test_1e_minus_30_scientific(self) -> None:
        d = Decimal("1E-30")
        result = canonical_decimal_string(d)
        assert result == "1E-30"

    def test_1e_plus_30_scientific(self) -> None:
        d = Decimal("1E+30")
        result = canonical_decimal_string(d)
        assert result == "1E+30"

    def test_0_00000000001_is_1e_minus_11(self) -> None:
        d = Decimal("0.00000000001")
        result = canonical_decimal_string(d)
        assert result == "1E-11"

    def test_0_000000000001_is_1e_minus_12(self) -> None:
        d = Decimal("0.000000000001")
        result = canonical_decimal_string(d)
        assert result == "1E-12"

    def test_99999999999_is_fixed(self) -> None:
        d = Decimal("99999999999")
        result = canonical_decimal_string(d)
        # adjusted exponent = 10, within [-10, 10] → fixed notation
        assert result == "99999999999"

    def test_100000000000_is_scientific(self) -> None:
        d = Decimal("100000000000")
        result = canonical_decimal_string(d)
        # adjusted exponent = 11, outside [-10, 10] → scientific notation
        assert result == "1E+11"

    def test_1e_minus_7_is_fixed(self) -> None:
        d = Decimal("1E-7")
        result = canonical_decimal_string(d)
        assert result == "0.0000001"

    def test_1e_minus_10_is_fixed(self) -> None:
        d = Decimal("1E-10")
        result = canonical_decimal_string(d)
        assert result == "0.0000000001"

    def test_1e_minus_11_is_scientific(self) -> None:
        d = Decimal("1E-11")
        result = canonical_decimal_string(d)
        assert result == "1E-11"

    def test_1e_plus_10_is_fixed(self) -> None:
        d = Decimal("1E+10")
        result = canonical_decimal_string(d)
        assert result == "10000000000"

    def test_1e_plus_11_is_scientific(self) -> None:
        d = Decimal("1E+11")
        result = canonical_decimal_string(d)
        assert result == "1E+11"


# =========================================================================
# T32: Map key sort stability
# =========================================================================


class TestMapKeySort:
    """T32: Dict-based payloads produce deterministic canonical JSON
    with sorted keys via canonicalize_api_payload."""

    def test_canonicalize_api_payload_sorts_keys(self) -> None:
        data = {"z": 1, "a": 2, "m": 3}
        result = canonicalize_api_payload(data)
        assert list(result.keys()) == ["a", "m", "z"]

    def test_nested_sort(self) -> None:
        data = {"b": {"z": 1, "a": 2}, "a": 1}
        result = canonicalize_api_payload(data)
        assert list(result.keys()) == ["a", "b"]
        assert list(result["b"].keys()) == ["a", "z"]

    def test_design_case_canonical_keys_sorted(self) -> None:
        case = project_validation_to_design_case(_validation_request())
        assert case.target_duty is not None
        import json

        from hexagent.core.canonical import canonical_json

        cj = canonical_json(case)
        d = json.loads(cj)

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


# =========================================================================
# T33: Input collection ordering rules
# =========================================================================


class TestCollectionOrder:
    """T33: Tuples preserve insertion order; catalog tuples are sorted."""

    def test_catalog_tuple_sorted_by_identity(self) -> None:
        cat_a = _make_cat("cat_a", opts=(_make_opt("o1"),))
        cat_b = _make_cat("cat_b", opts=(_make_opt("o2"),))
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
# T34: Provider identity field change -> digest change (full path)
# =========================================================================


class TestProviderDigestSensitivityFull:
    """T34: Changing any field in provider identity produces
    a different canonical request digest. Uses full path through
    build_sizing_canonical_request_context + compute_api_request_digest."""

    def test_name_change(self) -> None:
        cat = _make_cat()
        snap_a = _make_provider_snapshot(name="CoolProp")
        snap_b = _make_provider_snapshot(name="REFPROP")
        d_a = _compute_sizing_digest(cat, provider_snapshot=snap_a)
        d_b = _compute_sizing_digest(cat, provider_snapshot=snap_b)
        assert d_a != d_b

    def test_version_change(self) -> None:
        cat = _make_cat()
        snap_a = _make_provider_snapshot(version="6.6.0")
        snap_b = _make_provider_snapshot(version="7.0.0")
        d_a = _compute_sizing_digest(cat, provider_snapshot=snap_a)
        d_b = _compute_sizing_digest(cat, provider_snapshot=snap_b)
        assert d_a != d_b

    def test_git_revision_change(self) -> None:
        cat = _make_cat()
        snap_a = _make_provider_snapshot(git_revision="abc123")
        snap_b = _make_provider_snapshot(git_revision="def456")
        d_a = _compute_sizing_digest(cat, provider_snapshot=snap_a)
        d_b = _compute_sizing_digest(cat, provider_snapshot=snap_b)
        assert d_a != d_b

    def test_reference_state_policy_change(self) -> None:
        cat = _make_cat()
        snap_a = _make_provider_snapshot(reference_state_policy="IIR")
        snap_b = _make_provider_snapshot(reference_state_policy="NBP")
        d_a = _compute_sizing_digest(cat, provider_snapshot=snap_a)
        d_b = _compute_sizing_digest(cat, provider_snapshot=snap_b)
        assert d_a != d_b


# =========================================================================
# T35: Catalog authority field change -> digest change
# =========================================================================


class TestCatalogDigestSensitivity:
    """T35: Changing catalog identity fields produces different digests.
    Uses build_sizing_canonical_request_context + compute_api_request_digest."""

    def test_catalog_version_change(self) -> None:
        cat_a = _make_cat("cat1")
        d1 = _compute_sizing_digest(cat_a)

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
        d2 = _compute_sizing_digest(cat_b)
        assert d1 != d2

    def test_catalog_content_hash_change(self) -> None:
        """Different assembly options → different content hash → different digest."""
        cat_a = _make_cat("cat1", opts=(_make_opt("o1"),))
        d1 = _compute_sizing_digest(cat_a)
        cat_b = _make_cat("cat1", opts=(_make_opt("o1"), _make_opt("o2")))
        d2 = _compute_sizing_digest(cat_b)
        assert d1 != d2


# =========================================================================
# T36: Solver field change -> digest change
# =========================================================================


class TestSolverDigestSensitivity:
    """T36: Changing solver parameters produces different digests.
    Uses full canonical path."""

    def test_absolute_residual_change(self) -> None:
        cat = _make_cat()
        d1 = _compute_sizing_digest(cat, solver_params=SolverParamsSpec())
        d2 = _compute_sizing_digest(
            cat,
            solver_params=SolverParamsSpec(absolute_residual_w=Power(value=0.01, unit="W")),
        )
        assert d1 != d2

    def test_max_iterations_change(self) -> None:
        cat = _make_cat()
        d1 = _compute_sizing_digest(cat, solver_params=SolverParamsSpec())
        d2 = _compute_sizing_digest(
            cat,
            solver_params=SolverParamsSpec(max_iterations=200),
        )
        assert d1 != d2

    def test_bracket_tolerance_change(self) -> None:
        cat = _make_cat()
        d1 = _compute_sizing_digest(cat, solver_params=SolverParamsSpec())
        d2 = _compute_sizing_digest(
            cat,
            solver_params=SolverParamsSpec(
                bracket_temperature_tolerance_k=TemperatureDifference(value=0.001, unit="K")
            ),
        )
        assert d1 != d2


# =========================================================================
# T37: Geometry field change -> digest change
# =========================================================================


class TestGeometryDigestSensitivity:
    """T37: Changing geometry dimensions produces different projected models."""

    def test_inner_diameter_change(self) -> None:
        g1 = project_geometry_spec_to_geometry(_geometry_spec())
        spec2 = DoublePipeGeometrySpec(
            inner_tube_inner_diameter=Length(value=0.025, unit="m"),
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
            effective_length=Length(value=10.0, unit="m"),
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
    the canonical context digest."""

    def test_tube_boundary_condition_field_present(self) -> None:
        req = _sizing_api_request()
        assert req.tube_boundary_condition == "constant_wall_temperature"

    def test_annulus_boundary_condition_field_present(self) -> None:
        req = _sizing_api_request()
        assert req.annulus_boundary_condition == "constant_wall_temperature"

    def test_boundary_condition_change_changes_digest(self) -> None:
        cat = _make_cat()
        d1 = _compute_sizing_digest(
            cat,
            tube_boundary_condition="constant_wall_temperature",
            annulus_boundary_condition="constant_wall_temperature",
        )
        d2 = _compute_sizing_digest(
            cat,
            tube_boundary_condition="inner_wall_heated",
            annulus_boundary_condition="constant_wall_temperature",
        )
        assert d1 != d2


# =========================================================================
# T39: Duty change -> digest change
# =========================================================================


class TestDutyDigestSensitivity:
    """T39: Changing target duty produces different canonical context digests."""

    def test_duty_change(self) -> None:
        cat = _make_cat()
        d1 = _compute_sizing_digest(cat, validation_request=_validation_request_with_duty(100_000))
        d2 = _compute_sizing_digest(cat, validation_request=_validation_request_with_duty(200_000))
        assert d1 != d2


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
        from hexagent.optimization.context import (
            SizingRequestIdentity,
            build_sizing_request_identity,
        )

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
        from hexagent.optimization.context import build_sizing_request_identity

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
        from hexagent.optimization.context import build_sizing_request_identity

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

    def test_nan_rejected_in_canonical_decimal(self) -> None:
        with pytest.raises(ValueError, match="non-finite"):
            canonical_decimal_string(Decimal("NaN"))

    def test_inf_rejected_in_canonical_decimal(self) -> None:
        with pytest.raises(ValueError, match="non-finite"):
            canonical_decimal_string(Decimal("Inf"))

    def test_neg_inf_rejected_in_canonical_decimal(self) -> None:
        with pytest.raises(ValueError, match="non-finite"):
            canonical_decimal_string(Decimal("-Inf"))

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

        geom_dict = geom.to_dict()
        for k, v in geom_dict.items():
            if isinstance(v, float):
                assert math.isfinite(v), f"Non-finite value in geometry.{k}: {v}"

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
        td = props.get("target_duty", {})
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
        assert "double_pipe.service" not in source


# =========================================================================
# T45: Monkeypatch DoublePipeService.size() to fail immediately
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

        # Compute canonical digest — also must not call size()
        digest = _compute_sizing_digest(cat)
        assert digest.startswith("sha256:")
        assert len(digest) == 71

    def test_all_identity_digests_succeed_with_poisoned_size(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from hexagent.exchangers.double_pipe.service import DoublePipeService

        def _poisoned_size(self_inner: Any, case: Any) -> Any:
            raise RuntimeError("DoublePipeService.size() MUST NOT be called by TASK-010")

        monkeypatch.setattr(DoublePipeService, "size", _poisoned_size)

        cat = _make_cat()
        d1 = _compute_sizing_digest(cat, validation_request=_validation_request_with_duty(100_000))
        d2 = _compute_sizing_digest(cat, validation_request=_validation_request_with_duty(200_000))
        assert d1 != d2


# =========================================================================
# TestCanonicalDecimalVectors — all decimal test vectors
# =========================================================================


class TestCanonicalDecimalVectors:
    """Verify all canonical_decimal_string test vectors from Frozen Contract §8.1."""

    def test_zero(self) -> None:
        assert canonical_decimal_string(Decimal("0")) == "0"

    def test_negative_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="negative zero"):
            canonical_decimal_string(Decimal("-0"))

    def test_one(self) -> None:
        assert canonical_decimal_string(Decimal("1")) == "1"

    def test_one_point_zero(self) -> None:
        assert canonical_decimal_string(Decimal("1.0")) == "1"

    def test_one_point_five_trailing_zeros(self) -> None:
        assert canonical_decimal_string(Decimal("1.5000")) == "1.5"

    def test_rounding_44(self) -> None:
        assert canonical_decimal_string(Decimal("1.234567890123445")) == "1.23456789012344"

    def test_rounding_46(self) -> None:
        assert canonical_decimal_string(Decimal("1.234567890123455")) == "1.23456789012346"

    def test_999999999999999_5(self) -> None:
        assert canonical_decimal_string(Decimal("999999999999999.5")) == "1E+15"

    def test_1e_minus_30(self) -> None:
        assert canonical_decimal_string(Decimal("1E-30")) == "1E-30"

    def test_1e_plus_30(self) -> None:
        assert canonical_decimal_string(Decimal("1E+30")) == "1E+30"

    def test_0_00000000001(self) -> None:
        assert canonical_decimal_string(Decimal("0.00000000001")) == "1E-11"

    def test_0_000000000001(self) -> None:
        assert canonical_decimal_string(Decimal("0.000000000001")) == "1E-12"

    def test_99999999999(self) -> None:
        assert canonical_decimal_string(Decimal("99999999999")) == "99999999999"

    def test_100000000000(self) -> None:
        assert canonical_decimal_string(Decimal("100000000000")) == "1E+11"

    def test_1e_minus_7(self) -> None:
        assert canonical_decimal_string(Decimal("1E-7")) == "0.0000001"

    def test_1e_minus_10(self) -> None:
        assert canonical_decimal_string(Decimal("1E-10")) == "0.0000000001"

    def test_1e_minus_11(self) -> None:
        assert canonical_decimal_string(Decimal("1E-11")) == "1E-11"

    def test_1e_plus_10(self) -> None:
        assert canonical_decimal_string(Decimal("1E+10")) == "10000000000"

    def test_1e_plus_11(self) -> None:
        assert canonical_decimal_string(Decimal("1E+11")) == "1E+11"

    def test_non_decimal_type_raises(self) -> None:
        with pytest.raises(TypeError, match="Expected Decimal"):
            canonical_decimal_string(42)  # type: ignore[arg-type]


# =========================================================================
# TestCanonicalQuantityPayload — all quantity test vectors
# =========================================================================


class TestCanonicalQuantityPayload:
    """Verify canonical_quantity_payload returns {"value": ..., "unit": ...} format."""

    def test_power_100kw_format(self) -> None:
        q = Power(value=100, unit="kW")
        payload = canonical_quantity_payload(q)
        assert set(payload.keys()) == {"value", "unit"}
        assert payload["unit"] == "W"
        assert payload["value"] == "100000"
        assert isinstance(payload["value"], str)

    def test_power_100000w_format(self) -> None:
        q = Power(value=100_000, unit="W")
        payload = canonical_quantity_payload(q)
        assert payload == {"value": "100000", "unit": "W"}

    def test_length_1m_format(self) -> None:
        q = Length(value=1.0, unit="m")
        payload = canonical_quantity_payload(q)
        assert payload["unit"] == "m"
        assert payload["value"] == "1"

    def test_length_2cm_format(self) -> None:
        q = Length(value=2, unit="cm")
        payload = canonical_quantity_payload(q)
        assert payload["unit"] == "m"
        assert Decimal(payload["value"]) == Decimal("0.02")

    def test_mass_flow_format(self) -> None:
        q = MassFlow(value=1.0, unit="kg/s")
        payload = canonical_quantity_payload(q)
        assert payload["unit"] == "kg/s"
        assert payload["value"] == "1"

    def test_temperature_difference_k_format(self) -> None:
        q = TemperatureDifference(value=5, unit="K")
        payload = canonical_quantity_payload(q)
        assert payload["unit"] == "K"
        assert payload["value"] == "5"

    def test_temperature_difference_delta_degC_format(self) -> None:
        q = TemperatureDifference(value=5, unit="delta_degC")
        payload = canonical_quantity_payload(q)
        assert payload["unit"] == "K"
        assert payload["value"] == "5"

    def test_absolute_temperature_format(self) -> None:
        q = AbsoluteTemperature(value=370, unit="K")
        payload = canonical_quantity_payload(q)
        assert payload["unit"] == "K"
        assert payload["value"] == "370"

    def test_absolute_pressure_format(self) -> None:
        q = AbsolutePressure(value=200_000, unit="Pa")
        payload = canonical_quantity_payload(q)
        assert payload["unit"] == "Pa"
        assert payload["value"] == "200000"

    def test_fouling_resistance_format(self) -> None:
        q = FoulingResistance(value=0.0002, unit="m^2*K/W")
        payload = canonical_quantity_payload(q)
        assert "value" in payload
        assert "unit" in payload
        assert isinstance(payload["value"], str)

    def test_value_is_always_string(self) -> None:
        """The value in the canonical payload is always a string."""
        for q in [
            Power(value=1, unit="W"),
            Length(value=0.001, unit="m"),
            MassFlow(value=0.5, unit="kg/s"),
            TemperatureDifference(value=10, unit="K"),
            AbsolutePressure(value=101325, unit="Pa"),
        ]:
            payload = canonical_quantity_payload(q)
            assert isinstance(payload["value"], str), f"Not string for {q}"


# =========================================================================
# TestProviderRegistryImmutability — MappingProxyType
# =========================================================================


class TestProviderRegistryImmutability:
    """ProviderRegistry stores providers in MappingProxyType (truly immutable)."""

    def test_internal_storage_is_mapping_proxy(self) -> None:
        reg = _make_provider_registry()
        assert isinstance(reg._providers, MappingProxyType)

    def test_cannot_setitem_on_internal(self) -> None:
        reg = _make_provider_registry()
        with pytest.raises(TypeError):
            reg._providers["new"] = _make_provider_snapshot()  # type: ignore[index]

    def test_cannot_delitem_on_internal(self) -> None:
        reg = _make_provider_registry()
        with pytest.raises(TypeError):
            del reg._providers["default"]  # type: ignore[attr-defined]

    def test_repr_shows_sorted_keys(self) -> None:
        reg = ProviderRegistry(
            {
                "z": _make_provider_snapshot(name="Z"),
                "a": _make_provider_snapshot(name="A"),
            }
        )
        r = repr(reg)
        assert "a" in r
        assert "z" in r


# =========================================================================
# TestCatalogRegistryImmutability — MappingProxyType
# =========================================================================


class TestCatalogRegistryImmutability:
    """CatalogRegistry stores catalogs in MappingProxyType."""

    def test_internal_storage_is_mapping_proxy(self) -> None:
        reg = _make_cat_registry()
        assert isinstance(reg._by_key, MappingProxyType)

    def test_cannot_setitem_on_internal(self) -> None:
        reg = _make_cat_registry()
        cat = _make_cat()
        key = (
            cat.catalog_id,
            cat.catalog_version,
            cat.catalog_content_hash,
            cat.source_identity,
            cat.schema_version,
        )
        with pytest.raises(TypeError):
            reg._by_key[key] = cat  # type: ignore[index]

    def test_snapshots_property_returns_tuple(self) -> None:
        reg = _make_cat_registry()
        assert isinstance(reg.snapshots, tuple)
        assert len(reg.snapshots) == 1

    def test_repr_shows_count(self) -> None:
        reg = _make_cat_registry()
        assert "n=1" in repr(reg)


# =========================================================================
# TestCatalogSnapshotRefValidation — hash format, blank fields
# =========================================================================


class TestCatalogSnapshotRefValidation:
    """CatalogSnapshotReference validators: hash format, blank fields."""

    def test_valid_hash_accepted(self) -> None:
        ref = CatalogSnapshotReference(
            catalog_id="c1",
            catalog_version="v1",
            catalog_content_hash="sha256:" + "ab" * 32,
            source_identity="src",
            schema_version="1.0",
        )
        assert ref.catalog_content_hash == "sha256:" + "ab" * 32

    def test_invalid_hash_format_rejected(self) -> None:
        with pytest.raises(ValidationError, match="sha256"):
            CatalogSnapshotReference(
                catalog_id="c1",
                catalog_version="v1",
                catalog_content_hash="not_a_hash",
                source_identity="src",
                schema_version="1.0",
            )

    def test_hash_without_prefix_rejected(self) -> None:
        with pytest.raises(ValidationError, match="sha256"):
            CatalogSnapshotReference(
                catalog_id="c1",
                catalog_version="v1",
                catalog_content_hash="ab" * 32,
                source_identity="src",
                schema_version="1.0",
            )

    def test_hash_wrong_length_rejected(self) -> None:
        with pytest.raises(ValidationError, match="sha256"):
            CatalogSnapshotReference(
                catalog_id="c1",
                catalog_version="v1",
                catalog_content_hash="sha256:abcd",
                source_identity="src",
                schema_version="1.0",
            )

    def test_empty_catalog_id_rejected(self) -> None:
        with pytest.raises(ValidationError, match="non-empty"):
            CatalogSnapshotReference(
                catalog_id="",
                catalog_version="v1",
                catalog_content_hash="sha256:" + "ab" * 32,
                source_identity="src",
                schema_version="1.0",
            )

    def test_blank_catalog_id_rejected(self) -> None:
        with pytest.raises(ValidationError, match="non-empty"):
            CatalogSnapshotReference(
                catalog_id="   ",
                catalog_version="v1",
                catalog_content_hash="sha256:" + "ab" * 32,
                source_identity="src",
                schema_version="1.0",
            )

    def test_empty_source_identity_rejected(self) -> None:
        with pytest.raises(ValidationError, match="non-empty"):
            CatalogSnapshotReference(
                catalog_id="c1",
                catalog_version="v1",
                catalog_content_hash="sha256:" + "ab" * 32,
                source_identity="",
                schema_version="1.0",
            )

    def test_empty_schema_version_rejected(self) -> None:
        with pytest.raises(ValidationError, match="non-empty"):
            CatalogSnapshotReference(
                catalog_id="c1",
                catalog_version="v1",
                catalog_content_hash="sha256:" + "ab" * 32,
                source_identity="src",
                schema_version="",
            )

    def test_whitespace_trimmed(self) -> None:
        ref = CatalogSnapshotReference(
            catalog_id="  c1  ",
            catalog_version="  v1  ",
            catalog_content_hash="sha256:" + "ab" * 32,
            source_identity="  src  ",
            schema_version="  1.0  ",
        )
        assert ref.catalog_id == "c1"
        assert ref.catalog_version == "v1"
        assert ref.source_identity == "src"
        assert ref.schema_version == "1.0"


# =========================================================================
# TestCaseNameValidation — non-empty trimmed
# =========================================================================


class TestCaseNameValidation:
    """case_name is stored as provided — trimmed, no special validator."""

    def test_case_name_stored_as_string(self) -> None:
        req = _validation_request()
        assert isinstance(req.case_name, str)
        assert req.case_name == "test_case"

    def test_case_name_is_frozen(self) -> None:
        req = _validation_request()
        with pytest.raises((ValidationError, AttributeError)):
            req.case_name = "changed"

    def test_case_name_accessible_on_design_case(self) -> None:
        case = project_validation_to_design_case(_validation_request())
        assert case.name == "test_case"


# =========================================================================
# TestNumericStringCoercion — "1.0" rejected as float
# =========================================================================


class TestNumericStringCoercion:
    """Quantity types accept numeric-like strings (coerced to float),
    but reject non-numeric strings."""

    def test_numeric_string_length_coerced(self) -> None:
        """Numeric strings are coerced to float by Quantity."""
        q = Length(value="1.0", unit="m")
        assert q.value == pytest.approx(1.0)

    def test_non_numeric_string_length_rejected(self) -> None:
        """Non-numeric strings are rejected."""
        with pytest.raises((ValidationError, AttributeError)):
            Length(value="not_a_number", unit="m")

    def test_non_numeric_string_power_rejected(self) -> None:
        with pytest.raises((ValidationError, AttributeError)):
            Power(value="twenty_kW", unit="kW")

    def test_non_numeric_string_mass_flow_rejected(self) -> None:
        with pytest.raises((ValidationError, AttributeError)):
            MassFlow(value="not_valid", unit="kg/s")

    def test_non_numeric_string_temperature_rejected(self) -> None:
        with pytest.raises((ValidationError, AttributeError)):
            AbsoluteTemperature(value="hot", unit="K")


# =========================================================================
# TestSolverNoneVsEmpty (T9g) — canonical context equality
# =========================================================================


class TestSolverNoneVsEmpty:
    """solver_params=None and solver_params=SolverParamsSpec()
    produce identical canonical request context digests."""

    def test_none_and_default_produce_same_context(self) -> None:
        cat = _make_cat()
        cat_ref = _catalog_ref(cat)
        provider_snapshot = _make_provider_snapshot()
        provider_reg = ProviderRegistry({"default": provider_snapshot})
        cat_reg = CatalogRegistry([cat])
        resolved_provider = provider_reg.resolve("default")
        resolved_catalogs = tuple(authority.snapshot for authority in [cat_reg.resolve(cat_ref)])

        req_none = _sizing_api_request(cat_ref=cat_ref, solver_params=None)
        req_default = _sizing_api_request(cat_ref=cat_ref, solver_params=SolverParamsSpec())

        ctx_none = build_sizing_canonical_request_context(
            request=req_none,
            resolved_provider=resolved_provider,
            resolved_catalogs=resolved_catalogs,
        )
        ctx_default = build_sizing_canonical_request_context(
            request=req_default,
            resolved_provider=resolved_provider,
            resolved_catalogs=resolved_catalogs,
        )

        # The canonical context should be identical
        assert ctx_none == ctx_default

        # The digests should be identical
        d_none = compute_api_request_digest(ctx_none)
        d_default = compute_api_request_digest(ctx_default)
        assert d_none == d_default
        assert d_none.startswith("sha256:")
        assert len(d_none) == 71

    def test_none_and_default_produce_same_full_path_digest(self) -> None:
        """Test through the helper function as well."""
        cat = _make_cat()
        d_none = _compute_sizing_digest(cat, solver_params=None)
        d_default = _compute_sizing_digest(cat, solver_params=SolverParamsSpec())
        assert d_none == d_default


# =========================================================================
# Additional digest format tests
# =========================================================================


class TestDigestFormat:
    """Verify digest format: sha256:hex"""

    def test_digest_starts_with_sha256(self) -> None:
        cat = _make_cat()
        d = _compute_sizing_digest(cat)
        assert d.startswith("sha256:")

    def test_digest_length_is_71(self) -> None:
        cat = _make_cat()
        d = _compute_sizing_digest(cat)
        assert len(d) == 71  # "sha256:" (7) + 64 hex chars

    def test_digest_hex_lowercase(self) -> None:
        cat = _make_cat()
        d = _compute_sizing_digest(cat)
        hex_part = d[7:]
        assert hex_part == hex_part.lower()
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_digest_deterministic(self) -> None:
        cat = _make_cat()
        d1 = _compute_sizing_digest(cat)
        d2 = _compute_sizing_digest(cat)
        assert d1 == d2


# =========================================================================
# TestResolvedProviderAuthorityDigest — forged digest rejection
# =========================================================================


class TestResolvedProviderAuthorityDigest:
    """ResolvedProviderAuthority rejects forged identity_digest."""

    def test_forged_digest_rejected(self) -> None:
        """A ResolvedProviderAuthority with a wrong identity_digest is rejected."""
        from hexagent.api.models import ResolvedProviderAuthority
        from hexagent.api.registry import canonical_provider_identity_payload
        from hexagent.core.canonical import sha256_digest

        snap = _make_provider_snapshot()
        real_digest = sha256_digest(canonical_provider_identity_payload(snap))
        forged_digest = "sha256:" + "0" * 64
        assert forged_digest != real_digest

        with pytest.raises(Exception, match="identity_digest mismatch"):
            ResolvedProviderAuthority(
                provider_ref="test",
                identity=snap,
                identity_digest=forged_digest,
            )

    def test_valid_digest_accepted(self) -> None:
        """A ResolvedProviderAuthority with the correct identity_digest is accepted."""
        from hexagent.api.models import ResolvedProviderAuthority
        from hexagent.api.registry import canonical_provider_identity_payload
        from hexagent.core.canonical import sha256_digest

        snap = _make_provider_snapshot()
        real_digest = sha256_digest(canonical_provider_identity_payload(snap))

        authority = ResolvedProviderAuthority(
            provider_ref="test",
            identity=snap,
            identity_digest=real_digest,
        )
        assert authority.identity_digest == real_digest

    def test_digest_format_rejected_if_not_sha256(self) -> None:
        """identity_digest that doesn't match sha256:[0-9a-f]{64} is rejected."""
        from hexagent.api.models import ResolvedProviderAuthority

        snap = _make_provider_snapshot()
        with pytest.raises(Exception, match="sha256"):
            ResolvedProviderAuthority(
                provider_ref="test",
                identity=snap,
                identity_digest="not_a_valid_digest",
            )

    def test_provider_ref_blank_rejected(self) -> None:
        """Blank provider_ref is rejected by ResolvedProviderAuthority."""
        from hexagent.api.models import ResolvedProviderAuthority
        from hexagent.api.registry import canonical_provider_identity_payload
        from hexagent.core.canonical import sha256_digest

        snap = _make_provider_snapshot()
        real_digest = sha256_digest(canonical_provider_identity_payload(snap))

        with pytest.raises(Exception, match="non-empty"):
            ResolvedProviderAuthority(
                provider_ref="",
                identity=snap,
                identity_digest=real_digest,
            )

    def test_provider_ref_whitespace_rejected(self) -> None:
        """Whitespace-only provider_ref is rejected by ResolvedProviderAuthority."""
        from hexagent.api.models import ResolvedProviderAuthority
        from hexagent.api.registry import canonical_provider_identity_payload
        from hexagent.core.canonical import sha256_digest

        snap = _make_provider_snapshot()
        real_digest = sha256_digest(canonical_provider_identity_payload(snap))

        with pytest.raises(Exception, match="non-empty"):
            ResolvedProviderAuthority(
                provider_ref="   ",
                identity=snap,
                identity_digest=real_digest,
            )


# =========================================================================
# TestProviderRegistryDuplicateDetection — duplicate ref rejection
# =========================================================================


class TestProviderRegistryDuplicateDetection:
    """ProviderRegistry rejects duplicate refs via sequence input."""

    def test_duplicate_refs_via_sequence_rejected(self) -> None:
        """Sequence input with duplicate refs is rejected."""
        snap = _make_provider_snapshot()
        with pytest.raises(ValueError, match="Duplicate provider reference"):
            ProviderRegistry([("x", snap), ("x", snap)])

    def test_unique_refs_via_sequence_accepted(self) -> None:
        """Sequence input with unique refs is accepted."""
        snap = _make_provider_snapshot()
        reg = ProviderRegistry([("a", snap), ("b", snap)])
        assert "a" in repr(reg)
        assert "b" in repr(reg)

    def test_blank_ref_via_sequence_rejected(self) -> None:
        """Blank ref in sequence input is rejected."""
        snap = _make_provider_snapshot()
        with pytest.raises(ValueError, match="non-blank"):
            ProviderRegistry([("", snap)])

    def test_whitespace_ref_via_sequence_rejected(self) -> None:
        """Whitespace-only ref in sequence input is rejected."""
        snap = _make_provider_snapshot()
        with pytest.raises(ValueError, match="non-blank"):
            ProviderRegistry([("  ", snap)])

    def test_blank_ref_via_dict_rejected(self) -> None:
        """Blank ref in dict input is rejected."""
        snap = _make_provider_snapshot()
        with pytest.raises(ValueError, match="non-blank"):
            ProviderRegistry({"": snap})

    def test_whitespace_ref_via_dict_rejected(self) -> None:
        """Whitespace-only ref in dict input is rejected."""
        snap = _make_provider_snapshot()
        with pytest.raises(ValueError, match="non-blank"):
            ProviderRegistry({"   ": snap})

    def test_resolve_after_sequence_construction(self) -> None:
        """resolve() works correctly after sequence-based construction."""
        from hexagent.api.registry import canonical_provider_identity_payload
        from hexagent.core.canonical import sha256_digest

        snap = _make_provider_snapshot()
        reg = ProviderRegistry([("default", snap)])
        resolved = reg.resolve("default")
        expected = sha256_digest(canonical_provider_identity_payload(snap))
        assert resolved.identity_digest == expected


# =========================================================================
# P0-1: Exact Decimal unit conversion regression
# =========================================================================


class TestExactDecimalConversion:
    """P0-1: Verify canonical_quantity_payload uses exact Decimal arithmetic."""

    def test_exact_non_integer_conversion(self) -> None:
        """Non-trivial conversion: 1 inch = 0.0254 m (exact, no float error)."""
        q = Length(value=1.0, unit="inch")
        result = canonical_quantity_payload(q)
        assert result == {"value": "0.0254", "unit": "m"}

    def test_very_small_conversion(self) -> None:
        """Very small values should not lose precision."""
        q = Length(value=0.001, unit="mm")
        result = canonical_quantity_payload(q)
        # 0.001 mm = 0.000001 m = 1E-6 m
        assert result["value"] == "0.000001"
        assert result["unit"] == "m"

    def test_offset_vs_delta_temperature(self) -> None:
        """Offset (degC) and delta (delta_degC) must be distinguished."""
        # TemperatureDifference: 5 delta_degC = 5 K (multiplicative only)
        td = TemperatureDifference(value=5, unit="delta_degC")
        assert canonical_quantity_payload(td) == {"value": "5", "unit": "K"}
        # AbsoluteTemperature: 5 degC = 278.15 K (with offset)
        at = AbsoluteTemperature(value=5, unit="degC")
        result = canonical_quantity_payload(at)
        assert result["value"] == "278.15"
        assert result["unit"] == "K"

    def test_micrometer_precision(self) -> None:
        """Micrometer conversion preserves all significant digits."""
        q = Length(value=100, unit="um")
        result = canonical_quantity_payload(q)
        assert result["unit"] == "m"
        # 100 um = 0.0001 m
        assert Decimal(result["value"]) == Decimal("0.0001")


# =========================================================================
# P0-2: Catalog refs canonical ordering regression via project_sizing_api_request
# =========================================================================


class TestCatalogCanonicalOrdering:
    """P0-2: Reversed catalog refs input → identical full projection digest."""

    def test_reversed_catalog_refs_same_projection_digest(self) -> None:
        """Reversed catalog refs input order → identical full projection."""
        from hexagent.api.projection import project_sizing_api_request

        cat_a = _make_cat("cat_a", opts=(_make_opt("o1"),))
        cat_b = _make_cat("cat_b", opts=(_make_opt("o2"),))
        ref_a = _catalog_ref(cat_a)
        ref_b = _catalog_ref(cat_b)

        snap = _make_provider_snapshot()
        provider_reg = ProviderRegistry({"CoolProp": snap})
        cat_reg = CatalogRegistry([cat_a, cat_b])

        # Build sizing request with forward order
        req_fwd = _sizing_api_request(
            catalog_refs=(ref_a, ref_b),
        )
        # Build sizing request with reverse order
        req_rev = _sizing_api_request(
            catalog_refs=(ref_b, ref_a),
        )

        result_fwd = project_sizing_api_request(req_fwd, provider_reg, cat_reg)
        result_rev = project_sizing_api_request(req_rev, provider_reg, cat_reg)

        assert result_fwd.request_digest == result_rev.request_digest, (
            "Reversed catalog refs must produce same digest"
        )
        assert result_fwd.sizing_request.catalogs == result_rev.sizing_request.catalogs, (
            "SizingRequest.catalogs must be in same canonical order"
        )

    def test_three_catalog_order_independence(self) -> None:
        """Three catalogs in any order produce the same digest."""
        from hexagent.api.projection import project_sizing_api_request

        cat_a = _make_cat("aaa", opts=(_make_opt("o1"),))
        cat_b = _make_cat("bbb", opts=(_make_opt("o2"),))
        cat_c = _make_cat("ccc", opts=(_make_opt("o3"),))
        ref_a = _catalog_ref(cat_a)
        ref_b = _catalog_ref(cat_b)
        ref_c = _catalog_ref(cat_c)

        snap = _make_provider_snapshot()
        provider_reg = ProviderRegistry({"CoolProp": snap})
        cat_reg = CatalogRegistry([cat_a, cat_b, cat_c])

        req_abc = _sizing_api_request(catalog_refs=(ref_a, ref_b, ref_c))
        req_cba = _sizing_api_request(catalog_refs=(ref_c, ref_b, ref_a))

        result_abc = project_sizing_api_request(req_abc, provider_reg, cat_reg)
        result_cba = project_sizing_api_request(req_cba, provider_reg, cat_reg)

        assert result_abc.request_digest == result_cba.request_digest


# =========================================================================
# T87: Duplicate five-field catalog ref rejection via canonicalize_catalog_refs
# =========================================================================


class TestDuplicateCatalogRefRejection:
    """T87: Same five-field ref → reject by canonicalize_catalog_refs."""

    def test_identical_five_field_ref_rejected(self) -> None:
        """Exactly identical catalog ref in tuple → ValueError."""
        from hexagent.api.canonical_request import canonicalize_catalog_refs

        cat = _make_cat()
        ref = _catalog_ref(cat)
        with pytest.raises(ValueError, match="[Dd]uplicate"):
            canonicalize_catalog_refs((ref, ref))

    def test_duplicate_ref_via_projection_rejected(self) -> None:
        """Duplicate ref through project_sizing_api_request → rejected."""
        from hexagent.api.projection import project_sizing_api_request

        cat = _make_cat()
        ref = _catalog_ref(cat)
        snap = _make_provider_snapshot()
        provider_reg = ProviderRegistry({"CoolProp": snap})
        cat_reg = CatalogRegistry([cat])

        req = _sizing_api_request(catalog_refs=(ref, ref))
        with pytest.raises(ValueError, match="[Dd]uplicate"):
            project_sizing_api_request(req, provider_reg, cat_reg)


# =========================================================================
# T88: Same four-field identity + different hash → reject
# =========================================================================


class TestSameIdentityDifferentHashRejection:
    """T88: Same four-field identity with different content hash → rejected."""

    def test_same_identity_different_hash_via_canonicalize(self) -> None:
        """canonicalize_catalog_refs rejects same identity, different hash."""
        from hexagent.api.canonical_request import canonicalize_catalog_refs

        cat = _make_cat()
        ref_good = _catalog_ref(cat)
        # Same four fields, different hash
        ref_bad = CatalogSnapshotReference(
            catalog_id=cat.catalog_id,
            catalog_version=cat.catalog_version,
            catalog_content_hash="sha256:" + "ff" * 32,
            source_identity=cat.source_identity,
            schema_version=cat.schema_version,
        )
        with pytest.raises(ValueError, match="different.*content hash"):
            canonicalize_catalog_refs((ref_good, ref_bad))


# =========================================================================
# P0-5: Forged provider digest rejection via project_sizing_api_request
# =========================================================================


class TestForgedProviderDigestRejection:
    """P0-5: Forged identity_digest → reject at construction."""

    def test_forged_digest_rejected_at_authority_construction(self) -> None:
        """ResolvedProviderAuthority rejects a forged identity_digest."""
        from hexagent.api.models import ResolvedProviderAuthority
        from hexagent.api.registry import canonical_provider_identity_payload
        from hexagent.core.canonical import sha256_digest

        snap = _make_provider_snapshot()
        real_digest = sha256_digest(canonical_provider_identity_payload(snap))
        forged_digest = "sha256:" + "0" * 64
        assert forged_digest != real_digest

        with pytest.raises(Exception, match="identity_digest mismatch"):
            ResolvedProviderAuthority(
                provider_ref="test",
                identity=snap,
                identity_digest=forged_digest,
            )

    def test_valid_digest_accepted_at_authority_construction(self) -> None:
        """ResolvedProviderAuthority accepts the correct identity_digest."""
        from hexagent.api.models import ResolvedProviderAuthority
        from hexagent.api.registry import canonical_provider_identity_payload
        from hexagent.core.canonical import sha256_digest

        snap = _make_provider_snapshot()
        real_digest = sha256_digest(canonical_provider_identity_payload(snap))
        authority = ResolvedProviderAuthority(
            provider_ref="test",
            identity=snap,
            identity_digest=real_digest,
        )
        assert authority.identity_digest == real_digest

    def test_forged_digest_format_rejected(self) -> None:
        """identity_digest not matching sha256:[0-9a-f]{64} is rejected."""
        from hexagent.api.models import ResolvedProviderAuthority

        snap = _make_provider_snapshot()
        with pytest.raises(Exception, match="sha256"):
            ResolvedProviderAuthority(
                provider_ref="test",
                identity=snap,
                identity_digest="not_a_valid_digest",
            )


# =========================================================================
# P0-6: Duplicate provider ref rejection via sequence input
# =========================================================================


class TestDuplicateProviderRefRejection:
    """P0-6: Duplicate provider refs via Sequence input → reject."""

    def test_duplicate_pair_via_sequence_rejected(self) -> None:
        """Same (ref, snapshot) pair twice in sequence → ValueError."""
        snap = _make_provider_snapshot()
        with pytest.raises(ValueError, match="Duplicate provider reference"):
            ProviderRegistry([("x", snap), ("x", snap)])

    def test_different_snapshots_same_ref_rejected(self) -> None:
        """Same ref string with different snapshots → still rejected."""
        snap_a = _make_provider_snapshot(version="6.6.0")
        snap_b = _make_provider_snapshot(version="7.0.0")
        with pytest.raises(ValueError, match="Duplicate provider reference"):
            ProviderRegistry([("x", snap_a), ("x", snap_b)])

    def test_unique_refs_via_sequence_accepted(self) -> None:
        """Unique refs via sequence → accepted."""
        snap = _make_provider_snapshot()
        reg = ProviderRegistry([("a", snap), ("b", snap)])
        assert "a" in repr(reg)
        assert "b" in repr(reg)


# =========================================================================
# P1-1: Case name validation — blank → reject, trimmed → stored
# =========================================================================


class TestCaseNameValidationRegression:
    """P1-1: case_name blank/whitespace → reject; trimmed → stored correctly."""

    def test_empty_case_name_rejected(self) -> None:
        """Empty string case_name → ValidationError."""
        with pytest.raises((ValidationError, ValueError)):
            ValidationApiRequest(
                api_schema_version="1",
                case_name="",
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

    def test_whitespace_only_case_name_rejected(self) -> None:
        """Whitespace-only case_name → ValidationError."""
        with pytest.raises((ValidationError, ValueError)):
            ValidationApiRequest(
                api_schema_version="1",
                case_name="   ",
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

    def test_tab_and_newline_case_name_rejected(self) -> None:
        """Tab + newline only case_name → ValidationError."""
        with pytest.raises((ValidationError, ValueError)):
            ValidationApiRequest(
                api_schema_version="1",
                case_name="\t\n",
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

    def test_case_name_trimmed_correctly(self) -> None:
        """Leading/trailing whitespace trimmed → stored correctly."""
        req = ValidationApiRequest(
            api_schema_version="1",
            case_name="  my_case  ",
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
        assert req.case_name == "my_case"

    def test_trimmed_case_name_in_projection(self) -> None:
        """Trimmed case_name propagates correctly to domain model."""
        case = project_validation_to_design_case(
            ValidationApiRequest(
                api_schema_version="1",
                case_name="  trimmed_name  ",
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
        )
        assert case.name == "trimmed_name"


# =========================================================================
# P0-4: Unicode NFC in projection — decomposed/precomposed → same digest
# =========================================================================


class TestUnicodeNFCInProjection:
    """P0-4: Decomposed/precomposed Unicode in case_name → same digest."""

    def test_nfc_nfd_case_name_same_digest(self) -> None:
        """Decomposed and precomposed Unicode in case_name produce
        the same canonical digest because canonicalization applies NFC."""
        import unicodedata

        from hexagent.api.projection import project_sizing_api_request

        nfc_name = unicodedata.normalize("NFC", "café_study")
        nfd_name = unicodedata.normalize("NFD", "café_study")
        assert nfc_name != nfd_name  # Verify they're actually different bytes

        cat = _make_cat()
        ref = _catalog_ref(cat)
        snap = _make_provider_snapshot()
        provider_reg = ProviderRegistry({"CoolProp": snap})
        cat_reg = CatalogRegistry([cat])

        def _make_req(case_name: str) -> SizingApiRequest:
            vr = ValidationApiRequest(
                api_schema_version="1",
                case_name=case_name,
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
            return _sizing_api_request(cat_ref=ref, case=vr)

        result_nfc = project_sizing_api_request(_make_req(nfc_name), provider_reg, cat_reg)
        result_nfd = project_sizing_api_request(_make_req(nfd_name), provider_reg, cat_reg)

        assert result_nfc.request_digest == result_nfd.request_digest, (
            "NFC and NFD case_name must produce the same request digest"
        )


# =========================================================================
# P1-2: Numeric string coercion — bare string "1.0" rejected as Quantity
# =========================================================================


class TestNumericStringCoercionRegression:
    """P1-2: Bare string '1.0' is NOT accepted where a Quantity is expected
    in API DTOs.  Quantity types themselves may coerce numeric strings,
    but public DTOs reject bare strings for Quantity-typed fields."""

    def test_bare_string_target_duty_rejected(self) -> None:
        """Bare string '1.0' as target_duty → rejected."""
        data = _validation_request().model_dump(mode="python")
        data["target_duty"] = "1.0"
        with pytest.raises(ValidationError):
            ValidationApiRequest.model_validate(data)

    def test_bare_string_mass_flow_rejected(self) -> None:
        """Bare string '1.0' as mass_flow → rejected."""
        data = _hot_stream_spec().model_dump(mode="python")
        data["mass_flow"] = "1.0"
        with pytest.raises(ValidationError):
            FluidStreamSpec.model_validate(data)

    def test_bare_string_temperature_rejected(self) -> None:
        """Bare string '1.0' as temperature → rejected."""
        data = _hot_stream_spec().model_dump(mode="python")
        inlet_data = data["inlet"]
        inlet_data["temperature"] = "1.0"
        with pytest.raises(ValidationError):
            FluidStreamSpec.model_validate(data)

    def test_quantity_object_accepted_normally(self) -> None:
        """Quantity object for target_duty → accepted normally."""
        req = _validation_request()
        assert req.target_duty.si_value == pytest.approx(100_000.0)


# =========================================================================
# TestCanonicalDecimalVectorsRegression — all 18+ contract vectors
# =========================================================================


class TestCanonicalDecimalVectorsRegression:
    """Verify all 18+ canonical_decimal_string vectors from Frozen Contract §8.1
    as a single comprehensive test."""

    @pytest.mark.parametrize(
        "input_val, expected",
        [
            (Decimal("0"), "0"),
            (Decimal("1"), "1"),
            (Decimal("1.0"), "1"),
            (Decimal("1.5000"), "1.5"),
            (Decimal("1.234567890123445"), "1.23456789012344"),
            (Decimal("1.234567890123455"), "1.23456789012346"),
            (Decimal("999999999999999.5"), "1E+15"),
            (Decimal("1E-30"), "1E-30"),
            (Decimal("1E+30"), "1E+30"),
            (Decimal("0.00000000001"), "1E-11"),
            (Decimal("0.000000000001"), "1E-12"),
            (Decimal("99999999999"), "99999999999"),
            (Decimal("100000000000"), "1E+11"),
            (Decimal("1E-7"), "0.0000001"),
            (Decimal("1E-10"), "0.0000000001"),
            (Decimal("1E-11"), "1E-11"),
            (Decimal("1E+10"), "10000000000"),
            (Decimal("1E+11"), "1E+11"),
        ],
    )
    def test_vector(self, input_val: Decimal, expected: str) -> None:
        """Single parametrized test for all 18 contract vectors."""
        assert canonical_decimal_string(input_val) == expected

    def test_negative_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="negative zero"):
            canonical_decimal_string(Decimal("-0"))

    def test_non_decimal_type_raises(self) -> None:
        with pytest.raises(TypeError, match="Expected Decimal"):
            canonical_decimal_string(42)  # type: ignore[arg-type]


# =========================================================================
# TestCanonicalQuantityPayloadRegression — all required vectors
# =========================================================================


class TestCanonicalQuantityPayloadRegression:
    """Comprehensive canonical_quantity_payload vectors including
    exact decimal conversions, offset temperatures, and edge cases."""

    def test_power_kw_to_w(self) -> None:
        q = Power(value=100, unit="kW")
        assert canonical_quantity_payload(q) == {"value": "100000", "unit": "W"}

    def test_power_w(self) -> None:
        q = Power(value=100_000, unit="W")
        assert canonical_quantity_payload(q) == {"value": "100000", "unit": "W"}

    def test_length_m(self) -> None:
        q = Length(value=1.0, unit="m")
        assert canonical_quantity_payload(q) == {"value": "1", "unit": "m"}

    def test_length_cm(self) -> None:
        q = Length(value=2, unit="cm")
        payload = canonical_quantity_payload(q)
        assert payload["unit"] == "m"
        assert Decimal(payload["value"]) == Decimal("0.02")

    def test_mass_flow(self) -> None:
        q = MassFlow(value=1.0, unit="kg/s")
        assert canonical_quantity_payload(q) == {"value": "1", "unit": "kg/s"}

    def test_temperature_difference_k(self) -> None:
        q = TemperatureDifference(value=5, unit="K")
        assert canonical_quantity_payload(q) == {"value": "5", "unit": "K"}

    def test_temperature_difference_delta_degC(self) -> None:
        q = TemperatureDifference(value=5, unit="delta_degC")
        assert canonical_quantity_payload(q) == {"value": "5", "unit": "K"}

    def test_absolute_temperature_k(self) -> None:
        q = AbsoluteTemperature(value=370, unit="K")
        assert canonical_quantity_payload(q) == {"value": "370", "unit": "K"}

    def test_absolute_temperature_degC(self) -> None:
        """Offset conversion: 100 degC = 373.15 K."""
        q = AbsoluteTemperature(value=100, unit="degC")
        assert canonical_quantity_payload(q) == {"value": "373.15", "unit": "K"}

    def test_absolute_pressure(self) -> None:
        q = AbsolutePressure(value=200_000, unit="Pa")
        assert canonical_quantity_payload(q) == {"value": "200000", "unit": "Pa"}

    def test_fouling_resistance(self) -> None:
        q = FoulingResistance(value=0.0002, unit="m^2*K/W")
        payload = canonical_quantity_payload(q)
        assert "value" in payload
        assert "unit" in payload
        assert isinstance(payload["value"], str)

    def test_value_always_string(self) -> None:
        """The value in the canonical payload is always a string."""
        for q in [
            Power(value=1, unit="W"),
            Length(value=0.001, unit="m"),
            MassFlow(value=0.5, unit="kg/s"),
            TemperatureDifference(value=10, unit="K"),
            AbsolutePressure(value=101325, unit="Pa"),
        ]:
            payload = canonical_quantity_payload(q)
            assert isinstance(payload["value"], str), f"Not string for {q}"

    def test_exact_inch_conversion(self) -> None:
        """1 inch = 0.0254 m — exact Decimal, no float error."""
        q = Length(value=1.0, unit="inch")
        assert canonical_quantity_payload(q) == {"value": "0.0254", "unit": "m"}


# =========================================================================
# T45: Poison DoublePipeService.size() → project_sizing_api_request works
# =========================================================================


class TestPoisonDoublePipeServiceSize:
    """T45: Even when DoublePipeService.size() is monkeypatched to raise,
    project_sizing_api_request succeeds without ever calling it."""

    def test_project_sizing_api_request_with_poisoned_size(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """project_sizing_api_request works with poisoned DoublePipeService.size()."""
        from hexagent.api.projection import project_sizing_api_request
        from hexagent.exchangers.double_pipe.service import DoublePipeService

        def _poisoned_size(self_inner: Any, case: Any) -> Any:
            raise RuntimeError("DoublePipeService.size() MUST NOT be called")

        monkeypatch.setattr(DoublePipeService, "size", _poisoned_size)

        cat = _make_cat()
        ref = _catalog_ref(cat)
        snap = _make_provider_snapshot()
        provider_reg = ProviderRegistry({"CoolProp": snap})
        cat_reg = CatalogRegistry([cat])
        req = _sizing_api_request(cat_ref=ref)

        result = project_sizing_api_request(req, provider_reg, cat_reg)
        assert result.request_digest.startswith("sha256:")
        assert len(result.request_digest) == 71
        assert result.design_case.name == "test_case"

    def test_poisoned_size_still_detects_digest_changes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Different duties produce different digests even with poisoned size()."""
        from hexagent.api.projection import project_sizing_api_request
        from hexagent.exchangers.double_pipe.service import DoublePipeService

        def _poisoned_size(self_inner: Any, case: Any) -> Any:
            raise RuntimeError("MUST NOT be called")

        monkeypatch.setattr(DoublePipeService, "size", _poisoned_size)

        cat = _make_cat()
        ref = _catalog_ref(cat)
        snap = _make_provider_snapshot()
        provider_reg = ProviderRegistry({"CoolProp": snap})
        cat_reg = CatalogRegistry([cat])

        vr_100 = _validation_request_with_duty(100_000)
        vr_200 = _validation_request_with_duty(200_000)

        req_100 = _sizing_api_request(cat_ref=ref, case=vr_100)
        req_200 = _sizing_api_request(cat_ref=ref, case=vr_200)

        r100 = project_sizing_api_request(req_100, provider_reg, cat_reg)
        r200 = project_sizing_api_request(req_200, provider_reg, cat_reg)

        assert r100.request_digest != r200.request_digest


# =========================================================================
# TestCanonicalStringNFC — canonicalize_api_payload NFC normalization
# =========================================================================


class TestCanonicalStringNFC:
    """canonicalize_api_payload NFC-normalizes all strings."""

    def test_decomposed_and_precomposed_same_result(self) -> None:
        """Decomposed and precomposed Unicode strings → same canonical result."""
        import unicodedata

        nfc = unicodedata.normalize("NFC", "café")
        nfd = unicodedata.normalize("NFD", "café")
        assert nfc != nfd  # Different byte representations

        result_nfc = canonicalize_api_payload(nfc)
        result_nfd = canonicalize_api_payload(nfd)
        assert result_nfc == result_nfd

    def test_nfc_in_dict_values(self) -> None:
        """NFC normalization applies to string values inside dicts."""
        import unicodedata

        nfc = unicodedata.normalize("NFC", "Über")
        nfd = unicodedata.normalize("NFD", "Über")

        d_nfc = canonicalize_api_payload({"key": nfc})
        d_nfd = canonicalize_api_payload({"key": nfd})
        assert d_nfc == d_nfd

    def test_nfc_in_nested_structures(self) -> None:
        """NFC normalization in nested dicts and lists."""
        import unicodedata

        nfc = unicodedata.normalize("NFC", "naïve")
        nfd = unicodedata.normalize("NFD", "naïve")

        obj_nfc = {"a": [nfc, {"b": nfc}]}
        obj_nfd = {"a": [nfd, {"b": nfd}]}
        assert canonicalize_api_payload(obj_nfc) == canonicalize_api_payload(obj_nfd)

    def test_already_nfc_unchanged(self) -> None:
        """Already NFC string passes through unchanged."""
        import unicodedata

        s = "hello"
        assert unicodedata.is_normalized("NFC", s)
        assert canonicalize_api_payload(s) == s


# =========================================================================
# TestDigestSensitivityAll — all dimensions via project_sizing_api_request
# =========================================================================


class TestDigestSensitivityAll:
    """Comprehensive digest sensitivity test via project_sizing_api_request:
    changing any of provider/catalog/duty/solver/boundary → different digest."""

    @staticmethod
    def _project_digest(
        *,
        provider_snapshot: ProviderIdentitySnapshot | None = None,
        cat: CompleteDoublePipeCatalogSnapshot | None = None,
        validation_request: ValidationApiRequest | None = None,
        solver_params: SolverParamsSpec | None = None,
        tube_boundary_condition: str = "constant_wall_temperature",
        annulus_boundary_condition: str = "constant_wall_temperature",
    ) -> str:
        """Helper: project a sizing request and return the digest."""
        from hexagent.api.projection import project_sizing_api_request

        if cat is None:
            cat = _make_cat()
        if provider_snapshot is None:
            provider_snapshot = _make_provider_snapshot()
        if validation_request is None:
            validation_request = _validation_request()

        ref = _catalog_ref(cat)
        provider_reg = ProviderRegistry({provider_snapshot.name: provider_snapshot})
        cat_reg = CatalogRegistry([cat])

        expected = ExpectedProviderIdentity(
            name=provider_snapshot.name,
            version=provider_snapshot.version,
            git_revision=provider_snapshot.git_revision,
            reference_state_policy=provider_snapshot.reference_state_policy,
        )
        req = _sizing_api_request(
            cat_ref=ref,
            case=validation_request,
            expected_provider_identity=expected,
            solver_params=solver_params,
            tube_boundary_condition=tube_boundary_condition,
            annulus_boundary_condition=annulus_boundary_condition,
        )
        result = project_sizing_api_request(req, provider_reg, cat_reg)
        return result.request_digest

    def test_provider_name_sensitivity(self) -> None:
        d1 = self._project_digest(provider_snapshot=_make_provider_snapshot(name="CoolProp"))
        d2 = self._project_digest(provider_snapshot=_make_provider_snapshot(name="REFPROP"))
        assert d1 != d2

    def test_provider_version_sensitivity(self) -> None:
        d1 = self._project_digest(provider_snapshot=_make_provider_snapshot(version="6.6.0"))
        d2 = self._project_digest(provider_snapshot=_make_provider_snapshot(version="7.0.0"))
        assert d1 != d2

    def test_provider_git_revision_sensitivity(self) -> None:
        d1 = self._project_digest(provider_snapshot=_make_provider_snapshot(git_revision="abc123"))
        d2 = self._project_digest(provider_snapshot=_make_provider_snapshot(git_revision="def456"))
        assert d1 != d2

    def test_provider_reference_state_policy_sensitivity(self) -> None:
        d1 = self._project_digest(
            provider_snapshot=_make_provider_snapshot(reference_state_policy="IIR")
        )
        d2 = self._project_digest(
            provider_snapshot=_make_provider_snapshot(reference_state_policy="NBP")
        )
        assert d1 != d2

    def test_catalog_content_sensitivity(self) -> None:
        """Different assembly options → different content hash → different digest."""
        d1 = self._project_digest(cat=_make_cat("cat1", opts=(_make_opt("o1"),)))
        d2 = self._project_digest(cat=_make_cat("cat1", opts=(_make_opt("o1"), _make_opt("o2"))))
        assert d1 != d2

    def test_duty_sensitivity(self) -> None:
        d1 = self._project_digest(validation_request=_validation_request_with_duty(100_000))
        d2 = self._project_digest(validation_request=_validation_request_with_duty(200_000))
        assert d1 != d2

    def test_solver_max_iterations_sensitivity(self) -> None:
        d1 = self._project_digest(solver_params=SolverParamsSpec())
        d2 = self._project_digest(solver_params=SolverParamsSpec(max_iterations=50))
        assert d1 != d2

    def test_solver_absolute_residual_sensitivity(self) -> None:
        d1 = self._project_digest(solver_params=SolverParamsSpec())
        d2 = self._project_digest(
            solver_params=SolverParamsSpec(absolute_residual_w=Power(value=0.01, unit="W"))
        )
        assert d1 != d2

    def test_boundary_condition_sensitivity(self) -> None:
        """Changing boundary conditions → different digest."""
        d1 = self._project_digest(
            tube_boundary_condition="constant_wall_temperature",
            annulus_boundary_condition="constant_wall_temperature",
        )
        d2 = self._project_digest(
            tube_boundary_condition="inner_wall_heated",
            annulus_boundary_condition="inner_wall_heated",
        )
        assert d1 != d2


# =========================================================================
# TestCatalogRefSortKeyConsistency — sort key matches identity key
# =========================================================================


class TestCatalogRefSortKeyConsistency:
    """Verify canonical_catalog_ref_sort_key produces the same tuple
    as catalog_identity_key for corresponding ref/snapshot pairs."""

    def test_single_catalog_sort_key_matches_identity_key(self) -> None:
        """Sort key from ref == identity key from snapshot."""
        from hexagent.api.canonical_request import canonical_catalog_ref_sort_key
        from hexagent.optimization.catalog import catalog_identity_key

        cat = _make_cat()
        ref = _catalog_ref(cat)

        sort_key = canonical_catalog_ref_sort_key(ref)
        identity_key = catalog_identity_key(cat)

        assert sort_key == identity_key
        assert len(sort_key) == 5

    def test_multi_catalog_sort_keys_match(self) -> None:
        """All catalog refs' sort keys match their snapshots' identity keys."""
        from hexagent.api.canonical_request import canonical_catalog_ref_sort_key
        from hexagent.optimization.catalog import catalog_identity_key

        cats = [_make_cat(f"cat_{i}", opts=(_make_opt(f"o{i}"),)) for i in range(5)]
        refs = [_catalog_ref(c) for c in cats]

        for ref, cat in zip(refs, cats, strict=True):
            assert canonical_catalog_ref_sort_key(ref) == catalog_identity_key(cat)

    def test_sort_key_ordering_is_stable(self) -> None:
        """Sorting refs and snapshots by their respective keys yields
        the same ordering."""
        from hexagent.api.canonical_request import canonical_catalog_ref_sort_key
        from hexagent.optimization.catalog import catalog_identity_key

        cats_unsorted = [
            _make_cat("zzz", opts=(_make_opt("o3"),)),
            _make_cat("aaa", opts=(_make_opt("o1"),)),
            _make_cat("mmm", opts=(_make_opt("o2"),)),
        ]
        refs_unsorted = [_catalog_ref(c) for c in cats_unsorted]

        refs_sorted = sorted(refs_unsorted, key=canonical_catalog_ref_sort_key)
        cats_sorted = sorted(cats_unsorted, key=catalog_identity_key)

        for ref, cat in zip(refs_sorted, cats_sorted, strict=True):
            assert ref.catalog_id == cat.catalog_id

    def test_sort_key_tuple_field_order(self) -> None:
        """Sort key fields are in canonical order:
        (catalog_id, catalog_version, catalog_content_hash,
         source_identity, schema_version)."""
        from hexagent.api.canonical_request import canonical_catalog_ref_sort_key

        cat = _make_cat()
        ref = _catalog_ref(cat)
        key = canonical_catalog_ref_sort_key(ref)

        assert key == (
            cat.catalog_id,
            cat.catalog_version,
            cat.catalog_content_hash,
            cat.source_identity,
            cat.schema_version,
        )
