"""Targeted tests for FIXED_LAYOUT_VARIABLE_MDOT_HYDRAULIC_REPLAY_V1 (prototype)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.loader import load_general_user_design_case_json
from prototypes.v08_general_user_case.pipeline import validate_and_build_solver_handoff
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import build_candidate_rating_bindings
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.engineering_shortlist_robustness_v08 import (
    _CANONICAL_SCALE,
    _build_t168_with_envelope,
    _fixed_layout_tube_side_replay,
    _handoff_for_case,
    _perturb_case,
    _resolve_structural,
)
from prototypes.v08_thermal_rating.fixed_layout_variable_mdot_hydraulic_replay_v1 import (
    evaluate_mdot_scenario_v1,
    run_replay_matrix_v1,
)
from prototypes.v08_thermal_rating.v08_r27_hydraulic_bridge import (
    task174_hydraulic_postpass_from_bindings,
)


@pytest.fixture(scope="module")
def provider() -> CoolPropProvider:
    return CoolPropProvider()


@pytest.fixture(scope="module")
def normalized_handoff(provider: CoolPropProvider):
    case = load_general_user_design_case_json(FIXTURE_330.read_text(encoding="utf-8"))
    pipe = validate_and_build_solver_handoff(case, provider=provider)
    return pipe.normalized, pipe.handoff


def test_replay_matrix_covers_24_scenarios(provider: CoolPropProvider) -> None:
    payload = run_replay_matrix_v1(provider=provider)
    assert payload["scenario_count"] == 24
    assert payload["nonbaseline_count"] == 20
    assert payload["fixed_geometry_identity_pass"] is True
    assert payload["variable_mdot_binding_all_pass"] is True
    assert payload["physical_model_blocked_count"] == 4


def test_nonbaseline_tube_dp_differs_from_frozen_task174_postpass(
    provider: CoolPropProvider,
    normalized_handoff,
) -> None:
    normalized, handoff = normalized_handoff
    tube_count, tube_length_m = 235, Decimal("5.5")
    case_norm, _ = _perturb_case(normalized, scenario_key="tube_mdot_minus_1pct")
    handoff_s = _handoff_for_case(case_norm, provider)
    structural, outcome = _resolve_structural(
        normalized,
        handoff,
        tube_count=tube_count,
        tube_length_m=tube_length_m,
        envelope_scale=_CANONICAL_SCALE[tube_count],
    )
    scale = _CANONICAL_SCALE[tube_count]
    t168 = _build_t168_with_envelope(case_norm, handoff_s, scale)
    _fixed_layout_tube_side_replay(
        structural, t168=t168, scenario_key="tube_mdot_minus_1pct", baseline_re="5000"
    )
    from prototypes.v08_geometry_candidate_generation.geometry_identity_v2 import (
        geometry_projection_hash_v1,
    )

    bindings = build_candidate_rating_bindings(
        structural,
        space_hash=outcome.space_hash,
        t168_digest=structural.task168_request_hash_digest,
        normalized=case_norm,
        handoff=handoff_s,
        provider=provider,
        geometry_projection_hash=geometry_projection_hash_v1(structural),
    )
    assert bindings is not None
    frozen = task174_hydraulic_postpass_from_bindings(bindings)
    row = evaluate_mdot_scenario_v1(
        tube_count=tube_count,
        tube_length_m=tube_length_m,
        scenario_key="tube_mdot_minus_1pct",
        normalized_baseline=normalized,
        handoff_baseline=handoff,
        provider=provider,
    )
    assert row.variable_mdot_binding_pass is True
    assert row.tube_task029_dp_pa is not None
    assert row.tube_task029_dp_pa != frozen["recalculated_tube_dp_pa"]
    assert len(row.loss_tiers) == 3


def test_task027_blocks_241_tube_minus_3pct(
    provider: CoolPropProvider,
    normalized_handoff,
) -> None:
    normalized, handoff = normalized_handoff
    row = evaluate_mdot_scenario_v1(
        tube_count=241,
        tube_length_m=Decimal("6.0"),
        scenario_key="tube_mdot_minus_3pct",
        normalized_baseline=normalized,
        handoff_baseline=handoff,
        provider=provider,
    )
    assert row.outcome == "PHYSICAL_MODEL_BLOCKED"
    assert row.task027_blocker == "BL_T027_UNSUPPORTED_REYNOLDS_REGIME"


def test_artifact_written_when_matrix_runs(provider: CoolPropProvider, tmp_path: Path) -> None:
    from prototypes.v08_thermal_rating import fixed_layout_variable_mdot_hydraulic_replay_v1 as mod

    out = tmp_path / "replay.json"
    payload = run_replay_matrix_v1(provider=provider)
    mod.write_artifact(out, payload)
    assert out.is_file()
    assert payload["full_path_computed_count"] >= 12