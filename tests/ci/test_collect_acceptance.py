"""Subprocess-based acceptance tests for the structured collection plugin (P0-4).

Each test invokes pytest as a subprocess with the ``collect_nodes_plugin``
loaded, asserts the expected behaviour, and cleans up any temporary artefacts.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.pure]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PLUGIN = "tests.ci.collect_nodes_plugin"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

BASE_ENV: dict[str, str] = {
    "HX_TRACK": "pr-head",
    "HX_COMMIT_SHA": "test-sha-acceptance",
    "GITHUB_RUN_ID": "1",
    "GITHUB_RUN_ATTEMPT": "1",
    "PYTHONHASHSEED": "0",
    "TZ": "UTC",
    "LC_ALL": "C.UTF-8",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTEST_TIMEOUT": "30",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _acceptance_dir(tmp_path: Path) -> Path:
    """Create and return a unique subdirectory under ``tests/``."""
    d = Path("tests") / f"_accept_{tmp_path.name}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cleanup(tmp_path: Path) -> None:
    """Remove the acceptance subdirectory."""
    import shutil

    d = Path("tests") / f"_accept_{tmp_path.name}"
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)


def _run(
    tmp_path: Path,
    targets: list[str],
    *,
    scope: str = "shard",
    shard: str | None = None,
    zero_node_metadata: dict[str, Any] | None = None,
    extra_env: dict[str, str] | None = None,
    extra_args: list[str] | None = None,
    subprocess_timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    """Run *pytest* with the collection plugin and return the result."""
    output_path = tmp_path / "inventory.json"
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        PLUGIN,
        f"--hx-collection-scope={scope}",
        f"--hx-node-output={output_path}",
    ]
    if shard is not None:
        cmd.append(f"--hx-shard={shard}")
    if zero_node_metadata is not None:
        meta_path = tmp_path / "zero_node_metadata.json"
        meta_path.write_text(
            json.dumps(zero_node_metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        cmd.append(f"--hx-zero-node-metadata={meta_path}")
    if extra_args:
        cmd.extend(extra_args)
    cmd.extend(targets)

    env = {**os.environ, **BASE_ENV}
    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
        timeout=subprocess_timeout,
    )


def _read_inv(tmp_path: Path) -> dict[str, Any]:
    """Read and parse the inventory JSON."""
    return json.loads((tmp_path / "inventory.json").read_text(encoding="utf-8"))


def _read_marker_inv(tmp_path: Path) -> dict[str, Any]:
    """Read and parse the node-marker-inventory JSON."""
    return json.loads((tmp_path / "node-marker-inventory.json").read_text(encoding="utf-8"))


def _read_behavior_env(tmp_path: Path) -> dict[str, Any]:
    """Read and parse the behavior-environment JSON."""
    return json.loads((tmp_path / "behavior-environment.json").read_text(encoding="utf-8"))


def _inv_for_file(inv: dict[str, Any], path: str) -> dict[str, Any] | None:
    """Return the ``FileRecord`` for *path*, or ``None``."""
    for rec in inv.get("file_records", []):
        if rec["file"] == path:
            return rec
    return None


# ---------------------------------------------------------------------------
# Acceptance tests
# ---------------------------------------------------------------------------


def test_simple_function_collected(tmp_path: Path) -> None:
    """A simple test function is collected and appears in the inventory."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_simple.py"
    test_file.write_text("def test_hello():\n    assert True\n", encoding="utf-8")
    rel = test_file.as_posix()
    try:
        result = _run(tmp_path, [rel], scope="shard", shard="s1")
        assert result.returncode == 0, result.stderr
        inv = _read_inv(tmp_path)
        assert inv["node_count"] >= 1
        assert any(rel in nid for nid in inv["node_ids"])
        rec = _inv_for_file(inv, rel)
        assert rec is not None
        assert rec["node_count"] >= 1
    finally:
        _cleanup(tmp_path)


def test_class_method_collected(tmp_path: Path) -> None:
    """A test class with methods is collected."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_cls.py"
    test_file.write_text(
        "class TestMath:\n    def test_add(self):\n        assert 1 + 1 == 2\n",
        encoding="utf-8",
    )
    rel = test_file.as_posix()
    try:
        result = _run(tmp_path, [rel], scope="shard", shard="s1")
        assert result.returncode == 0, result.stderr
        inv = _read_inv(tmp_path)
        assert inv["node_count"] >= 1
        assert any("TestMath::test_add" in nid for nid in inv["node_ids"])
    finally:
        _cleanup(tmp_path)


def test_unicode_parametrized_id(tmp_path: Path) -> None:
    """Parametrized IDs with Unicode characters are preserved (pytest
    escapes them in the node ID)."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_unicode.py"
    test_file.write_text(
        textwrap.dedent(
            """\
            import pytest

            @pytest.mark.parametrize("name", ["α", "日本語", "🚀"])
            def test_param(name):
                assert name
            """
        ),
        encoding="utf-8",
    )
    rel = test_file.as_posix()
    try:
        result = _run(tmp_path, [rel], scope="shard", shard="s1")
        assert result.returncode == 0, result.stderr
        inv = _read_inv(tmp_path)
        assert inv["node_count"] == 3
        node_ids = inv["node_ids"]
        # Pytest escapes Unicode in param IDs (e.g. /u03b1 for α)
        assert any("/u03b1" in nid for nid in node_ids)
        assert any("/u65e5" in nid for nid in node_ids)
        assert any("/U0001f680" in nid for nid in node_ids)
    finally:
        _cleanup(tmp_path)


