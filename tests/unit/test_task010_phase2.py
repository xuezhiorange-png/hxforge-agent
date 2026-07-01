"""TASK-010 Phase 2 contract tests.

Covers:
- P0-1: Frozen API surface (6 routes, correct paths, operation IDs)
- P0-3: Exact ApiError contract
- P0-4: Unified exception handlers
- P0-5: App factory (no mutable globals)
- P0-6: RunRepository state machine
- P0-7: Idempotency contract
- T45: DoublePipeService.size() never called
- Validation endpoint (real CoolProp)
- Rating endpoint (real CoolProp + real RatingApplicationService)
- Rating replay (idempotency)
- Run retrieval
- Envelope models
- OpenAPI contract

NO MagicMock for production success paths.  All production paths use
real CoolPropProvider, real ProviderRegistry, real InMemoryRunRepository,
real RatingApplicationService, and real SizingService.
MagicMock is ONLY used for the T45 poison trap (patching
DoublePipeService.size to verify it is never called).
"""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hexagent.api.envelopes import (
    RatingRunEnvelope,
    SizingRunEnvelope,
    ValidationRunEnvelope,
)
from hexagent.api.errors import VALID_ERROR_CODES, ApiError, ApiErrorCode, ErrorDetail
from hexagent.api.repository import (
    CASCasError,
    ClaimOutcome,
    IdempotencyConflictError,
    InMemoryRunRepository,
    RepositoryStateError,
    RunState,
)

# ===================================================================
# Helper: minimal typed objects for repository unit tests
# ===================================================================


def _make_rating_envelope_and_bundle(
    *,
    request_digest: str = "req1",
    run_id=None,
):
    """Build RatingRunEnvelope + RatingRunArtifacts for repo tests.

    Uses model_construct() to bypass validators but builds serializable
    objects so that full parity checks (P0-3) pass, including digest
    recomputation and verify_rating_artifact_bundle.
    """
    from hexagent.api.artifacts import RatingRunArtifacts, compute_rating_artifact_bundle_digest
    from hexagent.api.envelopes import RatingRunEnvelope
    from hexagent.core.heat_balance import ProviderIdentitySnapshot
    from hexagent.domain.provenance import ProvenanceGraph
    from hexagent.exchangers.double_pipe.result import (
        RatingRequestIdentity,
        RatingResult,
        RatingStatus,
        SolverDetailsModel,
    )
    from hexagent.exchangers.double_pipe.thermal import FlowArrangement

    _id = run_id or uuid4()

    result = RatingResult.model_construct(
        status=RatingStatus.SUCCEEDED,
        flow_arrangement=FlowArrangement.COUNTERFLOW,
        heat_duty_w=1000.0,
        hot_outlet_temperature_k=350.0,
        cold_outlet_temperature_k=310.0,
        tube_reynolds=None,
        tube_prandtl=None,
        tube_nusselt=None,
        tube_h=None,
        tube_selected_correlation_id=None,
        tube_selected_correlation_version=None,
        tube_applicability_status=None,
        annulus_reynolds=None,
        annulus_prandtl=None,
        annulus_nusselt=None,
        annulus_h=None,
        annulus_selected_correlation_id=None,
        annulus_selected_correlation_version=None,
        annulus_applicability_status=None,
        area_inner_m2=0.1,
        area_outer_m2=0.15,
        resistance_breakdown=None,
        U_inner_basis=None,
        U_outer_basis=None,
        UA_w_k=None,
        C_hot_w_k=None,
        C_cold_w_k=None,
        C_min_w_k=None,
        C_max_w_k=None,
        capacity_ratio=None,
        NTU=None,
        effectiveness=None,
        LMTD_k=None,
        energy_residual_w=None,
        ua_lmtd_residual_w=None,
        Q_hot_w=None,
        Q_cold_w=None,
        relative_energy_residual=None,
        energy_tolerance_w=None,
        relative_ua_lmtd_residual=None,
        ua_lmtd_tolerance_w=None,
        iterations=1,
        converged=True,
        solver_termination_reason="converged",
        solver_details=SolverDetailsModel.model_construct(
            iterations=1,
            residual_w=0.0,
            function_evaluations=1,
            termination_reason="converged",
        ),
        warnings=(),
        blockers=(),
        failure=None,
        property_calls=(),
        provider_identity=ProviderIdentitySnapshot(
            name="test",
            version="1.0",
            git_revision="abc",
            reference_state_policy="IAPWS-IF97",
        ),
        request_identity=RatingRequestIdentity(
            hot_fluid_name="Water",
            hot_fluid_backend="iapws-if97",
            hot_fluid_components=(),
            cold_fluid_name="Water",
            cold_fluid_backend="iapws-if97",
            cold_fluid_components=(),
            hot_mass_flow_kg_s=1.0,
            cold_mass_flow_kg_s=1.0,
            hot_inlet_pressure_pa=101325.0,
            cold_inlet_pressure_pa=101325.0,
            hot_inlet_temperature_k=350.0,
            cold_inlet_temperature_k=300.0,
            flow_arrangement="counterflow",
            geometry={},
            solver_absolute_residual_w=1e-6,
            solver_relative_residual_fraction=1e-6,
            solver_bracket_temperature_tolerance_k=0.01,
            solver_max_iterations=100,
        ),
        result_hash="sha256:hash",
        provenance_graph=ProvenanceGraph(),
        provenance_digest="sha256:prov",
    )

    bundle = RatingRunArtifacts.model_construct(
        canonical_request_snapshot={},
        request_identity=result.request_identity,
        geometry_snapshot=None,
        solver_settings=None,
        provider_identity=result.provider_identity,
        result=result,
        provenance_graph=ProvenanceGraph(),
        artifact_bundle_digest="",
    )
    digest = compute_rating_artifact_bundle_digest(bundle)
    bundle = RatingRunArtifacts.model_construct(
        canonical_request_snapshot={},
        request_identity=result.request_identity,
        geometry_snapshot=None,
        solver_settings=None,
        provider_identity=result.provider_identity,
        result=result,
        provenance_graph=ProvenanceGraph(),
        artifact_bundle_digest=digest,
    )

    envelope = RatingRunEnvelope.model_construct(
        api_schema_version="1",
        operation="rateDoublePipe",
        run_id=_id,
        idempotency_key_digest="kid",
        request_digest=request_digest,
        result_kind="rating",
        result=result,
        result_hash=result.result_hash,
        warnings=(),
        blockers=(),
        failure=None,
        provenance=ProvenanceGraph(),
        provenance_digest=result.provenance_digest,
        artifact_bundle=bundle,
        artifact_bundle_digest=digest,
        report_links=None,
    )
    return envelope, bundle


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

    from hexagent.api.application import RatingApplicationService, SizingService
    from hexagent.api.main import ApplicationDependencies, create_app
    from hexagent.api.registry import CatalogRegistry, ProviderRegistry
    from hexagent.api.repository import InMemoryRunRepository
    from hexagent.core.heat_balance import ProviderIdentitySnapshot
    from hexagent.properties.coolprop_provider import CoolPropProvider

    provider = CoolPropProvider()
    # C1: Build snapshot with ALL 6 identity fields matching the kernel's
    # _provider_snapshot() output (now captures configuration_fingerprint
    # and cache_policy_version).
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
    deps = ApplicationDependencies(
        provider_registry=provider_registry,
        catalog_registry=catalog_registry,
        run_repository=repo,
        rating_service=rating_service,
        sizing_service=sizing_service,
    )
    app = create_app(deps)
    _APP_CACHE["app"] = app
    return app


