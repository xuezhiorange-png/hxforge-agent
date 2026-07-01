"""Structured pytest collection inventory for TASK-015A.

The plugin is intentionally self-contained and uses only the standard library plus
pytest so that collection authority does not depend on application imports.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Final, Literal, TypedDict, cast

import pytest

CollectionScope = Literal["global", "shard"]
ZeroNodeReason = Literal[
    "conditional-definition",
    "module-collection-skip",
    "hook-deselection",
    "unsupported-version",
]

_ALLOWED_SCOPES: Final = {"global", "shard"}
_ALLOWED_TRACKS: Final = {"pr-head", "merge-ref", "main", "nightly"}
_ALLOWED_ZERO_NODE_REASONS: Final = {
    "conditional-definition",
    "module-collection-skip",
    "hook-deselection",
    "unsupported-version",
}


class ZeroNodeMetadata(TypedDict):
    zero_node_reason: ZeroNodeReason
    reason_authority: str
    evidence: str


class FileRecord(TypedDict):
    file: str
    node_count: int
    zero_node_reason: ZeroNodeReason | None
    reason_authority: str | None
    evidence: str | None


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("hxforge-task-015a")
    group.addoption(
        "--hx-collection-scope",
        choices=sorted(_ALLOWED_SCOPES),
        help="Collection inventory scope: global or shard.",
    )
    group.addoption(
        "--hx-shard",
        help="Canonical manifest shard name; required only for shard collection.",
    )
    group.addoption(
        "--hx-node-output",
        help="Path for the structured node-inventory JSON output.",
    )
    group.addoption(
        "--hx-zero-node-metadata",
        help=(
            "Optional JSON mapping of test file paths to approved zero-node metadata. "
            "Required when an explicitly targeted test file collects zero nodes."
        ),
    )


def _normalize_path(value: str | Path) -> str:
    path = Path(value)
    try:
        path = path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        path = Path(value)
    return path.as_posix().removeprefix("./")


def _required_option(config: pytest.Config, name: str) -> str:
    value = config.getoption(name)
    if not isinstance(value, str) or not value.strip():
        raise pytest.UsageError(f"TASK-015A requires {name}")
    return value.strip()


def _required_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise pytest.UsageError(f"TASK-015A requires environment variable {name}")
    return value


def _parse_positive_int_environment(name: str) -> int:
    raw = _required_environment(name)
    try:
        value = int(raw)
    except ValueError as exc:
        raise pytest.UsageError(f"{name} must be an integer, got {raw!r}") from exc
    if value <= 0:
        raise pytest.UsageError(f"{name} must be positive, got {value}")
    return value


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        raise pytest.UsageError(f"required fingerprint input is missing: {path.as_posix()}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _plugin_versions(config: pytest.Config) -> dict[str, str]:
    versions: dict[str, str] = {}
    for _plugin, distribution in config.pluginmanager.list_plugin_distinfo():
        name = getattr(distribution, "project_name", None)
        version = getattr(distribution, "version", None)
        if isinstance(name, str) and isinstance(version, str):
            previous = versions.setdefault(name, version)
            if previous != version:
                raise pytest.UsageError(
                    f"conflicting versions reported for pytest plugin {name!r}: "
                    f"{previous!r} versus {version!r}"
                )
    return dict(sorted(versions.items()))


def _behavior_fingerprint(config: pytest.Config) -> str:
    locale = os.environ.get("LC_ALL") or os.environ.get("LANG") or ""
    payload: dict[str, Any] = {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "pytest_version": pytest.__version__,
        "plugin_versions": _plugin_versions(config),
        "lock_digest": _sha256_file(Path("uv.lock")),
        "pyproject_digest": _sha256_file(Path("pyproject.toml")),
        "working_directory": _normalize_path(Path.cwd()),
        "python_hash_seed": _required_environment("PYTHONHASHSEED"),
        "timezone": _required_environment("TZ"),
        "locale": locale,
        "pytest_addopts": os.environ.get("PYTEST_ADDOPTS", ""),
    }
    if not locale:
        raise pytest.UsageError("TASK-015A requires LC_ALL or LANG")
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _python_file_patterns(config: pytest.Config) -> tuple[str, ...]:
    patterns = config.getini("python_files")
    if not isinstance(patterns, list) or not all(isinstance(item, str) for item in patterns):
        raise pytest.UsageError("pytest python_files must be a list of strings")
    return tuple(patterns)


def _discover_test_files(root: Path, patterns: tuple[str, ...]) -> list[str]:
    if not root.is_dir():
        raise pytest.UsageError(f"global collection root must be a directory: {root}")
    files = {
        _normalize_path(path)
        for path in root.rglob("*.py")
        if path.is_file() and any(fnmatch.fnmatch(path.name, pattern) for pattern in patterns)
    }
    return sorted(files)


def _validate_collection_targets(
    config: pytest.Config, scope: CollectionScope, shard: str | None
) -> list[str]:
    args = [_normalize_path(arg) for arg in config.args]
    if scope == "global":
        if shard is not None:
            raise pytest.UsageError("global collection requires --hx-shard to be absent")
        if args != ["tests"]:
            raise pytest.UsageError(
                "global collection must target exactly tests/ and no explicit subset; "
                f"received {args!r}"
            )
        return _discover_test_files(Path("tests"), _python_file_patterns(config))

    if not shard:
        raise pytest.UsageError("shard collection requires a non-empty --hx-shard")
    if not args:
        raise pytest.UsageError("shard collection requires explicit test files")
    if "tests" in args:
        raise pytest.UsageError("shard collection must not target the whole tests/ directory")

    explicit_files: list[str] = []
    for raw, normalized in zip(config.args, args, strict=True):
        path = Path(raw)
        if not path.is_file():
            raise pytest.UsageError(f"shard target must be an existing file: {raw}")
        if path.suffix != ".py":
            raise pytest.UsageError(f"shard target must be a Python test file: {raw}")
        if not normalized.startswith("tests/"):
            raise pytest.UsageError(f"shard target must remain under tests/: {raw}")
        explicit_files.append(normalized)
    if len(explicit_files) != len(set(explicit_files)):
        raise pytest.UsageError("duplicate explicit test files are prohibited")
    return sorted(explicit_files)


def _load_zero_node_metadata(config: pytest.Config) -> dict[str, ZeroNodeMetadata]:
    value = config.getoption("--hx-zero-node-metadata")
    if value in (None, ""):
        return {}
    if not isinstance(value, str):
        raise pytest.UsageError("--hx-zero-node-metadata must be a path")
    path = Path(value)
    if not path.is_file():
        raise pytest.UsageError(f"zero-node metadata file does not exist: {value}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise pytest.UsageError(f"invalid zero-node metadata file: {value}") from exc
    if not isinstance(raw, dict):
        raise pytest.UsageError("zero-node metadata root must be a JSON object")

    metadata: dict[str, ZeroNodeMetadata] = {}
    for raw_file, raw_record in raw.items():
        if not isinstance(raw_file, str) or not isinstance(raw_record, dict):
            raise pytest.UsageError("zero-node metadata entries must map file strings to objects")
        expected_keys = {"zero_node_reason", "reason_authority", "evidence"}
        if set(raw_record) != expected_keys:
            raise pytest.UsageError(
                f"zero-node metadata for {raw_file!r} must contain exactly {expected_keys!r}"
            )
        reason = raw_record["zero_node_reason"]
        authority = raw_record["reason_authority"]
        evidence = raw_record["evidence"]
        if reason not in _ALLOWED_ZERO_NODE_REASONS:
            raise pytest.UsageError(f"unknown zero-node reason for {raw_file!r}: {reason!r}")
        if not isinstance(authority, str) or not authority.strip():
            raise pytest.UsageError(f"zero-node authority is required for {raw_file!r}")
        if not isinstance(evidence, str) or not evidence.strip():
            raise pytest.UsageError(f"zero-node evidence is required for {raw_file!r}")
        metadata[_normalize_path(raw_file)] = cast(
            ZeroNodeMetadata,
            {
                "zero_node_reason": reason,
                "reason_authority": authority.strip(),
                "evidence": evidence.strip(),
            },
        )
    return metadata


def _file_from_node_id(node_id: str) -> str:
    return _normalize_path(node_id.split("::", maxsplit=1)[0])


def _build_file_records(
    target_files: list[str], node_ids: list[str], zero_metadata: dict[str, ZeroNodeMetadata]
) -> list[FileRecord]:
    counts = Counter(_file_from_node_id(node_id) for node_id in node_ids)
    unknown_files = sorted(set(counts) - set(target_files))
    if unknown_files:
        raise pytest.UsageError(
            "collected node IDs reference files outside the declared target set: "
            f"{unknown_files!r}"
        )

    unused_metadata = sorted(set(zero_metadata) - set(target_files))
    if unused_metadata:
        raise pytest.UsageError(
            f"zero-node metadata references undeclared target files: {unused_metadata!r}"
        )

    records: list[FileRecord] = []
    for file_path in target_files:
        node_count = counts[file_path]
        metadata = zero_metadata.get(file_path)
        if node_count > 0:
            if metadata is not None:
                raise pytest.UsageError(
                    f"non-zero file must not declare zero-node metadata: {file_path}"
                )
            records.append(
                {
                    "file": file_path,
                    "node_count": node_count,
                    "zero_node_reason": None,
                    "reason_authority": None,
                    "evidence": None,
                }
            )
            continue

        if metadata is None:
            raise pytest.UsageError(
                "zero-node file requires approved metadata with a frozen reason code: "
                f"{file_path}"
            )
        records.append(
            {
                "file": file_path,
                "node_count": 0,
                "zero_node_reason": metadata["zero_node_reason"],
                "reason_authority": metadata["reason_authority"],
                "evidence": metadata["evidence"],
            }
        )
    return records


def pytest_collection_finish(session: pytest.Session) -> None:
    config = session.config
    output = config.getoption("--hx-node-output")
    scope_value = config.getoption("--hx-collection-scope")

    # The plugin may be loaded in ordinary test runs; it becomes authoritative only
    # when both required interface options are supplied.
    if output in (None, "") and scope_value in (None, ""):
        return
    if not isinstance(output, str) or not output.strip():
        raise pytest.UsageError("TASK-015A requires --hx-node-output")
    if scope_value not in _ALLOWED_SCOPES:
        raise pytest.UsageError(f"invalid --hx-collection-scope: {scope_value!r}")
    if session.testsfailed:
        raise pytest.UsageError("collection errors prohibit TASK-015A inventory output")

    scope = cast(CollectionScope, scope_value)
    raw_shard = config.getoption("--hx-shard")
    shard = raw_shard.strip() if isinstance(raw_shard, str) and raw_shard.strip() else None
    target_files = _validate_collection_targets(config, scope, shard)

    node_ids = sorted(item.nodeid.replace("\\", "/") for item in session.items)
    duplicates = sorted(node_id for node_id, count in Counter(node_ids).items() if count > 1)
    if duplicates:
        raise pytest.UsageError(f"duplicate collected node IDs are prohibited: {duplicates!r}")

    zero_metadata = _load_zero_node_metadata(config)
    file_records = _build_file_records(target_files, node_ids, zero_metadata)

    track = _required_environment("HX_TRACK")
    if track not in _ALLOWED_TRACKS:
        raise pytest.UsageError(f"invalid HX_TRACK: {track!r}")
    commit_sha = os.environ.get("HX_COMMIT_SHA", os.environ.get("GITHUB_SHA", "")).strip()
    if not commit_sha:
        raise pytest.UsageError("TASK-015A requires HX_COMMIT_SHA or GITHUB_SHA")

    payload: dict[str, Any] = {
        "schema_version": "1",
        "collection_scope": scope,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "pytest_version": pytest.__version__,
        "commit_sha": commit_sha,
        "track": track,
        "shard": shard,
        "run_id": _required_environment("GITHUB_RUN_ID"),
        "run_attempt": _parse_positive_int_environment("GITHUB_RUN_ATTEMPT"),
        "behavior_fingerprint_sha256": _behavior_fingerprint(config),
        "node_count": len(node_ids),
        "node_ids": node_ids,
        "file_records": file_records,
    }

    if payload["node_count"] != len(payload["node_ids"]):
        raise pytest.UsageError("node_count does not match node_ids length")

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
