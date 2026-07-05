"""Restricted-content boundary scan for TASK-014 immutable case revisions.

Implements Section 12.4 + 15 of the TASK-014 frozen design contract
(docs/tasks/TASK-014-immutable-case-revisions-persistence.md,
Frozen Contract Authority SHA
``6f337a6e81a8c2a7ba8059285aeef39bba59c7cb``).

Section 15.1 — no standards body text from ASME / ASTM / ISO / EN / GB /
JIS / DIN / NFPA / TEMA / API / AWS / ASHRAE / IIAR / EIGA.
Section 15.2 — no vendor catalog body.
Section 15.3 — no paid price list.
Section 15.4 — no restricted material property table.
Section 15.5 — no scanned pages / formula images with embedded numeric
content.
Section 15.6 — no copied standard tables.

The scan is intentionally metadata-driven: every fixture / example MUST
be synthetic or metadata-only and MUST use placeholders like
``internal://handbook/<id>`` for references. The scan recognises a small
list of restricted-source markers; new markers must be added in this
module and re-evaluated against the frozen contract.
"""

from __future__ import annotations

import re
from typing import Any

from hexagent.case_revisions.errors import RestrictedContentViolation

# --- Marker sets -----------------------------------------------------------

# Section 15.1 — standards-body tokens. We scan for case-insensitive
# word-boundary matches to avoid false positives on, e.g., the literal
# string ``ISO`` appearing inside a property reference like
# ``source_kind="iso8601"``.
_STANDARDS_BODY_TOKENS: tuple[str, ...] = (
    "ASME",
    "ASTM",
    "ISO",
    "EN",
    "GB",
    "JIS",
    "DIN",
    "NFPA",
    "TEMA",
    "API",
    "AWS",
    "ASHRAE",
    "IIAR",
    "EIGA",
)

# Section 15.2 — vendor catalog body markers. We look for the literal
# phrase "vendor catalog" in free-text fields.
_VENDOR_CATALOG_PHRASES: tuple[str, ...] = (
    "vendor catalog body",
    "vendor catalogue body",
)

# Section 15.3 — paid price list markers.
_PAID_PRICE_LIST_PHRASES: tuple[str, ...] = (
    "paid price list",
    "price list body",
)

# Section 15.4 — restricted material property table markers.
_RESTRICTED_PROPERTY_TABLE_PHRASES: tuple[str, ...] = (
    "restricted material property table",
    "restricted property table",
)

# Section 15.5 — scanned page / formula image markers. We accept either
# the phrase "scanned page" or a prefix like ``scan://`` / ``image://``
# that embeds numeric content.
_SCANNED_PAGE_PATTERNS: tuple[str, ...] = (
    r"scanned page",
    r"scan://[^\s]*\d",
    r"image://[^\s]*\d",
    r"formula image",
)

# Section 15.6 — copied standard table markers.
_COPIED_STANDARD_TABLE_PHRASES: tuple[str, ...] = (
    "copied standard table",
    "table reproduced from standard",
)


# --- Scanner ---------------------------------------------------------------


def _scan_string_for_phrases(value: str, phrases: tuple[str, ...]) -> str | None:
    lowered = value.lower()
    for phrase in phrases:
        if phrase.lower() in lowered:
            return phrase
    return None


def _scan_string_for_patterns(value: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        if re.search(pattern, value, flags=re.IGNORECASE):
            return pattern
    return None


def _extract_text_fields(payload: Any, path: str = "") -> list[tuple[str, str]]:
    """Yield ``(path, string)`` for every string leaf in ``payload``."""
    out: list[tuple[str, str]] = []
    if isinstance(payload, str):
        out.append((path, payload))
    elif isinstance(payload, dict):
        for key, value in payload.items():
            out.extend(_extract_text_fields(value, f"{path}.{key}" if path else str(key)))
    elif isinstance(payload, list):
        for idx, item in enumerate(payload):
            out.extend(_extract_text_fields(item, f"{path}[{idx}]"))
    return out


def scan_payload_for_restricted_content(
    payload: Any, *, root_case_id: str | None = None, revision_id: str | None = None
) -> None:
    """Section 12.4 / 15 — raise :class:`RestrictedContentViolation` iff
    ``payload`` contains any restricted-content marker.

    Returns ``None`` on a clean payload; raises on the first detected
    violation. Callers SHOULD run this scan BEFORE committing a revision
    to the repository so the audit trail records the rejection.
    """
    text_fields = _extract_text_fields(payload)

    for path, value in text_fields:
        # Section 15.1 — standards-body tokens (word-boundary match).
        for token in _STANDARDS_BODY_TOKENS:
            if re.search(rf"\b{re.escape(token)}\b", value):
                raise RestrictedContentViolation(
                    f"restricted standards-body token {token!r} found in "
                    f"payload at {path!r} (Section 15.1)",
                    root_case_id=root_case_id,
                    revision_id=revision_id,
                    violation_kind="standard_body",
                    offending_excerpt=value[:200],
                    path=path,
                )

        # Section 15.2 — vendor catalog body.
        phrase = _scan_string_for_phrases(value, _VENDOR_CATALOG_PHRASES)
        if phrase is not None:
            raise RestrictedContentViolation(
                f"vendor catalog body phrase {phrase!r} found in payload at "
                f"{path!r} (Section 15.2)",
                root_case_id=root_case_id,
                revision_id=revision_id,
                violation_kind="vendor_catalog_body",
                offending_excerpt=value[:200],
                path=path,
            )

        # Section 15.3 — paid price list.
        phrase = _scan_string_for_phrases(value, _PAID_PRICE_LIST_PHRASES)
        if phrase is not None:
            raise RestrictedContentViolation(
                f"paid price list phrase {phrase!r} found in payload at {path!r} (Section 15.3)",
                root_case_id=root_case_id,
                revision_id=revision_id,
                violation_kind="paid_price_list",
                offending_excerpt=value[:200],
                path=path,
            )

        # Section 15.4 — restricted material property table.
        phrase = _scan_string_for_phrases(value, _RESTRICTED_PROPERTY_TABLE_PHRASES)
        if phrase is not None:
            raise RestrictedContentViolation(
                f"restricted material property table phrase {phrase!r} found "
                f"in payload at {path!r} (Section 15.4)",
                root_case_id=root_case_id,
                revision_id=revision_id,
                violation_kind="restricted_property_table",
                offending_excerpt=value[:200],
                path=path,
            )

        # Section 15.5 — scanned page / formula image.
        pattern = _scan_string_for_patterns(value, _SCANNED_PAGE_PATTERNS)
        if pattern is not None:
            raise RestrictedContentViolation(
                f"scanned page / formula image pattern {pattern!r} found in "
                f"payload at {path!r} (Section 15.5)",
                root_case_id=root_case_id,
                revision_id=revision_id,
                violation_kind="scanned_page" if "scan" in pattern.lower() else "formula_image",
                offending_excerpt=value[:200],
                path=path,
            )

        # Section 15.6 — copied standard table.
        phrase = _scan_string_for_phrases(value, _COPIED_STANDARD_TABLE_PHRASES)
        if phrase is not None:
            raise RestrictedContentViolation(
                f"copied standard table phrase {phrase!r} found in payload at "
                f"{path!r} (Section 15.6)",
                root_case_id=root_case_id,
                revision_id=revision_id,
                violation_kind="copied_standard_table",
                offending_excerpt=value[:200],
                path=path,
            )


__all__ = ["scan_payload_for_restricted_content"]
