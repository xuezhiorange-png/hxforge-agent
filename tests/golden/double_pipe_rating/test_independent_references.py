"""Cross-validation tests: independent reference derivations vs. production kernel.

These tests verify that the independently derived reference results
(Gnielinski correlation + bisection solver) agree with the production
double-pipe rating kernel within frozen tolerances, and that the
derivation scripts are truly independent of hexagent modules.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Production kernel imports (used for the production-vs-reference comparison)
# ---------------------------------------------------------------------------
from hexagent.correlations.flow import ThermalBoundaryCondition
from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.rating import rate_double_pipe
from hexagent.exchangers.double_pipe.result import RatingResult
from hexagent.exchangers.double_pipe.solver import SolverParams
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.properties.base import FluidIdentifier
from hexagent.properties.coolprop_provider import CoolPropProvider

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).parent
_DERIVATIONS_DIR = _THIS_DIR / "derivations"

# ---------------------------------------------------------------------------
# Frozen comparison tolerances  (production kernel ↔ independent reference)
# ---------------------------------------------------------------------------
_Q_REL_TOL = 1e-5
_TEMP_ABS_TOL = 1e-5  # K  (absolute comparison for temperatures)
_UA_REL_TOL = 1e-5
_LMTD_REL_TOL = 1e-5

# ---------------------------------------------------------------------------
# Golden case ↔ reference input field mapping
# Maps golden-case top-level / geometry field → reference input_parameters key
# ---------------------------------------------------------------------------
_INPUT_MAP = {
    "geometry.inner_tube_inner_diameter_m": "D_i_m",
    "geometry.inner_tube_outer_diameter_m": "D_o_m",
    "geometry.outer_pipe_inner_diameter_m": "D_outer_m",
    "geometry.effective_length_m": "L_m",
    "geometry.wall_thermal_conductivity_w_m_k": "k_wall_W_m_K",
    "hot_mass_flow_kg_s": "m_hot_kg_s",
    "hot_inlet_temperature_k": "T_hot_in_K",
    "hot_inlet_pressure_pa": "P_hot_in_Pa",
    "cold_mass_flow_kg_s": "m_cold_kg_s",
    "cold_inlet_temperature_k": "T_cold_in_K",
    "cold_inlet_pressure_pa": "P_cold_in_Pa",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _deep_get(data: dict, dotted_key: str):
    """Retrieve a value from a nested dict using a dotted key like 'geometry.L_m'."""
    keys = dotted_key.split(".")
    current = data
    for k in keys:
        current = current[k]
    return current


def _load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _load_ref_script_module(script_path: Path):
    """Import a reference derivation script as a Python module."""
    module_name = script_path.stem
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _check_no_hexagent_imports(script_path: Path) -> None:
    """Parse the script's AST and fail if any hexagent import is found."""
    source = script_path.read_text()
    tree = ast.parse(source, filename=str(script_path))

    bad_nodes: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("hexagent"):
                    bad_nodes.append(f"import {alias.name} (line {node.lineno})")
        elif (
            isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("hexagent")
        ):
            bad_nodes.append(f"from {node.module} import ... (line {node.lineno})")

    assert not bad_nodes, (
        f"Reference script {script_path.name} contains hexagent imports:\n" + "\n".join(bad_nodes)
    )


def _run_production_kernel(golden: dict, provider: CoolPropProvider) -> RatingResult:
    """Run the production double-pipe rating kernel with golden case inputs."""
    geo_data = golden["geometry"]
    geometry = DoublePipeGeometry(**geo_data)

    hot_fluid = FluidIdentifier(name=golden["hot_fluid"])
    cold_fluid = FluidIdentifier(name=golden["cold_fluid"])
    flow_arrangement = FlowArrangement(golden["flow_arrangement"])

    result = rate_double_pipe(
        geometry=geometry,
        hot_fluid=hot_fluid,
        cold_fluid=cold_fluid,
        hot_mass_flow_kg_s=golden["hot_mass_flow_kg_s"],
        cold_mass_flow_kg_s=golden["cold_mass_flow_kg_s"],
        hot_inlet_temperature_k=golden["hot_inlet_temperature_k"],
        cold_inlet_temperature_k=golden["cold_inlet_temperature_k"],
        hot_inlet_pressure_pa=golden["hot_inlet_pressure_pa"],
        cold_inlet_pressure_pa=golden["cold_inlet_pressure_pa"],
        tube_in_hot=golden["tube_in_hot"],
        flow_arrangement=flow_arrangement,
        provider=provider,
        solver_params=SolverParams(),
        minimum_terminal_delta_t=0.5,
        tube_boundary_condition=ThermalBoundaryCondition.constant_wall_temperature,
        annulus_boundary_condition=ThermalBoundaryCondition.inner_wall_heated,
    )
    return result


