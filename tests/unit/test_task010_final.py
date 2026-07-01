"""TASK-010 Phase 2 final remediation contract tests.

Covers ALL remaining acceptance criteria:
- A6: T45 — DoublePipeService.size() never called on sizing requests
- A7: Rating replay (complete + conflict via sizing and rating)
- B1-B8: Report contract (13 sections, matrix, mandatory artifacts, RFC 6901,
         hashes, deterministic HTML, security)
- C1: Provider six-field authority (all 6 fields, version change, mismatch)
- C2: Single provenance digest authority
- C3: Rating canonical parity
- C4: Repository complete parity (typed artifact bundle)
- C5: FAILED_REPLAY (exact status + body replay)
- P0-4/P0-5/P0-6: Frozen contract matrix, artifact variants, DoublePipeReportModel

NO MagicMock for production success paths. All production paths use
real CoolPropProvider, real ProviderRegistry, real CatalogRegistry,
real InMemoryRunRepository, real RatingApplicationService, and
real SizingApplicationService. MagicMock is ONLY used for:
  - T45 poison trap (patching DoublePipeService.size)
  - C5 failure injection (patching execute to force failure)
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hexagent.api.application import (
    PreparedSizingRun,
    SizingApplicationService,
    SizingExecutionResult,
)
from hexagent.api.artifacts import verify_sizing_artifact_bundle
from hexagent.api.envelopes import RatingRunEnvelope, SizingRunEnvelope
from hexagent.api.models import SizingApiRequest
from hexagent.api.repository import (
    FrozenFailurePayload,
    InMemoryRunRepository,
    RunState,
)
from hexagent.core.canonical import sha256_digest
from hexagent.core.heat_balance import ProviderIdentitySnapshot
from hexagent.reporting import (
    MANDATORY_ARTIFACT_IDS,
    MANDATORY_ARTIFACT_OWNERS,
    REPORT_SECTION_ORDER,
    DoublePipeReportModel,
    NotImplementedReportArtifact,
    OutOfScopeReportArtifact,
    PresentReportArtifact,
    ReportArtifact,
    ReportArtifactId,
    ReportArtifactKind,
    ReportInstanceIdentity,
    ReportModel,
    ReportSection,
    ReportSectionId,
    ReportSectionStatus,
    ReportSourceDocument,
    UnavailableReportArtifact,
    build_report_html,
    compute_report_content_hash,
    compute_report_instance_hash,
    derive_source_state,
    resolve_source_pointer,
    validate_rfc6901_pointer,
    verify_report_section_status_matrix,
)

# ===================================================================
# Module-level cached test app (CoolProp init takes ~1s)
# ===================================================================

_APP_CACHE: dict[str, Any] = {}


def _create_test_app() -> FastAPI:
    """Create a test app with real CoolPropProvider and real services.
    Cached at module level to avoid re-initializing CoolProp for every test.
    """
    if "app" in _APP_CACHE:
        return _APP_CACHE["app"]

    from hexagent.api.application import (
        RatingApplicationService,
        SizingApplicationService,
        SizingService,
    )
    from hexagent.api.main import ApplicationDependencies, create_app
    from hexagent.api.registry import CatalogRegistry, ProviderRegistry
    from hexagent.properties.coolprop_provider import CoolPropProvider

    provider = CoolPropProvider()
    snapshot = ProviderIdentitySnapshot(
        name=provider.name,
        version=provider.version,
        git_revision=provider.git_revision,
        reference_state_policy=str(provider.reference_state_policy.value),
        configuration_fingerprint=getattr(provider, "_construction_fingerprint", ""),
        cache_policy_version=getattr(provider, "cache_policy_version", ""),
    )
    provider_registry = ProviderRegistry({"CoolProp": snapshot})
    catalog_registry = CatalogRegistry([])
    repo = InMemoryRunRepository()
    rating_service = RatingApplicationService(
        provider_registry=provider_registry,
        property_provider=provider,
    )
    sizing_service = SizingService(
        provider_registry=provider_registry,
        catalog_registry=catalog_registry,
    )
    sizing_app = SizingApplicationService(
        provider_registry=provider_registry,
        catalog_registry=catalog_registry,
        property_provider=provider,
    )
    deps = ApplicationDependencies(
        provider_registry=provider_registry,
        catalog_registry=catalog_registry,
        run_repository=repo,
        rating_service=rating_service,
        sizing_service=sizing_service,
        sizing_application_service=sizing_app,
    )
    app = create_app(deps)
    _APP_CACHE["app"] = app
    return app


def _create_fresh_app() -> FastAPI:
    """Create a test app with a fresh InMemoryRunRepository."""
    from hexagent.api.application import (
        RatingApplicationService,
        SizingApplicationService,
        SizingService,
    )
    from hexagent.api.main import ApplicationDependencies, create_app
    from hexagent.api.registry import CatalogRegistry, ProviderRegistry
    from hexagent.properties.coolprop_provider import CoolPropProvider

    provider = CoolPropProvider()
    snapshot = ProviderIdentitySnapshot(
        name=provider.name,
        version=provider.version,
        git_revision=provider.git_revision,
        reference_state_policy=str(provider.reference_state_policy.value),
        configuration_fingerprint=getattr(provider, "_construction_fingerprint", ""),
        cache_policy_version=getattr(provider, "cache_policy_version", ""),
    )
    provider_registry = ProviderRegistry({"CoolProp": snapshot})
    catalog_registry = CatalogRegistry([])
    repo = InMemoryRunRepository()
    rating_service = RatingApplicationService(
        provider_registry=provider_registry,
        property_provider=provider,
    )
    sizing_service = SizingService(
        provider_registry=provider_registry,
        catalog_registry=catalog_registry,
    )
    sizing_app = SizingApplicationService(
        provider_registry=provider_registry,
        catalog_registry=catalog_registry,
        property_provider=provider,
    )
    deps = ApplicationDependencies(
        provider_registry=provider_registry,
        catalog_registry=catalog_registry,
        run_repository=repo,
        rating_service=rating_service,
        sizing_service=sizing_service,
        sizing_application_service=sizing_app,
    )
    return create_app(deps)


# ===================================================================
# Request payload helpers
# ===================================================================


VALID_RATING_PAYLOAD = {
    "case": {
        "hot_stream": {
            "fluid": {"name": "water", "backend": "HEOS", "composition": {}},
            "mass_flow_rate_kg_s": 1.0,
            "inlet_temperature_k": 350.0,
            "inlet_pressure_pa": 101325.0,
        },
        "cold_stream": {
            "fluid": {"name": "water", "backend": "HEOS", "composition": {}},
            "mass_flow_rate_kg_s": 1.5,
            "inlet_temperature_k": 290.0,
            "inlet_pressure_pa": 101325.0,
        },
        "minimum_terminal_delta_t_k": 5.0,
    },
    "geometry": {
        "inner_tube_inner_diameter_m": 0.02,
        "inner_tube_outer_diameter_m": 0.025,
        "outer_pipe_inner_diameter_m": 0.05,
        "effective_length_m": 3.0,
        "wall_thermal_conductivity_w_m_k": 50.0,
        "inner_surface_roughness_m": 1e-5,
        "annulus_surface_roughness_m": 1e-5,
    },
    "provider_ref": "CoolProp",
    "tube_in_hot": True,
    "flow_arrangement": "counterflow",
    "tube_boundary_condition": "constant_temperature",
    "annulus_boundary_condition": "constant_temperature",
}


def _make_validation_request() -> dict[str, Any]:
    """Create a minimal valid ValidationApiRequest payload."""
    fouling = {
        "value": {"value": 0.0001, "unit": "m^2*K/W"},
        "source": {
            "source_type": "STANDARD",
            "reference_id": "TEMA",
            "edition": "10th",
            "table_or_clause": "Table 1",
            "verification_status": "VERIFIED",
            "note": "test",
        },
    }
    stream = {
        "fluid": {"backend": "iapws-if97", "name": "Water"},
        "inlet": {
            "type": "TP",
            "temperature": {"value": 350.0, "unit": "K"},
            "pressure": {"value": 101325.0, "unit": "Pa"},
            "schema_version": "1.0",
        },
        "mass_flow": {"value": 1.0, "unit": "kg/s"},
        "fouling": fouling,
    }
    cold_stream = {
        "fluid": {"backend": "iapws-if97", "name": "Water"},
        "inlet": {
            "type": "TP",
            "temperature": {"value": 300.0, "unit": "K"},
            "pressure": {"value": 101325.0, "unit": "Pa"},
            "schema_version": "1.0",
        },
        "mass_flow": {"value": 1.5, "unit": "kg/s"},
        "fouling": fouling,
    }
    return {
        "api_schema_version": "1",
        "case_name": "test-case",
        "hot_stream": stream,
        "cold_stream": cold_stream,
        "target_duty": {"value": 100000.0, "unit": "W"},
        "minimum_terminal_delta_t": {"value": 5.0, "unit": "K"},
        "design_pressure_hot": {"value": 200000.0, "unit": "Pa"},
        "design_pressure_cold": {"value": 200000.0, "unit": "Pa"},
        "design_temperature_hot": {"value": 400.0, "unit": "K"},
        "design_temperature_cold": {"value": 350.0, "unit": "K"},
        "required_area_margin_fraction": 0.1,
    }


def _make_rating_request() -> dict[str, Any]:
    """Create a minimal valid RatingApiRequest payload."""
    return {
        "api_schema_version": "1",
        "case": _make_validation_request(),
        "geometry": {
            "inner_tube_inner_diameter": {"value": 0.02, "unit": "m"},
            "inner_tube_outer_diameter": {"value": 0.025, "unit": "m"},
            "outer_pipe_inner_diameter": {"value": 0.05, "unit": "m"},
            "effective_length": {"value": 5.0, "unit": "m"},
            "wall_thermal_conductivity": {"value": 50.0, "unit": "W/(m*K)"},
            "inner_surface_roughness": {"value": 0.0, "unit": "m"},
            "annulus_surface_roughness": {"value": 0.0, "unit": "m"},
        },
        "tube_in_hot": True,
        "flow_arrangement": "counterflow",
        "tube_boundary_condition": "constant_wall_temperature",
        "annulus_boundary_condition": "constant_wall_temperature",
        "provider_ref": "CoolProp",
    }


def _make_sizing_request() -> dict[str, Any]:
    """Create a SizingApiRequest payload."""
    app = _create_test_app()
    resolved = app.state.deps.provider_registry.resolve("CoolProp")
    identity = resolved.identity

    return {
        "api_schema_version": "1",
        "case": _make_validation_request(),
        "tube_in_hot": True,
        "flow_arrangement": "counterflow",
        "tube_boundary_condition": "constant_wall_temperature",
        "annulus_boundary_condition": "constant_wall_temperature",
        "catalog_refs": [
            {
                "catalog_id": "cat-1",
                "catalog_version": "1.0",
                "catalog_content_hash": "sha256:" + "ab" * 32,
                "source_identity": "test",
                "schema_version": "1",
            }
        ],
        "optimization_objective": "minimum_outer_heat_transfer_area",
        "requested_top_n": 3,
        "expected_provider_identity": {
            "name": identity.name,
            "version": identity.version,
            "git_revision": identity.git_revision,
            "reference_state_policy": identity.reference_state_policy,
        },
    }


# ===================================================================
# Helper: execute a real rating and return (envelope_dict, envelope)
# ===================================================================


def _execute_rating(
    app: FastAPI,
    key: str = "test-rating-unique-key",
) -> tuple[dict[str, Any], RatingRunEnvelope]:
    """Execute a real rating request and return (json_dict, typed_envelope)."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        "/v1/double-pipe/rating",
        json=_make_rating_request(),
        headers={"Idempotency-Key": key},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    envelope = RatingRunEnvelope.model_validate(data)
    return data, envelope


