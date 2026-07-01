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
