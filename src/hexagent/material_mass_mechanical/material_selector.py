"""TASK-017 Slice A — MaterialSelector.

Implements the MaterialSelector component of the TASK-017 frozen
design contract
(docs/tasks/TASK-017-materials-mass-preliminary-mechanical.md,
Frozen Contract Authority Commit SHA
``6ed5b7dc7d8df163796eacb838afcf5702a4c53a``,
Frozen Contract Authority Base SHA
``fbb05ae71f21e6cfd4d1041afb5958c863166248``) §5.1.

Scope (Slice A only, per design §14):

* Resolve a ``MaterialResolutionRequest`` (component_role +
  material_record_id) against an in-memory TASK-013
  ``MaterialRecord`` to a ``MaterialResolutionResult``.
* Read the three TASK-017-required canonical property names from
  the TASK-013 record's ``property_values[]`` array:

  - ``density`` (kg/m^3)            — used by Slice B MassCalculator
  - ``youngs_modulus`` (GPa)        — used by Slice D span check
  - ``allowable_stress`` (MPa table) — used by Slice C stress check

* Enforce ``approval_state == "approved"`` and the canonical SI
  units declared in design §5.1.2.
* Raise :class:`MaterialSelectorError` with the 13 frozen error
  codes from design §7.

Out of scope for Slice A (explicit, per design §14.1 + §3.2):

* No mass derivation (Slice B).
* No preliminary mechanical checks (Slices C + D).
* No pressure-drop / C4 / cost / new-solver logic.
* No mutation of TASK-013 records (read-only).
* No TASK-018+ content.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Final

from hexagent.canonical_json import canonical_sha256
from hexagent.material_costs.models import ApprovalState, MaterialRecord

# Frozen Contract Authority Commit SHA — literal frozen at design freeze
# (design §19.1). MUST match the design contract SHA recorded in the
# implementation planning doc §1 and in the PR body / backlog row.
FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA: Final[str] = "6ed5b7dc7d8df163796eacb838afcf5702a4c53a"
FROZEN_CONTRACT_AUTHORITY_BASE_SHA: Final[str] = "fbb05ae71f21e6cfd4d1041afb5958c863166248"

# Closed set of component_role values consumed by the application layer
# (design §5.2.1). MaterialSelector only validates membership at the
# type level; full per-role coverage enforcement is Slice B's
# responsibility. The inner_tube / outer_pipe / hairpin_bend / fittings
# set is included here so that MaterialResolutionRequest enforces the
# four-role closed set for downstream slice readiness.
COMPONENT_ROLE_CLOSED_SET: Final[frozenset[str]] = frozenset(
    {"inner_tube", "outer_pipe", "hairpin_bend", "fittings"}
)

# TASK-017 required canonical property_name strings (design §5.1.2).
# These are names DECLARED BY TASK-017; they are not a TASK-013 frozen
# enum. If a future TASK-013 amendment uses different property_name
# strings, the selector must be updated to match (this is a contract
# revision, not a runtime concern).
PROPERTY_NAME_DENSITY: Final[str] = "density"
PROPERTY_NAME_YOUNGS_MODULUS: Final[str] = "youngs_modulus"
PROPERTY_NAME_ALLOWABLE_STRESS: Final[str] = "allowable_stress"

# Canonical SI units for each property (design §5.1.2).
UNIT_DENSITY: Final[str] = "kg/m^3"
UNIT_YOUNGS_MODULUS: Final[str] = "GPa"
UNIT_ALLOWABLE_STRESS: Final[str] = "MPa"

# Frozen error codes (design §7). Slice A only RAISES the three codes
# whose preconditions are reachable from a single MaterialRecord
# resolution; the remaining codes are reserved for Slices B / C / D
# and are exported here for the public error-code enum reference.
ERROR_MATERIAL_GOVERNANCE_INCOMPLETE: Final[str] = "MATERIAL_GOVERNANCE_INCOMPLETE"
ERROR_MATERIAL_GOVERNANCE_UNAPPROVED: Final[str] = "MATERIAL_GOVERNANCE_UNAPPROVED"
ERROR_MATERIAL_RESOLUTION_MISSING_ROLE: Final[str] = "MATERIAL_RESOLUTION_MISSING_ROLE"


@dataclass(frozen=True)
class MaterialResolutionRequest:
    """Input to the MaterialSelector (design §5.1).

    The full request per §5.1 also carries design_temperature_c /
    design_pressure_mpa / corrosion_allowance_mm /
    applicable_standard_id, but those fields are consumed only by
    Slices B / C / D. Slice A accepts them and echoes them into the
    provenance block so the slice-by-slice contract is satisfied
    without forcing Slice A to validate envelope thresholds.
    """

    component_role: str
    material_record_id: str
    design_temperature_c: float | None = None
    design_pressure_mpa: float | None = None
    corrosion_allowance_mm: float | None = None
    applicable_standard_id: str | None = None


@dataclass(frozen=True)
class MaterialProvenance:
    """Provenance block (design §8 minimum fields).

    Slice A returns a deterministic provenance block with the eight
    fields required by §8, plus a ``result_hash`` that is the
    lowercase hex SHA-256 of the canonical JSON of the full
    ``MaterialResolutionResult`` payload (design §10).
    """

    geometry_record_id: str
    material_record_id: str
    applicable_standard_id: str | None
    design_pressure_mpa: float | None
    design_temperature_c: float | None
    correlation_ids: tuple[str, ...] = field(default_factory=tuple)
    software_version: str = "0.1.0"
    git_commit: str = FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA
    result_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serializable provenance mapping."""
        return {
            "applicable_standard_id": self.applicable_standard_id,
            "correlation_ids": list(self.correlation_ids),
            "design_pressure_mpa": self.design_pressure_mpa,
            "design_temperature_c": self.design_temperature_c,
            "geometry_record_id": self.geometry_record_id,
            "git_commit": self.git_commit,
            "material_record_id": self.material_record_id,
            "result_hash": self.result_hash,
            "software_version": self.software_version,
        }


