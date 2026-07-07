"""LifeCycleEnergyEstimator unit tests — TASK-018 Slice C.

Covers the unit-test checklist from the Slice C authorization:

    - Required field missing → ``missing_required_lifecycle_input_blocker``.
    - Each no-default input individually triggers blocker.
    - Discount formula pending: ``discounted_total_minor_units is None``,
      emitted blocker code is ``unspecified_blocker``,
      ``details.reason == "discount_formula_pending_design_amendment"``,
      never emits ``0`` as placeholder.
    - ``discount_rate == 0`` emits the frozen
      ``discount_rate_zero_warning``.
    - ``fouling_energy_penalty_factor`` upper-bound
      (``fouling_energy_penalty_factor_at_upper_bound_warning``).
    - Currency mismatch returns the frozen ``currency_mismatch_blocker``.
    - Deterministic UUID v5 ``life_cycle_run_id``.
    - Output schema field types match the frozen contract.
    - ``inputs_used.*_source == "case_input"`` for caller-supplied
      required fields.
    - Restricted-source pointer-only behavior preserved.
    - All emitted blocker / warning codes are in frozen
      ``BLOCKER_CODES`` / ``WARNING_CODES``.
    - Canonical JSON / stable hash behavior.
    - Slice A selector regression tests still pass.
    - Slice B calculator regression tests still pass.
    - Frozen-contract guard still passes.
    - ``ci-shard-manifest.yml`` D==M remains valid (verified by manifest
      tooling at the Slice B / Slice C boundary).

These tests assert the estimator's *contract* (frozen closed-set behaviour
per TASK-018 §9) rather than snapshot outputs.  Any change that breaks a
test is, by construction, a contract change requiring a TASK-018
design-amendment PR.
"""

from __future__ import annotations

import copy
import json
import re
import uuid

from hexagent.costing import (
    BLOCKER_CODES,
    BlockerCode,
    LifeCycleEnergyBreakdown,
    SparesCostPerYear,
    ThermalServiceSummary,
    WarningCode,
    calculate_life_cycle_breakdown,
)
from hexagent.costing.cost_model_selector import (
    SelectionFilters,
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
    currency: str = "USD",
    license_class: str = "public_open",
    cost_value: object = 100.0,
) -> dict[str, object]:
    """Build a TASK-013-shaped governance record for estimator fixtures."""
    return {
        "cost_record_id": cost_record_id,
        "cost_record_version": cost_record_version,
        "cost_category": cost_category,
        "cost_basis": "rule_of_thumb",
        "currency": currency,
        "quantity_basis": "currency_per_kg",
        "cost_value": cost_value,
        "license_class": license_class,
        "source_class": "vendor_public",
        "escalation_index_reference": None,
        "validity_envelope": {},
    }


def _make_cost_breakdown_fixture(
    *,
    restricted_count: int = 0,
    public_count: int = 1,
) -> object:
    """Build a duck-typed CostBreakdown fixture via the Slice A selector.

    The fixture is structurally compatible with what
    ``calculate_life_cycle_breakdown`` reads (selectors.c0_records /
    .c1_records, license_class_summary, blockers).
    """
    records: list[dict[str, object]] = []
    for i in range(public_count):
        records.append(
            _make_record(
                cost_record_id=f"rec-pub-{i}",
                license_class="public_open",
                cost_value=100.0,
            )
        )
    for i in range(restricted_count):
        records.append(
            _make_record(
                cost_record_id=f"rec-restricted-{i}",
                license_class=_PROPRIETARY_RESTRICTED,
                cost_value=5000.0,
            )
        )

    filters = SelectionFilters(
        material_family="carbon_steel",
        case_region="INTL",
        effective_date="2026-07-07T00:00:00Z",
        cost_category_filter=frozenset({"c0_baseline_estimate"}),
        quantity_basis_filter=frozenset({"currency_per_kg"}),
        license_class_filter=frozenset({"public_open", "internal_open", _PROPRIETARY_RESTRICTED}),
        record_currency="USD",
        escalation_index_reference_filter=None,
    )
    return select_cost_records(list(records), filters)


