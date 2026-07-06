"""TASK-017 Slice C — PreliminaryMechanicalChecker tests (§9.1 only).

Validates the TASK-017 frozen design contract
(docs/tasks/TASK-017-materials-mass-preliminary-mechanical.md,
Frozen Contract Authority Commit SHA
``6ed5b7dc7d8df163796eacb838afcf5702a4c53a``) for the
allowable-stress preliminary screening check (design §9.1 +
§7 codes 11-13 + §8 provenance + §10.3 + §10.4).

Slice C tests cover §9.1 ONLY. They do NOT exercise the
minimum-wall check (§9.2) or the straight-pipe span check
(§9.3) — those are Slice D's scope.
"""

from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal

import pytest

from hexagent.canonical_json import canonical_json_bytes
from hexagent.material_mass_mechanical import (
    ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT,
    ERROR_MECHANICAL_CHECK_INPUT_UNIT_INCONSISTENT,
    ERROR_MECHANICAL_CHECK_UNSUPPORTED_ROLE,
    MECHANICAL_ROLES_FROZEN_ORDER,
    SUPPORTED_MECHANICAL_ROLES,
    MaterialProvenance,
    MaterialResolutionResult,
    MaterialSelectorError,
    PreliminaryCheckRequest,
    preliminary_check,
)


# ── Helpers ──────────────────────────────────────────────────────────
def _make_provenance(
    material_record_id: str = "mat:astm-sa-106-b:rev:2026-Q2:inner_tube",
    standard: str | None = "ASME-II-A-2023",
) -> MaterialProvenance:
    return MaterialProvenance(
        geometry_record_id="geom:placeholder",
        material_record_id=material_record_id,
        applicable_standard_id=standard,
        design_pressure_mpa=2.5,
        design_temperature_c=120.0,
        correlation_ids=("corr:sa-106-b-allowable-stress",),
        software_version="task-017-slice-a-v0.1.0",
        git_commit="see task-017 implementation head",
        result_hash="placeholder",
    )


def _make_resolution(
    *,
    component_role: str = "inner_tube",
    material_record_id: str = "mat:astm-sa-106-b:rev:2026-Q2:inner_tube",
    material_grade: str = "ASTM-SA-106-B",
    density_kg_m3: float | None = 7850.0,
    youngs_modulus_gpa: float | None = 200.0,
    allowable_table: dict[float, float] | None = None,
    use_default_table: bool = True,
) -> MaterialResolutionResult:
    """Build a MaterialResolutionResult with allowable_stress_mpa table.

    If ``use_default_table`` is True and ``allowable_table`` is None,
    a default table is used. To explicitly test the None-table case,
    pass ``use_default_table=False`` and ``allowable_table=None``.
    """
    if allowable_table is None and use_default_table:
        allowable_table = {120.0: 137.9, 200.0: 120.0, 300.0: 100.0}
    return MaterialResolutionResult(
        material_record_id=material_record_id,
        material_grade=material_grade,
        density_kg_m3=density_kg_m3,
        youngs_modulus_gpa=youngs_modulus_gpa,
        allowable_stress_mpa=allowable_table,
        provenance=_make_provenance(material_record_id=material_record_id),
    )


def _make_request(
    *,
    component_role: str = "inner_tube",
    design_pressure_mpa: Decimal = Decimal("2.5"),
    design_temperature_c: float = 120.0,
    outer_diameter_m: Decimal = Decimal("0.060"),
    inner_diameter_m: Decimal = Decimal("0.050"),
    allowable_table: dict[float, float] | None = None,
    material_record_id: str | None = None,
) -> PreliminaryCheckRequest:
    """Build a default PreliminaryCheckRequest."""
    if material_record_id is None:
        material_record_id = f"mat:placeholder:{component_role}"
    if allowable_table is None:
        # Build a table that always contains the design_temperature_c key
        allowable_table = {
            design_temperature_c: 137.9,
            200.0: 120.0,
            300.0: 100.0,
        }
    return PreliminaryCheckRequest(
        component_role=component_role,
        material_resolution=_make_resolution(
            component_role=component_role,
            material_record_id=material_record_id,
            allowable_table=allowable_table,
        ),
        design_pressure_mpa=design_pressure_mpa,
        design_temperature_c=design_temperature_c,
        outer_diameter_m=outer_diameter_m,
        inner_diameter_m=inner_diameter_m,
    )