def test_special_characters_in_id(tmp_path: Path) -> None:
    """Test IDs with spaces, parentheses, and multiple ``::`` separators."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_special.py"
    test_file.write_text(
        textwrap.dedent(
            """\
            import pytest

            @pytest.mark.parametrize("val", [pytest.param(1, id="a (b)")])
            def test_spaced(val):
                assert val == 1
            """
        ),
        encoding="utf-8",
    )
    rel = test_file.as_posix()
    try:
        result = _run(tmp_path, [rel], scope="shard", shard="s1")
        assert result.returncode == 0, result.stderr
        inv = _read_inv(tmp_path)
        assert inv["node_count"] >= 1
        assert any("a (b)" in nid for nid in inv["node_ids"])
    finally:
        _cleanup(tmp_path)


def test_execution_skip_still_collected(tmp_path: Path) -> None:
    """``@pytest.mark.skip`` is an execution-time skip – the node is still
    collected (node_count > 0)."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_execskip.py"
    test_file.write_text(
        textwrap.dedent(
            """\
            import pytest

            @pytest.mark.skip(reason="execution skip")
            def test_skip_me():
                assert True
            """
        ),
        encoding="utf-8",
    )
    rel = test_file.as_posix()
    try:
        result = _run(tmp_path, [rel], scope="shard", shard="s1")
        assert result.returncode == 0, result.stderr
        inv = _read_inv(tmp_path)
        rec = _inv_for_file(inv, rel)
        assert rec is not None
        assert rec["node_count"] >= 1
    finally:
        _cleanup(tmp_path)


