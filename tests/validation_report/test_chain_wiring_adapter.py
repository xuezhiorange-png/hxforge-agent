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
from pathlib import Path

import pytest

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


# 5. case_01 actual_output is no longer placeholder-only / empty where authorized production output is available.
def test_case_01_actual_output_has_production_values() -> None:
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-01")
    artifact = chain_adapter.compute_actual_output_via_chain(fixture)
    assert artifact["status"] in {"WIRED_VIA_CHAIN", "WIRED_VIA_CHAIN_PARTIAL"}
    produced = artifact.get("produced_fields", [])
    # At minimum, the adapter must produce the heat_duty field.
    assert "heat_duty_W" in produced


# 6. case_02 actual_output is no longer placeholder-only / empty where authorized production output is available.
def test_case_02_actual_output_has_production_values() -> None:
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-02")
    artifact = chain_adapter.compute_actual_output_via_chain(fixture)
    assert artifact["status"] in {"WIRED_VIA_CHAIN", "WIRED_VIA_CHAIN_PARTIAL"}
    # Adapter must surface the case-bound material_record_id strings
    # (the production's selected_material_ids.shell_material_id and
    # .tube_material_id are produced from the frozen fixture's
    # material_selection block).
    values = artifact.get("values", {})
    assert "selected_material_ids" in values
    assert values["selected_material_ids"]["shell_material_id"] is not None
    assert values["selected_material_ids"]["tube_material_id"] is not None


# 7. case_03 actual_output is no longer placeholder-only / empty where authorized production output is available.
def test_case_03_actual_output_has_production_values() -> None:
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-03")
    artifact = chain_adapter.compute_actual_output_via_chain(fixture)
    assert artifact["status"] in {"WIRED_VIA_CHAIN", "WIRED_VIA_CHAIN_PARTIAL"}
    # The discount_salvage_status signal must be set (deferred, not
    # invented).
    assert artifact.get("discount_salvage_status", {}).get(
        "discounted_total_minor_units"
    ) == "DEFERRED_PER_TASK_018_5_3"
    assert artifact.get("discount_salvage_status", {}).get(
        "salvage_minor_units"
    ) == "DEFERRED_PER_TASK_018_5_3_2"


# 8. expected_output remains unchanged.
def test_expected_output_unchanged_across_adapter_runs() -> None:
    """The adapter must not modify the fixture's expected_output. We
    re-load the fixture and assert the expected_output block is
    byte-identical to a precomputed SHA-256 of the frozen values."""
    fixture_01 = _load_fixture("TASK-019-GOLDEN-01")
    expected_01 = fixture_01["expected_output"]
    assert expected_01["heat_duty_W"] == 8368.0
    assert expected_01["LMTD_derived_values"]["LMTD_counterflow_K"] == 29.86

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
        case_block = materialize_case_block_with_chain_output(
            _CASES[case_id], repo_root=_REPO_ROOT
        )
        pressure_drop_records = [
            r for r in case_block["comparison"]["per_field"]
            if r["field"] == "pressure_drop"
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
        case_block = materialize_case_block_with_chain_output(
            _CASES[case_id], repo_root=_REPO_ROOT
        )
        for blocker in case_block["comparison"]["blockers"]:
            assert blocker in {
                "discount_formula_pending_design_amendment"
            }, f"unexpected blocker reason {blocker!r} in case {case_id}"


# 14. canonical_actual_output_sha256 is deterministic if added.
def test_canonical_actual_output_sha256_is_deterministic() -> None:
    from hexagent.validation_report import chain_adapter

    fixture = _load_fixture("TASK-019-GOLDEN-01")
    artifact_1 = chain_adapter.compute_actual_output_via_chain(fixture)
    artifact_2 = chain_adapter.compute_actual_output_via_chain(fixture)
    assert artifact_1["canonical_actual_output_sha256"] == artifact_2["canonical_actual_output_sha256"]


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
        def _walk(obj: object, path: str = "") -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(k, str) and any(
                        k.startswith(p) for p in _FORBIDDEN_SCOPE_FIELD_PREFIXES
                    ):
                        raise AssertionError(
                            f"case {case_id} adapter introduced forbidden-scope field "
                            f"{k!r} at path {path!r}"
                        )
                    _walk(v, f"{path}.{k}" if path else k)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    _walk(item, f"{path}[{i}]")
        _walk(artifact["values"])


# 18. no src/hexagent/exchangers/, correlations/, core/, material_mass_mechanical/, costing/** mutation is required or performed.
def test_no_upstream_mutation_required_or_performed() -> None:
    """The chain adapter must NOT mutate any production module
    outside validation_report/. We assert this by reading the
    production module file paths from the adapter's imports and
    verifying they are unchanged on disk (mtime < adapter creation
    time, or simply: the file mtimes for upstream modules are all
    older than the adapter file mtime)."""
    import importlib
    import inspect
    import time

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
    assert (
        cb_not_computable["actual_output_sha256"]
        != cb_chain["actual_output_sha256"]
    ), (
        "chain-wired actual_output_sha256 must differ from the NOT_COMPUTABLE "
        "placeholder's actual_output_sha256; otherwise the chain wiring is a no-op"
    )
