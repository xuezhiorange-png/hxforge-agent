"""Frozen R4 n=1 mesh metrics (read-only; do not re-run n=1 for evidence)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

R4_EVIDENCE_DIR = Path(__file__).resolve().parents[2] / (
    "docs/tasks/evidence/V07-GENERAL-RATING-POSITIVE-DUTY-CELL-AND-FIRST-MESH-R4"
)
R4_LOW_MESH_PATH = R4_EVIDENCE_DIR / "LOW_MESH_RESULT.json"

R4_FROZEN_CANDIDATE_ID = "82f370ff-73cd-5d71-aaf9-efc51645d22e"
R4_FROZEN_MESH_HASH = "4783f217d659e86290a8ae1aa9d9f062d9c327b8be61c0a4969949e3411df46a"
R4_FROZEN_DUTY_W = Decimal("45875.884128245187")
R4_FROZEN_ENERGY_RESIDUAL_W = Decimal("1.6E-10")
R4_FROZEN_TERMINAL_RESIDUAL_K = Decimal("2.4524E-9")
R4_FROZEN_TASK172_EVAL_COUNT = 4580
R4_FROZEN_WALL_SECONDS = Decimal("229.68")


@dataclass(frozen=True)
class FrozenR4N1Mesh:
    candidate_id: str
    mesh_level: int
    mesh_result_hash: str
    total_duty_w: Decimal
    energy_balance_residual_w: Decimal
    terminal_boundary_residual_k: Decimal
    task172_local_evaluation_count: int
    wall_seconds: Decimal
    source_path: str


def load_frozen_r4_n1_mesh() -> FrozenR4N1Mesh:
    """Load and verify frozen R4 n=1 mesh record against committed constants."""
    if not R4_LOW_MESH_PATH.is_file():
        raise FileNotFoundError(f"missing frozen R4 mesh evidence: {R4_LOW_MESH_PATH}")
    payload = json.loads(R4_LOW_MESH_PATH.read_text(encoding="utf-8"))
    mesh_hash = payload["mesh_result_hash"]
    if mesh_hash != R4_FROZEN_MESH_HASH:
        raise ValueError(f"R4 mesh hash drift: file={mesh_hash} expected={R4_FROZEN_MESH_HASH}")
    duty = Decimal(str(payload["total_duty_w"]))
    if duty != R4_FROZEN_DUTY_W:
        raise ValueError(f"R4 duty drift: file={duty} expected={R4_FROZEN_DUTY_W}")
    return FrozenR4N1Mesh(
        candidate_id=R4_FROZEN_CANDIDATE_ID,
        mesh_level=int(payload["mesh_level"]),
        mesh_result_hash=mesh_hash,
        total_duty_w=duty,
        energy_balance_residual_w=Decimal(str(payload["energy_balance_residual_w"])),
        terminal_boundary_residual_k=Decimal(str(payload["terminal_boundary_residual_k"])),
        task172_local_evaluation_count=int(payload["task172_local_evaluation_count"]),
        wall_seconds=Decimal(str(payload["wall_seconds"])),
        source_path=str(R4_LOW_MESH_PATH),
    )
