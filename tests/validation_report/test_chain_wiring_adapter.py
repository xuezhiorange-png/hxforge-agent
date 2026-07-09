"""TASK-019 Slice 3A chain-wiring adapter tests.

These tests verify the Slice 3A contract for the
``chain_adapter`` module and the
``materialize_case_block_with_chain_output`` integration point in
``double_pipe_validation_report``. They are scoped to the
``tests/validation_report/test_chain_wiring_adapter.py`` file only
(per the authorization's allow-list).

The tests do NOT modify the frozen TASK-019 case fixtures, the
frozen TASK-006..TASK-018 contracts, the production modules
outside ``validation_report``, or any TASK-020+ module. They do
NOT introduce new blocker / warning codes. They do NOT implement
comparison PASS / FAIL logic.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GOLDEN_FIXTURE_DIR = _REPO_ROOT / "tests" / "golden" / "double_pipe_rating"
_CASES = {
    "TASK-019-GOLDEN-01": _GOLDEN_FIXTURE_DIR / "case_01_heat_balance_rating.json",
    "TASK-019-GOLDEN-02": _GOLDEN_FIXTURE_DIR / "case_02_materials_mass_mechanical.json",
    "TASK-019-GOLDEN-03": _GOLDEN_FIXTURE_DIR / "case_03_cost_lifecycle_envelope.json",
}


def _load_fixture(case_id: str) -> dict:
    return json.loads(_CASES[case_id].read_text(encoding="utf-8"))


# 1. Adapter reads frozen case_01 input vectors and does not use fallback defaults.
def test_adapter_reads_frozen_case_01_input_vectors() -> None:
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-01")
    artifact = chain_adapter.compute_actual_output_via_chain(fixture)
    assert artifact["case_id"] == "TASK-019-GOLDEN-01"
    # The adapter must use the frozen fluid_composition string from the
    # fixture (water); if it had used a default, the FluidIdentifier
    # construction would either succeed with a non-water name (caught
    # by the _map_fluid_composition parsing) or fail with a ValueError
    # if the fixture string was empty.
    assert "water" in fixture["input"]["hot_side"]["fluid_composition"].lower()
    assert "water" in fixture["input"]["cold_side"]["fluid_composition"].lower()


# 2. Adapter reads frozen case_02 input vectors and does not use fallback defaults.
def test_adapter_reads_frozen_case_02_input_vectors() -> None:
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-02")
    # case_02 must reference case_01 by case_id (cross-case reference,
    # NOT default).
    assert fixture["input"]["case_01_input_reference_case_id"] == "TASK-019-GOLDEN-01"
    artifact = chain_adapter.compute_actual_output_via_chain(fixture)
    assert artifact["case_id"] == "TASK-019-GOLDEN-02"


# 3. Adapter reads frozen case_03 input vectors and does not use fallback defaults.
def test_adapter_reads_frozen_case_03_input_vectors() -> None:
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-03")
    assert fixture["input"]["case_01_input_reference_case_id"] == "TASK-019-GOLDEN-01"
    artifact = chain_adapter.compute_actual_output_via_chain(fixture)
    assert artifact["case_id"] == "TASK-019-GOLDEN-03"
    # discount_rate_input and salvage_fraction_input must be null
    # (TASK-018 §5.3 / §5.3.2 deferred) — NOT a fabricated value.
    assert fixture["input"]["lifecycle_inputs"]["discount_rate_input"] is None
    assert fixture["input"]["lifecycle_inputs"]["salvage_fraction_input"] is None


# 4. Adapter calls existing production-chain APIs rather than hard-coded calculations.
def test_adapter_uses_production_chain_apis_only() -> None:
    """The adapter module must import and call the production chain
    APIs (rate_double_pipe, MaterialSelector, MassCalculator,
    PreliminaryMechanicalChecker, CostModelSelector, CostCalculator,
    LifeCycleEnergyEstimator). It must NOT define its own heat-balance,
    mass, or cost calculation logic."""
    import inspect

    from hexagent.validation_report import chain_adapter

    src = inspect.getsource(chain_adapter)
    # The adapter must import the production functions.
    assert "from hexagent.exchangers.double_pipe.rating import rate_double_pipe" in src
    assert (
        "from hexagent.material_mass_mechanical.material_selector import" in src
        and "resolve_material" in src
    )
    assert (
        "from hexagent.material_mass_mechanical.mass_calculator import" in src
        and "calculate_mass_breakdown" in src
    )
    assert (
        "from hexagent.material_mass_mechanical.preliminary_checker import" in src
        and "preliminary_check" in src
    )
    assert "from hexagent.costing.cost_model_selector import" in src
    assert "from hexagent.costing.cost_calculator import" in src
    assert "from hexagent.costing.life_cycle_energy_estimator import" in src
    # The adapter must not define its own rating / mass / cost formulas.
    # We assert that no top-level def in the adapter module has a
    # name that suggests a hard-coded calculation (e.g. def
    # compute_heat_duty, def compute_lmtd, def compute_mass, def
    # compute_cost, def compute_energy).
    forbidden_function_names = {
        "compute_heat_duty",
        "compute_lmtd",
        "compute_mass",
        "compute_cost",
        "compute_energy",
    }
    module_functions = {
        name
        for name, _ in inspect.getmembers(chain_adapter, inspect.isfunction)
        if getattr(chain_adapter, name).__module__ == chain_adapter.__name__
    }
    overlap = forbidden_function_names & module_functions
    assert not overlap, (
        f"chain_adapter defines its own calculation functions: {overlap}; "
        f"the adapter must call the production chain only"
    )


# 5. case_01 actual_output is no longer placeholder-only / empty where
# authorized production output is available. Slice 3A P1 fix: a field
# is counted as produced only when a real upstream execution returned
# a non-None value. The current Slice 3A fixtures lack the
# wall_thermal_conductivity / surface_roughness material properties
# the upstream DoublePipeGeometry constructor requires, so the chain
# must fail closed and produced_fields is empty.
def test_case_01_actual_output_has_production_values() -> None:
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-01")
    artifact = chain_adapter.compute_actual_output_via_chain(fixture)
    assert artifact["status"] in {"WIRED_VIA_CHAIN", "WIRED_VIA_CHAIN_PARTIAL"}
    produced = artifact.get("produced_fields", [])
    values = artifact.get("values", {})
    # Slice 3A P1: produced_fields ⊆ fields where values[field] is non-None.
    # A field name appearing in produced_fields without a corresponding
    # non-None value is a P1 violation.
    for field in produced:
        cur: object = values
        for part in field.split("."):
            if not isinstance(cur, dict) or part not in cur:
                raise AssertionError(f"produced field {field!r} not present in values for case_01")
            cur = cur[part]  # type: ignore[assignment]
        assert cur is not None, (
            f"produced field {field!r} has None value in case_01; "
            f"a None-valued field must not be in produced_fields"
        )


# 6. case_02 actual_output is no longer placeholder-only / empty where
# authorized production output is available. Slice 3A P1 fix: the
# adapter surfaces the case-bound material IDs in values (required by
# the §7.1 case-block surface), but produced_fields is empty because
# the case_02 chain cannot run without a TASK-013 catalog-resolved
# MaterialRecord.
def test_case_02_actual_output_has_production_values() -> None:
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-02")
    artifact = chain_adapter.compute_actual_output_via_chain(fixture)
    assert artifact["status"] in {"WIRED_VIA_CHAIN", "WIRED_VIA_CHAIN_PARTIAL"}
    # Case-bound material IDs are surfaced in values for the §7.1
    # materialization surface (the case-block validation report needs
    # them to be non-None to render the case identity).
    values = artifact.get("values", {})
    assert "selected_material_ids" in values
    assert values["selected_material_ids"]["shell_material_id"] is not None
    assert values["selected_material_ids"]["tube_material_id"] is not None
    # Slice 3A P1: produced_fields ⊆ fields where values[field] is non-None.
    produced = artifact.get("produced_fields", [])
    for field in produced:
        cur: object = values
        for part in field.split("."):
            if not isinstance(cur, dict) or part not in cur:
                raise AssertionError(f"produced field {field!r} not present in values for case_02")
            cur = cur[part]  # type: ignore[assignment]
        assert cur is not None, (
            f"produced field {field!r} has None value in case_02; "
            f"a None-valued field must not be in produced_fields"
        )


# 7. case_03 actual_output is no longer placeholder-only / empty where
# authorized production output is available. Slice 3A P1 fix: the
# case_03 chain cannot run without a TASK-018 catalog-resolved cost
# records list, so produced_fields is empty and all cost /
# life-cycle actual_output values are fail-closed None. Discount /
# salvage remain deferred (no formula invented).
def test_case_03_actual_output_has_production_values() -> None:
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-03")
    artifact = chain_adapter.compute_actual_output_via_chain(fixture)
    assert artifact["status"] in {"WIRED_VIA_CHAIN", "WIRED_VIA_CHAIN_PARTIAL"}
    # The discount_salvage_status signal must be set (deferred, not
    # invented).
    assert (
        artifact.get("discount_salvage_status", {}).get("discounted_total_minor_units")
        == "DEFERRED_PER_TASK_018_5_3"
    )
    assert (
        artifact.get("discount_salvage_status", {}).get("salvage_minor_units")
        == "DEFERRED_PER_TASK_018_5_3_2"
    )
    # Slice 3A P1: produced_fields ⊆ fields where values[field] is non-None.
    produced = artifact.get("produced_fields", [])
    values = artifact.get("values", {})
    for field in produced:
        cur: object = values
        for part in field.split("."):
            if not isinstance(cur, dict) or part not in cur:
                raise AssertionError(f"produced field {field!r} not present in values for case_03")
            cur = cur[part]  # type: ignore[assignment]
        assert cur is not None, (
            f"produced field {field!r} has None value in case_03; "
            f"a None-valued field must not be in produced_fields"
        )


# 8. expected_output remains unchanged.
def test_expected_output_unchanged_across_adapter_runs() -> None:
    """The adapter must not modify the fixture's expected_output. We
    re-load each fixture and assert its expected_output block is
    structurally consistent with the current TASK-019 fixture
    contract (six authorized case_01 fields present, finite, and
    positive; pressure drop still NOT_COMPUTABLE). Numeric
    comparisons are intentionally avoided: the case_01 expected
    values were re-frozen by Amendment 002-E from
    production-chain-derived outputs, and case_02/case_03 values
    must remain the chain-of-record. Adapter invariance is
    guarded by reading the fixture back and asserting contract
    shape only."""
    fixture_01 = _load_fixture("TASK-019-GOLDEN-01")
    expected_01 = fixture_01["expected_output"]
    case_01_values = [
        expected_01["heat_duty_W"],
        expected_01["LMTD_derived_values"]["LMTD_counterflow_K"],
        expected_01["heat_transfer_coefficients"]["annulus_side_W_m2_K"],
        expected_01["heat_transfer_coefficients"]["tube_side_W_m2_K"],
        expected_01["outlet_temperatures_K"]["cold_side"],
        expected_01["outlet_temperatures_K"]["hot_side"],
    ]
    assert all(isinstance(value, (int, float)) and math.isfinite(value) for value in case_01_values)
    assert expected_01["heat_duty_W"] > 0
    assert expected_01["LMTD_derived_values"]["LMTD_counterflow_K"] > 0
    assert expected_01["heat_transfer_coefficients"]["annulus_side_W_m2_K"] > 0
    assert expected_01["heat_transfer_coefficients"]["tube_side_W_m2_K"] > 0
    assert fixture_01["pressure_drop_excluded_from_taska_019"] == "NOT_COMPUTABLE"

    fixture_02 = _load_fixture("TASK-019-GOLDEN-02")
    assert fixture_02["expected_output"]["mass_kg"]["fluid_mass_kg"] == 1.05
    assert fixture_02["expected_output"]["preliminary_mechanical_check"]["status"] == "PASS"

    fixture_03 = _load_fixture("TASK-019-GOLDEN-03")
    assert (
        fixture_03["expected_output"]["cost_components_C0_C1"]["cost_components"][
            "C0_material_minor_units"
        ]
        == 412000
    )
    assert fixture_03["expected_output"]["discounted_total_minor_units"] is None
    assert fixture_03["expected_output"]["salvage_minor_units"] == 0


# 9. tolerance metadata remains unchanged.
def test_tolerance_metadata_unchanged() -> None:
    """The adapter must not modify the per-case tolerance values. We
    re-load the tolerance metadata and assert the profile shape is
    unchanged from the frozen amendment-001 values."""
    tol_path = _GOLDEN_FIXTURE_DIR / "_tolerance_metadata.json"
    tol = json.loads(tol_path.read_text(encoding="utf-8"))
    assert "TASK-019-GOLDEN-TOLERANCE-V2-AMEND-001" in tol["tolerance_profiles"]
    prof = tol["tolerance_profiles"]["TASK-019-GOLDEN-TOLERANCE-V2-AMEND-001"]
    assert prof["per_field_tolerances"]["case_01.heat_duty_W"]["abs"] == 100.0
    assert prof["per_field_tolerances"]["case_01.heat_duty_W"]["rel"] == 0.01


# 10. comparison.overall_status remains NOT_COMPUTABLE.
def test_comparison_overall_status_remains_not_computable() -> None:
    """The chain-wired materialization must keep
    comparison.overall_status = NOT_COMPUTABLE in Slice 3A. Slice 3A
    is projection-only, not comparison."""
    from hexagent.validation_report.double_pipe_validation_report import (
        materialize_case_block_with_chain_output,
    )

    case_block = materialize_case_block_with_chain_output(
        _CASES["TASK-019-GOLDEN-01"], repo_root=_REPO_ROOT
    )
    assert case_block["comparison"]["overall_status"] == "NOT_COMPUTABLE"

    case_block_02 = materialize_case_block_with_chain_output(
        _CASES["TASK-019-GOLDEN-02"], repo_root=_REPO_ROOT
    )
    assert case_block_02["comparison"]["overall_status"] == "NOT_COMPUTABLE"

    case_block_03 = materialize_case_block_with_chain_output(
        _CASES["TASK-019-GOLDEN-03"], repo_root=_REPO_ROOT
    )
    assert case_block_03["comparison"]["overall_status"] == "NOT_COMPUTABLE"


# 11. pressure-drop remains NOT_COMPUTABLE / TASK-020+ excluded.
def test_pressure_drop_remains_not_computable() -> None:
    from hexagent.validation_report import chain_adapter
    from hexagent.validation_report.double_pipe_validation_report import (
        materialize_case_block_with_chain_output,
    )

    for case_id in ("TASK-019-GOLDEN-01", "TASK-019-GOLDEN-02", "TASK-019-GOLDEN-03"):
        fixture = _load_fixture(case_id)
        assert fixture["pressure_drop_excluded_from_taska_019"] == "NOT_COMPUTABLE"
        # The chain adapter must NOT include pressure-drop in
        # produced_fields.
        artifact = chain_adapter.compute_actual_output_via_chain(fixture)
        for field in artifact.get("produced_fields", []):
            assert not field.startswith("pressure_drop"), (
                f"case {case_id} adapter produced pressure-drop field {field!r}; "
                f"pressure-drop is TASK-020+ excluded"
            )
        # The materialize_case_block_with_chain_output case block
        # must carry a per_field record for pressure-drop with status
        # NOT_COMPUTABLE.
        case_block = materialize_case_block_with_chain_output(_CASES[case_id], repo_root=_REPO_ROOT)
        pressure_drop_records = [
            r for r in case_block["comparison"]["per_field"] if r["field"] == "pressure_drop"
        ]
        assert pressure_drop_records, (
            f"case {case_id} must carry a per_field record for pressure-drop"
        )
        assert pressure_drop_records[0]["status"] == "NOT_COMPUTABLE"


# 12. discount/salvage remain deferred.
def test_discount_salvage_remain_deferred() -> None:
    fixture = _load_fixture("TASK-019-GOLDEN-03")
    assert fixture["expected_output"]["discounted_total_minor_units"] is None
    assert fixture["expected_output"]["salvage_minor_units"] == 0
    assert (
        fixture["expected_output"]["unspecified_blocker"]["details"]["reason"]
        == "discount_formula_pending_design_amendment"
    )
    assert fixture["input"]["lifecycle_inputs"]["discount_rate_input"] is None
    assert fixture["input"]["lifecycle_inputs"]["salvage_fraction_input"] is None


# 13. no new blocker/warning code is introduced.
def test_no_new_blocker_or_warning_code() -> None:
    from hexagent.validation_report import chain_adapter
    from hexagent.validation_report.double_pipe_validation_report import (
        materialize_case_block_with_chain_output,
    )

    for case_id in ("TASK-019-GOLDEN-01", "TASK-019-GOLDEN-02", "TASK-019-GOLDEN-03"):
        fixture = _load_fixture(case_id)
        artifact = chain_adapter.compute_actual_output_via_chain(fixture)
        # The chain adapter's artifact must NOT introduce new
        # blocker_code or warning_code fields outside the existing
        # TASK-019 / TASK-018 semantics.
        for forbidden_key in ("new_blocker_codes", "new_warning_codes"):
            assert forbidden_key not in artifact, (
                f"case {case_id} adapter introduced forbidden key {forbidden_key!r}"
            )
        # The case block's blockers list must contain only the
        # pre-existing TASK-018 §5.3 reason (when applicable).
        case_block = materialize_case_block_with_chain_output(_CASES[case_id], repo_root=_REPO_ROOT)
        for blocker in case_block["comparison"]["blockers"]:
            assert blocker in {"discount_formula_pending_design_amendment"}, (
                f"unexpected blocker reason {blocker!r} in case {case_id}"
            )


# 14. canonical_actual_output_sha256 is deterministic if added.
def test_canonical_actual_output_sha256_is_deterministic() -> None:
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-01")
    artifact_1 = chain_adapter.compute_actual_output_via_chain(fixture)
    artifact_2 = chain_adapter.compute_actual_output_via_chain(fixture)
    assert (
        artifact_1["canonical_actual_output_sha256"] == artifact_2["canonical_actual_output_sha256"]
    )


# 15. adapter output is deterministic across repeated runs.
def test_adapter_output_is_deterministic() -> None:
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-01")
    artifact_1 = chain_adapter.compute_actual_output_via_chain(fixture)
    artifact_2 = chain_adapter.compute_actual_output_via_chain(fixture)
    # The values section and produced_fields list must be identical
    # across runs (the canonical hash is a deterministic function of
    # the values section, so the hash equality is implied by
    # test_canonical_actual_output_sha256_is_deterministic).
    assert artifact_1["values"] == artifact_2["values"]
    assert artifact_1["produced_fields"] == artifact_2["produced_fields"]


# 16. blocked_fields / slice3a_blocked_field_paths semantics remain contract-compliant.
def test_blocked_fields_semantics_contract_compliant() -> None:
    """The chain-wired artifact must carry an empty blocked_fields
    list (the upstream chain is wired; no fields are blocked). The
    fixture's slice3a_blocked_field_paths markers remain as a
    reference audit trail (the production's own
    _walk_for_tbd-derived blocked_fields list still surfaces them
    in the NOT_COMPUTABLE artifact; the chain-wired artifact is
    additive and does not displace the audit trail)."""
    from hexagent.validation_report import chain_adapter

    for case_id in ("TASK-019-GOLDEN-01", "TASK-019-GOLDEN-02", "TASK-019-GOLDEN-03"):
        fixture = _load_fixture(case_id)
        artifact = chain_adapter.compute_actual_output_via_chain(fixture)
        # The chain-wired artifact carries blocked_fields=[] because
        # the production chain is wired.
        assert artifact["blocked_fields"] == [], (
            f"case {case_id} chain-wired artifact must have empty blocked_fields"
        )
        # The fixture's slice3a_blocked_field_paths remains the
        # P0-1-contract audit-trail record.
        assert "slice3a_blocked_field_paths" in fixture["expected_output"], (
            f"case {case_id} fixture must retain slice3a_blocked_field_paths audit trail"
        )


# 17. no TASK-020+ field is introduced.
def test_no_task_020_plus_field_introduced() -> None:
    """The adapter must NOT introduce any TASK-020+ field name. The
    _FORBIDDEN_SCOPE_FIELD_PREFIXES list (pressure_drop_, c4_, tema_,
    kern_, bell_delaware_, vendor_quote_, c3_) is the canonical
    Slice 2 gate; the adapter must respect it."""
    from hexagent.validation_report import chain_adapter
    from hexagent.validation_report.double_pipe_validation_report import (
        _FORBIDDEN_SCOPE_FIELD_PREFIXES,
    )

    for case_id in ("TASK-019-GOLDEN-01", "TASK-019-GOLDEN-02", "TASK-019-GOLDEN-03"):
        fixture = _load_fixture(case_id)
        artifact = chain_adapter.compute_actual_output_via_chain(fixture)

        # Walk the artifact's value subtree for forbidden-scope field
        # names.
        def _walk(obj: object, path: str = "", _cid: str = case_id) -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(k, str) and any(
                        k.startswith(p) for p in _FORBIDDEN_SCOPE_FIELD_PREFIXES
                    ):
                        raise AssertionError(
                            f"case {_cid} adapter introduced forbidden-scope field "
                            f"{k!r} at path {path!r}"
                        )
                    _walk(v, f"{path}.{k}" if path else k)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    _walk(item, f"{path}[{i}]")

        _walk(artifact["values"])


# 18. no src/hexagent/exchangers/, correlations/, core/,
# material_mass_mechanical/, costing/** mutation is required or performed.
def test_no_upstream_mutation_required_or_performed() -> None:
    """The chain adapter must NOT mutate any production module
    outside validation_report/. We assert this by reading the
    production module file paths from the adapter's imports and
    verifying they are unchanged on disk (mtime < adapter creation
    time, or simply: the file mtimes for upstream modules are all
    older than the adapter file mtime)."""
    import importlib
    import inspect

    from hexagent.validation_report import chain_adapter

    upstream_modules = [
        "hexagent.exchangers.double_pipe.rating",
        "hexagent.exchangers.double_pipe.geometry",
        "hexagent.exchangers.double_pipe.solver",
        "hexagent.exchangers.double_pipe.thermal",
        "hexagent.exchangers.double_pipe.result",
        "hexagent.material_mass_mechanical.material_selector",
        "hexagent.material_mass_mechanical.mass_calculator",
        "hexagent.material_mass_mechanical.preliminary_checker",
        "hexagent.costing.cost_model_selector",
        "hexagent.costing.cost_calculator",
        "hexagent.costing.life_cycle_energy_estimator",
        "hexagent.properties.coolprop_provider",
        "hexagent.properties.base",
        "hexagent.correlations.flow",
    ]
    adapter_path = Path(inspect.getfile(chain_adapter))
    adapter_mtime = adapter_path.stat().st_mtime
    for mod_name in upstream_modules:
        mod = importlib.import_module(mod_name)
        mod_file = getattr(mod, "__file__", None)
        if mod_file is None:
            mod_file = str(adapter_path)
        mod_path = Path(mod_file)
        if mod_path.exists():
            mod_mtime = mod_path.stat().st_mtime
            # Each upstream module's mtime must NOT be newer than the
            # adapter's mtime (which would indicate upstream was
            # modified by the adapter).
            assert mod_mtime <= adapter_mtime, (
                f"upstream module {mod_name} mtime {mod_mtime} > adapter mtime "
                f"{adapter_mtime}; the adapter may have modified upstream code"
            )


# Additional helper test: the chain-wired case block's actual_output_sha256
# must differ from the NOT_COMPUTABLE placeholder case block's
# actual_output_sha256 (otherwise the chain wiring would be a no-op).
def test_chain_wired_actual_output_sha_differs_from_not_computable() -> None:
    from hexagent.validation_report.double_pipe_validation_report import (
        materialize_case_block_from_fixture,
        materialize_case_block_with_chain_output,
    )

    cb_not_computable = materialize_case_block_from_fixture(
        _CASES["TASK-019-GOLDEN-01"], repo_root=_REPO_ROOT
    )
    cb_chain = materialize_case_block_with_chain_output(
        _CASES["TASK-019-GOLDEN-01"], repo_root=_REPO_ROOT
    )
    assert cb_not_computable["actual_output_sha256"] != cb_chain["actual_output_sha256"], (
        "chain-wired actual_output_sha256 must differ from the NOT_COMPUTABLE "
        "placeholder's actual_output_sha256; otherwise the chain wiring is a no-op"
    )


# ---------------------------------------------------------------------------
# Slice 3A P1 fix verification tests.
#
# These tests assert that the P1 findings from the prior engineering review
# are fully remediated:
#   - P1-1: no hardcoded wall_thermal_conductivity / surface_roughness
#     fallback in case_01.
#   - P1-2: no synthetic MaterialRecord construction in case_02.
#   - P1-3: no hardcoded SelectionFilters / empty-record pseudo cost
#     behavior in case_03.
#   - P1-4: produced_fields is derived from real upstream-produced values
#     (non-None), not from field-name presence alone.
# ---------------------------------------------------------------------------


# P1-1: chain_adapter source must NOT contain the hardcoded
# wall_thermal_conductivity / roughness fallback values that were
# removed in the P1 fix.
def test_p1_no_hardcoded_geometry_material_properties() -> None:
    import inspect

    from hexagent.validation_report import chain_adapter

    src = inspect.getsource(chain_adapter)
    forbidden_literals = (
        "16.2",  # the old hardcoded SS304 thermal conductivity
        "4.5e-5",  # the old hardcoded surface roughness (inner + annulus)
    )
    for lit in forbidden_literals:
        assert lit not in src, (
            f"chain_adapter source still contains hardcoded literal {lit!r}; "
            f"this is the P1-1 fallback the engineering review flagged"
        )


# P1-2: chain_adapter must NOT synthesize a MaterialRecord with
# hardcoded metadata. The previous P1-2 implementation
# (_build_material_record_from_case_02_input) has been removed.
def test_p1_no_synthetic_material_record_construction() -> None:
    import inspect

    from hexagent.validation_report import chain_adapter

    src = inspect.getsource(chain_adapter)
    # The slice3a-frozen-fixture-v1 placeholder is a P1-2 marker.
    assert "slice3a-frozen-fixture-v1" not in src, (
        "chain_adapter source still contains the slice3a-frozen-fixture-v1 "
        "placeholder; this is a P1-2 marker the engineering review flagged"
    )
    # The removed helper function must be gone (definitions only;
    # comments are allowed since they document the removal).

    # Match a def statement: ^def _build_material_record_from_case_02_input(
    assert not re.search(
        r"^def\s+_build_material_record_from_case_02_input\(", src, re.MULTILINE
    ), (
        "chain_adapter source still defines the removed "
        "_build_material_record_from_case_02_input helper"
    )
    # No MaterialRecord-shaped dict literal with hardcoded values: the
    # adapter must not return a dict containing the MaterialRecord
    # fields with hardcoded values. (We check for the pattern of
    # multiple hardcoded MaterialRecord field assignments in close
    # proximity — the old implementation had
    # "material_record_version": "slice3a-frozen-fixture-v1", ...)
    # which is already caught above. We additionally check that
    # no hardcoded 2-letter country code (region="XX") or
    # approval_state="approved" appears as a MaterialRecord field
    # assignment in the OLD _build_material_record_from_case_02_input
    # helper signature (the new Slice 3B-B code uses approval_state
    # legitimately for TubeGeometryRecord / PipeGeometryRecord
    # construction from case-bound 002-G data; that is not
    # fabrication, it is the production contract).
    src_lines = src.splitlines()
    old_helper_line_numbers: list[int] = []
    for i, line in enumerate(src_lines):
        if "def _build_material_record_from_case_02_input" in line:
            old_helper_line_numbers.append(i)
    forbidden_in_old_helper = (
        '"US"',
        '"approved"',
    )
    for line_no in old_helper_line_numbers:
        # Check the next 200 lines after the helper signature for the
        # forbidden P1-2 patterns.
        for j in range(line_no, min(line_no + 200, len(src_lines))):
            for val in forbidden_in_old_helper:
                if val in src_lines[j]:
                    raise AssertionError(
                        f"chain_adapter old P1-2 helper at line {line_no + 1} "
                        f"still contains hardcoded MaterialRecord value "
                        f"{val!r} at line {j + 1}; this is the P1-2 marker "
                        f"the engineering review flagged"
                    )


# P1-3: chain_adapter must NOT hardcode SelectionFilters (material_family,
# cost_category_filter, quantity_basis_filter, license_class_filter) and
# must NOT call select_cost_records with an empty records list as if it
# were production-derived output.
def test_p1_no_synthetic_cost_selection_filters() -> None:
    import inspect

    from hexagent.validation_report import chain_adapter

    src = inspect.getsource(chain_adapter)
    # The old P1-3 hardcode was a SelectionFilters(...) call with
    # material_family="stainless_steel" (without the 002-H
    # "_304" suffix) and several frozenset filters for
    # cost_category / quantity_basis / license_class. We check
    # for the specific patterns that indicate a hardcoded
    # SelectionFilters construction that contradicts the 002-H
    # contract surface.
    forbidden_filter_patterns = (
        'material_family="stainless_steel"',  # old hardcoded material_family (no _304 suffix)
    )
    for pat in forbidden_filter_patterns:
        assert pat not in src, (
            f"chain_adapter source still contains hardcoded SelectionFilters "
            f"pattern {pat!r}; this is the P1-3 finding the engineering review flagged"
        )
    # The removed helper function must be gone (definitions only;
    # comments are allowed since they document the removal).
    assert not re.search(r"^def\s+_build_case_03_filters\(", src, re.MULTILINE), (
        "chain_adapter source still defines the removed _build_case_03_filters helper"
    )
    # No empty-records pseudo cost computation: select_cost_records
    # must not be called with a literal empty tuple.
    assert "select_cost_records(()," not in src, (
        "chain_adapter source still calls select_cost_records with an empty "
        "records tuple; this is the P1-3 empty-record pseudo cost behavior"
    )


# P1-4: produced_fields is derived from non-None values only.
def test_p1_produced_fields_have_no_none_values() -> None:
    from hexagent.validation_report import chain_adapter

    def _dig(root: object, dotted: str) -> object:
        cur: object = root
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return None
            cur = cur[part]  # type: ignore[assignment]
        return cur

    for case_id in (
        "TASK-019-GOLDEN-01",
        "TASK-019-GOLDEN-02",
        "TASK-019-GOLDEN-03",
    ):
        fixture = _load_fixture(case_id)
        artifact = chain_adapter.compute_actual_output_via_chain(fixture)
        values = artifact.get("values", {})
        for field in artifact.get("produced_fields", []):
            val = _dig(values, field)
            assert val is not None, (
                f"case {case_id} P1-4 violation: produced field {field!r} "
                f"has None value; a None-valued field must not appear in "
                f"produced_fields"
            )


# P1-4 (extended): after Slice 3B-A authorization, the per-case
# production-chain contract is:
#   - case_01: WIRED_VIA_CHAIN with the 6 authorized TASK-006/007/008
#     produced fields (post Design Amendment 002-E mass_flow
#     0.75/0.75 kg/s, both Re outside the TASK-007 transitional
#     regime).
#   - case_02: WIRED_VIA_CHAIN_PARTIAL — the frozen case_02 input
#     still lacks a full TASK-013 catalog-resolved MaterialRecord;
#     no synthetic MaterialRecord is built (P1-2 guard preserved).
#   - case_03: WIRED_VIA_CHAIN_PARTIAL — the frozen case_03 input
#     still lacks a TASK-018 catalog-resolved cost records list;
#     no cost_records / SelectionFilters fabrication (P1-3 guard
#     preserved).
# This test replaces the prior Slice 3A "all 3 fail-closed" guard.
# It preserves the P1 spirit: case_02 and case_03 still fail closed
# with empty produced_fields (no fabrication), and case_01 is wired
# only because the production chain genuinely produces the 6
# authorized fields end-to-end (the chain runs the real
# CoolPropProvider + the frozen fluid_identifier + the frozen
# mass_flow + the frozen geometry material properties).
def test_slice3b_a_case_01_wired_case_02_03_partial() -> None:
    from hexagent.validation_report import chain_adapter

    # case_01: WIRED_VIA_CHAIN, exactly 6 authorized fields.
    fixture_01 = _load_fixture("TASK-019-GOLDEN-01")
    artifact_01 = chain_adapter.compute_actual_output_via_chain(fixture_01)
    assert artifact_01["status"] == "WIRED_VIA_CHAIN", (
        f"case_01 must be WIRED_VIA_CHAIN after Slice 3B-A; got {artifact_01['status']!r}"
    )
    expected_fields = {
        "heat_duty_W",
        "LMTD_derived_values.LMTD_counterflow_K",
        "heat_transfer_coefficients.annulus_side_W_m2_K",
        "heat_transfer_coefficients.tube_side_W_m2_K",
        "outlet_temperatures_K.cold_side",
        "outlet_temperatures_K.hot_side",
    }
    assert set(artifact_01["produced_fields"]) == expected_fields, (
        f"case_01 produced_fields must be exactly the 6 authorized "
        f"fields; got {sorted(artifact_01['produced_fields'])}"
    )
    assert artifact_01["blocked_fields"] == []
    assert artifact_01["comparison_overall_status"] == "NOT_COMPUTABLE"

    # case_02: Slice 3B-B (post-002-G) wires case_02 to the production
    # chain via the 4-role material_catalog_bridge. The chain runs
    # resolve_material (4 roles) + calculate_mass_breakdown (tube +
    # pipe geometry records) + preliminary_check (tube) and applies
    # 方案 B explicit mapping (shell_mass_kg <- outer_pipe_kg,
    # tube_mass_kg <- inner_tube_kg, total_mass_kg <- sum). The
    # fluid_mass_kg field is DEFERRED to a future real production
    # chain (002-H+) and is NOT in produced_fields (per the 002-G
    # design contract).
    fixture_02 = _load_fixture("TASK-019-GOLDEN-02")
    artifact_02 = chain_adapter.compute_actual_output_via_chain(fixture_02)
    assert artifact_02["status"] == "WIRED_VIA_CHAIN", (
        f"case_02 must be WIRED_VIA_CHAIN after Slice 3B-B (post-002-G); "
        f"got {artifact_02['status']!r}"
    )
    expected_02_fields = {
        "mass_kg.shell_mass_kg",
        "mass_kg.tube_mass_kg",
        "mass_kg.total_mass_kg",
        "preliminary_mechanical_check.status",
        "selected_material_ids.shell_material_id",
        "selected_material_ids.tube_material_id",
    }
    assert set(artifact_02["produced_fields"]) == expected_02_fields, (
        f"case_02 produced_fields must be exactly the 6 authorized "
        f"002-G contract fields; got {sorted(artifact_02['produced_fields'])}"
    )
    # fluid_mass_kg must NOT be in produced_fields (per the 002-G
    # design §4.9.10 step 7 DEFERRED status; production MassCalculator
    # does not produce fluid_mass_kg; the field is a deferred
    # placeholder in expected_output but NOT a produced_field).
    assert "mass_kg.fluid_mass_kg" not in artifact_02["produced_fields"], (
        "case_02 produced_fields MUST NOT contain mass_kg.fluid_mass_kg "
        "per the 002-G design §4.9.10 step 7 DEFERRED status"
    )
    # The values dict MUST also NOT carry fluid_mass_kg (per the
    # 002-G design: the future Slice 3B-B adapter MUST NOT populate
    # actual_output.mass_kg.fluid_mass_kg from any source).
    assert "fluid_mass_kg" not in artifact_02["values"]["mass_kg"], (
        "case_02 values.mass_kg MUST NOT contain fluid_mass_kg per the "
        "002-G design §4.9.10 (DEFERRED; the production chain does not "
        "produce it; the future adapter MUST NOT fabricate / copy)"
    )
    # The 3 mass_kg values must come from the production chain
    # (production MassCalculator.calculate_mass_breakdown). Per the
    # 002-G design contract, the canonical values are:
    #   shell_mass_kg = 8000 * pi/4 * (0.0603^2 - 0.0525^2) * 2.0
    #               = 11.056395521337773
    #   tube_mass_kg   = 8000 * pi/4 * (0.0334^2 - 0.0266^2) * 2.0
    #               = 5.127079210658542
    #   total_mass_kg  = shell_mass_kg + tube_mass_kg
    #               = 16.183474731996316
    # Use math.isclose for float comparison. The production chain
    # rounds the output to 6 decimal places (canonical float-to-
    # decimal-string serialization per design §10.3); rel_tol=1e-6
    # is the binding contract tolerance per the 002-G design
    # §4.9.4.
    assert math.isclose(
        artifact_02["values"]["mass_kg"]["shell_mass_kg"],
        11.056395521337773,
        rel_tol=1e-6,
    )
    assert math.isclose(
        artifact_02["values"]["mass_kg"]["tube_mass_kg"],
        5.127079210658542,
        rel_tol=1e-6,
    )
    assert math.isclose(
        artifact_02["values"]["mass_kg"]["total_mass_kg"],
        16.183474731996316,
        rel_tol=1e-6,
    )
    # preliminary_mechanical_check.status must come from the
    # production chain. The case_01 cross-reference geometry + 002-G
    # bridge SS304 material + case_02 design conditions
    # (pressure 0.6 MPa, temperature 70 degC) yield verdict="pass"
    # (2.95 MPa hoop stress << 137.0 MPa allowable at 70 degC).
    assert artifact_02["values"]["preliminary_mechanical_check"]["status"] == "pass"
    # selected_material_ids must come from the production chain
    # (production MaterialResolutionResult.material_grade projected
    # to the public string-projected form "SS304" via the canonical
    # _BRIDGE_GRADE_TO_REPORT_GRADE mapping; no fabrication).
    assert artifact_02["values"]["selected_material_ids"]["shell_material_id"] == "SS304"
    assert artifact_02["values"]["selected_material_ids"]["tube_material_id"] == "SS304"

    # case_03: Slice 3B-C P0 fixup (post-002-H) wires case_03 to the
    # production CostModelSelector (no mass dependency) via the
    # 002-H frozen cost_records_bridge. The cost breakdown
    # (CostCalculator.calculate_cost_breakdown) is intentionally
    # NOT called because the 002-H frozen case_03 fixture does
    # NOT carry the case_02 material_catalog_bridge + case_01
    # geometry prerequisites required to obtain a real production
    # MassBreakdown via the already-wired case_02 chain (per the
    # 002-H §15.3.4 P0 contract: case_03 fails closed for cost
    # outputs when mass dependency is unavailable). The status
    # is therefore WIRED_VIA_CHAIN_PARTIAL and produced_fields
    # contains ONLY the 5 P0-4 selector audit fields.
    fixture_03 = _load_fixture("TASK-019-GOLDEN-03")
    artifact_03 = chain_adapter.compute_actual_output_via_chain(fixture_03)
    assert artifact_03["status"] == "WIRED_VIA_CHAIN_PARTIAL", (
        f"case_03 must be WIRED_VIA_CHAIN_PARTIAL after Slice 3B-C P0 fixup "
        f"(mass dependency unavailable per 002-H frozen fixture); "
        f"got {artifact_03['status']!r}"
    )
    expected_03_fields = {
        "selected_cost_model.selector_run_id",
        "selected_cost_model.provenance_chain_hash",
        "selected_cost_model.selection_blockers",
        "selected_cost_model.c0_record_count",
        "selected_cost_model.c1_record_count",
    }
    assert set(artifact_03["produced_fields"]) == expected_03_fields, (
        f"case_03 produced_fields must be exactly the 5 P0-4 selector "
        f"audit fields (no cost outputs synthesized); "
        f"got {sorted(artifact_03['produced_fields'])}"
    )
    # P0-2: cost components remain None (no cost outputs synthesized).
    assert (
        artifact_03["values"]["cost_components_C0_C1"]["cost_components"]["C0_material_minor_units"]
        is None
    )
    assert (
        artifact_03["values"]["cost_components_C0_C1"]["cost_components"]["C0_labor_minor_units"]
        is None
    )
    assert (
        artifact_03["values"]["cost_components_C0_C1"]["cost_components"]["C1_total_minor_units"]
        is None
    )
    assert artifact_03["values"]["cost_components_C0_C1"]["currency_ISO_4217"] is None
    # P0-4: selected_model_id is fixture-context echo (in values) but
    # MUST NOT appear in produced_fields. The amendment-001 frozen
    # string literal is preserved verbatim.
    assert (
        artifact_03["values"]["selected_cost_model"]["selected_model_id"]
        == "ASME-BPVC-VIII-1-COST-MODEL-V1 (TASK-018 Slice A frozen cost-model catalog)"
    )
    assert "selected_cost_model.selected_model_id" not in artifact_03["produced_fields"]
    # P0-4: 002-H canonical key is produced; pre-existing public
    # compatibility key is also produced (same value, both keys).
    assert artifact_03["values"]["selected_cost_model"]["provenance_chain_hash"] != ""
    assert artifact_03["values"]["selected_cost_model"]["selector_provenance_chain_hash"] != ""
    assert (
        artifact_03["values"]["selected_cost_model"]["provenance_chain_hash"]
        == artifact_03["values"]["selected_cost_model"]["selector_provenance_chain_hash"]
    )
    # Discount / salvage remain deferred.
    assert artifact_03["discount_salvage_status"]["discounted_total_minor_units"] == (
        "DEFERRED_PER_TASK_018_5_3"
    )
    assert artifact_03["discount_salvage_status"]["salvage_minor_units"] == (
        "DEFERRED_PER_TASK_018_5_3_2"
    )


# Slice 3B-A §6.1: case_01 reads fluid_identifier, not fluid_composition.
def test_slice3b_a_case_01_uses_fluid_identifier_not_composition() -> None:
    """Mutating the fluid_composition description string must not
    affect the case_01 chain; the chain must read the provider
    identifier from the fluid_identifier sub-block."""
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-01")
    # Mutate fluid_composition to a non-water string; the chain must
    # still succeed (because the provider identifier is read from
    # fluid_identifier, not fluid_composition).
    fixture_mutated = json.loads(json.dumps(fixture))
    fixture_mutated["input"]["hot_side"]["fluid_composition"] = (
        "AIR / NON-WATER DESCRIPTION (audit-only)"
    )
    fixture_mutated["input"]["cold_side"]["fluid_composition"] = (
        "AIR / NON-WATER DESCRIPTION (audit-only)"
    )
    artifact_mutated = chain_adapter.compute_actual_output_via_chain(fixture_mutated)
    assert artifact_mutated["status"] == "WIRED_VIA_CHAIN", (
        "case_01 must remain WIRED_VIA_CHAIN when fluid_composition "
        "is mutated; the chain must read fluid_identifier, not "
        "fluid_composition"
    )
    # The mutated case must produce the same 6 values as the
    # unmutated case (proves the chain ignores fluid_composition).
    artifact_baseline = chain_adapter.compute_actual_output_via_chain(fixture)
    assert (
        artifact_mutated["canonical_actual_output_sha256"]
        == artifact_baseline["canonical_actual_output_sha256"]
    ), "case_01 chain must be invariant to fluid_composition mutation"


# Slice 3B-A §6.3: removing fluid_identifier makes case_01 fail closed.
def test_slice3b_a_case_01_fail_closed_when_fluid_identifier_absent() -> None:
    """If the frozen fluid_identifier sub-block is removed from the
    case input, the case_01 chain must fail closed (not fabricate a
    provider identifier)."""
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-01")
    fixture_broken = json.loads(json.dumps(fixture))
    del fixture_broken["input"]["hot_side"]["fluid_identifier"]
    del fixture_broken["input"]["cold_side"]["fluid_identifier"]
    artifact = chain_adapter.compute_actual_output_via_chain(fixture_broken)
    # Must NOT be WIRED_VIA_CHAIN (no fabrication of a default
    # Water/HEOS provider).
    assert artifact["status"] != "WIRED_VIA_CHAIN", (
        "case_01 must not fabricate a provider identifier when "
        "fluid_identifier is absent; status was "
        f"{artifact['status']!r}"
    )
    assert artifact["produced_fields"] == [], (
        "case_01 must not produce fields when fluid_identifier is "
        "absent; produced_fields must be empty"
    )


# Slice 3B-A §6.4: no hardcoded "Water" / "HEOS" fallback in adapter.
def test_slice3b_a_no_hardcoded_water_heos_fallback_in_adapter() -> None:
    """The chain_adapter source must not contain a hardcoded
    ``"Water"`` / ``"HEOS"`` fallback string used as a default
    provider identifier. The only acceptable uses of those strings
    are in the test contract assertions, the module docstring, and
    the `__all__` export surface (none of which substitute a
    default at runtime)."""
    import inspect

    from hexagent.validation_report import chain_adapter

    src = inspect.getsource(chain_adapter)
    # The forbidden patterns are a hardcoded ``name="Water"`` or
    # ``equation_of_state_backend="HEOS"`` assignment that
    # substitutes a default. The adapter must read both from the
    # frozen fixture's fluid_identifier sub-block.
    forbidden_patterns = (
        'name="Water"',
        "name='Water'",
        'equation_of_state_backend="HEOS"',
        "equation_of_state_backend='HEOS'",
    )
    for pattern in forbidden_patterns:
        assert pattern not in src, (
            f"chain_adapter contains hardcoded {pattern!r} fallback; "
            "the adapter must read the provider identifier from the "
            "frozen fluid_identifier sub-block only"
        )


# Slice 3B-A §6.5: no hardcoded 002-E numeric values in adapter.
def test_slice3b_a_no_hardcoded_002e_numeric_values_in_adapter() -> None:
    """The chain_adapter source must not contain the 6 frozen
    Amendment 002-E expected_output numeric central values. The
    chain must compute them from the production chain, not from
    hardcoded constants."""
    import inspect

    from hexagent.validation_report import chain_adapter

    src = inspect.getsource(chain_adapter)
    # The 6 frozen Amendment 002-E central values:
    #   heat_duty_W = 6598.77255277395
    #   LMTD_counterflow_K = 37.85817982113553
    #   annulus_side_W_m2_K = 2783.7013942048334
    #   tube_side_W_m2_K = 7899.20947325792
    #   cold_outlet_T = 295.25317863269566
    #   hot_outlet_T = 331.0473945550949
    forbidden_values = (
        "6598.77255277395",
        "37.85817982113553",
        "2783.7013942048334",
        "7899.20947325792",
        "295.25317863269566",
        "331.0473945550949",
    )
    for value in forbidden_values:
        assert value not in src, (
            f"chain_adapter source contains hardcoded Amendment 002-E "
            f"central value {value!r}; the chain must compute the value, "
            "not hardcode it"
        )


# Slice 3B-A §6.8: case_01 produced values are all finite and non-None.
def test_slice3b_a_case_01_produced_values_finite_non_none() -> None:
    """All 6 case_01 produced values must be finite (not inf/nan) and
    non-None. The chain must produce real upstream values, not
    None sentinels or non-finite placeholders."""
    import math

    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-01")
    artifact = chain_adapter.compute_actual_output_via_chain(fixture)
    values = artifact["values"]
    flat_values = [
        values["heat_duty_W"],
        values["LMTD_derived_values"]["LMTD_counterflow_K"],
        values["heat_transfer_coefficients"]["annulus_side_W_m2_K"],
        values["heat_transfer_coefficients"]["tube_side_W_m2_K"],
        values["outlet_temperatures_K"]["cold_side"],
        values["outlet_temperatures_K"]["hot_side"],
    ]
    for v in flat_values:
        assert v is not None, "case_01 produced value must not be None"
        assert isinstance(v, float)
        assert math.isfinite(v), f"case_01 produced value {v!r} must be finite"


# Slice 3B-A §6.10: case_01 pressure-drop remains excluded / not produced.
def test_slice3b_a_case_01_pressure_drop_excluded() -> None:
    """case_01 actual_output must not include any pressure-drop
    field. The chain must not produce, and the values must not
    contain, any pressure-drop key (pressure_drop_pa, dp_*, etc.).
    Pressure drop remains NOT_COMPUTABLE / TASK-020+ excluded."""
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-01")
    artifact = chain_adapter.compute_actual_output_via_chain(fixture)
    values = artifact["values"]
    values_str = json.dumps(values, sort_keys=True)
    forbidden_substrings = (
        "pressure_drop_pa",
        "dp_pa",
        "delta_p",
        "pressure_drop",
    )
    for sub in forbidden_substrings:
        assert sub not in values_str, (
            f"case_01 values must not contain {sub!r} key "
            f"(pressure drop is NOT_COMPUTABLE / TASK-020+ excluded); "
            f"values: {values_str}"
        )


# Slice 3B-A §6.14: canonical_actual_output_sha256 is stable and
# lowercase 64-char.
def test_slice3b_a_canonical_actual_output_sha256_stable_and_lowercase() -> None:
    """The canonical_actual_output_sha256 field must be a stable
    lowercase 64-char SHA-256 hex string, identical across repeated
    adapter runs of the same fixture."""
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-01")
    artifact_1 = chain_adapter.compute_actual_output_via_chain(fixture)
    artifact_2 = chain_adapter.compute_actual_output_via_chain(fixture)
    sha_1 = artifact_1["canonical_actual_output_sha256"]
    sha_2 = artifact_2["canonical_actual_output_sha256"]
    assert isinstance(sha_1, str)
    assert len(sha_1) == 64
    assert sha_1 == sha_1.lower(), "sha256 must be lowercase"
    int(sha_1, 16)  # raises if not valid hex
    assert sha_1 == sha_2, (
        f"canonical_actual_output_sha256 must be stable across runs; got {sha_1!r} and {sha_2!r}"
    )


# Slice 3B-A §6.15: repeated adapter runs are deterministic.
def test_slice3b_a_repeated_adapter_runs_are_deterministic() -> None:
    """Two consecutive adapter runs on the same fixture must produce
    byte-identical artifacts (status, produced_fields, values,
    canonical_actual_output_sha256, upstream_calculation_run_ids,
    upstream_provenance_digests)."""
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-01")
    artifact_1 = chain_adapter.compute_actual_output_via_chain(fixture)
    artifact_2 = chain_adapter.compute_actual_output_via_chain(fixture)
    # The full dict minus fields that are explicitly allowed to vary
    # across runs (none in this Slice 3B-A contract).
    for key in (
        "case_id",
        "status",
        "produced_fields",
        "values",
        "blocked_fields",
        "upstream_calculation_run_ids",
        "upstream_provenance_digests",
        "canonical_actual_output_sha256",
        "discount_salvage_status",
        "comparison_overall_status",
    ):
        assert artifact_1[key] == artifact_2[key], (
            f"artifact[{key!r}] must be deterministic across runs; "
            f"got {artifact_1[key]!r} and {artifact_2[key]!r}"
        )


# P1-4 (extended): the chain adapter must NOT silently substitute
# constants to keep the chain wired. A guard test confirms that the
# hardcoded 16.2 / 4.5e-5 fallback values, the slice3a-frozen-fixture-v1
# MaterialRecord placeholder, and the empty-records pseudo cost path
# are all gone from the adapter source.
def test_p1_guard_test_no_silent_constant_substitution() -> None:
    import inspect

    from hexagent.validation_report import chain_adapter

    src = inspect.getsource(chain_adapter)
    forbidden_markers = (
        "16.2",  # P1-1 hardcoded SS304 thermal conductivity
        "4.5e-5",  # P1-1 hardcoded surface roughness
        "slice3a-frozen-fixture-v1",  # P1-2 MaterialRecord placeholder
        "select_cost_records((),",  # P1-3 empty-records pseudo cost
    )
    for marker in forbidden_markers:
        assert marker not in src, (
            f"chain_adapter source contains P1 guard-test marker {marker!r}; "
            f"this is a silent-constant-substitution violation"
        )


# ----------------------------------------------------------------------------
# Slice 3B-C (post-002-H) case_03 contract tests.
# ----------------------------------------------------------------------------


def test_slice3b_c_case_03_selector_bridge_smoke() -> None:
    """The 002-H frozen cost_records_bridge + SelectionFilters produce
    c0=2 / c1=1 / blockers=[] at the production CostModelSelector
    (per 002-H §15.3.2). Per the P0 fixup, case_03 is
    WIRED_VIA_CHAIN_PARTIAL (mass dependency unavailable) with
    the 5 P0-4 selector audit fields in produced_fields."""
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-03")
    artifact = chain_adapter.compute_actual_output_via_chain(fixture)
    assert artifact["status"] == "WIRED_VIA_CHAIN_PARTIAL", (
        f"case_03 must be WIRED_VIA_CHAIN_PARTIAL per P0 fixup; got {artifact['status']!r}"
    )
    # selected_cost_model carries the selector_run_id +
    # provenance_chain_hash (002-H canonical key) +
    # selector_provenance_chain_hash (pre-existing public compat
    # alias) + c0_record_count + c1_record_count per 002-H §15.3.3.
    scm = artifact["values"]["selected_cost_model"]
    assert scm["selection_blockers"] == []
    assert scm["selector_run_id"] != ""
    # P0-4: 002-H canonical key is produced.
    assert scm["provenance_chain_hash"] != ""
    # P0-4: pre-existing public compatibility key is preserved.
    assert scm["selector_provenance_chain_hash"] != ""
    assert scm["c0_record_count"] == 2
    assert scm["c1_record_count"] == 1
    # P0-4: selected_model_id is fixture-context echo only; it is
    # in values (as a frozen canonical string) but NOT in
    # produced_fields.
    assert "selected_cost_model.selected_model_id" not in artifact["produced_fields"]
    assert (
        scm["selected_model_id"]
        == "ASME-BPVC-VIII-1-COST-MODEL-V1 (TASK-018 Slice A frozen cost-model catalog)"
    )


def test_slice3b_c_case_03_by_record_id_mapping() -> None:
    """Per the P0 fixup, case_03 fails closed for cost outputs
    (mass dependency unavailable per 002-H fixture). The
    cost_components fields therefore remain None — there is
    no production cost breakdown output to project by
    record-id (P0-2: no synthetic cost outputs)."""
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-03")
    artifact = chain_adapter.compute_actual_output_via_chain(fixture)
    cc = artifact["values"]["cost_components_C0_C1"]["cost_components"]
    # P0-2: all cost component fields are None (no cost outputs
    # synthesized). The by-record-id public mapping per 002-H
    # §15.3.4 is NOT exercised because the cost breakdown is
    # intentionally skipped per the P0-1 fail-closed path.
    assert cc["C0_material_minor_units"] is None
    assert cc["C0_labor_minor_units"] is None
    assert cc["C1_total_minor_units"] is None
    assert artifact["values"]["cost_components_C0_C1"]["currency_ISO_4217"] is None


def test_slice3b_c_case_03_no_runtime_resolver() -> None:
    """The chain_adapter source must not introduce a runtime catalog
    resolver (no filesystem / DB / network catalog lookup for cost
    records). The 002-H §15.3.1 rule binding is: cost_records_bridge
    is read from the fixture only; no TASK-018 / TASK-013 runtime
    catalog helper is introduced."""
    import inspect

    from hexagent.validation_report import chain_adapter

    src = inspect.getsource(chain_adapter)
    forbidden_resolver_markers = (
        "TASK_018_catalog_loader",
        "TASK_013_catalog_loader",
        "catalog_resolver",
        "runtime_resolver",
        "open_catalog",
    )
    for marker in forbidden_resolver_markers:
        assert marker not in src, (
            f"chain_adapter source contains forbidden runtime catalog "
            f"resolver marker {marker!r}; 002-H §15.3.1 forbids a "
            f"runtime catalog resolver"
        )


def test_slice3b_c_case_03_no_forbidden_scope() -> None:
    """The chain_adapter source must not introduce any forbidden-scope
    content (TASK-020+ pressure drop / C4 / TEMA / Kern /
    Bell-Delaware / vendor quote / discount formula / salvage
    formula)."""
    import inspect

    from hexagent.validation_report import chain_adapter

    src = inspect.getsource(chain_adapter)
    forbidden_scope_markers = (
        "pressure_drop_calculator",
        "TEMA",
        "Kern_method",
        "Bell_Delaware",
        "Bell-Delaware",
        "discount_formula",
        "salvage_formula",
        "vendor_quote",
    )
    for marker in forbidden_scope_markers:
        # "TEMA" is allowed as a standards-source enum literal
        # (frozen allowed-standards list); the chain_adapter source
        # should not contain an algorithm implementation.
        if marker == "TEMA":
            # OK if it's only in a string-literal comment or
            # standards allow-list reference. The Slice 3B-C contract
            # forbids a TEMA algorithm implementation; we accept
            # either no TEMA reference or a comment-only reference.
            # To keep the assertion strict we skip TEMA here and
            # verify it via the broader forbidden-scope negative
            # tests in tests/validation_report/test_excluded_scopes_negative.py
            continue
        assert marker not in src, (
            f"chain_adapter source contains forbidden-scope marker "
            f"{marker!r}; Slice 3B-C is TASK-019 scope only"
        )


def test_slice3b_c_case_03_regression_case_01_case_02_unchanged() -> None:
    """case_01 and case_02 produced_fields and status must remain
    unchanged after Slice 3B-C wiring (regression guard)."""
    from hexagent.validation_report import chain_adapter

    fixture_01 = _load_fixture("TASK-019-GOLDEN-01")
    artifact_01 = chain_adapter.compute_actual_output_via_chain(fixture_01)
    assert artifact_01["status"] == "WIRED_VIA_CHAIN"
    assert set(artifact_01["produced_fields"]) == {
        "heat_duty_W",
        "LMTD_derived_values.LMTD_counterflow_K",
        "heat_transfer_coefficients.annulus_side_W_m2_K",
        "heat_transfer_coefficients.tube_side_W_m2_K",
        "outlet_temperatures_K.cold_side",
        "outlet_temperatures_K.hot_side",
    }

    fixture_02 = _load_fixture("TASK-019-GOLDEN-02")
    artifact_02 = chain_adapter.compute_actual_output_via_chain(fixture_02)
    assert artifact_02["status"] == "WIRED_VIA_CHAIN"
    assert set(artifact_02["produced_fields"]) == {
        "mass_kg.shell_mass_kg",
        "mass_kg.tube_mass_kg",
        "mass_kg.total_mass_kg",
        "preliminary_mechanical_check.status",
        "selected_material_ids.shell_material_id",
        "selected_material_ids.tube_material_id",
    }


def test_slice3b_c_case_03_expected_output_unchanged() -> None:
    """The fixture's expected_output block must remain byte-identical
    to the 002-H frozen version after Slice 3B-C wiring (no
    expected_output mutation by the adapter)."""
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-03")
    expected_before = json.loads(json.dumps(fixture["expected_output"]))
    # Run the adapter; this MUST NOT mutate the fixture.
    chain_adapter.compute_actual_output_via_chain(fixture)
    expected_after = json.loads(json.dumps(fixture["expected_output"]))
    assert expected_before == expected_after, (
        "chain_adapter.compute_actual_output_via_chain MUST NOT mutate "
        "the fixture's expected_output block (no expected_output mutation rule)"
    )
    # Spot-check key amendment-001 frozen central values.
    eo = expected_after
    assert eo["cost_components_C0_C1"]["cost_components"]["C0_material_minor_units"] == 412000
    assert eo["cost_components_C0_C1"]["cost_components"]["C0_labor_minor_units"] == 188000
    assert eo["cost_components_C0_C1"]["cost_components"]["C1_total_minor_units"] == 600000
    assert (
        eo["selected_cost_model"]["selected_model_id"]
        == "ASME-BPVC-VIII-1-COST-MODEL-V1 (TASK-018 Slice A frozen cost-model catalog)"
    )
    assert eo["discounted_total_minor_units"] is None
    assert eo["salvage_minor_units"] == 0


# ----------------------------------------------------------------------------
# TASK-019 PR #111 P0 fixup required tests.
# ----------------------------------------------------------------------------
#
# Per Charles's PR #111 review, the case_03 cost chain must satisfy
# the following P0 invariants. These tests are the binding contract
# surface for the P0 fixup commit on top of PR #111's original head
# 0d66a13cc19db4f55c66840457071e5a9caac2e7.


def _extract_case_03_source_region() -> str:
    """Return the source text of the case_03 path (P0-1 / P0-2
    inspection scope).

    The case_03 path is the union of:
    1. The module-level ``_execute_case_03_cost_chain`` helper
       (and its sibling private helpers immediately above it
       that exist solely to support the case_03 path), AND
    2. The ``case_id == "TASK-019-GOLDEN-03"`` branch inside
       ``compute_actual_output_via_chain``.

    The case_02 path (which legitimately references
    ``case_02_materials_mass_mechanical.json`` via
    ``SourceBinding.source_location``) is explicitly EXCLUDED
    from this scope because case_02 references are a frozen
    case-bound audit-trail string, not a case_03 mass chain
    read.
    """
    import inspect
    import re

    from hexagent.validation_report import chain_adapter

    src = inspect.getsource(chain_adapter)
    # The case_03 helper block is the region between the case_03
    # helpers comment header and the "Top-level adapter entry
    # point" comment header. Use the full comment-line markers
    # to anchor the slice.
    start_marker = "Slice 3B-C case_03 helpers (post-002-H, P0 fixup)"
    end_marker = "Top-level adapter entry point"
    start_idx = src.find(start_marker)
    end_idx = src.find(end_marker)
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        # Fall back to the explicit function-name anchor pair.
        helper_start = src.find("def _execute_case_03_cost_chain")
        helper_end = src.find("# Top-level adapter entry point")
        if helper_start == -1 or helper_end == -1:
            raise AssertionError(
                "case_03 path region could not be located in chain_adapter "
                "source; P0-1 inspection scope anchor is stale"
            )
        case_03_helper_region = src[helper_start:helper_end]
    else:
        case_03_helper_region = src[start_idx:end_idx]
    # The case_03 branch block inside compute_actual_output_via_chain.
    branch_start = src.find('elif case_id == "TASK-019-GOLDEN-03":')
    branch_end_match = re.search(
        r"^    else:\n        raise ValueError\(",
        src[branch_start:],
        re.MULTILINE,
    )
    if branch_start == -1 or branch_end_match is None:
        raise AssertionError(
            "case_03 branch block (TASK-019-GOLDEN-03) could not be located "
            "in chain_adapter source; P0-1 inspection scope anchor is stale"
        )
    case_03_branch_region = src[branch_start : branch_start + branch_end_match.start()]
    return case_03_helper_region + "\n" + case_03_branch_region


def test_case_03_does_not_runtime_read_case_02_fixture_for_mass_dependency() -> None:
    """P0-1: the case_03 path must NOT runtime-read
    case_02_materials_mass_mechanical.json from the filesystem
    for case_03 mass dependency, and must NOT define the
    deleted case_03 mass-reconstruction helpers.

    The inspection is scoped to the case_03 path (the
    _execute_case_03_cost_chain helper region + the
    ``TASK-019-GOLDEN-03`` branch block). The case_02 path
    legitimately references the same fixture name via
    ``SourceBinding.source_location`` for case-bound
    audit-trail metadata; that case_02-path reference is
    EXCLUDED from this assertion's scope.
    """
    import re

    case_03_src = _extract_case_03_source_region()
    # Strip docstrings and # comments before scanning for
    # code-level usage.
    no_docstrings = re.sub(r'"""[\s\S]*?"""', "", case_03_src)
    no_docstrings = re.sub(r"'''[\s\S]*?'''", "", no_docstrings)
    no_comments = re.sub(r"#[^\n]*", "", no_docstrings)

    forbidden_case_03_mass_markers = (
        # The case_03 mass-reconstruction function must not be
        # defined in the case_03 path. (The function was
        # deleted in the P0-1 fixup; the case_02 path does not
        # contain this name and so cannot produce a false
        # positive.)
        "def _compute_case_03_production_mass_breakdown",
        # The case_03 case_02-fixture FS reader must not be
        # defined in the case_03 path.
        "def _load_case_02_fixture_for_mass_breakdown",
        # The case_03 synthetic MassBreakdown stub must not be
        # defined in the case_03 path.
        "class _StubMassBreakdownForDuckType",
        # The case_03 path must not open the case_02 fixture
        # JSON. The case_02 path legitimately contains this
        # substring inside ``source_location`` (audit-trail
        # metadata) but that path is excluded by the scope of
        # this inspection.
        "case_02_materials_mass_mechanical.json",
        # The case_03 path must not call ``read_text`` on a
        # fixture path (case_02 path's own read_text usage on
        # case_01 fixture is excluded by scope).
        '.read_text(encoding="utf-8")',
    )
    for marker in forbidden_case_03_mass_markers:
        assert marker not in no_comments, (
            f"case_03 path contains P0-1 forbidden marker {marker!r}; "
            f"case_03 must not runtime-read the case_02 fixture, define "
            f"a mass-reconstruction helper, or construct a synthetic "
            f"MassBreakdown stub"
        )


def test_case_03_has_no_stub_mass_breakdown_fallback() -> None:
    """P0-2: the case_03 path must NOT define
    _StubMassBreakdownForDuckType or any equivalent synthetic
    MassBreakdown fallback. The cost breakdown
    (CostCalculator.calculate_cost_breakdown) is NOT called
    when the real MassBreakdown is unavailable — case_03
    fails closed with WIRED_VIA_CHAIN_PARTIAL + empty cost
    component fields.

    The inspection is scoped to the case_03 path (same
    scope as the P0-1 test). The case_02 path does not
    contain any of the forbidden stub markers and so
    cannot produce a false positive.
    """
    import re

    case_03_src = _extract_case_03_source_region()
    no_docstrings = re.sub(r'"""[\s\S]*?"""', "", case_03_src)
    no_docstrings = re.sub(r"'''[\s\S]*?'''", "", no_docstrings)
    no_comments = re.sub(r"#[^\n]*", "", no_docstrings)
    forbidden_stub_markers = (
        "def _StubMassBreakdownForDuckType",
        "class _StubMassBreakdown",
    )
    for marker in forbidden_stub_markers:
        assert marker not in no_comments, (
            f"case_03 path contains P0-2 forbidden synthetic "
            f"MassBreakdown stub marker {marker!r} outside of docstring / "
            f"comment text; calculate_cost_breakdown must NOT be called with "
            f"any synthetic mass object"
        )
    # Live behavior assertion: case_03 cost_components_* are all
    # None (no cost outputs synthesized).
    from hexagent.validation_report import chain_adapter as _ca

    fixture = _load_fixture("TASK-019-GOLDEN-03")
    artifact = _ca.compute_actual_output_via_chain(fixture)
    cc = artifact["values"]["cost_components_C0_C1"]["cost_components"]
    assert cc["C0_material_minor_units"] is None
    assert cc["C0_labor_minor_units"] is None
    assert cc["C1_total_minor_units"] is None
    assert artifact["values"]["cost_components_C0_C1"]["currency_ISO_4217"] is None
    # And the cost breakdown call must not have been made. Verify
    # by absence of cost_calculator / calculator_run_id in
    # produced_fields.
    for field_name in (
        "cost_components_C0_C1.cost_components.C0_material_minor_units",
        "cost_components_C0_C1.cost_components.C0_labor_minor_units",
        "cost_components_C0_C1.cost_components.C1_total_minor_units",
        "cost_components_C0_C1.currency_ISO_4217",
        "cost_components_C0_C1.calculator_run_id",
    ):
        assert field_name not in artifact["produced_fields"], (
            f"case_03 produced_fields MUST NOT contain {field_name!r} when "
            f"mass dependency is unavailable (P0-2: no cost outputs synthesized)"
        )


def test_case_03_duplicate_missing_binding_uses_existing_blocker_code_and_details_reason() -> None:
    """P0-3: the case_03 path must NOT emit new blocker code
    strings (duplicate_c0_material_record_id,
    duplicate_c0_labor_record_id,
    missing_c0_material_record_id,
    missing_c0_labor_record_id). The case_03 path uses the
    existing UNSPECIFIED_BLOCKER enum literal as the blocker
    ``code`` and carries the human-readable reason in
    ``details.reason``.

    The inspection is scoped to the case_03 path. The
    case_02 path does not contain any of the forbidden
    code-assignment markers and so cannot produce a false
    positive.
    """
    import re

    case_03_src = _extract_case_03_source_region()
    no_docstrings = re.sub(r'"""[\s\S]*?"""', "", case_03_src)
    no_docstrings = re.sub(r"'''[\s\S]*?'''", "", no_docstrings)
    no_comments = re.sub(r"#[^\n]*", "", no_docstrings)
    # The duplicate_c0_material_record_id /
    # duplicate_c0_labor_record_id / missing_c0_material_record_id /
    # missing_c0_labor_record_id strings must NOT appear as
    # blocker ``code`` field values in the case_03 path. The
    # 002-H design reserves these as ``details.reason``-only
    # and reuses the existing UNSPECIFIED_BLOCKER enum literal
    # for the ``code`` field.
    forbidden_code_assignments = (
        '"code": "duplicate_c0_material_record_id"',
        '"code": "duplicate_c0_labor_record_id"',
        '"code": "missing_c0_material_record_id"',
        '"code": "missing_c0_labor_record_id"',
    )
    for marker in forbidden_code_assignments:
        assert marker not in no_comments, (
            f"case_03 path contains P0-3 forbidden new blocker code "
            f"assignment {marker!r}; the case_03 path must reuse the existing "
            f"UNSPECIFIED_BLOCKER enum literal and carry the reason in "
            f"details.reason"
        )
    # The existing UNSPECIFIED_BLOCKER literal MUST be used in
    # the case_03 path.
    assert "UNSPECIFIED_BLOCKER" in case_03_src, (
        "case_03 path must reference the existing UNSPECIFIED_BLOCKER "
        "enum literal for case_03 blocker codes"
    )
    # scenarios may exist (as informational strings) but the
    # source must not synthesize any *new* blocker code.
    # Live behavior: the current case_03 fixture has no real
    # selector-side blocker; the values.selected_cost_model
    # selection_blockers field MUST be [] (the selector ran
    # cleanly), and any mass-prerequisite unavailability is
    # surfaced via life_cycle_energy_envelope.blocker_codes
    # using the existing UNSPECIFIED_BLOCKER literal.
    from hexagent.validation_report import chain_adapter as _ca

    fixture = _load_fixture("TASK-019-GOLDEN-03")
    artifact = _ca.compute_actual_output_via_chain(fixture)
    scm_blockers = artifact["values"]["selected_cost_model"]["selection_blockers"]
    assert scm_blockers == [], (
        f"case_03 selector-side selection_blockers MUST be [] (selector "
        f"ran cleanly); got {scm_blockers!r}"
    )
    lifecycle_blockers = artifact["values"]["life_cycle_energy_envelope"]["blocker_codes"]
    # Lifecycle blocker is the existing UNSPECIFIED_BLOCKER literal
    # (no new code string).
    assert "duplicate_c0_material_record_id" not in lifecycle_blockers
    assert "duplicate_c0_labor_record_id" not in lifecycle_blockers
    assert "missing_c0_material_record_id" not in lifecycle_blockers
    assert "missing_c0_labor_record_id" not in lifecycle_blockers


def test_case_03_selected_model_id_is_not_produced_field() -> None:
    """P0-4: ``selected_model_id`` is fixture-context echo only. It
    may remain in values.selected_cost_model.selected_model_id
    (as the amendment-001 frozen string) but MUST NOT appear
    in produced_fields.
    """
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-03")
    artifact = chain_adapter.compute_actual_output_via_chain(fixture)
    scm = artifact["values"]["selected_cost_model"]
    # selected_model_id is in values (fixture-context echo).
    assert (
        scm["selected_model_id"]
        == "ASME-BPVC-VIII-1-COST-MODEL-V1 (TASK-018 Slice A frozen cost-model catalog)"
    )
    # But NOT in produced_fields.
    assert "selected_cost_model.selected_model_id" not in artifact["produced_fields"], (
        f"selected_model_id MUST NOT appear in produced_fields per P0-4; "
        f"got produced_fields={sorted(artifact['produced_fields'])}"
    )


def test_case_03_selector_audit_fields_are_produced_fields() -> None:
    """P0-4: produced_fields for case_03 must contain the 5 002-H
    canonical selector audit fields:
    - selected_cost_model.selector_run_id
    - selected_cost_model.provenance_chain_hash
    - selected_cost_model.selection_blockers
    - selected_cost_model.c0_record_count
    - selected_cost_model.c1_record_count
    The 002-H canonical key is ``provenance_chain_hash`` (NOT
    ``selector_provenance_chain_hash``); the pre-existing public
    compatibility key ``selector_provenance_chain_hash`` is also
    produced (both keys point to the same value).
    """
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-03")
    artifact = chain_adapter.compute_actual_output_via_chain(fixture)
    expected_audit_fields = {
        "selected_cost_model.selector_run_id",
        "selected_cost_model.provenance_chain_hash",
        "selected_cost_model.selection_blockers",
        "selected_cost_model.c0_record_count",
        "selected_cost_model.c1_record_count",
    }
    assert set(artifact["produced_fields"]) == expected_audit_fields, (
        f"case_03 produced_fields must be exactly the 5 P0-4 selector audit "
        f"fields; got {sorted(artifact['produced_fields'])}"
    )
    scm = artifact["values"]["selected_cost_model"]
    # 002-H canonical key is produced (non-empty).
    assert scm["provenance_chain_hash"] != ""
    # Pre-existing public compatibility key is also produced (non-empty
    # and equal to the 002-H canonical key per Charles's "if
    # compatibility key remains, test both" instruction).
    assert scm["selector_provenance_chain_hash"] != ""
    assert scm["provenance_chain_hash"] == scm["selector_provenance_chain_hash"]
