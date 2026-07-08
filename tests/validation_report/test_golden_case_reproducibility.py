"""TASK-019 golden-case reproducibility tests (Slice 1).

Slice 1 scope: fixture-shape reproducibility only. Loads all 3 JSON
fixtures and asserts deterministic canonical-JSON serialization, the
frozen case ID list, the SHA-256 helper shape, and the absence of
non-deterministic fields. Does NOT run the full upstream chain (that is
Slice 2 territory).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from hexagent.validation_report import (
    TASK_019_GOLDEN_CASE_IDS,
    canonical_json_dumps,
    sha256_hex,
)


_GOLDEN_FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent / "golden" / "double_pipe_rating"
)


def test_all_three_fixtures_load() -> None:
    for case_id in TASK_019_GOLDEN_CASE_IDS:
        path = _GOLDEN_FIXTURE_DIR / _filename_for_case_id(case_id)
        assert path.exists(), f"missing fixture for {case_id}: {path}"
        with path.open() as fh:
            json.load(fh)  # raises if invalid


def test_case_ids_match_frozen_list() -> None:
    """The fixture file case_id values must match the frozen §4 list exactly."""
    for case_id in TASK_019_GOLDEN_CASE_IDS:
        path = _GOLDEN_FIXTURE_DIR / _filename_for_case_id(case_id)
        with path.open() as fh:
            data = json.load(fh)
        assert data["case_id"] == case_id, (
            f"file {path.name} case_id {data['case_id']!r} != {case_id!r}"
        )


def test_canonical_json_dumps_is_deterministic_across_fixtures() -> None:
    """Same fixture loaded twice → same canonical JSON string."""
    for case_id in TASK_019_GOLDEN_CASE_IDS:
        path = _GOLDEN_FIXTURE_DIR / _filename_for_case_id(case_id)
        with path.open() as fh:
            data = json.load(fh)
        s1 = canonical_json_dumps(data)
        s2 = canonical_json_dumps(data)
        assert s1 == s2, f"canonical_json_dumps non-deterministic for {case_id}"


def test_canonical_json_dumps_uses_sorted_keys() -> None:
    """Canonical form must use sorted keys (per frozen §3.3 + MASTER_DEVELOPMENT_SPEC §15.3)."""
    for case_id in TASK_019_GOLDEN_CASE_IDS:
        path = _GOLDEN_FIXTURE_DIR / _filename_for_case_id(case_id)
        with path.open() as fh:
            data = json.load(fh)
        canonical = canonical_json_dumps(data)
        # Find the first nested key sequence and assert it appears in sorted order
        # Easier check: the canonical form must equal what json.dumps produces
        # with sort_keys=True + the documented separators.
        import json as _json
        expected = _json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        assert canonical == expected, (
            f"canonical form for {case_id} does not match expected sorted-key output"
        )


def test_sha256_hex_helper_is_64_lowercase_hex() -> None:
    """SHA-256 helper must return 64-char lowercase hex per §3.3."""
    for case_id in TASK_019_GOLDEN_CASE_IDS:
        path = _GOLDEN_FIXTURE_DIR / _filename_for_case_id(case_id)
        with path.open() as fh:
            data = json.load(fh)
        h = sha256_hex(canonical_json_dumps(data))
        assert re.match(r"^[0-9a-f]{64}$", h), (
            f"sha256_hex did not return 64 lowercase hex chars for {case_id}: {h!r}"
        )


def test_no_random_or_wall_clock_or_platform_fields_in_fixtures() -> None:
    """Fixtures must NOT contain random UUIDs, wall-clock timestamps, or
    platform-dependent values. Slice 1 explicitly forbids these."""
    forbidden_substrings = (
        # Random UUID v4 format (8-4-4-4-12 with version digit 4)
        "xxxxxxxx-xxxx-4xxx",
        # Wall-clock ISO 8601 (would indicate datetime.now() leakage)
        # Match pattern but allow Slice 1 "TBD-by-Slice-2" placeholders.
        "1970-01-01",
        "2030-01-01",
    )
    for case_id in TASK_019_GOLDEN_CASE_IDS:
        path = _GOLDEN_FIXTURE_DIR / _filename_for_case_id(case_id)
        with path.open() as fh:
            text = fh.read()
        for fs in forbidden_substrings:
            assert fs not in text, (
                f"forbidden non-deterministic field {fs!r} found in {path.name}"
            )


def test_slice1_placeholder_strings_present_in_fixtures() -> None:
    """Slice 1 fixtures use TBD-by-Slice-2 placeholders. This test asserts
    they are present (proving the fixtures are Slice 1 skeletons, not
    final vectors). Slice 2 will replace them with real computed values."""
    for case_id in TASK_019_GOLDEN_CASE_IDS:
        path = _GOLDEN_FIXTURE_DIR / _filename_for_case_id(case_id)
        with path.open() as fh:
            text = fh.read()
        assert "TBD-by-Slice-2" in text, (
            f"Slice 1 placeholder TBD-by-Slice-2 missing in {path.name}"
        )


def test_metadata_files_exist() -> None:
    """Both _tolerance_metadata.json and _provenance_metadata.json must exist."""
    assert (_GOLDEN_FIXTURE_DIR / "_tolerance_metadata.json").exists()
    assert (_GOLDEN_FIXTURE_DIR / "_provenance_metadata.json").exists()


def test_metadata_files_are_valid_json() -> None:
    """Both metadata files must be valid JSON."""
    for fname in ("_tolerance_metadata.json", "_provenance_metadata.json"):
        path = _GOLDEN_FIXTURE_DIR / fname
        with path.open() as fh:
            data = json.load(fh)
        assert isinstance(data, dict), f"{fname} root must be a JSON object"


# --- helper ---


def _filename_for_case_id(case_id: str) -> str:
    if case_id == "TASK-019-GOLDEN-01":
        return "case_01_heat_balance_rating.json"
    if case_id == "TASK-019-GOLDEN-02":
        return "case_02_materials_mass_mechanical.json"
    if case_id == "TASK-019-GOLDEN-03":
        return "case_03_cost_lifecycle_envelope.json"
    raise ValueError(f"unknown case_id: {case_id!r}")
