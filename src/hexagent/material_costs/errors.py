"""Typed errors for material/cost data governance runtime (TASK-013).

Implements the TASK-013 frozen design contract
(docs/tasks/TASK-013-material-cost-data-governance.md,
Frozen Contract Authority SHA
``ee7aa092bca854316be961b536c7a121490aa385``):

* Section 14 — deterministic selectors that fail closed with a
  structured ``MaterialNotFound`` / ``CostNotFound`` error referencing
  record id, region, and selection time.
* Section 15 — structural separation of blockers vs warnings; CI
  MUST NOT downgrade a blocker to a warning.

The validation functions in :mod:`hexagent.material_costs.validation`
return a ``ValidationResult`` carrying separate ``blockers`` and
``warnings`` collections; only true failures of the determinism /
license / hash gates raise exceptions. Selection functions raise
``MaterialNotFound`` / ``CostNotFound`` for the structured fail-closed
case.
"""

from __future__ import annotations


class MaterialCostError(Exception):
    """Base class for material/cost data governance runtime errors."""


class MaterialCostValidationError(MaterialCostError):
    """Raised when a material or cost record fails a structural
    validation gate that the design contract explicitly classifies as
    a blocker (Section 15).

    The ``path`` attribute identifies the offending field path so
    machine-readable error reports can locate the failure.
    """

    def __init__(self, message: str, *, path: str = "") -> None:
        super().__init__(message)
        self.path = path


class MaterialNotFound(MaterialCostError):
    """Raised by :func:`hexagent.material_costs.selection.select_material_record`
    when no record satisfies the deterministic selection chain
    (Section 14). The error carries the search key, region, and
    selection time so callers can render a structured fail-closed
    response.
    """

    def __init__(
        self,
        material_record_id: str,
        *,
        region: str,
        selection_time: str,
        reason: str,
        rejected_candidate_count: int = 0,
    ) -> None:
        super().__init__(
            "MaterialNotFound: no material record matched "
            f"material_record_id={material_record_id!r} "
            f"region={region!r} selection_time={selection_time!r} "
            f"reason={reason!r} rejected_candidate_count={rejected_candidate_count}"
        )
        self.material_record_id = material_record_id
        self.region = region
        self.selection_time = selection_time
        self.reason = reason
        self.rejected_candidate_count = rejected_candidate_count


class CostNotFound(MaterialCostError):
    """Raised by :func:`hexagent.material_costs.selection.select_cost_record`
    when no record satisfies the deterministic selection chain
    (Section 14). Mirrors :class:`MaterialNotFound` for cost records.
    """

    def __init__(
        self,
        cost_record_id: str,
        *,
        region: str,
        selection_time: str,
        reason: str,
        rejected_candidate_count: int = 0,
    ) -> None:
        super().__init__(
            "CostNotFound: no cost record matched "
            f"cost_record_id={cost_record_id!r} "
            f"region={region!r} selection_time={selection_time!r} "
            f"reason={reason!r} rejected_candidate_count={rejected_candidate_count}"
        )
        self.cost_record_id = cost_record_id
        self.region = region
        self.selection_time = selection_time
        self.reason = reason
        self.rejected_candidate_count = rejected_candidate_count


__all__ = [
    "CostNotFound",
    "MaterialCostError",
    "MaterialCostValidationError",
    "MaterialNotFound",
]
