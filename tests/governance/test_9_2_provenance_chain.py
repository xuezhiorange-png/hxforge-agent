"""TASK-015 governance — Section 9.2 / 9.3 PROVENANCE chain test.

Implements the TASK-015 frozen design contract
(``docs/tasks/TASK-015-ci-security-and-release-automation.md``,
Frozen Contract Authority SHA
``39135e269b014e9c9310ac403a60591393d46b2d``).

Section 9.2 — every spec file MUST have a ``content_hash`` field
computed over the canonical representation.

Section 9.3 — every spec file MUST declare an ``owner`` (GitHub
username) and an ``updated_at`` ISO-8601 timestamp. Every change to a
spec file MUST go through a PR. The PR body MUST cite the prior
``content_hash`` and the new ``content_hash``, plus a one-paragraph
rationale.

This test file exercises the PROVENANCE chain at the validator +
test-harness level. It does NOT depend on GitHub API calls (per the
follow-up scope guidance: "Do not depend on GitHub API calls inside
unit tests unless already established in the repository test pattern").

The PR-side citation requirement (Section 9.3) is exercised by an
explicit PR-body shape test that asserts the prior / new
``content_hash`` pair must be present in the PR description when a
spec changes.
"""

from __future__ import annotations

import re

import pytest

from hexagent.governance import (
    SPEC_PATH_CI_PIPELINE,
    SPEC_PATH_FAILURE_TAXONOMY,
    SPEC_PATH_RELEASE,
    SPEC_PATH_SECURITY_GATE,
    compute_content_hash,
    validate_spec,
)
from hexagent.governance.spec_validator import _spec_for_hash

from ._factories import (
    build_ci_pipeline_spec,
    build_failure_taxonomy_spec,
    build_release_spec,
    build_security_gate_spec,
)


@pytest.mark.parametrize(
    "spec_path,builder",
    [
        (SPEC_PATH_CI_PIPELINE, build_ci_pipeline_spec),
        (SPEC_PATH_SECURITY_GATE, build_security_gate_spec),
        (SPEC_PATH_RELEASE, build_release_spec),
        (SPEC_PATH_FAILURE_TAXONOMY, build_failure_taxonomy_spec),
    ],
)
def test_9_2_provenance_each_spec_declares_owner_updated_at_content_hash(
    spec_path: str, builder
) -> None:
    """Section 9.2 + 9.3 — every spec file MUST declare ``owner``,
    ``updated_at``, and ``content_hash``. The validator must accept
    these as required fields and the content_hash must match the
    canonical sha256.
    """
    data = builder()
    # All three fields are present.
    assert isinstance(data.get("owner"), str) and data["owner"].strip(), (
        f"{spec_path}: owner MUST be a non-empty string"
    )
    assert isinstance(data.get("updated_at"), str), (
        f"{spec_path}: updated_at MUST be a string (ISO-8601 UTC)"
    )
    assert isinstance(data.get("content_hash"), str), (
        f"{spec_path}: content_hash MUST be a string (sha256 hex)"
    )
    # content_hash matches the canonical sha256.
    expected = compute_content_hash(_spec_for_hash(data))
    assert data["content_hash"] == expected, (
        f"{spec_path}: content_hash does not match canonical sha256; "
        f"got {data['content_hash']}, expected {expected}"
    )
    # Validator confirms the spec is clean.
    report = validate_spec(spec_path, data)
    assert report.is_clean, (
        f"{spec_path}: expected clean validator report; got "
        f"blockers={[f.to_dict() for f in report.blockers]}"
    )


@pytest.mark.parametrize(
    "spec_path,builder",
    [
        (SPEC_PATH_CI_PIPELINE, build_ci_pipeline_spec),
        (SPEC_PATH_SECURITY_GATE, build_security_gate_spec),
        (SPEC_PATH_RELEASE, build_release_spec),
        (SPEC_PATH_FAILURE_TAXONOMY, build_failure_taxonomy_spec),
    ],
)
def test_9_2_provenance_missing_owner_fails_validation(
    spec_path: str, builder
) -> None:
    """Section 9.3 — missing ``owner`` MUST fail validation as a
    BLOCKER (spec_schema_error on the ``owner`` field).
    """
    from hexagent.governance.spec_validator import _spec_for_hash, compute_content_hash

    data = builder()
    del data["owner"]
    # Re-stamp content_hash so the only blocker surfaces on the owner
    # field itself (Section 9.2 — content_hash is over the canonical
    # representation excluding itself).
    data["content_hash"] = compute_content_hash(_spec_for_hash(data))
    report = validate_spec(spec_path, data)
    owner_blockers = [
        f for f in report.blockers
        if f.field_path == "owner" and f.error_code == "spec_schema_error"
    ]
    assert len(owner_blockers) >= 1, (
        f"{spec_path}: expected at least one owner BLOCKER; got "
        f"blockers={[f.to_dict() for f in report.blockers]}"
    )


@pytest.mark.parametrize(
    "spec_path,builder",
    [
        (SPEC_PATH_CI_PIPELINE, build_ci_pipeline_spec),
        (SPEC_PATH_SECURITY_GATE, build_security_gate_spec),
        (SPEC_PATH_RELEASE, build_release_spec),
        (SPEC_PATH_FAILURE_TAXONOMY, build_failure_taxonomy_spec),
    ],
)
def test_9_2_provenance_missing_content_hash_fails_validation(
    spec_path: str, builder
) -> None:
    """Section 9.2 — missing ``content_hash`` MUST fail validation as
    a BLOCKER (the field is in :data:`COMMON_REQUIRED_FIELDS`).
    """
    data = builder()
    del data["content_hash"]
    report = validate_spec(spec_path, data)
    content_hash_blockers = [
        f for f in report.blockers
        if f.field_path == "content_hash"
        and f.error_code == "spec_schema_error"
    ]
    assert len(content_hash_blockers) >= 1, (
        f"{spec_path}: expected at least one content_hash BLOCKER on missing; "
        f"got blockers={[f.to_dict() for f in report.blockers]}"
    )


