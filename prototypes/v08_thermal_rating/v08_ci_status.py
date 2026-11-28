"""CI status helper: map delivery to the GitHub Actions run for the current HEAD SHA."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def ci_status_for_head(
    head_sha: str,
    *,
    branch: str = "cursor/v08-03-live-thermal-rating-1201",
    repo: str = "xuezhiorange-png/hxforge-agent",
) -> str:
    """Return conclusion_number, in_progress_number, or unknown for the run matching head_sha."""
    try:
        out = subprocess.check_output(
            [
                "gh",
                "run",
                "list",
                "--repo",
                repo,
                "--branch",
                branch,
                "--limit",
                "15",
                "--json",
                "conclusion,status,number,headSha",
            ],
            cwd=_REPO,
            text=True,
        )
        rows = json.loads(out)
        for row in rows:
            row_head = str(row.get("headSha", ""))
            if row_head.startswith(head_sha[:12]) or row_head == head_sha:
                num = row.get("number")
                if row.get("status") != "completed":
                    return f"in_progress_{num}"
                conclusion = row.get("conclusion") or "unknown"
                return f"{conclusion}_{num}"
        if rows and rows[0].get("status") != "completed":
            return f"no_matching_run_latest_in_progress_{rows[0].get('number')}"
        if rows:
            return f"no_matching_run_latest_{rows[0].get('conclusion')}_{rows[0].get('number')}"
        return "no_runs_found"
    except Exception as exc:
        return f"unknown_{type(exc).__name__}"


__all__ = ["ci_status_for_head"]
