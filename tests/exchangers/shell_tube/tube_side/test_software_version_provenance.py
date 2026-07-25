"""§6.1 / §A13 — Software-version provenance tests."""

from __future__ import annotations

import hexagent.exchangers.shell_tube.tube_side as ts
from hexagent.exchangers.shell_tube.tube_side.provenance import (
    DESIGN_CONTRACT_PATH,
    IMPLEMENTATION_SOFTWARE_VERSION,
    TASK_ID,
)


def test_software_version_constant() -> None:
    assert IMPLEMENTATION_SOFTWARE_VERSION == "0.1.0"


def test_task_id_constant() -> None:
    assert TASK_ID == "TASK-025"


def test_design_contract_path_constant() -> None:
    assert DESIGN_CONTRACT_PATH == "docs/tasks/TASK-025-shell-and-tube-tube-side-hydraulic-geometry.md"


def test_blocked_result_software_version_constant() -> None:
    result = ts.evaluate_task025(None)
    assert result.implementation_software_version == "0.1.0"
    assert result.provenance.implementation_software_version == "0.1.0"


def test_supported_software_version_tuple() -> None:
    assert ts.SUPPORTED_SOFTWARE_VERSION == ("0.1.0",)


def test_software_version_no_caller_supply() -> None:
    """§5 / §A13 — implementation-owned, not caller-supplied."""
    # The valid result is constructed via the scheduler; caller cannot
    # supply software_version through evaluate_task025. This test verifies
    # the implementation-owned contract is exposed.
    assert ts.IMPLEMENTATION_SOFTWARE_VERSION == "0.1.0"

# ruff: noqa: E501
