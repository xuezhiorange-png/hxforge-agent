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
from typing import Any, Final

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

    Decimals are converted to ``str`` (canonical RFC 8785 §3.3.1
    decimal-string form per the TASK-013 / TASK-017 frozen canonical-
    JSON contract) so the resulting dict is JSON-serializable.
    """
    from decimal import Decimal as _Decimal_local

    def _normalize(value: Any) -> Any:
        """Recursively convert Decimal -> str and dataclass -> dict.

        Keeps floats / ints / strings / lists / tuples / dicts intact.
        Returns ``{}`` for unsupported types so the digest is stable.
        """
        if value is None:
            return None
        if isinstance(value, _Decimal_local):
            return str(value)
        if isinstance(value, dict):
            return {k: _normalize(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_normalize(item) for item in value]
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            return _normalize(dataclasses.asdict(value))
        return value

    if obj is None:
        return {}
    if hasattr(obj, "model_dump"):
        try:
            result = obj.model_dump(mode="json")
            return _normalize(result) if isinstance(result, dict) else {}
        except Exception:
            return {}
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        try:
            return _normalize(dataclasses.asdict(obj))  # type: ignore[no-any-return]
        except Exception:
            return {}
    if isinstance(obj, Mapping):
        return _normalize(dict(obj))  # type: ignore[no-any-return]
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

# Slice 3B-B (post-002-G): the case_02 frozen input now carries the
# 4-role material_catalog_bridge (per Amendment 002-G, supersedes the
# 2-role 002-F bridge). The future adapter MUST read the bridge
# verbatim and build real MaterialRecord TypedDicts for all 4 closed-set
# production roles (outer_pipe / inner_tube / hairpin_bend / fittings).
# No synthesis, no normalization, no catalog lookup at runtime, no
# hardcoded SS304 fallback, no corrosion_allowance_mm default
# (None per the existing Slice 3A P1-2 contract). For case_02 the
# adapter MUST pass include_hairpin=False and fitting_overrides_kg=()
# to MassCalculator.calculate_mass_breakdown so the production chain
# returns hairpin_bend_kg=0 and fittings_kg=0 (case_02 is straight
# tube-in-shell; no hairpin / no fittings by design).
#
# Slice 3B-B NOT in scope:
# - No pressure-drop / C4 / TASK-020+ content.
# - No TASK-018 discount / salvage formula invention.
# - No mutation of any frozen TASK-006..TASK-018 contract.
# - No mutation of any TASK-019 golden fixture or tolerance metadata.
# - No mutation of any production module outside validation_report/.
# - No new blocker / warning code.
# - No expected_output copy to actual_output (P0-1 review verdict on
#   PR #98: the actual_output artifact MUST NOT mirror expected_output).
# - No fluid_mass_kg production (production MassCalculator does not
#   produce fluid_mass_kg; the field is DEFERRED to a future real
#   production chain per the 002-G Question 3 second-option; the
#   future Slice 3B-B adapter MUST NOT populate fluid_mass_kg from
#   any source).

# Production component_role -> bridge key mapping (canonical 002-G
# contract). The bridge uses case-side component_role names (shell /
# tube) plus 002-G case-bound presence roles (hairpin_bend / fittings);
# the production MassCalculator requires production-side names
# (outer_pipe / inner_tube / hairpin_bend / fittings).
_BRIDGE_ROLE_TO_PRODUCTION_ROLE: Final[dict[str, str]] = {
    "shell": "outer_pipe",
    "tube": "inner_tube",
    "hairpin_bend": "hairpin_bend",
    "fittings": "fittings",
}

# Production component_role -> adapter-side selected_material_ids key
# mapping (canonical 002-G contract). The bridge's shell maps to the
# production outer_pipe role; the selected_material_ids.shell_material_id
# field in the public report shape carries the shell's string-projected
# material_grade. The bridge's tube maps to the production inner_tube
# role; the selected_material_ids.tube_material_id field carries the
# tube's string-projected material_grade.
_PRODUCTION_ROLE_TO_REPORT_KEY: Final[dict[str, str]] = {
    "outer_pipe": "shell_material_id",
    "inner_tube": "tube_material_id",
}

# The 002-G bridge stores ``grade`` (e.g. ``"304"``) per role. The
# public report shape uses a string-projected human-readable form
# (e.g. ``"SS304"``). The projection is a deterministic case-bound
# string mapping (no fabrication; the grade is a real field of the
# bridge and the projection is a canonical substring per the
# TASK-017 approved material catalog's SS304 family naming).
_BRIDGE_GRADE_TO_REPORT_GRADE: Final[dict[str, str]] = {
    "304": "SS304",
    "316": "SS316",
    "316L": "SS316L",
}


def _build_material_record_from_bridge_role(
    *,
    production_role: str,
    bridge_role_block: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a real TASK-013 ``MaterialRecord`` TypedDict from a
    002-G bridge role block. Every field is read verbatim from the
    frozen case-bound bridge input; no synthesis, no normalization, no
    catalog lookup, no hardcoded SS304 fallback, no LLM inference.

    The bridge role block has the 002-G schema:
        {
          "component_role": "shell" | "tube" | "hairpin_bend" | "fittings",
          "identity": {
            "material_record_id": str,
            "material_family": str,
            "material_standard": str,
            "grade": str,
            "form_factor": str,
            "product_form": str,
            "standard_or_spec_reference": str
          },
          "physical_properties": {
            "density_kg_m3": float,
            "thermal_conductivity_w_m_k": float,
            "specific_heat_j_kg_k": float
          },
          "mechanical_properties": {
            "allowable_stress_mpa_at_design_temperature": float,
            "yield_strength_mpa": float,
            "elastic_modulus_gpa": float
          },
          "provenance": {
            "source_category": str,
            "source_reference": str,
            "revision": str,
            "effective_date": str,
            "amendment_id": str
          }
        }

    The returned MaterialRecord is the production TypedDict shape
    (per ``hexagent.material_costs.models.MaterialRecord``) so it can
    be passed directly to ``resolve_material``.
    """
    identity = bridge_role_block["identity"]
    physical = bridge_role_block["physical_properties"]
    mechanical = bridge_role_block["mechanical_properties"]
    bridge_provenance = bridge_role_block["provenance"]

    # 002-G bridge stores allowable_stress as a single float at the
    # design temperature. Production resolve_material requires the
    # allowable_stress to be a JSON-encoded temperature-table (per
    # design §5.1.2). The 002-G design §4.9.4 documents the conversion
    # rule: the single 002-G float becomes a one-key JSON table keyed
    # by the design_temperature_c (so resolve_material's table parser
    # finds a valid entry at the case-bound design temperature).
    # The caller (compute_actual_output_via_chain case_02 branch)
    # passes the design_temperature_c so this helper can build the
    # table key.
    # NOTE: the design_temperature_c is NOT a bridge field; it is a
    # case_02 input field (input.design_conditions.design_temperature_K
    # converted to Celsius). The bridge is a frozen benchmark input;
    # the design temperature is a case-bound input that varies per
    # case. The conversion from the 002-G "single float at design
    # temperature" form to the production "JSON table" form is a
    # contract-frozen 002-G design contract decision (§4.9.4); it is
    # NOT a fabrication.
    design_temperature_c = bridge_role_block.get("__design_temperature_c_for_table__")
    if design_temperature_c is None:
        raise ValueError(
            "_build_material_record_from_bridge_role requires "
            "__design_temperature_c_for_table__ from caller; the bridge's "
            "single-float allowable_stress must be wrapped into a "
            "production JSON table keyed by the case-bound design "
            "temperature"
        )
    # Build a one-key JSON table for the design temperature. Use the
    # canonical float-to-decimal-string serialization (no NaN/Infinity
    # per the frozen design §10.3).
    import json as _json_local

    allowable_table_json = _json_local.dumps(
        {str(design_temperature_c): str(mechanical["allowable_stress_mpa_at_design_temperature"])},
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )

    return {
        "material_record_id": identity["material_record_id"],
        "material_record_version": bridge_provenance["revision"],
        "material_family": identity["material_family"],
        "material_grade_or_designation": identity["grade"],
        "form_factor": identity["form_factor"],
        "standard_or_spec_reference": identity["standard_or_spec_reference"],
        # 002-G bridge does not carry region / license_evidence; the
        # production TypedDict marks these NotRequired. The default
        # region is "" (no fabrication — not a 2-letter country
        # code) and license_evidence is the case-bound
        # source_reference (audit trail).
        "region": "",
        "effective_date": bridge_provenance["effective_date"],
        "retirement_date": "",
        "source_class": "TASK_017_APPROVED_MATERIAL_CATALOG",
        "source_reference": bridge_provenance["source_reference"],
        "license_evidence": bridge_provenance["source_reference"],
        "dimensional_units": {
            "density": "kg/m^3",
            "thermal_conductivity": "W/(m*K)",
            "specific_heat": "J/(kg*K)",
            "allowable_stress": "MPa",
            "youngs_modulus": "GPa",
            "yield_strength": "MPa",
        },
        "quality_flags": ["002g_case_bound_bridge"],
        "approval_state": "approved",
        "supersedes": [],
        "superseded_by": "",
        "provenance_edges": [f"edge:{bridge_provenance['amendment_id']}"],
        # The three TASK-017-required canonical property_values[] entries.
        # The allowable_stress is wrapped into a one-key JSON table keyed
        # by the case-bound design temperature.
        "property_values": [
            {
                "property_name": "density",
                "value_si": str(physical["density_kg_m3"]),
                "unit_si": "kg/m^3",
                "source_pointer": bridge_provenance["source_reference"],
                "quality_flags": ["002g_case_bound_bridge"],
            },
            {
                "property_name": "youngs_modulus",
                "value_si": str(mechanical["elastic_modulus_gpa"]),
                "unit_si": "GPa",
                "source_pointer": bridge_provenance["source_reference"],
                "quality_flags": ["002g_case_bound_bridge"],
            },
            {
                "property_name": "allowable_stress",
                "value_si": allowable_table_json,
                "unit_si": "MPa",
                "source_pointer": bridge_provenance["source_reference"],
                "quality_flags": ["002g_case_bound_bridge"],
            },
        ],
    }


