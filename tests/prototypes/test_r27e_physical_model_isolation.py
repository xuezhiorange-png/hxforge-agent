"""R27E physical model isolation and provenance."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from prototypes.v07_general_rating_sizing_mvp import r27e_tube_regime_diagnostics

from prototypes.v07_general_rating_sizing_mvp.r27e_targeted_recovery import (
    R27D_ORIGINAL_BLOCKERS,
    R27D_RECOVERY_CANDIDATE_IDS,
)


def test_r27d_original_blockers_frozen_not_runtime_n1_codes() -> None:
    assert len(R27D_ORIGINAL_BLOCKERS) == len(R27D_RECOVERY_CANDIDATE_IDS)
    for cid in R27D_RECOVERY_CANDIDATE_IDS:
        blocker = R27D_ORIGINAL_BLOCKERS[cid]
        assert blocker != "_RuntimeFailure"
        assert not blocker.startswith("BLOCKED_N1")


def test_enthalpy_probe_distinguishes_coolprop_and_rating_domain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Provider:
        def state_ph(self, *_args, **_kwargs):
            return SimpleNamespace(temperature_k=293.4, phase="LIQUID")

    monkeypatch.setattr(r27e_tube_regime_diagnostics, "CoolPropProvider", _Provider)
    result = r27e_tube_regime_diagnostics.probe_enthalpy_domain_exit(
        enthalpy_j_kg=85139.624,
        pressure_pa=101325.0,
        rating_admitted_h_min_j_kg=92000.0,
        rating_admitted_h_max_j_kg=155000.0,
    )
    assert result["property_domain_ok"] is True
    assert result["rating_admitted_enthalpy_domain_ok"] is False
    assert result["rating_domain_is_not_coolprop_domain"] is True
