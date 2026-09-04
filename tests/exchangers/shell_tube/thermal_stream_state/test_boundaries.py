"""Lifecycle and ownership boundary tests for TASK160."""

from __future__ import annotations

from pathlib import Path

from hexagent.exchangers.shell_tube.thermal_stream_state import models
from hexagent.exchangers.shell_tube.thermal_stream_state.service import validate_request

from .test_ingress_models import make_r607_raw

PACKAGE_ROOT = (
    Path(__file__).resolve().parents[4]
    / "src"
    / "hexagent"
    / "exchangers"
    / "shell_tube"
    / "thermal_stream_state"
)


def _production_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in PACKAGE_ROOT.glob("*.py"))


def test_package_initialization_uses_only_the_package_dunder_init_path() -> None:
    assert (PACKAGE_ROOT / "__init__.py").is_file()
    assert not (PACKAGE_ROOT / "init.py").exists()


def test_task160_does_not_import_property_provider_or_performance_runtime() -> None:
    text = _production_text()
    assert "PropertyProvider" not in text
    assert "ShellSideFlowState" not in text
    assert "from hexagent.exchangers.shell_tube.shell_side_flow_state" in text


def test_success_result_exposes_no_downstream_performance_outputs() -> None:
    valid = validate_request(make_r607_raw()).valid
    assert valid is not None
    forbidden = {
        "c_min",
        "c_max",
        "capacity_ratio",
        "flow_arrangement",
        "effectiveness",
        "ntu",
        "heat_duty",
        "outlet_temperatures",
        "lmtd",
        "overall_u",
        "effective_area",
        "ua",
    }
    assert forbidden.isdisjoint(vars(valid))
    assert forbidden.isdisjoint(vars(models.CapacityRatedStream))


def test_task160_result_has_exactly_two_stream_records_and_two_cdot_values() -> None:
    valid = validate_request(make_r607_raw()).valid
    assert valid is not None
    assert len(valid.stream_records) == 2
    assert valid.c_dot_hot_W_K > 0
    assert valid.c_dot_cold_W_K > 0


def test_validation_result_has_one_and_only_one_branch() -> None:
    outcome = validate_request(make_r607_raw())
    assert (
        sum(
            value is not None
            for value in (outcome.raw_boundary_blocked, outcome.typed_blocked, outcome.valid)
        )
        == 1
    )


def test_raw_invalid_numeric_literals_fail_closed_without_float_conversion() -> None:
    raw = make_r607_raw()
    raw["stream_records"][0]["mass_flow_kg_s"] = "Infinity"  # type: ignore[index]
    outcome = validate_request(raw)
    assert outcome.raw_boundary_blocked is not None
    assert outcome.blockers


def test_no_performance_formula_identifiers_are_defined_in_task160_models() -> None:
    names = set(models.__all__)
    assert not {"Cmin", "Cmax", "capacity_ratio", "effectiveness", "NTU", "LMTD"} & names


def test_task160_is_not_a_public_shell_tube_root_export() -> None:
    parent_init = PACKAGE_ROOT.parent / "__init__.py"
    assert parent_init.is_file()
    assert "thermal_stream_state" not in parent_init.read_text(encoding="utf-8")
