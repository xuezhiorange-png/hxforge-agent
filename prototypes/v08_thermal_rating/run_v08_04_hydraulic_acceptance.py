"""CLI: V08-04 hydraulic acceptance bundle (experimental; no production sign-off)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from prototypes.v08_thermal_rating.v08_04_hydraulic_feasibility_gate import (
    write_acceptance_artifact,
)


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    payload = write_acceptance_artifact(path)
    summary = {
        k: payload[k]
        for k in payload
        if k
        not in (
            "R0",
            "K_SCENARIO_CLASSIFICATION_STATUS",
            "EXISTING_PROTOTYPES_REUSED",
        )
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())