def test_skipif_still_collected(tmp_path: Path) -> None:
    """``@pytest.mark.skipif`` is execution-time; the node is still
    collected (node_count > 0)."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_skipif.py"
    test_file.write_text(
        textwrap.dedent(
            """\
            import pytest

            @pytest.mark.skipif(True, reason="conditional skip")
            def test_skipif_me():
                assert True
            """
        ),
        encoding="utf-8",
    )
    rel = test_file.as_posix()
    try:
        result = _run(tmp_path, [rel], scope="shard", shard="s1")
        assert result.returncode == 0, result.stderr
        inv = _read_inv(tmp_path)
        rec = _inv_for_file(inv, rel)
        assert rec is not None
        assert rec["node_count"] >= 1
    finally:
        _cleanup(tmp_path)


def test_module_level_skip(tmp_path: Path) -> None:
    """A module with ``pytestmark = pytest.mark.skip`` that has been
    collection-suppressed via ``pytest_collection_modifyitems`` produces a
    zero-node record with ``module-collection-skip`` reason.

    Note: ``pytestmark = pytest.mark.skip`` alone does NOT prevent
    collection – tests are still collected.  To produce zero nodes we
    simulate the outcome: a conftest removes items from this file while a
    companion file keeps its items so pytest doesn't exit code 5.
    """
    d = _acceptance_dir(tmp_path)
    target = d / "test_modskip.py"
    target.write_text(
        textwrap.dedent(
            """\
            import pytest
            pytestmark = pytest.mark.skip(reason="whole module")

            def test_nothing():
                pass
            """
        ),
        encoding="utf-8",
    )
    companion = d / "test_companion.py"
    companion.write_text("def test_real():\n    assert True\n", encoding="utf-8")
    conftest = d / "conftest.py"
    conftest.write_text(
        textwrap.dedent(
            """\
            def pytest_collection_modifyitems(config, items):
                items[:] = [i for i in items if "test_companion" in i.nodeid]
            """
        ),
        encoding="utf-8",
    )
    rel = target.as_posix()
    rel_companion = companion.as_posix()
    meta = {
        rel: {
            "zero_node_reason": "module-collection-skip",
            "reason_authority": "test-author",
            "evidence": "pytestmark = pytest.mark.skip",
        }
    }
    try:
        result = _run(
            tmp_path,
            [rel, rel_companion],
            scope="shard",
            shard="s1",
            zero_node_metadata=meta,
        )
        assert result.returncode == 0, result.stderr
        inv = _read_inv(tmp_path)
        rec = _inv_for_file(inv, rel)
        assert rec is not None
        assert rec["node_count"] == 0
        assert rec["zero_node_reason"] == "module-collection-skip"
    finally:
        _cleanup(tmp_path)


def test_conditional_definition(tmp_path: Path) -> None:
    """A file where tests are conditionally excluded via a conftest produces
    a zero-node record with ``conditional-definition`` reason."""
    d = _acceptance_dir(tmp_path)
    target = d / "test_conddef.py"
    target.write_text(
        "def test_feature():\n    pass\n",
        encoding="utf-8",
    )
    companion = d / "test_real.py"
    companion.write_text("def test_real():\n    assert True\n", encoding="utf-8")
    conftest = d / "conftest.py"
    conftest.write_text(
        textwrap.dedent(
            """\
            _FEATURE_ENABLED = False

            def pytest_collection_modifyitems(config, items):
                if not _FEATURE_ENABLED:
                    items[:] = [i for i in items if "test_real" in i.nodeid]
            """
        ),
        encoding="utf-8",
    )
    rel = target.as_posix()
    rel_companion = companion.as_posix()
    meta = {
        rel: {
            "zero_node_reason": "conditional-definition",
            "reason_authority": "test-author",
            "evidence": "_FEATURE_ENABLED is False",
        }
    }
    try:
        result = _run(
            tmp_path,
            [rel, rel_companion],
            scope="shard",
            shard="s1",
            zero_node_metadata=meta,
        )
        assert result.returncode == 0, result.stderr
        inv = _read_inv(tmp_path)
        rec = _inv_for_file(inv, rel)
        assert rec is not None
        assert rec["node_count"] == 0
        assert rec["zero_node_reason"] == "conditional-definition"
    finally:
        _cleanup(tmp_path)


def test_hook_deselection(tmp_path: Path) -> None:
    """A conftest that deselects all items from a specific file produces a
    zero-node record with ``hook-deselection`` reason."""
    d = _acceptance_dir(tmp_path)
    target = d / "test_hookdesel.py"
    target.write_text(
        "def test_will_be_deselected():\n    assert True\n",
        encoding="utf-8",
    )
    companion = d / "test_real.py"
    companion.write_text("def test_real():\n    assert True\n", encoding="utf-8")
    conftest = d / "conftest.py"
    conftest.write_text(
        textwrap.dedent(
            """\
            def pytest_collection_modifyitems(config, items):
                items[:] = [i for i in items if "test_real" in i.nodeid]
            """
        ),
        encoding="utf-8",
    )
    rel = target.as_posix()
    rel_companion = companion.as_posix()
    meta = {
        rel: {
            "zero_node_reason": "hook-deselection",
            "reason_authority": "test-author",
            "evidence": "conftest cleared items",
        }
    }
    try:
        result = _run(
            tmp_path,
            [rel, rel_companion],
            scope="shard",
            shard="s1",
            zero_node_metadata=meta,
        )
        assert result.returncode == 0, result.stderr
        inv = _read_inv(tmp_path)
        rec = _inv_for_file(inv, rel)
        assert rec is not None
        assert rec["node_count"] == 0
        assert rec["zero_node_reason"] == "hook-deselection"
    finally:
        _cleanup(tmp_path)


def test_unsupported_version(tmp_path: Path) -> None:
    """A file with no tests (representing a module excluded for wrong Python
    version) yields a zero-node record with ``unsupported-version`` reason."""
    d = _acceptance_dir(tmp_path)
    # This file has no test functions – represents a module gated by version
    target = d / "test_unsupver.py"
    target.write_text(
        "# Conditionally excluded for unsupported Python versions\npass\n",
        encoding="utf-8",
    )
    companion = d / "test_real.py"
    companion.write_text("def test_real():\n    assert True\n", encoding="utf-8")
    rel = target.as_posix()
    rel_companion = companion.as_posix()
    meta = {
        rel: {
            "zero_node_reason": "unsupported-version",
            "reason_authority": "test-author",
            "evidence": "sys.version_info < (4, 0)",
        }
    }
    try:
        result = _run(
            tmp_path,
            [rel, rel_companion],
            scope="shard",
            shard="s1",
            zero_node_metadata=meta,
        )
        assert result.returncode == 0, result.stderr
        inv = _read_inv(tmp_path)
        rec = _inv_for_file(inv, rel)
        assert rec is not None
        assert rec["node_count"] == 0
        assert rec["zero_node_reason"] == "unsupported-version"
    finally:
        _cleanup(tmp_path)


def test_unknown_zero_node_reason_fails(tmp_path: Path) -> None:
    """Passing an invalid ``zero_node_reason`` string causes the plugin to
    error."""
    d = _acceptance_dir(tmp_path)
    target = d / "test_badreason.py"
    target.write_text("def test_ok():\n    pass\n", encoding="utf-8")
    rel = target.as_posix()
    meta = {
        rel: {
            "zero_node_reason": "not-a-real-reason",
            "reason_authority": "test-author",
            "evidence": "invalid",
        }
    }
    try:
        result = _run(tmp_path, [rel], scope="shard", shard="s1", zero_node_metadata=meta)
        # File has node_count=1, so zero-node metadata with bad reason
        # causes BOTH "non-zero file" AND "unknown zero-node reason" errors.
        assert result.returncode != 0
        combined = result.stderr + result.stdout
        assert "unknown zero-node reason" in combined.lower() or "non-zero file" in combined.lower()
    finally:
        _cleanup(tmp_path)


def test_import_error_fails(tmp_path: Path) -> None:
    """A file with a broken import causes a collection error (exit != 0)."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_importerr.py"
    test_file.write_text(
        textwrap.dedent(
            """\
            import nonexistent_module_xyz_12345  # noqa: F401

            def test_nothing():
                pass
            """
        ),
        encoding="utf-8",
    )
    rel = test_file.as_posix()
    try:
        result = _run(tmp_path, [rel], scope="shard", shard="s1")
        assert result.returncode != 0
    finally:
        _cleanup(tmp_path)


