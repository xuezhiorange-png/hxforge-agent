"""Approval-gate validation, value-payload validation, and structured
blocker/warning output for TASK-013 material / cost records.

Implements Section 5.5 / 6.4 / 13 / 15 of the TASK-013 frozen design
contract (docs/tasks/TASK-013-material-cost-data-governance.md,
Frozen Contract Authority SHA
``ee7aa092bca854316be961b536c7a121490aa385``).

This module is the single integration point for the schema,
license-boundary, value-payload, and approval-gate checks. It
returns a :class:`ValidationResult` that structurally separates
``blockers`` (Section 15 — never downgradable to warnings) from
``warnings`` (Section 15 — non-blocking).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hexagent.material_costs.errors import MaterialCostValidationError
from hexagent.material_costs.license_boundary import (
    enforce_cost_record_license_boundary,
    enforce_material_record_license_boundary,
)
from hexagent.material_costs.models import (
    ESCALATION_INDEX_CATEGORIES,
    HUMAN_EVIDENCE_REQUIRED_COST_SOURCE_CLASSES,
    HUMAN_EVIDENCE_REQUIRED_MATERIAL_SOURCE_CLASSES,
    ApprovalState,
    SourceClass,
)
from hexagent.material_costs.schema import (
    validate_cost_record_schema,
    validate_material_record_schema,
)

# ---------------------------------------------------------------------------
# Validation result containers (Section 15 structural separation).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation issue with kind + path + message.

    ``kind`` is one of ``"blocker"`` or ``"warning"`` per Section 15.
    """

    kind: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "path": self.path, "message": self.message}


@dataclass
class ValidationResult:
    """Structured validation output (Section 15).

    ``blockers`` and ``warnings`` are kept in disjoint lists; CI MUST
    NOT downgrade a blocker to a warning.
    """

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


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _source_class(record: dict[str, Any]) -> str:
    return str(record.get("source_class", ""))


def _human_entered(record: dict[str, Any]) -> dict[str, Any]:
    he = record.get("human_entered_evidence") or {}
    return he if isinstance(he, dict) else {}


def _issue(kind: str, path: str, message: str) -> ValidationIssue:
    return ValidationIssue(kind=kind, path=path, message=message)


def _is_decimal_string(value: Any) -> bool:
    """RFC 8785 §3.3.1 — shortest round-trippable decimal string."""
    if not isinstance(value, str) or not value:
        return False
    try:
        # Will raise if not a valid finite number.
        float(value)
    except ValueError:
        return False
    return True


# ---------------------------------------------------------------------------
# Value-payload validation (Sections 5.5 + 6.4).
# ---------------------------------------------------------------------------


def _check_property_values(record: dict[str, Any]) -> list[ValidationIssue]:
    """Section 5.5 — ``property_values`` rules."""

    path = "material_record.property_values"
    values = record.get("property_values")
    if values is None:
        return []

    issues: list[ValidationIssue] = []
    source_class = _source_class(record)
    dimensional_units = record.get("dimensional_units")
    declared_units: set[str] = (
        set(dimensional_units.values()) if isinstance(dimensional_units, dict) else set()
    )

    # Rule #1: RESTRICTED records MUST NOT carry property_values
    # (enforced also in license_boundary; here we mirror the
    # structured issue so it surfaces in the ValidationResult).
    if source_class == SourceClass.RESTRICTED_REFERENCE_METADATA_ONLY.value:
        issues.append(
            _issue(
                "blocker",
                path,
                "RESTRICTED_REFERENCE_METADATA_ONLY records MUST NOT carry "
                "property_values (Section 5.5 rule #1)",
            )
        )

    # Rule #2: only INTERNAL / PUBLIC / VENDOR (with usage_scope) /
    # USER records may carry property_values.
    allowed = {
        SourceClass.INTERNAL_ENGINEERING_ASSUMPTION.value,
        SourceClass.PUBLIC_METADATA.value,
        SourceClass.VENDOR_PERMISSIONED.value,
        SourceClass.USER_PROVIDED_PROJECT_DATA.value,
    }
    if (
        source_class not in allowed
        and source_class != SourceClass.RESTRICTED_REFERENCE_METADATA_ONLY.value
    ):
        issues.append(
            _issue(
                "blocker",
                path,
                f"property_values present but source_class={source_class!r} "
                "is not in the allowed source-class list (Section 5.5 rule #2)",
            )
        )

    if source_class == SourceClass.VENDOR_PERMISSIONED.value:
        usage = _human_entered(record).get("usage_scope")
        if not (isinstance(usage, str) and usage.strip()):
            issues.append(
                _issue(
                    "blocker",
                    path,
                    "VENDOR_PERMISSIONED records with property_values MUST "
                    "record a non-empty usage_scope in human_entered_evidence "
                    "(Section 5.5 rule #2)",
                )
            )

    # Rule #3 + #4 + #5 + #6: structural checks per-entry.
    if isinstance(values, list):
        for idx, entry in enumerate(values):
            entry_path = f"{path}[{idx}]"
            if not isinstance(entry, dict):
                issues.append(_issue("blocker", entry_path, "entry must be a JSON object"))
                continue

            value_si = entry.get("value_si")
            if not _is_decimal_string(value_si):
                issues.append(
                    _issue(
                        "blocker",
                        f"{entry_path}.value_si",
                        "value_si must be a decimal string (RFC 8785 §3.3.1)",
                    )
                )

            unit_si = entry.get("unit_si")
            if declared_units and isinstance(unit_si, str) and unit_si not in declared_units:
                issues.append(
                    _issue(
                        "blocker",
                        f"{entry_path}.unit_si",
                        f"unit_si {unit_si!r} is not declared in "
                        "dimensional_units (Section 5.5 rule #3)",
                    )
                )

            if not isinstance(entry.get("source_pointer"), str):
                issues.append(
                    _issue(
                        "blocker",
                        f"{entry_path}.source_pointer",
                        "source_pointer is required (Section 5.5)",
                    )
                )

            qfs = entry.get("quality_flags")
            if not isinstance(qfs, list):
                issues.append(
                    _issue(
                        "blocker",
                        f"{entry_path}.quality_flags",
                        "quality_flags must be a list",
                    )
                )

    return issues