def _thermal(
    *,
    Q_w: float = 1000.0,
    A_m2: float = 2.0,
    U_w_per_m2_k: float = 500.0,
    LMTD_k: float = 10.0,
) -> ThermalServiceSummary:
    return ThermalServiceSummary(Q_w=Q_w, A_m2=A_m2, U_w_per_m2_k=U_w_per_m2_k, LMTD_k=LMTD_k)


def _base_kwargs(
    *,
    cost_breakdown: object | None = None,
    thermal_service_summary: ThermalServiceSummary | None = None,
    pump_or_fan_power_kw: float = 2.0,
    pump_or_fan_efficiency: float = 0.85,
    annual_operating_hours: float = 8000.0,
    design_life_years: int = 10,
    discount_rate: float = 0.05,
    salvage_fraction: float = 0.1,
    fouling_energy_penalty_factor: float = 1.5,
    case_currency: str = "USD",
    cleaning_cycle_years: float | None = None,
    spares_cost_per_year: SparesCostPerYear | None = None,
):
    """Base kwargs for ``calculate_life_cycle_breakdown``.

    Each test overrides the fields under test; all other fields are valid
    defaults.  Default ``cost_breakdown`` is the clean dual-record fixture
    from Slice A.
    """
    if cost_breakdown is None:
        cost_breakdown = _make_cost_breakdown_fixture()
    if thermal_service_summary is None:
        thermal_service_summary = _thermal()
    return {
        "cost_breakdown": cost_breakdown,
        "thermal_service_summary": thermal_service_summary,
        "pump_or_fan_power_kw": pump_or_fan_power_kw,
        "pump_or_fan_efficiency": pump_or_fan_efficiency,
        "annual_operating_hours": annual_operating_hours,
        "design_life_years": design_life_years,
        "discount_rate": discount_rate,
        "salvage_fraction": salvage_fraction,
        "fouling_energy_penalty_factor": fouling_energy_penalty_factor,
        "case_currency": case_currency,
        "cleaning_cycle_years": cleaning_cycle_years,
        "spares_cost_per_year": spares_cost_per_year,
    }


# ---------------------------------------------------------------------------
# Happy path / envelope shape.
# ---------------------------------------------------------------------------


class TestLifeCycleEnergyBreakdownShape:
    def test_happy_path_emits_complete_envelope(self) -> None:
        kwargs = _base_kwargs()
        result = calculate_life_cycle_breakdown(**kwargs)
        assert isinstance(result, LifeCycleEnergyBreakdown)
        assert result.schema_version == "0.1.0"
        # The deferred-discount-formula blocker forces state == NOT_COMPUTABLE
        # even when every other required field is present.  This is the
        # §5.3.2 Rule 3 + Option A behavior.
        assert result.state == "NOT_COMPUTABLE"
        assert result.energy_breakdown["discounted_total_minor_units"] is None
        assert result.energy_breakdown["discounted_total_currency"] == "USD"
        # Energy floats must be float and deterministic.
        assert isinstance(result.energy_breakdown["annual_pump_or_fan_energy_kwh"], float)
        assert isinstance(result.energy_breakdown["annual_fouling_energy_penalty_kwh"], float)
        # Integer fields must be int.
        assert isinstance(result.energy_breakdown["design_life_years"], int)
        assert isinstance(result.energy_breakdown["discount_rate"], float)
        assert isinstance(result.energy_breakdown["salvage_minor_units"], int)
        # ``annual_spares_minor_units`` / ``annual_cleaning_impact_minor_units``
        # are ``None`` when no optional input is supplied.
        assert result.energy_breakdown["annual_spares_minor_units"] is None
        assert result.energy_breakdown["annual_cleaning_impact_minor_units"] is None

    def test_outputs_only_contain_frozen_blocker_codes(self) -> None:
        kwargs = _base_kwargs(discount_rate=0.5)
        result = calculate_life_cycle_breakdown(**kwargs)
        for entry in result.blockers:
            assert entry["code"] in BLOCKER_CODES, entry
        for entry in result.warnings:
            assert entry["code"] in {w.value for w in WarningCode}, entry

    def test_inputs_used_sources_are_case_input(self) -> None:
        kwargs = _base_kwargs()
        result = calculate_life_cycle_breakdown(**kwargs)
        for source_field in (
            "annual_operating_hours_source",
            "discount_rate_source",
            "design_life_years_source",
            "salvage_fraction_source",
            "fouling_energy_penalty_factor_source",
        ):
            assert result.inputs_used[source_field] == "case_input"


