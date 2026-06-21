"""Integration and compatibility regression tests (TASK-002 review item 6)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from hexagent.api.main import app
from hexagent.domain.models import (
    DesignCase,
    FluidSpec,
    FoulingSource,
)
from hexagent.domain.quantities import (
    AbsolutePressure,
    AbsoluteTemperature,
    MassFlow,
)

EXAMPLE_PATH = Path(__file__).resolve().parents[2] / "examples" / "water_water_double_pipe.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_example() -> dict:
    """Load the canonical example JSON fixture."""
    return json.loads(EXAMPLE_PATH.read_text())


def _build_full_design_case_payload() -> dict:
    """Return a complete, valid DesignCase payload dict."""
    return {
        "name": "unit-test-case",
        "hot_stream": {
            "fluid": {"backend": "CoolProp", "name": "Water", "phase_hint": "liquid"},
            "mass_flow": {"value": 2.0, "unit": "kg/s"},
            "state_spec": {
                "schema_version": "1.0",
                "type": "TP",
                "temperature": {"value": 90.0, "unit": "degC"},
                "pressure": {"value": 4.0, "unit": "bar(a)"},
            },
            "outlet_temperature": {"value": 60.0, "unit": "degC"},
            "allowable_pressure_drop": {"value": 50.0, "unit": "kPa"},
            "fouling_resistance_spec": {
                "value": {"value": 0.0002, "unit": "m^2*K/W"},
                "source": {
                    "source_type": "STANDARD",
                    "reference_id": "TEMA-RGP-T-2.4",
                    "edition": "TBD",
                    "table_or_clause": "TBD",
                    "verification_status": "UNVERIFIED_REFERENCE",
                    "note": "Placeholder",
                },
            },
        },
        "cold_stream": {
            "fluid": {"backend": "CoolProp", "name": "Water", "phase_hint": "liquid"},
            "mass_flow": {"value": 2.0, "unit": "kg/s"},
            "state_spec": {
                "schema_version": "1.0",
                "type": "TP",
                "temperature": {"value": 20.0, "unit": "degC"},
                "pressure": {"value": 3.0, "unit": "bar(a)"},
            },
            "outlet_temperature": {"value": 50.0, "unit": "degC"},
            "allowable_pressure_drop": {"value": 50.0, "unit": "kPa"},
            "fouling_resistance_spec": {
                "value": {"value": 0.0002, "unit": "m^2*K/W"},
                "source": {
                    "source_type": "STANDARD",
                    "reference_id": "TEMA-RGP-T-2.4",
                    "edition": "TBD",
                    "table_or_clause": "TBD",
                    "verification_status": "UNVERIFIED_REFERENCE",
                    "note": "Placeholder",
                },
            },
        },
        "constraints": {
            "design_pressure_hot": {"value": 10.0, "unit": "bar(a)"},
            "design_pressure_cold": {"value": 10.0, "unit": "bar(a)"},
            "design_temperature_hot": {"value": 120.0, "unit": "degC"},
            "design_temperature_cold": {"value": 80.0, "unit": "degC"},
            "corrosion_allowance": {"value": 1.0, "unit": "mm"},
            "required_area_margin_fraction": 0.1,
        },
        "target_duty": {"value": 250.0, "unit": "kW"},
    }


# ---------------------------------------------------------------------------
# (a) Example file validates against DesignCase
# ---------------------------------------------------------------------------


def test_example_validates_against_design_case() -> None:
    """The canonical example JSON must be fully valid under DesignCase."""
    payload = _load_example()
    case = DesignCase.model_validate(payload)
    assert case.name == "water-to-water-demo"


# ---------------------------------------------------------------------------
# (b) JSON round-trip: serialize → revalidate → compare
# ---------------------------------------------------------------------------


def test_design_case_json_round_trip() -> None:
    """DesignCase survives a JSON serialization round-trip without data loss."""
    payload = _load_example()
    case = DesignCase.model_validate(payload)

    exported = json.loads(case.model_dump_json())
    reimported = DesignCase.model_validate(exported)

    # Compare key fields (UUID changes on re-import, so compare the rest)
    assert reimported.name == case.name
    assert reimported.target_duty == case.target_duty
    assert reimported.hot_stream.mass_flow == case.hot_stream.mass_flow
    assert reimported.cold_stream.mass_flow == case.cold_stream.mass_flow
    assert reimported.constraints == case.constraints


# ---------------------------------------------------------------------------
# (c) API returns structured error on invalid unit dimension
# ---------------------------------------------------------------------------


def test_api_unit_error_response() -> None:
    """POST /v1/cases/validate with a wrong-dimension unit returns 422.

    The validate endpoint is validated by Pydantic; an invalid unit
    (e.g. pressure unit for a mass-flow field) should produce a 422
    with structured error detail containing 'quantity_unit_not_allowed'.
    """
    client = TestClient(app)

    # Build a valid payload then corrupt mass_flow.unit with a pressure unit
    payload = _build_full_design_case_payload()
    payload["hot_stream"]["mass_flow"]["unit"] = "Pa"  # wrong dimension

    response = client.post("/v1/cases/validate", json=payload)
    assert response.status_code == 422
    detail_text = json.dumps(response.json())
    assert "quantity_unit_not_allowed" in detail_text


# ---------------------------------------------------------------------------
# (d) Legacy TP + state_spec conflict rejected
# ---------------------------------------------------------------------------


def test_legacy_tp_payload_rejected() -> None:
    """Providing BOTH state_spec and inlet_temperature/inlet_pressure is invalid."""
    payload = _build_full_design_case_payload()

    # Add legacy inlet fields on top of existing state_spec
    payload["hot_stream"]["inlet_temperature"] = {"value": 90.0, "unit": "degC"}
    payload["hot_stream"]["inlet_pressure"] = {"value": 4.0, "unit": "bar(a)"}

    with pytest.raises(ValidationError, match="Cannot provide both state_spec and legacy"):
        DesignCase.model_validate(payload)


# ---------------------------------------------------------------------------
# (e) PQ state_spec quality out of range
# ---------------------------------------------------------------------------


def test_state_spec_pq_rejects_quality_out_of_range() -> None:
    """PQ state_spec quality must be in [0, 1]; 1.5 must fail."""
    payload = _build_full_design_case_payload()

    # Replace the hot stream's TP state_spec with a PQ one having bad quality
    payload["hot_stream"]["state_spec"] = {
        "schema_version": "1.0",
        "type": "PQ",
        "pressure": {"value": 4.0, "unit": "bar(a)"},
        "quality": 1.5,
    }

    with pytest.raises(ValidationError):
        DesignCase.model_validate(payload)


# ---------------------------------------------------------------------------
# (f) FoulingSource rejects unknown verification_status
# ---------------------------------------------------------------------------


def test_fouling_source_rejects_unknown_verification_status() -> None:
    """FoulingSource.verification_status must be a valid VerificationStatus enum."""
    with pytest.raises(ValidationError, match="verification_status"):
        FoulingSource(
            source_type="STANDARD",
            reference_id="TEMA-RGP-T-2.4",
            edition="TBD",
            table_or_clause="TBD",
            verification_status="INVALID",
            note="test",
        )


# ---------------------------------------------------------------------------
# (g) StrictBaseModel rejects extra fields
# ---------------------------------------------------------------------------


def test_strict_model_rejects_unknown_field() -> None:
    """FluidSpec (StrictBaseModel) must reject any unknown field."""
    with pytest.raises(ValidationError, match="extra_forbidden"):
        FluidSpec(backend="CoolProp", name="Water", unknown_field="oops")


# ---------------------------------------------------------------------------
# (h) AbsoluteTemperature rejects 0 K (-273.15 degC)
# ---------------------------------------------------------------------------


def test_absolute_temperature_rejects_zero_kelvin() -> None:
    """AbsoluteTemperature must be > 0 K; -273.15 degC = 0 K is invalid."""
    with pytest.raises(ValidationError):
        AbsoluteTemperature(value=-273.15, unit="degC")


# ---------------------------------------------------------------------------
# (i) AbsolutePressure rejects zero
# ---------------------------------------------------------------------------


def test_absolute_pressure_rejects_zero() -> None:
    """AbsolutePressure must be > 0 Pa; 0 Pa is invalid."""
    with pytest.raises(ValidationError):
        AbsolutePressure(value=0, unit="Pa")


# ---------------------------------------------------------------------------
# (j) MassFlow rejects zero
# ---------------------------------------------------------------------------


def test_mass_flow_rejects_zero() -> None:
    """MassFlow must be > 0; zero mass flow is invalid."""
    with pytest.raises(ValidationError):
        MassFlow(value=0, unit="kg/s")
