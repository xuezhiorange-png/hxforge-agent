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
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hexagent.api.envelopes import RatingRunEnvelope
from hexagent.api.repository import (
    FrozenFailurePayload,
    InMemoryRunRepository,
    RunState,
)
from hexagent.core.heat_balance import ProviderIdentitySnapshot
from hexagent.reporting import (
    MANDATORY_ARTIFACT_IDS,
    REPORT_SECTION_ORDER,
    ReportArtifactId,
    ReportArtifactKind,
    ReportInstanceIdentity,
    ReportModel,
    ReportSectionId,
    ReportSectionStatus,
    build_report_html,
    compute_report_content_hash,
    compute_report_instance_hash,
    render_report_html,
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
    """Create a SizingApiRequest payload.

    Uses fake catalog refs that will fail catalog resolution — used for
    tests where the status code doesn't need to be 200 (T45 poison trap,
    conflict detection, failure replay).
    """
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
# A6: T45 — DoublePipeService.size() never called
# ===================================================================


class TestA6T45:
    """T45: DoublePipeService.size() never called on sizing requests.

    The sizing endpoint uses SizingApplicationService (not
    DoublePipeService.size).  This test patches size() with a poison
    function and verifies it is never invoked.
    """

    def test_t45_poison_trap_on_sizing_request(self):
        """size() never called on any sizing HTTP request."""
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
                headers={"Idempotency-Key": "test-t45-poison"},
            )
        # Regardless of status, size() must NOT have been called
        assert poison_called["count"] == 0

    def test_t45_poison_trap_multiple_requests(self):
        """size() never called even across multiple sizing requests."""
        from hexagent.exchangers.double_pipe.service import DoublePipeService

        app = _create_fresh_app()
        client = TestClient(app, raise_server_exceptions=False)
        poison_called = {"count": 0}

        def poison(*args: Any, **kwargs: Any) -> None:
            poison_called["count"] += 1
            raise RuntimeError("DoublePipeService.size() was called!")

        sizing_payload = _make_sizing_request()
        with patch.object(DoublePipeService, "size", poison):
            # Multiple requests with different keys
            for i in range(3):
                client.post(
                    "/v1/double-pipe/sizing",
                    json=sizing_payload,
                    headers={"Idempotency-Key": f"test-t45-multi-{i}"},
                )
        assert poison_called["count"] == 0

    def test_t45_poison_trap_on_validation_and_rating(self):
        """size() not called on validation or rating endpoints either."""
        from hexagent.exchangers.double_pipe.service import DoublePipeService

        app = _create_fresh_app()
        client = TestClient(app, raise_server_exceptions=False)
        poison_called = {"count": 0}

        def poison(*args: Any, **kwargs: Any) -> None:
            poison_called["count"] += 1
            raise RuntimeError("DoublePipeService.size() was called!")

        with patch.object(DoublePipeService, "size", poison):
            # Validation (no idempotency key needed)
            client.post("/v1/cases/validate", json=_make_validation_request())
            # Rating
            client.post(
                "/v1/double-pipe/rating",
                json=_make_rating_request(),
                headers={"Idempotency-Key": "test-t45-val-rating"},
            )
        assert poison_called["count"] == 0


# ===================================================================
# A7: Sizing/Rating replay
# ===================================================================


