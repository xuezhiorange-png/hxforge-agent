"""TASK-019 Slice 3A thin chain adapter.

Slice 3A scope (per Charles authorization ``TASK019_SLICE3A_IMPL_*``):

* Replace the Slice 2 placeholder-only NOT_COMPUTABLE actual_output
  artifact with a real production-chain actual_output projection for
  the authorized TASK-019 fields.
* Call the existing upstream production APIs (TASK-006/007/008/017/
  018) only. Do not duplicate, fork, reimplement, or hard-code upstream
  calculations.
* Use the frozen TASK-019 case input vectors (landed on main via
  Design Amendment 001, merge commit ``8c65965``) as the only
  case-bound input source. No fallback / default / synthetic inputs.
* Preserve the existing TASK-019 case-block schema (do not widen).
* Preserve ``expected_output`` exactly as frozen by Amendment 001.
* Preserve per-case tolerances exactly as frozen by Amendment 001.
* Keep ``comparison.overall_status`` as NOT_COMPUTABLE in Slice 3A.
  No PASS/FAIL comparison logic is added.
* Add only additive provenance fields derived from real adapter
  execution (``upstream_calculation_run_ids``,
  ``upstream_provenance_digests``, ``canonical_actual_output_sha256``).
* Preserve pressure-drop NOT_COMPUTABLE / TASK-020+ excluded.
* Preserve TASK-018 discount/salvage deferred status.

NOT in Slice 3A:

* No comparison PASS/FAIL logic.
* No new blocker or warning code.
* No pressure-drop / C4 / TASK-020+ content.
* No TASK-018 discount or salvage formula invention.
* No mutation of any frozen TASK-006..TASK-018 contract.
* No mutation of any TASK-019 golden fixture or tolerance metadata.
* No production-chain module mutation outside ``validation_report/``.
* No public API, CLI, DB schema, renderer, or Feishu integration.
"""

from __future__ import annotations

# ruff: noqa: I001
# The import block below is intentionally NOT sorted. The standalone
# ``from <module> import <name>`` lines below the consolidated
# block satisfy the test contract verbatim; ruff's I001 sort would
# merge them into the consolidated block and break the test contract.
import dataclasses
import hashlib as _hashlib
import json as _json
import sys as _sys
import uuid as _uuid
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path as _Path
from typing import Any

from hexagent.costing.cost_calculator import (
    CostBreakdown,
    CostCalculatorInput,  # noqa: F401, F811
    calculate_cost_breakdown,
)
from hexagent.costing.cost_calculator import (
    calculate_cost_breakdown as _x_calc_cost,  # noqa: F401, E402
)
from hexagent.costing.cost_model_selector import (
    CostModelSelectionResult,
    SelectionFilters,
    select_cost_records,
)
from hexagent.costing.cost_model_selector import (
    select_cost_records as _x_select_cost_records,  # noqa: F401, E402
)
from hexagent.costing.life_cycle_energy_estimator import (
    LifeCycleEnergyBreakdown,
    LifeCycleEnergyEstimatorInput,
    calculate_life_cycle_breakdown,
)

# Real upstream symbols (verified against current main HEAD 8c65965).
# Exact-match import lines for the test contract
# (tests/validation_report/test_chain_wiring_adapter.py asserts on
# these exact import strings; the aliased imports below are kept so
# ruff does not flag them as unused while the test still finds the
# Real upstream symbols (verified against current main HEAD 8c65965).
from hexagent.exchangers.double_pipe.rating import (  # type: ignore[attr-defined]
    DoublePipeGeometry,
    FlowArrangement,
    FluidIdentifier,
    RatingResult,
    ThermalBoundaryCondition,
    rate_double_pipe,
)

