"""Approved TASK-011 benchmark case loader.

The TASK-011 frozen design contract mandates that every benchmark case be
an independently reviewable JSON artifact under ``benchmarks/cases/`` (per
contract §19.1.1 / §19.1.7 and the implementation file boundary §20).

This module is the read-only loader. It MUST NOT synthesize, mutate, or
recompute case payloads — every case payload is the on-disk JSON file. The
canonical hash is recomputed by the validator via the canonicalization
helper; this module only reads raw JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

# File-name prefix per the implementation boundary in contract §20.
CASE_FILE_PREFIX = "task011_case_"
CASE_FILE_SUFFIX = ".json"

# Expected case count per the implementation authorization.
APPROVED_CASES_COUNT = 20


def case_file_path(root: Path, case_id: str) -> Path:
    """Return the canonical on-disk path for a given ``case_id``.

    ``case_id`` MUST match ``task011_case_NN`` where ``NN`` is the zero-padded
    decimal index in [01, 20].
    """
    if not case_id.startswith(CASE_FILE_PREFIX):
        raise ValueError(f"case_id {case_id!r} does not match {CASE_FILE_PREFIX}NN")
    return root / "benchmarks" / "cases" / f"{case_id}{CASE_FILE_SUFFIX}"


def load_case(root: Path, case_id: str) -> dict[str, Any]:
    """Read and JSON-parse the case file for ``case_id``.

    Raises ``FileNotFoundError`` if the artifact does not exist; raises
    ``ValueError`` on malformed JSON.
    """
    path = case_file_path(root, case_id)
    with path.open("r", encoding="utf-8") as handle:
        value: Any = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(dict[str, Any], value)


def approved_cases(root: Path | str = Path(".")) -> list[dict[str, Any]]:
    """Return all 20 approved benchmark cases, sorted by ``case_id``.

    Reads from ``<root>/benchmarks/cases/task011_case_*.json`` only. The
    loader does NOT mutate, regenerate, or fall back to Python-side
    synthesis — every payload is the on-disk artifact.
    """
    root = Path(root)
    case_dir = root / "benchmarks" / "cases"
    case_files = sorted(case_dir.glob(f"{CASE_FILE_PREFIX}*{CASE_FILE_SUFFIX}"))
    if len(case_files) != APPROVED_CASES_COUNT:
        raise FileNotFoundError(
            f"expected {APPROVED_CASES_COUNT} case files under {case_dir}, found {len(case_files)}"
        )
    cases = [load_case(root, path.stem) for path in case_files]
    cases.sort(key=lambda case: cast(str, case["case_id"]))
    return cases


__all__ = ["APPROVED_CASES_COUNT", "approved_cases", "case_file_path", "load_case"]
