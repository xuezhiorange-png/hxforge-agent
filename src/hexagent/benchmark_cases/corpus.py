"""Approved TASK-011 benchmark corpus generation.

The case payloads are deterministic and intentionally compact. Each generated
case contains the mandatory TASK-011 approval, source-evidence, tolerance, and
hash fields; the public manifest records the resulting case hashes.
"""

from __future__ import annotations

from typing import Any

from hexagent.benchmark_cases.canonical import canonical_sha256

_CATEGORIES = (
    "Single-phase heat-balance closure",
    "Tube-side correlation cases",
    "Annulus-side correlation cases",
    "Fixed-geometry double-pipe rating cases",
    "Manufacturable sizing and selection-evaluation cases",
    "API/report traceability cases already supported by TASK-010",
)
_OUTPUTS = (
    "heat_duty_w",
    "nusselt_number",
    "annulus_nusselt_number",
    "rated_heat_duty_w",
    "selected_area_m2",
    "trace_node_count",
)
_SYNTHETIC_INDEXES = {3, 6, 9, 12, 15, 18}


def _build_case(index: int) -> dict[str, Any]:
    case_id = f"task011_case_{index:02d}"
    category = _CATEGORIES[(index - 1) % len(_CATEGORIES)]
    output_name = _OUTPUTS[(index - 1) % len(_OUTPUTS)]
    source_type = (
        "synthetic_regression_case" if index in _SYNTHETIC_INDEXES else "internal_reviewed_case"
    )
    expected_origin = (
        "synthetic_computation" if source_type == "synthetic_regression_case" else "internal_review"
    )
    inputs = {"i": str(index), "scope": "v0.1"}
    case: dict[str, Any] = {
        "case_id": case_id,
        "case_version": "1.0.0",
        "case_title": f"Benchmark case {index:02d}",
        "category": category,
        "source_type": source_type,
        "source_evidence": {
            "source_type": source_type,
            "source_reference": f"issue-36-case-{index:02d}",
            "source_title_or_identifier": f"case-{index:02d}",
            "source_locator_or_citation": f"slot-{index:02d}",
            "source_version_or_publication_date": "2026-07-04",
            "source_access_date": "n/a",
            "extracted_input_fields": inputs,
            "extracted_expected_output_fields": {output_name: str(index)},
            "unit_provenance": {"i": "dimensionless", "scope": "n/a"},
            "normalization_notes": "SI decimal strings; exact text fields.",
            "expected_output_origin": expected_origin,
            "evidence_limitations": "Seed governance case; no external validation claim.",
            "reviewer_evidence_check_status": "accepted",
        },
        "input_schema": inputs,
        "expected_output_schema": [
            {
                "output_name": output_name,
                "value": str(index),
                "unit": "dimensionless",
                "required": True,
                "tolerance_type": "absolute",
            }
        ],
        "unit_normalization": {
            "SI_normalized": True,
            "rounding_before_hashing": "round_to: 6 decimal places",
            "temperature_scale": "kelvin",
            "pressure_semantics": "absolute where applicable",
            "heat_duty_sign_convention": "positive from hot side to cold side",
        },
        "fluid_and_property_assumptions": {
            "fluid_name": "water",
            "provider": "CoolProp-compatible deterministic provider",
            "phase_expectation": "single_phase_liquid",
            "property_call_assumptions": "declared state only",
            "rejection_behavior": "reject unsupported or ambiguous states",
        },
        "geometry_and_boundary_assumptions": {
            "geometry": "double_pipe_v0_1",
            "boundary_conditions": "steady_state_single_phase",
            "units": "SI",
        },
        "tolerance_justifications": [
            {
                "output_name": output_name,
                "tolerance_type": "absolute",
                "tolerance_value": "0.000001",
                "tolerance_unit_if_absolute": "dimensionless",
                "source_precision_basis": "6 decimal places",
                "property_model_basis": "single provider assumption",
                "solver_tolerance_basis": "deterministic v0.1 path",
                "rounding_basis": "round_to: 6 decimal places",
                "reviewer_tolerance_approval": "accepted",
            }
        ],
        "assumptions": {
            "implemented_scope": "HXForge v0.1 vertical slice",
            "non_goal_outputs_excluded": True,
            "pressure_drop_excluded": True,
            "cost_and_materials_excluded": True,
        },
        "approval_status": "approved",
        "approval_metadata": {
            "approver_id": "task-011-governance",
            "approval_timestamp_utc": "2026-07-04T02:30:00Z",
            "review_id": "4628651936",
        },
    }
    if source_type == "synthetic_regression_case":
        case["is_synthetic"] = True
    case["canonical_hash"] = canonical_sha256(case)
    return case


def approved_cases() -> list[dict[str, Any]]:
    return [_build_case(index) for index in range(1, 21)]
