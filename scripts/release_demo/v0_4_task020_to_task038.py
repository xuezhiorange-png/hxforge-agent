#!/usr/bin/env python3
"""Generate the deterministic TASK039 v0.4 release-evidence bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from hexagent.release_demo.v0_4.artifacts import write_release_evidence
from hexagent.release_demo.v0_4.task039 import build_release_run


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--write-evidence", action="store_true")
    args = parser.parse_args()

    run = build_release_run()
    root = Path(__file__).resolve().parents[2]
    output_dir = root / "release_evidence" / "v0.4.0"
    write_release_evidence(
        output_dir=output_dir,
        demo_json_bytes=run.artifact_bytes["release_evidence/v0.4.0/task020-to-task038-demo.json"],
        demo_markdown_bytes=run.artifact_bytes[
            "release_evidence/v0.4.0/task020-to-task038-demo.md"
        ],
        manifest_bytes=run.artifact_bytes["release_evidence/v0.4.0/release-manifest.json"],
        acceptance_markdown_bytes=run.artifact_bytes[
            "release_evidence/v0.4.0/release-acceptance.md"
        ],
    )
    if args.format == "markdown":
        print(run.artifact_bytes["release_evidence/v0.4.0/task020-to-task038-demo.md"].decode())
    else:
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "release_version": "0.4.0",
                    "result_hash": run.final_result["result_hash"],
                    "result_id": run.final_result["result_id"],
                    "artifacts": list(run.artifact_bytes),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