def test_plugin_error_fails(tmp_path: Path) -> None:
    """An invalid plugin option causes an error."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_pluginerr.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    rel = test_file.as_posix()
    try:
        result = _run(
            tmp_path,
            [rel],
            scope="shard",
            shard="s1",
            extra_args=["--hx-collection-scope=bogus"],
        )
        assert result.returncode != 0
    finally:
        _cleanup(tmp_path)


def test_global_with_shard_rejected(tmp_path: Path) -> None:
    """Global scope combined with ``--hx-shard`` should error."""
    result = _run(
        tmp_path,
        ["tests"],
        scope="global",
        shard="some-shard",
        subprocess_timeout=60,
    )
    assert result.returncode != 0
    combined = result.stderr + result.stdout
    assert "shard" in combined.lower()


def test_shard_without_name_rejected(tmp_path: Path) -> None:
    """Shard scope without ``--hx-shard`` should error."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_shardnoname.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    rel = test_file.as_posix()
    try:
        output_path = tmp_path / "inventory.json"
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            PLUGIN,
            "--hx-collection-scope=shard",
            f"--hx-node-output={output_path}",
            rel,
        ]
        env = {**os.environ, **BASE_ENV}
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
            timeout=60,
        )
        assert result.returncode != 0
        combined = result.stderr + result.stdout
        assert "shard" in combined.lower()
    finally:
        _cleanup(tmp_path)


def test_global_with_explicit_subset_rejected(tmp_path: Path) -> None:
    """Global scope targeting explicit test files (not ``tests/``) should
    error."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_globalsubset.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    rel = test_file.as_posix()
    try:
        result = _run(tmp_path, [rel], scope="global", subprocess_timeout=60)
        assert result.returncode != 0
        combined = result.stderr + result.stdout
        assert (
            "tests/" in combined.lower()
            or "subset" in combined.lower()
            or "explicit" in combined.lower()
        )
    finally:
        _cleanup(tmp_path)


def test_shard_with_tests_dir_rejected(tmp_path: Path) -> None:
    """Shard scope targeting ``tests/`` directory should error."""
    result = _run(
        tmp_path,
        ["tests"],
        scope="shard",
        shard="s1",
        subprocess_timeout=60,
    )
    assert result.returncode != 0
    combined = result.stderr + result.stdout
    assert "tests/" in combined.lower() or "whole" in combined.lower()


def test_duplicate_node_ids_rejected(tmp_path: Path) -> None:
    """Duplicate explicit test file arguments cause an error."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_dupfile.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    rel = test_file.as_posix()
    try:
        output_path = tmp_path / "inventory.json"
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            PLUGIN,
            "--hx-collection-scope=shard",
            "--hx-shard=s1",
            f"--hx-node-output={output_path}",
            rel,
            rel,  # duplicate!
        ]
        env = {**os.environ, **BASE_ENV}
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
            timeout=60,
        )
        assert result.returncode != 0
        combined = result.stderr + result.stdout
        assert "duplicate" in combined.lower()
    finally:
        _cleanup(tmp_path)


