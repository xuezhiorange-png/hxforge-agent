"""CLI entry point: ``python -m hexagent.material_costs.validate``.

Accepts a positional path to a material / cost catalog directory. The
directory may contain ``material_records.json`` and
``cost_records.json``. Optional flags:

* ``--strict`` — exit with non-zero status on any blocker (default
  behavior is also strict; the flag is reserved for forward
  compatibility).
* ``--json`` — emit a JSON report on stdout instead of a human
  summary.

Exit codes:

* ``0`` — catalog passes validation.
* ``1`` — validation blockers found.
* ``2`` — loader / IO failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hexagent.material_costs.errors import (
    MaterialCostError,
    MaterialCostValidationError,
)
from hexagent.material_costs.loader import load_cost_records, load_material_records
from hexagent.material_costs.validation import (
    validate_cost_record,
    validate_material_record,
)


def _validate_catalog(catalog_path: Path) -> dict[str, object]:
    material_records = load_material_records(catalog_path)
    cost_records = load_cost_records(catalog_path)

    material_results = [validate_material_record(rec) for rec in material_records]
    cost_results = [validate_cost_record(rec) for rec in cost_records]

    total_blockers = sum(len(r.blockers) for r in material_results + cost_results)
    total_warnings = sum(len(r.warnings) for r in material_results + cost_results)

    return {
        "status": "ok" if total_blockers == 0 else "errors",
        "catalog_path": str(catalog_path),
        "material_record_count": len(material_records),
        "cost_record_count": len(cost_records),
        "total_blockers": total_blockers,
        "total_warnings": total_warnings,
        "material_results": [r.to_dict() for r in material_results],
        "cost_results": [r.to_dict() for r in cost_results],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m hexagent.material_costs.validate",
        description="Validate a TASK-013 material / cost catalog directory.",
    )
    parser.add_argument(
        "catalog_path",
        type=Path,
        help=(
            "Path to a catalog directory containing material_records.json and "
            "cost_records.json, OR a direct path to one of those files."
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict mode (default behavior; reserved for future CI flags).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON report on stdout instead of a human summary.",
    )
    args = parser.parse_args(argv)

    try:
        report = _validate_catalog(args.catalog_path)
    except MaterialCostValidationError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2
    except MaterialCostError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2

    if args.json:
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        status = str(report["status"])
        sys.stdout.write(
            f"{status.upper()}: catalog={report['catalog_path']} "
            f"material={report['material_record_count']} "
            f"cost={report['cost_record_count']} "
            f"blockers={report['total_blockers']} "
            f"warnings={report['total_warnings']}\n"
        )

    return 0 if report["status"] == "ok" else 1


__all__ = ["main"]


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main(sys.argv[1:]))
