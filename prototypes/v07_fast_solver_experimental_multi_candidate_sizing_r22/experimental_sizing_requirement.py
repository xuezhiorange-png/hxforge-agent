"""Versioned experimental multi-candidate sizing requirement (frozen Q13 space)."""

from __future__ import annotations

from decimal import Decimal

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task173_integrated_sizing.models import (
    SizingRequirementAuthority,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.r22_pinned_identity import (
    FROZEN_Q13_CANDIDATE_SPACE_HASH,
    TASK168_CANDIDATE_SPACE_AUTHORITY_ID,
)

_REQUIREMENT_ID = "V07-R22-EXPERIMENTAL-MULTI-CANDIDATE-SIZING-REQ-R1"
_AUTHORITY_VERSION = "experimental-r22-v1"


def experimental_multi_candidate_sizing_requirement(
    *,
    required_duty_w: str = "50000",
    max_tube_dp_pa: str = "1000",
    max_shell_dp_pa: str = "5000",
) -> SizingRequirementAuthority:
    projection = {
        "requirement_id": _REQUIREMENT_ID,
        "authority_version": _AUTHORITY_VERSION,
        "source_class": "EXPERIMENTAL_MULTI_CANDIDATE_SIZING",
        "source_id": "V07_FAST_SOLVER_EXPERIMENTAL_MULTI_CANDIDATE_SIZING_R22",
        "source_revision": "r22-20261019",
        "approval_status": "APPROVED",
        "evidence_refs": (
            "docs/tasks/evidence/V07-FAST-SOLVER-live-rating-result-r19-20261018T114658Z/",
            "docs/tasks/evidence/V07-FAST-SOLVER-general-candidate-continuation-r21e-20261019T111947Z/",
            "docs/tasks/evidence/TASK-173-v0.7-task174-native-bell-canonical-reduction-parity-and-enclosure-qualification-resume-r1.json",
        ),
        "provenance_refs": ("prototypes/v07_fast_solver_experimental_multi_candidate_sizing_r22/",),
        "required_duty_w": required_duty_w,
        "max_tube_dp_pa": max_tube_dp_pa,
        "max_shell_dp_pa": max_shell_dp_pa,
        "allowed_construction_families": ("FIXED_TUBESHEET",),
        "required_screening_policy_id": "V07-T173-SIZING-MANDATORY-SCREENING-R1",
        "discrete_candidate_authority_ids_and_hashes": (
            (TASK168_CANDIDATE_SPACE_AUTHORITY_ID, FROZEN_Q13_CANDIDATE_SPACE_HASH),
        ),
    }
    scalar_keys = ("required_duty_w", "max_tube_dp_pa", "max_shell_dp_pa")
    base_fields = {k: v for k, v in projection.items() if k not in scalar_keys}
    return SizingRequirementAuthority(
        **base_fields,
        required_duty_w=Decimal(required_duty_w),
        max_tube_dp_pa=Decimal(max_tube_dp_pa),
        max_shell_dp_pa=Decimal(max_shell_dp_pa),
        canonical_hash=canonical_sha256(projection),
    )
