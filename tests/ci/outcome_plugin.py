"""Structured pytest outcome plugin for TASK-015A.

Captures per-node outcomes via pytest hooks and writes a strict JSON
file that the telemetry runner can cross-validate against JUnit.

P1: Replaces heuristic xfail/xpass detection with authoritative hook data.
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
        self._outcomes: dict[str, OutcomeType] = {}

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(
        self, item: pytest.Item, call: pytest.CallInfo[Any]
    ) -> Any:  # pragma: no cover
        outcome = yield
        report = outcome.get_result()
        if report.when != "call":
            return

        node_id = item.nodeid.replace("\\", "/")
        terminal_style = report.outcome
        outcome_type: OutcomeType = _OUTCOME_MAP.get(terminal_style, "failed")

        # Detect xfail/xpass from markers
        for marker in item.iter_markers():
            if marker.name == "xfail":
                strict = marker.kwargs.get("strict", False)
                if terminal_style == "passed":
                    outcome_type = "xpassed" if strict else "passed"
                elif terminal_style == "skipped":
                    outcome_type = "xfailed"
                break

        self._outcomes[node_id] = outcome_type

    def write_outcomes(self, output_path: Path) -> None:
        """Write outcomes JSON file."""
        sorted_outcomes = dict(sorted(self._outcomes.items()))
        output_path.write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "outcomes": sorted_outcomes,
                    "total": len(sorted_outcomes),
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
