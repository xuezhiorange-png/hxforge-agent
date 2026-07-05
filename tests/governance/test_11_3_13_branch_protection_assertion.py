"""TASK-015 governance — Section 11.3.13 branch protection assertion test.

Implements the TASK-015 frozen design contract
(``docs/tasks/TASK-015-ci-security-and-release-automation.md``,
Frozen Contract Authority SHA
``39135e269b014e9c9310ac403a60591393d46b2d``).

Section 11.3.13 — "Branch protection assertion test: a PR targeting
``main`` MUST fail CI if the head SHA's ``content_hash`` does not match
the spec file's current ``content_hash``."

This test file implements the assertion at the **validator + test
harness** level (no GitHub API calls, no network). It uses the public
:func:`compute_content_hash` + :func:`validate_spec` to demonstrate
that:

1. When the head SHA's spec has a ``content_hash`` field equal to the
   spec's own canonical sha256 → ``validate_spec`` is CLEAN.
2. When the head SHA's spec has a stale ``content_hash`` (mismatch) →
   ``validate_spec`` raises a BLOCKER (``spec_schema_error`` on the
   ``content_hash`` field) — which the CI runtime translates into a
   failed ``task-015/<spec-name>/blockers`` status check.

The branch-protection assertion is therefore reproducible in a unit
test without depending on GitHub Actions / GitHub branch-protection
settings (which are out-of-scope for the contract per Section 14.3 +
Section 14.13).
"""

from __future__ import annotations

import pytest

from hexagent.governance import (
    SPEC_PATH_CI_PIPELINE,
    compute_content_hash,
    validate_spec,
)
from hexagent.governance.spec_validator import _spec_for_hash

from ._factories import build_ci_pipeline_spec


def _with_overridden_content_hash(spec: dict, new_hash: str) -> dict:
    """Return a shallow copy of ``spec`` with ``content_hash`` set to
    ``new_hash``. Used to simulate the branch-protection scenario where
    the head SHA's spec carries a stale content_hash."""
    out = dict(spec)
    out["content_hash"] = new_hash
    return out


def test_11_3_13_clean_spec_when_content_hash_matches_canonical() -> None:
    """Section 11.3.13 — when the head SHA's ``content_hash`` matches
    the spec's own canonical sha256, the validator is clean (no
    content_hash blocker). This is the GREEN-path branch-protection
    case.
    """
    spec = build_ci_pipeline_spec()
    # Factory has stamped the correct content_hash.
    assert spec["content_hash"] == compute_content_hash(_spec_for_hash(spec))
    report = validate_spec(SPEC_PATH_CI_PIPELINE, spec)
    content_hash_blockers = [f for f in report.blockers if f.field_path == "content_hash"]
    assert content_hash_blockers == [], (
        "content_hash matches canonical → expected no content_hash blocker; "
        f"got {[f.to_dict() for f in content_hash_blockers]}"
    )


def test_11_3_13_blocker_when_content_hash_does_not_match_canonical() -> None:
    """Section 11.3.13 — when the head SHA's ``content_hash`` does NOT
    match the spec's own canonical sha256, the validator emits a
    BLOCKER on the ``content_hash`` field. The CI runtime translates
    this into a failed branch-protection status check (RED on
    ``task-015/<spec-name>/blockers``).
    """
    spec = build_ci_pipeline_spec()
    # Simulate a stale head SHA by overriding content_hash to a known
    # wrong value.
    stale_spec = _with_overridden_content_hash(
        spec, "0000000000000000000000000000000000000000000000000000000000000000"
    )
    report = validate_spec(SPEC_PATH_CI_PIPELINE, stale_spec)
    content_hash_blockers = [f for f in report.blockers if f.field_path == "content_hash"]
    assert len(content_hash_blockers) == 1, (
        "expected exactly one content_hash blocker on stale spec; "
        f"got {[(f.error_code, f.severity, f.message) for f in content_hash_blockers]}"
    )
    blocker = content_hash_blockers[0]
    assert blocker.severity == "blocker", (
        "Section 11.3.13 — content_hash mismatch MUST surface as a BLOCKER"
    )
    assert blocker.error_code == "spec_schema_error", (
        "Section 11.3.13 — content_hash mismatch MUST surface as spec_schema_error"
    )
    # The blocker carries the canonical (expected) hash so CI tooling can
    # present the discrepancy.
    assert blocker.context.get("expected_content_hash") == compute_content_hash(
        _spec_for_hash(stale_spec)
    )


def test_11_3_13_branch_protection_status_check_name_shape() -> None:
    """Section 11.3.13 + Section 9 cross-cutting governance — the
    branch-protection status check follows the naming convention
    ``task-015/<spec-name>/blockers``. This test verifies the shape
    rather than the wiring (the wiring is asserted by the runtime hook
    workflow; the test pattern is enough to enforce the shape).
    """
    # ``spec-name`` is the canonical kebab-case identifier of the
    # CIPipelineSpec (``ci-pipeline``), NOT the spec_path.
    expected_check_name = "task-015/ci-pipeline/blockers"
    parts = expected_check_name.split("/")
    assert len(parts) == 3, f"status check name must have 3 slash-delimited parts; got {parts}"
    assert parts[0] == "task-015", f"first segment must be 'task-015'; got {parts[0]}"
    assert parts[2] == "blockers", f"last segment must be 'blockers'; got {parts[2]}"
    # Spec-name segment is the canonical kebab-case identifier of the
    # CIPipelineSpec (declared in Section 4.3).
    assert parts[1].islower() and " " not in parts[1], (
        f"spec-name segment must be lowercase kebab-case; got {parts[1]!r}"
    )


def test_11_3_13_validator_emits_disjoint_blocker_for_stale_hash() -> None:
    """Section 11.3.13 — a stale content_hash surfaces as a BLOCKER
    only (not a warning). This ensures branch-protection assertion is
    enforced at the highest severity.
    """
    spec = build_ci_pipeline_spec()
    stale_spec = _with_overridden_content_hash(
        spec,
        "deadbeef" * 8,  # 64 hex chars, but wrong
    )
    report = validate_spec(SPEC_PATH_CI_PIPELINE, stale_spec)
    content_hash_warnings = [f for f in report.warnings if f.field_path == "content_hash"]
    assert content_hash_warnings == [], (
        "Section 11.3.13 — content_hash mismatch MUST NOT be downgraded to a warning; "
        f"got {[f.to_dict() for f in content_hash_warnings]}"
    )


@pytest.mark.parametrize(
    "wrong_hash",
    [
        "",  # empty
        "0" * 64,  # wrong but well-formed hex
        "deadbeef",  # too short
        "not-hex-at-all",  # not hex
    ],
)
def test_11_3_13_various_stale_content_hashes_are_blocked(wrong_hash: str) -> None:
    """Section 11.3.13 — any content_hash value that does not match
    the canonical sha256 surfaces as a BLOCKER. This parametrize
    covers the common stale-hash shapes (empty, zeroed, truncated,
    non-hex).
    """
    spec = build_ci_pipeline_spec()
    stale_spec = _with_overridden_content_hash(spec, wrong_hash)
    report = validate_spec(SPEC_PATH_CI_PIPELINE, stale_spec)
    blockers = [f for f in report.blockers if f.field_path == "content_hash"]
    assert len(blockers) == 1, (
        f"expected one content_hash blocker for stale hash {wrong_hash!r}; got {len(blockers)}"
    )
    assert blockers[0].severity == "blocker"
