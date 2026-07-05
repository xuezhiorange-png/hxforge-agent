#!/usr/bin/env python3
"""TASK-016 Alpha Preview v0.1 minimal trial runner.

Implements the minimal runner surface described in
``docs/trials/TASK-016-alpha-preview-v0.1.md`` Section 3 (workflow) and
Section 5 (package layout), restricted to the TASK-016-TRIAL-004 scope:

  * Iterate the deterministic trial fixtures under
    ``examples/task016_alpha_preview_v0_1/fixtures/*.input.json``.
  * For each fixture, extract ``fixture_input.payload`` and feed it to
    :func:`hexagent.geometry_catalogs.load_geometry_catalog`.
  * Emit one deterministic success or blocker output per fixture, in
    the shape frozen by the TRIAL-002 expected output JSON files.
  * Compare each actual output against the corresponding expected
    output JSON file, on the fields specified by design Section 9.
  * Return non-zero exit when any fixture fails to match its expected
    output.

This runner is intentionally minimal:

  * It does not perform engineering calculations.
  * It does not implement pressure-drop, C0/C1/C4, mass, cost,
    material grade, mechanical suitability, or TASK-017+ semantics.
  * It does not modify fixtures, expected outputs, production code,
    tests, CI manifest, or governance files.
  * It is not a general-purpose framework — it is bound to the five
    TASK-016 Alpha Preview v0.1 trial cases.

Authority baseline
------------------

* TASK-016 design PR: ``#68`` (merged).
* Design merge commit: ``984eee5de49a3805182b54841463ebbba91fca88``.
* TASK-016 implementation PR: ``#67`` (merged).
* Implementation merge commit: ``ac7a4152698f039b4d6795f6a814228cb3c43def``.
* TASK-016-TRIAL dedicated Issue: ``#70`` (OPEN).
* TASK-016-TRIAL-004 implementation PR: ``#71`` (Draft).

Constraints
-----------

* No secrets are read.
* No environment variables are read for secret material.
* No network calls are made.
* No mutation of any fixture, expected output, or external file.
* This is a deterministic local dry-run only.

Usage
-----

::

    uv run --locked python scripts/run_task016_alpha_preview_case.py
    uv run --locked python scripts/run_task016_alpha_preview_case.py --case case_001_catalog_success
    uv run --locked python scripts/run_task016_alpha_preview_case.py --format json

Exit codes
----------

* ``0`` — every trial case matches its expected output (success or
  intended blocker) with no runner-internal error.
* ``1`` — at least one trial case diverged from its expected output.
* ``2`` — file-load / JSON-parse / runner-internal error.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from hexagent.geometry_catalogs import (
    GeometryCatalogBlockerError,
    load_geometry_catalog,
)

TRIAL_VERSION: Final[str] = "task-016-alpha-preview-v0.1"
DEFAULT_FIXTURE_DIR: Final[str] = "examples/task016_alpha_preview_v0_1/fixtures"
DEFAULT_EXPECTED_DIR: Final[str] = "examples/task016_alpha_preview_v0_1/expected"

# Fields that the runner compares against the expected output, per
# design Section 9 (success output shape) and the TRIAL-002 blocker
# output skeleton.
SUCCESS_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "trial_version",
    "case_id",
    "status",
    "catalog_content_hash",
    "ordered_geometry_ids",
    "record_hashes",
)
BLOCKER_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "trial_version",
    "case_id",
    "status",
    "error_code",
    "context",
)


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> dict[str, Any]:
    """Read and JSON-parse ``path``. Raises ``SystemExit(2)`` on any failure.

    The runner treats JSON-parse failure as a runner-internal error
    (exit code 2), not as a case-level divergence (exit code 1).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"[error] cannot read {path}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"[error] invalid JSON in {path}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if not isinstance(data, dict):
        print(f"[error] {path}: top-level JSON is not an object", file=sys.stderr)
        raise SystemExit(2)
    return data


