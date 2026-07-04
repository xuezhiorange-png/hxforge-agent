"""P1-1: Tests for the structured outcome plugin with real pytest subprocess runs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _run_with_outcome_plugin(
    tmp_path: Path,
    test_content: str,
) -> tuple[subprocess.CompletedProcess[str], dict | None]:
    """Write a test file, run pytest with the outcome plugin, return result + parsed outcomes."""
    test_file = tmp_path / "test_phases.py"
    test_file.write_text(test_content, encoding="utf-8")
    outcomes_path = tmp_path / "pytest-outcomes.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(test_file),
            "-p",
            "tests.ci.outcome_plugin",
            f"--hx-outcome-output={outcomes_path}",
            "--tb=short",
            "-q",
        ],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent.parent),
        env={**os.environ, "PYTHONPATH": "."},
    )

    outcomes = None
    if outcomes_path.is_file():
        try:
            outcomes = json.loads(outcomes_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            outcomes = None

    return result, outcomes


def _get_single_outcome(outcomes: dict) -> str:
    """Extract the single outcome value from a one-test outcomes dict."""
    vals = list(outcomes["outcomes"].values())
    assert len(vals) == 1, f"Expected 1 outcome, got {len(vals)}: {vals}"
    return vals[0]


class TestOutcomePlugin:
    """P1-1: Structured outcome plugin tests with real pytest subprocess runs."""

    def test_phase_setup_pass_call_pass_teardown_pass(self, tmp_path: Path) -> None:
        """Normal passing test → final: passed."""
        _, outcomes = _run_with_outcome_plugin(
            tmp_path,
            "def test_normal():\n    assert True\n",
        )
        assert outcomes is not None
        assert outcomes["schema_version"] == "1"
        assert outcomes["total"] == 1
        assert _get_single_outcome(outcomes) == "passed"

    def test_phase_setup_pass_call_fail_teardown_pass(self, tmp_path: Path) -> None:
        """Failing test → final: failed (teardown pass does NOT override call fail)."""
        _, outcomes = _run_with_outcome_plugin(
            tmp_path,
            "def test_normal():\n    assert False\n",
        )
        assert outcomes is not None
        assert _get_single_outcome(outcomes) == "failed"

    def test_phase_setup_fail_teardown_pass(self, tmp_path: Path) -> None:
        """Setup failure → final: failed (teardown pass does NOT override setup fail)."""
        _, outcomes = _run_with_outcome_plugin(
            tmp_path,
            "class TestSetup:\n"
            "    def setup_method(self):\n"
            '        raise RuntimeError("setup failed")\n'
            "    def test_something(self):\n"
            "        pass\n",
        )
        assert outcomes is not None
        assert _get_single_outcome(outcomes) == "failed"

    def test_phase_setup_skip(self, tmp_path: Path) -> None:
        """Skipped test → final: skipped."""
        _, outcomes = _run_with_outcome_plugin(
            tmp_path,
            "import pytest\n\n@pytest.mark.skip(reason='skip this')\ndef test_skip():\n    pass\n",
        )
        assert outcomes is not None
        assert _get_single_outcome(outcomes) == "skipped"

    def test_xfail_non_strict(self, tmp_path: Path) -> None:
        """xfail (non-strict, failing) → final: xfailed."""
        _, outcomes = _run_with_outcome_plugin(
            tmp_path,
            "import pytest\n\n"
            "@pytest.mark.xfail(strict=False)\n"
            "def test_xfail():\n"
            "    assert False\n",
        )
        assert outcomes is not None
        assert _get_single_outcome(outcomes) == "xfailed"

    def test_xpass_non_strict(self, tmp_path: Path) -> None:
        """xfail (non-strict, passing) → final: xpassed."""
        _, outcomes = _run_with_outcome_plugin(
            tmp_path,
            "import pytest\n\n"
            "@pytest.mark.xfail(strict=False)\n"
            "def test_xpass():\n"
            "    assert True\n",
        )
        assert outcomes is not None
        assert _get_single_outcome(outcomes) == "xpassed"

    def test_teardown_fail_after_call_pass(self, tmp_path: Path) -> None:
        """Teardown failure after call pass → final: failed."""
        _, outcomes = _run_with_outcome_plugin(
            tmp_path,
            "class TestTeardown:\n"
            "    def teardown_method(self):\n"
            '        raise RuntimeError("teardown failed")\n'
            "    def test_something(self):\n"
            "        pass\n",
        )
        assert outcomes is not None
        assert _get_single_outcome(outcomes) == "failed"

    def test_malformed_outcomes_file(self, tmp_path: Path) -> None:
        """Malformed outcomes file → outcome_parse_status = unavailable."""
        from tests.ci.run_test_shard import _read_and_validate_outcomes

        # Run pytest normally to get a valid file
        _run_with_outcome_plugin(
            tmp_path,
            "def test_ok():\n    pass\n",
        )
        outcomes_path = tmp_path / "pytest-outcomes.json"
        # Corrupt the file
        outcomes_path.write_text("NOT VALID JSON {{{", encoding="utf-8")
        # Verify validation rejects it
        result, _inv = _read_and_validate_outcomes(outcomes_path)
        assert result is None

    def test_missing_outcomes_file(self, tmp_path: Path) -> None:
        """Missing outcomes file → outcome_parse_status = unavailable."""
        from tests.ci.run_test_shard import _read_and_validate_outcomes

        # Run pytest with the plugin (creates a valid file somewhere)
        test_file = tmp_path / "test_phases.py"
        test_file.write_text("def test_ok():\n    pass\n", encoding="utf-8")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(test_file),
                "-p",
                "tests.ci.outcome_plugin",
                f"--hx-outcome-output={tmp_path / 'pytest-outcomes.json'}",
                "--tb=short",
                "-q",
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent.parent),
            env={**os.environ, "PYTHONPATH": "."},
        )
        # Check a different (missing) path
        missing_path = tmp_path / "definitely-not-there.json"
        result, _inv = _read_and_validate_outcomes(missing_path)
        assert result is None


# ── P0-3: Exact node equality tests ──────────────────────────────────────────


def _make_outcomes_json(
    tmp_path: Path,
    outcomes: dict[str, str],
    collection_complete: list[str] | None = None,
) -> Path:
    """Create a pytest-outcomes.json file."""
    cc = collection_complete if collection_complete is not None else sorted(outcomes.keys())
    data = {
        "schema_version": "1",
        "outcomes": dict(sorted(outcomes.items())),
        "total": len(outcomes),
        "collection_complete": sorted(cc),
    }
    path = tmp_path / "pytest-outcomes.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _make_node_inventory(
    tmp_path: Path,
    node_ids: list[str],
) -> Path:
    """Create a node-inventory.json file."""
    data = {
        "schema_version": "1",
        "node_ids": sorted(node_ids),
        "node_count": len(node_ids),
    }
    path = tmp_path / "node-inventory.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_p03_outcomes_missing_node_rejected(tmp_path: Path) -> None:
    """Outcomes missing one node vs collection_complete → rejected."""
    from tests.ci.run_test_shard import _read_and_validate_outcomes

    outcomes = {"a/test_one.py::test_a": "passed", "a/test_two.py::test_b": "passed"}
    _make_outcomes_json(
        tmp_path,
        outcomes,
        collection_complete=[
            "a/test_one.py::test_a",
            "a/test_two.py::test_b",
            "a/test_three.py::test_c",  # extra in cc
        ],
    )
    inv_path = _make_node_inventory(tmp_path, list(outcomes.keys()))
    result, _inv = _read_and_validate_outcomes(
        tmp_path / "pytest-outcomes.json",
        node_inventory_path=inv_path,
    )
    assert result is None, "must reject: collection_complete has extra node not in outcomes"


def test_p03_outcomes_extra_node_rejected(tmp_path: Path) -> None:
    """Outcomes has extra node not in collection_complete → rejected."""
    from tests.ci.run_test_shard import _read_and_validate_outcomes

    outcomes = {
        "a/test_one.py::test_a": "passed",
        "a/test_two.py::test_b": "passed",
        "a/test_three.py::test_c": "passed",
    }
    _make_outcomes_json(
        tmp_path,
        outcomes,
        collection_complete=[
            "a/test_one.py::test_a",
            "a/test_two.py::test_b",
            # missing test_three
        ],
    )
    inv_path = _make_node_inventory(tmp_path, list(outcomes.keys()))
    result, _inv = _read_and_validate_outcomes(
        tmp_path / "pytest-outcomes.json",
        node_inventory_path=inv_path,
    )
    assert result is None, "must reject: collection_complete missing a node from outcomes"


def test_p03_collection_complete_has_duplicates_rejected(tmp_path: Path) -> None:
    """collection_complete has duplicate node → rejected."""
    from tests.ci.run_test_shard import _read_and_validate_outcomes

    outcomes = {"a/test_one.py::test_a": "passed"}
    _make_outcomes_json(
        tmp_path,
        outcomes,
        collection_complete=[
            "a/test_one.py::test_a",
            "a/test_one.py::test_a",  # duplicate
        ],
    )
    result, _inv = _read_and_validate_outcomes(tmp_path / "pytest-outcomes.json")
    assert result is None, "must reject: duplicate in collection_complete"


def test_p03_collection_complete_differs_from_outcomes(tmp_path: Path) -> None:
    """collection_complete has same length but different node → rejected."""
    from tests.ci.run_test_shard import _read_and_validate_outcomes

    outcomes = {"a/test_one.py::test_a": "passed"}
    _make_outcomes_json(
        tmp_path,
        outcomes,
        collection_complete=[
            "a/test_different.py::test_x",  # different node, same count
        ],
    )
    result, _inv = _read_and_validate_outcomes(tmp_path / "pytest-outcomes.json")
    assert result is None, "must reject: collection_complete has different node"


def test_p03_node_inventory_differs_from_outcomes(tmp_path: Path) -> None:
    """Node inventory has same count but different nodes → rejected."""
    from tests.ci.run_test_shard import _read_and_validate_outcomes

    outcomes = {"a/test_one.py::test_a": "passed"}
    _make_outcomes_json(tmp_path, outcomes)
    inv_path = _make_node_inventory(tmp_path, ["b/test_other.py::test_x"])
    result, _inv = _read_and_validate_outcomes(
        tmp_path / "pytest-outcomes.json",
        node_inventory_path=inv_path,
    )
    assert result is None, "must reject: node inventory has different nodes"


def test_p03_valid_three_way_equality(tmp_path: Path) -> None:
    """Valid: outcomes, collection_complete, and node_inventory all match."""
    from tests.ci.run_test_shard import _read_and_validate_outcomes

    nodes = ["a/test_one.py::test_a", "b/test_two.py::test_b"]
    outcomes = {n: "passed" for n in nodes}
    _make_outcomes_json(tmp_path, outcomes)
    inv_path = _make_node_inventory(tmp_path, nodes)
    result, inv = _read_and_validate_outcomes(
        tmp_path / "pytest-outcomes.json",
        node_inventory_path=inv_path,
    )
    assert result is not None, "valid three-way equality should be accepted"
    assert inv.status == "available"


# ── P0-4: XPASS runner cross-validation tests ────────────────────────────────


def _run_outcome_with_test(tmp_path: Path, test_content: str) -> dict:
    """Run a test file with the outcome plugin and return parsed outcomes."""
    test_file = tmp_path / "test_x.py"
    test_file.write_text(test_content, encoding="utf-8")
    outcomes_path = tmp_path / "pytest-outcomes.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(test_file),
            "-p",
            "tests.ci.outcome_plugin",
            f"--hx-outcome-output={outcomes_path}",
            "--tb=short",
            "-q",
        ],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent.parent),
        env={**os.environ, "PYTHONPATH": "."},
    )
    if outcomes_path.exists():
        return json.loads(outcomes_path.read_text(encoding="utf-8"))
    return {}


def test_p04_xpass_non_strict(tmp_path: Path) -> None:
    """Non-strict XPASS: xfail(strict=False) + assert True → xpassed."""
    outcomes = _run_outcome_with_test(
        tmp_path,
        "import pytest\n@pytest.mark.xfail(strict=False)\ndef test_xpass():\n    assert True\n",
    )
    assert outcomes.get("outcomes", {}).get("test_x.py::test_xpass") == "xpassed"
    assert outcomes.get("total") == 1


def test_p04_xfail_normal(tmp_path: Path) -> None:
    """Normal xfail: xfail + assert False → xfailed."""
    outcomes = _run_outcome_with_test(
        tmp_path,
        "import pytest\n@pytest.mark.xfail\ndef test_xfail():\n    assert False\n",
    )
    assert outcomes.get("outcomes", {}).get("test_x.py::test_xfail") == "xfailed"


def test_p04_normal_pass(tmp_path: Path) -> None:
    """Normal pass."""
    outcomes = _run_outcome_with_test(
        tmp_path,
        "def test_pass():\n    assert True\n",
    )
    assert outcomes.get("outcomes", {}).get("test_x.py::test_pass") == "passed"


def test_p04_normal_fail(tmp_path: Path) -> None:
    """Normal fail."""
    outcomes = _run_outcome_with_test(
        tmp_path,
        "def test_fail():\n    assert False\n",
    )
    assert outcomes.get("outcomes", {}).get("test_x.py::test_fail") == "failed"


def test_p04_normal_skip(tmp_path: Path) -> None:
    """Normal skip."""
    outcomes = _run_outcome_with_test(
        tmp_path,
        "import pytest\ndef test_skip():\n    pytest.skip('intentional')\n",
    )
    assert outcomes.get("outcomes", {}).get("test_x.py::test_skip") == "skipped"
