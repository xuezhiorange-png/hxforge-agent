"""TASK-015 governance test factories.

Builds deterministic, valid spec data for use across the test suite.
The factories pre-compute ``content_hash`` from the rest of the spec
(Section 9.2 — the hash is the primary identity of the spec at a
given moment).
"""

from __future__ import annotations

from typing import Any

from hexagent.governance.spec_validator import _spec_for_hash, compute_content_hash

FIXED_UPDATED_AT = "2026-07-05T07:00:00Z"


def _stamp(data: dict[str, Any]) -> dict[str, Any]:
    """Stamp ``content_hash`` from the rest of the spec."""
    out = dict(data)
    out["content_hash"] = compute_content_hash(_spec_for_hash(out))
    return out


def build_ci_pipeline_spec(
    *,
    canonical_name: str = "ci-pipeline",
    updated_at: str = FIXED_UPDATED_AT,
    failure_modes: list[str] | None = None,
    jobs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return _stamp(
        {
            "schema_version": 1,
            "owner": "xuezhiorange-png",
            "updated_at": updated_at,
            "canonical_name": canonical_name,
            "failure_modes": list(failure_modes or []),
            "jobs": list(jobs or []),
            "required_status_checks": [
                "task-015/ci-pipeline/blockers",
                "task-015/ci-pipeline/warnings",
            ],
        }
    )


def build_security_gate_spec(
    *,
    gate_id: str = "security-gate",
    updated_at: str = FIXED_UPDATED_AT,
    failure_modes: list[str] | None = None,
    gates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return _stamp(
        {
            "schema_version": 1,
            "owner": "xuezhiorange-png",
            "updated_at": updated_at,
            "gate_id": gate_id,
            "failure_modes": list(failure_modes or []),
            "gates": list(gates or []),
            "restricted_source_categories": [
                "standard_body",
                "vendor_catalog_body",
                "paid_price_list",
                "restricted_property_table",
                "scanned_page",
                "formula_image",
                "copied_standard_table",
            ],
            "required_status_checks": [
                "task-015/security-gate/blockers",
                "task-015/security-gate/restricted-content",
            ],
        }
    )


def build_release_spec(
    *,
    release_channel: str = "stable",
    updated_at: str = FIXED_UPDATED_AT,
    failure_modes: list[str] | None = None,
    channels: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return _stamp(
        {
            "schema_version": 1,
            "owner": "xuezhiorange-png",
            "updated_at": updated_at,
            "release_channel": release_channel,
            "failure_modes": list(failure_modes or []),
            "channels": list(channels or []),
            "release_gate": {
                "require_content_hash_stability": True,
                "require_frozen_contract_reference": True,
                "frozen_contract_references": [
                    "task_011_frozen_contract",
                    "task_012_frozen_contract",
                    "task_013_frozen_contract",
                    "task_014_frozen_contract",
                    "task_015_frozen_contract",
                ],
            },
            "required_status_checks": [
                "task-015/release/blockers",
                "task-015/release/gate",
            ],
        }
    )


def build_failure_taxonomy_spec(
    *,
    updated_at: str = FIXED_UPDATED_AT,
    failure_modes: list[str] | None = None,
) -> dict[str, Any]:
    modes = list(
        failure_modes
        if failure_modes is not None
        else ["transient", "non_transient", "manual_intervention"]
    )
    return _stamp(
        {
            "schema_version": 1,
            "owner": "xuezhiorange-png",
            "updated_at": updated_at,
            "failure_modes": modes,
            "classification_rules": {
                "transient": {
                    "description": "re-run likely to succeed",
                    "severity": "warning",
                    "retry": "auto",
                },
                "non_transient": {
                    "description": "re-run unlikely to succeed",
                    "severity": "blocker",
                    "retry": "none",
                },
                "manual_intervention": {
                    "description": "human action required",
                    "severity": "blocker",
                    "retry": "none",
                },
            },
            "required_status_checks": [
                "task-015/failure-taxonomy/classification",
            ],
        }
    )


__all__ = [
    "FIXED_UPDATED_AT",
    "build_ci_pipeline_spec",
    "build_failure_taxonomy_spec",
    "build_release_spec",
    "build_security_gate_spec",
]
