"""Repository protocol definitions for design-case revisions and calculation runs.

These are pure *structural* protocols (duck-typed interfaces) that decouple
application services from persistence.  Any concrete store — in-memory,
PostgreSQL, Redis — must satisfy these contracts.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from hexagent.domain.revisions import (
    CalculationRun,
    DesignCaseRevision,
)


@runtime_checkable
class DesignCaseRevisionRepository(Protocol):
    """Persistence interface for :class:`DesignCaseRevision` objects."""

    def add(self, revision: DesignCaseRevision) -> None:
        """Persist a new revision.

        Raises
        ------
        DuplicateIdError
            If an entity with the same ``revision_id`` already exists.
        RevisionNumberConflictError
            If a revision for the same ``case_id`` with the same
            ``revision_number`` already exists.
        MissingParentError
            If ``revision.parent_revision_id`` is set but the parent does
            not exist in the store.
        """
        ...

    def get(self, revision_id: UUID) -> DesignCaseRevision:
        """Return the revision with the given *revision_id*.

        Raises
        ------
        KeyError
            If no such revision exists.
        """
        ...

    def latest(self, case_id: UUID) -> DesignCaseRevision | None:
        """Return the most recent revision for *case_id*, or ``None``."""
        ...

    def list_by_case(self, case_id: UUID) -> tuple[DesignCaseRevision, ...]:
        """Return all revisions for *case_id* ordered by ``revision_number`` ASC."""
        ...


@runtime_checkable
class CalculationRunRepository(Protocol):
    """Persistence interface for :class:`CalculationRun` objects."""

    def add(self, run: CalculationRun) -> None:
        """Persist a new run.

        Raises
        ------
        DuplicateIdError
            If an entity with the same ``run_id`` already exists.
        """
        ...

    def get(self, run_id: UUID) -> CalculationRun:
        """Return the run with the given *run_id*.

        Raises
        ------
        KeyError
            If no such run exists.
        """
        ...

    def update(self, run: CalculationRun) -> None:
        """Replace the stored run record.

        The implementation **must** validate state-machine transitions
        before accepting the update.

        Raises
        ------
        KeyError
            If no run with ``run.run_id`` exists.
        InvalidStateTransitionError
            If the new state is not reachable from the stored state.
        """
        ...

    def list_by_revision(self, revision_id: UUID) -> tuple[CalculationRun, ...]:
        """Return all runs for *revision_id* ordered by creation time ASC."""
        ...


__all__ = [
    "CalculationRunRepository",
    "DesignCaseRevisionRepository",
]