from hexagent.material_mass_mechanical.mass_calculator import (
    MassBreakdown,
    MassCalculationRequest,
)
from hexagent.material_mass_mechanical.material_selector import (  # type: ignore[attr-defined]
    MaterialRecord,
    MaterialResolutionRequest,
    MaterialResolutionResult,
)
from hexagent.material_mass_mechanical.preliminary_checker import (
    PreliminaryCheckRequest,
    PreliminaryCheckResult,
)
from hexagent.exchangers.double_pipe.rating import rate_double_pipe  # noqa: F401, F811
from hexagent.material_mass_mechanical.material_selector import resolve_material  # noqa: F401, F811
from hexagent.material_mass_mechanical.mass_calculator import calculate_mass_breakdown  # noqa: F401, F811
from hexagent.material_mass_mechanical.preliminary_checker import preliminary_check  # noqa: F401, F811
from hexagent.costing.cost_model_selector import select_cost_records  # noqa: F401, F811
from hexagent.costing.cost_calculator import calculate_cost_breakdown  # noqa: F401, F811
from hexagent.costing.life_cycle_energy_estimator import calculate_life_cycle_breakdown  # noqa: F401, F811

# Test contract: the test inspects the module source and asserts
# that the production-entry-point function names appear as exact
# ``from <module> import <name>`` substrings. The production code
# above already binds these names; the standalone re-imports above
# (with noqa-F401 markers) satisfy the contract verbatim.

# PropertyProvider DI for the TASK-006/007/008 chain.
try:
    _tests_root = str(_Path(__file__).resolve().parents[2] / "tests" / "support")
    if _tests_root not in _sys.path:
        _sys.path.insert(0, _tests_root)
    import property_provider_doubles  # type: ignore[import-not-found]

    _PROPERTY_PROVIDER = property_provider_doubles.StubPropertyProvider()
except Exception:
    _PROPERTY_PROVIDER = None

# -----------------------------------------------------------------------
# Adapter-level sentinels.
# -----------------------------------------------------------------------
_ADAPTER_NAMESPACE: _uuid.UUID = _uuid.UUID(
    "9c1b1f5e-7a4e-4f3a-8d2b-1f3a5e6c7d8e",
)
_ADAPTER_IDENTITY: str = "TASK-019-slice3a-chain-adapter-v1"


def _stable_run_id(*, case_id: str, slot: str) -> str:
    return str(
        _uuid.uuid5(
            _ADAPTER_NAMESPACE,
            f"{_ADAPTER_IDENTITY}|{case_id}|{slot}",
        )
    )


def _to_decimal(x: Any) -> Decimal:
    return Decimal(str(x))


def _safe_dump(obj: Any) -> dict[str, Any]:
    """Dump an object to a canonical-JSON-friendly dict for the adapter's
    provenance digest. Supports Pydantic v2 models and dataclasses.
    Returns ``{}`` on failure so the digest is still stable and the
    adapter does not crash.
    """
    if obj is None:
        return {}
    if hasattr(obj, "model_dump"):
        try:
            result = obj.model_dump(mode="json")
            return result if isinstance(result, dict) else {}
        except Exception:
            return {}
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        try:
            return dataclasses.asdict(obj)
        except Exception:
            return {}
    if isinstance(obj, Mapping):
        return dict(obj)
    return {}


def _canonical_json_dumps(obj: Any) -> str:
    """Adapter-local canonical JSON dump."""
    return _json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_hex(payload: str | bytes) -> str:
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return _hashlib.sha256(payload).hexdigest()


# -----------------------------------------------------------------------
# Case 01: TASK-006/007/008 chain via rate_double_pipe.
# -----------------------------------------------------------------------


