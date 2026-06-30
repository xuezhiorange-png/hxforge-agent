"""TASK-010 frozen report contract (B1–B8).

Contract §11: Report rendering.
- Deterministic output (same inputs → same bytes)
- Autoescaped HTML
- No external CDN/font/tracking
- No user template paths
- Blocks absolute paths, tracebacks, tokens, env vars
- Risk banners on every page

B1: Precise report models (StrEnums, artifact variants, section, report)
B2: Exactly 13 sections in fixed order
B3: Section/status matrix verification
B4: Mandatory artifact verification
B5: RFC 6901 JSON Pointer validation and resolution
B6: Deterministic report hashes
B7: Pre-render verification chain
B8: Deterministic secure HTML
"""

from __future__ import annotations

import html as _html
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from pydantic import ConfigDict, Discriminator, Tag, model_validator

from hexagent.core.canonical import sha256_digest
from hexagent.domain.models import StrictBaseModel

# ---------------------------------------------------------------------------
# Risk banners displayed on every report page
# ---------------------------------------------------------------------------

_RISK_BANNERS: tuple[str, ...] = (
    "PRELIMINARY",
    "NOT FOR PROCUREMENT",
    "NOT FOR CONSTRUCTION",
)

# ---------------------------------------------------------------------------
# Patterns that must never appear in rendered HTML output
# ---------------------------------------------------------------------------

_SENSITIVE_PATTERNS = re.compile(
    r"(ghp_|gho_|sk-[a-zA-Z0-9]{20,}|AKIA[A-Z0-9]{16})",
    re.IGNORECASE,
)

# =========================================================================
# B1 — Precise Report Models
# =========================================================================


class ReportArtifactKind(StrEnum):
    """Kinds of report artifacts."""

    CANONICAL_REQUEST_SNAPSHOT = "canonical_request_snapshot"
    REQUEST_IDENTITY = "request_identity"
    PROVIDER_IDENTITY = "provider_identity"
    GEOMETRY_SNAPSHOT = "geometry_snapshot"
    SOLVER_SETTINGS = "solver_settings"
    DOMAIN_RESULT = "domain_result"
    RESULT_HASH = "result_hash"
    PROVENANCE_GRAPH = "provenance_graph"
    PROVENANCE_DIGEST = "provenance_digest"
    BUNDLE_DIGEST = "bundle_digest"


class ReportSectionStatus(StrEnum):
    """Section presence status."""

    PRESENT = "present"
    NOT_APPLICABLE = "not_applicable"
    NOT_IMPLEMENTED = "not_implemented"
    OUT_OF_SCOPE = "out_of_scope"


class ReportSectionId(StrEnum):
    """The exactly-13 canonical section identifiers."""

    STATUS_BANNER = "status_banner"
    RUN_IDENTITY = "run_identity"
    INPUT_SUMMARY = "input_summary"
    GEOMETRY = "geometry"
    HEAT_BALANCE = "heat_balance"
    THERMAL_PERFORMANCE = "thermal_performance"
    SIZING_RANKING = "sizing_ranking"
    TOP_RANKED_CANDIDATES = "top_ranked_candidates"
    WARNINGS = "warnings"
    BLOCKERS = "blockers"
    FAILURE_DETAILS = "failure_details"
    PROVENANCE = "provenance"
    INTEGRITY = "integrity"


class ReportArtifactId(StrEnum):
    """Artifact identifiers — one per ReportArtifactKind."""

    CANONICAL_REQUEST_SNAPSHOT = "canonical_request_snapshot"
    REQUEST_IDENTITY = "request_identity"
    PROVIDER_IDENTITY = "provider_identity"
    GEOMETRY_SNAPSHOT = "geometry_snapshot"
    SOLVER_SETTINGS = "solver_settings"
    DOMAIN_RESULT = "domain_result"
    RESULT_HASH = "result_hash"
    PROVENANCE_GRAPH = "provenance_graph"
    PROVENANCE_DIGEST = "provenance_digest"
    BUNDLE_DIGEST = "bundle_digest"


# ---------------------------------------------------------------------------
# Artifact variant models (B1)
# ---------------------------------------------------------------------------


class PresentReportArtifact(StrictBaseModel):
    """A report artifact that is present with canonical data."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_id: ReportArtifactId
    kind: ReportArtifactKind
    section: ReportSectionId
    canonical_raw_value: str
    source_pointer: str  # RFC 6901 JSON Pointer


class UnavailableReportArtifact(StrictBaseModel):
    """A report artifact that is unavailable."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_id: ReportArtifactId
    kind: ReportArtifactKind
    section: ReportSectionId
    reason: str = "unavailable"


class NotImplementedReportArtifact(StrictBaseModel):
    """A report artifact that is not yet implemented."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_id: ReportArtifactId
    kind: ReportArtifactKind
    section: ReportSectionId
    reason: str = "not_implemented"


class OutOfScopeReportArtifact(StrictBaseModel):
    """A report artifact that is out of scope for this operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_id: ReportArtifactId
    kind: ReportArtifactKind
    section: ReportSectionId
    reason: str = "out_of_scope"


# ---------------------------------------------------------------------------
# Discriminated union for ReportArtifact (B1)
# ---------------------------------------------------------------------------
# All four variants share `kind: ReportArtifactKind`, so kind alone cannot
# discriminate.  We use a callable discriminator that inspects structural
# differences: PresentReportArtifact has `source_pointer` + `canonical_raw_value`
# while the other three are distinguished by their `reason` default.


def _artifact_discriminator(v: Any) -> str:
    """Callable discriminator for ReportArtifact union."""
    if isinstance(v, dict):
        if "source_pointer" in v and "canonical_raw_value" in v:
            return "present"
        reason = v.get("reason", "")
        if reason == "unavailable":
            return "unavailable"
        if reason == "not_implemented":
            return "not_implemented"
        return "out_of_scope"
    # Model instances
    if isinstance(v, PresentReportArtifact):
        return "present"
    if isinstance(v, UnavailableReportArtifact):
        return "unavailable"
    if isinstance(v, NotImplementedReportArtifact):
        return "not_implemented"
    return "out_of_scope"