# ── §5.2.2 Closed-set guard tests ───────────────────────────────────
class TestClosedSetGuard:
    def test_inner_tube_role_accepted(self) -> None:
        req = _make_request(component_role="inner_tube")
        result = preliminary_check(req)
        assert result.component_role == "inner_tube"

    def test_outer_pipe_role_accepted(self) -> None:
        req = _make_request(component_role="outer_pipe")
        result = preliminary_check(req)
        assert result.component_role == "outer_pipe"

    def test_hairpin_bend_role_rejected_not_in_scope(self) -> None:
        """hairpin_bend is not in §9.1 closed set."""
        req = _make_request(component_role="hairpin_bend")
        with pytest.raises(MaterialSelectorError) as exc_info:
            preliminary_check(req)
        assert exc_info.value.code == ERROR_MECHANICAL_CHECK_UNSUPPORTED_ROLE
        assert "supported_roles" in exc_info.value.context

    def test_fittings_role_rejected_not_supported(self) -> None:
        """fittings is mechanically de-scoped per design §5.2.2."""
        req = _make_request(component_role="fittings")
        with pytest.raises(MaterialSelectorError) as exc_info:
            preliminary_check(req)
        assert exc_info.value.code == ERROR_MECHANICAL_CHECK_UNSUPPORTED_ROLE
        assert "fittings" in exc_info.value.message

    def test_unknown_role_rejected(self) -> None:
        req = _make_request(component_role="mystery_role")
        with pytest.raises(MaterialSelectorError) as exc_info:
            preliminary_check(req)
        assert exc_info.value.code == ERROR_MECHANICAL_CHECK_UNSUPPORTED_ROLE

    def test_empty_role_rejected(self) -> None:
        req = _make_request(component_role="")
        with pytest.raises(MaterialSelectorError) as exc_info:
            preliminary_check(req)
        assert exc_info.value.code == ERROR_MECHANICAL_CHECK_UNSUPPORTED_ROLE

    def test_supported_roles_match_frozen_set(self) -> None:
        assert frozenset({"inner_tube", "outer_pipe"}) == SUPPORTED_MECHANICAL_ROLES
        assert MECHANICAL_ROLES_FROZEN_ORDER == ("inner_tube", "outer_pipe")


# ── §9.1 Hoop stress formula tests ──────────────────────────────────
class TestHoopStressFormula:
    def test_basic_hoop_stress(self) -> None:
        """σ = p·D/(2·t). p=2.5, D=0.060, t=0.005 → σ=15.0 MPa."""
        req = _make_request(
            design_pressure_mpa=Decimal("2.5"),
            outer_diameter_m=Decimal("0.060"),
            inner_diameter_m=Decimal("0.050"),  # t = 0.005
        )
        result = preliminary_check(req)
        expected_hoop = (
            Decimal("2.5") * Decimal("0.060") / (Decimal("2") * Decimal("0.005"))
        ).quantize(Decimal("0.000001"))
        assert result.hoop_stress_mpa == expected_hoop

    def test_hoop_stress_thin_wall_relationship(self) -> None:
        """Hoop stress scales linearly with pressure at fixed geometry."""
        req_low = _make_request(design_pressure_mpa=Decimal("1.0"))
        req_high = _make_request(design_pressure_mpa=Decimal("4.0"))
        r_low = preliminary_check(req_low)
        r_high = preliminary_check(req_high)
        assert r_high.hoop_stress_mpa == (r_low.hoop_stress_mpa * 4).quantize(Decimal("0.000001"))

    def test_hoop_stress_scales_inversely_with_thickness(self) -> None:
        """Halving wall thickness doubles hoop stress."""
        req_thick = _make_request(
            outer_diameter_m=Decimal("0.060"),
            inner_diameter_m=Decimal("0.040"),  # t = 0.010
        )
        req_thin = _make_request(
            outer_diameter_m=Decimal("0.060"),
            inner_diameter_m=Decimal("0.050"),  # t = 0.005
        )
        r_thick = preliminary_check(req_thick)
        r_thin = preliminary_check(req_thin)
        assert r_thin.hoop_stress_mpa == (r_thick.hoop_stress_mpa * 2).quantize(Decimal("0.000001"))


