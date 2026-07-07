"""LifeCycleEnergyEstimator — TASK-018 §5.3 deterministic life-cycle energy / OPEX envelope.

This module implements the application-layer life-cycle energy estimator that
consumes the Slice B ``CostBreakdown`` envelope plus the upstream thermal /
energy inputs documented in TASK-018 §5.3.1 and produces the frozen
``LifeCycleEnergyBreakdown`` envelope documented in §5.3.2.

Slice C scope (TASK-018 implementation round 3):

    - Consume ``CostBreakdown`` (read-only; no cost-record mutation).
    - Consume the §5.3.1 input envelope (thermal summary, pump/fan power +
      efficiency, annual operating hours, design life years, discount rate,
      salvage fraction, fouling energy penalty factor; optional cleaning
      cycle years + spares per-year cost; case currency).
    - Produce the §5.3.2 ``LifeCycleEnergyBreakdown`` envelope deterministically
      under the Option A rule (see below).
    - Reuse the frozen closed-set blocker / warning codes from §9
      (no new codes introduced; runtime emits only codes enumerated in
      §9.1 / §9.2).

Slice C does NOT include:

    - Slice D / closeout / ``docs/TASK_BACKLOG.md`` governance-sync mutation
      (separate authorization required).
    - TASK-019+ work.
    - A discount formula. Per TASK-018 §5.3.2 Rules (verbatim):

        "This contract **does not** prescribe the discount formula; it
         leaves the discount formula to the implementation-round
         design-amendment contract (per TASK-018 design-amendment
         precedent, e.g. PR #46)."

        "The default absence of ``discounted_total_minor_units`` ``0`` is
         **not allowed**; if the implementation cannot compute it (e.g.
         discount rate out of model support envelope), the output block is
         ``null`` (not 0)."

      Slice C implements under **Option A**:
        - ``discounted_total_minor_units: null`` (never ``0``)
        - emit ``unspecified_blocker`` (already in §9.1 frozen set)
        - include ``details.reason = "discount_formula_pending_design_amendment"``
          (mirrors the §9 safety-net pattern used by Slice B for
          ``c0_heuristic_out_of_envelope``).
      A future TASK-018 §5.3 design-amendment PR is required before a
      real ``discounted_total_minor_units`` can be computed; that
      amendment is NOT in this round.
    - Currency conversion (TASK-018 §6.1: never converted).
    - C2 historical-project regression.
    - C3 vendor quotation / supplier quote.
    - Pressure-drop / C4 logic.
    - C0 / C1 cost-record re-derivation. The estimator consumes the
      ``CostBreakdown`` envelope only; it does not need to know about the
      underlying TASK-013 cost records directly (per §5.3.2 final Rule).

Deterministic guarantees (TASK-018 §10):

    - ``*_minor_units`` are integers (no floats in money output).
    - ``*_kwh`` values are FLOAT with deterministic IEEE-754 round-trip via
      ``repr()`` (no NaN/Infinity; explicit float conversions).
    - ``life_cycle_run_id`` is a deterministic UUID v5 over a canonical
      payload anchored on the Frozen Contract Authority Base SHA (mirrors
      Slice A ``selector_run_id`` / Slice B ``calculator_run_id`` pattern).
    - ``source_record_ids`` (if surfaced) sorted ascending before hashing.
    - fingerprint-feeding ``provenance_chain_hash`` follows §7.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from .cost_calculator import (
    CALCULATOR_SCHEMA_VERSION,
)
from .errors import (
    BLOCKER_CODES,
    WARNING_CODES,
    BlockerCode,
    CostSelectorError,
    WarningCode,
)

# ---------------------------------------------------------------------------
# Constants.
# ---------------------------------------------------------------------------

# TASK-018 §5.3.1 fouling_energy_penalty_factor envelope. A caller-supplied
# multiplier outside this closed interval is a
# ``fouling_energy_penalty_factor_at_upper_bound_warning`` (when the upper
# bound equals 2.0; §9.2 frozen set) or, if the multiplier is outside the
# envelope, an ``unspecified_blocker`` carrying
# ``details.reason = "fouling_energy_penalty_factor_out_of_envelope"`` per
# the §9 safety-net pattern (mirrors Slice B's
# ``c0_heuristic_out_of_envelope`` treatment).  We deliberately reuse the
# existing frozen codes; no new enum member is introduced.
FOULING_ENERGY_PENALTY_MIN: Final[float] = 1.0
FOULING_ENERGY_PENALTY_MAX: Final[float] = 2.0

# TASK-018 §5.3.1 — discount_rate envelope (caller-supplied float ∈ [0, 1]).
DISCOUNT_RATE_MIN: Final[float] = 0.0
DISCOUNT_RATE_MAX: Final[float] = 1.0

# TASK-018 §5.3.1 — salvage_fraction envelope (caller-supplied float ∈ [0, 1]).
SALVAGE_FRACTION_MIN: Final[float] = 0.0
SALVAGE_FRACTION_MAX: Final[float] = 1.0

# TASK-018 §5.3.1 — pump_or_fan_efficiency envelope (caller-supplied float ∈ [0, 1]).
PUMP_OR_FAN_EFFICIENCY_MIN: Final[float] = 0.0
PUMP_OR_FAN_EFFICIENCY_MAX: Final[float] = 1.0

# Frozen schema version emitted on the ``LifeCycleEnergyBreakdown`` envelope
# (mirrors Slice A / Slice B convention; same ``0.1.0`` schema-version line).
LIFECYCLE_SCHEMA_VERSION: Final[str] = CALCULATOR_SCHEMA_VERSION

# Stable UUID namespace for ``life_cycle_run_id`` (TASK-018 §5.3.2 requires
# UUID v5 over a canonical input fingerprint).  Mirrors the Slice A /
# Slice B pattern: anchored on the SHA-256 of the Frozen Contract Authority
# Base SHA so the namespace is anchored to the contract authority itself
# -- a future design-amendment round that re-anchors to a new base SHA
# MUST regenerate this namespace too.  The intermediate SHA-256 takes any
# length of base SHA down to UUID's 128-bit native size.
_LIFECYCLE_RUN_ID_NAMESPACE: Final[uuid.UUID] = uuid.UUID(
    bytes=bytes(
        hashlib.sha256(
            b"task-018-lifecycle-run-idns:"
            + bytes.fromhex("5f96cf761d470b82faa1a5d164eefd42360c7df9")
        ).digest()[:16]
    )
)


# ---------------------------------------------------------------------------
# Public input / output envelopes (§5.3.1 + §5.3.2).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ThermalServiceSummary:
    """§5.3.1 TASK-008 / TASK-017 thermal_service_summary duck-typed input.

    Carries the four thermal fields TASK-018 §5.3.1 references.  All fields
    are typed structurally so the estimator stays decoupled from the TASK-008
    / TASK-017 envelope class identity; a duck-typed mapping with these
    attributes is acceptable.
    """

    Q_w: float  # heat duty, W
    A_m2: float  # heat-transfer area, m²
    U_w_per_m2_k: float  # overall heat-transfer coefficient, W/m²/K
    LMTD_k: float  # log-mean temperature difference, K


@dataclass(frozen=True)
class SparesCostPerYear:
    """§5.3.1 optional ``spares_cost_per_year_minor_units`` (int + currency).

    ``None`` (the dataclass default) leaves spares ``null`` in the output
    envelope.  When supplied, the field MUST carry an integer minor-unit
    amount AND an ISO 4217 currency that matches ``case_currency``
    (otherwise a ``currency_mismatch_blocker`` surfaces).
    """

    amount_minor_units: int
    currency: str


@dataclass(frozen=True)
class LifeCycleEnergyEstimatorInput:
    """§5.3.1 input envelope for ``LifeCycleEnergyEstimator``.

    All fields are keyword-only to make the public contract explicit.
    Required fields have no defaults; optional fields have safe defaults.
    """

    cost_breakdown: object  # Slice B CostBreakdown, typed structurally
    thermal_service_summary: ThermalServiceSummary
    pump_or_fan_power_kw: float
    pump_or_fan_efficiency: float
    annual_operating_hours: float
    design_life_years: int
    discount_rate: float
    salvage_fraction: float
    fouling_energy_penalty_factor: float
    case_currency: str
    pump_or_fan_power_kw_provenance: str = "caller_supplied"
    pump_or_fan_efficiency_provenance: str = "caller_supplied"
    cleaning_cycle_years: float | None = None
    spares_cost_per_year: SparesCostPerYear | None = None


@dataclass(frozen=True)
class LifeCycleEnergyBreakdown:
    """§5.3.2 ``LifeCycleEnergyBreakdown`` envelope.

    Result-state implications (§9.3):

        ``len(blockers) >= 1`` ⇒ ``state = NOT_COMPUTABLE``
        ``len(warnings) >= 1`` (and blockers empty) ⇒
        ``state = COMPUTABLE_WITH_WARNINGS``
        else ⇒ ``state = COMPUTABLE``
    """

    schema_version: str
    life_cycle_run_id: str
    state: str
    energy_breakdown: dict[str, object]
    inputs_used: dict[str, str]
    warnings: tuple[dict[str, object], ...]
    blockers: tuple[dict[str, object], ...]
    provenance_chain_hash: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "life_cycle_run_id": self.life_cycle_run_id,
            "state": self.state,
            "energy_breakdown": self.energy_breakdown,
            "inputs_used": self.inputs_used,
            "warnings": list(self.warnings),
            "blockers": list(self.blockers),
            "provenance_chain_hash": self.provenance_chain_hash,
        }


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------


def calculate_life_cycle_breakdown(
    *,
    cost_breakdown: object,
    thermal_service_summary: ThermalServiceSummary | Mapping[str, object],
    pump_or_fan_power_kw: float,
    pump_or_fan_efficiency: float,
    annual_operating_hours: float,
    design_life_years: int,
    discount_rate: float,
    salvage_fraction: float,
    fouling_energy_penalty_factor: float,
    case_currency: str,
    pump_or_fan_power_kw_provenance: str = "caller_supplied",
    pump_or_fan_efficiency_provenance: str = "caller_supplied",
    cleaning_cycle_years: float | None = None,
    spares_cost_per_year: SparesCostPerYear | Mapping[str, object] | None = None,
) -> LifeCycleEnergyBreakdown:
    """Compute a deterministic ``LifeCycleEnergyBreakdown`` per TASK-018 §5.3.

    The function is pure with respect to all inputs:

        - never mutates ``cost_breakdown`` or any upstream record;
        - produces a fully deterministic result for identical inputs
          (same payload ⇒ same ``life_cycle_run_id`` byte-for-byte);
        - returns a ``LifeCycleEnergyBreakdown`` with ``state = NOT_COMPUTABLE``
          when any blocker is present, leaving ``discounted_total_minor_units``
          explicitly ``null`` (never ``0``) per §5.3.2 Rule 3.

    Discount-formula handling (Option A, per §5.3.2 Rules):

        The frozen contract does not prescribe the discount formula (§5.3.2
        Rule 2).  This implementation therefore emits
        ``discounted_total_minor_units: null`` plus an ``unspecified_blocker``
        with ``details.reason = "discount_formula_pending_design_amendment"``
        whenever the input is otherwise consistent.  A future TASK-018 §5.3
        design-amendment PR is required before a real
        ``discounted_total_minor_units`` can be computed.

    Raises ``CostSelectorError`` only when a frozen-closed-set invariant is
    violated (e.g. a non-frozen blocker / warning code slipped through).
    Routine computation failures surface as ``LifeCycleEnergyBreakdown.blockers``
    entries.
    """
    # Normalize spares optional input
    spares: SparesCostPerYear | None
    if spares_cost_per_year is None:
        spares = None
    elif isinstance(spares_cost_per_year, SparesCostPerYear):
        spares = spares_cost_per_year
    else:
        spares_map: Any = spares_cost_per_year
        spares = SparesCostPerYear(
            amount_minor_units=int(spares_map["amount_minor_units"]),
            currency=str(spares_map["currency"]),
        )

    # Normalize thermal input (accept either dataclass or duck-typed mapping)
    if isinstance(thermal_service_summary, ThermalServiceSummary):
        thermal = thermal_service_summary
    else:
        thermal_map: Any = thermal_service_summary
        thermal = ThermalServiceSummary(
            Q_w=float(thermal_map["Q_w"]),
            A_m2=float(thermal_map["A_m2"]),
            U_w_per_m2_k=float(thermal_map["U_w_per_m2_k"]),
            LMTD_k=float(thermal_map["LMTD_k"]),
        )

    blockers: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []

    # Step 1 — propagate any CostBreakdown blockers.  Per §5.3.2 final Rule,
    # the estimator consumes the CostBreakdown envelope only; if the envelope
    # carries blockers (state == NOT_COMPUTABLE) the estimator MUST NOT
    # compute life-cycle energy math and MUST propagate.
    cost_breakdown_blockers = _cost_breakdown_blockers(cost_breakdown)
    for entry in cost_breakdown_blockers:
        blockers.append(_coerce_cost_breakdown_entry(entry))

    # Step 2 — no-default validation (§5.3.1).  Each required input absent
    # or out-of-envelope surfaces a frozen closed-set blocker.
    required_field_blockers = _check_required_fields(
        annual_operating_hours=annual_operating_hours,
        design_life_years=design_life_years,
        discount_rate=discount_rate,
        salvage_fraction=salvage_fraction,
        fouling_energy_penalty_factor=fouling_energy_penalty_factor,
        pump_or_fan_power_kw=pump_or_fan_power_kw,
        pump_or_fan_efficiency=pump_or_fan_efficiency,
        case_currency=case_currency,
        thermal=thermal,
    )
    blockers.extend(required_field_blockers)

    # Step 3 — currency alignment (§5.3.1 + §6.1).  No conversion; mismatch
    # with the spares optional input returns ``currency_mismatch_blocker``.
    spares_blockers = _check_spares_currency(spares, case_currency)
    blockers.extend(spares_blockers)

    # Step 4 — fouling_energy_penalty_factor envelope (§5.3.1: float ∈ [1.0, 2.0]).
    # The upper bound == 2.0 is treated as suspect per §9.2 frozen set
    # (``fouling_energy_penalty_factor_at_upper_bound_warning``); values
    # outside [1.0, 2.0] surface as ``unspecified_blocker`` with structured
    # ``details.reason = "fouling_energy_penalty_factor_out_of_envelope"`` per
    # the §9 safety-net pattern (no new enum entry).
    fouling_warnings, fouling_blockers = _check_fouling_envelope(fouling_energy_penalty_factor)
    warnings.extend(fouling_warnings)
    blockers.extend(fouling_blockers)

    # Step 5 — discount_rate zero-warning (§9.2 frozen set).
    # discount_rate == 0.0 is treated as advisory (no discounting applied),
    # per §9.2 frozen ``discount_rate_zero_warning`` rule.
    discount_warnings = _check_discount_rate_zero(discount_rate)
    warnings.extend(discount_warnings)

    # Step 6 — restricted-source pointer-only boundary (§8).
    # If the upstream CostBreakdown carries any proprietary_restricted pointer
    # the §8 line 340 rule fires: a ``restricted_only_provenance_warning``
    # is surfaced (the estimator does not propagate any restricted value body).
    restricted_warnings = _check_restricted_source_warning(cost_breakdown, warnings)
    warnings.extend(restricted_warnings)

    # Step 7 — compute the §5.3.2 envelope.  When any blocker is present we
    # skip the energy math and emit zero / null placeholders per the
    # NOT_COMPUTABLE contract rule (§9.3 fan-out + §5.3.2 Rule 3).
    state = _derive_state(len(blockers), len(warnings))

    if blockers:
        energy_breakdown = _zero_energy_breakdown(case_currency)
    else:
        energy_breakdown = _compute_energy_breakdown(
            cost_breakdown=cost_breakdown,
            thermal=thermal,
            pump_or_fan_power_kw=pump_or_fan_power_kw,
            pump_or_fan_efficiency=pump_or_fan_efficiency,
            annual_operating_hours=annual_operating_hours,
            design_life_years=design_life_years,
            discount_rate=discount_rate,
            salvage_fraction=salvage_fraction,
            fouling_energy_penalty_factor=fouling_energy_penalty_factor,
            cleaning_cycle_years=cleaning_cycle_years,
            spares=spares,
            case_currency=case_currency,
        )
        # Step 7b — discount formula (Option A) deferred to design-amendment.
        # Per §5.3.2 Rule 2 the contract does not prescribe the formula; per
        # Rule 3 we emit ``null`` + ``unspecified_blocker`` with structured
        # ``details.reason = "discount_formula_pending_design_amendment"``.
        discount_blockers: list[dict[str, object]] = [
            {
                "code": BlockerCode.UNSPECIFIED_BLOCKER.value,
                "details": {
                    "reason": "discount_formula_pending_design_amendment",
                    "discount_rate_supplied": float(discount_rate),
                    "design_life_years_supplied": int(design_life_years),
                },
            }
        ]
        # Per §9.3, emitting a blocker transitions state to NOT_COMPUTABLE.
        # The discount-formula deferred path intentionally does so — the
        # caller sees that no discounted total is computable today.
        state = _derive_state(len(blockers) + len(discount_blockers), len(warnings))
        blockers.extend(discount_blockers)
        # Replace discounted_total_minor_units with null explicitly (already
        # null in _compute_energy_breakdown, but assert here for clarity).
        energy_breakdown["discounted_total_minor_units"] = None
        energy_breakdown["discounted_total_currency"] = case_currency

    inputs_used = {
        "pump_or_fan_power_kw_provenance": str(pump_or_fan_power_kw_provenance),
        "pump_or_fan_efficiency_provenance": str(pump_or_fan_efficiency_provenance),
        "annual_operating_hours_source": "case_input",
        "discount_rate_source": "case_input",
        "design_life_years_source": "case_input",
        "salvage_fraction_source": "case_input",
        "fouling_energy_penalty_factor_source": "case_input",
    }

    # Step 8 — invariant guard: every emitted blocker / warning code MUST
    # belong to the frozen closed set (§9).
    _assert_frozen_codes(blockers, warnings)

    # Step 9 — provenance_chain_hash (TASK-018 §7).
    provenance_chain_hash = _compute_provenance_chain_hash(
        source_record_ids=_energy_breakdown_source_record_ids(energy_breakdown),
        cost_breakdown=cost_breakdown,
        inputs_used=inputs_used,
    )

    # Step 10 — life_cycle_run_id (TASK-018 §5.3.2 deterministic UUID v5).
    life_cycle_run_id = _compute_life_cycle_run_id(
        schema_version=LIFECYCLE_SCHEMA_VERSION,
        provenance_chain_hash=provenance_chain_hash,
        state=state,
        energy_breakdown=energy_breakdown,
        inputs_used=inputs_used,
    )

    return LifeCycleEnergyBreakdown(
        schema_version=LIFECYCLE_SCHEMA_VERSION,
        life_cycle_run_id=life_cycle_run_id,
        state=state,
        energy_breakdown=energy_breakdown,
        inputs_used=inputs_used,
        warnings=tuple(warnings),
        blockers=tuple(blockers),
        provenance_chain_hash=provenance_chain_hash,
    )


# ---------------------------------------------------------------------------
# Internal helpers.
# ---------------------------------------------------------------------------


def _cost_breakdown_blockers(cost_breakdown: object) -> list[dict[str, object]]:
    """Pull the upstream ``CostBreakdown`` blockers (slice B contract)."""
    blockers_attr = getattr(cost_breakdown, "blockers", ())
    return [dict(entry) for entry in blockers_attr]


def _coerce_cost_breakdown_entry(entry: Mapping[str, object]) -> dict[str, object]:
    """Coerce a Slice B blocker entry to the Slice C dict shape."""
    details_obj = entry.get("details", {}) or {}
    details_dict: dict[str, object] = dict(details_obj) if isinstance(details_obj, Mapping) else {}
    return {
        "code": str(entry.get("code", BlockerCode.UNSPECIFIED_BLOCKER.value)),
        "details": details_dict,
    }


def _check_required_fields(
    *,
    annual_operating_hours: float,
    design_life_years: int,
    discount_rate: float,
    salvage_fraction: float,
    fouling_energy_penalty_factor: float,
    pump_or_fan_power_kw: float,
    pump_or_fan_efficiency: float,
    case_currency: str,
    thermal: ThermalServiceSummary,
) -> list[dict[str, object]]:
    """§5.3.1 no-default validation.  Each required input absent / out-of-envelope
    surfaces a frozen closed-set blocker.
    """
    blockers: list[dict[str, object]] = []

    if annual_operating_hours is None or float(annual_operating_hours) <= 0.0:
        blockers.append(
            {
                "code": BlockerCode.MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER.value,
                "details": {
                    "missing_field": "annual_operating_hours",
                    "rule": "§5.3.1 — required float > 0; no default; absence blocks",
                },
            }
        )

    if design_life_years is None or int(design_life_years) <= 0:
        blockers.append(
            {
                "code": BlockerCode.MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER.value,
                "details": {
                    "missing_field": "design_life_years",
                    "rule": "§5.3.1 — required int > 0; no default; absence blocks",
                },
            }
        )

    if discount_rate is None or not (
        DISCOUNT_RATE_MIN <= float(discount_rate) <= DISCOUNT_RATE_MAX
    ):
        blockers.append(
            {
                "code": BlockerCode.MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER.value,
                "details": {
                    "missing_field": "discount_rate",
                    "rule": "§5.3.1 — required float ∈ [0, 1]; no default; absence blocks",
                },
            }
        )

    if salvage_fraction is None or not (
        SALVAGE_FRACTION_MIN <= float(salvage_fraction) <= SALVAGE_FRACTION_MAX
    ):
        blockers.append(
            {
                "code": BlockerCode.MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER.value,
                "details": {
                    "missing_field": "salvage_fraction",
                    "rule": "§5.3.1 — required float ∈ [0, 1]; no default; absence blocks",
                },
            }
        )

    if fouling_energy_penalty_factor is None or not (
        FOULING_ENERGY_PENALTY_MIN
        <= float(fouling_energy_penalty_factor)
        <= FOULING_ENERGY_PENALTY_MAX
    ):
        blockers.append(
            {
                "code": BlockerCode.MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER.value,
                "details": {
                    "missing_field": "fouling_energy_penalty_factor",
                    "rule": "§5.3.1 — required float ∈ [1.0, 2.0]; no default; absence blocks",
                },
            }
        )

    if pump_or_fan_power_kw is None or float(pump_or_fan_power_kw) < 0.0:
        blockers.append(
            {
                "code": BlockerCode.MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER.value,
                "details": {
                    "missing_field": "pump_or_fan_power_kw",
                    "rule": "§5.3.1 — required float (kW) per unit, with provenance",
                },
            }
        )

    if pump_or_fan_efficiency is None or not (
        PUMP_OR_FAN_EFFICIENCY_MIN <= float(pump_or_fan_efficiency) <= PUMP_OR_FAN_EFFICIENCY_MAX
    ):
        blockers.append(
            {
                "code": BlockerCode.MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER.value,
                "details": {
                    "missing_field": "pump_or_fan_efficiency",
                    "rule": "§5.3.1 — required float ∈ [0, 1]",
                },
            }
        )

    if (
        not isinstance(case_currency, str)
        or not case_currency
        or not case_currency.isalpha()
        or not (2 <= len(case_currency) <= 6)
    ):
        blockers.append(
            {
                "code": BlockerCode.MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER.value,
                "details": {
                    "missing_field": "case_currency",
                    "rule": "§5.3.1 — required ISO 4217 alpha; no default",
                },
            }
        )

    # Thermal envelope shape — every field must be a finite float.
    thermal_invalid = (
        not _is_finite_float(thermal.Q_w)
        or not _is_finite_float(thermal.A_m2)
        or not _is_finite_float(thermal.U_w_per_m2_k)
        or not _is_finite_float(thermal.LMTD_k)
        or float(thermal.A_m2) <= 0.0
        or float(thermal.U_w_per_m2_k) <= 0.0
    )
    if thermal_invalid:
        blockers.append(
            {
                "code": BlockerCode.MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER.value,
                "details": {
                    "missing_field": "thermal_service_summary",
                    "rule": (
                        "§5.3.1 — required envelope (Q, A, U, LMTD); "
                        "non-finite or non-positive area/U"
                    ),
                },
            }
        )

    return blockers


def _check_spares_currency(
    spares: SparesCostPerYear | None,
    case_currency: str,
) -> list[dict[str, object]]:
    """§5.3.1 + §6.1 spares optional input currency alignment.

    No conversion.  Currency mismatch returns ``currency_mismatch_blocker``.
    """
    if spares is None:
        return []
    if str(spares.currency) != str(case_currency):
        return [
            {
                "code": BlockerCode.CURRENCY_MISMATCH_BLOCKER.value,
                "details": {
                    "case_currency": str(case_currency),
                    "spares_currency": str(spares.currency),
                    "reason": "spares_cost_per_year_minor_units currency mismatch",
                },
            }
        ]
    return []


def _check_fouling_envelope(
    fouling_energy_penalty_factor: float,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """§5.3.1 fouling_energy_penalty_factor envelope [1.0, 2.0].

    Upper bound == 2.0 ⇒ ``fouling_energy_penalty_factor_at_upper_bound_warning``
    (§9.2 frozen set; "treated as suspect").  Values strictly outside
    [1.0, 2.0] ⇒ ``unspecified_blocker`` with structured
    ``details.reason = "fouling_energy_penalty_factor_out_of_envelope"`` per
    the §9 safety-net pattern (no new enum entry).
    """
    warnings: list[dict[str, object]] = []
    blockers: list[dict[str, object]] = []

    if fouling_energy_penalty_factor is None:
        return warnings, blockers

    val = float(fouling_energy_penalty_factor)
    if val < FOULING_ENERGY_PENALTY_MIN or val > FOULING_ENERGY_PENALTY_MAX:
        blockers.append(
            {
                "code": BlockerCode.UNSPECIFIED_BLOCKER.value,
                "details": {
                    "reason": "fouling_energy_penalty_factor_out_of_envelope",
                    "fouling_energy_penalty_factor": val,
                    "envelope_min": FOULING_ENERGY_PENALTY_MIN,
                    "envelope_max": FOULING_ENERGY_PENALTY_MAX,
                },
            }
        )
    elif val == FOULING_ENERGY_PENALTY_MAX:
        warnings.append(
            {
                "code": WarningCode.FOULING_ENERGY_PENALTY_FACTOR_AT_UPPER_BOUND_WARNING.value,
                "details": {
                    "fouling_energy_penalty_factor": val,
                    "rule": "§9.2 — treated as suspect at upper bound",
                },
            }
        )

    return warnings, blockers


def _check_discount_rate_zero(discount_rate: float) -> list[dict[str, object]]:
    """§9.2 frozen ``discount_rate_zero_warning`` rule.

    When ``discount_rate == 0`` the discount formula collapses to a no-op;
    the §9.2 frozen rule surfaces an advisory warning so engineering
    reviewers see the no-discounting choice explicitly.
    """
    if discount_rate is None:
        return []
    if float(discount_rate) == 0.0:
        return [
            {
                "code": WarningCode.DISCOUNT_RATE_ZERO_WARNING.value,
                "details": {
                    "discount_rate": 0.0,
                    "rule": "§9.2 — input equals 0 (no discounting applied); advisory",
                },
            }
        ]
    return []


def _check_restricted_source_warning(
    cost_breakdown: object,
    existing_warnings: list[dict[str, object]],
) -> list[dict[str, object]]:
    """§8 line 340 restricted-source pointer-only warning propagation.

    Per §8: "A ``license_class_summary`` field on ``CostModelSelectionResult``
    and ``CostBreakdown`` lists counts per class; ``proprietary_restricted_count
    > 0`` results in a ``restricted_only_provenance_warning``, not a blocker."
    The estimator consumes the CostBreakdown envelope, so the same rule
    fires on the estimator side.  We do not duplicate the warning if it was
    already emitted by the upstream Slice B calculator.
    """
    summary_obj = getattr(cost_breakdown, "license_class_summary", None)
    if not isinstance(summary_obj, Mapping):
        return []
    restricted_count = int(summary_obj.get("proprietary_restricted_count", 0) or 0)
    if restricted_count <= 0:
        return []
    if any(
        existing.get("code") == WarningCode.RESTRICTED_ONLY_PROVENANCE_WARNING.value
        for existing in existing_warnings
    ):
        return []
    return [
        {
            "code": WarningCode.RESTRICTED_ONLY_PROVENANCE_WARNING.value,
            "details": {
                "reason": "CostBreakdown.license_class_summary.proprietary_restricted_count > 0",
                "proprietary_restricted_count": restricted_count,
            },
        }
    ]


def _zero_energy_breakdown(case_currency: str) -> dict[str, object]:
    """§5.3.2 NOT_COMPUTABLE canonical zero / null placeholder block."""
    return {
        "annual_pump_or_fan_energy_kwh": 0.0,
        "annual_fouling_energy_penalty_kwh": 0.0,
        "annual_cleaning_impact_minor_units": None,
        "annual_spares_minor_units": None,
        "design_life_years": 0,
        "discount_rate": 0.0,
        "total_lifecycle_pump_fan_energy_kwh": 0.0,
        "total_lifecycle_fouling_energy_kwh": 0.0,
        "total_lifecycle_cleaning_minor_units": None,
        "total_lifecycle_spares_minor_units": None,
        "salvage_minor_units": 0,
        # Per §5.3.2 Rule 3: ``discounted_total_minor_units: null`` (never 0)
        # when the implementation cannot compute it.  Slice C always emits
        # ``null`` here — see Step 7b for the Option A deferred-formula
        # blocker that explains the ``null``.
        "discounted_total_minor_units": None,
        "discounted_total_currency": str(case_currency),
    }


def _compute_energy_breakdown(
    *,
    cost_breakdown: object,
    thermal: ThermalServiceSummary,
    pump_or_fan_power_kw: float,
    pump_or_fan_efficiency: float,
    annual_operating_hours: float,
    design_life_years: int,
    discount_rate: float,
    salvage_fraction: float,
    fouling_energy_penalty_factor: float,
    cleaning_cycle_years: float | None,
    spares: SparesCostPerYear | None,
    case_currency: str,
) -> dict[str, object]:
    """Compute the §5.3.2 energy_breakdown block.

    Discipline:

        - ``annual_pump_or_fan_energy_kwh`` =
            ``pump_or_fan_power_kw / max(pump_or_fan_efficiency, ε) *
             annual_operating_hours``  (per §5.3.2 + §10 deterministic
            float via ``repr()``).
        - ``annual_fouling_energy_penalty_kwh`` =
            ``annual_pump_or_fan_energy_kwh * (fouling_energy_penalty_factor - 1)``.
        - ``total_lifecycle_*_kwh`` =
            ``annual_*_kwh * design_life_years``.
        - ``annual_cleaning_impact_minor_units`` / ``annual_spares_minor_units``
            = integer minor units when the optional inputs are present;
            ``null`` otherwise (§5.3.1 + §5.3.2).
        - ``salvage_minor_units`` = integer minor units (a non-computable
            value today; Slice C emits ``0`` because the Slice B
            ``CostBreakdown.capex_envelope_minor_units`` is the contract
            basis — but since Slice C does not actually compute salvage
            money today (no prescribed formula), we surface ``0`` as
            the contract-prescribed integer placeholder when no salvage
            is computable from the upstream cost envelope).
        - ``discounted_total_minor_units`` = ``null`` (always, in Slice C —
            see Option A deferred-formula rule).
        - All money outputs are integer minor units per §5.3.2 + §10.
    """
    eff = max(float(pump_or_fan_efficiency), 1e-12)
    annual_pump_fan_kwh = (float(pump_or_fan_power_kw) / eff) * float(annual_operating_hours)
    annual_fouling_kwh = annual_pump_fan_kwh * (float(fouling_energy_penalty_factor) - 1.0)
    total_pump_fan_kwh = annual_pump_fan_kwh * int(design_life_years)
    total_fouling_kwh = annual_fouling_kwh * int(design_life_years)

    # annual cleaning impact (integer minor units).  The cleaning impact per
    # year is conservatively zero (no prescribed formula in §5.3); the field
    # is reserved for a future design-amendment round to prescribe the
    # cleaning-cost formula.  Slice C surfaces ``0`` when cleaning_cycle_years
    # is supplied (so the field is non-null) and ``null`` otherwise.
    annual_cleaning_minor: int | None = None if cleaning_cycle_years is None else 0

    # annual spares (integer minor units).  §5.3.1 explicitly says "absence
    # leaves spares null"; Slice C surfaces the supplied amount when present,
    # else null.
    annual_spares_minor: int | None = None if spares is None else int(spares.amount_minor_units)

    # total lifecycle cleaning / spares (integer minor units × design_life)
    total_cleaning_minor: int | None = (
        None
        if annual_cleaning_minor is None
        else int(annual_cleaning_minor) * int(design_life_years)
    )
    total_spares_minor: int | None = (
        None if annual_spares_minor is None else int(annual_spares_minor) * int(design_life_years)
    )

    # salvage_minor_units — Slice C does not prescribe a salvage formula
    # either (§5.3.2 freezes the field but does not prescribe how to
    # compute it).  We surface ``0`` as the integer placeholder when
    # salvage_fraction > 0 (the caller has indicated salvage is meaningful);
    # otherwise ``0`` to keep the field integer-typed and contract-conformant.
    # A future TASK-018 design-amendment round may prescribe the formula.
    salvage_minor = 0

    return {
        "annual_pump_or_fan_energy_kwh": float(annual_pump_fan_kwh),
        "annual_fouling_energy_penalty_kwh": float(annual_fouling_kwh),
        "annual_cleaning_impact_minor_units": annual_cleaning_minor,
        "annual_spares_minor_units": annual_spares_minor,
        "design_life_years": int(design_life_years),
        "discount_rate": float(discount_rate),
        "total_lifecycle_pump_fan_energy_kwh": float(total_pump_fan_kwh),
        "total_lifecycle_fouling_energy_kwh": float(total_fouling_kwh),
        "total_lifecycle_cleaning_minor_units": total_cleaning_minor,
        "total_lifecycle_spares_minor_units": total_spares_minor,
        "salvage_minor_units": int(salvage_minor),
        # Per §5.3.2 Rule 3: ``null`` (never 0).  Slice C never computes the
        # discounted total; the deferred-formula blocker (Step 7b) explains
        # the ``null`` to callers.
        "discounted_total_minor_units": None,
        "discounted_total_currency": str(case_currency),
    }


def _energy_breakdown_source_record_ids(
    energy_breakdown: dict[str, object],
) -> list[str]:
    """Slice C does not surface TASK-013 ``source_record_ids`` directly —
    it consumes the Slice B ``CostBreakdown`` envelope.  We surface an
    empty source_record_ids list (the §7 hash will reflect this absence).
    """
    return []


def _derive_state(blocker_count: int, warning_count: int) -> str:
    if blocker_count >= 1:
        return "NOT_COMPUTABLE"
    if warning_count >= 1:
        return "COMPUTABLE_WITH_WARNINGS"
    return "COMPUTABLE"


def _assert_frozen_codes(
    blockers: list[dict[str, object]],
    warnings: list[dict[str, object]],
) -> None:
    for entry in blockers:
        code = entry.get("code")
        if code not in BLOCKER_CODES:
            raise CostSelectorError(
                BlockerCode.UNSPECIFIED_BLOCKER.value,
                details={"non_frozen_blocker_code": str(code)},
            )
    for entry in warnings:
        code = entry.get("code")
        if code not in WARNING_CODES:
            raise CostSelectorError(
                BlockerCode.UNSPECIFIED_BLOCKER.value,
                details={"non_frozen_warning_code": str(code)},
            )


def _is_finite_float(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        f = float(value)
        return f == f and f not in (float("inf"), float("-inf"))
    return False


# ---------------------------------------------------------------------------
# Hashing + UUID v5 helpers.
# ---------------------------------------------------------------------------


def _compute_provenance_chain_hash(
    *,
    source_record_ids: Sequence[str],
    cost_breakdown: object,
    inputs_used: Mapping[str, str],
) -> str:
    """§7 + §10: SHA-256 over a canonical-JSON of the estimator's fingerprint.

    The hash is anchored on the same provenance envelope Slice B uses:
    ``{source_record_ids, correlation_ids, case_input_field, license_class,
    schema_version}``.  Slice C reuses Slice B's
    ``license_class_summary`` (int-typed) for the ``license_class`` field so
    the hash is structurally compatible with downstream integration
    boundary checks.
    """
    license_summary = getattr(cost_breakdown, "license_class_summary", None)
    if isinstance(license_summary, Mapping):
        license_class = {
            "public_open_count": int(license_summary.get("public_open_count", 0) or 0),
            "internal_open_count": int(license_summary.get("internal_open_count", 0) or 0),
            "proprietary_restricted_count": int(
                license_summary.get("proprietary_restricted_count", 0) or 0
            ),
        }
    else:
        license_class = {
            "public_open_count": 0,
            "internal_open_count": 0,
            "proprietary_restricted_count": 0,
        }
    payload = json.dumps(
        {
            "source_record_ids": sorted(source_record_ids),
            "correlation_ids": [],
            "case_input_field": dict(inputs_used),
            "license_class": license_class,
            "schema_version": LIFECYCLE_SCHEMA_VERSION,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _compute_life_cycle_run_id(
    *,
    schema_version: str,
    provenance_chain_hash: str,
    state: str,
    energy_breakdown: Mapping[str, object],
    inputs_used: Mapping[str, str],
) -> str:
    """§5.3.2 ``life_cycle_run_id``: deterministic UUID v5 over the result fingerprint."""
    payload = json.dumps(
        {
            "schema_version": schema_version,
            "provenance_chain_hash": provenance_chain_hash,
            "state": state,
            "energy_breakdown": {k: _stable(v) for k, v in energy_breakdown.items()},
            "inputs_used": dict(inputs_used),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return str(uuid.uuid5(_LIFECYCLE_RUN_ID_NAMESPACE, payload))


def _stable(value: object) -> object:
    """Make a value JSON-stable for hashing purposes.

    Floats use ``repr()`` per §10 (deterministic IEEE-754 round-trip).  Tuples
    are sorted if all elements are strings (sorted ascending); otherwise
    preserved.  Lists are sorted if all elements are strings; otherwise
    preserved.  Nested dicts are recursively stabilized.
    """
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, tuple):
        if all(isinstance(x, str) for x in value):
            return sorted(value)
        return [_stable(x) for x in value]
    if isinstance(value, list):
        if all(isinstance(x, str) for x in value):
            return sorted(value)
        return [_stable(x) for x in value]
    if isinstance(value, Mapping):
        return {k: _stable(value[k]) for k in sorted(value.keys())}
    return value


__all__ = [
    "FOULING_ENERGY_PENALTY_MAX",
    "FOULING_ENERGY_PENALTY_MIN",
    "LifeCycleEnergyBreakdown",
    "LifeCycleEnergyEstimatorInput",
    "LIFECYCLE_SCHEMA_VERSION",
    "SparesCostPerYear",
    "ThermalServiceSummary",
    "calculate_life_cycle_breakdown",
]
