from __future__ import annotations

from pathlib import Path

import pytest

from tests.ci.shard_manifest import (
    ManifestError,
    discover_test_files,
    load_manifest,
    verify_file_completeness,
)

pytestmark = pytest.mark.pure


def _write_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    (repo / "tests" / "unit").mkdir(parents=True)
    (repo / "tests" / "unit" / "test_a.py").write_text("def test_a(): pass\n")
    (repo / "tests" / "unit" / "test_b.py").write_text("def test_b(): pass\n")
    manifest_path = repo / "tests" / "ci-shards.yaml"
    return repo, manifest_path


def _valid_manifest() -> str:
    return """\
version: "1"
shards:
  - name: unit-a
    job: unit-a
    python: ["3.11", "3.12"]
    files:
      - tests/unit/test_a.py
    timeout: 120
  - name: unit-b
    job: unit-b
    python: ["3.12"]
    files:
      - tests/unit/test_b.py
    timeout: 180
"""


def test_load_manifest_and_verify_bidirectional_completeness(tmp_path: Path) -> None:
    repo, manifest_path = _write_repo(tmp_path)
    manifest_path.write_text(_valid_manifest())

    manifest = load_manifest(manifest_path, repo_root=repo)

    assert manifest.version == "1"
    assert [shard.name for shard in manifest.shards] == ["unit-a", "unit-b"]
    assert [shard.name for shard in manifest.applicable_shards("3.11")] == ["unit-a"]
    assert discover_test_files(repo / "tests", repo_root=repo) == {
        "tests/unit/test_a.py",
        "tests/unit/test_b.py",
    }
    verify_file_completeness(manifest, repo / "tests", repo_root=repo)


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ('version: "2"', "unsupported manifest version"),
        ("timeout: 0", "positive integer"),
        ('python: ["3.13"]', "unsupported versions"),
        ("name: Unit_A", "must match"),
        ("tests/unit/*.py", "globs are prohibited"),
        ("../tests/unit/test_a.py", "non-canonical"),
        ("tests/unit/test_missing.py", "does not exist"),
    ],
)
def test_manifest_rejects_invalid_contract_values(
    tmp_path: Path, replacement: str, message: str
) -> None:
    repo, manifest_path = _write_repo(tmp_path)
    text = _valid_manifest()
    if replacement.startswith("version:"):
        text = text.replace('version: "1"', replacement)
    elif replacement.startswith("timeout:"):
        text = text.replace("timeout: 120", replacement, 1)
    elif replacement.startswith("python:"):
        text = text.replace('python: ["3.11", "3.12"]', replacement)
    elif replacement.startswith("name:"):
        text = text.replace("name: unit-a", replacement)
    else:
        text = text.replace("tests/unit/test_a.py", replacement)
    manifest_path.write_text(text)

    with pytest.raises(ManifestError, match=message):
        load_manifest(manifest_path, repo_root=repo)


def test_manifest_rejects_duplicate_yaml_key(tmp_path: Path) -> None:
    repo, manifest_path = _write_repo(tmp_path)
    manifest_path.write_text(
        _valid_manifest().replace("    job: unit-a\n", "    job: unit-a\n    job: duplicate\n")
    )

    with pytest.raises(ManifestError, match="duplicate YAML mapping key"):
        load_manifest(manifest_path, repo_root=repo)


def test_manifest_rejects_duplicate_file_ownership(tmp_path: Path) -> None:
    repo, manifest_path = _write_repo(tmp_path)
    manifest_path.write_text(
        _valid_manifest().replace("tests/unit/test_b.py", "tests/unit/test_a.py")
    )

    with pytest.raises(ManifestError, match="duplicate shard file ownership"):
        load_manifest(manifest_path, repo_root=repo)


def test_file_completeness_reports_missing_discovered_file(tmp_path: Path) -> None:
    repo, manifest_path = _write_repo(tmp_path)
    unit_b_block = """\
  - name: unit-b
    job: unit-b
    python: ["3.12"]
    files:
      - tests/unit/test_b.py
    timeout: 180
"""
    manifest_path.write_text(_valid_manifest().replace(unit_b_block, ""))
    manifest = load_manifest(manifest_path, repo_root=repo)

    with pytest.raises(ManifestError, match="missing=.*test_b.py"):
        verify_file_completeness(manifest, repo / "tests", repo_root=repo)
