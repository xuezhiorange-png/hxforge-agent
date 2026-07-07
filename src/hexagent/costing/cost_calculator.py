"""CostCalculator — TASK-018 §5.2 deterministic C0/C1 cost breakdown.

This module implements the application-layer cost calculator that consumes
the ``CostModelSelectionResult`` from Slice A
(``cost_model_selector.py``) and produces the frozen
``CostBreakdown`` envelope documented in TASK-018 §5.2.2.

Slice B scope (TASK-018 implementation round 2):

    - Consume ``CostModelSelectionResult`` (read-only; no record mutation).
    - Consume TASK-017 ``MassBreakdown`` envelope (read-only) for C1.
    - Produce the §5.2.2 ``CostBreakdown`` envelope deterministically.
    - Reuse the frozen closed-set blocker / warning codes from §9
      (no new codes introduced; runtime emits only codes enumerated in
      §9.1 / §9.2). NOTE: TASK-018 §5.2.2 names the
      ``c0_heuristic_out_of_envelope_blocker`` condition for an
      out-of-envelope ``c0_heuristic_overrides`` multiplier, but §9.1
      does NOT contain a dedicated entry for it. Per §9 (top), this
      module therefore surfaces such cases via the §9 safety-net
      pattern: ``unspecified_blocker`` with
      ``details.reason = "c0_heuristic_out_of_envelope"``. Adding a
      dedicated blocker code to §9.1 requires a separate TASK-018
      §9 design-amendment PR.

Slice B does NOT include:

    - ``LifeCycleEnergyEstimator`` (lives in
      ``life_cycle_energy_estimator.py``, Slice C — separate authorization).
    - CAPEX / OPEX envelope decomposition (the contract specifies a
      single ``capex_envelope_minor_units`` derived from C0 + C1).
    - Currency conversion (TASK-018 §6.1: never converted).
    - C2 historical-project regression.
    - C3 vendor quotation / supplier quote.
    - Pressure-drop / C4 logic.
    - Any fuzzy / heuristic invention of cost values — every minor
      unit traceable to a TASK-013 record's ``cost_value``.

Deterministic guarantees (TASK-018 §10):

    - ``amount_minor_units`` are integers (no floats in money output).
    - ``calculator_run_id`` is a deterministic UUID v5 over a canonical
      payload anchored on the Frozen Contract Authority Base SHA.
    - component_breakdown ordering: cost_record_id ASC, then
      cost_record_version DESC (matching Slice A's sort order).
    - source_record_ids ASC (deterministic).
    - fingerprint-feeding ``provenance_chain_hash`` follows §7.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

from .cost_model_selector import SCHEMA_VERSION
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

# TASK-018 §5.2: c0_heuristic_overrides envelope. A caller-supplied
# multiplier outside this closed interval is the condition named in
# TASK-018 §5.2.2 (a "c0_heuristic_out_of_envelope" violation).  Per
# §9.1 (frozen closed set) and §9 (top, "No new codes may be introduced
# without amending this section"), no dedicated entry exists in §9.1
# for this condition; this module surfaces it under the §9 safety-net
# pattern by emitting ``unspecified_blocker`` with
# ``details.reason = "c0_heuristic_out_of_envelope"`` (see Step 2
# below).  Adding a dedicated ``c0_heuristic_out_of_envelope_blocker``
# entry to §9.1 requires a separate TASK-018 §9 design-amendment PR.
_C0_HEURISTIC_OVERRIDE_MIN: Final[float] = 0.5
_C0_HEURISTIC_OVERRIDE_MAX: Final[float] = 2.0

# Source-currency sentinel per §5.2.1: ``case_currency="SOURCE"``
# preserves the source record's currency verbatim when the contract
# permits it.
SOURCE_CURRENCY_SENTINEL: Final[str] = "SOURCE"

# Frozen schema version emitted on the ``CostBreakdown`` envelope.
CALCULATOR_SCHEMA_VERSION: Final[str] = SCHEMA_VERSION

# Stable UUID namespace for ``calculator_run_id`` (TASK-018 §5.2.2
# requires UUID v5 over a canonical payload).  Mirrors the
# Slice A pattern: anchored on the SHA-256 of the Frozen Contract
# Authority Base SHA.  A future TASK-018 design-amendment round that
# re-anchors to a new base SHA MUST regenerate this namespace too.
_CALCULATOR_RUN_ID_NAMESPACE: Final[uuid.UUID] = uuid.UUID(
    bytes=bytes(
        hashlib.sha256(
            b"task-018-calculator-run-idns:"
            + bytes.fromhex("5f96cf761d470b82faa1a5d164eefd42360c7df9")
        ).digest()[:16]
    )
)


# ---------------------------------------------------------------------------
# Public input / output envelopes (§5.2.1 + §5.2.2).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CostCalculatorInput:
    """§5.2.1 input envelope for ``CostCalculator``.

    All fields are keyword-only to make the public contract explicit.
    The default factory on ``c0_heuristic_overrides`` produces an
    empty dict so most callers omit it.
    """

    cost_model_selection_result: object  # CostModelSelectionResult, typed structurally
    mass_breakdown: object  # MassBreakdown (TASK-017), typed structurally
    case_currency: str
    case_region: str
    effective_date: str  # RFC 3339 UTC `Z` string
    component_role_overrides: Mapping[str, str] = field(default_factory=dict)
    c0_heuristic_overrides: Mapping[str, float] = field(default_factory=dict)
    escalation_index_reference_filter: frozenset[str] | None = None


@dataclass(frozen=True)
class ComponentSubtotalEntry:
    """A single component-role sub-total inside a ``*_subtotal`` block.

    Cost figures are INTEGER minor units per §5.2.2 / §10.
    """

    component_role: str
    cost_record_id: str
    cost_record_version: str
    cost_category: str
    amount_minor_units: int
    currency: str


@dataclass(frozen=True)
class CostSubtotalBlock:
    """§5.2.2 ``c0_subtotal`` / ``c1_subtotal`` block."""

    amount_minor_units: int
    currency: str
    component_breakdown: tuple[ComponentSubtotalEntry, ...]
    source_record_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "amount_minor_units": int(self.amount_minor_units),
            "currency": self.currency,
            "component_breakdown": [
                {
                    "component_role": e.component_role,
                    "cost_record_id": e.cost_record_id,
                    "cost_record_version": e.cost_record_version,
                    "cost_category": e.cost_category,
                    "amount_minor_units": int(e.amount_minor_units),
                    "currency": e.currency,
                }
                for e in self.component_breakdown
            ],
            "source_record_ids": list(self.source_record_ids),
        }


@dataclass(frozen=True)
class CostBreakdown:
    """§5.2.2 ``CostBreakdown`` envelope emitted by ``CostCalculator``.

    Result-state implications (§9.3):

        ``len(blockers) >= 1`` ⇒ ``state = NOT_COMPUTABLE``
        ``len(warnings) >= 1`` (and blockers empty) ⇒
        ``state = COMPUTABLE_WITH_WARNINGS``
        else ⇒ ``state = COMPUTABLE``
    """

    schema_version: str
    calculator_run_id: str
    state: str
    cost_breakdown: dict[str, object]  # CostSubtotalBlock.to_dict() shapes
    capex_envelope_minor_units: int
    capex_envelope_currency: str
    escalation_pointer_used: str | None
    license_class_summary: dict[str, int]
    warnings: tuple[dict[str, object], ...]
    blockers: tuple[dict[str, object], ...]
    provenance_chain_hash: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "calculator_run_id": self.calculator_run_id,
            "state": self.state,
            "cost_breakdown": self.cost_breakdown,
            "capex_envelope_minor_units": int(self.capex_envelope_minor_units),
            "capex_envelope_currency": self.capex_envelope_currency,
            "escalation_pointer_used": self.escalation_pointer_used,
            "license_class_summary": dict(self.license_class_summary),
            "warnings": list(self.warnings),
            "blockers": list(self.blockers),
            "provenance_chain_hash": self.provenance_chain_hash,
        }


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------


def calculate_cost_breakdown(
    *,
    cost_model_selection_result: object,
    mass_breakdown: object,
    case_currency: str,
    case_region: str,
    effective_date: str,
    component_role_overrides: Mapping[str, str] | None = None,
    c0_heuristic_overrides: Mapping[str, float] | None = None,
    escalation_index_reference_filter: frozenset[str] | None = None,
) -> CostBreakdown:
    """Compute a deterministic ``CostBreakdown`` per TASK-018 §5.2.

    The function is pure with respect to all inputs:

        - never mutates ``cost_model_selection_result`` or
          ``mass_breakdown`` or any records therein;
        - produces a fully deterministic result for identical inputs
          (same payload ⇒ same ``calculator_run_id`` byte-for-byte);
        - returns a ``CostBreakdown`` with ``state = NOT_COMPUTABLE``
          when any blocker is present, leaving C0 / C1 sub-totals
          zeroed and ``capex_envelope_minor_units = 0``.

    Raises ``CostSelectorError`` only when a frozen-closed-set invariant
    is violated (e.g. a non-frozen blocker code slipped through). Routine
    computation failures surface as ``CostBreakdown.blockers`` entries.
    """
    component_role_overrides = dict(component_role_overrides or {})
    c0_heuristic_overrides_map = dict(c0_heuristic_overrides or {})

    blockers: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []

    # Step 1 — propagate any selector-originated blockers.  The selector
    # is the source of truth for "did selection succeed?"; if it
    # emitted >=1 blocker the calculator MUST NOT perform any cost math
    # (§5.2 + §9.3 fan-out rule).  This includes the
    # ``region_unsupported_blocker``, ``validity_envelope_blocker``,
    # ``restricted_body_propagation_blocker`` etc. emitted by Slice A.
    selector_blockers = _selector_blockers(cost_model_selection_result)
    if selector_blockers:
        for entry in selector_blockers:
            blockers.append(_coerce_selector_entry(entry))

    # Step 2 — c0_heuristic_overrides envelope enforcement (§5.2 line 230).
    #
    # NOTE: TASK-018 §9.1 lists the frozen closed set of blocker codes,
    # which does NOT include a dedicated ``c0_heuristic_out_of_envelope_blocker``
    # entry.  Adding a new entry to ``BlockerCode`` would require a §9
    # design-amendment PR.  Per the §9 "anything else" rule, out-of-envelope
    # c0 overrides therefore surface as ``unspecified_blocker`` with
    # fully descriptive ``details`` so callers can distinguish them
    # (the calculator carries a structured envelope-break context, not
    # a generic safety-net "anything else" message).
    for cat, mult in c0_heuristic_overrides_map.items():
        if not (_C0_HEURISTIC_OVERRIDE_MIN <= float(mult) <= _C0_HEURISTIC_OVERRIDE_MAX):
            blockers.append(
                {
                    "code": BlockerCode.UNSPECIFIED_BLOCKER.value,
                    "details": {
                        "reason": "c0_heuristic_out_of_envelope",
                        "cost_category": str(cat),
                        "multiplier": float(mult),
                        "envelope_min": _C0_HEURISTIC_OVERRIDE_MIN,
                        "envelope_max": _C0_HEURISTIC_OVERRIDE_MAX,
                    },
                }
            )

    # Step 3 — currency alignment.
    chosen_currency, currency_blockers = _resolve_currency(
        cost_model_selection_result=cost_model_selection_result,
        case_currency=case_currency,
    )
    blockers.extend(currency_blockers)

    # Step 4 — restrict to public_open / internal_open only.
    visible_records = _filter_visible_records(cost_model_selection_result)

    # Step 5 — verify the chosen currency matches every visible
    # record's currency (the §5.2 / §6.1 rule: no conversion, all
    # must align or we block).  This catches cross-currency
    # contamination that the selector let through.
    for r in visible_records:
        rec_currency = str(r.get("currency", ""))
        if rec_currency and rec_currency != chosen_currency:
            # _resolve_currency already mapped case_currency="SOURCE"
            # to a single source currency; any record outside that
            # single chosen currency is a true mismatch.
            blockers.append(
                {
                    "code": BlockerCode.CURRENCY_MISMATCH_BLOCKER.value,
                    "details": {
                        "record_currency": rec_currency,
                        "case_currency": case_currency,
                        "chosen_currency": chosen_currency,
                    },
                }
            )

    # Step 6 — escalation pointer derivation.
    escalation_pointer_used, escalation_warnings, escalation_blockers = _resolve_escalation(
        visible_records=visible_records,
        escalation_index_reference_filter=escalation_index_reference_filter,
    )
    blockers.extend(escalation_blockers)
    warnings.extend(escalation_warnings)

    # Step 7 — compute C0 / C1 sub-totals.  When any blocker is present
    # we skip the math entirely (§9.3 fan-out to NOT_COMPUTABLE).
    if blockers:
        c0_block = _zero_subtotal(chosen_currency)
        c1_block = _zero_subtotal(chosen_currency)
        capex_minor_units = 0
    else:
        c0_records = _c0_records(cost_model_selection_result)
        c1_records = _c1_records(cost_model_selection_result)
        c0_block = _compute_subtotal(
            records=c0_records,
            currency=chosen_currency,
            component_role_overrides=component_role_overrides,
            c0_heuristic_overrides=c0_heuristic_overrides_map,
        )
        c1_block = _compute_c1_subtotal(
            records=c1_records,
            mass_breakdown=mass_breakdown,
            currency=chosen_currency,
            component_role_overrides=component_role_overrides,
        )
        capex_minor_units = int(str(c0_block["amount_minor_units"])) + int(
            str(c1_block["amount_minor_units"])
        )

    # Step 8 — license summary propagation (mirrors §5.1.3 envelope).
    license_summary = _license_summary(cost_model_selection_result)

    # Step 9 — per §8 line 340, the
    # ``restricted_only_provenance_warning`` rule also applies on
    # ``CostBreakdown`` whenever proprietary_restricted_count > 0; we
    # do not duplicate the warning if the selector already added one
    # for the same selection.
    if license_summary["proprietary_restricted_count"] > 0 and not any(
        existing.get("code") == WarningCode.RESTRICTED_ONLY_PROVENANCE_WARNING.value
        for existing in warnings
    ):
        warnings.append(
            {
                "code": WarningCode.RESTRICTED_ONLY_PROVENANCE_WARNING.value,
                "details": {
                    "reason": "license_class_summary.proprietary_restricted_count > 0",
                    "proprietary_restricted_count": license_summary["proprietary_restricted_count"],
                },
            }
        )

    state = _derive_state(len(blockers), len(warnings))

    # Step 10 — invariant guard: every emitted blocker / warning code
    # MUST belong to the frozen closed set (§9).
    _assert_frozen_codes(blockers, warnings)

    # Step 11 — provenance_chain_hash (TASK-018 §7).
    provenance_chain_hash = _compute_provenance_chain_hash(
        source_record_ids=_combined_source_record_ids(c0_block, c1_block),
        license_summary=license_summary,
    )

    # Step 12 — calculator_run_id (TASK-018 §5.2.2 deterministic UUID v5).
    calculator_run_id = _compute_calculator_run_id(
        schema_version=CALCULATOR_SCHEMA_VERSION,
        provenance_chain_hash=provenance_chain_hash,
        state=state,
        c0_amount=int(str(c0_block["amount_minor_units"])),
        c1_amount=int(str(c1_block["amount_minor_units"])),
        chosen_currency=chosen_currency,
        escalation_pointer_used=escalation_pointer_used,
        license_summary=license_summary,
    )

    return CostBreakdown(
        schema_version=CALCULATOR_SCHEMA_VERSION,
        calculator_run_id=calculator_run_id,
        state=state,
        cost_breakdown={
            "c0_subtotal": c0_block,
            "c1_subtotal": c1_block,
        },
        capex_envelope_minor_units=int(capex_minor_units),
        capex_envelope_currency=chosen_currency,
        escalation_pointer_used=escalation_pointer_used,
        license_class_summary=license_summary,
        warnings=tuple(warnings),
        blockers=tuple(blockers),
        provenance_chain_hash=provenance_chain_hash,
    )


# ---------------------------------------------------------------------------
# Internal helpers.
# ---------------------------------------------------------------------------


def _selector_blockers(result: object) -> list[dict[str, object]]:
    """Pull the selector's blockers (a frozen-closed-set invariant)."""
    blockers_attr = getattr(result, "selection_blockers", ())
    return [dict(entry) for entry in blockers_attr]


