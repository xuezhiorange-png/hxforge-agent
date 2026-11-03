"""Batch-append outer trial JSONL receipts (not a solver state store)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class OuterTrialJsonlWriter:
    def __init__(
        self,
        path: Path,
        *,
        batch_size: int = 5,
        flush_interval_s: float = 60.0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.path = path
        self.batch_size = batch_size
        self.flush_interval_s = flush_interval_s
        self.metadata = metadata or {}
        self._buffer: list[dict[str, Any]] = []
        self._last_flush = time.monotonic()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            header = {
                "schema_version": "task173.experimental-live-outer-trial-jsonl.v1",
                "metadata": self.metadata,
            }
            self.path.write_text(json.dumps(header) + "\n", encoding="utf-8")

    def append(self, receipt: dict[str, Any]) -> None:
        self._buffer.append(receipt)
        should_flush = len(self._buffer) >= self.batch_size or (
            time.monotonic() - self._last_flush >= self.flush_interval_s
        )
        if should_flush:
            self.flush()

    def flush(self) -> None:
        if not self._buffer:
            return
        with self.path.open("a", encoding="utf-8") as handle:
            for item in self._buffer:
                handle.write(json.dumps(item, sort_keys=True) + "\n")
        self._buffer.clear()
        self._last_flush = time.monotonic()