def _create_fresh_app() -> FastAPI:
    """Create a test app with a fresh InMemoryRunRepository.

    Used when tests need isolation from the cached app's repository state.
    """
    from hexagent.api.application import RatingApplicationService, SizingService
    from hexagent.api.main import ApplicationDependencies, create_app
    from hexagent.api.registry import CatalogRegistry, ProviderRegistry
    from hexagent.api.repository import InMemoryRunRepository
    from hexagent.core.heat_balance import ProviderIdentitySnapshot
    from hexagent.properties.coolprop_provider import CoolPropProvider

    provider = CoolPropProvider()
    # C1: Build snapshot with ALL 6 identity fields matching the kernel's
    # _provider_snapshot() output (now captures configuration_fingerprint
    # and cache_policy_version).
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
    deps = ApplicationDependencies(
        provider_registry=provider_registry,
        catalog_registry=catalog_registry,
        run_repository=repo,
        rating_service=rating_service,
        sizing_service=sizing_service,
    )
    return create_app(deps)


# ===================================================================
# Request payload helpers
# ===================================================================


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
        "mass_flow": {"value": 1.0, "unit": "kg/s"},
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
    """Create a minimal valid RatingApiRequest payload for real CoolProp."""
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
    """Create a minimal valid SizingApiRequest payload.

    Uses the cached app's provider identity for expected_provider_identity.
    """
    app = _create_test_app()
    provider = app.state.deps.provider_registry
    # Get the CoolProp snapshot to build expected identity
    resolved = provider.resolve("CoolProp")
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
        "provider_ref": "CoolProp",
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
# P0-1: Frozen API surface
# ===================================================================


class TestFrozenAPISurface:
    """Verify 6 frozen routes with correct paths and operation IDs."""

    def _get_openapi_paths(self) -> dict[str, dict[str, Any]]:
        app = _create_test_app()
        return app.openapi().get("paths", {})

    def test_sizing_route_path(self):
        paths = self._get_openapi_paths()
        assert "/v1/double-pipe/sizing" in paths
        assert "post" in paths["/v1/double-pipe/sizing"]

    def test_validation_route_path(self):
        paths = self._get_openapi_paths()
        assert "/v1/cases/validate" in paths
        assert "post" in paths["/v1/cases/validate"]

    def test_rating_route_path(self):
        paths = self._get_openapi_paths()
        assert "/v1/double-pipe/rating" in paths
        assert "post" in paths["/v1/double-pipe/rating"]

    def test_run_retrieval_path(self):
        paths = self._get_openapi_paths()
        assert "/v1/runs/{run_id}" in paths
        assert "get" in paths["/v1/runs/{run_id}"]

    def test_report_html_path(self):
        paths = self._get_openapi_paths()
        assert "/v1/runs/{run_id}/report.html" in paths

    def test_report_pdf_path(self):
        paths = self._get_openapi_paths()
        assert "/v1/runs/{run_id}/report.pdf" in paths

    def test_operation_ids_present(self):
        paths = self._get_openapi_paths()
        operation_ids = set()
        for path_data in paths.values():
            for method_data in path_data.values():
                if isinstance(method_data, dict) and "operationId" in method_data:
                    operation_ids.add(method_data["operationId"])
        required = {
            "validateCase",
            "rateDoublePipe",
            "sizeDoublePipe",
            "getRun",
            "getRunReportHtml",
            "getRunReportPdf",
        }
        assert required.issubset(operation_ids)

    def test_no_legacy_design_route(self):
        paths = self._get_openapi_paths()
        assert "/v1/design/double-pipe" not in paths

    def test_no_wrong_sizing_path(self):
        paths = self._get_openapi_paths()
        assert "/v1/sizing/double-pipe" not in paths


# ===================================================================
# P0-3: Exact ApiError contract
# ===================================================================


class TestApiErrorContract:
    def test_api_error_has_all_fields(self):
        error = ApiError(
            api_schema_version="1",
            operation="test",
            status_code=422,
            error_code="validation_failed",
            error_message="test error",
            request_digest=None,
            details=(),
        )
        assert error.api_schema_version == "1"
        assert error.operation == "test"
        assert error.status_code == 422
        assert error.error_code == "validation_failed"
        assert error.error_message == "test error"
        assert error.request_digest is None
        assert error.details == ()

    def test_api_error_frozen(self):
        error = ApiError(
            api_schema_version="1",
            operation=None,
            status_code=500,
            error_code="internal_error",
            error_message="internal",
            request_digest=None,
            details=(),
        )
        with pytest.raises((AttributeError, ValueError, TypeError)):
            error.status_code = 400

    def test_error_code_enum_values(self):
        expected = {
            "validation_failed",
            "idempotency_conflict",
            "run_not_found",
            "pdf_not_available",
            "internal_error",
        }
        assert expected == VALID_ERROR_CODES

    def test_error_code_must_be_valid(self):
        with pytest.raises((AttributeError, ValueError, TypeError)):
            ApiError(
                api_schema_version="1",
                operation=None,
                status_code=400,
                error_code="invalid_code",
                error_message="test",
                request_digest=None,
                details=(),
            )

    def test_error_detail_preview_limit(self):
        long_value = "x" * 300
        detail = ErrorDetail(
            path=("field",),
            code="error",
            message="msg",
            rejected_value_preview=long_value,
        )
        assert detail.rejected_value_preview is not None
        assert len(detail.rejected_value_preview) == 200

    def test_error_detail_frozen(self):
        detail = ErrorDetail(path=(), code="c", message="m")
        with pytest.raises((AttributeError, ValueError, TypeError)):
            detail.code = "new"

    def test_details_deterministic_ordering(self):
        d1 = ErrorDetail(path=("z",), code="a", message="m1")
        d2 = ErrorDetail(path=("a",), code="z", message="m2")
        d3 = ErrorDetail(path=("a",), code="a", message="m3")
        error = ApiError(
            api_schema_version="1",
            operation=None,
            status_code=422,
            error_code="validation_failed",
            error_message="test",
            request_digest=None,
            details=(d1, d2, d3),
        )
        paths_codes = [(d.path, d.code) for d in error.details]
        assert paths_codes == sorted(paths_codes)

    def test_api_error_json_serialization(self):
        error = ApiError(
            api_schema_version="1",
            operation="sizeDoublePipe",
            status_code=422,
            error_code="validation_failed",
            error_message="bad input",
            request_digest="sha256:abc",
            details=(
                ErrorDetail(
                    path=("case", "hot_stream"),
                    code="value_error",
                    message="invalid",
                ),
            ),
        )
        data = error.model_dump(mode="json")
        assert data["api_schema_version"] == "1"
        assert data["error_code"] == "validation_failed"
        assert data["status_code"] == 422

    def test_api_error_code_is_strenum(self):
        """ApiErrorCode values are StrEnum instances."""
        assert isinstance(ApiErrorCode.VALIDATION_FAILED, str)
        assert str(ApiErrorCode.VALIDATION_FAILED) == "validation_failed"


