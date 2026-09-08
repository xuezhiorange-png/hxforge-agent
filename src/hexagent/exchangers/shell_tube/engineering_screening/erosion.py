"""Erosion-risk screen with no unbound numeric allowable."""

from __future__ import annotations

from .errors import WarningCode
from .models import ScreenRecord, ScreenStatus, Task167Request


def build_erosion_screen(request: Task167Request) -> ScreenRecord:
    snapshot = request.screening_property_snapshot
    values = tuple(
        (name, str(value))
        for name, value in (
            ("tube_velocity_m_s", request.tube_side_result.bulk_velocity_m_s),
            ("shell_bulk_velocity_m_s", snapshot.shell_bulk_velocity_m_s),
            ("shell_crossflow_velocity_m_s", snapshot.shell_crossflow_velocity_m_s),
        )
        if value is not None
    )
    return ScreenRecord(
        screen_id="EROSION_RISK",
        status=ScreenStatus.WARN,
        authority_mode=request.screening_requirements.authority_mode,
        source_id="",
        rule_id=None,
        diagnostic_values=values,
        limit_values=(),
        reason_code=WarningCode.EROSION_LIMIT_NOT_BOUND.value,
        standard_claim=False,
        applicability=("PRELIMINARY_ENGINEERING_SCREENING",),
        evidence_refs=(request.tube_side_result.result_id, snapshot.evidence_ref),
    )


__all__ = ["build_erosion_screen"]
