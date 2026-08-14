"""TASK-029 identity contract tests (I17): 10 frozen TEST_ID proofs."""

from __future__ import annotations

from dataclasses import replace

import pytest

from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.canonical import (
    BLOCKED_HASH_KIND_TAGS,
    BLOCKER_ENTRY_KIND_TAGS,
    COMPOSITION_AUTHORITY_HASH_KIND_TAGS,
    EXCLUSION_AUTHORITY_HASH_KIND_TAGS,
    LEDGER_EXCLUSION_KIND_TAGS,
    LEDGER_HASH_KIND_TAGS,
    LEDGER_MEMBER_KIND_TAGS,
    MEMBER_AUTHORITY_HASH_KIND_TAGS,
    PROVENANCE_KIND_TAGS,
    RAW_BOUNDARY_BLOCKED_KIND_TAGS,
    RAW_PROJECTION_KIND_TAGS,
    REQUEST_HASH_KIND_TAGS,
    SUCCESS_HASH_KIND_TAGS,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.identity import (
    compute_blocked_result_hash,
    compute_composition_authority_hash,
    compute_raw_boundary_blocked_hash,
    compute_request_hash,
    compute_success_result_hash,
    derive_result_id,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029BlockedResult,
    Task029SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.pipeline import (
    compute_task029_composition,
)
from tests.exchangers.shell_tube.task029_frozen_vectors import (
    INPUT_EVIDENCE_REFS,
    PROFILE_ID,
    PROPERTY_SNAPSHOT_HASH,
    PROPERTY_SNAPSHOT_HASH_MISMATCH,
    TASK025_HYDRAULIC_AUTHORITY_HASH,
    TASK025_RESULT_HASH,
    TASK026_RESULT_HASH,
    TASK027_RESULT_HASH,
    TASK028_RESULT_HASH,
    TASK029_REQUEST_SCHEMA_VERSION,
    TYPED_BLOCKED_FIXTURE,
    VECTOR_03_COMPOSITION_HASH,
    VECTOR_04_REQUEST_HASH,
    VECTOR_06_SUCCESS_RESULT_HASH,
    VECTOR_06_SUCCESS_RESULT_ID,
    VECTOR_07_TYPED_BLOCKED_RESULT_HASH,
    VECTOR_07_TYPED_BLOCKED_RESULT_ID,
    VECTOR_08_RAW_BOUNDARY_CANONICAL_SHA256,
    copy_unknown_field_raw_request_fixture,
)
from tests.exchangers.shell_tube.test_task029_upstream import (
    build_oracle_success_result,
    build_production_fixtures,
    composition_to_raw_dict,
    task028_with_property_snapshot,
)


def test_T029_ID_001_REQUEST_HASH_VECTOR() -> None:
    actual = compute_request_hash(
        schema_version=TASK029_REQUEST_SCHEMA_VERSION,
        profile_id=PROFILE_ID,
        task027_result_hash=TASK027_RESULT_HASH,
        task028_result_hash=TASK028_RESULT_HASH,
        task025_hydraulic_authority_hash=TASK025_HYDRAULIC_AUTHORITY_HASH,
        task025_result_hash=TASK025_RESULT_HASH,
        task026_result_hash=TASK026_RESULT_HASH,
        property_snapshot_hash=PROPERTY_SNAPSHOT_HASH,
        composition_authority_hash=VECTOR_03_COMPOSITION_HASH,
    )
    assert actual == VECTOR_04_REQUEST_HASH


def test_T029_ID_002_SUCCESS_HASH_VECTOR() -> None:
    oracle_success = build_oracle_success_result()
    actual = compute_success_result_hash(oracle_success)
    assert actual == VECTOR_06_SUCCESS_RESULT_HASH


def test_T029_ID_003_SUCCESS_UUID_VECTOR() -> None:
    oracle_success = build_oracle_success_result()
    actual = derive_result_id(compute_success_result_hash(oracle_success))
    assert actual == VECTOR_06_SUCCESS_RESULT_ID


def test_T029_ID_004_TYPED_BLOCKED_HASH_VECTOR() -> None:
    fixtures = build_production_fixtures()
    bad_t028 = task028_with_property_snapshot(fixtures, PROPERTY_SNAPSHOT_HASH_MISMATCH)
    result = compute_task029_composition(
        composition_to_raw_dict(fixtures),
        task027_success_result=fixtures["task027"],
        task028_success_result=bad_t028,
        input_evidence_refs=INPUT_EVIDENCE_REFS,
    )
    assert isinstance(result, Task029BlockedResult)
    actual = compute_blocked_result_hash(result)
    assert actual == VECTOR_07_TYPED_BLOCKED_RESULT_HASH


def test_T029_ID_005_TYPED_BLOCKED_UUID_VECTOR() -> None:
    fixtures = build_production_fixtures()
    bad_t028 = task028_with_property_snapshot(
        fixtures,
        TYPED_BLOCKED_FIXTURE["property_snapshot_hash"],
    )
    result = compute_task029_composition(
        composition_to_raw_dict(fixtures),
        task027_success_result=fixtures["task027"],
        task028_success_result=bad_t028,
        input_evidence_refs=INPUT_EVIDENCE_REFS,
    )
    assert isinstance(result, Task029BlockedResult)
    actual = derive_result_id(result.result_hash)
    assert actual == VECTOR_07_TYPED_BLOCKED_RESULT_ID


def test_T029_ID_006_RAW_BOUNDARY_SHA_VECTOR() -> None:
    fixtures = build_production_fixtures()
    raw = copy_unknown_field_raw_request_fixture()
    blocked = compute_task029_composition(
        raw,
        task027_success_result=fixtures["task027"],
        task028_success_result=fixtures["task028"],
        input_evidence_refs=INPUT_EVIDENCE_REFS,
    )
    actual = compute_raw_boundary_blocked_hash(blocked)
    assert actual == VECTOR_08_RAW_BOUNDARY_CANONICAL_SHA256


def test_T029_ID_007_PY311_PY312_BYTE_IDENTITY() -> None:
    pytest.skip(reason="I18 owns py311/py312 cross-version byte-identity execution")


def test_T029_ID_008_EXACT_KIND_TAG_MAPS() -> None:
    assert MEMBER_AUTHORITY_HASH_KIND_TAGS == (
        "STRING",
        "STRING",
        "INTEGER",
        "ENUM",
        "ENUM",
        "STRING",
        "ENUM",
        "STRING",
        "STRING",
        "STRING",
        "INTEGER",
        "TUPLE",
    )
    assert EXCLUSION_AUTHORITY_HASH_KIND_TAGS == (
        "STRING",
        "STRING",
        "STRING",
        "ENUM",
        "TUPLE",
    )
    assert COMPOSITION_AUTHORITY_HASH_KIND_TAGS == (
        "STRING",
        "STRING",
        "ENUM",
        "STRING",
        "STRING",
        "TUPLE",
        "TUPLE",
        "TUPLE",
    )
    assert REQUEST_HASH_KIND_TAGS == (
        "STRING",
        "STRING",
        "STRING",
        "STRING",
        "STRING",
        "STRING",
        "STRING",
        "STRING",
        "STRING",
    )
    assert len(LEDGER_MEMBER_KIND_TAGS) == 16
    assert len(LEDGER_EXCLUSION_KIND_TAGS) == 7
    assert len(LEDGER_HASH_KIND_TAGS) == 11
    assert len(SUCCESS_HASH_KIND_TAGS) == 16
    assert len(BLOCKED_HASH_KIND_TAGS) == 16
    assert len(PROVENANCE_KIND_TAGS) == 5
    assert len(BLOCKER_ENTRY_KIND_TAGS) == 4
    assert len(RAW_PROJECTION_KIND_TAGS) == 2
    assert len(RAW_BOUNDARY_BLOCKED_KIND_TAGS) == 6


def test_T029_ID_009_REPEAT_RUN_IDENTITY() -> None:
    fixtures = build_production_fixtures()
    raw = composition_to_raw_dict(fixtures)
    first = compute_task029_composition(
        raw,
        task027_success_result=fixtures["task027"],
        task028_success_result=fixtures["task028"],
        input_evidence_refs=INPUT_EVIDENCE_REFS,
    )
    second = compute_task029_composition(
        raw,
        task027_success_result=fixtures["task027"],
        task028_success_result=fixtures["task028"],
        input_evidence_refs=INPUT_EVIDENCE_REFS,
    )
    assert isinstance(first, Task029SuccessResult)
    assert isinstance(second, Task029SuccessResult)
    assert first.result_hash == second.result_hash
    assert first.result_id == second.result_id


def test_T029_ID_010_CALLER_PERMUTATION_REQUEST_IDENTITY() -> None:
    fixtures = build_production_fixtures()
    composition = fixtures["composition"]
    permuted = replace(
        composition,
        member_authorities=(composition.member_authorities[1], composition.member_authorities[0]),
    )
    hash_a = compute_composition_authority_hash(composition)
    hash_b = compute_composition_authority_hash(permuted)
    assert hash_a == hash_b == VECTOR_03_COMPOSITION_HASH
    actual = compute_request_hash(
        schema_version=TASK029_REQUEST_SCHEMA_VERSION,
        profile_id=PROFILE_ID,
        task027_result_hash=TASK027_RESULT_HASH,
        task028_result_hash=TASK028_RESULT_HASH,
        task025_hydraulic_authority_hash=TASK025_HYDRAULIC_AUTHORITY_HASH,
        task025_result_hash=TASK025_RESULT_HASH,
        task026_result_hash=TASK026_RESULT_HASH,
        property_snapshot_hash=PROPERTY_SNAPSHOT_HASH,
        composition_authority_hash=hash_a,
    )
    assert actual == VECTOR_04_REQUEST_HASH