# ── §9.1 Verdict threshold tests (60% / 80%) ────────────────────────
class TestVerdictThresholds:
    def test_verdict_pass_below_60_percent(self) -> None:
        """hoop = 15, allowable = 137.9 → ratio ≈ 0.109 → pass."""
        req = _make_request(allowable_table={120.0: 137.9})
        result = preliminary_check(req)
        assert result.verdict == "pass"
        assert result.stress_utilization_ratio <= Decimal("0.6")

    def test_verdict_marginal_between_60_and_80(self) -> None:
        """Choose hoop and allowable so ratio ≈ 0.7 → marginal."""
        # hoop = 100, allowable = 150 → ratio ≈ 0.667 → marginal
        # Need σ = 100 with p=?, D=?, t=?
        # Use p = 10, D = 0.060, t = 0.003 → σ = 10·0.060/(2·0.003) = 100
        req = _make_request(
            design_pressure_mpa=Decimal("10.0"),
            outer_diameter_m=Decimal("0.060"),
            inner_diameter_m=Decimal("0.054"),  # t = 0.003
            allowable_table={120.0: 150.0},
        )
        result = preliminary_check(req)
        assert Decimal("0.6") < result.stress_utilization_ratio <= Decimal("0.8")
        assert result.verdict == "marginal"

    def test_verdict_blocked_preliminary_above_80(self) -> None:
        """Choose hoop and allowable so ratio > 0.8 → blocked_preliminary."""
        # σ = 100, allowable = 100 → ratio = 1.0 → blocked_preliminary
        req = _make_request(
            design_pressure_mpa=Decimal("10.0"),
            outer_diameter_m=Decimal("0.060"),
            inner_diameter_m=Decimal("0.054"),  # t = 0.003
            allowable_table={120.0: 100.0},
        )
        result = preliminary_check(req)
        assert result.stress_utilization_ratio > Decimal("0.8")
        assert result.verdict == "blocked_preliminary"

    def test_verdict_pass_exactly_at_60_percent(self) -> None:
        """Boundary: ratio == 0.6 → pass (§9.1 says <= 0.6)."""
        # hoop = 60, allowable = 100 → ratio = 0.6 → pass
        req = _make_request(
            design_pressure_mpa=Decimal("10.0"),
            outer_diameter_m=Decimal("0.060"),
            inner_diameter_m=Decimal("0.055"),  # t = 0.0025
            allowable_table={120.0: 100.0},
        )
        # 10 * 0.060 / (2 * 0.0025) = 0.6/0.005 = 120 → ratio 1.2 → blocked
        # Adjust: use p=5, D=0.060, t=0.0025 → 5·0.060/0.005 = 60 → ratio 0.6
        req = _make_request(
            design_pressure_mpa=Decimal("5.0"),
            outer_diameter_m=Decimal("0.060"),
            inner_diameter_m=Decimal("0.055"),  # t = 0.0025
            allowable_table={120.0: 100.0},
        )
        result = preliminary_check(req)
        assert result.verdict == "pass"  # boundary is pass per §9.1

    def test_verdict_blocked_for_detailed_design_large_diameter(self) -> None:
        """diameter > 1.0 m → blocked_for_detailed_design (§9.1 envelope)."""
        req = _make_request(
            outer_diameter_m=Decimal("1.5"),
            inner_diameter_m=Decimal("1.4"),
        )
        result = preliminary_check(req)
        assert result.verdict == "blocked_for_detailed_design"

    def test_verdict_blocked_for_detailed_design_exactly_at_envelope(self) -> None:
        """diameter == 1.0 m → still in envelope (NOT blocked_for_detailed_design)."""
        req = _make_request(
            outer_diameter_m=Decimal("1.0"),
            inner_diameter_m=Decimal("0.9"),
        )
        result = preliminary_check(req)
        # 1.0 m is exactly at envelope boundary — should NOT be blocked_for_detailed_design
        assert result.verdict != "blocked_for_detailed_design"

    def test_verdict_is_one_of_four_tiers(self) -> None:
        req = _make_request()
        result = preliminary_check(req)
        assert result.verdict in (
            "pass",
            "marginal",
            "blocked_preliminary",
            "blocked_for_detailed_design",
        )


