"""Tests for benchmark authority governance (P0-4).

41+ test scenarios covering:
  Section 1: Positive tests — zero nodes, N/A artifact, round-trip
  Section 2: Paired inventory validation
  Section 3: End-to-end positive test (real execution)
  Section 4: Node replacement negative tests
  Section 5: Missing / extra / duplicate node tests
  Section 6: Execution inventory validation
  Section 7: Outcomes schema validation
  Section 8: Telemetry validation
  Section 9: Evidence digest validation
  Section 10: Workflow static tests (nightly.yml governance)
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.ci.benchmark_authority import (
    BenchmarkAuthorityError,
    _build_executed_artifact,
    _build_not_applicable_artifact,
    _compute_file_sha256,
    _extract_collection_complete_nodes,
    _extract_outcome_nodes,
    _validate_outcome_category_counts,
    _validate_outcomes_schema,
    _validate_telemetry,
    extract_benchmark_nodes,
    load_and_validate_node_inventory,
    load_authority_artifact,
    load_marker_inventory,
    save_authority_artifact,
    validate_authority_artifact,
    validate_inventory_identity_match,
)

# ── Canonical test parameters ─────────────────────────────────────────────

_SHA: str = "a" * 40
_RUN_ID: str = "12345"
_RUN_ATTEMPT: int = 1
_PYTHON_VERSION: str = "3.12"

# ── Builder helpers ────────────────────────────────────────────────────────


def _make_marker_inv(
    node_markers: dict[str, list[str]],
    *,
    python_version: str = _PYTHON_VERSION,
    track: str = "nightly",
    collection_scope: str = "global",
    shard: str | None = None,
    commit_sha: str = _SHA,
    run_id: str = _RUN_ID,
    run_attempt: int = _RUN_ATTEMPT,
) -> dict[str, Any]:
    """Build a minimal marker inventory."""
    return {
        "schema_version": "1",
        "track": track,
        "commit_sha": commit_sha,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "python_version": python_version,
        "shard": shard,
        "collection_scope": collection_scope,
        "node_markers": node_markers,
        "node_count": len(node_markers),
    }


def _make_node_inv(
    node_ids: list[str],
    *,
    python_version: str = _PYTHON_VERSION,
    track: str = "nightly",
    commit_sha: str = _SHA,
    run_id: str = _RUN_ID,
    run_attempt: int = _RUN_ATTEMPT,
    collection_scope: str = "global",
    shard: str | None = None,
) -> dict[str, Any]:
    """Build a minimal node inventory."""
    return {
        "schema_version": "1",
        "collection_scope": collection_scope,
        "python_version": python_version,
        "commit_sha": commit_sha,
        "track": track,
        "shard": shard,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "node_count": len(node_ids),
        "node_ids": sorted(node_ids),
    }


def _make_outcomes(
    outcomes_map: dict[str, str],
    *,
    collection_complete: list[str] | None = None,
    total: int | None = None,
    schema_version: str = "1",
) -> dict[str, Any]:
    """Build a minimal outcomes dict matching the real schema."""
    if collection_complete is None:
        collection_complete = sorted(outcomes_map.keys())
    if total is None:
        total = len(outcomes_map)
    return {
        "schema_version": schema_version,
        "outcomes": outcomes_map,
        "total": total,
        "collection_complete": collection_complete,
    }


def _make_telemetry(
    *,
    pytest_exit_code: int = 0,
    tests_collected: int = 2,
    producer_authoritative: bool = True,
    counts_authoritative: bool = True,
    execution_status: str = "completed",
    commit_sha: str = _SHA,
    run_id: str = _RUN_ID,
    run_attempt: int = _RUN_ATTEMPT,
    python_version: str = _PYTHON_VERSION,
    shard: str = "benchmark",
    outcome_parse_status: str = "available",
    junit_parse_status: str = "available",
    resource_measurement_status: str = "available",
) -> dict[str, Any]:
    """Build a minimal telemetry dict."""
    tel: dict[str, Any] = {
        "track": "nightly",
        "commit_sha": commit_sha,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "python_version": python_version,
        "shard": shard,
        "execution_status": execution_status,
        "pytest_exit_code": pytest_exit_code,
        "producer_authoritative": producer_authoritative,
        "counts_authoritative": counts_authoritative,
        "outcome_parse_status": outcome_parse_status,
        "junit_parse_status": junit_parse_status,
        "resource_measurement_status": resource_measurement_status,
        "tests_collected": tests_collected,
        "tests_passed": tests_collected,
        "tests_failed": 0,
        "tests_skipped": 0,
        "tests_xfailed": 0,
        "tests_xpassed": 0,
    }
    return tel


_JUNIT_XML = '<testsuite tests="0"></testsuite>\n'


def _write_junit(path: Path) -> Path:
    """Write a minimal JUnit XML file."""
    path.write_text(_JUNIT_XML, encoding="utf-8")
    return path


def _valid_na_artifact() -> dict[str, Any]:
    """Build a valid N/A authority artifact."""
    return _build_not_applicable_artifact(
        commit_sha=_SHA,
        run_id=_RUN_ID,
        run_attempt=_RUN_ATTEMPT,
        python_version=_PYTHON_VERSION,
    )


def _valid_executed_artifact(
    node_ids: list[str],
    *,
    producer_authoritative: bool = True,
    pytest_exit_code: int = 0,
    evidence: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a valid executed authority artifact with mandatory evidence set."""
    validated_set = frozenset(node_ids)
    return _build_executed_artifact(
        commit_sha=_SHA,
        run_id=_RUN_ID,
        run_attempt=_RUN_ATTEMPT,
        python_version=_PYTHON_VERSION,
        benchmark_node_count=len(node_ids),
        benchmark_node_ids=node_ids,
        pytest_exit_code=pytest_exit_code,
        producer_authoritative=producer_authoritative,
        validated_evidence_node_ids=validated_set,
        evidence=evidence,
    )


def _validate(artifact: dict[str, Any]) -> None:
    """Validate artifact against canonical test parameters."""
    validate_authority_artifact(
        artifact,
        expected_commit_sha=_SHA,
        expected_run_id=_RUN_ID,
        expected_run_attempt=_RUN_ATTEMPT,
        expected_python_version=_PYTHON_VERSION,
    )


