"""Shared pytest runner that captures real resource telemetry.

P0-4: Strict telemetry:
  - execution_status field (completed/timeout/collection-error)
  - junit_parse_status (available/unavailable)
  - counts_authoritative flag
  - count consistency verification
  - RUSAGE_CHILDREN with explicit failure status
  - Fail-closed on resource unavailable when contract requires it
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


def _parse_junit(junit_path: Path) -> tuple[dict[str, int], str]:
    """Parse JUnit XML and extract test counts.

    Returns (counts_dict, parse_status).
    """
    counts = {
        "tests_collected": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_skipped": 0,
        "tests_xfailed": 0,
        "tests_xpassed": 0,
    }
    if not junit_path.exists():
        return counts, "unavailable"
    try:
        root = ET.parse(junit_path).getroot()
        # pytest writes <testsuites> wrapper; the counts are on the child <testsuite>
        suite = root.find("testsuite") if root.tag == "testsuites" else root
        counts["tests_collected"] = int(suite.attrib.get("tests", 0)) if suite is not None else 0
        for tc in (suite if suite is not None else root).iter("testcase"):
            is_failure = tc.find("failure") is not None
            is_error = tc.find("error") is not None
            skipped_el = tc.find("skipped")
            is_skipped = skipped_el is not None

            if is_skipped:
                message = skipped_el.attrib.get("message", "") if skipped_el is not None else ""
                msg_lower = message.lower()
                if "xfail" in msg_lower:
                    counts["tests_xfailed"] += 1
                else:
                    counts["tests_skipped"] += 1
            elif is_failure or is_error:
                counts["tests_failed"] += 1
            else:
                counts["tests_passed"] += 1
        return counts, "available"
    except (ET.ParseError, OSError):
        return counts, "unavailable"


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
    """Run pytest as subprocess and generate real telemetry."""
    junit = Path(junit_path)
    telemetry = Path(telemetry_path)
    stdout_file = Path(stdout_path)
    stderr_file = Path(stderr_path)

    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    cmd = [sys.executable, "-m", "pytest"] + pytest_args

    exit_code = -1
    result_stdout = ""
    result_stderr = ""
    resource_status = "available"
    resource_error = ""
    execution_status = "completed"

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
        result_stdout = result.stdout
        result_stderr = result.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = -9
        execution_status = "timeout"
        stdout_raw = exc.stdout or b""
        stderr_raw = exc.stderr or b""
        if isinstance(stdout_raw, bytes):
            stdout_raw = stdout_raw.decode("utf-8", errors="replace")
        if isinstance(stderr_raw, bytes):
            stderr_raw = stderr_raw.decode("utf-8", errors="replace")
        result_stdout = stdout_raw
        result_stderr = stderr_raw + f"\nTIMEOUT after {timeout}s"
    except Exception:
        exit_code = -1
        execution_status = "internal-error"
        result_stdout = ""
        result_stderr = "Runner internal error"
    end_time = time.monotonic()

    stdout_file.write_text(result_stdout, encoding="utf-8")
    stderr_file.write_text(result_stderr, encoding="utf-8")

    # Resource usage
    cpu_user = 0.0
    cpu_sys = 0.0
    peak_rss = 0
    try:
        r = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu_user = r.ru_utime
        cpu_sys = r.ru_stime
        peak_rss = r.ru_maxrss
    except (OSError, ValueError) as exc:
        resource_status = "unavailable"
        resource_error = str(exc)

    wall_clock = round(end_time - start_time, 3)

    # Parse JUnit — fail-closed
    junit_counts, junit_parse_status = _parse_junit(junit)

    # P0-4: Count consistency verification
    expected_total = (
        junit_counts["tests_passed"]
        + junit_counts["tests_failed"]
        + junit_counts["tests_skipped"]
        + junit_counts["tests_xfailed"]
        + junit_counts["tests_xpassed"]
    )
    counts_authoritative = (
        junit_parse_status == "available" and junit_counts["tests_collected"] == expected_total
    )

    # Detect collection error: exit code 2 or no tests collected with non-zero exit
    if (
        exit_code == 2
        and junit_counts["tests_collected"] == 0
        or junit_parse_status == "unavailable"
        and exit_code != 0
    ):
        execution_status = "collection-error"

    telemetry_data: dict[str, Any] = {
        "track": track,
        "commit_sha": commit_sha,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "python_version": python_version,
        "shard": shard,
        "execution_status": execution_status,
        "wall_clock_seconds": wall_clock,
        "cpu_user_seconds": round(cpu_user, 6),
        "cpu_system_seconds": round(cpu_sys, 6),
        "peak_rss_kb": peak_rss,
        "resource_measurement_status": resource_status,
        "resource_measurement_error": resource_error if resource_error else None,
        "pytest_exit_code": exit_code,
        "junit_parse_status": junit_parse_status,
        "counts_authoritative": counts_authoritative,
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
    pytest_args = sys.argv[1:]

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
