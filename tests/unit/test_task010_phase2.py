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
    snapshot = ProviderIdentitySnapshot(
        name=provider.name,
        version=provider.version,
        git_revision=provider.git_revision,
        reference_state_policy=str(provider.reference_state_policy.value),
        configuration_fingerprint=provider._construction_fingerprint,
        cache_policy_version=provider.cache_policy_version,
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
    snapshot = ProviderIdentitySnapshot(
        name=provider.name,
        version=provider.version,
        git_revision=provider.git_revision,
        reference_state_policy=str(provider.reference_state_policy.value),
        configuration_fingerprint=provider._construction_fingerprint,
        cache_policy_version=provider.cache_policy_version,
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
            operation="sizing",
        )
        assert result.outcome == ClaimOutcome.NEW_CLAIM
        assert result.record.state == RunState.CLAIMED

    def test_complete_replay(self):
        repo = InMemoryRunRepository()
        claim = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="sizing",
        )
        rec = repo.start(
            owner_token=claim.record.owner_token,
            expected_version=claim.record.record_version,
        )
        repo.complete(
            owner_token=claim.record.owner_token,
            expected_version=rec.record_version,
            envelope={"result_kind": "sizing", "request_digest": "req1"},
            artifact_bundle={"test": True},
        )
        result = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="sizing",
        )
        assert result.outcome == ClaimOutcome.COMPLETE_REPLAY

    def test_complete_different_digest_conflict(self):
        repo = InMemoryRunRepository()
        claim = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="sizing",
        )
        rec = repo.start(
            owner_token=claim.record.owner_token,
            expected_version=claim.record.record_version,
        )
        repo.complete(
            owner_token=claim.record.owner_token,
            expected_version=rec.record_version,
            envelope={"result_kind": "sizing", "request_digest": "req1"},
            artifact_bundle={"test": True},
        )
        with pytest.raises(IdempotencyConflictError):
            repo.claim(
                namespace_digest="ns1",
                request_digest="req2",
                operation="sizing",
            )

    def test_in_progress(self):
        repo = InMemoryRunRepository()
        repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="sizing",
        )
        result = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="sizing",
        )
        assert result.outcome == ClaimOutcome.IN_PROGRESS

    def test_stale_rejected(self):
        clock_time = datetime(2025, 1, 1, tzinfo=UTC)
        clock = lambda: clock_time  # noqa: E731
        repo = InMemoryRunRepository(clock=clock)
        repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="sizing",
        )
        clock_time = datetime(2025, 1, 2, tzinfo=UTC)
        result = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="sizing",
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
            operation="sizing",
        )
        old_token = claim.record.owner_token
        old_version = claim.record.record_version
        clock_time = datetime(2025, 1, 2, tzinfo=UTC)
        result = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="sizing",
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
            operation="sizing",
        )
        old_token = claim.record.owner_token
        old_version = claim.record.record_version
        clock_time = datetime(2025, 1, 2, tzinfo=UTC)
        repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="sizing",
            takeover=True,
        )
        with pytest.raises(CASCasError):
            repo.heartbeat(owner_token=old_token, expected_version=old_version)

    def test_cas_version_mismatch(self):
        repo = InMemoryRunRepository()
        claim = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="sizing",
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
            operation="sizing",
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
            operation="sizing",
        )
        with pytest.raises(RepositoryStateError):
            repo.complete(
                owner_token=claim.record.owner_token,
                expected_version=claim.record.record_version,
                envelope={"result_kind": "sizing"},
                artifact_bundle={"test": True},
            )

    def test_failed_replay(self):
        repo = InMemoryRunRepository()
        claim = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="sizing",
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
            operation="sizing",
        )
        assert result.outcome == ClaimOutcome.FAILED_REPLAY

    def test_failed_different_digest_conflict(self):
        repo = InMemoryRunRepository()
        claim = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="sizing",
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
                operation="sizing",
            )

    def test_get_by_run_id(self):
        repo = InMemoryRunRepository()
        claim = repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="sizing",
        )
        found = repo.get_by_run_id(claim.record.run_id)
        assert found is not None
        assert found.run_id == claim.record.run_id

    def test_get_by_namespace(self):
        repo = InMemoryRunRepository()
        repo.claim(
            namespace_digest="ns1",
            request_digest="req1",
            operation="sizing",
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
                        operation="sizing",
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
        # provenance_digest must match provenance graph hash
        assert envelope.provenance_digest == envelope.provenance.compute_hash()
        # artifact_bundle_digest must match bundle hash
        assert envelope.artifact_bundle_digest == envelope.artifact_bundle.bundle_hash

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
        assert "resolved_provider" in bundle
        assert "geometry_artifact" in bundle
        assert "solver_artifact" in bundle
        assert "rating_result" in bundle
        assert "result_hash" in bundle
        assert "provenance_graph" in bundle
        assert "provenance_digest" in bundle


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
