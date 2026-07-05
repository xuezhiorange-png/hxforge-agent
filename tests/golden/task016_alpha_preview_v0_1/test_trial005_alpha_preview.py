"""TASK-016 Alpha Preview v0.1 golden verification tests (TRIAL-005).

Implements the TRIAL-005 golden verification surface authorized by
``docs/trials/TASK-016-alpha-preview-v0.1.md``:

* Section 6.5 — ``test coverage that proves the trial fixtures remain
  deterministic``;
* Section 11 line 271 — ``TASK-016-TRIAL-005: add golden verification
  tests and CI manifest ownership``;
* Section 10.2 — every success case produces stable output;
* Section 10.5 — record and catalog hashes are stable and derived from
  canonical JSON;
* Section 10.8 — missing pipe reference blocker is covered by fixture
  and test;
* Section 10.9 — non-approved reference blocker is covered by fixture
  and test.

These tests are **bound to the five existing TASK-016 Alpha Preview
v0.1 trial cases** committed by TRIAL-001 (fixture skeletons) and
TRIAL-002 (expected output skeletons). They do not introduce new
fixtures, expected outputs, runner logic, or TASK-017+ semantics.

Authority baseline
------------------

* TASK-016 design PR: ``#68`` (merged).
* Design merge commit: ``984eee5de49a3805182b54841463ebbba91fca88``.
* TASK-016 implementation PR: ``#67`` (merged).
* Implementation merge commit: ``ac7a4152698f039b4d6795f6a814228cb3c43def``.
* TASK-016-TRIAL dedicated Issue: ``#70`` (OPEN).
* TASK-016-TRIAL-005 implementation PR: ``#71`` (Draft).
* TRIAL-001 commit: ``64d0bcaf8212866f3b39d135ce3c8d932db3fb7b``.
* TRIAL-002 commit: ``3b2b43bc2e24309dd742a8fb8ba7223bc41b0d18``.
* TRIAL-004 commit: ``eeb762d2abcf1db498ece05b360194f1b6b9b5bd``.

Constraints
-----------

* No mutation of any fixture, expected output, runner, production code,
  governance contract, CI manifest (other than registering this test
  file in the ``golden`` shard), or TASK-017+ surface.
* No engineering calculation; this test only verifies the
  TASK-016-frozen catalog loader behaviour against the TRIAL-001/002
  committed golden artifacts.
* No secrets, no network calls, no subprocess; the runner is invoked
  via direct in-process import so the test is hermetic and stable
  across Python 3.11 and 3.12 (design section 10.2).
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

import pytest

from hexagent.geometry_catalogs import (
    GeometryCatalogBlockerError,
    load_geometry_catalog,
)
from scripts.run_task016_alpha_preview_case import (
    TRIAL_VERSION,
    _build_blocker_output,
    _build_success_output,
)

pytestmark = pytest.mark.golden

# ---------------------------------------------------------------------------
# Canonical paths and constants
# ---------------------------------------------------------------------------

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
_FIXTURE_DIR: Final[Path] = _REPO_ROOT / "examples" / "task016_alpha_preview_v0_1" / "fixtures"
_EXPECTED_DIR: Final[Path] = _REPO_ROOT / "examples" / "task016_alpha_preview_v0_1" / "expected"

_SHA256_HEX_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")


# ---------------------------------------------------------------------------
# Per-case parameters
# ---------------------------------------------------------------------------


_CASE_PARAMETERS: Final[tuple[dict[str, str], ...]] = (
    {
        "case_id": "case_001_catalog_success",
        "fixture_name": "catalog_success.input.json",
        "expected_name": "catalog_success.expected.json",
        "status": "success",
    },
    {
        "case_id": "case_002_hairpin_success",
        "fixture_name": "hairpin_success.input.json",
        "expected_name": "hairpin_success.expected.json",
        "status": "success",
    },
    {
        "case_id": "case_003_blocker_unapproved_geometry",
        "fixture_name": "unapproved_geometry.input.json",
        "expected_name": "unapproved_geometry.expected.json",
        "status": "blocked",
    },
    {
        "case_id": "case_004_blocker_missing_pipe_reference",
        "fixture_name": "missing_pipe_reference.input.json",
        "expected_name": "missing_pipe_reference.expected.json",
        "status": "blocked",
    },
    {
        "case_id": "case_005_blocker_dimension_inconsistent",
        "fixture_name": "dimension_inconsistent.input.json",
        "expected_name": "dimension_inconsistent.expected.json",
        "status": "blocked",
    },
)


def _load_json(path: Path) -> dict[str, Any]:
    """Read and JSON-parse ``path``. Fails the test on JSON errors."""
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        pytest.fail(f"{path}: top-level JSON must be an object, got {type(data).__name__}")
    return data


def _build_actual(fixture: dict[str, Any]) -> dict[str, Any]:
    """Drive the runner's actual-output builders against ``fixture``."""
    try:
        return _build_success_output(fixture)
    except GeometryCatalogBlockerError as exc:
        return _build_blocker_output(fixture, exc)