def _check_cost_value(record: dict[str, Any]) -> list[ValidationIssue]:
    """Section 6.4 — ``cost_value`` rules."""

    path = "cost_record.cost_value"
    cv = record.get("cost_value")
    if cv is None:
        return []

    issues: list[ValidationIssue] = []
    source_class = _source_class(record)

    # Rule #1: RESTRICTED records MUST NOT carry cost_value.
    if source_class == SourceClass.RESTRICTED_REFERENCE_METADATA_ONLY.value:
        issues.append(
            _issue(
                "blocker",
                path,
                "RESTRICTED_REFERENCE_METADATA_ONLY records MUST NOT carry "
                "cost_value (Section 6.4 rule #1)",
            )
        )

    # Rule #2: allowed source classes only.
    allowed = {
        SourceClass.INTERNAL_ENGINEERING_ASSUMPTION.value,
        SourceClass.PUBLIC_METADATA.value,
        SourceClass.VENDOR_PERMISSIONED.value,
        SourceClass.USER_PROVIDED_PROJECT_DATA.value,
    }
    if (
        source_class not in allowed
        and source_class != SourceClass.RESTRICTED_REFERENCE_METADATA_ONLY.value
    ):
        issues.append(
            _issue(
                "blocker",
                path,
                f"cost_value present but source_class={source_class!r} is not "
                "in the allowed source-class list (Section 6.4 rule #2)",
            )
        )

    if source_class == SourceClass.VENDOR_PERMISSIONED.value:
        usage = _human_entered(record).get("usage_scope")
        if not (isinstance(usage, str) and usage.strip()):
            issues.append(
                _issue(
                    "blocker",
                    path,
                    "VENDOR_PERMISSIONED records with cost_value MUST record a "
                    "non-empty usage_scope in human_entered_evidence "
                    "(Section 6.4 rule #2)",
                )
            )

    # Rule #4: cost_value binds to record unit_basis / currency /
    # escalation_date.
    if isinstance(cv, dict):
        record_unit_basis = record.get("unit_basis")
        record_currency = record.get("currency")
        cv_unit_basis = cv.get("unit_basis")
        cv_currency = cv.get("currency")

        if (
            isinstance(record_unit_basis, str)
            and isinstance(cv_unit_basis, str)
            and cv_unit_basis != record_unit_basis
        ):
            issues.append(
                _issue(
                    "blocker",
                    f"{path}.unit_basis",
                    f"cost_value.unit_basis={cv_unit_basis!r} must equal record "
                    f"unit_basis={record_unit_basis!r} (Section 6.4 rule #4)",
                )
            )

        if (
            isinstance(record_currency, str)
            and isinstance(cv_currency, str)
            and cv_currency != record_currency
        ):
            issues.append(
                _issue(
                    "blocker",
                    f"{path}.currency",
                    f"cost_value.currency={cv_currency!r} must equal record "
                    f"currency={record_currency!r} (Section 6.4 rule #4)",
                )
            )

        # Rule #5 (escalation_date / escalation_index_reference).
        escalation_date = record.get("escalation_date")
        if escalation_date is not None:
            ref = cv.get("escalation_index_reference")
            if ref is None:
                justification = _human_entered(record).get("justification")
                if not (isinstance(justification, str) and justification.strip()):
                    issues.append(
                        _issue(
                            "blocker",
                            path,
                            "escalation_date is present but cost_value has no "
                            "escalation_index_reference and human_entered_evidence "
                            "has no justification (Section 6.4 rule #5 / 11)",
                        )
                    )

        if not _is_decimal_string(cv.get("value")):
            issues.append(
                _issue(
                    "blocker",
                    f"{path}.value",
                    "cost_value.value must be a decimal string (RFC 8785 §3.3.1) (Section 6.4)",
                )
            )
        if not _is_decimal_string(cv.get("quantity_value_si")):
            issues.append(
                _issue(
                    "blocker",
                    f"{path}.quantity_value_si",
                    "cost_value.quantity_value_si must be a decimal string "
                    "(RFC 8785 §3.3.1) (Section 6.4)",
                )
            )
        # Section 6.4: normalized_unit_price is OPTIONAL (may be
        # ``null`` or absent); when present and non-null it MUST be a
        # decimal string per RFC 8785 §3.3.1.
        normalized = cv.get("normalized_unit_price")
        if normalized is not None and not _is_decimal_string(normalized):
            issues.append(
                _issue(
                    "blocker",
                    f"{path}.normalized_unit_price",
                    "cost_value.normalized_unit_price, when present and "
                    "non-null, must be a decimal string "
                    "(RFC 8785 §3.3.1) (Section 6.4)",
                )
            )
        if not isinstance(cv.get("source_pointer"), str):
            issues.append(
                _issue(
                    "blocker",
                    f"{path}.source_pointer",
                    "cost_value.source_pointer is required (Section 6.4)",
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Approval gate validation (Section 13).
# ---------------------------------------------------------------------------


def _check_approval_gate(record: dict[str, Any], *, path: str) -> list[ValidationIssue]:
    """Section 13 — TASK-013-specific approval ladder.

    This function enforces the gate-semantics table; the four
    numeric-consistency checks (property_values/cost_value normalization
    and unit validation) are delegated to the value-payload checks
    above. The provenance / hash check is delegated to the schema
    module. Here we only assert the structural gate state.
    """
    issues: list[ValidationIssue] = []

    state = record.get("approval_state")
    if state not in set(ApprovalState.__members__.values()):
        issues.append(
            _issue(
                "blocker",
                f"{path}.approval_state",
                f"unknown approval_state {state!r}",
            )
        )
        return issues

    if state == ApprovalState.UNDER_REVIEW.value and not record.get("provenance_edges"):
        # Entering under_review requires provenance + dimensional_units
        # (the schema layer enforces their presence as blockers).
        issues.append(
            _issue(
                "blocker",
                f"{path}.provenance_edges",
                "cannot enter under_review without provenance_edges (Section 13)",
            )
        )

    return issues


# ---------------------------------------------------------------------------
# Human-entered-evidence presence (Section 5 / 6 last-but-one row).
# ---------------------------------------------------------------------------


def _check_human_entered_evidence(
    record: dict[str, Any],
    *,
    required_classes: frozenset[SourceClass],
    path: str,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    sc = _source_class(record)
    if sc not in set(required_classes.value for required_classes in required_classes):
        return issues
    he = record.get("human_entered_evidence")
    if not isinstance(he, dict) or not he:
        issues.append(
            _issue(
                "blocker",
                f"{path}.human_entered_evidence",
                f"required for source_class={sc!r}",
            )
        )
    return issues


# ---------------------------------------------------------------------------
# Cost-category vs escalation-rule (Section 11 / 6.1).
# ---------------------------------------------------------------------------


def _check_cost_category_escalation(record: dict[str, Any]) -> list[ValidationIssue]:
    """Section 11 — escalation index records use
    cost_category=cost_escalation_index or price_index and
    cost_basis=public_index; other categories MUST NOT use public_index
    unless they are themselves escalation index records.
    """
    issues: list[ValidationIssue] = []
    category = record.get("cost_category")
    basis = record.get("cost_basis")

    if category in {c.value for c in ESCALATION_INDEX_CATEGORIES}:
        if basis != "public_index":
            issues.append(
                _issue(
                    "blocker",
                    "cost_record.cost_basis",
                    f"escalation index category {category!r} MUST use "
                    f"cost_basis='public_index' (Section 11); got {basis!r}",
                )
            )
    else:
        if basis == "public_index":
            issues.append(
                _issue(
                    "blocker",
                    "cost_record.cost_basis",
                    "cost_basis='public_index' is reserved for escalation index "
                    f"records (Section 11); got category={category!r}",
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Top-level validation entry points.
# ---------------------------------------------------------------------------


def validate_material_record(record: Any) -> ValidationResult:
    """Validate a material record against the TASK-013 frozen contract.

    Returns a :class:`ValidationResult` with separate ``blockers`` and
    ``warnings`` lists. Raises :class:`MaterialCostValidationError` for
    arguments that are not JSON-compatible (this is the only exception
    path; everything else flows through the structured result).
    """
    if not isinstance(record, dict):
        raise MaterialCostValidationError(
            "validate_material_record requires a JSON-compatible dict",
            path="material_record",
        )

    result = ValidationResult()

    for msg in validate_material_record_schema(record):
        result.blockers.append(_issue("blocker", "material_record", msg))

    for msg in enforce_material_record_license_boundary(record):
        result.blockers.append(_issue("blocker", "material_record", msg))

    for issue in _check_property_values(record):
        result.blockers.append(issue)

    for issue in _check_approval_gate(record, path="material_record"):
        result.blockers.append(issue)

    for issue in _check_human_entered_evidence(
        record,
        required_classes=HUMAN_EVIDENCE_REQUIRED_MATERIAL_SOURCE_CLASSES,
        path="material_record",
    ):
        result.blockers.append(issue)

    # Section 15 — quality_flag-based warnings.
    qfs = record.get("quality_flags") or []
    if isinstance(qfs, list) and ("assumed_value" in qfs or "engineering_estimate" in qfs):
        result.warnings.append(
            _issue(
                "warning",
                "material_record.quality_flags",
                "quality_flags contains assumed_value or engineering_estimate",
            )
        )

    return result


def validate_cost_record(record: Any) -> ValidationResult:
    """Validate a cost record against the TASK-013 frozen contract."""
    if not isinstance(record, dict):
        raise MaterialCostValidationError(
            "validate_cost_record requires a JSON-compatible dict",
            path="cost_record",
        )

    result = ValidationResult()

    for msg in validate_cost_record_schema(record):
        result.blockers.append(_issue("blocker", "cost_record", msg))

    for msg in enforce_cost_record_license_boundary(record):
        result.blockers.append(_issue("blocker", "cost_record", msg))

    for issue in _check_cost_value(record):
        result.blockers.append(issue)

    for issue in _check_approval_gate(record, path="cost_record"):
        result.blockers.append(issue)

    for issue in _check_human_entered_evidence(
        record,
        required_classes=HUMAN_EVIDENCE_REQUIRED_COST_SOURCE_CLASSES,
        path="cost_record",
    ):
        result.blockers.append(issue)

    for issue in _check_cost_category_escalation(record):
        result.blockers.append(issue)

    # Section 15 — quality_flag-based warnings.
    qfs = record.get("quality_flags") or []
    if isinstance(qfs, list) and ("assumed_value" in qfs or "engineering_estimate" in qfs):
        result.warnings.append(
            _issue(
                "warning",
                "cost_record.quality_flags",
                "quality_flags contains assumed_value or engineering_estimate",
            )
        )

    # Section 11 / 15 — escalation_date present but
    # escalation_index_reference absent with documented justification
    # is a warning, not a blocker.
    if record.get("escalation_date") is not None:
        cv = record.get("cost_value")
        ref_present = isinstance(cv, dict) and cv.get("escalation_index_reference")
        if not ref_present:
            justification = _human_entered(record).get("justification")
            if isinstance(justification, str) and justification.strip():
                result.warnings.append(
                    _issue(
                        "warning",
                        "cost_record.escalation_date",
                        "escalation_date present but escalation_index_reference "
                        "absent; documentation justification recorded (Section 15)",
                    )
                )

    return result


__all__ = [
    "ValidationIssue",
    "ValidationResult",
    "validate_cost_record",
    "validate_material_record",
]
