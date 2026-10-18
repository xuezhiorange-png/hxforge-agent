"""R21 Phase A: deep request gate and sizing adapter fail-closed supplements."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_live_rating_result_r19.live_evidence_admission import (
    admit_full_live_mesh_evidence,
)
from prototypes.v07_fast_solver_live_rating_result_r19.live_rating_authority_gate import (
    enforce_live_rating_authority_gates,
)
from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task173_integrated_sizing.models import (
    SizingRequirementAuthority,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.candidate_b_sizing_requirement import (
    candidate_b_experimental_sizing_requirement,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_pinned_identity import (
    EXPERIMENTAL_CANDIDATE_SPACE_PLACEHOLDER,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.experimental_sizing_rating_adapter import (
    experimental_sizing_rating_adapter,
    load_verified_live_compact_from_r19_audit,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.live_compact_rating import (
    LiveCompactCandidateRating,
    live_compact_rating_hash,
)

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
REQ = candidate_b_experimental_sizing_requirement()


def _tight_requirement(**scalar_overrides: str) -> SizingRequirementAuthority:
    projection = {
        "requirement_id": "V07-R21-TIGHT-REQ-EXPERIMENTAL",
        "authority_version": "experimental-r21-v1",
        "source_class": "LIVE_RATING_ADAPTER_VALIDATION",
        "source_id": "V07_FAST_SOLVER_GENERAL_CANDIDATE_LIVE_RATING_R21",
        "source_revision": "r21-20261018",
        "approval_status": "APPROVED",
        "evidence_refs": ("prototypes/v07_fast_solver_rating_sizing_bridge_r20/",),
        "provenance_refs": ("prototypes/v07_fast_solver_rating_sizing_bridge_r20/",),
        "required_duty_w": "50000",
        "max_tube_dp_pa": "1000",
        "max_shell_dp_pa": "5000",
        "allowed_construction_families": ("FIXED_TUBESHEET",),
        "required_screening_policy_id": "V07-T173-SIZING-MANDATORY-SCREENING-R1",
        "discrete_candidate_authority_ids_and_hashes": (
            (
                "V07-T168-CANDIDATE-SPACE-EXPERIMENTAL-PLACEHOLDER-R20A",
                EXPERIMENTAL_CANDIDATE_SPACE_PLACEHOLDER,
            ),
        ),
    }
    projection.update(scalar_overrides)
    scalar_keys = ("required_duty_w", "max_tube_dp_pa", "max_shell_dp_pa")
    base_fields = {k: v for k, v in projection.items() if k not in scalar_keys}
    return SizingRequirementAuthority(
        **base_fields,
        required_duty_w=Decimal(projection["required_duty_w"]),
        max_tube_dp_pa=Decimal(projection["max_tube_dp_pa"]),
        max_shell_dp_pa=Decimal(projection["max_shell_dp_pa"]),
        canonical_hash=canonical_sha256(projection),
    )


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
    bad = t174.model_copy(
        update={"modeled_total_tube_side_pressure_drop_pa": t174.modeled_total_tube_side_pressure_drop_pa + Decimal("1")}
    )
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
    tight = _tight_requirement(max_tube_dp_pa="1")
    outcome = experimental_sizing_rating_adapter(ROOT, compact, tight)
    assert outcome.status == "BLOCKED"
    assert "TUBE_DP_ABOVE_MAXIMUM" in outcome.blocked_diagnostics


def test_sizing_shell_dp_limit_blocked() -> None:
    compact, _ = load_verified_live_compact_from_r19_audit(ROOT)
    tight = _tight_requirement(max_shell_dp_pa="1")
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