# ---------------------------------------------------------------------------
# Discovery sanity checks (run once per session)
# ---------------------------------------------------------------------------


def test_trial005_discovery_finds_all_five_pairs() -> None:
    """All five fixture/expected pairs must exist on disk (TRIAL-001/002 invariant)."""
    assert _FIXTURE_DIR.is_dir(), f"missing fixture dir: {_FIXTURE_DIR}"
    assert _EXPECTED_DIR.is_dir(), f"missing expected dir: {_EXPECTED_DIR}"

    for params in _CASE_PARAMETERS:
        fixture_path = _FIXTURE_DIR / params["fixture_name"]
        expected_path = _EXPECTED_DIR / params["expected_name"]
        assert fixture_path.is_file(), f"missing fixture: {fixture_path}"
        assert expected_path.is_file(), f"missing expected: {expected_path}"


def test_trial005_all_json_files_parse() -> None:
    """All ten trial JSON files (5 fixtures + 5 expected) must be JSON-parseable."""
    for params in _CASE_PARAMETERS:
        fixture_path = _FIXTURE_DIR / params["fixture_name"]
        expected_path = _EXPECTED_DIR / params["expected_name"]
        _load_json(fixture_path)  # raises on parse error
        _load_json(expected_path)


# ---------------------------------------------------------------------------
# Per-case verification (parametrized)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "params",
    list(_CASE_PARAMETERS),
    ids=[p["case_id"] for p in _CASE_PARAMETERS],
)
def test_trial005_actual_matches_expected_on_required_fields(
    params: Mapping[str, str],
) -> None:
    """Runner output must match the TRIAL-002 expected output on every
    design-section-9 required field for every trial case.

    Required fields (per design section 9 and the runner's
    ``SUCCESS_REQUIRED_FIELDS`` / ``BLOCKER_REQUIRED_FIELDS``):

    * common: ``trial_version``, ``case_id``, ``status``;
    * success: ``catalog_content_hash``, ``ordered_geometry_ids``,
      ``record_hashes``;
    * blocker: ``error_code``, ``context``.
    """
    fixture = _load_json(_FIXTURE_DIR / params["fixture_name"])
    expected = _load_json(_EXPECTED_DIR / params["expected_name"])
    actual = _build_actual(fixture)

    # Common required fields.
    assert actual["trial_version"] == TRIAL_VERSION
    assert actual["case_id"] == params["case_id"]
    assert actual["status"] == params["status"]
    assert actual["trial_version"] == expected["trial_version"]
    assert actual["case_id"] == expected["case_id"]
    assert actual["status"] == expected["status"]

    if params["status"] == "success":
        # Required success fields per design section 9.
        assert actual["catalog_content_hash"] == expected["catalog_content_hash"], (
            f"catalog_content_hash diverged for {params['case_id']!r}"
        )
        assert actual["ordered_geometry_ids"] == expected["ordered_geometry_ids"], (
            f"ordered_geometry_ids diverged for {params['case_id']!r}"
        )
        assert dict(actual["record_hashes"]) == dict(expected["record_hashes"]), (
            f"record_hashes diverged for {params['case_id']!r}"
        )
    else:
        # Required blocker fields per design section 9.
        assert actual["error_code"] == expected["error_code"], (
            f"error_code diverged for {params['case_id']!r}: "
            f"actual={actual['error_code']!r} expected={expected['error_code']!r}"
        )
        assert dict(actual["context"]) == dict(expected["context"]), (
            f"context diverged for {params['case_id']!r}"
        )


@pytest.mark.parametrize(
    "params",
    [p for p in _CASE_PARAMETERS if p["status"] == "success"],
    ids=[p["case_id"] for p in _CASE_PARAMETERS if p["status"] == "success"],
)
def test_trial005_success_hashes_are_real_sha256(params: Mapping[str, str]) -> None:
    """catalog_content_hash and every record_hash must be a 64-char
    lowercase hex SHA-256 (design section 10.5)."""
    expected = _load_json(_EXPECTED_DIR / params["expected_name"])

    catalog_content_hash = expected["catalog_content_hash"]
    assert isinstance(catalog_content_hash, str), (
        f"catalog_content_hash must be a string, got {type(catalog_content_hash).__name__}"
    )
    assert _SHA256_HEX_RE.match(catalog_content_hash), (
        f"catalog_content_hash is not 64-char lowercase hex SHA-256: {catalog_content_hash!r}"
    )

    record_hashes = expected["record_hashes"]
    assert isinstance(record_hashes, dict), (
        f"record_hashes must be a dict, got {type(record_hashes).__name__}"
    )
    assert record_hashes, "record_hashes must be non-empty"
    for geometry_id, record_hash in record_hashes.items():
        assert isinstance(geometry_id, str) and geometry_id, (
            f"record_hashes key must be a non-empty string, got {geometry_id!r}"
        )
        assert isinstance(record_hash, str), (
            f"record_hash for {geometry_id!r} must be a string, got {type(record_hash).__name__}"
        )
        assert _SHA256_HEX_RE.match(record_hash), (
            f"record_hash for {geometry_id!r} is not 64-char lowercase hex SHA-256: {record_hash!r}"
        )