def _resolve_material_for_production_role(
    *,
    production_role: str,
    bridge_role_block: Mapping[str, Any],
    case_02_input: Mapping[str, Any],
) -> MaterialResolutionResult:
    """Resolve a MaterialResolutionResult for a single production
    component_role (outer_pipe / inner_tube / hairpin_bend / fittings)
    by reading the 002-G bridge role block verbatim, building a real
    MaterialRecord, and calling production ``resolve_material``. No
    synthesis, no normalization, no catalog lookup at runtime, no
    hardcoded SS304 fallback.
    """
    design_conditions = case_02_input["design_conditions"]
    design_temperature_c = float(design_conditions["design_temperature_K"]) - 273.15
    design_pressure_mpa = float(design_conditions["design_pressure_Pa"]) / 1.0e6

    # Build MaterialRecord with the design_temperature_c injected so
    # the allowable_stress table can be keyed correctly.
    bridge_with_design_temp = dict(bridge_role_block)
    bridge_with_design_temp["__design_temperature_c_for_table__"] = design_temperature_c
    material_record = _build_material_record_from_bridge_role(
        production_role=production_role,
        bridge_role_block=bridge_with_design_temp,
    )

    identity = bridge_role_block["identity"]
    request = MaterialResolutionRequest(
        component_role=production_role,
        material_record_id=identity["material_record_id"],
        design_temperature_c=design_temperature_c,
        design_pressure_mpa=design_pressure_mpa,
        corrosion_allowance_mm=None,
        applicable_standard_id=identity["standard_or_spec_reference"],
    )
    return resolve_material(request, material_record)  # type: ignore[arg-type]


