"""TASK-024 strict Stage-1 schema parser.

Implements ``parse_request`` (Section 8.3 + 6.2) which:

- accepts an arbitrary Python object as raw input;
- requires the top level to be an exact built-in ``dict``;
- requires every top-level key to be an exact built-in ``str``;
- requires the top-level field set to match ``BaffleGeometryRequest``
  exactly (Section 6.2 / 8.3);
- performs exact raw-type checks (no coercion, no subclass acceptance);
- refuses unknown / alias / duplicate field evidence refs;
- does not perform authority hashing, identity cross-binding, geometry,
  warnings, or final blocked-result assembly (Section 6.3).

Stage-1 failures are surfaced only through the internal
``BaffleGeometrySchemaFailure`` (Section 6.1) whose closed blockers are
frozen by Section 11. No public validation function is exposed.

This module owns ``BaffleGeometrySchemaFailure`` (Section 6.1). The class
is intentionally module-private and never exported.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final, Tuple

from hexagent.exchangers.shell_tube import models as _t020
from hexagent.exchangers.shell_tube.baffle_geometry import models as _t024
from hexagent.exchangers.shell_tube.shell_bundle_geometry import models as _t022
from hexagent.exchangers.shell_tube.tube_layout import models as _t021

# Section 6.1 schema constants.
REQUEST_SCHEMA_VERSION: Final[str] = "task024.baffle-geometry-request.v1"
AXIAL_SPAN_SCHEMA_VERSION: Final[str] = "task024.baffle-axial-span.v1"
DESIGN_AUTHORITY_SCHEMA_VERSION: Final[str] = _t024.DESIGN_AUTHORITY_SCHEMA_VERSION

# Section 11 closed Stage-1 blockers.
_BFG_SCHEMA_VERSION_UNSUPPORTED: Final[str] = "BFG_SCHEMA_VERSION_UNSUPPORTED"
_BFG_UNKNOWN_FIELD: Final[str] = "BFG_UNKNOWN_FIELD"
_BFG_RAW_TYPE_INVALID: Final[str] = "BFG_RAW_TYPE_INVALID"
_BFG_DECIMAL_LEXICAL_INVALID: Final[str] = "BFG_DECIMAL_LEXICAL_INVALID"
_BFG_AXIAL_SPAN_SCHEMA_UNSUPPORTED: Final[str] = "BFG_AXIAL_SPAN_SCHEMA_UNSUPPORTED"
_BFG_AXIAL_SPAN_EVIDENCE_MISSING: Final[str] = "BFG_AXIAL_SPAN_EVIDENCE_MISSING"
_BFG_DESIGN_AUTHORITY_SCHEMA_UNSUPPORTED: Final[str] = (
    "BFG_DESIGN_AUTHORITY_SCHEMA_UNSUPPORTED"
)
_BFG_DESIGN_AUTHORITY_EVIDENCE_MISSING: Final[str] = (
    "BFG_DESIGN_AUTHORITY_EVIDENCE_MISSING"
)
_BFG_TASK020_CONFIGURATION_MISSING: Final[str] = (
    "BFG_TASK020_CONFIGURATION_MISSING"
)
_BFG_TASK020_CONFIGURATION_INVALID: Final[str] = (
    "BFG_TASK020_CONFIGURATION_INVALID"
)
_BFG_TASK021_LAYOUT_MISSING: Final[str] = "BFG_TASK021_LAYOUT_MISSING"
_BFG_TASK021_LAYOUT_INVALID: Final[str] = "BFG_TASK021_LAYOUT_INVALID"
_BFG_TASK022_GEOMETRY_MISSING: Final[str] = "BFG_TASK022_GEOMETRY_MISSING"
_BFG_TASK022_GEOMETRY_INVALID: Final[str] = "BFG_TASK022_GEOMETRY_INVALID"

# Stage rank for the schema stage (Section 10).
_SCHEMA_STAGE_RANK: Final[int] = 1


class _FailureCollector:
    """Ordered blocker accumulator.

    Deterministic across all Stage-1 inputs: insertion order follows the
    canonical field-walk order defined below, never ``dict`` /
    ``set`` insertion order.
    """

    __slots__ = ("_entries",)

    def __init__(self) -> None:
        self._entries: list = []

    def add(self, code: str, field_path: str, raw_component: Any) -> None:
        self._entries.append((code, field_path, raw_component))

    def snapshot(self) -> Tuple:
        return tuple(self._entries)


class BaffleGeometrySchemaFailure(Exception):
    """Section 6.1 internal Stage-1 schema failure.

    Carries the closed-set blocker codes, ordered deterministic blocker
    list, the raw failing component, and the already-validated context.
    Has no geometry result and no time / host / environment identity.
    """

    __slots__ = ("stage_rank", "blockers", "raw_component", "validated_context")

    def __init__(self, blockers: Tuple, raw_component: Any,
                 validated_context: Mapping) -> None:
        super().__init__("BaffleGeometrySchemaFailure")
        self.stage_rank = _SCHEMA_STAGE_RANK
        self.blockers = tuple(blockers)
        self.raw_component = raw_component
        self.validated_context = dict(validated_context)


def _is_exact_dict(value: Any) -> bool:
    return type(value) is dict


def _is_exact_str(value: Any) -> bool:
    return type(value) is str


def _is_exact_list(value: Any) -> bool:
    return type(value) is list


def _is_exact_int(value: Any) -> bool:
    return type(value) is int


def _is_exact_bool(value: Any) -> bool:
    return type(value) is bool


def _is_decimal_lexical_string(value: Any) -> bool:
    if not _is_exact_str(value):
        return False
    if value != value.strip():
        return False
    if value.startswith("+"):
        return False
    if "e" in value or "E" in value:
        return False
    try:
        from decimal import Decimal

        d = Decimal(value)
    except Exception:
        return False
    return d.is_finite()


def _check_decimal_str_field(failure: _FailureCollector, field_path: str,
                             value: Any) -> bool:
    """Return ``True`` and do nothing when the value is a valid finite
    canonical decimal lexical string. Otherwise record a Stage-1 blocker
    and return ``False``."""
    if _is_exact_str(value) and _is_decimal_lexical_string(value):
        return True
    failure.add(_BFG_DECIMAL_LEXICAL_INVALID, field_path, value)
    failure.add(_BFG_RAW_TYPE_INVALID, field_path, value)
    return False


def _check_required_field(failure: _FailureCollector, field_path: str,
                          raw_dict: dict, key: str) -> bool:
    if key not in raw_dict:
        failure.add(_BFG_UNKNOWN_FIELD, field_path, raw_dict)
        return False
    return True


def _check_no_extra_fields(failure: _FailureCollector, field_path: str,
                           raw_dict: dict, expected_keys: frozenset) -> bool:
    ok = True
    for k in raw_dict:
        if not _is_exact_str(k):
            failure.add(_BFG_UNKNOWN_FIELD, field_path, k)
            failure.add(_BFG_RAW_TYPE_INVALID, field_path, k)
            ok = False
            continue
        if k not in expected_keys:
            failure.add(_BFG_UNKNOWN_FIELD, field_path, k)
            ok = False
    return ok


def _check_evidence_refs_tuple(failure: _FailureCollector, field_path: str,
                               value: Any,
                               require_non_empty: bool = True) -> bool:
    """Validate evidence_refs: exact tuple of non-empty exact strings,
    lexicographically sorted, duplicate-free.

    Accepts an exact ``list`` of exact ``str`` inputs (raw) and rejects
    ``tuple`` subclasses, custom iterables, etc.
    """
    items = value
    if not _is_exact_list(items):
        failure.add(_BFG_RAW_TYPE_INVALID, field_path, value)
        return False
    if require_non_empty and len(items) == 0:
        failure.add(_BFG_UNKNOWN_FIELD, field_path, value)
        return False
    seen: list = []
    seen_set: set = set()
    ok = True
    for i, item in enumerate(items):
        item_path = f"{field_path}[{i}]"
        if not _is_exact_str(item):
            failure.add(_BFG_RAW_TYPE_INVALID, item_path, item)
            ok = False
            continue
        if item == "":
            failure.add(_BFG_UNKNOWN_FIELD, item_path, item)
            ok = False
            continue
        if item in seen_set:
            failure.add(_BFG_UNKNOWN_FIELD, item_path, item)
            ok = False
            continue
        seen.append(item)
        seen_set.add(item)
    if not ok:
        return False
    if list(items) != sorted(items):
        failure.add(_BFG_UNKNOWN_FIELD, field_path, value)
        return False
    return True


def _check_authority_dict(failure: _FailureCollector, field_path: str,
                          value: Any, expected_schema_version: str,
                          expected_keys: frozenset,
                          blocker_missing_evidence: str,
                          blocker_schema_unsupported: str,
                          required_decimal_fields: tuple = (),
                          min_decimal: str | None = None) -> bool:
    """Validate a TASK-024 caller-supplied authority object literal:

    - exact ``dict``;
    - exact ``str`` keys;
    - exact schema_version matching ``expected_schema_version``;
    - exact required field set (every key in ``expected_keys`` must
      exist; no extra keys allowed);
    - listed decimal fields must be canonical decimal strings;
    - ``min_decimal`` (if given) is applied to a closed rule: the value
      must be ``>= min_decimal`` under the closed lexical comparison
      and satisfy domain / sign rules.

    Returns ``True`` only when every check passes.
    """
    if not _is_exact_dict(value):
        failure.add(_BFG_RAW_TYPE_INVALID, field_path, value)
        return False
    if not _check_no_extra_fields(failure, field_path, value, expected_keys):
        pass

    # ``schema_version`` must exist and match exactly.
    if not _check_required_field(failure, field_path, value, "schema_version"):
        return False
    sv = value["schema_version"]
    if not _is_exact_str(sv):
        failure.add(_BFG_RAW_TYPE_INVALID, f"{field_path}.schema_version", sv)
        return False
    if sv != expected_schema_version:
        failure.add(blocker_schema_unsupported, f"{field_path}.schema_version", sv)
        return False

    # ``evidence_refs`` must be present, non-empty, sorted, dup-free.
    if not _check_required_field(failure, field_path, value, "evidence_refs"):
        failure.add(blocker_missing_evidence, f"{field_path}.evidence_refs", value)
        return False
    if not _check_evidence_refs_tuple(failure, f"{field_path}.evidence_refs",
                                      value["evidence_refs"], require_non_empty=True):
        failure.add(blocker_missing_evidence, f"{field_path}.evidence_refs",
                    value["evidence_refs"])
        return False

    # Required decimal fields.
    for dfield in required_decimal_fields:
        if not _check_required_field(failure, field_path, value, dfield):
            return False
        if not _check_decimal_str_field(
                failure, f"{field_path}.{dfield}",
                value[dfield]):
            return False

    # Min-decimal exclusion rule (closed lexical compare).
    if min_decimal is not None:
        for dfield in required_decimal_fields:
            if dfield == min_decimal[0]:
                v_str = value.get(dfield)
                if _is_exact_str(v_str) and _is_decimal_lexical_string(v_str):
                    from decimal import Decimal

                    if Decimal(v_str) < Decimal(min_decimal[1]):
                        failure.add(_BFG_DECIMAL_LEXICAL_INVALID,
                                    f"{field_path}.{dfield}", v_str)
                        return False
                break

    # Ensure all expected_keys are present (extra handled above).
    missing = False
    for ek in expected_keys:
        if ek not in value:
            failure.add(_BFG_UNKNOWN_FIELD, f"{field_path}.{ek}", value)
            missing = True
    if missing:
        return False
    return True


def _check_upstream_instance(failure: _FailureCollector, field_path: str,
                             value: Any, expected_type, blocker_missing: str,
                             blocker_invalid: str) -> bool:
    """Verify ``value`` is the exact upstream public model instance."""
    if value is None:
        failure.add(blocker_missing, field_path, value)
        return False
    if type(value) is not expected_type:
        failure.add(blocker_invalid, field_path, value)
        failure.add(_BFG_RAW_TYPE_INVALID, field_path, value)
        return False
    return True


_REQUEST_KEYS: Final[frozenset] = frozenset((
    "schema_version", "configuration", "tube_layout", "shell_bundle_geometry",
    "axial_span", "design_authority", "evidence_refs",
))

_AXIAL_SPAN_KEYS: Final[frozenset] = frozenset((
    "schema_version", "axial_start_coordinate_m", "axial_end_coordinate_m",
    "evidence_refs", "authority_hash",
))


def _parse_request_with_collector(raw_request, failure: _FailureCollector,
                                  validated: dict):
    """Append Stage-1 findings to ``failure`` and update ``validated`` with
    any partial recognized structures. Never raises.

    Returns the ``validated`` dict on success and ``None`` on failure.
    """
    # Top-level must be an exact ``dict``.
    if not _is_exact_dict(raw_request):
        failure.add(_BFG_RAW_TYPE_INVALID, ".", raw_request)
        return None
    if not _check_no_extra_fields(failure, "", raw_request, _REQUEST_KEYS):
        pass
    for k in _REQUEST_KEYS:
        if k not in raw_request:
            failure.add(_BFG_UNKNOWN_FIELD, f".{k}", raw_request)
    if failure.snapshot():
        return None

    # ``schema_version`` must equal REQUEST_SCHEMA_VERSION.
    sv = raw_request["schema_version"]
    if not _is_exact_str(sv):
        failure.add(_BFG_RAW_TYPE_INVALID, ".schema_version", sv)
        return None
    if sv != REQUEST_SCHEMA_VERSION:
        failure.add(_BFG_SCHEMA_VERSION_UNSUPPORTED, ".schema_version", sv)
        return None

    # Upstream instances: exact-type only.
    cfg = raw_request["configuration"]
    if not _check_upstream_instance(failure, ".configuration", cfg,
                                    _t020.ShellAndTubeConfiguration,
                                    _BFG_TASK020_CONFIGURATION_MISSING,
                                    _BFG_TASK020_CONFIGURATION_INVALID):
        return None
    validated["configuration"] = cfg

    layout = raw_request["tube_layout"]
    if not _check_upstream_instance(failure, ".tube_layout", layout,
                                    _t021.TubeLayout,
                                    _BFG_TASK021_LAYOUT_MISSING,
                                    _BFG_TASK021_LAYOUT_INVALID):
        return None
    validated["tube_layout"] = layout

    bundle = raw_request["shell_bundle_geometry"]
    if not _check_upstream_instance(failure, ".shell_bundle_geometry", bundle,
                                    _t022.ShellBundleGeometry,
                                    _BFG_TASK022_GEOMETRY_MISSING,
                                    _BFG_TASK022_GEOMETRY_INVALID):
        return None
    validated["shell_bundle_geometry"] = bundle

    # Axial span.
    axial_dict = raw_request["axial_span"]
    if not _check_authority_dict(
            failure, ".axial_span", axial_dict,
            AXIAL_SPAN_SCHEMA_VERSION, _AXIAL_SPAN_KEYS,
            _BFG_AXIAL_SPAN_EVIDENCE_MISSING,
            _BFG_AXIAL_SPAN_SCHEMA_UNSUPPORTED,
            required_decimal_fields=("axial_start_coordinate_m",
                                     "axial_end_coordinate_m"),
            min_decimal=None):
        return None
    validated["axial_span_raw"] = axial_dict

    # Design authority has additional fields beyond the authority_dict
    # template (baffle_type / baffle_count / baffle_thickness_m /
    # spacing_sequence_m / baffle_cut_fraction / orientation_sequence /
    # shell_to_baffle_diametral_clearance_m /
    # tube_to_baffle_hole_diametral_clearance_m / authority_hash).
    # Perform a focused Stage-1 raw-type check separately.
    da = raw_request["design_authority"]
    if not _is_exact_dict(da):
        failure.add(_BFG_RAW_TYPE_INVALID, ".design_authority", da)
        return None
    _DESIGN_AUTHORITY_KEYS = frozenset((
        "schema_version", "baffle_type", "baffle_count", "baffle_thickness_m",
        "spacing_sequence_m", "baffle_cut_fraction", "orientation_sequence",
        "shell_to_baffle_diametral_clearance_m",
        "tube_to_baffle_hole_diametral_clearance_m", "evidence_refs",
        "authority_hash",
    ))
    if not _check_no_extra_fields(failure, ".design_authority",
                                  da, _DESIGN_AUTHORITY_KEYS):
        pass
    for k in _DESIGN_AUTHORITY_KEYS:
        if k not in da:
            failure.add(_BFG_UNKNOWN_FIELD, f".design_authority.{k}", da)
    if not _is_exact_str(da.get("schema_version")):
        failure.add(_BFG_RAW_TYPE_INVALID, ".design_authority.schema_version",
                    da.get("schema_version"))
    elif da["schema_version"] != DESIGN_AUTHORITY_SCHEMA_VERSION:
        failure.add(_BFG_DESIGN_AUTHORITY_SCHEMA_UNSUPPORTED,
                    ".design_authority.schema_version",
                    da["schema_version"])
    # evidence_refs
    if "evidence_refs" not in da:
        failure.add(_BFG_DESIGN_AUTHORITY_EVIDENCE_MISSING,
                    ".design_authority.evidence_refs", da)
    elif not _check_evidence_refs_tuple(
            failure, ".design_authority.evidence_refs", da["evidence_refs"]):
        failure.add(_BFG_DESIGN_AUTHORITY_EVIDENCE_MISSING,
                    ".design_authority.evidence_refs", da["evidence_refs"])
    # baffle_type must be exact TASK-024 public enum instance.
    bt = da.get("baffle_type")
    if type(bt) is not _t024.BaffleType:
        failure.add(_BFG_RAW_TYPE_INVALID, ".design_authority.baffle_type", bt)
    else:
        if bt is not _t024.BaffleType.SINGLE_SEGMENTAL:
            failure.add(_BFG_UNKNOWN_FIELD,
                        ".design_authority.baffle_type", bt)
    # baffle_count: exact int >= 1, NOT bool.
    bc = da.get("baffle_count")
    if type(bc) is bool or not _is_exact_int(bc):
        failure.add(_BFG_RAW_TYPE_INVALID,
                    ".design_authority.baffle_count", bc)
    elif bc < 1:
        failure.add(_BFG_UNKNOWN_FIELD,
                    ".design_authority.baffle_count", bc)
    # baffle_thickness_m: canonical decimal string, > 0
    if not _check_decimal_str_field(
            failure, ".design_authority.baffle_thickness_m",
            da.get("baffle_thickness_m")):
        pass
    else:
        from decimal import Decimal as _D
        if _D(da["baffle_thickness_m"]) <= 0:
            failure.add(_BFG_DECIMAL_LEXICAL_INVALID,
                        ".design_authority.baffle_thickness_m",
                        da["baffle_thickness_m"])
    # baffle_cut_fraction: canonical decimal string, 0 < x < 1
    bcf = da.get("baffle_cut_fraction")
    if not _check_decimal_str_field(
            failure, ".design_authority.baffle_cut_fraction", bcf):
        pass
    else:
        from decimal import Decimal as _D2
        if not (0 < _D2(bcf) < 1):
            failure.add(_BFG_DECIMAL_LEXICAL_INVALID,
                        ".design_authority.baffle_cut_fraction", bcf)
    # shell_to_baffle_diametral_clearance_m / tube_to_baffle_hole_diametral_clearance_m
    # canonical decimal, >= 0
    for cfield in (
            "shell_to_baffle_diametral_clearance_m",
            "tube_to_baffle_hole_diametral_clearance_m"):
        cv = da.get(cfield)
        if not _check_decimal_str_field(
                failure, f".design_authority.{cfield}", cv):
            continue
        from decimal import Decimal as _D3
        if _D3(cv) < 0:
            failure.add(_BFG_DECIMAL_LEXICAL_INVALID,
                        f".design_authority.{cfield}", cv)
    # authority_hash: canonical SHA-256 hex, 64 lowercase hex chars
    ah = da.get("authority_hash")
    if not _is_exact_str(ah) or len(ah) != 64 or any(c not in "0123456789abcdef"
                                                     for c in ah):
        failure.add(_BFG_RAW_TYPE_INVALID,
                    ".design_authority.authority_hash", ah)
    # spacing_sequence_m: tuple of canonical decimal strings, all positive,
    # semantic order, non-empty, ordered.
    ssm = da.get("spacing_sequence_m")
    if not _is_exact_list(ssm):
        failure.add(_BFG_RAW_TYPE_INVALID,
                    ".design_authority.spacing_sequence_m", ssm)
    else:
        if len(ssm) == 0:
            failure.add(_BFG_UNKNOWN_FIELD,
                        ".design_authority.spacing_sequence_m", ssm)
        seq_ok = True
        prev_ssm = None
        from decimal import Decimal as _D4
        for i, item in enumerate(ssm):
            ipath = f".design_authority.spacing_sequence_m[{i}]"
            if not _check_decimal_str_field(failure, ipath, item):
                seq_ok = False
                continue
            if _D4(item) <= 0:
                failure.add(_BFG_DECIMAL_LEXICAL_INVALID, ipath, item)
                seq_ok = False
                continue
            if prev_ssm is not None:
                if list(ssm) != sorted(ssm):
                    failure.add(_BFG_UNKNOWN_FIELD,
                                ".design_authority.spacing_sequence_m", ssm)
                    seq_ok = False
                    break
            prev_ssm = item
        # Sort-order assertion repeated exactly once for closure.
        if seq_ok and list(ssm) != sorted(ssm):
            failure.add(_BFG_UNKNOWN_FIELD,
                        ".design_authority.spacing_sequence_m", ssm)
    # orientation_sequence: tuple of exact BaffleOrientation, length == baffle_count
    oseq = da.get("orientation_sequence")
    if not _is_exact_list(oseq):
        failure.add(_BFG_RAW_TYPE_INVALID,
                    ".design_authority.orientation_sequence", oseq)
    else:
        oseq_ok = True
        if type(bc) is int and not isinstance(bc, bool) and len(oseq) != bc:
            failure.add(_BFG_UNKNOWN_FIELD,
                        ".design_authority.orientation_sequence", oseq)
            oseq_ok = False
        for i, item in enumerate(oseq):
            if type(item) is not _t024.BaffleOrientation:
                failure.add(_BFG_RAW_TYPE_INVALID,
                            f".design_authority.orientation_sequence[{i}]",
                            item)
                oseq_ok = False
    # final missing check
    if failure.snapshot():
        return None
    validated["design_authority_raw"] = da
    # evidence_refs at top-level (request): tuple form required
    if not _check_required_field(failure, "", raw_request, "evidence_refs"):
        return None
    if not _check_evidence_refs_tuple(
            failure, ".evidence_refs", raw_request["evidence_refs"]):
        return None
    if failure.snapshot():
        return None

    # Build frozen BaffleGeometryRequest preserving the upstream instances.
    return _t024.BaffleGeometryRequest(
        schema_version=raw_request["schema_version"],
        configuration=cfg,
        tube_layout=layout,
        shell_bundle_geometry=bundle,
        axial_span=_t024.CallerSuppliedBaffleAxialSpan(
            schema_version=axial_dict["schema_version"],
            axial_start_coordinate_m=axial_dict["axial_start_coordinate_m"],
            axial_end_coordinate_m=axial_dict["axial_end_coordinate_m"],
            evidence_refs=tuple(axial_dict["evidence_refs"]),
            authority_hash=axial_dict["authority_hash"],
        ),
        design_authority=_t024.CallerSuppliedBaffleDesignAuthority(
            schema_version=da["schema_version"],
            baffle_type=da["baffle_type"],
            baffle_count=da["baffle_count"],
            baffle_thickness_m=da["baffle_thickness_m"],
            spacing_sequence_m=tuple(da["spacing_sequence_m"]),
            baffle_cut_fraction=da["baffle_cut_fraction"],
            orientation_sequence=tuple(da["orientation_sequence"]),
            shell_to_baffle_diametral_clearance_m=da[
                "shell_to_baffle_diametral_clearance_m"
            ],
            tube_to_baffle_hole_diametral_clearance_m=da[
                "tube_to_baffle_hole_diametral_clearance_m"
            ],
            evidence_refs=tuple(da["evidence_refs"]),
            authority_hash=da["authority_hash"],
        ),
        evidence_refs=tuple(raw_request["evidence_refs"]),
    )


def parse_request(raw_request: Any) -> _t024.BaffleGeometryRequest:
    """Stage-1 strict raw parser (Section 6.2 / 8.3).

    Returns an immutable ``BaffleGeometryRequest`` on success.

    Raises ``BaffleGeometrySchemaFailure`` on Stage-1 failure. The
    exception carries only the closed-set blockers, the raw failing
    component, and the already-validated context. No geometry result
    leaks through this boundary.
    """
    failure = _FailureCollector()
    validated: dict = {}
    parsed = _parse_request_with_collector(raw_request, failure, validated)
    if parsed is None:
        blockers = failure.snapshot()
        raw_component = raw_request
        raise BaffleGeometrySchemaFailure(
            blockers=blockers,
            raw_component=raw_component,
            validated_context=validated,
        )
    return parsed


__all__ = (
    "BaffleGeometrySchemaFailure",
    "parse_request",
)
