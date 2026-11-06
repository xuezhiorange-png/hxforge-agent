"""End-to-end V08-02 pipeline from user case JSON to geometry candidates."""

from __future__ import annotations

from pathlib import Path

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.loader import load_general_user_design_case_json
from prototypes.v08_general_user_case.pipeline import validate_and_build_solver_handoff
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.generator import generate_geometry_candidates
from prototypes.v08_geometry_candidate_generation.models import V08GeometryGenerationResult


def generate_geometry_from_user_case_path(
    path: Path,
    *,
    provider: CoolPropProvider | None = None,
    discrete_space_path: Path | None = None,
) -> V08GeometryGenerationResult:
    case = load_general_user_design_case_json(path.read_text(encoding="utf-8"))
    coolprop = provider or CoolPropProvider()
    pipeline = validate_and_build_solver_handoff(case, provider=coolprop)
    return generate_geometry_candidates(
        pipeline.normalized,
        pipeline.handoff,
        discrete_space_path=discrete_space_path,
    )


def generate_geometry_from_validated(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    discrete_space_path: Path | None = None,
) -> V08GeometryGenerationResult:
    return generate_geometry_candidates(
        normalized,
        handoff,
        discrete_space_path=discrete_space_path,
    )
