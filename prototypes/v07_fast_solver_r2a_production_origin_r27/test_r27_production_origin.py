"""R27 production certificate origin fail-closed tests."""

# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path

from prototypes.v07_fast_solver_r2a_producer_origin_r26.full_certificate_positive_witness import (
    run_full_certificate_positive_witness,
)
from prototypes.v07_fast_solver_r2a_production_origin_r27.negative_injection_r27 import (
    run_negative_injection_r27,
)
from prototypes.v07_fast_solver_r2a_production_origin_r27.production_origin_gate import (
    audit_production_certificate_origin,
    run_true_production_certificate_witness,
)

ROOT = Path(__file__).resolve().parents[2]


def test_contract_fixture_pass_not_production_verified() -> None:
    witness = run_full_certificate_positive_witness(ROOT)
    assert witness["witness_status"] == "PASS"
    assert witness["verifier_status"] == "CONTRACT_FIXTURE_PASS"


def test_true_production_witness_blocked_missing_event_projections() -> None:
    witness = run_true_production_certificate_witness(ROOT)
    assert witness["witness_status"] == "BLOCKED_EVIDENCE_MISSING"


def test_production_origin_audit_finds_pinned_certificates() -> None:
    audit = audit_production_certificate_origin(ROOT)
    assert audit["production_certificate_origin"] == "EVIDENCE_MISSING"
    assert audit["pinned_certificate_count"] == 3


def test_negative_injection_r27_exact_codes() -> None:
    rows = run_negative_injection_r27()
    assert all(row["PASS"] == "true" for row in rows)