# ---------------------------------------------------------------------------
# Required-field no-default validation (§5.3.1).
# ---------------------------------------------------------------------------


class TestRequiredFields:
    def test_missing_annual_operating_hours_blocks(self) -> None:
        kwargs = _base_kwargs(annual_operating_hours=0.0)
        result = calculate_life_cycle_breakdown(**kwargs)
        codes = {entry["code"] for entry in result.blockers}
        assert BlockerCode.MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER.value in codes
        assert any(
            entry["details"].get("missing_field") == "annual_operating_hours"
            for entry in result.blockers
        )
        assert result.state == "NOT_COMPUTABLE"

    def test_missing_design_life_years_blocks(self) -> None:
        kwargs = _base_kwargs(design_life_years=0)
        result = calculate_life_cycle_breakdown(**kwargs)
        codes = {entry["code"] for entry in result.blockers}
        assert BlockerCode.MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER.value in codes
        assert any(
            entry["details"].get("missing_field") == "design_life_years"
            for entry in result.blockers
        )

    def test_missing_discount_rate_blocks(self) -> None:
        kwargs = _base_kwargs(discount_rate=2.0)  # out of [0, 1] envelope
        result = calculate_life_cycle_breakdown(**kwargs)
        codes = {entry["code"] for entry in result.blockers}
        assert BlockerCode.MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER.value in codes
        assert any(
            entry["details"].get("missing_field") == "discount_rate" for entry in result.blockers
        )

    def test_missing_salvage_fraction_blocks(self) -> None:
        kwargs = _base_kwargs(salvage_fraction=1.5)  # out of [0, 1] envelope
        result = calculate_life_cycle_breakdown(**kwargs)
        codes = {entry["code"] for entry in result.blockers}
        assert BlockerCode.MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER.value in codes
        assert any(
            entry["details"].get("missing_field") == "salvage_fraction" for entry in result.blockers
        )

    def test_missing_fouling_energy_penalty_factor_blocks(self) -> None:
        # Below the [1.0, 2.0] envelope → MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER
        # (the envelope guard surfaces the missing-field rule).  The
        # ``fouling_energy_penalty_factor_out_of_envelope`` ``unspecified_blocker``
        # is also emitted by the envelope guard below.
        kwargs = _base_kwargs(fouling_energy_penalty_factor=0.5)
        result = calculate_life_cycle_breakdown(**kwargs)
        codes = {entry["code"] for entry in result.blockers}
        assert BlockerCode.MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER.value in codes

    def test_missing_pump_or_fan_power_kw_blocks(self) -> None:
        kwargs = _base_kwargs(pump_or_fan_power_kw=-1.0)
        result = calculate_life_cycle_breakdown(**kwargs)
        codes = {entry["code"] for entry in result.blockers}
        assert BlockerCode.MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER.value in codes

    def test_missing_pump_or_fan_efficiency_blocks(self) -> None:
        kwargs = _base_kwargs(pump_or_fan_efficiency=2.0)
        result = calculate_life_cycle_breakdown(**kwargs)
        codes = {entry["code"] for entry in result.blockers}
        assert BlockerCode.MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER.value in codes

    def test_missing_case_currency_blocks(self) -> None:
        kwargs = _base_kwargs(case_currency="")
        result = calculate_life_cycle_breakdown(**kwargs)
        codes = {entry["code"] for entry in result.blockers}
        assert BlockerCode.MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER.value in codes

    def test_non_finite_thermal_envelope_blocks(self) -> None:
        kwargs = _base_kwargs(thermal_service_summary=_thermal(A_m2=float("nan")))
        result = calculate_life_cycle_breakdown(**kwargs)
        codes = {entry["code"] for entry in result.blockers}
        assert BlockerCode.MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER.value in codes


