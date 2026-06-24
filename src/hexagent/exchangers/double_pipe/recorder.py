"""Unified evaluation recorder for double-pipe rating provenance.

Replaces manual seq_idx, _eval_counter, call_idx tracking with a
structured recorder that guarantees:
- Global consecutive sequence_index
- Unique consecutive evaluation_index per evaluation
- Call index within evaluation starts at 0
- One mutable object shared across all evaluation phases
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from hexagent.core.heat_balance import PropertyCallRecord
from hexagent.properties.base import PropertyProvider


class EvaluationRole(StrEnum):
    """Fixed roles for evaluation identity."""

    INLET = "inlet"
    Q_MAX_COUNTERFLOW = "q_max_counterflow"
    Q_MAX_PARALLEL_LIMITS = "q_max_parallel_limits"
    Q_MAX_PARALLEL_PINCH = "q_max_parallel_pinch"
    BRACKET_PROBE = "bracket_probe"
    SOLVER_ITERATION = "solver_iteration"
    FINAL_EVALUATION = "final_evaluation"


@dataclass
class EvaluationContext:
    """Tracks call indices within a single evaluation."""

    evaluation_index: int
    evaluation_role: EvaluationRole
    trial_q_w: float | None
    _next_call_index: int = field(default=0, init=False, repr=False)

    def next_call_index(self) -> int:
        idx = self._next_call_index
        self._next_call_index += 1
        return idx


@dataclass
class EvaluationRecorder:
    """Centralized recorder that allocates evaluation and sequence indices."""

    _next_evaluation_index: int = field(default=0, init=False, repr=False)
    _next_sequence_index: int = field(default=0, init=False, repr=False)

    def begin(self, role: EvaluationRole, trial_q_w: float | None = None) -> EvaluationContext:
        ctx = EvaluationContext(
            evaluation_index=self._next_evaluation_index,
            evaluation_role=role,
            trial_q_w=trial_q_w,
        )
        self._next_evaluation_index += 1
        return ctx

    def alloc_sequence(self) -> int:
        idx = self._next_sequence_index
        self._next_sequence_index += 1
        return idx

    def record_success(
        self,
        ctx: EvaluationContext,
        state: Any,
        *,
        query_type: str,
        inputs: tuple[tuple[str, float], ...],
        provider: PropertyProvider,
        stage: str,
        stream_role: str,
    ) -> PropertyCallRecord:
        """Record a successful property call."""
        from hexagent.exchangers.double_pipe.rating import _build_provider_call_record

        seq = self.alloc_sequence()
        call_idx = ctx.next_call_index()
        return _build_provider_call_record(
            state,
            query_type=query_type,
            inputs=inputs,
            provider=provider,
            stage=stage,
            stream_role=stream_role,
            sequence_index=seq,
            evaluation_index=ctx.evaluation_index,
            evaluation_role=ctx.evaluation_role.value,
            call_index_within_evaluation=call_idx,
            trial_q_w=ctx.trial_q_w,
        )

    def record_failure(
        self,
        ctx: EvaluationContext,
        *,
        fluid_name: str,
        query_type: str,
        inputs: tuple[tuple[str, float], ...],
        provider: PropertyProvider,
        stage: str,
        stream_role: str,
        error_code: str,
        error_message: str,
    ) -> PropertyCallRecord:
        """Record a failed property call."""
        from hexagent.exchangers.double_pipe.rating import _build_failed_provider_call_record

        seq = self.alloc_sequence()
        call_idx = ctx.next_call_index()
        return _build_failed_provider_call_record(
            fluid_name=fluid_name,
            query_type=query_type,
            inputs=inputs,
            provider=provider,
            stage=stage,
            stream_role=stream_role,
            sequence_index=seq,
            error_code=error_code,
            error_message=error_message,
            evaluation_index=ctx.evaluation_index,
            evaluation_role=ctx.evaluation_role.value,
            call_index_within_evaluation=call_idx,
            trial_q_w=ctx.trial_q_w,
        )
