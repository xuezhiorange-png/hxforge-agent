from __future__ import annotations

from pathlib import Path

from hexagent.exchangers.shell_tube.shell_bundle_geometry import (
    DESIGN_CONTRACT_PATH,
    BlockerCode,
    WarningCode,
)


def test_frozen_design_contract_remains_present_and_binding() -> None:
    text = Path(DESIGN_CONTRACT_PATH).read_text(encoding="utf-8")
    assert "TASK-022 — Shell-and-Tube Shell and Bundle Geometry Foundation" in text
    assert "### 18.1 Slice A — deterministic core" in text
    assert "No shell-size selection in the deterministic core" in text
    assert "72. TASK-023 through TASK-039 remain unallocated." in text


def test_closed_message_sets_match_design_tokens() -> None:
    text = Path(DESIGN_CONTRACT_PATH).read_text(encoding="utf-8")
    for item in BlockerCode:
        assert item.value in text
    for item in WarningCode:
        assert item.value in text