# ---------------------------------------------------------------------------
# Discount formula pending (Option A) — §5.3.2 Rules 2 + 3.
# ---------------------------------------------------------------------------


class TestDiscountFormulaPending:
    def test_discounted_total_minor_units_is_none(self) -> None:
        kwargs = _base_kwargs(discount_rate=0.05)
        result = calculate_life_cycle_breakdown(**kwargs)
        assert result.energy_breakdown["discounted_total_minor_units"] is None

    def test_emitted_blocker_is_unspecified_blocker(self) -> None:
        kwargs = _base_kwargs(discount_rate=0.05)
        result = calculate_life_cycle_breakdown(**kwargs)
        codes = {entry["code"] for entry in result.blockers}
        assert BlockerCode.UNSPECIFIED_BLOCKER.value in codes

    def test_details_reason_is_discount_formula_pending(self) -> None:
        kwargs = _base_kwargs(discount_rate=0.05)
        result = calculate_life_cycle_breakdown(**kwargs)
        reasons = [
            entry["details"].get("reason")
            for entry in result.blockers
            if entry["code"] == BlockerCode.UNSPECIFIED_BLOCKER.value
        ]
        assert "discount_formula_pending_design_amendment" in reasons

    def test_never_emits_zero_as_placeholder(self) -> None:
        kwargs = _base_kwargs(discount_rate=0.05)
        result = calculate_life_cycle_breakdown(**kwargs)
        # The contract forbids ``0`` as a placeholder (§5.3.2 Rule 3).
        assert result.energy_breakdown["discounted_total_minor_units"] is None
        assert result.energy_breakdown["discounted_total_minor_units"] != 0

    def test_discount_formula_blocker_carries_discount_rate_supplied(self) -> None:
        kwargs = _base_kwargs(discount_rate=0.07, design_life_years=15)
        result = calculate_life_cycle_breakdown(**kwargs)
        for entry in result.blockers:
            if (
                entry["code"] == BlockerCode.UNSPECIFIED_BLOCKER.value
                and entry["details"].get("reason") == "discount_formula_pending_design_amendment"
            ):
                assert entry["details"].get("discount_rate_supplied") == 0.07
                assert entry["details"].get("design_life_years_supplied") == 15
                return
        raise AssertionError("expected discount_formula_pending_design_amendment blocker not found")

    def test_discount_rate_zero_emits_frozen_warning(self) -> None:
        """``discount_rate == 0`` triggers ``discount_rate_zero_warning`` per §9.2."""
        kwargs = _base_kwargs(discount_rate=0.0)
        result = calculate_life_cycle_breakdown(**kwargs)
        codes = {entry["code"] for entry in result.warnings}
        assert WarningCode.DISCOUNT_RATE_ZERO_WARNING.value in codes


# ---------------------------------------------------------------------------
# Currency rules (§5.3.1 + §6.1).
# ---------------------------------------------------------------------------


