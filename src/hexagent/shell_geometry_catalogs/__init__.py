"""TASK-023 — Approved Shell Geometry Catalog framework.

This package owns the pure in-memory TASK-023 shell-geometry-catalog
authority framework. It exposes exactly seven public symbols:

- :class:`ShellGeometryCatalog`
- :class:`ShellGeometryRecord`
- :class:`ShellGeometryCatalogFailure`
- :class:`ShellGeometryCatalogBlockerCode`
- :data:`SHELL_GEOMETRY_CATALOG_BLOCKER_CODES`
- :func:`parse_shell_geometry_catalog`
- :func:`select_approved_shell_geometry`

No loader, file-path API, registry, adapter, persistence service,
CLI, report API, automatic sizing API, hash helper, internal model
or TASK-022 projection API is exposed.
"""

from __future__ import annotations

from .blockers import (
    SHELL_GEOMETRY_CATALOG_BLOCKER_CODES,
    ShellGeometryCatalogBlockerCode,
)
from .catalog import (
    ShellGeometryCatalogFailure,
    parse_shell_geometry_catalog,
    select_approved_shell_geometry,
)
from .models import ShellGeometryCatalog, ShellGeometryRecord

__all__ = [
    "SHELL_GEOMETRY_CATALOG_BLOCKER_CODES",
    "ShellGeometryCatalog",
    "ShellGeometryCatalogBlockerCode",
    "ShellGeometryCatalogFailure",
    "ShellGeometryRecord",
    "parse_shell_geometry_catalog",
    "select_approved_shell_geometry",
]
