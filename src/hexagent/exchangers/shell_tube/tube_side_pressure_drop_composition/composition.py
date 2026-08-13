"""TASK-029 pressure contribution extraction and T07 validation primitives.

I12/T07 scope: producer-field extraction, loss-coefficient convention, and exact
Decimal contribution guards. Ordered summation is deferred to a later gate.
"""

from __future__ import annotations

from decimal import Decimal, localcontext

from hexagent.exchangers.shell_tube.tube_side_local_loss.enums import (
    LossCoefficientConvention,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.models import (
    TubeSideLocalLossComponentResult,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.blocker_registry import (
    collapse_blockers,
    emit_blocker,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.decimal_identity import (
    TASK029_PRESSURE_QUANTUM_PA,
    task029_decimal_context,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
    ProducerTask,
    Task029BlockerCode,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029BlockerEntry,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.path_binding import (
    BoundPressurePathMember,
)

_TASK027_PRESSURE_FIELD_PATH = "task027_success_result.straight_tube_friction_pressure_drop_pa"
_TASK028_PRESSURE_FIELD_PATH = "task028_success_result.component_results"
_REQUIRED_TASK028_LOSS_COEFFICIENT_CONVENTION = (
    LossCoefficientConvention.K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2
)


def extract_pressure_contribution(bound_member: BoundPressurePathMember) -> Decimal:
    """Return frozen producer pressure contribution for a T06-bound member."""
    if bound_member.producer_task == ProducerTask.TASK_027:
        evidence = bound_member.task027_replay_evidence
        if evidence is None:
            msg = "TASK-027 bound member requires replay evidence"
            raise ValueError(msg)
        return evidence.straight_tube_friction_pressure_drop_pa

    if bound_member.producer_task == ProducerTask.TASK_028:
        component = bound_member.task028_component_result
        if component is None:
            msg = "TASK-028 bound member requires component result"
            raise ValueError(msg)
        return component.component_irreversible_pressure_loss_pa

    msg = f"unsupported producer task: {bound_member.producer_task!r}"
    raise ValueError(msg)


def validate_task028_loss_coefficient_convention(
    component: TubeSideLocalLossComponentResult,
    *,
    field_path: str = _TASK028_PRESSURE_FIELD_PATH,
) -> tuple[Task029BlockerEntry, ...]:
    """Validate TASK-028 loss coefficient convention against frozen production enum."""
    if component.loss_coefficient_convention != _REQUIRED_TASK028_LOSS_COEFFICIENT_CONVENTION:
        return (
            emit_blocker(
                Task029BlockerCode.BL_T029_PRODUCER_CONVENTION_MISMATCH,
                field_path,
            ),
        )
    return ()


def validate_contribution(
    value: object,
    *,
    field_path: str,
) -> tuple[Task029BlockerEntry, ...]:
    """Validate exact Decimal pressure contribution finite/positive/quantum semantics."""
    blockers: list[Task029BlockerEntry] = []

    if type(value) is not Decimal:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_PRESSURE_CONTRIBUTION_NONFINITE,
                field_path,
            )
        )
        return tuple(blockers)

    if not value.is_finite():
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_PRESSURE_CONTRIBUTION_NONFINITE,
                field_path,
            )
        )
        return tuple(blockers)

    if value <= Decimal("0"):
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_PRESSURE_CONTRIBUTION_NONPOSITIVE,
                field_path,
            )
        )

    with localcontext(task029_decimal_context()):
        if value.quantize(TASK029_PRESSURE_QUANTUM_PA) != value:
            blockers.append(
                emit_blocker(
                    Task029BlockerCode.BL_T029_PRESSURE_QUANTUM_MISMATCH,
                    field_path,
                )
            )

    return collapse_blockers(blockers)


def validate_bound_member_producer_convention(
    bound_member: BoundPressurePathMember,
    *,
    field_path: str = _TASK028_PRESSURE_FIELD_PATH,
) -> tuple[Task029BlockerEntry, ...]:
    """Validate TASK-028 producer convention for a bound member when applicable."""
    if bound_member.producer_task != ProducerTask.TASK_028:
        return ()
    component = bound_member.task028_component_result
    if component is None:
        return ()
    return validate_task028_loss_coefficient_convention(component, field_path=field_path)


__all__ = [
    "extract_pressure_contribution",
    "validate_bound_member_producer_convention",
    "validate_contribution",
    "validate_task028_loss_coefficient_convention",
]