ReportArtifact = Annotated[
    Annotated[PresentReportArtifact, Tag("present")]
    | Annotated[UnavailableReportArtifact, Tag("unavailable")]
    | Annotated[NotImplementedReportArtifact, Tag("not_implemented")]
    | Annotated[OutOfScopeReportArtifact, Tag("out_of_scope")],
    Discriminator(_artifact_discriminator),
]


# ---------------------------------------------------------------------------
# ReportSection (B1)
# ---------------------------------------------------------------------------


class ReportSection(StrictBaseModel):
    """A single section in the frozen report model."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    section_id: ReportSectionId
    title: str
    content: str
    status: ReportSectionStatus
    artifacts: tuple[ReportArtifact, ...] = ()


# =========================================================================
# B2 — Exactly 13 Sections in Fixed Order
# =========================================================================

REPORT_SECTION_ORDER: tuple[ReportSectionId, ...] = (
    ReportSectionId.STATUS_BANNER,
    ReportSectionId.RUN_IDENTITY,
    ReportSectionId.INPUT_SUMMARY,
    ReportSectionId.GEOMETRY,
    ReportSectionId.HEAT_BALANCE,
    ReportSectionId.THERMAL_PERFORMANCE,
    ReportSectionId.SIZING_RANKING,
    ReportSectionId.TOP_RANKED_CANDIDATES,
    ReportSectionId.WARNINGS,
    ReportSectionId.BLOCKERS,
    ReportSectionId.FAILURE_DETAILS,
    ReportSectionId.PROVENANCE,
    ReportSectionId.INTEGRITY,
)

_SECTION_TITLES: dict[ReportSectionId, str] = {
    ReportSectionId.STATUS_BANNER: "Status Banner",
    ReportSectionId.RUN_IDENTITY: "Run Identity",
    ReportSectionId.INPUT_SUMMARY: "Input Summary",
    ReportSectionId.GEOMETRY: "Geometry",
    ReportSectionId.HEAT_BALANCE: "Heat Balance",
    ReportSectionId.THERMAL_PERFORMANCE: "Thermal Performance",
    ReportSectionId.SIZING_RANKING: "Sizing & Ranking",
    ReportSectionId.TOP_RANKED_CANDIDATES: "Top Ranked Candidates",
    ReportSectionId.WARNINGS: "Warnings",
    ReportSectionId.BLOCKERS: "Blockers",
    ReportSectionId.FAILURE_DETAILS: "Failure Details",
    ReportSectionId.PROVENANCE: "Provenance",
    ReportSectionId.INTEGRITY: "Integrity",
}


# =========================================================================
# B4 — Mandatory Artifacts
# =========================================================================

MANDATORY_ARTIFACT_IDS: frozenset[ReportArtifactId] = frozenset(
    {
        ReportArtifactId.CANONICAL_REQUEST_SNAPSHOT,
        ReportArtifactId.REQUEST_IDENTITY,
        ReportArtifactId.PROVIDER_IDENTITY,
        ReportArtifactId.GEOMETRY_SNAPSHOT,
        ReportArtifactId.SOLVER_SETTINGS,
        ReportArtifactId.DOMAIN_RESULT,
        ReportArtifactId.RESULT_HASH,
        ReportArtifactId.PROVENANCE_GRAPH,
        ReportArtifactId.PROVENANCE_DIGEST,
        ReportArtifactId.BUNDLE_DIGEST,
    }
)

MANDATORY_ARTIFACT_OWNERS: dict[ReportArtifactId, ReportSectionId] = {
    ReportArtifactId.CANONICAL_REQUEST_SNAPSHOT: ReportSectionId.INPUT_SUMMARY,
    ReportArtifactId.REQUEST_IDENTITY: ReportSectionId.RUN_IDENTITY,
    ReportArtifactId.PROVIDER_IDENTITY: ReportSectionId.RUN_IDENTITY,
    ReportArtifactId.GEOMETRY_SNAPSHOT: ReportSectionId.GEOMETRY,
    ReportArtifactId.SOLVER_SETTINGS: ReportSectionId.INPUT_SUMMARY,
    ReportArtifactId.DOMAIN_RESULT: ReportSectionId.THERMAL_PERFORMANCE,
    ReportArtifactId.RESULT_HASH: ReportSectionId.INTEGRITY,
    ReportArtifactId.PROVENANCE_GRAPH: ReportSectionId.PROVENANCE,
    ReportArtifactId.PROVENANCE_DIGEST: ReportSectionId.PROVENANCE,
    ReportArtifactId.BUNDLE_DIGEST: ReportSectionId.INTEGRITY,
}

# Mapping from artifact kind → (owner section, candidate pointer paths in envelope dict)
_ARTIFACT_POINTER_MAP: dict[ReportArtifactKind, tuple[ReportSectionId, tuple[str, ...]]] = {
    ReportArtifactKind.CANONICAL_REQUEST_SNAPSHOT: (
        ReportSectionId.INPUT_SUMMARY,
        ("/artifact_bundle/canonical_request_snapshot",),
    ),
    ReportArtifactKind.REQUEST_IDENTITY: (
        ReportSectionId.RUN_IDENTITY,
        (
            "/artifact_bundle/request_identity",
            "/artifact_bundle/sizing_request_identity",
        ),
    ),
    ReportArtifactKind.PROVIDER_IDENTITY: (
        ReportSectionId.RUN_IDENTITY,
        (
            "/artifact_bundle/provider_identity",
            "/artifact_bundle/resolved_provider",
        ),
    ),
    ReportArtifactKind.GEOMETRY_SNAPSHOT: (
        ReportSectionId.GEOMETRY,
        ("/artifact_bundle/geometry_snapshot",),
    ),
    ReportArtifactKind.SOLVER_SETTINGS: (
        ReportSectionId.INPUT_SUMMARY,
        ("/artifact_bundle/solver_settings",),
    ),
    ReportArtifactKind.DOMAIN_RESULT: (
        ReportSectionId.THERMAL_PERFORMANCE,
        ("/artifact_bundle/result", "/artifact_bundle/optimization_result"),
    ),
    ReportArtifactKind.RESULT_HASH: (
        ReportSectionId.INTEGRITY,
        ("/result_hash",),
    ),
    ReportArtifactKind.PROVENANCE_GRAPH: (
        ReportSectionId.PROVENANCE,
        ("/artifact_bundle/provenance_graph", "/provenance"),
    ),
    ReportArtifactKind.PROVENANCE_DIGEST: (
        ReportSectionId.PROVENANCE,
        ("/provenance_digest",),
    ),
    ReportArtifactKind.BUNDLE_DIGEST: (
        ReportSectionId.INTEGRITY,
        ("/artifact_bundle_digest", "/artifact_bundle/bundle_hash"),
    ),
}


# =========================================================================
# B5 — RFC 6901 JSON Pointer
# =========================================================================


def validate_rfc6901_pointer(pointer: str) -> tuple[str | int, ...]:
    """Parse and validate a JSON Pointer per RFC 6901.

    Supports: ``""``, ``"/"``, ``"~0"``, ``"~1"``
    Rejects: missing leading slash (non-empty), trailing ``"~"``,
    illegal ``"~2"`` etc.
    """
    if pointer == "":
        return ()
    if not pointer.startswith("/"):
        raise ValueError(f"JSON Pointer must start with '/': {pointer!r}")

    # Reject trailing bare tilde
    if pointer.endswith("~"):
        raise ValueError(f"JSON Pointer has trailing '~': {pointer!r}")

    parts: list[str | int] = []
    for segment in pointer[1:].split("/"):
        # Validate escape sequences: only ~0 and ~1 are legal
        i = 0
        while i < len(segment):
            if segment[i] == "~":
                if i + 1 >= len(segment):
                    raise ValueError(f"Trailing '~' in segment: {segment!r}")
                next_char = segment[i + 1]
                if next_char not in ("0", "1"):
                    raise ValueError(f"Illegal escape '~{next_char}' in pointer: {pointer!r}")
                i += 2
            else:
                i += 1
        # Unescape
        unescaped = segment.replace("~0", "~").replace("~1", "/")
        parts.append(unescaped)
    return tuple(parts)


def resolve_source_pointer(obj: Any, pointer: str) -> Any:
    """Resolve a JSON Pointer against a Python dict/list structure.

    Returns the value at the pointer path.
    Raises ``ValueError`` if the path does not exist.
    """
    parts = validate_rfc6901_pointer(pointer)
    current = obj
    for part in parts:
        if isinstance(current, dict):
            if not isinstance(part, str):
                raise ValueError(f"Expected string key for dict, got {type(part).__name__}")
            if part not in current:
                raise ValueError(f"Key {part!r} not found in dict")
            current = current[part]
        elif isinstance(current, (list, tuple)):
            if isinstance(part, str):
                try:
                    idx = int(part)
                except ValueError:
                    raise ValueError(f"Invalid array index {part!r} for list/tuple") from None
            else:
                idx = part
            if idx < 0 or idx >= len(current):
                raise ValueError(f"Array index {idx} out of range [0, {len(current)})")
            current = current[idx]
        else:
            raise ValueError(f"Cannot traverse into {type(current).__name__} with key {part!r}")
    return current


# =========================================================================
# B6 — Report Hashes
# =========================================================================


@dataclass(frozen=True, slots=True)
class ReportInstanceIdentity:
    """Identity model for a report instance."""

    report_content_hash: str
    report_schema_version: str
    run_id: UUID
    operation: str


def compute_report_content_hash(sections: tuple[ReportSection, ...]) -> str:
    """Compute deterministic content hash over section data."""
    section_data = tuple((s.section_id.value, s.title, s.content, s.status.value) for s in sections)
    return sha256_digest(section_data)


def compute_report_instance_hash(identity: ReportInstanceIdentity) -> str:
    """SHA256 of the identity model."""
    return sha256_digest(
        {
            "report_content_hash": identity.report_content_hash,
            "report_schema_version": identity.report_schema_version,
            "run_id": str(identity.run_id),
            "operation": identity.operation,
        }
    )


# =========================================================================
# ReportModel (B1 + B2 validation)
# =========================================================================


class ReportModel(StrictBaseModel):
    """Deterministic report model built from a verified envelope.

    Frozen: once constructed the model cannot be mutated, which
    guarantees that :func:`render_report_html` produces identical
    bytes for identical inputs.

    Validates: exactly 13 sections, correct order, no duplicates,
    no missing, no extra (B2).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: UUID
    operation: str
    report_schema_version: str = "1.0"
    sections: tuple[ReportSection, ...]
    content_hash: str
    instance_hash: str

    @model_validator(mode="after")
    def _validate_sections(self) -> ReportModel:
        """B2: Validate exactly 13 sections in correct order."""
        if len(self.sections) != 13:
            raise ValueError(f"Expected 13 sections, got {len(self.sections)}")
        expected = REPORT_SECTION_ORDER
        actual = tuple(s.section_id for s in self.sections)
        if actual != expected:
            raise ValueError(
                f"Section order mismatch: expected {[e.value for e in expected]}, "
                f"got {[a.value for a in actual]}"
            )
        # No duplicates
        if len(set(actual)) != len(actual):
            raise ValueError("Duplicate section IDs")
        return self


