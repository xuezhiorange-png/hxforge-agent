"""Production frozen mesh ladder sequence guards."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.task173_integrated_rating.models import REVIEWED_MESH_SEQUENCE

PRODUCTION_MESH_SEQUENCE: tuple[int, ...] = REVIEWED_MESH_SEQUENCE


def validate_adjacent_mesh_pair(coarse_n: int, fine_n: int) -> None:
    """Reject comparisons that skip production ladder levels."""
    try:
        index = PRODUCTION_MESH_SEQUENCE.index(coarse_n)
    except ValueError:
        raise ValueError(f"coarse mesh_n={coarse_n} not in production sequence") from None
    if index + 1 >= len(PRODUCTION_MESH_SEQUENCE):
        raise ValueError(f"coarse mesh_n={coarse_n} has no successor in production sequence")
    expected_fine = PRODUCTION_MESH_SEQUENCE[index + 1]
    if fine_n != expected_fine:
        raise ValueError(
            f"non-adjacent mesh comparison coarse={coarse_n} fine={fine_n} "
            f"expected_fine={expected_fine}"
        )


def validate_run_sequence(mesh_levels: tuple[int, ...]) -> None:
    if not mesh_levels:
        return
    indices = []
    for mesh_n in mesh_levels:
        if mesh_n not in PRODUCTION_MESH_SEQUENCE:
            raise ValueError(f"mesh_n={mesh_n} not in production sequence")
        indices.append(PRODUCTION_MESH_SEQUENCE.index(mesh_n))
    for prev, curr in zip(indices, indices[1:], strict=False):
        if curr != prev + 1:
            raise ValueError(
                f"mesh ladder skip: {PRODUCTION_MESH_SEQUENCE[prev]} -> "
                f"{PRODUCTION_MESH_SEQUENCE[curr]} is not consecutive"
            )
