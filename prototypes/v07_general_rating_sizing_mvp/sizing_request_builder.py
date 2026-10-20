"""Build Task173 sizing requests from general engineering cases."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import Task168Request
from hexagent.exchangers.shell_tube.task173_integrated_sizing import (
    SizingRequirementAuthority,
    Task173SizingRequest,
    sizing_request_hash,
)

from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV1

_MVP_SPACE_ID = "V07-GENERAL-RATING-SIZING-MVP-CANDIDATE-SPACE-R1"


def _task173_test_module():
    return import_module("tests.exchangers.shell_tube.test_task173_integrated_sizing")


def build_task173_sizing_request(case: GeneralEngineeringCaseV1) -> Task173SizingRequest:
    """Bind general case targets to the reviewed Task173 R2 validation candidate space."""
    t173_tests = _task173_test_module()
    lengths = case.candidate_constraints.tube_lengths_m[: case.solver_budget.max_candidates_to_rate]
    spacings = case.candidate_constraints.baffle_spacings_m
    base = t173_tests._sizing_request(
        tube_lengths=tuple(lengths),
        baffle_spacings=tuple(spacings),
        validation_space_r2=True,
    )
    requirement = base.requirement_authority
    requirement_projection: dict[str, Any] = {
        "requirement_id": requirement.requirement_id,
        "authority_version": requirement.authority_version,
        "source_class": requirement.source_class,
        "source_id": requirement.source_id,
        "source_revision": requirement.source_revision,
        "approval_status": requirement.approval_status,
        "evidence_refs": (
            *requirement.evidence_refs,
            f"GENERAL_MVP_CASE_ID::{case.engineering_case_id}",
        ),
        "provenance_refs": (
            *requirement.provenance_refs,
            "GENERAL_MVP_WORKFLOW_NOT_PRODUCTION_APPROVED",
        ),
        "required_duty_w": case.target_duty_w,
        "max_tube_dp_pa": case.max_tube_side_pressure_drop_pa,
        "max_shell_dp_pa": case.max_shell_side_pressure_drop_pa,
        "allowed_construction_families": requirement.allowed_construction_families,
        "required_screening_policy_id": requirement.required_screening_policy_id,
        "discrete_candidate_authority_ids_and_hashes": (
            requirement.discrete_candidate_authority_ids_and_hashes
        ),
    }
    requirement_hash_projection = {
        **requirement_projection,
        "required_duty_w": str(case.target_duty_w),
        "max_tube_dp_pa": str(case.max_tube_side_pressure_drop_pa),
        "max_shell_dp_pa": str(case.max_shell_side_pressure_drop_pa),
    }
    requirement = SizingRequirementAuthority(
        **requirement_projection,
        canonical_hash=canonical_sha256(requirement_hash_projection),
    )
    metadata = dict(base.request_metadata)
    metadata.update(
        {
            "workflow": "V07_GENERAL_RATING_SIZING_END_TO_END_MVP_R1",
            "engineering_case_id": case.engineering_case_id,
            "experimental_ranking": "true",
            "production_design_approved": "false",
            "golden_reuse": "false",
        }
    )
    return base.model_copy(
        update={
            "requirement_authority": requirement,
            "request_metadata": tuple(sorted(metadata.items(), key=lambda item: item[0])),
        }
    )


def build_task168_request(case: GeneralEngineeringCaseV1) -> Task168Request:
    return build_task173_sizing_request(case).task168_candidate_request


def sizing_request_identity(request: Task173SizingRequest) -> str:
    return sizing_request_hash(request)