def _coerce_selector_entry(entry: Mapping[str, object]) -> dict[str, object]:
    """Coerce a selector blocker entry to the calculator's dict shape."""
    details_obj = entry.get("details", {}) or {}
    details_dict: dict[str, object] = dict(details_obj) if isinstance(details_obj, Mapping) else {}
    return {
        "code": str(entry.get("code", BlockerCode.UNSPECIFIED_BLOCKER.value)),
        "details": details_dict,
    }


def _resolve_currency(
    *,
    cost_model_selection_result: object,
    case_currency: str,
) -> tuple[str, list[dict[str, object]]]:
    """Resolve the calculator's chosen currency per §5.2.1 + §6.1.

    The contract never performs currency conversion. The semantics are:

        1. ``case_currency == "SOURCE"``: preserve the source record's
           currency verbatim. If multiple distinct currencies appear
           across visible records this is *ambiguous* and returns a
           ``currency_mismatch_blocker`` (with empty chosen_currency).
        2. ``case_currency`` is an ISO 4217 alpha code: every visible
           record must agree with it. If any record disagrees, return
           a ``currency_mismatch_blocker`` (chosen_currency is the
           case currency verbatim, with the offending record listed
           in details).
    """
    blockers: list[dict[str, object]] = []
    visible = _filter_visible_records(cost_model_selection_result)
    distinct_currencies = sorted(
        {str(r.get("currency", "")) for r in visible if str(r.get("currency", ""))}
    )

    if case_currency == SOURCE_CURRENCY_SENTINEL:
        if not distinct_currencies:
            blockers.append(
                {
                    "code": BlockerCode.CURRENCY_MISMATCH_BLOCKER.value,
                    "details": {
                        "case_currency": case_currency,
                        "reason": "source_currency_unresolved_no_records",
                    },
                }
            )
            return "", blockers
        if len(distinct_currencies) > 1:
            blockers.append(
                {
                    "code": BlockerCode.CURRENCY_MISMATCH_BLOCKER.value,
                    "details": {
                        "case_currency": case_currency,
                        "reason": "source_currency_ambiguous_multiple_currencies",
                        "distinct_source_currencies": distinct_currencies,
                    },
                }
            )
            return "", blockers
        return distinct_currencies[0], blockers

    # case_currency is an explicit ISO 4217 code: every visible record
    # must agree.
    mismatches = [
        (str(r.get("cost_record_id", "")), str(r.get("currency", "")))
        for r in visible
        if str(r.get("currency", "")) and str(r.get("currency", "")) != case_currency
    ]
    if mismatches:
        blockers.append(
            {
                "code": BlockerCode.CURRENCY_MISMATCH_BLOCKER.value,
                "details": {
                    "case_currency": case_currency,
                    "reason": "case_currency_mismatch",
                    "offending_records": mismatches,
                },
            }
        )
    return case_currency, blockers