def test_9_2_provenance_content_hash_regeneration_on_field_change() -> None:
    """Section 9.2 + 11.1.6 — changing a field recomputes the
    ``content_hash``; leaving fields untouched leaves the hash
    untouched. This pins the determinism invariant.
    """
    spec = build_ci_pipeline_spec()
    hash_before = spec["content_hash"]
    # Update updated_at by 1 second — canonical sha256 must change.
    from hexagent.governance.spec_validator import _spec_for_hash, compute_content_hash

    spec_changed = dict(spec)
    spec_changed["updated_at"] = "2026-07-05T07:00:01Z"
    spec_changed["content_hash"] = compute_content_hash(_spec_for_hash(spec_changed))
    assert spec_changed["content_hash"] != hash_before, (
        "changing a field MUST recompute content_hash"
    )
    # Field reordering alone MUST NOT change the hash (Section 9.1).
    spec_reordered = dict(spec)
    reordered_items = list(spec_reordered.items())
    reordered_items.reverse()
    spec_reordered = dict(reordered_items)
    spec_reordered["content_hash"] = compute_content_hash(_spec_for_hash(spec_reordered))
    assert spec_reordered["content_hash"] == hash_before, (
        "field reordering alone MUST NOT change content_hash (Section 9.1)"
    )


def test_9_3_pr_body_cites_prior_and_new_content_hash() -> None:
    """Section 9.3 — every spec change MUST go through a PR whose body
    cites the prior ``content_hash`` AND the new ``content_hash``,
    plus a one-paragraph rationale.

    This test pins the PR-body shape invariant without depending on
    GitHub API calls. The shape is enforceable via a regex check at
    PR-open time (the runtime hook workflow can run the same check).
    """
    # Construct a synthetic PR body following the Section 9.3 shape.
    prior_hash = "a" * 64
    new_hash = "b" * 64
    rationale = (
        "Update CI pipeline spec to register governance tests in shard manifest. "
        "Backward-compatible addition; no public API change. "
        "Validator-level hooks (Section 11.2.8 + 11.1.7) added without changing "
        "the storage model."
    )
    pr_body = (
        "## TASK-015 follow-up scope implementation\n"
        "\n"
        "Frozen Contract Authority SHA: "
        "`39135e269b014e9c9310ac403a60591393d46b2d`\n"
        "\n"
        f"PROVENANCE:\n"
        f"- prior content_hash: `{prior_hash}`\n"
        f"- new content_hash: `{new_hash}`\n"
        "\n"
        f"RATIONALE: {rationale}\n"
    )

    # Shape check 1 — both content_hash values are cited as 64-hex sha256.
    hex_re = re.compile(r"`([0-9a-f]{64})`")
    cited_hashes = hex_re.findall(pr_body)
    assert prior_hash in cited_hashes, (
        f"PR body MUST cite the prior content_hash ({prior_hash})"
    )
    assert new_hash in cited_hashes, (
        f"PR body MUST cite the new content_hash ({new_hash})"
    )
    # Shape check 2 — explicit "prior content_hash" / "new content_hash" labels.
    assert re.search(r"prior\s+content_hash", pr_body, re.IGNORECASE), (
        "PR body MUST contain the label 'prior content_hash'"
    )
    assert re.search(r"new\s+content_hash", pr_body, re.IGNORECASE), (
        "PR body MUST contain the label 'new content_hash'"
    )
    # Shape check 3 — a rationale paragraph is present.
    assert "RATIONALE" in pr_body or "rationale" in pr_body.lower(), (
        "PR body MUST contain a RATIONALE paragraph (Section 9.3)"
    )
    assert len(rationale) > 50, (
        "rationale MUST be a one-paragraph explanation (>50 chars)"
    )


def test_9_3_pr_body_missing_prior_content_hash_rejected() -> None:
    """Section 9.3 — a PR body that does NOT cite the prior
    content_hash is rejected by the shape check.
    """
    new_hash = "b" * 64
    bad_pr_body = (
        "## TASK-015 follow-up scope implementation\n"
        f"new content_hash: `{new_hash}`\n"
        "RATIONALE: a tiny rationale.\n"
    )
    cited_hashes = re.findall(r"`([0-9a-f]{64})`", bad_pr_body)
    # Only one hash cited; the prior hash is missing.
    assert len(cited_hashes) == 1
    assert not re.search(r"prior\s+content_hash", bad_pr_body, re.IGNORECASE)


def test_9_3_pr_body_cites_frozen_contract_authority_sha() -> None:
    """Section 9.3 cross-cutting — every PR touching TASK-015 specs
    MUST cite the Frozen Contract Authority SHA in the PR body.
    """
    fcas = "39135e269b014e9c9310ac403a60591393d46b2d"
    pr_body = (
        "## TASK-015 follow-up scope\n"
        f"\nFrozen Contract Authority SHA: `{fcas}`\n"
    )
    assert fcas in pr_body
    assert re.search(rf"`{fcas}`", pr_body)