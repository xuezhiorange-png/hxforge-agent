"""ULP nextafter polish and verified trial triple (V08-03)."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.task172_local_runtime.service import (
    _neighbor_float_triple_candidates,
    _neighbor_float_values,
    polish_eval_trial_residual_gate_at_nextafter,
)


def test_neighbor_triple_has_up_to_27_points() -> None:
    points = _neighbor_float_triple_candidates(100.0, 300.0, 299.0)
    assert len(points) == 27
    assert (100.0, 300.0, 299.0) in points


def test_neighbor_q_stays_nonnegative_at_zero() -> None:
    assert _neighbor_float_values(0.0, min_value=0.0) == (0.0, 5e-324)
    points = _neighbor_float_triple_candidates(0.0, 300.0, 299.0)
    assert all(q >= 0.0 for q, _, _ in points)


def test_polish_reports_baseline_when_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        "hexagent.exchangers.shell_tube.task172_local_runtime.service.eval_trial_residual_gate",
        lambda *args, **kwargs: None,
    )
    record = polish_eval_trial_residual_gate_at_nextafter(
        object(),
        object(),
        1.0,
        2.0,
        3.0,  # type: ignore[arg-type]
    )
    assert record["status"] == "UNAVAILABLE"