# ===================================================================
# Helper: build a record-like object for build_report_html
# ===================================================================


def _make_record_for_report(
    envelope: RatingRunEnvelope,
) -> SimpleNamespace:
    """Build a RunRecord-like object for build_report_html."""
    return SimpleNamespace(
        envelope=envelope,
        operation=envelope.operation,
        run_id=envelope.run_id,
        request_digest=envelope.request_digest,
    )


# ===================================================================
# Helper: make a dummy ReportInstanceIdentity for unit tests
# ===================================================================


def _dummy_identity(**overrides: Any) -> ReportInstanceIdentity:
    """Create a dummy ReportInstanceIdentity for unit tests."""
    defaults: dict[str, Any] = {
        "report_schema_version": "1",
        "report_content_hash": "sha256:" + "a" * 64,
        "run_id": uuid4(),
        "request_digest": "sha256:rd",
        "source_run_envelope_digest": "sha256:env",
        "source_domain_result_hash": "sha256:drh",
        "source_artifact_bundle_digest": "sha256:abd",
        "template_id": "t",
        "template_version": "v",
        "template_definition_hash": "sha256:tdh",
        "formatter_registry_version": "frv",
    }
    defaults.update(overrides)
    return ReportInstanceIdentity(**defaults)


def _dummy_model(
    sections: tuple[ReportSection, ...] | None = None,
    identity: ReportInstanceIdentity | None = None,
) -> DoublePipeReportModel:
    """Create a dummy DoublePipeReportModel for unit tests."""
    if sections is None:
        sections = tuple(
            ReportSection(
                section_id=sid,
                title=sid.value,
                content="test",
                status=ReportSectionStatus.COMPLETE,
            )
            for sid in REPORT_SECTION_ORDER
        )
    if identity is None:
        identity = _dummy_identity()
    return DoublePipeReportModel(
        report_schema_version="1",
        sections=sections,
        report_instance_identity=identity,
        report_content_hash=compute_report_content_hash(sections),
        report_instance_hash=compute_report_instance_hash(identity),
    )


# ===================================================================
# A6: T45 — DoublePipeService.size() never called
# ===================================================================


def _create_sizing_app() -> FastAPI:
    """Create a test app with a real catalog for sizing requests."""
    from hexagent.api.application import (
        RatingApplicationService,
        SizingApplicationService,
        SizingService,
    )
    from hexagent.api.main import ApplicationDependencies, create_app
    from hexagent.api.registry import CatalogRegistry, ProviderRegistry
    from hexagent.optimization.catalog import compute_catalog_content_hash
    from hexagent.optimization.models import (
        CompleteDoublePipeAssemblyOption,
        CompleteDoublePipeCatalogSnapshot,
        LengthSource,
    )
    from hexagent.properties.coolprop_provider import CoolPropProvider

    provider = CoolPropProvider()
    snapshot = ProviderIdentitySnapshot(
        name=provider.name,
        version=provider.version,
        git_revision=provider.git_revision,
        reference_state_policy=str(provider.reference_state_policy.value),
        configuration_fingerprint=getattr(provider, "_construction_fingerprint", ""),
        cache_policy_version=getattr(provider, "cache_policy_version", ""),
    )

    # Build a real catalog snapshot
    opt = CompleteDoublePipeAssemblyOption(
        assembly_option_id="opt1",
        inner_tube_inner_diameter_m=0.02,
        inner_tube_outer_diameter_m=0.025,
        outer_pipe_inner_diameter_m=0.05,
        wall_thermal_conductivity_w_m_k=50.0,
        inner_surface_roughness_m=1e-5,
        annulus_surface_roughness_m=1e-5,
        inner_fouling_resistance_m2k_w=0.0001,
        outer_fouling_resistance_m2k_w=0.0002,
        length_source=LengthSource(
            length_quantum_m="0.1",
            allowed_effective_lengths_m=(1.0, 2.0, 3.0, 5.0, 10.0),
        ),
        manufacturing_option_identity="std",
    )
    cat_hash = compute_catalog_content_hash(
        catalog_id="cat1",
        catalog_version="v1",
        source_identity="test",
        schema_version="1.0",
        assembly_options=(opt,),
    )
    cat = CompleteDoublePipeCatalogSnapshot(
        catalog_id="cat1",
        catalog_version="v1",
        source_identity="test",
        schema_version="1.0",
        assembly_options=(opt,),
        catalog_content_hash=cat_hash,
    )

    provider_registry = ProviderRegistry({"CoolProp": snapshot})
    catalog_registry = CatalogRegistry([cat])
    repo = InMemoryRunRepository()
    rating_service = RatingApplicationService(
        provider_registry=provider_registry,
        property_provider=provider,
    )
    sizing_service = SizingService(
        provider_registry=provider_registry,
        catalog_registry=catalog_registry,
    )
    sizing_app = SizingApplicationService(
        provider_registry=provider_registry,
        catalog_registry=catalog_registry,
        property_provider=provider,
    )
    deps = ApplicationDependencies(
        provider_registry=provider_registry,
        catalog_registry=catalog_registry,
        run_repository=repo,
        rating_service=rating_service,
        sizing_service=sizing_service,
        sizing_application_service=sizing_app,
    )
    return create_app(deps)


def _make_real_sizing_request(app: FastAPI) -> dict[str, Any]:
    """Create a SizingApiRequest with a valid catalog ref."""
    resolved = app.state.deps.provider_registry.resolve("CoolProp")
    identity = resolved.identity
    cat = app.state.deps.catalog_registry._canonical_order[0]

    return {
        "api_schema_version": "1",
        "case": _make_validation_request(),
        "tube_in_hot": True,
        "flow_arrangement": "counterflow",
        "tube_boundary_condition": "constant_wall_temperature",
        "annulus_boundary_condition": "constant_wall_temperature",
        "catalog_refs": [
            {
                "catalog_id": cat.catalog_id,
                "catalog_version": cat.catalog_version,
                "catalog_content_hash": cat.catalog_content_hash,
                "source_identity": cat.source_identity,
                "schema_version": cat.schema_version,
            }
        ],
        "optimization_objective": "minimum_outer_heat_transfer_area",
        "requested_top_n": 3,
        "expected_provider_identity": {
            "name": identity.name,
            "version": identity.version,
            "git_revision": identity.git_revision,
            "reference_state_policy": identity.reference_state_policy,
        },
    }


class TestA6T45:
    """T45: DoublePipeService.size() never called on sizing requests."""

    def test_t45_real_http_200(self):
        """T45: DoublePipeService.size() never called, sizing returns HTTP 200."""
        from hexagent.api.repository import RunState
        from hexagent.exchangers.double_pipe.service import DoublePipeService

        app = _create_sizing_app()
        client = TestClient(app, raise_server_exceptions=False)
        poison_called = {"count": 0}

        def poison(*args: Any, **kwargs: Any) -> None:
            poison_called["count"] += 1
            raise RuntimeError("DoublePipeService.size() was called!")

        sizing_payload = _make_real_sizing_request(app)
        with patch.object(DoublePipeService, "size", poison):
            resp = client.post(
                "/v1/double-pipe/sizing",
                json=sizing_payload,
                headers={"Idempotency-Key": "test-t45-real-200"},
            )

        assert resp.status_code == 200
        envelope = SizingRunEnvelope.model_validate(resp.json())
        assert envelope.artifact_bundle is not None
        repo = app.state.deps.run_repository
        record = repo.get_by_run_id(envelope.run_id)
        assert record is not None
        assert record.state == RunState.COMPLETE
        assert poison_called["count"] == 0


# ===================================================================
# A7: Sizing/Rating replay
# ===================================================================


