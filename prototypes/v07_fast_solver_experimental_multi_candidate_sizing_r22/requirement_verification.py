"""Independent sizing requirement canonical replay and trusted binding gates."""

# ruff: noqa: E501

from __future__ import annotations

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task173_integrated_sizing.models import (
    SizingRequirementAuthority,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_sizing_requirement import (
    experimental_multi_candidate_sizing_requirement,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.r22_pinned_identity import (
    FROZEN_Q13_CANDIDATE_SPACE_HASH,
    REQUIRED_SCREENING_POLICY_ID,
    REQUIREMENT_SCHEMA_CLASS,
    TASK168_CANDIDATE_SPACE_AUTHORITY_ID,
    TRUSTED_REQUIREMENT_AUTHORITY_VERSION,
    TRUSTED_REQUIREMENT_CANONICAL_HASH,
    TRUSTED_REQUIREMENT_ID,
    TRUSTED_REQUIREMENT_SOURCE_ID,
)


def requirement_canonical_projection(requirement: SizingRequirementAuthority) -> dict[str, object]:
    return requirement.model_dump(mode="json", exclude={"canonical_hash"})


def verify_requirement_canonical_hash(requirement: SizingRequirementAuthority) -> bool:
    return requirement.canonical_hash == canonical_sha256(requirement_canonical_projection(requirement))


def verify_requirement_schema_and_authority(requirement: SizingRequirementAuthority) -> str | None:
    if type(requirement) is not SizingRequirementAuthority:
        return "REQUIREMENT_SCHEMA_CLASS_MISMATCH"
    if REQUIREMENT_SCHEMA_CLASS != "SizingRequirementAuthority":
        return "REQUIREMENT_SCHEMA_CLASS_MISMATCH"
    if requirement.requirement_id != TRUSTED_REQUIREMENT_ID:
        return "REQUIREMENT_AUTHORITY_ID_MISMATCH"
    if requirement.authority_version != TRUSTED_REQUIREMENT_AUTHORITY_VERSION:
        return "REQUIREMENT_AUTHORITY_VERSION_MISMATCH"
    if requirement.source_id != TRUSTED_REQUIREMENT_SOURCE_ID:
        return "UNTRUSTED_REQUIREMENT_SOURCE"
    if requirement.required_screening_policy_id != REQUIRED_SCREENING_POLICY_ID:
        return "REQUIREMENT_SCREENING_POLICY_ID_MISMATCH"
    if len(requirement.discrete_candidate_authority_ids_and_hashes) != 1:
        return "REQUIREMENT_CANDIDATE_SPACE_BINDING_INVALID"
    authority_id, space_hash = requirement.discrete_candidate_authority_ids_and_hashes[0]
    if authority_id != TASK168_CANDIDATE_SPACE_AUTHORITY_ID:
        return "REQUIREMENT_CANDIDATE_SPACE_AUTHORITY_ID_MISMATCH"
    if space_hash != FROZEN_Q13_CANDIDATE_SPACE_HASH:
        return "REQUIREMENT_CANDIDATE_SPACE_HASH_MISMATCH"
    return None


def verify_trusted_requirement_binding(requirement: SizingRequirementAuthority) -> str | None:
    if not verify_requirement_canonical_hash(requirement):
        return "SIZING_REQUIREMENT_CANONICAL_HASH_MISMATCH"
    schema_code = verify_requirement_schema_and_authority(requirement)
    if schema_code is not None:
        return schema_code
    if requirement.canonical_hash != TRUSTED_REQUIREMENT_CANONICAL_HASH:
        return "UNTRUSTED_REQUIREMENT_CANONICAL_HASH"
    trusted = experimental_multi_candidate_sizing_requirement()
    trusted_projection = requirement_canonical_projection(trusted)
    actual_projection = requirement_canonical_projection(requirement)
    if actual_projection != trusted_projection:
        return "UNTRUSTED_REQUIREMENT_FIELD_BINDING"
    return None
