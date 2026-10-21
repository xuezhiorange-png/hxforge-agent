"""R9 evidence: experimental live-rating CLI and engineering preview."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.experimental_live_workflow import (
    run_experimental_live_rating_from_paths,
)

_DEFAULT_CASE = Path(__file__).resolve().parent / "cases" / "mvp_tube_hot_shell_cold_r9.json"
_DEFAULT_EVIDENCE_DIR = (
    "docs/tasks/evidence/V07-GENERAL-LIVE-RATING-CLI-AND-ENGINEERING-PREVIEW-R9"
)


def main(case_path: Path, output_dir: Path) -> dict[str, Any]:
    outcome = run_experimental_live_rating_from_paths(case_path, output_dir, mesh_level=1)
    raw_path = outcome.raw_result_path
    return {
        "status": outcome.status,
        "mesh_status": outcome.mesh_status,
        "raw_result_path": str(raw_path) if raw_path else None,
        "raw_result_sha256": outcome.raw_result_sha256,
        "total_numerical_seconds": outcome.total_numerical_seconds,
    }


if __name__ == "__main__":
    case = Path(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_CASE
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(_DEFAULT_EVIDENCE_DIR)
    print(json.dumps(main(case, out), indent=2))