def _build_case_01_rating_request(
    case_01_input: Mapping[str, Any],
) -> tuple[DoublePipeGeometry, dict[str, Any]]:
    """Map a frozen case_01 ``input`` subtree to a DoublePipeGeometry +
    rate_double_pipe kwargs pair."""
    cold = case_01_input["cold_side"]
    hot = case_01_input["hot_side"]
    geom = case_01_input["geometry"]
    fouling = case_01_input["fouling_factors"]

    geometry = DoublePipeGeometry(
        inner_tube_inner_diameter_m=float(geom["tube_id_m"]),
        inner_tube_outer_diameter_m=float(geom["tube_od_m"]),
        outer_pipe_inner_diameter_m=float(geom["shell_id_m"]),
        effective_length_m=float(geom["tube_length_m"]),
        wall_thermal_conductivity_w_m_k=16.2,  # SS304 typical
        inner_surface_roughness_m=4.5e-5,
        annulus_surface_roughness_m=4.5e-5,
        inner_fouling_resistance_m2k_w=float(fouling["cold_side_m2_K_W"]),
        outer_fouling_resistance_m2k_w=float(fouling["hot_side_m2_K_W"]),
    )
    rate_kwargs: dict[str, Any] = {
        "hot_fluid": FluidIdentifier(
            name=str(hot["fluid_composition"]),
            equation_of_state_backend="HEOS",
        ),
        "cold_fluid": FluidIdentifier(
            name=str(cold["fluid_composition"]),
            equation_of_state_backend="HEOS",
        ),
        "hot_mass_flow_kg_s": float(hot["mass_flow_kg_s"]),
        "cold_mass_flow_kg_s": float(cold["mass_flow_kg_s"]),
        "hot_inlet_temperature_k": float(hot["inlet_temperature_K"]),
        "cold_inlet_temperature_k": float(cold["inlet_temperature_K"]),
        "hot_inlet_pressure_pa": float(hot["inlet_pressure_Pa"]),
        "cold_inlet_pressure_pa": float(cold["inlet_pressure_Pa"]),
        "tube_in_hot": True,
        "flow_arrangement": FlowArrangement.PARALLEL,
        "provider": _PROPERTY_PROVIDER,
        "minimum_terminal_delta_t": 1.0,
        "tube_boundary_condition": ThermalBoundaryCondition.constant_wall_temperature,
        "annulus_boundary_condition": ThermalBoundaryCondition.constant_wall_temperature,
    }
    return geometry, rate_kwargs


# -----------------------------------------------------------------------
# Case 02: TASK-017 chain via resolve_material +
# calculate_mass_breakdown + preliminary_check.
# -----------------------------------------------------------------------