# ── §9.1 Allowable stress lookup tests ─────────────────────────────
class TestAllowableStressLookup:
    def test_lookup_at_design_temperature_exact_match(self) -> None:
        """allowable_table must contain design_temperature_c as exact key."""
        req = _make_request(
            design_temperature_c=120.0,
            allowable_table={120.0: 137.9, 200.0: 120.0},
        )
        result = preliminary_check(req)
        assert result.allowable_stress_mpa == Decimal("137.9").quantize(Decimal("0.000001"))

    def test_lookup_at_different_temperature(self) -> None:
        """Different design_temperature_c → different allowable."""
        req_120 = _make_request(
            design_temperature_c=120.0,
            allowable_table={120.0: 137.9, 200.0: 120.0},
        )
        req_200 = _make_request(
            design_temperature_c=200.0,
            allowable_table={120.0: 137.9, 200.0: 120.0},
        )
        r_120 = preliminary_check(req_120)
        r_200 = preliminary_check(req_200)
        assert r_120.allowable_stress_mpa == Decimal("137.900000")
        assert r_200.allowable_stress_mpa == Decimal("120.000000")

    def test_lookup_no_exact_key_rejected(self) -> None:
        """No exact key match → unit-inconsistent (no interpolation)."""
        req = _make_request(
            design_temperature_c=150.0,
            allowable_table={120.0: 137.9, 200.0: 120.0},
        )
        with pytest.raises(MaterialSelectorError) as exc_info:
            preliminary_check(req)
        assert exc_info.value.code == ERROR_MECHANICAL_CHECK_INPUT_UNIT_INCONSISTENT
        assert "design_temperature_c" in str(exc_info.value.context)

    def test_lookup_empty_table_rejected(self) -> None:
        req = _make_request(
            design_temperature_c=120.0,
            allowable_table={},
        )
        with pytest.raises(MaterialSelectorError) as exc_info:
            preliminary_check(req)
        assert exc_info.value.code == ERROR_MECHANICAL_CHECK_INPUT_UNIT_INCONSISTENT

    def test_lookup_none_table_rejected(self) -> None:
        """None allowable_stress_mpa → unit-inconsistent."""
        resolution = _make_resolution(allowable_table=None, use_default_table=False)
        req = PreliminaryCheckRequest(
            component_role="inner_tube",
            material_resolution=resolution,
            design_pressure_mpa=Decimal("2.5"),
            design_temperature_c=120.0,
            outer_diameter_m=Decimal("0.060"),
            inner_diameter_m=Decimal("0.050"),
        )
        with pytest.raises(MaterialSelectorError) as exc_info:
            preliminary_check(req)
        assert exc_info.value.code == ERROR_MECHANICAL_CHECK_INPUT_UNIT_INCONSISTENT

    def test_provenance_records_looked_up_temperature(self) -> None:
        req = _make_request(
            design_temperature_c=200.0,
            allowable_table={120.0: 137.9, 200.0: 120.0},
        )
        result = preliminary_check(req)
        assert result.provenance.allowable_temperature_c == 200.0


