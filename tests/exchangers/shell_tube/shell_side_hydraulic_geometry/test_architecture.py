# ruff: noqa: E501
from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

import hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry as package
import hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.validation as validation_module

PACKAGE_DIR = Path(validation_module.__file__).resolve().parent

ALLOWED_PRODUCTION_FILES = {
    "__init__.py",
    "authority.py",
    "canonical.py",
    "engineering_authority_snapshot.py",
    "formulas.py",
    "models.py",
    "schema.py",
    "validation.py",
}


def test_production_path_allowlist() -> None:
    actual = {
        path.name for path in PACKAGE_DIR.iterdir() if path.is_file() and path.suffix == ".py"
    }
    assert actual == ALLOWED_PRODUCTION_FILES


def test_public_surface_exports_only_validate_request() -> None:
    assert package.__all__ == ["validate_request"]
    assert hasattr(package, "validate_request")


def test_validation_module_no_binary_float_geometry() -> None:
    tree = ast.parse(Path(validation_module.__file__).read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "float"
        ):
            offenders.append(f"line {node.lineno}: float() call")
    assert offenders == []


def test_validation_module_no_forbidden_io_tokens() -> None:
    source = inspect.getsource(validation_module)
    forbidden = ("open(", "urllib", "socket", "subprocess", "datetime.now", "os.environ")
    for token in forbidden:
        assert token not in source


def test_formulas_module_uses_frozen_decimal_constants() -> None:
    formulas = importlib.import_module(
        "hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.formulas"
    )
    source = Path(formulas.__file__ or "").read_text(encoding="utf-8")
    assert "math.pi" not in source
    assert "math.sqrt" not in source
    assert "from math import" not in source