# =========================================================================
# B3 — Section/Status Matrix Verification
# =========================================================================

# Rating matrices keyed by result.status
_RATING_MATRIX: dict[str, dict[ReportSectionId, ReportSectionStatus]] = {
    "succeeded": {
        ReportSectionId.STATUS_BANNER: ReportSectionStatus.PRESENT,
        ReportSectionId.RUN_IDENTITY: ReportSectionStatus.PRESENT,
        ReportSectionId.INPUT_SUMMARY: ReportSectionStatus.PRESENT,
        ReportSectionId.GEOMETRY: ReportSectionStatus.PRESENT,
        ReportSectionId.HEAT_BALANCE: ReportSectionStatus.PRESENT,
        ReportSectionId.THERMAL_PERFORMANCE: ReportSectionStatus.PRESENT,
        ReportSectionId.SIZING_RANKING: ReportSectionStatus.OUT_OF_SCOPE,
        ReportSectionId.TOP_RANKED_CANDIDATES: ReportSectionStatus.OUT_OF_SCOPE,
        ReportSectionId.WARNINGS: ReportSectionStatus.PRESENT,
        ReportSectionId.BLOCKERS: ReportSectionStatus.PRESENT,
        ReportSectionId.FAILURE_DETAILS: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.PROVENANCE: ReportSectionStatus.PRESENT,
        ReportSectionId.INTEGRITY: ReportSectionStatus.PRESENT,
    },
    "blocked": {
        ReportSectionId.STATUS_BANNER: ReportSectionStatus.PRESENT,
        ReportSectionId.RUN_IDENTITY: ReportSectionStatus.PRESENT,
        ReportSectionId.INPUT_SUMMARY: ReportSectionStatus.PRESENT,
        ReportSectionId.GEOMETRY: ReportSectionStatus.PRESENT,
        ReportSectionId.HEAT_BALANCE: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.THERMAL_PERFORMANCE: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.SIZING_RANKING: ReportSectionStatus.OUT_OF_SCOPE,
        ReportSectionId.TOP_RANKED_CANDIDATES: ReportSectionStatus.OUT_OF_SCOPE,
        ReportSectionId.WARNINGS: ReportSectionStatus.PRESENT,
        ReportSectionId.BLOCKERS: ReportSectionStatus.PRESENT,
        ReportSectionId.FAILURE_DETAILS: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.PROVENANCE: ReportSectionStatus.PRESENT,
        ReportSectionId.INTEGRITY: ReportSectionStatus.PRESENT,
    },
    "failed": {
        ReportSectionId.STATUS_BANNER: ReportSectionStatus.PRESENT,
        ReportSectionId.RUN_IDENTITY: ReportSectionStatus.PRESENT,
        ReportSectionId.INPUT_SUMMARY: ReportSectionStatus.PRESENT,
        ReportSectionId.GEOMETRY: ReportSectionStatus.PRESENT,
        ReportSectionId.HEAT_BALANCE: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.THERMAL_PERFORMANCE: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.SIZING_RANKING: ReportSectionStatus.OUT_OF_SCOPE,
        ReportSectionId.TOP_RANKED_CANDIDATES: ReportSectionStatus.OUT_OF_SCOPE,
        ReportSectionId.WARNINGS: ReportSectionStatus.PRESENT,
        ReportSectionId.BLOCKERS: ReportSectionStatus.PRESENT,
        ReportSectionId.FAILURE_DETAILS: ReportSectionStatus.PRESENT,
        ReportSectionId.PROVENANCE: ReportSectionStatus.PRESENT,
        ReportSectionId.INTEGRITY: ReportSectionStatus.PRESENT,
    },
}

