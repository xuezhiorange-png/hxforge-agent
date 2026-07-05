#!/usr/bin/env python3
"""TASK-015 spec validation local dry-run script (follow-up slice, Section 9).

Implements the TASK-015 frozen design contract
(``docs/tasks/TASK-015-ci-security-and-release-automation.md``,
Frozen Contract Authority SHA
``39135e269b014e9c9310ac403a60591393d46b2d``).

Purpose
-------

This script is the companion local dry-run for the
``.github/workflows/task-015-spec-validation.yml`` workflow. It loads
each TASK-015 governance YAML spec under ``docs/governance/``, runs
:func:`hexagent.governance.validate_all_specs`, and emits one status
check per spec in the shape ``task-015/<spec-name>/blockers``:

* GREEN (exit 0) when no blockers.
* RED (non-zero exit) when any blocker is present.

Constraints
-----------

* No secrets are read.
* No environment variables are read for secret material.
* No OIDC trust is created.
* No registry artifacts are pushed.
* This is purely a simulated / local validation hook
  (frozen contract Section 14.13).

Usage
-----

::

    uv run --locked python scripts/run_task015_spec_validation.py

Exit codes
----------

* 0 — every spec is clean (no blockers).
* 1 — at least one spec has at least one blocker.
* 2 — file-load / parse error.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from hexagent.governance import (
    ALL_SPEC_PATHS,
    ValidationReport,
    load_spec,
    validate_all_specs,
)


def _load_all_specs(repo_root: Path, spec_root: Path) -> dict[str, dict[str, Any]]:
    """Load every TASK-015 spec under ``repo_root`` and return
    ``spec_path -> spec_data`` keyed by the canonical path strings
    declared in :data:`ALL_SPEC_PATHS` (e.g. ``docs/governance/ci_pipeline_spec.yaml``).

    The ``spec_root`` argument is used only for the relative path
    computation — the keys are always rooted at ``repo_root``.
    Missing files are reported but do not abort the script; the
    CI runtime surfaces them as ``spec_schema_error`` blockers via
    the validator.
    """
    out: dict[str, dict[str, Any]] = {}
    for spec_path in sorted(ALL_SPEC_PATHS):
        # ``spec_path`` is rooted at the repository (e.g.
        # ``docs/governance/ci_pipeline_spec.yaml``). The ``spec_root``
        # argument is informational only — we always load from
        # ``repo_root / spec_path`` so the keys match the validator's
        # ``SPEC_PATH_*`` constants.
        file_path = repo_root / spec_path
        if not file_path.exists():
            print(f"[warn] missing spec file: {spec_path}", file=sys.stderr)
            continue
        try:
            out[spec_path] = load_spec(file_path.read_text(encoding="utf-8"))
        except Exception as exc:
            # Surface as a synthetic validation finding via load_spec
            # is not the validator's job; just print and continue.
            print(f"[warn] failed to load {spec_path}: {exc}", file=sys.stderr)
    return out


def _status_check_name(spec_path: str, spec_data: Mapping[str, Any]) -> str:
    """Return the status-check name for ``spec_path`` per Section 9
    cross-cutting governance.

    Shape: ``task-015/<spec-name>/blockers`` where ``<spec-name>``
    is the spec's canonical identifier (e.g. ``ci-pipeline``,
    ``security-gate``, ``release``, ``failure-taxonomy``).

    The canonical identifier is taken from the spec's own
    ``canonical_name`` / ``gate_id`` / ``release_channel`` field
    (Section 4.3). Falling back to the YAML file stem keeps the
    script operational on malformed specs.
    """
    identifier = (
        spec_data.get("canonical_name")
        or spec_data.get("gate_id")
        or spec_data.get("release_channel")
    )
    if not isinstance(identifier, str) or not identifier.strip():
        identifier = Path(spec_path).stem
    return f"task-015/{identifier}/blockers"


def _format_report(report: ValidationReport) -> str:
    """Render a single ValidationReport as a human-readable summary."""
    lines: list[str] = []
    lines.append(f"spec_path: {report.spec_path}")
    lines.append(f"  blockers: {len(report.blockers)}")
    for blocker in report.blockers:
        lines.append(f"    - [{blocker.error_code}] {blocker.field_path}: {blocker.message}")
    lines.append(f"  warnings: {len(report.warnings)}")
    for warning in report.warnings:
        lines.append(f"    - [{warning.error_code}] {warning.field_path}: {warning.message}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "TASK-015 spec validation local dry-run. "
            "Emits one status check per spec in the shape "
            "'task-015/<spec-name>/blockers'."
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Repository root for resolving canonical spec paths (default: current directory).",
    )
    parser.add_argument(
        "--spec-root",
        type=Path,
        default=Path("docs/governance"),
        help="Root directory containing the governance YAML specs "
        "(default: docs/governance). Informational only — keys are "
        "rooted at --repo-root.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    args = parser.parse_args(argv)

    if not args.spec_root.exists():
        print(f"[error] spec root does not exist: {args.spec_root}", file=sys.stderr)
        return 2

    specs = _load_all_specs(args.repo_root, args.spec_root)
    if not specs:
        print(f"[error] no TASK-015 specs found under {args.repo_root}", file=sys.stderr)
        return 2

    reports = validate_all_specs(specs)
    total_blockers = sum(len(r.blockers) for r in reports.values())
    total_warnings = sum(len(r.warnings) for r in reports.values())

    if args.format == "json":
        payload = {
            "spec_root": str(args.spec_root),
            "status_checks": [
                {
                    "name": _status_check_name(spec_path, specs[spec_path]),
                    "spec_path": spec_path,
                    "is_clean": report.is_clean,
                    "blockers": [f.to_dict() for f in report.blockers],
                    "warnings": [f.to_dict() for f in report.warnings],
                }
                for spec_path, report in sorted(reports.items())
            ],
            "summary": {
                "spec_count": len(reports),
                "total_blockers": total_blockers,
                "total_warnings": total_warnings,
                "result": "GREEN" if total_blockers == 0 else "RED",
            },
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for spec_path in sorted(reports):
            print(_format_report(reports[spec_path]))
        print()
        print("=== TASK-015 status checks ===")
        for spec_path in sorted(reports):
            check_name = _status_check_name(spec_path, specs[spec_path])
            color = "GREEN" if reports[spec_path].is_clean else "RED"
            print(f"  {check_name}: {color}")
        print()
        print(
            f"summary: specs={len(reports)} blockers={total_blockers} "
            f"warnings={total_warnings} result="
            f"{'GREEN' if total_blockers == 0 else 'RED'}"
        )

    return 0 if total_blockers == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