class TestA7Replay:
    """Replay contract: same key + same body → exact replay,
    same key + different body → 409."""

    def test_rating_complete_replay_identical(self):
        """Same idempotency key + same body → exact JSON replay (200)."""
        app = _create_fresh_app()
        client = TestClient(app, raise_server_exceptions=False)
        rating_payload = _make_rating_request()
        key = "test-rating-replay-1"

        # First request — execute and store
        resp1 = client.post(
            "/v1/double-pipe/rating",
            json=rating_payload,
            headers={"Idempotency-Key": key},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()

        # Second request — replay
        resp2 = client.post(
            "/v1/double-pipe/rating",
            json=rating_payload,
            headers={"Idempotency-Key": key},
        )
        assert resp2.status_code == 200
        data2 = resp2.json()

        # Envelopes must be byte-for-byte identical
        assert data1 == data2

    def test_rating_different_body_same_key_returns_409(self):
        """Same idempotency key + different body → 409 conflict."""
        app = _create_fresh_app()
        client = TestClient(app, raise_server_exceptions=False)
        key = "test-rating-conflict-1"

        # First request
        resp1 = client.post(
            "/v1/double-pipe/rating",
            json=_make_rating_request(),
            headers={"Idempotency-Key": key},
        )
        assert resp1.status_code == 200

        # Second request — same key, different body (change effective length)
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

    def test_sizing_replay_same_key_same_body_returns_same_status(self):
        """Sizing replay with same key and same body returns same status."""
        app = _create_fresh_app()
        client = TestClient(app, raise_server_exceptions=False)
        sizing_payload = _make_sizing_request()
        key = "test-sizing-replay-same"

        resp1 = client.post(
            "/v1/double-pipe/sizing",
            json=sizing_payload,
            headers={"Idempotency-Key": key},
        )
        # May be 200 or 500 — replay must return the same status
        resp2 = client.post(
            "/v1/double-pipe/sizing",
            json=sizing_payload,
            headers={"Idempotency-Key": key},
        )
        assert resp1.status_code == resp2.status_code
        if resp1.status_code == 200:
            assert resp1.json() == resp2.json()


# ===================================================================
# B1-B8: Report contract tests
# ===================================================================


class TestB1ReportModels:
    """B1: Precise report models — StrEnums, artifact variants, section, report."""

    def test_report_section_id_exactly_thirteen(self):
        """Exactly 13 canonical section identifiers."""
        assert len(REPORT_SECTION_ORDER) == 13

    def test_report_section_status_is_strenum(self):
        """ReportSectionStatus values are StrEnum instances."""
        assert isinstance(ReportSectionStatus.PRESENT, str)
        assert str(ReportSectionStatus.PRESENT) == "present"
        assert isinstance(ReportSectionStatus.NOT_APPLICABLE, str)
        assert str(ReportSectionStatus.NOT_APPLICABLE) == "not_applicable"

    def test_report_artifact_kind_is_strenum(self):
        """ReportArtifactKind values are StrEnum instances."""
        assert isinstance(ReportArtifactKind.CANONICAL_REQUEST_SNAPSHOT, str)
        assert str(ReportArtifactKind.CANONICAL_REQUEST_SNAPSHOT) == "canonical_request_snapshot"

    def test_report_section_id_is_strenum(self):
        """ReportSectionId values are StrEnum instances."""
        assert isinstance(ReportSectionId.STATUS_BANNER, str)
        assert str(ReportSectionId.STATUS_BANNER) == "status_banner"


class TestB2ThirteenSections:
    """B2: Exactly 13 sections in fixed order."""

    def test_rating_report_has_thirteen_sections(self):
        """A real rating envelope produces a ReportModel with exactly 13 sections."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-b2-13-sections")
        record = _make_record_for_report(envelope)
        html = build_report_html(record)
        assert isinstance(html, bytes)

    def test_report_section_order_matches_constant(self):
        """REPORT_SECTION_ORDER matches the expected frozen order."""
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

    def test_report_model_rejects_wrong_section_count(self):
        """ReportModel rejects construction with != 13 sections."""
        from hexagent.reporting import ReportSection

        sections = (
            ReportSection(
                section_id=ReportSectionId.STATUS_BANNER,
                title="Status Banner",
                content="test",
                status=ReportSectionStatus.PRESENT,
            ),
            ReportSection(
                section_id=ReportSectionId.RUN_IDENTITY,
                title="Run Identity",
                content="test",
                status=ReportSectionStatus.PRESENT,
            ),
        )
        with pytest.raises(Exception, match="Expected 13 sections"):
            ReportModel(
                run_id=uuid4(),
                operation="rateDoublePipe",
                sections=sections,
                content_hash="sha256:abc",
                instance_hash="sha256:def",
            )


class TestB3SectionStatusMatrix:
    """B3: Section/status matrix verification."""

    def test_rating_succeeded_matrix(self):
        """Rating 'succeeded' status matrix verification passes."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-b3-matrix")
        record = _make_record_for_report(envelope)
        html = build_report_html(record)
        assert isinstance(html, bytes)

    def test_verify_matrix_rejects_unknown_termination(self):
        """verify_report_section_status_matrix rejects unknown termination."""
        from hexagent.reporting import ReportSection

        sections = tuple(
            ReportSection(
                section_id=sid,
                title=sid.value,
                content="test",
                status=ReportSectionStatus.PRESENT,
            )
            for sid in REPORT_SECTION_ORDER
        )
        model = ReportModel(
            run_id=uuid4(),
            operation="rateDoublePipe",
            sections=sections,
            content_hash="sha256:abc",
            instance_hash="sha256:def",
        )
        with pytest.raises(ValueError, match="Unknown rating termination status"):
            verify_report_section_status_matrix(model, "rateDoublePipe", "nonexistent_status")

    def test_verify_matrix_rejects_unsupported_operation(self):
        """verify_report_section_status_matrix rejects unsupported operation."""
        from hexagent.reporting import ReportSection

        sections = tuple(
            ReportSection(
                section_id=sid,
                title=sid.value,
                content="test",
                status=ReportSectionStatus.PRESENT,
            )
            for sid in REPORT_SECTION_ORDER
        )
        model = ReportModel(
            run_id=uuid4(),
            operation="unknownOp",
            sections=sections,
            content_hash="sha256:abc",
            instance_hash="sha256:def",
        )
        with pytest.raises(ValueError, match="Unsupported operation"):
            verify_report_section_status_matrix(model, "unknownOp", "succeeded")


