"""CostCalculator unit tests — TASK-018 Slice B.

Covers the unit-test checklist from the Slice B authorization:

    - CostBreakdown happy path (c0 + c1 records).
    - Deterministic component ordering.
    - Deterministic ``calculator_run_id``.
    - Stable ``source_record_ids``.
    - Integer minor units only (no floats in money output).
    - ``selection_blockers`` propagate to ``CostBreakdown.state ==
      NOT_COMPUTABLE``.
    - Currency mismatch returns ``currency_mismatch_blocker``.
    - ``case_currency="SOURCE"`` is deterministic; ambiguous source
      currency returns a ``currency_mismatch_blocker``.
    - c0 override within ``[0.5, 2.0]`` works.
    - c0 override outside ``[0.5, 2.0]`` returns an
      ``unspecified_blocker`` carrying
      ``details.reason == "c0_heuristic_out_of_envelope"``.
    - Escalation pointer is used only when permitted by selector /
      filter lineage.
    - No escalation is applied without filter lineage.
    - Restricted-source pointer-only behaviour preserved.
    - ``license_class_summary`` shape preserved.
    - No mutation of the input ``CostModelSelectionResult`` or its records.
    - Canonical serialization / stable hash behaviour.
    - Closed-set blocker / warning inventory.
    - Slice A selector regression tests still pass (covered indirectly
      via the slice A tests suite; this file freezes the Slice B
      contract only).
    - Frozen-contract-unchanged guard still passes (covered by the
      companion test file).

These tests assert the calculator's *contract* (frozen closed-set
behaviour per TASK-018 §9) rather than snapshot outputs. Any change
that breaks a test is, by construction, a contract change requiring a
TASK-018 design-amendment PR.
"""

from __future__ import annotations

import copy
import json
import re
import uuid

from hexagent.costing import (
    BLOCKER_CODES,
    BlockerCode,
    CostBreakdown,
    SelectionFilters,
    WarningCode,
    calculate_cost_breakdown,
    select_cost_records,
)

# ---------------------------------------------------------------------------
# Test fixture builders.
# ---------------------------------------------------------------------------

_PROPRIETARY_RESTRICTED = "proprietary_restricted"


def _make_record(
    cost_record_id: str = "rec-1",
    cost_record_version: str = "1.0.0",
    cost_category: str = "c0_baseline_estimate",
    cost_basis: str = "rule_of_thumb",
    currency: str = "USD",
    quantity_basis: str = "currency_per_kg",
    license_class: str = "public_open",
    source_class: str = "vendor_public",
    cost_value: object = 1250.0,  # $12.50 -> 1250 cents
    escalation_index_reference: str | None = None,
    validity_envelope: dict[str, object] | None = None,
    correlation_ids: list[str] | None = None,
) -> dict[str, object]:
    """Build a TASK-013-shaped governance record for calculator fixtures."""
    record: dict[str, object] = {
        "cost_record_id": cost_record_id,
        "cost_record_version": cost_record_version,
        "cost_category": cost_category,
        "cost_basis": cost_basis,
        "currency": currency,
        "quantity_basis": quantity_basis,
        "cost_value": cost_value,
        "license_class": license_class,
        "source_class": source_class,
        "escalation_index_reference": escalation_index_reference,
        "validity_envelope": dict(validity_envelope or {}),
    }
    if correlation_ids:
        record["correlation_ids"] = list(correlation_ids)
    return record


def _default_filters(
    record_currency: str | None = "USD",
    license_class_filter: frozenset[str] = frozenset({"public_open", "internal_open"}),
    cost_category_filter: frozenset[str] = frozenset(
        {"c0_baseline_estimate", "c1_material_weight", "c1_man_hours_labor"}
    ),
    quantity_basis_filter: frozenset[str] = frozenset({"currency_per_kg", "currency_per_hour"}),
) -> SelectionFilters:
    return SelectionFilters(
        material_family="carbon_steel",
        case_region="INTL",
        effective_date="2026-07-07T00:00:00Z",
        cost_category_filter=cost_category_filter,
        quantity_basis_filter=quantity_basis_filter,
        license_class_filter=license_class_filter,
        record_currency=record_currency,
        escalation_index_reference_filter=None,
    )