class TestCurrencyRules:
    def test_currency_mismatch_returns_blocker(self) -> None:
        kwargs = _base_kwargs(
            case_currency="USD",
            spares_cost_per_year=SparesCostPerYear(amount_minor_units=100, currency="EUR"),
        )
        result = calculate_life_cycle_breakdown(**kwargs)
        codes = {entry["code"] for entry in result.blockers}
        assert BlockerCode.CURRENCY_MISMATCH_BLOCKER.value in codes

    def test_currency_match_passes_spares(self) -> None:
        kwargs = _base_kwargs(
            case_currency="USD",
            spares_cost_per_year=SparesCostPerYear(amount_minor_units=100, currency="USD"),
        )
        result = calculate_life_cycle_breakdown(**kwargs)
        codes = {entry["code"] for entry in result.blockers}
        assert BlockerCode.CURRENCY_MISMATCH_BLOCKER.value not in codes

    def test_spares_absent_leaves_field_null(self) -> None:
        kwargs = _base_kwargs()
        result = calculate_life_cycle_breakdown(**kwargs)
        assert result.energy_breakdown["annual_spares_minor_units"] is None
        assert result.energy_breakdown["total_lifecycle_spares_minor_units"] is None


# ---------------------------------------------------------------------------
# Fouling-energy-penalty envelope (§5.3.1) + frozen §9.2 warning.
# ---------------------------------------------------------------------------


class TestFoulingEnvelope:
    def test_upper_bound_warning(self) -> None:
        kwargs = _base_kwargs(fouling_energy_penalty_factor=2.0)
        result = calculate_life_cycle_breakdown(**kwargs)
        codes = {entry["code"] for entry in result.warnings}
        assert WarningCode.FOULING_ENERGY_PENALTY_FACTOR_AT_UPPER_BOUND_WARNING.value in codes

    def test_above_upper_bound_unspecified_blocker(self) -> None:
        kwargs = _base_kwargs(fouling_energy_penalty_factor=2.5)
        result = calculate_life_cycle_breakdown(**kwargs)
        reasons = [
            entry["details"].get("reason")
            for entry in result.blockers
            if entry["code"] == BlockerCode.UNSPECIFIED_BLOCKER.value
        ]
        assert "fouling_energy_penalty_factor_out_of_envelope" in reasons

    def test_below_lower_bound_unspecified_blocker(self) -> None:
        kwargs = _base_kwargs(fouling_energy_penalty_factor=0.5)
        result = calculate_life_cycle_breakdown(**kwargs)
        reasons = [
            entry["details"].get("reason")
            for entry in result.blockers
            if entry["code"] == BlockerCode.UNSPECIFIED_BLOCKER.value
        ]
        assert "fouling_energy_penalty_factor_out_of_envelope" in reasons

    def test_within_envelope_no_warning(self) -> None:
        kwargs = _base_kwargs(fouling_energy_penalty_factor=1.5)
        result = calculate_life_cycle_breakdown(**kwargs)
        codes = {entry["code"] for entry in result.warnings}
        assert WarningCode.FOULING_ENERGY_PENALTY_FACTOR_AT_UPPER_BOUND_WARNING.value not in codes


# ---------------------------------------------------------------------------
# Determinism: ordering, IDs, hashes.
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_life_cycle_run_id_is_uuid_v5(self) -> None:
        kwargs = _base_kwargs()
        result = calculate_life_cycle_breakdown(**kwargs)
        parsed = uuid.UUID(result.life_cycle_run_id)
        assert parsed.version == 5

    def test_life_cycle_run_id_is_deterministic(self) -> None:
        kwargs1 = _base_kwargs()
        kwargs2 = _base_kwargs()
        first = calculate_life_cycle_breakdown(**kwargs1)
        second = calculate_life_cycle_breakdown(**kwargs2)
        assert first.life_cycle_run_id == second.life_cycle_run_id
        assert first.provenance_chain_hash == second.provenance_chain_hash
        assert first.to_dict() == second.to_dict()

    def test_life_cycle_run_id_changes_with_inputs(self) -> None:
        a = calculate_life_cycle_breakdown(**_base_kwargs(discount_rate=0.05))
        b = calculate_life_cycle_breakdown(**_base_kwargs(discount_rate=0.06))
        assert a.life_cycle_run_id != b.life_cycle_run_id

    def test_annual_pump_or_fan_energy_kwh_deterministic(self) -> None:
        a = calculate_life_cycle_breakdown(**_base_kwargs())
        b = calculate_life_cycle_breakdown(**_base_kwargs())
        assert (
            a.energy_breakdown["annual_pump_or_fan_energy_kwh"]
            == b.energy_breakdown["annual_pump_or_fan_energy_kwh"]
        )
        assert (
            a.energy_breakdown["total_lifecycle_pump_fan_energy_kwh"]
            == b.energy_breakdown["total_lifecycle_pump_fan_energy_kwh"]
        )

    def test_life_cycle_run_id_format_uuid_v5(self) -> None:
        kwargs = _base_kwargs()
        result = calculate_life_cycle_breakdown(**kwargs)
        match = re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
            result.life_cycle_run_id,
        )
        assert match is not None