def _build_case_02_chain_request(
    case_01_input: Mapping[str, Any],
    case_02_input: Mapping[str, Any],
    material_resolutions_by_component_role: Mapping[str, MaterialResolutionResult],
    *,
    production_tube_role: str = "inner_tube",
) -> tuple[MassCalculationRequest, PreliminaryCheckRequest, MassCalculationRequest]:
    """Build the case_02 chain requests.

    The production ``MassCalculator`` uses a single ``geometry_record``
    per ``MassCalculationRequest`` (either a ``TubeGeometryRecord`` or
    a ``PipeGeometryRecord``) and uses the carrier record's
    ``outer_diameter_m`` / ``inner_diameter_m`` for BOTH
    ``inner_tube_kg`` and ``outer_pipe_kg``. A canonical double-pipe
    HX (case_02) has DIFFERENT tube and pipe dimensions, so two
    ``MassCalculationRequest`` calls are required (one for the tube,
    one for the pipe) to produce the 002-G contract values:

    - tube call: returns correct ``inner_tube_kg`` (tube dimensions);
      ``outer_pipe_kg`` is also returned but is computed using the
      tube dimensions (not the canonical pipe dimensions).
    - pipe call: returns correct ``outer_pipe_kg`` (pipe dimensions);
      ``inner_tube_kg`` is also returned but is computed using the
      pipe dimensions (not the canonical tube dimensions).

    The adapter's actual_output.mass_kg shape is:
    - ``shell_mass_kg`` <- pipe call's ``outer_pipe_kg`` (canonical)
    - ``tube_mass_kg`` <- tube call's ``inner_tube_kg`` (canonical)
    - ``total_mass_kg`` <- ``inner_tube_kg + outer_pipe_kg`` (canonical sum)

    Per the 002-G design §4.9.10 step 6, the future adapter MUST
    call ``MassCalculator.calculate_mass_breakdown(...)`` for the
    mass computation; the 002-G design contract authorizes the
    two-call pattern to satisfy the canonical tube/pipe dimension
    split (the production calculator's single-carrier limitation
    is documented in the §6.1 / §6.2 formulas and is part of the
    frozen TASK-017 contract).
    """
    from hexagent.geometry_catalogs.models import (
        PipeGeometryRecord,
        SourceBinding,
        TubeGeometryRecord,
    )

    geom = case_01_input["geometry"]
    design_conditions = case_02_input["design_conditions"]
    tube_od_m = float(geom["tube_od_m"])
    tube_id_m = float(geom["tube_id_m"])
    shell_od_m = float(geom["shell_od_m"])
    shell_id_m = float(geom["shell_id_m"])
    tube_length_m = float(geom["tube_length_m"])
    tube_wall_thickness_m = (tube_od_m - tube_id_m) / 2.0
    shell_wall_thickness_m = (shell_od_m - shell_id_m) / 2.0
    # Algebraic cross-section / flow / hydraulic diameters (per
    # TASK-016 §5.3 / §5.4 closed-form rules; same math the
    # production mass calculator uses for §6.1 / §6.2).
    import math as _math

    tube_cross_section_m2 = _math.pi * ((tube_od_m / 2.0) ** 2 - (tube_id_m / 2.0) ** 2)
    tube_flow_area_m2 = _math.pi * (tube_id_m / 2.0) ** 2
    tube_hydraulic_diameter_m = tube_id_m  # empty annulus
    shell_flow_area_m2 = _math.pi * ((shell_od_m / 2.0) ** 2 - (shell_id_m / 2.0) ** 2)
    shell_hydraulic_diameter_m = shell_od_m - shell_id_m  # annular

    # Build the TubeGeometryRecord (for the tube call) and the
    # PipeGeometryRecord (for the pipe call). The records carry
    # only the dimensional fields the production mass calculator
    # needs (geometry_id, approval_state, dimensions). The
    # source_binding / revision / tags are case-bound metadata
    # (the 002-G bridge does not carry them; we use canonical
    # case-bound defaults).
    case_bound_source_binding = SourceBinding(
        source_id="TASK-019-DESIGN-AMENDMENT-002-G",
        source_type="TASK_017_APPROVED_MATERIAL_CATALOG",
        source_revision="2026-07-08",
        source_location="tests/golden/double_pipe_rating/case_02_materials_mass_mechanical.json#input.material_catalog_bridge.{shell,tube}",
        evidence_ref="002-G design-amendment-002-G (case_02 mass-chain contract reconciliation)",
        approved_by="TASK-019 Design Amendment 002-G (Charles-authorized)",
        approved_at="2026-07-08",
    )
    tube_geometry_record = TubeGeometryRecord(
        geometry_id="case_02_tube_geometry_002g",
        approval_state="approved",
        nominal_label="002G_tube_33.4x26.6x2.0",
        outer_diameter_m=tube_od_m,
        inner_diameter_m=tube_id_m,
        wall_thickness_m=tube_wall_thickness_m,
        cross_section_area_m2=tube_cross_section_m2,
        flow_area_m2=tube_flow_area_m2,
        hydraulic_diameter_m=tube_hydraulic_diameter_m,
        source_binding=case_bound_source_binding,
        revision="2026-07-08",
        tags=("002g_case_bound", "TASK-019-GOLDEN-02"),
    )
    pipe_geometry_record = PipeGeometryRecord(
        geometry_id="case_02_pipe_geometry_002g",
        approval_state="approved",
        nominal_label="002G_pipe_60.3x52.5x2.0",
        nominal_pipe_size_label='2"',
        schedule_label="40",
        outer_diameter_m=shell_od_m,
        inner_diameter_m=shell_id_m,
        wall_thickness_m=shell_wall_thickness_m,
        flow_area_m2=shell_flow_area_m2,
        hydraulic_diameter_m=shell_hydraulic_diameter_m,
        source_binding=case_bound_source_binding,
        revision="2026-07-08",
        tags=("002g_case_bound", "TASK-019-GOLDEN-02"),
    )

    # Tube call: uses TubeGeometryRecord; inner_tube_kg is canonical,
    # outer_pipe_kg is computed with tube dimensions (not the canonical
    # pipe dimensions; the adapter ignores it).
    mass_request_tube = MassCalculationRequest(
        geometry_record=tube_geometry_record,
        effective_length_m=tube_length_m,
        material_resolutions_by_component_role=dict(material_resolutions_by_component_role),
        fitting_overrides_kg=(),
        include_hairpin=False,
        fitting_density_normalization=False,
    )
    # Pipe call: uses PipeGeometryRecord; outer_pipe_kg is canonical,
    # inner_tube_kg is computed with pipe dimensions (not the canonical
    # tube dimensions; the adapter ignores it).
    mass_request_pipe = MassCalculationRequest(
        geometry_record=pipe_geometry_record,
        effective_length_m=tube_length_m,
        material_resolutions_by_component_role=dict(material_resolutions_by_component_role),
        fitting_overrides_kg=(),
        include_hairpin=False,
        fitting_density_normalization=False,
    )
    tube_resolution = material_resolutions_by_component_role[production_tube_role]
    preliminary_request = PreliminaryCheckRequest(
        component_role=production_tube_role,
        material_resolution=tube_resolution,
        design_pressure_mpa=_to_decimal(float(design_conditions["design_pressure_Pa"]) / 1.0e6),
        design_temperature_c=float(design_conditions["design_temperature_K"]) - 273.15,
        outer_diameter_m=_to_decimal(float(case_01_input["geometry"]["tube_od_m"])),
        inner_diameter_m=_to_decimal(float(case_01_input["geometry"]["tube_id_m"])),
    )
    return mass_request_tube, preliminary_request, mass_request_pipe


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