# ── §7 Input guard tests ────────────────────────────────────────────
class TestInputGuards:
    def test_pressure_zero_rejected(self) -> None:
        req = _make_request(design_pressure_mpa=Decimal("0"))
        with pytest.raises(MaterialSelectorError) as exc_info:
            preliminary_check(req)
        assert exc_info.value.code == ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT

    def test_pressure_negative_rejected(self) -> None:
        req = _make_request(design_pressure_mpa=Decimal("-1.0"))
        with pytest.raises(MaterialSelectorError) as exc_info:
            preliminary_check(req)
        assert exc_info.value.code == ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT

    def test_outer_diameter_zero_rejected(self) -> None:
        req = _make_request(outer_diameter_m=Decimal("0"))
        with pytest.raises(MaterialSelectorError) as exc_info:
            preliminary_check(req)
        assert exc_info.value.code == ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT

    def test_outer_diameter_negative_rejected(self) -> None:
        req = _make_request(outer_diameter_m=Decimal("-0.01"))
        with pytest.raises(MaterialSelectorError) as exc_info:
            preliminary_check(req)
        assert exc_info.value.code == ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT

    def test_inner_diameter_negative_rejected(self) -> None:
        req = _make_request(inner_diameter_m=Decimal("-0.001"))
        with pytest.raises(MaterialSelectorError) as exc_info:
            preliminary_check(req)
        assert exc_info.value.code == ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT

    def test_inner_diameter_equal_outer_rejected(self) -> None:
        """Wall thickness = 0 is mechanically meaningless."""
        req = _make_request(
            outer_diameter_m=Decimal("0.060"),
            inner_diameter_m=Decimal("0.060"),
        )
        with pytest.raises(MaterialSelectorError) as exc_info:
            preliminary_check(req)
        assert exc_info.value.code == ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT

    def test_inner_diameter_exceeds_outer_rejected(self) -> None:
        req = _make_request(
            outer_diameter_m=Decimal("0.060"),
            inner_diameter_m=Decimal("0.070"),
        )
        with pytest.raises(MaterialSelectorError) as exc_info:
            preliminary_check(req)
        assert exc_info.value.code == ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT


# ── §10.3 Decimal 6dp quantization tests ────────────────────────────
class TestDecimalQuantization:
    def test_hoop_stress_quantized_to_6dp(self) -> None:
        """All Decimal stress values have exponent == -6."""
        req = _make_request()
        result = preliminary_check(req)
        assert result.hoop_stress_mpa.as_tuple().exponent == -6

    def test_allowable_stress_quantized_to_6dp(self) -> None:
        req = _make_request()
        result = preliminary_check(req)
        assert result.allowable_stress_mpa.as_tuple().exponent == -6

    def test_utilization_ratio_quantized_to_6dp(self) -> None:
        req = _make_request()
        result = preliminary_check(req)
        assert result.stress_utilization_ratio.as_tuple().exponent == -6

    def test_provenance_pressure_quantized_to_6dp(self) -> None:
        req = _make_request(design_pressure_mpa=Decimal("2.5123456789"))
        result = preliminary_check(req)
        assert result.provenance.design_pressure_mpa.as_tuple().exponent == -6

    def test_provenance_wall_thickness_quantized_to_6dp(self) -> None:
        req = _make_request()
        result = preliminary_check(req)
        assert result.provenance.wall_thickness_m.as_tuple().exponent == -6


# ── §10.4 SHA-256 result hash tests ─────────────────────────────────
class TestResultHashDeterminism:
    def test_hash_is_64_hex_chars(self) -> None:
        req = _make_request()
        result = preliminary_check(req)
        assert len(result.preliminary_check_result_hash) == 64
        assert all(c in "0123456789abcdef" for c in result.preliminary_check_result_hash)

    def test_hash_stable_across_invocations(self) -> None:
        req = _make_request()
        r1 = preliminary_check(req)
        r2 = preliminary_check(req)
        assert r1.preliminary_check_result_hash == r2.preliminary_check_result_hash

    def test_hash_changes_when_input_changes(self) -> None:
        req_a = _make_request(design_pressure_mpa=Decimal("2.5"))
        req_b = _make_request(design_pressure_mpa=Decimal("2.6"))
        r_a = preliminary_check(req_a)
        r_b = preliminary_check(req_b)
        assert r_a.preliminary_check_result_hash != r_b.preliminary_check_result_hash

    def test_hash_changes_when_temperature_changes(self) -> None:
        req_a = _make_request(
            design_temperature_c=120.0,
            allowable_table={120.0: 137.9, 200.0: 120.0},
        )
        req_b = _make_request(
            design_temperature_c=200.0,
            allowable_table={120.0: 137.9, 200.0: 120.0},
        )
        r_a = preliminary_check(req_a)
        r_b = preliminary_check(req_b)
        assert r_a.preliminary_check_result_hash != r_b.preliminary_check_result_hash

    def test_hash_matches_manual_sha256(self) -> None:
        """Verify hash is what we expect from canonical_json + sha256."""
        req = _make_request(
            design_pressure_mpa=Decimal("2.5"),
            outer_diameter_m=Decimal("0.060"),
            inner_diameter_m=Decimal("0.050"),
            allowable_table={120.0: 137.9},
            material_record_id="mat:test:inner_tube",
        )
        result = preliminary_check(req)
        # Reconstruct expected payload (excluding result_hash field)
        expected_payload = {
            "component_role": "inner_tube",
            "hoop_stress_mpa": str(result.hoop_stress_mpa),
            "allowable_stress_mpa": str(result.allowable_stress_mpa),
            "stress_utilization_ratio": str(result.stress_utilization_ratio),
            "verdict": result.verdict,
            "provenance": replace(result.provenance, result_hash="").to_dict(),
        }
        expected = hashlib.sha256(canonical_json_bytes(expected_payload)).hexdigest()
        assert result.preliminary_check_result_hash == expected