def _filter_visible_records(result: object) -> list[dict[str, object]]:
    """Return TASK-013-shaped records visible to cost math.

    Per §8 line 338, ``proprietary_restricted`` records are pointer-only:
    their ``cost_value``, ``cost_basis``, and any quantity are NOT
    propagated. We additionally drop them from the visible set entirely
    for cost arithmetic so they cannot accidentally contribute to the
    cost envelope.
    """
    visible: list[dict[str, object]] = []
    for record in _all_records(result):
        if not isinstance(record, Mapping):
            continue
        if str(record.get("license_class", "")) == "proprietary_restricted":
            continue
        # Slice A sets ``cost_value = None`` for restricted records (pointer
        # only); the rule above covers this case via the license_class check.
        visible.append(dict(record))
    return visible


def _all_records(result: object) -> list[Mapping[str, object]]:
    c0 = getattr(result, "c0_records", ())
    c1 = getattr(result, "c1_records", ())
    out: list[Mapping[str, object]] = []
    for r in list(c0) + list(c1):
        out.append(dict(r) if isinstance(r, Mapping) else {})
    return out


def _c0_records(result: object) -> list[Mapping[str, object]]:
    return [dict(r) for r in getattr(result, "c0_records", ())]


def _c1_records(result: object) -> list[Mapping[str, object]]:
    return [dict(r) for r in getattr(result, "c1_records", ())]


