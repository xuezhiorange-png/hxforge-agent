"""R20A fail-closed binding repair — negative injection coverage."""

from __future__ import annotations

import copy
from decimal import Decimal
from pathlib import Path

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_live_rating_result_r19.live_evidence_admission import (
    admit_full_live_mesh_evidence,
)
from prototypes.v07_fast_solver_live_rating_result_r19.live_rating_authority_gate import (
    enforce_live_rating_authority_gates,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.candidate_b_sizing_requirement import (
    candidate_b_experimental_sizing_requirement,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.experimental_sizing_rating_adapter import (
    ExperimentalSizingAdapterOutcome,
    experimental_sizing_rating_adapter,
    load_verified_live_compact_from_r19_audit,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.live_compact_rating import (
    LiveCompactCandidateRating,
    live_compact_rating_hash,
)

ROOT = Path(__file__).resolve().parents[2]
REQ = candidate_b_experimental_sizing_requirement()


def _chain(**overrides):
    base = admit_full_live_mesh_evidence(ROOT, candidate_id=CANDIDATE_B_ID)
    data = {
        "request": base.request,
        "rating_request_hash": base.rating_request_hash,
        "snapshot_rel_path": base.snapshot_rel_path,
        "mesh_comparisons": base.mesh_comparisons,
        "mesh_stages": base.mesh_stages,
        "evidence_chain_hashes": base.evidence_chain_hashes,
        "ladder_status": base.ladder_status,
        "headroom_status": base.headroom_status,
    }
    data.update(overrides)
    return base.__class__(**data)


def _rehashed(compact: LiveCompactCandidateRating, **updates) -> LiveCompactCandidateRating:
    tampered = compact.model_copy(update=updates)
    digest = live_compact_rating_hash(tampered)
    return tampered.model_copy(update={"compact_result_hash": digest})


def _adapter(compact: LiveCompactCandidateRating):
    return experimental_sizing_rating_adapter(ROOT, compact, REQ)


def test_injection_mesh_stage_hash_tamper_blocked() -> None:
    chain = _chain()
    stages = list(chain.mesh_stages)
    bad = dict(stages[0])
    bad["mesh_result_hash"] = "f" * 64
    stages[0] = bad
    _, blocked = enforce_live_rating_authority_gates(ROOT, _chain(mesh_stages=tuple(stages)))
    assert blocked is not None
    assert blocked.blocked_code == "CALLER_MESH_STAGE_TAMPER_BLOCKED"


def test_injection_comparison_tamper_blocked() -> None:
    chain = _chain()
    comparisons = list(chain.mesh_comparisons)
    bad = copy.deepcopy(comparisons[-1])
    bad["overall_status"] = "FAIL"
    comparisons[-1] = bad
    _, blocked = enforce_live_rating_authority_gates(
        ROOT,
        _chain(mesh_comparisons=tuple(comparisons)),
    )
    assert blocked is not None
    assert blocked.blocked_code == "CALLER_MESH_COMPARISON_TAMPER_BLOCKED"


def test_injection_headroom_status_tamper_blocked() -> None:
    _, blocked = enforce_live_rating_authority_gates(ROOT, _chain(headroom_status="FAIL"))
    assert blocked is not None
    assert blocked.blocked_code == "CALLER_HEADROOM_EVIDENCE_TAMPER_BLOCKED"


def test_injection_request_hash_tamper_blocked() -> None:
    _, blocked = enforce_live_rating_authority_gates(ROOT, _chain(rating_request_hash="0" * 64))
    assert blocked is not None
    assert blocked.blocked_code == "CALLER_REQUEST_TAMPER_BLOCKED"


def test_injection_compact_duty_rehash_attack_blocked() -> None:
    compact, _ = load_verified_live_compact_from_r19_audit(ROOT)
    tampered = _rehashed(compact, total_duty_w=compact.total_duty_w + Decimal("1"))
    assert _adapter(tampered).status == "BLOCKED"


def test_injection_compact_temperature_tamper_blocked() -> None:
    compact, _ = load_verified_live_compact_from_r19_audit(ROOT)
    tampered = _rehashed(compact, tube_outlet_temperature_k=Decimal("250"))
    assert _adapter(tampered).status == "BLOCKED"


def test_injection_compact_mesh_identity_tamper_blocked() -> None:
    compact, _ = load_verified_live_compact_from_r19_audit(ROOT)
    tampered = _rehashed(compact, accepted_mesh_result_hash="0" * 64)
    assert _adapter(tampered).status == "BLOCKED"


def test_injection_untrusted_full_path_blocked() -> None:
    compact, _ = load_verified_live_compact_from_r19_audit(ROOT)
    artifact = compact.full_trajectory_artifact.model_copy(update={"path": "bogus/full.json"})
    tampered = _rehashed(compact, full_trajectory_artifact=artifact)
    outcome = _adapter(tampered)
    assert outcome.status == "BLOCKED"
    assert outcome.blocked_code == "SIZING_ADAPTER_PINNED_FULL_GATE_FAILED"


def test_injection_sizing_constraints_fail() -> None:
    compact, _ = load_verified_live_compact_from_r19_audit(ROOT)
    impossible = REQ.model_copy(update={"required_duty_w": Decimal("999999999")})
    outcome = experimental_sizing_rating_adapter(ROOT, compact, impossible)
    assert outcome.status == "BLOCKED"
    assert "DUTY_BELOW_REQUIRED" in outcome.blocked_diagnostics


def test_candidate_b_experimental_evaluated_happy_path() -> None:
    compact, _ = load_verified_live_compact_from_r19_audit(ROOT)
    outcome = _adapter(compact)
    assert isinstance(outcome, ExperimentalSizingAdapterOutcome)
