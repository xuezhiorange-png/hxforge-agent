"""Isolated 0.52 m shell layout recovery under segmental baffle cut (Task168 chain only)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.discrete_space import (
    format_engineering_decimal,
    load_v08_discrete_space,
)
from prototypes.v08_geometry_candidate_generation.generator import enumerate_structural_geometry
from prototypes.v08_geometry_candidate_generation.task168_builder import (
    build_v08_task168_request,
    filter_discrete_space_by_envelope,
)
from prototypes.v08_thermal_rating.task168_rejection_diagnostics_v08 import (
    BREAKTHROUGH_DISCRETE_SPACE_PATH,
)

_REPO = Path(__file__).resolve().parents[2]
SHELL_052_PROBE_M = Decimal("0.52")
_BFG_CODE = "BFG_BAFFLE_HOLE_DISK_INTERSECTS_CUT_BOUNDARY"


@dataclass(frozen=True)
class LayoutRecoveryAttempt:
    shell_inside_diameter_m: str
    baffle_cut_fraction: str
    placement_envelope_diameter_m: str
    task168_structurally_valid: bool
    physical_tube_count: int | None
    first_blocker_code: str | None
    failure_stage: str | None


@dataclass(frozen=True)
class LargerShellLayoutRecoveryReport:
    attempts: tuple[LayoutRecoveryAttempt, ...]
    larger_shell_layout_recovered: bool
    task168_result: str
    notes: tuple[str, ...]


def _with_envelope_override(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    discrete_path: Path,
    shell_m: Decimal,
    envelope_scale: Decimal,
) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    space = load_v08_discrete_space(discrete_path)
    filtered, _ = filter_discrete_space_by_envelope(space, normalized.design_envelope)
    filtered = replace(filtered, shell_inside_diameters_m=(shell_m,))
    t168 = build_v08_task168_request(normalized, handoff, filtered)
    tmpl = dict(t168.evaluation_input_authority.task021_request_template)
    envelope_m = (shell_m * envelope_scale).quantize(Decimal("0.0000000001"))
    tmpl.setdefault("placement_envelope", {})
    tmpl["placement_envelope"]["tube_center_envelope_diameter_m"] = str(envelope_m)
    tmpl["placement_envelope"]["evidence_refs"] = [
        "V08-03-CONSTRAINED-PLACEMENT-ENVELOPE-PROTOTYPE"
    ]
    from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
        evaluation_input_authority_hash,
    )

    evaluation = replace(
        t168.evaluation_input_authority,
        task021_request_template=tmpl,
        canonical_hash="",
    )
    evaluation = replace(
        evaluation, canonical_hash=evaluation_input_authority_hash(evaluation)
    )
    t168 = replace(t168, evaluation_input_authority=evaluation)
    enum = enumerate_structural_geometry(t168, filtered, (), max_valid_candidates=8)
    return enum.valid_structural, enum.rejections


def run_larger_shell_layout_recovery(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
) -> LargerShellLayoutRecoveryReport:
    """Probe supported single-segmental cuts with constrained Task021 placement envelopes."""
    attempts: list[LayoutRecoveryAttempt] = []
    notes: list[str] = []
    recovered = False
    for discrete_path, cut_label in (
        (BREAKTHROUGH_DISCRETE_SPACE_PATH, "0.35"),
        (
            _REPO / "docs/tasks/evidence/V08-03-breakthrough-discrete-space-cut049-r1.json",
            "0.49",
        ),
    ):
        space = load_v08_discrete_space(discrete_path)
        cut = Decimal(str(space.baffle_cut))
        for scale in (Decimal("0.90"), Decimal("0.85"), Decimal("0.80")):
            valid, rejections = _with_envelope_override(
                normalized,
                handoff,
                discrete_path=discrete_path,
                shell_m=SHELL_052_PROBE_M,
                envelope_scale=scale,
            )
            blocker = None
            stage = None
            if rejections:
                evidence = rejections[0].evidence
                blocker = evidence.get("blocker_code")
                stage = rejections[0].failure_stage
            attempt = LayoutRecoveryAttempt(
                shell_inside_diameter_m=format_engineering_decimal(SHELL_052_PROBE_M),
                baffle_cut_fraction=str(cut),
                placement_envelope_diameter_m=str(SHELL_052_PROBE_M * scale),
                task168_structurally_valid=bool(valid),
                physical_tube_count=(
                    int(valid[0].bundle.task021_layout.physical_tube_count) if valid else None
                ),
                first_blocker_code=blocker,
                failure_stage=stage,
            )
            attempts.append(attempt)
            if valid:
                recovered = True
                notes.append(
                    f"recovered_at_cut={cut_label}_envelope_scale={scale}_tubes={attempt.physical_tube_count}"
                )
                break
        if recovered:
            break

    bfg_hits = sum(1 for a in attempts if a.first_blocker_code == _BFG_CODE)
    if bfg_hits and not recovered:
        notes.append(f"{_BFG_CODE}_persisted_across_envelope_probes")
    task168_result = "STRUCTURAL_PASS" if recovered else "NO_VALID_0P52M_LAYOUT"
    return LargerShellLayoutRecoveryReport(
        attempts=tuple(attempts),
        larger_shell_layout_recovered=recovered,
        task168_result=task168_result,
        notes=tuple(notes),
    )


__all__ = [
    "LargerShellLayoutRecoveryReport",
    "run_larger_shell_layout_recovery",
]