def _recompute_reference_results(mod) -> dict:
    """Re-run the reference computation from the imported module and return a
    results dict that mirrors the JSON ``results`` section."""
    import CoolProp.CoolProp as CP

    # Inlet enthalpies
    props_hot_in = mod.get_properties_TP(mod.T_hot_in, mod.P_hot_in)
    props_cold_in = mod.get_properties_TP(mod.T_cold_in, mod.P_cold_in)
    h_hot_in = props_hot_in["h"]
    h_cold_in = props_cold_in["h"]

    # Q_max (same logic as main())
    T_hot_out_min = mod.T_cold_in + 0.5
    h_hot_out_min = CP.PropsSI("H", "T", T_hot_out_min, "P", mod.P_hot_in, mod.FLUID)
    Q_hot_limit = mod.m_hot * (h_hot_in - h_hot_out_min)

    T_cold_out_max = mod.T_hot_in - 0.5
    h_cold_out_max = CP.PropsSI("H", "T", T_cold_out_max, "P", mod.P_cold_in, mod.FLUID)
    Q_cold_limit = mod.m_cold * (h_cold_out_max - h_cold_in)

    q_max = min(Q_hot_limit, Q_cold_limit)

    # Solve
    result = mod.bisect_solve(h_hot_in, h_cold_in, q_max)

    # Energy check
    Q_hot = mod.m_hot * (h_hot_in - mod.get_properties_TP(result["T_hot_out"], mod.P_hot_in)["h"])
    Q_cold = mod.m_cold * (
        mod.get_properties_TP(result["T_cold_out"], mod.P_cold_in)["h"] - h_cold_in
    )
    energy_residual = Q_hot - Q_cold

    return {
        "Q_W": result["Q"],
        "T_hot_out_K": result["T_hot_out"],
        "T_cold_out_K": result["T_cold_out"],
        "UA_W_K": result["UA"],
        "LMTD_K": result["LMTD"],
        "ua_lmtd_residual_W": result["residual"],
        "energy_residual_W": energy_residual,
    }


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def provider() -> CoolPropProvider:
    return CoolPropProvider(cache_size=64)


# ---------------------------------------------------------------------------
# Parametrized cases
# ---------------------------------------------------------------------------

_CASES = [
    (
        "case1_counterflow_water_water",
        "case1_counterflow_reference.py",
        "case1_reference_result.json",
    ),
    (
        "case2_parallelflow_water_water",
        "case2_parallelflow_reference.py",
        "case2_reference_result.json",
    ),
    (
        "case3_variable_property",
        "case3_variable_property_reference.py",
        "case3_reference_result.json",
    ),
]