def _select(
    records: list[dict[str, object]],
    *,
    filters: SelectionFilters | None = None,
    escalation_index_reference_filter: frozenset[str] | None = None,
) -> object:
    """Run the Slice A selector and return the frozen result envelope."""
    if filters is None:
        filters = _default_filters()
    if escalation_index_reference_filter is not None:
        filters = SelectionFilters(
            material_family=filters.material_family,
            case_region=filters.case_region,
            effective_date=filters.effective_date,
            cost_category_filter=filters.cost_category_filter,
            quantity_basis_filter=filters.quantity_basis_filter,
            license_class_filter=filters.license_class_filter,
            escalation_index_reference_filter=escalation_index_reference_filter,
            record_currency=filters.record_currency,
            validity_envelope=filters.validity_envelope,
        )
    return select_cost_records(list(records), filters)


class _StubMassBreakdown:
    """Duck-typed stand-in for TASK-017 ``MassBreakdown``.

    Carries only the three fields the calculator reads; deliberately
    avoids importing ``hexagent.material_mass_mechanical`` so the
    calculator tests stay governed by TASK-018 alone.
    """

    def __init__(self, total_kg: float = 1.0) -> None:
        self.total_kg = float(total_kg)


# ---------------------------------------------------------------------------
# Happy-path: CostBreakdown shape and surface.
# ---------------------------------------------------------------------------


class TestCostBreakdownShape:
    def test_happy_path_emits_complete_envelope(self) -> None:
        c0 = _make_record(
            cost_record_id="rec-c0-1",
            cost_record_version="1.0.0",
            cost_category="c0_baseline_estimate",
            currency="USD",
            cost_value=1250.0,  # 1250 minor units
        )
        c1 = _make_record(
            cost_record_id="rec-c1-1",
            cost_record_version="1.0.0",
            cost_category="c1_material_weight",
            currency="USD",
            quantity_basis="currency_per_kg",
            cost_value=85.0,  # 85 minor units per kg
        )
        result = _select([c0, c1])
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(total_kg=2.5),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        assert isinstance(breakdown, CostBreakdown)
        assert breakdown.schema_version == "0.1.0"
        assert breakdown.state == "COMPUTABLE"
        assert breakdown.capex_envelope_currency == "USD"
        assert breakdown.escalation_pointer_used is None
        # Integer minor units only.
        assert isinstance(breakdown.capex_envelope_minor_units, int)
        for sub_key in ("c0_subtotal", "c1_subtotal"):
            sub = breakdown.cost_breakdown[sub_key]
            assert isinstance(sub["amount_minor_units"], int)
            for entry in sub["component_breakdown"]:
                assert isinstance(entry["amount_minor_units"], int)
                assert all(isinstance(v, int) for v in (entry["amount_minor_units"],))
        # C0: 1250 (scalar currency_per_kg basis used as scalar in c0 arithmetic).
        assert breakdown.cost_breakdown["c0_subtotal"]["amount_minor_units"] == 1250
        # C1: 85 * 2.5 = 212.5; banker's rounding rounds half-to-even so
        # ``round(212.5) == 212``.
        assert breakdown.cost_breakdown["c1_subtotal"]["amount_minor_units"] == 212

    def test_integer_minor_units_only_no_floats_in_money(self) -> None:
        c0 = _make_record(cost_record_id="rec-float", cost_value=1250.7)
        result = _select([c0])
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        # 1250.7 -> round -> 1251 (Python banker's rounding 1250.5 = 1250, 1250.7 = 1251).
        amount = breakdown.cost_breakdown["c0_subtotal"]["amount_minor_units"]
        assert isinstance(amount, int)
        assert amount == 1251

    def test_license_class_summary_mirrors_section_5_1_3_shape(self) -> None:
        records = [
            _make_record(cost_record_id="rec-pub", cost_value=10.0, license_class="public_open"),
            _make_record(
                cost_record_id="rec-internal",
                cost_category="c1_material_weight",
                cost_value=20.0,
                license_class="internal_open",
            ),
            _make_record(
                cost_record_id="rec-restricted",
                cost_value=30.0,
                license_class=_PROPRIETARY_RESTRICTED,
            ),
        ]
        result = _select(
            records,
            filters=_default_filters(
                license_class_filter=frozenset(
                    {"public_open", "internal_open", _PROPRIETARY_RESTRICTED}
                )
            ),
        )
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        assert breakdown.license_class_summary == {
            "public_open_count": 1,
            "internal_open_count": 1,
            "proprietary_restricted_count": 1,
        }

    def test_restricted_records_are_pointer_only_in_cost_envelope(self) -> None:
        """Proprietary-restricted records contribute NO minor units."""
        restricted = _make_record(
            cost_record_id="rec-restricted-payload",
            cost_value=9999.0,  # would dominate math if it leaked
            license_class=_PROPRIETARY_RESTRICTED,
        )
        public = _make_record(cost_record_id="rec-public", cost_value=42.0)
        result = _select(
            [restricted, public],
            filters=_default_filters(
                license_class_filter=frozenset(
                    {"public_open", "internal_open", _PROPRIETARY_RESTRICTED}
                )
            ),
        )
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        c0 = breakdown.cost_breakdown["c0_subtotal"]
        # No restricted value body propagated.
        record_ids_in_breakdown = {entry["cost_record_id"] for entry in c0["component_breakdown"]}
        assert record_ids_in_breakdown == {"rec-public"}
        assert c0["amount_minor_units"] == 42
        # ...but the restricted pointer is preserved in source_record_ids
        # of the calculator's source fan-out (selector-level bookkeeping;
        # the CostBreakdown envelope records only its own component
        # breakdown here, which by §8 is pointer-only for restricted
        # records and that means the component_breakdown simply omits
        # them — the §7 provenance_chain_hash carries the pointer).
        assert "rec-restricted-payload" not in record_ids_in_breakdown