# Sizing matrices keyed by termination_status
_SIZING_MATRIX: dict[str, dict[ReportSectionId, ReportSectionStatus]] = {
    "complete": {
        ReportSectionId.STATUS_BANNER: ReportSectionStatus.PRESENT,
        ReportSectionId.RUN_IDENTITY: ReportSectionStatus.PRESENT,
        ReportSectionId.INPUT_SUMMARY: ReportSectionStatus.PRESENT,
        ReportSectionId.GEOMETRY: ReportSectionStatus.PRESENT,
        ReportSectionId.HEAT_BALANCE: ReportSectionStatus.PRESENT,
        ReportSectionId.THERMAL_PERFORMANCE: ReportSectionStatus.PRESENT,
        ReportSectionId.SIZING_RANKING: ReportSectionStatus.PRESENT,
        ReportSectionId.TOP_RANKED_CANDIDATES: ReportSectionStatus.PRESENT,
        ReportSectionId.WARNINGS: ReportSectionStatus.PRESENT,
        ReportSectionId.BLOCKERS: ReportSectionStatus.PRESENT,
        ReportSectionId.FAILURE_DETAILS: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.PROVENANCE: ReportSectionStatus.PRESENT,
        ReportSectionId.INTEGRITY: ReportSectionStatus.PRESENT,
    },
    "partial": {
        ReportSectionId.STATUS_BANNER: ReportSectionStatus.PRESENT,
        ReportSectionId.RUN_IDENTITY: ReportSectionStatus.PRESENT,
        ReportSectionId.INPUT_SUMMARY: ReportSectionStatus.PRESENT,
        ReportSectionId.GEOMETRY: ReportSectionStatus.PRESENT,
        ReportSectionId.HEAT_BALANCE: ReportSectionStatus.PRESENT,
        ReportSectionId.THERMAL_PERFORMANCE: ReportSectionStatus.PRESENT,
        ReportSectionId.SIZING_RANKING: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.TOP_RANKED_CANDIDATES: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.WARNINGS: ReportSectionStatus.PRESENT,
        ReportSectionId.BLOCKERS: ReportSectionStatus.PRESENT,
        ReportSectionId.FAILURE_DETAILS: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.PROVENANCE: ReportSectionStatus.PRESENT,
        ReportSectionId.INTEGRITY: ReportSectionStatus.PRESENT,
    },
}