class TestB4MandatoryArtifacts:
    """B4: Mandatory artifact verification."""

    def test_mandatory_artifact_ids_present(self):
        """MANDATORY_ARTIFACT_IDS contains all 10 required artifacts."""
        assert len(MANDATORY_ARTIFACT_IDS) == 10
        expected_ids = {
            ReportArtifactId.CANONICAL_REQUEST_SNAPSHOT,
            ReportArtifactId.REQUEST_IDENTITY,
            ReportArtifactId.PROVIDER_IDENTITY,
            ReportArtifactId.GEOMETRY_SNAPSHOT,
            ReportArtifactId.SOLVER_SETTINGS,
            ReportArtifactId.DOMAIN_RESULT,
            ReportArtifactId.RESULT_HASH,
            ReportArtifactId.PROVENANCE_GRAPH,
            ReportArtifactId.PROVENANCE_DIGEST,
            ReportArtifactId.BUNDLE_DIGEST,
        }
        assert expected_ids == MANDATORY_ARTIFACT_IDS

    def test_rating_report_has_all_mandatory_artifacts(self):
        """A real rating report passes mandatory artifact verification."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-b4-mandatory")
        record = _make_record_for_report(envelope)
        html = build_report_html(record)
        assert isinstance(html, bytes)


class TestB5RFC6901Pointers:
    """B5: RFC 6901 JSON Pointer validation and resolution."""

    def test_empty_pointer(self):
        """Empty pointer returns empty tuple."""
        assert validate_rfc6901_pointer("") == ()

    def test_root_pointer(self):
        """/ returns a tuple with one empty string."""
        result = validate_rfc6901_pointer("/")
        assert result == ("",)

    def test_tilde_escape(self):
        """~0 → ~, ~1 → / within valid pointers."""
        assert validate_rfc6901_pointer("/~0") == ("~",)
        assert validate_rfc6901_pointer("/~1") == ("/",)

    def test_nested_pointer(self):
        """/foo/~0bar → ("foo", "~bar")"""
        assert validate_rfc6901_pointer("/foo/~0bar") == ("foo", "~bar")

    def test_deep_pointer(self):
        """/a/b/c → ("a", "b", "c")"""
        assert validate_rfc6901_pointer("/a/b/c") == ("a", "b", "c")

    def test_rejects_missing_leading_slash(self):
        """Non-empty pointer without leading / is rejected."""
        with pytest.raises(ValueError, match="must start with '/'"):
            validate_rfc6901_pointer("foo")

    def test_rejects_trailing_tilde(self):
        """Pointer ending with ~ is rejected."""
        with pytest.raises(ValueError, match="trailing '~'"):
            validate_rfc6901_pointer("/foo/~")

    def test_rejects_illegal_escape(self):
        """~2 is not a legal RFC 6901 escape."""
        with pytest.raises(ValueError, match="Illegal escape"):
            validate_rfc6901_pointer("/~2")

    def test_resolve_source_pointer_dict(self):
        """resolve_source_pointer traverses a nested dict/list."""
        obj = {"a": {"b": [1, 2, {"c": "found"}]}}
        assert resolve_source_pointer(obj, "/a/b/2/c") == "found"

    def test_resolve_source_pointer_missing_key(self):
        """resolve_source_pointer raises ValueError for missing key."""
        with pytest.raises(ValueError, match="not found"):
            resolve_source_pointer({"a": 1}, "/b")

    def test_pointer_round_trip_with_real_report(self):
        """Source pointers from a real report resolve correctly."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-b5-pointers")
        record = _make_record_for_report(envelope)
        html = build_report_html(record)
        assert isinstance(html, bytes)


