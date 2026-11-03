"""R25 R2A qualification tests."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.rating_pair_admission import (
    admit_candidate_b_live_rating,
    admit_second_candidate_live_rating,
)
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.frozen_candidate_qualification import (
    qualify_all_frozen_candidates,
)
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.negative_injection_r25 import (
    run_negative_injection_r25,
)
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.r2a_contract import (
    R2A_AUTHORITY_HASH,
    R2A_AUTHORITY_ID,
    production_r2a_contract_payload,
)
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.task167_rule_pack_claim_audit import (
    audit_both_candidates,
)

ROOT = Path(__file__).resolve().parents[2]


def test_production_r2a_contract_matches_service_constants() -> None:
    payload = production_r2a_contract_payload()
    assert payload["r2a_authority_id"] == R2A_AUTHORITY_ID
    assert payload["r2a_authority_hash"] == R2A_AUTHORITY_HASH


def test_frozen_candidates_insufficient_without_producer_non_trigger_witness() -> None:
    rows = qualify_all_frozen_candidates(ROOT)
    assert len(rows) == 4
    assert all(row["admission_status"] == "FROZEN_EVIDENCE_INSUFFICIENT" for row in rows)
    assert all(row["production_r2a_certificate_replay"] == "BLOCKED" for row in rows)


def test_task167_configuration_approval_not_verified_on_requests() -> None:
    audit = audit_both_candidates(
        admit_candidate_b_live_rating(ROOT),
        admit_second_candidate_live_rating(ROOT),
    )
    assert (
        audit["task167_configuration_rule_pack_approval"]
        == "CONFIGURATION_RULE_PACK_APPROVAL_NOT_VERIFIED"
    )
    assert audit["fiv_numeric_limit_authority"] == "MISSING"


def test_negative_injection_r25_all_pass() -> None:
    rows = run_negative_injection_r25()
    assert all(row["PASS"] == "true" for row in rows)


def test_qualification_determinism() -> None:
    a = qualify_all_frozen_candidates(ROOT)
    b = qualify_all_frozen_candidates(ROOT)
    ha = hashlib.sha256(json.dumps(a, sort_keys=True).encode()).hexdigest()
    hb = hashlib.sha256(json.dumps(b, sort_keys=True).encode()).hexdigest()
    assert ha == hb
