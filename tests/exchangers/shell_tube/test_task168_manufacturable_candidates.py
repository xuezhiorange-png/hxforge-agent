"""Targeted TASK-168 authority, enumeration, and identity tests."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, getcontext, localcontext
from typing import Any

from hexagent.exchangers.shell_tube import validate_request as validate_task020
from hexagent.exchangers.shell_tube.manufacturable_candidates import validate_request
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    discrete_authority_hash,
    requirement_authority_hash,
    shell_catalog_hash,
    shell_record_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.errors import BlockerCode
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import (
    TASK168_SCHEMA_VERSION,
    TASK168_SOURCE_DEFINITION_ID,
    TASK168_VERSION,
    CandidateStatus,
    DiscreteAuthoritySource,
    DiscreteCandidateSetAuthority,
    DiscreteDimensionRole,
    Task168Request,
    Task168RequirementAuthority,
    ValidationStatus,
)
from hexagent.exchangers.shell_tube.models import ConstructionFamily, ShellAndTubeConfiguration
from hexagent.shell_geometry_catalogs.models import (
    PROFILE_ID,
    RECORD_SCHEMA_VERSION,
    SOURCE_CLASS_PUBLIC_DOMAIN,
    ShellGeometryCatalog,
    ShellGeometryRecord,
    ShellSourceBinding,
)


def _configuration() -> ShellAndTubeConfiguration:
    raw = {
        "schema_version": "task020.configuration-request.v1",
        "case_authority": {
            "revision_id": "rev-task168",
            "payload_hash": "a" * 64,
            "domain_snapshot_hash": "b" * 64,
            "status": "committed",
        },
        "equipment_family": "SHELL_AND_TUBE",
        "authority_mode": "INTERNAL_GENERIC",
        "construction_family": "FIXED_TUBESHEET",
        "orientation": "HORIZONTAL",
        "shell_pass_count": 1,
        "tube_pass_count": 1,
        "front_head_token": "FRONT",
        "shell_token": "SHELL",
        "rear_head_token": "REAR",
        "standard_system_id": None,
        "requested_rule_pack_identity": None,
        "evidence_refs": ["task168-config"],
    }
    outcome = validate_task020(raw)
    assert outcome.configuration is not None, outcome
    return outcome.configuration


def _shell_catalog() -> ShellGeometryCatalog:
    binding = ShellSourceBinding(
        source_id="task023-test-source",
        source_type=SOURCE_CLASS_PUBLIC_DOMAIN,
        source_revision="v1",
        source_location="test://task023/shell",
        evidence_ref="task023-shell-evidence",
        approved_by="task168-test",
        approved_at="2026-01-01",
    )
    record = ShellGeometryRecord(
        schema_version=RECORD_SCHEMA_VERSION,
        geometry_id="shell-1",
        geometry_type="shell",
        profile_id=PROFILE_ID,
        revision="r1",
        approval_state="approved",
        shell_inside_diameter_m="0.8",
        nominal_label="test-shell",
        source_class=SOURCE_CLASS_PUBLIC_DOMAIN,
        license_evidence={},
        source_binding=binding,
        permission_evidence_refs=("permission-task168",),
        provenance_edge_ids=("edge-task168",),
        evidence_refs=("evidence-task168",),
        record_hash="",
    )
    record = replace(record, record_hash=shell_record_hash(record))
    catalog = ShellGeometryCatalog(
        schema_version="task023.approved-shell-geometry-catalog.v1",
        catalog_id="task023-test-catalog",
        catalog_version="v1",
        profile_id=PROFILE_ID,
        authority="TASK023_TEST_AUTHORITY",
        source_revision="v1",
        records=(record,),
        evidence_bundle_hash="c" * 64,
        catalog_hash="",
        effective_at=None,
    )
    return replace(catalog, catalog_hash=shell_catalog_hash(catalog))


def _authority(role: DiscreteDimensionRole, value: object) -> DiscreteCandidateSetAuthority:
    authority = DiscreteCandidateSetAuthority(
        authority_id=f"task168-{role.value.lower()}",
        authority_version="v1",
        dimension_role=role,
        source_class=DiscreteAuthoritySource.AUTHORIZED_PROJECT_DEFINED_DISCRETE_SET,
        source_id="task168-project-snapshot",
        source_revision="v1",
        approval_status="APPROVED",
        values=(value,),
        evidence_refs=(f"evidence-{role.value.lower()}",),
        provenance_refs=(f"provenance-{role.value.lower()}",),
        canonical_hash="",
    )
    return replace(authority, canonical_hash=discrete_authority_hash(authority))


def _request(**overrides: Any) -> Task168Request:
    requirement = Task168RequirementAuthority(
        requirement_id="task168-requirement",
        authority_version="v1",
        source_class="PROJECT_REQUIREMENT",
        source_id="task168-requirement-source",
        approval_status="APPROVED",
        allowed_construction_families=(ConstructionFamily.FIXED_TUBESHEET,),
        evidence_refs=("requirement-evidence",),
        provenance_refs=("requirement-provenance",),
        canonical_hash="",
    )
    requirement = replace(requirement, canonical_hash=requirement_authority_hash(requirement))
    authorities = (
        _authority(DiscreteDimensionRole.CONSTRUCTION_FAMILY, ConstructionFamily.FIXED_TUBESHEET),
        _authority(DiscreteDimensionRole.TUBE_OUTER_DIAMETER, Decimal("0.019")),
        _authority(DiscreteDimensionRole.TUBE_WALL_THICKNESS, Decimal("0.001")),
        _authority(DiscreteDimensionRole.TUBE_LENGTH, Decimal("3")),
        _authority(DiscreteDimensionRole.TUBE_PITCH, Decimal("0.025")),
        _authority(DiscreteDimensionRole.TUBE_LAYOUT, "LAYOUT_30_DEG"),
        _authority(DiscreteDimensionRole.TUBE_PASS_COUNT, 1),
        _authority(DiscreteDimensionRole.BAFFLE_TYPE, "SINGLE_SEGMENTAL"),
        _authority(DiscreteDimensionRole.BAFFLE_CUT, Decimal("0.25")),
        _authority(DiscreteDimensionRole.BAFFLE_SPACING, Decimal("0.3")),
        _authority(DiscreteDimensionRole.BAFFLE_COUNT, 4),
    )
    value = Task168Request(
        schema_version=TASK168_SCHEMA_VERSION,
        task168_version=TASK168_VERSION,
        source_definition_id=TASK168_SOURCE_DEFINITION_ID,
        task020_configuration=_configuration(),
        requirement_authority=requirement,
        shell_geometry_catalog=_shell_catalog(),
        discrete_candidate_set_authorities=authorities,
        candidate_evaluations=(),
        request_metadata=(("alpha", "1"), ("zeta", "2")),
    )
    return replace(value, **overrides)


def _codes(outcome: object) -> set[str]:
    branch = getattr(outcome, "typed_blocked", None) or getattr(
        outcome, "raw_boundary_blocked", None
    )
    return set() if branch is None else {item.code for item in branch.blockers}


def test_exact_discrete_enumeration_retains_missing_evaluation_as_audited_block() -> None:
    outcome = validate_request(_request())
    assert outcome.status is ValidationStatus.VALID
    assert outcome.valid is not None
    assert outcome.valid.total_theoretical_combinations == 1
    assert outcome.valid.total_enumerated_candidates == 1
    assert outcome.valid.blocked_count == 1
    assert outcome.valid.candidate_records[0].status is CandidateStatus.BLOCKED
    assert outcome.valid.candidate_records[0].disposition.value == "BLOCKED"
    assert any(
        blocker.code == BlockerCode.EVALUATION_AUTHORITY_REQUIRED.value
        for blocker in outcome.valid.candidate_records[0].blockers
    )
    assert outcome.valid.provenance.cycle_count == 0
    assert outcome.valid.provenance.self_edge_count == 0


def test_same_semantic_request_replays_exact_identity_under_ambient_decimal_context() -> None:
    first = validate_request(_request())
    assert first.valid is not None
    original_precision = getcontext().prec
    try:
        with localcontext() as context:
            context.prec = 7
            second = validate_request(_request())
        assert second.valid is not None
        assert first.valid.result_hash == second.valid.result_hash
        assert first.valid.result_id == second.valid.result_id
        assert [item.candidate_id for item in first.valid.candidate_records] == [
            item.candidate_id for item in second.valid.candidate_records
        ]
    finally:
        getcontext().prec = original_precision


def test_tampered_discrete_authority_hash_blocks_before_enumeration() -> None:
    request = _request()
    tampered = replace(
        request.discrete_candidate_set_authorities[0],
        canonical_hash="0" * 64,
    )
    outcome = validate_request(
        replace(
            request,
            discrete_candidate_set_authorities=(
                tampered,
                *request.discrete_candidate_set_authorities[1:],
            ),
        )
    )
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.DISCRETE_AUTHORITY_HASH_MISMATCH.value in _codes(outcome)


def test_unsupported_raw_object_never_invokes_repr_or_str() -> None:
    class Explosive:
        def __repr__(self) -> str:
            raise AssertionError("repr must not run")

        def __str__(self) -> str:
            raise AssertionError("str must not run")

    outcome = validate_request(Explosive())
    assert outcome.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert BlockerCode.UNSUPPORTED_RAW_VALUE.value in _codes(outcome)


def test_raw_unicode_surrogate_is_fail_closed() -> None:
    outcome = validate_request({"bad": "\ud800"})
    assert outcome.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert BlockerCode.RAW_UNICODE_ENCODING_FAILURE.value in _codes(outcome)


def test_no_psi_n_or_ranking_surface_is_exposed() -> None:
    import hexagent.exchangers.shell_tube.manufacturable_candidates as package

    assert package.__all__ == ("validate_request",)
    assert not hasattr(package, "candidate_score")
    assert not hasattr(package, "recommended_candidate_id")