@dataclass(frozen=True)
class MaterialResolutionResult:
    """Output of the MaterialSelector (design §5.1.3).

    Any TASK-017-required property listed in design §5.1.2 but absent
    from the TASK-013 record's ``property_values[]`` is set to
    ``None`` AND the selector raises
    ``MATERIAL_GOVERNANCE_INCOMPLETE`` (design §5.1.3 final paragraph
    + §7).
    """

    material_record_id: str
    material_grade: str
    density_kg_m3: float | None
    youngs_modulus_gpa: float | None
    allowable_stress_mpa: dict[float, float] | None
    provenance: MaterialProvenance

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serializable result mapping.

        Floating-point keys in ``allowable_stress_mpa`` are serialized
        via :func:`float_to_decimal_string` for canonical-JSON
        reproducibility (design §10 + TASK-013 §16 sharing the same
        canonical_json helper).
        """
        if self.allowable_stress_mpa is None:
            allowable_serialized: dict[str, float] | None = None
        else:
            allowable_serialized = {
                float_to_decimal_string(temp_c): self.allowable_stress_mpa[temp_c]
                for temp_c in sorted(self.allowable_stress_mpa)
            }
        return {
            "allowable_stress_mpa": allowable_serialized,
            "density_kg_m3": self.density_kg_m3,
            "material_grade": self.material_grade,
            "material_record_id": self.material_record_id,
            "provenance": self.provenance.to_dict(),
            "youngs_modulus_gpa": self.youngs_modulus_gpa,
        }


@dataclass(frozen=True)
class MaterialSelectorError(Exception):
    """Structured error returned by the MaterialSelector.

    Mirrors the design §7 contract: every error carries a ``code``
    (one of the 13 frozen error codes), a human-readable ``message``,
    and a ``context`` block that records the failing field for
    downstream diagnostics. Slice A only emits the three codes whose
    preconditions are reachable from a single MaterialRecord
    resolution; the other 10 codes are reserved for Slices B / C / D.
    """

    code: str
    message: str
    context: dict[str, Any]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"[{self.code}] {self.message}"


def float_to_decimal_string(value: float) -> str:
    """Format a finite float as its shortest round-trippable decimal.

    Used to ensure that float keys inside ``allowable_stress_mpa``
    are serialized to JSON deterministically (design §10 + TASK-013
    §16 RFC 8785 §3.3.1). Non-finite floats raise :class:`ValueError`
    to satisfy the TASK-012 / design §10 non-finite-floats
    prohibition.
    """
    import math

    if not math.isfinite(value):
        raise ValueError("non-finite float forbidden by canonical JSON rule")
    return repr(value)


def _find_property(property_values: list[Any], property_name: str) -> dict[str, Any] | None:
    """Return the TASK-013 ``property_values[]`` entry matching the
    given canonical property name, or ``None`` if absent.

    The lookup is exact-match (case-sensitive) because the
    ``property_name`` strings are a TASK-017-declared canonical name
    set (design §5.1.2) and a TASK-013 record that uses a
    differently-cased name is by definition not addressing TASK-017.
    """
    for entry in property_values:
        if not isinstance(entry, dict):
            continue
        if entry.get("property_name") == property_name:
            return entry
    return None


def _parse_allowable_stress_entry(
    entry: dict[str, Any],
) -> dict[float, float]:
    """Parse the TASK-013 ``allowable_stress`` ``property_values[]``
    entry into a ``dict[float, float]`` (design §5.1.2 note).

    The TASK-013 record's ``value_si`` for this property MUST carry a
    JSON-encoded string of the table shape
    ``{"<temperature_c>": "<stress_mpa_decimal_string>", ...}`` with
    ``unit_si = "MPa"``. Both keys and values are converted via
    :class:`decimal.Decimal` (NOT ``float(...)``) to preserve
    precision, per design §5.1.1.
    """
    from decimal import Decimal, InvalidOperation

    raw = entry.get("value_si")
    if not isinstance(raw, str) or not raw:
        raise MaterialSelectorError(
            code=ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
            message=(
                "allowable_stress property_values entry has non-string or "
                "empty value_si; expected a JSON-encoded {temperature_c: "
                "stress_mpa_decimal_string} table"
            ),
            context={
                "property_name": PROPERTY_NAME_ALLOWABLE_STRESS,
                "observed_type": type(raw).__name__,
            },
        )
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MaterialSelectorError(
            code=ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
            message=(
                "allowable_stress property_values entry value_si is not valid JSON-encoded table"
            ),
            context={
                "property_name": PROPERTY_NAME_ALLOWABLE_STRESS,
                "json_error": str(exc),
            },
        ) from exc
    if not isinstance(decoded, dict) or not decoded:
        raise MaterialSelectorError(
            code=ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
            message=(
                "allowable_stress property_values entry value_si decoded to "
                "a non-dict or empty mapping"
            ),
            context={
                "property_name": PROPERTY_NAME_ALLOWABLE_STRESS,
                "observed_type": type(decoded).__name__,
            },
        )
    table: dict[float, float] = {}
    for temp_key, stress_value in decoded.items():
        try:
            temp_c = float(Decimal(str(temp_key)))
            stress_mpa = float(Decimal(str(stress_value)))
        except (InvalidOperation, ValueError) as exc:
            raise MaterialSelectorError(
                code=ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
                message=(
                    "allowable_stress table entry has non-decimal temperature or stress value"
                ),
                context={
                    "property_name": PROPERTY_NAME_ALLOWABLE_STRESS,
                    "observed_key": str(temp_key),
                    "observed_value": str(stress_value),
                },
            ) from exc
        table[temp_c] = stress_mpa
    return table


def _check_unit(
    entry: dict[str, Any],
    *,
    expected_unit: str,
    property_name: str,
) -> None:
    """Raise ``MATERIAL_GOVERNANCE_INCOMPLETE`` if the unit does not
    match the canonical SI unit declared in design §5.1.2."""
    observed = entry.get("unit_si")
    if observed != expected_unit:
        raise MaterialSelectorError(
            code=ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
            message=(
                f"{property_name} property_values entry has a non-canonical "
                f"SI unit; expected {expected_unit!r}, observed {observed!r}"
            ),
            context={
                "property_name": property_name,
                "expected_unit_si": expected_unit,
                "observed_unit_si": observed,
            },
        )


def resolve_material(
    request: MaterialResolutionRequest,
    material_record: MaterialRecord,
    *,
    geometry_record_id: str = "",
    git_commit: str = FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA,
) -> MaterialResolutionResult:
    """Resolve a MaterialResolutionRequest against a TASK-013 record.

    Implements design §5.1 end-to-end:

    1. Reject any record whose ``approval_state != "approved"`` with
       ``MATERIAL_GOVERNANCE_UNAPPROVED``.
    2. Walk the record's ``property_values[]`` for the three
       TASK-017-required canonical names; raise
       ``MATERIAL_GOVERNANCE_INCOMPLETE`` if any required property
       (density, allowable_stress) is missing or has a unit
       mismatch.
    3. Convert decimal-string ``value_si`` entries to ``float`` via
       :class:`decimal.Decimal` (NOT ``float(...)`` directly) per
       design §5.1.1.
    4. Parse the ``allowable_stress`` JSON table into
       ``dict[float, float]`` keyed by °C, value in MPa.
    5. Return a :class:`MaterialResolutionResult` whose provenance
       block records the §8 minimum fields plus a SHA-256
       ``result_hash`` over the canonical-JSON-serialized result.

    The selector is BIT-IDENTICAL across replays and machines for the
    same input (design §10 + planning doc §8).
    """
    # Closed-set component_role guard (design §5.2.1 closed set).
    if request.component_role not in COMPONENT_ROLE_CLOSED_SET:
        raise MaterialSelectorError(
            code=ERROR_MATERIAL_RESOLUTION_MISSING_ROLE,
            message=(
                "component_role is not in the TASK-017 closed set "
                f"(allowed: {sorted(COMPONENT_ROLE_CLOSED_SET)})"
            ),
            context={
                "component_role": request.component_role,
                "allowed_roles": sorted(COMPONENT_ROLE_CLOSED_SET),
            },
        )

    # material_record_id binding — both sides must agree (design §5.1).
    record_id = material_record.get("material_record_id", "")
    if record_id != request.material_record_id:
        raise MaterialSelectorError(
            code=ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
            message=("TASK-013 material_record_id does not match the requested material_record_id"),
            context={
                "request_material_record_id": request.material_record_id,
                "observed_material_record_id": record_id,
            },
        )

    # Approval-state gate (design §7 MATERIAL_GOVERNANCE_UNAPPROVED).
    if material_record.get("approval_state") != ApprovalState.APPROVED.value:
        raise MaterialSelectorError(
            code=ERROR_MATERIAL_GOVERNANCE_UNAPPROVED,
            message=(
                "TASK-013 material record is not in approval_state="
                f"{ApprovalState.APPROVED.value!r}"
            ),
            context={
                "material_record_id": record_id,
                "observed_approval_state": material_record.get("approval_state"),
            },
        )

    property_values = material_record.get("property_values") or []
    if not isinstance(property_values, list):
        raise MaterialSelectorError(
            code=ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
            message=("TASK-013 material record property_values is not a list"),
            context={
                "material_record_id": record_id,
                "observed_type": type(property_values).__name__,
            },
        )

    # density (required, design §5.1.2).
    density_entry = _find_property(property_values, PROPERTY_NAME_DENSITY)
    if density_entry is None:
        raise MaterialSelectorError(
            code=ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
            message=(
                f"{PROPERTY_NAME_DENSITY!r} property_values entry is missing "
                "from the TASK-013 material record"
            ),
            context={
                "material_record_id": record_id,
                "property_name": PROPERTY_NAME_DENSITY,
            },
        )
    _check_unit(
        density_entry,
        expected_unit=UNIT_DENSITY,
        property_name=PROPERTY_NAME_DENSITY,
    )
    from decimal import Decimal, InvalidOperation

    try:
        density_kg_m3: float | None = float(Decimal(str(density_entry.get("value_si"))))
    except (InvalidOperation, ValueError) as exc:
        raise MaterialSelectorError(
            code=ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
            message=(f"{PROPERTY_NAME_DENSITY!r} value_si is not a valid decimal string"),
            context={
                "material_record_id": record_id,
                "property_name": PROPERTY_NAME_DENSITY,
                "observed_value_si": density_entry.get("value_si"),
            },
        ) from exc

    # youngs_modulus (optional, design §5.1.2 note: "MAY be absent").
    youngs_entry = _find_property(property_values, PROPERTY_NAME_YOUNGS_MODULUS)
    youngs_modulus_gpa: float | None
    if youngs_entry is None:
        youngs_modulus_gpa = None
    else:
        _check_unit(
            youngs_entry,
            expected_unit=UNIT_YOUNGS_MODULUS,
            property_name=PROPERTY_NAME_YOUNGS_MODULUS,
        )
        try:
            youngs_modulus_gpa = float(Decimal(str(youngs_entry.get("value_si"))))
        except (InvalidOperation, ValueError) as exc:
            raise MaterialSelectorError(
                code=ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
                message=(
                    f"{PROPERTY_NAME_YOUNGS_MODULUS!r} value_si is not a valid decimal string"
                ),
                context={
                    "material_record_id": record_id,
                    "property_name": PROPERTY_NAME_YOUNGS_MODULUS,
                    "observed_value_si": youngs_entry.get("value_si"),
                },
            ) from exc

    # allowable_stress (required, design §5.1.2 note: TABLE shape).
    allowable_entry = _find_property(property_values, PROPERTY_NAME_ALLOWABLE_STRESS)
    if allowable_entry is None:
        raise MaterialSelectorError(
            code=ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
            message=(
                f"{PROPERTY_NAME_ALLOWABLE_STRESS!r} property_values entry is "
                "missing from the TASK-013 material record"
            ),
            context={
                "material_record_id": record_id,
                "property_name": PROPERTY_NAME_ALLOWABLE_STRESS,
            },
        )
    _check_unit(
        allowable_entry,
        expected_unit=UNIT_ALLOWABLE_STRESS,
        property_name=PROPERTY_NAME_ALLOWABLE_STRESS,
    )
    allowable_stress_mpa = _parse_allowable_stress_entry(allowable_entry)

    provenance = MaterialProvenance(
        geometry_record_id=geometry_record_id,
        material_record_id=record_id,
        applicable_standard_id=request.applicable_standard_id,
        design_pressure_mpa=request.design_pressure_mpa,
        design_temperature_c=request.design_temperature_c,
        correlation_ids=(),
        git_commit=git_commit,
        result_hash="",  # filled in below
    )

    result = MaterialResolutionResult(
        material_record_id=record_id,
        material_grade=str(material_record.get("material_grade_or_designation", "")),
        density_kg_m3=density_kg_m3,
        youngs_modulus_gpa=youngs_modulus_gpa,
        allowable_stress_mpa=allowable_stress_mpa,
        provenance=provenance,
    )

    # Compute the result_hash over the canonical-JSON-serialized result
    # (design §10 + planning doc §8). result_hash is excluded from the
    # hash input itself (TASK-012 §13 excluded_hash_fields rule,
    # shared by the canonical_json helper).
    result_hash = canonical_sha256(result.to_dict())
    final_provenance = MaterialProvenance(
        geometry_record_id=provenance.geometry_record_id,
        material_record_id=provenance.material_record_id,
        applicable_standard_id=provenance.applicable_standard_id,
        design_pressure_mpa=provenance.design_pressure_mpa,
        design_temperature_c=provenance.design_temperature_c,
        correlation_ids=provenance.correlation_ids,
        software_version=provenance.software_version,
        git_commit=provenance.git_commit,
        result_hash=result_hash,
    )
    return MaterialResolutionResult(
        material_record_id=result.material_record_id,
        material_grade=result.material_grade,
        density_kg_m3=result.density_kg_m3,
        youngs_modulus_gpa=result.youngs_modulus_gpa,
        allowable_stress_mpa=result.allowable_stress_mpa,
        provenance=final_provenance,
    )


__all__ = [
    "COMPONENT_ROLE_CLOSED_SET",
    "ERROR_MATERIAL_GOVERNANCE_INCOMPLETE",
    "ERROR_MATERIAL_GOVERNANCE_UNAPPROVED",
    "ERROR_MATERIAL_RESOLUTION_MISSING_ROLE",
    "FROZEN_CONTRACT_AUTHORITY_BASE_SHA",
    "FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA",
    "MaterialProvenance",
    "MaterialResolutionRequest",
    "MaterialResolutionResult",
    "MaterialSelectorError",
    "PROPERTY_NAME_ALLOWABLE_STRESS",
    "PROPERTY_NAME_DENSITY",
    "PROPERTY_NAME_YOUNGS_MODULUS",
    "UNIT_ALLOWABLE_STRESS",
    "UNIT_DENSITY",
    "UNIT_YOUNGS_MODULUS",
    "float_to_decimal_string",
    "resolve_material",
]
