"""Persist live mesh comparison receipts for second-candidate continuation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_live_ladder_continuation_r14.comparison_history_admission import (
    comparison_canonical_sha256,
)

COMPARISON_RECEIPT_SCHEMA = "task173.experimental-live-mesh-comparison-receipt.v1"
COMPARISON_PROVENANCE_AUTHORITY_V1 = (
    "V07-FAST-SOLVER-GENERAL-CANDIDATE-COMPARISON-PROVENANCE-R21C-V1"
)


def comparison_receipt_path(comparison_dir: Path, coarse_n: int, fine_n: int) -> Path:
    return comparison_dir / f"live-mesh-n{coarse_n}-to-n{fine_n}-comparison.json"


def write_comparison_receipt(
    comparison_dir: Path,
    coarse_n: int,
    fine_n: int,
    comparison: dict[str, Any],
    *,
    repo_root: Path | None = None,
    provenance_authority_id: str = COMPARISON_PROVENANCE_AUTHORITY_V1,
) -> dict[str, str]:
    comparison_dir.mkdir(parents=True, exist_ok=True)
    path = comparison_receipt_path(comparison_dir, coarse_n, fine_n)
    canonical = comparison_canonical_sha256(comparison)
    body = {
        "schema_version": COMPARISON_RECEIPT_SCHEMA,
        "provenance_authority_id": provenance_authority_id,
        "coarse_mesh_n": coarse_n,
        "fine_mesh_n": fine_n,
        "comparison": comparison,
        "comparison_canonical_sha256": canonical,
    }
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    rel_path = str(path.relative_to(repo_root)) if repo_root is not None else str(path)
    return {
        "path": rel_path,
        "sha256": digest,
        "comparison_canonical_sha256": canonical,
    }


def load_comparison_receipt(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != COMPARISON_RECEIPT_SCHEMA:
        raise ValueError("invalid comparison receipt schema")
    comparison = dict(data["comparison"])
    expected = data.get("comparison_canonical_sha256")
    actual = comparison_canonical_sha256(comparison)
    if expected != actual:
        raise ValueError("comparison canonical sha256 mismatch")
    return comparison
