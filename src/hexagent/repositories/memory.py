"""In-memory repository implementations for development and testing.

All state lives in plain Python dicts.  Ordering is deterministic: revisions
are sorted by ``revision_number``, runs by ``created_at``.
"""
from __future__ import annotations

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
# State-transition table for CalculationRun
# ---------------------------------------------------------------------------
_VALID_TRANSITIONS: dict[CalculationRunStatus, frozenset[CalculationRunStatus]] = {
    CalculationRunStatus.PENDING: frozenset({
        CalculationRunStatus.RUNNING,
        CalculationRunStatus.CANCELLED,
    }),
    CalculationRunStatus.RUNNING: frozenset({
        CalculationRunStatus.SUCCEEDED,
        CalculationRunStatus.FAILED,
        CalculationRunStatus.BLOCKED,
        CalculationRunStatus.CANCELLED,
    }),
    CalculationRunStatus.SUCCEEDED: frozenset(),
    CalculationRunStatus.FAILED: frozenset(),
    CalculationRunStatus.BLOCKED: frozenset(),
    CalculationRunStatus.CANCELLED: frozenset(),
}


def is_valid_transition(current: CalculationRunStatus, target: CalculationRunStatus) -> bool:
    """Return True if *target* is reachable from *current*."""
    return target in _VALID_TRANSITIONS.get(current, frozenset())


# ---------------------------------------------------------------------------
# DesignCaseRevision repository
# ---------------------------------------------------------------------------


class InMemoryDesignCaseRevisionRepository:
    """Dict-backed store for :class:`DesignCaseRevision` objects."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, DesignCaseRevision] = {}
        self._by_case: dict[UUID, dict[int, DesignCaseRevision]] = {}

    # -- public API ----------------------------------------------------------

    def add(self, revision: DesignCaseRevision) -> None:
        """Persist a new revision with full constraint checking.

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

        # 4. Store
        self._by_id[revision.revision_id] = revision
        case_rev_map[revision.revision_number] = revision

    def get(self, revision_id: UUID) -> DesignCaseRevision:
        """Return the revision with the given *revision_id*."""
        try:
            return self._by_id[revision_id]
        except KeyError as err:
            raise KeyError(f"DesignCaseRevision not found: {revision_id}") from err

    def latest(self, case_id: UUID) -> DesignCaseRevision | None:
        """Return the most recent revision for *case_id*, or ``None``."""
        case_rev_map = self._by_case.get(case_id)
        if not case_rev_map:
            return None
        latest_number = max(case_rev_map)
        return case_rev_map[latest_number]

    def list_by_case(self, case_id: UUID) -> tuple[DesignCaseRevision, ...]:
        """Return all revisions for *case_id* ordered by revision_number ASC."""
        case_rev_map = self._by_case.get(case_id)
        if not case_rev_map:
            return ()
        return tuple(case_rev_map[n] for n in sorted(case_rev_map))


# ---------------------------------------------------------------------------
# CalculationRun repository
# ---------------------------------------------------------------------------


class InMemoryCalculationRunRepository:
    """Dict-backed store for :class:`CalculationRun` objects."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, CalculationRun] = {}
        self._by_revision: dict[UUID, list[UUID]] = {}  # revision_id → [run_id, …]

    # -- public API ----------------------------------------------------------

    def add(self, run: CalculationRun) -> None:
        """Persist a new run with duplicate-ID checking.

        Raises
        ------
        DuplicateIdError
            If a run with the same ``run_id`` already exists.
        """
        if run.run_id in self._by_id:
            raise DuplicateIdError("CalculationRun", str(run.run_id))

        self._by_id[run.run_id] = run
        self._by_revision.setdefault(run.case_revision_id, []).append(run.run_id)

    def get(self, run_id: UUID) -> CalculationRun:
        """Return the run with the given *run_id*."""
        try:
            return self._by_id[run_id]
        except KeyError as err:
            raise KeyError(f"CalculationRun not found: {run_id}") from err

    def update(self, run: CalculationRun) -> None:
        """Replace the stored run record with state-transition validation.

        The new run's ``status`` must be reachable from the stored run's
        current ``status`` per the state-machine definition.

        Raises
        ------
        KeyError
            If no run with ``run.run_id`` exists in the store.
        InvalidStateTransitionError
            If the new status is not reachable from the stored status.
        """
        stored = self._by_id.get(run.run_id)
        if stored is None:
            raise KeyError(f"CalculationRun not found: {run.run_id}")

        if not is_valid_transition(stored.status, run.status):
            raise InvalidStateTransitionError(stored.status, run.status)

        self._by_id[run.run_id] = run

    def list_by_revision(self, revision_id: UUID) -> tuple[CalculationRun, ...]:
        """Return all runs for *revision_id* ordered by creation time ASC."""
        run_ids = self._by_revision.get(revision_id, ())
        if not run_ids:
            return ()
        runs = [self._by_id[rid] for rid in run_ids]
        return tuple(sorted(runs, key=lambda r: r.started_at))


__all__ = [
    "InMemoryCalculationRunRepository",
    "InMemoryDesignCaseRevisionRepository",
    "is_valid_transition",
]