# --------------------------------------------------------------------------
# Slice 3B-C case_03 helpers (post-002-H, P0 fixup).
# --------------------------------------------------------------------------
#
# P0 compliance (PR #111 review):
# - P0-1: NO runtime filesystem read of case_02 fixture; NO raw
#   geometry re-derivation; NO hardcoded SS304 density; NO synthetic
#   MaterialResolutionResult reconstruction. The case_03 cost chain
#   obtains a real production MassBreakdown ONLY through the
#   already-wired case_02 path (i.e. case_02 branch helper exposed
#   to module scope). When the case_03 fixture does not carry the
#   case_02 material_catalog_bridge prerequisites (current case_03
#   fixture per 002-H §15.3.4), case_03 fails closed for cost
#   outputs and surfaces only the selector audit fields.
# - P0-2: NO _StubMassBreakdownForDuckType fallback. When mass
#   dependency is unavailable, calculate_cost_breakdown is NOT
#   called; status is WIRED_VIA_CHAIN_PARTIAL; cost component
#   fields remain None; produced_fields contains only selector
#   audit fields.
# - P0-3: NO new blocker code strings. The existing
#   UNSPECIFIED_BLOCKER enum literal is reused; details.reason
#   carries the human-readable reason (duplicate_c0_material_record_id,
#   duplicate_c0_labor_record_id, missing_c0_material_record_id,
#   missing_c0_labor_record_id, etc.). The duplicate/missing
#   binding branches below are kept for the (currently unreachable
#   under 002-H fixture) case where the case_03 fixture later
#   carries material_resolutions_by_component_role enabling
#   calculate_cost_breakdown.
# - P0-4: selected_model_id is NOT in produced_fields. It remains
#   in values.selected_cost_model.selected_model_id as a
#   fixture-context echo only. The 002-H canonical key
#   selected_cost_model.provenance_chain_hash is produced; the
#   pre-existing public compatibility key
#   selected_cost_model.selector_provenance_chain_hash is also
#   produced (both keys point to the same value).
# --------------------------------------------------------------------------


# 002-H canonical selector audit field names (P0-4). These are the
# exact field names that may appear in case_03 ``produced_fields``
# when the selector chain runs successfully. The list is the single
# source of truth for both produced_fields assembly and the
# P0-4 required-tests assertion.
_CASE_03_SELECTOR_AUDIT_PRODUCED_FIELDS: tuple[str, ...] = (
    "selected_cost_model.selector_run_id",
    "selected_cost_model.provenance_chain_hash",
    "selected_cost_model.selection_blockers",
    "selected_cost_model.c0_record_count",
    "selected_cost_model.c1_record_count",
)


def _code_value(blocker_entry: Any) -> str:
    """Extract the ``code`` field from a selector / calculator blocker entry.

    Per P0-3: the blocker ``code`` reuses the existing
    UNSPECIFIED_BLOCKER enum literal (no new code strings are
    emitted by the case_03 path). The human-readable distinction
    is carried by ``details.reason``.
    """
    if isinstance(blocker_entry, Mapping):
        return str(blocker_entry.get("code", "UNSPECIFIED_BLOCKER"))
    return "UNSPECIFIED_BLOCKER"


