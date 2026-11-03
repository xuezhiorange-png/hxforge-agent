"""Task167/FIV rule-pack authority intake (read-only, no numeric limit fabrication)."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any

from hexagent.exchangers.shell_tube.engineering_screening.authority import (
    FIV_NUMERIC_LIMIT_AUTHORITY_AVAILABLE,
    SOURCE_TASK020_RULE_PACK,
)


def fiv_authority_intake_report() -> dict[str, Any]:
    """Document what exists in-repo vs what is required for mandatory FIV screening."""
    return {
        "schema_version": "task167.fiv-authority-intake-report.v1",
        "fiv_numeric_limit_authority_available_constant": FIV_NUMERIC_LIMIT_AUTHORITY_AVAILABLE,
        "task167_rule_pack_source_found": True,
        "task167_rule_pack_source_id": SOURCE_TASK020_RULE_PACK,
        "approved_rule_pack_authority_id": "TASK012_TASK020_EVALUATED_RULE_PACK_AUTHORITY",
        "task167_rule_pack_approved_for_configuration_rules": True,
        "fiv_numeric_limit_authority": "MISSING",
        "fiv_applicability_verified": False,
        "distinction": (
            "Task012/020 approved rule pack governs configuration and qualitative screening; "
            "it does not supply approved critical-velocity numeric limits for FIV."
        ),
        "missing_for_fiv_numeric_screening": [
            "Approved FIV numeric limit coefficients with validity envelope",
            "Tube layout / span / support applicability binding on live rating requests",
            "Task167 approved_rule_pack_authority on R19/R21E frozen snapshots",
            "Licensed engineering sign-off for production numeric limits",
        ],
        "engineering_owner_approval_required": [
            "Authorize FIV numeric limit rule pack version and applicability envelope",
            "Bind Task167 screening bundle to live rating admission without mutating R19/R21E goldens",
            "Re-execute mandatory screening under Task173 policy after authority binding",
        ],
        "mandatory_screening_complete": False,
        "production_recommendation_authorized": False,
        "supplemental_screening_evidence_allowed": False,
        "authority_intake_status": "FIV_AUTHORITY_MISSING",
    }
