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

Slice C scope (TASK-018 implementation round 3):
    - ``life_cycle_energy_estimator`` — deterministic life-cycle energy /
      OPEX envelope application layer (TASK-018 §5.3).  Consumes the Slice B
      ``CostBreakdown`` envelope plus the TASK-008 / TASK-017 thermal
      summary and the §5.3.1 caller-supplied inputs and produces the
      §5.3.2 ``LifeCycleEnergyBreakdown`` with deterministic UUID v5
      ``life_cycle_run_id``, integer minor units on monetary fields,
      deterministic IEEE-754 round-trip on ``*_kwh`` floats, closed-set
      blocker / warning propagation.
    - Discount formula handling: per §5.3.2 Rule 2 the frozen contract
      does NOT prescribe the discount formula.  Slice C implements under
      **Option A**: emit ``discounted_total_minor_units: null`` plus an
      ``unspecified_blocker`` with
      ``details.reason = "discount_formula_pending_design_amendment"``,
      following the §9 safety-net pattern.  A future TASK-018 §5.3
      design-amendment PR is required before a real discounted total can
      be computed; that amendment is NOT in this round.

Slice C does NOT include:
    - ``docs/TASK_BACKLOG.md`` mutation (governance-sync deferred to a
      separate Charles-authorized round; the Slice A + Slice B rows in
      the implementation sub-table are stale).
    - A discount formula (reserved for a future TASK-018 §5.3
      design-amendment PR).
    - Slice D / closeout.
    - TASK-019+ work.
    - TASK-018 design file mutation.
    - Frozen TASK-011..TASK-017 contracts mutation.
    - Currency conversion (TASK-018 §6.1: never converted).
    - C2 historical-project regression; C3 vendor quotation.
    - Pressure-drop / C4 logic.
    - A new entry on the closed-set blocker / warning enums:
      out-of-envelope ``fouling_energy_penalty_factor`` surfaces as
      ``unspecified_blocker`` with a structured
      ``details.reason = "fouling_energy_penalty_factor_out_of_envelope"``
      field, which is the §9 safety-net pattern for a runtime fault not
      present in the frozen closed set.  Adding a dedicated
      ``fouling_energy_penalty_factor_out_of_envelope_blocker`` requires a
      separate §9 design-amendment PR.

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
from .life_cycle_energy_estimator import (
    FOULING_ENERGY_PENALTY_MAX,
    FOULING_ENERGY_PENALTY_MIN,
    LIFECYCLE_SCHEMA_VERSION,
    LifeCycleEnergyBreakdown,
    LifeCycleEnergyEstimatorInput,
    SparesCostPerYear,
    ThermalServiceSummary,
    calculate_life_cycle_breakdown,
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
    "FOULING_ENERGY_PENALTY_MAX",
    "FOULING_ENERGY_PENALTY_MIN",
    "LIFECYCLE_SCHEMA_VERSION",
    "LifeCycleEnergyBreakdown",
    "LifeCycleEnergyEstimatorInput",
    "SCHEMA_VERSION",
    "SOURCE_CURRENCY_SENTINEL",
    "SparesCostPerYear",
    "SelectionFilters",
    "ThermalServiceSummary",
    "WARNING_CODES",
    "WarningCode",
    "calculate_cost_breakdown",
    "calculate_life_cycle_breakdown",
    "select_cost_records",
]  # noqa: F822
