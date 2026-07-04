"""Validation surface for the TASK-011 benchmark-case corpus."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from hexagent.benchmark_cases.canonical import canonical_sha256
from hexagent.benchmark_cases.corpus import approved_cases

ALLOWED_CATEGORIES = {
    "Single-phase heat-balance closure",
    "Tube-side correlation cases",
    "Annulus-side correlation cases",
    "Fixed-geometry double-pipe rating cases",
    "Manufacturable sizing and selection-evaluation cases",
    "API/report traceability cases already supported by TASK-010",
}
FORBIDDEN_OUTPUT_PREFIXES = ("pressure_drop_", "c4_", "material_", "cost_")
REQUIRED_CASE_FIELDS = {
    "case_id",
    "case_version",
    "case_title",
    "category",
    "source_type",
    "source_evidence",
    "input_schema",
    "expected_output_schema",
    "unit_normalization",
    "fluid_and_property_assumptions",
    "geometry_and_boundary_assumptions",
    "tolerance_justifications",
    "assumptions",
    "approval_status",
    "canonical_hash",
}
REQUIRED_SOURCE_FIELDS = {
    "source_type",
    "source_reference",
    "source_title_or_identifier",
    "source_locator_or_citation",
    "source_version_or_publication_date",
    "source_access_date",
    "extracted_input_fields",
    "extracted_expected_output_fields",
    "unit_provenance",
    "normalization_notes",
    "expected_output_origin",
    "evidence_limitations",
    "reviewer_evidence_check_status",
}
REQUIRED_MANIFEST_FIELDS = {
    "manifest_version",
    "schema_version",
    "case_count",
    "case_ids",
    "case_hashes",
    "approval_snapshot",
    "synthetic_case_ids",
    "reviewer_sign_off",
}


class ValidationError(RuntimeError):
    """Raised when the benchmark corpus violates the TASK-011 contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value: Any = json.load(handle)
    _require(isinstance(value, dict), f"{path} must contain a JSON object")
    return cast(dict[str, Any], value)


def _string_list(value: Any, field: str) -> list[str]:
    _require(isinstance(value, list), f"{field} must be a list")
    _require(all(isinstance(item, str) for item in value), f"{field} must contain strings")
    return cast(list[str], value)


def _string_map(value: Any, field: str) -> dict[str, str]:
    _require(isinstance(value, dict), f"{field} must be a map")
    _require(
        all(isinstance(key, str) and isinstance(item, str) for key, item in value.items()),
        f"{field} must map strings to strings",
    )
    return cast(dict[str, str], value)


def _validate_case(case: dict[str, Any], *, synthetic_ids: set[str]) -> str:
    case_id = cast(str, case.get("case_id", "<unknown>"))
    _require(not REQUIRED_CASE_FIELDS - set(case), f"{case_id} missing required fields")
    _require(case["approval_status"] == "approved", f"{case_id} is not approved")
    _require(case["category"] in ALLOWED_CATEGORIES, f"{case_id} has unsupported category")

    source = cast(dict[str, Any], case["source_evidence"])
    _require(isinstance(source, dict), f"{case_id} source_evidence must be object")
    _require(not REQUIRED_SOURCE_FIELDS - set(source), f"{case_id} missing source evidence")
    _require(source["reviewer_evidence_check_status"] == "accepted", f"{case_id} not accepted")

    if case["source_type"] == "synthetic_regression_case":
        _require(case.get("is_synthetic") is True, f"{case_id} missing synthetic marker")
        _require(case_id in synthetic_ids, f"{case_id} missing from synthetic_case_ids")
        _require(
            source["expected_output_origin"] == "synthetic_computation",
            f"{case_id} synthetic origin mismatch",
        )

    outputs = cast(list[dict[str, Any]], case["expected_output_schema"])
    _require(isinstance(outputs, list) and bool(outputs), f"{case_id} has no outputs")
    output_names: set[str] = set()
    for output in outputs:
        name = cast(str, output.get("output_name"))
        _require(isinstance(name, str) and name, f"{case_id} output missing name")
        _require(not name.startswith(FORBIDDEN_OUTPUT_PREFIXES), f"{case_id} forbidden output")
        output_names.add(name)

    tolerances = cast(list[dict[str, Any]], case["tolerance_justifications"])
    tolerance_names = {
        cast(str, item.get("output_name"))
        for item in tolerances
        if isinstance(item, dict) and isinstance(item.get("output_name"), str)
    }
    _require(output_names <= tolerance_names, f"{case_id} tolerance coverage mismatch")

    digest = canonical_sha256(case)
    _require(digest == case["canonical_hash"], f"{case_id} canonical hash mismatch")
    return digest


def validate_corpus(root: Path | str = Path(".")) -> None:
    root = Path(root)
    manifest = _object(root / "benchmarks" / "manifests" / "task-011-approved-manifest.json")
    _require(not REQUIRED_MANIFEST_FIELDS - set(manifest), "manifest missing required fields")

    case_ids = _string_list(manifest["case_ids"], "case_ids")
    case_hashes = _string_map(manifest["case_hashes"], "case_hashes")
    synthetic_ids = set(_string_list(manifest["synthetic_case_ids"], "synthetic_case_ids"))
    _require(case_ids == sorted(case_ids), "case_ids must be sorted")
    _require(len(case_ids) == len(set(case_ids)), "case_ids must be unique")
    _require(manifest["case_count"] == len(case_ids) == 20, "case_count must be exactly 20")
    _require(set(case_hashes) == set(case_ids), "case_hashes keys mismatch")
    _require(synthetic_ids <= set(case_ids), "synthetic_case_ids must be subset of case_ids")

    cases_by_id = {case["case_id"]: case for case in approved_cases()}
    _require(set(cases_by_id) == set(case_ids), "approved case ids must match manifest")

    actual_synthetic_ids: set[str] = set()
    for case_id in case_ids:
        case = cases_by_id[case_id]
        digest = _validate_case(case, synthetic_ids=synthetic_ids)
        _require(case_hashes[case_id] == digest, f"{case_id} manifest hash mismatch")
        if case.get("is_synthetic") is True:
            actual_synthetic_ids.add(case_id)

    _require(actual_synthetic_ids == synthetic_ids, "synthetic_case_ids mismatch")
    approval_snapshot = cast(list[dict[str, Any]], manifest["approval_snapshot"])
    _require(len(approval_snapshot) == 20, "approval_snapshot must contain 20 records")
    _require(bool(manifest["reviewer_sign_off"]), "reviewer_sign_off is required")


def main() -> int:
    validate_corpus(Path.cwd())
    print("TASK-011 benchmark corpus validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
