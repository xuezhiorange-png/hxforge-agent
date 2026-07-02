"""Shared pytest runner that captures real resource telemetry.

P0-5: Telemetry fail-closed — runner exits non-zero if not authoritative.
P1: Integrates outcome plugin for structured xfail/xpass.
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
    """Parse JUnit XML. Returns (counts, parse_status)."""
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
        # Read from <testsuite> child element (pytest writes count there)
        suite = root.find("testsuite")
        if suite is not None:
            counts["tests_collected"] = int(suite.attrib.get("tests", 0))
        else:
            counts["tests_collected"] = int(root.attrib.get("tests", 0))
        for tc in root.iter("testcase"):
            is_failure = tc.find("failure") is not None
            is_error = tc.find("error") is not None
            skipped_el = tc.find("skipped")
            is_skipped = skipped_el is not None

            if is_skipped:
                message = skipped_el.attrib.get("message", "") if skipped_el is not None else ""
                if "xfail" in message.lower():
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


def _read_outcomes(outcomes_path: Path) -> dict[str, Any] | None:
    """Read structured outcome JSON if present."""
    if not outcomes_path.is_file():
        return None
    try:
        return json.loads(outcomes_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def run_pytest(
    pytest_args: list[str],
    *,
    env: dict[str, str] | None = None,
    timeout: int = 600,
    junit_path: str | Path = "junit.xml",
    telemetry_path: str | Path = "resource-telemetry.json",
    stdout_path: str | Path = "pytest-stdout.txt",
    stderr_path: str | Path = "pytest-stderr.txt",
    outcomes_path: str | Path = "pytest-outcomes.json",
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

    # Add outcome plugin
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "tests.ci.outcome_plugin",
        f"--hx-outcome-output={outcomes_path}",
    ] + pytest_args

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

    # Parse JUnit
    junit_counts, junit_parse_status = _parse_junit(junit)

    # Count consistency
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

    if (
        exit_code == 2
        and junit_counts["tests_collected"] == 0
        or junit_parse_status == "unavailable"
        and exit_code != 0
    ):
        execution_status = "collection-error"

    # P0-5: Compute producer_authoritative
    authority_failures: list[str] = []
    if execution_status != "completed":
        authority_failures.append(f"execution_status={execution_status}")
    if junit_parse_status != "available":
        authority_failures.append("junit_parse_status=unavailable")
    if not counts_authoritative:
        authority_failures.append("counts_authoritative=false")
    if resource_status != "available":
        authority_failures.append("resource_measurement_status=unavailable")
    if exit_code != 0:
        authority_failures.append(f"pytest_exit_code={exit_code}")

    producer_authoritative = len(authority_failures) == 0

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
        "producer_authoritative": producer_authoritative,
        "producer_authority_failures": authority_failures,
        "tests_collected": junit_counts["tests_collected"],
        "tests_passed": junit_counts["tests_passed"],
        "tests_failed": junit_counts["tests_failed"],
        "tests_skipped": junit_counts["tests_skipped"],
        "tests_xfailed": junit_counts["tests_xfailed"],
        "tests_xpassed": junit_counts["tests_xpassed"],
    }

    # Add behavior fingerprint if available
    beh_path = Path("behavior-environment.json")
    if beh_path.is_file():
        try:
            beh = json.loads(beh_path.read_text(encoding="utf-8"))
            digest = beh.get("canonical_json_sha256", "")
            if digest.startswith("sha256:"):
                telemetry_data["behavior_fingerprint_sha256"] = digest[7:]
        except (json.JSONDecodeError, OSError):
            pass

    telemetry.write_text(
        json.dumps(telemetry_data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # P0-5: Exit non-zero if not authoritative
    if not producer_authoritative and exit_code == 0:
        return 1

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
        outcomes_path="pytest-outcomes.json",
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
