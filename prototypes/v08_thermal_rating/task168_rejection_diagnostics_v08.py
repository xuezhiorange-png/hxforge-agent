"""Per-shell Task168 rejection evidence (no summarized failure text)."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.discrete_space import (
    load_v08_discrete_space,
)
from prototypes.v08_geometry_candidate_generation.generator import enumerate_structural_geometry
from prototypes.v08_geometry_candidate_generation.task168_builder import (
    build_v08_task168_request,
    filter_discrete_space_by_envelope,
)
from prototypes.v08_thermal_rating.experimental_geometry_discrete_space_v08 import (
    EXPERIMENTAL_V08_DISCRETE_SPACE_PATH,
)

_REPO = Path(__file__).resolve().parents[2]
BREAKTHROUGH_DISCRETE_SPACE_PATH = (
    _REPO / "docs/tasks/evidence/V08-03-breakthrough-discrete-space-r1.json"
)


@dataclass(frozen=True)
class Task168RejectionRow:
    shell_inside_diameter_m: str
    tube_length_m: str
    baffle_spacing_m: str
    baffle_cut_fraction: str
    failure_stage: str
    reason_codes: tuple[str, ...]
    blocker_code: str | None
    field_path: str | None
    message: str


def _enumerate_with_payload(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    discrete_path: Path,
    baffle_cut_override: Decimal | None = None,
) -> tuple[str, str, tuple[Any, ...], tuple[Any, ...]]:
    space = load_v08_discrete_space(discrete_path)
    if baffle_cut_override is not None and baffle_cut_override != space.baffle_cut:
        raise ValueError(
            f"baffle_cut_override {baffle_cut_override} inconsistent with discrete space {space.baffle_cut}"
        )
    filtered, _ = filter_discrete_space_by_envelope(space, normalized.design_envelope)
    t168 = build_v08_task168_request(normalized, handoff, filtered)
    enum = enumerate_structural_geometry(t168, filtered, (), max_valid_candidates=128)
    cut = str(baffle_cut_override or space.baffle_cut)
    rows: list[Task168RejectionRow] = []
    for r in enum.rejections:
        rows.append(
            Task168RejectionRow(
                shell_inside_diameter_m=str(r.evidence.get("shell_inside_diameter_m", "")),
                tube_length_m=str(r.evidence.get("tube_length_m", "")),
                baffle_spacing_m=str(r.evidence.get("baffle_spacing_m", "")),
                baffle_cut_fraction=cut,
                failure_stage=r.failure_stage,
                reason_codes=r.reason_codes,
                blocker_code=r.evidence.get("blocker_code"),
                field_path=r.evidence.get("field_path"),
                message=str(r.evidence.get("message", "")),
            )
        )
    digest = ""
    if enum.valid_structural:
        digest = enum.valid_structural[0].task168_request_hash_digest
    return enum.space_hash, digest, enum.valid_structural, tuple(rows)


def collect_larger_shell_task168_rejections(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    shell_diameters_m: tuple[str, ...] = ("0.52", "0.58", "0.62", "0.65"),
) -> tuple[Task168RejectionRow, ...]:
    """Baseline experimental space (baffle_cut 0.25) for shells that fail before hydraulics."""
    _sh, _dg, _valid, rows = _enumerate_with_payload(
        normalized, handoff, discrete_path=EXPERIMENTAL_V08_DISCRETE_SPACE_PATH
    )
    target = {str(s) for s in shell_diameters_m}
    return tuple(r for r in rows if r.shell_inside_diameter_m in target)


__all__ = [
    "BREAKTHROUGH_DISCRETE_SPACE_PATH",
    "Task168RejectionRow",
    "_enumerate_with_payload",
    "collect_larger_shell_task168_rejections",
]
