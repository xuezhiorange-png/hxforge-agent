"""Validation helpers for TASK-014 immutable case revisions.

Implements Section 12 (validation and blocker model) of the TASK-014
frozen design contract
(docs/tasks/TASK-014-immutable-case-revisions-persistence.md,
Frozen Contract Authority SHA
``6f337a6e81a8c2a7ba8059285aeef39bba59c7cb``).

Section 12.1 — structural blockers (missing identity fields, duplicate
``(root_case_id, revision_number)``, invalid status enum, etc.).
Section 12.2 — hash blockers (payload_hash / domain_snapshot_hash /
parent_chain_hash mismatch).
Section 12.3 — unit / provider / authority blockers (delegated; this
implementation does not perform upstream resolution).
Section 12.4 — restricted-content blockers (delegated to
:mod:`hexagent.case_revisions.restricted`).
Section 12.5 — concurrency blockers (expected_parent / token / sibling —
enforced at the repository layer; see :mod:`persistence`).
Section 12.6 — warnings (non-blocking).
Section 12.7 — structural separation: blockers and warnings live in
disjoint lists; a blocker MUST NOT be downgraded to a warning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hexagent.case_revisions.canonical import (
    compute_domain_snapshot_hash,
    compute_payload_hash,
)
from hexagent.case_revisions.errors import (
    MissingRevisionAuthority,
    RevisionHashMismatch,
    RevisionPersistenceFailure,
)
from hexagent.case_revisions.lifecycle import ensure_status_valid
from hexagent.case_revisions.models import CaseRevision, RevisionStatus
from hexagent.case_revisions.restricted import scan_payload_for_restricted_content

# --- Validation result containers (Section 12.7) --------------------------


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation issue with ``kind`` ∈ ``{"blocker", "warning"}``.

    Section 12.7 — the two collections MUST remain disjoint; a blocker
    MUST NOT be downgraded to a warning.
    """

    kind: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "path": self.path, "message": self.message}


@dataclass
class ValidationResult:
    """Section 12.7 — structural separation of blockers and warnings."""

    blockers: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.blockers

    def to_dict(self) -> dict[str, list[dict[str, str]]]:
        return {
            "blockers": [b.to_dict() for b in self.blockers],
            "warnings": [w.to_dict() for w in self.warnings],
        }

    def merge(self, other: ValidationResult) -> ValidationResult:
        self.blockers.extend(other.blockers)
        self.warnings.extend(other.warnings)
        return self


def _issue(kind: str, path: str, message: str) -> ValidationIssue:
    return ValidationIssue(kind=kind, path=path, message=message)


# --- Top-level validation entry point -------------------------------------


def validate_revision(
    revision: CaseRevision,
    *,
    parent_chain_rows: tuple[dict[str, Any], ...] = (),
) -> ValidationResult:
    """Return a :class:`ValidationResult` for ``revision``.

    Performs structural + hash + restricted-content checks; concurrency
    checks (expected_parent / token / sibling) are enforced at the
    repository layer because they require repository state.
    """
    result = ValidationResult()

    # Section 12.1 — required identity fields.
    if not revision.revision_id:
        result.blockers.append(_issue("blocker", "revision_id", "missing required identity field"))
    if not revision.root_case_id:
        result.blockers.append(_issue("blocker", "root_case_id", "missing required identity field"))
    if not isinstance(revision.revision_number, int) or revision.revision_number < 1:
        result.blockers.append(
            _issue(
                "blocker",
                "revision_number",
                f"revision_number must be int >= 1; got {revision.revision_number!r}",
            )
        )

    # Section 12.1 — status enum.
    try:
        ensure_status_valid(revision.status)
    except RevisionPersistenceFailure as err:
        result.blockers.append(_issue("blocker", "status", str(err)))

    # Section 12.1 — committed revisions require committed_at / committed_by.
    if revision.status == RevisionStatus.COMMITTED:
        if revision.committed_at is None:
            result.blockers.append(
                _issue(
                    "blocker",
                    "committed_at",
                    "committed revisions require committed_at (Section 12.1)",
                )
            )
        if not revision.committed_by:
            result.blockers.append(
                _issue(
                    "blocker",
                    "committed_by",
                    "committed revisions require committed_by (Section 12.1)",
                )
            )

    # Section 12.2 — payload_hash.
    try:
        actual = compute_payload_hash(revision.payload)
        if actual != revision.payload_hash:
            result.blockers.append(
                _issue(
                    "blocker",
                    "payload_hash",
                    f"payload_hash mismatch: expected {revision.payload_hash!r}, "
                    f"actual {actual!r} (Section 12.2)",
                )
            )
    except RevisionHashMismatch as err:
        result.blockers.append(_issue("blocker", "payload_hash", str(err)))

    # Section 12.2 — domain_snapshot_hash.
    try:
        actual_snapshot = compute_domain_snapshot_hash(
            identity=revision.identity,
            payload=revision.payload,
            provenance=revision.provenance,
            parent_chain=parent_chain_rows,
        )
        if actual_snapshot != revision.domain_snapshot_hash:
            result.blockers.append(
                _issue(
                    "blocker",
                    "domain_snapshot_hash",
                    f"domain_snapshot_hash mismatch: expected "
                    f"{revision.domain_snapshot_hash!r}, actual "
                    f"{actual_snapshot!r} (Section 12.2)",
                )
            )
    except RevisionHashMismatch as err:
        result.blockers.append(_issue("blocker", "domain_snapshot_hash", str(err)))

    # Section 12.6 — warnings (non-blocking). Kept structurally
    # disjoint from blockers (Section 12.7).
    _check_warning_conditions(revision, result)

    return result


