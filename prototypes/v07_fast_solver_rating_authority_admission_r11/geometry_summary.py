"""Structured geometry identity from validated CandidateRatingRequest."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
    candidate_rating_request_hash,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class GeometrySummary(StrictModel):
    schema_version: str = "task173.experimental-geometry-summary.v1"
    candidate_id: str
    candidate_hash: str
    task171_result_hash: str
    task171_topology_id: str
    task171_mesh_identity: str
    physical_ownership_hash: str
    interval_count: int
    rating_request_hash: str


def geometry_summary_from_request(request: CandidateRatingRequest) -> GeometrySummary:
    t171 = request.task171_result
    if t171.status != "VALIDATED":
        raise ValueError("task171 not VALIDATED")
    context = t173._candidate_context(request)
    return GeometrySummary(
        candidate_id=request.candidate_id,
        candidate_hash=request.candidate_hash,
        task171_result_hash=t171.result_hash,
        task171_topology_id=t171.topology_id,
        task171_mesh_identity=t171.mesh_identity,
        physical_ownership_hash=t171.physical_ownership_hash,
        interval_count=context.interval_count,
        rating_request_hash=candidate_rating_request_hash(request),
    )
