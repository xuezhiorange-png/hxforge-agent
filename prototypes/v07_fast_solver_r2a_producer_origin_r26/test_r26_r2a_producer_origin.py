"""R26 producer origin and independent Q1-Q15 replay tests."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from prototypes.v07_fast_solver_r2a_producer_origin_r26.full_certificate_positive_witness import (
    run_full_certificate_positive_witness,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.negative_injection_r26 import (
    run_negative_injection_r26,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.q_predicate_independent_replay import (
    run_captured_positive_witness,
)

ROOT = Path(__file__).resolve().parents[2]


def test_captured_q1_q15_independent_replay_positive() -> None:
    witness = run_captured_positive_witness(ROOT)
    assert witness["witness_status"] == "PASS"
    assert witness["q_independent_replay"] is True
    assert witness["tamper_q2_blocked"] is True


def test_full_certificate_positive_producer_witness() -> None:
    witness = run_full_certificate_positive_witness(ROOT)
    assert witness["witness_status"] == "PASS"
    assert witness["verifier_status"] == "CONTRACT_FIXTURE_PASS"
    assert witness["contract_fixture_status"] == "CONTRACT_FIXTURE_PASS"


def test_negative_injection_r26_exact_codes() -> None:
    rows = run_negative_injection_r26()
    assert all(row["PASS"] == "true" for row in rows)


def test_r26_witness_determinism() -> None:
    a = run_full_certificate_positive_witness(ROOT)
    b = run_full_certificate_positive_witness(ROOT)
    ha = hashlib.sha256(json.dumps(a, sort_keys=True).encode()).hexdigest()
    hb = hashlib.sha256(json.dumps(b, sort_keys=True).encode()).hexdigest()
    assert ha == hb
