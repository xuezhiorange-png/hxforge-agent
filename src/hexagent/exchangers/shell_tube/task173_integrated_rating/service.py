"""Deterministic TASK173 countercurrent rating and production-mesh admission."""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal, localcontext
from typing import Any, Literal, cast

from pydantic import ValidationError

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task172_local_runtime import (
    Task172BlockedResult,
    Task172LocalRequest,
    Task172LocalResult,
    build_local_support,
    recompute_task172_blocked_result_hash,
    recompute_task172_local_roundoff_bounds,
    recompute_task172_request_hash,
    recompute_task172_result_hash,
    recompute_task172_support_id,
)
from hexagent.exchangers.shell_tube.task172_local_runtime import (
    validate_request as task172_validate,
)
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CASE_REVISION_ID,
    DEFINITION_PROJECTION_HASH,
    PHYSICAL_OWNERSHIP_HASH,
    PROFILE_ID,
    SHELL_FLOW_PATH_ID,
    TASK171_RESULT_HASH,
    TOPOLOGY_ID,
    TUBE_FLOW_PATH_ID,
    LocalState,
    TopologyBinding,
    mesh_level_identity,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import (
    CELL_ROOT_SOLVER_AUTHORITY_ID,
    H_MAX_J_KG,
    H_MIN_J_KG,
    LOCAL_STATE_RECONSTRUCTION_AUTHORITY_ID,
    MAX_OUTER_BISECTION_ITERATIONS,
    OUTER_BOUNDARY_SOLVER_AUTHORITY_ID,
    PRODUCTION_MESH_PROFILE_AUTHORITY_ID,
    REFERENCE_PRESSURE_PA,
    REVIEWED_MESH_SEQUENCE,
    T_MAX_K,
    T_MIN_K,
    TERMINAL_TOLERANCE_K,
    ConvergenceComparison,
    FaceState,
    LocalStateReceipt,
    MeshObservables,
    PropertySnapshot,
    RatedCell,
    Task173BlockedResult,
    Task173Outcome,
    Task173Request,
    Task173SuccessResult,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.replay import (
    EXPECTED_TASK031_GEOMETRY_HASH,
    EXPECTED_TASK032_RESULT_HASH,
    EXPECTED_TASK166_RESULT_HASH,
    EXPECTED_TASK174_RESULT_HASH,
    SUPERSEDED_EFFECTIVE_IDENTITIES,
    NativeReplayError,
    public_projection,
    replay_shell_flow_authority,
)
from hexagent.properties.base import (
    FluidIdentifier,
    FluidState,
    PhaseRegion,
    PropertyProvider,
    ReferenceStatePolicy,
)
from hexagent.properties.coolprop_provider import CoolPropProvider

TUBE_INLET_T_K = Decimal("300")
SHELL_INLET_T_K = Decimal("298.15")
TUBE_MASS_FLOW_KG_S = Decimal("12")
SHELL_MASS_FLOW_KG_S = Decimal("20")
ENERGY_ACCEPTANCE_FLOOR_W = Decimal("1e-6")
MESH_DUTY_RELATIVE_THRESHOLD = Decimal("0.01")
MESH_DUTY_ABSOLUTE_THRESHOLD_W = Decimal("0.01")
MESH_WALL_EXTREMA_THRESHOLD_K = Decimal("0.01")
REQUIRED_CONSECUTIVE_PASSING_PAIRS = 2
REQUIRED_LATER_HEADROOM_LEVELS = 1
MAX_SUBDIVISIONS_PER_INTERVAL = 64
LATEST_ACCEPTABLE_CANDIDATE_SUBDIVISIONS = 32
MAX_HOLE_DYADIC_LEVELS_PER_BRACKET = 12
MAX_HOLE_RECOVERY_BRACKETS_PER_CELL = 15
MAX_HOLE_RECOVERY_PROBES_PER_CELL = (
    MAX_HOLE_RECOVERY_BRACKETS_PER_CELL * 2 * MAX_HOLE_DYADIC_LEVELS_PER_BRACKET
)
MAX_CELL_ROOT_BISECTION_ITERATIONS = 128
MAX_CELL_TASK172_EVALUATIONS = 512
CELL_ROOT_ENDPOINT_EVALUATIONS = 2
CELL_ROOT_FINAL_VERIFICATION_RESERVE = 1

LOCAL_STATE_RECONSTRUCTION_AUTHORITY = {
    "schema_version": "task173.local-state-reconstruction-authority.v1",
    "authority_id": LOCAL_STATE_RECONSTRUCTION_AUTHORITY_ID,
    "producer_class": "RECONSTRUCTED_LOCAL_STATE_PRODUCER",
    "operator": "ENTHALPY_MIDPOINT_AT_FIXED_REFERENCE_PRESSURE",
    "evaluation_pressure_pa": str(REFERENCE_PRESSURE_PA),
    "property_profile_id": PROFILE_ID,
    "property_source": "CoolProp HEOS::Water 8.0.0 DEF",
    "phase": "SINGLE_PHASE_LIQUID",
    "temperature_domain_k": [str(T_MIN_K), str(T_MAX_K)],
    "extrapolation_allowed": False,
    "clipping_allowed": False,
    "property_averaging_allowed": False,
    "backend_fallback_allowed": False,
    "task171_cell_mean_interpretation_claimed": False,
}
LOCAL_STATE_RECONSTRUCTION_AUTHORITY_HASH = canonical_sha256(LOCAL_STATE_RECONSTRUCTION_AUTHORITY)
OUTER_BOUNDARY_SOLVER_AUTHORITY = {
    "schema_version": "task173.outer-boundary-solver-authority.v1",
    "authority_id": OUTER_BOUNDARY_SOLVER_AUTHORITY_ID,
    "scope": CASE_REVISION_ID,
    "solver": "ONE_SIDED_FEASIBILITY_BOUNDARY_BISECTION",
    "shooting_variable": "SHELL_OUTLET_SPECIFIC_ENTHALPY_AT_X0",
    "lower_bound_j_kg": str(H_MIN_J_KG),
    "upper_bound_j_kg": str(H_MAX_J_KG),
    "target_enthalpy_j_kg": str(H_MIN_J_KG),
    "low_endpoint_class": "LOW_SIDE_DOMAIN_INFEASIBLE",
    "high_endpoint_class": "VALID_TRAJECTORY",
    "invalid_endpoint_is_physical_result": False,
    "terminal_temperature_tolerance_k": str(TERMINAL_TOLERANCE_K),
    "maximum_iterations": MAX_OUTER_BISECTION_ITERATIONS,
    "valid_negative_residual_endpoint_required": False,
    "scope_guard": "TARGET_STATE_EQUALS_HARD_PROPERTY_DOMAIN_BOUNDARY",
}
OUTER_BOUNDARY_SOLVER_AUTHORITY_HASH = canonical_sha256(OUTER_BOUNDARY_SOLVER_AUTHORITY)
CELL_ROOT_SOLVER_AUTHORITY = {
    "schema_version": "task173.valid-point-cell-root-authority.v2",
    "authority_id": CELL_ROOT_SOLVER_AUTHORITY_ID,
    "scope": CASE_REVISION_ID,
    "equation": "F(q)=q-q_TASK172(q)",
    "method": "VALID_POINT_ONLY_LOCAL_DYADIC_BRACKET_REFINEMENT",
    "valid_endpoint_signs": "F(q_low)<=0<=F(q_high)",
    "blocked_residual_acceptance_class": "TASK172_NUMERICAL_HOLE",
    "blocked_diagnostics_used_for_sign": False,
    "blocked_result_accepted_as_physical": False,
    "diagnostic_last_iterate_used": False,
    "hole_probe_order": "LOCAL_MIDPOINTS_FROM_VALID_ANCHORS_TOWARD_HOLE_IN_INCREASING_Q",
    "maximum_hole_dyadic_levels_per_bracket": MAX_HOLE_DYADIC_LEVELS_PER_BRACKET,
    "maximum_hole_probes_per_level": 2,
    "maximum_hole_recovery_brackets_per_cell": MAX_HOLE_RECOVERY_BRACKETS_PER_CELL,
    "maximum_hole_recovery_probes_per_cell": MAX_HOLE_RECOVERY_PROBES_PER_CELL,
    "maximum_cell_root_bisection_iterations": MAX_CELL_ROOT_BISECTION_ITERATIONS,
    "maximum_task172_evaluations_per_cell": MAX_CELL_TASK172_EVALUATIONS,
    "worst_case_authorized_task172_evaluations": (
        CELL_ROOT_ENDPOINT_EVALUATIONS
        + MAX_CELL_ROOT_BISECTION_ITERATIONS
        + MAX_HOLE_RECOVERY_PROBES_PER_CELL
        + CELL_ROOT_FINAL_VERIFICATION_RESERVE
    ),
    "cell_residual_acceptance_w": "1e-6",
    "task172_acceptance_policy_changed": False,
}
CELL_ROOT_SOLVER_AUTHORITY_HASH = canonical_sha256(CELL_ROOT_SOLVER_AUTHORITY)


def cell_root_worst_case_task172_evaluations() -> int:
    """Conservative evaluation budget including endpoints and final verification."""
    return (
        CELL_ROOT_ENDPOINT_EVALUATIONS
        + MAX_CELL_ROOT_BISECTION_ITERATIONS
        + MAX_HOLE_RECOVERY_PROBES_PER_CELL
        + CELL_ROOT_FINAL_VERIFICATION_RESERVE
    )


class _Stage3Failure(Exception):
    def __init__(self, code: str, *diagnostics: str) -> None:
        super().__init__(code)
        self.code = code
        self.diagnostics = tuple(diagnostics)


class _LowSideDomainInfeasible(Exception):
    """Search-only classification for an insufficient shell outlet enthalpy."""


class _Task172NumericalHole(Exception):
    """A preflight-valid trial rejected only by native residual acceptance."""


@dataclass
class _CellSearchStats:
    task172_local_evaluation_count: int = 0
    task172_numerical_hole_count: int = 0
    task172_numerical_hole_counts_by_code: dict[str, int] = field(default_factory=dict)
    task172_numerical_hole_trials: list[dict[str, str]] = field(default_factory=list)

    def record_evaluation(self) -> None:
        self.task172_local_evaluation_count += 1

    def record_hole(self, q_w: float, support_id: str) -> None:
        code = "BLOCKED_RESIDUAL_ACCEPTANCE"
        self.task172_numerical_hole_count += 1
        self.task172_numerical_hole_counts_by_code[code] = (
            self.task172_numerical_hole_counts_by_code.get(code, 0) + 1
        )
        self.task172_numerical_hole_trials.append(
            {"q_trial_w": repr(q_w), "failure_code": code, "physical_support_id": support_id}
        )


@dataclass(frozen=True)
class _ThermoState:
    native: FluidState
    snapshot: PropertySnapshot
    snapshot_hash: str


@dataclass(frozen=True)
class _CellEvaluation:
    q_w: Decimal
    tube_downstream: _ThermoState
    shell_next_physical: _ThermoState
    tube_local: _ThermoState
    shell_local: _ThermoState
    task172_request: Task172LocalRequest
    task172_result: Task172LocalResult


@dataclass(frozen=True)
class _CellTrial:
    q_w: float
    classification: Literal[
        "VALID_CELL_EVALUATION",
        "TASK172_NUMERICAL_HOLE",
        "LOW_SIDE_DOMAIN_INFEASIBLE",
        "HARD_BLOCKER",
    ]
    evaluation: _CellEvaluation | None = None
    residual: Decimal | None = None
    failure_code: str | None = None


def _eligible_trial(trial: _CellTrial) -> bool:
    return (
        trial.classification == "VALID_CELL_EVALUATION"
        and trial.evaluation is not None
        and trial.residual is not None
        and abs(trial.residual) <= Decimal("1e-6")
    )


def _valid_sign_pairs(trials: list[_CellTrial]) -> list[tuple[_CellTrial, _CellTrial]]:
    valid = sorted(
        (
            trial
            for trial in trials
            if trial.classification == "VALID_CELL_EVALUATION"
            and trial.evaluation is not None
            and trial.residual is not None
        ),
        key=lambda trial: trial.q_w,
    )
    pairs = [
        (left, right)
        for left, right in zip(valid, valid[1:], strict=False)
        if left.residual is not None
        and right.residual is not None
        and left.residual <= 0
        and right.residual >= 0
    ]
    return sorted(pairs, key=lambda pair: (pair[1].q_w - pair[0].q_w, pair[0].q_w))


def _dyadic_refine_valid_bracket(
    left: _CellTrial,
    right: _CellTrial,
    hole: _CellTrial,
    *,
    evaluate: Callable[[float], _CellTrial],
    all_trials: Callable[[], list[_CellTrial]],
    record_hole_neighbors: Callable[[list[_CellTrial]], None],
    on_level: Callable[[int], None] | None = None,
) -> tuple[_CellTrial, _CellTrial, _CellTrial | None]:
    """Refine locally around one hole with at most two probes per level."""
    if (
        left.classification != "VALID_CELL_EVALUATION"
        or right.classification != "VALID_CELL_EVALUATION"
        or hole.classification != "TASK172_NUMERICAL_HOLE"
        or not left.q_w < hole.q_w < right.q_w
        or left.residual is None
        or right.residual is None
        or left.residual > 0
        or right.residual < 0
    ):
        raise _Stage3Failure("BLOCKED_CELL_VALID_POINT_BRACKET_SIGN_INVALID")
    left_anchor, right_anchor = left, right
    left_hole_edge = right_hole_edge = hole.q_w
    for level in range(1, MAX_HOLE_DYADIC_LEVELS_PER_BRACKET + 1):
        if on_level is not None:
            on_level(level)
        evaluated_q = {trial.q_w for trial in all_trials()}
        probes = sorted(
            {
                (left_anchor.q_w + left_hole_edge) / 2.0,
                (right_hole_edge + right_anchor.q_w) / 2.0,
            }
        )
        level_trials: list[_CellTrial] = []
        for probe in probes:
            if probe in evaluated_q or not left.q_w < probe < right.q_w:
                continue
            trial = evaluate(probe)
            level_trials.append(trial)
            if trial.classification == "HARD_BLOCKER":
                raise _Stage3Failure(trial.failure_code or "BLOCKED_CELL_TASK172_HARD_BLOCKER")
            if trial.classification == "LOW_SIDE_DOMAIN_INFEASIBLE":
                raise _Stage3Failure(
                    "BLOCKED_CELL_CONSTITUTIVE_BRACKET_NOT_ESTABLISHED",
                    "local hole probe exited property domain",
                )
            if probe < hole.q_w:
                if trial.classification == "TASK172_NUMERICAL_HOLE":
                    left_hole_edge = probe
                elif trial.classification == "VALID_CELL_EVALUATION":
                    left_anchor = trial
            elif trial.classification == "TASK172_NUMERICAL_HOLE":
                right_hole_edge = probe
            elif trial.classification == "VALID_CELL_EVALUATION":
                right_anchor = trial
        samples = [trial for trial in all_trials() if left.q_w <= trial.q_w <= right.q_w]
        eligible = [trial for trial in level_trials if _eligible_trial(trial)]
        if eligible:
            record_hole_neighbors(all_trials())
            selected = min(
                eligible,
                key=lambda trial: (abs(trial.residual or Decimal(0)), trial.q_w),
            )
            return left, right, selected
        sign_pairs = _valid_sign_pairs(samples)
        if sign_pairs:
            next_left, next_right = sign_pairs[0]
            if next_right.q_w - next_left.q_w < right.q_w - left.q_w:
                record_hole_neighbors(all_trials())
                return next_left, next_right, None
    raise _Stage3Failure(
        "BLOCKED_CELL_VALID_EVALUATION_BRACKET_UNRESOLVED",
        f"maximum_hole_dyadic_levels={MAX_HOLE_DYADIC_LEVELS_PER_BRACKET}",
        "maximum_hole_probes_per_level=2",
        f"valid_bracket=[{left.q_w!r},{right.q_w!r}]",
    )


def _discover_valid_sign_bracket_from_endpoint_holes(
    lower_bound_q: float,
    upper_bound_q: float,
    endpoint_trials: tuple[_CellTrial, _CellTrial],
    *,
    evaluate: Callable[[float], _CellTrial],
    all_trials: Callable[[], list[_CellTrial]],
    record_hole_neighbors: Callable[[list[_CellTrial]], None],
    on_level: Callable[[int], None] | None = None,
) -> tuple[_CellTrial, _CellTrial, _CellTrial | None]:
    """Resolve one endpoint hole by bounded bisection toward its valid anchor."""
    if upper_bound_q <= lower_bound_q or any(
        trial.classification not in ("VALID_CELL_EVALUATION", "TASK172_NUMERICAL_HOLE")
        for trial in endpoint_trials
    ):
        raise _Stage3Failure("BLOCKED_CELL_VALID_POINT_BRACKET_SIGN_INVALID")
    lower_trial, upper_trial = endpoint_trials
    if (
        lower_trial.classification == "TASK172_NUMERICAL_HOLE"
        and upper_trial.classification == "TASK172_NUMERICAL_HOLE"
    ):
        raise _Stage3Failure(
            "BLOCKED_CELL_CONSTITUTIVE_BRACKET_NOT_ESTABLISHED",
            "both physical endpoints are numerical holes; no valid sign anchor exists",
        )
    lower_hole = lower_trial.classification == "TASK172_NUMERICAL_HOLE"
    hole_edge = lower_bound_q if lower_hole else upper_bound_q
    anchor = upper_trial if lower_hole else lower_trial
    if anchor.residual is None or anchor.evaluation is None:
        raise _Stage3Failure("BLOCKED_CELL_VALID_POINT_BRACKET_SIGN_INVALID")
    for level in range(1, MAX_HOLE_DYADIC_LEVELS_PER_BRACKET + 1):
        if on_level is not None:
            on_level(level)
        probe = (hole_edge + anchor.q_w) / 2.0
        if probe == hole_edge or probe == anchor.q_w:
            break
        trial = evaluate(probe)
        if trial.classification == "HARD_BLOCKER":
            raise _Stage3Failure(trial.failure_code or "BLOCKED_CELL_TASK172_HARD_BLOCKER")
        if trial.classification == "LOW_SIDE_DOMAIN_INFEASIBLE":
            raise _Stage3Failure(
                "BLOCKED_CELL_CONSTITUTIVE_BRACKET_NOT_ESTABLISHED",
                "endpoint-hole probe exited property domain",
            )
        if trial.classification == "TASK172_NUMERICAL_HOLE":
            hole_edge = probe
            continue
        if trial.classification != "VALID_CELL_EVALUATION" or trial.residual is None:
            raise _Stage3Failure("BLOCKED_CELL_VALID_POINT_BRACKET_SIGN_INVALID")
        if _eligible_trial(trial):
            record_hole_neighbors(all_trials())
            return trial, trial, trial
        samples = [
            candidate
            for candidate in all_trials()
            if lower_bound_q <= candidate.q_w <= upper_bound_q
        ]
        sign_pairs = _valid_sign_pairs(samples)
        if sign_pairs:
            record_hole_neighbors(all_trials())
            return sign_pairs[0][0], sign_pairs[0][1], None
        anchor = trial
    raise _Stage3Failure(
        "BLOCKED_CELL_VALID_EVALUATION_BRACKET_UNRESOLVED",
        f"maximum_hole_dyadic_levels={MAX_HOLE_DYADIC_LEVELS_PER_BRACKET}",
        f"physical_interval=[{lower_bound_q!r},{upper_bound_q!r}]",
    )


@dataclass(frozen=True)
class _CellRecord:
    support: Any
    solution: _CellEvaluation
    tube_upstream_face: FaceState
    tube_downstream_face: FaceState
    shell_physical_left_face: FaceState
    shell_physical_right_face: FaceState
    tube_receipt: LocalStateReceipt
    shell_receipt: LocalStateReceipt
    rated_cell: RatedCell
    tube_approach_k: Decimal
    shell_approach_k: Decimal


@dataclass(frozen=True)
class _MeshRun:
    subdivisions: int
    faces_tube: tuple[FaceState, ...]
    faces_shell: tuple[FaceState, ...]
    cells: tuple[_CellRecord, ...]
    observables: MeshObservables
    mesh_result_hash: str
    shooting_enthalpy: Decimal
    bisection_iterations: int
    task172_numerical_hole_neighborhoods: tuple[dict[str, str], ...] = ()


@dataclass(frozen=True)
class _OuterTrial:
    classification: str
    enthalpy_j_kg: Decimal
    mesh_run: _MeshRun | None = None
    diagnostics: tuple[str, ...] = ()


def _d(value: float | Decimal) -> Decimal:
    if type(value) is Decimal:
        result = value
    elif type(value) is float and math.isfinite(value):
        result = Decimal(str(value))
    else:
        raise TypeError("TASK173 canonical numeric values must be finite float or Decimal")
    if not result.is_finite():
        raise ValueError("non-finite TASK173 value")
    return result


def recompute_task173_request_hash(request: Task173Request) -> str:
    """Replay the immutable full-input identity of one TASK173 execution."""
    if type(request) is not Task173Request:
        raise TypeError("request hash replay requires exact Task173Request")
    return canonical_sha256(request.model_dump(mode="json"))


def recompute_task173_result_hash(result: Task173SuccessResult) -> str:
    """Replay the complete authoritative TASK173 result identity."""
    if type(result) is not Task173SuccessResult:
        raise TypeError("result hash replay requires exact Task173SuccessResult")
    projected = result.model_dump(mode="json")
    projected.pop("result_hash")
    projected.pop("result_id")
    return canonical_sha256(projected)


def _blocked(
    code: str,
    diagnostics: tuple[str, ...],
    request_hash: str | None,
    failed_mesh: int | None = None,
) -> Task173BlockedResult:
    projection = {
        "schema_version": "task173.fixed-geometry-rating-blocked.v1",
        "status": "BLOCKED",
        "failure_code": code,
        "failed_mesh_subdivisions": failed_mesh,
        "request_hash": request_hash,
        "diagnostics": list(diagnostics),
    }
    digest = canonical_sha256(projection)
    return Task173BlockedResult(
        schema_version="task173.fixed-geometry-rating-blocked.v1",
        status="BLOCKED",
        failure_code=code,
        failed_mesh_subdivisions=failed_mesh,
        request_hash=request_hash,
        diagnostics=diagnostics,
        result_hash=digest,
        result_id=f"urn:hxforge:task173:blocked:{digest}",
    )


def _roundtrip_float(value: float) -> str:
    if not math.isfinite(value):
        raise _Stage3Failure("BLOCKED_NONFINITE_PROPERTY_STATE")
    return str(Decimal(str(value)))


def _property_snapshot(state: FluidState) -> PropertySnapshot:
    provenance = state.provenance
    if (
        provenance.backend_name != "CoolProp"
        or provenance.backend_version != "8.0.0"
        or provenance.backend_git_revision != "ae81610e7d23efc57f9d051c8e70a4d66e87537f"
        or provenance.fluid_identifier != "HEOS::Water"
        or provenance.reference_state_policy is not ReferenceStatePolicy.DEF
        or state.phase is not PhaseRegion.LIQUID
    ):
        raise _Stage3Failure("BLOCKED_PROPERTY_AUTHORITY_OR_PHASE_MISMATCH")
    query_type = cast(Literal["TP", "PH"], provenance.query_type.value)
    if query_type not in {"TP", "PH"}:
        raise _Stage3Failure("BLOCKED_PROPERTY_QUERY_TYPE_MISMATCH", query_type)
    inputs = {key: _roundtrip_float(value) for key, value in provenance.inputs}
    return PropertySnapshot(
        temperature_k=_roundtrip_float(state.temperature_k),
        pressure_pa=_roundtrip_float(state.pressure_pa),
        enthalpy_j_kg=_roundtrip_float(state.enthalpy_j_kg),
        density_kg_m3=_roundtrip_float(state.density_kg_m3),
        cp_j_kg_k=_roundtrip_float(state.cp_j_kg_k),
        viscosity_pa_s=_roundtrip_float(state.viscosity_pa_s),
        conductivity_w_m_k=_roundtrip_float(state.conductivity_w_m_k),
        entropy_j_kg_k=_roundtrip_float(state.entropy_j_kg_k),
        phase="liquid",
        backend="HEOS::Water",
        provider="CoolProp",
        provider_version="8.0.0",
        provider_git_revision="ae81610e7d23efc57f9d051c8e70a4d66e87537f",
        reference_state="DEF",
        query_type=query_type,
        inputs=inputs,
        configuration_fingerprint=provenance.configuration_fingerprint,
    )


def _checked_thermo(
    state: FluidState,
    *,
    query_type: str,
) -> _ThermoState:
    snapshot = _property_snapshot(state)
    temperature = _d(state.temperature_k)
    pressure = _d(state.pressure_pa)
    enthalpy = _d(state.enthalpy_j_kg)
    # The approved property domain is expressed in T/P/phase. For a PH query,
    # the shooting enthalpy is hard-bounded before the provider call below;
    # the returned enthalpy is provider output. For a TP query, enthalpy is
    # likewise output, not a second shooting-coordinate input to clip or bound.
    if (
        not T_MIN_K <= temperature <= T_MAX_K
        or pressure != REFERENCE_PRESSURE_PA
        or state.phase is not PhaseRegion.LIQUID
        or snapshot.query_type != query_type
    ):
        raise _Stage3Failure(
            "BLOCKED_LOCAL_STATE_RECONSTRUCTION_DOMAIN_EXIT",
            f"T={temperature}",
            f"P={pressure}",
            f"h={enthalpy}",
            f"query={query_type}",
        )
    identity = canonical_sha256(snapshot.model_dump(mode="json"))
    return _ThermoState(state, snapshot, identity)


def _state_from_enthalpy(
    provider: PropertyProvider,
    enthalpy_j_kg: Decimal,
    *,
    shell_search_state: bool = False,
) -> _ThermoState:
    if enthalpy_j_kg < H_MIN_J_KG:
        if shell_search_state:
            raise _LowSideDomainInfeasible
        raise _Stage3Failure("BLOCKED_LOCAL_STATE_RECONSTRUCTION_DOMAIN_EXIT", f"h={enthalpy_j_kg}")
    if enthalpy_j_kg > H_MAX_J_KG:
        raise _Stage3Failure("BLOCKED_LOCAL_STATE_RECONSTRUCTION_DOMAIN_EXIT", f"h={enthalpy_j_kg}")
    if enthalpy_j_kg == H_MAX_J_KG:
        # H_MAX is the reviewed 300 K boundary state. PH inversion can return
        # a temperature just above the closed domain. Use the native TP
        # producer at this exact boundary. Its returned enthalpy is retained
        # as provider output and is not reinterpreted as the shooting input.
        return _state_at_inlet(provider, T_MAX_K)
    provider_enthalpy = Decimal(str(float(enthalpy_j_kg)))
    if provider_enthalpy < H_MIN_J_KG:
        if shell_search_state:
            raise _LowSideDomainInfeasible
        raise _Stage3Failure(
            "BLOCKED_LOCAL_STATE_RECONSTRUCTION_DOMAIN_EXIT",
            f"provider_h={provider_enthalpy}",
        )
    if provider_enthalpy > H_MAX_J_KG:
        raise _Stage3Failure(
            "BLOCKED_LOCAL_STATE_RECONSTRUCTION_DOMAIN_EXIT",
            f"provider_h={provider_enthalpy}",
        )
    try:
        state = provider.state_ph(
            FluidIdentifier(name="Water"),
            pressure_pa=float(REFERENCE_PRESSURE_PA),
            enthalpy_j_kg=float(enthalpy_j_kg),
            reference_state=ReferenceStatePolicy.DEF,
        )
    except Exception as exc:
        raise _Stage3Failure(
            "BLOCKED_PROPERTY_EVALUATION_FAILURE", "state_ph", type(exc).__name__
        ) from exc
    return _checked_thermo(state, query_type="PH")


def _state_at_inlet(
    provider: PropertyProvider,
    temperature_k: Decimal,
) -> _ThermoState:
    try:
        state = provider.state_tp(
            FluidIdentifier(name="Water"),
            temperature_k=float(temperature_k),
            pressure_pa=float(REFERENCE_PRESSURE_PA),
        )
    except Exception as exc:
        raise _Stage3Failure(
            "BLOCKED_PROPERTY_EVALUATION_FAILURE", "state_tp", type(exc).__name__
        ) from exc
    return _checked_thermo(state, query_type="TP")


def _face_state(
    thermo: _ThermoState,
    *,
    side: Literal["TUBE", "SHELL"],
    face_index: int,
    coordinate_m: Decimal,
    face_count: int,
    producer_authority_id: str,
) -> FaceState:
    path_id = TUBE_FLOW_PATH_ID if side == "TUBE" else SHELL_FLOW_PATH_ID
    if face_index == 0:
        role: Literal["INLET", "OUTLET", "INTERIOR"] = "INLET" if side == "TUBE" else "OUTLET"
    elif face_index == face_count:
        role = "OUTLET" if side == "TUBE" else "INLET"
    else:
        role = "INTERIOR"
    provenance: dict[str, str] = {
        "property_source": "CoolProp",
        "backend": "HEOS::Water",
        "version": "8.0.0",
        "reference_state": "DEF",
        "reconstruction_authority_hash": LOCAL_STATE_RECONSTRUCTION_AUTHORITY_HASH,
    }
    projection = {
        "schema_version": "task173.face-state.v1",
        "case_revision_id": CASE_REVISION_ID,
        "topology_id": TOPOLOGY_ID,
        "flow_path_id": path_id,
        "side": side,
        "face_index": face_index,
        "physical_coordinate_m": str(coordinate_m),
        "travel_role": role,
        "temperature_k": _roundtrip_float(thermo.native.temperature_k),
        "pressure_pa": str(REFERENCE_PRESSURE_PA),
        "enthalpy_j_kg": _roundtrip_float(thermo.native.enthalpy_j_kg),
        "property_profile_id": PROFILE_ID,
        "property_snapshot_hash": thermo.snapshot_hash,
        "producer_authority_id": producer_authority_id,
        "provenance": provenance,
    }
    digest = canonical_sha256(projection)
    return FaceState(
        face_id=f"urn:hxforge:task173:face:{digest}",
        face_hash=digest,
        case_revision_id=CASE_REVISION_ID,
        topology_id=TOPOLOGY_ID,
        flow_path_id=path_id,
        side=side,
        face_index=face_index,
        physical_coordinate_m=coordinate_m,
        travel_role=role,
        temperature_k=_d(thermo.native.temperature_k),
        pressure_pa=REFERENCE_PRESSURE_PA,
        enthalpy_j_kg=_d(thermo.native.enthalpy_j_kg),
        property_profile_id=PROFILE_ID,
        property_snapshot_hash=thermo.snapshot_hash,
        property_snapshot=thermo.snapshot,
        producer_authority_id=producer_authority_id,
        provenance=provenance,
    )


def _local_state_receipt(
    *,
    side: Literal["TUBE", "SHELL"],
    support: Any,
    upstream: FaceState,
    downstream: FaceState,
    evaluation_state: _ThermoState,
    cell_id: str,
) -> LocalStateReceipt:
    state_projection = {
        "schema_version": "task173.constitutive-evaluation-state.v1",
        "case_revision_id": CASE_REVISION_ID,
        "topology_id": TOPOLOGY_ID,
        "flow_path_id": TUBE_FLOW_PATH_ID if side == "TUBE" else SHELL_FLOW_PATH_ID,
        "side": side,
        "physical_support_id": support.physical_segment_id,
        "physical_segment_id": support.physical_segment_id,
        "numerical_cell_id": cell_id,
        "upstream_face_state_id": upstream.face_id,
        "upstream_face_state_hash": upstream.face_hash,
        "downstream_face_state_id": downstream.face_id,
        "downstream_face_state_hash": downstream.face_hash,
        "evaluation_temperature_k": _roundtrip_float(evaluation_state.native.temperature_k),
        "evaluation_pressure_pa": str(REFERENCE_PRESSURE_PA),
        "evaluation_enthalpy_j_kg": _roundtrip_float(evaluation_state.native.enthalpy_j_kg),
        "property_profile_id": PROFILE_ID,
        "property_snapshot_hash": evaluation_state.snapshot_hash,
        "reconstruction_authority_id": LOCAL_STATE_RECONSTRUCTION_AUTHORITY_ID,
        "reconstruction_authority_hash": LOCAL_STATE_RECONSTRUCTION_AUTHORITY_HASH,
    }
    state_hash = canonical_sha256(state_projection)
    receipt_projection = {
        **state_projection,
        "constitutive_evaluation_state_id": f"urn:hxforge:task173:local-state:{state_hash}",
        "reconstruction_authority_hash": LOCAL_STATE_RECONSTRUCTION_AUTHORITY_HASH,
    }
    receipt_hash = canonical_sha256(receipt_projection)
    return LocalStateReceipt(
        receipt_id=f"urn:hxforge:task173:local-state-receipt:{receipt_hash}",
        receipt_hash=receipt_hash,
        side=side,
        physical_support_id=support.physical_segment_id,
        physical_segment_id=support.physical_segment_id,
        numerical_cell_id=cell_id,
        upstream_face_state_id=upstream.face_id,
        upstream_face_state_hash=upstream.face_hash,
        downstream_face_state_id=downstream.face_id,
        downstream_face_state_hash=downstream.face_hash,
        constitutive_evaluation_state_id=f"urn:hxforge:task173:local-state:{state_hash}",
        constitutive_evaluation_state_hash=state_hash,
        constitutive_evaluation_temperature_k=_d(evaluation_state.native.temperature_k),
        constitutive_evaluation_enthalpy_j_kg=_d(evaluation_state.native.enthalpy_j_kg),
        constitutive_evaluation_property_snapshot_hash=evaluation_state.snapshot_hash,
        constitutive_evaluation_property_snapshot=evaluation_state.snapshot,
        reconstruction_authority_id=LOCAL_STATE_RECONSTRUCTION_AUTHORITY_ID,
        reconstruction_authority_hash=LOCAL_STATE_RECONSTRUCTION_AUTHORITY_HASH,
        property_profile_id=PROFILE_ID,
        topology_id=TOPOLOGY_ID,
        flow_path_id=TUBE_FLOW_PATH_ID if side == "TUBE" else SHELL_FLOW_PATH_ID,
    )


def _task172_request(
    support: Any,
    tube_state: _ThermoState,
    shell_state: _ThermoState,
    shell_authority: Any,
) -> Task172LocalRequest:
    topology = TopologyBinding(
        topology_id=TOPOLOGY_ID,
        task171_result_hash=TASK171_RESULT_HASH,
        mesh_identity="ec4a01bbfe81cd6b12ede63c6f4e4aa05372414868cee54a54fb7c98aaffd607",
        physical_ownership_hash=PHYSICAL_OWNERSHIP_HASH,
        definition_projection_hash=DEFINITION_PROJECTION_HASH,
        selected_variant="TUBE_HOT_SHELL_COLD",
        thermal_role_selection_authority_id="V07-T172-R119C-THERMAL-ROLE-SELECTION-R1",
        tube_role="HOT",
        shell_role="COLD",
        tube_flow_path_id=TUBE_FLOW_PATH_ID,
        shell_flow_path_id=SHELL_FLOW_PATH_ID,
    )
    return Task172LocalRequest(
        topology=topology,
        support=support,
        tube_bulk_state=LocalState(
            temperature_k=_d(tube_state.native.temperature_k),
            pressure_pa=REFERENCE_PRESSURE_PA,
        ),
        shell_bulk_state=LocalState(
            temperature_k=_d(shell_state.native.temperature_k),
            pressure_pa=REFERENCE_PRESSURE_PA,
        ),
        tube_mass_flow_kg_s=TUBE_MASS_FLOW_KG_S,
        shell_mass_flow_kg_s=SHELL_MASS_FLOW_KG_S,
        shell_flow_authority=shell_authority,
    )


def _preflight_task172_trial(
    q_w: float,
    *,
    support: Any,
    tube_local: _ThermoState,
    shell_local: _ThermoState,
    shell_authority: Any,
    request: Task172LocalRequest,
) -> None:
    """Prove all caller-known trial guards before native TASK172 evaluation."""
    if not math.isfinite(q_w) or q_w < 0:
        raise _Stage3Failure("BLOCKED_NONFINITE_OR_NEGATIVE_CELL_TRIAL", repr(q_w))
    for side, state in (("tube", tube_local), ("shell", shell_local)):
        native = state.native
        numeric_values = (
            native.temperature_k,
            native.pressure_pa,
            native.enthalpy_j_kg,
            native.density_kg_m3,
            native.cp_j_kg_k,
            native.viscosity_pa_s,
            native.conductivity_w_m_k,
        )
        if not all(math.isfinite(value) for value in numeric_values):
            raise _Stage3Failure("BLOCKED_NONFINITE_LOCAL_PROPERTY_STATE", side)
        if (
            not T_MIN_K <= _d(native.temperature_k) <= T_MAX_K
            or _d(native.pressure_pa) != REFERENCE_PRESSURE_PA
            or native.phase is not PhaseRegion.LIQUID
            or state.snapshot.backend != "HEOS::Water"
            or state.snapshot.provider != "CoolProp"
            or state.snapshot.provider_version != "8.0.0"
            or state.snapshot.reference_state != "DEF"
            or state.snapshot.phase != "liquid"
        ):
            raise _Stage3Failure("BLOCKED_LOCAL_PROPERTY_STATE_PREFLIGHT", side)
    if tube_local.native.temperature_k < shell_local.native.temperature_k:
        raise _Stage3Failure("BLOCKED_HOT_COLD_TEMPERATURE_CROSSING", "local-state-preflight")
    if (
        request.case_revision_id != CASE_REVISION_ID
        or request.topology.topology_id != TOPOLOGY_ID
        or request.topology.task171_result_hash != TASK171_RESULT_HASH
        or request.topology.physical_ownership_hash != PHYSICAL_OWNERSHIP_HASH
        or request.topology.tube_role != "HOT"
        or request.topology.shell_role != "COLD"
        or request.support != support
        or len(recompute_task172_support_id(request)) != 64
    ):
        raise _Stage3Failure("BLOCKED_TASK172_SUPPORT_OR_ROLE_PREFLIGHT")
    if (
        shell_authority.task031_geometry.geometry_hash != EXPECTED_TASK031_GEOMETRY_HASH
        or shell_authority.task166_result.result_hash != EXPECTED_TASK166_RESULT_HASH
    ):
        raise _Stage3Failure("BLOCKED_NATIVE_SHELL_FLOW_AUTHORITY_PREFLIGHT")


def _cell_evaluation(
    q_w: float,
    *,
    support: Any,
    tube_upstream: _ThermoState,
    shell_physical_left: _ThermoState,
    provider: PropertyProvider,
    shell_authority: Any,
) -> _CellEvaluation:
    q = _d(q_w)
    with localcontext() as context:
        context.prec = 70
        tube_downstream_h = _d(tube_upstream.native.enthalpy_j_kg) - q / TUBE_MASS_FLOW_KG_S
        shell_next_h = _d(shell_physical_left.native.enthalpy_j_kg) - q / SHELL_MASS_FLOW_KG_S
        tube_mid_h = (_d(tube_upstream.native.enthalpy_j_kg) + tube_downstream_h) / Decimal(2)
        shell_mid_h = (_d(shell_physical_left.native.enthalpy_j_kg) + shell_next_h) / Decimal(2)
    if tube_downstream_h < H_MIN_J_KG or tube_downstream_h > H_MAX_J_KG:
        raise _Stage3Failure(
            "BLOCKED_LOCAL_STATE_RECONSTRUCTION_DOMAIN_EXIT",
            "tube downstream face enthalpy outside admitted domain",
            str(tube_downstream_h),
        )
    if shell_next_h < H_MIN_J_KG:
        # Search-side feasibility only. No property call is made for this state.
        raise _LowSideDomainInfeasible
    if shell_next_h > H_MAX_J_KG:
        raise _Stage3Failure(
            "BLOCKED_LOCAL_STATE_RECONSTRUCTION_DOMAIN_EXIT",
            "shell next face enthalpy outside admitted domain",
            str(shell_next_h),
        )
    tube_downstream = _state_from_enthalpy(provider, tube_downstream_h)
    shell_next = _state_from_enthalpy(provider, shell_next_h, shell_search_state=True)
    tube_local = _state_from_enthalpy(provider, tube_mid_h)
    shell_local = _state_from_enthalpy(provider, shell_mid_h)
    task172_request = _task172_request(support, tube_local, shell_local, shell_authority)
    _preflight_task172_trial(
        q_w,
        support=support,
        tube_local=tube_local,
        shell_local=shell_local,
        shell_authority=shell_authority,
        request=task172_request,
    )
    task172_result = task172_validate(task172_request, provider)
    if type(task172_result) is Task172BlockedResult:
        if task172_result.failure_code == "BLOCKED_RESIDUAL_ACCEPTANCE":
            if task172_result.request_hash != recompute_task172_request_hash(
                task172_request
            ) or task172_result.blocked_result_hash != recompute_task172_blocked_result_hash(
                task172_result
            ):
                raise _Stage3Failure("BLOCKED_TASK172_BLOCKED_RESULT_IDENTITY_REPLAY")
            # Do not inspect/use diagnostic_last_iterate: it is not an evaluation of F(q).
            raise _Task172NumericalHole
        raise _Stage3Failure(
            "BLOCKED_TASK172_LOCAL_CONSTITUTIVE_CLOSURE",
            task172_result.failure_code,
        )
    if type(task172_result) is not Task172LocalResult:
        raise _Stage3Failure("BLOCKED_TASK172_RESULT_CONTRACT_TYPE")
    if (
        recompute_task172_request_hash(task172_request) != task172_result.request_hash
        or recompute_task172_result_hash(task172_result) != task172_result.result_hash
        or task172_result.physical_support_id != recompute_task172_support_id(task172_request)
        or task172_result.physical_segment_id != support.physical_segment_id
        or task172_result.tube_cell_id != support.tube_cell_id
        or task172_result.shell_cell_id != support.shell_cell_id
        or task172_result.wall_interface_id != support.wall_interface_id
    ):
        raise _Stage3Failure("BLOCKED_TASK172_LOCAL_IDENTITY_REPLAY")
    if task172_result.signed_q_hot_to_cold_w < 0:
        raise _Stage3Failure(
            "BLOCKED_NEGATIVE_PHYSICAL_HEAT_RATE",
            str(task172_result.signed_q_hot_to_cold_w),
        )
    return _CellEvaluation(
        q_w=q,
        tube_downstream=tube_downstream,
        shell_next_physical=shell_next,
        tube_local=tube_local,
        shell_local=shell_local,
        task172_request=task172_request,
        task172_result=task172_result,
    )


def _solve_cell(
    *,
    support: Any,
    tube_upstream: _ThermoState,
    shell_physical_left: _ThermoState,
    provider: PropertyProvider,
    shell_authority: Any,
    search_stats: _CellSearchStats | None = None,
    hole_neighborhoods: list[dict[str, str]] | None = None,
    mesh_subdivisions: int | None = None,
    outer_iteration: int | None = None,
    shooting_enthalpy: Decimal | None = None,
) -> _CellEvaluation:
    h_tube = _d(tube_upstream.native.enthalpy_j_kg)
    h_shell = _d(shell_physical_left.native.enthalpy_j_kg)
    with localcontext() as context:
        context.prec = 70
        tube_capacity = TUBE_MASS_FLOW_KG_S * (h_tube - H_MIN_J_KG)
        shell_capacity = SHELL_MASS_FLOW_KG_S * (h_shell - H_MIN_J_KG)
    if tube_capacity < 0 or shell_capacity < 0:
        raise _Stage3Failure("BLOCKED_LOCAL_STATE_RECONSTRUCTION_DOMAIN_EXIT")

    stats = search_stats if search_stats is not None else _CellSearchStats()
    neighborhoods = hole_neighborhoods if hole_neighborhoods is not None else []
    trials: dict[float, _CellTrial] = {}
    unrecorded_holes: list[float] = []
    closure_tolerance = Decimal("1e-6")
    cell_evaluation_count = 0
    cell_valid_evaluation_count = 0
    hole_recovery_probe_count = 0
    hole_recovery_bracket_count = 0
    current_search_level = 0
    current_left_trial: _CellTrial | None = None
    current_right_trial: _CellTrial | None = None

    def resource_diagnostics() -> tuple[str, ...]:
        left = current_left_trial
        right = current_right_trial
        width = (
            repr(right.q_w - left.q_w) if left is not None and right is not None else "UNAVAILABLE"
        )
        hole_codes = (
            "BLOCKED_RESIDUAL_ACCEPTANCE"
            if any(item.classification == "TASK172_NUMERICAL_HOLE" for item in trials.values())
            else "NONE"
        )
        mesh_value = mesh_subdivisions if mesh_subdivisions is not None else "UNAVAILABLE"
        outer_value = outer_iteration if outer_iteration is not None else "UNAVAILABLE"
        shooting_value = shooting_enthalpy if shooting_enthalpy is not None else "UNAVAILABLE"
        left_q = left.q_w if left is not None else "UNAVAILABLE"
        right_q = right.q_w if right is not None else "UNAVAILABLE"
        left_f = left.residual if left is not None and left.residual is not None else "UNAVAILABLE"
        right_f = (
            right.residual if right is not None and right.residual is not None else "UNAVAILABLE"
        )
        hole_count = sum(
            1 for item in trials.values() if item.classification == "TASK172_NUMERICAL_HOLE"
        )
        return (
            f"mesh_subdivisions={mesh_value}",
            f"physical_support_id={support.physical_segment_id}",
            f"tube_cell_id={support.tube_cell_id}",
            f"shell_cell_id={support.shell_cell_id}",
            f"wall_interface_id={support.wall_interface_id}",
            f"outer_iteration={outer_value}",
            f"shooting_enthalpy_j_kg={shooting_value}",
            f"left_q_w={left_q}",
            f"right_q_w={right_q}",
            f"left_f_q_w={left_f}",
            f"right_f_q_w={right_f}",
            f"current_search_level={current_search_level}",
            f"cell_evaluation_count={cell_evaluation_count}",
            f"cell_valid_evaluation_count={cell_valid_evaluation_count}",
            f"cell_hole_count={hole_count}",
            f"hole_recovery_bracket_count={hole_recovery_bracket_count}",
            f"hole_codes={hole_codes}",
            f"last_valid_bracket_width_w={width}",
        )

    def set_search_level(level: int) -> None:
        nonlocal current_search_level
        current_search_level = level

    def resource_exhaustion(message: str) -> _Stage3Failure:
        return _Stage3Failure(
            "BLOCKED_CELL_ROOT_RESOURCE_EXHAUSTION",
            message,
            f"maximum_task172_evaluations={MAX_CELL_TASK172_EVALUATIONS}",
            f"maximum_hole_recovery_probes_per_cell={MAX_HOLE_RECOVERY_PROBES_PER_CELL}",
            *resource_diagnostics(),
        )

    def evaluate(q: float) -> _CellTrial:
        nonlocal cell_evaluation_count, cell_valid_evaluation_count
        if q not in trials:
            if cell_evaluation_count >= MAX_CELL_TASK172_EVALUATIONS:
                raise resource_exhaustion("TASK172 evaluation cap reached")
            cell_evaluation_count += 1
            stats.record_evaluation()
            try:
                evaluation = _cell_evaluation(
                    q,
                    support=support,
                    tube_upstream=tube_upstream,
                    shell_physical_left=shell_physical_left,
                    provider=provider,
                    shell_authority=shell_authority,
                )
            except _Task172NumericalHole:
                stats.record_hole(q, support.physical_segment_id)
                unrecorded_holes.append(q)
                trials[q] = _CellTrial(q, "TASK172_NUMERICAL_HOLE")
            except _LowSideDomainInfeasible:
                trials[q] = _CellTrial(q, "LOW_SIDE_DOMAIN_INFEASIBLE")
            except _Stage3Failure as exc:
                trials[q] = _CellTrial(q, "HARD_BLOCKER", failure_code=exc.code)
                raise
            else:
                cell_valid_evaluation_count += 1
                residual = _d(q) - evaluation.task172_result.signed_q_hot_to_cold_w
                trials[q] = _CellTrial(q, "VALID_CELL_EVALUATION", evaluation, residual)
        return trials[q]

    def recovery_evaluate(q: float) -> _CellTrial:
        nonlocal hole_recovery_probe_count
        if q not in trials:
            if hole_recovery_probe_count >= MAX_HOLE_RECOVERY_PROBES_PER_CELL:
                raise resource_exhaustion("local numerical-hole probe cap reached")
            hole_recovery_probe_count += 1
        return evaluate(q)

    def begin_hole_recovery() -> None:
        nonlocal hole_recovery_bracket_count
        if hole_recovery_bracket_count >= MAX_HOLE_RECOVERY_BRACKETS_PER_CELL:
            raise resource_exhaustion("local numerical-hole bracket cap reached")
        hole_recovery_bracket_count += 1

    def require_valid(trial: _CellTrial, endpoint_name: str) -> tuple[_CellEvaluation, Decimal]:
        if trial.classification != "VALID_CELL_EVALUATION" or trial.evaluation is None:
            raise _Stage3Failure(
                "BLOCKED_CELL_CONSTITUTIVE_BRACKET_NOT_ESTABLISHED",
                f"{endpoint_name}_classification={trial.classification}",
            )
        if trial.residual is None:
            raise _Stage3Failure("BLOCKED_CELL_ROOT_RESIDUAL_MISSING")
        return trial.evaluation, trial.residual

    def is_eligible(trial: _CellTrial) -> bool:
        return _eligible_trial(trial) and abs(trial.residual or Decimal(0)) <= closure_tolerance

    def record_hole_neighbors(samples: list[_CellTrial]) -> None:
        valid = sorted(
            (
                sample
                for sample in samples
                if sample.classification == "VALID_CELL_EVALUATION"
                and sample.evaluation is not None
                and sample.residual is not None
            ),
            key=lambda sample: sample.q_w,
        )
        for hole_q in unrecorded_holes:
            left = [sample for sample in valid if sample.q_w < hole_q]
            right = [sample for sample in valid if sample.q_w > hole_q]
            if not left or not right:
                continue
            left_trial = left[-1]
            right_trial = right[0]
            assert left_trial.evaluation is not None and left_trial.residual is not None
            assert right_trial.evaluation is not None and right_trial.residual is not None
            neighborhoods.append(
                {
                    "physical_support_id": support.physical_segment_id,
                    "hole_q_trial_w": repr(hole_q),
                    "failure_code": "BLOCKED_RESIDUAL_ACCEPTANCE",
                    "left_valid_q_w": repr(left_trial.q_w),
                    "left_task172_result_hash": left_trial.evaluation.task172_result.result_hash,
                    "left_f_q_w": str(left_trial.residual),
                    "right_valid_q_w": repr(right_trial.q_w),
                    "right_task172_result_hash": right_trial.evaluation.task172_result.result_hash,
                    "right_f_q_w": str(right_trial.residual),
                }
            )
        unrecorded_holes.clear()

    lower = 0.0
    lower_trial = evaluate(lower)
    lower_is_hole = lower_trial.classification == "TASK172_NUMERICAL_HOLE"
    if not lower_is_hole:
        lower_evaluation, lower_residual = require_valid(lower_trial, "lower_endpoint")
        if lower_residual > 0:
            raise _Stage3Failure(
                "BLOCKED_NEGATIVE_PHYSICAL_HEAT_RATE",
                "native TASK172 requests negative q at the nonnegative cell boundary",
            )
        if is_eligible(lower_trial):
            return lower_evaluation

    cap = min(tube_capacity, shell_capacity)
    if cap <= 0:
        if lower_is_hole:
            raise _Stage3Failure(
                "BLOCKED_CELL_VALID_EVALUATION_BRACKET_UNRESOLVED",
                "no positive-width valid q interval remains after lower-endpoint hole",
            )
        if shell_capacity <= tube_capacity:
            # At the lower shell boundary, the valid q=0 constitutive evaluation
            # is positive. Any normal positive propagation leaves the domain.
            raise _LowSideDomainInfeasible
        raise _Stage3Failure("BLOCKED_CELL_CONSTITUTIVE_BRACKET_NOT_ESTABLISHED")

    upper = float(cap)
    # The provider accepts binary64 enthalpy. Move inward only as needed to
    # ensure the exact propagated Decimal state remains inside the reviewed box.
    for _ in range(8):
        q_decimal = Decimal(str(upper))
        with localcontext() as context:
            context.prec = 70
            tube_h = h_tube - q_decimal / TUBE_MASS_FLOW_KG_S
            shell_h = h_shell - q_decimal / SHELL_MASS_FLOW_KG_S
        if tube_h >= H_MIN_J_KG and shell_h >= H_MIN_J_KG:
            break
        upper = math.nextafter(upper, 0.0)
    else:
        raise _Stage3Failure("BLOCKED_CELL_CONSTITUTIVE_BRACKET_NOT_ESTABLISHED")
    if upper <= lower:
        if lower_is_hole:
            raise _Stage3Failure(
                "BLOCKED_CELL_VALID_EVALUATION_BRACKET_UNRESOLVED",
                "no positive-width valid q interval remains after lower-endpoint hole",
            )
        if shell_capacity <= tube_capacity:
            raise _LowSideDomainInfeasible
        raise _Stage3Failure("BLOCKED_CELL_CONSTITUTIVE_BRACKET_NOT_ESTABLISHED")

    upper_trial = evaluate(upper)
    upper_is_hole = upper_trial.classification == "TASK172_NUMERICAL_HOLE"
    if lower_is_hole or upper_is_hole:
        current_left_trial, current_right_trial = lower_trial, upper_trial
        begin_hole_recovery()
        lower_trial, upper_trial, eligible = _discover_valid_sign_bracket_from_endpoint_holes(
            lower,
            upper,
            (lower_trial, upper_trial),
            evaluate=recovery_evaluate,
            all_trials=lambda: list(trials.values()),
            record_hole_neighbors=record_hole_neighbors,
            on_level=set_search_level,
        )
        if eligible is not None:
            assert eligible.evaluation is not None
            return eligible.evaluation
    _, lower_residual = require_valid(lower_trial, "lower_endpoint")
    upper_evaluation, upper_residual = require_valid(upper_trial, "upper_endpoint")
    if lower_residual > 0:
        raise _Stage3Failure(
            "BLOCKED_NEGATIVE_PHYSICAL_HEAT_RATE",
            "valid lower cell bracket endpoint has positive residual",
        )
    if upper_residual < 0:
        if shell_capacity <= tube_capacity:
            # No valid constitutive root exists before the shell reaches its
            # hard lower property boundary: this is a search-side infeasibility.
            raise _LowSideDomainInfeasible
        raise _Stage3Failure(
            "BLOCKED_CELL_CONSTITUTIVE_BRACKET_NOT_ESTABLISHED",
            f"q_upper={upper}",
            f"residual_upper={upper_residual}",
        )
    if is_eligible(upper_trial):
        return upper_evaluation
    if lower_residual > 0 or upper_residual < 0:
        raise _Stage3Failure(
            "BLOCKED_CELL_CONSTITUTIVE_BRACKET_NOT_ESTABLISHED",
            f"F_lower_w={lower_residual}",
            f"F_upper_w={upper_residual}",
        )

    left = lower_trial
    right = upper_trial
    iterations = 0
    while iterations < MAX_CELL_ROOT_BISECTION_ITERATIONS:
        _, left_f = require_valid(left, "left_bracket")
        _, right_f = require_valid(right, "right_bracket")
        if left_f > 0 or right_f < 0:
            raise _Stage3Failure("BLOCKED_CELL_VALID_POINT_BRACKET_SIGN_INVALID")
        current_left_trial, current_right_trial = left, right
        midpoint = left.q_w + (right.q_w - left.q_w) / 2.0
        if midpoint == left.q_w or midpoint == right.q_w:
            eligible_endpoint = next(
                (sample for sample in (left, right) if is_eligible(sample)), None
            )
            if eligible_endpoint is not None and eligible_endpoint.evaluation is not None:
                return eligible_endpoint.evaluation
            raise _Stage3Failure(
                "PRECISION_FLOOR_UNRESOLVED",
                "CELL_ROOT_PRECISION_FLOOR_REACHED",
                f"left_q_w={left.q_w}",
                f"right_q_w={right.q_w}",
            )
        iterations += 1
        current_search_level = 0
        midpoint_trial = evaluate(midpoint)
        if midpoint_trial.classification == "LOW_SIDE_DOMAIN_INFEASIBLE":
            raise _Stage3Failure(
                "BLOCKED_CELL_CONSTITUTIVE_BRACKET_NOT_ESTABLISHED",
                "interior_trial_became_low_side_domain_infeasible",
            )
        if midpoint_trial.classification == "VALID_CELL_EVALUATION":
            if is_eligible(midpoint_trial):
                record_hole_neighbors(list(trials.values()))
                assert midpoint_trial.evaluation is not None
                return midpoint_trial.evaluation
            assert midpoint_trial.residual is not None
            if midpoint_trial.residual <= 0:
                left = midpoint_trial
            else:
                right = midpoint_trial
            continue

        # The hole has no residual sign. Refine only with valid native points.
        begin_hole_recovery()
        left, right, eligible = _dyadic_refine_valid_bracket(
            left,
            right,
            midpoint_trial,
            evaluate=recovery_evaluate,
            all_trials=lambda: list(trials.values()),
            record_hole_neighbors=record_hole_neighbors,
            on_level=set_search_level,
        )
        if eligible is not None:
            assert eligible.evaluation is not None
            return eligible.evaluation
    raise _Stage3Failure(
        "BLOCKED_CELL_ROOT_RESOURCE_EXHAUSTION",
        f"maximum_cell_root_bisection_iterations={MAX_CELL_ROOT_BISECTION_ITERATIONS}",
        *resource_diagnostics(),
    )


def _make_rated_cell(
    *,
    support: Any,
    solution: _CellEvaluation,
    tube_left_face: FaceState,
    tube_right_face: FaceState,
    shell_left_face: FaceState,
    shell_right_face: FaceState,
) -> _CellRecord:
    tube_id = support.tube_cell_id
    shell_id = support.shell_cell_id
    tube_receipt = _local_state_receipt(
        side="TUBE",
        support=support,
        upstream=tube_left_face,
        downstream=tube_right_face,
        evaluation_state=solution.tube_local,
        cell_id=tube_id,
    )
    # Shell travel is x=6 -> 0: right face is upstream and left face is downstream.
    shell_receipt = _local_state_receipt(
        side="SHELL",
        support=support,
        upstream=shell_right_face,
        downstream=shell_left_face,
        evaluation_state=solution.shell_local,
        cell_id=shell_id,
    )
    task_result = solution.task172_result
    bounds = recompute_task172_local_roundoff_bounds(solution.task172_request, task_result)
    duty_floor = sum(bounds[:3], Decimal(0))
    local_wall_floor = bounds[3]
    task_projection = task_result.model_dump(mode="json")
    rated = RatedCell(
        physical_support_id=support.physical_segment_id,
        physical_segment_id=support.physical_segment_id,
        support_start_m=support.support_start_m,
        support_end_m=support.support_end_m,
        tube_cell_id=tube_id,
        shell_cell_id=shell_id,
        wall_interface_id=support.wall_interface_id,
        tube_upstream_face_id=tube_left_face.face_id,
        tube_downstream_face_id=tube_right_face.face_id,
        shell_upstream_face_id=shell_right_face.face_id,
        shell_downstream_face_id=shell_left_face.face_id,
        tube_state_receipt=tube_receipt,
        shell_state_receipt=shell_receipt,
        task172_request_hash=task_result.request_hash,
        task172_result_id=task_result.result_id,
        task172_result_hash=task_result.result_hash,
        task172_result_projection=task_projection,
        signed_q_hot_to_cold_w=solution.q_w,
        wall_temperature_inner_k=task_result.wall_temperature_inner_k,
        wall_temperature_outer_k=task_result.wall_temperature_outer_k,
        shell_j_mu=task_result.shell_j_mu,
        local_duty_roundoff_bound_w=duty_floor,
        local_wall_temperature_roundoff_bound_k=local_wall_floor,
    )
    tube_approach = tube_left_face.temperature_k - shell_left_face.temperature_k
    shell_approach = tube_right_face.temperature_k - shell_right_face.temperature_k
    if (
        task_result.wall_temperature_inner_k < task_result.wall_temperature_outer_k
        or task_result.wall_temperature_inner_k > solution.tube_local.native.temperature_k
        or task_result.wall_temperature_outer_k < solution.shell_local.native.temperature_k
    ):
        raise _Stage3Failure(
            "BLOCKED_PHYSICAL_WALL_ORDERING",
            task_result.result_id,
        )
    return _CellRecord(
        support=support,
        solution=solution,
        tube_upstream_face=tube_left_face,
        tube_downstream_face=tube_right_face,
        shell_physical_left_face=shell_left_face,
        shell_physical_right_face=shell_right_face,
        tube_receipt=tube_receipt,
        shell_receipt=shell_receipt,
        rated_cell=rated,
        tube_approach_k=tube_approach,
        shell_approach_k=shell_approach,
    )


def _valid_trajectory(
    subdivisions: int,
    shell_outlet_enthalpy: Decimal,
    provider: PropertyProvider,
    shell_authority: Any,
    outer_iterations: int,
    search_stats: _CellSearchStats | None = None,
) -> _MeshRun:
    stats = search_stats if search_stats is not None else _CellSearchStats()
    hole_neighborhoods: list[dict[str, str]] = []
    mesh_id = mesh_level_identity(subdivisions)
    tube_face_thermo = _state_at_inlet(provider, TUBE_INLET_T_K)
    shell_face_thermo = _state_from_enthalpy(provider, shell_outlet_enthalpy)
    tube_faces: list[FaceState] = [
        _face_state(
            tube_face_thermo,
            side="TUBE",
            face_index=0,
            coordinate_m=Decimal("0"),
            face_count=5 * subdivisions,
            producer_authority_id="V07-T173-CASE-BOUNDARY-STATE-PROVIDER-R1",
        )
    ]
    shell_faces: list[FaceState] = [
        _face_state(
            shell_face_thermo,
            side="SHELL",
            face_index=0,
            coordinate_m=Decimal("0"),
            face_count=5 * subdivisions,
            producer_authority_id=OUTER_BOUNDARY_SOLVER_AUTHORITY_ID,
        )
    ]
    cells: list[_CellRecord] = []
    interval_duties: list[Decimal] = []
    for interval_index in range(5):
        interval_duty = Decimal(0)
        for subdivision_index in range(subdivisions):
            support = build_local_support(interval_index, subdivisions, subdivision_index)
            # The paired shell and tube numerical supports are one exact physical support.
            if not (
                support.support_start_m < support.support_end_m
                and support.inside_area_m2 > 0
                and support.outside_area_m2 > 0
            ):
                raise _Stage3Failure("BLOCKED_INVALID_COMMON_PHYSICAL_SUPPORT")
            tube_upstream = tube_face_thermo
            shell_physical_left = shell_face_thermo
            solution = _solve_cell(
                support=support,
                tube_upstream=tube_upstream,
                shell_physical_left=shell_physical_left,
                provider=provider,
                shell_authority=shell_authority,
                search_stats=stats,
                hole_neighborhoods=hole_neighborhoods,
                mesh_subdivisions=subdivisions,
                outer_iteration=outer_iterations,
                shooting_enthalpy=shell_outlet_enthalpy,
            )
            coordinate = support.support_end_m
            face_index = len(tube_faces)
            tube_right = _face_state(
                solution.tube_downstream,
                side="TUBE",
                face_index=face_index,
                coordinate_m=coordinate,
                face_count=5 * subdivisions,
                producer_authority_id="V07-T173-FACE-ENTHALPY-PROPAGATION-R1",
            )
            shell_right = _face_state(
                solution.shell_next_physical,
                side="SHELL",
                face_index=face_index,
                coordinate_m=coordinate,
                face_count=5 * subdivisions,
                producer_authority_id="V07-T173-FACE-ENTHALPY-PROPAGATION-R1",
            )
            record = _make_rated_cell(
                support=support,
                solution=solution,
                tube_left_face=tube_faces[-1],
                tube_right_face=tube_right,
                shell_left_face=shell_faces[-1],
                shell_right_face=shell_right,
            )
            if record.tube_approach_k < 0 or record.shell_approach_k < 0:
                raise _Stage3Failure(
                    "BLOCKED_HOT_COLD_TEMPERATURE_CROSSING",
                    support.tube_cell_id,
                )
            if solution.q_w < 0:
                raise _Stage3Failure("BLOCKED_NEGATIVE_PHYSICAL_HEAT_RATE")
            cells.append(record)
            interval_duty += solution.q_w
            tube_face_thermo = solution.tube_downstream
            shell_face_thermo = solution.shell_next_physical
            tube_faces.append(tube_right)
            shell_faces.append(shell_right)
        interval_duties.append(interval_duty)

    if len(cells) != 5 * subdivisions or len(tube_faces) != 5 * subdivisions + 1:
        raise _Stage3Failure("BLOCKED_MESH_SUPPORT_CARDINALITY")
    if len(shell_faces) != len(tube_faces):
        raise _Stage3Failure("BLOCKED_MESH_FACE_CARDINALITY")
    for index, (tube_face, shell_face) in enumerate(zip(tube_faces, shell_faces, strict=True)):
        if (
            tube_face.face_index != shell_face.face_index
            or tube_face.physical_coordinate_m != shell_face.physical_coordinate_m
            or tube_face.topology_id != shell_face.topology_id
            or tube_face.case_revision_id != shell_face.case_revision_id
        ):
            raise _Stage3Failure("BLOCKED_COMMON_FACE_IDENTITY_MISMATCH", str(index))
        if tube_face.temperature_k < shell_face.temperature_k:
            raise _Stage3Failure("BLOCKED_HOT_COLD_TEMPERATURE_CROSSING", str(index))

    q_wall = sum((cell.solution.q_w for cell in cells), Decimal(0))
    hot_loss = TUBE_MASS_FLOW_KG_S * (tube_faces[0].enthalpy_j_kg - tube_faces[-1].enthalpy_j_kg)
    cold_gain = SHELL_MASS_FLOW_KG_S * (
        shell_faces[0].enthalpy_j_kg - shell_faces[-1].enthalpy_j_kg
    )
    energy_residual = max(
        abs(hot_loss - q_wall),
        abs(cold_gain - q_wall),
        abs(hot_loss - cold_gain),
    )
    total_roundoff_floor = sum(
        (cell.rated_cell.local_duty_roundoff_bound_w for cell in cells), Decimal(0)
    )
    energy_tolerance = max(ENERGY_ACCEPTANCE_FLOOR_W, total_roundoff_floor)
    if energy_residual > energy_tolerance:
        raise _Stage3Failure(
            "BLOCKED_WHOLE_EXCHANGER_ENERGY_BALANCE",
            f"residual_w={energy_residual}",
            f"tolerance_w={energy_tolerance}",
        )
    all_walls_inner = tuple(cell.rated_cell.wall_temperature_inner_k for cell in cells)
    all_walls_outer = tuple(cell.rated_cell.wall_temperature_outer_k for cell in cells)
    wall_floor = max(
        (cell.rated_cell.local_wall_temperature_roundoff_bound_k for cell in cells),
        default=Decimal(0),
    )
    duty_floor = total_roundoff_floor
    min_approach = min(
        (face_t.temperature_k - face_s.temperature_k)
        for face_t, face_s in zip(tube_faces, shell_faces, strict=True)
    )
    terminal_residual_h = shell_faces[-1].enthalpy_j_kg - H_MIN_J_KG
    terminal_residual_t = shell_faces[-1].temperature_k - T_MIN_K
    if terminal_residual_h < 0 or terminal_residual_t < 0:
        raise _Stage3Failure("BLOCKED_TERMINAL_BOUNDARY_BELOW_PRESCRIBED_STATE")
    if any(
        not value.is_finite()
        for value in (
            q_wall,
            hot_loss,
            cold_gain,
            energy_residual,
            terminal_residual_h,
            terminal_residual_t,
            min_approach,
        )
    ):
        raise _Stage3Failure("BLOCKED_NONFINITE_MESH_OBSERVABLE")

    tube_count = 5 * subdivisions
    shell_count = 5 * subdivisions
    wall_count = 5 * subdivisions
    if tube_count + shell_count != 10 * subdivisions:
        raise _Stage3Failure("BLOCKED_MESH_CELL_COUNT_CONTRACT")
    projection = {
        "schema_version": "task173.mesh-rating-run.v1",
        "case_revision_id": CASE_REVISION_ID,
        "mesh_identity": mesh_id,
        "subdivisions_per_physical_interval_per_side": subdivisions,
        "tube_cell_count": tube_count,
        "shell_cell_count": shell_count,
        "total_numerical_cell_count": tube_count + shell_count,
        "wall_interface_count": wall_count,
        "shooting_enthalpy_j_kg": str(shell_outlet_enthalpy),
        "outer_bisection_iterations": outer_iterations,
        "tube_face_hashes": [face.face_hash for face in tube_faces],
        "shell_face_hashes": [face.face_hash for face in shell_faces],
        "cells": [cell.rated_cell.model_dump(mode="json") for cell in cells],
        "interval_duties_w": [str(value) for value in interval_duties],
        "total_duty_w": str(q_wall),
        "hot_energy_loss_w": str(hot_loss),
        "cold_energy_gain_w": str(cold_gain),
        "energy_balance_residual_w": str(energy_residual),
        "terminal_boundary_residual_k": str(terminal_residual_t),
        "terminal_boundary_residual_j_kg": str(terminal_residual_h),
        "task031_geometry_hash": EXPECTED_TASK031_GEOMETRY_HASH,
        "task032_result_hash": EXPECTED_TASK032_RESULT_HASH,
        "task166_result_hash": EXPECTED_TASK166_RESULT_HASH,
        "task174_result_hash": EXPECTED_TASK174_RESULT_HASH,
        "task172_local_evaluation_count": stats.task172_local_evaluation_count,
        "task172_numerical_hole_count": stats.task172_numerical_hole_count,
        "task172_numerical_hole_counts_by_code": stats.task172_numerical_hole_counts_by_code,
        "task172_numerical_hole_neighborhoods": hole_neighborhoods,
    }
    rating_hash = canonical_sha256(projection)
    observables = MeshObservables(
        subdivisions_per_interval=subdivisions,
        mesh_level_identity=mesh_id,
        tube_cell_count=tube_count,
        shell_cell_count=shell_count,
        total_numerical_cell_count=tube_count + shell_count,
        wall_interface_count=wall_count,
        total_duty_w=q_wall,
        interval_duty_w=tuple(interval_duties),
        tube_outlet_temperature_k=tube_faces[-1].temperature_k,
        shell_outlet_temperature_k=shell_faces[0].temperature_k,
        wall_inner_min_k=min(all_walls_inner),
        wall_inner_max_k=max(all_walls_inner),
        wall_outer_min_k=min(all_walls_outer),
        wall_outer_max_k=max(all_walls_outer),
        minimum_approach_temperature_k=min_approach,
        hot_energy_loss_w=hot_loss,
        cold_energy_gain_w=cold_gain,
        wall_duty_sum_w=q_wall,
        energy_balance_residual_w=energy_residual,
        terminal_boundary_residual_k=terminal_residual_t,
        terminal_boundary_residual_j_kg=terminal_residual_h,
        duty_roundoff_floor_w=duty_floor,
        wall_temperature_roundoff_floor_k=wall_floor,
        task172_local_evaluation_count=stats.task172_local_evaluation_count,
        task172_numerical_hole_count=stats.task172_numerical_hole_count,
        task172_numerical_hole_counts_by_code=dict(stats.task172_numerical_hole_counts_by_code),
        task172_numerical_hole_neighborhoods=tuple(hole_neighborhoods),
        rating_result_hash=rating_hash,
        local_task172_result_hashes=tuple(cell.rated_cell.task172_result_hash for cell in cells),
    )
    return _MeshRun(
        subdivisions=subdivisions,
        faces_tube=tuple(tube_faces),
        faces_shell=tuple(shell_faces),
        cells=tuple(cells),
        observables=observables,
        mesh_result_hash=rating_hash,
        shooting_enthalpy=shell_outlet_enthalpy,
        bisection_iterations=outer_iterations,
        task172_numerical_hole_neighborhoods=tuple(hole_neighborhoods),
    )


def _outer_trial(
    subdivisions: int,
    enthalpy_j_kg: Decimal,
    provider: PropertyProvider,
    shell_authority: Any,
    iterations: int,
    search_stats: _CellSearchStats | None = None,
) -> _OuterTrial:
    try:
        run = _valid_trajectory(
            subdivisions,
            enthalpy_j_kg,
            provider,
            shell_authority,
            iterations,
            search_stats,
        )
    except _LowSideDomainInfeasible:
        # Search classification only: never return a partial trajectory as a result.
        return _OuterTrial("LOW_SIDE_DOMAIN_INFEASIBLE", enthalpy_j_kg)
    except _Stage3Failure as exc:
        return _OuterTrial("HARD_BLOCKER", enthalpy_j_kg, diagnostics=(exc.code, *exc.diagnostics))
    if (
        run.observables.terminal_boundary_residual_j_kg < 0
        or run.observables.terminal_boundary_residual_k < 0
    ):
        return _OuterTrial(
            "HARD_BLOCKER",
            enthalpy_j_kg,
            diagnostics=("BLOCKED_NEGATIVE_TERMINAL_RESIDUAL",),
        )
    return _OuterTrial("VALID_TRAJECTORY", enthalpy_j_kg, mesh_run=run)


def _terminal_tolerance_pass(run: _MeshRun) -> bool:
    residual_t = run.observables.terminal_boundary_residual_k
    residual_h = run.observables.terminal_boundary_residual_j_kg
    cp = Decimal(run.faces_shell[-1].property_snapshot.cp_j_kg_k)
    h_floor = Decimal(str(math.ulp(float(H_MIN_J_KG))))
    allowed_h = cp * TERMINAL_TOLERANCE_K + h_floor
    return (
        Decimal(0) <= residual_t <= TERMINAL_TOLERANCE_K and Decimal(0) <= residual_h <= allowed_h
    )


def _assert_outer_classification_order(
    seen_low: list[Decimal],
    seen_valid: list[Decimal],
    enthalpy_j_kg: Decimal,
    classification: str,
) -> None:
    if classification == "LOW_SIDE_DOMAIN_INFEASIBLE":
        if any(valid_h < enthalpy_j_kg for valid_h in seen_valid):
            raise _Stage3Failure(
                "BLOCKED_OUTER_FEASIBILITY_CLASSIFICATION_NONMONOTONIC",
                f"infeasible_h={enthalpy_j_kg}",
            )
    elif classification == "VALID_TRAJECTORY":
        if any(low_h > enthalpy_j_kg for low_h in seen_low):
            raise _Stage3Failure(
                "BLOCKED_OUTER_FEASIBILITY_CLASSIFICATION_NONMONOTONIC",
                f"valid_h={enthalpy_j_kg}",
            )
    else:
        raise _Stage3Failure("BLOCKED_OUTER_TRIAL_CLASSIFICATION_INVALID", classification)


def _solve_outer_boundary(
    subdivisions: int,
    provider: PropertyProvider,
    shell_authority: Any,
    search_stats: _CellSearchStats | None = None,
) -> _MeshRun:
    def trial_at(enthalpy: Decimal, iteration: int) -> _OuterTrial:
        if search_stats is None:
            return _outer_trial(subdivisions, enthalpy, provider, shell_authority, iteration)
        return _outer_trial(
            subdivisions, enthalpy, provider, shell_authority, iteration, search_stats
        )

    h_low = H_MIN_J_KG
    h_high = H_MAX_J_KG
    low_trial = trial_at(h_low, 0)
    if low_trial.classification != "LOW_SIDE_DOMAIN_INFEASIBLE":
        if low_trial.classification == "HARD_BLOCKER":
            raise _Stage3Failure(*low_trial.diagnostics)
        raise _Stage3Failure("BLOCKED_OUTER_LOW_ENDPOINT_NOT_INFEASIBLE")
    high_trial = trial_at(h_high, 0)
    if high_trial.classification != "VALID_TRAJECTORY" or high_trial.mesh_run is None:
        if high_trial.classification == "HARD_BLOCKER":
            raise _Stage3Failure(*high_trial.diagnostics)
        raise _Stage3Failure("BLOCKED_OUTER_FEASIBLE_UPPER_ENDPOINT_NOT_FOUND")
    high_run = high_trial.mesh_run
    if (
        high_run.observables.terminal_boundary_residual_j_kg < 0
        or high_run.observables.terminal_boundary_residual_k < 0
    ):
        raise _Stage3Failure("BLOCKED_OUTER_HIGH_ENDPOINT_RESIDUAL_NEGATIVE")
    seen_low = [h_low]
    seen_valid = [h_high]
    if _terminal_tolerance_pass(high_run):
        return high_run

    iterations = 0
    while iterations < MAX_OUTER_BISECTION_ITERATIONS:
        with localcontext() as context:
            context.prec = 80
            h_mid = (h_low + h_high) / Decimal(2)
        if h_mid in (h_low, h_high) or float(h_mid) in (float(h_low), float(h_high)):
            temp_floor = Decimal(
                str(math.ulp(float(high_run.observables.terminal_boundary_residual_k + T_MIN_K)))
            )
            if _terminal_tolerance_pass(high_run):
                return high_run
            if (
                high_run.observables.terminal_boundary_residual_k - temp_floor
                > TERMINAL_TOLERANCE_K
            ):
                raise _Stage3Failure(
                    "BLOCKED_OUTER_BOUNDARY_PRECISION_FLOOR_REACHED",
                    f"terminal_residual_k={high_run.observables.terminal_boundary_residual_k}",
                )
            raise _Stage3Failure(
                "PRECISION_FLOOR_UNRESOLVED",
                "OUTER_BOUNDARY_PRECISION_FLOOR_REACHED",
                f"terminal_residual_k={high_run.observables.terminal_boundary_residual_k}",
            )
        iterations += 1
        trial = trial_at(h_mid, iterations)
        if trial.classification == "HARD_BLOCKER":
            raise _Stage3Failure(*trial.diagnostics)
        if trial.classification == "LOW_SIDE_DOMAIN_INFEASIBLE":
            _assert_outer_classification_order(seen_low, seen_valid, h_mid, trial.classification)
            h_low = h_mid
            seen_low.append(h_mid)
            continue
        if trial.classification != "VALID_TRAJECTORY" or trial.mesh_run is None:
            raise _Stage3Failure("BLOCKED_OUTER_TRIAL_CLASSIFICATION_INVALID")
        _assert_outer_classification_order(seen_low, seen_valid, h_mid, trial.classification)
        if (
            trial.mesh_run.observables.terminal_boundary_residual_j_kg < 0
            or trial.mesh_run.observables.terminal_boundary_residual_k < 0
        ):
            raise _Stage3Failure("BLOCKED_VALID_TRAJECTORY_NEGATIVE_RESIDUAL")
        h_high = h_mid
        seen_valid.append(h_mid)
        high_run = trial.mesh_run
        if _terminal_tolerance_pass(high_run):
            return high_run
    raise _Stage3Failure(
        "BLOCKED_OUTER_BOUNDARY_RESOURCE_EXHAUSTION",
        f"maximum_iterations={MAX_OUTER_BISECTION_ITERATIONS}",
    )


def _classify_difference(
    difference: Decimal, floor: Decimal, threshold: Decimal
) -> Literal["PASS", "FAIL", "PRECISION_FLOOR_UNRESOLVED"]:
    if difference + floor <= threshold:
        return "PASS"
    if difference - floor > threshold:
        return "FAIL"
    return "PRECISION_FLOOR_UNRESOLVED"


def _compare_meshes(coarse: _MeshRun, fine: _MeshRun) -> ConvergenceComparison:
    coarse_obs = coarse.observables
    fine_obs = fine.observables
    if len(coarse_obs.interval_duty_w) != 5 or len(fine_obs.interval_duty_w) != 5:
        raise _Stage3Failure("BLOCKED_MISSING_OBSERVABLE_AUTHORITY")
    interval_differences = tuple(
        abs(fine_value - coarse_value)
        for coarse_value, fine_value in zip(
            coarse_obs.interval_duty_w, fine_obs.interval_duty_w, strict=True
        )
    )
    # Each mesh is first conservatively reduced onto the same five immutable
    # physical intervals; only then is the extensive total compared.
    duty_difference = abs(fine_obs.total_duty_w - coarse_obs.total_duty_w)
    denominator = max(abs(coarse_obs.total_duty_w), abs(fine_obs.total_duty_w))
    if denominator <= MESH_DUTY_ABSOLUTE_THRESHOLD_W:
        duty_metric = duty_difference
        duty_metric_units: Literal["W", "RELATIVE_FRACTION"] = "W"
        duty_metric_threshold = MESH_DUTY_ABSOLUTE_THRESHOLD_W
        duty_precision_floor_metric = (
            coarse_obs.duty_roundoff_floor_w + fine_obs.duty_roundoff_floor_w
        )
    else:
        duty_metric = duty_difference / denominator
        duty_metric_units = "RELATIVE_FRACTION"
        duty_metric_threshold = MESH_DUTY_RELATIVE_THRESHOLD
        duty_precision_floor_metric = (
            coarse_obs.duty_roundoff_floor_w + fine_obs.duty_roundoff_floor_w
        ) / denominator
    duty_floor = coarse_obs.duty_roundoff_floor_w + fine_obs.duty_roundoff_floor_w
    duty_status = _classify_difference(
        duty_metric,
        duty_precision_floor_metric,
        duty_metric_threshold,
    )

    extrema = {
        "T_wall_inner_min": abs(fine_obs.wall_inner_min_k - coarse_obs.wall_inner_min_k),
        "T_wall_inner_max": abs(fine_obs.wall_inner_max_k - coarse_obs.wall_inner_max_k),
        "T_wall_outer_min": abs(fine_obs.wall_outer_min_k - coarse_obs.wall_outer_min_k),
        "T_wall_outer_max": abs(fine_obs.wall_outer_max_k - coarse_obs.wall_outer_max_k),
    }
    wall_floor = (
        coarse_obs.wall_temperature_roundoff_floor_k + fine_obs.wall_temperature_roundoff_floor_k
    )
    wall_statuses = tuple(
        _classify_difference(value, wall_floor, MESH_WALL_EXTREMA_THRESHOLD_K)
        for value in extrema.values()
    )
    if "FAIL" in wall_statuses:
        wall_status: Literal["PASS", "FAIL", "PRECISION_FLOOR_UNRESOLVED"] = "FAIL"
    elif "PRECISION_FLOOR_UNRESOLVED" in wall_statuses:
        wall_status = "PRECISION_FLOOR_UNRESOLVED"
    else:
        wall_status = "PASS"
    statuses = (duty_status, wall_status)
    if "FAIL" in statuses:
        overall: Literal["PASS", "FAIL", "PRECISION_FLOOR_UNRESOLVED"] = "FAIL"
    elif "PRECISION_FLOOR_UNRESOLVED" in statuses:
        overall = "PRECISION_FLOOR_UNRESOLVED"
    else:
        overall = "PASS"
    return ConvergenceComparison(
        coarse_subdivisions=coarse.subdivisions,
        fine_subdivisions=fine.subdivisions,
        interval_duty_differences_w=interval_differences,
        duty_difference_w=duty_difference,
        duty_metric=duty_metric,
        duty_metric_units=duty_metric_units,
        duty_metric_threshold=duty_metric_threshold,
        duty_precision_floor_metric=duty_precision_floor_metric,
        duty_precision_floor_w=duty_floor,
        duty_status=duty_status,
        wall_extrema_differences_k=extrema,
        wall_precision_floor_k=wall_floor,
        wall_status=wall_status,
        overall_status=overall,
    )


def _validate_reference_input(
    request: Task173Request,
) -> tuple[Any, Any, dict[str, Any]]:
    try:
        shell_authority, task174, replay = replay_shell_flow_authority(
            request.shell_flow_replay_bundle
        )
    except NativeReplayError as exc:
        message = str(exc)
        code = message.split(":", maxsplit=1)[0]
        raise _Stage3Failure(code, message) from exc
    if request.task174_result != public_projection(task174):
        raise _Stage3Failure("BLOCKED_SUPERSEDED_OR_UNBOUND_TASK174_RESULT")
    if task174.task166_result_hash != EXPECTED_TASK166_RESULT_HASH:
        raise _Stage3Failure("BLOCKED_SUPERSEDED_TASK166_EFFECTIVE_BINDING")
    effective_task174_json = json.dumps(
        request.task174_result, sort_keys=True, separators=(",", ":")
    )
    if any(identity in effective_task174_json for identity in SUPERSEDED_EFFECTIVE_IDENTITIES):
        raise _Stage3Failure("BLOCKED_SUPERSEDED_STAGE2_IDENTITY_IN_EFFECTIVE_BINDING")
    return shell_authority, task174, replay


def _run_mesh_sequence(
    provider_factory: Callable[[], PropertyProvider], shell_authority: Any
) -> tuple[list[_MeshRun], list[ConvergenceComparison], int | None, int | None]:
    runs: list[_MeshRun] = []
    comparisons: list[ConvergenceComparison] = []
    candidate_index: int | None = None
    headroom_index: int | None = None
    search_summaries: list[dict[str, Any]] = []
    for subdivisions in REVIEWED_MESH_SEQUENCE:
        search_stats = _CellSearchStats()
        try:
            run = _solve_outer_boundary(
                subdivisions,
                provider_factory(),
                shell_authority,
                search_stats,
            )
        except _Stage3Failure as exc:
            search_summaries.append(
                {
                    "subdivisions_per_interval": subdivisions,
                    "task172_local_evaluation_count": search_stats.task172_local_evaluation_count,
                    "task172_numerical_hole_count": search_stats.task172_numerical_hole_count,
                    "task172_numerical_hole_counts_by_code": dict(
                        search_stats.task172_numerical_hole_counts_by_code
                    ),
                }
            )
            raise _Stage3Failure(
                exc.code,
                *exc.diagnostics,
                "task172_numerical_hole_count_by_mesh="
                + json.dumps(search_summaries, sort_keys=True, separators=(",", ":")),
                f"mesh_subdivisions={subdivisions}",
            ) from exc
        search_summaries.append(
            {
                "subdivisions_per_interval": subdivisions,
                "task172_local_evaluation_count": search_stats.task172_local_evaluation_count,
                "task172_numerical_hole_count": search_stats.task172_numerical_hole_count,
                "task172_numerical_hole_counts_by_code": dict(
                    search_stats.task172_numerical_hole_counts_by_code
                ),
            }
        )
        runs.append(run)
        if len(runs) > 1:
            comparison = _compare_meshes(runs[-2], runs[-1])
            comparisons.append(comparison)
        if candidate_index is None and len(comparisons) >= REQUIRED_CONSECUTIVE_PASSING_PAIRS:
            if all(
                item.overall_status == "PASS"
                for item in comparisons[-REQUIRED_CONSECUTIVE_PASSING_PAIRS:]
            ):
                candidate_index = len(runs) - 1
                if candidate_index >= len(REVIEWED_MESH_SEQUENCE) - 1:
                    raise _Stage3Failure("MESH_RESOURCE_EXHAUSTED", "candidate has no headroom")
                continue
        elif (
            candidate_index is not None
            and len(runs) - 1 == candidate_index + REQUIRED_LATER_HEADROOM_LEVELS
        ):
            headroom_comparison = comparisons[-1]
            if headroom_comparison.overall_status == "PASS":
                headroom_index = len(runs) - 1
                return runs, comparisons, candidate_index, headroom_index
            raise _Stage3Failure(
                "MESH_NOT_CONVERGED",
                "earliest two-pair candidate failed its required later headroom comparison",
                f"candidate_n={runs[candidate_index].subdivisions}",
                f"headroom_status={headroom_comparison.overall_status}",
            )
    raise _Stage3Failure(
        "MESH_RESOURCE_EXHAUSTED",
        "MESH_NOT_CONVERGED",
        f"maximum_subdivisions={MAX_SUBDIVISIONS_PER_INTERVAL}",
        f"latest_candidate={LATEST_ACCEPTABLE_CANDIDATE_SUBDIVISIONS}",
    )


def _build_success(
    request: Task173Request,
    request_hash: str,
    shell_authority: Any,
    task174: Any,
    replay: dict[str, Any],
    runs: list[_MeshRun],
    comparisons: list[ConvergenceComparison],
    candidate_index: int,
    headroom_index: int,
) -> Task173SuccessResult:
    accepted = runs[candidate_index]
    headroom = runs[headroom_index]
    deterministic_replay = _solve_outer_boundary(
        accepted.subdivisions, CoolPropProvider(), shell_authority
    )
    same_face_ids = tuple(face.face_id for face in accepted.faces_tube) == tuple(
        face.face_id for face in deterministic_replay.faces_tube
    ) and tuple(face.face_id for face in accepted.faces_shell) == tuple(
        face.face_id for face in deterministic_replay.faces_shell
    )
    same_local_ids = (
        accepted.observables.local_task172_result_hashes
        == deterministic_replay.observables.local_task172_result_hashes
    )
    if (
        accepted.mesh_result_hash != deterministic_replay.mesh_result_hash
        or not same_face_ids
        or not same_local_ids
    ):
        raise _Stage3Failure("BLOCKED_TASK173_DETERMINISM_REPLAY_MISMATCH")
    if not _terminal_tolerance_pass(accepted):
        raise _Stage3Failure("BLOCKED_COUNTERCURRENT_TERMINAL_BOUNDARY_TOLERANCE")
    if accepted.observables.energy_balance_residual_w > max(
        ENERGY_ACCEPTANCE_FLOOR_W,
        accepted.observables.duty_roundoff_floor_w,
    ):
        raise _Stage3Failure("BLOCKED_WHOLE_EXCHANGER_ENERGY_BALANCE")
    mesh_identity = accepted.observables.mesh_level_identity
    projection = Task173SuccessResult(
        schema_version="task173.fixed-geometry-rating-result.v1",
        status="VALIDATED",
        case_revision_id=CASE_REVISION_ID,
        case_mode="RATING_FIXED_GEOMETRY",
        task171_topology_id=TOPOLOGY_ID,
        task171_result_hash=TASK171_RESULT_HASH,
        task171_mesh_identity="ec4a01bbfe81cd6b12ede63c6f4e4aa05372414868cee54a54fb7c98aaffd607",
        physical_ownership_hash=PHYSICAL_OWNERSHIP_HASH,
        task031_geometry_id=shell_authority.task031_geometry.geometry_id,
        task031_geometry_hash=shell_authority.task031_geometry.geometry_hash,
        task031_request_hash=shell_authority.task031_geometry.request_hash,
        task032_result_id=replay["task032_result_id"],
        task032_result_hash=replay["task032_result_hash"],
        task032_request_hash=replay["task032_request_hash"],
        task166_result_id=shell_authority.task166_result.result_id,
        task166_result_hash=shell_authority.task166_result.result_hash,
        task166_request_hash=shell_authority.task166_result.request_hash,
        task172_implementation_version=accepted.cells[
            0
        ].solution.task172_result.implementation_version,
        task174_result_id=task174.result_id,
        task174_result_hash=task174.result_hash,
        property_profile_id=PROFILE_ID,
        reconstruction_authority_id=LOCAL_STATE_RECONSTRUCTION_AUTHORITY_ID,
        reconstruction_authority_hash=LOCAL_STATE_RECONSTRUCTION_AUTHORITY_HASH,
        cell_root_solver_authority_id=CELL_ROOT_SOLVER_AUTHORITY_ID,
        cell_root_solver_authority_hash=CELL_ROOT_SOLVER_AUTHORITY_HASH,
        outer_solver_authority_id=OUTER_BOUNDARY_SOLVER_AUTHORITY_ID,
        outer_solver_authority_hash=OUTER_BOUNDARY_SOLVER_AUTHORITY_HASH,
        outer_low_endpoint_class="LOW_SIDE_DOMAIN_INFEASIBLE",
        outer_high_endpoint_class="VALID_TRAJECTORY",
        invalid_low_endpoint_used_as_physical_result=False,
        production_mesh_profile_authority_id=PRODUCTION_MESH_PROFILE_AUTHORITY_ID,
        production_mesh_identity=mesh_identity,
        accepted_subdivisions_per_interval=accepted.subdivisions,
        accepted_tube_cell_count=accepted.observables.tube_cell_count,
        accepted_shell_cell_count=accepted.observables.shell_cell_count,
        accepted_total_numerical_cell_count=accepted.observables.total_numerical_cell_count,
        accepted_wall_interface_count=accepted.observables.wall_interface_count,
        headroom_subdivisions_per_interval=headroom.subdivisions,
        total_duty_w=accepted.observables.total_duty_w,
        tube_outlet_temperature_k=accepted.observables.tube_outlet_temperature_k,
        shell_outlet_temperature_k=accepted.observables.shell_outlet_temperature_k,
        tube_outlet_pressure_pa=task174.tube_outlet_pressure_pa,
        shell_outlet_pressure_pa=task174.shell_outlet_pressure_pa,
        hot_energy_loss_w=accepted.observables.hot_energy_loss_w,
        cold_energy_gain_w=accepted.observables.cold_energy_gain_w,
        wall_duty_sum_w=accepted.observables.wall_duty_sum_w,
        energy_balance_residual_w=accepted.observables.energy_balance_residual_w,
        energy_balance_pass=True,
        terminal_boundary_residual_k=accepted.observables.terminal_boundary_residual_k,
        terminal_boundary_residual_j_kg=accepted.observables.terminal_boundary_residual_j_kg,
        shell_outlet_shooting_enthalpy_j_kg=accepted.shooting_enthalpy,
        outer_bisection_iterations=accepted.bisection_iterations,
        minimum_approach_temperature_k=accepted.observables.minimum_approach_temperature_k,
        wall_inner_min_k=accepted.observables.wall_inner_min_k,
        wall_inner_max_k=accepted.observables.wall_inner_max_k,
        wall_outer_min_k=accepted.observables.wall_outer_min_k,
        wall_outer_max_k=accepted.observables.wall_outer_max_k,
        inlet_and_outlet_face_states=(
            accepted.faces_tube[0],
            accepted.faces_tube[-1],
            accepted.faces_shell[0],
            accepted.faces_shell[-1],
        ),
        accepted_mesh_face_states=accepted.faces_tube + accepted.faces_shell,
        accepted_mesh_cells=tuple(cell.rated_cell for cell in accepted.cells),
        mesh_levels=tuple(run.observables for run in runs),
        convergence_comparisons=tuple(comparisons),
        duty_convergence_pass=True,
        wall_extrema_convergence_pass=True,
        consecutive_pair_rule_pass=True,
        headroom_rule_pass=True,
        precision_floor_status="RESOLVED_PASS",
        real_case_mesh_admissible=True,
        sizing_execution_status="NOT_APPLICABLE_CURRENT_REFERENCE_CASE",
        legacy_task163_diagnostic_status="NOT_APPLICABLE_TO_V07_VARIABLE_LOCAL_CONSTITUTIVE_MODEL",
        request_hash=request_hash,
        result_hash="pending",
        result_id="pending",
        provenance={
            "case_revision_id": CASE_REVISION_ID,
            "native_shell_flow_replay_status": "PASS",
            "native_shell_flow_bundle_hash": replay["bundle_canonical_hash"],
            "task174_result_hash": task174.result_hash,
            "task172_runtime_version": accepted.cells[
                0
            ].solution.task172_result.implementation_version,
            "outer_solver_authority_hash": OUTER_BOUNDARY_SOLVER_AUTHORITY_HASH,
            "local_reconstruction_authority_hash": LOCAL_STATE_RECONSTRUCTION_AUTHORITY_HASH,
            "cell_root_solver_authority_hash": CELL_ROOT_SOLVER_AUTHORITY_HASH,
            "task172_acceptance_policy_changed": "false",
            "task172_numerical_hole_count_by_mesh": json.dumps(
                {
                    str(run.subdivisions): run.observables.task172_numerical_hole_count
                    for run in runs
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            "same_input_same_result": "true",
            "same_face_state_identities": str(same_face_ids).lower(),
            "same_local_task172_identities": str(same_local_ids).lower(),
            "test_fixture_used_as_authority": "false",
        },
    )
    digest = recompute_task173_result_hash(projection)
    return projection.model_copy(
        update={
            "result_hash": digest,
            "result_id": f"urn:hxforge:task173:{digest}",
        }
    )


def validate_request(
    raw_request: Task173Request | dict[str, Any],
    provider: PropertyProvider | None = None,
) -> Task173Outcome:
    """Validate/replay the effective native inputs and solve the fixed-geometry case."""
    parsed: Task173Request | None = None
    request_hash: str | None = None
    try:
        if type(raw_request) is Task173Request:
            parsed = raw_request
        elif type(raw_request) is dict:
            encoded = json.dumps(raw_request, separators=(",", ":"), ensure_ascii=False)
            parsed = Task173Request.model_validate_json(encoded, strict=True)
        else:
            raise TypeError("expected exact Task173Request or raw dict")
        request_hash = recompute_task173_request_hash(parsed)
        shell_authority, task174, replay = _validate_reference_input(parsed)
        runs, comparisons, candidate_index, headroom_index = _run_mesh_sequence(
            (lambda: provider) if provider is not None else CoolPropProvider,
            shell_authority,
        )
        if candidate_index is None or headroom_index is None:
            raise _Stage3Failure("MESH_NOT_CONVERGED")
        return _build_success(
            parsed,
            request_hash,
            shell_authority,
            task174,
            replay,
            runs,
            comparisons,
            candidate_index,
            headroom_index,
        )
    except ValidationError as exc:
        return _blocked(
            "BLOCKED_TASK173_REQUEST_SCHEMA_INVALID",
            (str(exc),),
            request_hash,
        )
    except NativeReplayError as exc:
        return _blocked(
            "BLOCKED_NATIVE_SHELL_FLOW_REPLAY_MISMATCH",
            (str(exc),),
            request_hash,
        )
    except _Stage3Failure as exc:
        return _blocked(
            exc.code,
            tuple(exc.diagnostics),
            request_hash,
            failed_mesh=(
                next(
                    (
                        int(item.split("=", 1)[1])
                        for item in exc.diagnostics
                        if item.startswith("mesh_subdivisions=")
                    ),
                    None,
                )
            ),
        )
    except Exception as exc:
        return _blocked(
            "BLOCKED_TASK173_UNEXPECTED_RUNTIME_FAILURE",
            (type(exc).__name__, str(exc)),
            request_hash,
        )


__all__ = [
    "CELL_ROOT_SOLVER_AUTHORITY",
    "CELL_ROOT_SOLVER_AUTHORITY_HASH",
    "LOCAL_STATE_RECONSTRUCTION_AUTHORITY",
    "LOCAL_STATE_RECONSTRUCTION_AUTHORITY_HASH",
    "OUTER_BOUNDARY_SOLVER_AUTHORITY",
    "OUTER_BOUNDARY_SOLVER_AUTHORITY_HASH",
    "recompute_task173_request_hash",
    "recompute_task173_result_hash",
    "validate_request",
]
