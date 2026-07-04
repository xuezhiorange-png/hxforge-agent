"""CLI entry point: ``python -m hexagent.rule_packs.validate``.

Accepts a positional path to a rule-pack directory. Optional flags:

* ``--strict`` — exit with non-zero status on any error (default behavior
  is also strict; the flag is accepted for forward compatibility with
  Section 15 future CI flags).
* ``--json`` — emit a JSON report on stdout instead of a human-readable
  summary.

Exit codes:

* ``0`` — rule-pack passes validation.
* ``1`` — validation errors found.
* ``2`` — loader / IO failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hexagent.rule_packs.errors import RulePackError
from hexagent.rule_packs.validation import validate_rule_pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m hexagent.rule_packs.validate",
        description="Validate a TASK-012 rule-pack directory.",
    )
    parser.add_argument(
        "rule_pack_path",
        type=Path,
        help="Path to a rule-pack directory (containing manifest.json).",
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
        report = validate_rule_pack(args.rule_pack_path)
    except RulePackError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2

    if args.json:
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        if report["status"] == "ok":
            sys.stdout.write(
                f"OK: rule-pack at {report['rule_pack_path']} "
                f"({report['rule_count']} rules) passes validation\n"
            )
        else:
            sys.stdout.write(
                f"FAIL: rule-pack at {report['rule_pack_path']} "
                f"has {len(report['errors'])} error(s):\n"
            )
            for err in report["errors"]:
                sys.stdout.write(f"  - {err['path']}: {err['message']}\n")

    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