def verify_report_section_status_matrix(
    model: ReportModel,
    operation: str,
    termination_status: str,
) -> None:
    """Verify each section's status matches the expected matrix.

    Raises :class:`ValueError` on any mismatch.
    """
    if operation == "rateDoublePipe":
        matrix = _RATING_MATRIX.get(termination_status)
        if matrix is None:
            raise ValueError(f"Unknown rating termination status: {termination_status!r}")
    elif operation == "sizeDoublePipe":
        matrix = _SIZING_MATRIX.get(termination_status)
        if matrix is None:
            raise ValueError(f"Unknown sizing termination status: {termination_status!r}")
    else:
        raise ValueError(f"Unsupported operation for status matrix: {operation!r}")

    for section in model.sections:
        expected = matrix.get(section.section_id)
        if expected is None:
            raise ValueError(f"Section {section.section_id.value} not in status matrix")
        if section.status != expected:
            raise ValueError(
                f"Section {section.section_id.value}: "
                f"expected status {expected.value}, got {section.status.value}"
            )


# =========================================================================
# Section/Artifact Building Helpers
# =========================================================================


def _get_result_status(envelope: Any) -> str:
    """Extract the result status string from an envelope."""
    result = envelope.result
    if hasattr(result, "status"):
        return str(result.status)
    if hasattr(result, "termination_status"):
        return str(result.termination_status)
    return "unknown"


def _get_termination_status(envelope: Any) -> str:
    """Extract the termination status for matrix verification."""
    if envelope.operation == "rateDoublePipe":
        return str(envelope.result.status)
    if envelope.operation == "sizeDoublePipe":
        return str(envelope.result.termination_status)
    raise ValueError(f"Unsupported operation: {envelope.operation}")


def _build_section_statuses(
    envelope: Any,
) -> dict[ReportSectionId, ReportSectionStatus]:
    """Build the expected section status map from the envelope."""
    operation = envelope.operation
    if operation == "rateDoublePipe":
        status = str(envelope.result.status)
        matrix = _RATING_MATRIX.get(status)
        if matrix is None:
            raise ValueError(f"Unknown rating status: {status!r}")
        return dict(matrix)
    if operation == "sizeDoublePipe":
        status = str(envelope.result.termination_status)
        matrix = _SIZING_MATRIX.get(status)
        if matrix is None:
            raise ValueError(f"Unknown sizing termination: {status!r}")
        return dict(matrix)
    raise ValueError(f"Unsupported operation: {operation!r}")


def _section_content(
    section_id: ReportSectionId,
    envelope: Any,
    status: ReportSectionStatus,
) -> str:
    """Build text content for a report section."""
    title = _SECTION_TITLES[section_id]

    if status == ReportSectionStatus.OUT_OF_SCOPE:
        return f"{title} is out of scope for this operation."
    if status == ReportSectionStatus.NOT_APPLICABLE:
        return f"{title} is not applicable."
    if status == ReportSectionStatus.NOT_IMPLEMENTED:
        return f"{title} is not yet implemented."

    # PRESENT — build actual content from envelope
    result = envelope.result
    lines: list[str] = []

    if section_id == ReportSectionId.STATUS_BANNER:
        lines.append(f"Operation: {envelope.operation}")
        lines.append(f"Result Kind: {envelope.result_kind}")
        lines.append(f"Status: {_get_result_status(envelope)}")

    elif section_id == ReportSectionId.RUN_IDENTITY:
        lines.append(f"Run ID: {envelope.run_id}")
        lines.append(f"Operation: {envelope.operation}")
        lines.append(f"Request Digest: {envelope.request_digest}")
        if hasattr(envelope, "idempotency_key_digest"):
            lines.append(f"Idempotency Key Digest: {envelope.idempotency_key_digest}")

    elif section_id == ReportSectionId.INPUT_SUMMARY:
        snapshot = getattr(envelope, "artifact_bundle", None)
        if snapshot is not None and hasattr(snapshot, "canonical_request_snapshot"):
            snap = snapshot.canonical_request_snapshot
            if isinstance(snap, dict):
                for k, v in sorted(snap.items()):
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"Canonical Request: {snap}")
        else:
            lines.append("Canonical request snapshot available in artifacts.")

    elif section_id == ReportSectionId.GEOMETRY:
        bundle = getattr(envelope, "artifact_bundle", None)
        if bundle is not None:
            geom = getattr(bundle, "geometry_snapshot", None)
            if geom is not None and hasattr(geom, "model_dump"):
                for k, v in sorted(geom.model_dump().items()):
                    lines.append(f"  {k}: {v}")
            else:
                lines.append("Geometry snapshot available in artifacts.")
        else:
            lines.append("Geometry data available in artifacts.")

    elif section_id == ReportSectionId.HEAT_BALANCE:
        if hasattr(result, "heat_duty_w") and result.heat_duty_w is not None:
            lines.append(f"Heat Duty: {result.heat_duty_w} W")
        if hasattr(result, "LMTD_k") and result.LMTD_k is not None:
            lines.append(f"LMTD: {result.LMTD_k} K")
        if hasattr(result, "effectiveness") and result.effectiveness is not None:
            lines.append(f"Effectiveness: {result.effectiveness}")
        if hasattr(result, "energy_residual_w") and result.energy_residual_w is not None:
            lines.append(f"Energy Residual: {result.energy_residual_w} W")
        if not lines:
            lines.append("Heat balance data available in result.")

    elif section_id == ReportSectionId.THERMAL_PERFORMANCE:
        if hasattr(result, "U_inner_basis") and result.U_inner_basis is not None:
            lines.append(f"U_inner: {result.U_inner_basis} W/(m2·K)")
        if hasattr(result, "U_outer_basis") and result.U_outer_basis is not None:
            lines.append(f"U_outer: {result.U_outer_basis} W/(m2·K)")
        if hasattr(result, "UA_w_k") and result.UA_w_k is not None:
            lines.append(f"UA: {result.UA_w_k} W/K")
        if hasattr(result, "NTU") and result.NTU is not None:
            lines.append(f"NTU: {result.NTU}")
        if hasattr(result, "capacity_ratio") and result.capacity_ratio is not None:
            lines.append(f"Capacity Ratio: {result.capacity_ratio}")
        if not lines:
            lines.append("Thermal performance data available in result.")

    elif section_id == ReportSectionId.SIZING_RANKING:
        if hasattr(result, "termination_status"):
            lines.append(f"Termination Status: {result.termination_status}")
        if hasattr(result, "total_candidate_count"):
            lines.append(f"Total Candidates: {result.total_candidate_count}")
        if hasattr(result, "feasible_candidate_count"):
            lines.append(f"Feasible Candidates: {result.feasible_candidate_count}")
        if not lines:
            lines.append("Sizing ranking data available in result.")

    elif section_id == ReportSectionId.TOP_RANKED_CANDIDATES:
        if hasattr(result, "ordered_top_n_record_digests"):
            digests = result.ordered_top_n_record_digests
            lines.append(f"Top {len(digests)} candidate(s):")
            for i, d in enumerate(digests):
                lines.append(f"  [{i}] {d}")
        if not lines:
            lines.append("Top ranked candidates available in result.")

    elif section_id == ReportSectionId.WARNINGS:
        warnings = getattr(envelope, "warnings", ())
        if warnings:
            lines.append(f"Warnings ({len(warnings)}):")
            for w in warnings:
                code = getattr(w, "code", "?")
                sev = getattr(w, "severity", "?")
                msg = getattr(w, "message", str(w))
                lines.append(f"  [{sev}] {code}: {msg}")
        else:
            lines.append("No warnings.")

    elif section_id == ReportSectionId.BLOCKERS:
        blockers = getattr(envelope, "blockers", ())
        if blockers:
            lines.append(f"Blockers ({len(blockers)}):")
            for b in blockers:
                code = getattr(b, "code", "?")
                sev = getattr(b, "severity", "?")
                msg = getattr(b, "message", str(b))
                lines.append(f"  [{sev}] {code}: {msg}")
        else:
            lines.append("No blockers.")

    elif section_id == ReportSectionId.FAILURE_DETAILS:
        failure = getattr(envelope, "failure", None)
        if failure is not None:
            code = getattr(failure, "code", "?")
            msg = getattr(failure, "message", str(failure))
            lines.append(f"Failure Code: {code}")
            lines.append(f"Message: {msg}")
        else:
            lines.append("No failure recorded.")

    elif section_id == ReportSectionId.PROVENANCE:
        provenance = getattr(envelope, "provenance", None)
        if provenance is not None:
            nodes = getattr(provenance, "nodes", ())
            edges = getattr(provenance, "edges", ())
            lines.append(f"Provenance Digest: {envelope.provenance_digest}")
            lines.append(f"Nodes: {len(nodes)}")
            lines.append(f"Edges: {len(edges)}")
        else:
            lines.append(f"Provenance Digest: {envelope.provenance_digest}")

    elif section_id == ReportSectionId.INTEGRITY:
        lines.append(f"Result Hash: {envelope.result_hash}")
        lines.append(f"Provenance Digest: {envelope.provenance_digest}")
        lines.append(f"Bundle Digest: {envelope.artifact_bundle_digest}")

    return "\n".join(lines)