# ---------------------------------------------------------------------------
# Determinism: ordering, IDs, hashes.
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_component_ordering_by_record_id_asc_version_desc(self) -> None:
        records = [
            _make_record(cost_record_id="rec-z", cost_record_version="1.0.0", cost_value=10.0),
            _make_record(cost_record_id="rec-a", cost_record_version="2.0.0", cost_value=20.0),
            _make_record(cost_record_id="rec-a", cost_record_version="1.0.0", cost_value=30.0),
            _make_record(cost_record_id="rec-m", cost_record_version="1.1.0", cost_value=40.0),
        ]
        result = _select(records)
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        ids = [
            (entry["cost_record_id"], entry["cost_record_version"])
            for entry in breakdown.cost_breakdown["c0_subtotal"]["component_breakdown"]
        ]
        assert ids == [
            ("rec-a", "2.0.0"),
            ("rec-a", "1.0.0"),
            ("rec-m", "1.1.0"),
            ("rec-z", "1.0.0"),
        ]

    def test_calculator_run_id_is_uuid_v5(self) -> None:
        c0 = _make_record(cost_record_id="rec-uuid", cost_value=10.0)
        result = _select([c0])
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        # Parse as UUID.  This rejects the legacy 40-char SHA-1 style.
        parsed = uuid.UUID(breakdown.calculator_run_id)
        assert parsed.version == 5

    def test_calculator_run_id_is_deterministic(self) -> None:
        c0 = _make_record(cost_record_id="rec-det", cost_value=10.0)
        result = _select([c0])
        first = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        # Re-run with a fresh, independent selector result.
        result2 = _select([c0])
        second = calculate_cost_breakdown(
            cost_model_selection_result=result2,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        assert first.calculator_run_id == second.calculator_run_id
        assert first.provenance_chain_hash == second.provenance_chain_hash
        assert first.to_dict() == second.to_dict()

    def test_calculator_run_id_changes_with_inputs(self) -> None:
        c0_a = _make_record(cost_record_id="rec-a", cost_value=10.0)
        c0_b = _make_record(cost_record_id="rec-b", cost_value=20.0)
        result_a = _select([c0_a])
        result_b = _select([c0_b])
        breakdown_a = calculate_cost_breakdown(
            cost_model_selection_result=result_a,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        breakdown_b = calculate_cost_breakdown(
            cost_model_selection_result=result_b,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        assert breakdown_a.calculator_run_id != breakdown_b.calculator_run_id

    def test_source_record_ids_are_sorted_unique(self) -> None:
        records = [
            _make_record(cost_record_id=f"rec-{n:03d}", cost_value=10.0) for n in (5, 1, 3, 2, 4)
        ]
        result = _select(records)
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        ids = breakdown.cost_breakdown["c0_subtotal"]["source_record_ids"]
        assert ids == sorted(set(ids))
        assert ids == [f"rec-{n:03d}" for n in (1, 2, 3, 4, 5)]


# ---------------------------------------------------------------------------
# selection_blockers fan-out.
# ---------------------------------------------------------------------------


class TestSelectorBlockerFanOut:
    def test_selector_blockers_force_not_computable(self) -> None:
        # Empty record list triggers ``region_unsupported_blocker`` from
        # Slice A.  The calculator MUST propagate this and never run cost
        # math: ``state == NOT_COMPUTABLE``, sub-totals zero, capex zero.
        result = _select([])
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        assert breakdown.state == "NOT_COMPUTABLE"
        assert breakdown.cost_breakdown["c0_subtotal"]["amount_minor_units"] == 0
        assert breakdown.cost_breakdown["c1_subtotal"]["amount_minor_units"] == 0
        assert breakdown.capex_envelope_minor_units == 0
        codes = {entry["code"] for entry in breakdown.blockers}
        assert BlockerCode.REGION_UNSUPPORTED_BLOCKER.value in codes

    def test_selector_blocker_invalid_input_carries_code(self) -> None:
        # Slice A emits ``validity_envelope_blocker`` when the record's
        # ``validity_envelope`` exceeds the caller's cap.  Build a record
        # whose envelope literally exceeds the cap and a filter that
        # carries that cap; the selector rejects, and the calculator
        # propagates the code through to CostBreakdown.blockers.
        record = _make_record(
            cost_record_id="rec-env",
            cost_value=10.0,
            validity_envelope={"max_unit_price_currency": 10.0, "currency": "USD"},
        )
        filters = SelectionFilters(
            material_family="carbon_steel",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
            cost_category_filter=frozenset({"c0_baseline_estimate"}),
            quantity_basis_filter=frozenset({"currency_per_kg"}),
            license_class_filter=frozenset({"public_open", "internal_open"}),
            record_currency="USD",
            # Case-side cap is 5.0; the record's stored actual is 10.0,
            # which violates the cap and triggers the selector blocker.
            validity_envelope={
                "max_unit_price_currency": 5.0,
                "currency": "USD",
            },
        )
        result = select_cost_records([record], filters)
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        codes = {entry["code"] for entry in breakdown.blockers}
        assert BlockerCode.VALIDITY_ENVELOPE_BLOCKER.value in codes
        assert breakdown.state == "NOT_COMPUTABLE"


# ---------------------------------------------------------------------------
# Currency rules (§5.2 + §6.1).
# ---------------------------------------------------------------------------


class TestCurrencyRules:
    def test_currency_mismatch_returns_blocker(self) -> None:
        c0 = _make_record(cost_record_id="rec-usd", currency="USD", cost_value=10.0)
        c0_eur = _make_record(cost_record_id="rec-eur", currency="EUR", cost_value=20.0)
        result = _select([c0, c0_eur])
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        codes = {entry["code"] for entry in breakdown.blockers}
        assert BlockerCode.CURRENCY_MISMATCH_BLOCKER.value in codes
        assert breakdown.state == "NOT_COMPUTABLE"

    def test_case_currency_source_preserves_single_record_currency(self) -> None:
        c0 = _make_record(cost_record_id="rec-eur", currency="EUR", cost_value=10.0)
        result = _select(
            [c0],
            filters=_default_filters(record_currency=None),
        )
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="SOURCE",  # noqa: S107 -- sentinel string from contract
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        assert breakdown.state == "COMPUTABLE"
        assert breakdown.capex_envelope_currency == "EUR"
        assert breakdown.cost_breakdown["c0_subtotal"]["currency"] == "EUR"

    def test_case_currency_source_ambiguous_returns_mismatch_blocker(self) -> None:
        c0_usd = _make_record(cost_record_id="rec-usd", currency="USD", cost_value=10.0)
        c0_eur = _make_record(cost_record_id="rec-eur", currency="EUR", cost_value=20.0)
        result = _select(
            [c0_usd, c0_eur],
            filters=_default_filters(record_currency=None),
        )
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="SOURCE",  # noqa: S107
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        codes = {entry["code"] for entry in breakdown.blockers}
        assert BlockerCode.CURRENCY_MISMATCH_BLOCKER.value in codes
        assert breakdown.state == "NOT_COMPUTABLE"


# ---------------------------------------------------------------------------
# c0_heuristic_overrides envelope [0.5, 2.0].
# ---------------------------------------------------------------------------


class TestC0OverrideEnvelope:
    def test_override_within_envelope_scales_amount(self) -> None:
        c0 = _make_record(
            cost_record_id="rec-scale",
            cost_value=100.0,  # 100 minor units baseline
        )
        result = _select([c0])
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
            c0_heuristic_overrides={"c0_baseline_estimate": 1.5},
        )
        assert breakdown.state == "COMPUTABLE"
        # 100 * 1.5 = 150.
        assert breakdown.cost_breakdown["c0_subtotal"]["amount_minor_units"] == 150

    def test_override_at_envelope_boundary_accepted(self) -> None:
        c0 = _make_record(cost_value=100.0)
        result = _select([c0])
        for boundary in (0.5, 2.0):
            breakdown = calculate_cost_breakdown(
                cost_model_selection_result=result,
                mass_breakdown=_StubMassBreakdown(),
                case_currency="USD",
                case_region="INTL",
                effective_date="2026-07-07T00:00:00Z",
                c0_heuristic_overrides={"c0_baseline_estimate": boundary},
            )
            assert breakdown.state == "COMPUTABLE", boundary

    def test_override_below_envelope_returns_unspecified_blocker_with_envelope_reason(
        self,
    ) -> None:
        c0 = _make_record(cost_value=100.0)
        result = _select([c0])
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
            c0_heuristic_overrides={"c0_baseline_estimate": 0.4},
        )
        codes = {entry["code"] for entry in breakdown.blockers}
        assert BlockerCode.UNSPECIFIED_BLOCKER.value in codes
        reasons = [
            entry["details"].get("reason")
            for entry in breakdown.blockers
            if entry["code"] == BlockerCode.UNSPECIFIED_BLOCKER.value
        ]
        assert "c0_heuristic_out_of_envelope" in reasons
        assert breakdown.state == "NOT_COMPUTABLE"

    def test_override_above_envelope_returns_unspecified_blocker(self) -> None:
        c0 = _make_record(cost_value=100.0)
        result = _select([c0])
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
            c0_heuristic_overrides={"c0_baseline_estimate": 2.1},
        )
        codes = {entry["code"] for entry in breakdown.blockers}
        assert BlockerCode.UNSPECIFIED_BLOCKER.value in codes
        assert breakdown.state == "NOT_COMPUTABLE"


