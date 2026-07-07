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

Slice B scope (TASK-018 implementation round 2):
    - ``cost_calculator`` — deterministic C0/C1 cost breakdown
      application layer (TASK-018 §5.2).  Consumes the Slice A
      ``CostModelSelectionResult`` plus the TASK-017 ``MassBreakdown``
      envelope and produces the §5.2.2 ``CostBreakdown`` with integer
      minor units, deterministic UUID v5 ``calculator_run_id``,
      closed-set blocker / warning propagation.

Slice B does NOT include:
    - ``LifeCycleEnergyEstimator`` (TASK-018 §5.3) — Slice C,
      separate authorization.
    - Currency conversion (TASK-018 §6.1: never converted).
    - C2 historical-project regression; C3 vendor quotation.
    - Pressure-drop / C4 logic.
    - A new entry on the closed-set blocker / warning enums: out-of-envelope
      ``c0_heuristic_overrides`` surface as ``unspecified_blocker`` with a
      structured ``details.reason = "c0_heuristic_out_of_envelope"`` field,
      which is the §9 safety-net pattern for a runtime fault not present
      in the frozen closed set.  Adding a dedicated
      ``c0_heuristic_out_of_envelope_blocker`` requires a separate §9
      design-amendment PR.

All public entry points are read-only with respect to the TASK-013 cost
records they consume; no caller-supplied record mutation is performed
inside this package.
"""

from .cost_calculator import (
    CALCULATOR_SCHEMA_VERSION,
    SOURCE_CURRENCY_SENTINEL,
    ComponentSubtotalEntry,
    CostBreakdown,
    CostCalculatorInput,
    CostSubtotalBlock,
    calculate_cost_breakdown,
)
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
    "CALCULATOR_SCHEMA_VERSION",
    "ComponentSubtotalEntry",
    "CostBreakdown",
    "CostCalculatorInput",
    "CostModelSelectionResult",
    "CostModelSelector",
    "CostSelectorError",
    "CostSelectorWarning",
    "CostSubtotalBlock",
    "SCHEMA_VERSION",
    "SOURCE_CURRENCY_SENTINEL",
    "SelectionFilters",
    "WARNING_CODES",
    "WarningCode",
    "calculate_cost_breakdown",
    "select_cost_records",
]  # noqa: F822
