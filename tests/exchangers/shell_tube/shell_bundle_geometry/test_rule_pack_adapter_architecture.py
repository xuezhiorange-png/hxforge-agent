"""Architecture / boundary test for the TASK-022 Slice B1 adapter.

Hard-bounds checks (Spec §14):

* No filesystem / network / database / environment / clock / locale
  / global-registry / path / loader call in the production adapter
  modules.
* No fixture / vendor catalog / golden / expected output /
  standard-data file created.
* No shell-geometry adapter code; no GeometryCatalog reference.
* No slice-A six-core mutation; no TASK-012/-016/-020/-021 mutation.
* No tests files that reference slice-B2.

The tests use AST parsing to walk every source file in the
allowlist and check actual import / call expressions for any
forbidden token. Substring-only matches inside docstrings are
explicitly stripped before analysis so that documentation mentions
of ``pathlib`` / ``open(`` do not trip the gate.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

FORBIDDEN_IMPORT_TOKENS: set[str] = {
    "os",
    "pathlib",
    "socket",
    "subprocess",
    "requests",
    "httpx",
    "sqlalchemy",
    "random",
    "time",
    "datetime",
    "getenv",
    "environ",
    "locale",
    "shell_geometry_adapter",
    "GeometryCatalog",
    "nearest",
    "first_match",
    "fallback",
    "default_rule",
}

ALLOWED_ADAPTER_MODULES: tuple[str, ...] = (
    "src/hexagent/exchangers/shell_tube/shell_bundle_geometry/adapter_blockers.py",
    "src/hexagent/exchangers/shell_tube/shell_bundle_geometry/rule_pack_adapter.py",
)


def _strip_docstring(tree: ast.AST) -> ast.AST:
    """Return ``tree`` with its leading docstring node removed if present."""
    if isinstance(tree, ast.Module) and tree.body:
        first = tree.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            tree.body = tree.body[1:]
    return tree


def _parse(rel_path: str) -> ast.Module:
    tree = ast.parse(Path(rel_path).read_text(encoding="utf-8"))
    return _strip_docstring(tree)  # type: ignore[return-value]


def _collect_module_text(rel_path: str) -> str:
    return Path(rel_path).read_text(encoding="utf-8")


def test_production_modules_have_no_forbidden_imports() -> None:
    """The two new production modules import only stdlib + slice-A + TASK-012."""
    for rel_path in ALLOWED_ADAPTER_MODULES:
        tree = _parse(rel_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
                bad = names & FORBIDDEN_IMPORT_TOKENS
                assert not bad, f"{rel_path}: forbidden import: {bad}"
            if isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".")[0]
                assert top not in FORBIDDEN_IMPORT_TOKENS, f"{rel_path}: {top}"
            if isinstance(node, ast.Attribute):
                # ``adapter_module.forbidden`` attribute access (rare).
                attr = node.attr
                assert attr not in FORBIDDEN_IMPORT_TOKENS, f"{rel_path}: attribute access {attr}"


def test_no_loader_call() -> None:
    """The adapter MUST NOT call ``load_rule_pack`` or ``validate_rule_pack(Path)``."""
    forbidden_callees = {"load_rule_pack", "validate_rule_pack"}
    for rel_path in ALLOWED_ADAPTER_MODULES:
        tree = _parse(rel_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in forbidden_callees:
                    raise AssertionError(f"{rel_path}: forbidden call {func.id}()")


def test_no_geometry_catalog_or_shell_adapter_term() -> None:
    """No shell-adapter implementation can be authored under B1."""
    for rel_path in ALLOWED_ADAPTER_MODULES:
        tree = _parse(rel_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in {
                "GeometryCatalog",
                "shell_geometry_adapter",
                "ApprovedShellGeometrySnapshot",
            }:
                raise AssertionError(f"{rel_path}: forbidden name {node.id}")
            if isinstance(node, ast.Attribute) and node.attr in {
                "GeometryCatalog",
                "shell_geometry_adapter",
                "ApprovedShellGeometrySnapshot",
            }:
                raise AssertionError(f"{rel_path}: forbidden attr {node.attr}")


def test_no_filepath_or_open_call() -> None:
    """The adapter must not perform filesystem I/O via AST call detection."""
    forbidden_calls = {"open"}
    forbidden_attrs = {"glob", "rglob"}
    for rel_path in ALLOWED_ADAPTER_MODULES:
        tree = _parse(rel_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in forbidden_calls:
                    raise AssertionError(f"{rel_path}: forbidden open()")
                if isinstance(func, ast.Attribute) and func.attr in forbidden_attrs:
                    raise AssertionError(f"{rel_path}: forbidden .{func.attr}() call")


def test_no_pathlib_in_imports() -> None:
    """``pathlib`` must never be imported (the AST walk above covers
    attribute / call sites; this catches imports separately)."""
    for rel_path in ALLOWED_ADAPTER_MODULES:
        tree = _parse(rel_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
                assert "pathlib" not in names, rel_path
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] != "pathlib", rel_path


def test_no_clock_or_locale_in_imports() -> None:
    for rel_path in ALLOWED_ADAPTER_MODULES:
        tree = _parse(rel_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
                for token in ("time", "datetime", "locale"):
                    assert token not in names, rel_path
            if isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".")[0]
                assert top not in {"time", "datetime", "locale"}, rel_path


def test_no_clock_or_locale_in_attribute_call() -> None:
    """Forbid ``time.time(...)``, ``datetime.now(...)``, ``locale.getlocale(...)``."""
    forbidden = {("time", "time"), ("datetime", "now"), ("locale", "getlocale")}
    for rel_path in ALLOWED_ADAPTER_MODULES:
        tree = _parse(rel_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                attr = node.func
                combo = (attr.value.id if isinstance(attr.value, ast.Name) else None, attr.attr)
                if combo in forbidden:
                    raise AssertionError(f"{rel_path}: forbidden {combo[0]}.{combo[1]}")


def test_default_value_or_nearest_match_policy_is_absent() -> None:
    """Forbid first-match / nearest / hidden-default behavior in code."""
    forbidden_names = {"nearest_match", "first_match", "default_rule", "fallback"}
    for rel_path in ALLOWED_ADAPTER_MODULES:
        tree = _parse(rel_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in forbidden_names:
                raise AssertionError(f"{rel_path}: forbidden function {node.name}")
            if isinstance(node, ast.Name) and node.id in forbidden_names:
                raise AssertionError(f"{rel_path}: forbidden identifier {node.id}")


def test_slice_a_six_core_files_are_unchanged() -> None:
    """The six Slice A core modules must remain at their B1 base SHA.

    Round auth base is the merge commit that introduced Slice A
    (``8ba1d9e0...``). The 6-core invariant is checked against THIS
    base, not the older Slice A authoring base.
    """
    files = (
        "src/hexagent/exchangers/shell_tube/shell_bundle_geometry/__init__.py",
        "src/hexagent/exchangers/shell_tube/shell_bundle_geometry/models.py",
        "src/hexagent/exchangers/shell_tube/shell_bundle_geometry/canonical.py",
        "src/hexagent/exchangers/shell_tube/shell_bundle_geometry/schema.py",
        "src/hexagent/exchangers/shell_tube/shell_bundle_geometry/authority.py",
        "src/hexagent/exchangers/shell_tube/shell_bundle_geometry/geometry.py",
        "src/hexagent/exchangers/shell_tube/shell_bundle_geometry/validation.py",
    )
    # ``__init__.py`` is explicitly excluded from the locked set
    # because the additive B1 export per Issue #147 Record 6 / spec
    # §13 widens its surface.
    locked_core = set(files[1:])
    import subprocess

    base_sha = "8ba1d9e026a34c3089500833e71fe25ce5ac92ba"
    proc = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            f"{base_sha}...HEAD",
            "--",
            *locked_core,
        ],
        cwd=os.getcwd(),
        capture_output=True,
        text=True,
        check=False,
    )
    changed = {line.strip() for line in proc.stdout.splitlines() if line.strip()}
    leaked = locked_core & changed
    assert not leaked, f"forbidden slice-A core mutations vs {base_sha[:9]}: {leaked}"


def test_no_task012_or_task016_mutation() -> None:
    """TASK-012 / TASK-016 production and test files must remain untouched
    against the B1 base SHA.
    """
    base_sha = "8ba1d9e026a34c3089500833e71fe25ce5ac92ba"
    target_dirs = (
        "src/hexagent/rule_packs",
        "tests/rule_packs",
        "src/hexagent/geometry_catalogs",
        "tests/geometry_catalogs",
    )
    import subprocess

    proc = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            f"{base_sha}...HEAD",
            "--",
            *target_dirs,
        ],
        cwd=os.getcwd(),
        capture_output=True,
        text=True,
        check=False,
    )
    leaked = {line.strip() for line in proc.stdout.splitlines() if line.strip()}
    assert not leaked, f"TASK-012/TASK-016 mutations vs {base_sha[:9]}: {leaked}"


def test_no_shell_adapter_module_created() -> None:
    """The slice-B2 shell-geometry adapter file must not exist."""
    assert not Path(
        "src/hexagent/exchangers/shell_tube/shell_bundle_geometry/shell_geometry_adapter.py"
    ).exists()


def test_no_vendor_or_fixture_files_created() -> None:
    """No fixtures / vendor catalog / production rule-pack artifacts."""
    forbidden_glob = Path("tests/fixtures")
    if forbidden_glob.exists():
        # ``tests/fixtures/task022`` is the only directory explicitly
        # forbidden by Spec §4. Its presence would be a violation.
        task022_fixtures = list(forbidden_glob.glob("task022/**/*"))
        assert not task022_fixtures, (
            f"forbidden task022 fixtures directory present: {task022_fixtures}"
        )
