"""Tests for TASK-017 Slice A — MaterialSelector.

Tests are scoped to design §5.1 (MaterialSelector) only. Slice B
(MassCalculator), Slice C (allowable-stress-only check), and
Slice D (minimum-wall + straight-pipe-span checks) tests are NOT
included in this round per the slice authorization template
(docs/tasks/TASK-017-materials-mass-mechanical-implementation.md
§10) and the planning doc §6 test plan which scopes each test to
a single slice.

Each test must pass under Python 3.11 + 3.12 (project
``requires-python = ">=3.11"``); determinism is asserted via
``result_hash`` equality across two invocations.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, cast

import pytest

from hexagent.material_costs.models import (
    ApprovalState,
    MaterialFamily,
    MaterialRecord,
    SourceClass,
)
from hexagent.material_mass_mechanical import material_selector
from hexagent.material_mass_mechanical.material_selector import (
    COMPONENT_ROLE_CLOSED_SET,
    ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
    ERROR_MATERIAL_GOVERNANCE_UNAPPROVED,
    ERROR_MATERIAL_RESOLUTION_MISSING_ROLE,
    FROZEN_CONTRACT_AUTHORITY_BASE_SHA,
    FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA,
    PROPERTY_NAME_ALLOWABLE_STRESS,
    PROPERTY_NAME_DENSITY,
    PROPERTY_NAME_YOUNGS_MODULUS,
    MaterialResolutionRequest,
    MaterialSelectorError,
    resolve_material,
)

# Captured at import time so tests assert against the actual frozen
# design SHAs (design §19.1 / §19.2).
EXPECTED_AUTHORITY_COMMIT_SHA = "6ed5b7dc7d8df163796eacb838afcf5702a4c53a"
EXPECTED_AUTHORITY_BASE_SHA = "fbb05ae71f21e6cfd4d1041afb5958c863166248"


def _selector_source() -> str:
    """Read the MaterialSelector source file once for guard tests."""
    return Path(material_selector.__file__).read_text(encoding="utf-8")


def _as_record(d: dict[str, Any]) -> MaterialRecord:
    """Cast a test fixture dict to MaterialRecord for the type checker.

    The MaterialRecord TypedDict only declares NotRequired keys for
    optional fields; the cast is safe because tests construct records
    with the required keys populated and mutate them only via
    well-typed dict operations.
    """
    return cast(MaterialRecord, d)


# ----------------- Fixtures -----------------


def _property_value(
    *,
    name: str,
    value_si: str,
    unit_si: str,
    source_pointer: str = "internal://task-013/handbook",
) -> dict[str, Any]:
    """Build a TASK-013 ``property_values[]`` entry matching §5.5."""
    return {
        "property_name": name,
        "value_si": value_si,
        "unit_si": unit_si,
        "source_pointer": source_pointer,
        "quality_flags": ["assumed_value"],
    }


def _base_material_record(
    *,
    approval_state: str = "approved",
    include_youngs_modulus: bool = True,
    include_allowable_stress: bool = True,
    density_value_si: str = "7850",
    allowable_table_json: str | None = None,
    record_id: str = "mat:astm-sa-106-b:rev:2026-Q2",
) -> dict[str, Any]:
    """Return a TASK-013 material record fixture with the three
    TASK-017-required canonical properties (density, optional
    youngs_modulus, optional/required allowable_stress table)."""
    if allowable_table_json is None:
        allowable_table_json = '{"20": "137.895", "200": "103.421", "400": "68.947"}'
    record: dict[str, Any] = {
        "material_record_id": record_id,
        "material_record_version": "1.0.0",
        "material_family": MaterialFamily.CARBON_STEEL.value,
        "material_grade_or_designation": "SA-106-B",
        "form_factor": "pipe",
        "region": "US",
        "effective_date": "2026-01-01T00:00:00Z",
        "source_class": SourceClass.INTERNAL_ENGINEERING_ASSUMPTION.value,
        "source_reference": "internal://handbook/SA-106-B",
        "license_evidence": "project_internal_authority",
        "dimensional_units": {"density": "kg/m^3", "youngs_modulus": "GPa"},
        "quality_flags": ["assumed_value"],
        "approval_state": approval_state,
        "provenance_edges": ["edge:internal-handbook/SA-106-B"],
        "property_values": [
            _property_value(
                name=PROPERTY_NAME_DENSITY,
                value_si=density_value_si,
                unit_si="kg/m^3",
            ),
        ],
    }
    if include_youngs_modulus:
        record["property_values"].append(
            _property_value(
                name=PROPERTY_NAME_YOUNGS_MODULUS,
                value_si="200",
                unit_si="GPa",
            )
        )
    if include_allowable_stress:
        record["property_values"].append(
            _property_value(
                name=PROPERTY_NAME_ALLOWABLE_STRESS,
                value_si=allowable_table_json,
                unit_si="MPa",
            )
        )
    return record


def _base_request(
    *,
    component_role: str = "inner_tube",
    material_record_id: str = "mat:astm-sa-106-b:rev:2026-Q2",
    design_temperature_c: float | None = 200.0,
    design_pressure_mpa: float | None = 5.0,
    corrosion_allowance_mm: float | None = 1.5,
    applicable_standard_id: str | None = "ASME B31.3",
) -> MaterialResolutionRequest:
    return MaterialResolutionRequest(
        component_role=component_role,
        material_record_id=material_record_id,
        design_temperature_c=design_temperature_c,
        design_pressure_mpa=design_pressure_mpa,
        corrosion_allowance_mm=corrosion_allowance_mm,
        applicable_standard_id=applicable_standard_id,
    )


# ----------------- Tests: closed-set guards -----------------


def test_component_role_closed_set_has_four_roles() -> None:
    """Design §5.2.1 closes the component_role set on four tokens."""
    assert (
        frozenset({"inner_tube", "outer_pipe", "hairpin_bend", "fittings"})
        == COMPONENT_ROLE_CLOSED_SET
    )


def test_resolve_rejects_unknown_component_role() -> None:
    """component_role outside the closed set -> MATERIAL_RESOLUTION_MISSING_ROLE."""
    record = _base_material_record()
    request = _base_request(component_role="support_bracket")
    with pytest.raises(MaterialSelectorError) as exc_info:
        resolve_material(request, _as_record(record))
    assert exc_info.value.code == ERROR_MATERIAL_RESOLUTION_MISSING_ROLE


# ----------------- Tests: approval-state gate -----------------


@pytest.mark.parametrize(
    "non_approved_state",
    [
        ApprovalState.DRAFT.value,
        ApprovalState.UNDER_REVIEW.value,
        ApprovalState.REJECTED.value,
        ApprovalState.SUPERSEDED.value,
    ],
)
def test_resolve_rejects_non_approved_state(
    non_approved_state: str,
) -> None:
    """Design §7: approval_state != approved -> MATERIAL_GOVERNANCE_UNAPPROVED."""
    record = _base_material_record(approval_state=non_approved_state)
    request = _base_request()
    with pytest.raises(MaterialSelectorError) as exc_info:
        resolve_material(request, _as_record(record))
    assert exc_info.value.code == ERROR_MATERIAL_GOVERNANCE_UNAPPROVED


# ----------------- Tests: record_id binding -----------------


def test_resolve_rejects_record_id_mismatch() -> None:
    """record_id mismatch is a MATERIAL_GOVERNANCE_INCOMPLETE failure."""
    record = _base_material_record(
        record_id="mat:different-record:rev:2026-Q2",
    )
    request = _base_request(
        material_record_id="mat:astm-sa-106-b:rev:2026-Q2",
    )
    with pytest.raises(MaterialSelectorError) as exc_info:
        resolve_material(request, _as_record(record))
    assert exc_info.value.code == ERROR_MATERIAL_GOVERNANCE_INCOMPLETE
    assert exc_info.value.context["request_material_record_id"] == ("mat:astm-sa-106-b:rev:2026-Q2")
    assert exc_info.value.context["observed_material_record_id"] == (
        "mat:different-record:rev:2026-Q2"
    )


# ----------------- Tests: property_values[] walk -----------------


def test_resolve_happy_path_returns_complete_result() -> None:
    record = _base_material_record()
    request = _base_request()
    result = resolve_material(request, _as_record(record))

    assert result.material_record_id == "mat:astm-sa-106-b:rev:2026-Q2"
    assert result.material_grade == "SA-106-B"
    assert result.density_kg_m3 == pytest.approx(7850.0)
    assert result.youngs_modulus_gpa == pytest.approx(200.0)
    assert result.allowable_stress_mpa == pytest.approx(
        {20.0: 137.895, 200.0: 103.421, 400.0: 68.947}
    )
    # Provenance block carries the §8 minimum fields.
    assert result.provenance.geometry_record_id == ""
    assert result.provenance.material_record_id == "mat:astm-sa-106-b:rev:2026-Q2"
    assert result.provenance.applicable_standard_id == "ASME B31.3"
    assert result.provenance.design_pressure_mpa == pytest.approx(5.0)
    assert result.provenance.design_temperature_c == pytest.approx(200.0)
    assert result.provenance.correlation_ids == ()
    # result_hash is the lowercase 64-char SHA-256 of the canonical JSON.
    assert isinstance(result.provenance.result_hash, str)
    assert len(result.provenance.result_hash) == 64
    assert all(c in "0123456789abcdef" for c in result.provenance.result_hash)


def test_resolve_with_youngs_modulus_absent_returns_none() -> None:
    """Design §5.1.2 note: youngs_modulus MAY be absent."""
    record = _base_material_record(include_youngs_modulus=False)
    request = _base_request()
    result = resolve_material(request, _as_record(record))
    assert result.youngs_modulus_gpa is None


def test_resolve_missing_density_returns_incomplete() -> None:
    record = _base_material_record()
    record["property_values"] = [
        entry
        for entry in record["property_values"]
        if entry["property_name"] != PROPERTY_NAME_DENSITY
    ]
    request = _base_request()
    with pytest.raises(MaterialSelectorError) as exc_info:
        resolve_material(request, _as_record(record))
    assert exc_info.value.code == ERROR_MATERIAL_GOVERNANCE_INCOMPLETE
    assert exc_info.value.context["property_name"] == PROPERTY_NAME_DENSITY


def test_resolve_missing_allowable_stress_returns_incomplete() -> None:
    record = _base_material_record(include_allowable_stress=False)
    request = _base_request()
    with pytest.raises(MaterialSelectorError) as exc_info:
        resolve_material(request, _as_record(record))
    assert exc_info.value.code == ERROR_MATERIAL_GOVERNANCE_INCOMPLETE
    assert exc_info.value.context["property_name"] == (PROPERTY_NAME_ALLOWABLE_STRESS)


@pytest.mark.parametrize(
    "bad_unit",
    ["kg/m3", "g/cm^3", "kg/litre", ""],
)
def test_resolve_density_unit_mismatch_returns_incomplete(
    bad_unit: str,
) -> None:
    record = _base_material_record()
    for entry in record["property_values"]:
        if entry["property_name"] == PROPERTY_NAME_DENSITY:
            entry["unit_si"] = bad_unit
    request = _base_request()
    with pytest.raises(MaterialSelectorError) as exc_info:
        resolve_material(request, _as_record(record))
    assert exc_info.value.code == ERROR_MATERIAL_GOVERNANCE_INCOMPLETE
    assert exc_info.value.context["property_name"] == PROPERTY_NAME_DENSITY
    assert exc_info.value.context["observed_unit_si"] == bad_unit


def test_resolve_youngs_modulus_unit_mismatch_returns_incomplete() -> None:
    record = _base_material_record()
    for entry in record["property_values"]:
        if entry["property_name"] == PROPERTY_NAME_YOUNGS_MODULUS:
            entry["unit_si"] = "MPa"  # wrong canonical SI
    request = _base_request()
    with pytest.raises(MaterialSelectorError) as exc_info:
        resolve_material(request, _as_record(record))
    assert exc_info.value.code == ERROR_MATERIAL_GOVERNANCE_INCOMPLETE


def test_resolve_allowable_stress_unit_mismatch_returns_incomplete() -> None:
    record = _base_material_record()
    for entry in record["property_values"]:
        if entry["property_name"] == PROPERTY_NAME_ALLOWABLE_STRESS:
            entry["unit_si"] = "ksi"
    request = _base_request()
    with pytest.raises(MaterialSelectorError) as exc_info:
        resolve_material(request, _as_record(record))
    assert exc_info.value.code == ERROR_MATERIAL_GOVERNANCE_INCOMPLETE


def test_resolve_density_decimal_string_precision() -> None:
    """Design §5.1.1: Decimal(value_si) preserves precision (NOT float(...))."""
    record = _base_material_record(density_value_si="7850.123456789")
    request = _base_request()
    result = resolve_material(request, _as_record(record))
    # Python float loses some precision but Decimal->float must round-trip
    # the value back as the same float.
    assert result.density_kg_m3 == pytest.approx(7850.123456789)


# ----------------- Tests: allowable_stress table shape -----------------


def test_resolve_allowable_stress_table_parses_json() -> None:
    record = _base_material_record(
        allowable_table_json='{"-20": "150.0", "100": "120.5"}',
    )
    request = _base_request()
    result = resolve_material(request, _as_record(record))
    assert result.allowable_stress_mpa == pytest.approx({-20.0: 150.0, 100.0: 120.5})


def test_resolve_allowable_stress_invalid_json_returns_incomplete() -> None:
    record = _base_material_record(allowable_table_json="not-json{")
    request = _base_request()
    with pytest.raises(MaterialSelectorError) as exc_info:
        resolve_material(request, _as_record(record))
    assert exc_info.value.code == ERROR_MATERIAL_GOVERNANCE_INCOMPLETE


def test_resolve_allowable_stress_non_dict_returns_incomplete() -> None:
    record = _base_material_record(allowable_table_json="[1,2,3]")
    request = _base_request()
    with pytest.raises(MaterialSelectorError) as exc_info:
        resolve_material(request, _as_record(record))
    assert exc_info.value.code == ERROR_MATERIAL_GOVERNANCE_INCOMPLETE


def test_resolve_allowable_stress_non_decimal_value_returns_incomplete() -> None:
    record = _base_material_record(
        allowable_table_json='{"20": "not-a-number"}',
    )
    request = _base_request()
    with pytest.raises(MaterialSelectorError) as exc_info:
        resolve_material(request, _as_record(record))
    assert exc_info.value.code == ERROR_MATERIAL_GOVERNANCE_INCOMPLETE


# ----------------- Tests: determinism + provenance -----------------


def test_resolve_is_deterministic_across_invocations() -> None:
    """Design §10 / planning doc §6 determinism rule: two invocations
    on identical inputs MUST produce identical result_hash."""
    record = _base_material_record()
    request = _base_request()
    result_1 = resolve_material(request, _as_record(record))
    # Use a deep copy so the underlying record is not mutated.
    result_2 = resolve_material(request, _as_record(copy.deepcopy(record)))
    assert result_1.provenance.result_hash == result_2.provenance.result_hash
    assert result_1.to_dict() == result_2.to_dict()


def test_result_to_dict_is_canonical_json_hashable() -> None:
    """The result dict must round-trip through canonical_sha256
    without raising (no non-finite floats)."""
    from hexagent.canonical_json import canonical_sha256

    record = _base_material_record()
    request = _base_request()
    result = resolve_material(request, _as_record(record))
    payload = result.to_dict()
    h1 = canonical_sha256(payload)
    h2 = canonical_sha256(payload)
    assert h1 == h2
    assert len(h1) == 64


def test_frozen_contract_authority_shas_are_exposed() -> None:
    """The frozen contract SHAs from design §19 are exposed as
    module-level literals so callers can verify the contract is
    the one they expect."""
    assert FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA == EXPECTED_AUTHORITY_COMMIT_SHA
    assert FROZEN_CONTRACT_AUTHORITY_BASE_SHA == EXPECTED_AUTHORITY_BASE_SHA
    # And they must round-trip to the design §19 SHA literals.
    assert FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA == ("6ed5b7dc7d8df163796eacb838afcf5702a4c53a")
    assert FROZEN_CONTRACT_AUTHORITY_BASE_SHA == ("fbb05ae71f21e6cfd4d1041afb5958c863166248")


# ----------------- Tests: forbidden-scope guards -----------------


def test_no_pressure_drop_correlation_id_anywhere_in_module() -> None:
    """Planning doc §6: no-pressure-drop guard test asserts that no
    pressure-drop correlation id appears anywhere in the TASK-017
    code path.

    The Module-level docstring is permitted to mention
    "pressure-drop" as part of the explicit NO-list (forbidden
    scope); this test inspects only the **executable** code (token
    must not appear in any function name, import, attribute access,
    or string literal used at runtime).
    """
    src = _selector_source()
    # Strip module-level docstrings (both __init__.py and
    # material_selector.py) so the NO-list mentions are allowed.
    import re as _re

    no_docstrings = _re.sub(r'^\s*""".*?"""', "", src, flags=_re.DOTALL | _re.MULTILINE)
    forbidden = (
        "pressure_drop",
        "pressure-drop",
        "darcy",
        "fanning",
        "Colebrook",
    )
    for token in forbidden:
        assert token not in no_docstrings, (
            f"forbidden pressure-drop token {token!r} found in material_selector.py"
        )


def test_no_cost_or_currency_or_capex_anywhere_in_module() -> None:
    """Planning doc §6: no-cost guard test asserts that no currency
    code, CAPEX / OPEX / life-cycle symbol appears anywhere in the
    TASK-017 code path."""
    src = _selector_source()
    forbidden = (
        "CAPEX",
        "OPEX",
        "USD",
        "EUR",
        "CNY",
        "RMB",
        "life_cycle",
        "lifecycle",
        "life-cycle",
        "cost_record",
        "CostRecord",
        "CostValue",
        "select_cost_record",
    )
    for token in forbidden:
        assert token not in src, f"forbidden cost token {token!r} found in material_selector.py"


def test_module_does_not_import_geometry_catalogs_or_exchangers() -> None:
    """Slice A boundary: MaterialSelector must NOT depend on the
    TASK-016 geometry catalog module (Slice B / C consume it
    instead)."""
    src = _selector_source()
    assert "hexagent.geometry_catalogs" not in src
    assert "hexagent.exchangers" not in src


def test_module_does_not_implement_slices_b_c_d() -> None:
    """Slice A boundary: MassCalculator / PreliminaryMechanicalChecker
    must not be implemented in this round.

    Slice B / C / D names are permitted to appear in module-level
    docstrings (which list what is OUT OF SCOPE for this slice);
    only the **executable** code is inspected.
    """
    import re as _re

    src = _selector_source()
    no_docstrings = _re.sub(r'^\s*""".*?"""', "", src, flags=_re.DOTALL | _re.MULTILINE)
    forbidden = (
        "MassCalculator",
        "MassBreakdown",
        "PreliminaryMechanicalChecker",
        "MechanicalCheckReport",
        "hoop_stress",
        "wall_thickness",
        "unsupported_span",
    )
    for token in forbidden:
        assert token not in no_docstrings, (
            f"slice B/C/D token {token!r} found in material_selector.py executable code"
        )
