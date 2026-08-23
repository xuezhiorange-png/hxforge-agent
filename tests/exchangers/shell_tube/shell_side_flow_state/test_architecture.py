"""Architecture and CI-shard isolation contracts."""

from pathlib import Path

from hexagent.exchangers.shell_tube.shell_side_flow_state import validation


def test_t032_arc_001_no_task033_task034_runtime_dependency() -> None:
    package = (
        Path(__file__).parents[4]
        / "src"
        / "hexagent"
        / "exchangers"
        / "shell_tube"
        / "shell_side_flow_state"
    )
    forbidden = ("task033", "task034", "TASK033", "TASK034")
    for path in package.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert not any(token in source for token in forbidden), path
    assert validation.__name__.endswith("validation")


def test_t032_arc_002_ci_manifest_12_module_paths_excludes_package_marker() -> None:
    manifest = Path(__file__).parents[4] / "ci-shard-manifest.yml"
    source = manifest.read_text(encoding="utf-8")
    task032_paths = [
        line.strip()
        for line in source.splitlines()
        if "tests/exchangers/shell_tube/shell_side_flow_state/" in line
    ]
    assert len(task032_paths) == 12
    assert not any(path.endswith("/__init__.py") for path in task032_paths)
