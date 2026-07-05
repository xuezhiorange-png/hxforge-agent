"""Optimistic concurrency helpers for TASK-014 immutable case revisions.

Implements Section 13.2 of the TASK-014 frozen design contract
(docs/tasks/TASK-014-immutable-case-revisions-persistence.md,
Frozen Contract Authority SHA
``6f337a6e81a8c2a7ba8059285aeef39bba59c7cb``).

Each committed revision carries an ``optimistic_concurrency_token``
(opaque string). A request that attempts to act on a revision MUST
present the expected token; a token mismatch surfaces as
:class:`CaseRevisionConflict` with
``conflict_reason="token_mismatch"``.

The token MUST be unique across the entire system so that no two
revisions can share it. The repository enforces uniqueness on insert
(Section 9.2 / 13.5 + Section 13.2 combined).

This module provides:

* :func:`mint_optimistic_concurrency_token` — generate a token for a
  revision at commit time. Uses ``hashlib.sha256`` over a deterministic
  string (``revision_id | created_at``) to keep tests reproducible.
* :func:`assert_token_matches` — convenience wrapper that raises
  ``CaseRevisionConflict`` with ``conflict_reason="token_mismatch"`` on
  mismatch.
"""

from __future__ import annotations

import hashlib

from hexagent.case_revisions.errors import CaseRevisionConflict


def mint_optimistic_concurrency_token(*, revision_id: str, created_at_iso: str) -> str:
    """Return a 64-hex SHA-256 token derived from ``revision_id`` and
    ``created_at``.

    The output is deterministic for a given ``(revision_id, created_at)``
    pair, which keeps tests reproducible while still being a
    collision-resistant opaque token in production use.
    """
    payload = f"{revision_id}|{created_at_iso}".encode()
    return hashlib.sha256(payload).hexdigest()


def assert_token_matches(
    *,
    revision_id: str,
    expected_token: str,
    actual_token: str | None,
    root_case_id: str | None = None,
) -> None:
    """Raise :class:`CaseRevisionConflict` with
    ``conflict_reason="token_mismatch"`` iff ``expected_token`` does not
    equal ``actual_token``.

    Section 13.2 — a token mismatch is a concurrency blocker. Stale
    expected-parent conditions do NOT use this path (Section 12.5 +
    13.1 + 16.2 disambiguation rule).
    """
    if actual_token != expected_token:
        raise CaseRevisionConflict(
            f"optimistic_concurrency_token mismatch for revision_id={revision_id!r} (Section 13.2)",
            root_case_id=root_case_id,
            revision_id=revision_id,
            conflict_reason="token_mismatch",
            expected_parent_revision_id=None,
            actual_parent_revision_id=None,
            attempted_revision_number=None,
        )


__all__ = [
    "assert_token_matches",
    "mint_optimistic_concurrency_token",
]
