"""TASK-013 material / cost data governance runtime.

Implements the TASK-013 frozen design contract
(docs/tasks/TASK-013-material-cost-data-governance.md,
Frozen Contract Authority SHA
``ee7aa092bca854316be961b536c7a121490aa385``):

* Typed models and closed-set enums (Section 4 / 5 / 6 / 12 / 13).
* Schema validation for material / cost records (Section 5 / 6 / 10).
* License boundary enforcement (Section 9 + TASK-012 Section 5 / 7.2).
* Canonical SHA-256 hashing via the shared
  :mod:`hexagent.canonical_json` helper (Section 16).
* Approval-state gate validation (Section 13).
* Deterministic material / cost record selection (Section 14).
* Structured blocker / warning validation output (Section 15).
* Catalog loader and CLI entry point (``python -m
  hexagent.material_costs.validate``) for in-memory validation of a
  catalog directory.

No persistence layer, no DB / ORM / migration, no public HTTP / RPC
/ API change, no engineering correlation or solver code, no
pressure-drop / C4 / shell-and-tube / plate / air-cooler / two-phase
/ refrigerant logic is implemented here; those are explicitly
out-of-scope per TASK-013 Section 21.
"""

from __future__ import annotations

from hexagent.material_costs.errors import (
    CostNotFound,
    MaterialCostError,
    MaterialCostValidationError,
    MaterialNotFound,
)
from hexagent.material_costs.models import (
    APPROVAL_GATE_ORDER,
    ESCALATION_INDEX_CATEGORIES,
    SOURCE_CLASSES_REQUIRE_USAGE_SCOPE,
    VALUE_CARRYING_SOURCE_CLASSES,
    ApprovalState,
    CostBasis,
    CostCategory,
    CostRecord,
    CostValue,
    EngineeringPropertyDescriptor,
    FormFactor,
    HumanEnteredEvidence,
    IssuingBody,
    MaterialFamily,
    MaterialRecord,
    PropertyValue,
    QualityFlag,
    QuantityBasis,
    SourceClass,
    StandardOrSpecReference,
)
from hexagent.material_costs.selection import (
    select_cost_record,
    select_material_record,
)
from hexagent.material_costs.validation import (
    ValidationIssue,
    ValidationResult,
    validate_cost_record,
    validate_material_record,
)

__all__ = [
    "APPROVAL_GATE_ORDER",
    "ApprovalState",
    "CostBasis",
    "CostCategory",
    "CostNotFound",
    "CostRecord",
    "CostValue",
    "ESCALATION_INDEX_CATEGORIES",
    "EngineeringPropertyDescriptor",
    "FormFactor",
    "HumanEnteredEvidence",
    "IssuingBody",
    "MaterialCostError",
    "MaterialCostValidationError",
    "MaterialFamily",
    "MaterialNotFound",
    "MaterialRecord",
    "PropertyValue",
    "QualityFlag",
    "QuantityBasis",
    "SOURCE_CLASSES_REQUIRE_USAGE_SCOPE",
    "SourceClass",
    "StandardOrSpecReference",
    "VALUE_CARRYING_SOURCE_CLASSES",
    "ValidationIssue",
    "ValidationResult",
    "select_cost_record",
    "select_material_record",
    "validate_cost_record",
    "validate_material_record",
]
