"""Validation surface for the TASK-011 benchmark-case corpus."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from hexagent.benchmark_cases.canonical import canonical_sha256

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
REQUIRED_SOURCE_EVIDENCE_FIELDS = {
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


def _load_json_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value: Any = json.load(handle)
    _require(isinstance(value, dict), f"{path} must contain a JSON object")
    return cast(dict[str, Any], value)


def _load_json_object_list(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        value: Any = json.load(handle)
    _require(isinstance(value, list), f"{path} must contain a JSON array")
    for item in value:
        _require(isinstance(item, dict), f"{path} must contain only JSON objects")
    return cast(list[dict[str, Any]], value)


def _string_list(value: Any, field: str) -> list[str]:
    _require(isinstance(value, list), f"{field} must be a list")
    for item in value:
        _require(isinstance(item, str), f"{field} must contain only strings")
    return cast(list[str], value)


def _string_map(value: Any, field: str) -> dict[str, str]:
    _require(isinstance(value, dict), f"{field} must be a map")
    for key, item in value.items():
        _require(
            isinstance(key, str) and isinstance(item, str),
            f"{field} must map strings to strings",
        )
    return cast(dict[str, str], value)


def _validate_case(case: dict[str, Any], *, manifest_synthetic_ids: set[str]) -> str:
    missing = sorted(REQUIRED_CASE_FIELDS - set(case))
    _require(not missing, f"{case.get('case_id', '<unknown>')} missing fields: {missing}")

    case_id = cast(str, case["case_id"])
    _require(isinstance(case_id, str) and case_id, "case_id must be a non-empty string")
    category = cast(str, case["category"])
    _require(category in ALLOWED_CATEGORIES, f"{case_id} has unsupported category")
    _require(case["approval_status"] == "approved", f"{case_id} is not approved")

    source_evidence_value = case["source_evidence"]
    _require(isinstance(source_evidence_value, dict), f"{case_id} source_evidence must be object")
    source_evidence = cast(dict[str, Any], source_evidence_value)
    missing_source = sorted(REQUIRED_SOURCE_EVIDENCE_FIELDS - set(source_evidence))
    _require(not missing_source, f"{case_id} missing source fields: {missing_source}")
    _require(
        source_evidence["reviewer_evidence_check_status"] == "accepted",
        f"{case_id} evidence review is not accepted",
    )

    if case["source_type"] == "synthetic_regression_case":
        _require(
            case.get("is_synthetic") is True,
            f"{case_id} synthetic case missing is_synthetic=true",
        )
        _require(
            case_id in manifest_synthetic_ids,
            f"{case_id} synthetic case missing from manifest",
        )
        _require(
            source_evidence["expected_output_origin"] == "synthetic_computation",
            f"{case_id} synthetic case must declare synthetic_computation origin",
        )

    expected_outputs = case["expected_output_schema"]
    _require(
        isinstance(expected_outputs, list) and bool(expected_outputs),
        f"{case_id} has no expected outputs",
    )
    output_names: list[str] = []
    for output_value in expected_outputs:
        _require(isinstance(output_value, dict), f"{case_id} expected outputs must be objects")
        output = cast(dict[str, Any], output_value)
        name = output.get("output_name")
        _require(isinstance(name, str) and name, f"{case_id} expected output missing output_name")
        output_names.append(name)
        _require(
            not name.startswith(FORBIDDEN_OUTPUT_PREFIXES),
            f"{case_id} uses forbidden expected output prefix: {name}",
        )

    tolerance_values = case["tolerance_justifications"]
    _require(
        isinstance(tolerance_values, list),
        f"{case_id} tolerance_justifications must be a list",
    )
    tolerance_names = {
        item.get("output_name")
        for item in tolerance_values
        if isinstance(item, dict) and isinstance(item.get("output_name"), str)
    }
    _require(
        set(output_names) <= tolerance_names,
        f"{case_id} lacks tolerance justification coverage",
    )

    recomputed_hash = canonical_sha256(case)
    _require(recomputed_hash == case["canonical_hash"], f"{case_id} canonical hash mismatch")
    return recomputed_hash


def validate_corpus(root: Path | str = Path(".")) -> None:
    root = Path(root)
    manifest_path = root / "benchmarks" / "manifests" / "task-011-approved-manifest.json"
    cases_path = root / "benchmarks" / "cases" / "task-011-approved-cases.json"

    manifest = _load_json_object(manifest_path)
    cases = _load_json_object_list(cases_path)
    missing_manifest = sorted(REQUIRED_MANIFEST_FIELDS - set(manifest))
    _require(not missing_manifest, f"manifest missing fields: {missing_manifest}")

    case_ids = _string_list(manifest["case_ids"], "manifest.case_ids")
    case_hashes = _string_map(manifest["case_hashes"], "manifest.case_hashes")
    synthetic_case_ids = _string_list(manifest["synthetic_case_ids"], "manifest.synthetic_case_ids")

    _require(case_ids == sorted(case_ids), "manifest case_ids must be sorted")
    _require(len(case_ids) == len(set(case_ids)), "manifest case_ids must be unique")
    _require(manifest["case_count"] == len(case_ids), "manifest case_count mismatch")
    _require(
        manifest["case_count"] == 20,
        "TASK-011 first implementation target must contain 20 cases",
    )
    _require(set(case_hashes) == set(case_ids), "manifest case_hashes keys mismatch")

    cases_by_id = {case.get("case_id"): case for case in cases}
    _require(set(cases_by_id) == set(case_ids), "case corpus ids do not match manifest")
    _require(len(cases_by_id) == len(cases), "case corpus must not contain duplicate ids")

    synthetic_ids = set(synthetic_case_ids)
    _require(synthetic_ids <= set(case_ids), "synthetic_case_ids must be a subset of case_ids")

    actual_synthetic_ids: set[str] = set()
    for case_id in case_ids:
        case = cases_by_id[case_id]
        recomputed_hash = _validate_case(case, manifest_synthetic_ids=synthetic_ids)
        _require(case_hashes[case_id] == recomputed_hash, f"manifest hash mismatch for {case_id}")
        if case.get("is_synthetic") is True:
            actual_synthetic_ids.add(case_id)

    _require(actual_synthetic_ids == synthetic_ids, "synthetic_case_ids mismatch corpus contents")
    approval_snapshot = manifest["approval_snapshot"]
    _require(isinstance(approval_snapshot, list), "manifest approval_snapshot must be a list")
    _require(
        len(approval_snapshot) == manifest["case_count"],
        "manifest approval_snapshot must contain one record per case",
    )
    _require(bool(manifest["reviewer_sign_off"]), "manifest reviewer_sign_off is required")


def main() -> int:
    validate_corpus(Path.cwd())
    print("TASK-011 benchmark corpus validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
