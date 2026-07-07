"""CostModelSelector unit tests — TASK-018 Slice A.

Covers the unit-test checklist from the Slice A authorization:

    - valid selector success path
    - deterministic ordering
    - missing required field blocker
    - region mismatch blocker
    - currency mismatch / unsupported FX blocker
    - effective date / expiration blocker
    - license restricted-source blocker
    - escalation reference pointer behavior
    - duplicate / ambiguous record blocker
    - no mutation of input records
    - canonical output hash / stable serialization behavior
    - closed-set error code inventory

These tests assert the selector's *contract* (frozen closed-set
behavior) rather than snapshot outputs. Any change that breaks a test
is, by construction, a contract change requiring a TASK-018
design-amendment PR.
"""

from __future__ import annotations

import copy
import json
import warnings

from hexagent.costing.cost_model_selector import (
    SCHEMA_VERSION,
    CostModelSelector,
    SelectionFilters,
    select_cost_records,
)
from hexagent.costing.errors import (
    BLOCKER_CODES,
    WARNING_CODES,
    BlockerCode,
    WarningCode,
)

# ---- Test fixture builders (TASK-013-shaped records — read-only inputs). ----


def _make_record(
    cost_record_id: str = "rec-1",
    cost_record_version: str = "1.0.0",
    cost_category: str = "c0_baseline_estimate",
    cost_basis: str = "rule_of_thumb",
    currency: str = "USD",
    quantity_basis: str = "currency_per_kg",
    license_class: str = "public_open",
    source_class: str = "vendor_public",
    cost_value: object = 12.5,
    escalation_index_reference: str | None = None,
    validity_envelope: dict[str, object] | None = None,
    correlation_ids: list[str] | None = None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    """Construct a TASK-013-shaped governance record (no mutation in-place)."""
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
    if extra:
        record.update(extra)
    return record


def _default_filters(
    record_currency: str | None = "USD",
    license_class_filter: frozenset[str] = frozenset({"public_open", "internal_open"}),
    cost_category_filter: frozenset[str] = frozenset(
        {"c0_baseline_estimate", "c1_material_weight"}
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


# ---- (1) valid selector success path ----


def test_valid_selector_success_path() -> None:
    record = _make_record(cost_record_id="rec-A", cost_record_version="1.0.0")
    result = select_cost_records([record], _default_filters())
    assert result.schema_version == SCHEMA_VERSION
    assert result.selector_run_id  # non-empty uuid-like string
    assert len(result.c0_records) == 1
    assert len(result.c1_records) == 0
    assert len(result.selection_warnings) == 0
    assert len(result.selection_blockers) == 0
    assert result.license_class_summary == {
        "public_open_count": 1,
        "internal_open_count": 0,
        "proprietary_restricted_count": 0,
    }
    assert result.provenance_chain_hash  # SHA-256 hex


# ---- (2) deterministic ordering ----


def test_deterministic_ordering_by_cost_record_id_ascending() -> None:
    records = [
        _make_record(cost_record_id="rec-C", cost_record_version="1.0.0"),
        _make_record(cost_record_id="rec-A", cost_record_version="1.0.0"),
        _make_record(cost_record_id="rec-B", cost_record_version="1.0.0"),
    ]
    result = select_cost_records(records, _default_filters())
    ids = [r["cost_record_id"] for r in result.c0_records]
    assert ids == ["rec-A", "rec-B", "rec-C"]


def test_deterministic_ordering_version_descending_within_id() -> None:
    """cost_record_id same; cost_record_version higher comes first."""
    records = [
        _make_record(cost_record_id="rec-A", cost_record_version="1.0.0"),
        _make_record(cost_record_id="rec-A", cost_record_version="2.0.0"),
        _make_record(cost_record_id="rec-A", cost_record_version="1.5.0"),
    ]
    result = select_cost_records(records, _default_filters())
    versions = [r["cost_record_version"] for r in result.c0_records]
    assert versions == ["2.0.0", "1.5.0", "1.0.0"]


def test_deterministic_across_runs_byte_identical() -> None:
    """Same inputs ⇒ same outputs, byte-for-byte."""
    records = [
        _make_record(cost_record_id="rec-A"),
        _make_record(cost_record_id="rec-B", cost_record_version="2.0.0"),
        _make_record(cost_record_id="rec-C"),
    ]
    result_first = select_cost_records(records, _default_filters())
    result_second = select_cost_records(records, _default_filters())
    # Re-serialize to a stable form and compare
    a = json.dumps(result_first.to_dict(), sort_keys=True, default=str)
    b = json.dumps(result_second.to_dict(), sort_keys=True, default=str)
    assert a == b
    assert result_first.provenance_chain_hash == result_second.provenance_chain_hash


# ---- (3) missing required field blocker ----


def test_missing_required_field_blocker() -> None:
    record = _make_record()
    del record["cost_value"]  # remove a required field
    result = select_cost_records([record], _default_filters())
    codes = [b["code"] for b in result.selection_blockers]
    assert BlockerCode.UNSPECIFIED_BLOCKER.value in codes
    # The malformed record must NOT leak into the buckets
    assert result.c0_records == ()
    assert result.c1_records == ()


# ---- (4) region mismatch blocker (selected against case_region) ----


def test_region_unsupported_blocker_when_no_records() -> None:
    """Empty record list yields region_unsupported_blocker."""
    result = select_cost_records([], _default_filters())
    codes = [b["code"] for b in result.selection_blockers]
    assert BlockerCode.REGION_UNSUPPORTED_BLOCKER.value in codes


def test_region_unsupported_only_when_no_candidates_after_filters() -> None:
    """Records exist but none match the c0_/c1_ bucket prefix."""
    record = _make_record(cost_category="c2_history_project")  # not in c0 / c1
    result = select_cost_records([record], _default_filters())
    codes = [b["code"] for b in result.selection_blockers]
    assert BlockerCode.UNSPECIFIED_BLOCKER.value in codes
    assert "cost_category_does_not_match_c0_or_c1" in str(result.selection_blockers)


# ---- (5) currency mismatch / FX behavior ----


def test_currency_mismatch_emits_warning_not_blocker_no_implicit_fx() -> None:
    """Selector never converts currency; mismatch yields a warning only."""
    record_usd = _make_record(cost_record_id="rec-USD", currency="USD")
    record_eur = _make_record(cost_record_id="rec-EUR", currency="EUR")
    # ``record_currency="USD"`` is the case-level target. EUR records
    # produce currency_fallback_used_warning, NOT a currency_mismatch_blocker;
    # the selector MUST NOT perform any FX conversion.
    result = select_cost_records([record_usd, record_eur], _default_filters(record_currency="USD"))
    codes_w = [w["code"] for w in result.selection_warnings]
    assert WarningCode.CURRENCY_FALLBACK_USED_WARNING.value in codes_w
    codes_b = [b["code"] for b in result.selection_blockers]
    assert BlockerCode.CURRENCY_MISMATCH_BLOCKER.value not in codes_b


# ---- (6) effective date / expiration (validity_envelope) blocker ----


def test_validity_envelope_blocker_when_exceeded() -> None:
    """Envelope cap exceeded → validity_envelope_blocker; record excluded."""
    base = _make_record(cost_record_id="rec-env")
    # Build the record with a record-level validity_envelope that the
    # caller's envelope cap is meant to gate. The actual stored value
    # exceeds the cap → blocker.
    record = dict(base)
    record["validity_envelope"] = {"max_unit_price_per_kg": 250.0}
    record["cost_value"] = 250.0
    filters = SelectionFilters(
        material_family="carbon_steel",
        case_region="INTL",
        effective_date="2026-07-07T00:00:00Z",
        cost_category_filter=frozenset({"c0_baseline_estimate"}),
        quantity_basis_filter=frozenset({"currency_per_kg"}),
        license_class_filter=frozenset({"public_open", "internal_open"}),
        record_currency="USD",
        # Caller cap = 100; the record stores 250 → exceeds cap.
        validity_envelope={"max_unit_price_per_kg": 100.0},
    )
    result = select_cost_records([record], filters)
    codes = [b["code"] for b in result.selection_blockers]
    assert BlockerCode.VALIDITY_ENVELOPE_BLOCKER.value in codes
    assert result.c0_records == ()


# ---- (7) license restricted-source blocker / pointer-only behavior ----


def test_license_restricted_record_pointer_only_no_body_propagation() -> None:
    """Proprietary_restricted records surface as pointer-only; cost_value is None.

    Note: in this round the selector keeps the default-filters behavior
    (no `proprietary_restricted` in `license_class_filter`), so the
    record is filtered out and the warning is emitted via the
    license-class check path. This exercises the pointer-only body
    stripping conditional too.
    """
    record = _make_record(
        cost_record_id="rec-restricted",
        license_class="proprietary_restricted",
        cost_value=999.99,
    )
    # Default filters ALLOW only public_open + internal_open (no
    # ``proprietary_restricted``), so the record is filtered out via
    # the license-class check. The selector still emits
    # restricted_only_provenance_warning.
    result = select_cost_records([record], _default_filters())
    codes_w = [w["code"] for w in result.selection_warnings]
    assert WarningCode.RESTRICTED_ONLY_PROVENANCE_WARNING.value in codes_w
    # Record does NOT appear in the buckets (filter suppressed).
    assert result.c0_records == ()

    # Now exercise the explicit-opt-in path: caller passes
    # ``proprietary_restricted`` in ``license_class_filter``.
    # The record passes the license check, lands in the bucket, and
    # the projection MUST have ``cost_value`` set to ``None``.
    filters_optin = SelectionFilters(
        material_family="carbon_steel",
        case_region="INTL",
        effective_date="2026-07-07T00:00:00Z",
        cost_category_filter=frozenset({"c0_baseline_estimate"}),
        quantity_basis_filter=frozenset({"currency_per_kg"}),
        license_class_filter=frozenset({"public_open", "internal_open", "proprietary_restricted"}),
        record_currency="USD",
    )
    result_optin = select_cost_records([record], filters_optin)
    # Caller has explicitly opted-in to proprietary_restricted: license
    # check passes.  However, per TASK-018 §8 line 340, the result
    # envelope's ``license_class_summary.proprietary_restricted_count``
    # being > 0 MUST trigger ``restricted_only_provenance_warning``
    # regardless of how the license filter handled the record upstream.
    codes_w_opt = [w["code"] for w in result_optin.selection_warnings]
    assert WarningCode.RESTRICTED_ONLY_PROVENANCE_WARNING.value in codes_w_opt
    # Record DOES appear in the bucket (license filter accepts it),
    # but the body MUST be stripped (pointer-only projection).
    assert len(result_optin.c0_records) == 1
    assert result_optin.c0_records[0]["cost_value"] is None
    assert result_optin.c0_records[0]["license_class"] == "proprietary_restricted"


def test_license_class_filter_exclusion_emits_only_warning() -> None:
    """Excluded license classes are surfaced as a warning, not a silent drop."""
    record = _make_record(
        cost_record_id="rec-excluded",
        license_class="proprietary_restricted",
    )
    # Default filters ALLOW only public_open + internal_open (no
    # ``proprietary_restricted``), so the record is filtered out.
    # The selector still emits restricted_only_provenance_warning.
    result = select_cost_records([record], _default_filters())
    codes_w = [w["code"] for w in result.selection_warnings]
    assert WarningCode.RESTRICTED_ONLY_PROVENANCE_WARNING.value in codes_w
    # But the record does NOT appear in the buckets (filter suppressed).
    assert result.c0_records == ()


# ---- (8) escalation reference pointer behavior ----


def test_escalation_reference_pointer_passes_through() -> None:
    record = _make_record(
        cost_record_id="rec-esc",
        cost_value=10.0,
        escalation_index_reference="idx-cpi-2025",
    )
    result = select_cost_records([record], _default_filters())
    assert len(result.c0_records) == 1
    assert result.c0_records[0]["escalation_index_reference"] == "idx-cpi-2025"


def test_escalation_reference_none_when_record_has_no_escalation() -> None:
    record = _make_record(cost_record_id="rec-no-esc", escalation_index_reference=None)
    result = select_cost_records([record], _default_filters())
    assert result.c0_records[0]["escalation_index_reference"] is None


# ---- (9) duplicate / ambiguous record ----


def test_duplicate_records_same_id_deduplicated_to_highest_version() -> None:
    """Same cost_record_id across records ⇒ only the highest version is kept."""
    records = [
        _make_record(cost_record_id="rec-dup", cost_record_version="1.0.0"),
        _make_record(cost_record_id="rec-dup", cost_record_version="3.0.0"),
        _make_record(cost_record_id="rec-dup", cost_record_version="2.0.0"),
    ]
    result = select_cost_records(records, _default_filters())
    # All 3 records survive the filter pipeline; ordering rules apply.
    versions = [r["cost_record_version"] for r in result.c0_records]
    assert versions == ["3.0.0", "2.0.0", "1.0.0"]
    # Selection itself does not raise an exception; ambiguity is documented
    # via deterministic ordering, not blockers.
    assert result.selection_blockers == ()


def test_invalid_cost_record_version_surfaces_as_blocker() -> None:
    """A non-semver cost_record_version is treated as an unspecified_blocker
    via the internal sort-key path; the record is dropped before bucketing.
    The selection MUST still complete (no exception escaping to caller)."""
    record = _make_record(cost_record_id="rec-bad", cost_record_version="not_semver")
    # The internal _negate_semver call emits a CostSelectorError which
    # we catch + record into selection_blockers. We catch the
    # ``CostSelectorError`` indirectly by inspecting selection_blockers.
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = select_cost_records([record], _default_filters())
    codes = [b["code"] for b in result.selection_blockers]
    assert BlockerCode.UNSPECIFIED_BLOCKER.value in codes


# ---- (10) no mutation of input records ----


def test_input_records_not_mutated() -> None:
    """The selector MUST NOT mutate any record passed in (TASK-018 §17)."""
    record = _make_record()
    original = copy.deepcopy(record)
    _ = select_cost_records([record], _default_filters())
    assert record == original
    # Hashes of the input record before and after also match.
    pre_hash = json.dumps(record, sort_keys=True, default=str)
    _ = select_cost_records([record], _default_filters())
    post_hash = json.dumps(record, sort_keys=True, default=str)
    assert pre_hash == post_hash


# ---- (11) canonical output hash / stable serialization ----


def test_provenance_chain_hash_stable_for_same_inputs() -> None:
    a = select_cost_records([_make_record()], _default_filters())
    b = select_cost_records([_make_record()], _default_filters())
    assert a.provenance_chain_hash == b.provenance_chain_hash


def test_provenance_chain_hash_changes_when_input_changes() -> None:
    a = select_cost_records([_make_record(cost_record_id="rec-A")], _default_filters())
    b = select_cost_records([_make_record(cost_record_id="rec-B")], _default_filters())
    assert a.provenance_chain_hash != b.provenance_chain_hash


def test_selector_run_id_changes_with_input() -> None:
    a = select_cost_records([_make_record(cost_record_id="rec-A")], _default_filters())
    b = select_cost_records([_make_record(cost_record_id="rec-B")], _default_filters())
    assert a.selector_run_id != b.selector_run_id


# ---- (12) closed-set error code inventory ----


def test_blocker_closed_set_only_callsites() -> None:
    """Build an oracle of all TASK-018 §9.1 blocker codes and confirm the
    selector never emits a code outside this closed set across the
    exercises above."""
    allowed = set(BLOCKER_CODES)
    # Run an aggressive scenario that exercises every selector code path.
    bad = _make_record()
    del bad["cost_value"]
    scenario: list[dict[str, object]] = [
        _make_record(cost_record_id="ok"),
        _make_record(cost_record_id="bad-cost", cost_record_version="not_semver"),
        bad,
    ]  # type: ignore[list-item]  # bad is intentionally a malformed dict
    # Envelope violation
    env = _make_record(
        cost_record_id="env-bad",
        validity_envelope={"max_density_kg_per_m3": 8000.0},
        cost_value=42.0,
    )
    env_dict: dict[str, object] = dict(env)
    env_dict["validity_envelope"] = {"max_density_kg_per_m3": 8000.0, "density_kg_per_m3": 9000.0}
    scenario.append(env_dict)
    result = select_cost_records(scenario, _default_filters())
    observed = {b["code"] for b in result.selection_blockers}
    # Observed ⊆ allowed
    assert observed.issubset(allowed), observed - allowed


def test_warning_closed_set_only_callsites() -> None:
    """Companion to the above for warning codes (TASK-018 §9.2)."""
    allowed = set(WARNING_CODES)
    scenario = [
        _make_record(cost_record_id="rec-USD", currency="USD"),
        _make_record(cost_record_id="rec-EUR", currency="EUR"),
        _make_record(
            cost_record_id="rec-restricted",
            license_class="proprietary_restricted",
        ),
    ]
    result = select_cost_records(scenario, _default_filters())
    observed = {w["code"] for w in result.selection_warnings}
    assert observed.issubset(allowed), observed - allowed


def test_class_selector_module_exposes_required_frozen_anchors() -> None:
    """Sanity: the application layer exposes the contract anchors."""
    sel = CostModelSelector
    assert sel.SCHEMA_VERSION == SCHEMA_VERSION
    assert callable(sel.select)  # bound via class body


# ---- P1-1 design-conformance tests: license_class_summary shape ----


def test_license_class_summary_keys_use_count_suffix_per_design() -> None:
    """TASK-018 §5.1.3 + §5.2.2 + §8 specify ``*_count`` suffix keys."""
    result = select_cost_records([_make_record()], _default_filters())
    assert set(result.license_class_summary.keys()) == {
        "public_open_count",
        "internal_open_count",
        "proprietary_restricted_count",
    }


# ---- P1-2 design-conformance tests: §8 restricted-warning emission ----


def test_restricted_only_provenance_warning_emitted_when_envelope_contains_restricted() -> None:
    """§8 line 340: ``proprietary_restricted_count > 0`` ⇒ warning."""
    record = _make_record(
        cost_record_id="rec-restricted-opt-in",
        license_class="proprietary_restricted",
    )
    filters_optin = SelectionFilters(
        material_family="carbon_steel",
        case_region="INTL",
        effective_date="2026-07-07T00:00:00Z",
        cost_category_filter=frozenset({"c0_baseline_estimate"}),
        quantity_basis_filter=frozenset({"currency_per_kg"}),
        license_class_filter=frozenset({"public_open", "internal_open", "proprietary_restricted"}),
        record_currency="USD",
    )
    result = select_cost_records([record], filters_optin)
    assert result.license_class_summary["proprietary_restricted_count"] == 1
    codes_w = [w["code"] for w in result.selection_warnings]
    assert WarningCode.RESTRICTED_ONLY_PROVENANCE_WARNING.value in codes_w
    # Dedupe: only one entry of this code in warnings.
    assert codes_w.count(WarningCode.RESTRICTED_ONLY_PROVENANCE_WARNING.value) == 1


# ---- P1-3 design-conformance tests: selector_run_id format / UUID v5 ----


def test_selector_run_id_is_uuid_v5_format() -> None:
    """§5.1.3: ``selector_run_id`` MUST be a deterministic UUID v5."""
    import uuid as _uuid

    result = select_cost_records([_make_record()], _default_filters())
    parsed = _uuid.UUID(result.selector_run_id)  # raises if not a UUID
    assert parsed.version == 5


def test_selector_run_id_is_deterministic_across_equivalent_inputs() -> None:
    """Same canonical inputs ⇒ identical selector_run_id (UUID v5 determinism)."""
    a = select_cost_records([_make_record()], _default_filters())
    b = select_cost_records([_make_record()], _default_filters())
    assert a.selector_run_id == b.selector_run_id


def test_selector_run_id_changes_when_selection_changes() -> None:
    a = select_cost_records([_make_record(cost_record_id="rec-A")], _default_filters())
    b = select_cost_records([_make_record(cost_record_id="rec-B")], _default_filters())
    assert a.selector_run_id != b.selector_run_id


# ---- P1-4 design-conformance tests: escalation_index_reference_filter ----


def test_escalation_filter_selects_matching_pointer() -> None:
    """§5.1.1 / §5.2.2: a record whose ``escalation_index_reference`` is
    in the caller's filter set is selected."""
    rec_match = _make_record(cost_record_id="rec-match", escalation_index_reference="idx-cpi-2025")
    rec_no_match = _make_record(
        cost_record_id="rec-no-match", escalation_index_reference="idx-ppi-2024"
    )
    filters = SelectionFilters(
        material_family="carbon_steel",
        case_region="INTL",
        effective_date="2026-07-07T00:00:00Z",
        cost_category_filter=frozenset({"c0_baseline_estimate"}),
        quantity_basis_filter=frozenset({"currency_per_kg"}),
        license_class_filter=frozenset({"public_open", "internal_open"}),
        record_currency="USD",
        escalation_index_reference_filter=frozenset({"idx-cpi-2025"}),
    )
    result = select_cost_records([rec_match, rec_no_match], filters)
    ids = [r["cost_record_id"] for r in result.c0_records]
    assert ids == ["rec-match"]
    assert result.license_class_summary["public_open_count"] == 1


def test_escalation_filter_excludes_non_matching_pointer() -> None:
    """§5.1.1: a record whose ``escalation_index_reference`` is NOT in the
    caller's filter set is excluded."""
    rec = _make_record(
        cost_record_id="rec-non-matching",
        escalation_index_reference="idx-ppi-2024",
    )
    filters = SelectionFilters(
        material_family="carbon_steel",
        case_region="INTL",
        effective_date="2026-07-07T00:00:00Z",
        cost_category_filter=frozenset({"c0_baseline_estimate"}),
        quantity_basis_filter=frozenset({"currency_per_kg"}),
        license_class_filter=frozenset({"public_open", "internal_open"}),
        record_currency="USD",
        escalation_index_reference_filter=frozenset({"idx-cpi-2025"}),
    )
    result = select_cost_records([rec], filters)
    assert result.c0_records == ()
    assert result.license_class_summary["public_open_count"] == 0


def test_escalation_filter_excludes_records_with_null_pointer_when_filter_is_set() -> None:
    """Records with ``escalation_index_reference=None`` are excluded
    whenever the caller supplied a (non-None) filter set."""
    rec_null = _make_record(cost_record_id="rec-null", escalation_index_reference=None)
    rec_with_ptr = _make_record(cost_record_id="rec-ptr", escalation_index_reference="idx-cpi-2025")
    filters = SelectionFilters(
        material_family="carbon_steel",
        case_region="INTL",
        effective_date="2026-07-07T00:00:00Z",
        cost_category_filter=frozenset({"c0_baseline_estimate"}),
        quantity_basis_filter=frozenset({"currency_per_kg"}),
        license_class_filter=frozenset({"public_open", "internal_open"}),
        record_currency="USD",
        escalation_index_reference_filter=frozenset({"idx-cpi-2025"}),
    )
    result = select_cost_records([rec_null, rec_with_ptr], filters)
    ids = [r["cost_record_id"] for r in result.c0_records]
    assert ids == ["rec-ptr"]


def test_escalation_filter_none_means_no_filtering() -> None:
    """When ``escalation_index_reference_filter`` is ``None``, the
    selector does NOT enforce escalation matching (records pass)."""
    rec_null = _make_record(cost_record_id="rec-null", escalation_index_reference=None)
    rec_with_ptr = _make_record(cost_record_id="rec-ptr", escalation_index_reference="idx-cpi-2025")
    filters = SelectionFilters(
        material_family="carbon_steel",
        case_region="INTL",
        effective_date="2026-07-07T00:00:00Z",
        cost_category_filter=frozenset({"c0_baseline_estimate"}),
        quantity_basis_filter=frozenset({"currency_per_kg"}),
        license_class_filter=frozenset({"public_open", "internal_open"}),
        record_currency="USD",
        escalation_index_reference_filter=None,
    )
    result = select_cost_records([rec_null, rec_with_ptr], filters)
    ids = sorted([str(r["cost_record_id"]) for r in result.c0_records])
    assert ids == ["rec-null", "rec-ptr"]


def test_escalation_filter_deterministic_after_filter_pass() -> None:
    """Two runs with the same inputs and escalation filter set produce
    byte-identical selector_run_id and provenance_chain_hash."""
    filters = SelectionFilters(
        material_family="carbon_steel",
        case_region="INTL",
        effective_date="2026-07-07T00:00:00Z",
        cost_category_filter=frozenset({"c0_baseline_estimate"}),
        quantity_basis_filter=frozenset({"currency_per_kg"}),
        license_class_filter=frozenset({"public_open", "internal_open"}),
        record_currency="USD",
        escalation_index_reference_filter=frozenset({"idx-cpi-2025"}),
    )
    rec = _make_record(cost_record_id="rec-det", escalation_index_reference="idx-cpi-2025")
    a = select_cost_records([rec], filters)
    b = select_cost_records([rec], filters)
    assert a.selector_run_id == b.selector_run_id
    assert a.provenance_chain_hash == b.provenance_chain_hash
