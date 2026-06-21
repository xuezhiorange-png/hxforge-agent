from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4


class Clock(Protocol):
    """Protocol for obtaining the current time."""

    def utcnow(self) -> datetime: ...


class IdGenerator(Protocol):
    """Protocol for generating unique identifiers."""

    def new_id(self) -> UUID: ...


# ---------------------------------------------------------------------------
# Production implementations
# ---------------------------------------------------------------------------


class SystemClock:
    """Clock backed by the system clock (UTC)."""

    def utcnow(self) -> datetime:
        return datetime.now(UTC)


class Uuid4Generator:
    """ID generator using uuid4()."""

    def new_id(self) -> UUID:
        return uuid4()


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class FixedClock:
    """Deterministic clock for testing.

    Call ``advance()`` or ``set_time()`` to control the reported time.
    """

    def __init__(self, initial: datetime | None = None) -> None:
        self._time: datetime = initial or datetime(2024, 1, 1, tzinfo=UTC)

    def utcnow(self) -> datetime:
        return self._time

    def advance(self, **kwargs: int) -> datetime:
        """Advance the clock by the given delta (e.g. ``hours=1``)."""
        from datetime import timedelta

        self._time = self._time + timedelta(**kwargs)
        return self._time

    def set_time(self, dt: datetime) -> None:
        """Set the clock to an explicit time."""
        if dt.tzinfo is None:
            raise ValueError("datetime must be timezone-aware (use UTC)")
        self._time = dt


class FixedIdGenerator:
    """Deterministic ID generator for testing.

    Generates sequential IDs (1, 2, 3, …) by default, or you can
    provide an explicit sequence.
    """

    def __init__(self, ids: list[UUID] | None = None) -> None:
        self._ids = list(ids) if ids is not None else []
        self._counter = 0

    def new_id(self) -> UUID:
        if self._counter < len(self._ids):
            result = self._ids[self._counter]
        else:
            result = UUID(int=self._counter + 1)
        self._counter += 1
        return result


__all__ = [
    "Clock",
    "FixedClock",
    "FixedIdGenerator",
    "IdGenerator",
    "SystemClock",
    "Uuid4Generator",
]