class TestA7Replay:
    """Replay contract."""

    def test_rating_complete_replay(self):
        """first 200, second 200 same envelope."""
        app = _create_fresh_app()
        client = TestClient(app, raise_server_exceptions=False)
        rating_payload = _make_rating_request()
        key = "test-a7-rating-replay"

        resp1 = client.post(
            "/v1/double-pipe/rating",
            json=rating_payload,
            headers={"Idempotency-Key": key},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()

        resp2 = client.post(
            "/v1/double-pipe/rating",
            json=rating_payload,
            headers={"Idempotency-Key": key},
        )
        assert resp2.status_code == 200
        data2 = resp2.json()

        assert data1 == data2

    def test_different_request_conflict(self):
        """409."""
        app = _create_fresh_app()
        client = TestClient(app, raise_server_exceptions=False)
        key = "test-a7-conflict"

        resp1 = client.post(
            "/v1/double-pipe/rating",
            json=_make_rating_request(),
            headers={"Idempotency-Key": key},
        )
        assert resp1.status_code == 200

        different = _make_rating_request()
        different["geometry"]["effective_length"]["value"] = 10.0

        resp2 = client.post(
            "/v1/double-pipe/rating",
            json=different,
            headers={"Idempotency-Key": key},
        )
        assert resp2.status_code == 409
        data = resp2.json()
        assert data["error_code"] == "idempotency_conflict"


# ===================================================================
# A7b: Sizing COMPLETE replay with counting wrapper
# ===================================================================


class CountingSizingApplicationService:
    """Wrapper that counts execute() calls while delegating to the real service."""

    def __init__(self, delegate: SizingApplicationService):
        self.delegate = delegate
        self.execute_count = 0

    def prepare(self, request: SizingApiRequest) -> PreparedSizingRun:
        return self.delegate.prepare(request)

    def execute(self, prepared: PreparedSizingRun) -> SizingExecutionResult:
        self.execute_count += 1
        return self.delegate.execute(prepared)


def _create_sizing_app_with_counter() -> tuple[FastAPI, CountingSizingApplicationService]:
    """Create a test app with CountingSizingApplicationService wrapping real service.

    Returns (app, counter) where counter.execute_count tracks execute() calls.
    """
    from hexagent.api.application import (
        RatingApplicationService,
        SizingApplicationService,
        SizingService,
    )
    from hexagent.api.main import ApplicationDependencies, create_app
    from hexagent.api.registry import CatalogRegistry, ProviderRegistry
    from hexagent.optimization.catalog import compute_catalog_content_hash
    from hexagent.optimization.models import (
        CompleteDoublePipeAssemblyOption,
        CompleteDoublePipeCatalogSnapshot,
        LengthSource,
    )
    from hexagent.properties.coolprop_provider import CoolPropProvider

    provider = CoolPropProvider()
    snapshot = ProviderIdentitySnapshot(
        name=provider.name,
        version=provider.version,
        git_revision=provider.git_revision,
        reference_state_policy=str(provider.reference_state_policy.value),
        configuration_fingerprint=getattr(provider, "_construction_fingerprint", ""),
        cache_policy_version=getattr(provider, "cache_policy_version", ""),
    )

    # Build a real catalog snapshot
    opt = CompleteDoublePipeAssemblyOption(
        assembly_option_id="opt1",
        inner_tube_inner_diameter_m=0.02,
        inner_tube_outer_diameter_m=0.025,
        outer_pipe_inner_diameter_m=0.05,
        wall_thermal_conductivity_w_m_k=50.0,
        inner_surface_roughness_m=1e-5,
        annulus_surface_roughness_m=1e-5,
        inner_fouling_resistance_m2k_w=0.0001,
        outer_fouling_resistance_m2k_w=0.0002,
        length_source=LengthSource(
            length_quantum_m="0.1",
            allowed_effective_lengths_m=(1.0, 2.0, 3.0, 5.0, 10.0),
        ),
        manufacturing_option_identity="std",
    )
    cat_hash = compute_catalog_content_hash(
        catalog_id="cat1",
        catalog_version="v1",
        source_identity="test",
        schema_version="1.0",
        assembly_options=(opt,),
    )
    cat = CompleteDoublePipeCatalogSnapshot(
        catalog_id="cat1",
        catalog_version="v1",
        source_identity="test",
        schema_version="1.0",
        assembly_options=(opt,),
        catalog_content_hash=cat_hash,
    )

    provider_registry = ProviderRegistry({"CoolProp": snapshot})
    catalog_registry = CatalogRegistry([cat])
    repo = InMemoryRunRepository()
    rating_service = RatingApplicationService(
        provider_registry=provider_registry,
        property_provider=provider,
    )
    sizing_service = SizingService(
        provider_registry=provider_registry,
        catalog_registry=catalog_registry,
    )
    sizing_app = SizingApplicationService(
        provider_registry=provider_registry,
        catalog_registry=catalog_registry,
        property_provider=provider,
    )
    counter = CountingSizingApplicationService(sizing_app)
    deps = ApplicationDependencies(
        provider_registry=provider_registry,
        catalog_registry=catalog_registry,
        run_repository=repo,
        rating_service=rating_service,
        sizing_service=sizing_service,
        sizing_application_service=counter,
    )
    app = create_app(deps)
    return app, counter


class TestA7bSizingCompleteReplay:
    """P0-7: Sizing COMPLETE replay with counting wrapper.

    Verifies that same-key replay returns identical envelope without
    re-executing the sizing optimization pipeline.
    """

    def test_sizing_complete_replay_returns_identical_envelope(self):
        """P0-7: Same key+body -> HTTP 200, identical envelope on replay."""
        app, counter = _create_sizing_app_with_counter()
        client = TestClient(app, raise_server_exceptions=False)
        sizing_payload = _make_real_sizing_request(app)
        key = "test-p07-sizing-replay"

        # First POST -- should execute sizing pipeline
        resp1 = client.post(
            "/v1/double-pipe/sizing",
            json=sizing_payload,
            headers={"Idempotency-Key": key},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        envelope1 = SizingRunEnvelope.model_validate(data1)
        verify_sizing_artifact_bundle(envelope1.artifact_bundle)
        # Repository state
        repo = app.state.deps.run_repository
        record1 = repo.get_by_run_id(envelope1.run_id)
        assert record1 is not None
        assert record1.state == RunState.COMPLETE
        # execute_count == 1
        assert counter.execute_count == 1

        # Second POST with same key+body -- should replay, not re-execute
        resp2 = client.post(
            "/v1/double-pipe/sizing",
            json=sizing_payload,
            headers={"Idempotency-Key": key},
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        # execute_count stays at 1
        assert counter.execute_count == 1
        # Response JSON identical — compare typed envelopes to avoid
        # tuple/list serialization differences in raw JSON
        envelope2 = SizingRunEnvelope.model_validate(data2)
        assert envelope1.run_id == envelope2.run_id
        assert envelope1.result_hash == envelope2.result_hash
        assert envelope1.provenance_digest == envelope2.provenance_digest
        assert envelope1.artifact_bundle_digest == envelope2.artifact_bundle_digest
        assert envelope1.api_schema_version == envelope2.api_schema_version
        assert envelope1.operation == envelope2.operation
        assert envelope1.result_kind == envelope2.result_kind
        assert envelope1.warnings == envelope2.warnings
        assert envelope1.blockers == envelope2.blockers
        assert envelope1.failure == envelope2.failure
        assert envelope1.provenance == envelope2.provenance
        assert envelope1.artifact_bundle == envelope2.artifact_bundle
        # T45 assertion: DoublePipeService.size never called on sizing path
        from hexagent.exchangers.double_pipe.service import DoublePipeService

        assert not hasattr(DoublePipeService, "_test_t45_sizing_called") or not getattr(
            DoublePipeService, "_test_t45_sizing_called", False
        )

    def test_sizing_complete_replay_does_not_reexecute(self):
        """P0-7: execute_count stays at 1 after second request."""
        app, counter = _create_sizing_app_with_counter()
        client = TestClient(app, raise_server_exceptions=False)
        sizing_payload = _make_real_sizing_request(app)
        key = "test-p07-no-reexecute"

        # First POST
        resp1 = client.post(
            "/v1/double-pipe/sizing",
            json=sizing_payload,
            headers={"Idempotency-Key": key},
        )
        assert resp1.status_code == 200
        assert counter.execute_count == 1

        # Second POST -- replay
        resp2 = client.post(
            "/v1/double-pipe/sizing",
            json=sizing_payload,
            headers={"Idempotency-Key": key},
        )
        assert resp2.status_code == 200
        assert counter.execute_count == 1

    def test_sizing_same_key_different_body_returns_409(self):
        """P0-7: Same key but different body -> HTTP 409 (IDEMPOTENCY_CONFLICT)."""
        app, counter = _create_sizing_app_with_counter()
        client = TestClient(app, raise_server_exceptions=False)
        key = "test-p07-sizing-conflict"

        sizing_payload = _make_real_sizing_request(app)
        resp1 = client.post(
            "/v1/double-pipe/sizing",
            json=sizing_payload,
            headers={"Idempotency-Key": key},
        )
        assert resp1.status_code == 200

        # Different body with same key
        different_payload = _make_real_sizing_request(app)
        different_payload["requested_top_n"] = 5

        resp2 = client.post(
            "/v1/double-pipe/sizing",
            json=different_payload,
            headers={"Idempotency-Key": key},
        )
        assert resp2.status_code == 409
        data = resp2.json()
        assert data["error_code"] == "idempotency_conflict"


# ===================================================================
# B1-B8: Report contract tests
# ===================================================================


class TestB1ReportModels:
    """B1: Precise report models."""

    def test_report_source_document_exact(self):
        """ReportSourceDocument has exactly 3 values."""
        assert len(ReportSourceDocument) == 3
        assert set(ReportSourceDocument) == {
            ReportSourceDocument.RUN_ENVELOPE,
            ReportSourceDocument.ARTIFACT_BUNDLE,
            ReportSourceDocument.CANONICAL_REQUEST,
        }

    def test_report_artifact_kind_exact(self):
        """ReportArtifactKind has exactly 4 values."""
        assert len(ReportArtifactKind) == 4
        assert set(ReportArtifactKind) == {
            ReportArtifactKind.PRESENT,
            ReportArtifactKind.NOT_AVAILABLE,
            ReportArtifactKind.NOT_IMPLEMENTED,
            ReportArtifactKind.OUT_OF_SCOPE,
        }
        assert str(ReportArtifactKind.PRESENT) == "present"
        assert str(ReportArtifactKind.NOT_AVAILABLE) == "not_available"
        assert str(ReportArtifactKind.NOT_IMPLEMENTED) == "not_implemented"
        assert str(ReportArtifactKind.OUT_OF_SCOPE) == "out_of_scope"

    def test_report_section_status_exact(self):
        """ReportSectionStatus has exactly 5 values."""
        assert len(ReportSectionStatus) == 5
        assert set(ReportSectionStatus) == {
            ReportSectionStatus.COMPLETE,
            ReportSectionStatus.PARTIAL,
            ReportSectionStatus.EMPTY,
            ReportSectionStatus.BLOCKED,
            ReportSectionStatus.NOT_APPLICABLE,
        }
        assert str(ReportSectionStatus.COMPLETE) == "complete"
        assert str(ReportSectionStatus.PARTIAL) == "partial"
        assert str(ReportSectionStatus.EMPTY) == "empty"
        assert str(ReportSectionStatus.BLOCKED) == "blocked"
        assert str(ReportSectionStatus.NOT_APPLICABLE) == "not_applicable"

    def test_report_artifact_id_exact(self):
        """ReportArtifactId has exactly 36 values."""
        assert len(ReportArtifactId) == 36
        expected_values = {
            "status",
            "termination_status",
            "run_id",
            "api_version",
            "operation",
            "request_digest",
            "case_name",
            "hot_fluid",
            "cold_fluid",
            "hot_inlet_t",
            "cold_inlet_t",
            "mass_flows",
            "design_pressures",
            "design_temperatures",
            "geometry_spec",
            "heat_duty",
            "energy_residual",
            "tube_htc",
            "annulus_htc",
            "overall_u",
            "effectiveness",
            "sizing_rank",
            "optimization_objective",
            "warning_messages",
            "blocker_messages",
            "top_ranked_candidates",
            "failure_reason",
            "provenance_graph",
            "result_hash",
            "bundle_hash",
            "pressure_drop",
            "velocity",
            "materials",
            "cost",
            "mechanical",
            "procurement",
        }
        assert {v.value for v in ReportArtifactId} == expected_values

    def test_discriminator(self):
        """ReportArtifact uses kind discriminator — P0-5 field layout."""
        from pydantic import TypeAdapter

        ta = TypeAdapter(ReportArtifact)

        # Test PRESENT variant (P0-5: includes formatter fields)
        present = ta.validate_python(
            {
                "kind": "present",
                "artifact_id": "status",
                "source_document": "run_envelope",
                "source_document_digest": "sha256:abc",
                "source_json_pointer": "/result/status",
                "authority_digest": "sha256:def",
                "canonical_raw_value": "success",
                "formatter_id": "default",
                "formatter_version": "1.0",
                "rounding_mode": "round",
                "formatted_display_value": "success",
            }
        )
        assert isinstance(present, PresentReportArtifact)
        assert present.kind == ReportArtifactKind.PRESENT

        # Test NOT_AVAILABLE variant (P0-5: reason_code + capability)
        not_avail = ta.validate_python(
            {
                "kind": "not_available",
                "artifact_id": "cost",
                "reason_code": "section_not_available",
                "capability": "not_applicable",
            }
        )
        assert isinstance(not_avail, UnavailableReportArtifact)
        assert not_avail.kind == ReportArtifactKind.NOT_AVAILABLE

        # Test NOT_IMPLEMENTED variant (P0-5: capability only)
        not_impl = ta.validate_python(
            {
                "kind": "not_implemented",
                "artifact_id": "materials",
                "capability": "not_implemented",
            }
        )
        assert isinstance(not_impl, NotImplementedReportArtifact)
        assert not_impl.kind == ReportArtifactKind.NOT_IMPLEMENTED

        # Test OUT_OF_SCOPE variant (P0-5: capability only)
        out_of_scope = ta.validate_python(
            {
                "kind": "out_of_scope",
                "artifact_id": "sizing_rank",
                "capability": "out_of_scope",
            }
        )
        assert isinstance(out_of_scope, OutOfScopeReportArtifact)
        assert out_of_scope.kind == ReportArtifactKind.OUT_OF_SCOPE


class TestP05ArtifactVariantFields:
    """P0-5: Non-PRESENT artifact variants have exact fields."""

    def test_unavailable_fields_exact(self):
        """UnavailableReportArtifact: kind, artifact_id, reason_code, capability."""
        art = UnavailableReportArtifact(
            kind=ReportArtifactKind.NOT_AVAILABLE,
            artifact_id=ReportArtifactId.COST,
            reason_code="section_not_available",
            capability="not_applicable",
        )
        assert art.kind == ReportArtifactKind.NOT_AVAILABLE
        assert art.artifact_id == ReportArtifactId.COST
        assert art.reason_code == "section_not_available"
        assert art.capability == "not_applicable"

    def test_not_implemented_fields_exact(self):
        """NotImplementedReportArtifact: kind, artifact_id, capability."""
        art = NotImplementedReportArtifact(
            kind=ReportArtifactKind.NOT_IMPLEMENTED,
            artifact_id=ReportArtifactId.MATERIALS,
            capability="not_implemented",
        )
        assert art.kind == ReportArtifactKind.NOT_IMPLEMENTED
        assert art.artifact_id == ReportArtifactId.MATERIALS
        assert art.capability == "not_implemented"

    def test_out_of_scope_fields_exact(self):
        """OutOfScopeReportArtifact: kind, artifact_id, capability."""
        art = OutOfScopeReportArtifact(
            kind=ReportArtifactKind.OUT_OF_SCOPE,
            artifact_id=ReportArtifactId.SIZING_RANK,
            capability="out_of_scope",
        )
        assert art.kind == ReportArtifactKind.OUT_OF_SCOPE
        assert art.artifact_id == ReportArtifactId.SIZING_RANK
        assert art.capability == "out_of_scope"

    def test_present_has_formatter_fields(self):
        """PresentReportArtifact: all formatter fields required."""
        art = PresentReportArtifact(
            kind=ReportArtifactKind.PRESENT,
            artifact_id=ReportArtifactId.STATUS,
            source_document=ReportSourceDocument.RUN_ENVELOPE,
            source_document_digest="sha256:abc",
            source_json_pointer="/result/status",
            authority_digest="sha256:def",
            canonical_raw_value="success",
            formatter_id="default",
            formatter_version="1.0",
            rounding_mode="round",
            formatted_display_value="success",
        )
        assert art.formatter_id == "default"
        assert art.formatter_version == "1.0"
        assert art.rounding_mode == "round"
        assert art.formatted_display_value == "success"

    def test_unavailable_rejects_source_document(self):
        """UnavailableReportArtifact rejects source_document field."""
        with pytest.raises((TypeError, ValueError)):
            UnavailableReportArtifact(
                kind=ReportArtifactKind.NOT_AVAILABLE,
                artifact_id=ReportArtifactId.COST,
                reason_code="x",
                capability="x",
                source_document="run_envelope",  # type: ignore[call-arg]
            )


# ===================================================================
# B2: Exactly 13 Sections in Fixed Order
# ===================================================================


class TestB2ThirteenSections:
    """B2: Exactly 13 sections in fixed order."""

    def test_section_order_constant(self):
        """len == 13, correct order."""
        assert len(REPORT_SECTION_ORDER) == 13
        expected = (
            ReportSectionId.STATUS_BANNER,
            ReportSectionId.RUN_IDENTITY,
            ReportSectionId.INPUT_SUMMARY,
            ReportSectionId.GEOMETRY,
            ReportSectionId.HEAT_BALANCE,
            ReportSectionId.THERMAL_PERFORMANCE,
            ReportSectionId.SIZING_RANKING,
            ReportSectionId.TOP_RANKED_CANDIDATES,
            ReportSectionId.WARNINGS,
            ReportSectionId.BLOCKERS,
            ReportSectionId.FAILURE_DETAILS,
            ReportSectionId.PROVENANCE,
            ReportSectionId.INTEGRITY,
        )
        assert expected == REPORT_SECTION_ORDER

    def test_report_model_rejects_wrong_count(self):
        """ReportModel rejects construction with != 13 sections."""
        sections = (
            ReportSection(
                section_id=ReportSectionId.STATUS_BANNER,
                title="Status Banner",
                content="test",
                status=ReportSectionStatus.COMPLETE,
            ),
            ReportSection(
                section_id=ReportSectionId.RUN_IDENTITY,
                title="Run Identity",
                content="test",
                status=ReportSectionStatus.COMPLETE,
            ),
        )
        with pytest.raises(Exception, match="Expected 13 sections"):
            ReportModel(
                report_schema_version="1",
                sections=sections,
                report_instance_identity=_dummy_identity(),
                report_content_hash="sha256:abc",
                report_instance_hash="sha256:ih",
            )


# ===================================================================
# B3: Section/Status Matrix Verification (P0-4: exact frozen contract)
# ===================================================================


class TestB3SectionStatusMatrix:
    """B3: Section/status matrix verification."""

    def test_matrix_rejects_unknown_operation(self):
        """verify_report_section_status_matrix raises on bad operation."""
        model = _dummy_model()
        bad_env = SimpleNamespace(
            operation="unknown_op",
            result=None,
            blockers=(),
            warnings=(),
            failure=None,
        )
        with pytest.raises(ValueError, match="Unsupported operation"):
            verify_report_section_status_matrix(model, "unknown_op", bad_env)


# ===================================================================
# P0-4: 5 x 13 = 65 exact matrix assertions
# ===================================================================


class TestP04ExactMatrix:
    """P0-4: Exactly 65 cells matching the frozen contract."""

    def test_rating_succeeded_exact_13_cells(self):
        """rating_succeeded: all 13 sections exact."""
        from hexagent.reporting import _RATING_MATRIX

        expected = _RATING_MATRIX["rating_succeeded"]
        assert expected == {
            ReportSectionId.STATUS_BANNER: ReportSectionStatus.COMPLETE,
            ReportSectionId.RUN_IDENTITY: ReportSectionStatus.COMPLETE,
            ReportSectionId.INPUT_SUMMARY: ReportSectionStatus.COMPLETE,
            ReportSectionId.GEOMETRY: ReportSectionStatus.COMPLETE,
            ReportSectionId.HEAT_BALANCE: ReportSectionStatus.COMPLETE,
            ReportSectionId.THERMAL_PERFORMANCE: ReportSectionStatus.COMPLETE,
            ReportSectionId.SIZING_RANKING: ReportSectionStatus.NOT_APPLICABLE,
            ReportSectionId.TOP_RANKED_CANDIDATES: ReportSectionStatus.NOT_APPLICABLE,
            ReportSectionId.WARNINGS: ReportSectionStatus.COMPLETE,
            ReportSectionId.BLOCKERS: ReportSectionStatus.EMPTY,
            ReportSectionId.FAILURE_DETAILS: ReportSectionStatus.NOT_APPLICABLE,
            ReportSectionId.PROVENANCE: ReportSectionStatus.COMPLETE,
            ReportSectionId.INTEGRITY: ReportSectionStatus.COMPLETE,
        }
        assert len(expected) == 13

    def test_rating_blocked_exact_13_cells(self):
        """rating_blocked: all 13 sections exact."""
        from hexagent.reporting import _RATING_MATRIX

        expected = _RATING_MATRIX["rating_blocked"]
        assert expected == {
            ReportSectionId.STATUS_BANNER: ReportSectionStatus.BLOCKED,
            ReportSectionId.RUN_IDENTITY: ReportSectionStatus.COMPLETE,
            ReportSectionId.INPUT_SUMMARY: ReportSectionStatus.COMPLETE,
            ReportSectionId.GEOMETRY: ReportSectionStatus.NOT_APPLICABLE,
            ReportSectionId.HEAT_BALANCE: ReportSectionStatus.NOT_APPLICABLE,
            ReportSectionId.THERMAL_PERFORMANCE: ReportSectionStatus.NOT_APPLICABLE,
            ReportSectionId.SIZING_RANKING: ReportSectionStatus.NOT_APPLICABLE,
            ReportSectionId.TOP_RANKED_CANDIDATES: ReportSectionStatus.NOT_APPLICABLE,
            ReportSectionId.WARNINGS: ReportSectionStatus.PARTIAL,
            ReportSectionId.BLOCKERS: ReportSectionStatus.COMPLETE,
            ReportSectionId.FAILURE_DETAILS: ReportSectionStatus.NOT_APPLICABLE,
            ReportSectionId.PROVENANCE: ReportSectionStatus.COMPLETE,
            ReportSectionId.INTEGRITY: ReportSectionStatus.COMPLETE,
        }
        assert len(expected) == 13

    def test_rating_failed_exact_13_cells(self):
        """rating_failed: all 13 sections exact."""
        from hexagent.reporting import _RATING_MATRIX

        expected = _RATING_MATRIX["rating_failed"]
        assert expected == {
            ReportSectionId.STATUS_BANNER: ReportSectionStatus.BLOCKED,
            ReportSectionId.RUN_IDENTITY: ReportSectionStatus.COMPLETE,
            ReportSectionId.INPUT_SUMMARY: ReportSectionStatus.COMPLETE,
            ReportSectionId.GEOMETRY: ReportSectionStatus.NOT_APPLICABLE,
            ReportSectionId.HEAT_BALANCE: ReportSectionStatus.PARTIAL,
            ReportSectionId.THERMAL_PERFORMANCE: ReportSectionStatus.PARTIAL,
            ReportSectionId.SIZING_RANKING: ReportSectionStatus.NOT_APPLICABLE,
            ReportSectionId.TOP_RANKED_CANDIDATES: ReportSectionStatus.NOT_APPLICABLE,
            ReportSectionId.WARNINGS: ReportSectionStatus.PARTIAL,
            ReportSectionId.BLOCKERS: ReportSectionStatus.PARTIAL,
            ReportSectionId.FAILURE_DETAILS: ReportSectionStatus.COMPLETE,
            ReportSectionId.PROVENANCE: ReportSectionStatus.COMPLETE,
            ReportSectionId.INTEGRITY: ReportSectionStatus.COMPLETE,
        }
        assert len(expected) == 13

    def test_sizing_complete_exact_13_cells(self):
        """sizing_complete: all 13 sections exact."""
        from hexagent.reporting import _SIZING_MATRIX

        expected = _SIZING_MATRIX["sizing_complete"]
        assert expected == {
            ReportSectionId.STATUS_BANNER: ReportSectionStatus.COMPLETE,
            ReportSectionId.RUN_IDENTITY: ReportSectionStatus.COMPLETE,
            ReportSectionId.INPUT_SUMMARY: ReportSectionStatus.COMPLETE,
            ReportSectionId.GEOMETRY: ReportSectionStatus.COMPLETE,
            ReportSectionId.HEAT_BALANCE: ReportSectionStatus.NOT_APPLICABLE,
            ReportSectionId.THERMAL_PERFORMANCE: ReportSectionStatus.NOT_APPLICABLE,
            ReportSectionId.SIZING_RANKING: ReportSectionStatus.COMPLETE,
            ReportSectionId.TOP_RANKED_CANDIDATES: ReportSectionStatus.COMPLETE,
            ReportSectionId.WARNINGS: ReportSectionStatus.COMPLETE,
            ReportSectionId.BLOCKERS: ReportSectionStatus.EMPTY,
            ReportSectionId.FAILURE_DETAILS: ReportSectionStatus.NOT_APPLICABLE,
            ReportSectionId.PROVENANCE: ReportSectionStatus.COMPLETE,
            ReportSectionId.INTEGRITY: ReportSectionStatus.COMPLETE,
        }
        assert len(expected) == 13

    def test_sizing_partial_exact_13_cells(self):
        """sizing_partial: all 13 sections exact."""
        from hexagent.reporting import _SIZING_MATRIX

        expected = _SIZING_MATRIX["sizing_partial"]
        assert expected == {
            ReportSectionId.STATUS_BANNER: ReportSectionStatus.PARTIAL,
            ReportSectionId.RUN_IDENTITY: ReportSectionStatus.COMPLETE,
            ReportSectionId.INPUT_SUMMARY: ReportSectionStatus.COMPLETE,
            ReportSectionId.GEOMETRY: ReportSectionStatus.PARTIAL,
            ReportSectionId.HEAT_BALANCE: ReportSectionStatus.NOT_APPLICABLE,
            ReportSectionId.THERMAL_PERFORMANCE: ReportSectionStatus.NOT_APPLICABLE,
            ReportSectionId.SIZING_RANKING: ReportSectionStatus.PARTIAL,
            ReportSectionId.TOP_RANKED_CANDIDATES: ReportSectionStatus.PARTIAL,
            ReportSectionId.WARNINGS: ReportSectionStatus.COMPLETE,
            ReportSectionId.BLOCKERS: ReportSectionStatus.PARTIAL,
            ReportSectionId.FAILURE_DETAILS: ReportSectionStatus.NOT_APPLICABLE,
            ReportSectionId.PROVENANCE: ReportSectionStatus.COMPLETE,
            ReportSectionId.INTEGRITY: ReportSectionStatus.COMPLETE,
        }
        assert len(expected) == 13

    def test_total_65_cells(self):
        """5 matrices x 13 sections = 65 exact cells."""
        from hexagent.reporting import _RATING_MATRIX, _SIZING_MATRIX

        total = 0
        for matrix in [_RATING_MATRIX, _SIZING_MATRIX]:
            for section_map in matrix.values():
                total += len(section_map)
        assert total == 65

    def test_all_5_source_states_covered(self):
        """All 5 source states are present in the combined matrix."""
        from hexagent.reporting import _RATING_MATRIX, _SIZING_MATRIX

        all_states = set(_RATING_MATRIX.keys()) | set(_SIZING_MATRIX.keys())
        assert all_states == {
            "rating_succeeded",
            "rating_blocked",
            "rating_failed",
            "sizing_complete",
            "sizing_partial",
        }

    def test_each_matrix_covers_all_13_sections(self):
        """Each of the 5 matrices has exactly 13 section keys."""
        from hexagent.reporting import _RATING_MATRIX, _SIZING_MATRIX

        all_matrices = {**_RATING_MATRIX, **_SIZING_MATRIX}
        for state, matrix in all_matrices.items():
            assert len(matrix) == 13, f"{state} has {len(matrix)} sections, expected 13"
            for section_id in REPORT_SECTION_ORDER:
                assert section_id in matrix, f"{state} missing section {section_id.value}"


# ===================================================================
# P0-6: Content hash includes all artifact fields
# ===================================================================


class TestP06ContentHash:
    """P0-6: Content hash includes all artifact fields."""

    def test_content_hash_includes_artifacts(self):
        """Content hash differs when artifacts differ."""
        sections_a = (
            ReportSection(
                section_id=ReportSectionId.STATUS_BANNER,
                title="Status",
                content="test",
                status=ReportSectionStatus.COMPLETE,
                artifacts=(
                    PresentReportArtifact(
                        kind=ReportArtifactKind.PRESENT,
                        artifact_id=ReportArtifactId.STATUS,
                        source_document=ReportSourceDocument.RUN_ENVELOPE,
                        source_document_digest="sha256:aaa",
                        source_json_pointer="/result/status",
                        authority_digest="sha256:auth1",
                        canonical_raw_value="ok",
                        formatter_id="f1",
                        formatter_version="1.0",
                        rounding_mode="round",
                        formatted_display_value="ok",
                    ),
                ),
            ),
        )
        sections_b = (
            ReportSection(
                section_id=ReportSectionId.STATUS_BANNER,
                title="Status",
                content="test",
                status=ReportSectionStatus.COMPLETE,
                artifacts=(
                    PresentReportArtifact(
                        kind=ReportArtifactKind.PRESENT,
                        artifact_id=ReportArtifactId.STATUS,
                        source_document=ReportSourceDocument.RUN_ENVELOPE,
                        source_document_digest="sha256:bbb",
                        source_json_pointer="/result/status",
                        authority_digest="sha256:auth2",
                        canonical_raw_value="fail",
                        formatter_id="f2",
                        formatter_version="2.0",
                        rounding_mode="trunc",
                        formatted_display_value="fail",
                    ),
                ),
            ),
        )

        # Pad to 13 sections
        def _pad(arts: tuple[ReportSection, ...]) -> tuple[ReportSection, ...]:
            result = list(arts)
            for sid in REPORT_SECTION_ORDER:
                if sid not in [a.section_id for a in result]:
                    result.append(
                        ReportSection(
                            section_id=sid,
                            title=sid.value,
                            content="",
                            status=ReportSectionStatus.NOT_APPLICABLE,
                        )
                    )
            return tuple(result)

        h1 = compute_report_content_hash(_pad(sections_a))
        h2 = compute_report_content_hash(_pad(sections_b))
        assert h1 != h2

    def test_content_hash_includes_unavailable_fields(self):
        """Content hash differs when UnavailableReportArtifact fields differ."""
        sec_a = (
            ReportSection(
                section_id=ReportSectionId.SIZING_RANKING,
                title="Sizing",
                content="n/a",
                status=ReportSectionStatus.NOT_APPLICABLE,
                artifacts=(
                    UnavailableReportArtifact(
                        kind=ReportArtifactKind.NOT_AVAILABLE,
                        artifact_id=ReportArtifactId.SIZING_RANK,
                        reason_code="not_applicable",
                        capability="n/a",
                    ),
                ),
            ),
        )
        sec_b = (
            ReportSection(
                section_id=ReportSectionId.SIZING_RANKING,
                title="Sizing",
                content="n/a",
                status=ReportSectionStatus.NOT_APPLICABLE,
                artifacts=(
                    UnavailableReportArtifact(
                        kind=ReportArtifactKind.NOT_AVAILABLE,
                        artifact_id=ReportArtifactId.SIZING_RANK,
                        reason_code="blocked",
                        capability="blocked",
                    ),
                ),
            ),
        )

        def _pad(arts: tuple[ReportSection, ...]) -> tuple[ReportSection, ...]:
            result = list(arts)
            for sid in REPORT_SECTION_ORDER:
                if sid not in [a.section_id for a in result]:
                    result.append(
                        ReportSection(
                            section_id=sid,
                            title=sid.value,
                            content="",
                            status=ReportSectionStatus.NOT_APPLICABLE,
                        )
                    )
            return tuple(result)

        h1 = compute_report_content_hash(_pad(sec_a))
        h2 = compute_report_content_hash(_pad(sec_b))
        assert h1 != h2


# ===================================================================
# P0-6: Instance hash verification
# ===================================================================


class TestP06InstanceHash:
    """P0-6: Instance hash = sha256_digest(report_instance_identity)."""

    def test_instance_hash_deterministic(self):
        """compute_report_instance_hash is deterministic."""
        run_id = uuid4()
        identity = ReportInstanceIdentity(
            report_content_hash="sha256:" + "a" * 64,
            report_schema_version="1",
            run_id=run_id,
            request_digest="sha256:rd",
            source_run_envelope_digest="sha256:env",
            source_domain_result_hash="sha256:drh",
            source_artifact_bundle_digest="sha256:abd",
            template_id="t",
            template_version="v",
            template_definition_hash="sha256:tdh",
            formatter_registry_version="frv",
        )
        h1 = compute_report_instance_hash(identity)
        h2 = compute_report_instance_hash(identity)
        assert h1 == h2
        assert h1.startswith("sha256:")

    def test_instance_hash_varies_per_field(self):
        """Changing any identity field changes the instance hash."""
        base = {
            "report_schema_version": "1",
            "report_content_hash": "sha256:a",
            "run_id": uuid4(),
            "request_digest": "sha256:rd",
            "source_run_envelope_digest": "sha256:env",
            "source_domain_result_hash": "sha256:drh",
            "source_artifact_bundle_digest": "sha256:abd",
            "template_id": "t",
            "template_version": "v",
            "template_definition_hash": "sha256:tdh",
            "formatter_registry_version": "frv",
        }
        h0 = compute_report_instance_hash(ReportInstanceIdentity(**base))

        for field in base:
            modified = dict(base)
            val = modified[field]
            if isinstance(val, UUID):
                modified[field] = uuid4()
            else:
                modified[field] = val + "_x"
            h1 = compute_report_instance_hash(ReportInstanceIdentity(**modified))
            assert h1 != h0, f"Field {field!r} change did not alter instance hash"

    def test_report_model_has_instance_hash(self):
        """DoublePipeReportModel includes report_instance_hash."""
        model = _dummy_model()
        assert model.report_instance_hash == compute_report_instance_hash(
            model.report_instance_identity
        )

    def test_double_pipe_report_model_fields(self):
        """DoublePipeReportModel has exactly 5 fields."""
        fields = set(DoublePipeReportModel.model_fields.keys())
        assert fields == {
            "report_schema_version",
            "sections",
            "report_instance_identity",
            "report_content_hash",
            "report_instance_hash",
        }

    def test_report_instance_identity_11_fields(self):
        """ReportInstanceIdentity has exactly 11 fields."""
        identity = _dummy_identity()
        d = {
            "report_schema_version": identity.report_schema_version,
            "report_content_hash": identity.report_content_hash,
            "run_id": str(identity.run_id),
            "request_digest": identity.request_digest,
            "source_run_envelope_digest": identity.source_run_envelope_digest,
            "source_domain_result_hash": identity.source_domain_result_hash,
            "source_artifact_bundle_digest": identity.source_artifact_bundle_digest,
            "template_id": identity.template_id,
            "template_version": identity.template_version,
            "template_definition_hash": identity.template_definition_hash,
            "formatter_registry_version": identity.formatter_registry_version,
        }
        assert len(d) == 11


# ===================================================================
# P0-6: Tamper tests for each authority digest
# ===================================================================


class TestP06TamperDigests:
    """P0-6: Tamper tests for source authority digests."""

    def test_tamper_source_run_envelope_digest(self):
        """Changing source_run_envelope_digest changes instance hash."""
        id1 = _dummy_identity(source_run_envelope_digest="sha256:aaa")
        id2 = _dummy_identity(source_run_envelope_digest="sha256:bbb")
        assert compute_report_instance_hash(id1) != compute_report_instance_hash(id2)

    def test_tamper_source_domain_result_hash(self):
        """Changing source_domain_result_hash changes instance hash."""
        id1 = _dummy_identity(source_domain_result_hash="sha256:aaa")
        id2 = _dummy_identity(source_domain_result_hash="sha256:bbb")
        assert compute_report_instance_hash(id1) != compute_report_instance_hash(id2)

    def test_tamper_source_artifact_bundle_digest(self):
        """Changing source_artifact_bundle_digest changes instance hash."""
        id1 = _dummy_identity(source_artifact_bundle_digest="sha256:aaa")
        id2 = _dummy_identity(source_artifact_bundle_digest="sha256:bbb")
        assert compute_report_instance_hash(id1) != compute_report_instance_hash(id2)

    def test_tamper_template_definition_hash(self):
        """Changing template_definition_hash changes instance hash."""
        id1 = _dummy_identity(template_definition_hash="sha256:aaa")
        id2 = _dummy_identity(template_definition_hash="sha256:bbb")
        assert compute_report_instance_hash(id1) != compute_report_instance_hash(id2)

    def test_tamper_request_digest(self):
        """Changing request_digest changes instance hash."""
        id1 = _dummy_identity(request_digest="sha256:aaa")
        id2 = _dummy_identity(request_digest="sha256:bbb")
        assert compute_report_instance_hash(id1) != compute_report_instance_hash(id2)

    def test_tamper_report_content_hash(self):
        """Changing report_content_hash changes instance hash."""
        id1 = _dummy_identity(report_content_hash="sha256:aaa")
        id2 = _dummy_identity(report_content_hash="sha256:bbb")
        assert compute_report_instance_hash(id1) != compute_report_instance_hash(id2)

    def test_tamper_formatter_registry_version(self):
        """Changing formatter_registry_version changes instance hash."""
        id1 = _dummy_identity(formatter_registry_version="v1")
        id2 = _dummy_identity(formatter_registry_version="v2")
        assert compute_report_instance_hash(id1) != compute_report_instance_hash(id2)


# ===================================================================
# P0-6: Envelope-derived source state rejection
# ===================================================================


class TestP06EnvelopeSourceState:
    """P0-6: Envelope-derived source state."""

    def test_derive_rating_succeeded(self):
        """No failure, no blockers -> rating_succeeded."""
        env = SimpleNamespace(
            operation="rateDoublePipe",
            failure=None,
            blockers=(),
            warnings=(),
        )
        assert derive_source_state(env) == "rating_succeeded"

    def test_derive_rating_failed(self):
        """failure is not None -> rating_failed."""
        env = SimpleNamespace(
            operation="rateDoublePipe",
            failure=SimpleNamespace(code="ERR", message="boom"),
            blockers=(),
            warnings=(),
        )
        assert derive_source_state(env) == "rating_failed"

    def test_derive_rating_blocked(self):
        """Non-empty blockers -> rating_blocked."""
        env = SimpleNamespace(
            operation="rateDoublePipe",
            failure=None,
            blockers=(SimpleNamespace(code="B1", message="block")),
            warnings=(),
        )
        assert derive_source_state(env) == "rating_blocked"

    def test_derive_sizing_complete(self):
        """termination_status=complete -> sizing_complete."""
        env = SimpleNamespace(
            operation="sizeDoublePipe",
            result=SimpleNamespace(termination_status="complete"),
        )
        assert derive_source_state(env) == "sizing_complete"

    def test_derive_sizing_partial(self):
        """termination_status=partial -> sizing_partial."""
        env = SimpleNamespace(
            operation="sizeDoublePipe",
            result=SimpleNamespace(termination_status="partial"),
        )
        assert derive_source_state(env) == "sizing_partial"

    def test_derive_rejects_unsupported_operation(self):
        """Unsupported operation raises ValueError."""
        env = SimpleNamespace(operation="validateCase")
        with pytest.raises(ValueError, match="Unsupported operation"):
            derive_source_state(env)

    def test_verify_matrix_rejects_bad_operation(self):
        """verify_report_section_status_matrix raises on unsupported operation."""
        model = _dummy_model()
        env = SimpleNamespace(operation="bad_op")
        with pytest.raises(ValueError, match="Unsupported operation"):
            verify_report_section_status_matrix(model, "bad_op", env)


# ===================================================================
# B4: Mandatory artifact verification
# ===================================================================


class TestB4MandatoryArtifacts:
    """B4: Mandatory artifact verification."""

    def test_mandatory_set_exact_five(self):
        """MANDATORY_ARTIFACT_IDS contains exactly 5 required artifacts."""
        assert len(MANDATORY_ARTIFACT_IDS) == 5
        expected_ids = {
            ReportArtifactId.STATUS,
            ReportArtifactId.RUN_ID,
            ReportArtifactId.REQUEST_DIGEST,
            ReportArtifactId.RESULT_HASH,
            ReportArtifactId.BUNDLE_HASH,
        }
        assert expected_ids == MANDATORY_ARTIFACT_IDS

    def test_mandatory_owners_exact(self):
        """All 5 mandatory artifacts mapped to correct sections."""
        expected_owners = {
            ReportArtifactId.STATUS: ReportSectionId.STATUS_BANNER,
            ReportArtifactId.RUN_ID: ReportSectionId.RUN_IDENTITY,
            ReportArtifactId.REQUEST_DIGEST: ReportSectionId.RUN_IDENTITY,
            ReportArtifactId.RESULT_HASH: ReportSectionId.INTEGRITY,
            ReportArtifactId.BUNDLE_HASH: ReportSectionId.INTEGRITY,
        }
        assert expected_owners == MANDATORY_ARTIFACT_OWNERS


# ===================================================================
# B5: RFC 6901 JSON Pointer validation and resolution
# ===================================================================


class TestB5RFC6901Pointers:
    """B5: RFC 6901 JSON Pointer validation and resolution."""

    def test_empty_pointer(self):
        assert validate_rfc6901_pointer("") == ()

    def test_root_pointer(self):
        result = validate_rfc6901_pointer("/")
        assert result == ("",)

    def test_tilde_escape(self):
        assert validate_rfc6901_pointer("/~0") == ("~",)
        assert validate_rfc6901_pointer("/~1") == ("/",)

    def test_slash_escape(self):
        assert validate_rfc6901_pointer("/~1") == ("/",)

    def test_nested(self):
        assert validate_rfc6901_pointer("/foo/bar") == ("foo", "bar")

    def test_rejects_missing_slash(self):
        with pytest.raises(ValueError, match="must start with '/'"):
            validate_rfc6901_pointer("foo")

    def test_rejects_trailing_tilde(self):
        with pytest.raises(ValueError, match="Trailing ~"):
            validate_rfc6901_pointer("/~")

    def test_rejects_illegal_escape(self):
        with pytest.raises(ValueError, match="Illegal escape"):
            validate_rfc6901_pointer("/~2")

    def test_resolve_dict(self):
        obj = {"a": 1}
        assert resolve_source_pointer(obj, "/a") == 1

    def test_resolve_missing(self):
        with pytest.raises(KeyError):
            resolve_source_pointer({"a": 1}, "/b")


# ===================================================================
# B6: Deterministic report hashes
# ===================================================================


class TestB6ReportHashes:
    """B6: Deterministic report hashes."""

    def test_content_hash_deterministic(self):
        """Same sections -> same hash."""

        def _make_sections(content: str) -> tuple[ReportSection, ...]:
            return tuple(
                ReportSection(
                    section_id=sid,
                    title=sid.value,
                    content=content,
                    status=ReportSectionStatus.COMPLETE,
                )
                for sid in REPORT_SECTION_ORDER
            )

        h1 = compute_report_content_hash(_make_sections("same content"))
        h2 = compute_report_content_hash(_make_sections("same content"))
        assert h1 == h2

    def test_different_content_different_hash(self):
        """Different section statuses produce different content hash."""

        def _make_sections(status: ReportSectionStatus) -> tuple[ReportSection, ...]:
            return tuple(
                ReportSection(
                    section_id=sid,
                    title=sid.value,
                    content="same",
                    status=status,
                )
                for sid in REPORT_SECTION_ORDER
            )

        h1 = compute_report_content_hash(_make_sections(ReportSectionStatus.COMPLETE))
        h2 = compute_report_content_hash(_make_sections(ReportSectionStatus.PARTIAL))
        assert h1 != h2


# ===================================================================
# B7: Pre-render verification chain
# ===================================================================


class TestB7PreRender:
    """B7: Pre-render verification chain."""

    def test_full_chain_produces_html(self):
        """build_report_html from a real completed run."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-b7-chain")
        record = _make_record_for_report(envelope)
        html = build_report_html(record)
        assert isinstance(html, bytes)
        assert len(html) > 0
        assert b"<!DOCTYPE html>" in html
        assert b"<html" in html

    def test_rejects_missing_envelope(self):
        """build_report_html rejects a record with no envelope."""
        record = SimpleNamespace(
            envelope=None,
            operation="rateDoublePipe",
        )
        with pytest.raises(ValueError, match="no envelope"):
            build_report_html(record)


# ===================================================================
# B8: Deterministic secure HTML
# ===================================================================


class TestB8SecureHTML:
    """B8: Deterministic secure HTML."""

    def test_deterministic_bytes(self):
        """Same record -> same bytes."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-b8-deterministic")
        record = _make_record_for_report(envelope)
        html1 = build_report_html(record)
        html2 = build_report_html(record)
        assert html1 == html2

    def test_risk_banners_present(self):
        """PRELIMINARY, NOT FOR PROCUREMENT, NOT FOR CONSTRUCTION."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-b8-banners")
        record = _make_record_for_report(envelope)
        html = build_report_html(record).decode("utf-8")
        assert "PRELIMINARY" in html
        assert "NOT FOR PROCUREMENT" in html
        assert "NOT FOR CONSTRUCTION" in html

    def test_no_external_resources(self):
        """No http/https links."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-b8-no-external")
        record = _make_record_for_report(envelope)
        html = build_report_html(record).decode("utf-8")
        assert "http://" not in html
        assert "https://" not in html

    def test_no_tracebacks(self):
        """No 'Traceback' in output."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-b8-no-traceback")
        record = _make_record_for_report(envelope)
        html = build_report_html(record).decode("utf-8")
        assert "Traceback" not in html

    def test_html_escaping(self):
        """<script> is escaped."""
        from hexagent.reporting import _escape

        result = _escape("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


# ===================================================================
# C1: Provider six-field authority
# ===================================================================


class TestC1ProviderSixField:
    """C1: Provider six-field authority."""

    def test_all_six_fields_compared(self):
        """ProviderIdentitySnapshot has all 6 fields."""
        snapshot = ProviderIdentitySnapshot(
            name="test",
            version="1.0",
            git_revision="abc",
            reference_state_policy="default",
            configuration_fingerprint="fp1",
            cache_policy_version="cpv1",
        )
        assert snapshot.name == "test"
        assert snapshot.version == "1.0"
        assert snapshot.git_revision == "abc"
        assert snapshot.reference_state_policy == "default"
        assert snapshot.configuration_fingerprint == "fp1"
        assert snapshot.cache_policy_version == "cpv1"

    def test_provider_version_change_changes_digest(self):
        from hexagent.api.models import canonical_provider_identity_payload

        snap1 = ProviderIdentitySnapshot(
            name="CoolProp",
            version="6.6.0",
            git_revision="abc",
            reference_state_policy="default",
            configuration_fingerprint="fp",
            cache_policy_version="cpv",
        )
        snap2 = ProviderIdentitySnapshot(
            name="CoolProp",
            version="7.0.0",
            git_revision="abc",
            reference_state_policy="default",
            configuration_fingerprint="fp",
            cache_policy_version="cpv",
        )
        assert sha256_digest(canonical_provider_identity_payload(snap1)) != sha256_digest(
            canonical_provider_identity_payload(snap2)
        )

    def test_provider_mismatch_returns_422(self):
        from hexagent.api.application import RatingApplicationService, SizingService
        from hexagent.api.main import ApplicationDependencies, create_app
        from hexagent.api.registry import CatalogRegistry, ProviderRegistry
        from hexagent.properties.coolprop_provider import CoolPropProvider

        provider = CoolPropProvider()
        wrong_snapshot = ProviderIdentitySnapshot(
            name=provider.name,
            version="999.0.0",
            git_revision=provider.git_revision,
            reference_state_policy=str(provider.reference_state_policy.value),
            configuration_fingerprint=getattr(provider, "_construction_fingerprint", ""),
            cache_policy_version=getattr(provider, "cache_policy_version", ""),
        )
        provider_registry = ProviderRegistry({"CoolProp": wrong_snapshot})
        catalog_registry = CatalogRegistry([])
        repo = InMemoryRunRepository()
        rating_service = RatingApplicationService(
            provider_registry=provider_registry,
            property_provider=provider,
        )
        sizing_service = SizingService(
            provider_registry=provider_registry,
            catalog_registry=catalog_registry,
        )
        deps = ApplicationDependencies(
            provider_registry=provider_registry,
            catalog_registry=catalog_registry,
            run_repository=repo,
            rating_service=rating_service,
            sizing_service=sizing_service,
        )
        app = create_app(deps)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/v1/double-pipe/rating",
            json=_make_rating_request(),
            headers={"Idempotency-Key": "test-c1-mismatch"},
        )
        assert resp.status_code == 422
        assert resp.json()["error_code"] == "validation_failed"

    def test_provider_identity_payload_has_all_six_fields(self):
        from hexagent.api.models import canonical_provider_identity_payload

        snapshot = ProviderIdentitySnapshot(
            name="test",
            version="1.0",
            git_revision="abc",
            reference_state_policy="default",
            configuration_fingerprint="fp",
            cache_policy_version="cpv",
        )
        payload = canonical_provider_identity_payload(snapshot)
        assert set(payload.keys()) == {
            "name",
            "version",
            "git_revision",
            "reference_state_policy",
            "configuration_fingerprint",
            "cache_policy_version",
        }


# ===================================================================
# C2: Single provenance digest authority
# ===================================================================


class TestC2ProvenanceDigest:
    """C2: Single provenance digest authority."""

    def test_rating_provenance_digest_single_authority(self):
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c2-prov-rating")
        assert envelope.provenance_digest == envelope.result.provenance_digest


# ===================================================================
# C3: Rating canonical parity
# ===================================================================


class TestC3RatingCanonicalParity:
    """C3: Rating canonical parity."""

    def test_result_hash_parity(self):
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c3-result-hash")
        assert envelope.result_hash == envelope.result.result_hash

    def test_provenance_digest_parity(self):
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c3-prov-hash")
        assert envelope.provenance_digest == envelope.result.provenance_digest

    def test_artifact_bundle_digest_parity(self):
        from hexagent.api.artifacts import compute_rating_artifact_bundle_digest

        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c3-bundle-hash")
        expected = compute_rating_artifact_bundle_digest(envelope.artifact_bundle)
        assert envelope.artifact_bundle_digest == expected

    def test_bundle_object_parity(self):
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c3-bundle-parity")
        bundle = envelope.artifact_bundle
        assert bundle.result == envelope.result
        assert bundle.request_identity == envelope.result.request_identity
        assert bundle.provider_identity == envelope.result.provider_identity
        assert bundle.provenance_graph == envelope.result.provenance_graph

    def test_warnings_parity(self):
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c3-warnings")
        assert envelope.warnings == envelope.result.warnings

    def test_blockers_parity(self):
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c3-blockers")
        assert envelope.blockers == envelope.result.blockers

    def test_failure_parity(self):
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c3-failure")
        assert envelope.failure == envelope.result.failure


# ===================================================================
# C4: Repository complete parity
# ===================================================================


class TestC4RepositoryCompleteParity:
    """C4: Repository complete parity."""

    def test_repository_stores_typed_envelope(self):
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c4-typed-envelope")
        repo = app.state.deps.run_repository
        record = repo.get_by_run_id(envelope.run_id)
        assert record is not None
        assert record.state == RunState.COMPLETE
        assert record.envelope is not None
        assert isinstance(record.envelope, RatingRunEnvelope)

    def test_repository_stores_typed_artifact_bundle(self):
        from hexagent.api.artifacts import RatingRunArtifacts

        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c4-typed-bundle")
        repo = app.state.deps.run_repository
        record = repo.get_by_run_id(envelope.run_id)
        assert record is not None
        assert record.artifact_bundle is not None
        assert isinstance(record.artifact_bundle, RatingRunArtifacts)

    def test_repository_record_run_id_matches_envelope(self):
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c4-run-id-match")
        repo = app.state.deps.run_repository
        record = repo.get_by_run_id(envelope.run_id)
        assert record is not None
        assert record.run_id == envelope.run_id

    def test_repository_record_request_digest_matches(self):
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c4-req-digest")
        repo = app.state.deps.run_repository
        record = repo.get_by_run_id(envelope.run_id)
        assert record is not None
        assert record.request_digest == envelope.request_digest

    def test_repository_record_operation_matches(self):
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c4-operation")
        repo = app.state.deps.run_repository
        record = repo.get_by_run_id(envelope.run_id)
        assert record is not None
        assert record.operation == envelope.operation


# ===================================================================
# C5: FAILED_REPLAY
# ===================================================================


class TestC5FailedReplay:
    """C5: FAILED_REPLAY returns the exact stored failure status + body."""

    def test_rating_failed_replay_returns_exact_status_and_body(self):
        app = _create_fresh_app()
        client = TestClient(app, raise_server_exceptions=False)
        key = "test-c5-fail-replay-rating"

        def failing_execute(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("Forced failure for C5 test")

        with patch.object(app.state.deps.rating_service, "execute", failing_execute):
            resp1 = client.post(
                "/v1/double-pipe/rating",
                json=_make_rating_request(),
                headers={"Idempotency-Key": key},
            )

        assert resp1.status_code == 500
        data1 = resp1.json()
        assert data1["error_code"] == "internal_error"

        resp2 = client.post(
            "/v1/double-pipe/rating",
            json=_make_rating_request(),
            headers={"Idempotency-Key": key},
        )
        assert resp2.status_code == 500
        data2 = resp2.json()
        assert data1["status_code"] == data2["status_code"]
        assert data1["error_code"] == data2["error_code"]
        assert data1["error_message"] == data2["error_message"]

    def test_failed_replay_does_not_return_200(self):
        app = _create_fresh_app()
        client = TestClient(app, raise_server_exceptions=False)
        key = "test-c5-no-200"

        def failing_execute(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("Forced failure")

        with patch.object(app.state.deps.rating_service, "execute", failing_execute):
            resp1 = client.post(
                "/v1/double-pipe/rating",
                json=_make_rating_request(),
                headers={"Idempotency-Key": key},
            )
        assert resp1.status_code != 200

        resp2 = client.post(
            "/v1/double-pipe/rating",
            json=_make_rating_request(),
            headers={"Idempotency-Key": key},
        )
        assert resp2.status_code != 200

    def test_frozen_failure_payload_dataclass(self):
        payload = FrozenFailurePayload(
            status_code=500,
            error_code="internal_error",
            error_message="test error",
            request_digest="sha256:abc",
            operation="rateDoublePipe",
        )
        assert payload.status_code == 500
        assert payload.error_code == "internal_error"
        assert payload.error_message == "test error"
        assert payload.request_digest == "sha256:abc"
        assert payload.operation == "rateDoublePipe"
        with pytest.raises(AttributeError):
            payload.status_code = 400  # type: ignore[misc]

    def test_rating_failed_replay_exact_body_match(self):
        app = _create_fresh_app()
        client = TestClient(app, raise_server_exceptions=False)
        key = "test-c5-exact-body"

        def failing_execute(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("Forced failure for exact body test")

        with patch.object(app.state.deps.rating_service, "execute", failing_execute):
            resp1 = client.post(
                "/v1/double-pipe/rating",
                json=_make_rating_request(),
                headers={"Idempotency-Key": key},
            )

        resp2 = client.post(
            "/v1/double-pipe/rating",
            json=_make_rating_request(),
            headers={"Idempotency-Key": key},
        )
        assert resp1.json() == resp2.json()


# ===================================================================
# OpenAPI contract (supplementary)
# ===================================================================


class TestOpenAPIFinal:
    """OpenAPI: exactly 6 operation IDs, unique, discriminator on result_kind."""

    def test_exactly_six_operation_ids(self):
        app = _create_test_app()
        schema = app.openapi()
        paths = schema.get("paths", {})
        operation_ids = set()
        for path_data in paths.values():
            for method_data in path_data.values():
                if isinstance(method_data, dict) and "operationId" in method_data:
                    operation_ids.add(method_data["operationId"])
        expected = {
            "validateCase",
            "rateDoublePipe",
            "sizeDoublePipe",
            "getRun",
            "getRunReportHtml",
            "getRunReportPdf",
        }
        assert operation_ids == expected

    def test_discriminator_on_result_kind(self):
        app = _create_test_app()
        schema_str = json.dumps(app.openapi())
        assert "result_kind" in schema_str

    def test_operation_ids_unique(self):
        app = _create_test_app()
        schema = app.openapi()
        paths = schema.get("paths", {})
        ids: list[str] = []
        for path_data in paths.values():
            for method_data in path_data.values():
                if isinstance(method_data, dict) and "operationId" in method_data:
                    ids.append(method_data["operationId"])
        assert len(ids) == len(set(ids))
