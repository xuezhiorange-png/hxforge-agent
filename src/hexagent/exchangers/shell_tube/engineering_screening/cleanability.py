"""Construction-family and fouling/cleanability screening."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.models import ConstructionFamily

from .authority import SOURCE_BELL_GOSSETT_UTUBE, SOURCE_CHEMICAL_ENGINEER_CONSTRUCTION
from .errors import BlockerCode, WarningCode
from .models import FoulingTendency, ScreenRecord, ScreenStatus, Task167Request


def build_cleanability_screen(
    request: Task167Request,
) -> tuple[ScreenRecord, tuple[tuple[BlockerCode, str], ...]]:
    config = request.task020_configuration
    requirements = request.screening_requirements
    family = config.construction_family
    evidence = (SOURCE_BELL_GOSSETT_UTUBE, SOURCE_CHEMICAL_ENGINEER_CONSTRUCTION)
    diagnostics: list[tuple[str, str]] = [("construction_family", family.value)]
    blockers: list[tuple[BlockerCode, str]] = []
    status = ScreenStatus.PASS
    reason = "CLEANABILITY_REQUIREMENTS_SATISFIED"

    shell_clean = requirements.shell_side_mechanical_cleaning_required
    tube_clean = requirements.tube_side_mechanical_cleaning_required
    if family is ConstructionFamily.FIXED_TUBESHEET:
        if shell_clean is True:
            status = ScreenStatus.BLOCKED
            reason = BlockerCode.CLEANABILITY_REQUIREMENT_UNSATISFIED.value
            blockers.append(
                (
                    BlockerCode.CLEANABILITY_REQUIREMENT_UNSATISFIED,
                    "shell_side_mechanical_cleaning_required",
                )
            )
        elif (
            requirements.shell_side_fouling_tendency is not FoulingTendency.UNSPECIFIED
            or tube_clean is True
        ):
            status = ScreenStatus.WARN
            reason = WarningCode.MECHANICAL_CLEANABILITY_CAUTION.value
    elif family is ConstructionFamily.U_TUBE:
        if tube_clean is True:
            status = ScreenStatus.WARN
            reason = WarningCode.MECHANICAL_CLEANABILITY_CAUTION.value
            diagnostics.append(("tube_side_bend_limitation", "TRUE"))
        elif shell_clean is True:
            diagnostics.append(("removable_bundle", "FAVORABLE"))
    elif family is ConstructionFamily.FLOATING_HEAD:
        if requirements.removable_bundle_required is True:
            diagnostics.append(("removable_bundle", "FAVORABLE"))
        if tube_clean is True or shell_clean is True:
            diagnostics.append(("broad_cleaning_access", "SUBTYPE_DEPENDENT"))
    return (
        ScreenRecord(
            screen_id="FOULING_CLEANABILITY",
            status=status,
            authority_mode=requirements.authority_mode,
            source_id=";".join(evidence),
            rule_id=None,
            diagnostic_values=tuple(diagnostics),
            limit_values=(),
            reason_code=reason,
            standard_claim=False,
            applicability=("PRELIMINARY_ENGINEERING_SCREENING",),
            evidence_refs=evidence,
        ),
        tuple(blockers),
    )


__all__ = ["build_cleanability_screen"]
