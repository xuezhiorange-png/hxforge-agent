"""R13 evidence: variable shell / tube-count live sizing (two new n=1 ratings)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_CASE = _REPO / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_variable_bundle_r13.json"
_EVIDENCE = _REPO / "docs/tasks/evidence/V07-GENERAL-VARIABLE-BUNDLE-GEOMETRY-SIZING-R13"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "prototypes.v07_general_rating_sizing_mvp",
            "--input",
            str(_CASE),
            "--output",
            str(output_dir),
            "--mode",
            "experimental-variable-bundle-sizing-r13",
            "--mesh",
            "1",
        ],
        cwd=_REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    outcome = json.loads((output_dir / "WORKFLOW_OUTCOME.json").read_text(encoding="utf-8"))
    decision = json.loads(
        (output_dir / "TARGET_DIRECTED_SIZING_DECISION.json").read_text(encoding="utf-8")
    )
    names = [
        "R13_ENGINEERING_REPORT.json",
        "R13_ENGINEERING_REPORT.md",
        "TARGET_DIRECTED_SIZING_DECISION.json",
        "R13_BASELINE_COMPARISON.json",
        "R12_25M_TASK174_BLOCKER_ANALYSIS.json",
        "RAW_RESULT.json",
        "CANDIDATE_RATING_RESULTS.json",
    ]
    files = {name: _sha256(output_dir / name) for name in names if (output_dir / name).is_file()}
    manifest_doc = {
        "schema_version": "hxforge.evidence-manifest.v1",
        "task_id": "V07_GENERAL_VARIABLE_BUNDLE_GEOMETRY_SIZING_R13",
        "files": files,
    }
    (output_dir / "EVIDENCE_MANIFEST.json").write_text(
        json.dumps(manifest_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest_doc["files"]["EVIDENCE_MANIFEST.json"] = _sha256(output_dir / "EVIDENCE_MANIFEST.json")
    (output_dir / "EVIDENCE_MANIFEST.json").write_text(
        json.dumps(manifest_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "cli_exit_code": proc.returncode,
        "workflow_outcome": outcome,
        "target_directed_decision": decision,
        "stderr_tail": (proc.stderr or "")[-1500:],
    }


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else _EVIDENCE
    print(json.dumps(main(out), indent=2))