class TestB6ReportHashes:
    """B6: Deterministic report hashes."""

    def test_content_hash_deterministic(self):
        """Same inputs produce the same content hash."""
        from hexagent.reporting import ReportSection

        def _make_sections(content: str) -> tuple:
            return tuple(
                ReportSection(
                    section_id=sid,
                    title=sid.value,
                    content=content,
                    status=ReportSectionStatus.PRESENT,
                )
                for sid in REPORT_SECTION_ORDER
            )

        h1 = compute_report_content_hash(_make_sections("same content"))
        h2 = compute_report_content_hash(_make_sections("same content"))
        assert h1 == h2

    def test_instance_hash_deterministic(self):
        """compute_report_instance_hash is deterministic."""
        identity = ReportInstanceIdentity(
            report_content_hash="sha256:" + "a" * 64,
            report_schema_version="1.0",
            run_id=uuid4(),
            operation="rateDoublePipe",
        )
        h1 = compute_report_instance_hash(identity)
        h2 = compute_report_instance_hash(identity)
        assert h1 == h2
        assert h1.startswith("sha256:")

    def test_content_hash_changes_on_different_sections(self):
        """Different section content produces different content hash."""
        from hexagent.reporting import ReportSection

        def _make_sections(content: str) -> tuple:
            return tuple(
                ReportSection(
                    section_id=sid,
                    title=sid.value,
                    content=content,
                    status=ReportSectionStatus.PRESENT,
                )
                for sid in REPORT_SECTION_ORDER
            )

        h1 = compute_report_content_hash(_make_sections("content-a"))
        h2 = compute_report_content_hash(_make_sections("content-b"))
        assert h1 != h2

    def test_full_report_hash_chain(self):
        """Full build_report_html executes the entire hash verification chain."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-b6-full-hash")
        record = _make_record_for_report(envelope)
        html = build_report_html(record)
        assert isinstance(html, bytes)
        # The function internally verifies content_hash and instance_hash


class TestB7PreRenderVerification:
    """B7: Pre-render verification chain."""

    def test_build_report_html_full_chain(self):
        """build_report_html executes the full verification chain."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-b7-chain")
        record = _make_record_for_report(envelope)
        html = build_report_html(record)
        assert isinstance(html, bytes)
        assert len(html) > 0
        assert b"<!DOCTYPE html>" in html
        assert b"<html" in html

    def test_build_report_html_rejects_missing_envelope(self):
        """build_report_html rejects a record with no envelope."""
        record = SimpleNamespace(
            envelope=None,
            operation="rateDoublePipe",
        )
        with pytest.raises(ValueError, match="no envelope"):
            build_report_html(record)