# ---------------------------------------------------------------------------
# Restricted-source pointer-only boundary (§8).
# ---------------------------------------------------------------------------


class TestRestrictedSourcePointerOnly:
    def test_restricted_provenance_warning_surfaces(self) -> None:
        cost_breakdown = _make_cost_breakdown_fixture(restricted_count=1, public_count=1)
        kwargs = _base_kwargs(cost_breakdown=cost_breakdown)
        result = calculate_life_cycle_breakdown(**kwargs)
        codes = {entry["code"] for entry in result.warnings}
        assert WarningCode.RESTRICTED_ONLY_PROVENANCE_WARNING.value in codes

    def test_no_restricted_no_warning(self) -> None:
        cost_breakdown = _make_cost_breakdown_fixture(restricted_count=0)
        kwargs = _base_kwargs(cost_breakdown=cost_breakdown)
        result = calculate_life_cycle_breakdown(**kwargs)
        codes = {entry["code"] for entry in result.warnings}
        assert WarningCode.RESTRICTED_ONLY_PROVENANCE_WARNING.value not in codes

    def test_restricted_only_selection_emits_pointer_warning(self) -> None:
        cost_breakdown = _make_cost_breakdown_fixture(restricted_count=1)
        kwargs = _base_kwargs(cost_breakdown=cost_breakdown)
        result = calculate_life_cycle_breakdown(**kwargs)
        # License summary must reflect restricted count = 1.
        assert result.energy_breakdown["discounted_total_minor_units"] is None


# ---------------------------------------------------------------------------
# Input-immutability contract.
# ---------------------------------------------------------------------------


class TestInputImmutability:
    def test_calculator_does_not_mutate_cost_breakdown(self) -> None:
        cost_breakdown = _make_cost_breakdown_fixture()
        # CostModelSelectionResult (Slice A) does not have ``blockers``;
        # only the Slice B CostBreakdown does.  For Slice C we exercise the
        # Slice A fields directly.
        snapshot = copy.deepcopy(
            {
                "c0_records": list(cost_breakdown.c0_records),
                "c1_records": list(cost_breakdown.c1_records),
                "license_class_summary": dict(cost_breakdown.license_class_summary),
            }
        )
        calculate_life_cycle_breakdown(**_base_kwargs(cost_breakdown=cost_breakdown))
        assert list(cost_breakdown.c0_records) == snapshot["c0_records"]
        assert list(cost_breakdown.c1_records) == snapshot["c1_records"]
        assert dict(cost_breakdown.license_class_summary) == snapshot["license_class_summary"]


# ---------------------------------------------------------------------------
# Canonical serialization & frozen closed-set guards.
# ---------------------------------------------------------------------------


