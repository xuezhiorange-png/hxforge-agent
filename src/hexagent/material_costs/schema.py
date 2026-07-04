"""Structural schema validation for TASK-013 material / cost records.

Implements Section 5 / 6 / 12 / 16 of the TASK-013 frozen design
contract (docs/tasks/TASK-013-material-cost-data-governance.md,
Frozen Contract Authority SHA
``ee7aa092bca854316be961b536c7a121490aa385``).

This module is intentionally narrow: it checks presence of required
fields, type / closed-set membership of every field, and the
content-addressable ``record_hash``. License-boundary enforcement,
approval-gate validation, and deterministic selection live in
:mod:`hexagent.material_costs.license_boundary`,
:mod:`hexagent.material_costs.validation`, and
:mod:`hexagent.material_costs.selection` respectively.
"""

from __future__ import annotations

import re
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.material_costs.errors import MaterialCostValidationError
from hexagent.material_costs.models import (
    COST_RECORD_REQUIRED_FIELDS,
    MATERIAL_RECORD_REQUIRED_FIELDS,
    CostBasis,
    CostCategory,
    FormFactor,
    MaterialFamily,
    QualityFlag,
    QuantityBasis,
    SourceClass,
)

_HASH_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_REGION_RE = re.compile(r"^[A-Z]{2}$")


