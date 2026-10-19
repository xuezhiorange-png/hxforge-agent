"""Versioned experimental sizing requirement for second-candidate general live rating."""

from __future__ import annotations

from decimal import Decimal

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task173_integrated_sizing.models import (
    SizingRequirementAuthority,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_pinned_identity import (
    EXPERIMENTAL_CANDIDATE_SPACE_PLACEHOLDER,
)

_REQUIREMENT_ID = "V07-R21B-SECOND-CANDIDATE-GENERAL-LIVE-RATING-REQ-R1-EXPERIMENTAL"
_AUTHORITY_VERSION = "experimental-r21b-v1"


def second_candidate_experimental_sizing_requirement(
    *,
    required_duty_w: str = "50000",
    max_tube_dp_pa: str = "1000",
    max_shell_dp_pa: str = "5000",
) -> SizingRequirementAuthority:
    projection = {
        "requirement_id": _REQUIREMENT_ID,
        "authority_version": _AUTHORITY_VERSION,
        "source_class": "GENERAL_LIVE_RATING_ADAPTER_VALIDATION",
        "source_id": "V07_FAST_SOLVER_GENERAL_CANDIDATE_CONTINUATION_R21B",
        "source_revision": "r21b-20261019",
        "approval_status": "APPROVED",
        "evidence_refs": (
            "docs/tasks/evidence/V07-FAST-SOLVER-general-candidate-live-rating-r21-20261018T162215Z/",
        ),
        "provenance_refs": (
            "prototypes/v07_fast_solver_general_candidate_live_rating_r21/",
        ),
        "required_duty_w": required_duty_w,
        "max_tube_dp_pa": max_tube_dp_pa,
        "max_shell_dp_pa": max_shell_dp_pa,
        "allowed_construction_families": ("FIXED_TUBESHEET",),
        "required_screening_policy_id": "V07-T173-SIZING-MANDATORY-SCREENING-R1",
        "discrete_candidate_authority_ids_and_hashes": (
            (
                "V07-T168-CANDIDATE-SPACE-EXPERIMENTAL-PLACEHOLDER-R20A",
                EXPERIMENTAL_CANDIDATE_SPACE_PLACEHOLDER,
            ),
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
