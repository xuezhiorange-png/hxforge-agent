"""CLI: V08-05 qualified Top-N and engineering report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from prototypes.v08_thermal_rating.v08_05_qualified_top_n_engineering_report import (
    render_v08_05_markdown,
    run_v08_05_qualified_selection,
    v08_05_report_to_json,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="V08-05 qualified Top-N engineering report")
    ap.add_argument("case_json", type=Path, nargs="?", help="User case JSON file")
    ap.add_argument("--top-n", type=int, default=5)
    ap.add_argument("--max-candidates", type=int, default=48)
    ap.add_argument("--markdown", type=Path, default=None)
    ap.add_argument("--json-out", type=Path, default=None)
    ap.add_argument("--no-mdot", action="store_true")
    args = ap.parse_args()
    if args.case_json is None:
        ap.print_help()
        return 2
    text = args.case_json.read_text(encoding="utf-8")
    report = run_v08_05_qualified_selection(
        text,
        max_candidates=args.max_candidates,
        top_n=args.top_n,
        run_mdot_on_recommendation=not args.no_mdot,
    )
    payload = v08_05_report_to_json(report)
    summary = {
        k: payload[k]
        for k in (
            "task_id",
            "case_outcome",
            "report_hash",
            "top_n",
            "production_rating_validated",
        )
    }
    print(json.dumps(summary, indent=2))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if args.markdown:
        args.markdown.write_text(render_v08_05_markdown(report), encoding="utf-8")
    return 0 if report.case_outcome != "INVALID_INPUT" else 1


if __name__ == "__main__":
    raise SystemExit(main())