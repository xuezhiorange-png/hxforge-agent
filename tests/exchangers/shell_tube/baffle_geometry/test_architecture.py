"""TASK-024 Round 6 architecture guards for the public validation producer."""

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

import hexagent.exchangers.shell_tube.baffle_geometry as package
import hexagent.exchangers.shell_tube.baffle_geometry.validation as validation_module

VALIDATION_SRC = Path(validation_module.__file__).resolve()
PACKAGE_DIR = VALIDATION_SRC.parent

ALLOWED_PRODUCTION_FILES = {
    "authority.py",
    "canonical.py",
    "geometry.py",
    "models.py",
    "schema.py",
    "validation.py",
    "__init__.py",
}


def test_production_path_allowlist() -> None:
    actual = {
        path.name for path in PACKAGE_DIR.iterdir() if path.is_file() and path.suffix == ".py"
    }
    assert actual == ALLOWED_PRODUCTION_FILES


def test_public_surface_exports_only_validate_request() -> None:
    assert package.__all__ == ["validate_request"]
    assert set(dir(package)) >= {"validate_request"}


def test_private_helpers_not_public() -> None:
    forbidden_public = (
        "parse_request",
        "validate_typed_request",
        "compute_geometry_foundation",
        "validate_authority_foundation",
    )
    for name in forbidden_public:
        assert not hasattr(package, name)


def test_validation_module_does_not_import_forbidden_io_modules() -> None:
    source = inspect.getsource(validation_module)
    source_no_docstring = source.split('"""', 2)[-1] if '"""' in source else source
    forbidden_tokens = [
        "open(",
        "Path(",
        "subprocess",
        "urllib",
        "socket",
        "datetime.now",
        "date.today",
        "locale",
        "random.",
        "eval(",
        "exec(",
        "pickle",
        "getenv",
        "os.environ",
        "import os",
        "from os",
    ]
    for token in forbidden_tokens:
        assert token not in source_no_docstring, f"validation module uses {token!r}"


def test_validation_module_no_dataclasses_asdict() -> None:
    source = inspect.getsource(validation_module)
    no_docs = source.split('"""', 2)[-1] if '"""' in source else source
    assert "dataclasses.asdict" not in no_docs


def test_validation_module_no_second_canonical_serializer() -> None:
    text = VALIDATION_SRC.read_text()
    forbidden = (
        "json" + "." + "dumps",
        "hashlib" + "." + "sha256",
    )
    for needle in forbidden:
        assert needle not in text, f"forbidden: {needle}"


def test_validation_module_no_mypy_suppression() -> None:
    text = VALIDATION_SRC.read_text()
    pound = chr(35)
    at = chr(64)
    type_ignore = pound + " type" + ": ignore"
    mypy_directive = pound + " mypy" + ":"
    no_type_check = at + "no_type_check"
    for needle in (type_ignore, mypy_directive, no_type_check):
        assert needle not in text, f"forbidden suppression: {needle}"


def test_validation_module_follows_geometry_architecture_patterns() -> None:
    tree = ast.parse(VALIDATION_SRC.read_text())
    offenders: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            continue
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "float":
                offenders.append(f"line {node.lineno}: float() call")
    assert offenders == []


def test_schema_and_geometry_modules_remain_private() -> None:
    schema = importlib.import_module("hexagent.exchangers.shell_tube.baffle_geometry.schema")
    assert "parse_request" not in package.__all__
    assert "validate_typed_request" not in package.__all__
    assert "compute_geometry_foundation" not in package.__all__
    assert "validate_authority_foundation" not in package.__all__
    assert "parse_request" in schema.__all__
    assert package.validate_request is validation_module.validate_request