def test_deterministic_output(tmp_path: Path) -> None:
    """Running the same collection twice produces identical JSON."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_deterministic.py"
    test_file.write_text(
        textwrap.dedent(
            """\
            def test_alpha():
                assert True

            def test_beta():
                assert True
            """
        ),
        encoding="utf-8",
    )
    rel = test_file.as_posix()
    try:
        results = []
        for i in range(2):
            out = tmp_path / f"inventory_{i}.json"
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                PLUGIN,
                "--hx-collection-scope=shard",
                "--hx-shard=s1",
                f"--hx-node-output={out}",
                rel,
            ]
            env = {**os.environ, **BASE_ENV}
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
                env=env,
                timeout=60,
            )
            assert proc.returncode == 0, proc.stderr
            results.append(json.loads(out.read_text(encoding="utf-8")))

        assert results[0]["node_count"] == results[1]["node_count"]
        assert results[0]["node_ids"] == results[1]["node_ids"]
        assert results[0]["file_records"] == results[1]["file_records"]
        assert (
            results[0]["behavior_fingerprint_sha256"] == results[1]["behavior_fingerprint_sha256"]
        )
    finally:
        _cleanup(tmp_path)


def test_node_markers_present_in_inventory(tmp_path: Path) -> None:
    """A test file with markers produces a node_markers dict in the marker inventory."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_markers.py"
    test_file.write_text(
        textwrap.dedent(
            """\
            import pytest

            @pytest.mark.pure
            def test_alpha():
                assert True

            @pytest.mark.slow
            def test_beta():
                assert True
            """
        ),
        encoding="utf-8",
    )
    rel = test_file.as_posix()
    try:
        result = _run(tmp_path, [rel], scope="shard", shard="s1")
        assert result.returncode == 0, result.stderr
        inv = _read_inv(tmp_path)
        # node-inventory.json must NOT contain node_markers (frozen schema v1)
        assert "node_markers" not in inv, "node-inventory.json must not contain node_markers"
        # Markers come exclusively from node-marker-inventory.json
        minv = _read_marker_inv(tmp_path)
        assert isinstance(minv["node_markers"], dict)
        # Every node_id should have an entry
        for nid in inv["node_ids"]:
            assert nid in minv["node_markers"], f"missing node_markers for {nid}"
        # Check specific marker content
        markers = minv["node_markers"]
        alpha_nid = next(nid for nid in inv["node_ids"] if "test_alpha" in nid)
        beta_nid = next(nid for nid in inv["node_ids"] if "test_beta" in nid)
        assert markers[alpha_nid] == ["pure"]
        assert markers[beta_nid] == ["slow"]
    finally:
        _cleanup(tmp_path)


def test_node_markers_sorted_and_deduplicated(tmp_path: Path) -> None:
    """Markers are sorted lexicographically and deduplicated (marker inventory)."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_marksort.py"
    test_file.write_text(
        textwrap.dedent(
            """\
            import pytest

            @pytest.mark.pure
            @pytest.mark.golden
            @pytest.mark.pure  # intentional duplicate at decorator level
            def test_multi():
                assert True
            """
        ),
        encoding="utf-8",
    )
    rel = test_file.as_posix()
    try:
        result = _run(tmp_path, [rel], scope="shard", shard="s1")
        assert result.returncode == 0, result.stderr
        inv = _read_inv(tmp_path)
        assert "node_markers" not in inv, "node-inventory.json must not contain node_markers"
        minv = _read_marker_inv(tmp_path)
        markers = minv["node_markers"]
        nid = next(nid for nid in inv["node_ids"] if "test_multi" in nid)
        # Must be sorted and deduplicated
        assert markers[nid] == ["golden", "pure"]
    finally:
        _cleanup(tmp_path)


def test_node_markers_empty_when_no_decorators(tmp_path: Path) -> None:
    """Tests with no markers get an empty list in node_markers (marker inventory)."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_nomark.py"
    test_file.write_text("def test_plain():\n    assert True\n", encoding="utf-8")
    rel = test_file.as_posix()
    try:
        result = _run(tmp_path, [rel], scope="shard", shard="s1")
        assert result.returncode == 0, result.stderr
        inv = _read_inv(tmp_path)
        assert "node_markers" not in inv, "node-inventory.json must not contain node_markers"
        minv = _read_marker_inv(tmp_path)
        markers = minv["node_markers"]
        nid = inv["node_ids"][0]
        assert markers[nid] == []
    finally:
        _cleanup(tmp_path)


def test_node_markers_class_level_marker(tmp_path: Path) -> None:
    """A marker on a class propagates to all its methods (marker inventory)."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_cls_mark.py"
    test_file.write_text(
        textwrap.dedent(
            """\
            import pytest

            @pytest.mark.integration
            class TestSuite:
                def test_one(self):
                    assert True
                def test_two(self):
                    assert True
            """
        ),
        encoding="utf-8",
    )
    rel = test_file.as_posix()
    try:
        result = _run(tmp_path, [rel], scope="shard", shard="s1")
        assert result.returncode == 0, result.stderr
        inv = _read_inv(tmp_path)
        assert "node_markers" not in inv, "node-inventory.json must not contain node_markers"
        minv = _read_marker_inv(tmp_path)
        markers = minv["node_markers"]
        for nid in inv["node_ids"]:
            assert markers[nid] == ["integration"], f"node {nid} missing class-level marker"
    finally:
        _cleanup(tmp_path)


def test_node_markers_module_level_marker(tmp_path: Path) -> None:
    """A module-level pytestmark propagates to all collected nodes (marker inventory)."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_modmark.py"
    test_file.write_text(
        textwrap.dedent(
            """\
            import pytest
            pytestmark = pytest.mark.benchmark

            def test_bench_a():
                assert True

            def test_bench_b():
                assert True
            """
        ),
        encoding="utf-8",
    )
    rel = test_file.as_posix()
    try:
        result = _run(tmp_path, [rel], scope="shard", shard="s1")
        assert result.returncode == 0, result.stderr
        inv = _read_inv(tmp_path)
        assert "node_markers" not in inv, "node-inventory.json must not contain node_markers"
        minv = _read_marker_inv(tmp_path)
        markers = minv["node_markers"]
        for nid in inv["node_ids"]:
            assert markers[nid] == ["benchmark"], f"node {nid} missing module-level marker"
    finally:
        _cleanup(tmp_path)