def _expected_path_for(fixture_path: Path, expected_dir: Path) -> Path:
    """Map a fixture input path to its expected output path.

    ``catalog_success.input.json`` -> ``catalog_success.expected.json``.
    """
    return expected_dir / fixture_path.name.replace(".input.json", ".expected.json")


# ---------------------------------------------------------------------------
# Actual-output construction
# ---------------------------------------------------------------------------


def _build_success_output(fixture: dict[str, Any]) -> dict[str, Any]:
    """Load ``fixture['fixture_input']['payload']`` and build a success dict.

    The dict shape mirrors the TRIAL-002 success expected output:

      * ``trial_version`` taken from the fixture envelope.
      * ``case_id`` taken from the fixture envelope.
      * ``status`` = ``"success"``.
      * ``catalog_content_hash`` = the deterministic SHA-256 from
        :func:`load_geometry_catalog`.
      * ``ordered_geometry_ids`` = list of geometry_id in canonical
        order, taken from the loaded :class:`GeometryCatalog`.
      * ``record_hashes`` = ``{geometry_id: record_hash}`` for every
        loaded record.
    """
    payload = fixture.get("fixture_input", {}).get("payload")
    if not isinstance(payload, dict):
        raise ValueError("fixture_input.payload is missing or not an object")

    catalog = load_geometry_catalog(payload)

    ordered_geometry_ids = [record.geometry_id for record in catalog.records]
    record_hashes = {record.geometry_id: record.record_hash for record in catalog.records}

    return {
        "trial_version": fixture.get("trial_version", TRIAL_VERSION),
        "case_id": fixture.get("case_id", ""),
        "status": "success",
        "catalog_content_hash": catalog.content_hash,
        "ordered_geometry_ids": ordered_geometry_ids,
        "record_hashes": record_hashes,
    }


def _build_blocker_output(
    fixture: dict[str, Any],
    blocker: GeometryCatalogBlockerError,
) -> dict[str, Any]:
    """Build a blocker dict from the raised ``GeometryCatalogBlockerError``.

    The dict shape mirrors the TRIAL-002 blocker expected output:

      * ``trial_version`` taken from the fixture envelope.
      * ``case_id`` taken from the fixture envelope.
      * ``status`` = ``"blocked"``.
      * ``error_code`` = the blocker's ``error_code`` attribute.
      * ``context`` = the blocker's ``context`` mapping (a plain dict
        copy so JSON serialization is stable).
    """
    context = dict(blocker.context) if isinstance(blocker.context, Mapping) else {}
    return {
        "trial_version": fixture.get("trial_version", TRIAL_VERSION),
        "case_id": fixture.get("case_id", ""),
        "status": "blocked",
        "error_code": blocker.error_code,
        "context": context,
    }


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def _select_required_fields(actual: dict[str, Any]) -> tuple[str, ...]:
    """Return the required-field tuple for ``actual`` based on its ``status``."""
    status = actual.get("status")
    if status == "success":
        return SUCCESS_REQUIRED_FIELDS
    if status == "blocked":
        return BLOCKER_REQUIRED_FIELDS
    raise ValueError(f"unknown actual status: {status!r}")


def _diff_field(field: str, actual: Any, expected: Any) -> list[str]:
    """Return human-readable divergence lines for ``field``."""
    if field == "record_hashes":
        # dict-of-strings; compare key sets and per-key equality.
        if not isinstance(actual, dict) or not isinstance(expected, dict):
            return [
                f"  {field}: type mismatch (actual={type(actual).__name__}, "
                f"expected={type(expected).__name__})"
            ]
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        lines: list[str] = []
        for key in missing:
            lines.append(f"  {field}: missing key {key!r}")
        for key in extra:
            lines.append(f"  {field}: extra key {key!r}")
        for key in sorted(set(actual) & set(expected)):
            if actual[key] != expected[key]:
                lines.append(
                    f"  {field}[{key!r}]: actual={actual[key]!r} expected={expected[key]!r}"
                )
        return lines
    if actual != expected:
        return [f"  {field}: actual={actual!r} expected={expected!r}"]
    return []