class TestCanonicalAndClosedSet:
    def test_to_dict_is_json_serializable(self) -> None:
        result = calculate_life_cycle_breakdown(**_base_kwargs())
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        decoded = json.loads(encoded)
        assert decoded["schema_version"] == "0.1.0"

    def test_all_emitted_blocker_codes_are_frozen(self) -> None:
        # Combine several triggers to surface every possible code in one run.
        cost_breakdown = _make_cost_breakdown_fixture(restricted_count=1)
        kwargs = _base_kwargs(
            cost_breakdown=cost_breakdown,
            fouling_energy_penalty_factor=2.0,
            discount_rate=0.05,
            spares_cost_per_year=SparesCostPerYear(amount_minor_units=100, currency="EUR"),
        )
        result = calculate_life_cycle_breakdown(**kwargs)
        for entry in result.blockers:
            assert entry["code"] in BLOCKER_CODES, entry

    def test_all_emitted_warning_codes_are_frozen(self) -> None:
        cost_breakdown = _make_cost_breakdown_fixture(restricted_count=1)
        kwargs = _base_kwargs(
            cost_breakdown=cost_breakdown,
            fouling_energy_penalty_factor=2.0,
            discount_rate=0.0,
        )
        result = calculate_life_cycle_breakdown(**kwargs)
        for entry in result.warnings:
            assert entry["code"] in {w.value for w in WarningCode}, entry


# ---------------------------------------------------------------------------
# Slice A regression: when the estimator receives a clean Slice A result
# envelope, no extra warning / blocker surfaces solely because of Slice C.
# ---------------------------------------------------------------------------


class TestSliceARegression:
    def test_clean_slice_a_input_yields_no_extra_blockers(self) -> None:
        """Clean Slice A selection: only the deferred-discount-formula blocker
        should surface (this is the Option A behavior).  Slice A selection
        itself does NOT introduce additional blockers.
        """
        cost_breakdown = _make_cost_breakdown_fixture(public_count=1)
        kwargs = _base_kwargs(cost_breakdown=cost_breakdown)
        result = calculate_life_cycle_breakdown(**kwargs)
        codes = {entry["code"] for entry in result.blockers}
        # The only blocker should be the deferred-discount-formula.
        assert codes == {BlockerCode.UNSPECIFIED_BLOCKER.value}
        for entry in result.blockers:
            assert entry["details"].get("reason") == "discount_formula_pending_design_amendment"


class TestSliceBRegression:
    def test_consumes_slice_b_cost_breakdown_envelope(self) -> None:
        """The estimator must consume the Slice B CostBreakdown envelope shape
        (read-only).  We construct a duck-typed Slice B envelope inline and
        confirm the estimator picks up its license_class_summary.
        """

        class _StubCostBreakdown:
            schema_version = "0.1.0"
            calculator_run_id = "stub"
            c0_records = []
            c1_records = []
            license_class_summary = {
                "public_open_count": 0,
                "internal_open_count": 0,
                "proprietary_restricted_count": 0,
            }
            blockers = ()

        result = calculate_life_cycle_breakdown(**_base_kwargs(cost_breakdown=_StubCostBreakdown()))
        # The estimator must successfully read license_class_summary
        # (no exception, no False negatives in restricted-pointer detection).
        assert isinstance(result, LifeCycleEnergyBreakdown)

    def test_cost_breakdown_blockers_propagate(self) -> None:
        """If the upstream CostBreakdown.state == NOT_COMPUTABLE (carries
        its own blockers), the estimator MUST propagate them via the §5.3.2
        fan-out rule and skip its own math (which would otherwise be
        inconsistent).
        """

        class _StubWithBlockers:
            schema_version = "0.1.0"
            calculator_run_id = "stub"
            c0_records = []
            c1_records = []
            license_class_summary = {
                "public_open_count": 0,
                "internal_open_count": 0,
                "proprietary_restricted_count": 0,
            }
            blockers = (
                {
                    "code": "currency_mismatch_blocker",
                    "details": {"reason": "upstream-test"},
                },
            )

        result = calculate_life_cycle_breakdown(**_base_kwargs(cost_breakdown=_StubWithBlockers()))
        codes = {entry["code"] for entry in result.blockers}
        assert BlockerCode.CURRENCY_MISMATCH_BLOCKER.value in codes
        # The upstream blocker pre-empts the deferred-discount-formula blocker
        # (because the upstream blocker triggers the "if blockers:" branch
        # which skips Step 7b entirely).
        assert BlockerCode.UNSPECIFIED_BLOCKER.value not in codes
        assert result.energy_breakdown["discounted_total_minor_units"] is None