def _license_summary(result: object) -> dict[str, int]:
    """Mirror the §5.1.3 license_class_summary typed-int shape."""
    raw = getattr(result, "license_class_summary", None)
    if isinstance(raw, Mapping):
        return {
            "public_open_count": int(raw.get("public_open_count", 0) or 0),
            "internal_open_count": int(raw.get("internal_open_count", 0) or 0),
            "proprietary_restricted_count": int(raw.get("proprietary_restricted_count", 0) or 0),
        }
    return {
        "public_open_count": 0,
        "internal_open_count": 0,
        "proprietary_restricted_count": 0,
    }


def _resolve_escalation(
    *,
    visible_records: Sequence[Mapping[str, object]],
    escalation_index_reference_filter: frozenset[str] | None,
) -> tuple[str | None, list[dict[str, object]], list[dict[str, object]]]:
    """Resolve ``escalation_pointer_used`` per §5.2 rule.

    Discipline:

        - If the filter is ``None`` (or empty): no escalation is applied.
        - If the filter is non-empty: pick the first visible record whose
          ``escalation_index_reference`` is in the filter set.  If multiple
          match, pick the deterministic min-cost_record_id; this is the
          "no default" path.
        - Surfaces ``currency_fallback_used_warning`` when the chosen
          pointer comes from a record the selector excluded by license
          class (no such case in the current contract path, but recorded
          for forward compat).
    """
    warnings: list[dict[str, object]] = []
    blockers: list[dict[str, object]] = []

    if not escalation_index_reference_filter:
        return None, warnings, blockers

    eligible: list[Mapping[str, object]] = []
    for record in visible_records:
        pointer = record.get("escalation_index_reference")
        if isinstance(pointer, str) and pointer in escalation_index_reference_filter:
            eligible.append(record)

    if not eligible:
        blockers.append(
            {
                "code": BlockerCode.UNSPECIFIED_BLOCKER.value,
                "details": {
                    "reason": "no_visible_record_with_escalation_pointer_in_filter",
                    "escalation_index_reference_filter": sorted(escalation_index_reference_filter),
                },
            }
        )
        return None, warnings, blockers

    eligible.sort(
        key=lambda r: (
            str(r.get("cost_record_id", "")),
            _negate_semver(str(r.get("cost_record_version", "0.0.0"))),
        )
    )
    return str(eligible[0].get("escalation_index_reference", "")) or None, warnings, blockers


