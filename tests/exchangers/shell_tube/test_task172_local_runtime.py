"""Production-contract tests for the TASK172 local constitutive runtime."""

from __future__ import annotations

import json
import platform
import sys
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import CoolProp
import pytest
import scipy

from hexagent.exchangers.shell_tube.bell_delaware import canonical as task166_canonical
from hexagent.exchangers.shell_tube.bell_delaware.models import (
    ApplicabilityLedger,
    ApplicabilityStatus,
    BellGeometry,
    CompletenessLedger,
    ProvenanceGraph,
    Task166Result,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import (
    canonical as task031_canonical,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.models import (
    AGGREGATE_AUTHORITY_PROFILE_ID,
    FLOW_REGION_IDENTITY,
    FORMULA_A_ID,
    FORMULA_B_ID,
    RESULT_SCHEMA_VERSION,
    ShellSideHydraulicGeometry,
)
from hexagent.exchangers.shell_tube.task172_local_runtime import (
    Task172BlockedResult,
    Task172LocalRequest,
    Task172LocalResult,
    build_local_support,
    recompute_task172_blocked_result_hash,
    recompute_task172_request_hash,
    recompute_task172_result_hash,
    validate_request,
)
from hexagent.exchangers.shell_tube.task172_local_runtime import models as runtime_models
from hexagent.exchangers.shell_tube.task172_local_runtime import service as runtime_service
from hexagent.properties.base import FluidIdentifier, PhaseRegion
from hexagent.properties.coolprop_provider import CoolPropProvider


def _bell_geometry() -> BellGeometry:
    return BellGeometry(
        shell_inside_diameter_m=Decimal("0.5"),
        bundle_outer_diameter_m=Decimal("0.45486592081130829065079429561196969724856074243842"),
        tube_outer_diameter_m=Decimal("0.01905"),
        tube_pitch_m=Decimal("0.0254"),
        baffle_cut_fraction=Decimal("0.25"),
        baffle_count=4,
        central_baffle_spacing_m=Decimal("1.2"),
        inlet_baffle_spacing_m=Decimal("0.6"),
        outlet_baffle_spacing_m=Decimal("0.6"),
        shell_to_bundle_diametral_clearance_m=Decimal(
            "0.04513407918869170934920570438803030275143925756158"
        ),
        shell_to_baffle_diametral_clearance_m=Decimal("0.00635"),
        tube_to_baffle_hole_diametral_clearance_m=Decimal("0.001"),
        tube_count=Decimal("253"),
        layout_id="55b3085c-6a2a-5394-8617-7102e7eb66a8",
        layout_angle="LAYOUT_30_DEG",
        theta_ctl_rad=Decimal("1"),
        theta_ds_rad=Decimal("1"),
        window_tube_fraction=Decimal("0.2"),
        pure_crossflow_tube_fraction=Decimal("0.6"),
        central_crossflow_tube_rows=Decimal("12"),
        window_tube_rows=Decimal("12"),
        total_crossflow_tube_rows=Decimal("100"),
        window_tube_count=Decimal("50"),
        gross_window_flow_area_m2=Decimal("0.02"),
        window_tube_area_m2=Decimal("0.01"),
        central_crossflow_flow_area_m2=Decimal("0.15"),
        window_flow_area_m2=Decimal("0.01"),
        shell_to_baffle_leakage_area_m2=Decimal("0.005"),
        tube_to_baffle_leakage_area_m2=Decimal("0.005"),
        total_leakage_area_m2=Decimal("0.01"),
        bundle_bypass_area_m2=Decimal("0.01"),
        shell_leakage_fraction=Decimal("0.02"),
        leakage_area_ratio=Decimal("0.03"),
        bypass_area_ratio=Decimal("0.04"),
        effective_tube_pitch_m=Decimal("0.0254"),
        window_hydraulic_diameter_m=Decimal("0.018"),
        source_formula_ids=("GONCALVES_2019_EQ3_EQ4", "GONCALVES_2019_EQ5_EQ35"),
    )


def _native_shell_flow_authority() -> runtime_models.ShellFlowAuthority:
    upstream = {
        "task020_configuration_id": "96637b2b-3583-5fdd-8645-bb2b5526996a",
        "task020_configuration_hash": (
            "04fbacd4037e4740328dd76b01caa0e85f22569924308d74b35bb13f0beb9125"
        ),
        "task021_layout_id": "55b3085c-6a2a-5394-8617-7102e7eb66a8",
        "task021_layout_hash": "1dabd4362cc0c446da892bfe92b48fc6066b01ab3ca037d31ff4213e91fcc550",
        "task022_geometry_id": "cbacec31-31fa-5e14-aa1b-be05e04b96dc",
        "task022_geometry_hash": "2384f3b31b279dac696951372d4b4781c58b8594c4d09091ec1a5cdaab7049f4",
        "task024_geometry_id": "279ed479-378d-5ea5-b2f0-8926133bf4dd",
        "task024_geometry_hash": "68efd0e8dc69f203d49b73b2a87106863725d9a1b4a9bf1282cc1f650942d994",
    }
    geometry_fields: dict[str, Any] = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "geometry_id": "",
        "geometry_hash": "",
        "request_hash": "2" * 64,
        **upstream,
        "engineering_authority_id": task031_canonical.ENGINEERING_AUTHORITY_ID,
        "engineering_authority_hash": task031_canonical.ENGINEERING_AUTHORITY_HASH,
        "formula_a_id": FORMULA_A_ID,
        "formula_b_id": FORMULA_B_ID,
        "pattern_family": "TRIANGULAR",
        "flow_region_identity": FLOW_REGION_IDENTITY,
        "central_inter_baffle_spacing_m": "1.200000000000",
        "central_crossflow_flow_area_m2": "0.150000000000000000000000",
        "shell_side_equivalent_hydraulic_diameter_m": "0.018293343850",
        "warnings": (),
        "blockers": (),
        "deferred_capabilities": (),
    }
    provenance = {
        "task_id": "TASK-031",
        "design_contract_path": (
            "docs/tasks/TASK-031-shell-and-tube-shell-side-flow-path-hydraulic-geometry.md"
        ),
        **upstream,
        "engineering_authority_profile_id": AGGREGATE_AUTHORITY_PROFILE_ID,
        "engineering_authority_hash": task031_canonical.ENGINEERING_AUTHORITY_HASH,
        "formula_a_id": FORMULA_A_ID,
        "formula_b_id": FORMULA_B_ID,
        "source_authority_freeze_comment_id": "test-fixture-freeze-comment",
        "source_ids": ("native-test-fixture",),
        "pattern_family": "TRIANGULAR",
        "flow_region_identity": FLOW_REGION_IDENTITY,
        "software_version": task031_canonical.IMPLEMENTATION_SOFTWARE_VERSION,
        "git_commit": task031_canonical.GIT_COMMIT,
        "request_hash": geometry_fields["request_hash"],
        "warnings": [],
        "deferred_capabilities": [],
        "provenance_hash": "3" * 64,
    }
    geometry_fields["provenance"] = tuple(provenance.items())
    geometry = ShellSideHydraulicGeometry(**geometry_fields)
    geometry_hash = task031_canonical.sha256_hex(
        task031_canonical.success_geometry_canonical_projection(geometry)
    )
    geometry = replace(
        geometry,
        geometry_hash=geometry_hash,
        geometry_id=task031_canonical.geometry_id(geometry_hash),
    )

    evidence = {
        "task020_evidence": (
            ("configuration_id", upstream["task020_configuration_id"]),
            ("configuration_hash", upstream["task020_configuration_hash"]),
        ),
        "tube_layout_evidence": (
            ("layout_id", upstream["task021_layout_id"]),
            ("layout_hash", upstream["task021_layout_hash"]),
        ),
        "shell_bundle_evidence": (
            ("geometry_id", upstream["task022_geometry_id"]),
            ("geometry_hash", upstream["task022_geometry_hash"]),
        ),
        "baffle_evidence": (
            ("geometry_id", upstream["task024_geometry_id"]),
            ("geometry_hash", upstream["task024_geometry_hash"]),
        ),
        "shell_side_hydraulic_evidence": (
            ("geometry_id", geometry.geometry_id),
            ("geometry_hash", geometry.geometry_hash),
        ),
    }
    bell = _bell_geometry()
    result = Task166Result(
        request_hash="4" * 64,
        bell_geometry=bell,
        applicability=ApplicabilityLedger(checks=(), status=ApplicabilityStatus.APPLICABLE),
        completeness=CompletenessLedger(
            required_fields=("bell_geometry",), present_fields=("bell_geometry",), status="COMPLETE"
        ),
        provenance=ProvenanceGraph(nodes=(), edges=(), graph_hash="5" * 64),
        **evidence,
    )
    task166_hash = task166_canonical.result_hash(result)
    result = replace(
        result,
        result_hash=task166_hash,
        result_id=task166_canonical.result_id(task166_hash),
    )
    return runtime_models.ShellFlowAuthority(
        task031_geometry=geometry,
        task166_result=result,
    )


def _request(
    *, tube_temperature: str = "300", shell_temperature: str = "298.15"
) -> Task172LocalRequest:
    topology = runtime_models.TopologyBinding(
        topology_id=runtime_models.TOPOLOGY_ID,
        task171_result_hash=runtime_models.TASK171_RESULT_HASH,
        mesh_identity=runtime_models.MESH_IDENTITY,
        physical_ownership_hash=runtime_models.PHYSICAL_OWNERSHIP_HASH,
        definition_projection_hash=runtime_models.DEFINITION_PROJECTION_HASH,
        selected_variant="TUBE_HOT_SHELL_COLD",
        thermal_role_selection_authority_id=runtime_models.THERMAL_ROLE_AUTHORITY_ID,
        tube_role="HOT",
        shell_role="COLD",
        tube_flow_path_id=runtime_models.TUBE_FLOW_PATH_ID,
        shell_flow_path_id=runtime_models.SHELL_FLOW_PATH_ID,
    )
    support = build_local_support(0, 1, 0)
    shell_flow = _native_shell_flow_authority()
    return Task172LocalRequest(
        topology=topology,
        support=support,
        tube_bulk_state=runtime_models.LocalState(
            temperature_k=Decimal(tube_temperature), pressure_pa=Decimal("101325")
        ),
        shell_bulk_state=runtime_models.LocalState(
            temperature_k=Decimal(shell_temperature), pressure_pa=Decimal("101325")
        ),
        tube_mass_flow_kg_s=Decimal("12.000000"),
        shell_mass_flow_kg_s=Decimal("20.000000"),
        shell_flow_authority=shell_flow,
    )


def test_task172_keeps_task031_authority_profile_and_identity_layers_distinct() -> None:
    authority = _native_shell_flow_authority()
    provenance = dict(authority.task031_geometry.provenance)
    assert provenance["engineering_authority_profile_id"] == AGGREGATE_AUTHORITY_PROFILE_ID
    assert authority.task031_geometry.engineering_authority_id == (
        task031_canonical.ENGINEERING_AUTHORITY_ID
    )
    assert provenance["engineering_authority_profile_id"] != (
        authority.task031_geometry.engineering_authority_id
    )


def test_task172_clean_local_closure_replays_exact_result_bytes() -> None:
    request = _request()
    first = validate_request(request, CoolPropProvider())
    second = validate_request(request, CoolPropProvider())

    assert type(first) is Task172LocalResult
    assert type(second) is Task172LocalResult
    assert first.model_dump_json() == second.model_dump_json()
    assert first.request_hash == second.request_hash
    assert first.result_hash == second.result_hash
    assert first.request_hash == recompute_task172_request_hash(request)
    assert first.result_hash == recompute_task172_result_hash(first)
    assert first.result_id == f"urn:hxforge:task172:{first.result_hash}"
    assert first.signed_q_hot_to_cold_w > 0
    assert first.case_id == runtime_models.CASE_ID
    assert first.case_revision_id == runtime_models.CASE_REVISION_ID
    assert first.topology_id == runtime_models.TOPOLOGY_ID
    assert first.shell_j_mu > Decimal("0")
    assert (
        first.shell_jmu_model_authority_canonical_hash
        == runtime_models.SHELL_JMU_MODEL_AUTHORITY_CANONICAL_HASH
    )
    assert first.tube_correlation_id == "tube_turbulent_gnielinski"
    assert first.tube_reynolds_number > Decimal("3000")
    assert first.residual_acceptance_state == "PASS_C_RESIDUAL_SPECIFIC_ULP_OPERATION_BOUND"
    assert first.blockers == ()


def test_task172_schema_rejects_unknown_fields_and_wrong_authority() -> None:
    raw = _request().model_dump(mode="python")
    raw["unreviewed"] = True
    blocked = validate_request(raw, CoolPropProvider())
    assert type(blocked) is Task172BlockedResult
    assert blocked.failure_code == "BLOCKED_INVALID_REQUEST_SCHEMA"

    raw = _request().model_dump(mode="python")
    raw["topology"]["topology_id"] = "invented"
    blocked = validate_request(raw, CoolPropProvider())
    assert type(blocked) is Task172BlockedResult
    assert blocked.failure_code == "BLOCKED_INVALID_REQUEST_SCHEMA"


def test_task172_r2_case_binding_rejects_predecessor_tube_flow() -> None:
    raw = _request().model_dump(mode="python")
    raw["tube_mass_flow_kg_s"] = Decimal("10.000000")
    blocked = validate_request(raw, CoolPropProvider())
    assert type(blocked) is Task172BlockedResult
    assert blocked.failure_code == "BLOCKED_INVALID_REQUEST_SCHEMA"

    request = _request()
    assert request.case_revision_id == "V07-T172-PROJECT-ENGINEERING-REFERENCE-CASE-R2"
    assert request.tube_mass_flow_kg_s == Decimal("12.000000")


def test_task172_local_support_cannot_cross_or_reassign_physical_interval() -> None:
    raw = _request().model_dump(mode="python")
    raw["support"]["support_end_m"] = Decimal("1.2001")
    blocked = validate_request(raw, CoolPropProvider())
    assert type(blocked) is Task172BlockedResult
    assert blocked.failure_code == "BLOCKED_INVALID_REQUEST_SCHEMA"

    raw = _request().model_dump(mode="python")
    raw["support"]["inside_area_m2"] = Decimal("15.022153591681")
    blocked = validate_request(raw, CoolPropProvider())
    assert type(blocked) is Task172BlockedResult

    raw = _request().model_dump(mode="python")
    raw["support"]["tube_cell_id"] = "TASK171:TUBE:CELL:0"
    blocked = validate_request(raw, CoolPropProvider())
    assert type(blocked) is Task172BlockedResult
    assert blocked.failure_code == "BLOCKED_INVALID_REQUEST_SCHEMA"


def test_task172_refined_support_identity_is_deterministic_and_preserves_ownership() -> None:
    supports = [
        build_local_support(interval, 64, child) for interval in range(5) for child in range(64)
    ]
    assert len(supports) == 320
    assert len({item.tube_cell_id for item in supports}) == 320
    assert len({item.shell_cell_id for item in supports}) == 320
    assert len({item.wall_interface_id for item in supports}) == 320
    assert sum((item.inside_area_m2 for item in supports), Decimal("0")) == Decimal("75.1107679584")
    assert sum((item.outside_area_m2 for item in supports), Decimal("0")) == Decimal(
        "90.848262197302892909889504"
    )
    assert all(item.support_end_m <= item.physical_segment_end_m for item in supports)

    first = build_local_support(0, 2, 0)
    second = build_local_support(0, 2, 0)
    assert first == second
    request = _request().model_copy(update={"support": first})
    result = validate_request(request, CoolPropProvider())
    assert type(result) is Task172LocalResult
    assert result.subdivisions_per_physical_interval_per_side == 2
    assert result.mesh_level_identity == first.mesh_level_identity


def test_task172_negative_physical_direction_is_typed_blocked_not_repaired() -> None:
    outcome = validate_request(
        _request(tube_temperature="298.15", shell_temperature="300"), CoolPropProvider()
    )
    assert type(outcome) is Task172BlockedResult
    assert outcome.failure_code == "BLOCKED_NEGATIVE_PHYSICAL_HEAT_RATE"
    assert outcome.blockers == ("BLOCKED_NEGATIVE_PHYSICAL_HEAT_RATE",)
    assert outcome.blocked_result_hash == recompute_task172_blocked_result_hash(outcome)


def test_task172_property_provider_and_domain_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = CoolPropProvider()

    def failed_state(
        self: CoolPropProvider, fluid: FluidIdentifier, temperature_k: float, pressure_pa: float
    ) -> Any:
        raise RuntimeError("sentinel property failure")

    monkeypatch.setattr(CoolPropProvider, "state_tp", failed_state)
    failed = validate_request(_request(), provider)
    assert type(failed) is Task172BlockedResult
    assert failed.failure_code == "BLOCKED_PROPERTY_EVALUATION_FAILURE"

    raw = _request().model_dump(mode="python")
    raw["shell_bulk_state"]["pressure_pa"] = Decimal("99999")
    failed = validate_request(raw, CoolPropProvider())
    assert type(failed) is Task172BlockedResult
    assert failed.failure_code == "BLOCKED_INVALID_REQUEST_SCHEMA"


def test_task172_phase_and_tube_correlation_applicability_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = CoolPropProvider()
    original_state = provider.state_tp

    def gas_state(fluid: FluidIdentifier, temperature_k: float, pressure_pa: float) -> Any:
        return replace(original_state(fluid, temperature_k, pressure_pa), phase=PhaseRegion.GAS)

    monkeypatch.setattr(provider, "state_tp", gas_state)
    phase_result = validate_request(_request(), provider)
    assert type(phase_result) is Task172BlockedResult
    assert phase_result.failure_code == "BLOCKED_PROPERTY_PHASE"

    provider = CoolPropProvider()
    original_state = provider.state_tp

    def high_viscosity(fluid: FluidIdentifier, temperature_k: float, pressure_pa: float) -> Any:
        state = original_state(fluid, temperature_k, pressure_pa)
        return replace(state, viscosity_pa_s=state.viscosity_pa_s * 100.0)

    monkeypatch.setattr(provider, "state_tp", high_viscosity)
    correlation_result = validate_request(_request(), provider)
    assert type(correlation_result) is Task172BlockedResult
    assert correlation_result.failure_code == "BLOCKED_TUBE_C3_REGIME_NOT_APPLICABLE"


def test_task172_clean_surface_and_wall_material_authority_are_frozen() -> None:
    raw = _request().model_dump(mode="python")
    raw["tube_inside_fouling_m2_k_w"] = Decimal("0.0001")
    fouled = validate_request(raw, CoolPropProvider())
    assert type(fouled) is Task172BlockedResult
    assert fouled.failure_code == "BLOCKED_INVALID_REQUEST_SCHEMA"

    raw = _request().model_dump(mode="python")
    raw["material_source_sha256"] = "0" * 64
    wrong_material = validate_request(raw, CoolPropProvider())
    assert type(wrong_material) is Task172BlockedResult
    assert wrong_material.failure_code == "BLOCKED_INVALID_REQUEST_SCHEMA"


def test_task172_nonconvergence_nonfinite_trial_and_property_domain_exit_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import numpy as np

    provider = CoolPropProvider()

    def nonconverged(fun: Any, initial: Any, **kwargs: Any) -> Any:
        return SimpleNamespace(success=False, nfev=6, status=0, x=initial)

    monkeypatch.setattr(runtime_service, "least_squares", nonconverged)
    result = validate_request(_request(), provider)
    assert type(result) is Task172BlockedResult
    assert result.failure_code == "BLOCKED_NONCONVERGENCE"

    provider = CoolPropProvider()

    def nonfinite_trial(fun: Any, initial: Any, **kwargs: Any) -> Any:
        trial = np.asarray(initial, dtype=float).copy()
        trial[0] = float("nan")
        fun(trial)
        raise AssertionError("nonfinite trial unexpectedly returned")

    monkeypatch.setattr(runtime_service, "least_squares", nonfinite_trial)
    result = validate_request(_request(), provider)
    assert type(result) is Task172BlockedResult
    assert result.failure_code == "BLOCKED_NONFINITE_TRIAL"

    provider = CoolPropProvider()

    def out_of_domain_trial(fun: Any, initial: Any, **kwargs: Any) -> Any:
        trial = np.asarray(initial, dtype=float).copy()
        trial[1:] = 297.0
        fun(trial)
        raise AssertionError("domain exit unexpectedly returned")

    monkeypatch.setattr(runtime_service, "least_squares", out_of_domain_trial)
    result = validate_request(_request(), provider)
    assert type(result) is Task172BlockedResult
    assert result.failure_code == "BLOCKED_PROPERTY_TEMPERATURE_DOMAIN_EXIT"


@pytest.mark.parametrize("temperature", ["298.15", "300.00"])
def test_task172_reviewed_temperature_domain_includes_closed_boundaries(temperature: str) -> None:
    request = _request(tube_temperature=temperature)
    outcome = validate_request(request, CoolPropProvider())
    assert type(outcome) is Task172LocalResult


_DOGBOX_CANDIDATE_AUTHORITY_ID = "V07-T172-R94-FAIL-ONLY-DOGBOX-FALLBACK-CANDIDATE-R1"
_DOGBOX_HOLE_FIXTURE = (
    Path(__file__).parent / "fixtures" / "task172_n32_residual_holes_candidate_r1.json"
)
_DOGBOX_CORPUS_FIXTURE = (
    Path(__file__).parent / "fixtures" / "task172_fail_only_dogbox_characterization_r1.json"
)
_DOGBOX_FRESH_CORPUS_FIXTURE = (
    Path(__file__).parent / "fixtures" / "task172_fail_only_dogbox_fresh_n8_n16_r1.json"
)


def _candidate_request_from_projection(
    payload: dict[str, Any], shell_authority: Any
) -> Task172LocalRequest:
    raw = dict(payload)
    authority_projection = raw["shell_flow_authority"]
    if "task031_geometry" not in authority_projection:
        raw["shell_flow_authority"] = shell_authority.model_dump(mode="json")
    return Task172LocalRequest.model_validate_json(json.dumps(raw), strict=True)


def _capture_r94_or_dogbox_candidate(
    request: Task172LocalRequest,
    provider: CoolPropProvider,
    *,
    method: str,
) -> tuple[Any, dict[str, Any]]:
    original_least_squares = runtime_service.least_squares
    capture: dict[str, Any] = {}

    def selected_solver(fun: Any, x0: Any, **kwargs: Any) -> Any:
        callback_count = 0

        def counted_residual(values: Any) -> Any:
            nonlocal callback_count
            callback_count += 1
            return fun(values)

        capture["initial_x"] = [repr(float(value)) for value in x0]
        capture["requested_options"] = {
            "method": kwargs["method"],
            "loss": kwargs["loss"],
            "ftol": kwargs["ftol"],
            "xtol": kwargs["xtol"],
            "gtol": kwargs["gtol"],
            "jac": kwargs["jac"],
            "diff_step": kwargs["diff_step"],
            "max_nfev": kwargs["max_nfev"],
            "tr_solver": kwargs["tr_solver"],
            "x_scale": [repr(float(value)) for value in kwargs["x_scale"]],
            "f_scale": kwargs["f_scale"],
        }
        assert kwargs["method"] == "trf"
        assert kwargs["max_nfev"] == 6
        assert runtime_service._CALLBACK_CAP == 24
        selected = dict(kwargs)
        selected["method"] = method
        solver = original_least_squares(counted_residual, x0, **selected)
        capture["solver"] = {
            "method": method,
            "success": bool(solver.success),
            "status": int(solver.status),
            "message": str(solver.message),
            "nfev": int(solver.nfev),
            "njev": None if solver.njev is None else int(solver.njev),
            "callback_count": callback_count,
            "cost": float(solver.cost),
            "optimality": float(solver.optimality),
            "active_mask": [int(value) for value in solver.active_mask],
            "scaled_residual_vector": [float(value) for value in solver.fun],
            "solution": [float(value) for value in solver.x],
        }
        return solver

    runtime_service.least_squares = selected_solver
    try:
        outcome = validate_request(request, provider)
    finally:
        runtime_service.least_squares = original_least_squares
    return outcome, capture


def _dogbox_candidate_projection(result: Task172LocalResult) -> Task172LocalResult:
    projected = result.model_copy(
        update={
            "numerical_profile_id": _DOGBOX_CANDIDATE_AUTHORITY_ID,
            "solver_status": (
                "R94_TRF_RESIDUAL_FAIL_THEN_DOGBOX_FALLBACK_"
                + result.solver_status.rsplit("_", 1)[-1]
            ),
            "result_hash": "",
            "result_id": "",
        }
    )
    result_hash = recompute_task172_result_hash(projected)
    return projected.model_copy(
        update={
            "result_hash": result_hash,
            "result_id": f"urn:hxforge:task172:{result_hash}",
        }
    )


def _candidate_decision(
    request: Task172LocalRequest,
    baseline: Any,
    fallback: Any,
) -> dict[str, Any]:
    if type(baseline) is Task172LocalResult:
        return {
            "baseline": baseline,
            "result": baseline,
            "path": "PRIMARY_R94_TRF",
            "fallback_invoked": False,
            "classification": "VALIDATED",
        }
    if type(baseline) is not Task172BlockedResult:
        return {
            "baseline": baseline,
            "result": baseline,
            "path": "HARD_BLOCKER_UNEXPECTED_TYPE",
            "fallback_invoked": False,
            "classification": "HARD_BLOCKER",
        }
    if baseline.failure_code != "BLOCKED_RESIDUAL_ACCEPTANCE":
        return {
            "baseline": baseline,
            "result": baseline,
            "path": "HARD_BLOCKER_NON_RESIDUAL",
            "fallback_invoked": False,
            "classification": baseline.failure_code,
        }
    if baseline.request_hash != recompute_task172_request_hash(
        request
    ) or baseline.blocked_result_hash != recompute_task172_blocked_result_hash(baseline):
        return {
            "baseline": baseline,
            "result": baseline,
            "path": "HARD_BLOCKER_BLOCKED_IDENTITY_REPLAY",
            "fallback_invoked": False,
            "classification": "BLOCKED_RESULT_IDENTITY_REPLAY",
        }
    fallback_result = fallback()
    if type(fallback_result) is not Task172LocalResult:
        return {
            "baseline": baseline,
            "result": fallback_result,
            "path": "DOGBOX_FALLBACK_NOT_VALID",
            "fallback_invoked": True,
            "classification": getattr(fallback_result, "failure_code", "HARD_BLOCKER"),
        }
    candidate_result = _dogbox_candidate_projection(fallback_result)
    return {
        "baseline": baseline,
        "result": candidate_result,
        "path": "R94_TRF_RESIDUAL_FAIL_THEN_DOGBOX_FALLBACK",
        "fallback_invoked": True,
        "classification": "VALIDATED",
    }


def _candidate_identity_receipt(
    request: Task172LocalRequest,
    result: Task172LocalResult,
    provider: CoolPropProvider,
) -> dict[str, Any]:
    assert recompute_task172_request_hash(request) == result.request_hash
    assert recompute_task172_result_hash(result) == result.result_hash
    assert result.result_id == f"urn:hxforge:task172:{result.result_hash}"
    support_id = runtime_service.recompute_task172_support_id(request)
    assert result.physical_support_id == support_id
    assert result.tube_cell_id == request.support.tube_cell_id
    assert result.shell_cell_id == request.support.shell_cell_id
    assert result.wall_interface_id == request.support.wall_interface_id
    tube_snapshot, tube_id, _ = runtime_service._snapshot(
        provider,
        request,
        "TUBE",
        f"{request.support.tube_cell_id}:CELL_MEAN",
        request.tube_bulk_state.temperature_k,
        request.tube_bulk_state.pressure_pa,
    )
    shell_snapshot, shell_id, _ = runtime_service._snapshot(
        provider,
        request,
        "SHELL",
        f"{request.support.shell_cell_id}:CELL_MEAN",
        request.shell_bulk_state.temperature_k,
        request.shell_bulk_state.pressure_pa,
    )
    tube_wall_snapshot, tube_wall_id, _ = runtime_service._snapshot(
        provider,
        request,
        "TUBE",
        f"{request.support.wall_interface_id}:TUBE_FLUID_WALL_INTERFACE",
        result.wall_temperature_inner_k,
        request.tube_bulk_state.pressure_pa,
    )
    shell_wall_snapshot, shell_wall_id, _ = runtime_service._snapshot(
        provider,
        request,
        "SHELL",
        f"{request.support.wall_interface_id}:SHELL_FLUID_WALL_INTERFACE",
        result.wall_temperature_outer_k,
        request.shell_bulk_state.pressure_pa,
    )
    assert result.tube_property_snapshot_identity == tube_id
    assert result.shell_property_snapshot_identity == shell_id
    assert result.tube_wall_property_snapshot_identity == tube_wall_id
    assert result.shell_wall_property_snapshot_identity == shell_wall_id
    bounds = runtime_service.recompute_task172_local_roundoff_bounds(request, result)[:3]
    assert all(
        abs(residual) <= bound
        for residual, bound in zip(result.residual_vector_w, bounds, strict=True)
    )
    assert result.signed_q_hot_to_cold_w >= 0
    assert (
        request.shell_bulk_state.temperature_k
        <= result.wall_temperature_outer_k
        <= result.wall_temperature_inner_k
        <= request.tube_bulk_state.temperature_k
    )
    return {
        "request_hash": result.request_hash,
        "result_id": result.result_id,
        "result_hash": result.result_hash,
        "support_id": support_id,
        "tube_cell_id": result.tube_cell_id,
        "shell_cell_id": result.shell_cell_id,
        "wall_interface_id": result.wall_interface_id,
        "property_snapshot_ids": [tube_id, shell_id, tube_wall_id, shell_wall_id],
        "property_snapshot_hashes": [
            tube_snapshot.property_snapshot_hash,
            shell_snapshot.property_snapshot_hash,
            tube_wall_snapshot.property_snapshot_hash,
            shell_wall_snapshot.property_snapshot_hash,
        ],
        "tube_htc_w_m2_k": str(result.tube_htc_w_m2_k),
        "shell_htc_w_m2_k": str(result.shell_htc_w_m2_k),
        "q_w": str(result.signed_q_hot_to_cold_w),
        "wall_inner_k": str(result.wall_temperature_inner_k),
        "wall_outer_k": str(result.wall_temperature_outer_k),
        "residuals_w": [str(value) for value in result.residual_vector_w],
        "r98_bounds_w": [str(value) for value in bounds],
        "solver_status": result.solver_status,
        "solver_nfev": result.solver_nfev,
        "callback_count": result.residual_callback_count,
    }


def test_proposed_fail_only_original_seed_dogbox_candidate_diagnostic_capture(
    record_property: Any,
) -> None:
    """Diagnostic-only proposed fallback; never changes TASK172 production authority."""
    from hexagent.exchangers.shell_tube.task173_integrated_rating.replay import (
        replay_shell_flow_authority,
    )

    provider = CoolPropProvider()
    repository_root = Path(__file__).parents[3]
    stage2_path = (
        repository_root
        / "docs"
        / "tasks"
        / "evidence"
        / "TASK-172-stage2-native-shell-flow-replay-correction-r1.json"
    )
    stage2 = json.loads(stage2_path.read_text(encoding="utf-8"))
    shell_authority, _, shell_replay = replay_shell_flow_authority(stage2, provider)
    assert shell_replay["status"] == "PASS"

    holes = json.loads(_DOGBOX_HOLE_FIXTURE.read_text(encoding="utf-8"))["holes"]
    fixture = json.loads(_DOGBOX_CORPUS_FIXTURE.read_text(encoding="utf-8"))
    fresh = json.loads(_DOGBOX_FRESH_CORPUS_FIXTURE.read_text(encoding="utf-8"))
    assert fixture["n32_fresh_replay"]["task172_attempts"] == 4617
    assert fixture["n32_fresh_replay"]["hole_count"] == 6
    assert len(fixture["baseline_valid_requests"]) == 18
    assert len(fresh["samples"]) == 50

    n32_hole_q = {
        "91c13f7949d32d90de13f95b14b2fc521f822c13f009ea6d132f965936cbb75f": 13126.5211409284,
        "946e8d83c8052f3c1db6f8aa31793f2b0b1523f7e392a1fa9e1da675daadde85": 12238.6979627684,
        "0b1a138aa86081e91b23d814fd9309c14ae0d8087bdff230b41ca1cf9dfb9d9a": 281.753033433674,
        "5fd98bd16cf306447b5ba359f44078d4dedca27d861d5573a0cafc4eeab2d0d3": 282.95916799460576,
        "3ffebffa5aaf4957cd4d743e8530885795831d29328b5a2fc63e55287d08720d": 0.0,
        "a52cda0abab920f9fd3a853e0ba3f3fa4289c38c88768bcda054377af08b70ec": 1834.90115580185,
    }
    hole_results: list[dict[str, Any]] = []
    baseline_classifications: list[str] = []
    for item in holes:
        request = _candidate_request_from_projection(item["request"], shell_authority)
        request_hash = recompute_task172_request_hash(request)
        assert request_hash == item["request_hash"]
        baseline, baseline_capture = _capture_r94_or_dogbox_candidate(
            request, provider, method="trf"
        )
        assert baseline.request_hash == request_hash
        assert baseline_capture["requested_options"]["method"] == "trf"
        assert baseline_capture["requested_options"]["max_nfev"] == 6
        if type(baseline) is Task172BlockedResult:
            baseline_classification = baseline.failure_code
            baseline_hash_replay = (
                baseline.blocked_result_hash == recompute_task172_blocked_result_hash(baseline)
            )
        elif type(baseline) is Task172LocalResult:
            baseline_classification = "VALID_TASK172_RESULT"
            baseline_hash_replay = baseline.result_hash == recompute_task172_result_hash(baseline)
        else:
            baseline_classification = type(baseline).__name__
            baseline_hash_replay = False
        baseline_classifications.append(baseline_classification)

        fallback_calls: list[dict[str, Any]] = []

        def make_fallback(
            current_request: Task172LocalRequest,
            current_calls: list[dict[str, Any]],
        ) -> Any:
            def fallback() -> Any:
                result, capture = _capture_r94_or_dogbox_candidate(
                    current_request, provider, method="dogbox"
                )
                current_calls.append(capture)
                return result

            return fallback

        decision = _candidate_decision(request, baseline, make_fallback(request, fallback_calls))
        result = decision["result"]
        identity: dict[str, Any] | None = None
        candidate_solver: dict[str, Any] | None = None
        replay_identical = False
        if decision["fallback_invoked"]:
            assert baseline_classification == "BLOCKED_RESIDUAL_ACCEPTANCE"
            assert decision["path"] == "R94_TRF_RESIDUAL_FAIL_THEN_DOGBOX_FALLBACK"
            candidate_solver = fallback_calls[0]["solver"]
            if type(result) is Task172LocalResult:
                assert fallback_calls[0]["requested_options"]["method"] == "trf"
                assert (
                    fallback_calls[0]["requested_options"] == baseline_capture["requested_options"]
                )
                assert fallback_calls[0]["initial_x"] == baseline_capture["initial_x"]
                assert candidate_solver["method"] == "dogbox"
                assert candidate_solver["nfev"] <= 6
                assert candidate_solver["nfev"] > 0
                assert candidate_solver["callback_count"] <= 24
                assert result.residual_callback_count <= 24
                assert result.numerical_profile_id == _DOGBOX_CANDIDATE_AUTHORITY_ID
                assert result.solver_status.startswith(
                    "R94_TRF_RESIDUAL_FAIL_THEN_DOGBOX_FALLBACK_"
                )
                identity = _candidate_identity_receipt(request, result, provider)
                assert identity["result_hash"] == recompute_task172_result_hash(result)

                replay, replay_capture = _capture_r94_or_dogbox_candidate(
                    request, provider, method="dogbox"
                )
                assert type(replay) is Task172LocalResult
                replay_projection = _dogbox_candidate_projection(replay)
                assert replay_capture["initial_x"] == baseline_capture["initial_x"]
                assert replay_projection.result_hash == result.result_hash
                assert replay_projection.result_id == result.result_id
                assert replay_projection.model_dump(mode="json") == result.model_dump(mode="json")
                replay_identical = True
        elif type(result) is Task172LocalResult:
            assert decision["fallback_invoked"] is False
            assert result is baseline
            identity = _candidate_identity_receipt(request, result, provider)
        q_trial = Decimal(str(n32_hole_q[request_hash]))
        hole_results.append(
            {
                "request_hash": request_hash,
                "baseline_classification": baseline_classification,
                "baseline_failure_code": (
                    baseline.failure_code if type(baseline) is Task172BlockedResult else None
                ),
                "baseline_result_hash": (
                    baseline.result_hash if type(baseline) is Task172LocalResult else None
                ),
                "baseline_blocked_result_hash": (
                    baseline.blocked_result_hash if type(baseline) is Task172BlockedResult else None
                ),
                "baseline_hash_replay": baseline_hash_replay,
                "baseline_solver": baseline_capture["solver"],
                "original_seed": baseline_capture["initial_x"],
                "seed_projection_hash": runtime_service.canonical_sha256(
                    {"request_hash": request_hash, "original_seed": baseline_capture["initial_x"]}
                ),
                "fallback_invoked": decision["fallback_invoked"],
                "candidate_classification": decision["classification"],
                "candidate_solver": candidate_solver,
                "candidate_callback_count": (
                    result.residual_callback_count if type(result) is Task172LocalResult else None
                ),
                "candidate_result": identity,
                "task173_q_trial_w": str(q_trial),
                "f_q_w": (
                    str(q_trial - result.signed_q_hot_to_cold_w)
                    if type(result) is Task172LocalResult
                    else None
                ),
                "candidate_result_replay_identical": replay_identical,
            }
        )

    assert len(hole_results) == 6

    historical = fixture["n16_upper_target_hole"]
    historical_request = _candidate_request_from_projection(historical["request"], shell_authority)
    assert recompute_task172_request_hash(historical_request) == historical["request_hash"]
    historical_baseline, historical_baseline_capture = _capture_r94_or_dogbox_candidate(
        historical_request, provider, method="trf"
    )
    historical_fallback_captures: list[dict[str, Any]] = []

    def historical_fallback() -> Any:
        result, capture = _capture_r94_or_dogbox_candidate(
            historical_request, provider, method="dogbox"
        )
        historical_fallback_captures.append(capture)
        return result

    historical_decision = _candidate_decision(
        historical_request, historical_baseline, historical_fallback
    )
    historical_result = historical_decision["result"]
    historical_identity = (
        _candidate_identity_receipt(historical_request, historical_result, provider)
        if type(historical_result) is Task172LocalResult
        else None
    )
    historical_f_q = (
        str(Decimal("111.3949198456") - historical_result.signed_q_hot_to_cold_w)
        if type(historical_result) is Task172LocalResult
        else None
    )

    valid_rows = fixture["baseline_valid_requests"] + fresh["samples"]
    valid_hashes: list[str] = []
    valid_sources: dict[str, int] = {}
    valid_corpus_report: list[dict[str, Any]] = []
    baseline_valid_count = 0
    fallback_invocations_on_baseline_valid = 0
    baseline_hashes_preserved = 0
    local_reference_hash_matches = 0

    def make_corpus_fallback(
        current_request: Task172LocalRequest,
        current_captures: list[dict[str, Any]],
    ) -> Any:
        def fallback() -> Any:
            result, capture = _capture_r94_or_dogbox_candidate(
                current_request, provider, method="dogbox"
            )
            current_captures.append(capture)
            return result

        return fallback

    for sample in valid_rows:
        request = _candidate_request_from_projection(sample["request"], shell_authority)
        request_hash = recompute_task172_request_hash(request)
        assert request_hash == sample["request_hash"]
        baseline, baseline_capture = _capture_r94_or_dogbox_candidate(
            request, provider, method="trf"
        )
        fallback_captures: list[dict[str, Any]] = []
        decision = _candidate_decision(
            request, baseline, make_corpus_fallback(request, fallback_captures)
        )
        candidate_result = decision["result"]
        baseline_classification = (
            "VALID_TASK172_RESULT"
            if type(baseline) is Task172LocalResult
            else baseline.failure_code
            if type(baseline) is Task172BlockedResult
            else type(baseline).__name__
        )
        candidate_identity = (
            _candidate_identity_receipt(request, candidate_result, provider)
            if type(candidate_result) is Task172LocalResult
            else None
        )
        expected_result = sample.get("result", {})
        baseline_hash = baseline.result_hash if type(baseline) is Task172LocalResult else None
        candidate_hash = (
            candidate_result.result_hash if type(candidate_result) is Task172LocalResult else None
        )
        baseline_is_valid = type(baseline) is Task172LocalResult
        baseline_valid_count += int(baseline_is_valid)
        fallback_invoked = bool(decision["fallback_invoked"])
        fallback_invocations_on_baseline_valid += int(baseline_is_valid and fallback_invoked)
        hash_preserved = bool(
            baseline_is_valid
            and type(candidate_result) is Task172LocalResult
            and candidate_result is baseline
            and candidate_hash == baseline_hash
        )
        baseline_hashes_preserved += int(hash_preserved)
        reference_hash_matches = candidate_hash == sample.get("result_hash")
        local_reference_hash_matches += int(reference_hash_matches)
        if candidate_hash is not None:
            valid_hashes.append(candidate_hash)
        source = sample.get("source", f"fresh_n{sample.get('mesh_n')}_production_path")
        valid_sources[source] = valid_sources.get(source, 0) + 1
        valid_corpus_report.append(
            {
                "request_hash": request_hash,
                "fixture_request_hash": sample.get("request_hash"),
                "source": source,
                "baseline_classification": baseline_classification,
                "baseline_result_hash": baseline_hash,
                "baseline_result_id": (
                    baseline.result_id if type(baseline) is Task172LocalResult else None
                ),
                "baseline_blocked_result_hash": (
                    baseline.blocked_result_hash if type(baseline) is Task172BlockedResult else None
                ),
                "baseline_solver": baseline_capture["solver"],
                "fallback_invoked": fallback_invoked,
                "fallback_solver": (fallback_captures[0]["solver"] if fallback_captures else None),
                "candidate_classification": decision["classification"],
                "candidate_result_hash": candidate_hash,
                "candidate_result_id": (
                    candidate_result.result_id
                    if type(candidate_result) is Task172LocalResult
                    else None
                ),
                "candidate_identity_replay": candidate_identity is not None,
                "candidate_is_baseline_object": candidate_result is baseline,
                "baseline_hash_preserved": hash_preserved,
                "matches_local_reference_hash": reference_hash_matches,
                "candidate_q_w": (
                    str(candidate_result.signed_q_hot_to_cold_w)
                    if type(candidate_result) is Task172LocalResult
                    else None
                ),
                "candidate_wall_inner_k": (
                    str(candidate_result.wall_temperature_inner_k)
                    if type(candidate_result) is Task172LocalResult
                    else None
                ),
                "candidate_wall_outer_k": (
                    str(candidate_result.wall_temperature_outer_k)
                    if type(candidate_result) is Task172LocalResult
                    else None
                ),
                "candidate_residuals_w": (
                    [str(value) for value in candidate_result.residual_vector_w]
                    if type(candidate_result) is Task172LocalResult
                    else None
                ),
                "candidate_property_snapshot_ids": (
                    [
                        candidate_result.tube_property_snapshot_identity,
                        candidate_result.shell_property_snapshot_identity,
                        candidate_result.tube_wall_property_snapshot_identity,
                        candidate_result.shell_wall_property_snapshot_identity,
                    ]
                    if type(candidate_result) is Task172LocalResult
                    else None
                ),
                "candidate_property_snapshot_hashes": (
                    candidate_identity["property_snapshot_hashes"]
                    if candidate_identity is not None
                    else None
                ),
                "candidate_htc_w_m2_k": (
                    {
                        "tube": str(candidate_result.tube_htc_w_m2_k),
                        "shell": str(candidate_result.shell_htc_w_m2_k),
                    }
                    if type(candidate_result) is Task172LocalResult
                    else None
                ),
                "fixture_result_projection": expected_result,
            }
        )

    assert len(valid_rows) == 68
    assert sum(valid_sources.get(f"fresh_n{n}_production_path", 0) for n in (8, 16)) == 50
    assert any(
        sample["request_hash"] == "fd9287e7200cc1fa723ecfeef31067d907a484bf18558b05a8488e5ed6e90cb9"
        for sample in valid_rows
    )
    assert valid_sources.get("predecessor_n16_upper_target_13_valid_requests") == 13
    assert valid_sources.get("fresh_n32_outer_iteration_23_valid_request") == 5

    low_duty_base = _candidate_request_from_projection(
        fresh["samples"][0]["request"], shell_authority
    )
    low_duty_request = low_duty_base.model_copy(
        update={
            "tube_bulk_state": low_duty_base.tube_bulk_state.model_copy(
                update={"temperature_k": Decimal("298.30")}
            ),
            "shell_bulk_state": low_duty_base.shell_bulk_state.model_copy(
                update={"temperature_k": Decimal("298.20")}
            ),
        }
    )
    low_duty_baseline = validate_request(low_duty_request, provider)
    assert type(low_duty_baseline) is Task172LocalResult
    low_duty_fallback_called = False

    def unexpected_low_duty_fallback() -> Any:
        nonlocal low_duty_fallback_called
        low_duty_fallback_called = True
        raise AssertionError("baseline-valid low-duty request must bypass fallback")

    low_duty_decision = _candidate_decision(
        low_duty_request, low_duty_baseline, unexpected_low_duty_fallback
    )
    assert low_duty_decision["fallback_invoked"] is False
    assert low_duty_decision["result"] is low_duty_baseline
    assert low_duty_fallback_called is False
    assert low_duty_baseline.signed_q_hot_to_cold_w < Decimal("525.8138170509478")
    low_duty_identity = _candidate_identity_receipt(low_duty_request, low_duty_baseline, provider)

    candidate_report = {
        "proposed_only": True,
        "authority_id": _DOGBOX_CANDIDATE_AUTHORITY_ID,
        "python": sys.version,
        "platform": platform.platform(),
        "coolprop": CoolProp.__version__,
        "scipy": scipy.__version__,
        "primary": {"method": "trf", "max_nfev": 6, "callback_cap": 24},
        "fallback": {
            "method": "dogbox",
            "initialization": "ORIGINAL_R94_DETERMINISTIC_SEED",
            "max_nfev": 6,
            "callback_cap": 24,
        },
        "target_holes": hole_results,
        "target_holes_baseline_classifications": baseline_classifications,
        "target_holes_all_baseline_residual_holes": all(
            value == "BLOCKED_RESIDUAL_ACCEPTANCE" for value in baseline_classifications
        ),
        "target_holes_all_recovered_by_fallback": all(
            item["fallback_invoked"]
            and item["candidate_result"] is not None
            and item["candidate_result_replay_identical"]
            for item in hole_results
        ),
        "target_holes_fallback_invocation_count": sum(
            int(item["fallback_invoked"]) for item in hole_results
        ),
        "target_holes_recovered_count": sum(
            int(item["candidate_classification"] == "VALIDATED") for item in hole_results
        ),
        "n16_upper_endpoint": {
            "request_hash": historical["request_hash"],
            "baseline_classification": (
                historical_baseline.failure_code
                if type(historical_baseline) is Task172BlockedResult
                else "VALID_TASK172_RESULT"
                if type(historical_baseline) is Task172LocalResult
                else type(historical_baseline).__name__
            ),
            "fallback_invoked": historical_decision["fallback_invoked"],
            "fallback_solver": (
                historical_fallback_captures[0]["solver"] if historical_fallback_captures else None
            ),
            "candidate_result": historical_identity,
            "candidate_f_q_w": historical_f_q,
            "r3_authority_changed": False,
        },
        "baseline_valid_corpus": {
            "size": len(valid_rows),
            "current_baseline_valid_count": baseline_valid_count,
            "fallback_invocations": sum(
                int(
                    row["fallback_invoked"]
                    and row["baseline_classification"] == "VALID_TASK172_RESULT"
                )
                for row in valid_corpus_report
            ),
            "hashes_preserved": baseline_hashes_preserved,
            "local_reference_hash_matches": local_reference_hash_matches,
            "local_reference_hashes_match_all": local_reference_hash_matches
            == baseline_valid_count,
            "fallback_bypassed_for_every_baseline_valid": (
                fallback_invocations_on_baseline_valid == 0
                and baseline_hashes_preserved == baseline_valid_count
            ),
            "sources": valid_sources,
            "results": valid_corpus_report,
        },
        "additional_low_duty_valid_edge_case": low_duty_identity,
    }
    serialized = json.dumps(candidate_report, sort_keys=True, separators=(",", ":"))
    record_property("task172_fail_only_dogbox_candidate", serialized)
    print(f"TASK172_FAIL_ONLY_DOGBOX_CANDIDATE={serialized}")
    # Portability is an adjudication outcome, not a test precondition. Keep the
    # complete native matrix in JUnit even when an environment's baseline
    # classification or result identity differs from the local reference.
    assert fallback_invocations_on_baseline_valid == 0
    assert baseline_hashes_preserved == baseline_valid_count


@pytest.mark.parametrize(
    "failure_code",
    [
        "BLOCKED_NONCONVERGENCE",
        "BLOCKED_SOLVER_FAILURE",
        "BLOCKED_SOLVER_RESOURCE_EXHAUSTION",
        "BLOCKED_PROPERTY_TEMPERATURE_DOMAIN_EXIT",
        "BLOCKED_NEGATIVE_PHYSICAL_HEAT_RATE",
        "BLOCKED_PHYSICAL_WALL_ORDERING",
        "BLOCKED_INVALID_REQUEST_IDENTITY_REPLAY",
    ],
)
def test_proposed_dogbox_fallback_never_consumes_non_residual_blockers(
    failure_code: str,
) -> None:
    request = _request()
    blocked = runtime_service._blocked(
        failure_code,
        "candidate.non_residual_blocker",
        recompute_task172_request_hash(request),
    )
    calls: list[bool] = []

    def fallback() -> Any:
        calls.append(True)
        raise AssertionError("non-residual blocker must not trigger fallback")

    decision = _candidate_decision(request, blocked, fallback)
    assert decision["fallback_invoked"] is False
    assert decision["result"] is blocked
    assert decision["classification"] == failure_code
    assert calls == []


def test_proposed_dogbox_fallback_rejects_invalid_residual_blocked_identity() -> None:
    request = _request()
    blocked = runtime_service._blocked(
        "BLOCKED_RESIDUAL_ACCEPTANCE",
        "candidate.invalid_request_hash",
        "0" * 64,
    )
    calls: list[bool] = []

    def fallback() -> Any:
        calls.append(True)
        raise AssertionError("invalid blocked-result request binding must not trigger fallback")

    decision = _candidate_decision(request, blocked, fallback)
    assert decision["fallback_invoked"] is False
    assert decision["classification"] == "BLOCKED_RESULT_IDENTITY_REPLAY"
    assert calls == []


def test_proposed_dogbox_fallback_rejects_invalid_blocked_result_hash() -> None:
    request = _request()
    blocked = runtime_service._blocked(
        "BLOCKED_RESIDUAL_ACCEPTANCE",
        "candidate.invalid_blocked_result_hash",
        recompute_task172_request_hash(request),
    ).model_copy(update={"blocked_result_hash": "0" * 64})
    calls: list[bool] = []

    def fallback() -> Any:
        calls.append(True)
        raise AssertionError("invalid blocked-result hash must not trigger fallback")

    decision = _candidate_decision(request, blocked, fallback)
    assert decision["fallback_invoked"] is False
    assert decision["classification"] == "BLOCKED_RESULT_IDENTITY_REPLAY"
    assert calls == []
