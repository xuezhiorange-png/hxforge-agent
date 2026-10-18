"""Push trial JSONL batches to GitHub during long live workers."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Callable


def git_push_paths(
    root: Path,
    branch: str,
    message: str,
    paths: list[Path],
) -> str | None:
    rel_paths = [str(p.relative_to(root)) for p in paths if p.exists()]
    if not rel_paths:
        return None
    try:
        subprocess.run(["git", "add", *rel_paths], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", message], cwd=root, check=True, capture_output=True)
        subprocess.run(
            ["git", "push", "-u", "origin", branch],
            cwd=root,
            check=True,
            capture_output=True,
        )
        rev = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        return rev.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


class TrialJsonlPushMonitor:
    """Poll a trials JSONL file while a child worker runs and push completed batches."""

    def __init__(
        self,
        *,
        root: Path,
        branch: str,
        trials_path: Path,
        push_fn: Callable[[str, list[Path]], str | None] | None = None,
        poll_interval_s: float = 30.0,
        min_new_lines: int = 5,
    ) -> None:
        self.root = root
        self.branch = branch
        self.trials_path = trials_path
        self.poll_interval_s = poll_interval_s
        self.min_new_lines = min_new_lines
        self._last_size = 0
        self._last_push = time.monotonic()
        self._push_count = 0
        self._last_remote_sha: str | None = None
        if push_fn is None:
            push_fn = lambda msg, paths: git_push_paths(root, branch, msg, paths)
        self._push_fn = push_fn

    @property
    def last_remote_sha(self) -> str | None:
        return self._last_remote_sha

    @property
    def push_count(self) -> int:
        return self._push_count

    def maybe_push(self, *, force: bool = False) -> str | None:
        if not self.trials_path.is_file():
            return None
        size = self.trials_path.stat().st_size
        new_bytes = size - self._last_size
        elapsed = time.monotonic() - self._last_push
        if not force and new_bytes <= 0:
            return None
        line_growth = max(0, new_bytes // 80)
        if not force and line_growth < self.min_new_lines and elapsed < 60.0:
            return None
        sha = self._push_fn(
            f"R17 trial batch {self._push_count + 1}",
            [self.trials_path],
        )
        if sha:
            self._last_remote_sha = sha
            self._push_count += 1
            self._last_size = size
            self._last_push = time.monotonic()
        return sha

    def wait_while_process_alive(self, process: object, *, budget_s: float, grace_s: float) -> None:
        deadline = time.monotonic() + budget_s + grace_s
        while getattr(process, "is_alive", lambda: False)():
            if time.monotonic() >= deadline:
                break
            process.join(timeout=self.poll_interval_s)  # type: ignore[attr-defined]
            self.maybe_push()
        self.maybe_push(force=True)