# ── §10.4 Canonical JSON serialization tests ─────────────────────────
class TestCanonicalJsonSerializable:
    def test_result_to_dict_is_json_serializable(self) -> None:
        import json

        req = _make_request()
        result = preliminary_check(req)
        json.dumps(result.to_dict())

    def test_provenance_to_dict_is_json_serializable(self) -> None:
        import json

        req = _make_request()
        result = preliminary_check(req)
        json.dumps(result.provenance.to_dict())


# ── §8 Provenance tests ─────────────────────────────────────────────
class TestProvenance:
    def test_provenance_has_required_fields(self) -> None:
        """8 §8 minimum + 4 slice-specific = 12 fields."""
        req = _make_request()
        result = preliminary_check(req)
        required_fields = {
            "material_record_id",
            "applicable_standard_id",
            "design_pressure_mpa",
            "design_temperature_c",
            "correlation_ids",
            "software_version",
            "git_commit",
            "result_hash",
            "outer_diameter_m",
            "inner_diameter_m",
            "wall_thickness_m",
            "allowable_temperature_c",
        }
        d = result.provenance.to_dict()
        assert required_fields.issubset(set(d.keys()))

    def test_provenance_correlation_ids_default_empty_tuple(self) -> None:
        req = _make_request()
        result = preliminary_check(req)
        assert result.provenance.correlation_ids == ()

    def test_provenance_carries_result_hash(self) -> None:
        req = _make_request()
        result = preliminary_check(req)
        assert result.provenance.result_hash == result.preliminary_check_result_hash

    def test_provenance_applicable_standard_id_from_resolution(self) -> None:
        req = _make_request(material_record_id="mat:custom:inner_tube")
        result = preliminary_check(req)
        assert result.provenance.applicable_standard_id == "ASME-II-A-2023"


# ── Slice A consumption tests ───────────────────────────────────────
class TestSliceAConsumption:
    def test_consumes_allowable_stress_table_from_resolution(self) -> None:
        """Different allowable_table → different verdict."""
        req_safe = _make_request(
            allowable_table={120.0: 137.9},
        )
        req_low = _make_request(
            allowable_table={120.0: 10.0},
        )
        r_safe = preliminary_check(req_safe)
        r_low = preliminary_check(req_low)
        assert r_safe.verdict == "pass"
        assert r_low.verdict == "blocked_preliminary"

    def test_consumes_material_record_id_from_resolution(self) -> None:
        req = _make_request(material_record_id="mat:custom-id:inner_tube")
        result = preliminary_check(req)
        assert result.provenance.material_record_id == "mat:custom-id:inner_tube"


