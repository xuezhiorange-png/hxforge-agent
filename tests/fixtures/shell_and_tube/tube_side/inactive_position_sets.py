"""Inactive-position-set fixtures for TASK-025 participation tests.

Each function returns the complement of the matching ``active_position_sets``
fixture against the default 8-position layout.
"""

from __future__ import annotations


def full_inactive() -> tuple[str, ...]:
    return ()


def half_inactive_first() -> tuple[str, ...]:
    return tuple(f"P{i:03d}" for i in range(4, 8))


def single_inactive() -> tuple[str, ...]:
    return tuple(f"P{i:03d}" for i in range(1, 8))


def half_inactive_last() -> tuple[str, ...]:
    return tuple(f"P{i:03d}" for i in range(4))


__all__ = [
    "full_inactive",
    "half_inactive_first",
    "single_inactive",
    "half_inactive_last",
]
