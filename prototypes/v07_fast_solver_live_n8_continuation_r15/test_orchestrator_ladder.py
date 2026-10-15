"""Orchestrator-level ladder regression (no live numerical solve)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_live_ladder_continuation_r14.continuation_engine import (
    LadderContinuationDeps,
    run_live_ladder_continuation,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.stage_admission import (
    PriorStagePin,
)

ROOT = Path(__file__).resolve().parents[2]


def _load_request():
    runner = (
        ROOT
        / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
    )
    spec = importlib.util.spec_from_file_location("q13", runner)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _candidate, rating_request = mod._build_candidate_requests()[CANDIDATE_B_ID]
    return rating_request


def _cmp(status: str, coarse: int, fine: int) -> dict[str, str | int]:
    return {
        "overall_status": status,
        "duty_status": status,
        "wall_status": status,
        "coarse_subdivisions": coarse,
        "fine_subdivisions": fine,
    }


def _stage(mesh_n: int, request_hash: str) -> dict[str, object]:
    return {
        "mesh_n": mesh_n,
        "worker_status": "TERMINAL_ACCEPTED",
        "terminal_tolerance_pass": True,
        "shooting_enthalpy_for_rehydrate": str(mesh_n),
        "outer_iterations_for_rehydrate": 1,
        "mesh_result_hash": f"{mesh_n:064x}",
        "rating_request_hash": request_hash,
        "candidate_id": CANDIDATE_B_ID,
    }


def test_orchestrator_headroom_candidate_n32_n64() -> None:
    request = _load_request()
    request_hash = request.candidate_id  # replaced below
    from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
        candidate_rating_request_hash,
    )

    request_hash = candidate_rating_request_hash(request)
    compare_script = {
        (1, 2): _cmp("FAIL", 1, 2),
        (2, 4): _cmp("FAIL", 2, 4),
        (4, 8): _cmp("FAIL", 4, 8),
        (8, 16): _cmp("PASS", 8, 16),
        (16, 32): _cmp("PASS", 16, 32),
        (32, 64): _cmp("PASS", 32, 64),
    }

    def mock_admit(_root: Path, pin: PriorStagePin, **kwargs: object) -> dict[str, object]:
        return _stage(pin.mesh_n, str(kwargs["expected_request_hash"]))

    def mock_rehydrate(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"status": "OK"}

    def mock_compare(
        _snapshot: Path, *, coarse: dict[str, object], fine: dict[str, object], **_kw: object
    ) -> dict[str, object]:
        key = (int(coarse["mesh_n"]), int(fine["mesh_n"]))
        return {"status": "OK", "comparison": compare_script[key]}

    live_calls: list[int] = []

    def mock_live_worker(
        _snapshot: Path, *, mesh_n: int, **_kw: object
    ) -> dict[str, object]:
        live_calls.append(mesh_n)
        return _stage(mesh_n, request_hash)

    pins = tuple(
        PriorStagePin(n, f"fake/n{n}.json", "0" * 64) for n in (1, 2, 4)
    )
    outcome = run_live_ladder_continuation(
        request,
        root=ROOT,
        source_commit="test",
        snapshot_dir=ROOT / "docs/tasks/evidence/.r15-test-snapshot",
        stage_dir=None,
        prior_pins=pins,
        live_mesh_levels=(8, 16, 32, 64),
        mesh_budgets_s={8: 1, 16: 1, 32: 1, 64: 1},
        total_budget_s=60.0,
        rehydrate_budget_s=1.0,
        compare_budget_s=1.0,
        deps=LadderContinuationDeps(
            run_live_worker=mock_live_worker,
            bounded_rehydrate=mock_rehydrate,
            bounded_compare=mock_compare,
            admit_prior=mock_admit,
        ),
    )
    assert live_calls == [8, 16, 32, 64]
    assert outcome.ladder_continuation_status == "HEADROOM_PASS"
    assert len(outcome.mesh_comparisons) == 6


def test_orchestrator_headroom_fail_blocks() -> None:
    request = _load_request()
    from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
        candidate_rating_request_hash,
    )

    request_hash = candidate_rating_request_hash(request)
    compare_script = {
        (1, 2): _cmp("PASS", 1, 2),
        (2, 4): _cmp("PASS", 2, 4),
        (4, 8): _cmp("FAIL", 4, 8),
    }

    def mock_admit(_root: Path, pin: PriorStagePin, **kwargs: object) -> dict[str, object]:
        return _stage(pin.mesh_n, str(kwargs["expected_request_hash"]))

    def mock_rehydrate(*_a: object, **_k: object) -> dict[str, object]:
        return {"status": "OK"}

    def mock_compare(
        _snapshot: Path, *, coarse: dict[str, object], fine: dict[str, object], **_kw: object
    ) -> dict[str, object]:
        key = (int(coarse["mesh_n"]), int(fine["mesh_n"]))
        return {"status": "OK", "comparison": compare_script[key]}

    def mock_live_worker(_snapshot: Path, *, mesh_n: int, **_kw: object) -> dict[str, object]:
        return _stage(mesh_n, request_hash)

    pins = tuple(PriorStagePin(n, f"fake/n{n}.json", "0" * 64) for n in (1, 2))
    outcome = run_live_ladder_continuation(
        request,
        root=ROOT,
        source_commit="test",
        snapshot_dir=ROOT / "docs/tasks/evidence/.r15-test-snapshot",
        stage_dir=None,
        prior_pins=pins,
        live_mesh_levels=(4, 8),
        mesh_budgets_s={4: 1, 8: 1},
        total_budget_s=30.0,
        rehydrate_budget_s=1.0,
        compare_budget_s=1.0,
        deps=LadderContinuationDeps(
            run_live_worker=mock_live_worker,
            bounded_rehydrate=mock_rehydrate,
            bounded_compare=mock_compare,
            admit_prior=mock_admit,
        ),
    )
    assert outcome.status == "BLOCKED"
    assert outcome.blocked_code == "MESH_NOT_CONVERGED"


def test_orchestrator_rehydrate_replay_mismatch() -> None:
    request = _load_request()
    from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
        candidate_rating_request_hash,
    )

    request_hash = candidate_rating_request_hash(request)

    def mock_admit(_root: Path, pin: PriorStagePin, **kwargs: object) -> dict[str, object]:
        return _stage(pin.mesh_n, str(kwargs["expected_request_hash"]))

    def mock_rehydrate(*_a: object, **_k: object) -> dict[str, object]:
        return {
            "status": "GATE_FAIL",
            "blocked_code": "REPLAY_MISMATCH",
            "blocked_diagnostics": ("hash",),
        }

    def mock_compare(*_a: object, **_k: object) -> dict[str, object]:
        raise AssertionError("compare should not run")

    def mock_live_worker(_snapshot: Path, *, mesh_n: int, **_kw: object) -> dict[str, object]:
        return _stage(mesh_n, request_hash)

    outcome = run_live_ladder_continuation(
        request,
        root=ROOT,
        source_commit="test",
        snapshot_dir=ROOT / "docs/tasks/evidence/.r15-test-snapshot",
        stage_dir=None,
        prior_pins=(PriorStagePin(1, "fake/n1.json", "0" * 64),),
        live_mesh_levels=(),
        mesh_budgets_s={},
        total_budget_s=10.0,
        rehydrate_budget_s=1.0,
        compare_budget_s=1.0,
        deps=LadderContinuationDeps(
            run_live_worker=mock_live_worker,
            bounded_rehydrate=mock_rehydrate,
            bounded_compare=mock_compare,
            admit_prior=mock_admit,
        ),
    )
    assert outcome.status == "BLOCKED"
    assert outcome.blocked_code == "REPLAY_MISMATCH"


def test_orchestrator_compare_timeout() -> None:
    request = _load_request()
    from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
        candidate_rating_request_hash,
    )

    request_hash = candidate_rating_request_hash(request)

    def mock_admit(_root: Path, pin: PriorStagePin, **kwargs: object) -> dict[str, object]:
        return _stage(pin.mesh_n, str(kwargs["expected_request_hash"]))

    def mock_rehydrate(*_a: object, **_k: object) -> dict[str, object]:
        return {"status": "OK"}

    def mock_compare(*_a: object, **_k: object) -> dict[str, object]:
        return {"status": "TIMEOUT", "blocked_code": "COMPARE_HARD_TIMEOUT"}

    def mock_live_worker(_snapshot: Path, *, mesh_n: int, **_kw: object) -> dict[str, object]:
        return _stage(mesh_n, request_hash)

    outcome = run_live_ladder_continuation(
        request,
        root=ROOT,
        source_commit="test",
        snapshot_dir=ROOT / "docs/tasks/evidence/.r15-test-snapshot",
        stage_dir=None,
        prior_pins=(
            PriorStagePin(1, "fake/n1.json", "0" * 64),
            PriorStagePin(2, "fake/n2.json", "0" * 64),
        ),
        live_mesh_levels=(),
        mesh_budgets_s={},
        total_budget_s=10.0,
        rehydrate_budget_s=1.0,
        compare_budget_s=1.0,
        deps=LadderContinuationDeps(
            run_live_worker=mock_live_worker,
            bounded_rehydrate=mock_rehydrate,
            bounded_compare=mock_compare,
            admit_prior=mock_admit,
        ),
    )
    assert outcome.status == "TIMEOUT"
    assert outcome.blocked_code == "COMPARE_HARD_TIMEOUT"
