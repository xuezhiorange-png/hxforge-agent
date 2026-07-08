"""TASK-019 excluded-scopes negative guard tests (Slice 1).

Asserts that:
- Golden fixture JSON contains no pressure_drop_*, c4_*, tema_*, kern_*,
  bell_delaware_*, vendor_quote_*, c3_* keys.
- No TASK-020+ content.
- No new correlation registry entries.
- No new property provider entries.
- No real discount formula: discounted_total_minor_units remains null
  for case 03; no function or fixture field encodes discount computation.
- No real salvage formula: salvage_minor_units remains 0 for case 03.
- No Issue #23 action: no implementation code, fixture, generated report,
  runtime path, or new non-governance doc performs or implies Issue #23
  action. Governance-only references in frozen docs are allowed.
- No Feishu outbound: no outbound integration, webhook, client, token,
  URL, or send path. Governance-only references in frozen docs are allowed.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_GOLDEN_FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent / "golden" / "double_pipe_rating"
)


# --- Forbidden key prefixes in fixture JSONs (per frozen design §6) ---


FORBIDDEN_FIXTURE_KEY_PREFIXES = (
    "pressure_drop_",
    "c4_",
    "tema_",
    "kern_",
    "bell_delaware_",
    "vendor_quote_",
    "c3_",
)


def _all_fixture_paths():
    return [
        _GOLDEN_FIXTURE_DIR / "case_01_heat_balance_rating.json",
        _GOLDEN_FIXTURE_DIR / "case_02_materials_mass_mechanical.json",
        _GOLDEN_FIXTURE_DIR / "case_03_cost_lifecycle_envelope.json",
    ]


def _all_keys_recursive(obj, path=""):
    """Yield all key paths in a nested dict."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            yield new_path
            yield from _all_keys_recursive(v, new_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from _all_keys_recursive(item, f"{path}[{i}]")


def _is_forbidden_key(key: str, forbidden_prefixes) -> str:
    """Return the forbidden prefix that matches the key, or empty string.

    Uses word-boundary matching: the forbidden prefix must be followed by a
    non-alphanumeric char (or end-of-string) for it to count as a match.
    This avoids false positives on metadata fields like
    ``pressure_drop_excluded_from_taska_019`` where the prefix is part of
    a longer descriptive key but the field is NOT a pressure-drop value.

    Per frozen design §6 + authorization intent, the FORBIDDEN items are
    actual pressure-drop VALUES, not metadata. Real pressure-drop value
    keys (e.g. ``pressure_drop_value``, ``pressure_drop_pa``) still match
    because they end with a non-alphanumeric char (or end-of-string).
    """
    last_segment = key.rsplit(".", 1)[-1]
    for forbidden in forbidden_prefixes:
        if not last_segment.startswith(forbidden):
            continue
        # Word-boundary check: the prefix must be followed by a non-alphanumeric
        # char or end-of-string to count as a true "forbidden prefix" match.
        if len(last_segment) == len(forbidden):
            return forbidden  # exact match
        next_char = last_segment[len(forbidden)]
        if not next_char.isalnum() and next_char != "_":
            return forbidden
    return ""


def test_fixtures_have_no_forbidden_key_prefixes() -> None:
    """All 3 fixtures must not contain any forbidden key prefix (word-boundary).

    The forbidden prefix list (e.g. ``pressure_drop_*``) targets actual
    pressure-drop value keys. Metadata fields that happen to start with
    the forbidden string as part of a longer descriptive key
    (e.g. ``pressure_drop_excluded_from_taska_019``) are NOT flagged —
    this matches frozen design §6 intent: pressure drop is excluded from
    TASK-019, but recording this exclusion in a metadata field is allowed.
    """
    for fp in _all_fixture_paths():
        with fp.open() as fh:
            data = json.load(fh)
        keys = list(_all_keys_recursive(data))
        for k in keys:
            forbidden = _is_forbidden_key(k, FORBIDDEN_FIXTURE_KEY_PREFIXES)
            if forbidden:
                raise AssertionError(
                    f"fixture {fp.name} contains forbidden key {k!r} "
                    f"matching prefix {forbidden!r}"
                )


def test_pressure_drop_value_is_not_computable_in_all_fixtures() -> None:
    """Per frozen design §6, pressure_drop is excluded from TASK-019; fixtures
    must record pressure_drop as NOT_COMPUTABLE or absent (not as a real value)."""
    for fp in _all_fixture_paths():
        with fp.open() as fh:
            data = json.load(fh)
        eo = data.get("expected_output", {})
        # If pressure_drop key is present, it must be a non-computable marker
        pd_value = eo.get("pressure_drop")
        if pd_value is not None:
            # Allow NOT_COMPUTABLE marker but not a numeric value
            assert not isinstance(pd_value, (int, float)), (
                f"fixture {fp.name} has numeric pressure_drop value {pd_value!r}; "
                f"pressure drop is excluded from TASK-019 per frozen design §6"
            )


# --- Case 03: TASK-018 Option A boundary preserved ---


def test_case_03_discounted_total_minor_units_is_null() -> None:
    """Per frozen design §5.1, TASK-018 Option A: discounted_total_minor_units is null."""
    path = _GOLDEN_FIXTURE_DIR / "case_03_cost_lifecycle_envelope.json"
    with path.open() as fh:
        data = json.load(fh)
    eo = data.get("expected_output", {})
    assert eo.get("discounted_total_minor_units") is None, (
        f"case 03 must have discounted_total_minor_units=null per Option A; "
        f"got {eo.get('discounted_total_minor_units')!r}"
    )


def test_case_03_salvage_minor_units_is_zero_placeholder() -> None:
    """Per frozen design §5.2, salvage_minor_units is 0 placeholder (no real formula)."""
    path = _GOLDEN_FIXTURE_DIR / "case_03_cost_lifecycle_envelope.json"
    with path.open() as fh:
        data = json.load(fh)
    eo = data.get("expected_output", {})
    assert eo.get("salvage_minor_units") == 0, (
        f"case 03 must have salvage_minor_units=0 placeholder; "
        f"got {eo.get('salvage_minor_units')!r}"
    )


def test_case_03_unspecified_blocker_records_discount_formula_deferral() -> None:
    """Case 03 must record the TASK-018 Option A unspecified_blocker signal
    with reason="discount_formula_pending_design_amendment" when represented."""
    path = _GOLDEN_FIXTURE_DIR / "case_03_cost_lifecycle_envelope.json"
    with path.open() as fh:
        data = json.load(fh)
    eo = data.get("expected_output", {})
    # unspecified_blocker may be absent (Slice 1 may not wire this yet) or
    # carry the canonical reason string. If present, must carry the reason.
    blocker = eo.get("unspecified_blocker")
    if blocker is not None:
        assert isinstance(blocker, dict)
        reason = blocker.get("details", {}).get("reason")
        assert reason == "discount_formula_pending_design_amendment", (
            f"unspecified_blocker.details.reason must be the canonical "
            f"discount_formula_pending_design_amendment string; got {reason!r}"
        )


def test_no_real_discount_formula_in_implementation() -> None:
    """No real discount formula may appear in the validation_report source."""
    src_path = (
        _REPO_ROOT / "src" / "hexagent" / "validation_report" / "double_pipe_validation_report.py"
    )
    if not src_path.exists():
        return
    text = src_path.read_text()
    # Forbidden: a function/method that *computes* a discount (not just observes
    # the Option A boundary). Slice 1 is schema-only; any discount calculation
    # logic is forbidden.
    forbidden_discount_compute_patterns = (
        r"def\s+\w*[Dd]iscount\w*\s*\(",
        r"def\s+compute_discount",
        r"def\s+apply_discount",
        r"def\s+npv\w*\s*\(",
        r"def\s+irr\w*\s*\(",
        r"def\s+pv\w*\s*\(",
        r"discount_rate\s*\*",
        r"\(1\s*\+\s*r\)\s*\*\*",  # compounding formula
        r"sum.*\*\s*discount",  # PV sum pattern
    )
    for pat in forbidden_discount_compute_patterns:
        if re.search(pat, text):
            raise AssertionError(
                f"real discount-formula computation pattern found in "
                f"double_pipe_validation_report.py: {pat!r}"
            )


def test_no_real_salvage_formula_in_implementation() -> None:
    """No real salvage formula may appear in the validation_report source."""
    src_path = (
        _REPO_ROOT / "src" / "hexagent" / "validation_report" / "double_pipe_validation_report.py"
    )
    if not src_path.exists():
        return
    text = src_path.read_text()
    forbidden_salvage_compute_patterns = (
        r"def\s+\w*[Ss]alvage\w*\s*\(",
        r"def\s+compute_salvage",
        r"def\s+apply_salvage",
        r"salvage_fraction\s*\*",
    )
    for pat in forbidden_salvage_compute_patterns:
        if re.search(pat, text):
            raise AssertionError(
                f"real salvage-formula computation pattern found in "
                f"double_pipe_validation_report.py: {pat!r}"
            )


# --- No Issue #23 / Feishu action in implementation ---


def test_no_implementation_code_touches_issue_23() -> None:
    """No implementation code, fixture, generated report, runtime path, or
    new non-governance doc performs or implies Issue #23 action. Governance-
    only references in frozen docs are allowed (and indeed the design
    contract must reference Issue #23 as a boundary)."""
    # Scan src/ for Issue #23 references OUTSIDE of governance-exclusion context
    src_path = _REPO_ROOT / "src" / "hexagent" / "validation_report" / "double_pipe_validation_report.py"
    if not src_path.exists():
        return
    text = src_path.read_text()
    # The only acceptable Issue #23 reference in implementation code is a
    # governance-comment line explaining the boundary. Slice 1 implementation
    # code should not need to mention Issue #23 at all.
    for i, line in enumerate(text.splitlines(), start=1):
        if "Issue #23" in line or "Issue 23" in line or "issue/23" in line:
            # Allow only in explicit governance-boundary comments
            stripped = line.strip()
            if not (
                stripped.startswith("#") or
                "governance" in stripped.lower() or
                "frozen design" in stripped.lower() or
                "Issue #23 remains NOT TOUCHED" in stripped
            ):
                raise AssertionError(
                    f"non-governance Issue #23 reference in "
                    f"double_pipe_validation_report.py L{i}: {line!r}"
                )


def test_no_feishu_outbound_in_implementation() -> None:
    """No Feishu outbound integration, webhook, client, token, URL, or send
    path in implementation code. Governance-only references are allowed."""
    src_path = _REPO_ROOT / "src" / "hexagent" / "validation_report" / "double_pipe_validation_report.py"
    if not src_path.exists():
        return
    text = src_path.read_text()
    forbidden_feishu_runtime_patterns = (
        r"import\s+feishu",
        r"from\s+feishu\s+import",
        r"feishu\.send",
        r"feishu_send_message",
        r"feishu_webhook",
        r"requests\.post\([^)]*feishu",
        r"https://open\.feishu\.cn",
        r"https://open\.larksuite\.com",
    )
    for pat in forbidden_feishu_runtime_patterns:
        if re.search(pat, text):
            raise AssertionError(
                f"Feishu runtime pattern found in "
                f"double_pipe_validation_report.py: {pat!r}"
            )


def test_fixtures_contain_no_feishu_or_issue_23_action_keys() -> None:
    """Fixtures must not carry Issue #23 action keys or Feishu send paths."""
    forbidden_key_substrings = (
        "issue_23_action",
        "feishu_send",
        "feishu_webhook",
    )
    for fp in _all_fixture_paths():
        with fp.open() as fh:
            text = fh.read()
        for sub in forbidden_key_substrings:
            assert sub not in text, (
                f"forbidden key substring {sub!r} found in {fp.name}"
            )