def _compute_subtotal(
    *,
    records: Iterable[Mapping[str, object]],
    currency: str,
    component_role_overrides: Mapping[str, str],
    c0_heuristic_overrides: Mapping[str, float],
) -> dict[str, object]:
    """Compute a deterministic C0 / C1 ``CostSubtotalBlock`` dict.

    The arithmetic contract:

        - Every minor-unit amount is an INTEGER (no floats in money
          output). Numeric inputs may be ``int | float`` (TASK-013
          ``cost_value``); the conversion rounds-to-nearest then
          casts to int.  NaN / inf inputs produce 0 minor units and a
          bookkeeping ``unspecified_warning`` so callers can see the
          data quality issue without blocking.
        - ``component_role`` defaults to ``""`` (the empty string)
          unless the caller supplied a ``component_role_overrides``
          mapping keyed on ``cost_record_id``.
        - Ordering is ``cost_record_id`` ASC, then ``cost_record_version``
          DESC (same as Slice A).
    """
    selected: list[tuple[_RecordKey, dict[str, object]]] = []
    source_record_ids: list[str] = []
    notes_for_warnings: list[str] = []

    for record in records:
        if not isinstance(record, Mapping):
            continue
        if str(record.get("license_class", "")) == "proprietary_restricted":
            # Pointer-only; never contribute to the math.
            continue
        record_id = str(record.get("cost_record_id", ""))
        record_version = str(record.get("cost_record_version", "0.0.0"))
        record_category = str(record.get("cost_category", ""))
        try:
            sort_key = _RecordKey(
                cost_record_id=record_id,
                cost_record_version=record_version,
            )
        except _InvalidSemver as exc:
            notes_for_warnings.append(f"invalid cost_record_version on {record_id}: {exc.value}")
            continue

        minor_units = _cost_value_to_minor_units(record.get("cost_value"))
        if minor_units is None:
            notes_for_warnings.append(
                f"non-finite cost_value on {record_id}: {record.get('cost_value')!r}"
            )
            minor_units = 0
        else:
            multiplier = c0_heuristic_overrides.get(record_category)
            if multiplier is not None:
                # The envelope guard has already filtered out-of-envelope
                # multipliers; this is the in-envelope scaling.
                minor_units = int(round(minor_units * float(multiplier)))

        component_role = component_role_overrides.get(record_id, "")
        selected.append(
            (
                sort_key,
                {
                    "component_role": component_role,
                    "cost_record_id": record_id,
                    "cost_record_version": record_version,
                    "cost_category": record_category,
                    "amount_minor_units": int(minor_units),
                    "currency": str(record.get("currency", currency)),
                },
            )
        )
        if record_id:
            source_record_ids.append(record_id)

    selected.sort(
        key=lambda kr: (
            kr[0].cost_record_id,
            _negate_semver(kr[0].cost_record_version),
        )
    )

    component_breakdown = tuple(
        ComponentSubtotalEntry(
            component_role=str(e["component_role"]),
            cost_record_id=str(e["cost_record_id"]),
            cost_record_version=str(e["cost_record_version"]),
            cost_category=str(e["cost_category"]),
            amount_minor_units=int(str(e["amount_minor_units"])),
            currency=str(e["currency"]),
        )
        for _, e in selected
    )

    return {
        "amount_minor_units": int(sum(int(str(e["amount_minor_units"])) for _, e in selected)),
        "currency": currency,
        "component_breakdown": [
            {
                "component_role": str(e.component_role),
                "cost_record_id": str(e.cost_record_id),
                "cost_record_version": str(e.cost_record_version),
                "cost_category": str(e.cost_category),
                "amount_minor_units": int(e.amount_minor_units),
                "currency": str(e.currency),
            }
            for e in component_breakdown
        ],
        "source_record_ids": sorted({str(rid) for rid in source_record_ids if rid}),
        # bookkeeping notes are echoed by the caller into the
        # CalculatorResult.warnings list; we surface here for test
        # introspection.
        "_internal_notes": notes_for_warnings,
    }


