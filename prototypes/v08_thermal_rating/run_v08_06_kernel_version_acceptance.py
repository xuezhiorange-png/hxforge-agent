"""Run V08-06 NEW_RATING_KERNEL_VERSION_ACCEPTANCE matrix."""

# ruff: noqa: E501

from __future__ import annotations

import json

from prototypes.v08_thermal_rating.v08_06_kernel_version_acceptance import (
    write_v08_06_kernel_artifact,
)


def main() -> int:
    payload = write_v08_06_kernel_artifact()
    print(json.dumps({k: payload[k] for k in payload if k not in ("r0_shortlist_rows", "slot_records")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())