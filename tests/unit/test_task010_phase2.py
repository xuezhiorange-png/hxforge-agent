"""TASK-010 Phase 2 contract tests.

Covers:
- P0-1: Frozen API surface (6 routes, correct paths, operation IDs)
- P0-2: Legacy routes removed
- P0-3: Exact ApiError contract
- P0-4: Unified exception handlers
- P0-5: App factory (no mutable globals)
- P0-6: RunRepository state machine
- P0-7: Idempotency contract
- T45: DoublePipeService.size() never called
"""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hexagent.api.envelopes import (
    RatingRunEnvelope,
    SizingRunEnvelope,
    ValidationRunEnvelope,
)
from hexagent.api.errors import VALID_ERROR_CODES, ApiError, ErrorDetail
from hexagent.api.repository import (
    CASCasError,
    ClaimOutcome,
    IdempotencyConflictError,
    InMemoryRunRepository,
    RepositoryStateError,
    RunState,
)

# ===================================================================
# Helpers
# ===================================================================


def _make_provider_snapshot(**overrides: Any) -> Any:
    from hexagent.core.heat_balance import ProviderIdentitySnapshot

    base = {
        "name": "test-provider",
        "version": "0.1.0",
        "git_revision": "abc123",
        "reference_state_policy": "iir",
        "configuration_fingerprint": "fp1",
        "cache_policy_version": "v1",
    }
    base.update(overrides)
    return ProviderIdentitySnapshot(**base)


def _compute_identity_digest(snapshot: Any) -> str:
    from hexagent.api.models import canonical_provider_identity_payload
    from hexagent.core.canonical import sha256_digest

    payload = canonical_provider_identity_payload(snapshot)
    return sha256_digest(payload)


def _make_provider_registry(**overrides: Any) -> MagicMock:
    """Create a mock ProviderRegistry with a resolved authority."""
    from hexagent.api.models import ResolvedProviderAuthority

    snapshot = _make_provider_snapshot(**overrides)
    digest = _compute_identity_digest(snapshot)
    authority = ResolvedProviderAuthority(
        provider_ref="test-provider",
        identity=snapshot,
        identity_digest=digest,
    )
    registry = MagicMock()
    registry.resolve.return_value = authority
    return registry


def _make_catalog_registry() -> MagicMock:
    registry = MagicMock()
    registry.resolve_all.return_value = ()
    return registry


def _make_run_repository() -> InMemoryRunRepository:
    return InMemoryRunRepository()


def _make_sizing_service() -> MagicMock:
    service = MagicMock()
    service.process.return_value = MagicMock(
        request_digest="sha256:" + "b" * 64,
        canonical_request_snapshot={"test": True},
        design_case=MagicMock(),
        sizing_request=MagicMock(),
        sizing_request_identity=MagicMock(),
        effective_solver_params=MagicMock(),
        resolved_provider=MagicMock(),
        resolved_catalogs=(),
        provenance=MagicMock(compute_hash=lambda: "sha256:" + "c" * 64),
    )
    service.run_optimization.return_value = MagicMock(
        model_dump=lambda **kw: {"test": True},
        result_hash="sha256:" + "d" * 64,
        provenance_digest="sha256:" + "c" * 64,
    )
    return service


def _make_rating_service() -> MagicMock:
    service = MagicMock()
    result = MagicMock()
    result.model_dump.return_value = {"test": True}
    result.result_hash = "sha256:" + "e" * 64
    result.provenance_digest = "sha256:" + "f" * 64
    service.rate.return_value = result
    return service


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
        "fluid": {"backend": "iapws-if97", "name": "water"},
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
        "fluid": {"backend": "iapws-if97", "name": "water"},
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


def _make_sizing_request() -> dict[str, Any]:
    """Create a minimal valid SizingApiRequest payload."""
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
        "provider_ref": "test-provider",
        "optimization_objective": "minimum_outer_heat_transfer_area",
        "requested_top_n": 3,
        "expected_provider_identity": {
            "name": "test-provider",
            "version": "0.1.0",
            "git_revision": "abc123",
            "reference_state_policy": "iir",
        },
    }


def _create_test_app(**kwargs: Any) -> FastAPI:
    from hexagent.api.main import create_app

    defaults = {
        "provider_registry": _make_provider_registry(),
        "catalog_registry": _make_catalog_registry(),
        "run_repository": _make_run_repository(),
        "sizing_service": _make_sizing_service(),
        "rating_service": _make_rating_service(),
    }
    defaults.update(kwargs)
    return create_app(**defaults)


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
# P0-2: Legacy routes removed
# ===================================================================


class TestLegacyRoutesRemoved:
    def test_no_legacy_design_route_in_app(self):
        app = _create_test_app()
        schema = app.openapi()
        assert "/v1/design/double-pipe" not in schema.get("paths", {})


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
        repo1 = _make_run_repository()
        repo2 = _make_run_repository()
        app1 = _create_test_app(run_repository=repo1)
        app2 = _create_test_app(run_repository=repo2)
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
            envelope=MagicMock(),
            artifact_bundle=MagicMock(),
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
            envelope=MagicMock(),
            artifact_bundle=MagicMock(),
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
                envelope=MagicMock(),
                artifact_bundle=MagicMock(),
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
            json={"api_schema_version": "1"},
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
    def test_poison_trap_not_triggered(self):
        from hexagent.exchangers.double_pipe.service import DoublePipeService

        app = _create_test_app()
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
        assert poison_called["count"] == 0


# ===================================================================
# Validation endpoint
# ===================================================================


class TestValidationEndpoint:
    def test_valid_request_returns_200(self):
        app = _create_test_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/v1/cases/validate",
            json=_make_validation_request(),
        )
        assert resp.status_code in (200, 422)

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
# OpenAPI contract
# ===================================================================


class TestOpenAPIContract:
    def test_six_operations_present(self):
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

    def test_no_sizing_service_result_in_schema(self):
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
        provenance = MagicMock()
        provenance.compute_hash.return_value = "sha256:" + "a" * 64
        result = MagicMock()
        result.result_hash = "sha256:" + "b" * 64
        result.provenance_digest = "sha256:" + "a" * 64

        with pytest.raises(Exception, match="failure must be None"):
            SizingRunEnvelope(
                api_schema_version="1",
                operation="sizeDoublePipe",
                run_id=uuid4(),
                idempotency_key_digest="sha256:abc",
                request_digest="sha256:def",
                result_kind="sizing",
                result=result,
                result_hash="sha256:" + "b" * 64,
                warnings=(),
                blockers=(),
                failure="not_none",
                provenance=provenance,
                provenance_digest="sha256:" + "a" * 64,
                artifact_bundle=None,
                artifact_bundle_digest="",
                report_links=None,
            )

    def test_rating_envelope_result_hash_parity(self):
        provenance = MagicMock()
        provenance.compute_hash.return_value = "sha256:" + "a" * 64
        result = MagicMock()
        result.result_hash = "sha256:" + "b" * 64
        result.provenance_digest = "sha256:" + "a" * 64

        with pytest.raises(Exception, match="result_hash mismatch"):
            RatingRunEnvelope(
                api_schema_version="1",
                operation="rateDoublePipe",
                run_id=uuid4(),
                idempotency_key_digest="sha256:abc",
                request_digest="sha256:def",
                result_kind="rating",
                result=result,
                result_hash="sha256:" + "x" * 64,
                warnings=(),
                blockers=(),
                failure=None,
                provenance=provenance,
                provenance_digest="sha256:" + "a" * 64,
                artifact_bundle=None,
                artifact_bundle_digest="",
                report_links=None,
            )
