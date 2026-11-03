#!/usr/bin/env python3
"""Generate R27H candidate-space extension report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/opt/cursor/artifacts/r27h-extension"),
    )
    parser.add_argument(
        "--fixture-copy",
        type=Path,
        default=Path("tests/fixtures/R27H_CANDIDATE_SPACE_EXTENSION.json"),
    )
    args = parser.parse_args()
    from prototypes.v07_general_rating_sizing_mvp.r27h_candidate_space_extension import (
        run_r27h_candidate_space_extension,
        write_r27h_reports,
    )

    report = run_r27h_candidate_space_extension()
    write_r27h_reports(report, args.output_dir)
    args.fixture_copy.parent.mkdir(parents=True, exist_ok=True)
    args.fixture_copy.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    summary = {"fixture": str(args.fixture_copy), "answers": report["engineering_answers"]}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
