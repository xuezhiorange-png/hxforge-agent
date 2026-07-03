"""Shared pytest runner that captures real resource telemetry.

P0-5: Telemetry fail-closed — runner exits non-zero if not authoritative.
P0-2: Consumes structured pytest outcomes as counting authority.
P0-7: Cross-validates outcomes vs JUnit vs node inventory.
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

_OUTCOME_VALID_VALUES = frozenset({"passed", "failed", "skipped", "xfailed", "xpassed"})


def _read_node_inventory(inventory_path: Path) -> dict[str, Any] | None:
    """Read and validate node-inventory.json. Returns validated dict or None."""
    if not inventory_path.is_file():
        return None
    try:
        raw = json.loads(inventory_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(raw, dict):
        return None
    node_ids = raw.get("node_ids")
    if not isinstance(node_ids, list):
        return None
    if raw.get("node_count") != len(node_ids):
        return None
    return raw


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


def _read_and_validate_outcomes(
    outcomes_path: Path,
    *,
    node_inventory_path: Path | None = None,
) -> dict[str, Any] | None:
    """Read, parse, and validate structured outcome JSON.

    P0-3: When node_inventory_path is provided, enforces strict set equality
    between outcomes keys, collection_complete list, and node_inventory.node_ids.

    Returns validated outcomes dict or None if invalid/missing.
    Validation is strict — any schema violation returns None.
    """
    if not outcomes_path.is_file():
        return None
    try:
        raw = json.loads(outcomes_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    # Schema validation — fail closed
    if not isinstance(raw, dict):
        return None
    if raw.get("schema_version") != "1":
        return None
    outcomes_map = raw.get("outcomes")
    if not isinstance(outcomes_map, dict):
        return None
    if not isinstance(raw.get("total"), int):
        return None
    if raw["total"] != len(outcomes_map):
        return None

    # Validate every outcome value and collect unique node IDs
    for node_id, outcome_val in outcomes_map.items():
        if not isinstance(node_id, str) or not node_id:
            return None
        if outcome_val not in _OUTCOME_VALID_VALUES:
            return None

    # Validate collection_complete: must be list of strings, unique, non-empty
    cc = raw.get("collection_complete")
    if not isinstance(cc, list):
        return None
    for item in cc:
        if not isinstance(item, str) or not item:
            return None
    if len(cc) != len(set(cc)):
        return None  # duplicates in collection_complete

    # P0-3: Exact 3-way node set equality
    outcome_node_ids = set(outcomes_map.keys())
    cc_node_ids = set(cc)

    if outcome_node_ids != cc_node_ids:
        return None

    if node_inventory_path is not None:
        inv = _read_node_inventory(node_inventory_path)
        if inv is not None:
            # Only cross-validate if file exists and is valid
            inv_node_ids = set(inv["node_ids"])
            if inv_node_ids != outcome_node_ids:
                return None

    return raw


def _aggregate_outcomes(outcomes_data: dict[str, Any]) -> dict[str, int]:
    """Aggregate outcome counts from validated outcome data."""
    outcomes_map = outcomes_data["outcomes"]
    counts = {
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_skipped": 0,
        "tests_xfailed": 0,
        "tests_xpassed": 0,
    }
    for outcome_val in outcomes_map.values():
        key = f"tests_{outcome_val}"
        if key in counts:
            counts[key] += 1
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
    outcomes_path: str | Path = "pytest-outcomes.json",
    node_inventory_path: str | Path = "node-inventory.json",
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
    outcomes_file = Path(outcomes_path)
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

    # Parse and validate structured outcomes (P0-2)
    # P0-3: Also cross-validate against node-inventory (if present alongside outcomes)
    effective_inv_path: Path | None = None
    if node_inventory_path:
        inv_candidate = Path(node_inventory_path)
        # Resolve relative to outcomes file directory to avoid stale repo-root files
        if not inv_candidate.is_absolute():
            inv_candidate = outcomes_file.parent / inv_candidate
        if inv_candidate.is_file():
            effective_inv_path = inv_candidate
    outcomes_data = _read_and_validate_outcomes(
        outcomes_file, node_inventory_path=effective_inv_path
    )
    outcome_parse_status = "available" if outcomes_data is not None else "unavailable"
    outcome_counts = _aggregate_outcomes(outcomes_data) if outcomes_data is not None else None

    # ── Cross-validate outcomes vs JUnit (P0-4: XPASS-safe) ────────────────
    # Structured outcomes are the five-category authority.
    # JUnit proves: XML exists, testcase total is correct, and
    # failure/error count is consistent.  Per-category equality for
    # passed/xpassed/skipped/xfailed is NOT checked because the JUnit
    # parser cannot reliably distinguish XPASS from normal pass.
    counts_authoritative = False
    counts_mismatch_detail = ""

    if outcome_parse_status == "available" and junit_parse_status == "available":
        assert outcome_counts is not None  # for type checker
        outcomes_total = outcomes_data["total"]  # type: ignore[union-attr]
        junit_total = junit_counts["tests_collected"]

        # Check 1: outcomes total == JUnit collected
        if outcomes_total != junit_total:
            counts_mismatch_detail = (
                f"outcomes_total={outcomes_total} != junit_collected={junit_total}"
            )
        # Check 2: JUnit failure+error count <= structured failed count
        # (XPASS with strict mode becomes a JUnit failure, so structured
        # failed can be >= JUnit failed+error, never less)
        else:
            junit_fail_or_error = junit_counts["tests_failed"]
            structured_failed = outcome_counts["tests_failed"]
            if junit_fail_or_error > structured_failed:
                counts_mismatch_detail = (
                    f"junit_fail_or_error={junit_fail_or_error} > "
                    f"structured_failed={structured_failed}"
                )
            else:
                counts_authoritative = True
    elif outcome_parse_status == "unavailable":
        counts_mismatch_detail = "outcome artifact missing or invalid"
    elif junit_parse_status == "unavailable":
        counts_mismatch_detail = "JUnit unavailable"

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
    if outcome_parse_status != "available":
        authority_failures.append("outcome_parse_status=unavailable")
    if not counts_authoritative:
        authority_failures.append(f"counts_authoritative=false: {counts_mismatch_detail}")
    if resource_status != "available":
        authority_failures.append("resource_measurement_status=unavailable")
    if exit_code != 0:
        authority_failures.append(f"pytest_exit_code={exit_code}")

    producer_authoritative = len(authority_failures) == 0

    # Use outcome counts as the counting authority when available (P0-2)
    if outcome_counts is not None:
        final_counts = outcome_counts
    else:
        final_counts = {
            "tests_passed": junit_counts["tests_passed"],
            "tests_failed": junit_counts["tests_failed"],
            "tests_skipped": junit_counts["tests_skipped"],
            "tests_xfailed": junit_counts["tests_xfailed"],
            "tests_xpassed": junit_counts["tests_xpassed"],
        }

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
        "outcome_parse_status": outcome_parse_status,
        "counts_authoritative": counts_authoritative,
        "counts_mismatch_detail": counts_mismatch_detail if counts_mismatch_detail else None,
        "producer_authoritative": producer_authoritative,
        "producer_authority_failures": authority_failures,
        "tests_collected": junit_counts["tests_collected"],
        "tests_passed": final_counts["tests_passed"],
        "tests_failed": final_counts["tests_failed"],
        "tests_skipped": final_counts["tests_skipped"],
        "tests_xfailed": final_counts["tests_xfailed"],
        "tests_xpassed": final_counts["tests_xpassed"],
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
        diag = (
            f"RUNNER: non-authoritative telemetry, returning 1.\n"
            f"  failures={authority_failures}\n"
            f"  exit={exit_code} exec={execution_status}\n"
            f"  junit={junit_parse_status} outcome={outcome_parse_status}\n"
            f"  resource={resource_status}\n"
            f"  collected={junit_counts['tests_collected']}\n"
            f"  passed={final_counts['tests_passed']} failed={final_counts['tests_failed']}\n"
            f"  cnt_auth={counts_authoritative} mismatch={counts_mismatch_detail}"
        )
        # Write to both stderr and diagnostic file for CI visibility
        import contextlib
        import sys as _sys

        print(diag, file=_sys.stderr)
        with contextlib.suppress(OSError):
            Path("runner-diagnostic.txt").write_text(diag + "\n", encoding="utf-8")
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

    # Extract --hx-node-output path for cross-validation with outcomes
    node_inv_path = "node-inventory.json"
    for i, arg in enumerate(pytest_args):
        if arg.startswith("--hx-node-output="):
            node_inv_path = arg.split("=", 1)[1]
            break
        if arg == "--hx-node-output" and i + 1 < len(pytest_args):
            node_inv_path = pytest_args[i + 1]
            break

    exit_code = run_pytest(
        pytest_args,
        junit_path=junit_xml,
        telemetry_path="resource-telemetry.json",
        stdout_path="pytest-stdout.txt",
        stderr_path="pytest-stderr.txt",
        outcomes_path="pytest-outcomes.json",
        node_inventory_path=node_inv_path,
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
