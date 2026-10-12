"""Mesh replay admission for formal compare (hash + terminal + identity)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from hexagent.properties.base import PropertyProvider
from prototypes.v07_fast_solver_evidence_gate.prior_mesh_evidence import (
    verify_and_load_r6_n8_result_body,
    verify_and_load_r8_n16_result_body,
)
from prototypes.v07_fast_solver_replay_n8_r6.strict_replay import strict_replay_level

ROOT = Path(__file__).resolve().parents[2]


def _parity_label(replay_meta: dict[str, Any]) -> Literal["PASS", "FAIL"]:
    return "PASS" if replay_meta.get("hash_parity") == "PASS" else "FAIL"


def admit_n8_replay(
    provider: PropertyProvider,
    shell_authority: Any,
    *,
    rating_request_hash: str,
) -> dict[str, Any]:
    loaded = verify_and_load_r6_n8_result_body()
    path = ROOT / loaded["evidence_path"]
    replay = strict_replay_level(
        8,
        loaded["result_body"],
        path,
        provider,
        shell_authority,
        rating_request_hash=rating_request_hash,
    )
    mesh_run = replay.pop("_mesh_run")
    return {
        "subdivisions": 8,
        "hash_parity": _parity_label(replay),
        "replay": {k: v for k, v in replay.items()},
        "mesh_run": mesh_run,
        "evidence_source_commit": loaded["source_commit"],
    }


def admit_n16_replay(
    provider: PropertyProvider,
    shell_authority: Any,
    *,
    rating_request_hash: str,
) -> dict[str, Any]:
    loaded = verify_and_load_r8_n16_result_body()
    path = ROOT / loaded["evidence_path"]
    replay = strict_replay_level(
        16,
        loaded["result_body"],
        path,
        provider,
        shell_authority,
        rating_request_hash=rating_request_hash,
    )
    mesh_run = replay.pop("_mesh_run")
    return {
        "subdivisions": 16,
        "hash_parity": _parity_label(replay),
        "replay": {k: v for k, v in replay.items()},
        "mesh_run": mesh_run,
        "evidence_source_commit": loaded["source_commit"],
    }
