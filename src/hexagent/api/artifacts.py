"""Typed artifact bundles for rating and sizing runs (TASK-010 Phase 2).

Provides frozen Pydantic models that bind together all inputs, outputs,
provenance, and integrity hashes for a completed run.  Construction
auto-verifies all hash parities via ``model_validator(mode="after")``.

A1: All fields are runtime-typed — no Any in public models.
A4: Sizing artifact bundle verifier with full parity checks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ConfigDict, model_validator

from hexagent.core.canonical import sha256_digest
from hexagent.core.heat_balance import ProviderIdentitySnapshot
from hexagent.domain.models import StrictBaseModel
from hexagent.domain.provenance import ProvenanceGraph
from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.result import (
    RatingRequestIdentity,
    RatingResult,
)
from hexagent.exchangers.double_pipe.solver import SolverParams

if TYPE_CHECKING:
    from hexagent.optimization.models import SizingRequest
    from hexagent.optimization.phase3_builder import (
        OptimizationResult,
        RankedCandidateRecord,
    )
    from hexagent.optimization.phase3_evaluation import (
        CandidateDispositionRecord,
        Phase3EvaluationInput,
    )
    from hexagent.optimization.phase3_verifier import Phase3AuthoritativeArtifacts

# ---------------------------------------------------------------------------
# Rating bundle digest (P0-3)
# ---------------------------------------------------------------------------


def compute_rating_artifact_bundle_digest(bundle: RatingRunArtifacts) -> str:
    """Compute deterministic bundle digest excluding the digest field itself."""
    payload = bundle.model_dump(mode="python")
    # Remove the digest field from the payload
    payload.pop("artifact_bundle_digest", None)
    return sha256_digest(payload)


# ---------------------------------------------------------------------------
# Rating bundle verifier (P0-3)
# ---------------------------------------------------------------------------


def verify_rating_artifact_bundle(bundle: RatingRunArtifacts) -> None:
    """Verify all parities in a rating bundle.

    Checks (in order):
    1. result.verify_hash() — verify the result's own hash
    2. result.verify_provenance() — verify provenance chain
    2b. result.validate_integrity() — Pydantic structural validation
    3. geometry_snapshot is non-None and ALL 9 fields match request_identity geometry
    4. solver_settings fields match execution authority (tolerance, max_iterations)
    5. provider_identity 6-field binding matches result.provider_identity
    6. canonical_request_snapshot is non-None and digest is valid
    7. Recompute provenance graph hash and compare with result.provenance_digest
    8. artifact_bundle_digest recompute
    9. result request_identity parity
    10. result provider_identity parity
    11. provenance object parity
    """
    # -- 1. result hash verification ------------------------------------------
    if not bundle.result.verify_hash():
        raise ValueError("result hash verification failed")

    # -- 2. result provenance verification ------------------------------------
    if not bundle.result.verify_provenance():
        raise ValueError("result provenance verification failed")

    # -- 2b. validate_integrity — Pydantic structural validation ---------------
    valid, issues = bundle.result.validate_integrity()
    if not valid:
        raise ValueError(f"RatingResult.validate_integrity() failed: {'; '.join(issues)}")

    # -- 3. geometry_snapshot non-None and fields match request_identity ------
    if bundle.geometry_snapshot is None:
        raise ValueError("geometry_snapshot must not be None")
    geom = bundle.geometry_snapshot
    ri_geom = bundle.request_identity.geometry
    _GEOM_FIELDS = (
        "inner_tube_inner_diameter_m",
        "inner_tube_outer_diameter_m",
        "outer_pipe_inner_diameter_m",
        "effective_length_m",
        "wall_thermal_conductivity_w_m_k",
        "inner_surface_roughness_m",
        "annulus_surface_roughness_m",
        "inner_fouling_resistance_m2k_w",
        "outer_fouling_resistance_m2k_w",
    )
    for _gf in _GEOM_FIELDS:
        _geom_val = getattr(geom, _gf, None)
        _ri_val = ri_geom.get(_gf)
        if _ri_val is not None and _geom_val != _ri_val:
            raise ValueError(f"geometry_snapshot.{_gf} mismatch with request_identity.geometry")

    # -- 4. solver_settings fields match execution authority ------------------
    if bundle.solver_settings is None:
        raise ValueError("solver_settings must not be None")
    sp = bundle.solver_settings
    ri = bundle.request_identity
    if sp.absolute_residual_w != ri.solver_absolute_residual_w:
        raise ValueError("solver_settings.absolute_residual_w mismatch")
    if sp.relative_residual_fraction != ri.solver_relative_residual_fraction:
        raise ValueError("solver_settings.relative_residual_fraction mismatch")
    if sp.bracket_temperature_tolerance_k != ri.solver_bracket_temperature_tolerance_k:
        raise ValueError("solver_settings.bracket_temperature_tolerance_k mismatch")
    if sp.max_iterations != ri.solver_max_iterations:
        raise ValueError("solver_settings.max_iterations mismatch")

    # -- 5. provider_identity 6-field binding ---------------------------------
    if bundle.provider_identity != bundle.result.provider_identity:
        raise ValueError("provider_identity mismatch with result.provider_identity")

    # -- 6. canonical_request_snapshot non-None and digest valid ---------------
    if bundle.canonical_request_snapshot is None:
        raise ValueError("canonical_request_snapshot must not be None")
    from hexagent.api.canonical_request import compute_api_request_digest

    crs_digest = compute_api_request_digest(bundle.canonical_request_snapshot)
    if not crs_digest:
        raise ValueError("canonical_request_snapshot produced empty digest")

    # -- 7. Recompute provenance graph hash and compare -----------------------
    from hexagent.domain.provenance import ProvenanceNodeType

    _core_nodes = [
        n for n in bundle.provenance_graph.nodes if n.node_type != ProvenanceNodeType.RESULT
    ]
    _core_node_ids = {n.node_id for n in _core_nodes}
    _core_edges = [e for e in bundle.provenance_graph.edges if e.target_id in _core_node_ids]
    from hexagent.domain.provenance import ProvenanceGraph as _PG

    _core_graph = _PG(nodes=tuple(_core_nodes), edges=tuple(_core_edges))
    from hexagent.exchangers.double_pipe.result import _provenance_graph_digest

    computed_core_hash = _provenance_graph_digest(_core_graph)
    if (
        bundle.result.core_provenance_digest
        and computed_core_hash != bundle.result.core_provenance_digest
    ):
        raise ValueError(
            f"provenance_graph hash mismatch: computed {computed_core_hash!r}, "
            f"result.core_provenance_digest {bundle.result.core_provenance_digest!r}"
        )

    # -- 8. bundle digest recompute -------------------------------------------
    expected_digest = compute_rating_artifact_bundle_digest(bundle)
    if bundle.artifact_bundle_digest != expected_digest:
        raise ValueError("artifact_bundle_digest mismatch")

    # -- 9. result request identity parity ------------------------------------
    if bundle.result.request_identity != bundle.request_identity:
        raise ValueError("result request_identity mismatch")

    # -- 10. result provider identity parity ----------------------------------
    if bundle.result.provider_identity != bundle.provider_identity:
        raise ValueError("result provider_identity mismatch")

    # -- 11. provenance object parity -----------------------------------------
    if bundle.result.provenance_graph != bundle.provenance_graph:
        raise ValueError("result provenance_graph mismatch")


# ---------------------------------------------------------------------------
# Rating bundle (P0-3 — precise frozen contract)
# ---------------------------------------------------------------------------


class RatingRunArtifacts(StrictBaseModel):
    """Frozen contract RatingRunArtifacts."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    canonical_request_snapshot: dict[str, object]
    request_identity: RatingRequestIdentity
    geometry_snapshot: DoublePipeGeometry
    solver_settings: SolverParams
    provider_identity: ProviderIdentitySnapshot
    result: RatingResult
    provenance_graph: ProvenanceGraph
    artifact_bundle_digest: str

    # -- auto-verify on construction ----------------------------------------

    @model_validator(mode="after")
    def _verify_bundle(self) -> RatingRunArtifacts:
        verify_rating_artifact_bundle(self)
        return self


