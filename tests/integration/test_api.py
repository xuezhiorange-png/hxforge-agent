"""Integration and compatibility regression tests (TASK-002 review item 6)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from hexagent.domain.models import (
    DesignCase,
    FluidSpec,
    FoulingSource,
    StreamSpec,
    TPStateSpec,
)
from hexagent.domain.quantities import (
    AbsolutePressure,
    AbsoluteTemperature,
    MassFlow,
    TemperatureDifference,
)
from hexagent.exchangers.double_pipe.service import DoublePipeService

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
        configuration_fingerprint=getattr(provider, "_construction_fingerprint", "fp1"),
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


app = _make_test_app()


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
            "fouling_resistance": {
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
            "fouling_resistance": {
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


# ===========================================================================
# TASK-002 round-2 item 5: Schema metadata tests
# ===========================================================================


# -----------------------------------------------------------------------
# (a) MassFlow schema metadata
# -----------------------------------------------------------------------


def test_schema_metadata_mass_flow() -> None:
    """MassFlow.model_json_schema() exposes quantity_kind, si_unit, allowed_units."""
    schema = MassFlow.model_json_schema()
    assert schema.get("quantity_kind") == "mass_flow"
    assert schema.get("si_unit") == "kg/s"
    allowed = schema.get("allowed_units", [])
    assert isinstance(allowed, list) and len(allowed) > 0


# -----------------------------------------------------------------------
# (b) AbsoluteTemperature schema metadata
# -----------------------------------------------------------------------


def test_schema_metadata_absolute_temperature() -> None:
    """AbsoluteTemperature schema exposes quantity_kind, si_unit, examples."""
    schema = AbsoluteTemperature.model_json_schema()
    assert schema.get("quantity_kind") == "absolute_temperature"
    assert schema.get("si_unit") == "K"
    examples = schema.get("examples", [])
    assert isinstance(examples, list) and len(examples) > 0


# -----------------------------------------------------------------------
# (c) TemperatureDifference schema metadata
# -----------------------------------------------------------------------


def test_schema_metadata_temperature_difference() -> None:
    """TemperatureDifference schema exposes quantity_kind."""
    schema = TemperatureDifference.model_json_schema()
    assert schema.get("quantity_kind") == "temperature_difference"


# -----------------------------------------------------------------------
# (d) AbsolutePressure schema metadata
# -----------------------------------------------------------------------


def test_schema_metadata_absolute_pressure() -> None:
    """AbsolutePressure schema exposes quantity_kind and si_unit."""
    schema = AbsolutePressure.model_json_schema()
    assert schema.get("quantity_kind") == "absolute_pressure"
    assert schema.get("si_unit") == "Pa"


# ===========================================================================
# TASK-002 round-2 item 6: Canonical model integration tests
# ===========================================================================


# -----------------------------------------------------------------------
# (e) Canonical TP design case — uses state_spec, not legacy fields
# -----------------------------------------------------------------------


def test_canonical_tp_design_case() -> None:
    """DesignCase with TP state_spec and structured fouling validates.

    DoublePipeService.size() must NOT return BLOCKED/DP-003 (the
    legacy-fields-required error).  It may return NOT_IMPLEMENTED for
    other reasons but not because of missing inlet fields.
    """
    payload = _build_full_design_case_payload()
    case = DesignCase.model_validate(payload)

    result = DoublePipeService().size(case)
    dp003_warnings = [w for w in result.warnings if w.code == "DP-003"]
    assert not dp003_warnings, (
        f"Expected no DP-003 warning, got: {[w.message for w in dp003_warnings]}"
    )


# -----------------------------------------------------------------------
# (f) Bare fouling quantity rejected — must be structured
# -----------------------------------------------------------------------


def test_unsourced_fouling_rejected() -> None:
    """A bare fouling_resistance quantity (without source) must be rejected."""
    payload = _build_full_design_case_payload()
    payload["hot_stream"]["fouling_resistance"] = {"value": 0.0002, "unit": "m^2*K/W"}
    with pytest.raises(ValidationError):
        DesignCase.model_validate(payload)


# -----------------------------------------------------------------------
# (g) Unsupported schema_version rejected
# -----------------------------------------------------------------------


def test_unsupported_schema_version_rejected() -> None:
    """TPStateSpec with schema_version='9.9' must fail (not Literal '1.0')."""
    with pytest.raises(ValidationError, match="schema_version"):
        TPStateSpec(
            type="TP",
            schema_version="9.9",
            temperature={"value": 300.0, "unit": "K"},
            pressure={"value": 1e5, "unit": "Pa"},
        )


# -----------------------------------------------------------------------
# (h) FluidSpec backend is required
# -----------------------------------------------------------------------


def test_fluid_backend_required() -> None:
    """FluidSpec without 'backend' must fail (field is required)."""
    with pytest.raises(ValidationError, match="backend"):
        FluidSpec(name="Water")


# -----------------------------------------------------------------------
# (i) Legacy TP still works
# -----------------------------------------------------------------------


def test_legacy_tp_still_works() -> None:
    """StreamSpec with legacy inlet_temperature + inlet_pressure + structured fouling validates.
    Properties inlet_temperature_k and inlet_pressure_pa return correct SI values.
    """
    payload = {
        "fluid": {"backend": "CoolProp", "name": "Water", "phase_hint": "liquid"},
        "mass_flow": {"value": 1.0, "unit": "kg/s"},
        "inlet_temperature": {"value": 80.0, "unit": "degC"},
        "inlet_pressure": {"value": 3.0, "unit": "bar(a)"},
        "outlet_temperature": {"value": 60.0, "unit": "degC"},
        "fouling_resistance": {
            "value": {"value": 0.0002, "unit": "m^2*K/W"},
            "source": {
                "source_type": "STANDARD",
                "reference_id": "TEMA-RGP-T-2.4",
                "edition": "TBD",
                "table_or_clause": "TBD",
                "verification_status": "UNVERIFIED_REFERENCE",
                "note": "test",
            },
        },
    }
    stream = StreamSpec.model_validate(payload)
    assert stream.inlet_temperature_k == pytest.approx(353.15, abs=1e-6)
    assert stream.inlet_pressure_pa == pytest.approx(300_000.0, abs=1e-3)


# -----------------------------------------------------------------------
# (j) state_spec + legacy conflict rejected
# -----------------------------------------------------------------------


def test_state_spec_conflicting_with_legacy_rejected() -> None:
    """StreamSpec with BOTH state_spec TP AND inlet_temperature must fail."""
    payload = {
        "fluid": {"backend": "CoolProp", "name": "Water", "phase_hint": "liquid"},
        "mass_flow": {"value": 1.0, "unit": "kg/s"},
        "state_spec": {
            "schema_version": "1.0",
            "type": "TP",
            "temperature": {"value": 90.0, "unit": "degC"},
            "pressure": {"value": 4.0, "unit": "bar(a)"},
        },
        "inlet_temperature": {"value": 80.0, "unit": "degC"},
        "fouling_resistance": {
            "value": {"value": 0.0002, "unit": "m^2*K/W"},
            "source": {
                "source_type": "STANDARD",
                "reference_id": "TEMA-RGP-T-2.4",
                "edition": "TBD",
                "table_or_clause": "TBD",
                "verification_status": "UNVERIFIED_REFERENCE",
                "note": "test",
            },
        },
    }
    with pytest.raises(ValidationError, match="Cannot provide both state_spec and legacy"):
        StreamSpec.model_validate(payload)


# -----------------------------------------------------------------------
# (k) Bare fouling dict not accepted by canonical model
# -----------------------------------------------------------------------


def test_bare_fouling_not_in_canonical_model() -> None:
    """StreamSpec with fouling_resistance as a plain dict (not structured) must fail."""
    payload = {
        "fluid": {"backend": "CoolProp", "name": "Water", "phase_hint": "liquid"},
        "mass_flow": {"value": 1.0, "unit": "kg/s"},
        "state_spec": {
            "schema_version": "1.0",
            "type": "TP",
            "temperature": {"value": 90.0, "unit": "degC"},
            "pressure": {"value": 4.0, "unit": "bar(a)"},
        },
        "fouling_resistance": {"value": 0.0002, "unit": "m^2*K/W"},
    }
    with pytest.raises(ValidationError):
        StreamSpec.model_validate(payload)