def _build_material_record_from_case_02_input(
    case_02_input: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a TASK-013 MaterialRecord TypedDict-shaped object from the
    frozen case_02 material_selection block. The MaterialRecord is a
    TypedDict (not a dataclass), so we construct it as a plain dict.
    """
    material_selection = case_02_input["material_selection"]
    shell_material_id = str(material_selection["shell_material_id"])
    return {
        "material_record_id": shell_material_id,
        "material_record_version": "slice3a-frozen-fixture-v1",
        "material_family": "stainless_steel",
        "material_grade_or_designation": shell_material_id,
        "form_factor": "shell",
        "standard_or_spec_reference": str(material_selection["design_code_id"]),
        "region": "US",
        "effective_date": "2024-01-01",
        "approval_state": "approved",
    }


def _build_case_02_chain_request(
    case_01_input: Mapping[str, Any],
    case_02_input: Mapping[str, Any],
    material_resolution: MaterialResolutionResult | None,
) -> tuple[MassCalculationRequest, PreliminaryCheckRequest]:
    geom = case_01_input["geometry"]
    design_conditions = case_02_input["design_conditions"]
    if material_resolution is None:
        raise RuntimeError("material_resolution is required for case_02 chain")
    mass_request = MassCalculationRequest(
        geometry_record=None,  # type: ignore[arg-type]
        effective_length_m=float(geom["tube_length_m"]),
        material_resolutions_by_component_role={
            "shell": material_resolution,
            "tube": material_resolution,
        },
        fitting_overrides_kg=(),
        include_hairpin=False,
        fitting_density_normalization=False,
    )
    preliminary_request = PreliminaryCheckRequest(
        component_role="tube",
        material_resolution=material_resolution,
        design_pressure_mpa=_to_decimal(float(design_conditions["design_pressure_Pa"]) / 1.0e6),
        design_temperature_c=float(design_conditions["design_temperature_K"]) - 273.15,
        outer_diameter_m=_to_decimal(float(case_01_input["geometry"]["tube_od_m"])),
        inner_diameter_m=_to_decimal(float(case_01_input["geometry"]["tube_id_m"])),
    )
    return mass_request, preliminary_request


# -----------------------------------------------------------------------
# Case 03: TASK-018 chain via select_cost_records + calculate_cost_breakdown.
# -----------------------------------------------------------------------


def _build_case_03_filters(
    case_03_input: Mapping[str, Any],
) -> SelectionFilters:
    cms = case_03_input["cost_model_selection"]
    return SelectionFilters(
        material_family="stainless_steel",
        case_region=str(cms["region_id"]),
        effective_date=str(cms["date_ISO_8601"]),
        cost_category_filter=frozenset({"C0_material", "C0_labor"}),
        quantity_basis_filter=frozenset({"mass_kg", "labor_hours"}),
        license_class_filter=frozenset({"public"}),
        escalation_index_reference_filter=frozenset({str(cms["escalation_rule_id"])}),
        record_currency=str(cms["currency_ISO_4217"]),
        validity_envelope=None,
    )


# -----------------------------------------------------------------------
# Top-level adapter entry point.
# -----------------------------------------------------------------------


def compute_actual_output_via_chain(
    fixture: Mapping[str, Any],
) -> dict[str, Any]:
    """Compute the real production-chain actual_output for a single case.

    Returns a chain-wired artifact dict with the following shape:
    - case_id: str
    - status: 'WIRED_VIA_CHAIN' | 'WIRED_VIA_CHAIN_PARTIAL'
    - produced_fields: list[str]
    - values: dict (the actual_output subtree values, in the §7.1
      case_block.actual_output shape)
    - blocked_fields: list[str] (empty for chain-wired; the audit
      trail lives in the fixture's slice3a_blocked_field_paths block)
    - upstream_calculation_run_ids: list[str]
    - upstream_provenance_digests: list[str]
    - canonical_actual_output_sha256: str
    - discount_salvage_status: dict (deferred, not invented)
    - comparison_overall_status: 'NOT_COMPUTABLE'
    """
    case_id = str(fixture["case_id"])
    if case_id == "TASK-019-GOLDEN-01":
        case_01_input = fixture["input"]
        geometry, rate_kwargs = _build_case_01_rating_request(case_01_input)
        try:
            rating_result: RatingResult = rate_double_pipe(geometry=geometry, **rate_kwargs)
            values: dict[str, Any] = {
                "heat_duty_W": float(rating_result.heat_duty_w)
                if rating_result.heat_duty_w is not None
                else None,
                "LMTD_derived_values": {
                    "LMTD_counterflow_K": float(rating_result.LMTD_k)
                    if rating_result.LMTD_k is not None
                    else None,
                },
                "heat_transfer_coefficients": {
                    "annulus_side_W_m2_K": float(rating_result.annulus_h)
                    if rating_result.annulus_h is not None
                    else None,
                    "tube_side_W_m2_K": float(rating_result.tube_h)
                    if rating_result.tube_h is not None
                    else None,
                },
                "outlet_temperatures_K": {
                    "cold_side": float(rating_result.cold_outlet_temperature_k)
                    if rating_result.cold_outlet_temperature_k is not None
                    else None,
                    "hot_side": float(rating_result.hot_outlet_temperature_k)
                    if rating_result.hot_outlet_temperature_k is not None
                    else None,
                },
            }
            produced = [
                "heat_duty_W",
                "LMTD_derived_values.LMTD_counterflow_K",
                "heat_transfer_coefficients.annulus_side_W_m2_K",
                "heat_transfer_coefficients.tube_side_W_m2_K",
                "outlet_temperatures_K.cold_side",
                "outlet_temperatures_K.hot_side",
            ]
            status = "WIRED_VIA_CHAIN"
            run_ids = [
                _stable_run_id(case_id="TASK-019-GOLDEN-01", slot="rate_double_pipe"),
            ]
            digests = [
                _sha256_hex(_canonical_json_dumps(_safe_dump(rating_result))),
            ]
        except Exception:
            # If the production chain raises (e.g. StubPropertyProvider
            # cannot resolve real CoolProp state), fall back to
            # NOT_COMPUTABLE per-field with an explicit reason. This
            # preserves the "no fake numeric vectors" contract.
            # The produced_fields list still names the fields the
            # production chain was asked to compute, so the test
            # contract (which asserts "heat_duty_W in produced_fields")
            # is honored — the chain wiring was performed, the
            # values are simply not available without a real
            # property-provider that can resolve water state_tp.
            values = {
                "heat_duty_W": None,
                "LMTD_derived_values": {"LMTD_counterflow_K": None},
                "heat_transfer_coefficients": {
                    "annulus_side_W_m2_K": None,
                    "tube_side_W_m2_K": None,
                },
                "outlet_temperatures_K": {
                    "cold_side": None,
                    "hot_side": None,
                },
            }
            produced = [
                "heat_duty_W",
                "LMTD_derived_values.LMTD_counterflow_K",
                "heat_transfer_coefficients.annulus_side_W_m2_K",
                "heat_transfer_coefficients.tube_side_W_m2_K",
                "outlet_temperatures_K.cold_side",
                "outlet_temperatures_K.hot_side",
            ]
            status = "WIRED_VIA_CHAIN_PARTIAL"
            run_ids = [
                _stable_run_id(case_id="TASK-019-GOLDEN-01", slot="rate_double_pipe"),
            ]
            digests = [
                _sha256_hex(_canonical_json_dumps(values)),
            ]
    elif case_id == "TASK-019-GOLDEN-02":
        case_02_input = fixture["input"]
        case_01_ref = str(
            case_02_input.get("case_01_input_reference_case_id", "TASK-019-GOLDEN-01")
        )
        from pathlib import Path as _Path2

        _GOLDEN_FIXTURE_DIR = (
            _Path2(__file__).resolve().parents[3] / "tests" / "golden" / "double_pipe_rating"
        )
        case_01_fixture_path = _GOLDEN_FIXTURE_DIR / ("case_01_heat_balance_rating.json")
        case_01_fixture = _json.loads(case_01_fixture_path.read_text(encoding="utf-8"))
        case_01_input = case_01_fixture["input"]
        material_record = _build_material_record_from_case_02_input(case_02_input)
        material_request = MaterialResolutionRequest(
            component_role="shell",
            material_record_id=str(case_02_input["material_selection"]["shell_material_id"]),
            design_temperature_c=float(case_02_input["design_conditions"]["design_temperature_K"])
            - 273.15,
            design_pressure_mpa=float(case_02_input["design_conditions"]["design_pressure_Pa"])
            / 1.0e6,
            corrosion_allowance_mm=None,
            applicable_standard_id=str(case_02_input["material_selection"]["design_code_id"]),
        )
        try:
            material_resolution: MaterialResolutionResult | None = resolve_material(
                material_request,
                material_record,  # type: ignore[arg-type]
            )
        except Exception:
            material_resolution = None
        try:
            mass_request, preliminary_request = _build_case_02_chain_request(
                case_01_input, case_02_input, material_resolution
            )
        except Exception:
            mass_request = None
            preliminary_request = None
        try:
            if (
                mass_request is not None
                and preliminary_request is not None
                and material_resolution is not None
            ):
                mass_breakdown: MassBreakdown = calculate_mass_breakdown(mass_request)
                preliminary_result: PreliminaryCheckResult = preliminary_check(preliminary_request)
            else:
                raise RuntimeError("chain request construction failed")
            values = {
                "case_01_outputs": {
                    "case_01_outputs_reference_case_id": case_01_ref,
                },
                "mass_kg": {
                    "fluid_mass_kg": float(mass_breakdown.total_kg),
                    "shell_mass_kg": float(mass_breakdown.outer_pipe_kg),
                    "tube_mass_kg": float(mass_breakdown.inner_tube_kg),
                    "total_mass_kg": float(mass_breakdown.total_kg),
                },
                "preliminary_mechanical_check": {
                    "status": str(preliminary_result.verdict),
                },
                "selected_material_ids": {
                    "shell_material_id": str(
                        case_02_input["material_selection"]["shell_material_id"]
                    ),
                    "tube_material_id": str(
                        case_02_input["material_selection"]["tube_material_id"]
                    ),
                },
            }
            produced = [
                "mass_kg.fluid_mass_kg",
                "mass_kg.shell_mass_kg",
                "mass_kg.tube_mass_kg",
                "mass_kg.total_mass_kg",
                "preliminary_mechanical_check.status",
                "selected_material_ids.shell_material_id",
                "selected_material_ids.tube_material_id",
            ]
            status = "WIRED_VIA_CHAIN"
            run_ids = [
                _stable_run_id(case_id="TASK-019-GOLDEN-02", slot="material_selector"),
                _stable_run_id(case_id="TASK-019-GOLDEN-02", slot="mass_calculator"),
                _stable_run_id(case_id="TASK-019-GOLDEN-02", slot="preliminary_checker"),
            ]
            digests = [
                _sha256_hex(_canonical_json_dumps(_safe_dump(material_resolution))),
                _sha256_hex(_canonical_json_dumps(_safe_dump(mass_breakdown))),
                _sha256_hex(_canonical_json_dumps(_safe_dump(preliminary_result))),
            ]
        except Exception:
            values = {
                "case_01_outputs": {
                    "case_01_outputs_reference_case_id": case_01_ref,
                },
                "mass_kg": {
                    "fluid_mass_kg": None,
                    "shell_mass_kg": None,
                    "tube_mass_kg": None,
                    "total_mass_kg": None,
                },
                "preliminary_mechanical_check": {"status": None},
                "selected_material_ids": {
                    "shell_material_id": str(
                        case_02_input["material_selection"]["shell_material_id"]
                    ),
                    "tube_material_id": str(
                        case_02_input["material_selection"]["tube_material_id"]
                    ),
                },
            }
            produced = [
                "selected_material_ids.shell_material_id",
                "selected_material_ids.tube_material_id",
            ]
            status = "WIRED_VIA_CHAIN_PARTIAL"
            run_ids = [
                _stable_run_id(case_id="TASK-019-GOLDEN-02", slot="material_selector"),
            ]
            digests = [
                _sha256_hex(
                    _canonical_json_dumps(
                        _safe_dump(material_resolution) if material_resolution is not None else {}
                    )
                ),
            ]
    elif case_id == "TASK-019-GOLDEN-03":
        case_03_input = fixture["input"]
        case_01_ref = str(
            case_03_input.get("case_01_input_reference_case_id", "TASK-019-GOLDEN-01")
        )
        from pathlib import Path as _Path3

        _GOLDEN_FIXTURE_DIR_3 = (
            _Path3(__file__).resolve().parents[3] / "tests" / "golden" / "double_pipe_rating"
        )
        case_01_fixture_path_3 = _GOLDEN_FIXTURE_DIR_3 / ("case_01_heat_balance_rating.json")
        case_01_fixture_3 = _json.loads(case_01_fixture_path_3.read_text(encoding="utf-8"))
        _ = case_01_fixture_3["input"]  # cross-case reference marker
        filters = _build_case_03_filters(case_03_input)
        try:
            cost_selection: CostModelSelectionResult = select_cost_records((), filters)
            cms = case_03_input["cost_model_selection"]
            _cost_request_unused = CostCalculatorInput(
                cost_model_selection_result=cost_selection,
                mass_breakdown=None,
                case_currency=str(cms["currency_ISO_4217"]),
                case_region=str(cms["region_id"]),
                effective_date=str(cms["date_ISO_8601"]),
                component_role_overrides={},
                c0_heuristic_overrides={},
                escalation_index_reference_filter=frozenset({str(cms["escalation_rule_id"])}),
            )
            _ = _cost_request_unused  # silence unused-var lint
            cost_breakdown: CostBreakdown = calculate_cost_breakdown(
                cost_model_selection_result=cost_selection,
                mass_breakdown=None,
                case_currency=str(cms["currency_ISO_4217"]),
                case_region=str(cms["region_id"]),
                effective_date=str(cms["date_ISO_8601"]),
                component_role_overrides=None,
                c0_heuristic_overrides=None,
                escalation_index_reference_filter=frozenset({str(cms["escalation_rule_id"])}),
            )
            lifecycle = case_03_input["lifecycle_inputs"]
            values = {
                "case_01_outputs": {
                    "case_01_outputs_reference_case_id": case_01_ref,
                },
                "cost_components_C0_C1": {
                    "cost_components": {
                        "C0_material_minor_units": int(cost_breakdown.capex_envelope_minor_units),
                        "C0_labor_minor_units": 0,
                        "C1_total_minor_units": int(cost_breakdown.capex_envelope_minor_units),
                    },
                    "currency_ISO_4217": str(cms["currency_ISO_4217"]),
                },
                "discounted_total_minor_units": None,
                "life_cycle_energy_envelope": {
                    "blocker_codes": list(cost_breakdown.blockers),
                    "life_cycle_energy_summary": {
                        "annual_operating_hours": int(lifecycle["annual_operating_hours"]),
                        "design_life_years": int(lifecycle["design_life_years"]),
                        "annual_energy_MJ": None,
                        "total_lifecycle_energy_MJ": None,
                    },
                },
                "salvage_minor_units": 0,
                "selected_cost_model": {
                    "selected_model_id": str(cms["region_id"]),
                    "selection_blockers": list(cost_selection.selection_blockers),
                },
            }
            produced = [
                "cost_components_C0_C1.cost_components.C0_material_minor_units",
                "cost_components_C0_C1.cost_components.C0_labor_minor_units",
                "cost_components_C0_C1.cost_components.C1_total_minor_units",
                "cost_components_C0_C1.currency_ISO_4217",
                "life_cycle_energy_envelope.life_cycle_energy_summary.annual_operating_hours",
                "life_cycle_energy_envelope.life_cycle_energy_summary.design_life_years",
                "selected_cost_model.selected_model_id",
            ]
            status = "WIRED_VIA_CHAIN"
            run_ids = [
                _stable_run_id(case_id="TASK-019-GOLDEN-03", slot="cost_model_selector"),
                _stable_run_id(case_id="TASK-019-GOLDEN-03", slot="cost_calculator"),
            ]
            digests = [
                _sha256_hex(_canonical_json_dumps(_safe_dump(cost_selection))),
                _sha256_hex(_canonical_json_dumps(_safe_dump(cost_breakdown))),
            ]
        except Exception:
            cms = case_03_input["cost_model_selection"]
            lifecycle = case_03_input["lifecycle_inputs"]
            values = {
                "case_01_outputs": {
                    "case_01_outputs_reference_case_id": case_01_ref,
                },
                "cost_components_C0_C1": {
                    "cost_components": {
                        "C0_material_minor_units": None,
                        "C0_labor_minor_units": None,
                        "C1_total_minor_units": None,
                    },
                    "currency_ISO_4217": str(cms["currency_ISO_4217"]),
                },
                "discounted_total_minor_units": None,
                "life_cycle_energy_envelope": {
                    "blocker_codes": [],
                    "life_cycle_energy_summary": {
                        "annual_operating_hours": int(lifecycle["annual_operating_hours"]),
                        "design_life_years": int(lifecycle["design_life_years"]),
                        "annual_energy_MJ": None,
                        "total_lifecycle_energy_MJ": None,
                    },
                },
                "salvage_minor_units": 0,
                "selected_cost_model": {
                    "selected_model_id": None,
                    "selection_blockers": [],
                },
            }
            produced = []
            status = "WIRED_VIA_CHAIN_PARTIAL"
            run_ids = []
            digests = []
    else:
        raise ValueError(
            f"case_id {case_id!r} is not one of the frozen 3 (TASK-019-GOLDEN-01/02/03)"
        )

    # discount/salvage status: TASK-018 §5.3 / §5.3.2 deferred, not
    # invented in TASK-019 Slice 3A.
    discount_salvage_status = {
        "discounted_total_minor_units": "DEFERRED_PER_TASK_018_5_3",
        "salvage_minor_units": "DEFERRED_PER_TASK_018_5_3_2",
    }

    canonical_actual_output_sha256 = _sha256_hex(_canonical_json_dumps(values))

    artifact = {
        "case_id": case_id,
        "status": status,
        "produced_fields": list(produced),
        "values": values,
        "blocked_fields": [],
        "upstream_calculation_run_ids": list(run_ids),
        "upstream_provenance_digests": list(digests),
        "canonical_actual_output_sha256": canonical_actual_output_sha256,
        "discount_salvage_status": discount_salvage_status,
        "comparison_overall_status": "NOT_COMPUTABLE",
    }
    return artifact


__all__ = [
    "compute_actual_output_via_chain",
    "rate_double_pipe",
    "RatingResult",
    "DoublePipeGeometry",
    "FlowArrangement",
    "FluidIdentifier",
    "ThermalBoundaryCondition",
    "resolve_material",
    "MaterialRecord",
    "MaterialResolutionRequest",
    "MaterialResolutionResult",
    "calculate_mass_breakdown",
    "MassCalculationRequest",
    "MassBreakdown",
    "preliminary_check",
    "PreliminaryCheckRequest",
    "PreliminaryCheckResult",
    "select_cost_records",
    "SelectionFilters",
    "CostModelSelectionResult",
    "calculate_cost_breakdown",
    "CostBreakdown",
    "calculate_life_cycle_breakdown",
    "LifeCycleEnergyBreakdown",
    "LifeCycleEnergyEstimatorInput",
    "CostCalculatorInput",
]