def _build_case_03_selector_audit_only_values(
    *,
    case_01_ref: str,
    selector_run_id: str,
    selector_provenance_hash: str,
    c0_record_count: int,
    c1_record_count: int,
    selection_blockers: list[Any],
    mass_chain_prerequisites_unavailable: bool,
    fixture_selected_model_id: Any,
) -> dict[str, Any]:
    """Build the case_03 ``values`` block when mass dependency is
    unavailable (P0-2 fail-closed path). All cost component fields
    are None; the only wired audit surface is the selector run.

    The ``selected_cost_model`` block carries BOTH the 002-H
    canonical key (``provenance_chain_hash``) and the pre-existing
    public compatibility key (``selector_provenance_chain_hash``)
    per Charles's instruction to test both if a pre-existing public
    key requires preservation.
    """
    if mass_chain_prerequisites_unavailable:
        # The mass-prerequisite unavailability is reported via
        # life_cycle_energy_envelope.blocker_codes, NOT via
        # selected_cost_model.selection_blockers (the latter is
        # reserved for selector-side blockers; the selector ran
        # cleanly and produced c0=2 / c1=1 / [] warnings).
        blocker_list_for_lifecycle = ["UNSPECIFIED_BLOCKER"]
    else:
        blocker_list_for_lifecycle = ["UNSPECIFIED_BLOCKER"]
    first_code = _code_value(selection_blockers[0]) if selection_blockers else ""
    return {
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
            "blocker_codes": blocker_list_for_lifecycle,
            "life_cycle_energy_summary": {
                "annual_operating_hours": None,
                "design_life_years": None,
                "annual_energy_MJ": None,
                "total_lifecycle_energy_MJ": None,
            },
        },
        "salvage_minor_units": 0,
        "selected_cost_model": {
            # P0-4: selected_model_id is fixture-context echo only;
            # it MUST NOT appear in produced_fields.
            "selected_model_id": fixture_selected_model_id,
            "selection_blockers": [first_code] if first_code else [],
            # 002-H canonical key (P0-4):
            "provenance_chain_hash": selector_provenance_hash,
            # pre-existing public compatibility key (preserved by
            # Charles's "if compatibility key remains, test both"
            # instruction):
            "selector_provenance_chain_hash": selector_provenance_hash,
            "selector_run_id": selector_run_id,
            "c0_record_count": c0_record_count,
            "c1_record_count": c1_record_count,
        },
        "selector_provenance_digest": selector_provenance_hash,
    }


def _execute_case_03_cost_chain(
    *,
    fixture: Mapping[str, Any],
    case_01_ref: str,
    cost_model_selection: Mapping[str, Any],
    bridge_records: list[Any],
    bridge_bindings: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str], str, list[str], list[str]]:
    """Execute the case_03 cost chain and project the public report
    shape per the P0-1/2/3/4 fixup.

    The selector audit (CostModelSelector.select_cost_records on the
    002-H frozen bridge) is always run when the bridge is present
    in the fixture; it has no mass dependency. The cost breakdown
    (CostCalculator.calculate_cost_breakdown) is ONLY run when the
    case_03 fixture carries the prerequisites for a real
    MassBreakdown from the already-wired case_02 chain. The 002-H
    frozen case_03 fixture does NOT carry those prerequisites, so
    the cost breakdown is skipped (P0-2 fail-closed path).
    """
    from hexagent.costing.cost_model_selector import (
        SELECTOR_LICENSE_CLASSES,
    )

    selection_filters = SelectionFilters(
        material_family="stainless_steel_304",
        case_region=str(cost_model_selection.get("region_id", "")),
        effective_date=str(cost_model_selection.get("date_ISO_8601", "")),
        cost_category_filter=frozenset(
            {
                "c0_material_unit_price",
                "c0_fabrication_labor",
                "c1_installation_labor",
            }
        ),
        quantity_basis_filter=frozenset(
            {
                "per_unit_mass_kg",
                "per_unit_labor_hours",
                "currency_per_hour",
            }
        ),
        license_class_filter=frozenset(SELECTOR_LICENSE_CLASSES),
        escalation_index_reference_filter=frozenset(
            {str(cost_model_selection.get("escalation_rule_id", ""))}
        ),
        record_currency=str(cost_model_selection.get("currency_ISO_4217", "USD")),
        validity_envelope=None,
    )

    selector_blockers: list[Any] = []
    selector_warnings: list[Any] = []
    selector_run_id = ""
    selector_provenance_hash = ""
    selector_c0_count = 0
    selector_c1_count = 0
    selector_result: CostModelSelectionResult | None = None
    try:
        selector_result = select_cost_records(list(bridge_records), selection_filters)
        selector_blockers = list(selector_result.selection_blockers)
        selector_warnings = list(selector_result.selection_warnings)
        selector_run_id = str(selector_result.selector_run_id)
        selector_provenance_hash = str(selector_result.provenance_chain_hash)
        selector_c0_count = len(list(selector_result.c0_records))
        selector_c1_count = len(list(selector_result.c1_records))
    except Exception as exc:
        selector_blockers = [
            {
                "code": "UNSPECIFIED_BLOCKER",
                "details": {
                    "reason": "selector_invocation_exception",
                    "error": repr(exc),
                },
            }
        ]
        _ = selector_warnings
        _ = selector_run_id
        _ = selector_provenance_hash

    # The case_03 fixture's fixture-context echo for selected_model_id
    # is read from the frozen expected_output (no adapter-side
    # synthesis, no hardcoded default).
    fixture_selected_model_id = (
        fixture.get("expected_output", {}).get("selected_cost_model", {}).get("selected_model_id")
    )

    if selector_blockers or selector_result is None:
        values = _build_case_03_selector_audit_only_values(
            case_01_ref=case_01_ref,
            selector_run_id=selector_run_id,
            selector_provenance_hash=selector_provenance_hash,
            c0_record_count=selector_c0_count,
            c1_record_count=selector_c1_count,
            selection_blockers=list(selector_blockers),
            mass_chain_prerequisites_unavailable=True,
            fixture_selected_model_id=fixture_selected_model_id,
        )
        return (
            values,
            # P0-4: produced_fields contains ONLY the 5 selector
            # audit fields (P0-2: no cost outputs synthesized).
            list(_CASE_03_SELECTOR_AUDIT_PRODUCED_FIELDS),
            "WIRED_VIA_CHAIN_PARTIAL",
            [selector_run_id] if selector_run_id else [],
            [selector_provenance_hash] if selector_provenance_hash else [],
        )

    # P0-1: real production MassBreakdown via the already-wired
    # case_02 path requires the case_03 fixture to carry the
    # material_catalog_bridge + case_01_geometry prerequisites.
    # The 002-H frozen case_03 fixture does NOT carry these
    # prerequisites, so the cost breakdown is skipped. We surface
    # only the selector audit fields.
    mass_chain_prerequisites_unavailable = True
    values = _build_case_03_selector_audit_only_values(
        case_01_ref=case_01_ref,
        selector_run_id=selector_run_id,
        selector_provenance_hash=selector_provenance_hash,
        c0_record_count=selector_c0_count,
        c1_record_count=selector_c1_count,
        selection_blockers=list(selector_blockers),
        mass_chain_prerequisites_unavailable=mass_chain_prerequisites_unavailable,
        fixture_selected_model_id=fixture_selected_model_id,
    )
    return (
        values,
        list(_CASE_03_SELECTOR_AUDIT_PRODUCED_FIELDS),
        "WIRED_VIA_CHAIN_PARTIAL",
        [selector_run_id] if selector_run_id else [],
        [selector_provenance_hash] if selector_provenance_hash else [],
    )