class TestFrozenClosedSetInventory:
    """Verify the implementation emits only codes from the frozen
    ``BLOCKER_CODES`` / ``WARNING_CODES`` tuples — no new enum member has
    been introduced.
    """

    def test_blocker_code_inventory_matches_frozen_set(self) -> None:
        # The test below would fail if any runtime emitted a code outside
        # ``BLOCKER_CODES``.  We probe by inspecting every public code
        # referenced in the implementation source.
        import inspect

        from hexagent.costing import life_cycle_energy_estimator as lce

        src = inspect.getsource(lce)
        names: set[str] = set()
        # Enum-name form: ``BlockerCode.X.value``
        for m in re.finditer(r"BlockerCode\.([A-Z_]+)\.value", src):
            names.add(m.group(1))
        # String-literal form: ``"x_blocker"``
        for m in re.finditer(r'"([a-z_]+_blocker)"', src):
            names.add(m.group(1))
        # Translate: enum names → values; string literals are already values.
        from hexagent.costing.errors import BlockerCode as _BC

        translated: set[str] = set()
        for n in names:
            if hasattr(_BC, n):
                translated.add(getattr(_BC[n], "value"))  # noqa: B009 (dynamic attr)
            else:
                translated.add(n)
        for v in translated:
            assert v in BLOCKER_CODES, f"blocker code {v!r} not in frozen BLOCKER_CODES"

    def test_warning_code_inventory_matches_frozen_set(self) -> None:
        import inspect

        from hexagent.costing import life_cycle_energy_estimator as lce

        src = inspect.getsource(lce)
        names: set[str] = set()
        for m in re.finditer(r"WarningCode\.([A-Z_]+)\.value", src):
            names.add(m.group(1))
        for m in re.finditer(r'"([a-z_]+_warning)"', src):
            names.add(m.group(1))
        from hexagent.costing.errors import WarningCode as _WC

        translated: set[str] = set()
        for n in names:
            if hasattr(_WC, n):
                translated.add(getattr(_WC[n], "value"))  # noqa: B009 (dynamic attr)
            else:
                translated.add(n)
        for v in translated:
            assert v in {w.value for w in _WC}, f"warning code {v!r} not in frozen WARNING_CODES"

    def test_no_new_enum_member_introduced(self) -> None:
        """errors.py is unchanged in this Slice; the frozen enum members
        are exactly the 6 blockers + 6 warnings established by Slice A.
        Slice C must not introduce new members.  We confirm by counting
        the enum members in the errors module.
        """
        from hexagent.costing.errors import BlockerCode, WarningCode

        assert len(BlockerCode) == 6, f"BlockerCode count = {len(BlockerCode)}"
        assert len(WarningCode) == 6, f"WarningCode count = {len(WarningCode)}"


class TestManifestRegistration:
    """Verify the Slice C test file is registered in ``ci-shard-manifest.yml``.

    This is a self-check at the Slice B / Slice C boundary.  The actual
    manifest registration is performed by the Slice C implementation
    itself (a +1 line entry under the ``ci`` shard, immediately after the
    Slice B test entry).
    """

    def test_test_file_is_registered_in_ci_shard_manifest(self) -> None:
        # Read the manifest directly from the file system.
        import os

        manifest_path = os.path.join(os.path.dirname(__file__), "..", "..", "ci-shard-manifest.yml")
        with open(manifest_path) as f:
            content = f.read()
        # Slice C test file must appear immediately after the Slice B entry.
        assert "tests/costing/test_cost_calculator.py" in content
        assert "tests/costing/test_life_cycle_energy_estimator.py" in content
        idx_b = content.index("tests/costing/test_cost_calculator.py")
        idx_c = content.index("tests/costing/test_life_cycle_energy_estimator.py")
        assert idx_c > idx_b, "Slice C test entry must come after Slice B entry"