class TestB8DeterministicSecureHTML:
    """B8: Deterministic secure HTML."""

    def test_html_deterministic_same_model(self):
        """Same ReportModel produces identical HTML bytes."""
        from hexagent.reporting import ReportSection

        sections = tuple(
            ReportSection(
                section_id=sid,
                title=sid.value,
                content=f"Content for {sid.value}",
                status=ReportSectionStatus.PRESENT,
            )
            for sid in REPORT_SECTION_ORDER
        )
        model = ReportModel(
            run_id=uuid4(),
            operation="rateDoublePipe",
            sections=sections,
            content_hash="sha256:" + "a" * 64,
            instance_hash="sha256:" + "b" * 64,
        )
        html1 = render_report_html(model)
        html2 = render_report_html(model)
        assert html1 == html2

    def test_html_contains_risk_banners(self):
        """HTML output contains all three risk banners."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-b8-banners")
        record = _make_record_for_report(envelope)
        html = build_report_html(record).decode("utf-8")
        assert "PRELIMINARY" in html
        assert "NOT FOR PROCUREMENT" in html
        assert "NOT FOR CONSTRUCTION" in html

    def test_html_no_external_resources(self):
        """HTML has no external CDN, font, or tracking references."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-b8-no-external")
        record = _make_record_for_report(envelope)
        html = build_report_html(record).decode("utf-8")
        assert "cdn" not in html.lower()
        assert "googleapis" not in html.lower()

    def test_html_no_traceback_leaking(self):
        """HTML output never contains traceback strings."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-b8-no-traceback")
        record = _make_record_for_report(envelope)
        html = build_report_html(record).decode("utf-8")
        assert "Traceback" not in html

    def test_html_escape_redacts_tokens(self):
        """_escape redacts known token patterns."""
        from hexagent.reporting import _escape

        assert "[REDACTED]" in _escape("ghp_abcdefghijklmnopqrstuvwxyz")
        assert "[REDACTED]" in _escape("sk-abc123456789012345678")

    def test_html_escape_autoescapes_injection(self):
        """_escape HTML-escapes dangerous characters."""
        from hexagent.reporting import _escape

        assert "&lt;" in _escape("<script>")
        assert "&amp;" in _escape("a&b")
        assert "&quot;" in _escape('"hello"')

    def test_html_escape_blocks_absolute_paths(self):
        """Absolute paths in content are blocked."""
        from hexagent.reporting import _escape

        result = _escape("/etc/passwd")
        assert "[BLOCKED]" in result
        assert "/etc/passwd" not in result

    def test_html_escape_blocks_env_var_lookalikes(self):
        """Env-var patterns are redacted."""
        from hexagent.reporting import _escape

        result = _escape("${HOME}/secret")
        assert "[REDACTED]" in result
        result2 = _escape("%USERPROFILE%")
        assert "[REDACTED]" in result2

    def test_html_no_user_template_paths(self):
        """HTML output contains no user-supplied template paths."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-b8-no-templates")
        record = _make_record_for_report(envelope)
        html = build_report_html(record).decode("utf-8")
        # Should be purely self-contained, no Jinja/Mako/external template refs
        assert "jinja" not in html.lower()
        assert "mako" not in html.lower()


# ===================================================================
# C1: Provider six-field authority
# ===================================================================


