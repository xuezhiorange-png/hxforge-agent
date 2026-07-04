"""In-memory catalog loader for TASK-013 material / cost records.

Implements the TASK-013 frozen design contract Section 19 (Future
implementation file boundary) loader half. The loader reads a
catalog directory containing JSON record files and groups them into
in-memory lists that are passed to the deterministic selectors
(Section 14). No persistence layer / database / migration is
implemented (Section 21 explicit non-goal).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hexagent.material_costs.errors import MaterialCostValidationError


def load_material_records(
    path: str | Path,
    *,
    record_filename: str = "material_records.json",
) -> list[dict[str, Any]]:
    """Load material records from a JSON file.

    The JSON file MUST be a top-level array of record dicts.
    """
    catalog_path = Path(path)
    target = catalog_path if catalog_path.is_file() else catalog_path / record_filename
    if not target.is_file():
        return []
    with target.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, list):
        raise MaterialCostValidationError(
            f"material catalog {target} must be a JSON array; got {type(data).__name__}",
            path=str(target),
        )
    return [rec for rec in data if isinstance(rec, dict)]


def load_cost_records(
    path: str | Path,
    *,
    record_filename: str = "cost_records.json",
) -> list[dict[str, Any]]:
    """Load cost records from a JSON file.

    The JSON file MUST be a top-level array of record dicts.
    """
    catalog_path = Path(path)
    target = catalog_path if catalog_path.is_file() else catalog_path / record_filename
    if not target.is_file():
        return []
    with target.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, list):
        raise MaterialCostValidationError(
            f"cost catalog {target} must be a JSON array; got {type(data).__name__}",
            path=str(target),
        )
    return [rec for rec in data if isinstance(rec, dict)]


__all__ = [
    "load_cost_records",
    "load_material_records",
]
