"""ULP nextafter polish and verified trial triple (V08-03)."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.task172_local_runtime.models import Task172BlockedResult
from hexagent.exchangers.shell_tube.task172_local_runtime.service import (
    _neighbor_float_triple_candidates,
    _neighbor_float_values,
    _warm_start_from_blocked,
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


def test_warm_start_reads_nine_fields_from_field_path() -> None:
    blocked = Task172BlockedResult(
        status="BLOCKED",
        request_hash="a" * 64,
        blocked_result_hash="b" * 64,
        failure_code="BLOCKED_RESIDUAL_ACCEPTANCE",
        field_path="102691.28;302.08697;300.917545;-2.24e-9;-9.02e-10;2.95e-9;1.97e-9;1.00e-8;2.63e-9",
        diagnostic_last_iterate=("102691.28", "302.08697", "300.917545"),
        blockers=("BLOCKED_RESIDUAL_ACCEPTANCE",),
    )
    warm = _warm_start_from_blocked(blocked)
    assert warm == (102691.28, 302.08697, 300.917545)


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
