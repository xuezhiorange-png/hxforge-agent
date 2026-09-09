"""Source-transparent velocity diagnostics."""

from __future__ import annotations

from decimal import Decimal, DecimalException, localcontext

from .authority import SOURCE_TASK020_RULE_PACK
from .errors import BlockerCode, WarningCode
from .models import (
    NozzleGeometryAuthority,
    ScreeningPropertySnapshot,
    ScreenRecord,
    ScreenStatus,
    Task167Request,
)


def _pairs(values: tuple[tuple[str, object], ...]) -> tuple[tuple[str, str], ...]:
    return tuple((key, str(value)) for key, value in values if value is not None)


def _diagnostic(
    screen_id: str,
    status: ScreenStatus,
    request: Task167Request,
    source_id: str,
    values: tuple[tuple[str, object], ...],
    reason: str,
    evidence_refs: tuple[str, ...],
    *,
    limit_values: tuple[tuple[str, str], ...] = (),
) -> ScreenRecord:
    return ScreenRecord(
        screen_id=screen_id,
        status=status,
        authority_mode=request.screening_requirements.authority_mode,
        source_id=source_id,
        rule_id=None,
        diagnostic_values=_pairs(values),
        limit_values=limit_values,
        reason_code=reason,
        standard_claim=False,
        applicability=("PRELIMINARY_ENGINEERING_SCREENING",),
        evidence_refs=tuple(sorted(evidence_refs, key=lambda value: value.encode("utf-8"))),
    )


def build_velocity_screens(
    request: Task167Request,
) -> tuple[tuple[ScreenRecord, ...], list[tuple[BlockerCode, str]]]:
    snapshot = request.screening_property_snapshot
    requirements = request.screening_requirements
    evidence = (snapshot.evidence_ref,)
    screens: list[ScreenRecord] = []
    blockers: list[tuple[BlockerCode, str]] = []

    tube_velocity = request.tube_side_result.bulk_velocity_m_s
    screens.append(
        _diagnostic(
            "TUBE_VELOCITY",
            ScreenStatus.WARN,
            request,
            "TASK026_ACCEPTED_TUBE_SIDE_THERMAL_RESULT",
            (("tube_velocity_m_s", tube_velocity),),
            WarningCode.SCREENING_LIMIT_UNBOUND.value,
            (request.tube_side_result.result_id,),
        )
    )

    shell_values: list[tuple[str, object]] = []
    if snapshot.shell_bulk_velocity_m_s is not None:
        shell_values.append(("shell_bulk_velocity_m_s", snapshot.shell_bulk_velocity_m_s))
    if snapshot.shell_crossflow_velocity_m_s is not None:
        shell_values.append(("shell_crossflow_velocity_m_s", snapshot.shell_crossflow_velocity_m_s))
    if not shell_values:
        blockers.append(
            (
                BlockerCode.SHELL_VELOCITY_NOT_COMPUTABLE,
                "screening_property_snapshot.shell_bulk_velocity_m_s",
            )
        )
        screens.append(
            _diagnostic(
                "SHELL_VELOCITY",
                ScreenStatus.BLOCKED,
                request,
                snapshot.source_id,
                (),
                BlockerCode.SHELL_VELOCITY_NOT_COMPUTABLE.value,
                evidence,
            )
        )
    else:
        screens.append(
            _diagnostic(
                "SHELL_VELOCITY",
                ScreenStatus.WARN,
                request,
                snapshot.source_id,
                tuple(shell_values),
                WarningCode.SCREENING_LIMIT_UNBOUND.value,
                evidence + (request.task166_result.result_id,),
            )
        )

    if request.nozzle_geometry is None:
        reason = (
            BlockerCode.NOZZLE_GEOMETRY_NOT_AVAILABLE.value
            if requirements.nozzle_velocity_screen_required
            else WarningCode.NOZZLE_VELOCITY_NOT_EVALUATED.value
        )
        status = (
            ScreenStatus.BLOCKED
            if requirements.nozzle_velocity_screen_required
            else ScreenStatus.WARN
        )
        if requirements.nozzle_velocity_screen_required:
            blockers.append((BlockerCode.NOZZLE_GEOMETRY_NOT_AVAILABLE, "nozzle_geometry"))
        screens.append(
            _diagnostic(
                "NOZZLE_VELOCITY",
                status,
                request,
                SOURCE_TASK020_RULE_PACK,
                (),
                reason,
                (),
            )
        )
    else:
        nozzle, failure = _nozzle_velocity(request.nozzle_geometry, snapshot)
        if failure is not None:
            blockers.append(failure)
            screens.append(
                _diagnostic(
                    "NOZZLE_VELOCITY",
                    ScreenStatus.BLOCKED,
                    request,
                    request.nozzle_geometry.source_id,
                    (),
                    failure[0].value,
                    (request.nozzle_geometry.evidence_ref,),
                )
            )
        else:
            screens.append(
                _diagnostic(
                    "NOZZLE_VELOCITY",
                    ScreenStatus.WARN,
                    request,
                    request.nozzle_geometry.source_id,
                    (("nozzle_velocity_m_s", nozzle),),
                    WarningCode.SCREENING_LIMIT_UNBOUND.value,
                    (request.nozzle_geometry.evidence_ref,),
                )
            )
    return tuple(screens), blockers


def _nozzle_velocity(
    geometry: NozzleGeometryAuthority,
    snapshot: ScreeningPropertySnapshot,
) -> tuple[Decimal | None, tuple[BlockerCode, str] | None]:
    mass = snapshot.nozzle_mass_flow_rate_kg_s
    density = snapshot.nozzle_density_kg_m3
    if mass is None or density is None:
        return None, (BlockerCode.NOZZLE_AUTHORITY_INVALID, "nozzle mass flow/density")
    if mass <= Decimal("0") or density <= Decimal("0") or geometry.flow_area_m2 <= Decimal("0"):
        return None, (BlockerCode.NOZZLE_AUTHORITY_INVALID, "nozzle positive domain")
    try:
        with localcontext() as context:
            context.prec = 50
            value = mass / (density * geometry.flow_area_m2)
    except DecimalException:
        return None, (BlockerCode.NONFINITE_ENGINEERING_RESULT, "nozzle_velocity")
    if not value.is_finite() or value < Decimal("0"):
        return None, (BlockerCode.NONFINITE_ENGINEERING_RESULT, "nozzle_velocity")
    return value, None


__all__ = ["build_velocity_screens"]
