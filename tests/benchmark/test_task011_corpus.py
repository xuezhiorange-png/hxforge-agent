"""Pytest coverage for TASK-011 benchmark corpus contract §19.1 / §9.3.

Tests are written against the frozen design contract SHA
``7cfdb4f0989b6d384533c7a29e9a2156c731bd0f`` (see
``docs/tasks/TASK-011-frozen-contract-metadata.md``). Each test exercises a
specific §19.1 validation form or §9.3 transition row so that a regression
on any single clause surfaces as a deterministic test failure.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from hexagent.benchmark_cases.canonical import canonical_json_bytes, canonical_sha256
from hexagent.benchmark_cases.corpus import (
    APPROVED_CASES_COUNT,
    approved_cases,
    case_file_path,
    load_case,
)
from hexagent.benchmark_cases.transition import (
    all_transitions,
    has_transition,
    transition,
)
from hexagent.benchmark_cases.validation import (
    FORBIDDEN_OUTPUT_PREFIXES,
    REQUIRED_CASE_FIELDS,
    ValidationError,
    _class_specific_source_fields_present,
    _mandatory_source_fields_present,
    validate_corpus,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


# --- §19.1.5 + §19.1.1 + §17.4 — happy path ---------------------------------


def test_corpus_loads_twenty_approved_cases_from_artifacts() -> None:
    cases = approved_cases(_repo_root())
    assert len(cases) == APPROVED_CASES_COUNT
    assert {c["case_id"] for c in cases} == {f"task011_case_{index:02d}" for index in range(1, 21)}


def test_every_case_has_independent_artifact_file() -> None:
    root = _repo_root()
    for case_id in (f"task011_case_{index:02d}" for index in range(1, 21)):
        path = case_file_path(root, case_id)
        assert path.is_file(), f"missing artifact for {case_id}: {path}"


def test_validate_corpus_passes_for_clean_repository() -> None:
    """§19.1 — every validation form passes against the committed corpus."""
    validate_corpus(_repo_root())


# --- §19.1.3 — canonical hash integrity ------------------------------------


def test_corpus_recovers_when_one_case_artifact_is_tampered(tmp_path: Path) -> None:
    """Modifying any case file must break canonical hash verification (§17.4)."""
    root = _repo_root()
    # Copy corpus into a temp directory
    for sub in ("benchmarks/cases", "benchmarks/manifests"):
        src = root / sub
        dst = tmp_path / sub
        dst.mkdir(parents=True)
        for f in src.iterdir():
            (dst / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    # Tamper with one case
    target = tmp_path / "benchmarks" / "cases" / "task011_case_01.json"
    case = json.loads(target.read_text(encoding="utf-8"))
    case["case_title"] = case["case_title"] + " TAMPERED"
    target.write_text(json.dumps(case, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="canonical hash mismatch"):
        validate_corpus(tmp_path)


def test_manifest_must_reference_real_case_artifacts(tmp_path: Path) -> None:
    """§18 — case_ids must point to existing case files."""
    root = _repo_root()
    for sub in ("benchmarks/cases", "benchmarks/manifests"):
        src = root / sub
        dst = tmp_path / sub
        dst.mkdir(parents=True)
        for f in src.iterdir():
            (dst / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    # Remove one case artifact
    (tmp_path / "benchmarks" / "cases" / "task011_case_05.json").unlink()
    with pytest.raises(ValidationError, match="case artifact missing"):
        validate_corpus(tmp_path)


def test_synthetic_case_id_mismatch_is_rejected(tmp_path: Path) -> None:
    """§19.1.8 — synthetic_case_ids must equal the corpus synthetic set."""
    root = _repo_root()
    for sub in ("benchmarks/cases", "benchmarks/manifests"):
        src = root / sub
        dst = tmp_path / sub
        dst.mkdir(parents=True)
        for f in src.iterdir():
            (dst / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    manifest_path = tmp_path / "benchmarks" / "manifests" / "task-011-approved-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Drop one synthetic id from manifest
    manifest["synthetic_case_ids"] = [
        cid for cid in manifest["synthetic_case_ids"] if cid != "task011_case_03"
    ]
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValidationError, match="missing from synthetic_case_ids"):
        validate_corpus(tmp_path)


# --- §8 — mandatory fields --------------------------------------------------


def test_review_workflow_state_is_a_mandatory_case_field() -> None:
    """§8.12 / P0-3 — review_workflow_state must be in REQUIRED_CASE_FIELDS."""
    assert "review_workflow_state" in REQUIRED_CASE_FIELDS


def test_missing_review_workflow_state_is_rejected(tmp_path: Path) -> None:
    root = _repo_root()
    for sub in ("benchmarks/cases", "benchmarks/manifests"):
        src = root / sub
        dst = tmp_path / sub
        dst.mkdir(parents=True)
        for f in src.iterdir():
            (dst / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    target = tmp_path / "benchmarks" / "cases" / "task011_case_01.json"
    case = json.loads(target.read_text(encoding="utf-8"))
    del case["review_workflow_state"]
    # Recompute hash so we exercise the §17.4 path before §8 catches the field
    case["canonical_hash"] = canonical_sha256({**case, "canonical_hash": "<placeholder>"})
    target.write_text(json.dumps(case, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="missing required fields"):
        validate_corpus(tmp_path)


def test_approved_case_requires_review_workflow_state_approved(tmp_path: Path) -> None:
    """§16 — approval_status=approved implies review_workflow_state=approved."""
    root = _repo_root()
    for sub in ("benchmarks/cases", "benchmarks/manifests"):
        src = root / sub
        dst = tmp_path / sub
        dst.mkdir(parents=True)
        for f in src.iterdir():
            (dst / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    target = tmp_path / "benchmarks" / "cases" / "task011_case_01.json"
    case = json.loads(target.read_text(encoding="utf-8"))
    case["review_workflow_state"] = "under_review"
    case["canonical_hash"] = canonical_sha256({**case, "canonical_hash": "<placeholder>"})
    target.write_text(json.dumps(case, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(
        ValidationError, match="approval_status=approved requires review_workflow_state=approved"
    ):
        validate_corpus(tmp_path)


# --- §9 — source evidence ---------------------------------------------------


def test_internal_reviewed_case_requires_class_specific_fields() -> None:
    """§9.2.4 — author_identity, review_thread_reference, date, scope."""
    case = load_case(_repo_root(), "task011_case_01")
    source = copy.deepcopy(case["source_evidence"])
    source.pop("author_identity")
    ok, msg = _class_specific_source_fields_present(source, case["case_id"])
    assert ok is False
    assert "author_identity" in msg


def test_synthetic_regression_case_must_mark_not_independent_evidence() -> None:
    """§9.2.5 — is_independent_validation_evidence must be False."""
    case = load_case(_repo_root(), "task011_case_03")
    source = copy.deepcopy(case["source_evidence"])
    source["is_independent_validation_evidence"] = True
    ok, msg = _class_specific_source_fields_present(source, case["case_id"])
    assert ok is False
    assert "is_independent_validation_evidence" in msg


def test_universal_source_evidence_missing_is_detected() -> None:
    case = load_case(_repo_root(), "task011_case_01")
    source = copy.deepcopy(case["source_evidence"])
    source.pop("source_reference")
    assert _mandatory_source_fields_present(source, case["case_id"]) is False
    assert "source_reference" not in source


# --- §7 / §19.1.10 — forbidden output prefixes ------------------------------


def test_no_case_uses_forbidden_output_prefixes() -> None:
    for case in approved_cases(_repo_root()):
        for output in case["expected_output_schema"]:
            name = output["output_name"]
            assert not any(name.startswith(p) for p in FORBIDDEN_OUTPUT_PREFIXES), (
                f"{case['case_id']} has forbidden output {name}"
            )


# --- §9.3 — transition table ------------------------------------------------


def test_transition_table_covers_required_rows() -> None:
    """Every (stage, condition) pair the validator invokes MUST be a table row."""
    # §9.3.1 universal/class-specific × pre_approval / approval_attempt /
    # manifest_inclusion / ci_validation
    for stage in ("pre_approval", "approval_attempt", "manifest_inclusion", "ci_validation"):
        assert has_transition(stage, "universal_source_evidence_missing")
        assert has_transition(stage, "class_specific_source_evidence_missing")
    # §9.3.2 reviewer_status_* per stage
    for stage in ("pre_approval", "approval_attempt", "manifest_inclusion", "ci_validation"):
        assert has_transition(stage, "reviewer_status_pending")
        assert has_transition(stage, "reviewer_status_rejected")
    # §9.3.3 synthetic rules per stage
    for stage in ("pre_approval", "approval_attempt", "manifest_inclusion", "ci_validation"):
        assert has_transition(stage, "synthetic_marker_missing")
        assert has_transition(stage, "synthetic_cited_as_independent_evidence")


def test_transition_function_is_deterministic_and_pure() -> None:
    """§9.3.4 — invoking twice with identical inputs yields identical outputs."""
    for _ in range(2):
        assert (
            transition("pre_approval", "universal_source_evidence_missing", "draft")
            == "needs_source"
        )
        assert (
            transition("approval_attempt", "universal_source_evidence_missing", "draft")
            == "rejected"
        )
        assert (
            transition("manifest_inclusion", "universal_source_evidence_missing", "draft")
            == "rejected"
        )
        assert (
            transition("ci_validation", "universal_source_evidence_missing", "draft") == "rejected"
        )


def test_transition_table_verbatim_matches_contract_sections() -> None:
    """Encode §9.3.1 / §9.3.2 / §9.3.3 verbatim — see transition module docstring."""
    table = dict(((s, c), n) for s, c, n in all_transitions())
    assert table[("pre_approval", "universal_source_evidence_missing")] == "needs_source"
    assert table[("approval_attempt", "universal_source_evidence_missing")] == "rejected"
    assert table[("manifest_inclusion", "universal_source_evidence_missing")] == "rejected"
    assert table[("ci_validation", "universal_source_evidence_missing")] == "rejected"
    # §9.3.2
    assert table[("pre_approval", "reviewer_status_accepted")] == "under_review"
    assert table[("approval_attempt", "reviewer_status_accepted")] == "approved"
    # §9.3.3
    # The "any" stage in §9.3.3 is enumerated explicitly for each of the 4
    # lifecycle stages; verify all 4 rows resolve to "rejected".
    for stage in ("pre_approval", "approval_attempt", "manifest_inclusion", "ci_validation"):
        assert table[(stage, "synthetic_cited_as_independent_evidence")] == "rejected"
        assert table[(stage, "synthetic_marker_missing")] in {"needs_source", "rejected"}


# --- §17 — canonical JSON / RFC 8785 ---------------------------------------


def test_canonical_sha256_excludes_canonical_hash_field() -> None:
    """§17.1 — canonical_hash is excluded from the hash input."""
    a = {"case_id": "x", "canonical_hash": "AAAA"}
    b = {"case_id": "x", "canonical_hash": "BBBB"}
    assert canonical_sha256(a) == canonical_sha256(b)


def test_canonical_sha256_excludes_mutable_review_comments() -> None:
    """§17.1 — mutable_review_comments is excluded from the hash input."""
    a = {"case_id": "x", "mutable_review_comments": "first"}
    b = {"case_id": "x", "mutable_review_comments": "second"}
    assert canonical_sha256(a) == canonical_sha256(b)


def test_canonical_json_normalizes_unicode_via_nfc() -> None:
    """§17.1 — NFC normalization on string keys/values (UAX #15)."""
    decomposed = {"cafe\u0301": "value"}  # 'café' with combining accent
    composed = {"café": "value"}  # precomposed
    assert canonical_json_bytes(decomposed) == canonical_json_bytes(composed)


def test_canonical_json_orders_keys_recursively() -> None:
    """§17.1 — sorted keys at every object level, recursively."""
    a = {"z": 1, "a": {"y": 2, "x": 3}}
    b = {"a": {"x": 3, "y": 2}, "z": 1}
    assert canonical_json_bytes(a) == canonical_json_bytes(b)


def test_canonical_json_rejects_nan_and_infinity() -> None:
    """§17.3 — NaN, +Inf, -Inf are FORBIDDEN at hash time."""
    with pytest.raises((ValueError, TypeError)):
        canonical_sha256({"v": float("nan")})
    with pytest.raises((ValueError, TypeError)):
        canonical_sha256({"v": float("inf")})


def test_every_artifact_hash_matches_manifest() -> None:
    """§19.1.3 — manifest.case_hashes must equal recomputed hashes."""
    cases = approved_cases(_repo_root())
    case_by_id = {case["case_id"]: case for case in cases}
    manifest_path = _repo_root() / "benchmarks" / "manifests" / "task-011-approved-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for case_id, expected in manifest["case_hashes"].items():
        actual = canonical_sha256({**case_by_id[case_id], "canonical_hash": "<placeholder>"})
        assert actual == expected, f"{case_id}: expected {expected} got {actual}"


# --- §9.3.4 — table execution at ci_validation stage -------------------------


def test_validator_executes_transition_table_per_case() -> None:
    """The CI gate must call the §9.3 transition table for every case (§9.3.4).

    We do this indirectly by tampering the corpus so a §9.3 condition fires
    (synthetic cited as independent evidence) and asserting the validator
    rejects the corpus.
    """
    root = _repo_root()
    tmp = root.parent / "_tmp_t11"
    if tmp.exists():
        import shutil

        shutil.rmtree(tmp)
    for sub in ("benchmarks/cases", "benchmarks/manifests"):
        src = root / sub
        dst = tmp / sub
        dst.mkdir(parents=True)
        for f in src.iterdir():
            (dst / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    # Mark one synthetic case as cited-as-independent — this MUST trigger §9.3.3
    target = tmp / "benchmarks" / "cases" / "task011_case_03.json"
    case = json.loads(target.read_text(encoding="utf-8"))
    case["source_evidence"]["is_independent_validation_evidence"] = True
    case["canonical_hash"] = canonical_sha256({**case, "canonical_hash": "<placeholder>"})
    target.write_text(json.dumps(case, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        validate_corpus(tmp)
    import shutil

    shutil.rmtree(tmp)


# --- §19.1.4 — case_count invariants ----------------------------------------


def test_case_count_invariants(tmp_path: Path) -> None:
    root = _repo_root()
    for sub in ("benchmarks/cases", "benchmarks/manifests"):
        src = root / sub
        dst = tmp_path / sub
        dst.mkdir(parents=True)
        for f in src.iterdir():
            (dst / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    manifest_path = tmp_path / "benchmarks" / "manifests" / "task-011-approved-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["case_count"] = 19  # wrong
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValidationError, match="case_count"):
        validate_corpus(tmp_path)


# --- §19.1.7 — golden vs benchmark path separation ---------------------------


def test_benchmarks_does_not_contain_tests_subtree() -> None:
    """§19.1.7 — benchmarks/ and tests/ MUST be disjoint."""
    benchmarks = _repo_root() / "benchmarks"
    nested = benchmarks / "tests"
    assert not nested.exists(), f"forbidden subtree at {nested}"
    assert not any(nested.glob("*"))
