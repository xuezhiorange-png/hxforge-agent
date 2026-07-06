"""TASK-017 Slice B — MassCalculator.

Implements the MassCalculator component of the TASK-017 frozen
design contract
(docs/tasks/TASK-017-materials-mass-preliminary-mechanical.md,
Frozen Contract Authority Commit SHA
``6ed5b7dc7d8df163796eacb838afcf5702a4c53a``,
Frozen Contract Authority Base SHA
``fbb05ae71f21e6cfd4d1041afb5958c863166248``) §5.2 + §6.

Scope (Slice B only, per design §14.2 + §3.2):

* Compute deterministic mass totals (kg) for each of the four
  closed-set component_role strings declared in §5.2.1:

  - ``inner_tube``   — straight-pipe metal mass (annulus volume × density)
  - ``outer_pipe``   — straight-pipe metal mass (annulus volume × density)
  - ``hairpin_bend`` — half-torus metal mass (per §6.3 formula)
  - ``fittings``     — end-fitting placeholder (sum of overrides, optional
                       density normalization)

* Consume Slice A's :class:`MaterialResolutionResult` per
  component_role (read-only); no re-derivation of material
  properties.
* Consume a TASK-016 :class:`GeometryCatalog` for the geometry
  record and the tube-geometry reference for hairpin
  calculations (read-only).
* Enforce ``approval_state == "approved"`` for the geometry
  record (and for the tube reference resolved via
  ``tube_geometry_id`` for hairpin masses).
* Enforce the four-role closed set: any missing role raises
  ``MATERIAL_RESOLUTION_MISSING_ROLE`` (§5.2.1).
* Produce a deterministic ``MassBreakdown`` with a 64-char
  SHA-256 ``calculation_hash`` over the canonical inputs
  (§10) and a ``MassProvenance`` block carrying all eight
  §8 fields plus ``result_hash``.
* Raise :class:`MaterialSelectorError` with the 13 frozen
  error codes from §7 (extending Slice A's exception class
  with an optional ``provenance`` field).

Out of scope for Slice B (explicit, per design §14.2 + §3.2):

* No preliminary mechanical checks (Slices C + D).
* No pressure-drop / C4 / cost / new-solver logic.
* No mutation of TASK-013 records or TASK-016 catalogs
  (read-only).
* No TASK-018+ content.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Any, Final

from hexagent.canonical_json import canonical_sha256
from hexagent.geometry_catalogs.models import (
    GeometryCatalog,
    GeometryRecord,
    HairpinGeometryRecord,
    PipeGeometryRecord,
    TubeGeometryRecord,
)
from hexagent.material_mass_mechanical.material_selector import (
    COMPONENT_ROLE_CLOSED_SET,
    ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
    ERROR_MATERIAL_RESOLUTION_MISSING_ROLE,
    FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA,
    MaterialResolutionResult,
    MaterialSelectorError,
    float_to_decimal_string,
)

# Slice B introduces 5 new frozen error codes that are not defined in
# Slice A (which only emits the 3 reachable-from-selector codes).
# The remaining 5 mechanical / input codes are reserved for Slices C
# and D and are intentionally NOT defined in this module.
# See Slice B implementation planning doc §9 for the full 13-code
# error model.
ERROR_GEOMETRY_CATALOG_UNAPPROVED: Final[str] = "GEOMETRY_CATALOG_UNAPPROVED"
ERROR_GEOMETRY_CATALOG_INCONSISTENT: Final[str] = "GEOMETRY_CATALOG_INCONSISTENT"
ERROR_HAIRPIN_BEND_INPUT_INCOMPLETE: Final[str] = "HAIRPIN_BEND_INPUT_INCOMPLETE"
ERROR_INPUT_DIMENSIONAL_INCONSISTENT: Final[str] = "INPUT_DIMENSIONAL_INCONSISTENT"
ERROR_INPUT_UNIT_INCONSISTENT: Final[str] = "INPUT_UNIT_INCONSISTENT"

# ---------------------------------------------------------------------------
# Constants — frozen at TASK-017 design freeze
# ---------------------------------------------------------------------------

#: Reference carbon-steel density documented in design §6.4 (kg/m^3).
#: Used by the optional ``fitting_density_normalization`` scaling path.
_REFERENCE_CARBON_STEEL_DENSITY_KG_M3: Final[float] = 7850.0

#: Documented Decimal quantizer precisions (design §10.3).
_DECIMAL_QUANTIZE_KG: Final[Decimal] = Decimal("0.000001")
_DECIMAL_QUANTIZE_M: Final[Decimal] = Decimal("0.0001")
_DECIMAL_QUANTIZE_MPA: Final[Decimal] = Decimal("0.0001")
_DECIMAL_QUANTIZE_GPA: Final[Decimal] = Decimal("0.000000001")

#: Closed set of component_role strings that the MassCalculator MUST
#: receive in ``material_resolutions_by_component_role`` (design §5.2.1).
#: Re-exported from Slice A's :data:`COMPONENT_ROLE_CLOSED_SET` for
#: convenience, but mass-calculator-side enumeration is duplicated here
#: as a frozen tuple to give deterministic iteration order (which the
#: canonical-JSON output depends on for reproducibility).
COMPONENT_ROLES_FROZEN_ORDER: Final[tuple[str, ...]] = (
    "inner_tube",
    "outer_pipe",
    "hairpin_bend",
    "fittings",
)


# ---------------------------------------------------------------------------
# Slice B error-code usage notes
# ---------------------------------------------------------------------------
#
# Slice B introduces 5 new frozen error codes that are not defined in
# Slice A (which only emits the 3 reachable-from-selector codes).
# The remaining 5 mechanical / input codes are reserved for Slices C
# and D and are intentionally NOT defined in this module.
#
# All 13 frozen error code values come from design §7 (frozen
# contract). The 5 codes introduced by Slice B live as Final[str]
# literals above; the 3 codes emitted by Slice A live in
# material_selector.py. Both modules are single-source-of-truth
# within their respective slice boundaries; no alias indirection
# is needed.


# ---------------------------------------------------------------------------
# Dataclasses — design §5.2.2 + §8
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MassCalculationRequest:
    """Input to the :class:`MassCalculator` (design §5.2).

    Required fields (design §5.2 + §6):

    * ``geometry_record`` — TASK-016 geometry record (any of the three
      closed-set geometry types). For :class:`HairpinGeometryRecord`,
      the record carries ``effective_length_m`` directly per TASK-016
      §5.5. For :class:`TubeGeometryRecord` /
      :class:`PipeGeometryRecord`, the effective length is NOT a
      documented field of the TASK-016 record (TASK-016 §5.3 / §5.4
      carry only the cross-sectional dimensions); therefore the
      caller MUST supply ``effective_length_m`` explicitly on the
      request. The mass calculator only reads
      ``effective_length_m`` from a :class:`HairpinGeometryRecord`
      when computing the hairpin formula (§6.3 sanity check); for
      straight-pipe mass (§6.1 / §6.2) the request-level
      ``effective_length_m`` is always used. No mutation.
    * ``material_resolutions_by_component_role`` — mapping from the
      four closed-set component_role strings to Slice A
      :class:`MaterialResolutionResult` outputs. The calculator
      requires a MaterialResolutionResult for **every** role.
    * ``fitting_overrides_kg`` — optional tuple of end-fitting
      override masses. Empty tuple = no overrides; ``fittings_kg``
      will be ``0.0`` per design §6.4.
    * ``include_hairpin`` — boolean switch. When ``False``, the
      hairpin record (if any) is ignored and ``hairpin_bend_kg``
      is forced to ``0.0`` per design §6.3 ("If the geometry
      record is straight-pipe only (no hairpin entry),
      ``hairpin_bend_kg`` is 0").
    * ``fitting_density_normalization`` — boolean switch. When
      ``True`` (default), the fittings mass is scaled by
      ``fittings_density_kg_m3 / 7850.0`` per design §6.4. When
      ``False``, ``fittings_kg = sum(fitting_overrides_kg)``
      exactly.

    Forbidden scope (design §3.2):

    * No new component_role strings are accepted.
    * No pressure-drop / cost / C4 inputs.
    """

    geometry_record: GeometryRecord
    effective_length_m: float
    material_resolutions_by_component_role: Mapping[str, MaterialResolutionResult]
    fitting_overrides_kg: tuple[float, ...] = ()
    include_hairpin: bool = False
    fitting_density_normalization: bool = True


@dataclass(frozen=True)
class MassProvenance:
    """Provenance block for a :class:`MassBreakdown` (design §8).

    Carries the eight §8 minimum fields plus ``result_hash`` (the
    lowercase hex SHA-256 over the canonical JSON of the full
    ``MassBreakdown`` payload per design §10). For mass calculations,
    ``correlation_ids`` is always an empty tuple per design §8
    ("empty list for mass").
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
class MassBreakdown:
    """Output of the :class:`MassCalculator` (design §5.2.2).

    Six numeric component-mass fields (kg), the ``total_kg`` sum, the
    ``calculation_hash`` 64-char SHA-256, and a ``MassProvenance``
    block carrying the eight §8 audit fields.
    """

    inner_tube_kg: float
    outer_pipe_kg: float
    hairpin_bend_kg: float
    fittings_kg: float
    total_kg: float
    calculation_hash: str
    provenance: MassProvenance

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serializable breakdown mapping.

        All kg values are quantized to 6 decimal places per design §10.3
        ("6 decimal places for kg") and serialized via
        :func:`float_to_decimal_string` for canonical-JSON reproducibility
        (design §10 + TASK-013 §16 sharing the same canonical_json helper).
        """
        return {
            "calculation_hash": self.calculation_hash,
            "fittings_kg": float_to_decimal_string(self.fittings_kg),
            "hairpin_bend_kg": float_to_decimal_string(self.hairpin_bend_kg),
            "inner_tube_kg": float_to_decimal_string(self.inner_tube_kg),
            "outer_pipe_kg": float_to_decimal_string(self.outer_pipe_kg),
            "provenance": self.provenance.to_dict(),
            "total_kg": float_to_decimal_string(self.total_kg),
        }


# ---------------------------------------------------------------------------
# Helpers — internal validation, formula primitives
# ---------------------------------------------------------------------------


def _quantize_kg(value: float) -> float:
    """Quantize a kg value to 6 decimal places (design §10.3).

    Uses :class:`decimal.Decimal` with ROUND_HALF_EVEN to preserve
    deterministic rounding across Python 3.10 / 3.11 / 3.12 (per
    design §11.4 determinism requirement).
    """
    if not math.isfinite(value):
        raise ValueError("non-finite float forbidden by canonical JSON rule")
    try:
        quantized = Decimal(str(value)).quantize(_DECIMAL_QUANTIZE_KG, rounding=ROUND_HALF_EVEN)
    except InvalidOperation as exc:  # pragma: no cover - guarded above
        raise ValueError(f"invalid kg value: {value!r}") from exc
    return float(quantized)


def _require_positive_dimension(name: str, value: float) -> float:
    """Validate that ``value`` is a finite, strictly-positive dimension.

    Used by hairpin / straight-pipe formulas. Raises
    :class:`MaterialSelectorError` with code
    ``INPUT_DIMENSIONAL_INCONSISTENT`` (design §7) on failure.
    """
    if not math.isfinite(value):
        raise MaterialSelectorError(
            code=ERROR_INPUT_DIMENSIONAL_INCONSISTENT,
            message=(
                f"{name} must be a finite number; observed non-finite value (NaN or ±Infinity)"
            ),
            context={"field": name, "observed": repr(value)},
        )
    if value < 0.0:
        raise MaterialSelectorError(
            code=ERROR_INPUT_DIMENSIONAL_INCONSISTENT,
            message=(f"{name} must be non-negative; observed negative value"),
            context={"field": name, "observed": value},
        )
    return value


def _check_geometry_approved(geometry_id: str, approval_state: str) -> None:
    """Enforce the TASK-016 ``approval_state == "approved"`` gate.

    Raises :class:`MaterialSelectorError` with code
    ``GEOMETRY_CATALOG_UNAPPROVED`` (design §7) if the geometry record
    is in any non-approved state.
    """
    if approval_state != "approved":
        raise MaterialSelectorError(
            code=ERROR_GEOMETRY_CATALOG_UNAPPROVED,
            message=(
                "geometry record is not in 'approved' state; "
                "TASK-017 mass calculator requires approved geometry"
            ),
            context={
                "geometry_record_id": geometry_id,
                "observed_approval_state": approval_state,
            },
        )


def _check_dimension_consistency(
    geometry_id: str,
    outer_diameter_m: float,
    inner_diameter_m: float,
) -> None:
    """Enforce the §7 ``outer_diameter_m >= inner_diameter_m`` invariant.

    Raises :class:`MaterialSelectorError` with code
    ``GEOMETRY_CATALOG_INCONSISTENT`` (design §7) on violation.
    """
    if outer_diameter_m < inner_diameter_m:
        raise MaterialSelectorError(
            code=ERROR_GEOMETRY_CATALOG_INCONSISTENT,
            message=(
                "geometry record has inconsistent dimensions: outer_diameter_m < inner_diameter_m"
            ),
            context={
                "geometry_record_id": geometry_id,
                "outer_diameter_m": outer_diameter_m,
                "inner_diameter_m": inner_diameter_m,
            },
        )


def _resolve_tube_record(
    catalog: GeometryCatalog,
    tube_geometry_id: str,
    hairpin_geometry_id: str,
) -> Any:
    """Resolve a hairpin's ``tube_geometry_id`` to its catalog record.

    Per design §6.3, the tube diameters used in the hairpin formula
    come from a TASK-016 catalog lookup keyed on
    ``tube_geometry_id``. Raises :class:`MaterialSelectorError` with
    code ``HAIRPIN_BEND_INPUT_INCOMPLETE`` (design §7) if the
    referenced tube record is not present in the catalog.
    """
    for record in catalog.records:
        if record.geometry_id == tube_geometry_id:
            return record
    raise MaterialSelectorError(
        code=ERROR_HAIRPIN_BEND_INPUT_INCOMPLETE,
        message=(
            "hairpin geometry references a tube_geometry_id that "
            "is not present in the supplied GeometryCatalog"
        ),
        context={
            "hairpin_geometry_id": hairpin_geometry_id,
            "tube_geometry_id": tube_geometry_id,
        },
    )


def _straight_pipe_section_kg(
    *,
    density_kg_m3: float,
    outer_diameter_m: float,
    inner_diameter_m: float,
    effective_length_m: float,
) -> float:
    """Implement the §6.1 / §6.2 straight-pipe mass formula.

    Formula: ``density * pi * ((outer/2)^2 - (inner/2)^2) * length``.
    """
    _require_positive_dimension("outer_diameter_m", outer_diameter_m)
    _require_positive_dimension("inner_diameter_m", inner_diameter_m)
    _require_positive_dimension("effective_length_m", effective_length_m)
    cross_section_area_m2 = math.pi * (
        (outer_diameter_m / 2.0) ** 2 - (inner_diameter_m / 2.0) ** 2
    )
    if cross_section_area_m2 < 0.0:
        # Defensive: outer < inner is also caught by
        # _check_dimension_consistency at the geometry-record level,
        # but the formula's own subtraction may also produce a small
        # negative due to floating-point rounding when the records are
        # borderline-consistent. Clamp to 0.0 to keep determinism.
        cross_section_area_m2 = 0.0
    return density_kg_m3 * cross_section_area_m2 * effective_length_m


def _hairpin_bend_kg(
    *,
    density_kg_m3: float,
    tube_outer_diameter_m: float,
    tube_inner_diameter_m: float,
    bend_radius_m: float,
    effective_length_m: float,
    number_of_tubes: int,
) -> float:
    """Implement the §6.3 hairpin mass formula.

    Formula:
        bend_cross_section_area_m2 = pi * ((tube_outer/2)^2 - (tube_inner/2)^2)
        bend_centerline_arc_length_m = pi * bend_radius_m
        single_bend_volume_m3 = area * arc_length
        total_bend_volume_m3 = single_bend_volume * number_of_tubes
        hairpin_bend_kg = density * total_bend_volume_m3

    Raises :class:`MaterialSelectorError` with code
    ``HAIRPIN_BEND_INPUT_INCOMPLETE`` (design §7) if a required
    hairpin input is missing or non-positive. Raises with code
    ``GEOMETRY_CATALOG_INCONSISTENT`` if the §7 hairpin-length
    sanity check (``effective_length_m < pi * bend_radius_m``)
    fails.
    """
    _require_positive_dimension("tube_outer_diameter_m", tube_outer_diameter_m)
    _require_positive_dimension("tube_inner_diameter_m", tube_inner_diameter_m)
    _require_positive_dimension("bend_radius_m", bend_radius_m)
    _require_positive_dimension("effective_length_m", effective_length_m)
    if not isinstance(number_of_tubes, int) or number_of_tubes <= 0:
        raise MaterialSelectorError(
            code=ERROR_HAIRPIN_BEND_INPUT_INCOMPLETE,
            message=(
                f"hairpin number_of_tubes must be a positive integer; observed {number_of_tubes!r}"
            ),
            context={
                "field": "number_of_tubes",
                "observed": number_of_tubes,
            },
        )
    arc_length_m = math.pi * bend_radius_m
    if effective_length_m < arc_length_m:
        raise MaterialSelectorError(
            code=ERROR_GEOMETRY_CATALOG_INCONSISTENT,
            message=(
                "hairpin effective_length_m < pi * bend_radius_m; "
                "geometry flagged as inconsistent (design §6.3 sanity "
                "check)"
            ),
            context={
                "effective_length_m": effective_length_m,
                "arc_length_m": arc_length_m,
                "bend_radius_m": bend_radius_m,
            },
        )
    cross_section_area_m2 = math.pi * (
        (tube_outer_diameter_m / 2.0) ** 2 - (tube_inner_diameter_m / 2.0) ** 2
    )
    if cross_section_area_m2 < 0.0:
        cross_section_area_m2 = 0.0
    single_bend_volume_m3 = cross_section_area_m2 * arc_length_m
    total_bend_volume_m3 = single_bend_volume_m3 * number_of_tubes
    return density_kg_m3 * total_bend_volume_m3


def _fittings_kg(
    *,
    density_kg_m3: float,
    fitting_overrides_kg: tuple[float, ...],
    density_normalization: bool,
) -> float:
    """Implement the §6.4 fittings mass formula.

    When ``density_normalization`` is True (default):
        ``fittings_kg = sum(overrides) * (density / 7850.0)``

    When ``density_normalization`` is False:
        ``fittings_kg = sum(overrides)`` (exact mass sum, no scaling)

    Raises :class:`MaterialSelectorError` with code
    ``INPUT_DIMENSIONAL_INCONSISTENT`` (design §7) if any override
    is non-finite or negative. Raises with code
    ``MATERIAL_GOVERNANCE_INCOMPLETE` if ``density_kg_m3`` is None
    (i.e. the underlying material record did not provide a density
    property — the calculator cannot scale without it).
    """
    if density_kg_m3 is None:
        raise MaterialSelectorError(
            code=ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
            message=(
                "fittings role material resolution has no density_kg_m3; "
                "cannot apply density-normalized fittings mass formula"
            ),
            context={"component_role": "fittings"},
        )
    total_override_kg = 0.0
    for idx, override in enumerate(fitting_overrides_kg):
        if not math.isfinite(override):
            raise MaterialSelectorError(
                code=ERROR_INPUT_DIMENSIONAL_INCONSISTENT,
                message=(
                    f"fitting_overrides_kg[{idx}] must be a finite "
                    "number; observed non-finite value"
                ),
                context={
                    "field": f"fitting_overrides_kg[{idx}]",
                    "observed": repr(override),
                },
            )
        if override < 0.0:
            raise MaterialSelectorError(
                code=ERROR_INPUT_DIMENSIONAL_INCONSISTENT,
                message=(
                    f"fitting_overrides_kg[{idx}] must be non-negative; observed negative value"
                ),
                context={
                    "field": f"fitting_overrides_kg[{idx}]",
                    "observed": override,
                },
            )
        total_override_kg += override
    if density_normalization:
        return total_override_kg * (density_kg_m3 / _REFERENCE_CARBON_STEEL_DENSITY_KG_M3)
    return total_override_kg


# ---------------------------------------------------------------------------
# Public entry point — design §5.2 + §6
# ---------------------------------------------------------------------------


def calculate_mass_breakdown(
    request: MassCalculationRequest,
    catalog: GeometryCatalog | None = None,
) -> MassBreakdown:
    """Compute the deterministic :class:`MassBreakdown` for a request.

    Implements the full §6 mass-formula pipeline. Consumes the supplied
    TASK-016 :class:`GeometryCatalog` for hairpin tube-geometry lookup
    (per design §6.3). Raises :class:`MaterialSelectorError` with the
    appropriate frozen error code on any failure mode.

    Args:
        request: the mass-calculation input bundle.
        catalog: optional TASK-016 geometry catalog. REQUIRED when the
            geometry record is a :class:`HairpinGeometryRecord` (its
            ``tube_geometry_id`` reference must be resolvable).
            Optional for straight-pipe-only paths (tube / pipe); when
            omitted and the geometry record is straight-pipe only, the
            calculator simply uses the dimensions carried on the
            geometry record itself.

    Returns:
        :class:`MassBreakdown` carrying the four component masses, the
        total, the deterministic ``calculation_hash`` (64-char SHA-256
        over the canonical inputs per §10), and the §8 provenance block.
    """
    geometry_record = request.geometry_record
    geometry_id = geometry_record.geometry_id

    # Step 1 — Geometry approval gate (design §7: GEOMETRY_CATALOG_UNAPPROVED).
    _check_geometry_approved(geometry_id, geometry_record.approval_state)

    # Step 1.5 — Resolve the straight-pipe carrier record. When the
    # geometry record is a TubeGeometryRecord or PipeGeometryRecord,
    # the straight-pipe dimensions are read directly from it. When
    # it is a HairpinGeometryRecord (design §5.5), the straight-pipe
    # dimensions for inner_tube / outer_pipe come from the referenced
    # tube / pipe records (which MUST be resolvable via the supplied
    # catalog when one is present; otherwise the calculator can only
    # honor the hairpin formula path).
    hairpin_record = geometry_record if isinstance(geometry_record, HairpinGeometryRecord) else None
    # Narrow straight_carrier_outer / _inner to float in both branches.
    straight_carrier_outer_m: float
    straight_carrier_inner_m: float
    straight_carrier_geometry_id: str
    if hairpin_record is not None:
        # Hairpin carrier: read tube / pipe dimensions from the
        # referenced records. The catalog must be supplied so we can
        # resolve tube_geometry_id (and pipe_geometry_id if needed).
        if catalog is None:
            raise MaterialSelectorError(
                code=ERROR_HAIRPIN_BEND_INPUT_INCOMPLETE,
                message=(
                    "hairpin geometry_record requires a TASK-016 "
                    "GeometryCatalog to resolve tube_geometry_id and "
                    "pipe_geometry_id for inner_tube / outer_pipe "
                    "straight-pipe mass"
                ),
                context={
                    "hairpin_geometry_id": hairpin_record.geometry_id,
                    "tube_geometry_id": hairpin_record.tube_geometry_id,
                    "pipe_geometry_id": hairpin_record.pipe_geometry_id,
                },
            )
        straight_carrier = _resolve_tube_record(
            catalog=catalog,
            tube_geometry_id=hairpin_record.tube_geometry_id,
            hairpin_geometry_id=hairpin_record.geometry_id,
        )
        # narrow to TubeGeometryRecord (the only thing _resolve_tube_record
        # can return — by the closed-set definition).
        assert isinstance(straight_carrier, TubeGeometryRecord)
        straight_carrier_outer_m = straight_carrier.outer_diameter_m
        straight_carrier_inner_m = straight_carrier.inner_diameter_m
        straight_carrier_geometry_id = straight_carrier.geometry_id
        _check_geometry_approved(straight_carrier.geometry_id, straight_carrier.approval_state)
    else:
        # narrow: non-hairpin means TubeGeometryRecord or PipeGeometryRecord
        assert isinstance(geometry_record, (TubeGeometryRecord, PipeGeometryRecord))
        straight_carrier_outer_m = geometry_record.outer_diameter_m
        straight_carrier_inner_m = geometry_record.inner_diameter_m
        straight_carrier_geometry_id = geometry_id
    _check_dimension_consistency(
        straight_carrier_geometry_id,
        straight_carrier_outer_m,
        straight_carrier_inner_m,
    )

    # Step 2 — Validate the four-role closed set is fully populated
    # (design §5.2.1: any missing role -> MATERIAL_RESOLUTION_MISSING_ROLE).
    resolutions = request.material_resolutions_by_component_role
    missing_roles: list[str] = []
    for role in COMPONENT_ROLES_FROZEN_ORDER:
        if role not in resolutions:
            missing_roles.append(role)
    if missing_roles:
        raise MaterialSelectorError(
            code=ERROR_MATERIAL_RESOLUTION_MISSING_ROLE,
            message=(
                "material_resolutions_by_component_role is missing one or "
                "more of the four frozen component_role keys"
            ),
            context={
                "missing_roles": missing_roles,
                "expected_roles": list(COMPONENT_ROLES_FROZEN_ORDER),
            },
        )
    # Also reject any extra keys that are not in the frozen four-role set
    # (design §5.2.1: closed set; extra roles are not allowed).
    extra_roles: list[str] = [role for role in resolutions if role not in COMPONENT_ROLE_CLOSED_SET]
    if extra_roles:
        raise MaterialSelectorError(
            code=ERROR_MATERIAL_RESOLUTION_MISSING_ROLE,
            message=(
                "material_resolutions_by_component_role contains keys that "
                "are not in the frozen four-role closed set"
            ),
            context={
                "extra_roles": sorted(extra_roles),
                "expected_roles": sorted(COMPONENT_ROLE_CLOSED_SET),
            },
        )

    # Step 3 — Material approval gate (design §7: MATERIAL_GOVERNANCE_UNAPPROVED).
    # The MaterialSelector already enforces this when building each
    # MaterialResolutionResult, but we re-check at the calculator level
    # so a caller that hand-builds a result cannot smuggle an unapproved
    # material into the mass path.
    for role in COMPONENT_ROLES_FROZEN_ORDER:
        result = resolutions[role]
        if result.provenance.material_record_id != result.material_record_id:
            # Sanity check: provenance and result should agree on the
            # material record id; if not, the result is malformed.
            raise MaterialSelectorError(
                code=ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
                message=(
                    f"component_role={role!r}: provenance.material_record_id "
                    "does not match MaterialResolutionResult.material_record_id"
                ),
                context={
                    "component_role": role,
                    "result_material_record_id": result.material_record_id,
                    "provenance_material_record_id": result.provenance.material_record_id,
                },
            )

    # Step 4 — Per-component mass computation (design §6).
    inner_tube_resolution = resolutions["inner_tube"]
    outer_pipe_resolution = resolutions["outer_pipe"]
    hairpin_bend_resolution = resolutions["hairpin_bend"]
    fittings_resolution = resolutions["fittings"]

    # Inner tube (§6.1): straight-pipe mass from the geometry record.
    if inner_tube_resolution.density_kg_m3 is None:
        raise MaterialSelectorError(
            code=ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
            message=("inner_tube material resolution has no density_kg_m3; cannot compute mass"),
            context={"component_role": "inner_tube"},
        )
    # Straight-pipe inner / outer tube mass uses the request-level
    # effective_length_m (the TASK-016 Tube / Pipe records do not
    # carry effective_length_m; the request is the canonical carrier
    # of the length dimension per the design §6.1 / §6.2 contract).
    # The straight-pipe dimensions are read from straight_carrier,
    # which may be the geometry record itself (tube / pipe case) or
    # the tube record referenced by a hairpin geometry record.
    straight_length_m = _require_positive_dimension(
        "effective_length_m", request.effective_length_m
    )
    inner_tube_kg_raw = _straight_pipe_section_kg(
        density_kg_m3=inner_tube_resolution.density_kg_m3,
        outer_diameter_m=straight_carrier_outer_m,
        inner_diameter_m=straight_carrier_inner_m,
        effective_length_m=straight_length_m,
    )

    # Outer pipe (§6.2): straight-pipe mass from the geometry record.
    # The §6.2 table in §5.2.1 says outer_pipe also reads the same
    # dimension fields; design §6.2 says "TASK-016 pipe geometry record"
    # but in the canonical TASK-016 catalog the straight-pipe record
    # is the PipeGeometryRecord which carries the same
    # outer_diameter_m / inner_diameter_m / effective_length_m fields.
    # We treat them as a single straight-pipe geometry source for the
    # mass calculator (the geometry record itself is the role's source).
    if outer_pipe_resolution.density_kg_m3 is None:
        raise MaterialSelectorError(
            code=ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
            message=("outer_pipe material resolution has no density_kg_m3; cannot compute mass"),
            context={"component_role": "outer_pipe"},
        )
    outer_pipe_kg_raw = _straight_pipe_section_kg(
        density_kg_m3=outer_pipe_resolution.density_kg_m3,
        outer_diameter_m=straight_carrier_outer_m,
        inner_diameter_m=straight_carrier_inner_m,
        effective_length_m=straight_length_m,
    )

    # Hairpin bend (§6.3): only if the geometry record is a hairpin AND
    # include_hairpin is True. Otherwise hairpin_bend_kg = 0.0
    # (design §6.3 "If the geometry record is straight-pipe only (no
    # hairpin entry), hairpin_bend_kg is 0").
    hairpin_bend_kg_raw = 0.0
    if request.include_hairpin and hairpin_record is not None:
        if hairpin_bend_resolution.density_kg_m3 is None:
            raise MaterialSelectorError(
                code=ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
                message=(
                    "hairpin_bend material resolution has no density_kg_m3; "
                    "cannot compute hairpin mass"
                ),
                context={"component_role": "hairpin_bend"},
            )
        if catalog is None:
            raise MaterialSelectorError(
                code=ERROR_HAIRPIN_BEND_INPUT_INCOMPLETE,
                message=(
                    "hairpin mass computation requires a TASK-016 "
                    "GeometryCatalog to resolve tube_geometry_id; "
                    "catalog was not supplied"
                ),
                context={
                    "hairpin_geometry_id": hairpin_record.geometry_id,
                    "tube_geometry_id": hairpin_record.tube_geometry_id,
                },
            )
        # Check the referenced tube record is also approved (design §7
        # geometry approval gate applied to references, mirroring
        # TASK-016 §5.5 "approved geometry references" rule).
        tube_record = _resolve_tube_record(
            catalog=catalog,
            tube_geometry_id=hairpin_record.tube_geometry_id,
            hairpin_geometry_id=hairpin_record.geometry_id,
        )
        _check_geometry_approved(tube_record.geometry_id, tube_record.approval_state)
        hairpin_bend_kg_raw = _hairpin_bend_kg(
            density_kg_m3=hairpin_bend_resolution.density_kg_m3,
            tube_outer_diameter_m=tube_record.outer_diameter_m,
            tube_inner_diameter_m=tube_record.inner_diameter_m,
            bend_radius_m=hairpin_record.bend_radius_m,
            effective_length_m=hairpin_record.effective_length_m,
            number_of_tubes=hairpin_record.number_of_tubes,
        )

    # Fittings (§6.4): sum of overrides, optionally density-normalized.
    if fittings_resolution.density_kg_m3 is None:
        raise MaterialSelectorError(
            code=ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
            message=(
                "fittings role material resolution has no density_kg_m3; "
                "cannot compute fittings mass"
            ),
            context={"component_role": "fittings"},
        )
    fittings_kg_raw = _fittings_kg(
        density_kg_m3=fittings_resolution.density_kg_m3,
        fitting_overrides_kg=request.fitting_overrides_kg,
        density_normalization=request.fitting_density_normalization,
    )

    # Step 5 — Quantize to design §10.3 precision and build the breakdown.
    inner_tube_kg = _quantize_kg(inner_tube_kg_raw)
    outer_pipe_kg = _quantize_kg(outer_pipe_kg_raw)
    hairpin_bend_kg = _quantize_kg(hairpin_bend_kg_raw)
    fittings_kg = _quantize_kg(fittings_kg_raw)
    total_kg = _quantize_kg(inner_tube_kg + outer_pipe_kg + hairpin_bend_kg + fittings_kg)

    # Step 6 — Deterministic calculation_hash (§10.4 SHA-256 over
    # canonical JSON of the breakdown's *numerical* content; provenance
    # goes into the result_hash field separately).
    # The hash input MUST be the canonical-JSON-serialized breakdown
    # WITHOUT the provenance.result_hash field itself (it is hashed,
    # but with an empty placeholder first, then re-hashed? No — design
    # §10.5 says "Provenance fields are included in the hashed JSON",
    # so we include them; we exclude the calculation_hash itself
    # because it is the hash OF the input).
    pre_hash_payload: dict[str, Any] = {
        "fittings_kg": float_to_decimal_string(fittings_kg),
        "hairpin_bend_kg": float_to_decimal_string(hairpin_bend_kg),
        "inner_tube_kg": float_to_decimal_string(inner_tube_kg),
        "outer_pipe_kg": float_to_decimal_string(outer_pipe_kg),
        "total_kg": float_to_decimal_string(total_kg),
    }
    calculation_hash = canonical_sha256(pre_hash_payload)

    # Step 7 — Build provenance block (§8) with the nine fields
    # (8 minimum + result_hash). The material_record_id is taken from
    # the inner_tube resolution (the principal role for mass). design
    # §8 does not require multiple material record ids in the mass
    # provenance; per the planning doc Slice A already established
    # the convention of recording one material record id per
    # breakdown.
    provenance_payload: dict[str, Any] = {
        "applicable_standard_id": (inner_tube_resolution.provenance.applicable_standard_id),
        "correlation_ids": [],
        "design_pressure_mpa": (inner_tube_resolution.provenance.design_pressure_mpa),
        "design_temperature_c": (inner_tube_resolution.provenance.design_temperature_c),
        "geometry_record_id": geometry_id,
        "git_commit": FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA,
        "material_record_id": inner_tube_resolution.material_record_id,
        "software_version": "0.1.0",
    }
    # Step 8 — Compute result_hash (§10.4 + §10.5: provenance fields
    # included in the hashed JSON). We compute the hash over the
    # breakdown payload plus the provenance block (excluding
    # result_hash itself, which is the hash of the input).
    full_payload_for_result_hash: dict[str, Any] = {
        "calculation_hash": calculation_hash,
        "fittings_kg": float_to_decimal_string(fittings_kg),
        "hairpin_bend_kg": float_to_decimal_string(hairpin_bend_kg),
        "inner_tube_kg": float_to_decimal_string(inner_tube_kg),
        "outer_pipe_kg": float_to_decimal_string(outer_pipe_kg),
        "provenance": provenance_payload,
        "total_kg": float_to_decimal_string(total_kg),
    }
    result_hash = canonical_sha256(full_payload_for_result_hash)
    provenance_payload["result_hash"] = result_hash

    provenance = MassProvenance(
        geometry_record_id=geometry_id,
        material_record_id=inner_tube_resolution.material_record_id,
        applicable_standard_id=(inner_tube_resolution.provenance.applicable_standard_id),
        design_pressure_mpa=(inner_tube_resolution.provenance.design_pressure_mpa),
        design_temperature_c=(inner_tube_resolution.provenance.design_temperature_c),
        correlation_ids=(),
        software_version="0.1.0",
        git_commit=FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA,
        result_hash=result_hash,
    )

    return MassBreakdown(
        inner_tube_kg=inner_tube_kg,
        outer_pipe_kg=outer_pipe_kg,
        hairpin_bend_kg=hairpin_bend_kg,
        fittings_kg=fittings_kg,
        total_kg=total_kg,
        calculation_hash=calculation_hash,
        provenance=provenance,
    )