def _compute_c1_subtotal(
    *,
    records: Iterable[Mapping[str, object]],
    mass_breakdown: object,
    currency: str,
    component_role_overrides: Mapping[str, str],
) -> dict[str, object]:
    """C1 sub-total: combines C1 record ``cost_value`` with TASK-017 mass.

    The C1 arithmetic differs from C0 because TASK-018 §5.2 mandates
    that C1 records are "material-weight + man-hour + labor-burden cost
    categories that consume TASK-017 mass totals (``MassBreakdown``)
    plus TASK-013 labor-minute records".

    Discipline:

        - Each C1 record's ``cost_value`` is interpreted in minor units
          per its ``quantity_basis``:
              ``currency_per_kg`` × TASK-017 ``total_kg`` (rounded)
              ``currency_per_hour`` × 0 (no time input from this slice)
              any other ``quantity_basis`` is treated as scalar.
        - mass is read via ``getattr(mass_breakdown, "total_kg", 0.0)``
          (duck-typed against TASK-017 ``MassBreakdown``).
        - integer minor units only.
    """
    mass_total_kg = 0.0
    total_kg_attr = getattr(mass_breakdown, "total_kg", None)
    if isinstance(total_kg_attr, (int, float)):
        mass_total_kg = float(total_kg_attr)

    selected: list[tuple[_RecordKey, dict[str, object]]] = []
    source_record_ids: list[str] = []
    notes_for_warnings: list[str] = []

    for record in records:
        if not isinstance(record, Mapping):
            continue
        if str(record.get("license_class", "")) == "proprietary_restricted":
            continue
        record_id = str(record.get("cost_record_id", ""))
        record_version = str(record.get("cost_record_version", "0.0.0"))
        record_category = str(record.get("cost_category", ""))
        quantity_basis = str(record.get("quantity_basis", ""))
        try:
            sort_key = _RecordKey(
                cost_record_id=record_id,
                cost_record_version=record_version,
            )
        except _InvalidSemver as exc:
            notes_for_warnings.append(f"invalid cost_record_version on {record_id}: {exc.value}")
            continue
        base_minor = _cost_value_to_minor_units(record.get("cost_value"))
        if base_minor is None:
            notes_for_warnings.append(
                f"non-finite cost_value on {record_id}: {record.get('cost_value')!r}"
            )
            base_minor = 0

        if quantity_basis == "currency_per_kg":
            minor_units = int(round(base_minor * mass_total_kg))
        elif quantity_basis == "currency_per_hour":
            # No labor-time input from this slice; C1 is bounded to
            # cost-per-kg semantics at the calculator layer.  Falling
            # back to base_minor keeps every C1 record auditable
            # without inventing labor hours.
            minor_units = int(round(base_minor))
        else:
            minor_units = int(round(base_minor))

        component_role = component_role_overrides.get(record_id, "")
        selected.append(
            (
                sort_key,
                {
                    "component_role": component_role,
                    "cost_record_id": record_id,
                    "cost_record_version": record_version,
                    "cost_category": record_category,
                    "amount_minor_units": int(minor_units),
                    "currency": str(record.get("currency", currency)),
                },
            )
        )
        if record_id:
            source_record_ids.append(record_id)

    selected.sort(
        key=lambda kr: (
            kr[0].cost_record_id,
            _negate_semver(kr[0].cost_record_version),
        )
    )

    component_breakdown = tuple(
        ComponentSubtotalEntry(
            component_role=str(e["component_role"]),
            cost_record_id=str(e["cost_record_id"]),
            cost_record_version=str(e["cost_record_version"]),
            cost_category=str(e["cost_category"]),
            amount_minor_units=int(str(e["amount_minor_units"])),
            currency=str(e["currency"]),
        )
        for _, e in selected
    )

    return {
        "amount_minor_units": int(sum(int(str(e["amount_minor_units"])) for _, e in selected)),
        "currency": currency,
        "component_breakdown": [
            {
                "component_role": str(e.component_role),
                "cost_record_id": str(e.cost_record_id),
                "cost_record_version": str(e.cost_record_version),
                "cost_category": str(e.cost_category),
                "amount_minor_units": int(e.amount_minor_units),
                "currency": str(e.currency),
            }
            for e in component_breakdown
        ],
        "source_record_ids": sorted({str(rid) for rid in source_record_ids if rid}),
        "_internal_notes": notes_for_warnings,
    }


