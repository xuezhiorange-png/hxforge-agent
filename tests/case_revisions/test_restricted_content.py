"""Section 18.9 — Restricted-content fixture scan tests + Section 15."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from hexagent.case_revisions import (
    RestrictedContentViolation,
    scan_payload_for_restricted_content,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK014_DIR = REPO_ROOT / "src" / "hexagent" / "case_revisions"
TASK014_TESTS_DIR = REPO_ROOT / "tests" / "case_revisions"


def test_standards_body_tokens_detected() -> None:
    """Section 15.1 — standards-body token (e.g., ``ASME``) detected."""
    for token in ("ASME", "ASTM", "ISO", "TEMA", "API"):
        payload = {"text": f"reference to {token} standard"}
        with pytest.raises(RestrictedContentViolation) as ei:
            scan_payload_for_restricted_content(payload)
        assert ei.value.violation_kind == "standard_body"


def test_standards_body_tokens_not_triggered_by_substring() -> None:
    """Section 15.1 — substring matches (e.g., ``iso`` inside ``isobaric``)
    MUST NOT trigger."""
    payload = {"text": "isobaric compression at standard conditions"}
    # Should NOT raise — "ISO" appears only as substring "iso" not word.
    scan_payload_for_restricted_content(payload)


def test_vendor_catalog_body_detected() -> None:
    payload = {"text": "vendor catalog body for pump selection"}
    with pytest.raises(RestrictedContentViolation) as ei:
        scan_payload_for_restricted_content(payload)
    assert ei.value.violation_kind == "vendor_catalog_body"


def test_paid_price_list_detected() -> None:
    payload = {"text": "paid price list for material grades"}
    with pytest.raises(RestrictedContentViolation) as ei:
        scan_payload_for_restricted_content(payload)
    assert ei.value.violation_kind == "paid_price_list"


def test_restricted_property_table_detected() -> None:
    payload = {"text": "restricted material property table for alloy X"}
    with pytest.raises(RestrictedContentViolation) as ei:
        scan_payload_for_restricted_content(payload)
    assert ei.value.violation_kind == "restricted_property_table"


def test_scanned_page_pattern_detected() -> None:
    payload = {"reference": "scan://page-1-2026"}
    with pytest.raises(RestrictedContentViolation) as ei:
        scan_payload_for_restricted_content(payload)
    assert ei.value.violation_kind == "scanned_page"


def test_formula_image_pattern_detected() -> None:
    payload = {"reference": "image://formula-dittus-boelter-001"}
    with pytest.raises(RestrictedContentViolation) as ei:
        scan_payload_for_restricted_content(payload)
    assert ei.value.violation_kind == "formula_image"


def test_copied_standard_table_detected() -> None:
    payload = {"text": "copied standard table for heat exchanger tubes"}
    with pytest.raises(RestrictedContentViolation) as ei:
        scan_payload_for_restricted_content(payload)
    assert ei.value.violation_kind == "copied_standard_table"


def test_clean_payload_passes_scan() -> None:
    """A synthetic / metadata-only payload with internal:// placeholders
    MUST pass the scan."""
    payload = {
        "case_id": "case-1",
        "reference": "internal://handbook/case-1",
        "notes": "synthetic fixture for testing",
    }
    # Should not raise.
    scan_payload_for_restricted_content(payload)


def test_repo_wide_fixture_scan_finds_no_restricted_content() -> None:
    """Section 18.9 — repo-wide scan asserts no TASK-014 fixture or
    example contains restricted content.

    The scanner source (``restricted.py``) and the test module itself
    (``test_restricted_content.py``) MUST mention the restricted
    phrases — they are the canonical test fixtures. We therefore
    scope the scan to the rest of the TASK-014 source + tests tree.
    """
    suspicious_patterns = (
        "ASME B31",
        "ASTM A",
        "vendor catalog body",
        "paid price list",
        "restricted material property table",
        "scanned page reference",
        "formula image",
        "copied standard table",
    )
    excluded = {
        TASK014_DIR / "restricted.py",
        TASK014_TESTS_DIR / "test_restricted_content.py",
    }
    found: list[tuple[Path, str, str]] = []
    # Scan TASK-014 source + tests (only — not the whole repo).
    for root in (TASK014_DIR, TASK014_TESTS_DIR):
        for path in root.rglob("*.py"):
            if path in excluded:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                for pattern in suspicious_patterns:
                    if re.search(re.escape(pattern), line, flags=re.IGNORECASE):
                        found.append((path, f"L{line_no}", line.strip()))
    assert not found, (
        f"restricted-content pattern detected in fixtures: {found}\n"
        "Use synthetic / metadata-only placeholders (e.g., internal://handbook/<id>)."
    )
