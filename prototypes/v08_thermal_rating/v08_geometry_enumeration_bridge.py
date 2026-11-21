"""Enumerate structural bundles from an explicit discrete-space path."""

from __future__ import annotations

from pathlib import Path

from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    request_hash as task168_request_hash_digest,
)
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.discrete_space import (
    load_v08_discrete_space,
)
from prototypes.v08_geometry_candidate_generation.generator import enumerate_structural_geometry
from prototypes.v08_geometry_candidate_generation.structural_bundles import (
    V08StructuralGeometryBundle,
)
from prototypes.v08_geometry_candidate_generation.task168_builder import (
    build_v08_task168_request,
    filter_discrete_space_by_envelope,
)


def enumerate_structural_bundles_for_space(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    discrete_space_path: Path,
    max_valid: int = 64,
) -> tuple[str, str, tuple[V08StructuralGeometryBundle, ...], dict[str, str]]:
    space = load_v08_discrete_space(discrete_space_path)
    filtered, _ = filter_discrete_space_by_envelope(space, normalized.design_envelope)
    t168 = build_v08_task168_request(normalized, handoff, filtered)
    t168_digest = task168_request_hash_digest(t168)
    enum = enumerate_structural_geometry(t168, filtered, (), max_valid_candidates=max_valid)
    geom_by_id = {row.candidate_id: row.geometry_projection_hash for row in enum.candidate_records}
    return enum.space_hash, t168_digest, enum.valid_structural, geom_by_id


__all__ = ["enumerate_structural_bundles_for_space"]
