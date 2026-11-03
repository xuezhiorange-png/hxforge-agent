"""R21 Phase A: deep request gate and sizing adapter fail-closed supplements."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from hexagent.exchangers.shell_tube.task173_integrated_sizing.models import (
    SizingRequirementAuthority,
)
from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_experimental_sizing_requirement as scer,
)
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
    experimental_sizing_rating_adapter,
    load_verified_live_compact_from_r19_audit,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.live_compact_rating import (
    live_compact_rating_hash,
)

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
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


def _tampered_chain_request(request):
    return _chain(request=request)


def test_injection_task171_topology_keeps_result_hash_blocked() -> None:
    base = admit_full_live_mesh_evidence(ROOT, candidate_id=CANDIDATE_B_ID)
    t171 = base.request.task171_result
    topo = t171.topology_definition
    assert topo is not None
    intervals = list(topo.intervals)
    start = Decimal(str(intervals[0].start_m))
    first = intervals[0].model_copy(update={"start_m": str(start + Decimal("0.01"))})
    intervals[0] = first
    bad_topo = topo.model_copy(update={"intervals": tuple(intervals)})
    bad_t171 = t171.model_copy(update={"topology_definition": bad_topo})
    _, blocked = enforce_live_rating_authority_gates(
        ROOT, _tampered_chain_request(base.request.model_copy(update={"task171_result": bad_t171}))
    )
    assert blocked is not None
    assert blocked.blocked_code == "CALLER_REQUEST_TAMPER_BLOCKED"


def test_injection_task031_geometry_keeps_geometry_hash_blocked() -> None:
    base = admit_full_live_mesh_evidence(ROOT, candidate_id=CANDIDATE_B_ID)
    geom = base.request.task031_geometry
    area = Decimal(str(geom.central_crossflow_flow_area_m2))
    bad_geom = replace(geom, central_crossflow_flow_area_m2=str(area + Decimal("1")))
    _, blocked = enforce_live_rating_authority_gates(
        ROOT,
        _tampered_chain_request(base.request.model_copy(update={"task031_geometry": bad_geom})),
    )
    assert blocked is not None
    assert blocked.blocked_code == "CALLER_REQUEST_TAMPER_BLOCKED"


def test_injection_task174_keeps_result_hash_blocked() -> None:
    base = admit_full_live_mesh_evidence(ROOT, candidate_id=CANDIDATE_B_ID)
    t174 = base.request.task174_result
    tube_dp = t174.modeled_total_tube_side_pressure_drop_pa + Decimal("1")
    bad = t174.model_copy(update={"modeled_total_tube_side_pressure_drop_pa": tube_dp})
    _, blocked = enforce_live_rating_authority_gates(
        ROOT, _tampered_chain_request(base.request.model_copy(update={"task174_result": bad}))
    )
    assert blocked is not None
    assert blocked.blocked_code in (
        "CALLER_REQUEST_TAMPER_BLOCKED",
        "CALLER_TASK174_BINDING_TAMPER_BLOCKED",
    )


def test_sizing_requirement_model_copy_canonical_hash_bypass_blocked() -> None:
    compact, _ = load_verified_live_compact_from_r19_audit(ROOT)
    bypass_data = REQ.model_dump()
    bypass_data["required_duty_w"] = Decimal("1")
    bypass = SizingRequirementAuthority.model_construct(**bypass_data)
    outcome = experimental_sizing_rating_adapter(ROOT, compact, bypass)
    assert outcome.status == "BLOCKED"
    assert outcome.blocked_code == "SIZING_REQUIREMENT_CANONICAL_HASH_MISMATCH"


def test_sizing_tube_dp_limit_blocked() -> None:
    compact, _ = load_verified_live_compact_from_r19_audit(ROOT)
    tight = scer.second_candidate_experimental_sizing_requirement(max_tube_dp_pa="1")
    outcome = experimental_sizing_rating_adapter(ROOT, compact, tight)
    assert outcome.status == "BLOCKED"
    assert "TUBE_DP_ABOVE_MAXIMUM" in outcome.blocked_diagnostics


def test_sizing_shell_dp_limit_blocked() -> None:
    compact, _ = load_verified_live_compact_from_r19_audit(ROOT)
    tight = scer.second_candidate_experimental_sizing_requirement(max_shell_dp_pa="1")
    outcome = experimental_sizing_rating_adapter(ROOT, compact, tight)
    assert outcome.status == "BLOCKED"
    assert "SHELL_DP_ABOVE_MAXIMUM" in outcome.blocked_diagnostics


def test_compact_engineering_rehash_tamper_blocked() -> None:
    compact, _ = load_verified_live_compact_from_r19_audit(ROOT)
    tampered = compact.model_copy(update={"minimum_approach_temperature_k": Decimal("1")})
    digest = live_compact_rating_hash(tampered)
    rebinding = tampered.model_copy(update={"compact_result_hash": digest})
    outcome = experimental_sizing_rating_adapter(ROOT, rebinding, REQ)
    assert outcome.status == "BLOCKED"
