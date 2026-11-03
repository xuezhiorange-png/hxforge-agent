"""R10 evidence: multi-candidate experimental live-rating CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CASE = (
    _REPO_ROOT / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_multi_candidate_r10.json"
)
_DEFAULT_EVIDENCE_DIR = "docs/tasks/evidence/V07-GENERAL-MULTI-CANDIDATE-LIVE-RATING-R10"


def main(case_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "prototypes.v07_general_rating_sizing_mvp",
            "--input",
            str(case_path),
            "--output",
            str(output_dir),
            "--mode",
            "experimental-live-rating",
            "--mesh",
            "1",
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    outcome = json.loads((output_dir / "WORKFLOW_OUTCOME.json").read_text(encoding="utf-8"))
    return {
        "cli_exit_code": proc.returncode,
        "workflow_outcome": outcome,
        "stdout": proc.stdout[-2000:] if proc.stdout else "",
        "stderr": proc.stderr[-2000:] if proc.stderr else "",
    }


if __name__ == "__main__":
    case = Path(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_CASE
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(_DEFAULT_EVIDENCE_DIR)
    print(json.dumps(main(case, out), indent=2))