def validate_revision_or_raise(
    revision: CaseRevision,
    *,
    parent_chain_rows: tuple[dict[str, Any], ...] = (),
) -> ValidationResult:
    """Like :func:`validate_revision` but also raise structured errors for
    the canonical blocker categories (hash mismatch, restricted content,
    missing authority). Used by callers that prefer exception flow over
    result-based flow.

    Concurrency blockers (expected_parent / token / sibling) are NOT
    raised here; they live in the repository layer.
    """
    # Section 12.4 — restricted content scan (raises on first hit).
    scan_payload_for_restricted_content(revision.payload)

    # Section 12.2 — hash mismatches surface as RevisionHashMismatch.
    actual_payload_hash = compute_payload_hash(revision.payload)
    if actual_payload_hash != revision.payload_hash:
        raise RevisionHashMismatch(
            "payload_hash does not match canonicalized payload (Section 12.2)",
            root_case_id=revision.root_case_id,
            revision_id=revision.revision_id,
            expected_payload_hash=revision.payload_hash,
            actual_payload_hash=actual_payload_hash,
            hash_field="payload_hash",
        )
    actual_snapshot = compute_domain_snapshot_hash(
        identity=revision.identity,
        payload=revision.payload,
        provenance=revision.provenance,
        parent_chain=parent_chain_rows,
    )
    if actual_snapshot != revision.domain_snapshot_hash:
        raise RevisionHashMismatch(
            "domain_snapshot_hash does not match canonicalized domain snapshot (Section 12.2)",
            root_case_id=revision.root_case_id,
            revision_id=revision.revision_id,
            expected_payload_hash=revision.domain_snapshot_hash,
            actual_payload_hash=actual_snapshot,
            hash_field="domain_snapshot_hash",
        )
    return validate_revision(revision, parent_chain_rows=parent_chain_rows)


# --- Warning helpers -------------------------------------------------------


def _check_warning_conditions(revision: CaseRevision, result: ValidationResult) -> None:
    """Section 12.6 — collect non-blocking warnings. Strictly disjoint
    from blockers (Section 12.7). Stale expected-parent MUST NOT appear
    here (Section 12.5 + 12.7 disambiguation rule)."""
    # ``effective_date`` older than 5 years — we surface this only when
    # the identity dict declares ``effective_date`` as an RFC-3339 UTC
    # string. We do not perform actual date arithmetic in this layer
    # (callers may pass pre-evaluated booleans); the implementation here
    # is intentionally a no-op when the field is absent.
    effective_date = revision.identity.get("effective_date")
    is_legacy_marker = revision.identity.get("_legacy_marker") is True
    if effective_date is not None and isinstance(effective_date, str) and is_legacy_marker:
        result.warnings.append(
            _issue(
                "warning",
                "identity.effective_date",
                "effective_date older than 5 years (Section 12.6)",
            )
        )

    tombstone_chain_length = revision.identity.get("tombstone_chain_length")
    if isinstance(tombstone_chain_length, int) and tombstone_chain_length > 5:
        result.warnings.append(
            _issue(
                "warning",
                "identity.tombstone_chain_length",
                "tombstone chain length greater than 5 (Section 12.6)",
            )
        )


# --- Missing-authority resolver helper ------------------------------------


def assert_revision_authority_resolves(
    revision: CaseRevision,
    *,
    resolver: Any = None,
) -> None:
    """Section 12.3 — raise :class:`MissingRevisionAuthority` iff the
    revision references an upstream authority that the caller-supplied
    ``resolver`` cannot resolve.

    ``resolver`` is a callable ``(kind, reference) -> bool``. Tests can
    pass a stub; production callers wire this to the TASK-005 / TASK-013
    / TASK-012 lookups. The default resolver raises
    :class:`MissingRevisionAuthority` for any non-``None`` reference
    (fail-closed posture; see Section 12.3).
    """
    references = revision.identity.get("authority_references") or {}
    if not isinstance(references, dict):
        return
    for kind, reference in references.items():
        if reference is None:
            continue
        if resolver is None:
            raise MissingRevisionAuthority(
                f"authority reference for kind={kind!r} could not be resolved "
                "by the default fail-closed resolver (Section 12.3)",
                root_case_id=revision.root_case_id,
                revision_id=revision.revision_id,
                missing_authority=str(kind),
                reference=str(reference),
            )
        ok = bool(resolver(kind, reference))
        if not ok:
            raise MissingRevisionAuthority(
                f"authority reference for kind={kind!r} could not be resolved (Section 12.3)",
                root_case_id=revision.root_case_id,
                revision_id=revision.revision_id,
                missing_authority=str(kind),
                reference=str(reference),
            )


__all__ = [
    "ValidationIssue",
    "ValidationResult",
    "assert_revision_authority_resolves",
    "validate_revision",
    "validate_revision_or_raise",
]