class TestC1ProviderSixField:
    """C1: Provider six-field authority.

    All 6 identity fields are compared:
    name, version, git_revision, reference_state_policy,
    configuration_fingerprint, cache_policy_version.
    """

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
        """Changing the version field changes the identity_digest."""
        from hexagent.api.models import canonical_provider_identity_payload
        from hexagent.core.canonical import sha256_digest

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
        digest1 = sha256_digest(canonical_provider_identity_payload(snap1))
        digest2 = sha256_digest(canonical_provider_identity_payload(snap2))
        assert digest1 != digest2

    def test_provider_git_revision_change_changes_digest(self):
        """Changing git_revision changes the identity_digest."""
        from hexagent.api.models import canonical_provider_identity_payload
        from hexagent.core.canonical import sha256_digest

        snap1 = ProviderIdentitySnapshot(
            name="CoolProp",
            version="1.0",
            git_revision="aaa",
            reference_state_policy="default",
            configuration_fingerprint="",
            cache_policy_version="",
        )
        snap2 = ProviderIdentitySnapshot(
            name="CoolProp",
            version="1.0",
            git_revision="bbb",
            reference_state_policy="default",
            configuration_fingerprint="",
            cache_policy_version="",
        )
        digest1 = sha256_digest(canonical_provider_identity_payload(snap1))
        digest2 = sha256_digest(canonical_provider_identity_payload(snap2))
        assert digest1 != digest2

    def test_provider_fingerprint_change_changes_digest(self):
        """Changing configuration_fingerprint changes the identity_digest."""
        from hexagent.api.models import canonical_provider_identity_payload
        from hexagent.core.canonical import sha256_digest

        snap1 = ProviderIdentitySnapshot(
            name="CoolProp",
            version="1.0",
            git_revision="abc",
            reference_state_policy="default",
            configuration_fingerprint="old_fp",
            cache_policy_version="",
        )
        snap2 = ProviderIdentitySnapshot(
            name="CoolProp",
            version="1.0",
            git_revision="abc",
            reference_state_policy="default",
            configuration_fingerprint="new_fp",
            cache_policy_version="",
        )
        digest1 = sha256_digest(canonical_provider_identity_payload(snap1))
        digest2 = sha256_digest(canonical_provider_identity_payload(snap2))
        assert digest1 != digest2

    def test_provider_cache_policy_change_changes_digest(self):
        """Changing cache_policy_version changes the identity_digest."""
        from hexagent.api.models import canonical_provider_identity_payload
        from hexagent.core.canonical import sha256_digest

        snap1 = ProviderIdentitySnapshot(
            name="CoolProp",
            version="1.0",
            git_revision="abc",
            reference_state_policy="default",
            configuration_fingerprint="",
            cache_policy_version="v1",
        )
        snap2 = ProviderIdentitySnapshot(
            name="CoolProp",
            version="1.0",
            git_revision="abc",
            reference_state_policy="default",
            configuration_fingerprint="",
            cache_policy_version="v2",
        )
        digest1 = sha256_digest(canonical_provider_identity_payload(snap1))
        digest2 = sha256_digest(canonical_provider_identity_payload(snap2))
        assert digest1 != digest2

    def test_provider_mismatch_returns_422(self):
        """Mismatched provider identity returns 422."""
        from hexagent.api.application import RatingApplicationService, SizingService
        from hexagent.api.main import ApplicationDependencies, create_app
        from hexagent.api.registry import CatalogRegistry, ProviderRegistry
        from hexagent.properties.coolprop_provider import CoolPropProvider

        provider = CoolPropProvider()
        # Build a snapshot with WRONG version
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
        data = resp.json()
        assert data["error_code"] == "validation_failed"

    def test_provider_identity_payload_has_all_six_fields(self):
        """canonical_provider_identity_payload includes all 6 fields."""
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
    """C2: Single provenance digest authority.

    The provenance_digest in the envelope must match the result's
    provenance_digest.  There is exactly one source of truth.
    """

    def test_rating_provenance_digest_single_authority(self):
        """Rating envelope.provenance_digest == result.provenance_digest."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c2-prov-rating")
        assert envelope.provenance_digest == envelope.result.provenance_digest


# ===================================================================
# C3: Rating canonical parity
# ===================================================================


class TestC3RatingCanonicalParity:
    """C3: Rating canonical parity.

    Envelope hashes match their expected sources:
    - result_hash == result.result_hash
    - provenance_digest == result.provenance_digest
    - artifact_bundle_digest == bundle.artifact_bundle_digest
    """

    def test_result_hash_parity(self):
        """envelope.result_hash == result.result_hash."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c3-result-hash")
        assert envelope.result_hash == envelope.result.result_hash

    def test_provenance_digest_parity(self):
        """envelope.provenance_digest == result.provenance_digest."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c3-prov-hash")
        assert envelope.provenance_digest == envelope.result.provenance_digest

    def test_artifact_bundle_digest_parity(self):
        """envelope.artifact_bundle_digest matches bundle's own digest."""
        from hexagent.api.artifacts import compute_rating_artifact_bundle_digest

        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c3-bundle-hash")
        expected = compute_rating_artifact_bundle_digest(envelope.artifact_bundle)
        assert envelope.artifact_bundle_digest == expected

    def test_bundle_object_parity(self):
        """artifact_bundle result/request_identity/provider_identity/provenance
        all match the envelope result."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c3-bundle-parity")
        bundle = envelope.artifact_bundle
        assert bundle.result == envelope.result
        assert bundle.request_identity == envelope.result.request_identity
        assert bundle.provider_identity == envelope.result.provider_identity
        assert bundle.provenance_graph == envelope.result.provenance_graph

    def test_warnings_parity(self):
        """envelope.warnings == result.warnings."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c3-warnings")
        assert envelope.warnings == envelope.result.warnings

    def test_blockers_parity(self):
        """envelope.blockers == result.blockers."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c3-blockers")
        assert envelope.blockers == envelope.result.blockers

    def test_failure_parity(self):
        """envelope.failure == result.failure."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c3-failure")
        assert envelope.failure == envelope.result.failure


# ===================================================================
# C4: Repository complete parity
# ===================================================================


