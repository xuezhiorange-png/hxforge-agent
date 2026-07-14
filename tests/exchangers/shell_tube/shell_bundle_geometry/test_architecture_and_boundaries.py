from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_IMPORT_TOKENS = {
    "os",
    "pathlib",
    "socket",
    "subprocess",
    "requests",
    "httpx",
    "random",
    "time",
}


def test_core_has_exact_module_boundary_and_no_forbidden_io_imports() -> None:
    root = Path("src/hexagent/exchangers/shell_tube/shell_bundle_geometry")
    expected = {
        "__init__.py",
        "models.py",
        "canonical.py",
        "schema.py",
        "authority.py",
        "geometry.py",
        "validation.py",
        "adapter_blockers.py",
        "rule_pack_adapter.py",
    }
    actual = {path.name for path in root.glob("*.py")}
    assert actual == expected
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
                assert names.isdisjoint(FORBIDDEN_IMPORT_TOKENS), (path, names)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in FORBIDDEN_IMPORT_TOKENS, path


def test_parent_and_upstream_packages_are_read_only_dependencies() -> None:
    assert Path("src/hexagent/exchangers/shell_tube/__init__.py").exists()
    assert Path("src/hexagent/exchangers/shell_tube/tube_layout/__init__.py").exists()
