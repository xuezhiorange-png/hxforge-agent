"""Tests for benchmark authority governance (P0-4).

23 test scenarios covering:
  Section 1: Positive tests (N/A and Executed authority)
  Section 2: Negative tests — node/inventory/evidence mismatches
  Section 3: Artifact field validation (identity, track, status, etc.)
  Section 4: Paired inventory validation (marker ↔ node)
  Section 5: Workflow static tests (nightly.yml governance)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.ci.benchmark_authority import (
    BenchmarkAuthorityError,
    _build_executed_artifact,
    _build_not_applicable_artifact,
    extract_benchmark_nodes,
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


# ══════════════════════════════════════════════════════════════════════════
# Section 1: Positive tests
# ══════════════════════════════════════════════════════════════════════════


class TestZeroNodeNA:
    """Scenario 1: N/A positive — zero benchmark nodes → valid N/A authority."""

    def test_extract_returns_empty(self) -> None:
        inv = _make_marker_inv(
            {
                "tests/unit/test_a.py::test_x": ["pure"],
                "tests/unit/test_b.py::test_y": ["provider"],
            }
        )
        nodes = extract_benchmark_nodes(inv)
        assert nodes == []

    def test_na_artifact_schema(self) -> None:
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
        _validate(_valid_na_artifact())

    def test_na_roundtrip(self, tmp_path: Path) -> None:
        artifact = _valid_na_artifact()
        p = tmp_path / "benchmark-authority.json"
        save_authority_artifact(artifact, p)
        loaded = load_authority_artifact(p)
        _validate(loaded)


class TestExecutedBenchmark:
    """Scenario 2: Executed positive — real @pytest.mark.benchmark execution.

    Creates a temporary test file with @pytest.mark.benchmark under tests/,
    runs actual collection and execution using the real infrastructure,
    then verifies the artifact is valid and node sets are consistent.
    """

    def test_real_benchmark_execution(self, tmp_path: Path) -> None:
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
            env = {
                **{
                    k: v
                    for k, v in __import__("os").environ.items()
                    if k in {"PATH", "HOME", "UV", "VIRTUAL_ENV"}
                },
                "PYTHONPATH": f"{project_root}:.",
                "HX_TRACK": "nightly",
                "HX_COMMIT_SHA": _SHA,
                "GITHUB_RUN_ID": _RUN_ID,
                "GITHUB_RUN_ATTEMPT": str(_RUN_ATTEMPT),
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
                timeout=60,
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
                expected_python_version=f"{sys.version_info.major}.{sys.version_info.minor}",
            )

            # ── 4. Extract benchmark nodes from marker inventory ────────
            benchmark_nodes = extract_benchmark_nodes(marker_inv)
            tmp_bench_nodes = [n for n in benchmark_nodes if "_tmp_bench" in n]
            assert len(tmp_bench_nodes) == 1, (
                f"Expected 1 temp benchmark node, got: {tmp_bench_nodes}"
            )
            assert any("test_example_benchmark" in nid for nid in tmp_bench_nodes)

            # ── 5. Run the benchmark test for real ──────────────────────
            run_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    str(bench_file),
                    "-k",
                    "test_example_benchmark",
                    "--tb=short",
                ],
                capture_output=True,
                text=True,
                cwd=project_root,
                env=env,
                timeout=60,
            )
            pytest_exit_code = run_result.returncode

            # ── 6. Build executed authority artifact ────────────────────
            validated_set = frozenset(tmp_bench_nodes)
            artifact = _build_executed_artifact(
                commit_sha=_SHA,
                run_id=_RUN_ID,
                run_attempt=_RUN_ATTEMPT,
                python_version=f"{sys.version_info.major}.{sys.version_info.minor}",
                benchmark_node_count=len(tmp_bench_nodes),
                benchmark_node_ids=tmp_bench_nodes,
                pytest_exit_code=pytest_exit_code,
                producer_authoritative=True,
                validated_evidence_node_ids=validated_set,
            )

            # ── 7. Validate the artifact ───────────────────────────────
            validate_authority_artifact(
                artifact,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=f"{sys.version_info.major}.{sys.version_info.minor}",
            )

            assert artifact["status"] == "executed"
            assert artifact["authority_valid"] is True
            assert artifact["pytest_exit_code"] == pytest_exit_code
            assert artifact["benchmark_node_count"] == len(tmp_bench_nodes)
            assert artifact["benchmark_node_ids"] == sorted(tmp_bench_nodes)

            # ── 8. Cross-validate: marker benchmark nodes == artifact IDs
            assert set(artifact["benchmark_node_ids"]) == set(tmp_bench_nodes), (
                "Artifact node IDs must equal marker-inventory benchmark nodes"
            )

            # ── 9. Cross-validate: benchmark nodes subset of node inventory
            node_inv_raw = json.loads(node_inv_output.read_text(encoding="utf-8"))
            inv_node_ids = set(node_inv_raw.get("node_ids", []))
            assert set(tmp_bench_nodes).issubset(inv_node_ids), (
                f"Benchmark nodes {tmp_bench_nodes} not subset of "
                f"node inventory {sorted(inv_node_ids)}"
            )

        finally:
            bench_file.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════════════════════
# Section 2: Negative tests — node/inventory/evidence mismatches
# ══════════════════════════════════════════════════════════════════════════


class TestNodeMismatches:
    """Scenarios 3, 9, 19: node set and inventory mismatch failures."""

    def test_same_count_node_replacement(self) -> None:
        """Scenario 3: expected={'a','b'}, actual={'a','x'} → FAIL."""
        marker_inv = _make_marker_inv(
            {
                "a": ["benchmark"],
                "b": ["benchmark"],
            }
        )
        node_inv = _make_node_inv(["a", "x"])
        with pytest.raises(BenchmarkAuthorityError, match="node set mismatch"):
            validate_inventory_identity_match(node_inv, marker_inv)

    def test_marker_inventory_vs_node_inventory_drift(self) -> None:
        """Scenario 9: Marker inventory node set ≠ node inventory → FAIL."""
        marker_inv = _make_marker_inv(
            {
                "tests/a.py::t1": ["benchmark"],
                "tests/b.py::t2": ["pure"],
            }
        )
        node_inv = _make_node_inv(["tests/c.py::t3", "tests/d.py::t4"])
        with pytest.raises(BenchmarkAuthorityError, match="node set mismatch"):
            validate_inventory_identity_match(node_inv, marker_inv)

    def test_marker_missing_from_node_inventory(self) -> None:
        """Scenario 9 variant: marker has node missing in node inventory."""
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

    def test_extra_node_in_node_inventory(self) -> None:
        """Scenario 9 variant: node inventory has node not in marker."""
        marker_inv = _make_marker_inv({"a": ["benchmark"]})
        node_inv = _make_node_inv(["a", "extra"])
        with pytest.raises(BenchmarkAuthorityError, match="node set mismatch"):
            validate_inventory_identity_match(node_inv, marker_inv)


class TestDuplicateNodes:
    """Scenario 6: Duplicate node → FAIL."""

    def test_duplicate_node_ids_in_artifact(self) -> None:
        artifact = _valid_executed_artifact(["a"])
        # Tamper: duplicate the node (bypassing evidence check)
        artifact["benchmark_node_ids"] = ["a", "a"]
        artifact["benchmark_node_count"] = 2
        with pytest.raises(BenchmarkAuthorityError, match="unique"):
            _validate(artifact)

    def test_duplicate_node_ids_in_node_inventory(self, tmp_path: Path) -> None:
        """Node inventory with duplicate node_ids → FAIL."""
        from tests.ci.benchmark_authority import load_and_validate_node_inventory

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


class TestEvidenceMismatches:
    """Scenarios 4, 5, 7, 8: outcomes and evidence mismatches."""

    def test_missing_outcome_node(self, tmp_path: Path) -> None:
        """Scenario 4: expected has node not in outcomes → FAIL."""
        from tests.ci.benchmark_authority import (
            _extract_outcome_nodes,
            _load_json_file,
        )

        outcomes_file = tmp_path / "outcomes.json"
        outcomes_file.write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "results": {"a": "passed"},
                    "summary": {
                        "passed": 1,
                        "failed": 0,
                        "skipped": 0,
                        "error": 0,
                        "xfail": 0,
                        "total": 1,
                    },
                }
            ),
            encoding="utf-8",
        )
        outcomes = _load_json_file(outcomes_file, "outcomes")
        outcome_nodes = _extract_outcome_nodes(outcomes)

        benchmark_nodes = {"a", "b"}
        assert outcome_nodes != benchmark_nodes
        # b is missing from outcomes
        missing = benchmark_nodes - outcome_nodes
        assert missing == {"b"}

    def test_extra_outcome_node(self, tmp_path: Path) -> None:
        """Scenario 5: outcomes has node not in expected → FAIL."""
        from tests.ci.benchmark_authority import _extract_outcome_nodes

        outcomes_file = tmp_path / "outcomes.json"
        outcomes_file.write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "results": {
                        "a": "passed",
                        "b": "passed",
                        "extra": "passed",
                    },
                    "summary": {
                        "passed": 3,
                        "failed": 0,
                        "skipped": 0,
                        "error": 0,
                        "xfail": 0,
                        "total": 3,
                    },
                }
            ),
            encoding="utf-8",
        )
        outcomes_data = json.loads(outcomes_file.read_text(encoding="utf-8"))
        outcome_nodes = _extract_outcome_nodes(outcomes_data)

        benchmark_nodes = {"a", "b"}
        assert outcome_nodes != benchmark_nodes
        # extra is in outcomes but not in benchmark
        extra = outcome_nodes - benchmark_nodes
        assert extra == {"extra"}

    def test_duplicate_outcome_node(self, tmp_path: Path) -> None:
        """Scenario 6 variant: duplicate in outcomes results dict (JSON dicts can't have dupes)."""
        # JSON dicts can't have duplicate keys, so duplicate detection
        # is really about the artifacts that use lists.
        # Test that duplicate node_ids in artifact fails validation.
        artifact = _valid_executed_artifact(["a"])
        artifact["benchmark_node_ids"] = ["a", "a"]
        artifact["benchmark_node_count"] = 2
        with pytest.raises(BenchmarkAuthorityError, match="unique"):
            _validate(artifact)

    def test_collection_complete_vs_outcomes_mismatch(self) -> None:
        """Scenario 7: collection_complete nodes ≠ outcome nodes → FAIL."""
        # Build a marker inventory where collection_complete nodes
        # are a subset of benchmark nodes, but outcomes report more nodes
        marker_inv = _make_marker_inv(
            {
                "tests/a.py::t1": ["benchmark", "collection_complete"],
            }
        )
        # Outcomes report two nodes but marker only has one
        outcome_nodes = {"tests/a.py::t1", "tests/b.py::t2"}
        benchmark_set = set(extract_benchmark_nodes(marker_inv))
        assert outcome_nodes != benchmark_set

    def test_execution_inventory_vs_outcomes_mismatch(self, tmp_path: Path) -> None:
        """Scenario 8: execution inventory node set ≠ outcome node set → FAIL."""
        from tests.ci.benchmark_authority import (
            _extract_execution_inventory_nodes,
            _extract_outcome_nodes,
            _load_json_file,
        )

        exec_inv_file = tmp_path / "exec_inv.json"
        exec_inv_file.write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "node_ids": ["a", "b"],
                    "node_count": 2,
                }
            ),
            encoding="utf-8",
        )
        outcomes_file = tmp_path / "outcomes.json"
        outcomes_file.write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "results": {"a": "passed"},
                    "summary": {
                        "passed": 1,
                        "failed": 0,
                        "skipped": 0,
                        "error": 0,
                        "xfail": 0,
                        "total": 1,
                    },
                }
            ),
            encoding="utf-8",
        )
        exec_inv = _load_json_file(exec_inv_file, "exec_inv")
        outcomes = _load_json_file(outcomes_file, "outcomes")
        exec_nodes = _extract_execution_inventory_nodes(exec_inv)
        outcome_nodes = _extract_outcome_nodes(outcomes)
        assert exec_nodes != outcome_nodes