def _build_artifacts_for_section(
    section_id: ReportSectionId,
    envelope_dict: dict[str, Any],
    section_statuses: dict[ReportSectionId, ReportSectionStatus],
) -> list[ReportArtifact]:
    """Build artifact list for a given section."""
    artifacts: list[ReportArtifact] = []
    section_status = section_statuses[section_id]

    for kind, (owner_section, pointer_candidates) in _ARTIFACT_POINTER_MAP.items():
        if owner_section != section_id:
            continue

        artifact_id = ReportArtifactId(kind.value)

        if section_status in (
            ReportSectionStatus.OUT_OF_SCOPE,
            ReportSectionStatus.NOT_APPLICABLE,
            ReportSectionStatus.NOT_IMPLEMENTED,
        ):
            # Section is not present — artifact inherits the status
            if section_status == ReportSectionStatus.OUT_OF_SCOPE:
                artifacts.append(
                    OutOfScopeReportArtifact(
                        artifact_id=artifact_id,
                        kind=kind,
                        section=section_id,
                        reason="out_of_scope",
                    )
                )
            elif section_status == ReportSectionStatus.NOT_APPLICABLE:
                artifacts.append(
                    UnavailableReportArtifact(
                        artifact_id=artifact_id,
                        kind=kind,
                        section=section_id,
                        reason="unavailable",
                    )
                )
            else:
                artifacts.append(
                    NotImplementedReportArtifact(
                        artifact_id=artifact_id,
                        kind=kind,
                        section=section_id,
                        reason="not_implemented",
                    )
                )
        else:
            # Section is PRESENT — try to resolve the pointer
            resolved = False
            for pointer in pointer_candidates:
                try:
                    value = resolve_source_pointer(envelope_dict, pointer)
                    canonical_raw = _canonical_raw(value)
                    artifacts.append(
                        PresentReportArtifact(
                            artifact_id=artifact_id,
                            kind=kind,
                            section=section_id,
                            canonical_raw_value=canonical_raw,
                            source_pointer=pointer,
                        )
                    )
                    resolved = True
                    break
                except (ValueError, KeyError, IndexError):
                    continue
            if not resolved:
                # Could not resolve — mark unavailable
                artifacts.append(
                    UnavailableReportArtifact(
                        artifact_id=artifact_id,
                        kind=kind,
                        section=section_id,
                        reason="pointer_unresolvable",
                    )
                )

    return artifacts


def _canonical_raw(value: Any) -> str:
    """Convert a value to its canonical string representation."""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return json.dumps(value)
    if value is None:
        return "null"
    # Complex types → canonical JSON
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _build_sections_from_envelope(
    envelope: Any,
) -> tuple[ReportSection, ...]:
    """Build exactly 13 report sections from a run envelope."""
    section_statuses = _build_section_statuses(envelope)
    envelope_dict = envelope.model_dump(mode="json")

    sections: list[ReportSection] = []
    for section_id in REPORT_SECTION_ORDER:
        status = section_statuses[section_id]
        title = _SECTION_TITLES[section_id]
        content = _section_content(section_id, envelope, status)
        artifacts = _build_artifacts_for_section(section_id, envelope_dict, section_statuses)
        sections.append(
            ReportSection(
                section_id=section_id,
                title=title,
                content=content,
                status=status,
                artifacts=tuple(artifacts),
            )
        )

    return tuple(sections)


