"""Persist live rating mesh stage receipts for downstream verification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def stage_receipt_path(stage_dir: Path, mesh_n: int) -> Path:
    return stage_dir / f"live-mesh-n{mesh_n}-receipt.json"


def write_stage_receipt(
    stage_dir: Path,
    mesh_n: int,
    receipt: dict[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, str]:
    stage_dir.mkdir(parents=True, exist_ok=True)
    path = stage_receipt_path(stage_dir, mesh_n)
    body = {
        "schema_version": "task173.experimental-live-mesh-stage-receipt.v1",
        "mesh_n": mesh_n,
        "receipt": receipt,
    }
    path.write_text(json.dumps(body, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    rel_path = str(path.relative_to(repo_root)) if repo_root is not None else str(path)
    return {"path": rel_path, "sha256": digest}


def load_stage_receipt(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != "task173.experimental-live-mesh-stage-receipt.v1":
        raise ValueError("invalid stage receipt schema")
    return data["receipt"]
