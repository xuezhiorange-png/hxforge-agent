"""R20: live compact authority, fail-closed gates, sizing adapter, R19 file audit."""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_live_rating_result_r19.live_evidence_admission import (
    admit_full_live_mesh_evidence,
)
from prototypes.v07_fast_solver_live_rating_result_r19.live_rating_authority_gate import (
    enforce_live_rating_authority_gates,
)
from prototypes.v07_fast_solver_live_rating_result_r19.live_result_hash import (
    LIVE_RATING_RESULT_R19_AUTHORITY_ID,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.candidate_b_sizing_requirement import (
    candidate_b_experimental_sizing_requirement,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.experimental_sizing_rating_adapter import (
    ExperimentalSizingAdapterOutcome,
    authority_open_items,
    experimental_sizing_rating_adapter,
    load_verified_live_compact_from_r19_audit,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.live_compact_rating import (
    live_compact_rating_hash,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_full_file_audit import (
    R19AuditError,
    audit_r19_full_live_rating_file,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_pinned_identity import (
    R19_LEGACY_COMPACT_HASH,
    R19_LEGACY_COMPACT_REL,
    R19_RESULT_HASH,
)

ROOT = Path(__file__).resolve().parents[2]


def test_r19_full_file_independent_audit_parity() -> None:
    audit = audit_r19_full_live_rating_file(ROOT)
    assert audit["full_file_sha256"] == audit["full_git_blob_content_sha256"]
    assert audit["full_result_hash"] == R19_RESULT_HASH
    assert audit["full_result_hash"] == audit["full_result_hash_recomputed"]


def test_live_compact_v1_authority_matches_full() -> None:
    compact, audit = load_verified_live_compact_from_r19_audit(ROOT)
    assert compact.experimental_rating_authority_id == LIVE_RATING_RESULT_R19_AUTHORITY_ID
    assert compact.full_result_hash == audit["full_result_hash"]
    assert compact.compact_result_hash == live_compact_rating_hash(compact)
    legacy = json.loads((ROOT / R19_LEGACY_COMPACT_REL).read_text(encoding="utf-8"))
    assert legacy["compact_result_hash"] == R19_LEGACY_COMPACT_HASH
    assert legacy["experimental_rating_authority_id"] != LIVE_RATING_RESULT_R19_AUTHORITY_ID


def test_sizing_adapter_executes_candidate_b_constraints() -> None:
    compact, _ = load_verified_live_compact_from_r19_audit(ROOT)
    requirement = candidate_b_experimental_sizing_requirement()
    outcome = experimental_sizing_rating_adapter(ROOT, compact, requirement)
    assert isinstance(outcome, ExperimentalSizingAdapterOutcome)
    assert outcome.candidate_id == CANDIDATE_B_ID
    assert outcome.rated_duty_w > Decimal("50000")
    assert outcome.tube_dp_pa < requirement.max_tube_dp_pa
    assert outcome.shell_dp_pa < requirement.max_shell_dp_pa
    assert outcome.production_validate_candidate_rating_usable is False
    assert outcome.duty_constraint == "PASS"


def test_gate_blocks_tampered_historical_pass() -> None:
    chain = admit_full_live_mesh_evidence(ROOT, candidate_id=CANDIDATE_B_ID)
    comparisons = list(chain.mesh_comparisons)
    bad = copy.deepcopy(comparisons[3])
    bad["overall_status"] = "FAIL"
    comparisons[3] = bad
    tampered = chain.__class__(
        request=chain.request,
        rating_request_hash=chain.rating_request_hash,
        snapshot_rel_path=chain.snapshot_rel_path,
        mesh_comparisons=tuple(comparisons),
        mesh_stages=chain.mesh_stages,
        evidence_chain_hashes=chain.evidence_chain_hashes,
        ladder_status=chain.ladder_status,
        headroom_status=chain.headroom_status,
    )
    _, blocked = enforce_live_rating_authority_gates(ROOT, tampered)
    assert blocked is not None
    assert blocked.blocked_code == "CALLER_MESH_COMPARISON_TAMPER_BLOCKED"


def test_gate_blocks_spoofed_ladder_status_without_chain_support() -> None:
    chain = admit_full_live_mesh_evidence(ROOT, candidate_id=CANDIDATE_B_ID)
    spoofed = chain.__class__(
        request=chain.request,
        rating_request_hash=chain.rating_request_hash,
        snapshot_rel_path=chain.snapshot_rel_path,
        mesh_comparisons=chain.mesh_comparisons,
        mesh_stages=chain.mesh_stages,
        evidence_chain_hashes=chain.evidence_chain_hashes,
        ladder_status="MESH_CANDIDATE_IDENTIFIED",
        headroom_status="PASS",
    )
    _, blocked = enforce_live_rating_authority_gates(ROOT, spoofed)
    assert blocked is not None
    assert blocked.blocked_code == "CALLER_HEADROOM_EVIDENCE_TAMPER_BLOCKED"


def test_sizing_adapter_blocks_wrong_compact_authority() -> None:
    compact, _ = load_verified_live_compact_from_r19_audit(ROOT)
    bad = compact.model_copy(
        update={
            "experimental_rating_authority_id": "V07-FAST-SOLVER-RATING-AUTHORITY-ADMISSION-R11",
        }
    )
    bad = bad.model_copy(update={"compact_result_hash": live_compact_rating_hash(bad)})
    outcome = experimental_sizing_rating_adapter(
        ROOT,
        bad,
        candidate_b_experimental_sizing_requirement(),
    )
    assert outcome.status == "BLOCKED"


def test_audit_rejects_wrong_file_sha(tmp_path: Path) -> None:
    bogus = tmp_path / "bogus.json"
    bogus.write_text("{}", encoding="utf-8")
    with pytest.raises(R19AuditError):
        audit_r19_full_live_rating_file(tmp_path)


def test_authority_open_items_nonempty() -> None:
    assert len(authority_open_items()) >= 3
