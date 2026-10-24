"""Frozen R5 n=2 mesh metrics (read-only)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

R5_EVIDENCE_DIR = Path(__file__).resolve().parents[2] / (
    "docs/tasks/evidence/V07-GENERAL-RATING-MESH-N2-AND-PERFORMANCE-R5"
)
R5_MESH_PATH = R5_EVIDENCE_DIR / "MESH_N2_RESULT.json"

R5_FROZEN_MESH_HASH = "d6c6f4d17bd9d023dda36501b712e05015ceb369916e06da1fde995deac10a7e"
R5_FROZEN_DUTY_W = Decimal("45868.2439988560625")
R5_FROZEN_ENERGY_RESIDUAL_W = Decimal("1.375E-10")
R5_FROZEN_TERMINAL_RESIDUAL_K = Decimal("6.11116E-9")
R5_FROZEN_TASK172_EVAL_COUNT = 8055
R5_FROZEN_WALL_SECONDS = Decimal("437.427")


@dataclass(frozen=True)
class FrozenR5N2Mesh:
    mesh_level: int
    mesh_result_hash: str
    total_duty_w: Decimal
    energy_balance_residual_w: Decimal
    terminal_boundary_residual_k: Decimal
    task172_local_evaluation_count: int
    wall_seconds: Decimal
    source_path: str


def load_frozen_r5_n2_mesh() -> FrozenR5N2Mesh:
    if not R5_MESH_PATH.is_file():
        raise FileNotFoundError(f"missing frozen R5 mesh evidence: {R5_MESH_PATH}")
    payload = json.loads(R5_MESH_PATH.read_text(encoding="utf-8"))
    mesh_hash = payload["mesh_result_hash"]
    if mesh_hash != R5_FROZEN_MESH_HASH:
        raise ValueError(f"R5 mesh hash drift: file={mesh_hash} expected={R5_FROZEN_MESH_HASH}")
    return FrozenR5N2Mesh(
        mesh_level=int(payload["mesh_level"]),
        mesh_result_hash=mesh_hash,
        total_duty_w=Decimal(str(payload["total_duty_w"])),
        energy_balance_residual_w=Decimal(str(payload["energy_balance_residual_w"])),
        terminal_boundary_residual_k=Decimal(str(payload["terminal_boundary_residual_k"])),
        task172_local_evaluation_count=int(payload["task172_local_evaluation_count"]),
        wall_seconds=Decimal(str(payload["wall_seconds"])),
        source_path=str(R5_MESH_PATH),
    )
