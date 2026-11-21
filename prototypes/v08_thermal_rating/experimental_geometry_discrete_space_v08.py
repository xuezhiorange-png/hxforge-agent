"""Experimental V08-03 geometry discrete space (does not replace R1 authority)."""

from __future__ import annotations

from pathlib import Path

from prototypes.v08_geometry_candidate_generation.discrete_space import (
    DEFAULT_V08_DISCRETE_SPACE_PATH,
    V08DiscreteSpaceAuthority,
    load_v08_discrete_space,
)

REPO = Path(__file__).resolve().parents[2]
EXPERIMENTAL_V08_DISCRETE_SPACE_PATH = (
    REPO / "docs/tasks/evidence/V08-03-experimental-geometry-discrete-space-r1.json"
)
EXPERIMENTAL_GEOMETRY_LABEL = "EXPERIMENTAL_GEOMETRY_NOT_MANUFACTURING_APPROVED"


def load_approved_r1_discrete_space() -> V08DiscreteSpaceAuthority:
    return load_v08_discrete_space(DEFAULT_V08_DISCRETE_SPACE_PATH)


def load_experimental_coopt_discrete_space() -> V08DiscreteSpaceAuthority:
    return load_v08_discrete_space(EXPERIMENTAL_V08_DISCRETE_SPACE_PATH)


__all__ = [
    "EXPERIMENTAL_GEOMETRY_LABEL",
    "EXPERIMENTAL_V08_DISCRETE_SPACE_PATH",
    "load_approved_r1_discrete_space",
    "load_experimental_coopt_discrete_space",
]