# ── Forbidden-scope guard tests ─────────────────────────────────────
class TestForbiddenScopeGuards:
    def test_no_pressure_drop_token(self) -> None:
        import inspect

        from hexagent.material_mass_mechanical import preliminary_checker

        source = inspect.getsource(preliminary_checker)
        forbidden = ["pressure_drop", "darcy", "reynolds", "friction_factor"]
        for token in forbidden:
            assert token not in source.lower(), (
                f"Forbidden token {token!r} found in preliminary_checker"
            )

    def test_no_cost_token(self) -> None:
        import inspect

        from hexagent.material_mass_mechanical import preliminary_checker

        source = inspect.getsource(preliminary_checker)
        # Strip module docstring (which mentions "cost" as NOT IMPLEMENTED)
        parts = source.split('"""', 2)
        body = parts[2] if len(parts) >= 3 else source
        forbidden = ["currency", "price", "usd", "cny", "rmb"]
        for token in forbidden:
            assert (
                f" {token} " not in body.lower()
                and f"_{token}_" not in body.lower()
                and f"_{token} " not in body.lower()
                and f" {token}_" not in body.lower()
            ), f"Forbidden token {token!r} found in preliminary_checker body"
        # "cost" may appear in docstring (legitimately) but NOT in body
        assert " cost " not in body.lower(), (
            "'cost' token found in module body (not just docstring)"
        )

    def test_no_slice_d_token(self) -> None:
        """Slice C section must NOT reference Slice D-specific check terms.

        Scoped to the Slice C code region only (above the Slice D
        boundary header line) AND excludes the module docstring, which
        is the shared Slice C + Slice D preamble that legitimately
        enumerates Slice D's additions. Slice D's own code lives
        below the boundary and is tested by
        ``tests/material_mass_mechanical/test_preliminary_checker_slice_d.py``.
        """
        import inspect

        from hexagent.material_mass_mechanical import preliminary_checker

        source = inspect.getsource(preliminary_checker)
        # Scope guard: Slice C section ends at the Slice D header line.
        slice_d_header = "# Slice D — Minimum-wall check (§9.2) + straight-pipe span check (§9.3)"
        scoped = source.split(slice_d_header, 1)[0] if slice_d_header in source else source
        # Strip module docstring (which enumerates Slice D's
        # additions legitimately in the shared preamble).
        parts = scoped.split('"""', 2)
        body = parts[2] if len(parts) >= 3 else scoped
        # Slice D introduces minimum-wall + span checks
        forbidden = [
            "minimum_wall",
            "straight_pipe_span",
            "corrosion_allowance",
            "span_check",
            "effective_wall_m",
            "unsupported_span",
        ]
        for token in forbidden:
            assert token not in body.lower(), (
                f"Forbidden Slice D token {token!r} found in Slice C code "
                "body of preliminary_checker"
            )

    def test_no_closeout_token(self) -> None:
        import inspect

        from hexagent.material_mass_mechanical import preliminary_checker

        source = inspect.getsource(preliminary_checker)
        # Strip module docstring (which mentions "Closeout" as NOT IMPLEMENTED)
        parts = source.split('"""', 2)
        body = parts[2] if len(parts) >= 3 else source
        forbidden = ["closeout", "ready_to_merge", "release_gate"]
        for token in forbidden:
            assert token not in body.lower(), (
                f"Forbidden closeout token {token!r} found in module body"
            )

    def test_no_detailed_mechanical_design(self) -> None:
        """Slice C is preliminary screening only.

        Scoped to the Slice C code region (above the Slice D
        boundary) AND excludes the module docstring, which correctly
        enumerates the detailed-mechanical terms that the
        implementation MUST NOT introduce.
        """
        import inspect

        from hexagent.material_mass_mechanical import preliminary_checker

        source = inspect.getsource(preliminary_checker)
        # Scope to Slice C section only (same boundary as
        # test_no_slice_d_token).
        slice_d_header = "# Slice D — Minimum-wall check (§9.2) + straight-pipe span check (§9.3)"
        scoped = source.split(slice_d_header, 1)[0] if slice_d_header in source else source
        # Strip module docstring (which enumerates forbidden terms in
        # negative form: "we MUST NOT introduce … fatigue, creep, …").
        parts = scoped.split('"""', 2)
        body = parts[2] if len(parts) >= 3 else scoped
        forbidden = ["creep", "fatigue", "buckling", "weld_efficiency"]
        for token in forbidden:
            assert token not in body.lower(), (
                f"Forbidden detailed-mechanical token {token!r} found in "
                "Slice C code body of preliminary_checker"
            )

    def test_no_c4_token(self) -> None:
        import inspect

        from hexagent.material_mass_mechanical import preliminary_checker

        source = inspect.getsource(preliminary_checker)
        forbidden = ["c4_iteration", "iterative_solver", "new_solver"]
        for token in forbidden:
            assert token not in source.lower(), f"Forbidden solver/C4 token {token!r} found"


