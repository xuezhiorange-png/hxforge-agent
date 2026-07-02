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
        cwd="/root/hxforge-agent",
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
        result = _read_and_validate_outcomes(outcomes_path)
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
            cwd="/root/hxforge-agent",
            env={**os.environ, "PYTHONPATH": "."},
        )
        # Check a different (missing) path
        missing_path = tmp_path / "definitely-not-there.json"
        result = _read_and_validate_outcomes(missing_path)
        assert result is None
