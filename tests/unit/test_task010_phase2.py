"""TASK-010 Phase 2 — API contract and service tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from hexagent.api.errors import ApiError, ErrorDetail
from hexagent.api.main import app
from hexagent.api.models import (
    CatalogSnapshotReference,
    FluidStreamSpec,
    SizingApiRequest,
    ValidationApiRequest,
)
from hexagent.api.registry import CatalogRegistry, ProviderRegistry
from hexagent.api.sizing_service import SizingService, SizingServiceResult
from hexagent.core.heat_balance import ProviderIdentitySnapshot
from hexagent.domain.models import (
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
    MassFlow,
    Power,
    TemperatureDifference,
)
from hexagent.optimization.catalog import compute_catalog_content_hash
from hexagent.optimization.context import (
    ExpectedProviderIdentity,
    OptimizationObjective,
)
from hexagent.optimization.models import (
    CompleteDoublePipeAssemblyOption,
    CompleteDoublePipeCatalogSnapshot,
    LengthSource,
)

# =========================================================================
# Helpers
# =========================================================================


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
            length_quantum_m="0.1",
            allowed_effective_lengths_m=(1.0, 2.0, 3.0),
        ),
        manufacturing_option_identity="std",
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
        catalog_content_hash=compute_catalog_content_hash(
            catalog_id=catalog_id,
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=opts,
        ),
    )


def _catalog_ref(
    cat: CompleteDoublePipeCatalogSnapshot,
) -> CatalogSnapshotReference:
    return CatalogSnapshotReference(
        catalog_id=cat.catalog_id,
        catalog_version=cat.catalog_version,
        catalog_content_hash=cat.catalog_content_hash,
        source_identity=cat.source_identity,
        schema_version=cat.schema_version,
    )


def _make_provider_snapshot(**overrides: str) -> ProviderIdentitySnapshot:
    defaults = dict(
        name="CoolProp",
        version="6.6.0",
        git_revision="abc123",
        reference_state_policy="IIR",
        configuration_fingerprint="",
        cache_policy_version="",
    )
    defaults.update(overrides)
    return ProviderIdentitySnapshot(**defaults)


def _make_provider_registry(ref: str = "CoolProp", **overrides: str) -> ProviderRegistry:
    return ProviderRegistry({ref: _make_provider_snapshot(**overrides)})


def _make_cat_registry(
    cats: list[CompleteDoublePipeCatalogSnapshot] | None = None,
) -> CatalogRegistry:
    if cats is None:
        cats = [_make_cat()]
    return CatalogRegistry(cats)


def _fouling_spec() -> FoulingResistanceSpec:
    return FoulingResistanceSpec(
        value=FoulingResistance(value=0.0002, unit="m^2*K/W"),
        source=FoulingSource(
            source_type=FoulingSourceType.STANDARD,
            reference_id="TEMA",
            edition="10th",
            table_or_clause="Table RGP-2.4",
            verification_status=VerificationStatus.VERIFIED,
            note="Clean",
        ),
    )


def _validation_request() -> ValidationApiRequest:
    return ValidationApiRequest(
        api_schema_version="1",
        case_name="test_case",
        hot_stream=FluidStreamSpec(
            fluid=FluidSpec(backend="CoolProp", name="Water", phase_hint="liquid"),
            inlet=TPStateSpec(
                type="TP",
                temperature=AbsoluteTemperature(value=370, unit="K"),
                pressure=AbsolutePressure(value=200000, unit="Pa"),
            ),
            mass_flow=MassFlow(value=1, unit="kg/s"),
            fouling=_fouling_spec(),
        ),
        cold_stream=FluidStreamSpec(
            fluid=FluidSpec(backend="CoolProp", name="Water", phase_hint="liquid"),
            inlet=TPStateSpec(
                type="TP",
                temperature=AbsoluteTemperature(value=300, unit="K"),
                pressure=AbsolutePressure(value=200000, unit="Pa"),
            ),
            mass_flow=MassFlow(value=2, unit="kg/s"),
            fouling=_fouling_spec(),
        ),
        target_duty=Power(value=100000, unit="W"),
        minimum_terminal_delta_t=TemperatureDifference(value=5, unit="K"),
        design_pressure_hot=AbsolutePressure(value=500000, unit="Pa"),
        design_pressure_cold=AbsolutePressure(value=500000, unit="Pa"),
        design_temperature_hot=AbsoluteTemperature(value=400, unit="K"),
        design_temperature_cold=AbsoluteTemperature(value=350, unit="K"),
        required_area_margin_fraction=0.1,
    )


def _sizing_request(**kwargs: object) -> SizingApiRequest:
    cat = _make_cat()
    cat_ref = _catalog_ref(cat)
    defaults: dict[str, object] = dict(
        api_schema_version="1",
        case=_validation_request(),
        catalog_refs=(cat_ref,),
        tube_boundary_condition="constant_wall_temperature",
        annulus_boundary_condition="constant_wall_temperature",
        flow_arrangement="counterflow",
        optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
        requested_top_n=3,
        expected_provider_identity=ExpectedProviderIdentity(
            name="CoolProp",
            version="6.6.0",
            git_revision="abc123",
            reference_state_policy="IIR",
        ),
    )
    defaults.update(kwargs)
    return SizingApiRequest(**defaults)  # type: ignore[arg-type]


# =========================================================================
# SizingService tests
# =========================================================================


class TestSizingService:
    """Test the sizing application service."""

    def test_happy_path_returns_result(self):
        cat = _make_cat()
        cat_reg = _make_cat_registry([cat])
        prov_reg = _make_provider_registry(ref="CoolProp")
        service = SizingService(prov_reg, cat_reg)
        req = _sizing_request()
        result = service.process(req)
        assert isinstance(result, SizingServiceResult)
        assert result.request_digest.startswith("sha256:")
        assert len(result.request_digest) == 71

    def test_result_has_all_artifacts(self):
        cat = _make_cat()
        cat_reg = _make_cat_registry([cat])
        prov_reg = _make_provider_registry(ref="CoolProp")
        service = SizingService(prov_reg, cat_reg)
        req = _sizing_request()
        result = service.process(req)
        assert result.design_case is not None
        assert result.sizing_request is not None
        assert result.sizing_request_identity is not None
        assert result.effective_solver_params is not None
        assert result.resolved_provider is not None
        assert result.resolved_catalogs is not None
        assert result.canonical_request_snapshot is not None
        assert result.request_digest is not None

    def test_request_digest_deterministic(self):
        cat = _make_cat()
        cat_reg = _make_cat_registry([cat])
        prov_reg = _make_provider_registry(ref="CoolProp")
        service = SizingService(prov_reg, cat_reg)
        req = _sizing_request()
        r1 = service.process(req)
        r2 = service.process(req)
        assert r1.request_digest == r2.request_digest
        assert r1.canonical_request_snapshot == r2.canonical_request_snapshot

    def test_provider_mismatch_raises(self):
        cat = _make_cat()
        cat_reg = _make_cat_registry([cat])
        # Provider version differs from expected
        prov_reg = _make_provider_registry(ref="CoolProp", version="7.0.0")
        service = SizingService(prov_reg, cat_reg)
        req = _sizing_request()
        with pytest.raises(ValueError, match="Provider identity mismatch"):
            service.process(req)

    def test_unknown_provider_raises(self):
        cat = _make_cat()
        cat_reg = _make_cat_registry([cat])
        prov_reg = _make_provider_registry(ref="other")
        service = SizingService(prov_reg, cat_reg)
        req = _sizing_request()
        with pytest.raises(ValueError):
            service.process(req)

    def test_no_calls_to_double_pipe_service_size(self, monkeypatch):
        """Prove the service never calls the forbidden assumed-U path."""
        from hexagent.exchangers.double_pipe.service import DoublePipeService

        def _poison(*args: object, **kwargs: object) -> None:
            raise RuntimeError("DoublePipeService.size() was called!")

        monkeypatch.setattr(DoublePipeService, "size", _poison)
        cat = _make_cat()
        cat_reg = _make_cat_registry([cat])
        prov_reg = _make_provider_registry(ref="CoolProp")
        service = SizingService(prov_reg, cat_reg)
        req = _sizing_request()
        result = service.process(req)
        assert result.request_digest.startswith("sha256:")


# =========================================================================
# API endpoint tests
# =========================================================================


class TestSizingEndpoint:
    """Test the /v1/sizing/double-pipe endpoint."""

    def test_endpoint_exists(self):
        client = TestClient(app, raise_server_exceptions=False)
        # POST with empty body should get 422 (validation error), not 404
        response = client.post("/v1/sizing/double-pipe", json={})
        assert response.status_code == 422

    def test_invalid_request_returns_422(self):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/v1/sizing/double-pipe", json={"invalid": True})
        assert response.status_code == 422

    def test_extra_fields_rejected(self):
        client = TestClient(app, raise_server_exceptions=False)
        payload = _sizing_request().model_dump(mode="json")
        payload["bogus_field"] = True
        response = client.post("/v1/sizing/double-pipe", json=payload)
        assert response.status_code == 422


# =========================================================================
# Structured error tests
# =========================================================================


class TestStructuredErrors:
    """Test ApiError and ErrorDetail models."""

    def test_api_error_frozen(self):
        err = ApiError(
            error_code="TEST",
            message="test message",
            details=(ErrorDetail(code="test_code", message="detail"),),
        )
        with pytest.raises(ValidationError):
            err.error_code = "OTHER"

    def test_error_detail_frozen(self):
        detail = ErrorDetail(code="test", message="msg")
        with pytest.raises(ValidationError):
            detail.code = "other"

    def test_error_detail_with_path(self):
        detail = ErrorDetail(
            path=("case", "hot_stream", "mass_flow"),
            code="invalid_type",
            message="Expected Quantity",
            rejected_value_preview='"not_a_number"',
        )
        assert detail.path == ("case", "hot_stream", "mass_flow")
        assert detail.rejected_value_preview == '"not_a_number"'
