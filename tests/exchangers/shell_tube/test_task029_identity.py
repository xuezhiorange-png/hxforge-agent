"""TASK-029 identity contract tests (I17): 10 frozen TEST_ID proofs."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

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
    canonicalize_blocked_result,
    canonicalize_composition_authority,
    canonicalize_ledger,
    canonicalize_member_authority,
    canonicalize_raw_boundary_blocked,
    canonicalize_request_projection,
    canonicalize_success_result,
    compute_blocked_result_hash,
    compute_composition_authority_hash,
    compute_raw_boundary_blocked_hash,
    compute_request_hash,
    compute_success_result_hash,
    derive_result_id,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029BlockedResult,
    Task029RawBoundaryBlockedResult,
    Task029SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.pipeline import (
    compute_task029_composition,
)
from tests.exchangers.shell_tube.task029_frozen_vectors import (
    INPUT_EVIDENCE_REFS,
    M000_MEMBER_AUTHORITY_FIXTURE,
    M001_MEMBER_AUTHORITY_FIXTURE,
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
    VECTOR_01_M000_HASH,
    VECTOR_01_M000_HASH_INPUT_LEN,
    VECTOR_02_M001_HASH,
    VECTOR_02_M001_HASH_INPUT_LEN,
    VECTOR_03_COMPOSITION_HASH,
    VECTOR_03_COMPOSITION_HASH_INPUT_LEN,
    VECTOR_04_REQUEST_HASH,
    VECTOR_04_REQUEST_HASH_INPUT_LEN,
    VECTOR_05_LEDGER_HASH,
    VECTOR_05_LEDGER_HASH_INPUT_LEN,
    VECTOR_06_SUCCESS_HASH_INPUT_LEN,
    VECTOR_06_SUCCESS_RESULT_HASH,
    VECTOR_06_SUCCESS_RESULT_ID,
    VECTOR_07_TYPED_BLOCKED_HASH_INPUT_LEN,
    VECTOR_07_TYPED_BLOCKED_RESULT_HASH,
    VECTOR_07_TYPED_BLOCKED_RESULT_ID,
    VECTOR_08_RAW_BOUNDARY_CANONICAL_LEN,
    VECTOR_08_RAW_BOUNDARY_CANONICAL_SHA256,
    copy_unknown_field_raw_request_fixture,
)
from tests.exchangers.shell_tube.test_task029_upstream import (
    build_oracle_ledger,
    build_oracle_success_result,
    build_production_fixtures,
    composition_to_raw_dict,
    member_from_fixture,
    task028_with_property_snapshot,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PY311_EXECUTABLE = Path(
    "/Users/charles/.local/share/uv/python/cpython-3.11-macos-aarch64-none/bin/python3.11"
)
_PY312_EXECUTABLE = Path(
    "/Users/charles/.local/share/uv/python/cpython-3.12-macos-aarch64-none/bin/python3.12"
)
_I18_PY311_EVIDENCE_DIR = Path("/tmp/task029-i18-py311")
_I18_PY312_EVIDENCE_DIR = Path("/tmp/task029-i18-py312")


def _vector_record(
    canonical_bytes: bytes,
    *,
    result_hash: str | None = None,
    result_id: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "canonical_bytes_hex": canonical_bytes.hex(),
        "canonical_len": len(canonical_bytes),
        "canonical_sha256": hashlib.sha256(canonical_bytes).hexdigest(),
    }
    if result_hash is not None:
        record["result_hash"] = result_hash
    if result_id is not None:
        record["result_id"] = result_id
    return record


def _collect_i18_vector_evidence() -> dict[str, Any]:
    """Collect frozen TASK-029 canonical byte evidence for all 8 oracle vectors."""
    fixtures = build_production_fixtures()
    m000 = member_from_fixture(M000_MEMBER_AUTHORITY_FIXTURE)
    m001 = member_from_fixture(M001_MEMBER_AUTHORITY_FIXTURE)
    oracle_success = build_oracle_success_result()
    success_hash = compute_success_result_hash(oracle_success)
    bad_t028 = task028_with_property_snapshot(fixtures, PROPERTY_SNAPSHOT_HASH_MISMATCH)
    typed_blocked = compute_task029_composition(
        composition_to_raw_dict(fixtures),
        task027_success_result=fixtures["task027"],
        task028_success_result=bad_t028,
        input_evidence_refs=INPUT_EVIDENCE_REFS,
    )
    if not isinstance(typed_blocked, Task029BlockedResult):
        msg = "expected typed blocked result for VECTOR_07"
        raise TypeError(msg)
    typed_blocked_hash = compute_blocked_result_hash(typed_blocked)
    raw_boundary_blocked = compute_task029_composition(
        copy_unknown_field_raw_request_fixture(),
        task027_success_result=fixtures["task027"],
        task028_success_result=fixtures["task028"],
        input_evidence_refs=INPUT_EVIDENCE_REFS,
    )
    if not isinstance(raw_boundary_blocked, Task029RawBoundaryBlockedResult):
        msg = "expected raw-boundary blocked result for VECTOR_08"
        raise TypeError(msg)
    return {
        "python_version": ".".join(str(part) for part in sys.version_info[:3]),
        "vectors": {
            "01": _vector_record(canonicalize_member_authority(m000)),
            "02": _vector_record(canonicalize_member_authority(m001)),
            "03": _vector_record(canonicalize_composition_authority(fixtures["composition"])),
            "04": _vector_record(
                canonicalize_request_projection(
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
            ),
            "05": _vector_record(canonicalize_ledger(build_oracle_ledger())),
            "06": _vector_record(
                canonicalize_success_result(oracle_success),
                result_hash=success_hash,
                result_id=derive_result_id(success_hash),
            ),
            "07": _vector_record(
                canonicalize_blocked_result(typed_blocked),
                result_hash=typed_blocked_hash,
                result_id=derive_result_id(typed_blocked_hash),
            ),
            "08": _vector_record(canonicalize_raw_boundary_blocked(raw_boundary_blocked)),
        },
    }


def _assert_frozen_i18_vector_evidence(evidence: dict[str, Any]) -> None:
    """Assert collected evidence matches I15 frozen oracle literals."""
    vectors = evidence["vectors"]
    expected = {
        "01": (VECTOR_01_M000_HASH_INPUT_LEN, VECTOR_01_M000_HASH),
        "02": (VECTOR_02_M001_HASH_INPUT_LEN, VECTOR_02_M001_HASH),
        "03": (VECTOR_03_COMPOSITION_HASH_INPUT_LEN, VECTOR_03_COMPOSITION_HASH),
        "04": (VECTOR_04_REQUEST_HASH_INPUT_LEN, VECTOR_04_REQUEST_HASH),
        "05": (VECTOR_05_LEDGER_HASH_INPUT_LEN, VECTOR_05_LEDGER_HASH),
        "06": (VECTOR_06_SUCCESS_HASH_INPUT_LEN, VECTOR_06_SUCCESS_RESULT_HASH),
        "07": (VECTOR_07_TYPED_BLOCKED_HASH_INPUT_LEN, VECTOR_07_TYPED_BLOCKED_RESULT_HASH),
        "08": (VECTOR_08_RAW_BOUNDARY_CANONICAL_LEN, VECTOR_08_RAW_BOUNDARY_CANONICAL_SHA256),
    }
    for vector_id, (expected_len, expected_hash) in expected.items():
        record = vectors[vector_id]
        assert record["canonical_len"] == expected_len
        assert record["canonical_sha256"] == expected_hash
        assert bytes.fromhex(record["canonical_bytes_hex"]) == bytes.fromhex(
            record["canonical_bytes_hex"]
        )
    assert vectors["06"]["result_hash"] == VECTOR_06_SUCCESS_RESULT_HASH
    assert vectors["06"]["result_id"] == VECTOR_06_SUCCESS_RESULT_ID
    assert vectors["07"]["result_hash"] == VECTOR_07_TYPED_BLOCKED_RESULT_HASH
    assert vectors["07"]["result_id"] == VECTOR_07_TYPED_BLOCKED_RESULT_ID


def _write_i18_evidence(path: Path, evidence: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, sort_keys=True), encoding="utf-8")


def _read_i18_evidence(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_i18_evidence_subprocess(python_executable: Path, output_path: Path) -> dict[str, Any]:
    env = os.environ.copy()
    repo_src = str(_REPO_ROOT / "src")
    repo_root = str(_REPO_ROOT)
    env["PYTHONPATH"] = f"{repo_src}:{repo_root}"
    command = (
        "import json, pathlib, sys;"
        f"sys.path[:0] = [{repo_src!r}, {repo_root!r}];"
        "from tests.exchangers.shell_tube.test_task029_identity import ("
        "_collect_i18_vector_evidence,"
        ");"
        "out = pathlib.Path(sys.argv[1]);"
        "out.parent.mkdir(parents=True, exist_ok=True);"
        "payload = json.dumps(_collect_i18_vector_evidence(), sort_keys=True);"
        "out.write_text(payload, encoding='utf-8')"
    )
    completed = subprocess.run(
        [str(python_executable), "-c", command, str(output_path)],
        cwd=_REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        msg = completed.stderr or completed.stdout or "subprocess evidence collection failed"
        raise RuntimeError(msg)
    return _read_i18_evidence(output_path)


def _assert_py311_py312_byte_identity(
    py311_evidence: dict[str, Any],
    py312_evidence: dict[str, Any],
) -> None:
    for vector_id in ("01", "02", "03", "04", "05", "06", "07", "08"):
        left = py311_evidence["vectors"][vector_id]
        right = py312_evidence["vectors"][vector_id]
        assert left["canonical_bytes_hex"] == right["canonical_bytes_hex"]
        assert left["canonical_len"] == right["canonical_len"]
        assert left["canonical_sha256"] == right["canonical_sha256"]
    assert (
        py311_evidence["vectors"]["06"]["result_hash"]
        == py312_evidence["vectors"]["06"]["result_hash"]
    )
    assert (
        py311_evidence["vectors"]["06"]["result_id"] == py312_evidence["vectors"]["06"]["result_id"]
    )
    assert (
        py311_evidence["vectors"]["07"]["result_hash"]
        == py312_evidence["vectors"]["07"]["result_hash"]
    )
    assert (
        py311_evidence["vectors"]["07"]["result_id"] == py312_evidence["vectors"]["07"]["result_id"]
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
    """Prove all 8 frozen oracle canonical bytes are byte-identical on py311 and py312."""
    import pytest

    if not _PY311_EXECUTABLE.is_file():
        pytest.fail("Python 3.11 runtime unavailable for I18 cross-version proof")
    if not _PY312_EXECUTABLE.is_file():
        pytest.fail("Python 3.12 runtime unavailable for I18 cross-version proof")

    current_evidence = _collect_i18_vector_evidence()
    _assert_frozen_i18_vector_evidence(current_evidence)
    repeat_evidence = _collect_i18_vector_evidence()
    assert repeat_evidence == current_evidence

    py311_path = _I18_PY311_EVIDENCE_DIR / "evidence.json"
    py312_path = _I18_PY312_EVIDENCE_DIR / "evidence.json"
    py311_evidence = _run_i18_evidence_subprocess(_PY311_EXECUTABLE, py311_path)
    py312_evidence = _run_i18_evidence_subprocess(_PY312_EXECUTABLE, py312_path)
    _assert_frozen_i18_vector_evidence(py311_evidence)
    _assert_frozen_i18_vector_evidence(py312_evidence)
    _assert_py311_py312_byte_identity(py311_evidence, py312_evidence)


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
