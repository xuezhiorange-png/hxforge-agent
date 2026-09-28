"""Production-contract tests for the TASK172 local constitutive runtime."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

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