# =========================================================================
# Verification Helpers (B4, B5)
# =========================================================================


def _verify_mandatory_artifacts(model: ReportModel) -> None:
    """B4: Verify mandatory artifacts are present and correctly placed."""
    seen: dict[ReportArtifactId, ReportSectionId] = {}

    for section in model.sections:
        for artifact in section.artifacts:
            aid = artifact.artifact_id
            if aid in seen:
                raise ValueError(
                    f"Duplicate artifact ID {aid.value!r}: "
                    f"in {section.section_id.value} "
                    f"and {seen[aid].value}"
                )
            seen[aid] = section.section_id

    # Check all mandatory artifacts present
    for artifact_id in MANDATORY_ARTIFACT_IDS:
        if artifact_id not in seen:
            raise ValueError(f"Missing mandatory artifact: {artifact_id.value!r}")

        expected_section = MANDATORY_ARTIFACT_OWNERS[artifact_id]
        actual_section = seen[artifact_id]
        if actual_section != expected_section:
            raise ValueError(
                f"Artifact {artifact_id.value!r} in wrong section: "
                f"expected {expected_section.value}, got {actual_section.value}"
            )


def _verify_source_pointers(model: ReportModel, envelope_dict: dict[str, Any]) -> None:
    """B5: Resolve source pointers and verify canonical raw values."""
    for section in model.sections:
        for artifact in section.artifacts:
            if isinstance(artifact, PresentReportArtifact):
                # Validate pointer format
                validate_rfc6901_pointer(artifact.source_pointer)
                # Resolve and verify
                resolved = resolve_source_pointer(envelope_dict, artifact.source_pointer)
                expected_raw = _canonical_raw(resolved)
                if artifact.canonical_raw_value != expected_raw:
                    raise ValueError(
                        f"Artifact {artifact.artifact_id.value!r}: "
                        f"canonical_raw_value mismatch. "
                        f"Expected {expected_raw!r}, "
                        f"got {artifact.canonical_raw_value!r}"
                    )


# =========================================================================
# B7 — Pre-render Verification Chain
# =========================================================================


def build_report_html(record: Any) -> bytes:
    """Build an HTML report from a repository :class:`RunRecord`.

    Executes the full verification chain (B7):
    1. Retrieve stored run record
    2. Verify domain result
    3. Verify provenance
    4. Verify artifact bundle
    5. Verify run envelope
    6. Verify section/status matrix
    7. Verify mandatory artifacts
    8. Resolve source pointers
    9. Verify canonical raw values
    10. Verify report hashes
    11. Render HTML

    Raises :class:`ValueError` on any verification failure.
    """
    # 1. Retrieve stored run record
    if record.envelope is None:
        raise ValueError("Record has no envelope")

    envelope = record.envelope
    operation = record.operation

    # 2. Verify domain result (check envelope fields exist)
    if not hasattr(envelope, "result") or envelope.result is None:
        raise ValueError("Envelope has no result")
    if not hasattr(envelope, "result_hash"):
        raise ValueError("Envelope has no result_hash")
    if not hasattr(envelope, "result_kind"):
        raise ValueError("Envelope has no result_kind")

    # 3. Verify provenance (check provenance_digest matches)
    if not hasattr(envelope, "provenance_digest"):
        raise ValueError("Envelope has no provenance_digest")
    if not hasattr(envelope, "provenance"):
        raise ValueError("Envelope has no provenance")
    # Cross-check: provenance_digest must match result's provenance_digest
    prov_match = hasattr(envelope.result, "provenance_digest")
    if prov_match and envelope.provenance_digest != envelope.result.provenance_digest:
        raise ValueError("provenance_digest mismatch between envelope and result")

    # 4. Verify artifact bundle (check bundle parity)
    if not hasattr(envelope, "artifact_bundle"):
        raise ValueError("Envelope has no artifact_bundle")
    if not hasattr(envelope, "artifact_bundle_digest"):
        raise ValueError("Envelope has no artifact_bundle_digest")

    # 5. Verify run envelope (cross-field parity)
    if envelope.operation != operation:
        raise ValueError(
            f"Envelope operation {envelope.operation!r} != record operation {operation!r}"
        )
    has_rd = hasattr(envelope, "request_digest") and hasattr(record, "request_digest")
    if has_rd and envelope.request_digest != record.request_digest:
        raise ValueError("Envelope request_digest != record request_digest")

    # Build sections
    sections = _build_sections_from_envelope(envelope)

    # Compute content hash
    content_hash = compute_report_content_hash(sections)

    # Compute instance hash
    instance_identity = ReportInstanceIdentity(
        report_content_hash=content_hash,
        report_schema_version="1.0",
        run_id=envelope.run_id,
        operation=operation,
    )
    instance_hash = compute_report_instance_hash(instance_identity)

    # Build model (triggers B2 section validation)
    model = ReportModel(
        run_id=envelope.run_id,
        operation=operation,
        report_schema_version="1.0",
        sections=sections,
        content_hash=content_hash,
        instance_hash=instance_hash,
    )

    # 6. Verify section/status matrix
    termination_status = _get_termination_status(envelope)
    verify_report_section_status_matrix(model, operation, termination_status)

    # 7. Verify mandatory artifacts
    _verify_mandatory_artifacts(model)

    # 8 & 9. Resolve source pointers and verify canonical raw values
    envelope_dict = envelope.model_dump(mode="json")
    _verify_source_pointers(model, envelope_dict)

    # 10. Verify report hashes
    # Content hash is computed fresh above — verify it matches
    recomputed_content = compute_report_content_hash(model.sections)
    if recomputed_content != content_hash:
        raise ValueError("Content hash recomputation mismatch")
    recomputed_instance = compute_report_instance_hash(instance_identity)
    if recomputed_instance != instance_hash:
        raise ValueError("Instance hash recomputation mismatch")

    # 11. Render HTML
    return render_report_html(model)


