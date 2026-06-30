from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from hexagent.api.main import app
from hexagent.domain.models import StreamSpec

EXAMPLE_PATH = Path(__file__).resolve().parents[2] / "examples" / "water_water_double_pipe.json"


def test_missing_fouling_returns_422_via_api() -> None:
    payload = json.loads(EXAMPLE_PATH.read_text())
    payload["hot_stream"].pop("fouling_resistance")
    response = TestClient(app, raise_server_exceptions=False).post("/v1/cases/validate", json=payload)
    assert response.status_code == 422
    data = response.json()
    # New frozen ApiError format: top-level error_code
    assert data.get("api_schema_version") == "1"
    assert data.get("error_code") == "validation_failed"


def test_schema_requires_fouling_resistance() -> None:
    assert "fouling_resistance" in StreamSpec.model_json_schema()["required"]