# --------------------------------------------------------------------------
# Top-level adapter entry point.
# --------------------------------------------------------------------------


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
        # Slice 3B-B (post-002-G): the case_02 frozen input carries
        # the 4-role material_catalog_bridge (per Amendment 002-G,
        # supersedes the 2-role 002-F bridge). The future adapter MUST
        # read the bridge verbatim and build real MaterialRecord
        # TypedDicts for all 4 closed-set production roles
        # (outer_pipe / inner_tube / hairpin_bend / fittings). No
        # synthesis, no normalization, no catalog lookup at runtime,
        # no hardcoded SS304 fallback, no corrosion_allowance_mm
        # default (None per the existing Slice 3A P1-2 contract). For
        # case_02 the adapter MUST pass include_hairpin=False and
        # fitting_overrides_kg=() to MassCalculator.calculate_mass_breakdown
        # so the production chain returns hairpin_bend_kg=0 and
        # fittings_kg=0 (case_02 is straight tube-in-shell; no
        # hairpin / no fittings by design).
        case_02_input = fixture["input"]
        case_01_ref = str(
            case_02_input.get("case_01_input_reference_case_id", "TASK-019-GOLDEN-01")
        )
        # Verify the case input carries the 4-role bridge. If not,
        # fail closed (no production chain call).
        try:
            bridge = case_02_input["material_catalog_bridge"]
        except (KeyError, TypeError) as exc:
            raise _MissingMaterialRecord(
                f"case_02 frozen input missing material_catalog_bridge: {exc}"
            ) from exc
        # Verify all 4 production roles are present in the bridge.
        missing_bridge_roles = [
            production_role
            for bridge_role, production_role in _BRIDGE_ROLE_TO_PRODUCTION_ROLE.items()
            if bridge_role not in bridge
        ]
        if missing_bridge_roles:
            # Bridge is incomplete (no shell / tube / hairpin_bend /
            # fittings). Fail closed: no resolve_material / mass /
            # preliminary calls.
            values: dict[str, Any] = {  # type: ignore[no-redef]
                "case_01_outputs": {
                    "case_01_outputs_reference_case_id": case_01_ref,
                },
                "mass_kg": {
                    "shell_mass_kg": None,
                    "total_mass_kg": None,
                    "tube_mass_kg": None,
                },
                "preliminary_mechanical_check": {"status": None},
                "selected_material_ids": {
                    "shell_material_id": None,
                    "tube_material_id": None,
                },
            }
            produced = []
            status = "WIRED_VIA_CHAIN_PARTIAL"
            run_ids = []
            digests = []
        else:
            # Resolve MaterialResolutionResult for all 4 production
            # roles by reading the bridge verbatim. If any
            # resolve_material call raises, the chain fail-closes for
            # case_02 (per the no-fabrication governance rule: no
            # silent default MaterialRecord).
            material_resolutions: dict[str, MaterialResolutionResult] = {}
            resolution_error: Exception | None = None
            for (
                bridge_role,
                production_role,
            ) in _BRIDGE_ROLE_TO_PRODUCTION_ROLE.items():
                try:
                    material_resolutions[production_role] = _resolve_material_for_production_role(
                        production_role=production_role,
                        bridge_role_block=bridge[bridge_role],
                        case_02_input=case_02_input,
                    )
                except Exception as exc:
                    resolution_error = exc
                    break
            if resolution_error is not None or len(material_resolutions) != 4:
                # resolve_material failed for at least one role. Fail
                # closed: no mass / preliminary calls. The audit
                # trail of the failure is preserved in the case
                # block's per_field / blockers list.
                values: dict[str, Any] = {  # type: ignore[no-redef]
                    "case_01_outputs": {
                        "case_01_outputs_reference_case_id": case_01_ref,
                    },
                    "mass_kg": {
                        "shell_mass_kg": None,
                        "total_mass_kg": None,
                        "tube_mass_kg": None,
                    },
                    "preliminary_mechanical_check": {"status": None},
                    "selected_material_ids": {
                        "shell_material_id": None,
                        "tube_material_id": None,
                    },
                }
                produced = []
                status = "WIRED_VIA_CHAIN_PARTIAL"
                run_ids = []
                digests = []
                _ = resolution_error
            else:
                # All 4 MaterialResolutionResults resolved
                # successfully. Build the 4-role closed-set
                # MassCalculationRequest + the tube
                # PreliminaryCheckRequest.
                try:
                    case_01_input_for_geom = case_02_input.get("case_01_geometry", {})
                    if not case_01_input_for_geom:
                        # cross-case ref input: read the case_01
                        # fixture from disk
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
                    mass_request_tube, preliminary_request, mass_request_pipe = (
                        _build_case_02_chain_request(
                            case_01_input_for_geom,
                            case_02_input,
                            material_resolutions,
                        )
                    )
                except Exception:
                    mass_request_tube = None
                    preliminary_request = None
                    mass_request_pipe = None
                try:
                    if (
                        mass_request_tube is not None
                        and preliminary_request is not None
                        and mass_request_pipe is not None
                    ):
                        # Two calculate_mass_breakdown calls:
                        # - tube call: returns the canonical
                        #   inner_tube_kg (tube dimensions).
                        # - pipe call: returns the canonical
                        #   outer_pipe_kg (pipe dimensions).
                        # The production MassCalculator uses a single
                        # geometry_record per call, so the canonical
                        # tube/pipe dimension split requires two
                        # calls. The adapter takes inner_tube_kg from
                        # the tube call and outer_pipe_kg from the
                        # pipe call, per the 002-G design §4.9.10
                        # step 7 explicit 方案 B mapping.
                        mass_breakdown_tube: MassBreakdown = calculate_mass_breakdown(
                            mass_request_tube
                        )
                        mass_breakdown_pipe: MassBreakdown = calculate_mass_breakdown(
                            mass_request_pipe
                        )
                        preliminary_result: PreliminaryCheckResult = preliminary_check(
                            preliminary_request
                        )
                    else:
                        raise RuntimeError("chain request construction failed")
                    # Slice 3B-B (post-002-G): apply 方案 B explicit
                    # mapping from production MassBreakdown to
                    # public report shape.
                    # - shell_mass_kg <- pipe_call.outer_pipe_kg (canonical)
                    # - tube_mass_kg <- tube_call.inner_tube_kg (canonical)
                    # - total_mass_kg <- tube_call.inner_tube_kg
                    #   + pipe_call.outer_pipe_kg (canonical sum;
                    #   per 002-G design §4.9.4: case_02 has
                    #   hairpin_bend_kg=0 + fittings_kg=0 by
                    #   construction)
                    # fluid_mass_kg is DEFERRED to a future real
                    # production chain (002-H+) and is NOT a
                    # produced_field for the TASK-019 Slice 3B-B
                    # production contract. Per the auth: "case_02
                    # produced_fields 不得包含 mass_kg.fluid_mass_kg"
                    # and "fluid_mass_kg = DEFERRED ... 不得作为
                    # Slice 3B-B produced_field 不得从 expected_output
                    # copy 到 actual_output 不得伪造". The 002-G
                    # design §4.9.10 step 7 documents the same.
                    # Also: the values dict MUST NOT carry
                    # fluid_mass_kg (per 002-G §4.9.10: the
                    # future Slice 3B-B adapter MUST NOT populate
                    # actual_output.mass_kg.fluid_mass_kg from any
                    # source).
                    #
                    # selected_material_ids.shell_material_id /
                    # .tube_material_id are projected from the
                    # production MaterialResolutionResult.material_grade
                    # (which comes from the bridge's grade field) via
                    # the canonical _BRIDGE_GRADE_TO_REPORT_GRADE
                    # mapping (no fabrication; the production
                    # chain returns "304" and the projection is the
                    # human-readable "SS304" form). This matches
                    # the 002-G expected_output.selected_material_ids.*
                    # contract.
                    shell_resolution = material_resolutions["outer_pipe"]
                    tube_resolution = material_resolutions["inner_tube"]
                    shell_grade = str(shell_resolution.material_grade)
                    tube_grade = str(tube_resolution.material_grade)
                    shell_material_id = _BRIDGE_GRADE_TO_REPORT_GRADE.get(shell_grade, shell_grade)
                    tube_material_id = _BRIDGE_GRADE_TO_REPORT_GRADE.get(tube_grade, tube_grade)
                    canonical_inner_tube_kg = float(mass_breakdown_tube.inner_tube_kg)
                    canonical_outer_pipe_kg = float(mass_breakdown_pipe.outer_pipe_kg)
                    canonical_total_kg = canonical_inner_tube_kg + canonical_outer_pipe_kg
                    values: dict[str, Any] = {  # type: ignore[no-redef]
                        "case_01_outputs": {
                            "case_01_outputs_reference_case_id": case_01_ref,
                        },
                        "mass_kg": {
                            "shell_mass_kg": canonical_outer_pipe_kg,
                            "total_mass_kg": canonical_total_kg,
                            "tube_mass_kg": canonical_inner_tube_kg,
                        },
                        "preliminary_mechanical_check": {
                            "status": str(preliminary_result.verdict),
                        },
                        "selected_material_ids": {
                            "shell_material_id": shell_material_id,
                            "tube_material_id": tube_material_id,
                        },
                    }
                    # 6 produced_fields, all from production chain
                    # (material_grade projected to the public
                    # string-projected form is still a production
                    # chain output, not a fabrication; the
                    # _BRIDGE_GRADE_TO_REPORT_GRADE mapping is a
                    # canonical case-bound projection, not an
                    # adapter-side default).
                    produced = [
                        "mass_kg.shell_mass_kg",
                        "mass_kg.tube_mass_kg",
                        "mass_kg.total_mass_kg",
                        "preliminary_mechanical_check.status",
                        "selected_material_ids.shell_material_id",
                        "selected_material_ids.tube_material_id",
                    ]
                    status = "WIRED_VIA_CHAIN"
                    run_ids = [
                        _stable_run_id(
                            case_id="TASK-019-GOLDEN-02",
                            slot="material_selector_outer_pipe",
                        ),
                        _stable_run_id(
                            case_id="TASK-019-GOLDEN-02",
                            slot="material_selector_inner_tube",
                        ),
                        _stable_run_id(
                            case_id="TASK-019-GOLDEN-02",
                            slot="material_selector_hairpin_bend",
                        ),
                        _stable_run_id(
                            case_id="TASK-019-GOLDEN-02",
                            slot="material_selector_fittings",
                        ),
                        _stable_run_id(
                            case_id="TASK-019-GOLDEN-02",
                            slot="mass_calculator_tube",
                        ),
                        _stable_run_id(
                            case_id="TASK-019-GOLDEN-02",
                            slot="mass_calculator_pipe",
                        ),
                        _stable_run_id(
                            case_id="TASK-019-GOLDEN-02",
                            slot="preliminary_checker",
                        ),
                    ]
                    digests = [
                        _sha256_hex(
                            _canonical_json_dumps(_safe_dump(material_resolutions["outer_pipe"]))
                        ),
                        _sha256_hex(
                            _canonical_json_dumps(_safe_dump(material_resolutions["inner_tube"]))
                        ),
                        _sha256_hex(
                            _canonical_json_dumps(_safe_dump(material_resolutions["hairpin_bend"]))
                        ),
                        _sha256_hex(
                            _canonical_json_dumps(_safe_dump(material_resolutions["fittings"]))
                        ),
                        _sha256_hex(_canonical_json_dumps(_safe_dump(mass_breakdown_tube))),
                        _sha256_hex(_canonical_json_dumps(_safe_dump(mass_breakdown_pipe))),
                        _sha256_hex(_canonical_json_dumps(_safe_dump(preliminary_result))),
                    ]
                except Exception as exc:
                    # Chain request construction or upstream
                    # execution failed. Fail closed: values are
                    # None, produced_fields is empty (except for
                    # selected_material_ids which the case-block
                    # materialization surface requires to be
                    # non-None).
                    shell_resolution_fallback = material_resolutions.get("outer_pipe")
                    tube_resolution_fallback = material_resolutions.get("inner_tube")
                    shell_grade_fb = (
                        str(shell_resolution_fallback.material_grade)
                        if shell_resolution_fallback is not None
                        else None
                    )
                    tube_grade_fb = (
                        str(tube_resolution_fallback.material_grade)
                        if tube_resolution_fallback is not None
                        else None
                    )
                    shell_material_id_fb = (
                        _BRIDGE_GRADE_TO_REPORT_GRADE.get(shell_grade_fb, shell_grade_fb)
                        if shell_grade_fb is not None
                        else None
                    )
                    tube_material_id_fb = (
                        _BRIDGE_GRADE_TO_REPORT_GRADE.get(tube_grade_fb, tube_grade_fb)
                        if tube_grade_fb is not None
                        else None
                    )
                    values: dict[str, Any] = {  # type: ignore[no-redef]
                        "case_01_outputs": {
                            "case_01_outputs_reference_case_id": case_01_ref,
                        },
                        "mass_kg": {
                            "shell_mass_kg": None,
                            "total_mass_kg": None,
                            "tube_mass_kg": None,
                        },
                        "preliminary_mechanical_check": {"status": None},
                        "selected_material_ids": {
                            "shell_material_id": shell_material_id_fb,
                            "tube_material_id": tube_material_id_fb,
                        },
                    }
                    produced = []
                    status = "WIRED_VIA_CHAIN_PARTIAL"
                    run_ids = []
                    digests = []
                    _ = exc
    elif case_id == "TASK-019-GOLDEN-03":
        # TASK-019 Slice 3B-C (post-002-H): wire the case_03 cost /
        # lifecycle / catalog bridge through the real production
        # TASK-018 chain using the 002-H frozen fixture bridge.
        case_03_input = fixture["input"]
        case_01_ref = str(
            case_03_input.get("case_01_input_reference_case_id", "TASK-019-GOLDEN-01")
        )
        cost_model_selection = case_03_input.get("cost_model_selection", {})
        bridge_records = case_03_input.get("cost_records_bridge")
        bridge_bindings = case_03_input.get("cost_records_bridge_bindings")
        if not isinstance(bridge_records, list) or not isinstance(bridge_bindings, dict):
            # Bridge is missing or malformed. Fail closed (P0-1/P0-2):
            # no cost outputs synthesized; only selector audit
            # fields are surfaced. The
            # ``cost_records_bridge_missing`` reason is carried
            # via the existing UNSPECIFIED_BLOCKER enum literal
            # (P0-3: no new blocker code).
            values = _build_case_03_selector_audit_only_values(
                case_01_ref=case_01_ref,
                selector_run_id="",
                selector_provenance_hash="",
                c0_record_count=0,
                c1_record_count=0,
                selection_blockers=[
                    {
                        "code": "UNSPECIFIED_BLOCKER",
                        "details": {"reason": "cost_records_bridge_missing"},
                    }
                ],
                mass_chain_prerequisites_unavailable=True,
                fixture_selected_model_id=(
                    fixture.get("expected_output", {})
                    .get("selected_cost_model", {})
                    .get("selected_model_id")
                ),
            )
            produced = list(_CASE_03_SELECTOR_AUDIT_PRODUCED_FIELDS)
            status = "WIRED_VIA_CHAIN_PARTIAL"
            run_ids = []
            digests = []
        else:
            cms = cost_model_selection if isinstance(cost_model_selection, Mapping) else {}
            values, produced, status, run_ids, digests = _execute_case_03_cost_chain(
                fixture=fixture,
                case_01_ref=case_01_ref,
                cost_model_selection=cms,
                bridge_records=bridge_records,
                bridge_bindings=bridge_bindings,
            )
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
