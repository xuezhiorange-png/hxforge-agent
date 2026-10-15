"""Rolling mesh convergence state aligned with production _run_mesh_sequence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

REQUIRED_CONSECUTIVE_PASSING_PAIRS = 2
REQUIRED_LATER_HEADROOM_LEVELS = 1

ComparisonStatus = Literal["PASS", "FAIL"]


@dataclass
class RollingMeshState:
    runs_mesh_n: list[int] = field(default_factory=list)
    comparisons: list[dict[str, Any]] = field(default_factory=list)
    candidate_index: int | None = None
    headroom_index: int | None = None
    ladder_status: Literal[
        "LIVE_RATING_IN_PROGRESS",
        "MESH_COMPARISON_FAIL_CONTINUE",
        "MESH_COMPARISON_PASS",
        "MESH_CANDIDATE_IDENTIFIED",
        "HEADROOM_PASS",
        "LIVE_RATING_EXPERIMENTAL_COMPLETE",
        "BLOCKED",
    ] = "LIVE_RATING_IN_PROGRESS"
    blocked_code: str | None = None
    blocked_diagnostics: tuple[str, ...] = ()

    def record_mesh_accepted(self, mesh_n: int) -> None:
        self.runs_mesh_n.append(mesh_n)

    def record_comparison(self, comparison: dict[str, Any]) -> None:
        self.comparisons.append(comparison)
        self._update_after_comparison()

    def _update_after_comparison(self) -> None:
        if (
            self.candidate_index is None
            and len(self.comparisons) >= REQUIRED_CONSECUTIVE_PASSING_PAIRS
        ):
            recent = self.comparisons[-REQUIRED_CONSECUTIVE_PASSING_PAIRS:]
            if all(item.get("overall_status") == "PASS" for item in recent):
                self.candidate_index = len(self.runs_mesh_n) - 1
                self.ladder_status = "MESH_CANDIDATE_IDENTIFIED"
                return
        if self.comparisons:
            last = self.comparisons[-1]
            recent_pass = len(self.comparisons) >= REQUIRED_CONSECUTIVE_PASSING_PAIRS and all(
                item.get("overall_status") == "PASS"
                for item in self.comparisons[-REQUIRED_CONSECUTIVE_PASSING_PAIRS:]
            )
            if last.get("overall_status") == "PASS" and recent_pass:
                self.ladder_status = "MESH_COMPARISON_PASS"
            else:
                self.ladder_status = "MESH_COMPARISON_FAIL_CONTINUE"

    def terminal_boundary_failed(self) -> None:
        self.ladder_status = "BLOCKED"
        self.blocked_code = "MESH_TERMINAL_BOUNDARY_FAILED"
        self.blocked_diagnostics = ("terminal acceptance required before compare",)

    def budget_exhausted(self) -> None:
        self.ladder_status = "TIMEOUT"
        self.blocked_code = "NUMERICAL_BUDGET_EXHAUSTED"

    def check_headroom_after_new_mesh(self, headroom_mesh_n: int) -> None:
        if self.candidate_index is None:
            return
        candidate_n = self.runs_mesh_n[self.candidate_index]
        expected_headroom_index = self.candidate_index + REQUIRED_LATER_HEADROOM_LEVELS
        if len(self.runs_mesh_n) - 1 != expected_headroom_index:
            return
        if self.comparisons and self.comparisons[-1].get("overall_status") == "PASS":
            self.headroom_index = len(self.runs_mesh_n) - 1
            self.ladder_status = "HEADROOM_PASS"
        else:
            self.ladder_status = "BLOCKED"
            self.blocked_code = "MESH_NOT_CONVERGED"
            self.blocked_diagnostics = (
                f"candidate_n={candidate_n}",
                f"headroom_n={headroom_mesh_n}",
                (
                    "status="
                    f"{self.comparisons[-1].get('overall_status') if self.comparisons else 'NONE'}"
                ),
            )

    def after_comparison_recorded(self, fine_mesh_n: int) -> bool:
        """Apply headroom transition when production index matches. Returns True if blocked."""
        if self.candidate_index is None:
            return False
        expected_headroom_index = self.candidate_index + REQUIRED_LATER_HEADROOM_LEVELS
        if len(self.runs_mesh_n) - 1 == expected_headroom_index:
            self.check_headroom_after_new_mesh(fine_mesh_n)
            return self.ladder_status == "BLOCKED"
        return False
