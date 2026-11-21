"""CoolProp TP→PH audit mapping and failure visibility."""

from __future__ import annotations

from decimal import Decimal

import pytest

from hexagent.properties.base import FluidIdentifier
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    load_case_bindings,
    resolve_candidate_bindings_by_id,
)
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.enthalpy_audit_context_v08 import (
    run_enthalpy_audit_body,
    tp_ph_reconstruction_audit,
)

FROZEN_CANDIDATE_ID = "9277ebb8-5b05-5130-8b90-92ee4768606b"


@pytest.fixture(scope="module")
def bindings_330():
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    row = resolve_candidate_bindings_by_id(
        FROZEN_CANDIDATE_ID, normalized, handoff, provider, max_valid=64
    )
    assert row is not None
    return row, provider


def test_tp_ph_water_mapping_pass(bindings_330) -> None:
    bindings, provider = bindings_330

    def body(_c: object, _t: object) -> object:
        return tp_ph_reconstruction_audit(provider, bindings)

    audit = run_enthalpy_audit_body(bindings, provider, subdivisions=1, body=body)
    assert audit.query_status == "PASS"
    assert audit.user_fluid_identity == "PURE_ORDINARY_WATER"
    assert audit.coolprop_fluid_name == "Water"
    assert audit.delta_h_j_kg is not None
    assert audit.property_exception is None
    assert audit.delta_t_k is not None


def test_tp_ph_invalid_fluid_blocked(bindings_330, monkeypatch: pytest.MonkeyPatch) -> None:
    bindings, provider = bindings_330

    def body(_c: object, _t: object) -> object:
        return tp_ph_reconstruction_audit(provider, bindings)

    # Force invalid CoolProp fluid name while keeping user identity unchanged.
    import prototypes.v08_thermal_rating.enthalpy_audit_context_v08 as mod

    def _bad_map(_b):
        return ("PURE_ORDINARY_WATER", "NotARealCoolPropFluidXYZ", "test")

    monkeypatch.setattr(mod, "_coolprop_water_for_v08_shell", _bad_map)
    audit = run_enthalpy_audit_body(bindings, provider, subdivisions=1, body=body)
    assert audit.query_status == "BLOCKED"
    assert audit.delta_h_j_kg is None
    assert audit.property_exception is not None


def test_pure_ordinary_water_string_fails_coolprop_directly() -> None:
    provider = CoolPropProvider()
    with pytest.raises(Exception):
        provider.state_tp(FluidIdentifier(name="PURE_ORDINARY_WATER"), 295.0, 101325.0)
