#!/usr/bin/env python3
"""Run the frozen TASK036 v0.3 TASK-020 -> TASK-035 demo.

The runner delegates all producer work to the public TASK031--TASK035
operations.  It only assembles the release evidence projections and writes
the four persisted D23 evidence files when explicitly requested.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from hexagent.release_demo.artifacts import (
    RELEASE_EVIDENCE_ROOT,
    render_demo_markdown_bytes,
    render_json_bytes,
    write_release_evidence,
)
from hexagent.release_demo.schema import (
    DEMO_RESULT_SCHEMA_VERSION,
    DEMO_SUCCESS_ID,
    IMPLEMENTATION_SOFTWARE_VERSION,
    PROFILE_ID,
    RELEASE_VERSION,
    SOURCE_MAIN_SHA,
    SOURCE_MAIN_TREE,
)
from hexagent.release_demo.task036 import build_release_run


def build_release_evidence(run: Any | None = None) -> dict[str, Any]:
    """Return the deterministic demo JSON projection from a public run."""

    current_run = build_release_run() if run is None else run
    identities = current_run.final_result["release_acceptance_ledger"][
        "required_producer_identities"
    ]
    return {
        "schema_version": DEMO_RESULT_SCHEMA_VERSION,
        "profile_id": PROFILE_ID,
        "implementation_software_version": IMPLEMENTATION_SOFTWARE_VERSION,
        "demo_id": DEMO_SUCCESS_ID,
        "release_version": RELEASE_VERSION,
        "source_commit": SOURCE_MAIN_SHA,
        "source_tree": SOURCE_MAIN_TREE,
        "production_graph": current_run.graph_evidence,
        "success_demo": {
            "demo_id": DEMO_SUCCESS_ID,
            "status": "VALID",
            "task034_result_hash": current_run.final_result["task034_result_hash"],
            "task034_result_id": current_run.final_result["task034_result_id"],
            "task035_result_hash": current_run.final_result["task035_result_hash"],
            "task035_result_id": current_run.final_result["task035_result_id"],
        },
        "blocked_demos": list(current_run.blocked_cases),
        "producer_identities": identities,
        "upstream_evidence_ledger": current_run.upstream_evidence_ledger,
        "capability_boundary": {
            "available": current_run.final_result["release_acceptance_ledger"][
                "required_available_capabilities"
            ],
            "unavailable": current_run.final_result["release_acceptance_ledger"][
                "unavailable_capabilities"
            ],
            "release_acceptance_is_not_engineering_correctness_proof": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--write-evidence", action="store_true")
    args = parser.parse_args()
    run = build_release_run()
    evidence = build_release_evidence(run)
    if args.write_evidence:
        output_dir = Path(RELEASE_EVIDENCE_ROOT)
        write_release_evidence(
            output_dir=output_dir,
            demo_json_bytes=run.artifact_bytes[
                "release_evidence/v0.3.0/task020-to-task035-demo.json"
            ],
            demo_markdown_bytes=run.artifact_bytes[
                "release_evidence/v0.3.0/task020-to-task035-demo.md"
            ],
            manifest_bytes=run.artifact_bytes["release_evidence/v0.3.0/release-manifest.json"],
            acceptance_markdown_bytes=run.artifact_bytes[
                "release_evidence/v0.3.0/release-acceptance.md"
            ],
        )
    rendered = (
        render_json_bytes(evidence)
        if args.format == "json"
        else render_demo_markdown_bytes(evidence)
    )
    print(rendered.decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
