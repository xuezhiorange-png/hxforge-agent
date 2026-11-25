"""CLI: V08-06 independent E2E acceptance matrix."""

from __future__ import annotations

import argparse
import json

from prototypes.v08_thermal_rating.v08_06_independent_e2e_acceptance import write_v08_06_artifact


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live-r0-rating", action="store_true")
    ap.add_argument("--max-rating", type=int, default=1)
    ap.add_argument("--max-candidates", type=int, default=32)
    args = ap.parse_args()
    payload = write_v08_06_artifact(
        attempt_live_rating_r0_only=args.live_r0_rating,
        max_rating_geometries=args.max_rating,
        max_candidates=args.max_candidates,
    )
    print(
        json.dumps(
            {k: payload[k] for k in payload if k != "case_records"},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())