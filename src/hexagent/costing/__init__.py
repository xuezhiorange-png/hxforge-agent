"""TASK-018 implementation — cost application layer (C0/C1).

Read-only consumer of the TASK-013 cost-data governance layer and the
TASK-017 mass / mechanical application layer outputs. This package
implements the application-layer contracts specified in
``docs/tasks/TASK-018-c0-c1-cost-and-life-cycle-energy.md``
(Frozen Contract Authority Commit SHA ``19200bf1a3c5d86b6b6129a3fc78c820ff9d3fa8``,
Base SHA ``5f96cf761d470b82faa1a5d164eefd42360c7df9``).

Slice A scope (TASK-018 implementation round 1):
    - ``cost_model_selector`` — read-only deterministic selection of TASK-013
      cost records for the CostModelSelector contract (TASK-018 §5.1).
    - ``errors`` — closed-set error / warning code enumeration
      (TASK-018 §9).

Slice A does NOT include:
    - CostCalculator (TASK-018 §5.2) — Slice B, separate authorization.
    - LifeCycleEnergyEstimator (TASK-018 §5.3) — Slice C, separate authorization.
    - CAPEX / OPEX / C0 / C1 subtotal computation.
    - Currency conversion, escalation math, region-specific tax/installation.
    - C2 history-project regression; C3 vendor quotation.
    - Pressure-drop / C4 logic.

All public entry points are read-only with respect to the TASK-013 cost
records they consume; no caller-supplied record mutation is performed
inside this package.
"""

from .cost_model_selector import (
    SCHEMA_VERSION,
    CostModelSelectionResult,
    CostModelSelector,
    SelectionFilters,
    select_cost_records,
)
from .errors import (
    BLOCKER_CODES,
    WARNING_CODES,
    BlockerCode,
    CostSelectorError,
    CostSelectorWarning,
    WarningCode,
)

__all__ = [
    "BLOCKER_CODES",
    "BlockerCode",
    "CostModelSelectionResult",
    "CostModelSelector",
    "CostSelectorError",
    "CostSelectorWarning",
    "SCHEMA_VERSION",
    "SelectionFilters",
    "WARNING_CODES",
    "WarningCode",
    "select_cost_records",
]  # noqa: F822