@pytest.mark.parametrize(
    "params",
    [p for p in _CASE_PARAMETERS if p["status"] == "success"],
    ids=[p["case_id"] for p in _CASE_PARAMETERS if p["status"] == "success"],
)
def test_trial005_success_output_is_deterministic(params: Mapping[str, str]) -> None:
    """Running the runner twice on the same fixture must produce identical
    output (design section 10.2 — stability across Python 3.11 / 3.12)."""
    fixture = _load_json(_FIXTURE_DIR / params["fixture_name"])

    first = _build_actual(fixture)
    second = _build_actual(fixture)
    assert first == second, f"runner output is not deterministic for {params['case_id']!r}"


def test_trial005_missing_pipe_reference_uses_pipe_geometry_id() -> None:
    """Design section 10.8: the missing pipe reference blocker must be
    triggered and ``context.reference_field`` must identify the
    pipe-side reference (not the tube-side)."""
    fixture = _load_json(_FIXTURE_DIR / "missing_pipe_reference.input.json")
    expected = _load_json(_EXPECTED_DIR / "missing_pipe_reference.expected.json")

    assert expected["error_code"] == "geometry_reference_missing"
    assert expected["context"]["reference_field"] == "pipe_geometry_id"

    actual = _build_actual(fixture)
    assert actual["error_code"] == "geometry_reference_missing"
    assert actual["context"]["reference_field"] == "pipe_geometry_id"


def test_trial005_unapproved_reference_is_geometry_record_unapproved() -> None:
    """Design section 10.9: the non-approved (invalid approval_state)
    reference blocker must be triggered."""
    fixture = _load_json(_FIXTURE_DIR / "unapproved_geometry.input.json")
    expected = _load_json(_EXPECTED_DIR / "unapproved_geometry.expected.json")

    assert expected["error_code"] == "geometry_record_unapproved"

    actual = _build_actual(fixture)
    assert actual["error_code"] == "geometry_record_unapproved"


# ---------------------------------------------------------------------------
# Catalog-loader-level invariants (no runner, direct TASK-016 API check)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "params",
    [p for p in _CASE_PARAMETERS if p["status"] == "success"],
    ids=[p["case_id"] for p in _CASE_PARAMETERS if p["status"] == "success"],
)
def test_trial005_load_geometry_catalog_matches_expected(params: Mapping[str, str]) -> None:
    """Direct TASK-016 catalog loader call must produce the same
    catalog_content_hash + record_hash set as the expected output.

    This is the design-section-10.5 invariant: hash stability is a
    property of the TASK-016 implementation, not of the runner wrapper.
    """
    fixture = _load_json(_FIXTURE_DIR / params["fixture_name"])
    expected = _load_json(_EXPECTED_DIR / params["expected_name"])
    payload = fixture["fixture_input"]["payload"]

    catalog = load_geometry_catalog(payload)
    assert catalog.content_hash == expected["catalog_content_hash"], (
        f"catalog.content_hash diverged from expected for {params['case_id']!r}"
    )

    actual_record_hashes = {r.geometry_id: r.record_hash for r in catalog.records}
    assert actual_record_hashes == dict(expected["record_hashes"]), (
        f"record_hash set diverged from expected for {params['case_id']!r}"
    )

    # ordered_geometry_ids must follow the catalog's deterministic order.
    actual_ordered = [r.geometry_id for r in catalog.records]
    assert actual_ordered == list(expected["ordered_geometry_ids"]), (
        f"ordered_geometry_ids diverged from expected for {params['case_id']!r}"
    )


def test_trial005_blocker_fixtures_raise_geometry_catalog_blocker_error() -> None:
    """The three blocker fixtures must raise ``GeometryCatalogBlockerError``
    when fed to the TASK-016 catalog loader directly, and the raised
    error_code must match the expected output."""
    blocker_params = [p for p in _CASE_PARAMETERS if p["status"] == "blocked"]
    assert len(blocker_params) == 3, f"expected exactly 3 blocker cases, got {len(blocker_params)}"

    for params in blocker_params:
        fixture = _load_json(_FIXTURE_DIR / params["fixture_name"])
        expected = _load_json(_EXPECTED_DIR / params["expected_name"])
        payload = fixture["fixture_input"]["payload"]

        with pytest.raises(GeometryCatalogBlockerError) as excinfo:
            load_geometry_catalog(payload)

        raised = excinfo.value
        assert raised.error_code == expected["error_code"], (
            f"loader raised error_code={raised.error_code!r} for "
            f"{params['case_id']!r}, expected {expected['error_code']!r}"
        )
        assert dict(raised.context) == dict(expected["context"]), (
            f"loader context diverged from expected for {params['case_id']!r}"
        )
