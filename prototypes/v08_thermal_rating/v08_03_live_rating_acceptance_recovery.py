#!/usr/bin/env python3
"""V08-03 LIVE_RATING_ACCEPTANCE_RECOVERY — 250 kW terminal closeout (local, no publish)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_REPO), str(_REPO / "src")]

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.case_identity_v08 import CASE_250KW_ID, FIXTURE_250
from prototypes.v08_thermal_rating.v08_03_live_rating_bridge import (
    bridge_report_to_delivery_fields,
    run_v08_05_with_live_thermal_rating,
)

DEFAULT_ARTIFACT = Path("/opt/cursor/artifacts/v08_03_live_rating_acceptance_recovery.json")


def main() -> int:
    text = FIXTURE_250.read_text(encoding="utf-8")
    bridge = run_v08_05_with_live_thermal_rating(
        text,
        provider=CoolPropProvider(),
        max_candidates=32,
        top_n=5,
        max_live_rating_geometries=32,
        min_accepted_distinct_geometries=2,
    )
    payload = bridge_report_to_delivery_fields(bridge, engineering_case_id=CASE_250KW_ID)
    payload["FIXTURE"] = str(FIXTURE_250.relative_to(_REPO))
    payload["MANUFACTURABLE_STRUCTURAL_COUNT_250KW"] = 3
    if bridge.live_rating is not None:
        payload["MODEL_BLOCKERS"] = list(bridge.live_rating.model_blockers)
        payload["ENGINEERING_ACCEPTANCE_BLOCKERS"] = list(
            bridge.live_rating.engineering_acceptance_blockers
        )
    DEFAULT_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_ARTIFACT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["V08_03_ENGINEERING_ACCEPTANCE"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())