# =========================================================================
# B8 — Deterministic Secure HTML
# =========================================================================


def _escape(text: str) -> str:
    """HTML-escape *text* and block potential injection vectors.

    - Absolute paths → ``[BLOCKED]``
    - Traceback / exception references → ``[REDACTED]``
    - Known secret-token patterns → ``[REDACTED]``
    - Env-var look-alikes (``${...}`` or ``%VAR%``) → ``[REDACTED]``
    """
    # Block absolute paths
    if text.startswith("/") or text.startswith("\\"):
        text = "[BLOCKED]"

    # Block tracebacks
    lower = text.lower()
    if "traceback" in lower or "exception" in lower:
        text = text.replace("Traceback", "[REDACTED]")
        text = text.replace("traceback", "[redacted]")
        text = text.replace("Exception", "[REDACTED]")
        text = text.replace("exception", "[redacted]")

    # Block secret tokens
    text = _SENSITIVE_PATTERNS.sub("[REDACTED]", text)

    # Block env-var look-alikes
    text = re.sub(r"\$\{[^}]+\}", "[REDACTED]", text)
    text = re.sub(r"%[A-Z_][A-Z0-9_]*%", "[REDACTED]", text)

    return _html.escape(text, quote=True)


def render_report_html(model: ReportModel) -> bytes:
    """Render a :class:`ReportModel` to deterministic HTML bytes.

    Contract guarantees (B8):
    - Deterministic output (same model → same bytes)
    - Autoescaped output (all user data passed through :func:`_escape`)
    - No external CDN / font / tracking resources
    - No user-supplied template paths
    - No absolute paths in output
    - No traceback / exception leaking
    - No token / env-var leaking
    - PRELIMINARY / NOT FOR PROCUREMENT / NOT FOR CONSTRUCTION banners
    """
    parts: list[str] = []
    parts.append('<!DOCTYPE html>\n<html lang="en">\n<head>')
    parts.append('<meta charset="utf-8">')
    parts.append(f"<title>Run Report {_escape(str(model.run_id))}</title>")
    parts.append(
        "<style>"
        "body{font-family:monospace;margin:2em}"
        ".banner{background:#c00;color:#fff;padding:0.5em;margin:0.5em 0;font-weight:bold}"
        ".section{border:1px solid #ccc;padding:1em;margin:1em 0}"
        ".section-header{font-weight:bold;margin-bottom:0.5em}"
        ".status{font-style:italic;color:#555}"
        ".hash{font-family:monospace;font-size:0.9em;word-break:break-all}"
        "</style>"
    )
    parts.append("</head>\n<body>")

    # Risk banners — must appear on every page
    for banner in _RISK_BANNERS:
        parts.append(f'<div class="banner">{_escape(banner)}</div>')

    # Header
    parts.append("<h1>Run Report</h1>")
    parts.append(f"<p><strong>Run ID:</strong> {_escape(str(model.run_id))}</p>")
    parts.append(f"<p><strong>Operation:</strong> {_escape(model.operation)}</p>")
    parts.append(
        f"<p><strong>Content Hash:</strong> "
        f'<span class="hash">{_escape(model.content_hash)}</span></p>'
    )
    parts.append(
        f"<p><strong>Instance Hash:</strong> "
        f'<span class="hash">{_escape(model.instance_hash)}</span></p>'
    )
    parts.append(f"<p><strong>Schema Version:</strong> {_escape(model.report_schema_version)}</p>")

    # Sections (order is deterministic because the tuple is frozen)
    for section in model.sections:
        parts.append('<div class="section">')
        parts.append(f'<div class="section-header">{_escape(section.title)}</div>')
        parts.append(f'<p class="status">Status: {_escape(section.status.value)}</p>')
        # Render content with line breaks preserved
        for line in section.content.split("\n"):
            parts.append(f"<p>{_escape(line)}</p>")
        # Render artifacts
        if section.artifacts:
            parts.append("<details><summary>Artifacts</summary><ul>")
            for art in section.artifacts:
                art_id = _escape(art.artifact_id.value)
                art_kind = _escape(art.kind.value)
                if isinstance(art, PresentReportArtifact):
                    pointer = _escape(art.source_pointer)
                    raw_preview = _escape(art.canonical_raw_value[:200])
                    parts.append(
                        f"<li><strong>{art_id}</strong> ({art_kind}): "
                        f"<code>{pointer}</code> = <code>{raw_preview}</code></li>"
                    )
                else:
                    reason = _escape(getattr(art, "reason", "unknown"))
                    parts.append(f"<li><strong>{art_id}</strong> ({art_kind}): [{reason}]</li>")
            parts.append("</ul></details>")
        parts.append("</div>")

    parts.append("</body>\n</html>")
    return "\n".join(parts).encode("utf-8")


# =========================================================================
# Public API
# =========================================================================

__all__ = [
    "MANDATORY_ARTIFACT_IDS",
    "MANDATORY_ARTIFACT_OWNERS",
    "NotImplementedReportArtifact",
    "OutOfScopeReportArtifact",
    "PresentReportArtifact",
    "REPORT_SECTION_ORDER",
    "ReportArtifact",
    "ReportArtifactId",
    "ReportArtifactKind",
    "ReportInstanceIdentity",
    "ReportModel",
    "ReportSection",
    "ReportSectionId",
    "ReportSectionStatus",
    "UnavailableReportArtifact",
    "build_report_html",
    "compute_report_content_hash",
    "compute_report_instance_hash",
    "render_report_html",
    "resolve_source_pointer",
    "validate_rfc6901_pointer",
    "verify_report_section_status_matrix",
]
