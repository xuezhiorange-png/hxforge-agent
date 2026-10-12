#!/usr/bin/env python3
"""Replay TASK173 provider-quantization enclosure authority hashes.

Run from any working directory with the repository's locked environment:
    uv run --locked --no-sync python \
      docs/tasks/evidence/TASK-173-v0.7-provider-quantization-enclosure-hash-replay-r1.py

The only evidence input is the committed qualification receipt beside this
script. Hash semantics come from hexagent.canonical_json at the source HEAD
recorded in the companion replay-contract evidence.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from hexagent.canonical_json import canonical_sha256  # noqa: E402

EVIDENCE_PATH = Path(__file__).with_name(
    "TASK-173-v0.7-task174-native-bell-canonical-reduction-parity-and-enclosure-qualification-resume-r1.json"
)

EXPECTED_AUTHORITY_ID = "V07-T173-CELL-ROOT-PROVIDER-QUANTIZATION-ENCLOSURE-R1"
EXPECTED_AUTHORITY_HASH = "c95b5bf23b15a9c93b6ef47c3ad2043708bef9ae66429116855a4306f8102ab2"
EXPECTED_MATRIX_HASH = "92cb9fa0a65041199f67ebe588b460bcef868c64fdd6044e990f4309b6af8840"
EXPECTED_RUNNER_SHA256 = "14dbbdb324e38bb1bf5d034f6ccf04637967d629354da763e02248dc04b5adfb"
EXPECTED_RAW_LOG_SHA256 = "1e0ba509a895595137494df3fba1ee02747455412090b61eedfc34b1346f940d"
EXPECTED_EVENT_HASHES = (
    "8d90538c68e50c0fea4a8e778ad2eed3717f313002a5cc77ea183eaa348dc372",
    "0e3747bafd71aa64ac4636583e9792a97c6b10a2d160b583a463778e94875264",
    "0d02ac649288aed1bae8d538407a53d2be3b31723721d5a5bc17d475b2d0a90a",
    "23c628ec5844f0e22afd23f2101852ab016ab939c207cdf9bff31bace95492ba",
    "7dc5cc80392ec4f03c96e353b602e321689e433a39401259a6288ef3258dd99f",
    "9c6937bc7241e781746275ce6f3368313074a3cf3eab9dfb259d2605162fedc4",
    "2a8a1eabc32bd24c49991d1688daa62f48f66c351dea2e40fffed8a7e6b52410",
    "01d83e4423fd2a57af72def1d5796e05bdd07936edfc8fe3b6a668a63f90103d",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"REPLAY_FAIL: {message}")


def main() -> None:
    evidence: dict[str, Any] = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    authority = evidence["authority_candidate"]
    _require(authority["projection"]["authority_id"] == EXPECTED_AUTHORITY_ID, "authority ID")
    authority_hash = canonical_sha256(authority["projection"])
    _require(authority_hash == authority["canonical_hash"], "stored authority hash")
    _require(authority_hash == EXPECTED_AUTHORITY_HASH, "frozen authority hash")

    qualification = evidence["qualification"]
    matrix = qualification["qualification_matrix"]
    matrix_hash = canonical_sha256(matrix)
    _require(
        matrix_hash == qualification["qualification_matrix_canonical_hash"],
        "stored qualification matrix hash",
    )
    _require(matrix_hash == EXPECTED_MATRIX_HASH, "frozen qualification matrix hash")
    _require(matrix["diagnostic_runner_sha256"] == EXPECTED_RUNNER_SHA256, "runner identity")
    _require(matrix["raw_diagnostic_log_sha256"] == EXPECTED_RAW_LOG_SHA256, "raw log identity")

    events = matrix["all_trigger_events"]
    _require(len(events) == len(EXPECTED_EVENT_HASHES) == 8, "event count")
    replayed_event_hashes: list[str] = []
    for index, (event, expected_hash) in enumerate(
        zip(events, EXPECTED_EVENT_HASHES, strict=True), 1
    ):
        event_preimage = dict(event)
        recorded_hash = event_preimage.pop("quantization_enclosure_hash", None)
        _require(recorded_hash is not None, f"event {index} missing self hash")
        replayed_hash = canonical_sha256(event_preimage)
        _require(recorded_hash == expected_hash, f"event {index} stored hash")
        _require(replayed_hash == expected_hash, f"event {index} replay hash")
        replayed_event_hashes.append(replayed_hash)

    _require(
        matrix["uncertainty_replay"]["all_enclosure_event_hashes"] == replayed_event_hashes,
        "uncertainty replay event-hash order",
    )

    print(f"AUTHORITY_HASH={authority_hash}")
    print(f"QUALIFICATION_MATRIX_HASH={matrix_hash}")
    for index, event_hash in enumerate(replayed_event_hashes, 1):
        print(f"EVENT_HASH[{index}]={event_hash}")
    print("ALL_REPLAY_PASS=true")


if __name__ == "__main__":
    main()