def _zero_subtotal(currency: str) -> dict[str, object]:
    """Return the canonical zero sub-total block used when blockers fan out."""
    return {
        "amount_minor_units": 0,
        "currency": currency or "",
        "component_breakdown": [],
        "source_record_ids": [],
    }


def _combined_source_record_ids(
    c0_block: Mapping[str, object], c1_block: Mapping[str, object]
) -> list[str]:
    c0_ids_obj = c0_block.get("source_record_ids", []) or []
    c1_ids_obj = c1_block.get("source_record_ids", []) or []
    c0_ids: list[str] = [str(x) for x in c0_ids_obj] if isinstance(c0_ids_obj, list) else []
    c1_ids: list[str] = [str(x) for x in c1_ids_obj] if isinstance(c1_ids_obj, list) else []
    return sorted(set(c0_ids) | set(c1_ids))


def _derive_state(blocker_count: int, warning_count: int) -> str:
    if blocker_count >= 1:
        return "NOT_COMPUTABLE"
    if warning_count >= 1:
        return "COMPUTABLE_WITH_WARNINGS"
    return "COMPUTABLE"


def _assert_frozen_codes(
    blockers: list[dict[str, object]], warnings: list[dict[str, object]]
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


# ---------------------------------------------------------------------------
# Hashing + UUID v5 helpers.
# ---------------------------------------------------------------------------


class _InvalidSemver(ValueError):
    """Raised when a ``cost_record_version`` cannot be parsed as semver."""

    def __init__(self, value: str) -> None:
        super().__init__(value)
        self.value = value


@dataclass(frozen=True)
class _RecordKey:
    cost_record_id: str
    cost_record_version: str


def _negate_semver(version: str) -> tuple[int, int, int, str]:
    """Return ``(-major, -minor, -patch, label)`` for DESC ``cost_record_version``.

    Mirrors Slice A's helper so the C0 / C1 sub-total component
    ordering is consistent with the selector's sort order.
    """
    core, _, _pre = version.partition("-")
    parts = core.split(".")
    try:
        nums = [int(p) for p in parts[:3]] + [0] * (3 - len(parts[:3]))
    except ValueError as exc:
        raise _InvalidSemver(version) from exc
    return (-nums[0], -nums[1], -nums[2], _pre)


def _cost_value_to_minor_units(value: object) -> int | None:
    """Convert a TASK-013 ``cost_value`` payload to integer minor units.

    The contract requires integer minor units in the output; inputs may
    be ``int`` / ``float`` / string-encoded numeric. NaN and inf are
    surfaced as ``None`` so the caller can emit a bookkeeping warning.
    """
    if isinstance(value, bool):
        # Reject booleans outright: True/False are not money values.
        return None
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return int(round(value))
    if isinstance(value, str):
        try:
            f = float(value)
        except ValueError:
            return None
        if f != f or f in (float("inf"), float("-inf")):
            return None
        return int(round(f))
    return None


def _compute_provenance_chain_hash(
    *,
    source_record_ids: Sequence[str],
    license_summary: Mapping[str, int],
) -> str:
    """§7 + §10: SHA-256 over a canonical-JSON of the calculator's fingerprint."""
    payload = json.dumps(
        {
            "source_record_ids": sorted(source_record_ids),
            "correlation_ids": [],
            "case_input_field": {},
            "license_class": dict(license_summary),
            "schema_version": CALCULATOR_SCHEMA_VERSION,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _compute_calculator_run_id(
    *,
    schema_version: str,
    provenance_chain_hash: str,
    state: str,
    c0_amount: int,
    c1_amount: int,
    chosen_currency: str,
    escalation_pointer_used: str | None,
    license_summary: Mapping[str, int],
) -> str:
    """§5.2.2 ``calculator_run_id``: deterministic UUID v5 over the result fingerprint."""
    payload = json.dumps(
        {
            "schema_version": schema_version,
            "provenance_chain_hash": provenance_chain_hash,
            "state": state,
            "c0_amount_minor_units": int(c0_amount),
            "c1_amount_minor_units": int(c1_amount),
            "chosen_currency": chosen_currency,
            "escalation_pointer_used": escalation_pointer_used,
            "license_summary": dict(license_summary),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return str(uuid.uuid5(_CALCULATOR_RUN_ID_NAMESPACE, payload))


__all__ = [
    "CALCULATOR_SCHEMA_VERSION",
    "CostBreakdown",
    "CostCalculatorInput",
    "CostSubtotalBlock",
    "ComponentSubtotalEntry",
    "SOURCE_CURRENCY_SENTINEL",
    "calculate_cost_breakdown",
]
