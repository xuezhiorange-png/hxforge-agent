"""Construction-family suitability screen."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.models import ConstructionFamily

from .authority import SOURCE_BELL_GOSSETT_UTUBE, SOURCE_ELSEVIER_SHELL_TUBE_OVERVIEW
from .errors import BlockerCode
from .models import ScreenRecord, ScreenStatus, Task167Request


def build_construction_screen(
    request: Task167Request,
) -> tuple[ScreenRecord, tuple[tuple[BlockerCode, str], ...]]:
    requirements = request.screening_requirements
    family = request.task020_configuration.construction_family
    blockers: list[tuple[BlockerCode, str]] = []
    diagnostics = [("construction_family", family.value)]
    status = ScreenStatus.PASS
    reason = "CONSTRUCTION_FAMILY_SUITABLE_FOR_DECLARED_REQUIREMENTS"
    if (
        requirements.removable_bundle_required is True
        and family is ConstructionFamily.FIXED_TUBESHEET
    ):
        status = ScreenStatus.BLOCKED
        reason = BlockerCode.CLEANABILITY_REQUIREMENT_UNSATISFIED.value
        blockers.append(
            (BlockerCode.CLEANABILITY_REQUIREMENT_UNSATISFIED, "removable_bundle_required")
        )
    elif family is ConstructionFamily.FIXED_TUBESHEET:
        diagnostics.append(("differential_expansion", "CONSTRAINED"))
    elif family is ConstructionFamily.U_TUBE:
        diagnostics.extend((("bundle_removable", "TRUE"), ("tube_bend_access", "LIMITED")))
    else:
        diagnostics.append(("differential_axial_movement", "ACCOMMODATED"))
    return (
        ScreenRecord(
            screen_id="CONSTRUCTION_FAMILY_SUITABILITY",
            status=status,
            authority_mode=requirements.authority_mode,
            source_id=";".join((SOURCE_BELL_GOSSETT_UTUBE, SOURCE_ELSEVIER_SHELL_TUBE_OVERVIEW)),
            rule_id=None,
            diagnostic_values=tuple(diagnostics),
            limit_values=(),
            reason_code=reason,
            standard_claim=False,
            applicability=("PRELIMINARY_ENGINEERING_SCREENING",),
            evidence_refs=(SOURCE_BELL_GOSSETT_UTUBE, SOURCE_ELSEVIER_SHELL_TUBE_OVERVIEW),
        ),
        tuple(blockers),
    )


__all__ = ["build_construction_screen"]
