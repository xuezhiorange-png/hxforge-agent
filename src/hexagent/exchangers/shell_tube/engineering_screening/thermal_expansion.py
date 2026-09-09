"""Qualitative construction screening plus source-transparent expansion diagnostic."""

from __future__ import annotations

from decimal import DecimalException, localcontext

from hexagent.exchangers.shell_tube.models import ConstructionFamily

from .authority import SOURCE_NIST_THERMAL_EXPANSION
from .errors import BlockerCode, WarningCode
from .models import ScreenRecord, ScreenStatus, Task167Request


def build_thermal_expansion_screen(
    request: Task167Request,
) -> tuple[ScreenRecord, tuple[tuple[BlockerCode, str], ...]]:
    snapshot = request.screening_property_snapshot
    family = request.task020_configuration.construction_family
    names = (
        snapshot.coefficient_thermal_expansion_per_k,
        snapshot.effective_length_m,
        snapshot.reference_temperature_k,
        snapshot.effective_shell_temperature_k,
        snapshot.effective_tube_temperature_k,
    )
    diagnostics: list[tuple[str, str]] = [("construction_family", family.value)]
    blockers: list[tuple[BlockerCode, str]] = []
    if all(value is not None for value in names):
        alpha, length, reference, shell_temperature, tube_temperature = names
        assert alpha is not None and length is not None and reference is not None
        assert shell_temperature is not None and tube_temperature is not None
        try:
            with localcontext() as context:
                context.prec = 50
                shell_expansion = alpha * length * (shell_temperature - reference)
                tube_expansion = alpha * length * (tube_temperature - reference)
                differential = shell_expansion - tube_expansion
        except DecimalException:
            blockers.append((BlockerCode.NONFINITE_ENGINEERING_RESULT, "thermal_expansion"))
        else:
            diagnostics.extend(
                (
                    ("shell_free_thermal_expansion_m", str(shell_expansion)),
                    ("tube_free_thermal_expansion_m", str(tube_expansion)),
                    ("differential_free_expansion_m", str(differential)),
                )
            )
    else:
        diagnostics.append(("diagnostic_values", "INCOMPLETE"))

    if blockers:
        status = ScreenStatus.BLOCKED
        reason = blockers[0][0].value
    elif family is ConstructionFamily.FIXED_TUBESHEET:
        status = ScreenStatus.WARN
        reason = WarningCode.FIXED_TUBESHEET_DIFFERENTIAL_EXPANSION_CAUTION.value
    else:
        status = ScreenStatus.PASS
        reason = "STRUCTURAL_EXPANSION_ACCOMMODATED_BY_CONSTRUCTION_FAMILY"
    if not all(value is not None for value in names):
        status = ScreenStatus.WARN
        reason = WarningCode.THERMAL_EXPANSION_DIAGNOSTIC_ONLY.value
    return (
        ScreenRecord(
            screen_id="THERMAL_EXPANSION",
            status=status,
            authority_mode=request.screening_requirements.authority_mode,
            source_id=SOURCE_NIST_THERMAL_EXPANSION,
            rule_id=None,
            diagnostic_values=tuple(diagnostics),
            limit_values=(),
            reason_code=reason,
            standard_claim=False,
            applicability=("PRELIMINARY_ENGINEERING_SCREENING",),
            evidence_refs=(
                SOURCE_NIST_THERMAL_EXPANSION,
                request.screening_property_snapshot.evidence_ref,
            ),
        ),
        tuple(blockers),
    )


__all__ = ["build_thermal_expansion_screen"]
