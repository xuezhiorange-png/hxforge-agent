from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hexagent.domain.models import StreamSpec

pytestmark = pytest.mark.integration

EXAMPLE_PATH = Path(__file__).resolve().parents[2] / "examples" / "water_water_double_pipe.json"


def _make_test_app():
    """Create a test app with real CoolProp provider."""
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


app = _make_test_app()


def test_missing_fouling_returns_422_via_api() -> None:
    payload = json.loads(EXAMPLE_PATH.read_text())
    payload["hot_stream"].pop("fouling_resistance")
    response = TestClient(app, raise_server_exceptions=False).post(
        "/v1/cases/validate", json=payload
    )
    assert response.status_code == 422
    data = response.json()
    # New frozen ApiError format: top-level error_code
    assert data.get("api_schema_version") == "1"
    assert data.get("error_code") == "validation_failed"


def test_schema_requires_fouling_resistance() -> None:
    assert "fouling_resistance" in StreamSpec.model_json_schema()["required"]