@pytest.mark.parametrize("case_id,script_name,ref_json_name", _CASES)
class TestIndependentReferences:
    """Parametrised cross-validation for each golden case."""

    # ---- helpers to load once per test method ----------------------------

    def _golden(self, case_id: str) -> dict:
        return _load_json(_THIS_DIR / f"{case_id}.json")

    def _ref_json(self, ref_json_name: str) -> dict:
        return _load_json(_DERIVATIONS_DIR / ref_json_name)

    def _ref_script_path(self, script_name: str) -> Path:
        return _DERIVATIONS_DIR / script_name

    # ---- 1. Reference metadata -------------------------------------------

    def test_reference_metadata(self, case_id: str, script_name: str, ref_json_name: str) -> None:
        ref = self._ref_json(ref_json_name)
        meta = ref["reference"]

        assert meta["method"] != ""
        assert meta["source"] != ""
        assert meta["independent_from_production_kernel"] is True
        assert meta["derivation_file"] == script_name
        # Hash must be a valid 64-char hex string
        assert len(meta["reference_result_hash"]) == 64
        int(meta["reference_result_hash"], 16)  # raises on invalid hex

    # ---- 2. Reference input matches golden case input --------------------

    def test_reference_input_matches_golden(
        self, case_id: str, script_name: str, ref_json_name: str
    ) -> None:
        golden = self._golden(case_id)
        ref = self._ref_json(ref_json_name)
        ref_inputs = ref["input_parameters"]

        for golden_key, ref_key in _INPUT_MAP.items():
            golden_val = _deep_get(golden, golden_key)
            ref_val = ref_inputs[ref_key]
            assert golden_val == pytest.approx(ref_val, rel=1e-12), (
                f"Input mismatch for {golden_key} (golden) vs "
                f"{ref_key} (reference): {golden_val} != {ref_val}"
            )

    # ---- 3. Reference result hash -----------------------------------------

    def test_reference_result_hash(
        self, case_id: str, script_name: str, ref_json_name: str
    ) -> None:
        ref = self._ref_json(ref_json_name)
        stored_hash = ref["reference"]["reference_result_hash"]

        result_str = json.dumps(ref["results"], sort_keys=True, default=str)
        computed_hash = hashlib.sha256(result_str.encode()).hexdigest()

        assert stored_hash == computed_hash, (
            f"Reference result hash mismatch: stored={stored_hash}, computed={computed_hash}"
        )

    # ---- 4. Production kernel vs. independent reference ------------------

    def test_production_vs_reference(
        self,
        case_id: str,
        script_name: str,
        ref_json_name: str,
        provider: CoolPropProvider,
    ) -> None:
        golden = self._golden(case_id)
        ref = self._ref_json(ref_json_name)
        ref_results = ref["results"]

        prod = _run_production_kernel(golden, provider)

        # Heat duty (relative)
        assert prod.heat_duty_w is not None
        assert prod.heat_duty_w == pytest.approx(ref_results["Q_W"], rel=_Q_REL_TOL)

        # Hot outlet temperature (absolute, K)
        assert prod.hot_outlet_temperature_k is not None
        assert prod.hot_outlet_temperature_k == pytest.approx(
            ref_results["T_hot_out_K"], abs=_TEMP_ABS_TOL
        )

        # Cold outlet temperature (absolute, K)
        assert prod.cold_outlet_temperature_k is not None
        assert prod.cold_outlet_temperature_k == pytest.approx(
            ref_results["T_cold_out_K"], abs=_TEMP_ABS_TOL
        )

        # UA (relative)
        assert prod.UA_w_k is not None
        assert prod.UA_w_k == pytest.approx(ref_results["UA_W_K"], rel=_UA_REL_TOL)

        # LMTD (relative)
        assert prod.LMTD_k is not None
        assert prod.LMTD_k == pytest.approx(ref_results["LMTD_K"], rel=_LMTD_REL_TOL)

    # ---- 5. Reference script has no hexagent imports (AST) ----------------

    def test_script_no_hexagent_imports(
        self, case_id: str, script_name: str, ref_json_name: str
    ) -> None:
        script_path = self._ref_script_path(script_name)
        _check_no_hexagent_imports(script_path)

    # ---- 6. Script computation matches JSON (prevent JSON-script drift) ---

    def test_script_computation_matches_json(
        self, case_id: str, script_name: str, ref_json_name: str
    ) -> None:
        script_path = self._ref_script_path(script_name)
        ref = self._ref_json(ref_json_name)
        ref_results = ref["results"]

        mod = _load_ref_script_module(script_path)

        recomputed = _recompute_reference_results(mod)

        # Compare each key result field
        for key in ("Q_W", "T_hot_out_K", "T_cold_out_K", "UA_W_K", "LMTD_K"):
            assert recomputed[key] == pytest.approx(ref_results[key], rel=1e-10), (
                f"Script-vs-JSON drift for {key}: "
                f"recomputed={recomputed[key]}, json={ref_results[key]}"
            )

    # ---- 7. Reference script functions are importable and callable --------

    def test_reference_script_importable(
        self, case_id: str, script_name: str, ref_json_name: str
    ) -> None:
        script_path = self._ref_script_path(script_name)
        mod = _load_ref_script_module(script_path)

        # Core computation functions must exist and be callable
        assert callable(getattr(mod, "bisect_solve", None))
        assert callable(getattr(mod, "evaluate_residual", None))
        assert callable(getattr(mod, "get_properties_TP", None))
        assert callable(getattr(mod, "get_temperature_PH", None))
        assert callable(getattr(mod, "gnielinski_nusselt", None))
        assert callable(getattr(mod, "petukhov_friction_factor", None))
        assert callable(getattr(mod, "compute_thermal_resistance", None))