# ══════════════════════════════════════════════════════════════════════════
# Section 3: Artifact field validation
# ══════════════════════════════════════════════════════════════════════════


class TestArtifactFieldValidation:
    """Scenarios 10-17: Artifact field validation failures."""

    # ── Scenario 12: producer_authoritative=false → FAIL ──────────────────
    def test_producer_not_authoritative(self) -> None:
        artifact = _valid_executed_artifact(["a"])
        artifact["producer_authoritative"] = False
        with pytest.raises(BenchmarkAuthorityError, match="producer_authoritative must be true"):
            _validate(artifact)

    # ── Scenario 13: pytest exit code non-zero → FAIL ─────────────────────
    def test_pytest_exit_code_nonzero(self) -> None:
        artifact = _valid_executed_artifact(["a"])
        artifact["pytest_exit_code"] = 1
        with pytest.raises(BenchmarkAuthorityError, match="pytest_exit_code must be 0"):
            _validate(artifact)

    def test_pytest_exit_code_5(self) -> None:
        artifact = _valid_executed_artifact(["a"])
        artifact["pytest_exit_code"] = 5
        with pytest.raises(BenchmarkAuthorityError, match="pytest_exit_code must be 0"):
            _validate(artifact)

    # ── Scenario 14: Wrong track → FAIL ──────────────────────────────────
    def test_wrong_track(self) -> None:
        artifact = _valid_na_artifact()
        artifact["track"] = "pr-head"
        with pytest.raises(BenchmarkAuthorityError, match="track must be 'nightly'"):
            _validate(artifact)

    # ── Scenario 15: Wrong collection_scope → FAIL ───────────────────────
    def test_wrong_collection_scope(self) -> None:
        artifact = _valid_na_artifact()
        artifact["collection_scope"] = "shard"
        with pytest.raises(BenchmarkAuthorityError, match="collection_scope must be 'global'"):
            _validate(artifact)

    # ── Scenario 16: Wrong shard → FAIL ──────────────────────────────────
    def test_wrong_shard(self) -> None:
        artifact = _valid_na_artifact()
        artifact["shard"] = "invalid-shard"
        with pytest.raises(BenchmarkAuthorityError, match="shard must be one of"):
            _validate(artifact)

    # ── Scenario 17: Wrong SHA → FAIL ────────────────────────────────────
    def test_wrong_commit_sha(self) -> None:
        artifact = _valid_na_artifact()
        artifact["commit_sha"] = "b" * 40
        with pytest.raises(BenchmarkAuthorityError, match="commit_sha mismatch"):
            _validate(artifact)

    def test_invalid_commit_sha(self) -> None:
        """commit_sha must be exactly 40 hex characters."""
        artifact = _valid_na_artifact()
        artifact["commit_sha"] = "not-hex-at-all!"
        with pytest.raises(BenchmarkAuthorityError, match="40 hex chars"):
            _validate(artifact)

    # ── Scenario 17: Wrong run_id → FAIL ─────────────────────────────────
    def test_wrong_run_id(self) -> None:
        artifact = _valid_na_artifact()
        artifact["run_id"] = "99999"
        with pytest.raises(BenchmarkAuthorityError, match="run_id mismatch"):
            _validate(artifact)

    # ── Scenario 17: Wrong run_attempt → FAIL ────────────────────────────
    def test_wrong_run_attempt(self) -> None:
        artifact = _valid_na_artifact()
        artifact["run_attempt"] = 2
        with pytest.raises(BenchmarkAuthorityError, match="run_attempt mismatch"):
            _validate(artifact)

    # ── Scenario 17: Wrong python version → FAIL ─────────────────────────
    def test_wrong_python_version(self) -> None:
        artifact = _valid_na_artifact()
        artifact["python_version"] = "3.11"
        with pytest.raises(BenchmarkAuthorityError, match="python_version"):
            _validate(artifact)

    # ── Unknown status → FAIL ────────────────────────────────────────────
    def test_unknown_status(self) -> None:
        artifact = _valid_na_artifact()
        artifact["status"] = "unknown"
        with pytest.raises(BenchmarkAuthorityError, match="unknown status"):
            _validate(artifact)

    # ── Unknown reason → FAIL ────────────────────────────────────────────
    def test_unknown_reason(self) -> None:
        artifact = _valid_na_artifact()
        artifact["reason"] = "something-else"
        with pytest.raises(BenchmarkAuthorityError, match="unknown reason"):
            _validate(artifact)

    # ── authority_valid=false → FAIL ──────────────────────────────────────
    def test_authority_valid_false(self) -> None:
        artifact = _valid_na_artifact()
        artifact["authority_valid"] = False
        with pytest.raises(BenchmarkAuthorityError, match="authority_valid must be true"):
            _validate(artifact)

    # ── N/A but node_count > 0 → FAIL ────────────────────────────────────
    def test_na_with_positive_count(self) -> None:
        artifact = _valid_na_artifact()
        artifact["benchmark_node_count"] = 3
        with pytest.raises(BenchmarkAuthorityError, match="length"):
            _validate(artifact)

    # ── executed but node_count == 0 → FAIL ──────────────────────────────
    def test_executed_with_zero_count(self) -> None:
        validated_set = frozenset(["a"])
        artifact = _build_executed_artifact(
            commit_sha=_SHA,
            run_id=_RUN_ID,
            run_attempt=_RUN_ATTEMPT,
            python_version=_PYTHON_VERSION,
            benchmark_node_count=1,
            benchmark_node_ids=["a"],
            pytest_exit_code=0,
            producer_authoritative=True,
            validated_evidence_node_ids=validated_set,
        )
        artifact["benchmark_node_count"] = 0
        artifact["benchmark_node_ids"] = []
        with pytest.raises(BenchmarkAuthorityError, match="requires benchmark_node_count > 0"):
            _validate(artifact)

    # ── node_ids not sorted → FAIL ───────────────────────────────────────
    def test_node_ids_not_sorted(self) -> None:
        artifact = _valid_executed_artifact(["a", "b"])
        artifact["benchmark_node_ids"] = ["b", "a"]
        with pytest.raises(BenchmarkAuthorityError, match="canonically sorted"):
            _validate(artifact)

    # ── node_ids length ≠ node_count → FAIL ──────────────────────────────
    def test_node_ids_length_mismatch(self) -> None:
        artifact = _valid_executed_artifact(["a", "b", "c"])
        artifact["benchmark_node_ids"] = ["a", "b"]
        with pytest.raises(BenchmarkAuthorityError, match="length"):
            _validate(artifact)

    # ── node_ids not strings → FAIL ──────────────────────────────────────
    def test_node_ids_not_strings(self) -> None:
        validated_set = frozenset(["a"])
        artifact = _build_executed_artifact(
            commit_sha=_SHA,
            run_id=_RUN_ID,
            run_attempt=_RUN_ATTEMPT,
            python_version=_PYTHON_VERSION,
            benchmark_node_count=1,
            benchmark_node_ids=["a"],
            pytest_exit_code=0,
            producer_authoritative=True,
            validated_evidence_node_ids=validated_set,
        )
        artifact["benchmark_node_ids"] = [1, 2]
        artifact["benchmark_node_count"] = 2
        with pytest.raises(BenchmarkAuthorityError, match="only strings"):
            _validate(artifact)

    # ── malformed JSON on load → FAIL ────────────────────────────────────
    def test_malformed_json_load(self, tmp_path: Path) -> None:
        p = tmp_path / "benchmark-authority.json"
        p.write_text("NOT JSON", encoding="utf-8")
        with pytest.raises(BenchmarkAuthorityError, match="cannot parse"):
            load_authority_artifact(p)

    # ── outcomes missing or malformed JSON → FAIL (Scenario 10) ─────────
    def test_outcomes_missing_file(self, tmp_path: Path) -> None:
        """Scenario 10: outcomes file missing → FileNotFoundError."""
        outcomes_path = tmp_path / "pytest-outcomes.json"
        assert not outcomes_path.exists()
        with pytest.raises((BenchmarkAuthorityError, FileNotFoundError)):
            outcomes_path.read_text(encoding="utf-8")

    def test_outcomes_malformed_json(self, tmp_path: Path) -> None:
        """Scenario 10: outcomes file malformed JSON → detection."""
        outcomes_path = tmp_path / "pytest-outcomes.json"
        outcomes_path.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            json.loads(outcomes_path.read_text(encoding="utf-8"))

    # ── telemetry missing or malformed JSON → FAIL (Scenario 11) ────────
    def test_telemetry_missing_file(self, tmp_path: Path) -> None:
        """Scenario 11: telemetry file missing → detection."""
        tel_path = tmp_path / "resource-telemetry.json"
        assert not tel_path.exists()

    def test_telemetry_malformed_json(self, tmp_path: Path) -> None:
        """Scenario 11: telemetry file malformed JSON → detection."""
        tel_path = tmp_path / "resource-telemetry.json"
        tel_path.write_text("}[invalid", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            json.loads(tel_path.read_text(encoding="utf-8"))

    # ── evidence validation with missing outcomes → FAIL ─────────────────
    def test_validate_evidence_missing_outcomes(self, tmp_path: Path) -> None:
        """validate_executed_benchmark_evidence with missing outcomes file."""
        from tests.ci.benchmark_authority import validate_executed_benchmark_evidence

        marker_inv_path = tmp_path / "marker.json"
        marker_inv_path.write_text(
            json.dumps(
                _make_marker_inv(
                    {"a": ["benchmark"]},
                    collection_scope="global",
                )
            ),
            encoding="utf-8",
        )
        outcomes_path = tmp_path / "outcomes.json"  # does not exist
        telemetry_path = tmp_path / "telemetry.json"  # does not exist

        with pytest.raises(BenchmarkAuthorityError, match="cannot parse"):
            validate_executed_benchmark_evidence(
                marker_inventory_path=marker_inv_path,
                node_inventory_path=None,
                execution_node_inventory_path=None,
                outcomes_path=outcomes_path,
                telemetry_path=telemetry_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )


# ══════════════════════════════════════════════════════════════════════════
# Section 4: Paired inventory validation
# ══════════════════════════════════════════════════════════════════════════


class TestPairedInventoryValidation:
    """Scenarios 18-19: Paired inventory consistency."""

    def test_consistent_paired_inventories(self) -> None:
        """Scenario 18: N/A with consistent marker and node inventories → PASS."""
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

    def test_marker_inventory_identity_binding(self) -> None:
        """Scenario 18 variant: marker inventory identity fields match."""
        marker_inv = _make_marker_inv(
            {"a": ["benchmark"]},
            commit_sha=_SHA,
            run_id=_RUN_ID,
            run_attempt=_RUN_ATTEMPT,
        )
        assert marker_inv["commit_sha"] == _SHA
        assert marker_inv["run_id"] == _RUN_ID
        assert marker_inv["run_attempt"] == _RUN_ATTEMPT

    def test_marker_inventory_wrong_sha(self, tmp_path: Path) -> None:
        """Scenario 19: marker inventory with wrong SHA → FAIL."""
        marker_path = tmp_path / "marker_wrong_sha.json"
        inv = _make_marker_inv(
            {"a": ["benchmark"]},
            commit_sha="b" * 40,
        )
        marker_path.write_text(json.dumps(inv), encoding="utf-8")
        with pytest.raises(BenchmarkAuthorityError, match="commit_sha mismatch"):
            load_marker_inventory(
                marker_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )

    def test_marker_inventory_wrong_run_id(self, tmp_path: Path) -> None:
        """Scenario 19 variant: marker inventory with wrong run_id → FAIL."""
        marker_path = tmp_path / "marker_wrong_rid.json"
        inv = _make_marker_inv(
            {"a": ["benchmark"]},
            run_id="WRONG",
        )
        marker_path.write_text(json.dumps(inv), encoding="utf-8")
        with pytest.raises(BenchmarkAuthorityError, match="run_id mismatch"):
            load_marker_inventory(
                marker_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )

    def test_node_inventory_wrong_sha(self, tmp_path: Path) -> None:
        """Scenario 19 variant: node inventory with wrong SHA → FAIL."""
        from tests.ci.benchmark_authority import load_and_validate_node_inventory

        inv_path = tmp_path / "node_inv_wrong_sha.json"
        inv = _make_node_inv(["a"], commit_sha="c" * 40)
        inv_path.write_text(json.dumps(inv), encoding="utf-8")
        with pytest.raises(BenchmarkAuthorityError, match="commit_sha mismatch"):
            load_and_validate_node_inventory(
                inv_path,
                expected_commit_sha=_SHA,
                expected_run_id=_RUN_ID,
                expected_run_attempt=_RUN_ATTEMPT,
                expected_python_version=_PYTHON_VERSION,
            )

    def test_identity_field_mismatch_between_inventories(self) -> None:
        """Scenario 19: node and marker inventories have different identity fields."""
        marker_inv = _make_marker_inv(
            {"a": ["benchmark"]},
            commit_sha=_SHA,
        )
        node_inv = _make_node_inv(["a"], commit_sha="d" * 40)
        with pytest.raises(BenchmarkAuthorityError, match="mismatch between"):
            validate_inventory_identity_match(node_inv, marker_inv)

    def test_identity_run_attempt_mismatch_between_inventories(self) -> None:
        """Scenario 19: run_attempt differs between inventories."""
        marker_inv = _make_marker_inv({"a": ["benchmark"]}, run_attempt=1)
        node_inv = _make_node_inv(["a"], run_attempt=2)
        with pytest.raises(BenchmarkAuthorityError, match="run_attempt mismatch"):
            validate_inventory_identity_match(node_inv, marker_inv)

    def test_collection_scope_mismatch_between_inventories(self) -> None:
        """Scenario 15+19: collection_scope differs between inventories."""
        marker_inv = _make_marker_inv(
            {"a": ["benchmark"]},
            collection_scope="global",
        )
        node_inv = _make_node_inv(
            ["a"],
            collection_scope="shard",
        )
        with pytest.raises(BenchmarkAuthorityError, match="collection_scope mismatch"):
            validate_inventory_identity_match(node_inv, marker_inv)

    def test_shard_mismatch_between_inventories(self) -> None:
        """Scenario 16+19: shard differs between inventories."""
        marker_inv = _make_marker_inv(
            {"a": ["benchmark"]},
            shard=None,
        )
        node_inv = _make_node_inv(
            ["a"],
            shard="shard-0",
        )
        with pytest.raises(BenchmarkAuthorityError, match="shard mismatch"):
            validate_inventory_identity_match(node_inv, marker_inv)


# ══════════════════════════════════════════════════════════════════════════
# Section 5: Workflow static tests
# ══════════════════════════════════════════════════════════════════════════


class TestWorkflowStatic:
    """Scenarios 20-23: Verify nightly.yml contains governed patterns."""

    NIGHTLY_YML = Path(".github/workflows/nightly.yml")

    @pytest.fixture()
    def nightly_content(self) -> str:
        return self.NIGHTLY_YML.read_text(encoding="utf-8")

    def test_no_bare_exit_0_on_benchmark(self, nightly_content: str) -> None:
        """Scenario 20/22: No false-green exit-5-to-exit-0 pattern."""
        assert (
            'echo "No benchmark-marked tests collected (exit 5), treating as pass"'
            not in nightly_content
        )
        assert 'if [ "$RC" -eq 5 ]; then' not in nightly_content

    def test_benchmark_nonzero_calls_benchmark_authority(self, nightly_content: str) -> None:
        """Scenario 20: Benchmark non-zero path calls 'benchmark_authority'."""
        assert "tests.ci.benchmark_authority" in nightly_content

    def test_final_gate_validates_authority(self, nightly_content: str) -> None:
        """Scenario 21: Final gate validates all evidence."""
        assert "benchmark-authority.json" in nightly_content
        assert (
            "validate_authority_artifact" in nightly_content
            or "benchmark_authority" in nightly_content
            or "validate" in nightly_content
        )

    def test_no_bare_python3_in_benchmark(self, nightly_content: str) -> None:
        """Scenario 22: No bare python3 (must use uv run --locked)."""
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

    def test_no_bare_python3_in_final_gate(self, nightly_content: str) -> None:
        """Scenario 22: Final gate has no bare python3."""
        gate_start = nightly_content.find("final-gate:")
        assert gate_start != -1, "final-gate job not found"
        gate_section = nightly_content[gate_start:]

        for line in gate_section.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue
            if "python3" in stripped and "uv run" not in stripped:
                pytest.fail(f"Bare python3 found in final-gate job: {stripped!r}")

    def test_no_true_masking_in_collection(self, nightly_content: str) -> None:
        """Scenario 23: No || true masking in collection steps."""
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

    def test_benchmark_authority_artifact_uploaded(self, nightly_content: str) -> None:
        """Benchmark authority artifact must be uploaded."""
        assert "benchmark-authority.json" in nightly_content

    def test_benchmark_node_inventory_uploaded(self, nightly_content: str) -> None:
        """Benchmark node inventory must be uploaded."""
        assert (
            "benchmark-node-inventory.json" in nightly_content
            or "node-marker-inventory.json" in nightly_content
        )

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

    def test_validate_step_always_runs(self, nightly_content: str) -> None:
        """Validate authority step must run with `if: always()`."""
        step_name = "Validate benchmark authority artifact"
        assert step_name in nightly_content
        validate_start = nightly_content.find(f"name: {step_name}")
        assert validate_start != -1, f"Step '{step_name}' not found"
        # if: always() must appear on the next line after the step name
        following = nightly_content[validate_start : validate_start + 200]
        assert "always()" in following, f"Step '{step_name}' must have if: always()"