# ---------------------------------------------------------------------------
# Sizing bundle hash helper
# ---------------------------------------------------------------------------


def compute_sizing_artifact_bundle_digest(
    bundle: SizingRunArtifacts,
) -> str:
    """Compute deterministic bundle digest excluding the digest field itself.

    Serializes all fields except ``artifact_bundle_digest`` to a canonical
    Python representation and computes sha256.
    """
    payload = bundle.model_dump(mode="python")
    payload.pop("artifact_bundle_digest", None)
    return sha256_digest(payload)


# ---------------------------------------------------------------------------
# Sizing bundle verifier (A4)
# ---------------------------------------------------------------------------


def verify_sizing_artifact_bundle(artifacts: SizingRunArtifacts) -> None:
    """Verify all parities in a sizing artifact bundle (A4).

    Full verification chain:
    1. artifact_bundle_digest recompute
    2. provenance_digest == provenance_graph.compute_hash()
    3. SizingRequest structural validation via model_validate
    4. Evaluation input authority validation (digest recomputation)
    5. MaterializationResult authority validation (verify_or_raise)
    6. Phase3AuthoritativeArtifacts non-None (full verification in step 12)
    7. Ranking: ranked_records are sorted by rank
    8. Ranked count matches feasible_candidate_count
    9. Top-N: top_n_records is exact prefix
    10. Top-N count matches min(requested, feasible)
    11. Disposition count matches total_candidate_count
    12. Call verify_phase3_result_semantics_or_raise()
    """
    # 1. Bundle digest recompute
    expected_digest = compute_sizing_artifact_bundle_digest(artifacts)
    if artifacts.artifact_bundle_digest != expected_digest:
        raise ValueError(
            f"artifact_bundle_digest mismatch: bundle has "
            f"{artifacts.artifact_bundle_digest!r}, recomputed {expected_digest!r}"
        )

    opt = artifacts.optimization_result

    # 2. provenance_digest parity (C2: single provenance digest authority)
    computed_prov = artifacts.provenance_graph.compute_hash()
    if opt.provenance_digest != computed_prov:
        raise ValueError(
            f"provenance_digest mismatch: result has {opt.provenance_digest!r}, "
            f"provenance_graph.compute_hash() returned {computed_prov!r}"
        )

    # 3. SizingRequest structural validation
    if artifacts.sizing_request is None:
        raise ValueError("sizing_request must not be None")
    # Validate via the frozen Pydantic model
    from hexagent.optimization.models import SizingRequest as _SR

    try:
        _SR.model_validate(artifacts.sizing_request.model_dump(mode="python"))
    except Exception as exc:
        raise ValueError(f"SizingRequest.model_validate() failed: {exc}") from exc
    if not artifacts.sizing_request.catalogs:
        raise ValueError("sizing_request.catalogs must be non-empty")

    # 4. Evaluation input authority validation
    if artifacts.evaluation_input is None:
        raise ValueError("evaluation_input must not be None")
    # Verify evaluation_input_digest by recomputing the canonical payload hash
    from hexagent.optimization.phase3_evaluation import _evaluation_input_payload

    ei_expected_digest = sha256_digest(_evaluation_input_payload(artifacts.evaluation_input))
    if artifacts.evaluation_input.evaluation_input_digest != ei_expected_digest:
        raise ValueError(
            f"evaluation_input.evaluation_input_digest mismatch: "
            f"stored {artifacts.evaluation_input.evaluation_input_digest!r} "
            f"!= recomputed {ei_expected_digest!r}"
        )

    # 5. Materialization result authority validation
    if artifacts.evaluation_input.materialization_result is None:
        raise ValueError("evaluation_input.materialization_result must not be None")
    try:
        artifacts.evaluation_input.materialization_result.verify_or_raise()
    except Exception as exc:
        raise ValueError(f"materialization_result.verify_or_raise() failed: {exc}") from exc

    # 6. Phase3 authoritative artifacts — verify via the frozen authority verifier
    if artifacts.phase3_authoritative_artifacts is None:
        raise ValueError("phase3_authoritative_artifacts must not be None")
    # Note: Phase3AuthoritativeArtifacts does not have verify_or_raise;
    # full verification is done by verify_phase3_result_semantics_or_raise in step 12.

    # 7. Ranking: ranked_records are sorted by rank
    for i in range(len(artifacts.ranked_records)):
        if artifacts.ranked_records[i].rank != i + 1:
            raise ValueError(
                f"ranked_records[{i}].rank = {artifacts.ranked_records[i].rank}, expected {i + 1}"
            )

    # 8. Ranked count matches feasible
    if len(artifacts.ranked_records) != opt.feasible_candidate_count:
        raise ValueError(
            f"ranked_records count {len(artifacts.ranked_records)} != "
            f"feasible_candidate_count {opt.feasible_candidate_count}"
        )

    # 9. Top-N is prefix of ranked records
    if artifacts.top_n_records != artifacts.ranked_records[: len(artifacts.top_n_records)]:
        raise ValueError("top_n_records is not a prefix of ranked_records")

    # 10. Top-N count matches min(requested, feasible)
    expected_top_n = min(opt.requested_top_n, opt.feasible_candidate_count)
    if len(artifacts.top_n_records) != expected_top_n:
        raise ValueError(
            f"top_n_records count {len(artifacts.top_n_records)} != expected {expected_top_n}"
        )

    # 11. Disposition count matches total
    if len(artifacts.dispositions) != opt.total_candidate_count:
        raise ValueError(
            f"dispositions count {len(artifacts.dispositions)} != "
            f"total_candidate_count {opt.total_candidate_count}"
        )

    # 12. Call verify_phase3_result_semantics_or_raise()
    from hexagent.optimization.phase3_verifier import (
        verify_phase3_result_semantics_or_raise,
    )

    verify_phase3_result_semantics_or_raise(
        result=opt,
        graph=artifacts.provenance_graph,
        evaluation_input=artifacts.evaluation_input,
        artifacts=artifacts.phase3_authoritative_artifacts,
        dispositions=artifacts.dispositions,
        ranked_records=artifacts.ranked_records,
    )