# ── Dataclass shape tests ───────────────────────────────────────────
class TestDataclassShape:
    def test_request_dataclass_is_frozen(self) -> None:
        req = _make_request()
        with pytest.raises(FrozenInstanceError):
            req.component_role = "outer_pipe"  # type: ignore[misc]

    def test_result_dataclass_is_frozen(self) -> None:
        req = _make_request()
        result = preliminary_check(req)
        with pytest.raises(FrozenInstanceError):
            result.verdict = "blocked_preliminary"  # type: ignore[misc]

    def test_provenance_dataclass_is_frozen(self) -> None:
        req = _make_request()
        result = preliminary_check(req)
        with pytest.raises(FrozenInstanceError):
            result.provenance.material_record_id = "tampered"  # type: ignore[misc]

    def test_request_rejects_non_str_role(self) -> None:
        with pytest.raises(TypeError):
            PreliminaryCheckRequest(
                component_role=123,  # type: ignore[arg-type]
                material_resolution=_make_resolution(),
                design_pressure_mpa=Decimal("2.5"),
                design_temperature_c=120.0,
                outer_diameter_m=Decimal("0.060"),
                inner_diameter_m=Decimal("0.050"),
            )

    def test_result_to_dict_has_all_keys(self) -> None:
        req = _make_request()
        result = preliminary_check(req)
        d = result.to_dict()
        expected_keys = {
            "component_role",
            "hoop_stress_mpa",
            "allowable_stress_mpa",
            "stress_utilization_ratio",
            "verdict",
            "provenance",
            "preliminary_check_result_hash",
        }
        assert expected_keys.issubset(set(d.keys()))


# ── Ordering / determinism across role variants ──────────────────────
class TestOrderingDeterminism:
    def test_two_role_results_produce_distinct_hashes(self) -> None:
        hashes = set()
        for role in ("inner_tube", "outer_pipe"):
            req = _make_request(component_role=role)
            r = preliminary_check(req)
            hashes.add(r.preliminary_check_result_hash)
        assert len(hashes) == 2

    def test_ordered_iteration_is_deterministic(self) -> None:
        order1 = list(MECHANICAL_ROLES_FROZEN_ORDER)
        order2 = list(MECHANICAL_ROLES_FROZEN_ORDER)
        assert order1 == order2
        assert order1 == ["inner_tube", "outer_pipe"]


# ── Verdict stability / blocker shape ───────────────────────────────
class TestVerdictStability:
    def test_same_input_same_verdict(self) -> None:
        req = _make_request()
        r1 = preliminary_check(req)
        r2 = preliminary_check(req)
        assert r1.verdict == r2.verdict

    def test_blocker_error_shape_includes_required_fields(self) -> None:
        req = _make_request(design_pressure_mpa=Decimal("0"))
        with pytest.raises(MaterialSelectorError) as exc_info:
            preliminary_check(req)
        err = exc_info.value
        assert hasattr(err, "code")
        assert hasattr(err, "message")
        assert hasattr(err, "context")
        assert err.code == ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT
        assert isinstance(err.message, str) and len(err.message) > 0
        assert isinstance(err.context, dict)

    def test_blocked_for_detailed_design_has_valid_hash(self) -> None:
        req = _make_request(
            outer_diameter_m=Decimal("2.0"),
            inner_diameter_m=Decimal("1.9"),
        )
        result = preliminary_check(req)
        assert result.verdict == "blocked_for_detailed_design"
        assert len(result.preliminary_check_result_hash) == 64