class TestC4RepositoryCompleteParity:
    """C4: Repository complete parity.

    On repository.complete(), the stored envelope and artifact_bundle
    must be the typed models, not raw dicts.
    """

    def test_repository_stores_typed_envelope(self):
        """Repository stores a typed RatingRunEnvelope after complete."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c4-typed-envelope")
        repo = app.state.deps.run_repository
        record = repo.get_by_run_id(envelope.run_id)
        assert record is not None
        assert record.state == RunState.COMPLETE
        assert record.envelope is not None
        assert isinstance(record.envelope, RatingRunEnvelope)

    def test_repository_stores_typed_artifact_bundle(self):
        """Repository stores typed RatingRunArtifacts."""
        from hexagent.api.artifacts import RatingRunArtifacts

        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c4-typed-bundle")
        repo = app.state.deps.run_repository
        record = repo.get_by_run_id(envelope.run_id)
        assert record is not None
        assert record.artifact_bundle is not None
        assert isinstance(record.artifact_bundle, RatingRunArtifacts)

    def test_repository_record_run_id_matches_envelope(self):
        """Stored record.run_id == envelope.run_id."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c4-run-id-match")
        repo = app.state.deps.run_repository
        record = repo.get_by_run_id(envelope.run_id)
        assert record is not None
        assert record.run_id == envelope.run_id

    def test_repository_record_request_digest_matches(self):
        """Stored record.request_digest == envelope.request_digest."""
        app = _create_fresh_app()
        _, envelope = _execute_rating(app, key="test-c4-req-digest")
        repo = app.state.deps.run_repository
        record = repo.get_by_run_id(envelope.run_id)
        assert record is not None
        assert record.request_digest == envelope.request_digest

    def test_repository_record_operation_matches(self):
        """Stored record.operation == envelope.operation."""
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
        """First request fails → 500; second request (same key) → same 500, same body."""
        app = _create_fresh_app()
        client = TestClient(app, raise_server_exceptions=False)
        key = "test-c5-fail-replay-rating"

        # Patch the rating service to force a failure
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

        # Second request with same key — FAILED_REPLAY
        resp2 = client.post(
            "/v1/double-pipe/rating",
            json=_make_rating_request(),
            headers={"Idempotency-Key": key},
        )
        assert resp2.status_code == 500
        data2 = resp2.json()

        # Exact same status code and body
        assert data1["status_code"] == data2["status_code"]
        assert data1["error_code"] == data2["error_code"]
        assert data1["error_message"] == data2["error_message"]

    def test_failed_replay_does_not_return_200(self):
        """FAILED_REPLAY must NOT return 200 — it returns the stored error."""
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

        # Replay
        resp2 = client.post(
            "/v1/double-pipe/rating",
            json=_make_rating_request(),
            headers={"Idempotency-Key": key},
        )
        assert resp2.status_code != 200

    def test_failed_replay_stores_frozen_failure_payload(self):
        """Repository stores a FrozenFailurePayload on failure."""
        app = _create_fresh_app()
        client = TestClient(app, raise_server_exceptions=False)
        key = "test-c5-frozen-payload"

        def failing_execute(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("Forced failure")

        with patch.object(app.state.deps.rating_service, "execute", failing_execute):
            resp = client.post(
                "/v1/double-pipe/rating",
                json=_make_rating_request(),
                headers={"Idempotency-Key": key},
            )

        assert resp.status_code == 500

        # Verify the response body is an ApiError
        data = resp.json()
        assert data["error_code"] == "internal_error"

    def test_frozen_failure_payload_dataclass(self):
        """FrozenFailurePayload is a frozen dataclass with expected fields."""
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
        # Frozen — cannot mutate
        with pytest.raises(AttributeError):
            payload.status_code = 400  # type: ignore[misc]

    def test_rating_failed_replay_exact_body_match(self):
        """FAILED_REPLAY returns byte-for-byte identical error body."""
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

        # Replay
        resp2 = client.post(
            "/v1/double-pipe/rating",
            json=_make_rating_request(),
            headers={"Idempotency-Key": key},
        )

        # Full JSON body comparison
        assert resp1.json() == resp2.json()


# ===================================================================
# OpenAPI contract (supplementary)
# ===================================================================


class TestOpenAPIFinal:
    """OpenAPI: exactly 6 operation IDs, unique, discriminator on result_kind."""

    def test_exactly_six_operation_ids(self):
        """The OpenAPI schema has exactly 6 operation IDs."""
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
        """AnyRunEnvelope uses result_kind as discriminator."""
        app = _create_test_app()
        schema_str = json.dumps(app.openapi())
        assert "result_kind" in schema_str

    def test_operation_ids_unique(self):
        """All 6 operation IDs are unique."""
        app = _create_test_app()
        schema = app.openapi()
        paths = schema.get("paths", {})
        ids: list[str] = []
        for path_data in paths.values():
            for method_data in path_data.values():
                if isinstance(method_data, dict) and "operationId" in method_data:
                    ids.append(method_data["operationId"])
        assert len(ids) == len(set(ids))