# ---------------------------------------------------------------------------
# Escalation pointer rule.
# ---------------------------------------------------------------------------


class TestEscalationPointerRule:
    def test_no_filter_yields_no_escalation(self) -> None:
        c0 = _make_record(
            cost_record_id="rec-esc",
            cost_value=10.0,
            escalation_index_reference="esc-1",
        )
        result = _select([c0])
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
            escalation_index_reference_filter=None,
        )
        assert breakdown.escalation_pointer_used is None
        assert breakdown.state == "COMPUTABLE"

    def test_filter_with_matching_pointer_used(self) -> None:
        c0 = _make_record(
            cost_record_id="rec-esc",
            cost_value=10.0,
            escalation_index_reference="esc-target",
        )
        # The selector with a non-None filter excludes records whose
        # escalation pointer is not in the allowed set; we only have
        # one record so it survives, and the calculator picks its
        # pointer as escalation_pointer_used.
        result = _select(
            [c0],
            escalation_index_reference_filter=frozenset({"esc-target"}),
        )
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
            escalation_index_reference_filter=frozenset({"esc-target"}),
        )
        assert breakdown.escalation_pointer_used == "esc-target"
        assert breakdown.state == "COMPUTABLE"

    def test_filter_with_no_visible_pointer_returns_blocker(self) -> None:
        c0 = _make_record(
            cost_record_id="rec-esc",
            cost_value=10.0,
            escalation_index_reference="esc-other",
        )
        # Selector filter only allows "esc-target"; "esc-other" is excluded.
        # Calculator receives a selection result with no eligible pointer.
        result = _select(
            [c0],
            escalation_index_reference_filter=frozenset({"esc-target"}),
        )
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
            escalation_index_reference_filter=frozenset({"esc-target"}),
        )
        codes = {entry["code"] for entry in breakdown.blockers}
        assert BlockerCode.UNSPECIFIED_BLOCKER.value in codes
        assert breakdown.state == "NOT_COMPUTABLE"