# ===================================================================
# P0-4: Unified exception handlers
# ===================================================================


class TestExceptionHandlers:
    def test_validation_error_returns_frozen_api_error(self):
        app = _create_test_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/v1/cases/validate", json={"invalid": True})
        assert resp.status_code == 422
        data = resp.json()
        assert data["api_schema_version"] == "1"
        assert data["error_code"] == "validation_failed"
        assert data["status_code"] == 422

    def test_no_traceback_in_error_response(self):
        app = _create_test_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/v1/double-pipe/sizing",
            json={"invalid": "data"},
            headers={"Idempotency-Key": "test-key-1"},
        )
        assert resp.status_code == 422
        body = resp.text
        assert "Traceback" not in body

    def test_501_pdf_not_available(self):
        app = _create_test_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(f"/v1/runs/{uuid4()}/report.pdf")
        assert resp.status_code == 501
        data = resp.json()
        assert data["error_code"] == "pdf_not_available"

    def test_404_run_not_found(self):
        app = _create_test_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(f"/v1/runs/{uuid4()}")
        assert resp.status_code == 404
        data = resp.json()
        assert data["error_code"] == "run_not_found"


# ===================================================================
# P0-5: App factory (no mutable globals)
# ===================================================================


class TestAppFactory:
    def test_create_app_returns_fastapi(self):
        app = _create_test_app()
        assert isinstance(app, FastAPI)

    def test_app_state_has_deps(self):
        app = _create_test_app()
        assert hasattr(app.state, "deps")

    def test_different_apps_have_different_repos(self):
        app1 = _create_fresh_app()
        app2 = _create_fresh_app()
        assert app1.state.deps.run_repository is not app2.state.deps.run_repository


# ===================================================================
# P0-6: RunRepository state machine
# ===================================================================


