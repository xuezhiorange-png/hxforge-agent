"""Tests for V08-02 automatic geometry candidate generation."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from hexagent.canonical_json import canonical_sha256
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.loader import load_general_user_design_case_json
from prototypes.v08_general_user_case.physical_feasibility import assess_physical_feasibility
from prototypes.v08_general_user_case.pipeline import validate_and_build_solver_handoff
from prototypes.v08_general_user_case.solver_handoff import build_solver_handoff
from prototypes.v08_general_user_case.user_design_case import OptionalDesignEnvelopeConstraints
from prototypes.v08_geometry_candidate_generation.discrete_space import (
    DEFAULT_V08_DISCRETE_SPACE_PATH,
    load_v08_discrete_space,
)
from prototypes.v08_geometry_candidate_generation.generator import generate_geometry_candidates
from prototypes.v08_geometry_candidate_generation.pipeline import (
    generate_geometry_from_user_case_path,
)
from prototypes.v08_geometry_candidate_generation.task168_builder import (
    build_v08_task168_request,
    filter_discrete_space_by_envelope,
    read_task168_bound_process_inputs,
)

FIXTURE_NO_GEOMETRY = Path("tests/fixtures/v08_user_case_no_geometry.json")
REPO_ROOT = Path(__file__).resolve().parents[2]


def _handoff_from_fixture(path: Path = FIXTURE_NO_GEOMETRY):
    case = load_general_user_design_case_json((REPO_ROOT / path).read_text(encoding="utf-8"))
    pipeline = validate_and_build_solver_handoff(case, provider=CoolPropProvider())
    return pipeline.normalized, pipeline.handoff


@pytest.mark.timeout(600)
def test_v08_02_generates_at_least_two_distinct_valid_candidates() -> None:
    normalized, handoff = _handoff_from_fixture()
    result = generate_geometry_candidates(normalized, handoff)
    assert result.status == "OK", result.rejections[:5]
    assert len(result.candidates) >= 2
    assert result.distinct_valid_geometry_count >= 2
    hashes = {c.geometry_projection_hash for c in result.candidates}
    assert len(hashes) >= 2
    for candidate in result.candidates:
        assert candidate.thermal_rating_status == "THERMAL_RATING_PENDING"
        assert candidate.full_path_dp_status == "FULL_PATH_DP_PENDING"
        assert candidate.geometry_validation == "STRUCTURALLY_VALID"
    assert result.user_geometry_required is False
    assert result.preserved_search_parameters["target_duty_w"] == "250000"
    assert result.geometry_source_authority == "V08-GENERAL-GEOMETRY-DISCRETE-SPACE-R1"


@pytest.mark.timeout(600)
def test_v08_02_envelope_narrowing_changes_candidate_set() -> None:
    normalized, handoff = _handoff_from_fixture()
    wide = generate_geometry_candidates(normalized, handoff)
    assert wide.status == "OK"

    space = load_v08_discrete_space()
    filtered, _ = filter_discrete_space_by_envelope(
        space,
        normalized.design_envelope.model_copy(
            update={
                "max_shell_inside_diameter_m": Decimal("0.46"),
                "max_tube_length_m": Decimal("4.6"),
            }
        ),
    )
    assert filtered.shell_inside_diameters_m == (Decimal("0.45"),)

    tight_case = normalized.model_copy(
        update={
            "design_envelope": OptionalDesignEnvelopeConstraints(
                max_shell_inside_diameter_m=Decimal("0.46"),
                max_tube_length_m=Decimal("4.6"),
            )
        }
    )
    tight_handoff = build_solver_handoff(
        tight_case,
        assess_physical_feasibility(tight_case, CoolPropProvider()),
        CoolPropProvider(),
    )
    tight = generate_geometry_candidates(tight_case, tight_handoff)
    assert tight.status in {"OK", "NO_STRUCTURAL_CANDIDATE"}
    wide_shells = {c.shell_inside_diameter_m for c in wide.candidates}
    tight_shells = {c.shell_inside_diameter_m for c in tight.candidates}
    assert wide_shells != tight_shells or len(wide.candidates) > len(tight.candidates)


@pytest.mark.timeout(120)
def test_v08_02_no_structural_candidate_when_envelope_excludes_all() -> None:
    normalized, handoff = _handoff_from_fixture()

    impossible = normalized.model_copy(
        update={
            "design_envelope": OptionalDesignEnvelopeConstraints(
                min_shell_inside_diameter_m=Decimal("2.0"),
                max_shell_inside_diameter_m=Decimal("2.5"),
            )
        }
    )
    impossible_handoff = build_solver_handoff(
        impossible,
        assess_physical_feasibility(impossible, CoolPropProvider()),
        CoolPropProvider(),
    )
    result = generate_geometry_candidates(impossible, impossible_handoff)
    assert result.status == "NO_STRUCTURAL_CANDIDATE"
    assert not result.candidates
    assert any(
        "NO_AUTHORIZED_GEOMETRY_AFTER_ENVELOPE" in row.reason_codes for row in result.rejections
    )


@pytest.mark.timeout(600)
def test_v08_02_deterministic_result_hash() -> None:
    normalized, handoff = _handoff_from_fixture()
    first = generate_geometry_candidates(normalized, handoff)
    second = generate_geometry_candidates(normalized, handoff)
    assert first.result_hash == second.result_hash
    assert [c.candidate_id for c in first.candidates] == [c.candidate_id for c in second.candidates]


@pytest.mark.timeout(600)
def test_v08_02_pipeline_from_fixture_path() -> None:
    result = generate_geometry_from_user_case_path(REPO_ROOT / FIXTURE_NO_GEOMETRY)
    assert result.status == "OK"
    assert result.result_hash


@pytest.mark.timeout(120)
def test_v08_02_blocked_geometry_source_missing_catalog() -> None:
    normalized, handoff = _handoff_from_fixture()
    missing = REPO_ROOT / "tests/fixtures/v08_missing_discrete_space.json"
    result = generate_geometry_candidates(normalized, handoff, discrete_space_path=missing)
    assert result.status == "BLOCKED_GEOMETRY_SOURCE"


@pytest.mark.timeout(120)
def test_v08_02_does_not_reference_330kw_case_id() -> None:
    normalized, handoff = _handoff_from_fixture()
    result = generate_geometry_candidates(normalized, handoff)
    blob = json.dumps(result.as_dict())
    assert "330" not in blob or "250000" in blob
    assert normalized.engineering_case_id != "v07-acceptance-330kw"


def test_v08_02_discrete_space_evidence_on_disk() -> None:
    assert DEFAULT_V08_DISCRETE_SPACE_PATH.is_file()
    space = load_v08_discrete_space()
    assert space.approval_status.startswith("APPROVED")
    raw = json.loads(DEFAULT_V08_DISCRETE_SPACE_PATH.read_text())
    assert canonical_sha256(raw) == space.content_hash


@pytest.mark.timeout(120)
def test_v08_02_blocks_missing_handoff_mass_flow() -> None:
    normalized, handoff = _handoff_from_fixture()
    broken = handoff.model_copy(
        update={
            "consumable_parameters": {
                k: v
                for k, v in handoff.consumable_parameters.items()
                if k != "shell_mass_flow_kg_s"
            }
        }
    )
    result = generate_geometry_candidates(normalized, broken)
    assert result.status == "BLOCKED_USER_PARAMETER_BINDING"
    assert "shell_mass_flow_kg_s" in result.rejections[0].evidence.get("missing_fields", "")


@pytest.mark.timeout(120)
def test_v08_02_task168_inputs_follow_user_mass_flow_and_temperature() -> None:
    normalized, handoff_a = _handoff_from_fixture()
    space = load_v08_discrete_space()
    req_a = build_v08_task168_request(normalized, handoff_a, space)
    inputs_a = read_task168_bound_process_inputs(req_a)

    payload = json.loads((REPO_ROOT / FIXTURE_NO_GEOMETRY).read_text(encoding="utf-8"))
    payload["tube_side"]["mass_flow"] = {"value": 10.0, "unit": "kg/s"}
    payload["shell_side"]["mass_flow"] = {"value": 12.0, "unit": "kg/s"}
    payload["tube_side"]["inlet_temperature"] = {"value": 50, "unit": "degC"}
    payload["shell_side"]["inlet_temperature"] = {"value": 15, "unit": "degC"}
    case_b = load_general_user_design_case_json(json.dumps(payload))
    pipeline_b = validate_and_build_solver_handoff(case_b, provider=CoolPropProvider())
    req_b = build_v08_task168_request(pipeline_b.normalized, pipeline_b.handoff, space)
    inputs_b = read_task168_bound_process_inputs(req_b)

    assert inputs_a["tube_mass_flow_kg_s"] in {"14.5", "14.500000"}
    assert inputs_a["shell_mass_flow_kg_s"] in {"18", "18.0", "18.000000"}
    assert inputs_b["tube_mass_flow_kg_s"] in {"10", "10.0", "10.000000"}
    assert inputs_b["shell_mass_flow_kg_s"] in {"12", "12.0", "12.000000"}
    assert inputs_a["tube_inlet_temperature_k"] != inputs_b["tube_inlet_temperature_k"]
    assert inputs_a["shell_inlet_temperature_k"] != inputs_b["shell_inlet_temperature_k"]
    assert "20" not in inputs_a["shell_mass_flow_kg_s"]
    assert inputs_a["shell_mass_flow_kg_s"] != "20"


@pytest.mark.timeout(600)
def test_v08_02_per_shell_task021_envelope_scales_with_shell_id() -> None:
    from decimal import Decimal

    from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168
    from hexagent.exchangers.shell_tube.manufacturable_candidates.models import DIMENSION_ORDER

    normalized, handoff = _handoff_from_fixture()
    space = load_v08_discrete_space()
    t168 = build_v08_task168_request(normalized, handoff, space)
    authorities = task168._authority_map(t168)
    first_combo = tuple(
        task168._sort_values(authorities[role].values)[0]
        for role in DIMENSION_ORDER
        if role != "SHELL_GEOMETRY_ID"
    )
    envelopes: dict[str, str] = {}
    tube_counts: dict[str, int] = {}
    for record in t168.shell_geometry_catalog.records:
        candidate = task168._candidate(t168, authorities, record, first_combo)
        payload = task168._task021_payload(
            t168.evaluation_input_authority,
            candidate,
            t168.task020_configuration,
        )
        env = str(payload["placement_envelope"]["tube_center_envelope_diameter_m"])
        shell_m = Decimal(record.shell_inside_diameter_m)
        expected = str((shell_m * Decimal("0.9")).quantize(Decimal("0.0000000001")))
        assert env == expected
        envelopes[record.shell_inside_diameter_m] = env
        bundle, failure, _ = task168._execute_candidate_chain(
            t168,
            candidate,
            record,
            include_legacy_task162=False,
            include_legacy_task168_rating_dependencies=False,
            preserve_baffle_orientation_sequence=False,
        )
        if failure is None:
            tube_counts[record.shell_inside_diameter_m] = int(
                bundle.task021_layout.physical_tube_count
            )
    assert len(envelopes) >= 3
    assert len(set(envelopes.values())) >= 2
    assert len(tube_counts) >= 1
    if len(tube_counts) >= 2:
        assert len(set(tube_counts.values())) >= 2


@pytest.mark.timeout(120)
def test_v08_02_unauthorized_discrete_space_tube_mismatch_blocked() -> None:
    normalized, handoff = _handoff_from_fixture()
    bad = REPO_ROOT / "tests/fixtures/v08_discrete_space_bad_tube_od.json"
    result = generate_geometry_candidates(normalized, handoff, discrete_space_path=bad)
    assert result.status == "BLOCKED_GEOMETRY_SOURCE"
    assert "TASK-172" in result.rejections[0].evidence.get("message", "") or (
        "tube_outer_diameter" in result.rejections[0].evidence.get("message", "")
    )
