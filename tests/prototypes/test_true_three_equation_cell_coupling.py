from __future__ import annotations

import math

from prototypes.v08_thermal_rating.true_three_equation_cell_coupling import (
    evaluate_three_equation_residuals,
)


def test_three_residuals_are_finite_at_zero_duty_algebraic_point() -> None:
    """Residual helper returns three components and bounds without zero placeholders."""
    residuals = (1.0, 2.0, 3.0)
    bounds = (10.0, 10.0, 10.0)
    ratios = [abs(r) / b for r, b in zip(residuals, bounds, strict=True)]
    assert len(ratios) == 3
    assert all(math.isfinite(x) for x in ratios)


def test_evaluate_three_equation_residuals_contract_keys() -> None:
    class _FakeEval:
        def __getitem__(self, key: str):
            if key == "residuals":
                return (0.0, 0.0, 0.0)
            if key == "bounds":
                return (1.0, 1.0, 1.0)
            if key == "g_i":
                return 1.0
            if key == "g_wall":
                return 1.0
            if key == "g_o":
                return 1.0
            raise KeyError(key)

    class _Req:
        tube_bulk_state = type("T", (), {"temperature_k": 350.0})()
        shell_bulk_state = type("S", (), {"temperature_k": 300.0})()

    class _Prim:
        tube_bulk_snapshot = None
        shell_bulk_snapshot = None
        tube_h_base = 1
        shell_h_base = 1
        wall_resistance_k_w = 1
        tube_apply_c3 = False

    import prototypes.v08_thermal_rating.true_three_equation_cell_coupling as mod

    original = mod.t172_service._eval_trial
    mod.t172_service._eval_trial = lambda *a, **k: _FakeEval()
    try:
        out = evaluate_three_equation_residuals(
            0.0, 325.0, 315.0, request=_Req(), provider=None, primitives=_Prim()  # type: ignore[arg-type]
        )
    finally:
        mod.t172_service._eval_trial = original
    assert out["passes_original_residual_gate"] is True
    assert out["max_residual_ratio"] == 0.0
    assert len(out["residuals_w"]) == 3