class TestRunRepository:
    def test_new_claim(self):
        repo = InMemoryRunRepository()
        result = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
        )
        assert result.outcome == ClaimOutcome.NEW_CLAIM
        assert result.record.state == RunState.CLAIMED

    def test_complete_replay(self):
        repo = InMemoryRunRepository()
        claim = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
        )
        rec = repo.start(
            owner_token=claim.record.owner_token,
            expected_version=claim.record.record_version,
        )
        envelope, bundle = _make_rating_envelope_and_bundle(
            request_digest="req1",
            run_id=rec.run_id,
        )
        repo.complete(
            owner_token=claim.record.owner_token,
            expected_version=rec.record_version,
            envelope=envelope,
            artifact_bundle=bundle,
        )
        result = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
        )
        assert result.outcome == ClaimOutcome.COMPLETE_REPLAY

    def test_complete_different_digest_conflict(self):
        repo = InMemoryRunRepository()
        claim = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
        )
        rec = repo.start(
            owner_token=claim.record.owner_token,
            expected_version=claim.record.record_version,
        )
        envelope, bundle = _make_rating_envelope_and_bundle(
            request_digest="req1",
            run_id=rec.run_id,
        )
        repo.complete(
            owner_token=claim.record.owner_token,
            expected_version=rec.record_version,
            envelope=envelope,
            artifact_bundle=bundle,
        )
        with pytest.raises(IdempotencyConflictError):
            repo.claim(
                namespace_digest="ns1",
                request_digest="req2",
                operation="rateDoublePipe",
            )

    def test_in_progress(self):
        repo = InMemoryRunRepository()
        repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
        )
        result = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
        )
        assert result.outcome == ClaimOutcome.IN_PROGRESS

    def test_stale_rejected(self):
        clock_time = datetime(2025, 1, 1, tzinfo=UTC)
        clock = lambda: clock_time  # noqa: E731
        repo = InMemoryRunRepository(clock=clock)
        repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
        )
        clock_time = datetime(2025, 1, 2, tzinfo=UTC)
        result = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
            takeover=False,
        )
        assert result.outcome == ClaimOutcome.STALE_REJECTED

    def test_stale_takeover(self):
        clock_time = datetime(2025, 1, 1, tzinfo=UTC)
        clock = lambda: clock_time  # noqa: E731
        repo = InMemoryRunRepository(clock=clock)
        claim = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
        )
        old_token = claim.record.owner_token
        old_version = claim.record.record_version
        clock_time = datetime(2025, 1, 2, tzinfo=UTC)
        result = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
            takeover=True,
        )
        assert result.outcome == ClaimOutcome.STALE_TAKEOVER
        assert result.record.owner_token != old_token
        assert result.record.record_version > old_version

    def test_old_owner_cas_failure_after_takeover(self):
        clock_time = datetime(2025, 1, 1, tzinfo=UTC)
        clock = lambda: clock_time  # noqa: E731
        repo = InMemoryRunRepository(clock=clock)
        claim = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
        )
        old_token = claim.record.owner_token
        old_version = claim.record.record_version
        clock_time = datetime(2025, 1, 2, tzinfo=UTC)
        repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
            takeover=True,
        )
        with pytest.raises(CASCasError):
            repo.heartbeat(owner_token=old_token, expected_version=old_version)

    def test_cas_version_mismatch(self):
        repo = InMemoryRunRepository()
        claim = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
        )
        with pytest.raises(CASCasError):
            repo.start(
                owner_token=claim.record.owner_token,
                expected_version=999,
            )

    def test_cas_unknown_owner_token(self):
        repo = InMemoryRunRepository()
        with pytest.raises(CASCasError):
            repo.heartbeat(owner_token=uuid4(), expected_version=1)

    def test_start_requires_claimed_state(self):
        repo = InMemoryRunRepository()
        claim = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
        )
        rec = repo.start(
            owner_token=claim.record.owner_token,
            expected_version=claim.record.record_version,
        )
        with pytest.raises(RepositoryStateError):
            repo.start(
                owner_token=claim.record.owner_token,
                expected_version=rec.record_version,
            )

    def test_complete_requires_running_state(self):
        repo = InMemoryRunRepository()
        claim = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
        )
        with pytest.raises(RepositoryStateError):
            repo.complete(
                owner_token=claim.record.owner_token,
                expected_version=claim.record.record_version,
                envelope=None,
                artifact_bundle=None,
            )

    def test_failed_replay(self):
        repo = InMemoryRunRepository()
        claim = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
        )
        rec = repo.start(
            owner_token=claim.record.owner_token,
            expected_version=claim.record.record_version,
        )
        repo.fail(
            owner_token=claim.record.owner_token,
            expected_version=rec.record_version,
            failure="test",
        )
        result = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
        )
        assert result.outcome == ClaimOutcome.FAILED_REPLAY

    def test_failed_different_digest_conflict(self):
        repo = InMemoryRunRepository()
        claim = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
        )
        rec = repo.start(
            owner_token=claim.record.owner_token,
            expected_version=claim.record.record_version,
        )
        repo.fail(
            owner_token=claim.record.owner_token,
            expected_version=rec.record_version,
            failure="test",
        )
        with pytest.raises(IdempotencyConflictError):
            repo.claim(
                namespace_digest="ns1",
                request_digest="req2",
                operation="rateDoublePipe",
            )

    def test_get_by_run_id(self):
        repo = InMemoryRunRepository()
        claim = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
        )
        found = repo.get_by_run_id(claim.record.run_id)
        assert found is not None
        assert found.run_id == claim.record.run_id

    def test_get_by_namespace(self):
        repo = InMemoryRunRepository()
        repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="rateDoublePipe",
        )
        found = repo.get_by_namespace("ns1")
        assert found is not None

    def test_get_by_run_id_not_found(self):
        repo = InMemoryRunRepository()
        assert repo.get_by_run_id(uuid4()) is None

    def test_get_by_namespace_not_found(self):
        repo = InMemoryRunRepository()
        assert repo.get_by_namespace("nonexistent") is None

    def test_thread_safety(self):
        repo = InMemoryRunRepository()
        errors: list[Exception] = []

        def claim_ns(ns: str) -> None:
            try:
                for i in range(10):
                    repo.claim(
                        namespace_digest=f"{ns}-{i}",
                        request_digest=f"req-{i}",
                        operation="rateDoublePipe",
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=claim_ns, args=(f"t{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0

    def test_claim_outcomes_are_strenum(self):
        """ClaimOutcome and RunState are StrEnum instances."""
        assert isinstance(ClaimOutcome.NEW_CLAIM, str)
        assert isinstance(RunState.CLAIMED, str)
        assert str(ClaimOutcome.NEW_CLAIM) == "new_claim"
        assert str(RunState.CLAIMED) == "claimed"


# ===================================================================
# P0-7: Idempotency contract
# ===================================================================


class TestIdempotencyContract:
    def test_idempotency_key_required_for_sizing(self):
        app = _create_test_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/v1/double-pipe/sizing",
            json=_make_sizing_request(),
        )
        assert resp.status_code == 422

    def test_idempotency_key_required_for_rating(self):
        app = _create_test_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/v1/double-pipe/rating",
            json=_make_rating_request(),
        )
        assert resp.status_code == 422

    def test_empty_idempotency_key_rejected(self):
        app = _create_test_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/v1/double-pipe/sizing",
            json=_make_sizing_request(),
            headers={"Idempotency-Key": ""},
        )
        assert resp.status_code == 422

    def test_long_idempotency_key_rejected(self):
        app = _create_test_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/v1/double-pipe/sizing",
            json=_make_sizing_request(),
            headers={"Idempotency-Key": "x" * 129},
        )
        assert resp.status_code == 422

    def test_control_char_in_key_rejected(self):
        app = _create_test_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/v1/double-pipe/sizing",
            json=_make_sizing_request(),
            headers={"Idempotency-Key": "key\x00bad"},
        )
        assert resp.status_code == 422


# ===================================================================
# T45: DoublePipeService.size() poison trap
# ===================================================================


class TestForbiddenDoublePipeServiceSize:
    """Verify DoublePipeService.size() is never called by the sizing endpoint.

    The sizing endpoint uses the SizingService (Phase 1 projection) and
    _execute_sizing (Phase 3 pipeline).  Neither path should touch
    DoublePipeService.size().  This test patches size() with a poison
    function and verifies it was never invoked.
    """

    def test_poison_trap_not_triggered(self):
        from hexagent.exchangers.double_pipe.service import DoublePipeService

        app = _create_fresh_app()
        client = TestClient(app, raise_server_exceptions=False)
        poison_called = {"count": 0}

        def poison(*args: Any, **kwargs: Any) -> None:
            poison_called["count"] += 1
            raise RuntimeError("DoublePipeService.size() was called!")

        with patch.object(DoublePipeService, "size", poison):
            client.post(
                "/v1/double-pipe/sizing",
                json=_make_sizing_request(),
                headers={"Idempotency-Key": "test-poison-key"},
            )
        # The sizing endpoint may return 422 (catalog mismatch) or
        # 501 (optimization pipeline not wired) — but DoublePipeService.size()
        # must NOT have been called.
        assert poison_called["count"] == 0


# ===================================================================
# Validation endpoint (real CoolProp)
# ===================================================================


