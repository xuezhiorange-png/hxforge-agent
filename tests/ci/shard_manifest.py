"""Strict TASK-015A test-shard manifest parsing and completeness checks."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Final, Literal, cast

import yaml

PythonVersion = Literal["3.11", "3.12"]

_SUPPORTED_PYTHON_VERSIONS: Final = {"3.11", "3.12"}
_TOP_LEVEL_KEYS: Final = {"version", "shards"}
_SHARD_KEYS: Final = {"name", "job", "python", "files", "timeout"}
_TEST_FILE_PATTERNS: Final = ("test_*.py", "*_test.py")
_CANONICAL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_GLOB_CHARACTERS: Final = frozenset("*?[]")


class ManifestError(ValueError):
    """Raised when the shard manifest violates the frozen contract."""


class _UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeyLoader, node: yaml.nodes.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ManifestError(f"duplicate YAML mapping key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


@dataclass(frozen=True, slots=True)
class ShardSpec:
    """One explicit CI shard."""

    name: str
    job: str
    python: tuple[PythonVersion, ...]
    files: tuple[str, ...]
    timeout: int


@dataclass(frozen=True, slots=True)
class ShardManifest:
    """Validated TASK-015A shard manifest."""

    version: str
    shards: tuple[ShardSpec, ...]

    @property
    def file_set(self) -> frozenset[str]:
        return frozenset(file for shard in self.shards for file in shard.files)

    def applicable_shards(self, version: PythonVersion) -> tuple[ShardSpec, ...]:
        return tuple(shard for shard in self.shards if version in shard.python)

    def shard(self, name: str) -> ShardSpec:
        for shard in self.shards:
            if shard.name == name:
                return shard
        raise ManifestError(f"unknown shard: {name!r}")


def _require_exact_keys(value: dict[Any, Any], expected: set[str], context: str) -> None:
    keys = set(value)
    if keys != expected:
        missing = sorted(expected - keys)
        unknown = sorted(str(key) for key in keys - expected)
        raise ManifestError(f"{context} keys mismatch; missing={missing!r}, unknown={unknown!r}")


def _require_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{context} must be a non-empty string")
    if value != value.strip():
        raise ManifestError(f"{context} must not contain leading or trailing whitespace")
    return value


def _require_canonical_name(value: Any, context: str) -> str:
    name = _require_string(value, context)
    if _CANONICAL_NAME.fullmatch(name) is None:
        raise ManifestError(f"{context} must match {_CANONICAL_NAME.pattern!r}, got {name!r}")
    return name


def _is_test_file(path: str) -> bool:
    name = PurePosixPath(path).name
    return any(fnmatch.fnmatch(name, pattern) for pattern in _TEST_FILE_PATTERNS)


def _canonical_test_path(raw: Any, repo_root: Path, test_root: Path) -> str:
    path_string = _require_string(raw, "shard file")
    if "\\" in path_string:
        raise ManifestError(f"shard file must use POSIX separators: {path_string!r}")
    if any(character in path_string for character in _GLOB_CHARACTERS):
        raise ManifestError(f"globs are prohibited in shard files: {path_string!r}")

    pure = PurePosixPath(path_string)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ManifestError(f"non-canonical shard file path: {path_string!r}")
    if not path_string.startswith("tests/"):
        raise ManifestError(f"shard file must be under tests/: {path_string!r}")
    if not _is_test_file(path_string):
        raise ManifestError(f"shard file is not a pytest test file: {path_string!r}")

    candidate = repo_root.joinpath(*pure.parts)
    if not candidate.exists():
        raise ManifestError(f"shard file does not exist: {path_string!r}")
    if not candidate.is_file():
        raise ManifestError(f"shard path is not a file: {path_string!r}")

    resolved = candidate.resolve()
    try:
        resolved.relative_to(test_root.resolve())
    except ValueError as exc:
        raise ManifestError(f"shard file resolves outside the test root: {path_string!r}") from exc

    canonical = candidate.relative_to(repo_root).as_posix()
    if canonical != path_string:
        raise ManifestError(f"shard file path is not canonical: {path_string!r} != {canonical!r}")
    return path_string


def _parse_python_versions(value: Any, context: str) -> tuple[PythonVersion, ...]:
    if not isinstance(value, list) or not value:
        raise ManifestError(f"{context} must be a non-empty list")
    if not all(isinstance(item, str) for item in value):
        raise ManifestError(f"{context} entries must be strings")
    if len(value) != len(set(value)):
        raise ManifestError(f"{context} contains duplicate versions")
    unknown = sorted(set(value) - _SUPPORTED_PYTHON_VERSIONS)
    if unknown:
        raise ManifestError(f"{context} contains unsupported versions: {unknown!r}")
    return tuple(cast(PythonVersion, version) for version in value)


def _parse_timeout(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ManifestError(f"{context} must be a positive integer")
    return value


def load_manifest(path: Path, *, repo_root: Path | None = None) -> ShardManifest:
    """Load and strictly validate a TASK-015A YAML manifest."""

    manifest_path = path.resolve()
    root = (repo_root or manifest_path.parent).resolve()
    test_root = root / "tests"
    if not manifest_path.is_file():
        raise ManifestError(f"manifest does not exist: {manifest_path}")
    if not test_root.is_dir():
        raise ManifestError(f"test root does not exist: {test_root}")

    try:
        raw = yaml.load(manifest_path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except (OSError, yaml.YAMLError) as exc:
        raise ManifestError(f"unable to parse manifest: {manifest_path}") from exc
    if not isinstance(raw, dict):
        raise ManifestError("manifest root must be a mapping")
    _require_exact_keys(raw, _TOP_LEVEL_KEYS, "manifest")

    version = _require_string(raw["version"], "manifest version")
    if version != "1":
        raise ManifestError(f"unsupported manifest version: {version!r}")

    raw_shards = raw["shards"]
    if not isinstance(raw_shards, list) or not raw_shards:
        raise ManifestError("manifest shards must be a non-empty list")

    shard_names: set[str] = set()
    job_names: set[str] = set()
    owned_files: set[str] = set()
    shards: list[ShardSpec] = []
    for index, raw_shard in enumerate(raw_shards):
        context = f"shards[{index}]"
        if not isinstance(raw_shard, dict):
            raise ManifestError(f"{context} must be a mapping")
        _require_exact_keys(raw_shard, _SHARD_KEYS, context)

        name = _require_canonical_name(raw_shard["name"], f"{context}.name")
        job = _require_canonical_name(raw_shard["job"], f"{context}.job")
        if name in shard_names:
            raise ManifestError(f"duplicate shard name: {name!r}")
        if job in job_names:
            raise ManifestError(f"duplicate job name: {job!r}")
        job_names.add(job)
        shard_names.add(name)

        python = _parse_python_versions(raw_shard["python"], f"{context}.python")
        timeout = _parse_timeout(raw_shard["timeout"], f"{context}.timeout")

        raw_files = raw_shard["files"]
        if not isinstance(raw_files, list) or not raw_files:
            raise ManifestError(f"{context}.files must be a non-empty list")
        files: list[str] = []
        for raw_file in raw_files:
            file_path = _canonical_test_path(raw_file, root, test_root)
            if file_path in owned_files:
                raise ManifestError(f"duplicate shard file ownership: {file_path!r}")
            owned_files.add(file_path)
            files.append(file_path)

        shards.append(
            ShardSpec(
                name=name,
                job=job,
                python=python,
                files=tuple(files),
                timeout=timeout,
            )
        )

    return ShardManifest(version=version, shards=tuple(shards))


def discover_test_files(test_root: Path, *, repo_root: Path | None = None) -> frozenset[str]:
    """Discover every canonical pytest file under the test root."""

    root = (repo_root or test_root.parent).resolve()
    resolved_test_root = test_root.resolve()
    if not resolved_test_root.is_dir():
        raise ManifestError(f"test root does not exist: {test_root}")

    discovered: set[str] = set()
    for candidate in test_root.rglob("*.py"):
        if not candidate.is_file() or not _is_test_file(candidate.name):
            continue
        resolved = candidate.resolve()
        try:
            resolved.relative_to(resolved_test_root)
        except ValueError as exc:
            raise ManifestError(
                f"discovered test file resolves outside test root: {candidate}"
            ) from exc
        discovered.add(candidate.relative_to(root).as_posix())
    return frozenset(discovered)


def verify_file_completeness(
    manifest: ShardManifest, test_root: Path, *, repo_root: Path | None = None
) -> None:
    """Prove bidirectional file equality D == M."""

    discovered = discover_test_files(test_root, repo_root=repo_root)
    owned = manifest.file_set
    missing = sorted(discovered - owned)
    stale = sorted(owned - discovered)
    if missing or stale:
        raise ManifestError(f"test file ownership mismatch; missing={missing!r}, stale={stale!r}")