def _ensure_dict(record: Any, *, path: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise MaterialCostValidationError(
            f"{path} must be a JSON object; got {type(record).__name__}",
            path=path,
        )
    return record


def _check_required_fields(
    record: dict[str, Any],
    *,
    required: frozenset[str],
    path: str,
) -> list[str]:
    """Return a list of missing required field names (blockers)."""
    missing = sorted(field for field in required if field not in record)
    return [f"{path}: missing required field {field!r}" for field in missing]


def _check_enum_value(
    field: str,
    value: Any,
    enum_cls: Any,
    *,
    path: str,
) -> list[str]:
    allowed = frozenset(enum_cls.__members__.values())
    if value not in allowed:
        return [f"{path}.{field}: unknown enum value {value!r}; expected one of {sorted(allowed)}"]
    return []


def _check_quality_flags(values: Any, *, path: str) -> list[str]:
    if not isinstance(values, list) or not values:
        return [f"{path}.quality_flags: must be a non-empty list of strings"]
    issues: list[str] = []
    for idx, flag in enumerate(values):
        if not isinstance(flag, str):
            issues.append(
                f"{path}.quality_flags[{idx}]: must be a string; got {type(flag).__name__}"
            )
            continue
        if flag not in set(QualityFlag.__members__.values()):
            issues.append(f"{path}.quality_flags[{idx}]: unknown quality flag {flag!r}")
    return issues


def _check_date(value: Any, *, field: str, path: str) -> list[str]:
    if not isinstance(value, str) or not _DATE_RE.match(value):
        return [f"{path}.{field}: must be RFC 3339 UTC with 'Z' suffix; got {value!r}"]
    return []


def _check_region(value: Any, *, path: str) -> list[str]:
    if not isinstance(value, str) or (value != "INTL" and not _REGION_RE.match(value)):
        return [f"{path}.region: must be ISO 3166-1 alpha-2 or 'INTL'; got {value!r}"]
    return []


def _check_property_value_shape(value: Any, *, path: str) -> list[str]:
    issues: list[str] = []
    if not isinstance(value, dict):
        return [f"{path}: property_values entries must be JSON objects"]
    required_subfields = ("property_name", "value_si", "unit_si", "source_pointer")
    for field in required_subfields:
        if field not in value:
            issues.append(f"{path}: missing required subfield {field!r}")
    if "quality_flags" not in value:
        issues.append(f"{path}: missing required subfield 'quality_flags'")
    return issues


def _compute_record_hash(record: dict[str, Any]) -> str:
    """Return SHA-256 hex digest of canonical JSON with ``record_hash``
    excluded (Section 16)."""
    without_hash = {key: item for key, item in record.items() if key != "record_hash"}
    return canonical_sha256(without_hash)


def _check_record_hash(record: dict[str, Any], *, path: str) -> list[str]:
    stored = record.get("record_hash")
    if not isinstance(stored, str) or not _HASH_HEX_RE.match(stored):
        return [f"{path}.record_hash: must be a 64-char lowercase hex string; got {stored!r}"]
    computed = _compute_record_hash(record)
    if computed != stored:
        return [f"{path}.record_hash: hash mismatch (stored={stored!r}, computed={computed!r})"]
    return []


def validate_material_record_schema(record: Any) -> list[str]:
    """Return a list of structural blocker issues (empty list = pass).

    This function performs only structural / closed-set / hash checks.
    License-boundary and approval-gate checks live in
    :mod:`hexagent.material_costs.validation`.
    """
    path = "material_record"
    record_d = _ensure_dict(record, path=path)
    issues: list[str] = []

    issues.extend(
        _check_required_fields(record_d, required=MATERIAL_RECORD_REQUIRED_FIELDS, path=path)
    )
    if issues:
        # Missing fields short-circuit the rest of the structural checks.
        return issues

    issues.extend(
        _check_enum_value("material_family", record_d["material_family"], MaterialFamily, path=path)
    )
    issues.extend(_check_enum_value("form_factor", record_d["form_factor"], FormFactor, path=path))
    issues.extend(
        _check_enum_value("source_class", record_d["source_class"], SourceClass, path=path)
    )
    issues.extend(_check_region(record_d["region"], path=path))
    issues.extend(_check_date(record_d["effective_date"], field="effective_date", path=path))
    retirement = record_d.get("retirement_date")
    if retirement is not None:
        issues.extend(_check_date(retirement, field="retirement_date", path=path))

    if not isinstance(record_d["dimensional_units"], dict):
        issues.append(
            f"{path}.dimensional_units: must be a JSON object mapping fields to SI unit strings"
        )

    issues.extend(_check_quality_flags(record_d["quality_flags"], path=path))

    # Optional engineering_properties metadata dictionary.
    eng = record_d.get("engineering_properties")
    if eng is not None:
        if not isinstance(eng, dict):
            issues.append(f"{path}.engineering_properties: must be a JSON object when present")
        else:
            for key, sub in eng.items():
                if not isinstance(sub, dict):
                    issues.append(f"{path}.engineering_properties[{key!r}]: must be a JSON object")

    # Optional property_values array of objects (Section 5.5).
    pv = record_d.get("property_values")
    if pv is not None:
        if not isinstance(pv, list):
            issues.append(f"{path}.property_values: must be an array when present")
        else:
            for idx, value in enumerate(pv):
                issues.extend(
                    _check_property_value_shape(value, path=f"{path}.property_values[{idx}]")
                )

    # provenance_edges must be a non-empty list (Section 8).
    prov = record_d["provenance_edges"]
    if not isinstance(prov, list) or not prov:
        issues.append(f"{path}.provenance_edges: must be a non-empty list of edge ids (Section 8)")
    elif not all(isinstance(e, str) and e for e in prov):
        issues.append(f"{path}.provenance_edges: every entry must be a non-empty string")

    # record_hash: 64-char hex + content-addressable match (Section 16).
    issues.extend(_check_record_hash(record_d, path=path))

    return issues


def validate_cost_record_schema(record: Any) -> list[str]:
    """Return a list of structural blocker issues (empty list = pass)."""
    path = "cost_record"
    record_d = _ensure_dict(record, path=path)
    issues: list[str] = []

    issues.extend(_check_required_fields(record_d, required=COST_RECORD_REQUIRED_FIELDS, path=path))
    if issues:
        return issues

    issues.extend(
        _check_enum_value("cost_category", record_d["cost_category"], CostCategory, path=path)
    )
    issues.extend(_check_enum_value("cost_basis", record_d["cost_basis"], CostBasis, path=path))
    issues.extend(
        _check_enum_value("quantity_basis", record_d["quantity_basis"], QuantityBasis, path=path)
    )
    issues.extend(
        _check_enum_value("source_class", record_d["source_class"], SourceClass, path=path)
    )
    issues.extend(_check_region(record_d["region"], path=path))
    issues.extend(_check_date(record_d["effective_date"], field="effective_date", path=path))
    escalation_date = record_d.get("escalation_date")
    if escalation_date is not None:
        issues.extend(_check_date(escalation_date, field="escalation_date", path=path))

    currency = record_d["currency"]
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha():
        issues.append(
            f"{path}.currency: must be a 3-letter ISO 4217 alphabetic code; got {currency!r}"
        )

    unit_basis = record_d["unit_basis"]
    if not isinstance(unit_basis, str) or not unit_basis:
        issues.append(f"{path}.unit_basis: must be a non-empty SI unit string")

    issues.extend(_check_quality_flags(record_d["quality_flags"], path=path))

    cv = record_d.get("cost_value")
    if cv is not None:
        if not isinstance(cv, dict):
            issues.append(f"{path}.cost_value: must be a JSON object when present")
        else:
            for field in (
                "value",
                "currency",
                "quantity_value_si",
                "unit_basis",
                "source_pointer",
            ):
                if field not in cv:
                    issues.append(f"{path}.cost_value: missing required subfield {field!r}")

    prov = record_d["provenance_edges"]
    if not isinstance(prov, list) or not prov:
        issues.append(f"{path}.provenance_edges: must be a non-empty list of edge ids (Section 8)")
    elif not all(isinstance(e, str) and e for e in prov):
        issues.append(f"{path}.provenance_edges: every entry must be a non-empty string")

    issues.extend(_check_record_hash(record_d, path=path))
    return issues


__all__ = [
    "validate_cost_record_schema",
    "validate_material_record_schema",
]
