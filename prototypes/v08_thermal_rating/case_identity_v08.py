"""V08 engineering case identity (250 kW vs 330 kW) — hashes only, no cross-mixing."""
# ruff: noqa: E501

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    request_hash as task168_request_hash_digest,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.loader import load_general_user_design_case_json
from prototypes.v08_general_user_case.pipeline import validate_and_build_solver_handoff
from prototypes.v08_geometry_candidate_generation.discrete_space import (
    DEFAULT_V08_DISCRETE_SPACE_PATH,
    load_v08_discrete_space,
)
from prototypes.v08_geometry_candidate_generation.generator import enumerate_structural_geometry
from prototypes.v08_geometry_candidate_generation.task168_builder import (
    build_v08_task168_request,
    filter_discrete_space_by_envelope,
)

REPO = Path(__file__).resolve().parents[2]
FIXTURE_250 = REPO / "tests/fixtures/v08_user_case_no_geometry_task174_admissible.json"
FIXTURE_330 = REPO / "tests/fixtures/v08_user_case_hxforge_330kw_strict_dp.json"

CASE_250KW_ID = "V08_250KW_TASK174_ADMISSIBLE"
CASE_330KW_ID = "HXFORGE_330KW_STRICT_DP"


def _case_row(fixture: Path, case_label: str) -> dict[str, Any]:
    text = fixture.read_text(encoding="utf-8")
    case = load_general_user_design_case_json(text)
    pipeline = validate_and_build_solver_handoff(case, provider=CoolPropProvider())
    normalized = pipeline.normalized
    handoff = pipeline.handoff
    space = load_v08_discrete_space(DEFAULT_V08_DISCRETE_SPACE_PATH)
    filtered, _ = filter_discrete_space_by_envelope(space, normalized.design_envelope)
    t168 = build_v08_task168_request(normalized, handoff, filtered)
    digest = task168_request_hash_digest(t168)
    enum = enumerate_structural_geometry(t168, filtered, (), max_valid_candidates=256)
    fixture_sha = hashlib.sha256(text.encode()).hexdigest()
    return {
        "case_label": case_label,
        "fixture_path": str(fixture.relative_to(REPO)),
        "engineering_case_id": normalized.engineering_case_id,
        "normalized_input_hash": handoff.normalized_input_hash,
        "downstream_readiness": handoff.downstream_readiness,
        "task168_request_hash": digest,
        "candidate_space_hash": enum.space_hash,
        "fixture_sha256": fixture_sha,
        "target_duty_w": str(normalized.target_duty_w),
        "tube_inlet_k": str(normalized.tube_side.inlet_temperature_k),
        "shell_inlet_k": str(normalized.shell_side.inlet_temperature_k),
        "tube_mdot_kg_s": str(normalized.tube_side.mass_flow_kg_s),
        "shell_mdot_kg_s": str(normalized.shell_side.mass_flow_kg_s),
    }


def build_case_identity_bundle() -> dict[str, Any]:
    row_250 = _case_row(FIXTURE_250, CASE_250KW_ID)
    row_330 = _case_row(FIXTURE_330, CASE_330KW_ID)
    thermal_identity_distinct = row_250["normalized_input_hash"] != row_330["normalized_input_hash"]
    task168_distinct = row_250["task168_request_hash"] != row_330["task168_request_hash"]
    return {
        "CASE_250KW_IDENTITY": row_250,
        "CASE_330KW_IDENTITY": row_330,
        "CASE_CROSS_CONTAMINATION": not (thermal_identity_distinct and task168_distinct),
        "shared_candidate_space_hash": row_250["candidate_space_hash"]
        == row_330["candidate_space_hash"],
        "candidate_e1_9277_case_binding": CASE_250KW_ID,
        "note": "e1baa795 / 9277ebb8 enumerated from 250 kW fixture only",
    }