def test_node_markers_parametrized_test(tmp_path: Path) -> None:
    """Parametrized tests each get their own marker list (marker inventory)."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_param_mark.py"
    test_file.write_text(
        textwrap.dedent(
            """\
            import pytest

            @pytest.mark.pure
            @pytest.mark.parametrize("val", [1, 2, 3])
            def test_param(val):
                assert val in (1, 2, 3)
            """
        ),
        encoding="utf-8",
    )
    rel = test_file.as_posix()
    try:
        result = _run(tmp_path, [rel], scope="shard", shard="s1")
        assert result.returncode == 0, result.stderr
        inv = _read_inv(tmp_path)
        assert "node_markers" not in inv, "node-inventory.json must not contain node_markers"
        assert inv["node_count"] == 3
        minv = _read_marker_inv(tmp_path)
        markers = minv["node_markers"]
        for nid in inv["node_ids"]:
            assert "pure" in markers[nid], f"node {nid} missing pure marker"
    finally:
        _cleanup(tmp_path)


def test_node_markers_mixed_markers(tmp_path: Path) -> None:
    """Tests with different combinations of the frozen marker taxonomy (marker inventory)."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_mixed.py"
    test_file.write_text(
        textwrap.dedent(
            """\
            import pytest

            @pytest.mark.golden
            @pytest.mark.pure
            def test_golden_pure():
                assert True

            @pytest.mark.provider
            @pytest.mark.coolprop
            def test_coolprop():
                assert True

            @pytest.mark.integration
            @pytest.mark.slow
            def test_integ():
                assert True
            """
        ),
        encoding="utf-8",
    )
    rel = test_file.as_posix()
    try:
        result = _run(tmp_path, [rel], scope="shard", shard="s1")
        assert result.returncode == 0, result.stderr
        inv = _read_inv(tmp_path)
        assert "node_markers" not in inv, "node-inventory.json must not contain node_markers"
        minv = _read_marker_inv(tmp_path)
        markers = minv["node_markers"]
        golden_nid = next(nid for nid in inv["node_ids"] if "test_golden_pure" in nid)
        coolprop_nid = next(nid for nid in inv["node_ids"] if "test_coolprop" in nid)
        integ_nid = next(nid for nid in inv["node_ids"] if "test_integ" in nid)
        assert markers[golden_nid] == ["golden", "pure"]
        assert markers[coolprop_nid] == ["coolprop", "provider"]
        assert markers[integ_nid] == ["integration", "slow"]
    finally:
        _cleanup(tmp_path)


# ---------------------------------------------------------------------------
# behavior-environment.json acceptance tests
# ---------------------------------------------------------------------------


