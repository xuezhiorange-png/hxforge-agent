"""CLI for V08 autonomous design tool (experimental user-input delivery)."""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import json
from pathlib import Path

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_250, FIXTURE_330
from prototypes.v08_thermal_rating.v08_05_qualified_top_n_engineering_report import (
    merged_web_api_payload,
    render_v08_05_markdown,
    run_v08_05_qualified_selection,
)

_REPO = Path(__file__).resolve().parents[2]
_FIXTURES = {
    "330kw": FIXTURE_330,
    "250kw": FIXTURE_250,
    "constraint_change": _REPO / "tests/fixtures/v08_user_case_330kw_tight_envelope.json",
    "infeasible": _REPO / "tests/fixtures/v08_user_case_infeasible_duty_5mw.json",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="V08 autonomous design tool (experimental)")
    parser.add_argument(
        "--scenario",
        choices=["330kw", "250kw", "constraint_change", "infeasible", "all"],
        default="all",
    )
    parser.add_argument(
        "--case-file", type=Path, default=None, help="Path to user design case JSON"
    )
    parser.add_argument("--max-candidates", type=int, default=40)
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("/opt/cursor/artifacts"),
    )
    args = parser.parse_args()
    provider = CoolPropProvider()
    scenarios = list(_FIXTURES.keys()) if args.scenario == "all" else [args.scenario]
    if args.case_file is not None:
        text = args.case_file.read_text(encoding="utf-8")
        report = run_v08_05_qualified_selection(
            text,
            provider=provider,
            max_candidates=args.max_candidates,
            run_mdot_on_recommendation=True,
        )
        artifact_dir = args.artifact_dir
        artifact_dir.mkdir(parents=True, exist_ok=True)
        stem = args.case_file.stem
        (artifact_dir / f"v08_autonomous_design_{stem}.json").write_text(
            json.dumps(merged_web_api_payload(report), indent=2), encoding="utf-8"
        )
        (artifact_dir / f"v08_autonomous_design_{stem}.md").write_text(
            render_v08_05_markdown(report), encoding="utf-8"
        )
        mirror = report.design_tool_mirror
        print(
            json.dumps(
                {
                    "case": mirror.ingestion.engineering_case_id if mirror else None,
                    "v08_05_outcome": report.case_outcome,
                    "experimental_top_n": list(report.top_n.experimental_prescreen),
                },
                indent=2,
            )
        )
        return
    artifact_dir = args.artifact_dir
    artifact_dir.mkdir(parents=True, exist_ok=True)
    for key in scenarios:
        text = _FIXTURES[key].read_text(encoding="utf-8")
        report = run_v08_05_qualified_selection(
            text,
            provider=provider,
            max_candidates=args.max_candidates,
            run_mdot_on_recommendation=key != "infeasible",
        )
        (artifact_dir / f"v08_autonomous_design_{key}.json").write_text(
            json.dumps(merged_web_api_payload(report), indent=2), encoding="utf-8"
        )
        (artifact_dir / f"v08_autonomous_design_{key}.md").write_text(
            render_v08_05_markdown(report), encoding="utf-8"
        )
        mirror = report.design_tool_mirror
        summary = {
            "scenario": key,
            "case": mirror.ingestion.engineering_case_id if mirror else None,
            "experimental_top_n": list(report.top_n.experimental_prescreen),
            "case_outcome": report.case_outcome,
            "no_feasible": report.case_outcome
            in ("NO_FEASIBLE_DESIGN", "OUT_OF_ENVELOPE", "INVALID_INPUT"),
        }
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