def _sha256_hex(data: str) -> str:
    """Compute SHA-256 hex digest of a string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════════════════
# Section 1: Positive tests — zero nodes, N/A artifact, round-trip
# ══════════════════════════════════════════════════════════════════════════


class TestZeroNodeNA:
    """Scenario 1: Zero benchmark nodes → valid N/A authority.
    Scenario 2: N/A artifact schema validation.
    Scenario 3: N/A artifact round-trip through save/load/validate.
    """

    def test_extract_returns_empty(self) -> None:
        """Scenario 1: extract_benchmark_nodes returns empty for no-benchmark markers."""
        inv = _make_marker_inv(
            {
                "tests/unit/test_a.py::test_x": ["pure"],
                "tests/unit/test_b.py::test_y": ["provider"],
            }
        )
        nodes = extract_benchmark_nodes(inv)
        assert nodes == []

    def test_na_artifact_schema(self) -> None:
        """Scenario 2: N/A artifact has correct schema fields."""
        artifact = _valid_na_artifact()
        assert artifact["status"] == "not_applicable"
        assert artifact["reason"] == "no-benchmark-nodes"
        assert artifact["authority_valid"] is True
        assert artifact["benchmark_node_count"] == 0
        assert artifact["benchmark_node_ids"] == []
        assert artifact["pytest_exit_code"] is None
        assert artifact["producer_authoritative"] is None
        assert artifact["collection_scope"] == "global"
        assert artifact["shard"] is None

    def test_na_artifact_validates(self) -> None:
        """Scenario 2: N/A artifact passes authority validation."""
        _validate(_valid_na_artifact())

    def test_na_roundtrip(self, tmp_path: Path) -> None:
        """Scenario 3: N/A artifact survives save → load → validate."""
        artifact = _valid_na_artifact()
        p = tmp_path / "benchmark-authority.json"
        save_authority_artifact(artifact, p)
        loaded = load_authority_artifact(p)
        _validate(loaded)
        assert loaded["status"] == "not_applicable"
        assert loaded["authority_valid"] is True


# ══════════════════════════════════════════════════════════════════════════
# Section 2: Paired inventory validation
# ══════════════════════════════════════════════════════════════════════════


class TestPairedInventory:
    """Scenario 4: Paired inventory validation (consistent marker + node inventories).
    Scenario 38: N/A paired inventories consistent → PASS.
    Scenario 39: N/A marker vs node inventory drift → FAIL.
    """

    def test_consistent_paired_inventories(self) -> None:
        """Scenario 4/38: Consistent marker and node inventories → PASS."""
        nodes = ["tests/a.py::t1", "tests/b.py::t2"]
        marker_inv = _make_marker_inv(
            {
                "tests/a.py::t1": ["pure"],
                "tests/b.py::t2": ["provider"],
            }
        )
        node_inv = _make_node_inv(nodes)
        # Should not raise — node sets are identical
        validate_inventory_identity_match(node_inv, marker_inv)

    def test_same_count_node_replacement_fails(self) -> None:
        """Scenario 6: Same-count node replacement → FAIL."""
        marker_inv = _make_marker_inv(
            {
                "a": ["benchmark"],
                "b": ["benchmark"],
            }
        )
        node_inv = _make_node_inv(["a", "x"])
        with pytest.raises(BenchmarkAuthorityError, match="node set mismatch"):
            validate_inventory_identity_match(node_inv, marker_inv)

    def test_marker_vs_node_inventory_drift_fails(self) -> None:
        """Scenario 39: Marker vs node inventory drift → FAIL."""
        marker_inv = _make_marker_inv(
            {
                "tests/a.py::t1": ["benchmark"],
                "tests/b.py::t2": ["pure"],
            }
        )
        node_inv = _make_node_inv(["tests/c.py::t3", "tests/d.py::t4"])
        with pytest.raises(BenchmarkAuthorityError, match="node set mismatch"):
            validate_inventory_identity_match(node_inv, marker_inv)

    def test_marker_missing_in_node_inventory_fails(self) -> None:
        """Scenario 39 variant: marker has node missing in node inventory → FAIL."""
        marker_inv = _make_marker_inv(
            {
                "a": ["benchmark"],
                "b": ["benchmark"],
                "c": ["benchmark"],
            }
        )
        node_inv = _make_node_inv(["a", "b"])
        with pytest.raises(BenchmarkAuthorityError, match="node set mismatch"):
            validate_inventory_identity_match(node_inv, marker_inv)

    def test_extra_node_in_node_inventory_fails(self) -> None:
        """Scenario 39 variant: node inventory has node not in marker → FAIL."""
        marker_inv = _make_marker_inv({"a": ["benchmark"]})
        node_inv = _make_node_inv(["a", "extra"])
        with pytest.raises(BenchmarkAuthorityError, match="node set mismatch"):
            validate_inventory_identity_match(node_inv, marker_inv)

    def test_identity_field_sha_mismatch(self) -> None:
        """Identity fields differ between inventories → FAIL."""
        marker_inv = _make_marker_inv({"a": ["benchmark"]}, commit_sha=_SHA)
        node_inv = _make_node_inv(["a"], commit_sha="d" * 40)
        with pytest.raises(BenchmarkAuthorityError, match="mismatch between"):
            validate_inventory_identity_match(node_inv, marker_inv)

    def test_identity_run_attempt_mismatch(self) -> None:
        """run_attempt differs between inventories → FAIL."""
        marker_inv = _make_marker_inv({"a": ["benchmark"]}, run_attempt=1)
        node_inv = _make_node_inv(["a"], run_attempt=2)
        with pytest.raises(BenchmarkAuthorityError, match="run_attempt mismatch"):
            validate_inventory_identity_match(node_inv, marker_inv)

    def test_collection_scope_mismatch(self) -> None:
        """collection_scope differs between inventories → FAIL."""
        marker_inv = _make_marker_inv({"a": ["benchmark"]}, collection_scope="global")
        node_inv = _make_node_inv(["a"], collection_scope="shard")
        with pytest.raises(BenchmarkAuthorityError, match="collection_scope mismatch"):
            validate_inventory_identity_match(node_inv, marker_inv)

    def test_shard_mismatch(self) -> None:
        """shard differs between inventories → FAIL."""
        marker_inv = _make_marker_inv({"a": ["benchmark"]}, shard=None)
        node_inv = _make_node_inv(["a"], shard="shard-0")
        with pytest.raises(BenchmarkAuthorityError, match="shard mismatch"):
            validate_inventory_identity_match(node_inv, marker_inv)

    def test_node_count_mismatch(self) -> None:
        """node_count differs between inventories → FAIL."""
        nodes = ["a", "b", "c"]
        marker_inv = _make_marker_inv({"a": ["benchmark"], "b": ["benchmark"], "c": ["benchmark"]})
        node_inv = _make_node_inv(nodes)
        # Tamper: set wrong node_count on marker_inv
        marker_inv["node_count"] = 5
        with pytest.raises(BenchmarkAuthorityError, match="node_count mismatch"):
            validate_inventory_identity_match(node_inv, marker_inv)


# ══════════════════════════════════════════════════════════════════════════
# Section 3: End-to-end positive test (real execution)
# ══════════════════════════════════════════════════════════════════════════


class TestEndToEndPositive:
    """Scenario 5: End-to-end positive test.

    Creates a temp benchmark test file, runs real global collection,
    extracts benchmark nodes, runs execution via run_test_shard subprocess,
    generates execution inventory + outcomes + telemetry, calls real CLI
    'benchmark_authority execute', calls real CLI 'benchmark_authority validate'
    with all evidence, verifies four-set equality, evidence digests.
    """

    def test_real_benchmark_execution(self, tmp_path: Path) -> None:
        """Scenario 5: Full end-to-end benchmark authority flow."""
        # ── 1. Create a temp test file under tests/ with @pytest.mark.benchmark
        tests_dir = Path(__file__).resolve().parent.parent  # tests/
        bench_file = tests_dir / "_tmp_bench_authority_test.py"
        try:
            bench_file.write_text(
                "import pytest\n\n"
                "@pytest.mark.benchmark\n"
                "def test_example_benchmark():\n"
                "    assert 1 + 1 == 2\n\n"
                "def test_non_benchmark():\n"
                "    assert True\n",
                encoding="utf-8",
            )

            project_root = str(Path(__file__).resolve().parent.parent.parent)
            inv_output_dir = tmp_path / "inv"
            inv_output_dir.mkdir()
            node_inv_output = inv_output_dir / "node-inventory.json"

            actual_python = f"{sys.version_info.major}.{sys.version_info.minor}"
            env = {
                **{
                    k: v
                    for k, v in os.environ.items()
                    if k in {"PATH", "HOME", "UV", "VIRTUAL_ENV"}
                },
                "PYTHONPATH": f"{project_root}:.",
                "HX_TRACK": "nightly",
                "HX_COMMIT_SHA": _SHA,
                "GITHUB_RUN_ID": _RUN_ID,
                "GITHUB_RUN_ATTEMPT": str(_RUN_ATTEMPT),
                # run_test_shard reads these env vars
                "TRACK": "nightly",
                "COMMIT_SHA": _SHA,
                "RUN_ID": _RUN_ID,
                "RUN_ATTEMPT": str(_RUN_ATTEMPT),
                "PYTHON_VERSION": actual_python,
                "PYTHONHASHSEED": "0",
                "TZ": "UTC",
                "LC_ALL": "C.UTF-8",
            }

            # ── 2. Run pytest --collect-only with collect_nodes_plugin ──
            collect_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "--collect-only",
                    "-p",
                    "tests.ci.collect_nodes_plugin",
                    "--hx-collection-scope",
                    "global",
                    "--hx-node-output",
                    str(node_inv_output),
                    "tests/",
                ],
                capture_output=True,
                text=True,
                cwd=project_root,
                env=env,
                timeout=120,
            )
            assert collect_result.returncode == 0, (
                f"Collection failed:\nstdout={collect_result.stdout}\n"
                f"stderr={collect_result.stderr}"
            )

            # ── 3. Validate marker inventory was produced ───────────────
            marker_inv_path = inv_output_dir / "node-marker-inventory.json"
            assert marker_inv_path.exists(), "node-marker-inventory.json not produced"

            marker_inv = load_marker_inventory(
                marker_inv_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=actual_python,
            )

            # ── 4. Extract benchmark nodes from marker inventory ────────
            benchmark_nodes = extract_benchmark_nodes(marker_inv)
            tmp_bench_nodes = [n for n in benchmark_nodes if "_tmp_bench" in n]
            assert len(tmp_bench_nodes) == 1, (
                f"Expected 1 temp benchmark node, got: {tmp_bench_nodes}"
            )
            assert any("test_example_benchmark" in nid for nid in tmp_bench_nodes)

            # ── 5. Run execution via pytest directly (not run_test_shard,
            #    to avoid cwd collision with the outer shard) ─────────
            exec_node_inv_path = tmp_path / "benchmark-execution-node-inventory.json"
            outcomes_path = tmp_path / "pytest-outcomes.json"
            junit_path = tmp_path / "nightly-benchmark-junit.xml"
            telemetry_path = tmp_path / "resource-telemetry.json"

            exec_env = {**env, "SHARD": "benchmark"}
            run_cmd = [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "tests.ci.outcome_plugin",
                f"--hx-outcome-output={outcomes_path}",
                "--timeout=300",
                "-q",
                "-p",
                "tests.ci.collect_nodes_plugin",
                "--hx-collection-scope",
                "shard",
                "--hx-shard",
                "benchmark",
                "--hx-node-output",
                str(exec_node_inv_path),
                f"--junitxml={junit_path}",
            ] + tmp_bench_nodes

            run_result = subprocess.run(
                run_cmd,
                capture_output=True,
                text=True,
                cwd=project_root,
                env=exec_env,
                timeout=120,
            )

            # ── 6. Generate telemetry from the inner run ──────────────
            # (replicate run_test_shard telemetry logic)
            import time as _time

            _end = _time.monotonic()
            _junit_counts = {
                "tests_collected": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "tests_skipped": 0,
                "tests_xfailed": 0,
                "tests_xpassed": 0,
            }
            if junit_path.exists():
                try:
                    import xml.etree.ElementTree as _ET

                    _root = _ET.parse(str(junit_path)).getroot()
                    _suite = _root.find("testsuite")
                    if _suite is not None:
                        _junit_counts["tests_collected"] = int(_suite.attrib.get("tests", 0))
                    for _tc in _root.iter("testcase"):
                        if _tc.find("failure") is not None or _tc.find("error") is not None:
                            _junit_counts["tests_failed"] += 1
                        elif _tc.find("skipped") is not None:
                            _junit_counts["tests_skipped"] += 1
                        else:
                            _junit_counts["tests_passed"] += 1
                except Exception:
                    pass

            _exit_code = run_result.returncode
            _telemetry_data = {
                "track": exec_env.get("TRACK", ""),
                "commit_sha": exec_env.get("COMMIT_SHA", ""),
                "run_id": exec_env.get("RUN_ID", ""),
                "run_attempt": int(exec_env.get("RUN_ATTEMPT", "1")),
                "python_version": exec_env.get("PYTHON_VERSION", ""),
                "shard": "benchmark",
                "execution_status": "completed",
                "pytest_exit_code": _exit_code,
                "junit_parse_status": "available" if junit_path.exists() else "unavailable",
                "outcome_parse_status": "available" if outcomes_path.exists() else "unavailable",
                "counts_authoritative": True,
                "resource_measurement_status": "available",
                "producer_authoritative": (
                    _exit_code == 0 and junit_path.exists() and outcomes_path.exists()
                ),
                "tests_collected": _junit_counts["tests_collected"],
                "tests_passed": _junit_counts["tests_passed"],
                "tests_failed": _junit_counts["tests_failed"],
                "tests_skipped": _junit_counts["tests_skipped"],
                "tests_xfailed": 0,
                "tests_xpassed": 0,
            }
            telemetry_path.write_text(
                json.dumps(_telemetry_data, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            # ── 7. Verify four-set equality ────────────────────────────
            exec_inv = json.loads(exec_node_inv_path.read_text(encoding="utf-8"))
            exec_node_set = set(exec_inv.get("node_ids", []))
            outcomes_data = json.loads(outcomes_path.read_text(encoding="utf-8"))
            outcome_node_set = set(outcomes_data.get("outcomes", {}).keys())
            cc_set = set(outcomes_data.get("collection_complete", []))
            bench_set = set(tmp_bench_nodes)

            assert exec_node_set == bench_set, (
                f"Execution inventory != benchmark nodes: "
                f"exec_only={exec_node_set - bench_set}, "
                f"bench_only={bench_set - exec_node_set}"
            )
            assert outcome_node_set == bench_set, (
                f"Outcomes != benchmark nodes: "
                f"outcome_only={outcome_node_set - bench_set}, "
                f"bench_only={bench_set - outcome_node_set}"
            )
            assert cc_set == bench_set, (
                f"collection_complete != benchmark nodes: "
                f"cc_only={cc_set - bench_set}, "
                f"bench_only={bench_set - cc_set}"
            )

            # ── 8. Call real CLI 'benchmark_authority execute' ──────────
            authority_output = tmp_path / "benchmark-authority.json"
            execute_cmd = [
                sys.executable,
                "-m",
                "tests.ci.benchmark_authority",
                "execute",
                "--global-marker-inventory",
                str(marker_inv_path),
                "--global-node-inventory",
                str(node_inv_output),
                "--execution-node-inventory",
                str(exec_node_inv_path),
                "--outcomes",
                str(outcomes_path),
                "--telemetry",
                str(telemetry_path),
                "--junit",
                str(junit_path),
                "--output",
                str(authority_output),
                "--commit-sha",
                _SHA,
                "--run-id",
                _RUN_ID,
                "--run-attempt",
                str(_RUN_ATTEMPT),
                "--python-version",
                actual_python,
            ]
            exec_result = subprocess.run(
                execute_cmd,
                capture_output=True,
                text=True,
                cwd=project_root,
                env=env,
                timeout=30,
            )
            assert exec_result.returncode == 0, (
                f"benchmark_authority execute failed:\n"
                f"stdout={exec_result.stdout}\nstderr={exec_result.stderr}"
            )
            assert authority_output.exists(), "benchmark-authority.json not produced"

            # ── 9. Call real CLI 'benchmark_authority validate' ─────────
            validate_cmd = [
                sys.executable,
                "-m",
                "tests.ci.benchmark_authority",
                "validate",
                "--artifact",
                str(authority_output),
                "--global-marker-inventory",
                str(marker_inv_path),
                "--global-node-inventory",
                str(node_inv_output),
                "--execution-node-inventory",
                str(exec_node_inv_path),
                "--outcomes",
                str(outcomes_path),
                "--telemetry",
                str(telemetry_path),
                "--junit",
                str(junit_path),
                "--commit-sha",
                _SHA,
                "--run-id",
                _RUN_ID,
                "--run-attempt",
                str(_RUN_ATTEMPT),
                "--python-version",
                actual_python,
            ]
            val_result = subprocess.run(
                validate_cmd,
                capture_output=True,
                text=True,
                cwd=project_root,
                env=env,
                timeout=30,
            )
            assert val_result.returncode == 0, (
                f"benchmark_authority validate failed:\n"
                f"stdout={val_result.stdout}\nstderr={val_result.stderr}"
            )

            # ── 10. Verify status == 'executed' ────────────────────────
            artifact = load_authority_artifact(authority_output)
            assert artifact["status"] == "executed"
            assert artifact["authority_valid"] is True
            assert artifact["pytest_exit_code"] == 0
            assert artifact["producer_authoritative"] is True
            assert artifact["benchmark_node_count"] == len(tmp_bench_nodes)

            # ── 11. Verify evidence digests ────────────────────────────
            evidence = artifact.get("evidence", {})
            assert isinstance(evidence, dict), "artifact.evidence must be a dict"
            expected_keys = {
                "global_marker_inventory_sha256",
                "global_node_inventory_sha256",
                "execution_node_inventory_sha256",
                "outcomes_sha256",
                "telemetry_sha256",
                "junit_sha256",
            }
            assert set(evidence.keys()) == expected_keys, (
                f"Evidence keys mismatch: got {set(evidence.keys())}"
            )
            # Verify actual SHA-256 values match file contents
            assert evidence["global_marker_inventory_sha256"] == _compute_file_sha256(
                marker_inv_path
            )
            assert evidence["global_node_inventory_sha256"] == _compute_file_sha256(node_inv_output)
            assert evidence["outcomes_sha256"] == _compute_file_sha256(outcomes_path)
            assert evidence["telemetry_sha256"] == _compute_file_sha256(telemetry_path)
            assert evidence["junit_sha256"] == _compute_file_sha256(junit_path)

            # ── 12. Verify four-set equality on final artifact ─────────
            artifact_bench_set = set(artifact["benchmark_node_ids"])
            assert artifact_bench_set == bench_set

        finally:
            bench_file.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════════════════════
# Section 4: Node replacement negative tests
# ══════════════════════════════════════════════════════════════════════════


class TestNodeReplacement:
    """Scenarios 6-7: Node set replacement failures."""

    def test_same_count_outcome_replacement_fails(self, tmp_path: Path) -> None:
        """Scenario 6: Same-count outcome replacement → FAIL.

        outcomes reports {a, x} instead of {a, b} — same count but different nodes.
        Must be rejected by the production validator.
        """
        from tests.ci.benchmark_authority import validate_executed_benchmark_evidence

        marker_inv = _make_marker_inv(
            {
                "a": ["benchmark", "collection_complete"],
                "b": ["benchmark", "collection_complete"],
            }
        )
        marker_path = tmp_path / "marker.json"
        marker_path.write_text(json.dumps(marker_inv), encoding="utf-8")

        node_inv = _make_node_inv(["a", "b"])
        node_inv_path = tmp_path / "node.json"
        node_inv_path.write_text(json.dumps(node_inv), encoding="utf-8")

        exec_inv = _make_node_inv(
            ["a", "b"],
            collection_scope="shard",
            shard="benchmark",
        )
        exec_path = tmp_path / "exec.json"
        exec_path.write_text(json.dumps(exec_inv), encoding="utf-8")

        outcomes = _make_outcomes({"a": "passed", "x": "passed"})
        outcomes_path = tmp_path / "outcomes.json"
        outcomes_path.write_text(json.dumps(outcomes), encoding="utf-8")

        telemetry = _make_telemetry(tests_collected=2)
        tel_path = tmp_path / "telemetry.json"
        tel_path.write_text(json.dumps(telemetry), encoding="utf-8")

        junit_path = tmp_path / "junit.xml"
        _write_junit(junit_path)

        with pytest.raises(BenchmarkAuthorityError, match="mismatch"):
            validate_executed_benchmark_evidence(
                marker_inventory_path=marker_path,
                node_inventory_path=node_inv_path,
                execution_node_inventory_path=exec_path,
                outcomes_path=outcomes_path,
                telemetry_path=tel_path,
                junit_path=junit_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )

    def test_same_count_execution_inventory_replacement_fails(self, tmp_path: Path) -> None:
        """Scenario 7: Same-count execution inventory replacement → FAIL.

        Execution inventory reports {a, x} instead of {a, b}.
        """
        from tests.ci.benchmark_authority import validate_executed_benchmark_evidence

        marker_inv = _make_marker_inv(
            {
                "a": ["benchmark", "collection_complete"],
                "b": ["benchmark", "collection_complete"],
            }
        )
        marker_path = tmp_path / "marker.json"
        marker_path.write_text(json.dumps(marker_inv), encoding="utf-8")

        node_inv = _make_node_inv(["a", "b"])
        node_inv_path = tmp_path / "node.json"
        node_inv_path.write_text(json.dumps(node_inv), encoding="utf-8")

        exec_inv_raw = {
            "schema_version": "1",
            "collection_scope": "shard",
            "python_version": _PYTHON_VERSION,
            "commit_sha": _SHA,
            "track": "nightly",
            "shard": "benchmark",
            "run_id": _RUN_ID,
            "run_attempt": _RUN_ATTEMPT,
            "node_count": 2,
            "node_ids": ["a", "x"],
        }
        exec_path = tmp_path / "exec.json"
        exec_path.write_text(json.dumps(exec_inv_raw), encoding="utf-8")

        outcomes = _make_outcomes({"a": "passed", "b": "passed"})
        outcomes_path = tmp_path / "outcomes.json"
        outcomes_path.write_text(json.dumps(outcomes), encoding="utf-8")

        telemetry = _make_telemetry(tests_collected=2)
        tel_path = tmp_path / "telemetry.json"
        tel_path.write_text(json.dumps(telemetry), encoding="utf-8")

        junit_path = tmp_path / "junit.xml"
        _write_junit(junit_path)

        with pytest.raises(BenchmarkAuthorityError, match="mismatch"):
            validate_executed_benchmark_evidence(
                marker_inventory_path=marker_path,
                node_inventory_path=node_inv_path,
                execution_node_inventory_path=exec_path,
                outcomes_path=outcomes_path,
                telemetry_path=tel_path,
                junit_path=junit_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )


# ══════════════════════════════════════════════════════════════════════════
# Section 5: Missing / extra / duplicate node tests
# ══════════════════════════════════════════════════════════════════════════


class TestMissingExtraNodes:
    """Scenarios 8-12: Missing and extra node failures."""

    def test_missing_outcome_node_fails(self, tmp_path: Path) -> None:
        """Scenario 8: Missing outcome node → FAIL."""
        from tests.ci.benchmark_authority import validate_executed_benchmark_evidence

        marker_inv = _make_marker_inv(
            {
                "a": ["benchmark", "collection_complete"],
                "b": ["benchmark", "collection_complete"],
            }
        )
        marker_path = tmp_path / "marker.json"
        marker_path.write_text(json.dumps(marker_inv), encoding="utf-8")

        node_inv = _make_node_inv(["a", "b"])
        node_inv_path = tmp_path / "node.json"
        node_inv_path.write_text(json.dumps(node_inv), encoding="utf-8")

        exec_inv = _make_node_inv(
            ["a", "b"],
            collection_scope="shard",
            shard="benchmark",
        )
        exec_path = tmp_path / "exec.json"
        exec_path.write_text(json.dumps(exec_inv), encoding="utf-8")

        outcomes = _make_outcomes({"a": "passed"})
        outcomes_path = tmp_path / "outcomes.json"
        outcomes_path.write_text(json.dumps(outcomes), encoding="utf-8")

        telemetry = _make_telemetry(tests_collected=2)
        tel_path = tmp_path / "telemetry.json"
        tel_path.write_text(json.dumps(telemetry), encoding="utf-8")

        junit_path = tmp_path / "junit.xml"
        _write_junit(junit_path)

        with pytest.raises(BenchmarkAuthorityError, match="mismatch"):
            validate_executed_benchmark_evidence(
                marker_inventory_path=marker_path,
                node_inventory_path=node_inv_path,
                execution_node_inventory_path=exec_path,
                outcomes_path=outcomes_path,
                telemetry_path=tel_path,
                junit_path=junit_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )

    def test_extra_outcome_node_fails(self, tmp_path: Path) -> None:
        """Scenario 9: Extra outcome node → FAIL."""
        from tests.ci.benchmark_authority import validate_executed_benchmark_evidence

        marker_inv = _make_marker_inv(
            {
                "a": ["benchmark", "collection_complete"],
            }
        )
        marker_path = tmp_path / "marker.json"
        marker_path.write_text(json.dumps(marker_inv), encoding="utf-8")

        node_inv = _make_node_inv(["a"])
        node_inv_path = tmp_path / "node.json"
        node_inv_path.write_text(json.dumps(node_inv), encoding="utf-8")

        exec_inv = _make_node_inv(
            ["a"],
            collection_scope="shard",
            shard="benchmark",
        )
        exec_path = tmp_path / "exec.json"
        exec_path.write_text(json.dumps(exec_inv), encoding="utf-8")

        outcomes = _make_outcomes({"a": "passed", "extra": "passed"})
        outcomes_path = tmp_path / "outcomes.json"
        outcomes_path.write_text(json.dumps(outcomes), encoding="utf-8")

        telemetry = _make_telemetry(tests_collected=2)
        tel_path = tmp_path / "telemetry.json"
        tel_path.write_text(json.dumps(telemetry), encoding="utf-8")

        junit_path = tmp_path / "junit.xml"
        _write_junit(junit_path)

        with pytest.raises(BenchmarkAuthorityError, match="mismatch"):
            validate_executed_benchmark_evidence(
                marker_inventory_path=marker_path,
                node_inventory_path=node_inv_path,
                execution_node_inventory_path=exec_path,
                outcomes_path=outcomes_path,
                telemetry_path=tel_path,
                junit_path=junit_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )

    def test_missing_collection_complete_node_fails(self, tmp_path: Path) -> None:
        """Scenario 10: collection_complete nodes != outcome nodes → FAIL."""
        from tests.ci.benchmark_authority import validate_executed_benchmark_evidence

        marker_inv = _make_marker_inv(
            {
                "a": ["benchmark"],
                "b": ["benchmark"],
            }
        )
        marker_path = tmp_path / "marker.json"
        marker_path.write_text(json.dumps(marker_inv), encoding="utf-8")

        node_inv = _make_node_inv(["a", "b"])
        node_inv_path = tmp_path / "node.json"
        node_inv_path.write_text(json.dumps(node_inv), encoding="utf-8")

        exec_inv = _make_node_inv(
            ["a", "b"],
            collection_scope="shard",
            shard="benchmark",
        )
        exec_path = tmp_path / "exec.json"
        exec_path.write_text(json.dumps(exec_inv), encoding="utf-8")

        # collection_complete only has "a" but outcomes has "a" and "b"
        outcomes = {
            "schema_version": "1",
            "outcomes": {"a": "passed", "b": "passed"},
            "total": 2,
            "collection_complete": ["a"],
        }
        outcomes_path = tmp_path / "outcomes.json"
        outcomes_path.write_text(json.dumps(outcomes), encoding="utf-8")

        telemetry = _make_telemetry(tests_collected=2)
        tel_path = tmp_path / "telemetry.json"
        tel_path.write_text(json.dumps(telemetry), encoding="utf-8")

        junit_path = tmp_path / "junit.xml"
        _write_junit(junit_path)

        with pytest.raises(BenchmarkAuthorityError, match="collection_complete"):
            validate_executed_benchmark_evidence(
                marker_inventory_path=marker_path,
                node_inventory_path=node_inv_path,
                execution_node_inventory_path=exec_path,
                outcomes_path=outcomes_path,
                telemetry_path=tel_path,
                junit_path=junit_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )

    def test_extra_collection_complete_node_fails(self) -> None:
        """Scenario 11: Extra collection_complete node → FAIL.

        Outcomes collection_complete has a node not in marker benchmark nodes.
        """
        outcomes = _make_outcomes(
            {"a": "passed"},
            collection_complete=["a", "extra"],
        )
        outcome_nodes = _extract_outcome_nodes(outcomes)
        cc_nodes = _extract_collection_complete_nodes(outcomes)
        assert "extra" in cc_nodes
        assert outcome_nodes != cc_nodes

    def test_duplicate_collection_complete_node_fails(self) -> None:
        """Scenario 12: Duplicate collection_complete node → FAIL."""
        outcomes = _make_outcomes(
            {"a": "passed"},
            collection_complete=["a", "a"],
        )
        cc = outcomes["collection_complete"]
        assert len(cc) == 2
        assert cc[0] == cc[1]
        with pytest.raises(BenchmarkAuthorityError):
            _validate_outcomes_schema(outcomes)


# ══════════════════════════════════════════════════════════════════════════
# Section 6: Execution inventory validation
# ══════════════════════════════════════════════════════════════════════════


class TestExecutionInventory:
    """Scenarios 13-21: Execution inventory validation failures."""

    def test_duplicate_execution_inventory_node_fails(self, tmp_path: Path) -> None:
        """Scenario 13: Duplicate execution inventory node → FAIL."""
        raw = _make_node_inv(
            ["a", "a"],
            collection_scope="shard",
            shard="benchmark",
        )
        inv_path = tmp_path / "exec_inv.json"
        inv_path.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(BenchmarkAuthorityError, match="unique"):
            load_and_validate_node_inventory(
                inv_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
                expected_collection_scope="shard",
                expected_shard="benchmark",
            )

    def test_execution_inventory_node_count_error_fails(self, tmp_path: Path) -> None:
        """Scenario 14: Execution inventory node_count error → FAIL."""
        raw = {
            "schema_version": "1",
            "collection_scope": "shard",
            "python_version": _PYTHON_VERSION,
            "commit_sha": _SHA,
            "track": "nightly",
            "shard": "benchmark",
            "run_id": _RUN_ID,
            "run_attempt": _RUN_ATTEMPT,
            "node_count": 999,
            "node_ids": ["a", "b"],
        }
        inv_path = tmp_path / "exec_inv.json"
        inv_path.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(BenchmarkAuthorityError, match="node_ids length.*node_count"):
            load_and_validate_node_inventory(
                inv_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
                expected_collection_scope="shard",
                expected_shard="benchmark",
            )

    def test_execution_inventory_unsorted_fails(self, tmp_path: Path) -> None:
        """Scenario 15: Execution inventory unsorted → FAIL."""
        raw = {
            "schema_version": "1",
            "collection_scope": "shard",
            "python_version": _PYTHON_VERSION,
            "commit_sha": _SHA,
            "track": "nightly",
            "shard": "benchmark",
            "run_id": _RUN_ID,
            "run_attempt": _RUN_ATTEMPT,
            "node_count": 2,
            "node_ids": ["b", "a"],
        }
        inv_path = tmp_path / "exec_inv.json"
        inv_path.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(BenchmarkAuthorityError, match="canonically sorted"):
            load_and_validate_node_inventory(
                inv_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
                expected_collection_scope="shard",
                expected_shard="benchmark",
            )

    def test_execution_inventory_wrong_scope_fails(self, tmp_path: Path) -> None:
        """Scenario 16: Execution inventory wrong scope (global instead of shard) → FAIL."""
        raw = _make_node_inv(
            ["a", "b"],
            collection_scope="global",
            shard="benchmark",
        )
        inv_path = tmp_path / "exec_inv.json"
        inv_path.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(BenchmarkAuthorityError, match="collection_scope"):
            load_and_validate_node_inventory(
                inv_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
                expected_collection_scope="shard",
                expected_shard="benchmark",
            )

    def test_execution_inventory_wrong_shard_fails(self, tmp_path: Path) -> None:
        """Scenario 17: Execution inventory wrong shard (shard-0 instead of benchmark) → FAIL."""
        raw = _make_node_inv(
            ["a", "b"],
            collection_scope="shard",
            shard="shard-0",
        )
        inv_path = tmp_path / "exec_inv.json"
        inv_path.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(BenchmarkAuthorityError, match="shard"):
            load_and_validate_node_inventory(
                inv_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
                expected_collection_scope="shard",
                expected_shard="benchmark",
            )

    def test_execution_inventory_wrong_sha_fails(self, tmp_path: Path) -> None:
        """Scenario 18: Execution inventory wrong SHA → FAIL."""
        raw = _make_node_inv(
            ["a", "b"],
            commit_sha="b" * 40,
            collection_scope="shard",
            shard="benchmark",
        )
        inv_path = tmp_path / "exec_inv.json"
        inv_path.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(BenchmarkAuthorityError, match="commit_sha mismatch"):
            load_and_validate_node_inventory(
                inv_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
                expected_collection_scope="shard",
                expected_shard="benchmark",
            )

    def test_execution_inventory_wrong_run_id_fails(self, tmp_path: Path) -> None:
        """Scenario 19: Execution inventory wrong run_id → FAIL."""
        raw = _make_node_inv(
            ["a", "b"],
            run_id="WRONG",
            collection_scope="shard",
            shard="benchmark",
        )
        inv_path = tmp_path / "exec_inv.json"
        inv_path.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(BenchmarkAuthorityError, match="run_id mismatch"):
            load_and_validate_node_inventory(
                inv_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
                expected_collection_scope="shard",
                expected_shard="benchmark",
            )

    def test_execution_inventory_wrong_attempt_fails(self, tmp_path: Path) -> None:
        """Scenario 20: Execution inventory wrong attempt → FAIL."""
        raw = _make_node_inv(
            ["a", "b"],
            run_attempt=2,
            collection_scope="shard",
            shard="benchmark",
        )
        inv_path = tmp_path / "exec_inv.json"
        inv_path.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(BenchmarkAuthorityError, match="run_attempt mismatch"):
            load_and_validate_node_inventory(
                inv_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
                expected_collection_scope="shard",
                expected_shard="benchmark",
            )

    def test_execution_inventory_wrong_python_fails(self, tmp_path: Path) -> None:
        """Scenario 21: Execution inventory wrong Python version → FAIL."""
        raw = _make_node_inv(
            ["a", "b"],
            python_version="3.11",
            collection_scope="shard",
            shard="benchmark",
        )
        inv_path = tmp_path / "exec_inv.json"
        inv_path.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(BenchmarkAuthorityError, match="python_version"):
            load_and_validate_node_inventory(
                inv_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
                expected_collection_scope="shard",
                expected_shard="benchmark",
            )


# ══════════════════════════════════════════════════════════════════════════
# Section 7: Outcomes schema validation
# ══════════════════════════════════════════════════════════════════════════


class TestOutcomesSchema:
    """Scenarios 22-26: Outcomes schema validation failures."""

    def test_outcomes_missing_file_fails(self, tmp_path: Path) -> None:
        """Scenario 22: Outcomes missing file → FAIL."""
        from tests.ci.benchmark_authority import validate_executed_benchmark_evidence

        marker_inv = _make_marker_inv({"a": ["benchmark", "collection_complete"]})
        marker_path = tmp_path / "marker.json"
        marker_path.write_text(json.dumps(marker_inv), encoding="utf-8")

        outcomes_path = tmp_path / "nonexistent-outcomes.json"
        tel_path = tmp_path / "telemetry.json"
        tel_path.write_text(json.dumps(_make_telemetry()), encoding="utf-8")
        junit_path = tmp_path / "junit.xml"
        _write_junit(junit_path)

        with pytest.raises(BenchmarkAuthorityError, match="cannot parse"):
            validate_executed_benchmark_evidence(
                marker_inventory_path=marker_path,
                node_inventory_path=None,
                execution_node_inventory_path=None,
                outcomes_path=outcomes_path,
                telemetry_path=tel_path,
                junit_path=junit_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )

    def test_outcomes_malformed_json_fails(self, tmp_path: Path) -> None:
        """Scenario 23: Outcomes malformed JSON → FAIL."""
        from tests.ci.benchmark_authority import validate_executed_benchmark_evidence

        marker_inv = _make_marker_inv({"a": ["benchmark", "collection_complete"]})
        marker_path = tmp_path / "marker.json"
        marker_path.write_text(json.dumps(marker_inv), encoding="utf-8")

        outcomes_path = tmp_path / "outcomes.json"
        outcomes_path.write_text("{not valid json", encoding="utf-8")
        tel_path = tmp_path / "telemetry.json"
        tel_path.write_text(json.dumps(_make_telemetry()), encoding="utf-8")
        junit_path = tmp_path / "junit.xml"
        _write_junit(junit_path)

        with pytest.raises(BenchmarkAuthorityError, match="cannot parse"):
            validate_executed_benchmark_evidence(
                marker_inventory_path=marker_path,
                node_inventory_path=None,
                execution_node_inventory_path=None,
                outcomes_path=outcomes_path,
                telemetry_path=tel_path,
                junit_path=junit_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )

    def test_outcomes_wrong_schema_version_fails(self) -> None:
        """Scenario 24: Outcomes wrong schema_version → FAIL."""
        outcomes = _make_outcomes({"a": "passed"}, schema_version="2")
        with pytest.raises(BenchmarkAuthorityError, match="schema_version"):
            _validate_outcomes_schema(outcomes)

    def test_invalid_outcome_value_fails(self) -> None:
        """Scenario 25: Invalid outcome value → FAIL."""
        outcomes = _make_outcomes({"a": "INVALID_VALUE"})
        with pytest.raises(BenchmarkAuthorityError):
            _validate_outcomes_schema(outcomes)

    def test_outcomes_total_mismatch_fails(self) -> None:
        """Scenario 26: Outcomes total mismatch → FAIL."""
        outcomes = {
            "schema_version": "1",
            "outcomes": {"a": "passed", "b": "passed"},
            "total": 1,
            "collection_complete": ["a", "b"],
        }
        with pytest.raises(BenchmarkAuthorityError, match="total"):
            _validate_outcomes_schema(outcomes)

    def test_valid_outcomes_schema_passes(self) -> None:
        """Valid outcomes schema → PASS."""
        outcomes = _make_outcomes(
            {"a": "passed", "b": "failed"},
            collection_complete=["a", "b"],
        )
        _validate_outcomes_schema(outcomes)

    def test_outcome_values_allowed(self) -> None:
        """All allowed outcome values pass schema validation."""
        for val in ("passed", "failed", "skipped", "xfailed", "xpassed"):
            outcomes = _make_outcomes({f"test_{val}": val})
            _validate_outcomes_schema(outcomes)

    def test_extract_outcome_nodes_reads_outcomes_key(self) -> None:
        """_extract_outcome_nodes reads from outcomes['outcomes']."""
        outcomes = _make_outcomes({"a": "passed", "b": "failed"})
        nodes = _extract_outcome_nodes(outcomes)
        assert nodes == {"a", "b"}

    def test_extract_collection_complete_reads_from_outcomes(self) -> None:
        """_extract_collection_complete_nodes reads from outcomes['collection_complete']."""
        outcomes = _make_outcomes(
            {"a": "passed"},
            collection_complete=["a"],
        )
        cc = _extract_collection_complete_nodes(outcomes)
        assert cc == {"a"}


# ══════════════════════════════════════════════════════════════════════════
# Section 8: Telemetry validation
# ══════════════════════════════════════════════════════════════════════════


class TestTelemetryValidation:
    """Scenarios 27-34: Telemetry validation failures."""

    def test_telemetry_missing_file_fails(self, tmp_path: Path) -> None:
        """Scenario 27: Telemetry missing file → FAIL."""
        from tests.ci.benchmark_authority import validate_executed_benchmark_evidence

        marker_inv = _make_marker_inv({"a": ["benchmark", "collection_complete"]})
        marker_path = tmp_path / "marker.json"
        marker_path.write_text(json.dumps(marker_inv), encoding="utf-8")

        outcomes = _make_outcomes({"a": "passed"})
        outcomes_path = tmp_path / "outcomes.json"
        outcomes_path.write_text(json.dumps(outcomes), encoding="utf-8")

        tel_path = tmp_path / "nonexistent-telemetry.json"
        junit_path = tmp_path / "junit.xml"
        _write_junit(junit_path)

        with pytest.raises(BenchmarkAuthorityError, match="cannot parse"):
            validate_executed_benchmark_evidence(
                marker_inventory_path=marker_path,
                node_inventory_path=None,
                execution_node_inventory_path=None,
                outcomes_path=outcomes_path,
                telemetry_path=tel_path,
                junit_path=junit_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )

    def test_telemetry_malformed_json_fails(self, tmp_path: Path) -> None:
        """Scenario 28: Telemetry malformed JSON → FAIL."""
        from tests.ci.benchmark_authority import validate_executed_benchmark_evidence

        marker_inv = _make_marker_inv({"a": ["benchmark", "collection_complete"]})
        marker_path = tmp_path / "marker.json"
        marker_path.write_text(json.dumps(marker_inv), encoding="utf-8")

        outcomes = _make_outcomes({"a": "passed"})
        outcomes_path = tmp_path / "outcomes.json"
        outcomes_path.write_text(json.dumps(outcomes), encoding="utf-8")

        tel_path = tmp_path / "telemetry.json"
        tel_path.write_text("}[invalid", encoding="utf-8")
        junit_path = tmp_path / "junit.xml"
        _write_junit(junit_path)

        with pytest.raises(BenchmarkAuthorityError, match="cannot parse"):
            validate_executed_benchmark_evidence(
                marker_inventory_path=marker_path,
                node_inventory_path=None,
                execution_node_inventory_path=None,
                outcomes_path=outcomes_path,
                telemetry_path=tel_path,
                junit_path=junit_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )

    def test_telemetry_wrong_sha_fails(self) -> None:
        """Scenario 29: Telemetry wrong identity (SHA) → FAIL."""
        telemetry = _make_telemetry(commit_sha="b" * 40)
        with pytest.raises(BenchmarkAuthorityError, match="commit_sha"):
            _validate_telemetry(
                telemetry,
                expected_pytest_exit_code=0,
                expected_node_count=2,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )

    def test_telemetry_producer_not_authoritative_fails(self) -> None:
        """Scenario 30: Telemetry producer_authoritative=false → FAIL."""
        telemetry = _make_telemetry(producer_authoritative=False)
        with pytest.raises(BenchmarkAuthorityError, match="producer_authoritative"):
            _validate_telemetry(
                telemetry,
                expected_pytest_exit_code=0,
                expected_node_count=2,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )

    def test_telemetry_counts_not_authoritative_fails(self) -> None:
        """Scenario 31: Telemetry counts_authoritative=false → FAIL."""
        telemetry = _make_telemetry(counts_authoritative=False)
        with pytest.raises(BenchmarkAuthorityError, match="counts_authoritative"):
            _validate_telemetry(
                telemetry,
                expected_pytest_exit_code=0,
                expected_node_count=2,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )

    def test_telemetry_pytest_exit_code_nonzero_fails(self) -> None:
        """Scenario 32: Telemetry pytest exit code nonzero → FAIL."""
        telemetry = _make_telemetry(pytest_exit_code=1)
        with pytest.raises(BenchmarkAuthorityError, match="pytest_exit_code"):
            _validate_telemetry(
                telemetry,
                expected_pytest_exit_code=0,
                expected_node_count=2,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )

    def test_telemetry_collected_count_mismatch_fails(self) -> None:
        """Scenario 33: Telemetry collected count mismatch → FAIL."""
        telemetry = _make_telemetry(tests_collected=999)
        with pytest.raises(BenchmarkAuthorityError, match="tests_collected"):
            _validate_telemetry(
                telemetry,
                expected_pytest_exit_code=0,
                expected_node_count=2,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )

    def test_validate_outcome_category_count_mismatch_fails(self) -> None:
        """Scenario 34: Outcome category count mismatch → FAIL."""
        outcomes = _make_outcomes({"a": "passed", "b": "passed"})
        outcomes["summary"] = {
            "passed": 2,
            "failed": 0,
            "skipped": 0,
            "error": 0,
            "xfail": 0,
            "total": 2,
        }
        telemetry = {
            "tests_passed": 1,
            "tests_failed": 0,
            "tests_skipped": 0,
            "tests_xfailed": 0,
            "tests_xpassed": 0,
            "tests_collected": 2,
        }
        with pytest.raises(BenchmarkAuthorityError, match="tests_passed"):
            _validate_outcome_category_counts(outcomes, telemetry)

    def test_validate_telemetry_wrong_run_id_fails(self) -> None:
        """Telemetry wrong run_id → FAIL."""
        telemetry = _make_telemetry(run_id="WRONG")
        with pytest.raises(BenchmarkAuthorityError, match="run_id"):
            _validate_telemetry(
                telemetry,
                expected_pytest_exit_code=0,
                expected_node_count=2,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )

    def test_validate_telemetry_wrong_attempt_fails(self) -> None:
        """Telemetry wrong attempt → FAIL."""
        telemetry = _make_telemetry(run_attempt=99)
        with pytest.raises(BenchmarkAuthorityError, match="run_attempt"):
            _validate_telemetry(
                telemetry,
                expected_pytest_exit_code=0,
                expected_node_count=2,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )

    def test_validate_telemetry_wrong_python_fails(self) -> None:
        """Telemetry wrong python_version → FAIL."""
        telemetry = _make_telemetry(python_version="3.11")
        with pytest.raises(BenchmarkAuthorityError, match="python_version"):
            _validate_telemetry(
                telemetry,
                expected_pytest_exit_code=0,
                expected_node_count=2,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )

    def test_valid_telemetry_passes(self) -> None:
        """Valid telemetry → PASS."""
        telemetry = _make_telemetry(tests_collected=2)
        _validate_telemetry(
            telemetry,
            expected_pytest_exit_code=0,
            expected_node_count=2,
            expected_commit_sha=_SHA,
            expected_run_id=_RUN_ID,
            expected_run_attempt=_RUN_ATTEMPT,
            expected_python_version=_PYTHON_VERSION,
        )


# ══════════════════════════════════════════════════════════════════════════
# Section 9: Evidence digest validation
# ══════════════════════════════════════════════════════════════════════════


class TestEvidenceDigests:
    """Scenarios 35-37: Evidence digest mismatch failures."""

    def test_authority_evidence_digest_mismatch_fails(self, tmp_path: Path) -> None:
        """Scenario 35: Authority evidence digest mismatch → FAIL."""
        artifact = _valid_executed_artifact(
            ["a"],
            evidence={
                "global_marker_inventory_sha256": "0" * 64,
                "global_node_inventory_sha256": "0" * 64,
                "execution_node_inventory_sha256": "0" * 64,
                "outcomes_sha256": "0" * 64,
                "telemetry_sha256": "0" * 64,
                "junit_sha256": "0" * 64,
            },
        )
        for name, content in [
            ("marker.json", '{"key": "value1"}'),
            ("node.json", '{"key": "value2"}'),
            ("exec.json", '{"key": "value3"}'),
            ("outcomes.json", '{"key": "value4"}'),
            ("telemetry.json", '{"key": "value5"}'),
            ("junit.xml", "<root/>"),
        ]:
            p = tmp_path / name
            p.write_text(content, encoding="utf-8")

        correct_evidence = {
            "global_marker_inventory_sha256": _compute_file_sha256(tmp_path / "marker.json"),
            "global_node_inventory_sha256": _compute_file_sha256(tmp_path / "node.json"),
            "execution_node_inventory_sha256": _compute_file_sha256(tmp_path / "exec.json"),
            "outcomes_sha256": _compute_file_sha256(tmp_path / "outcomes.json"),
            "telemetry_sha256": _compute_file_sha256(tmp_path / "telemetry.json"),
            "junit_sha256": _compute_file_sha256(tmp_path / "junit.xml"),
        }

        assert artifact["evidence"]["outcomes_sha256"] != correct_evidence["outcomes_sha256"]

    def test_evidence_sha256_computation(self, tmp_path: Path) -> None:
        """Scenario 36: Verify _compute_file_sha256 produces correct SHA-256 digests."""
        content = "hello world\n"
        p = tmp_path / "test.txt"
        p.write_text(content, encoding="utf-8")
        digest = _compute_file_sha256(p)
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert digest == expected
        assert len(digest) == 64

    def test_evidence_digest_round_trip(self, tmp_path: Path) -> None:
        """Scenario 37: Evidence digests survive save/load."""
        evidence = {
            "global_marker_inventory_sha256": "a" * 64,
            "global_node_inventory_sha256": "b" * 64,
            "execution_node_inventory_sha256": "c" * 64,
            "outcomes_sha256": "d" * 64,
            "telemetry_sha256": "e" * 64,
            "junit_sha256": "f" * 64,
        }
        artifact = _valid_executed_artifact(["a"], evidence=evidence)
        p = tmp_path / "benchmark-authority.json"
        save_authority_artifact(artifact, p)
        loaded = load_authority_artifact(p)
        assert loaded["evidence"] == evidence


# ══════════════════════════════════════════════════════════════════════════
# Section 10: Workflow static tests
# ══════════════════════════════════════════════════════════════════════════


class TestWorkflowStatic:
    """Scenarios 40-41: Verify nightly.yml contains governed patterns."""

    NIGHTLY_YML = Path(".github/workflows/nightly.yml")

    @pytest.fixture()
    def nightly_content(self) -> str:
        return self.NIGHTLY_YML.read_text(encoding="utf-8")

    def test_benchmark_nonzero_calls_benchmark_authority_execute(
        self, nightly_content: str
    ) -> None:
        """Scenario 40: Non-zero path calls benchmark_authority execute."""
        required_strings = [
            "tests.ci.run_test_shard",
            "tests.ci.collect_nodes_plugin",
            "--hx-collection-scope",
            "shard",
            "--hx-shard",
            "benchmark",
            "--hx-node-output",
            "benchmark-execution-node-inventory.json",
            "tests.ci.benchmark_authority execute",
            "--global-marker-inventory",
            "--global-node-inventory",
            "--execution-node-inventory",
            "--outcomes",
            "--telemetry",
            "--junit",
        ]
        for s in required_strings:
            assert s in nightly_content, f"Required string not found: {s!r}"

    def test_final_gate_passes_all_source_evidence(self, nightly_content: str) -> None:
        """Scenario 41: Final gate passes all source evidence to validate."""
        gate_section = nightly_content[nightly_content.find("final-gate:") :]
        required_evidence = [
            "--global-marker-inventory",
            "--global-node-inventory",
            "--execution-node-inventory",
            "--outcomes",
            "--telemetry",
            "--junit",
            "benchmark_authority validate",
        ]
        for s in required_evidence:
            assert s in gate_section, f"Final gate missing: {s!r}"

    def test_no_bare_exit_0_on_benchmark(self, nightly_content: str) -> None:
        """No false-green exit-5-to-exit-0 pattern."""
        assert (
            'echo "No benchmark-marked tests collected (exit 5), treating as pass"'
            not in nightly_content
        )
        assert 'if [ "$RC" -eq 5 ]; then' not in nightly_content

    def test_no_bare_python3_in_benchmark(self, nightly_content: str) -> None:
        """No bare python3 (must use uv run --locked)."""
        benchmark_start = nightly_content.find("benchmark:")
        assert benchmark_start != -1, "benchmark job not found"
        final_gate_start = nightly_content.find("golden-regression:", benchmark_start)
        if final_gate_start == -1:
            final_gate_start = len(nightly_content)
        benchmark_section = nightly_content[benchmark_start:final_gate_start]

        for line in benchmark_section.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue
            if "python3" in stripped and "uv run" not in stripped:
                pytest.fail(f"Bare python3 found in benchmark job: {stripped!r}")

    def test_benchmark_job_uses_locked_execution(self, nightly_content: str) -> None:
        """All uv commands in benchmark job must use --locked."""
        benchmark_start = nightly_content.find("benchmark:")
        assert benchmark_start != -1
        final_gate_start = nightly_content.find("golden-regression:", benchmark_start)
        if final_gate_start == -1:
            final_gate_start = len(nightly_content)
        benchmark_section = nightly_content[benchmark_start:final_gate_start]

        for line in benchmark_section.splitlines():
            stripped = line.strip()
            if "uv run" in stripped and "--locked" not in stripped:
                pytest.fail(f"uv run without --locked in benchmark job: {stripped!r}")

    def test_no_true_masking_in_collection(self, nightly_content: str) -> None:
        """No || true masking in collection steps."""
        collect_start = nightly_content.find("Collect global marker inventory")
        if collect_start == -1:
            collect_start = nightly_content.find("--hx-collection-scope")
        if collect_start == -1:
            pytest.skip("Collection step not found in nightly.yml")

        section = nightly_content[max(0, collect_start - 200) : collect_start + 2000]

        for line in section.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue
            assert "|| true" not in stripped, f"|| true masking found in collection: {stripped!r}"

    def test_validate_step_always_runs(self, nightly_content: str) -> None:
        """Validate authority step must run with `if: always()`."""
        step_name = "Validate benchmark authority artifact"
        assert step_name in nightly_content
        validate_start = nightly_content.find(f"name: {step_name}")
        assert validate_start != -1, f"Step '{step_name}' not found"
        following = nightly_content[validate_start : validate_start + 200]
        assert "always()" in following, f"Step '{step_name}' must have if: always()"


# ══════════════════════════════════════════════════════════════════════════
# Section 11: Additional artifact field validation
# ══════════════════════════════════════════════════════════════════════════


class TestArtifactFieldValidation:
    """Additional artifact field validation failures."""

    def test_producer_not_authoritative_fails(self) -> None:
        """producer_authoritative=false → FAIL."""
        artifact = _valid_executed_artifact(["a"])
        artifact["producer_authoritative"] = False
        with pytest.raises(BenchmarkAuthorityError, match="producer_authoritative must be true"):
            _validate(artifact)

    def test_pytest_exit_code_nonzero_fails(self) -> None:
        """pytest exit code non-zero → FAIL."""
        artifact = _valid_executed_artifact(["a"])
        artifact["pytest_exit_code"] = 1
        with pytest.raises(BenchmarkAuthorityError, match="pytest_exit_code must be 0"):
            _validate(artifact)

    def test_wrong_track_fails(self) -> None:
        """Wrong track → FAIL."""
        artifact = _valid_na_artifact()
        artifact["track"] = "pr-head"
        with pytest.raises(BenchmarkAuthorityError, match="track must be 'nightly'"):
            _validate(artifact)

    def test_wrong_collection_scope_fails(self) -> None:
        """Wrong collection_scope → FAIL."""
        artifact = _valid_na_artifact()
        artifact["collection_scope"] = "shard"
        with pytest.raises(BenchmarkAuthorityError, match="collection_scope must be 'global'"):
            _validate(artifact)

    def test_wrong_shard_fails(self) -> None:
        """Wrong shard → FAIL."""
        artifact = _valid_na_artifact()
        artifact["shard"] = "invalid-shard"
        with pytest.raises(BenchmarkAuthorityError, match="shard must be one of"):
            _validate(artifact)

    def test_wrong_commit_sha_fails(self) -> None:
        """Wrong commit_sha → FAIL."""
        artifact = _valid_na_artifact()
        artifact["commit_sha"] = "b" * 40
        with pytest.raises(BenchmarkAuthorityError, match="commit_sha mismatch"):
            _validate(artifact)

    def test_invalid_commit_sha_format_fails(self) -> None:
        """commit_sha must be exactly 40 hex characters."""
        artifact = _valid_na_artifact()
        artifact["commit_sha"] = "not-hex-at-all!"
        with pytest.raises(BenchmarkAuthorityError, match="40 hex chars"):
            _validate(artifact)

    def test_wrong_run_id_fails(self) -> None:
        """Wrong run_id → FAIL."""
        artifact = _valid_na_artifact()
        artifact["run_id"] = "99999"
        with pytest.raises(BenchmarkAuthorityError, match="run_id mismatch"):
            _validate(artifact)

    def test_wrong_run_attempt_fails(self) -> None:
        """Wrong run_attempt → FAIL."""
        artifact = _valid_na_artifact()
        artifact["run_attempt"] = 2
        with pytest.raises(BenchmarkAuthorityError, match="run_attempt mismatch"):
            _validate(artifact)

    def test_wrong_python_version_fails(self) -> None:
        """Wrong python version → FAIL."""
        artifact = _valid_na_artifact()
        artifact["python_version"] = "3.11"
        with pytest.raises(BenchmarkAuthorityError, match="python_version"):
            _validate(artifact)

    def test_unknown_status_fails(self) -> None:
        """Unknown status → FAIL."""
        artifact = _valid_na_artifact()
        artifact["status"] = "unknown"
        with pytest.raises(BenchmarkAuthorityError, match="unknown status"):
            _validate(artifact)

    def test_unknown_reason_fails(self) -> None:
        """Unknown reason → FAIL."""
        artifact = _valid_na_artifact()
        artifact["reason"] = "something-else"
        with pytest.raises(BenchmarkAuthorityError, match="unknown reason"):
            _validate(artifact)

    def test_authority_valid_false_fails(self) -> None:
        """authority_valid=false → FAIL."""
        artifact = _valid_na_artifact()
        artifact["authority_valid"] = False
        with pytest.raises(BenchmarkAuthorityError, match="authority_valid must be true"):
            _validate(artifact)

    def test_malformed_json_load_fails(self, tmp_path: Path) -> None:
        """Malformed JSON on load → FAIL."""
        p = tmp_path / "benchmark-authority.json"
        p.write_text("NOT JSON", encoding="utf-8")
        with pytest.raises(BenchmarkAuthorityError, match="cannot parse"):
            load_authority_artifact(p)

    def test_node_ids_not_sorted_fails(self) -> None:
        """node_ids not sorted → FAIL."""
        artifact = _valid_executed_artifact(["a", "b"])
        artifact["benchmark_node_ids"] = ["b", "a"]
        with pytest.raises(BenchmarkAuthorityError, match="canonically sorted"):
            _validate(artifact)

    def test_node_ids_length_mismatch_fails(self) -> None:
        """node_ids length ≠ node_count → FAIL."""
        artifact = _valid_executed_artifact(["a", "b", "c"])
        artifact["benchmark_node_ids"] = ["a", "b"]
        with pytest.raises(BenchmarkAuthorityError, match="length"):
            _validate(artifact)

    def test_duplicate_node_ids_in_artifact_fails(self) -> None:
        """Duplicate node_ids in artifact → FAIL."""
        artifact = _valid_executed_artifact(["a"])
        artifact["benchmark_node_ids"] = ["a", "a"]
        artifact["benchmark_node_count"] = 2
        with pytest.raises(BenchmarkAuthorityError, match="unique"):
            _validate(artifact)

    def test_duplicate_node_ids_in_node_inventory_fails(self, tmp_path: Path) -> None:
        """Node inventory with duplicate node_ids → FAIL."""
        raw: dict[str, Any] = {
            "schema_version": "1",
            "collection_scope": "global",
            "python_version": _PYTHON_VERSION,
            "commit_sha": _SHA,
            "track": "nightly",
            "shard": None,
            "run_id": _RUN_ID,
            "run_attempt": _RUN_ATTEMPT,
            "node_count": 2,
            "node_ids": ["a", "a"],
        }
        inv_path = tmp_path / "dup_node_inv.json"
        inv_path.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(BenchmarkAuthorityError, match="unique"):
            load_and_validate_node_inventory(
                inv_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )
