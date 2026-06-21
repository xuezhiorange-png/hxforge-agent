"""In-memory repository implementations for development and testing.

All state lives in plain Python dicts.  Ordering is deterministic: revisions
are sorted by ``revision_number``, runs by ``created_at``.

Deep-copy policy
~~~~~~~~~~~~~~~~
Every ``add()`` stores a **deep copy** of the entity; every ``get()``
returns a **deep copy**.  This guarantees that callers cannot mutate
repository state through retrieved objects.
"""
from __future__ import annotations

import copy
from uuid import UUID

from hexagent.domain.revisions import (
    CalculationRun,
    CalculationRunStatus,
    DesignCaseRevision,
    DuplicateIdError,
    InvalidStateTransitionError,
    MissingParentError,
    RevisionNumberConflictError,
)

# ---------------------------------------------------------------------------
# DesignCaseRevision repository
# ---------------------------------------------------------------------------


class InMemoryDesignCaseRevisionRepository:
    """Dict-backed store for :class:`DesignCaseRevision` objects.

    All stored and retrieved objects are deeply copied to prevent
    external mutation of repository state.
    """

    def __init__(self) -> None:
        self._by_id: dict[UUID, DesignCaseRevision] = {}
        self._by_case: dict[UUID, dict[int, DesignCaseRevision]] = {}

    # -- public API ----------------------------------------------------------

    def add(self, revision: DesignCaseRevision) -> None:
        """Persist a new revision with full constraint checking.

        Stores a **deep copy** — the caller retains ownership of the
        original object.

        Raises
        ------
        DuplicateIdError
            If a revision with the same ``revision_id`` already exists.
        RevisionNumberConflictError
            If a revision for the same ``case_id`` with the same
            ``revision_number`` already exists.
        MissingParentError
            If ``parent_revision_id`` is set but the parent does not exist.
        """
        # 1. Duplicate ID
        if revision.revision_id in self._by_id:
            raise DuplicateIdError("DesignCaseRevision", str(revision.revision_id))

        # 2. Revision number conflict
        case_rev_map = self._by_case.setdefault(revision.case_id, {})
        if revision.revision_number in case_rev_map:
            raise RevisionNumberConflictError(
                revision.case_id, revision.revision_number,
            )

        # 3. Missing parent
        if (
            revision.parent_revision_id is not None
            and revision.parent_revision_id not in self._by_id
        ):
            raise MissingParentError(str(revision.parent_revision_id))

        # 4. Store deep copy
        snapshot = copy.deepcopy(revision)
        self._by_id[revision.revision_id] = snapshot
        case_rev_map[revision.revision_number] = snapshot

    def get(self, revision_id: UUID) -> DesignCaseRevision:
        """Return a **deep copy** of the revision."""
        try:
            return copy.deepcopy(self._by_id[revision_id])
        except KeyError as err:
            raise KeyError(f"DesignCaseRevision not found: {revision_id}") from err

    def latest(self, case_id: UUID) -> DesignCaseRevision | None:
        """Return a deep copy of the most recent revision, or ``None``."""
        case_rev_map = self._by_case.get(case_id)
        if not case_rev_map:
            return None
        latest_number = max(case_rev_map)
        return copy.deepcopy(case_rev_map[latest_number])

    def list_by_case(self, case_id: UUID) -> tuple[DesignCaseRevision, ...]:
        """Return deep copies of all revisions ordered by revision_number ASC."""
        case_rev_map = self._by_case.get(case_id)
        if not case_rev_map:
            return ()
        return tuple(copy.deepcopy(case_rev_map[n]) for n in sorted(case_rev_map))


# ---------------------------------------------------------------------------
# CalculationRun repository
# ---------------------------------------------------------------------------


# Immutable identity fields that must not change during an update.
_IMMUTABLE_RUN_FIELDS: frozenset[str] = frozenset({
    "case_id",
    "case_revision_id",
    "run_type",
    "input_hash",
    "git_commit",
    "software_version",
    "schema_version",
})


class InMemoryCalculationRunRepository:
    """Dict-backed store for :class:`CalculationRun` objects.

    All stored and retrieved objects are deeply copied to prevent
    external mutation of repository state.
    """

    def __init__(self) -> None:
        self._by_id: dict[UUID, CalculationRun] = {}
        self._by_revision: dict[UUID, list[UUID]] = {}  # revision_id → [run_id, …]

    # -- public API ----------------------------------------------------------

    def add(self, run: CalculationRun) -> None:
        """Persist a new run with duplicate-ID checking.

        Only accepts ``PENDING`` or ``RUNNING`` as initial status.
        Stores a **deep copy**.

        Raises
        ------
        DuplicateIdError
            If a run with the same ``run_id`` already exists.
        InvalidStateTransitionError
            If the initial status is not valid.
        """
        if run.run_id in self._by_id:
            raise DuplicateIdError("CalculationRun", str(run.run_id))

        # Validate initial status
        if run.status not in (
            CalculationRunStatus.PENDING,
            CalculationRunStatus.RUNNING,
        ):
            raise InvalidStateTransitionError(
                "(new)", run.status,
            )

        snapshot = copy.deepcopy(run)
        self._by_id[run.run_id] = snapshot
        self._by_revision.setdefault(run.case_revision_id, []).append(run.run_id)

    def get(self, run_id: UUID) -> CalculationRun:
        """Return a **deep copy** of the run."""
        try:
            return copy.deepcopy(self._by_id[run_id])
        except KeyError as err:
            raise KeyError(f"CalculationRun not found: {run_id}") from err

    def update(self, run: CalculationRun) -> None:
        """Replace the stored run record with strict invariant checks.

        Validates:
        1. State transition is legal.
        2. Immutable identity fields have not changed.
        3. Status-dependent invariants are satisfied.

        Stores a **deep copy**.

        Raises
        ------
        KeyError
            If no run with ``run.run_id`` exists in the store.
        InvalidStateTransitionError
            If the new status is not reachable from the stored status.
        IntegrityError-like ValueError
            If immutable fields are changed or invariants are violated.
        """
        stored = self._by_id.get(run.run_id)
        if stored is None:
            raise KeyError(f"CalculationRun not found: {run.run_id}")

        # 1. State transition
        from hexagent.domain.revisions import is_valid_transition
        if not is_valid_transition(stored.status, run.status):
            raise InvalidStateTransitionError(stored.status, run.status)

        # 2. Immutable identity fields
        for field_name in _IMMUTABLE_RUN_FIELDS:
            old_val = getattr(stored, field_name)
            new_val = getattr(run, field_name)
            if old_val != new_val:
                raise ValueError(
                    f"Cannot change immutable field '{field_name}' "
                    f"during update: {old_val!r} → {new_val!r}"
                )

        # 3. Status-dependent invariants
        _validate_run_invariants(run)

        snapshot = copy.deepcopy(run)
        self._by_id[run.run_id] = snapshot

    def list_by_revision(self, revision_id: UUID) -> tuple[CalculationRun, ...]:
        """Return deep copies of all runs ordered by creation time ASC."""
        run_ids = self._by_revision.get(revision_id, ())
        if not run_ids:
            return ()
        runs = [self._by_id[rid] for rid in run_ids]
        return tuple(copy.deepcopy(r) for r in sorted(runs, key=lambda r: r.started_at))


# ---------------------------------------------------------------------------
# Run invariant validation (centralised)
# ---------------------------------------------------------------------------



def _validate_run_invariants(run: CalculationRun) -> None:
    """Validate status-dependent invariants on a CalculationRun.

    Raises ``ValueError`` if invariants are violated.
    """
    status = run.status

    # SUCCEEDED: must have a real result_hash
    if status == CalculationRunStatus.SUCCEEDED:
        if not run.result_hash or not _is_valid_hash(run.result_hash):
            raise ValueError(
                "SUCCEEDED run must have a valid result_hash "
                f"(got {run.result_hash!r})"
            )
        if run.failure is not None:
            raise ValueError("SUCCEEDED run must not have a failure record")

    # FAILED: must have a failure record
    if status == CalculationRunStatus.FAILED:
        if run.failure is None:
            raise ValueError("FAILED run must have a failure record")
        if run.result_hash and _is_valid_hash(run.result_hash):
            raise ValueError("FAILED run must not have a valid result_hash")

    # BLOCKED: must have at least one blocker
    if status == CalculationRunStatus.BLOCKED and not run.blockers:
        raise ValueError("BLOCKED run must have at least one blocker")

    # Terminal states must have completed_at
    if status in (
        CalculationRunStatus.SUCCEEDED,
        CalculationRunStatus.FAILED,
        CalculationRunStatus.BLOCKED,
        CalculationRunStatus.CANCELLED,
    ):
        if run.completed_at is None:
            raise ValueError(
                f"Terminal status {status.value} requires completed_at"
            )
        if run.completed_at <= run.started_at:
            raise ValueError(
                f"completed_at ({run.completed_at}) must be after "
                f"started_at ({run.started_at})"
            )

    # Non-terminal: must NOT have completed_at
    non_terminal = status in (CalculationRunStatus.PENDING, CalculationRunStatus.RUNNING)
    if non_terminal and run.completed_at is not None:
        raise ValueError(
            f"Non-terminal status {status.value} must not have completed_at"
        )


def _is_valid_hash(h: str) -> bool:
    """Return True if *h* is a valid ``sha256:<64-hex>`` string."""
    if not h.startswith("sha256:"):
        return False
    hex_part = h[7:]
    if len(hex_part) != 64:
        return False
    try:
        int(hex_part, 16)
        return True
    except ValueError:
        return False


__all__ = [
    "InMemoryCalculationRunRepository",
    "InMemoryDesignCaseRevisionRepository",
]