class TestValidationEndpoint:
    """Validation endpoint tests using real CoolProp provider."""

    def test_valid_request_returns_200(self):
        """A valid validation request must return 200 (not 200 or 422)."""
        app = _create_test_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/v1/cases/validate", json=_make_validation_request())
        assert resp.status_code == 200
        data = resp.json()
        assert data["result_kind"] == "validation"
        envelope = ValidationRunEnvelope.model_validate(data)
        assert envelope.request_digest.startswith("sha256:")
        assert envelope.api_schema_version == "1"
        assert envelope.operation == "validateCase"
        assert envelope.result is None
        assert envelope.validation_receipt_hash.startswith("sha256:")

    def test_extra_fields_rejected(self):
        app = _create_test_app()
        client = TestClient(app, raise_server_exceptions=False)
        payload = _make_validation_request()
        payload["unknown_field"] = "bad"
        resp = client.post("/v1/cases/validate", json=payload)
        assert resp.status_code == 422
        data = resp.json()
        assert data["api_schema_version"] == "1"
        assert data["error_code"] == "validation_failed"


# ===================================================================
# Rating endpoint (real CoolProp + real RatingApplicationService)
# ===================================================================


class TestRatingEndpoint:
    """Rating endpoint tests with real CoolProp provider."""

    def test_real_rating_returns_200(self):
        """Execute a real rating request via CoolProp and parse the envelope."""
        app = _create_fresh_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/v1/double-pipe/rating",
            json=_make_rating_request(),
            headers={"Idempotency-Key": "test-rating-key-1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["result_kind"] == "rating"
        assert data["api_schema_version"] == "1"
        assert data["result_hash"].startswith("sha256:")
        assert data["artifact_bundle"] is not None
        assert data["artifact_bundle_digest"].startswith("sha256:")
        assert data["provenance_digest"].startswith("sha256:")
        # Verify the envelope parses correctly via typed model
        envelope = RatingRunEnvelope.model_validate(data)
        assert envelope.result_kind == "rating"
        assert envelope.operation == "rateDoublePipe"
        assert envelope.request_digest.startswith("sha256:")
        assert len(envelope.idempotency_key_digest) == 64  # raw sha256 hex
        assert envelope.failure is None

    def test_rating_envelope_hash_parity(self):
        """Verify result_hash, provenance_digest, artifact_bundle_digest match."""
        app = _create_fresh_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/v1/double-pipe/rating",
            json=_make_rating_request(),
            headers={"Idempotency-Key": "test-rating-parity-key"},
        )
        assert resp.status_code == 200
        envelope = RatingRunEnvelope.model_validate(resp.json())
        # result_hash must match result's own hash
        assert envelope.result_hash == envelope.result.result_hash
        # provenance_digest must match result's provenance_digest
        # (computed by kernel using _provenance_graph_digest which excludes
        # result_hash from metadata — differs from provenance.compute_hash())
        assert envelope.provenance_digest == envelope.result.provenance_digest
        # artifact_bundle_digest must match bundle hash
        assert envelope.artifact_bundle_digest == envelope.artifact_bundle.artifact_bundle_digest

    def test_rating_artifact_bundle_typed(self):
        """Artifact bundle is typed RatingRunArtifacts, not a raw dict."""
        app = _create_fresh_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/v1/double-pipe/rating",
            json=_make_rating_request(),
            headers={"Idempotency-Key": "test-rating-artifacts-key"},
        )
        assert resp.status_code == 200
        data = resp.json()
        bundle = data["artifact_bundle"]
        assert "canonical_request_snapshot" in bundle
        assert "request_identity" in bundle
        assert "geometry_snapshot" in bundle
        assert "solver_settings" in bundle
        assert "provider_identity" in bundle
        assert "result" in bundle
        assert "provenance_graph" in bundle
        assert "artifact_bundle_digest" in bundle


# ===================================================================
# Rating replay (idempotency)
# ===================================================================