# ---------------------------------------------------------------------------
# Sizing bundle (A1 — fully typed, no Any at runtime after model_rebuild)
# ---------------------------------------------------------------------------


class SizingRunArtifacts(StrictBaseModel):
    """Typed artifact bundle for sizing runs (A1).

    All fields use forward references resolved at import time via
    model_rebuild.  ``from __future__ import annotations`` turns all
    annotations into strings so Python never tries to resolve them
    eagerly; Pydantic resolves them when the model is first used.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    canonical_request_snapshot: dict[str, object]
    sizing_request: SizingRequest
    evaluation_input: Phase3EvaluationInput
    phase3_authoritative_artifacts: Phase3AuthoritativeArtifacts
    dispositions: tuple[CandidateDispositionRecord, ...]
    ranked_records: tuple[RankedCandidateRecord, ...]
    top_n_records: tuple[RankedCandidateRecord, ...]
    optimization_result: OptimizationResult
    provenance_graph: ProvenanceGraph
    artifact_bundle_digest: str

    # -- auto-verify on construction ----------------------------------------

    @model_validator(mode="after")
    def _verify_bundle(self) -> SizingRunArtifacts:
        verify_sizing_artifact_bundle(self)
        return self


# ---------------------------------------------------------------------------
# Rebuild models to resolve forward references at runtime
# ---------------------------------------------------------------------------


def _rebuild_sizing_models() -> None:
    """Resolve forward references in SizingRunArtifacts."""
    try:
        from hexagent.optimization.models import SizingRequest as _SR
        from hexagent.optimization.phase3_builder import (
            OptimizationResult as _OR,
        )
        from hexagent.optimization.phase3_builder import (
            RankedCandidateRecord as _RCR,
        )
        from hexagent.optimization.phase3_evaluation import (
            CandidateDispositionRecord as _CDR,
        )
        from hexagent.optimization.phase3_evaluation import (
            Phase3EvaluationInput as _PEI,
        )
        from hexagent.optimization.phase3_verifier import (
            Phase3AuthoritativeArtifacts as _PAA,
        )

        SizingRunArtifacts.model_rebuild(
            _types_namespace={
                "SizingRequest": _SR,
                "Phase3EvaluationInput": _PEI,
                "Phase3AuthoritativeArtifacts": _PAA,
                "CandidateDispositionRecord": _CDR,
                "RankedCandidateRecord": _RCR,
                "OptimizationResult": _OR,
            },
        )
    except ImportError:
        pass  # optimization module not available during minimal imports


_rebuild_sizing_models()

__all__ = [
    "RatingRunArtifacts",
    "SizingRunArtifacts",
    "compute_rating_artifact_bundle_digest",
    "compute_sizing_artifact_bundle_digest",
    "verify_rating_artifact_bundle",
    "verify_sizing_artifact_bundle",
]
