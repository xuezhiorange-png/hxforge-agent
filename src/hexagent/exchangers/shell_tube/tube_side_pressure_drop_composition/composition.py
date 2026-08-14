"""TASK-029 pressure contribution extraction, T07 validation, and T11 composition.

I12/T07 scope: producer-field extraction, loss-coefficient convention, exact
Decimal contribution guards, and ordered pressure summation.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, localcontext

from hexagent.exchangers.shell_tube.tube_side_local_loss.enums import (
    LossCoefficientConvention,
    Task028ComponentFlowDirectionAssertion,
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
    normalize_negative_zero,
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
_TASK028_COMPONENT_DIRECTION_FIELD_PATH = (
    "task028_success_result.component_results[].flow_direction_assertion"
)
_TASK028_PRESSURE_CONTRIBUTION_FIELD_PATH = (
    "task028_success_result.component_results[].component_irreversible_pressure_loss_pa"
)
_REQUIRED_TASK028_LOSS_COEFFICIENT_CONVENTION = (
    LossCoefficientConvention.K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2
)


class CompositionArithmeticFailure(Exception):
    """Internal T11 ordered-sum arithmetic failure after T07 contribution validation."""


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


def validate_task028_component_direction(
    component: TubeSideLocalLossComponentResult,
    *,
    field_path: str = _TASK028_COMPONENT_DIRECTION_FIELD_PATH,
) -> tuple[Task029BlockerEntry, ...]:
    """Validate TASK-028 component flow direction against frozen production enum."""
    if component.flow_direction_assertion != Task028ComponentFlowDirectionAssertion.START_TO_END:
        return (
            emit_blocker(
                Task029BlockerCode.BL_T029_FLOW_DIRECTION_MISMATCH,
                field_path,
                evidence_refs=(component.component_id,),
            ),
        )
    return ()


def validate_bound_member_task028_component_direction(
    bound_member: BoundPressurePathMember,
    *,
    field_path: str = _TASK028_COMPONENT_DIRECTION_FIELD_PATH,
) -> tuple[Task029BlockerEntry, ...]:
    """Validate TASK-028 component direction for a bound member when applicable."""
    if bound_member.producer_task != ProducerTask.TASK_028:
        return ()
    component = bound_member.task028_component_result
    if component is None:
        return ()
    return validate_task028_component_direction(component, field_path=field_path)


def pressure_contribution_field_path(bound_member: BoundPressurePathMember) -> str:
    """Return frozen producer pressure field path for a T06-bound member."""
    if bound_member.producer_task == ProducerTask.TASK_027:
        return _TASK027_PRESSURE_FIELD_PATH
    return _TASK028_PRESSURE_CONTRIBUTION_FIELD_PATH


def sum_ordered_contributions(contributions: tuple[Decimal, ...]) -> Decimal:
    """Sum globally ordered validated pressure contributions with one final quantization."""
    try:
        with localcontext(task029_decimal_context()):
            total = Decimal("0")
            for contribution in contributions:
                total += contribution
            return normalize_negative_zero(total.quantize(TASK029_PRESSURE_QUANTUM_PA))
    except (InvalidOperation, OverflowError, ValueError) as exc:
        msg = "ordered pressure contribution sum failed"
        raise CompositionArithmeticFailure(msg) from exc


__all__ = [
    "CompositionArithmeticFailure",
    "extract_pressure_contribution",
    "pressure_contribution_field_path",
    "sum_ordered_contributions",
    "validate_bound_member_producer_convention",
    "validate_bound_member_task028_component_direction",
    "validate_contribution",
    "validate_task028_component_direction",
    "validate_task028_loss_coefficient_convention",
]