# ---------------------------------------------------------------------------
# Restricted-source pointer-only boundary.
# ---------------------------------------------------------------------------


class TestRestrictedSourcePointerOnly:
    def test_restricted_records_emit_no_cost_value_body(self) -> None:
        restricted = _make_record(
            cost_record_id="rec-restricted-body",
            cost_value=5000.0,
            license_class=_PROPRIETARY_RESTRICTED,
        )
        result = _select(
            [restricted],
            filters=_default_filters(
                license_class_filter=frozenset(
                    {"public_open", "internal_open", _PROPRIETARY_RESTRICTED}
                )
            ),
        )
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        # The cost envelope carries no restricted value body.
        c0 = breakdown.cost_breakdown["c0_subtotal"]
        assert c0["amount_minor_units"] == 0
        for entry in c0["component_breakdown"]:
            assert entry["cost_record_id"] != "rec-restricted-body"

    def test_restricted_only_selection_emits_pointer_warning(self) -> None:
        restricted_only = _make_record(
            cost_record_id="rec-restricted-only",
            license_class=_PROPRIETARY_RESTRICTED,
        )
        # Caller filters to restricted-only.
        result = _select(
            [restricted_only],
            filters=_default_filters(license_class_filter=frozenset({_PROPRIETARY_RESTRICTED})),
        )
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        # Restricted-only provenance warning (§8 line 340) surfaces
        # even though cost math is zeroed.
        codes = {entry["code"] for entry in breakdown.warnings}
        assert WarningCode.RESTRICTED_ONLY_PROVENANCE_WARNING.value in codes


