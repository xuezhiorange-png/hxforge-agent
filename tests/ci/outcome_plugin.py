"""Structured pytest outcome plugin for TASK-015A.

Captures per-node outcomes via pytest hooks and writes a strict JSON
file that the telemetry runner can cross-validate against JUnit.

Phase-aware outcome semantics (priority-based, NOT last-phase-wins):
- setup error/failure → final failed (teardown pass does NOT override)
- setup skip/xfailed → preserved (call/teardown don't override unless fail)
- call outcome → normal final outcome (unless teardown fails)
- teardown pass → does NOT override any prior outcome
- teardown fail/error → forces final failed
- Each collected node produces exactly one final outcome.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final, Literal

import pytest

OutcomeType = Literal["passed", "failed", "skipped", "xfailed", "xpassed"]

_OUTCOME_MAP: Final[dict[str, OutcomeType]] = {
    "passed": "passed",
    "failed": "failed",
    "error": "failed",
    "skipped": "skipped",
}


class OutcomeCollector:
    """Collects structured outcomes from pytest hooks."""

    def __init__(self) -> None:
        # node_id → per-phase outcomes (setup, call, teardown)
        self._phase_outcomes: dict[str, dict[str, OutcomeType | None]] = {}
        # node_id → final resolved outcome
        self._outcomes: dict[str, OutcomeType] = {}
        # Set of node_ids that completed collection
        self._collection_complete: set[str] = set()

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(
        self, item: pytest.Item, call: pytest.CallInfo[Any]
    ) -> Any:  # pragma: no cover
        outcome = yield
        report = outcome.get_result()

        node_id = item.nodeid.replace("\\", "/")

        # Initialize phase tracking for this node
        if node_id not in self._phase_outcomes:
            self._phase_outcomes[node_id] = {
                "setup": None,
                "call": None,
                "teardown": None,
            }

        phase = report.when  # "setup", "call", or "teardown"
        if phase not in ("setup", "call", "teardown"):
            return

        # Determine outcome for this phase
        phase_outcome = self._determine_phase_outcome(report, item)
        if phase_outcome is not None:
            self._phase_outcomes[node_id][phase] = phase_outcome

        # Final outcome via priority-based state machine
        self._update_final_outcome(node_id)

    def _determine_phase_outcome(
        self, report: pytest.TestReport, item: pytest.Item
    ) -> OutcomeType | None:
        """Determine the outcome for a single test phase."""
        terminal_style = report.outcome

        if terminal_style == "skipped":
            return "xfailed" if getattr(report, "wasxfail", None) is not None else "skipped"

        if terminal_style == "passed":
            return "xpassed" if getattr(report, "wasxfail", None) is not None else "passed"

        if terminal_style in ("failed", "error"):
            return "failed"

        # Fallback: map via the static outcome map
        return _OUTCOME_MAP.get(terminal_style, "failed")

    def _update_final_outcome(self, node_id: str) -> None:
        """Update the final outcome using priority-based semantics.

        Priority rules (NOT last-phase-wins):
        1. setup failed/error → final failed (only teardown fail can re-affirm)
        2. setup skip/xfailed → preserved unless call/teardown fails
        3. call outcome → normal final (passed/failed/skipped/xfailed/xpassed)
        4. teardown pass → does NOT override anything
        5. teardown failed/error → forces final failed
        """
        phases = self._phase_outcomes.get(node_id, {})
        setup = phases.get("setup")
        call = phases.get("call")
        teardown = phases.get("teardown")

        final: OutcomeType | None = None

        # Phase 1: setup outcome establishes base
        if setup is not None:
            final = setup

        # Phase 2: call outcome overrides setup (except setup-fail is sticky)
        if call is not None:
            if setup == "failed":
                # setup failed → call doesn't override, stays failed
                pass
            else:
                final = call

        # Phase 3: teardown fail/error forces failed; teardown pass is ignored
        if teardown == "failed":
            final = "failed"
        # teardown "passed"/"skipped"/etc. → do NOT override

        if final is not None:
            self._outcomes[node_id] = final

    @pytest.hookimpl(hookwrapper=True)
    def pytest_collection_modifyitems(
        self, session: pytest.Session, config: pytest.Config, items: list[pytest.Item]
    ) -> Any:  # pragma: no cover
        """Track collection completion."""
        yield  # noqa: F841
        # After collection finishes, mark all collected item IDs as complete
        for item in items:
            node_id = item.nodeid.replace("\\", "/")
            self._collection_complete.add(node_id)

    def write_outcomes(self, output_path: Path) -> None:
        """Write outcomes JSON file."""
        sorted_outcomes = dict(sorted(self._outcomes.items()))
        output_path.write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "outcomes": sorted_outcomes,
                    "total": len(sorted_outcomes),
                    "collection_complete": sorted(self._collection_complete),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    @property
    def outcomes(self) -> dict[str, OutcomeType]:
        return dict(self._outcomes)

    @property
    def collection_complete(self) -> set[str]:
        return set(self._collection_complete)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:  # pragma: no cover
    output = session.config.getoption("--hx-outcome-output", default="")
    if not output:
        return
    collector = session.config._hx_outcome_collector  # type: ignore[attr-defined]
    collector.write_outcomes(Path(output))


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("hxforge-outcomes")
    group.addoption(
        "--hx-outcome-output",
        default="",
        help="Path for structured outcome JSON output.",
    )


def pytest_configure(config: pytest.Config) -> None:
    collector = OutcomeCollector()
    config._hx_outcome_collector = collector  # type: ignore[attr-defined]
    config.pluginmanager.register(collector, "hxforge-outcome-collector")
