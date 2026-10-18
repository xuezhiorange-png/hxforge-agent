"""Experimental sizing requirement for Candidate B live-rating adapter validation."""

from __future__ import annotations

from decimal import Decimal

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task173_integrated_sizing.models import (
    SizingRequirementAuthority,
)

_EXPERIMENTAL_REQUIREMENT_ID = "V07-R20-CANDIDATE-B-LIVE-RATING-ADAPTER-REQ-R1"
_PLACEHOLDER_CANDIDATE_SPACE_HASH = (
    "0000000000000000000000000000000000000000000000000000000000000000"
)


def candidate_b_experimental_sizing_requirement() -> SizingRequirementAuthority:
    """Duty/DP limits aligned with Candidate B live snapshot (not production approval)."""
    projection = {
        "requirement_id": _EXPERIMENTAL_REQUIREMENT_ID,
        "authority_version": "experimental-r20-v1",
        "source_class": "LIVE_RATING_ADAPTER_VALIDATION",
        "source_id": "V07_FAST_SOLVER_RATING_SIZING_BRIDGE_R20",
        "source_revision": "r20-20261018",
        "approval_status": "APPROVED",
        "evidence_refs": (
            "docs/tasks/evidence/V07-FAST-SOLVER-live-rating-result-r19-20261018T114658Z/"
            "FULL_LIVE_RATING.json",
        ),
        "provenance_refs": ("prototypes/v07_fast_solver_rating_sizing_bridge_r20/",),
        "required_duty_w": "50000",
        "max_tube_dp_pa": "1000",
        "max_shell_dp_pa": "5000",
        "allowed_construction_families": ("FIXED_TUBESHEET",),
        "required_screening_policy_id": "V07-T173-SIZING-MANDATORY-SCREENING-R1",
        "discrete_candidate_authority_ids_and_hashes": (
            ("V07-T168-CANDIDATE-SPACE-R2", _PLACEHOLDER_CANDIDATE_SPACE_HASH),
        ),
    }
    scalar_keys = ("required_duty_w", "max_tube_dp_pa", "max_shell_dp_pa")
    base_fields = {k: v for k, v in projection.items() if k not in scalar_keys}
    return SizingRequirementAuthority(
        **base_fields,
        required_duty_w=Decimal("50000"),
        max_tube_dp_pa=Decimal("1000"),
        max_shell_dp_pa=Decimal("5000"),
        canonical_hash=canonical_sha256(projection),
    )