# ---------------------------------------------------------------------------
# Input-immutability contract.
# ---------------------------------------------------------------------------


class TestInputImmutability:
    def test_calculator_does_not_mutate_selection_result(self) -> None:
        c0 = _make_record(cost_record_id="rec-immut", cost_value=12.0)
        result = _select([c0])
        snapshot = copy.deepcopy(result.to_dict())
        # Calculate with every relevant kwarg populated.
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(total_kg=2.0),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
            component_role_overrides={"rec-immut": "inner_tube"},
            c0_heuristic_overrides={"c0_baseline_estimate": 1.2},
            escalation_index_reference_filter=None,
        )
        # The selection envelope (input to the calculator) is untouched.
        assert result.to_dict() == snapshot
        # Sanity: the calculator DID run successfully.
        assert breakdown.state in {"COMPUTABLE", "COMPUTABLE_WITH_WARNINGS"}

    def test_calculator_does_not_mutate_cost_records(self) -> None:
        records = [
            _make_record(cost_record_id="rec-orig-1", cost_value=10.0),
            _make_record(cost_record_id="rec-orig-2", cost_value=20.0),
        ]
        snapshots = [copy.deepcopy(r) for r in records]
        result = _select(records)
        calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(total_kg=1.0),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        # Re-locate the records that ended up in the selection envelope.
        for snap in snapshots:
            for r in result.c0_records:
                if r["cost_record_id"] == snap["cost_record_id"]:
                    assert dict(r) == snap


