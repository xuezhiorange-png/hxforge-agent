"""Unified evaluation recorder for double-pipe rating provenance.

Replaces manual seq_idx, _eval_counter, call_idx tracking with a
structured recorder that guarantees:
- Global consecutive sequence_index
- Unique consecutive evaluation_index per evaluation
- Call index within evaluation starts at 0
- Single ownership: every record is owned by exactly one recorder
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


class SolverEvaluationPhase(StrEnum):
    """Phase tag for solver residual function calls.

    Passed explicitly to the residual function so the solver does not
    depend on shared mutable state.
    """

    BRACKET_PROBE = "bracket_probe"
    SOLVER_ITERATION = "solver_iteration"


@dataclass
class EvaluationContext:
    """Tracks call indices within a single evaluation."""

    evaluation_index: int
    evaluation_role: str
    trial_q_w: float | None
    _next_call_index: int = field(default=0, init=False, repr=False)

    def next_call_index(self) -> int:
        idx = self._next_call_index
        self._next_call_index += 1
        return idx


@dataclass
class EvaluationRecorder:
    """Centralized recorder that allocates evaluation and sequence indices.

    Single owner of all PropertyCallRecord instances. Every call to
    record_success() or record_failure() appends to the internal _records
    list atomically. Callers must NOT maintain separate property_calls
    lists and must NOT extend/append records externally.
    """

    _records: list[PropertyCallRecord] = field(default_factory=list, repr=False)
    _next_evaluation_index: int = field(default=0, init=False, repr=False)
    _next_sequence_index: int = field(default=0, init=False, repr=False)

    @property
    def records(self) -> tuple[PropertyCallRecord, ...]:
        """Read-only view of all recorded property calls."""
        return tuple(self._records)

    @property
    def record_count(self) -> int:
        """Number of records currently held."""
        return len(self._records)

    def begin(self, role: str, trial_q_w: float | None = None) -> EvaluationContext:
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
        """Record a successful property call and append to internal records."""
        from hexagent.exchangers.double_pipe.rating import _build_provider_call_record

        seq = self.alloc_sequence()
        call_idx = ctx.next_call_index()
        rec = _build_provider_call_record(
            state,
            query_type=query_type,
            inputs=inputs,
            provider=provider,
            stage=stage,
            stream_role=stream_role,
            sequence_index=seq,
            evaluation_index=ctx.evaluation_index,
            evaluation_role=ctx.evaluation_role,
            call_index_within_evaluation=call_idx,
            trial_q_w=ctx.trial_q_w,
        )
        self._records.append(rec)
        return rec

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
        """Record a failed property call and append to internal records."""
        from hexagent.exchangers.double_pipe.rating import _build_failed_provider_call_record

        seq = self.alloc_sequence()
        call_idx = ctx.next_call_index()
        rec = _build_failed_provider_call_record(
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
            evaluation_role=ctx.evaluation_role,
            call_index_within_evaluation=call_idx,
            trial_q_w=ctx.trial_q_w,
        )
        self._records.append(rec)
        return rec
