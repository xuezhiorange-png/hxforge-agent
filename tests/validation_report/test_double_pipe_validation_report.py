"""TASK-019 validation-report schema tests (Slice 1).

Asserts that :func:`build_double_pipe_validation_report` produces a
report dictionary matching the frozen §7.1 shape with exactly 3 case
blocks and a deterministic report_id.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Ensure repo root is importable so we can import the source module.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from hexagent.validation_report import (
    ALLOWED_OVERALL_STATUSES,
    TASK_019_GOLDEN_CASE_IDS,
    TASK_019_VALIDATION_REPORT_V1,
    build_double_pipe_validation_report,
    canonical_json_dumps,
    deterministic_report_id,
    sha256_hex,
)

# --- Schema constants tests ---


def test_schema_version_constant_is_frozen() -> None:
    """Schema version must be the frozen V1 value from §7.1."""
    assert TASK_019_VALIDATION_REPORT_V1 == "TASK-019-VALIDATION-REPORT-V1"


def test_golden_case_ids_constant_is_frozen() -> None:
    """Exactly 3 case IDs, in fixed order, matching §4."""
    assert tuple(TASK_019_GOLDEN_CASE_IDS) == (
        "TASK-019-GOLDEN-01",
        "TASK-019-GOLDEN-02",
        "TASK-019-GOLDEN-03",
    )


def test_allowed_overall_statuses_constant_is_frozen() -> None:
    """Allowed overall statuses per §7.3."""
    assert ALLOWED_OVERALL_STATUSES == frozenset({"PASS", "FAIL", "NOT_COMPUTABLE"})


# --- Report builder skeleton tests ---


_GOLDEN_FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent / "golden" / "double_pipe_rating"
)


def _stub_case_block(case_id: str, overall_status: str = "PASS") -> dict:
    """Build a minimal case-block stub for skeleton tests.

    Slice 1 does NOT run the full upstream chain. This stub provides the
    minimum required §7.1 fields with deterministic placeholder values.
    """
    return {
        "case_id": case_id,
        "case_title": f"Slice 1 stub for {case_id}",
        "input_sha256": sha256_hex(f"slice1-stub-input-{case_id}"),
        "expected_output_sha256": sha256_hex(f"slice1-stub-expected-{case_id}"),
        "actual_output_sha256": sha256_hex(f"slice1-stub-actual-{case_id}"),
        "comparison": {
            "overall_status": overall_status,
            "per_field": [],
            "blockers": [],
            "warnings": [],
        },
        "provenance": {
            "correlation_ids": ["TASK-007-stub-correlation-id"],
            "provider_ids": ["TASK-015A-stub-provider-id"],
            "rule_pack_ids": [],
            "design_contract_versions": {"TASK-019": "TASK-019-validation-report-impl-v0.1.0-slice1"},
        },
    }


def test_report_top_level_keys_match_frozen_section_7_1() -> None:
    """Top-level keys must match the frozen §7.1 schema exactly."""
    blocks = [_stub_case_block(cid) for cid in TASK_019_GOLDEN_CASE_IDS]
    report = build_double_pipe_validation_report(per_case_blocks=blocks)

    expected_top_keys = {
        "report_schema_version",
        "report_id",
        "generated_at",
        "upstream_contract_versions",
        "run_environment",
        "golden_cases",
        "aggregate_summary",
        "license_boundary_attestation",
    }
    assert set(report.keys()) == expected_top_keys


def test_report_schema_version_is_frozen_v1() -> None:
    blocks = [_stub_case_block(cid) for cid in TASK_019_GOLDEN_CASE_IDS]
    report = build_double_pipe_validation_report(per_case_blocks=blocks)
    assert report["report_schema_version"] == TASK_019_VALIDATION_REPORT_V1


def test_report_contains_exactly_three_cases() -> None:
    blocks = [_stub_case_block(cid) for cid in TASK_019_GOLDEN_CASE_IDS]
    report = build_double_pipe_validation_report(per_case_blocks=blocks)
    assert len(report["golden_cases"]) == 3
    case_ids = [b["case_id"] for b in report["golden_cases"]]
    assert set(case_ids) == set(TASK_019_GOLDEN_CASE_IDS)


def test_each_case_has_required_section_7_1_fields() -> None:
    blocks = [_stub_case_block(cid) for cid in TASK_019_GOLDEN_CASE_IDS]
    report = build_double_pipe_validation_report(per_case_blocks=blocks)
    required = {
        "case_id",
        "case_title",
        "input_sha256",
        "expected_output_sha256",
        "actual_output_sha256",
        "comparison",
        "provenance",
    }
    for block in report["golden_cases"]:
        assert required <= set(block.keys()), (
            f"case block {block.get('case_id')!r} missing keys: "
            f"{required - set(block.keys())!r}"
        )


def test_each_case_input_hash_is_64_lowercase_hex() -> None:
    blocks = [_stub_case_block(cid) for cid in TASK_019_GOLDEN_CASE_IDS]
    report = build_double_pipe_validation_report(per_case_blocks=blocks)
    for block in report["golden_cases"]:
        for k in ("input_sha256", "expected_output_sha256", "actual_output_sha256"):
            h = block[k]
            assert len(h) == 64 and h == h.lower() and re.match(r"^[0-9a-f]{64}$", h), (
                f"case {block['case_id']!r} field {k!r} is not 64-char lowercase hex: {h!r}"
            )


def test_aggregate_summary_counts_sum_to_three() -> None:
    """Per frozen §7.1, aggregate_summary counts must sum to total_cases=3."""
    blocks = [
        _stub_case_block("TASK-019-GOLDEN-01", "PASS"),
        _stub_case_block("TASK-019-GOLDEN-02", "FAIL"),
        _stub_case_block("TASK-019-GOLDEN-03", "NOT_COMPUTABLE"),
    ]
    report = build_double_pipe_validation_report(per_case_blocks=blocks)
    summary = report["aggregate_summary"]
    assert summary["total_cases"] == 3
    assert summary["passed"] + summary["failed"] + summary["not_computable"] == summary["total_cases"]
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["not_computable"] == 1


def test_report_id_is_deterministic_across_repeated_calls() -> None:
    """Same input → same report_id (UUID v5)."""
    blocks = [_stub_case_block(cid) for cid in TASK_019_GOLDEN_CASE_IDS]
    r1 = build_double_pipe_validation_report(per_case_blocks=blocks)
    r2 = build_double_pipe_validation_report(per_case_blocks=blocks)
    assert r1["report_id"] == r2["report_id"]
    # UUID v5 string format
    assert re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", r1["report_id"]), (
        f"report_id is not UUID v5 format: {r1['report_id']!r}"
    )


def test_canonical_json_dumps_is_deterministic() -> None:
    """canonical_json_dumps must produce the same string for the same input."""
    obj = {"b": 1, "a": 2, "nested": {"y": 2, "x": 1}}
    s1 = canonical_json_dumps(obj)
    s2 = canonical_json_dumps(obj)
    assert s1 == s2
    assert s1 == '{"a":2,"b":1,"nested":{"x":1,"y":2}}'


def test_sha256_hex_is_canonical_64_lowercase_hex() -> None:
    h = sha256_hex("hello")
    assert len(h) == 64 and h == h.lower() and re.match(r"^[0-9a-f]{64}$", h)
    assert h == sha256_hex("hello")  # deterministic


def test_deterministic_report_id_constant_is_stable() -> None:
    """deterministic_report_id() with default args returns the same UUID each call."""
    rid1 = deterministic_report_id()
    rid2 = deterministic_report_id()
    assert rid1 == rid2


def test_report_rejects_wrong_case_count() -> None:
    """Exactly 3 case blocks required; 1 / 2 / 4 must raise."""
    import pytest

    blocks_1 = [_stub_case_block("TASK-019-GOLDEN-01")]
    blocks_2 = [
        _stub_case_block("TASK-019-GOLDEN-01"),
        _stub_case_block("TASK-019-GOLDEN-02"),
    ]
    blocks_4 = [
        _stub_case_block("TASK-019-GOLDEN-01"),
        _stub_case_block("TASK-019-GOLDEN-02"),
        _stub_case_block("TASK-019-GOLDEN-03"),
        _stub_case_block("TASK-019-GOLDEN-99"),
    ]
    with pytest.raises(ValueError):
        build_double_pipe_validation_report(per_case_blocks=blocks_1)
    with pytest.raises(ValueError):
        build_double_pipe_validation_report(per_case_blocks=blocks_2)
    with pytest.raises(ValueError):
        build_double_pipe_validation_report(per_case_blocks=blocks_4)


def test_report_rejects_invalid_overall_status() -> None:
    """A case block with overall_status outside ALLOWED_OVERALL_STATUSES must raise."""
    import pytest

    bad_block = _stub_case_block("TASK-019-GOLDEN-01", overall_status="BOGUS")
    with pytest.raises(ValueError):
        build_double_pipe_validation_report(per_case_blocks=[bad_block, _stub_case_block("TASK-019-GOLDEN-02"), _stub_case_block("TASK-019-GOLDEN-03")])


def test_report_rejects_missing_required_keys() -> None:
    """A case block missing required keys must raise."""
    import pytest

    incomplete = {"case_id": "TASK-019-GOLDEN-01"}  # missing everything else
    with pytest.raises(ValueError):
        build_double_pipe_validation_report(per_case_blocks=[incomplete, _stub_case_block("TASK-019-GOLDEN-02"), _stub_case_block("TASK-019-GOLDEN-03")])


# --- Fixture file presence (Slice 1 schema-shape reproducibility) ---


def test_golden_fixtures_exist_and_are_loadable() -> None:
    """Slice 1 contract: all 3 golden fixtures exist, are valid JSON, and
    contain a ``case_id`` matching the expected TASK-019-GOLDEN-NN pattern."""
    expected = {
        "tests/golden/double_pipe_rating/case_01_heat_balance_rating.json": "TASK-019-GOLDEN-01",
        "tests/golden/double_pipe_rating/case_02_materials_mass_mechanical.json": "TASK-019-GOLDEN-02",
        "tests/golden/double_pipe_rating/case_03_cost_lifecycle_envelope.json": "TASK-019-GOLDEN-03",
    }
    for rel_path, expected_case_id in expected.items():
        p = _REPO_ROOT / rel_path
        assert p.exists(), f"missing fixture: {rel_path}"
        with p.open() as fh:
            data = json.load(fh)
        assert data["case_id"] == expected_case_id, (
            f"{rel_path} case_id mismatch: {data['case_id']!r} != {expected_case_id!r}"
        )
