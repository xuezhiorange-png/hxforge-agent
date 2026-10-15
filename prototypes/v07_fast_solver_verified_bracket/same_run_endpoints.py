"""Same-worker verified bracket endpoints for reuse in narrow bisection."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173


@dataclass(frozen=True)
class SameRunBracketEndpoints:
    run_session_id: str
    authority_id: str
    subdivisions: int
    rating_request_hash: str
    h_low_j_kg: str
    h_high_j_kg: str
    low_trial: t173._OuterTrial
    high_trial: t173._OuterTrial

    def endpoint_receipt_hashes(self) -> dict[str, str | None]:
        low_hash = None
        high_hash = None
        if self.low_trial.mesh_run is not None:
            low_hash = self.low_trial.mesh_run.mesh_result_hash
        if self.high_trial.mesh_run is not None:
            high_hash = self.high_trial.mesh_run.mesh_result_hash
        return {
            "low_endpoint_mesh_hash": low_hash,
            "high_endpoint_mesh_hash": high_hash,
        }

    def assert_matches_solve_context(
        self,
        *,
        run_session_id: str,
        authority_id: str,
        subdivisions: int,
        rating_request_hash: str,
        h_low_j_kg: str,
        h_high_j_kg: str,
    ) -> None:
        if run_session_id != self.run_session_id:
            raise ValueError("run_session_id mismatch for endpoint reuse")
        if authority_id != self.authority_id:
            raise ValueError("authority_id mismatch for endpoint reuse")
        if subdivisions != self.subdivisions:
            raise ValueError("subdivisions mismatch for endpoint reuse")
        if rating_request_hash != self.rating_request_hash:
            raise ValueError("rating_request_hash mismatch for endpoint reuse")
        if Decimal(h_low_j_kg) != Decimal(self.h_low_j_kg):
            raise ValueError("h_low_j_kg mismatch for endpoint reuse")
        if Decimal(h_high_j_kg) != Decimal(self.h_high_j_kg):
            raise ValueError("h_high_j_kg mismatch for endpoint reuse")

    def validate_physics(self) -> None:
        if self.low_trial.classification != "LOW_SIDE_DOMAIN_INFEASIBLE":
            raise ValueError(
                f"low endpoint not LOW_SIDE_DOMAIN_INFEASIBLE: {self.low_trial.classification}"
            )
        if self.low_trial.classification == "HARD_BLOCKER":
            raise ValueError("low endpoint HARD_BLOCKER")
        if self.high_trial.classification == "HARD_BLOCKER":
            raise ValueError("high endpoint HARD_BLOCKER")
        if self.high_trial.classification != "VALID_TRAJECTORY":
            raise ValueError(
                f"high endpoint not VALID_TRAJECTORY: {self.high_trial.classification}"
            )
        if self.high_trial.mesh_run is None:
            raise ValueError("high endpoint missing mesh_run")
        obs = self.high_trial.mesh_run.observables
        if obs.terminal_boundary_residual_j_kg < 0 or obs.terminal_boundary_residual_k < 0:
            raise ValueError("high endpoint negative terminal residual")

    def to_audit_dict(self) -> dict[str, Any]:
        return {
            "run_session_id": self.run_session_id,
            "authority_id": self.authority_id,
            "subdivisions": self.subdivisions,
            "rating_request_hash": self.rating_request_hash,
            "h_low_j_kg": self.h_low_j_kg,
            "h_high_j_kg": self.h_high_j_kg,
            "low_classification": self.low_trial.classification,
            "high_classification": self.high_trial.classification,
            **self.endpoint_receipt_hashes(),
        }
