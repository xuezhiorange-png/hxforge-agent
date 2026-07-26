"""Active-position-set fixtures for TASK-025 participation tests."""

from __future__ import annotations


def full_active() -> tuple[str, ...]:
    return tuple(f"P{i:03d}" for i in range(8))


def half_active_first() -> tuple[str, ...]:
    return tuple(f"P{i:03d}" for i in range(4))


def single_active() -> tuple[str, ...]:
    return ("P000",)


def half_active_last() -> tuple[str, ...]:
    return tuple(f"P{i:03d}" for i in range(4, 8))


__all__ = [
    "full_active",
    "half_active_first",
    "single_active",
    "half_active_last",
]