def _compare_outputs(actual: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    """Compare ``actual`` to ``expected`` and return a list of divergences.

    Only the design-§9-required fields are compared. Extra fields in
    ``expected`` (such as the explanatory ``notes`` block) are ignored
    so that future prose-only edits to expected outputs do not break
    the runner.
    """
    required = _select_required_fields(actual)
    divergences: list[str] = []
    for field in required:
        if field not in expected:
            divergences.append(f"  expected.{field}: missing")
            continue
        divergences.extend(_diff_field(field, actual.get(field), expected[field]))
    # Also verify expected status / error_code agree with actual so a
    # wrong-typed expected file cannot pass silently.
    if "status" in expected and expected["status"] != actual.get("status"):
        divergences.append(
            f"  expected.status={expected['status']!r} but actual.status={actual.get('status')!r}"
        )
    return divergences


# ---------------------------------------------------------------------------
# Per-case execution
# ---------------------------------------------------------------------------


def _run_case(
    fixture_path: Path,
    expected_path: Path,
) -> tuple[str, bool, list[str]]:
    """Run one fixture end-to-end and return ``(case_id, ok, divergences)``.

    ``ok`` is ``True`` iff the runner-internal execution produced an
    output that matches the expected output on every required field.
    Divergences (empty list on success) are collected as human-readable
    strings for the text-mode summary.
    """
    fixture = _read_json(fixture_path)
    expected = _read_json(expected_path)

    expected_status = expected.get("status")
    try:
        actual = _build_success_output(fixture)
    except GeometryCatalogBlockerError as exc:
        actual = _build_blocker_output(fixture, exc)
    except Exception as exc:  # noqa: BLE001 - report any unexpected failure as divergence
        return (
            fixture.get("case_id", fixture_path.stem),
            False,
            [f"  runner-internal error: {type(exc).__name__}: {exc}"],
        )

    # Sanity: if expected says pass, runner must report success; if
    # expected says blocked, runner must report blocked.
    if expected_status == "pass" and actual.get("status") != "success":
        return (
            actual.get("case_id", fixture_path.stem),
            False,
            [f"  expected_status='pass' but runner emitted status={actual.get('status')!r}"],
        )
    if expected_status == "blocked" and actual.get("status") != "blocked":
        return (
            actual.get("case_id", fixture_path.stem),
            False,
            [f"  expected_status='blocked' but runner emitted status={actual.get('status')!r}"],
        )

    divergences = _compare_outputs(actual, expected)
    return (
        actual.get("case_id", fixture_path.stem),
        not divergences,
        divergences,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _discover_cases(
    fixture_dir: Path,
    expected_dir: Path,
    case_filter: str | None,
) -> list[tuple[Path, Path]]:
    """Discover fixture/expected pairs sorted by fixture filename.

    Only files whose fixture stem matches an existing expected file
    are returned; otherwise the runner treats the missing pair as a
    runner-internal error (exit code 2).
    """
    if not fixture_dir.is_dir():
        print(f"[error] fixture dir does not exist: {fixture_dir}", file=sys.stderr)
        raise SystemExit(2)
    if not expected_dir.is_dir():
        print(f"[error] expected dir does not exist: {expected_dir}", file=sys.stderr)
        raise SystemExit(2)

    pairs: list[tuple[Path, Path]] = []
    for fixture_path in sorted(fixture_dir.glob("*.input.json")):
        if case_filter:
            # Allow matching any of the following identifiers:
            #   * full case_id from the fixture envelope (e.g.
            #     ``case_001_catalog_success``);
            #   * the file stem with both suffixes stripped
            #     (e.g. ``catalog_success``); or
            #   * the file stem with only the JSON suffix stripped
            #     (e.g. ``catalog_success.input``), which is what
            #     :pyattr:`Path.stem` returns.
            envelope_case_id = ""
            try:
                envelope_case_id = str(
                    json.loads(fixture_path.read_text(encoding="utf-8")).get("case_id", "")
                )
            except (OSError, json.JSONDecodeError):
                envelope_case_id = ""
            short_stem = fixture_path.name.removesuffix(".input.json")
            candidates = (short_stem, fixture_path.stem, envelope_case_id)
            if case_filter not in candidates:
                continue
        expected_path = _expected_path_for(fixture_path, expected_dir)
        if not expected_path.is_file():
            print(
                f"[error] missing expected output for {fixture_path.name}: {expected_path}",
                file=sys.stderr,
            )
            raise SystemExit(2)
        pairs.append((fixture_path, expected_path))
    return pairs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "TASK-016 Alpha Preview v0.1 minimal trial runner. Loads each "
            "fixture under examples/task016_alpha_preview_v0_1/fixtures/, "
            "emits a deterministic success or blocker output, and compares "
            "against the TRIAL-002 expected output JSONs."
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Repository root (default: current directory).",
    )
    parser.add_argument(
        "--fixture-dir",
        type=Path,
        default=None,
        help=f"Fixtures directory relative to --repo-root (default: {DEFAULT_FIXTURE_DIR}).",
    )
    parser.add_argument(
        "--expected-dir",
        type=Path,
        default=None,
        help="Expected outputs directory relative to --repo-root "
        f"(default: {DEFAULT_EXPECTED_DIR}).",
    )
    parser.add_argument(
        "--case",
        type=str,
        default=None,
        help="Restrict to a single fixture stem (e.g. case_001_catalog_success).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    args = parser.parse_args(argv)

    repo_root: Path = args.repo_root.resolve()
    fixture_dir: Path = (
        args.fixture_dir if args.fixture_dir is not None else repo_root / DEFAULT_FIXTURE_DIR
    )
    expected_dir: Path = (
        args.expected_dir if args.expected_dir is not None else repo_root / DEFAULT_EXPECTED_DIR
    )
    if not fixture_dir.exists():
        fixture_dir = repo_root / DEFAULT_FIXTURE_DIR
    if not expected_dir.exists():
        expected_dir = repo_root / DEFAULT_EXPECTED_DIR

    pairs = _discover_cases(fixture_dir, expected_dir, args.case)
    if not pairs:
        print(
            f"[error] no trial fixtures discovered under {fixture_dir}",
            file=sys.stderr,
        )
        return 2

    results: list[dict[str, Any]] = []
    for fixture_path, expected_path in pairs:
        case_id, ok, divergences = _run_case(fixture_path, expected_path)
        results.append(
            {
                "case_id": case_id,
                "fixture": str(fixture_path.relative_to(repo_root)),
                "expected": str(expected_path.relative_to(repo_root)),
                "ok": ok,
                "divergences": divergences,
            }
        )

    passed = sum(1 for r in results if r["ok"])
    failed = sum(1 for r in results if not r["ok"])
    overall_ok = failed == 0

    if args.format == "json":
        payload = {
            "trial_version": TRIAL_VERSION,
            "fixture_dir": str(fixture_dir.relative_to(repo_root))
            if fixture_dir.is_relative_to(repo_root)
            else str(fixture_dir),
            "expected_dir": str(expected_dir.relative_to(repo_root))
            if expected_dir.is_relative_to(repo_root)
            else str(expected_dir),
            "results": results,
            "summary": {
                "total": len(results),
                "passed": passed,
                "failed": failed,
                "result": "GREEN" if overall_ok else "RED",
            },
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for r in results:
            tag = "PASS" if r["ok"] else "FAIL"
            print(f"[{tag}] {r['case_id']}  ({r['fixture']})")
            for line in r["divergences"]:
                print(line)
        print()
        print(
            f"summary: total={len(results)} passed={passed} failed={failed} "
            f"result={'GREEN' if overall_ok else 'RED'}"
        )

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