class TestRatingReplay:
    """Verify same idempotency key returns identical stored envelope."""

    def test_same_key_returns_identical_envelope(self):
        app = _create_fresh_app()
        client = TestClient(app, raise_server_exceptions=False)
        request_payload = _make_rating_request()
        key = "test-rating-replay-key"

        # First request — execute and store
        resp1 = client.post(
            "/v1/double-pipe/rating",
            json=request_payload,
            headers={"Idempotency-Key": key},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()

        # Second request with same key — replay
        resp2 = client.post(
            "/v1/double-pipe/rating",
            json=request_payload,
            headers={"Idempotency-Key": key},
        )
        assert resp2.status_code == 200
        data2 = resp2.json()

        # Envelopes must be identical (byte-for-byte JSON comparison)
        assert data1 == data2


# ===================================================================
# Run retrieval
# ===================================================================


class TestRunRetrieval:
    def test_not_found_returns_404(self):
        app = _create_test_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(f"/v1/runs/{uuid4()}")
        assert resp.status_code == 404
        data = resp.json()
        assert data["error_code"] == "run_not_found"


# ===================================================================
# Envelope models
# ===================================================================


class TestEnvelopeModels:
    def test_validation_envelope_fields(self):
        env = ValidationRunEnvelope(
            api_schema_version="1",
            operation="validateCase",
            run_id=uuid4(),
            request_digest="sha256:abc",
            result_kind="validation",
            result=None,
            validation_receipt_hash="sha256:def",
            report_links=None,
        )
        assert env.result_kind == "validation"
        assert env.report_links is None

    def test_sizing_envelope_failure_must_be_none(self):
        """SizingRunEnvelope rejects non-None failure field."""
        with pytest.raises(Exception, match="none_required|failure must be None"):
            SizingRunEnvelope(
                api_schema_version="1",
                operation="sizeDoublePipe",
                run_id=uuid4(),
                idempotency_key_digest="sha256:abc",
                request_digest="sha256:def",
                result_kind="sizing",
                result=None,
                result_hash="sha256:" + "b" * 64,
                warnings=(),
                blockers=(),
                failure="not_none",
                provenance=None,
                provenance_digest="",
                artifact_bundle=None,
                artifact_bundle_digest="",
                report_links=None,
            )


# ===================================================================
# OpenAPI contract
# ===================================================================


class TestOpenAPIContract:
    def test_exact_six_operation_ids(self):
        """Verify exactly 6 operation IDs in the OpenAPI schema."""
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

    def test_no_sizing_service_result_in_schema(self):
        """SizingServiceResult must not leak into the public OpenAPI schema."""
        app = _create_test_app()
        schema = app.openapi()
        schema_str = json.dumps(schema)
        assert "SizingServiceResult" not in schema_str

    def test_no_legacy_design_path(self):
        app = _create_test_app()
        schema = app.openapi()
        assert "/v1/design/double-pipe" not in schema.get("paths", {})

    def test_deterministic_schema_generation(self):
        app = _create_test_app()
        schema1 = json.dumps(app.openapi(), sort_keys=True)
        schema2 = json.dumps(app.openapi(), sort_keys=True)
        assert schema1 == schema2

    def test_discriminator_in_envelope_union(self):
        """AnyRunEnvelope uses result_kind as discriminator."""
        app = _create_test_app()
        schema = app.openapi()
        schema_str = json.dumps(schema)
        # The discriminated union should reference result_kind
        assert "result_kind" in schema_str

    def test_six_frozen_paths(self):
        """Verify the exact set of 6 paths."""
        app = _create_test_app()
        schema = app.openapi()
        paths = schema.get("paths", {})
        frozen_paths = {
            "/v1/cases/validate": {"post"},
            "/v1/double-pipe/rating": {"post"},
            "/v1/double-pipe/sizing": {"post"},
            "/v1/runs/{run_id}": {"get"},
            "/v1/runs/{run_id}/report.html": {"get"},
            "/v1/runs/{run_id}/report.pdf": {"get"},
        }
        for path, methods in frozen_paths.items():
            assert path in paths, f"Missing path: {path}"
            for method in methods:
                assert method in paths[path], f"Missing {method} {path}"
        # No extra paths beyond the frozen set
        assert set(paths.keys()) == set(frozen_paths.keys())


# ===================================================================
# P0-3: Repository.complete() trust boundary tamper tests
# ===================================================================


class TestCompleteTrustBoundary:
    """Tamper tests for the enhanced complete() trust boundary (P0-3).

    Each test creates a RUNNING record, then attempts complete() with
    a specific tamper.  On ANY failure the record must stay RUNNING,
    no state transition occurs, and no envelope is stored.
    """

    def _running_record(self, operation: str = "rateDoublePipe"):
        """Helper: create a RUNNING record ready for complete()."""
        repo = InMemoryRunRepository()
        claim = repo.claim(
            namespace_digest=f"ns-{operation}",
            request_digest="req1",
            operation=operation,
        )
        rec = repo.start(
            owner_token=claim.record.owner_token,
            expected_version=claim.record.record_version,
        )
        return repo, claim.record.owner_token, rec

    def _valid_rating_pair(self, *, request_digest: str = "req1"):
        """Helper: return a valid (envelope, bundle) for rating."""
        return _make_rating_envelope_and_bundle(request_digest=request_digest)

    # -- type rejection tests -----------------------------------------------

    def test_complete_rejects_wrong_envelope_type(self):
        """SizingRunEnvelope for rateDoublePipe → RepositoryStateError."""
        from hexagent.api.envelopes import ValidationRunEnvelope

        repo, token, rec = self._running_record("rateDoublePipe")
        wrong_env = ValidationRunEnvelope.model_construct(
            api_schema_version="1",
            operation="validateCase",
            run_id=rec.run_id,
            request_digest="req1",
            result_kind="validation",
            result=None,
            validation_receipt_hash="sha256:x",
            report_links=None,
        )
        env, bundle = self._valid_rating_pair()
        with pytest.raises(RepositoryStateError, match="RatingRunEnvelope"):
            repo.complete(
                owner_token=token,
                expected_version=rec.record_version,
                envelope=wrong_env,
                artifact_bundle=bundle,
            )
        # Record stays RUNNING
        stored = repo.get_by_run_id(rec.run_id)
        assert stored.state == RunState.RUNNING
        assert stored.completed_at is None
        assert stored.envelope is None
        assert stored.artifact_bundle is None

    def test_complete_rejects_wrong_bundle_type(self):
        """SizingRunArtifacts for rateDoublePipe → RepositoryStateError."""
        from hexagent.api.artifacts import SizingRunArtifacts

        repo, token, rec = self._running_record("rateDoublePipe")
        env, _bundle = self._valid_rating_pair()
        wrong_bundle = SizingRunArtifacts.model_construct(
            canonical_request_snapshot={},
            sizing_request=None,
            evaluation_input=None,
            phase3_authoritative_artifacts=None,
            dispositions=(),
            ranked_records=(),
            top_n_records=(),
            optimization_result=None,
            provenance_graph=None,
            artifact_bundle_digest="sha256:x",
        )
        with pytest.raises(RepositoryStateError, match="RatingRunArtifacts"):
            repo.complete(
                owner_token=token,
                expected_version=rec.record_version,
                envelope=env,
                artifact_bundle=wrong_bundle,
            )
        stored = repo.get_by_run_id(rec.run_id)
        assert stored.state == RunState.RUNNING

    def test_complete_rejects_null_bundle(self):
        """None artifact_bundle for rateDoublePipe → RepositoryStateError."""
        repo, token, rec = self._running_record("rateDoublePipe")
        env, _bundle = self._valid_rating_pair()
        with pytest.raises(RepositoryStateError, match="RatingRunArtifacts"):
            repo.complete(
                owner_token=token,
                expected_version=rec.record_version,
                envelope=env,
                artifact_bundle=None,  # type: ignore[arg-type]
            )
        stored = repo.get_by_run_id(rec.run_id)
        assert stored.state == RunState.RUNNING

    # -- parity rejection tests ---------------------------------------------

    def test_complete_rejects_operation_mismatch(self):
        """envelope.operation != record.operation → ValueError."""
        repo, token, rec = self._running_record("rateDoublePipe")
        env, bundle = self._valid_rating_pair()
        # Tamper: use a bundle whose envelope has wrong operation
        # We construct a new envelope with operation="validateCase"
        from hexagent.api.envelopes import RatingRunEnvelope

        RatingRunEnvelope.model_construct(
            api_schema_version="1",
            operation="rateDoublePipe",  # must match for isinstance check
            run_id=rec.run_id,
            idempotency_key_digest="kid",
            request_digest="req1",
            result_kind="rating",
            result=env.result,
            result_hash=env.result.result_hash,
            warnings=(),
            blockers=(),
            failure=None,
            provenance=env.provenance,
            provenance_digest=env.result.provenance_digest,
            artifact_bundle=bundle,
            artifact_bundle_digest=bundle.artifact_bundle_digest,
            report_links=None,
        )
        # The record.operation is "rateDoublePipe" but we'll use a
        # record with a different operation to test the mismatch
        repo2, token2, rec2 = self._running_record("rateDoublePipe")
        # Manually tamper the record's operation by creating a new claim
        # with a different operation but same namespace
        # Actually, we can't easily change record.operation after creation.
        # Instead, test the mismatch by constructing an envelope with
        # a different operation string in the model_construct
        # The key check is: envelope.operation != record.operation
        # Since both are "rateDoublePipe", we need a different approach.
        # Let's create a record with one operation and try to complete
        # with an envelope of a different operation.
        # We can't easily do this without the record having a different
        # operation. Let's just verify the check exists by testing
        # request_digest mismatch instead, which is easier to trigger.
        # Actually, we CAN test this: use model_construct to set
        # operation to something that won't match
        env_bad_op = RatingRunEnvelope.model_construct(
            api_schema_version="1",
            operation="sizeDoublePipe",  # tampered!
            run_id=rec.run_id,
            idempotency_key_digest="kid",
            request_digest="req1",
            result_kind="rating",
            result=env.result,
            result_hash=env.result.result_hash,
            warnings=(),
            blockers=(),
            failure=None,
            provenance=env.provenance,
            provenance_digest=env.result.provenance_digest,
            artifact_bundle=bundle,
            artifact_bundle_digest=bundle.artifact_bundle_digest,
            report_links=None,
        )
        with pytest.raises(ValueError, match="operation"):
            repo.complete(
                owner_token=token,
                expected_version=rec.record_version,
                envelope=env_bad_op,
                artifact_bundle=bundle,
            )
        stored = repo.get_by_run_id(rec.run_id)
        assert stored.state == RunState.RUNNING

    def test_complete_rejects_request_digest_mismatch(self):
        """envelope.request_digest != record.request_digest → ValueError."""
        repo, token, rec = self._running_record("rateDoublePipe")
        env, bundle = self._valid_rating_pair(request_digest="DIFFERENT_DIGEST")
        with pytest.raises(ValueError, match="request_digest"):
            repo.complete(
                owner_token=token,
                expected_version=rec.record_version,
                envelope=env,
                artifact_bundle=bundle,
            )
        stored = repo.get_by_run_id(rec.run_id)
        assert stored.state == RunState.RUNNING

    def test_complete_rejects_bundle_identity_mismatch(self):
        """envelope.artifact_bundle != artifact_bundle arg → ValueError."""
        from hexagent.api.artifacts import RatingRunArtifacts

        repo, token, rec = self._running_record("rateDoublePipe")
        env, bundle = self._valid_rating_pair()
        # Construct a second bundle with different canonical_request_snapshot
        tampered_bundle = RatingRunArtifacts.model_construct(
            canonical_request_snapshot={"tampered": True},  # different!
            request_identity=bundle.request_identity,
            geometry_snapshot=bundle.geometry_snapshot,
            solver_settings=bundle.solver_settings,
            provider_identity=bundle.provider_identity,
            result=bundle.result,
            provenance_graph=bundle.provenance_graph,
            artifact_bundle_digest=bundle.artifact_bundle_digest,
        )
        # Use envelope from pair1 but artifact_bundle from pair2
        with pytest.raises(ValueError, match="artifact_bundle"):
            repo.complete(
                owner_token=token,
                expected_version=rec.record_version,
                envelope=env,
                artifact_bundle=tampered_bundle,
            )
        stored = repo.get_by_run_id(rec.run_id)
        assert stored.state == RunState.RUNNING

    def test_complete_rejects_result_mismatch(self):
        """artifact_bundle.result != envelope.result → ValueError."""
        repo, token, rec = self._running_record("rateDoublePipe")
        env, bundle = self._valid_rating_pair()
        # Create a different result object
        from hexagent.exchangers.double_pipe.result import (
            RatingResult,
            RatingStatus,
            SolverDetailsModel,
        )
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement

        other_result = RatingResult.model_construct(
            status=RatingStatus.SUCCEEDED,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            heat_duty_w=9999.0,  # different!
            hot_outlet_temperature_k=350.0,
            cold_outlet_temperature_k=310.0,
            tube_reynolds=None,
            tube_prandtl=None,
            tube_nusselt=None,
            tube_h=None,
            tube_selected_correlation_id=None,
            tube_selected_correlation_version=None,
            tube_applicability_status=None,
            annulus_reynolds=None,
            annulus_prandtl=None,
            annulus_nusselt=None,
            annulus_h=None,
            annulus_selected_correlation_id=None,
            annulus_selected_correlation_version=None,
            annulus_applicability_status=None,
            area_inner_m2=0.1,
            area_outer_m2=0.15,
            resistance_breakdown=None,
            U_inner_basis=None,
            U_outer_basis=None,
            UA_w_k=None,
            C_hot_w_k=None,
            C_cold_w_k=None,
            C_min_w_k=None,
            C_max_w_k=None,
            capacity_ratio=None,
            NTU=None,
            effectiveness=None,
            LMTD_k=None,
            energy_residual_w=None,
            ua_lmtd_residual_w=None,
            Q_hot_w=None,
            Q_cold_w=None,
            relative_energy_residual=None,
            energy_tolerance_w=None,
            relative_ua_lmtd_residual=None,
            ua_lmtd_tolerance_w=None,
            iterations=1,
            converged=True,
            solver_termination_reason="converged",
            solver_details=SolverDetailsModel.model_construct(
                iterations=1,
                residual_w=0.0,
                function_evaluations=1,
                termination_reason="converged",
            ),
            warnings=(),
            blockers=(),
            failure=None,
            property_calls=(),
            provider_identity=env.result.provider_identity,
            request_identity=env.result.request_identity,
            result_hash="sha256:tampered_hash",
            provenance_graph=env.result.provenance_graph,
            provenance_digest="sha256:tampered_prov",
        )
        # Construct envelope where artifact_bundle has the original result
        # but envelope.result is the tampered result
        from hexagent.api.envelopes import RatingRunEnvelope

        env_mismatched = RatingRunEnvelope.model_construct(
            api_schema_version="1",
            operation="rateDoublePipe",
            run_id=rec.run_id,
            idempotency_key_digest="kid",
            request_digest="req1",
            result_kind="rating",
            result=other_result,  # tampered!
            result_hash=other_result.result_hash,
            warnings=(),
            blockers=(),
            failure=None,
            provenance=env.provenance,
            provenance_digest=env.result.provenance_digest,
            artifact_bundle=bundle,  # bundle still has original result
            artifact_bundle_digest=bundle.artifact_bundle_digest,
            report_links=None,
        )
        with pytest.raises(ValueError, match="result"):
            repo.complete(
                owner_token=token,
                expected_version=rec.record_version,
                envelope=env_mismatched,
                artifact_bundle=bundle,
            )
        stored = repo.get_by_run_id(rec.run_id)
        assert stored.state == RunState.RUNNING

    def test_complete_rejects_result_hash_mismatch(self):
        """result.result_hash != envelope.result_hash → ValueError."""
        repo, token, rec = self._running_record("rateDoublePipe")
        env, bundle = self._valid_rating_pair()
        # Tamper envelope's result_hash to not match result.result_hash
        from hexagent.api.envelopes import RatingRunEnvelope

        env_tampered = RatingRunEnvelope.model_construct(
            api_schema_version="1",
            operation="rateDoublePipe",
            run_id=rec.run_id,
            idempotency_key_digest="kid",
            request_digest="req1",
            result_kind="rating",
            result=env.result,
            result_hash="sha256:TAMPERED_HASH",  # tampered!
            warnings=(),
            blockers=(),
            failure=None,
            provenance=env.provenance,
            provenance_digest=env.result.provenance_digest,
            artifact_bundle=bundle,
            artifact_bundle_digest=bundle.artifact_bundle_digest,
            report_links=None,
        )
        with pytest.raises(ValueError, match="result_hash"):
            repo.complete(
                owner_token=token,
                expected_version=rec.record_version,
                envelope=env_tampered,
                artifact_bundle=bundle,
            )
        stored = repo.get_by_run_id(rec.run_id)
        assert stored.state == RunState.RUNNING

    def test_complete_rejects_provenance_mismatch(self):
        """artifact_bundle.provenance_graph != envelope.provenance → ValueError."""
        repo, token, rec = self._running_record("rateDoublePipe")
        env, bundle = self._valid_rating_pair()
        from hexagent.api.envelopes import RatingRunEnvelope
        from hexagent.domain.provenance import ProvenanceGraph, ProvenanceNode, ProvenanceNodeType

        tampered_prov = ProvenanceGraph.model_construct(
            schema_version="1.0",
            nodes=(
                ProvenanceNode.model_construct(
                    node_id=uuid4(),
                    node_type=ProvenanceNodeType.CASE_REVISION,
                    label="tampered",
                    metadata=(),
                    payload_hash="sha256:" + "00" * 32,
                ),
            ),
            edges=(),
        )
        env_tampered = RatingRunEnvelope.model_construct(
            api_schema_version="1",
            operation="rateDoublePipe",
            run_id=rec.run_id,
            idempotency_key_digest="kid",
            request_digest="req1",
            result_kind="rating",
            result=env.result,
            result_hash=env.result.result_hash,
            warnings=(),
            blockers=(),
            failure=None,
            provenance=tampered_prov,  # tampered!
            provenance_digest=env.result.provenance_digest,
            artifact_bundle=bundle,
            artifact_bundle_digest=bundle.artifact_bundle_digest,
            report_links=None,
        )
        with pytest.raises(ValueError, match="provenance"):
            repo.complete(
                owner_token=token,
                expected_version=rec.record_version,
                envelope=env_tampered,
                artifact_bundle=bundle,
            )
        stored = repo.get_by_run_id(rec.run_id)
        assert stored.state == RunState.RUNNING

    def test_complete_rejects_bundle_digest_mismatch(self):
        """Recomputed digest != envelope.artifact_bundle_digest → ValueError."""
        repo, token, rec = self._running_record("rateDoublePipe")
        env, bundle = self._valid_rating_pair()
        from hexagent.api.envelopes import RatingRunEnvelope

        env_tampered = RatingRunEnvelope.model_construct(
            api_schema_version="1",
            operation="rateDoublePipe",
            run_id=rec.run_id,
            idempotency_key_digest="kid",
            request_digest="req1",
            result_kind="rating",
            result=env.result,
            result_hash=env.result.result_hash,
            warnings=(),
            blockers=(),
            failure=None,
            provenance=env.provenance,
            provenance_digest=env.result.provenance_digest,
            artifact_bundle=bundle,
            artifact_bundle_digest="sha256:TAMPERED_DIGEST",  # tampered!
            report_links=None,
        )
        with pytest.raises(ValueError, match="artifact_bundle_digest"):
            repo.complete(
                owner_token=token,
                expected_version=rec.record_version,
                envelope=env_tampered,
                artifact_bundle=bundle,
            )
        stored = repo.get_by_run_id(rec.run_id)
        assert stored.state == RunState.RUNNING

    def test_complete_rejects_canonical_request_tamper(self):
        """Tampered canonical_request_snapshot → digest mismatch → ValueError."""
        repo, token, rec = self._running_record("rateDoublePipe")
        env, bundle = self._valid_rating_pair()
        from hexagent.api.artifacts import RatingRunArtifacts
        from hexagent.api.envelopes import RatingRunEnvelope

        # Tamper the canonical_request_snapshot in the bundle
        tampered_bundle = RatingRunArtifacts.model_construct(
            canonical_request_snapshot={"tampered": True},  # tampered!
            request_identity=bundle.request_identity,
            geometry_snapshot=bundle.geometry_snapshot,
            solver_settings=bundle.solver_settings,
            provider_identity=bundle.provider_identity,
            result=bundle.result,
            provenance_graph=bundle.provenance_graph,
            artifact_bundle_digest=bundle.artifact_bundle_digest,
        )
        env_tampered = RatingRunEnvelope.model_construct(
            api_schema_version="1",
            operation="rateDoublePipe",
            run_id=rec.run_id,
            idempotency_key_digest="kid",
            request_digest="req1",
            result_kind="rating",
            result=env.result,
            result_hash=env.result.result_hash,
            warnings=(),
            blockers=(),
            failure=None,
            provenance=env.provenance,
            provenance_digest=env.result.provenance_digest,
            artifact_bundle=tampered_bundle,
            artifact_bundle_digest=tampered_bundle.artifact_bundle_digest,  # old digest!
            report_links=None,
        )
        with pytest.raises(ValueError, match="artifact_bundle_digest"):
            repo.complete(
                owner_token=token,
                expected_version=rec.record_version,
                envelope=env_tampered,
                artifact_bundle=tampered_bundle,
            )
        stored = repo.get_by_run_id(rec.run_id)
        assert stored.state == RunState.RUNNING

    def test_complete_failure_does_not_transition_state(self):
        """After ANY parity failure, record stays RUNNING, no envelope stored."""
        repo, token, rec = self._running_record("rateDoublePipe")
        env, bundle = self._valid_rating_pair(request_digest="WRONG_DIGEST")
        original_version = rec.record_version
        original_started_at = rec.started_at

        with pytest.raises(ValueError):
            repo.complete(
                owner_token=token,
                expected_version=rec.record_version,
                envelope=env,
                artifact_bundle=bundle,
            )

        stored = repo.get_by_run_id(rec.run_id)
        assert stored.state == RunState.RUNNING
        assert stored.completed_at is None
        assert stored.envelope is None
        assert stored.artifact_bundle is None
        assert stored.record_version == original_version
        assert stored.started_at == original_started_at
