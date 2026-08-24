"""TASK033 public-boundary and import architecture tests."""

from __future__ import annotations

from pathlib import Path

from hexagent.exchangers.shell_tube.shell_side_heat_transfer import __all__

ROOT = Path(__file__).parents[4]


def test_public_boundary_exports_validate_request_only() -> None:
    assert __all__ == ["validate_request"]


def test_allowlisted_production_module_count() -> None:
    package = ROOT / "src/hexagent/exchangers/shell_tube/shell_side_heat_transfer"
    files = sorted(path.name for path in package.glob("*.py"))
    assert len(files) == 13


def test_private_task032_import_is_absent() -> None:
    package = ROOT / "src/hexagent/exchangers/shell_tube/shell_side_heat_transfer"
    source = "\n".join(path.read_text() for path in package.glob("*.py"))
    assert "shell_side_flow_state" not in source


def test_production_correlation_is_single_and_frozen() -> None:
    from hexagent.exchangers.shell_tube.shell_side_heat_transfer.models import CORRELATION_ID

    assert CORRELATION_ID == "TASK033_KERN_KHARAJI_2021_EQ58_NO_WALL_CORRECTION_V1"


def test_manifest_scope_is_separate_from_workflow() -> None:
    manifest = (ROOT / "ci-shard-manifest.yml").read_text()
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "shell_side_heat_transfer" in manifest
    assert "shell_side_heat_transfer" not in workflow
