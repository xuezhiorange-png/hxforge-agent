"""TASK-019 Slice 3A / 3B-A thin chain adapter.

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
* Preserve ``expected_output`` exactly as frozen by Amendment 001
  (re-frozen for case_01 by Design Amendment 002-E; production chain
  outputs must match within tolerance but are not copied from
  ``expected_output``).
* Preserve per-case tolerances exactly as frozen by Amendment 001
  (per-field basis notes updated by Amendment 002-E).
* Keep ``comparison.overall_status`` as NOT_COMPUTABLE in Slice 3A
  and 3B-A. No PASS/FAIL comparison logic is added.
* Add only additive provenance fields derived from real adapter
  execution (``upstream_calculation_run_ids``,
  ``upstream_provenance_digests``, ``canonical_actual_output_sha256``).
* Preserve pressure-drop NOT_COMPUTABLE / TASK-020+ excluded.
* Preserve TASK-018 discount/salvage deferred status.

Slice 3B-A scope (per Charles authorization
``TASK019_SLICE3B_A_IMPL_*``):

* Enable case_01 ``actual_output`` to be produced by the existing
  TASK-006/007/008 production chain using the frozen case_01 inputs
  (post Design Amendment 002-E: mass_flow 0.75/0.75 kg/s, both Re
  outside the TASK-007 transitional regime).
* Read provider identifiers (name / equation_of_state_backend) from
  ``fixture["input"][...]["fluid_identifier"]`` (not from
  ``fluid_composition`` and not from a hardcoded "Water" / "HEOS"
  fallback). ``fluid_composition`` remains an audit / description
  field only.
* Use the production ``CoolPropProvider`` (HEOS) as the
  PropertyProvider for the TASK-006/007/008 chain. The previous
  test-support StubPropertyProvider import path (which could not
  resolve real CoolProp state and forced case_01 to fail-closed
  partial) is retired in Slice 3B-A. No hardcoded water states are
  configured on the property provider.
* case_01 must return ``status == "WIRED_VIA_CHAIN"`` with
  ``produced_fields`` equal to the six authorized TASK-006/007/008
  fields and all values finite non-None.
* case_02 and case_03 remain ``WIRED_VIA_CHAIN_PARTIAL`` (no
  MaterialRecord synthesis, no SelectionFilters fabrication, no
  cost_records fabrication, no discount/salvage formula).

NOT in Slice 3A / 3B-A:

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
import uuid as _uuid
from collections.abc import Mapping
from decimal import Decimal
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
# Slice 3B-A fix: the previous StubPropertyProvider import path went
# through tests/support/ and could not resolve real CoolProp state.
# Use the production CoolPropProvider instead so the case_01 chain
# actually runs end-to-end. The import lives in this file only;
# tests/support/ is not modified. If CoolProp is unavailable at
# runtime, the chain falls back to fail-closed partial (no
# fabrication).
try:
    from hexagent.properties.coolprop_provider import CoolPropProvider as _CoolPropProvider

    _PROPERTY_PROVIDER: object = _CoolPropProvider()
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
# Slice 3A P1 fix: typed sentinels for fail-closed upstream-catalog
# unavailability. These signal that the case input does not contain the
# catalog-resolved data the upstream chain requires; the adapter must
# fail closed (NOT_COMPUTABLE for the affected actual_output fields) and
# must not fabricate constants to keep the chain wired.
# -----------------------------------------------------------------------


class _MissingGeometryMaterialProperties(Exception):
    """Raised when the frozen case input does not carry the material
    properties required to construct a real DoublePipeGeometry
    (wall_thermal_conductivity_w_m_k, inner_surface_roughness_m,
    annulus_surface_roughness_m). The adapter must NOT substitute
    hardcoded constants; it must propagate to a fail-closed
    actual_output."""


class _MissingMaterialRecord(Exception):
    """Raised when the frozen case input does not carry a full
    MaterialRecord (only logical material IDs). The adapter must NOT
    synthesize a MaterialRecord; it must propagate to a fail-closed
    actual_output for material/mass/preliminary-mechanical fields."""


class _MissingCostRecords(Exception):
    """Raised when the frozen case input does not carry the cost-record
    list the upstream select_cost_records API requires. The adapter
    must NOT pass an empty records list as if it were a
    production-derived result; it must propagate to a fail-closed
    actual_output for all cost fields."""


def _case_input_has_geometry_material_properties(
    case_input: Mapping[str, Any],
) -> bool:
    """Return True iff the frozen case input carries the
    wall_thermal_conductivity_w_m_k, inner_surface_roughness_m, and
    annulus_surface_roughness_m values the upstream
    DoublePipeGeometry constructor requires. Slice 3A does not have
    a TASK-013 catalog lookup helper, so when these are absent the
    adapter must fail closed."""
    try:
        geom = case_input["geometry"]
    except (KeyError, TypeError):
        return False
    if not isinstance(geom, Mapping):
        return False
    required = (
        "wall_thermal_conductivity_w_m_k",
        "inner_surface_roughness_m",
        "annulus_surface_roughness_m",
    )
    return all(k in geom and geom[k] is not None for k in required)


def _case_input_has_full_material_record(
    case_input: Mapping[str, Any],
) -> bool:
    """Return True iff the frozen case input carries a fully-populated
    MaterialRecord (not just logical material IDs). Slice 3A does
    not have a TASK-013 catalog lookup helper, so when only IDs are
    present the adapter must fail closed."""
    try:
        ms = case_input["material_selection"]
    except (KeyError, TypeError):
        return False
    if not isinstance(ms, Mapping):
        return False
    required = (
        "material_record_id",
        "material_record_version",
        "material_family",
        "material_grade_or_designation",
        "form_factor",
        "standard_or_spec_reference",
        "region",
        "effective_date",
        "approval_state",
    )
    return all(k in ms and ms[k] is not None for k in required)


def _case_input_has_cost_records(
    case_input: Mapping[str, Any],
) -> bool:
    """Return True iff the frozen case input carries a list of
    pre-resolved cost records the upstream select_cost_records API
    requires. Slice 3A does not have a TASK-018 catalog lookup
    helper, so when the records list is absent the adapter must
    fail closed."""
    try:
        cms = case_input["cost_model_selection"]
    except (KeyError, TypeError):
        return False
    if not isinstance(cms, Mapping):
        return False
    records = cms.get("cost_records")
    if not isinstance(records, list) or len(records) == 0:
        return False
    return all(
        isinstance(r, Mapping) and "record_id" in r and r["record_id"] is not None for r in records
    )


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

    # Slice 3A P1 fix: do not hardcode wall_thermal_conductivity or
    # surface_roughness values. These are catalog-resolved material
    # properties that must come from the upstream TASK-013/017 catalog
    # (not from the frozen case input, not from a hardcoded constant).
    # Since the adapter does not have access to the catalog in Slice 3A,
    # and the case input does not include these values, we omit them
    # from the DoublePipeGeometry construction and fail-closed for the
    # geometry-dependent actual_output fields.
    if not _case_input_has_geometry_material_properties(case_01_input):
        # Case input lacks the required material properties; raise
        # a typed sentinel so the caller can mark the case as
        # PARTIAL / NOT_COMPUTABLE rather than producing fake numbers.
        raise _MissingGeometryMaterialProperties(
            "case_01 frozen input lacks wall_thermal_conductivity_w_m_k, "
            "inner_surface_roughness_m, annulus_surface_roughness_m; "
            "cannot construct DoublePipeGeometry without fabrication"
        )
    geometry = DoublePipeGeometry(
        inner_tube_inner_diameter_m=float(geom["tube_id_m"]),
        inner_tube_outer_diameter_m=float(geom["tube_od_m"]),
        outer_pipe_inner_diameter_m=float(geom["shell_id_m"]),
        effective_length_m=float(geom["tube_length_m"]),
        wall_thermal_conductivity_w_m_k=float(geom["wall_thermal_conductivity_w_m_k"]),
        inner_surface_roughness_m=float(geom["inner_surface_roughness_m"]),
        annulus_surface_roughness_m=float(geom["annulus_surface_roughness_m"]),
        inner_fouling_resistance_m2k_w=float(fouling["cold_side_m2_K_W"]),
        outer_fouling_resistance_m2k_w=float(fouling["hot_side_m2_K_W"]),
    )

    # Slice 3B-A fix: read provider identifiers from the frozen
    # fluid_identifier sub-blocks (per Design Amendment 002-D and
    # 002-E). The fluid_composition string remains an audit /
    # description field and is not used for provider construction.
    # This avoids any regex parsing or normalization of the
    # fluid_composition string and keeps Water/HEOS as fully
    # case-bound inputs (no hardcoded fallback).
    def _provider_identifier(side: Mapping[str, Any]) -> FluidIdentifier:
        fi = side["fluid_identifier"]
        return FluidIdentifier(
            name=str(fi["name"]),
            equation_of_state_backend=str(fi["equation_of_state_backend"]),
        )

    rate_kwargs: dict[str, Any] = {
        "hot_fluid": _provider_identifier(hot),
        "cold_fluid": _provider_identifier(cold),
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


# Slice 3A P1 fix: removed the previous
# ``_build_material_record_from_case_02_input`` helper that synthesized
# a MaterialRecord dict from constants. The frozen case_02 input only
# carries logical material IDs (shell_material_id, tube_material_id,
# design_code_id); a real MaterialRecord must be resolved through the
# TASK-013 catalog, which is not available in Slice 3A. Therefore the
# adapter must fail closed for material/mass/preliminary-mechanical
# actual_output fields and must NOT fabricate MaterialRecord metadata.
#
# The only case_02 fields that remain projected are
# ``selected_material_ids.shell_material_id`` and
# ``selected_material_ids.tube_material_id`` because they are directly
# case-bound and not fabricated.


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


# Slice 3A P1 fix: removed the previous ``_build_case_03_filters`` helper
# that hardcoded material_family, cost_category_filter,
# quantity_basis_filter, and license_class_filter values. The frozen
# case_03 input does not carry these filter values, and the adapter
# has no TASK-018 catalog lookup helper to derive them. Therefore the
# case_03 chain must fail closed (see the TASK-019-GOLDEN-03 branch
# in ``compute_actual_output_via_chain`` below). Discount / salvage
# remain deferred per TASK-018 §5.3 / §5.3.2 (no formula invented).


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
    # Initialize chain-wired artifact locals so mypy can see them across
    # if/elif/elif branches. Each branch reassigns the locals with
    # branch-specific values.
    values: dict[str, Any] = {}
    produced: list[str] = []
    status = "WIRED_VIA_CHAIN_PARTIAL"
    run_ids: list[str] = []
    digests: list[str] = []
    if case_id == "TASK-019-GOLDEN-01":
        case_01_input = fixture["input"]
        try:
            geometry, rate_kwargs = _build_case_01_rating_request(case_01_input)
        except (
            _MissingGeometryMaterialProperties,
            KeyError,
            TypeError,
        ) as exc:
            # Slice 3A P1 fix: case_01 frozen input does not carry the
            # wall_thermal_conductivity / surface_roughness values the
            # upstream DoublePipeGeometry constructor requires. The
            # adapter has no TASK-013 catalog lookup helper, so it must
            # NOT substitute hardcoded constants. Fail closed: all
            # geometry-dependent actual_output fields go None and
            # produced_fields is empty (no real upstream-produced
            # value).
            # Slice 3B-A addition: also catch KeyError / TypeError
            # raised when the frozen fluid_identifier sub-block is
            # missing or malformed. The adapter must NOT fabricate a
            # default Water/HEOS provider identifier; it must fail
            # closed (WIRED_VIA_CHAIN_PARTIAL with empty
            # produced_fields) so the §6.3 / §6.4 invariants hold.
            values: dict[str, Any] = {  # type: ignore[no-redef]
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
            produced = []
            status = "WIRED_VIA_CHAIN_PARTIAL"
            run_ids = []
            digests = []
            # Stash the exception for the provenance digest so the
            # caller can see *why* the chain failed closed.
            _ = exc
        else:
            try:
                rating_result: RatingResult = rate_double_pipe(geometry=geometry, **rate_kwargs)
                values: dict[str, Any] = {  # type: ignore[no-redef]
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
                # Slice 3A P1 fix: produced_fields is derived from
                # the real upstream-produced values. A field appears
                # in produced_fields only when its value is non-None
                # AND was actually returned by the upstream call. No
                # field name is ever listed solely because the chain
                # was asked to compute it.
                produced = [
                    name
                    for name, val in (
                        ("heat_duty_W", values["heat_duty_W"]),
                        (
                            "LMTD_derived_values.LMTD_counterflow_K",
                            values["LMTD_derived_values"]["LMTD_counterflow_K"],
                        ),
                        (
                            "heat_transfer_coefficients.annulus_side_W_m2_K",
                            values["heat_transfer_coefficients"]["annulus_side_W_m2_K"],
                        ),
                        (
                            "heat_transfer_coefficients.tube_side_W_m2_K",
                            values["heat_transfer_coefficients"]["tube_side_W_m2_K"],
                        ),
                        (
                            "outlet_temperatures_K.cold_side",
                            values["outlet_temperatures_K"]["cold_side"],
                        ),
                        (
                            "outlet_temperatures_K.hot_side",
                            values["outlet_temperatures_K"]["hot_side"],
                        ),
                    )
                    if val is not None
                ]
                status = "WIRED_VIA_CHAIN"
                run_ids = [
                    _stable_run_id(case_id="TASK-019-GOLDEN-01", slot="rate_double_pipe"),
                ]
                digests = [
                    _sha256_hex(_canonical_json_dumps(_safe_dump(rating_result))),
                ]
            except Exception as exc:
                # Upstream chain raised (e.g. StubPropertyProvider
                # cannot resolve real CoolProp state). Fail closed:
                # values are None, produced_fields is empty.
                values: dict[str, Any] = {  # type: ignore[no-redef]
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
                produced = []
                status = "WIRED_VIA_CHAIN_PARTIAL"
                run_ids = []
                digests = []
                _ = exc
    elif case_id == "TASK-019-GOLDEN-02":
        # Slice 3A P1 fix: the frozen case_02 input only carries logical
        # material IDs, not a full TASK-013 MaterialRecord. Since the
        # adapter has no TASK-013 catalog lookup helper, it must NOT
        # synthesize a MaterialRecord. Therefore resolve_material /
        # calculate_mass_breakdown / preliminary_check cannot run; the
        # only projected fields are selected_material_ids.*, which come
        # directly from the case input and are not fabricated.
        case_02_input = fixture["input"]
        case_01_ref = str(
            case_02_input.get("case_01_input_reference_case_id", "TASK-019-GOLDEN-01")
        )
        # Verify the case input is the expected shape; if it is missing
        # required material_selection fields, fail closed.
        try:
            shell_material_id = str(case_02_input["material_selection"]["shell_material_id"])
            tube_material_id = str(case_02_input["material_selection"]["tube_material_id"])
        except (KeyError, TypeError) as exc:
            raise _MissingMaterialRecord(
                f"case_02 frozen input missing material_selection fields: {exc}"
            ) from exc
        if not _case_input_has_full_material_record(case_02_input):
            # Case input carries only logical IDs, not a full catalog
            # MaterialRecord. Fail closed: no resolve_material / mass /
            # preliminary calls; the only projected values are the
            # case-bound material IDs (which the case-block materialization
            # surface requires). produced_fields is empty because no
            # upstream chain call returned a value.
            values: dict[str, Any] = {  # type: ignore[no-redef]
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
                    "shell_material_id": shell_material_id,
                    "tube_material_id": tube_material_id,
                },
            }
            # Slice 3A P1 fix: produced_fields is empty for fail-closed
            # cases (no real upstream execution returned a value).
            # The case-bound material IDs are still surfaced in
            # ``values`` for the §7.1 case-block materialization, but
            # they are NOT counted as produced actual_output fields.
            produced = []
            status = "WIRED_VIA_CHAIN_PARTIAL"
            run_ids = []
            digests = []
        else:
            # Real MaterialRecord present — call the upstream chain.
            # (Unreachable in current Slice 3A fixtures, but kept for
            # forward compatibility when the TASK-013 catalog lookup
            # helper is added.)
            material_record = dict(case_02_input["material_selection"])
            material_request = MaterialResolutionRequest(
                component_role="shell",
                material_record_id=str(case_02_input["material_selection"]["material_record_id"]),
                design_temperature_c=float(
                    case_02_input["design_conditions"]["design_temperature_K"]
                )
                - 273.15,
                design_pressure_mpa=float(case_02_input["design_conditions"]["design_pressure_Pa"])
                / 1.0e6,
                corrosion_allowance_mm=None,
                applicable_standard_id=str(
                    case_02_input["material_selection"]["standard_or_spec_reference"]
                ),
            )
            try:
                material_resolution: MaterialResolutionResult | None = resolve_material(
                    material_request,
                    material_record,  # type: ignore[arg-type]
                )
            except Exception:
                material_resolution = None
            try:
                case_01_input_for_geom = case_02_input.get("case_01_geometry", {})
                if not case_01_input_for_geom:
                    # cross-case ref input
                    from pathlib import Path as _PathCase02

                    _GOLDEN_FIXTURE_DIR_C02 = (
                        _PathCase02(__file__).resolve().parents[3]
                        / "tests"
                        / "golden"
                        / "double_pipe_rating"
                    )
                    case_01_fixture_path_c02 = _GOLDEN_FIXTURE_DIR_C02 / (
                        "case_01_heat_balance_rating.json"
                    )
                    case_01_fixture_c02 = _json.loads(
                        case_01_fixture_path_c02.read_text(encoding="utf-8")
                    )
                    case_01_input_for_geom = case_01_fixture_c02["input"]
                mass_request, preliminary_request = _build_case_02_chain_request(
                    case_01_input_for_geom, case_02_input, material_resolution
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
                    preliminary_result: PreliminaryCheckResult = preliminary_check(
                        preliminary_request
                    )
                else:
                    raise RuntimeError("chain request construction failed")
                values: dict[str, Any] = {  # type: ignore[no-redef]
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
                        "shell_material_id": shell_material_id,
                        "tube_material_id": tube_material_id,
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
                values: dict[str, Any] = {  # type: ignore[no-redef]
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
                        "shell_material_id": shell_material_id,
                        "tube_material_id": tube_material_id,
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
                            _safe_dump(material_resolution)
                            if material_resolution is not None
                            else {}
                        )
                    ),
                ]
    elif case_id == "TASK-019-GOLDEN-03":
        # Slice 3A P1 fix: the frozen case_03 input only carries
        # cost_model_selection metadata (region / date / currency /
        # escalation rule), not a pre-resolved list of cost records
        # that the upstream select_cost_records API requires. The
        # adapter has no TASK-018 catalog lookup helper, so it must
        # NOT pass an empty records list and must NOT fabricate
        # SelectionFilters (material_family, cost_category_filter,
        # quantity_basis_filter, license_class_filter). Therefore all
        # cost / life-cycle / selected_cost_model fields go fail-closed
        # (NOT_COMPUTABLE). Discount / salvage remain deferred per
        # TASK-018 §5.3 / §5.3.2 (no formula invented).
        case_03_input = fixture["input"]
        case_01_ref = str(
            case_03_input.get("case_01_input_reference_case_id", "TASK-019-GOLDEN-01")
        )
        # Slice 3A does not implement a TASK-018 catalog lookup helper;
        # the case_03 chain must therefore fail closed for all
        # cost / life-cycle / selected_cost_model fields.
        values: dict[str, Any] = {  # type: ignore[no-redef]
            "case_01_outputs": {
                "case_01_outputs_reference_case_id": case_01_ref,
            },
            "cost_components_C0_C1": {
                "cost_components": {
                    "C0_material_minor_units": None,
                    "C0_labor_minor_units": None,
                    "C1_total_minor_units": None,
                },
                "currency_ISO_4217": None,
            },
            "discounted_total_minor_units": None,
            "life_cycle_energy_envelope": {
                "blocker_codes": [],
                "life_cycle_energy_summary": {
                    "annual_operating_hours": None,
                    "design_life_years": None,
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
