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


def test_core_has_no_forbidden_io_imports() -> None:
    root = Path("src/hexagent/exchangers/shell_tube/tube_layout")
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
                assert names.isdisjoint(FORBIDDEN_IMPORT_TOKENS), (path, names)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in FORBIDDEN_IMPORT_TOKENS, path


def test_parent_package_file_is_not_changed_by_slice_a() -> None:
    path = Path("src/hexagent/exchangers/shell_tube/__init__.py")
    assert path.exists()