# ---------------------------------------------------------------------------
# Canonical serialization & frozen closed-set guards.
# ---------------------------------------------------------------------------


class TestCanonicalAndClosedSet:
    def test_to_dict_is_json_serializable(self) -> None:
        c0 = _make_record(cost_record_id="rec-canonical", cost_value=10.0)
        result = _select([c0])
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        # Round-trip through json to catch any non-JSON-friendly field.
        encoded = json.dumps(breakdown.to_dict(), sort_keys=True)
        decoded = json.loads(encoded)
        assert decoded["schema_version"] == "0.1.0"

    def test_all_emitted_blocker_codes_are_frozen(self) -> None:
        c0 = _make_record(cost_value=10.0)
        c0_eur = _make_record(cost_record_id="rec-eur", currency="EUR", cost_value=20.0)
        result = _select([c0, c0_eur])
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
            c0_heuristic_overrides={"c0_baseline_estimate": 3.0},
        )
        for entry in breakdown.blockers:
            assert entry["code"] in BLOCKER_CODES, entry

    def test_all_emitted_warning_codes_are_frozen(self) -> None:
        restricted_only = _make_record(
            cost_record_id="rec-restr-only",
            license_class=_PROPRIETARY_RESTRICTED,
        )
        result = _select(
            [restricted_only],
            filters=_default_filters(license_class_filter=frozenset({_PROPRIETARY_RESTRICTED})),
        )
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        for entry in breakdown.warnings:
            assert entry["code"] in {w.value for w in WarningCode}, entry

    def test_calculator_run_id_format_uuid_v5(self) -> None:
        c0 = _make_record(cost_value=10.0)
        result = _select([c0])
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        # 36 characters with hyphens; version 5 in the UUID string form.
        match = re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
            breakdown.calculator_run_id,
        )
        assert match is not None


# ---------------------------------------------------------------------------
# Slice A regression: when the calculator is fed a Slice A result
# envelope, no warning / blocker surfaces solely because of the
# calculator layer.
# ---------------------------------------------------------------------------


class TestSliceARegression:
    def test_no_slice_a_regression_on_clean_selection(self) -> None:
        c0 = _make_record(cost_record_id="rec-clean", cost_value=42.0)
        c1 = _make_record(
            cost_record_id="rec-clean-c1",
            cost_category="c1_material_weight",
            quantity_basis="currency_per_kg",
            cost_value=10.0,
        )
        result = _select([c0, c1])
        breakdown = calculate_cost_breakdown(
            cost_model_selection_result=result,
            mass_breakdown=_StubMassBreakdown(total_kg=1.0),
            case_currency="USD",
            case_region="INTL",
            effective_date="2026-07-07T00:00:00Z",
        )
        assert breakdown.state == "COMPUTABLE"
        assert breakdown.warnings == ()
        assert breakdown.blockers == ()
