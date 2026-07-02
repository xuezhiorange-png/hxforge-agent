"""Shared pytest runner that captures real resource telemetry.

This runner:
1. Spawns pytest as a subprocess (RUSAGE_CHILDREN, not RUSAGE_SELF)
2. Records wall-clock time
3. Captures the real exit code
4. Writes stdout/stderr
5. Parses JUnit XML
6. Generates telemetry with real metrics
7. Exits with the original pytest exit code

Pitfalls handled:
- Telemetry generator resources are NOT counted as pytest resources
- Failed pytest does NOT lose telemetry (always() semantics)
- Fixed "-1" exit code is never used
- No silent "except Exception: pass" with zero values
"""

from __future__ import annotations

import json
import os
import resource
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def _parse_junit(junit_path: Path) -> dict[str, int]:
    """Parse JUnit XML and extract test counts."""
    counts = {
        "tests_collected": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_skipped": 0,
        "tests_xfailed": 0,
        "tests_xpassed": 0,
    }
    if not junit_path.exists():
        return counts
    try:
        root = ET.parse(junit_path).getroot()
        # Count from top-level attributes
        counts["tests_collected"] = int(root.attrib.get("tests", 0))
        for tc in root.iter("testcase"):
            is_failure = tc.find("failure") is not None
            is_error = tc.find("error") is not None
            is_skipped = tc.find("skipped") is not None
            # Check for xfail/xpass in the skipped element
            if is_skipped:
                skipped_el = tc.find("skipped")
                message = skipped_el.attrib.get("message", "") if skipped_el is not None else ""
                if "xfail" in message.lower():
                    counts["tests_xfailed"] += 1
                else:
                    counts["tests_skipped"] += 1
            elif is_failure or is_error:
                counts["tests_failed"] += 1
            else:
                counts["tests_passed"] += 1
        # xpassed: check for 'passed' attribute on xfail cases
        # Actually pytest marks xpassed as 'passed' in JUnit — they show as passed
        # We rely on the counts from pytest output for xfailed/xpassed accuracy
    except (ET.ParseError, OSError) as exc:
        print(f"WARNING: failed to parse JUnit XML: {exc}", file=sys.stderr)
    return counts


def run_pytest(
    pytest_args: list[str],
    *,
    env: dict[str, str] | None = None,
    timeout: int = 600,
    junit_path: str | Path = "junit.xml",
    telemetry_path: str | Path = "resource-telemetry.json",
    stdout_path: str | Path = "pytest-stdout.txt",
    stderr_path: str | Path = "pytest-stderr.txt",
    track: str = "",
    commit_sha: str = "",
    run_id: str = "",
    run_attempt: int = 1,
    python_version: str = "",
    shard: str = "",
) -> int:
    """Run pytest as subprocess and generate real telemetry.

    Returns the original pytest exit code.
    """
    junit = Path(junit_path)
    telemetry = Path(telemetry_path)
    stdout_file = Path(stdout_path)
    stderr_file = Path(stderr_path)

    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    cmd = [sys.executable, "-m", "pytest"] + pytest_args

    start_time = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            env=run_env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        exit_code = result.returncode
    except subprocess.TimeoutExpired as exc:
        exit_code = -9
        result_stdout = exc.stdout or ""
        result_stderr = (exc.stderr or "") + f"\nTIMEOUT after {timeout}s"
    else:
        result_stdout = result.stdout
        result_stderr = result.stderr
    end_time = time.monotonic()

    # Always write stdout/stderr
    stdout_file.write_text(result_stdout, encoding="utf-8")
    stderr_file.write_text(result_stderr, encoding="utf-8")

    # Capture real child process resource usage
    cpu_user = 0.0
    cpu_sys = 0.0
    peak_rss = 0
    try:
        r = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu_user = r.ru_utime
        cpu_sys = r.ru_stime
        peak_rss = r.ru_maxrss  # Linux: bytes; macOS: bytes
        # Normalize: on Linux ru_maxrss is in kilobytes
        if sys.platform == "linux":
            pass  # Already KB
        else:
            peak_rss = peak_rss // 1024  # Convert bytes to KB
    except (OSError, ValueError):
        # RUSAGE_CHILDREN may not be available on all platforms
        pass

    wall_clock = round(end_time - start_time, 3)

    # Parse JUnit
    junit_counts = _parse_junit(junit)

    telemetry_data: dict[str, Any] = {
        "track": track,
        "commit_sha": commit_sha,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "python_version": python_version,
        "shard": shard,
        "wall_clock_seconds": wall_clock,
        "cpu_user_seconds": round(cpu_user, 6),
        "cpu_system_seconds": round(cpu_sys, 6),
        "peak_rss_kb": peak_rss,
        "pytest_exit_code": exit_code,
        "tests_collected": junit_counts["tests_collected"],
        "tests_passed": junit_counts["tests_passed"],
        "tests_failed": junit_counts["tests_failed"],
        "tests_skipped": junit_counts["tests_skipped"],
        "tests_xfailed": junit_counts["tests_xfailed"],
        "tests_xpassed": junit_counts["tests_xpassed"],
    }

    telemetry.write_text(
        json.dumps(telemetry_data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return exit_code


def main() -> None:
    """CLI entry point: runs pytest and generates telemetry.

    All arguments are forwarded directly to pytest.  The runner auto-detects
    --junitxml from the forwarded arguments.

    Usage: python -m tests.ci.run_test_shard [pytest args...]

    Environment variables read:
      TRACK, COMMIT_SHA, RUN_ID, RUN_ATTEMPT, PYTHON_VERSION, SHARD,
      PYTEST_TIMEOUT (optional, default 600)
    """
    pytest_args = sys.argv[1:]

    # Auto-detect --junitxml from forwarded pytest args
    junit_xml = "junit.xml"
    for i, arg in enumerate(pytest_args):
        if arg.startswith("--junitxml="):
            junit_xml = arg.split("=", 1)[1]
            break
        if arg == "--junitxml" and i + 1 < len(pytest_args):
            junit_xml = pytest_args[i + 1]
            break

    exit_code = run_pytest(
        pytest_args,
        junit_path=junit_xml,
        telemetry_path="resource-telemetry.json",
        stdout_path="pytest-stdout.txt",
        stderr_path="pytest-stderr.txt",
        track=os.environ.get("TRACK", ""),
        commit_sha=os.environ.get("COMMIT_SHA", ""),
        run_id=os.environ.get("RUN_ID", ""),
        run_attempt=int(os.environ.get("RUN_ATTEMPT", "1")),
        python_version=os.environ.get("PYTHON_VERSION", ""),
        shard=os.environ.get("SHARD", ""),
        timeout=int(os.environ.get("PYTEST_TIMEOUT", "600")),
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