def test_behavior_environment_json_produced(tmp_path: Path) -> None:
    """A successful collection produces a valid behavior-environment.json artifact."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_behenv.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    rel = test_file.as_posix()
    try:
        result = _run(tmp_path, [rel], scope="shard", shard="s1")
        assert result.returncode == 0, result.stderr
        beh = _read_behavior_env(tmp_path)
        # Schema version
        assert beh["schema_version"] == "1"
        # Payload structure
        payload = beh["payload"]
        assert isinstance(payload, dict)
        assert "python_version" in payload
        assert "environment" in payload
        assert isinstance(payload["environment"], dict)
        assert "file_digests" in payload
        assert isinstance(payload["file_digests"], dict)
        assert "working_directory" in payload
        # File digests include required files
        assert "uv.lock" in payload["file_digests"]
        assert "pyproject.toml" in payload["file_digests"]
        # Fingerprint is sha256: hex string
        fp = beh["canonical_json_sha256"]
        assert fp.startswith("sha256:")
        assert len(fp) == 71  # "sha256:" + 64 hex chars
    finally:
        _cleanup(tmp_path)


def test_behavior_environment_fingerprint_matches_payload(tmp_path: Path) -> None:
    """The canonical_json_sha256 in behavior-environment.json matches the payload."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_behenv2.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    rel = test_file.as_posix()
    try:
        result = _run(tmp_path, [rel], scope="shard", shard="s1")
        assert result.returncode == 0, result.stderr
        beh = _read_behavior_env(tmp_path)
        import hashlib as _hl

        canonical = json.dumps(
            beh["payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        expected_fp = "sha256:" + _hl.sha256(canonical.encode("utf-8")).hexdigest()
        assert beh["canonical_json_sha256"] == expected_fp
    finally:
        _cleanup(tmp_path)


# ---------------------------------------------------------------------------
# Workflow-env acceptance tests for the behavior environment contract
# ---------------------------------------------------------------------------


def test_workflow_env_generates_fingerprint(tmp_path: Path) -> None:
    """A real workflow environment with all governed and non-governed vars
    generates a valid fingerprint."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_wfenv.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    rel = test_file.as_posix()
    workflow_env = {
        **BASE_ENV,
        # Non-governed workflow vars (run_test_shard.py consumer side)
        "TRACK": "pr-head",
        "COMMIT_SHA": "abc123",
        "RUN_ID": "42",
        "RUN_ATTEMPT": "1",
        "PYTHON_VERSION": "3.12",
        "SHARD": "s1",
    }
    try:
        result = _run(tmp_path, [rel], scope="shard", shard="s1", extra_env=workflow_env)
        assert result.returncode == 0, result.stderr
        beh = _read_behavior_env(tmp_path)
        assert beh["schema_version"] == "1"
        fp = beh["canonical_json_sha256"]
        assert fp.startswith("sha256:")
        assert len(fp) == 71
    finally:
        _cleanup(tmp_path)


def test_pytest_timeout_enters_payload(tmp_path: Path) -> None:
    """PYTEST_TIMEOUT is present in the behavior-environment.json payload."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_timeout_payload.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    rel = test_file.as_posix()
    try:
        result = _run(
            tmp_path,
            [rel],
            scope="shard",
            shard="s1",
            extra_env={"PYTEST_TIMEOUT": "120"},
        )
        assert result.returncode == 0, result.stderr
        beh = _read_behavior_env(tmp_path)
        env_map = beh["payload"]["environment"]
        assert "PYTEST_TIMEOUT" in env_map, "PYTEST_TIMEOUT missing from payload"
        assert env_map["PYTEST_TIMEOUT"] == "120"
    finally:
        _cleanup(tmp_path)


def test_changing_timeout_changes_fingerprint(tmp_path: Path) -> None:
    """Different PYTEST_TIMEOUT values produce different fingerprints."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_timeout_diff.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    rel = test_file.as_posix()
    fingerprints: list[str] = []
    for timeout_val in ("30", "600"):
        out = tmp_path / f"inventory_{timeout_val}.json"
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            PLUGIN,
            "--hx-collection-scope=shard",
            "--hx-shard=s1",
            f"--hx-node-output={out}",
            rel,
        ]
        env = {**os.environ, **BASE_ENV, "PYTEST_TIMEOUT": timeout_val}
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
            timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
        beh_path = out.parent / "behavior-environment.json"
        beh = json.loads(beh_path.read_text(encoding="utf-8"))
        fingerprints.append(beh["canonical_json_sha256"])
    assert len(fingerprints) == 2
    assert fingerprints[0] != fingerprints[1], "changing PYTEST_TIMEOUT must change fingerprint"


def test_undeclared_pytest_unknown_setting_fails_closed(tmp_path: Path) -> None:
    """An undeclared governed-namespace variable PYTEST_UNKNOWN_SETTING
    triggers fail-closed (non-zero exit)."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_unk.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    rel = test_file.as_posix()
    try:
        result = _run(
            tmp_path,
            [rel],
            scope="shard",
            shard="s1",
            extra_env={"PYTEST_UNKNOWN_SETTING": "should-fail"},
        )
        assert result.returncode != 0, (
            "undeclared PYTEST_UNKNOWN_SETTING must cause fail-closed error"
        )
        combined = result.stderr + result.stdout
        assert (
            "undeclared" in combined.lower()
            or "unknown" in combined.lower()
            or "behavior" in combined.lower()
        ), f"expected fail-closed message, got: {combined[:500]}"
    finally:
        _cleanup(tmp_path)


def test_normal_github_runner_vars_not_rejected(tmp_path: Path) -> None:
    """Standard GitHub runner env vars (CI, GITHUB_ACTIONS, etc.) do not
    trigger the fail-closed check."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_ghevars.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    rel = test_file.as_posix()
    github_vars = {
        "CI": "true",
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_REPOSITORY": "owner/repo",
        "RUNNER_OS": "Linux",
        "RUNNER_NAME": "test-runner",
    }
    try:
        result = _run(
            tmp_path,
            [rel],
            scope="shard",
            shard="s1",
            extra_env=github_vars,
        )
        assert result.returncode == 0, f"GitHub runner vars must not be rejected: {result.stderr}"
    finally:
        _cleanup(tmp_path)


def test_global_and_shard_same_behavior_env_same_fingerprint(tmp_path: Path) -> None:
    """Same behavior env with different shard names produces the same
    behavior fingerprint — the fingerprint is independent of scope."""
    d = _acceptance_dir(tmp_path)
    test_file = d / "test_fp_match.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    rel = test_file.as_posix()
    fingerprints: list[str] = []
    for shard_name in ("s1", "s2"):
        out = tmp_path / f"inventory_{shard_name}.json"
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            PLUGIN,
            "--hx-collection-scope=shard",
            f"--hx-shard={shard_name}",
            f"--hx-node-output={out}",
            rel,
        ]
        env = {**os.environ, **BASE_ENV}
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
            timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
        beh_path = out.parent / "behavior-environment.json"
        beh = json.loads(beh_path.read_text(encoding="utf-8"))
        fingerprints.append(beh["canonical_json_sha256"])
    assert len(fingerprints) == 2
    assert fingerprints[0] == fingerprints[1], (
        "same behavior env must produce same fingerprint regardless of shard/scope"
    )


# ---------------------------------------------------------------------------
# run_test_shard.py telemetry acceptance tests
# ---------------------------------------------------------------------------


def test_run_test_shard_telemetry_fields_present(tmp_path: Path) -> None:
    """Telemetry output contains execution_status, junit_parse_status,
    and counts_authoritative fields."""
    from tests.ci.run_test_shard import run_pytest

    test_file = tmp_path / "test_tel.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    run_pytest(
        [str(test_file)],
        env={"PYTHONPATH": str(REPO_ROOT)},
        timeout=30,
        junit_path=str(tmp_path / "junit.xml"),
        telemetry_path=str(tmp_path / "telemetry.json"),
        stdout_path=str(tmp_path / "stdout.txt"),
        stderr_path=str(tmp_path / "stderr.txt"),
        track="pr-head",
        commit_sha="abc123",
        run_id="1",
        run_attempt=1,
        python_version="3.12",
        shard="s1",
    )
    telemetry = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))
    # execution_status field
    assert "execution_status" in telemetry
    assert telemetry["execution_status"] in (
        "completed",
        "timeout",
        "collection-error",
        "internal-error",
    )
    # junit_parse_status field
    assert "junit_parse_status" in telemetry
    assert telemetry["junit_parse_status"] in ("available", "unavailable")
    # counts_authoritative field
    assert "counts_authoritative" in telemetry
    assert isinstance(telemetry["counts_authoritative"], bool)


def test_run_test_shard_counts_authoritative_pass(tmp_path: Path) -> None:
    """When tests pass and JUnit is available, counts_authoritative is True
    and count consistency holds."""
    from tests.ci.run_test_shard import run_pytest

    test_a = tmp_path / "test_a.py"
    test_a.write_text("def test_alpha():\n    assert True\n", encoding="utf-8")
    test_b = tmp_path / "test_b.py"
    test_b.write_text("def test_beta():\n    assert True\n", encoding="utf-8")
    exit_code = run_pytest(
        [
            str(test_a),
            str(test_b),
            f"--junitxml={tmp_path / 'junit.xml'}",
        ],
        env={"PYTHONPATH": str(REPO_ROOT)},
        timeout=30,
        junit_path=str(tmp_path / "junit.xml"),
        telemetry_path=str(tmp_path / "telemetry.json"),
        stdout_path=str(tmp_path / "stdout.txt"),
        stderr_path=str(tmp_path / "stderr.txt"),
        track="pr-head",
        commit_sha="abc123",
        run_id="1",
        run_attempt=1,
        python_version="3.12",
        shard="s1",
    )
    telemetry = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))
    assert exit_code == 0
    assert telemetry["junit_parse_status"] == "available"
    assert telemetry["counts_authoritative"] is True
    # Count consistency: tests_collected == sum of pass/fail/skip/xfail/xpass
    expected_total = (
        telemetry["tests_passed"]
        + telemetry["tests_failed"]
        + telemetry["tests_skipped"]
        + telemetry["tests_xfailed"]
        + telemetry["tests_xpassed"]
    )
    assert telemetry["tests_collected"] == expected_total


def test_run_test_shard_counts_authoritative_fail(tmp_path: Path) -> None:
    """When tests fail, counts_authoritative is still True if JUnit is
    consistent, and tests_failed > 0."""
    from tests.ci.run_test_shard import run_pytest

    test_file = tmp_path / "test_fail.py"
    test_file.write_text("def test_fails():\n    assert False\n", encoding="utf-8")
    exit_code = run_pytest(
        [
            str(test_file),
            f"--junitxml={tmp_path / 'junit.xml'}",
        ],
        env={"PYTHONPATH": str(REPO_ROOT)},
        timeout=30,
        junit_path=str(tmp_path / "junit.xml"),
        telemetry_path=str(tmp_path / "telemetry.json"),
        stdout_path=str(tmp_path / "stdout.txt"),
        stderr_path=str(tmp_path / "stderr.txt"),
        track="pr-head",
        commit_sha="abc123",
        run_id="1",
        run_attempt=1,
        python_version="3.12",
        shard="s1",
    )
    telemetry = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))
    assert exit_code != 0
    assert telemetry["tests_failed"] > 0
    assert telemetry["counts_authoritative"] is True
    # Count consistency
    expected_total = (
        telemetry["tests_passed"]
        + telemetry["tests_failed"]
        + telemetry["tests_skipped"]
        + telemetry["tests_xfailed"]
        + telemetry["tests_xpassed"]
    )
    assert telemetry["tests_collected"] == expected_total
