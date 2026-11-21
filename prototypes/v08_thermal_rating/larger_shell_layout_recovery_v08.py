"""Isolated 0.52 m shell layout recovery under segmental baffle cut (Task168 chain only)."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.discrete_space import (
    V08DiscreteSpaceAuthority,
    format_engineering_decimal,
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
from prototypes.v08_thermal_rating.task168_rejection_diagnostics_v08 import (
    BREAKTHROUGH_DISCRETE_SPACE_PATH,
)

_REPO = Path(__file__).resolve().parents[2]
SHELL_052_PROBE_M = Decimal("0.52")
_BFG_CODE = "BFG_BAFFLE_HOLE_DISK_INTERSECTS_CUT_BOUNDARY"
RECOVERY_AUTHORITY_LABEL = "V08-03-CONSTRAINED-PLACEMENT-ENVELOPE-PROTOTYPE"


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


@dataclass(frozen=True)
class RecoveredShell052Bundle:
    """One Task168-valid 0.52 m bundle with provenance for downstream full-chain replay."""

    structural_bundle: V08StructuralGeometryBundle
    candidate_space_hash: str
    discrete_space_authority_id: str
    discrete_space_content_hash: str
    placement_envelope_diameter_m: str
    envelope_scale: str
    baffle_cut_fraction: str
    experimental_authority_label: str
    recovery_note: str


@dataclass(frozen=True)
class EnvelopeEnumerationOutcome:
    space_hash: str
    filtered_space: V08DiscreteSpaceAuthority
    valid_structural: tuple[V08StructuralGeometryBundle, ...]
    rejections: tuple[Any, ...]
    placement_envelope_diameter_m: str
    envelope_scale: Decimal


def _with_envelope_override(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    discrete_path: Path,
    shell_m: Decimal,
    envelope_scale: Decimal,
) -> EnvelopeEnumerationOutcome:
    space = load_v08_discrete_space(discrete_path)
    filtered, _ = filter_discrete_space_by_envelope(space, normalized.design_envelope)
    filtered = replace(filtered, shell_inside_diameters_m=(shell_m,))
    t168 = build_v08_task168_request(normalized, handoff, filtered)
    tmpl = dict(t168.evaluation_input_authority.task021_request_template)
    envelope_m = (shell_m * envelope_scale).quantize(Decimal("0.0000000001"))
    tmpl.setdefault("placement_envelope", {})
    tmpl["placement_envelope"]["tube_center_envelope_diameter_m"] = str(envelope_m)
    tmpl["placement_envelope"]["evidence_refs"] = [RECOVERY_AUTHORITY_LABEL]
    from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
        evaluation_input_authority_hash,
    )

    evaluation = replace(
        t168.evaluation_input_authority,
        task021_request_template=tmpl,
        canonical_hash="",
    )
    evaluation = replace(evaluation, canonical_hash=evaluation_input_authority_hash(evaluation))
    t168 = replace(t168, evaluation_input_authority=evaluation)
    enum = enumerate_structural_geometry(t168, filtered, (), max_valid_candidates=32)
    return EnvelopeEnumerationOutcome(
        space_hash=enum.space_hash,
        filtered_space=filtered,
        valid_structural=enum.valid_structural,
        rejections=enum.rejections,
        placement_envelope_diameter_m=str(envelope_m),
        envelope_scale=envelope_scale,
    )


def resolve_recovered_shell_052_bundle(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
) -> RecoveredShell052Bundle | None:
    """Return the same 0.52 m layout that passed Task168 in the recovery probe (first success)."""
    for discrete_path, cut_label in (
        (BREAKTHROUGH_DISCRETE_SPACE_PATH, "BREAKTHROUGH_CUT_035"),
        (
            _REPO / "docs/tasks/evidence/V08-03-breakthrough-discrete-space-cut049-r1.json",
            "BREAKTHROUGH_CUT_049",
        ),
    ):
        space = load_v08_discrete_space(discrete_path)
        cut = format_engineering_decimal(space.baffle_cut)
        for scale in (Decimal("0.90"), Decimal("0.85"), Decimal("0.80")):
            outcome = _with_envelope_override(
                normalized,
                handoff,
                discrete_path=discrete_path,
                shell_m=SHELL_052_PROBE_M,
                envelope_scale=scale,
            )
            for item in outcome.valid_structural:
                shell_d = str(item.shell_record.shell_inside_diameter_m)
                if Decimal(shell_d) != SHELL_052_PROBE_M:
                    continue
                return RecoveredShell052Bundle(
                    structural_bundle=item,
                    candidate_space_hash=outcome.space_hash,
                    discrete_space_authority_id=space.authority_id,
                    discrete_space_content_hash=space.content_hash,
                    placement_envelope_diameter_m=outcome.placement_envelope_diameter_m,
                    envelope_scale=str(scale),
                    baffle_cut_fraction=cut,
                    experimental_authority_label=f"{RECOVERY_AUTHORITY_LABEL}/{cut_label}",
                    recovery_note=(
                        f"envelope_scale={scale} tubes="
                        f"{int(item.bundle.task021_layout.physical_tube_count)}"
                    ),
                )
    return None


def run_larger_shell_layout_recovery(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
) -> LargerShellLayoutRecoveryReport:
    """Probe supported single-segmental cuts with constrained Task021 placement envelopes."""
    recovered_bundle = resolve_recovered_shell_052_bundle(normalized, handoff)
    attempts: list[LayoutRecoveryAttempt] = []
    notes: list[str] = []
    recovered = recovered_bundle is not None
    if recovered and recovered_bundle is not None:
        notes.append(recovered_bundle.recovery_note)
    if not recovered:
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
                outcome = _with_envelope_override(
                    normalized,
                    handoff,
                    discrete_path=discrete_path,
                    shell_m=SHELL_052_PROBE_M,
                    envelope_scale=scale,
                )
                blocker = None
                stage = None
                if outcome.rejections:
                    evidence = outcome.rejections[0].evidence
                    blocker = evidence.get("blocker_code")
                    stage = outcome.rejections[0].failure_stage
                attempts.append(
                    LayoutRecoveryAttempt(
                        shell_inside_diameter_m=format_engineering_decimal(SHELL_052_PROBE_M),
                        baffle_cut_fraction=str(cut),
                        placement_envelope_diameter_m=outcome.placement_envelope_diameter_m,
                        task168_structurally_valid=bool(outcome.valid_structural),
                        physical_tube_count=(
                            int(outcome.valid_structural[0].bundle.task021_layout.physical_tube_count)
                            if outcome.valid_structural
                            else None
                        ),
                        first_blocker_code=blocker,
                        failure_stage=stage,
                    )
                )
        bfg_hits = sum(1 for a in attempts if a.first_blocker_code == _BFG_CODE)
        if bfg_hits:
            notes.append(f"{_BFG_CODE}_persisted_across_envelope_probes")
    task168_result = "STRUCTURAL_PASS" if recovered else "NO_VALID_0P52M_LAYOUT"
    return LargerShellLayoutRecoveryReport(
        attempts=tuple(attempts),
        larger_shell_layout_recovered=recovered,
        task168_result=task168_result,
        notes=tuple(notes),
    )


__all__ = [
    "EnvelopeEnumerationOutcome",
    "LargerShellLayoutRecoveryReport",
    "RecoveredShell052Bundle",
    "resolve_recovered_shell_052_bundle",
    "run_larger_shell_layout_recovery",
]