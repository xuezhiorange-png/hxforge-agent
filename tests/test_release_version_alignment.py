"""Current distribution-version alignment contract for the v0.6 release lane."""

from __future__ import annotations

import tomllib
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DISTRIBUTION_VERSION = "0.6.0"


def _pyproject_version() -> str:
    with (REPOSITORY_ROOT / "pyproject.toml").open("rb") as handle:
        document = tomllib.load(handle)
    return document["project"]["version"]


def _uv_lock_project_version() -> str:
    with (REPOSITORY_ROOT / "uv.lock").open("rb") as handle:
        document = tomllib.load(handle)
    package_records = [
        package
        for package in document["package"]
        if package.get("name") == "heat-exchanger-design-agent"
    ]
    assert len(package_records) == 1
    return package_records[0]["version"]


def test_pyproject_current_distribution_version_is_v06() -> None:
    assert _pyproject_version() == EXPECTED_DISTRIBUTION_VERSION


def test_uv_lock_local_project_version_is_v06() -> None:
    assert _uv_lock_project_version() == EXPECTED_DISTRIBUTION_VERSION


def test_current_distribution_metadata_versions_are_aligned() -> None:
    assert _pyproject_version() == _uv_lock_project_version()
