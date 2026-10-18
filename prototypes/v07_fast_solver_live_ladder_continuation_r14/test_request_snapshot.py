"""Spawn-safe request snapshot hash parity and tamper rejection."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest

from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    candidate_rating_request_hash,
)
from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_live_ladder_continuation_r14.request_snapshot import (
    build_request_snapshot,
    restore_request_from_snapshot,
    verify_snapshot_integrity,
)

ROOT = Path(__file__).resolve().parents[2]


def _load_candidate_b_request():
    runner = (
        ROOT
        / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
    )
    spec = importlib.util.spec_from_file_location("q13_test", runner)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _candidate, rating_request = mod._build_candidate_requests()[CANDIDATE_B_ID]
    return rating_request


def test_frozen_candidate_b_snapshot_roundtrip_hash_parity() -> None:
    request = _load_candidate_b_request()
    snapshot = build_request_snapshot(
        request, source_commit="21cff09c176f48621fba55e1f52a8f27cb2bdaa9"
    )
    restored = restore_request_from_snapshot(snapshot)
    assert candidate_rating_request_hash(restored) == snapshot["rating_request_hash"]
    assert candidate_rating_request_hash(restored) == candidate_rating_request_hash(request)
    again = build_request_snapshot(restored, source_commit=snapshot["source_commit"])
    assert again["snapshot_sha256"] == snapshot["snapshot_sha256"]


def test_tampered_snapshot_rejected() -> None:
    request = _load_candidate_b_request()
    snapshot = build_request_snapshot(request, source_commit="test")
    bad = copy.deepcopy(snapshot)
    bad["rating_request_projection"]["task020_configuration_id"] = "tampered"
    with pytest.raises(ValueError, match="snapshot_sha256 mismatch"):
        verify_snapshot_integrity(bad)


def test_candidate_id_mismatch_rejected() -> None:
    request = _load_candidate_b_request()
    snapshot = build_request_snapshot(request, source_commit="test")
    snapshot["candidate_id"] = "00000000-0000-0000-0000-000000000001"
    with pytest.raises(ValueError, match="snapshot_sha256 mismatch"):
        restore_request_from_snapshot(snapshot)


def test_upstream_binding_tamper_rejected() -> None:
    request = _load_candidate_b_request()
    snapshot = build_request_snapshot(request, source_commit="test")
    tampered = copy.deepcopy(snapshot)
    tampered["upstream_binding_hashes"]["task029_result_hash"] = "0" * 64
    tampered["snapshot_sha256"] = None
    from prototypes.v07_fast_solver_live_ladder_continuation_r14.request_snapshot import (
        snapshot_content_digest,
    )

    body = {k: v for k, v in tampered.items() if k != "snapshot_sha256"}
    tampered["snapshot_sha256"] = snapshot_content_digest(body)
    with pytest.raises(ValueError, match="upstream binding mismatch"):
        restore_request_from_snapshot(tampered)
