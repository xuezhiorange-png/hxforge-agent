"""TASK-015A manifest verifier CLI.

Deterministically verifies that the discovered test files (D) equal the
manifest-declared files (M), and emits a JSON matrix suitable for GitHub
Actions ``include`` consumption.

Usage::

    uv run --locked python -m tests.ci.verify_manifest \\
        --manifest ci-shard-manifest.yml --test-root tests
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .shard_manifest import (
    ManifestError,
    ShardManifest,
    ShardSpec,
    discover_test_files,
    load_manifest,
    verify_file_completeness,
)


def _shard_to_dict(shard: ShardSpec) -> dict[str, Any]:
    """Serialize a ShardSpec to a JSON-safe dict."""
    return {
        "name": shard.name,
        "job": shard.job,
        "python": list(shard.python),
        "files": list(shard.files),
        "timeout": shard.timeout,
    }


def _shard_to_matrix_rows(shard: ShardSpec) -> list[dict[str, Any]]:
    """Serialize a ShardSpec to one GitHub Actions matrix ``include`` row per Python version.

    ``files`` is joined with spaces so the runner can split on whitespace.
    """
    return [
        {
            "name": shard.name,
            "job": shard.job,
            "python": py,
            "files": " ".join(shard.files),
            "timeout": shard.timeout,
        }
        for py in shard.python
    ]


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.  Returns 0 on success, 1 on error."""
    parser = argparse.ArgumentParser(
        description="Verify D==M and emit a CI JSON matrix.",
    )
    parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help="Path to the ci-shard-manifest.yml file.",
    )
    parser.add_argument(
        "--test-root",
        required=True,
        type=Path,
        help="Path to the tests/ directory.",
    )
    args = parser.parse_args(argv)

    try:
        manifest_path: Path = args.manifest.resolve()
        test_root: Path = args.test_root.resolve()

        # Determine repo root from manifest location (manifest lives at repo root).
        repo_root = manifest_path.parent

        manifest: ShardManifest = load_manifest(manifest_path, repo_root=repo_root)
        discovered: frozenset[str] = discover_test_files(test_root, repo_root=repo_root)

        # This raises ManifestError if D != M.
        verify_file_completeness(manifest, test_root, repo_root=repo_root)

        # Build deterministic (sorted) output.
        shards_sorted = sorted(manifest.shards, key=lambda s: s.name)

        matrix_rows: list[dict[str, Any]] = []
        for s in shards_sorted:
            matrix_rows.extend(_shard_to_matrix_rows(s))

        output: dict[str, Any] = {
            "status": "pass",
            "discovered_count": len(discovered),
            "manifest_count": len(manifest.file_set),
            "shards": [_shard_to_dict(s) for s in shards_sorted],
            "matrix": {
                "include": matrix_rows,
            },
            "d_equals_m": True,
        }

        json.dump(output, sys.stdout, sort_keys=True, separators=(",", ":"))
        print()  # trailing newline
        return 0

    except (ManifestError, OSError, ValueError) as exc:
        output_fail: dict[str, Any] = {
            "status": "fail",
            "error": str(exc),
            "d_equals_m": False,
        }
        json.dump(output_fail, sys.stdout, sort_keys=True, separators=(",", ":"))
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
