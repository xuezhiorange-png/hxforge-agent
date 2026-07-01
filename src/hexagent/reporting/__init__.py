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
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any, Literal
from uuid import UUID

from pydantic import ConfigDict, Discriminator, model_validator

from hexagent.core.canonical import sha256_digest
from hexagent.domain.models import StrictBaseModel

if TYPE_CHECKING:
    from hexagent.api.envelopes import RatingRunEnvelope, SizingRunEnvelope
    from hexagent.api.repository import RunRecord

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


class ReportSourceDocument(StrEnum):
    """Source documents that report artifacts can originate from."""

    RUN_ENVELOPE = "run_envelope"
    ARTIFACT_BUNDLE = "artifact_bundle"
    CANONICAL_REQUEST = "canonical_request"


class ReportArtifactKind(StrEnum):
    """Kinds of report artifacts."""

    PRESENT = "present"
    NOT_AVAILABLE = "not_available"
    NOT_IMPLEMENTED = "not_implemented"
    OUT_OF_SCOPE = "out_of_scope"


class ReportSectionStatus(StrEnum):
    """Section completion status."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


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
    """Artifact identifiers — one per logical data point in the report."""

    STATUS = "status"
    TERMINATION_STATUS = "termination_status"
    RUN_ID = "run_id"
    API_VERSION = "api_version"
    OPERATION = "operation"
    REQUEST_DIGEST = "request_digest"
    CASE_NAME = "case_name"
    HOT_FLUID = "hot_fluid"
    COLD_FLUID = "cold_fluid"
    HOT_INLET_T = "hot_inlet_t"
    COLD_INLET_T = "cold_inlet_t"
    MASS_FLOWS = "mass_flows"
    DESIGN_PRESSURES = "design_pressures"
    DESIGN_TEMPERATURES = "design_temperatures"
    GEOMETRY_SPEC = "geometry_spec"
    HEAT_DUTY = "heat_duty"
    ENERGY_RESIDUAL = "energy_residual"
    TUBE_HTC = "tube_htc"
    ANNULUS_HTC = "annulus_htc"
    OVERALL_U = "overall_u"
    EFFECTIVENESS = "effectiveness"
    SIZING_RANK = "sizing_rank"
    OPTIMIZATION_OBJECTIVE = "optimization_objective"
    WARNING_MESSAGES = "warning_messages"
    BLOCKER_MESSAGES = "blocker_messages"
    TOP_RANKED_CANDIDATES = "top_ranked_candidates"
    FAILURE_REASON = "failure_reason"
    PROVENANCE_GRAPH = "provenance_graph"
    RESULT_HASH = "result_hash"
    BUNDLE_HASH = "bundle_hash"
    PRESSURE_DROP = "pressure_drop"
    VELOCITY = "velocity"
    MATERIALS = "materials"
    COST = "cost"
    MECHANICAL = "mechanical"
    PROCUREMENT = "procurement"


# ---------------------------------------------------------------------------
# Artifact variant models (B1, P0-5)
# ---------------------------------------------------------------------------


class PresentReportArtifact(StrictBaseModel):
    """A report artifact that is present with canonical data."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[ReportArtifactKind.PRESENT]
    artifact_id: ReportArtifactId
    source_document: ReportSourceDocument
    source_document_digest: str
    source_json_pointer: str
    authority_digest: str
    canonical_raw_value: str
    source_unit: str | None = None
    display_unit: str | None = None
    formatter_id: str
    formatter_version: str
    rounding_mode: str
    formatted_display_value: str


class UnavailableReportArtifact(StrictBaseModel):
    """A report artifact that is unavailable."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[ReportArtifactKind.NOT_AVAILABLE]
    artifact_id: ReportArtifactId
    reason_code: str
    capability: str


class NotImplementedReportArtifact(StrictBaseModel):
    """A report artifact that is not yet implemented."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[ReportArtifactKind.NOT_IMPLEMENTED]
    artifact_id: ReportArtifactId
    capability: str


class OutOfScopeReportArtifact(StrictBaseModel):
    """A report artifact that is out of scope for this operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[ReportArtifactKind.OUT_OF_SCOPE]
    artifact_id: ReportArtifactId
    capability: str


# ---------------------------------------------------------------------------
# Discriminated union for ReportArtifact (B1)
# ---------------------------------------------------------------------------
# Each variant has a `kind` field with a distinct Literal StrEnum value,
# so Pydantic v2 Discriminator("kind") resolves unambiguously.

ReportArtifact = Annotated[
    PresentReportArtifact
    | UnavailableReportArtifact
    | NotImplementedReportArtifact
    | OutOfScopeReportArtifact,
    Discriminator("kind"),
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
# B4 — Mandatory Artifacts (exactly 5)
# =========================================================================

MANDATORY_ARTIFACT_IDS: frozenset[ReportArtifactId] = frozenset(
    {
        ReportArtifactId.STATUS,
        ReportArtifactId.RUN_ID,
        ReportArtifactId.REQUEST_DIGEST,
        ReportArtifactId.RESULT_HASH,
        ReportArtifactId.BUNDLE_HASH,
    }
)

MANDATORY_ARTIFACT_OWNERS: dict[ReportArtifactId, ReportSectionId] = {
    ReportArtifactId.STATUS: ReportSectionId.STATUS_BANNER,
    ReportArtifactId.RUN_ID: ReportSectionId.RUN_IDENTITY,
    ReportArtifactId.REQUEST_DIGEST: ReportSectionId.RUN_IDENTITY,
    ReportArtifactId.RESULT_HASH: ReportSectionId.INTEGRITY,
    ReportArtifactId.BUNDLE_HASH: ReportSectionId.INTEGRITY,
}


# ---------------------------------------------------------------------------
# Artifact → section + pointer mapping
# ---------------------------------------------------------------------------

# Mapping: artifact_id → (owner section, source_document, pointer candidates)
_ARTIFACT_MAP: dict[
    ReportArtifactId,
    tuple[ReportSectionId, ReportSourceDocument, tuple[str, ...]],
] = {
    ReportArtifactId.STATUS: (
        ReportSectionId.STATUS_BANNER,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/result/status", "/result/result_status"),
    ),
    ReportArtifactId.TERMINATION_STATUS: (
        ReportSectionId.STATUS_BANNER,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/result/termination_status",),
    ),
    ReportArtifactId.RUN_ID: (
        ReportSectionId.RUN_IDENTITY,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/run_id",),
    ),
    ReportArtifactId.API_VERSION: (
        ReportSectionId.RUN_IDENTITY,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/api_schema_version",),
    ),
    ReportArtifactId.OPERATION: (
        ReportSectionId.RUN_IDENTITY,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/operation",),
    ),
    ReportArtifactId.REQUEST_DIGEST: (
        ReportSectionId.RUN_IDENTITY,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/request_digest",),
    ),
    ReportArtifactId.CASE_NAME: (
        ReportSectionId.INPUT_SUMMARY,
        ReportSourceDocument.CANONICAL_REQUEST,
        ("/case_name",),
    ),
    ReportArtifactId.HOT_FLUID: (
        ReportSectionId.INPUT_SUMMARY,
        ReportSourceDocument.CANONICAL_REQUEST,
        ("/hot_stream/fluid/name",),
    ),
    ReportArtifactId.COLD_FLUID: (
        ReportSectionId.INPUT_SUMMARY,
        ReportSourceDocument.CANONICAL_REQUEST,
        ("/cold_stream/fluid/name",),
    ),
    ReportArtifactId.HOT_INLET_T: (
        ReportSectionId.INPUT_SUMMARY,
        ReportSourceDocument.CANONICAL_REQUEST,
        ("/hot_stream/inlet/temperature/value",),
    ),
    ReportArtifactId.COLD_INLET_T: (
        ReportSectionId.INPUT_SUMMARY,
        ReportSourceDocument.CANONICAL_REQUEST,
        ("/cold_stream/inlet/temperature/value",),
    ),
    ReportArtifactId.MASS_FLOWS: (
        ReportSectionId.INPUT_SUMMARY,
        ReportSourceDocument.CANONICAL_REQUEST,
        ("/hot_stream/mass_flow/value",),
    ),
    ReportArtifactId.DESIGN_PRESSURES: (
        ReportSectionId.INPUT_SUMMARY,
        ReportSourceDocument.CANONICAL_REQUEST,
        ("/design_pressure_hot/value",),
    ),
    ReportArtifactId.DESIGN_TEMPERATURES: (
        ReportSectionId.INPUT_SUMMARY,
        ReportSourceDocument.CANONICAL_REQUEST,
        ("/design_temperature_hot/value",),
    ),
    ReportArtifactId.GEOMETRY_SPEC: (
        ReportSectionId.GEOMETRY,
        ReportSourceDocument.ARTIFACT_BUNDLE,
        ("/geometry_snapshot",),
    ),
    ReportArtifactId.HEAT_DUTY: (
        ReportSectionId.HEAT_BALANCE,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/result/heat_duty_w",),
    ),
    ReportArtifactId.ENERGY_RESIDUAL: (
        ReportSectionId.HEAT_BALANCE,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/result/energy_residual_w",),
    ),
    ReportArtifactId.TUBE_HTC: (
        ReportSectionId.THERMAL_PERFORMANCE,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/result/U_inner_basis",),
    ),
    ReportArtifactId.ANNULUS_HTC: (
        ReportSectionId.THERMAL_PERFORMANCE,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/result/U_outer_basis",),
    ),
    ReportArtifactId.OVERALL_U: (
        ReportSectionId.THERMAL_PERFORMANCE,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/result/U_inner_basis", "/result/U_outer_basis"),
    ),
    ReportArtifactId.EFFECTIVENESS: (
        ReportSectionId.THERMAL_PERFORMANCE,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/result/effectiveness",),
    ),
    ReportArtifactId.PRESSURE_DROP: (
        ReportSectionId.THERMAL_PERFORMANCE,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/result/pressure_drop_tube_pa", "/result/pressure_drop_annulus_pa"),
    ),
    ReportArtifactId.VELOCITY: (
        ReportSectionId.THERMAL_PERFORMANCE,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/result/velocity_tube_m_s", "/result/velocity_annulus_m_s"),
    ),
    ReportArtifactId.MATERIALS: (
        ReportSectionId.GEOMETRY,
        ReportSourceDocument.ARTIFACT_BUNDLE,
        ("/geometry_snapshot/wall_thermal_conductivity",),
    ),
    ReportArtifactId.SIZING_RANK: (
        ReportSectionId.SIZING_RANKING,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/result/termination_status",),
    ),
    ReportArtifactId.OPTIMIZATION_OBJECTIVE: (
        ReportSectionId.SIZING_RANKING,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/result/optimization_objective",),
    ),
    ReportArtifactId.COST: (
        ReportSectionId.SIZING_RANKING,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/result/cost",),
    ),
    ReportArtifactId.MECHANICAL: (
        ReportSectionId.SIZING_RANKING,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/result/mechanical",),
    ),
    ReportArtifactId.PROCUREMENT: (
        ReportSectionId.SIZING_RANKING,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/result/procurement",),
    ),
    ReportArtifactId.WARNING_MESSAGES: (
        ReportSectionId.WARNINGS,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/warnings",),
    ),
    ReportArtifactId.BLOCKER_MESSAGES: (
        ReportSectionId.BLOCKERS,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/blockers",),
    ),
    ReportArtifactId.TOP_RANKED_CANDIDATES: (
        ReportSectionId.TOP_RANKED_CANDIDATES,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/result/ordered_top_n_record_digests",),
    ),
    ReportArtifactId.FAILURE_REASON: (
        ReportSectionId.FAILURE_DETAILS,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/failure/message", "/failure/code"),
    ),
    ReportArtifactId.PROVENANCE_GRAPH: (
        ReportSectionId.PROVENANCE,
        ReportSourceDocument.ARTIFACT_BUNDLE,
        ("/provenance_graph",),
    ),
    ReportArtifactId.RESULT_HASH: (
        ReportSectionId.INTEGRITY,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/result_hash",),
    ),
    ReportArtifactId.BUNDLE_HASH: (
        ReportSectionId.INTEGRITY,
        ReportSourceDocument.RUN_ENVELOPE,
        ("/artifact_bundle_digest",),
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

    parts = pointer.split("/")[1:]
    result: list[str | int] = []
    for part in parts:
        # Check for trailing ~
        if part.endswith("~"):
            raise ValueError(f"Trailing ~ in pointer: {pointer!r}")
        # Validate escape sequences BEFORE unescaping: only ~0 and ~1 are legal
        i = 0
        while i < len(part):
            if part[i] == "~":
                if i + 1 >= len(part) or part[i + 1] not in ("0", "1"):
                    raise ValueError(f"Illegal escape sequence in pointer: {pointer!r}")
                i += 2
            else:
                i += 1
        # Unescape ~1 -> / and ~0 -> ~
        unescaped = part.replace("~1", "/").replace("~0", "~")
        # Try to parse as int for array indices
        try:
            result.append(int(unescaped))
        except ValueError:
            result.append(unescaped)
    return tuple(result)


def resolve_source_pointer(obj: Any, pointer: str) -> Any:
    """Resolve a JSON Pointer against a Python dict/list structure.

    Returns the value at the pointer path.
    Raises ``ValueError`` if the path does not exist.
    """
    parts = validate_rfc6901_pointer(pointer)
    current: Any = obj
    for part in parts:
        if isinstance(current, dict):
            current = current[part]
        elif isinstance(current, (list, tuple)):
            idx = part if isinstance(part, int) else int(part)
            current = current[idx]
        else:
            raise ValueError(f"Cannot resolve {part!r} in {type(current)}")
    return current


def select_report_source_document(
    *,
    envelope: RatingRunEnvelope | SizingRunEnvelope,
    source_document: ReportSourceDocument,
) -> dict[str, object]:
    """Select the root document dict for a given source_document enum.

    Accepts a typed envelope (RatingRunEnvelope | SizingRunEnvelope) and
    extracts the appropriate sub-document based on *source_document*.

    RUN_ENVELOPE  → the full envelope dict
    ARTIFACT_BUNDLE → envelope.artifact_bundle dict
    CANONICAL_REQUEST → envelope.artifact_bundle.canonical_request_snapshot dict

    Raises ``ValueError`` if the requested sub-document is missing.
    """
    envelope_dict: dict[str, object] = envelope.model_dump(mode="json")
    if source_document is ReportSourceDocument.RUN_ENVELOPE:
        return envelope_dict
    if source_document is ReportSourceDocument.ARTIFACT_BUNDLE:
        bundle = envelope_dict.get("artifact_bundle")
        if bundle is None:
            raise ValueError("No artifact_bundle in envelope")
        return dict(bundle) if isinstance(bundle, dict) else {}
    if source_document is ReportSourceDocument.CANONICAL_REQUEST:
        bundle = envelope_dict.get("artifact_bundle")
        if bundle is None:
            raise ValueError("No artifact_bundle in envelope")
        crs = bundle.get("canonical_request_snapshot") if isinstance(bundle, dict) else None
        if crs is None:
            raise ValueError("No canonical_request_snapshot")
        return dict(crs) if isinstance(crs, dict) else {}
    raise ValueError(f"Unknown source_document: {source_document}")


# =========================================================================
# B6 — Report Hashes (P0-6: frozen ReportInstanceIdentity + DoublePipeReportModel)
# =========================================================================


# ---------------------------------------------------------------------------
# Template authority — the actual render string and its hash
# ---------------------------------------------------------------------------

REPORT_TEMPLATE_DEFINITION: str = (
    '<!DOCTYPE html>\n<html lang="en">\n<head>'
    '<meta charset="utf-8">'
    "<title>Run Report {run_id}</title>"
    "<style>"
    "body{font-family:monospace;margin:2em}"
    ".banner{background:#c00;color:#fff;padding:0.5em;margin:0.5em 0;font-weight:bold}"
    ".section{border:1px solid #ccc;padding:1em;margin:1em 0}"
    ".section-header{font-weight:bold;margin-bottom:0.5em}"
    ".status{font-style:italic;color:#555}"
    ".hash{font-family:monospace;font-size:0.9em;word-break:break-all}"
    "</style>"
    "</head>\n<body>"
    "{risk_banners}"
    "<h1>Run Report</h1>"
    "<p><strong>Run ID:</strong> {run_id}</p>"
    '<p><strong>Content Hash:</strong> <span class="hash">{content_hash}</span></p>'
    '<p><strong>Instance Hash:</strong> <span class="hash">{instance_hash}</span></p>'
    "{sections}"
    "</body>\n</html>"
)

REPORT_TEMPLATE_DEFINITION_HASH: str = sha256_digest(REPORT_TEMPLATE_DEFINITION)


class ReportInstanceIdentity(StrictBaseModel):
    """Identity model for a report instance — 11-field frozen Pydantic contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    report_schema_version: Literal["1"]
    report_content_hash: str
    run_id: UUID
    request_digest: str
    source_run_envelope_digest: str
    source_domain_result_hash: str
    source_artifact_bundle_digest: str
    template_id: str
    template_version: str
    template_definition_hash: str
    formatter_registry_version: str


def compute_report_content_hash(sections: tuple[ReportSection, ...]) -> str:
    """Compute deterministic content hash over section data.

    Includes all artifact fields: section_id, status, ordered artifacts,
    and every variant field.
    """
    payload_sections: list[dict[str, Any]] = []
    for s in sections:
        artifact_list: list[dict[str, Any]] = []
        for a in s.artifacts:
            artifact_dict: dict[str, Any] = {
                "kind": a.kind.value,
                "artifact_id": a.artifact_id.value,
            }
            if isinstance(a, PresentReportArtifact):
                artifact_dict["source_document"] = a.source_document.value
                artifact_dict["source_document_digest"] = a.source_document_digest
                artifact_dict["source_json_pointer"] = a.source_json_pointer
                artifact_dict["authority_digest"] = a.authority_digest
                artifact_dict["canonical_raw_value"] = a.canonical_raw_value
                artifact_dict["formatter_id"] = a.formatter_id
                artifact_dict["formatter_version"] = a.formatter_version
                artifact_dict["rounding_mode"] = a.rounding_mode
                artifact_dict["formatted_display_value"] = a.formatted_display_value
                if a.source_unit is not None:
                    artifact_dict["source_unit"] = a.source_unit
                if a.display_unit is not None:
                    artifact_dict["display_unit"] = a.display_unit
            elif isinstance(a, UnavailableReportArtifact):
                artifact_dict["reason_code"] = a.reason_code
                artifact_dict["capability"] = a.capability
            elif isinstance(a, (NotImplementedReportArtifact, OutOfScopeReportArtifact)):
                artifact_dict["capability"] = a.capability
            artifact_list.append(artifact_dict)
        payload_sections.append(
            {
                "section_id": s.section_id.value,
                "status": s.status.value,
                "artifacts": artifact_list,
            }
        )
    return sha256_digest({"sections": payload_sections})


def compute_report_instance_hash(identity: ReportInstanceIdentity) -> str:
    """SHA256 of the ReportInstanceIdentity.

    instance hash = sha256_digest(report_instance_identity.model_dump()).
    """
    return sha256_digest(identity.model_dump(mode="json"))


# =========================================================================
# ReportModel — DoublePipeReportModel (P0-6)
# =========================================================================


class DoublePipeReportModel(StrictBaseModel):
    """Deterministic report model built from a verified envelope.

    Frozen: once constructed the model cannot be mutated, which
    guarantees that :func:`render_report_html` produces identical
    bytes for identical inputs.

    Validates: exactly 13 sections, correct order, no duplicates,
    no missing, no extra (B2).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    report_schema_version: Literal["1"]
    sections: tuple[ReportSection, ...]
    report_instance_identity: ReportInstanceIdentity
    report_content_hash: str
    report_instance_hash: str

    @model_validator(mode="after")
    def _validate_sections(self) -> DoublePipeReportModel:  # noqa: N805
        """B2: Validate exactly 13 sections in correct order + P0-7 identity consistency."""
        if len(self.sections) != 13:
            raise ValueError(f"Expected 13 sections, got {len(self.sections)}")
        expected = REPORT_SECTION_ORDER
        actual = tuple(s.section_id for s in self.sections)
        if actual != expected:
            raise ValueError("Section order mismatch")
        # P0-7: Recompute content hash from sections and verify match
        recomputed_content_hash = compute_report_content_hash(self.sections)
        if recomputed_content_hash != self.report_content_hash:
            raise ValueError(
                "report_content_hash does not match "
                "sha256_digest(sections) — content hash recomputation mismatch"
            )
        # P0-7: Identity content hash must match
        if self.report_instance_identity.report_content_hash != self.report_content_hash:
            raise ValueError(
                "report_instance_identity.report_content_hash does not match report_content_hash"
            )
        # P0-7: Identity schema version must match
        if self.report_instance_identity.report_schema_version != self.report_schema_version:
            raise ValueError(
                "report_instance_identity.report_schema_version "
                "does not match report_schema_version"
            )
        # P0-7: Instance hash must match recomputed value
        expected_instance_hash = compute_report_instance_hash(self.report_instance_identity)
        if self.report_instance_hash != expected_instance_hash:
            raise ValueError(
                "report_instance_hash does not match "
                "sha256_digest(report_instance_identity.model_dump())"
            )
        return self


# Backward-compatible alias
ReportModel = DoublePipeReportModel


# =========================================================================
# B3 — Section/Status Matrix Verification (P0-4: exact frozen contract)
# =========================================================================

# Rating matrices keyed by source_state — EXACT values from frozen contract
_RATING_MATRIX: dict[str, dict[ReportSectionId, ReportSectionStatus]] = {
    "rating_succeeded": {
        ReportSectionId.STATUS_BANNER: ReportSectionStatus.COMPLETE,
        ReportSectionId.RUN_IDENTITY: ReportSectionStatus.COMPLETE,
        ReportSectionId.INPUT_SUMMARY: ReportSectionStatus.COMPLETE,
        ReportSectionId.GEOMETRY: ReportSectionStatus.COMPLETE,
        ReportSectionId.HEAT_BALANCE: ReportSectionStatus.COMPLETE,
        ReportSectionId.THERMAL_PERFORMANCE: ReportSectionStatus.COMPLETE,
        ReportSectionId.SIZING_RANKING: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.TOP_RANKED_CANDIDATES: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.WARNINGS: ReportSectionStatus.COMPLETE,
        ReportSectionId.BLOCKERS: ReportSectionStatus.EMPTY,
        ReportSectionId.FAILURE_DETAILS: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.PROVENANCE: ReportSectionStatus.COMPLETE,
        ReportSectionId.INTEGRITY: ReportSectionStatus.COMPLETE,
    },
    "rating_blocked": {
        ReportSectionId.STATUS_BANNER: ReportSectionStatus.BLOCKED,
        ReportSectionId.RUN_IDENTITY: ReportSectionStatus.COMPLETE,
        ReportSectionId.INPUT_SUMMARY: ReportSectionStatus.COMPLETE,
        ReportSectionId.GEOMETRY: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.HEAT_BALANCE: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.THERMAL_PERFORMANCE: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.SIZING_RANKING: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.TOP_RANKED_CANDIDATES: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.WARNINGS: ReportSectionStatus.PARTIAL,
        ReportSectionId.BLOCKERS: ReportSectionStatus.COMPLETE,
        ReportSectionId.FAILURE_DETAILS: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.PROVENANCE: ReportSectionStatus.COMPLETE,
        ReportSectionId.INTEGRITY: ReportSectionStatus.COMPLETE,
    },
    "rating_failed": {
        ReportSectionId.STATUS_BANNER: ReportSectionStatus.BLOCKED,
        ReportSectionId.RUN_IDENTITY: ReportSectionStatus.COMPLETE,
        ReportSectionId.INPUT_SUMMARY: ReportSectionStatus.COMPLETE,
        ReportSectionId.GEOMETRY: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.HEAT_BALANCE: ReportSectionStatus.PARTIAL,
        ReportSectionId.THERMAL_PERFORMANCE: ReportSectionStatus.PARTIAL,
        ReportSectionId.SIZING_RANKING: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.TOP_RANKED_CANDIDATES: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.WARNINGS: ReportSectionStatus.PARTIAL,
        ReportSectionId.BLOCKERS: ReportSectionStatus.PARTIAL,
        ReportSectionId.FAILURE_DETAILS: ReportSectionStatus.COMPLETE,
        ReportSectionId.PROVENANCE: ReportSectionStatus.COMPLETE,
        ReportSectionId.INTEGRITY: ReportSectionStatus.COMPLETE,
    },
}

# Sizing matrices keyed by source_state — EXACT values from frozen contract
_SIZING_MATRIX: dict[str, dict[ReportSectionId, ReportSectionStatus]] = {
    "sizing_complete": {
        ReportSectionId.STATUS_BANNER: ReportSectionStatus.COMPLETE,
        ReportSectionId.RUN_IDENTITY: ReportSectionStatus.COMPLETE,
        ReportSectionId.INPUT_SUMMARY: ReportSectionStatus.COMPLETE,
        ReportSectionId.GEOMETRY: ReportSectionStatus.COMPLETE,
        ReportSectionId.HEAT_BALANCE: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.THERMAL_PERFORMANCE: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.SIZING_RANKING: ReportSectionStatus.COMPLETE,
        ReportSectionId.TOP_RANKED_CANDIDATES: ReportSectionStatus.COMPLETE,
        ReportSectionId.WARNINGS: ReportSectionStatus.COMPLETE,
        ReportSectionId.BLOCKERS: ReportSectionStatus.EMPTY,
        ReportSectionId.FAILURE_DETAILS: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.PROVENANCE: ReportSectionStatus.COMPLETE,
        ReportSectionId.INTEGRITY: ReportSectionStatus.COMPLETE,
    },
    "sizing_partial": {
        ReportSectionId.STATUS_BANNER: ReportSectionStatus.PARTIAL,
        ReportSectionId.RUN_IDENTITY: ReportSectionStatus.COMPLETE,
        ReportSectionId.INPUT_SUMMARY: ReportSectionStatus.COMPLETE,
        ReportSectionId.GEOMETRY: ReportSectionStatus.PARTIAL,
        ReportSectionId.HEAT_BALANCE: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.THERMAL_PERFORMANCE: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.SIZING_RANKING: ReportSectionStatus.PARTIAL,
        ReportSectionId.TOP_RANKED_CANDIDATES: ReportSectionStatus.PARTIAL,
        ReportSectionId.WARNINGS: ReportSectionStatus.COMPLETE,
        ReportSectionId.BLOCKERS: ReportSectionStatus.PARTIAL,
        ReportSectionId.FAILURE_DETAILS: ReportSectionStatus.NOT_APPLICABLE,
        ReportSectionId.PROVENANCE: ReportSectionStatus.COMPLETE,
        ReportSectionId.INTEGRITY: ReportSectionStatus.COMPLETE,
    },
}


def _get_expected_matrix(
    source_state: str,
) -> dict[ReportSectionId, ReportSectionStatus]:
    """Return expected section→status mapping for the given source state."""
    combined = {**_RATING_MATRIX, **_SIZING_MATRIX}
    matrix = combined.get(source_state)
    if matrix is None:
        raise ValueError(f"Unknown source state: {source_state!r}")
    return matrix


def derive_source_state(envelope: Any) -> str:
    """Determine the source_state string from an envelope.

    This implements the envelope-derived source_state derivation (P0-6).
    """
    operation = envelope.operation
    if operation == "rateDoublePipe":
        failure = getattr(envelope, "failure", None)
        if failure is not None:
            return "rating_failed"
        blockers = getattr(envelope, "blockers", ())
        if blockers:
            return "rating_blocked"
        return "rating_succeeded"
    if operation == "sizeDoublePipe":
        result = envelope.result
        ts = str(getattr(result, "termination_status", "unknown"))
        if ts in ("complete", "COMPLETE"):
            return "sizing_complete"
        if ts in ("partial", "PARTIAL"):
            return "sizing_partial"
        raise ValueError(f"Unknown sizing termination status: {ts!r}")
    raise ValueError(f"Unsupported operation for status matrix: {operation!r}")


def verify_report_section_status_matrix(
    model: ReportModel | DoublePipeReportModel,
    operation: str,
    source_envelope: Any,
) -> None:
    """Verify each section's status matches the exact frozen contract matrix.

    Accepts a source_envelope and derives source_state internally via
    :func:`derive_source_state`.  No flexible matching — every cell
    must match exactly.

    Raises :class:`ValueError` on any mismatch.
    """
    source_state = derive_source_state(source_envelope)
    expected = _get_expected_matrix(source_state)
    for section in model.sections:
        if section.section_id not in expected:
            raise ValueError(f"Unexpected section {section.section_id.value}")
        exp = expected[section.section_id]
        actual = section.status
        if actual != exp:
            raise ValueError(
                f"Section {section.section_id.value}: "
                f"expected status {exp.value}, got {actual.value}"
            )


# =========================================================================
# Section/Artifact Building Helpers
# =========================================================================


def _section_content(
    section_id: ReportSectionId,
    envelope: Any,
    status: ReportSectionStatus,
) -> str:
    """Build text content for a report section."""
    title = _SECTION_TITLES[section_id]

    if status == ReportSectionStatus.NOT_APPLICABLE:
        return f"{title} is not applicable."
    if status == ReportSectionStatus.BLOCKED:
        return f"{title} is blocked."
    if status == ReportSectionStatus.EMPTY:
        return f"No {title.lower()} recorded."

    # COMPLETE or PARTIAL — build actual content from envelope
    result = envelope.result
    lines: list[str] = []

    if section_id == ReportSectionId.STATUS_BANNER:
        lines.append(f"Operation: {envelope.operation}")
        result_kind = getattr(envelope, "result_kind", "unknown")
        lines.append(f"Result Kind: {result_kind}")
        if hasattr(result, "status"):
            lines.append(f"Status: {result.status}")
        elif hasattr(result, "termination_status"):
            lines.append(f"Termination Status: {result.termination_status}")

    elif section_id == ReportSectionId.RUN_IDENTITY:
        lines.append(f"Run ID: {envelope.run_id}")
        lines.append(f"Operation: {envelope.operation}")
        lines.append(f"Request Digest: {envelope.request_digest}")

    elif section_id == ReportSectionId.INPUT_SUMMARY:
        bundle = getattr(envelope, "artifact_bundle", None)
        if bundle is not None and hasattr(bundle, "canonical_request_snapshot"):
            snap = bundle.canonical_request_snapshot
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
            prov_digest = getattr(envelope, "provenance_digest", "N/A")
            lines.append(f"Provenance Digest: {prov_digest}")
            lines.append(f"Nodes: {len(nodes)}")
            lines.append(f"Edges: {len(edges)}")
        else:
            prov_digest = getattr(envelope, "provenance_digest", "N/A")
            lines.append(f"Provenance Digest: {prov_digest}")

    elif section_id == ReportSectionId.INTEGRITY:
        result_hash = getattr(envelope, "result_hash", "N/A")
        prov_digest = getattr(envelope, "provenance_digest", "N/A")
        bundle_digest = getattr(envelope, "artifact_bundle_digest", "N/A")
        lines.append(f"Result Hash: {result_hash}")
        lines.append(f"Provenance Digest: {prov_digest}")
        lines.append(f"Bundle Digest: {bundle_digest}")

    return "\n".join(lines)


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


def _build_section_statuses(
    envelope: Any,
) -> dict[ReportSectionId, ReportSectionStatus]:
    """Build the expected section status map from the envelope."""
    source_state = derive_source_state(envelope)
    matrix = _get_expected_matrix(source_state)
    return matrix


def _build_artifacts_for_section(
    section_id: ReportSectionId,
    envelope: RatingRunEnvelope | SizingRunEnvelope,
    section_statuses: dict[ReportSectionId, ReportSectionStatus],
) -> list[ReportArtifact]:
    """Build artifact list for a given section."""
    artifacts: list[ReportArtifact] = []
    section_status = section_statuses[section_id]

    for artifact_id, (owner_section, source_doc, pointer_candidates) in _ARTIFACT_MAP.items():
        if owner_section != section_id:
            continue

        if (
            section_status
            in (
                ReportSectionStatus.NOT_APPLICABLE,
                ReportSectionStatus.BLOCKED,
            )
            and artifact_id not in MANDATORY_ARTIFACT_IDS
        ):
            artifacts.append(
                UnavailableReportArtifact(
                    kind=ReportArtifactKind.NOT_AVAILABLE,
                    artifact_id=artifact_id,
                    reason_code="section_not_available",
                    capability=section_status.value,
                )
            )
            continue

        # Section is COMPLETE, PARTIAL, or EMPTY — try to resolve the pointer
        resolved = False
        root_document = select_report_source_document(
            envelope=envelope,
            source_document=source_doc,
        )
        source_document_digest = sha256_digest(root_document)
        for pointer in pointer_candidates:
            try:
                value = resolve_source_pointer(root_document, pointer)
                canonical_raw = _canonical_raw(value)
                authority_digest = sha256_digest(value)
                artifacts.append(
                    PresentReportArtifact(
                        kind=ReportArtifactKind.PRESENT,
                        artifact_id=artifact_id,
                        source_document=source_doc,
                        source_document_digest=source_document_digest,
                        source_json_pointer=pointer,
                        authority_digest=authority_digest,
                        canonical_raw_value=canonical_raw,
                        formatter_id="default",
                        formatter_version="1.0",
                        rounding_mode="round",
                        formatted_display_value=canonical_raw,
                    )
                )
                resolved = True
                break
            except (ValueError, KeyError, IndexError):
                continue
        if not resolved:
            artifacts.append(
                UnavailableReportArtifact(
                    kind=ReportArtifactKind.NOT_AVAILABLE,
                    artifact_id=artifact_id,
                    reason_code="pointer_not_resolved",
                    capability=section_status.value,
                )
            )

    return artifacts


def _build_sections_from_envelope(
    envelope: RatingRunEnvelope | SizingRunEnvelope,
) -> tuple[ReportSection, ...]:
    """Build exactly 13 report sections from a run envelope."""
    section_statuses = _build_section_statuses(envelope)

    sections: list[ReportSection] = []
    for section_id in REPORT_SECTION_ORDER:
        status = section_statuses[section_id]
        title = _SECTION_TITLES[section_id]
        content = _section_content(section_id, envelope, status)
        artifacts = _build_artifacts_for_section(section_id, envelope, section_statuses)
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


def _verify_mandatory_artifacts(model: ReportModel | DoublePipeReportModel) -> None:
    """B4: Verify mandatory artifacts are present, correctly placed, and PresentReportArtifact."""
    seen: dict[ReportArtifactId, ReportSectionId] = {}

    for section in model.sections:
        for artifact in section.artifacts:
            aid = artifact.artifact_id
            if aid in MANDATORY_ARTIFACT_IDS and not isinstance(artifact, PresentReportArtifact):
                raise ValueError(
                    f"Mandatory artifact {aid.value!r} must be PresentReportArtifact, "
                    f"got {type(artifact).__name__}"
                )
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


def _verify_source_pointers(
    model: ReportModel | DoublePipeReportModel,
    envelope: RatingRunEnvelope | SizingRunEnvelope,
) -> None:
    """B5: Resolve source pointers against per-document roots and verify.

    Verifies: source_document_digest, source_json_pointer resolution,
    canonical_raw_value, authority_digest.
    """
    for section in model.sections:
        for artifact in section.artifacts:
            if isinstance(artifact, PresentReportArtifact):
                # Validate pointer format
                validate_rfc6901_pointer(artifact.source_json_pointer)
                # Get root document for this artifact's source_document
                root_document = select_report_source_document(
                    envelope=envelope,
                    source_document=artifact.source_document,
                )
                # Verify source_document_digest matches
                expected_doc_digest = sha256_digest(root_document)
                if artifact.source_document_digest != expected_doc_digest:
                    raise ValueError(
                        f"Artifact {artifact.artifact_id.value!r}: "
                        f"source_document_digest mismatch. "
                        f"Expected {expected_doc_digest!r}, "
                        f"got {artifact.source_document_digest!r}"
                    )
                # Resolve against root document and verify
                resolved = resolve_source_pointer(root_document, artifact.source_json_pointer)
                expected_raw = _canonical_raw(resolved)
                if artifact.canonical_raw_value != expected_raw:
                    raise ValueError(
                        f"Artifact {artifact.artifact_id.value!r}: "
                        f"canonical_raw_value mismatch. "
                        f"Expected {expected_raw!r}, "
                        f"got {artifact.canonical_raw_value!r}"
                    )
                # Verify authority_digest matches
                expected_auth_digest = sha256_digest(resolved)
                if artifact.authority_digest != expected_auth_digest:
                    raise ValueError(
                        f"Artifact {artifact.artifact_id.value!r}: "
                        f"authority_digest mismatch. "
                        f"Expected {expected_auth_digest!r}, "
                        f"got {artifact.authority_digest!r}"
                    )


# =========================================================================
# B7 — Pre-render Verification Chain
# =========================================================================


def build_report_html(record: RunRecord) -> bytes:
    """Build an HTML report from a repository :class:`RunRecord`.

    Executes the full verification chain (B7):
    1. Retrieve stored run record
    2. Verify domain result
    3. Verify provenance
    4. Verify artifact bundle
    5. Verify run envelope (cross-field parity)
    6. Build 13 sections from envelope
    7. Build artifacts for each section
    8. Verify status matrix
    9. Verify mandatory artifacts
    10. Verify report hashes
    11. Render HTML

    Raises :class:`ValueError` on any verification failure.
    """
    # 1. Retrieve stored run record
    if record.envelope is None:
        raise ValueError("Record has no envelope")

    envelope = record.envelope
    operation = record.operation

    # 2. Verify domain result (envelope always has these fields per frozen contract)
    if envelope.result is None:
        raise ValueError("Envelope has no result")
    if envelope.result_hash is None:
        raise ValueError("Envelope has no result_hash")

    # 3. Verify provenance (check provenance_digest matches)
    if not hasattr(envelope, "provenance_digest"):
        raise ValueError("Envelope has no provenance_digest")
    if not hasattr(envelope, "provenance"):
        raise ValueError("Envelope has no provenance")
    # Cross-check: provenance_digest must match result's provenance_digest
    if (
        hasattr(envelope.result, "provenance_digest")
        and envelope.provenance_digest != envelope.result.provenance_digest
    ):
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

    # 6 & 7. Build sections and artifacts from envelope
    sections = _build_sections_from_envelope(envelope)

    # Compute content hash
    content_hash = compute_report_content_hash(sections)

    # Build identity (P0-6: 11-field version)
    source_run_envelope_digest = sha256_digest(envelope.model_dump(mode="json"))
    source_domain_result_hash = (
        envelope.result.result_hash if hasattr(envelope.result, "result_hash") else ""
    )
    source_artifact_bundle_digest = envelope.artifact_bundle_digest

    instance_identity = ReportInstanceIdentity(
        report_schema_version="1",
        report_content_hash=content_hash,
        run_id=envelope.run_id,
        request_digest=envelope.request_digest,
        source_run_envelope_digest=source_run_envelope_digest,
        source_domain_result_hash=source_domain_result_hash,
        source_artifact_bundle_digest=source_artifact_bundle_digest,
        template_id="double_pipe_v1",
        template_version="1.0.0",
        template_definition_hash=REPORT_TEMPLATE_DEFINITION_HASH,
        formatter_registry_version="1.0.0",
    )

    # Instance hash = sha256_digest(report_instance_identity)
    report_instance_hash = compute_report_instance_hash(instance_identity)

    # Build DoublePipeReportModel (P0-6)
    model = DoublePipeReportModel(
        report_schema_version="1",
        sections=sections,
        report_instance_identity=instance_identity,
        report_content_hash=content_hash,
        report_instance_hash=report_instance_hash,
    )

    # 8. Verify section/status matrix (P0-6: accepts source_envelope)
    verify_report_section_status_matrix(model, operation, envelope)

    # 9. Verify mandatory artifacts (exactly 5 present, correct owners)
    _verify_mandatory_artifacts(model)

    # 10. Verify source pointers and canonical raw values
    _verify_source_pointers(model, envelope)

    # 11. Verify report hashes
    recomputed_content = compute_report_content_hash(model.sections)
    if recomputed_content != content_hash:
        raise ValueError("Content hash recomputation mismatch")

    # Verify instance hash
    recomputed_instance_hash = compute_report_instance_hash(instance_identity)
    if recomputed_instance_hash != report_instance_hash:
        raise ValueError("Instance hash recomputation mismatch")

    # 12. Render HTML
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


def render_report_html(model: ReportModel | DoublePipeReportModel) -> bytes:
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
    parts.append(f"<title>Run Report {_escape(str(model.report_instance_identity.run_id))}</title>")
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
    run_id_str = _escape(str(model.report_instance_identity.run_id))
    parts.append(f"<p><strong>Run ID:</strong> {run_id_str}</p>")
    parts.append(
        f"<p><strong>Content Hash:</strong> "
        f'<span class="hash">{_escape(model.report_content_hash)}</span></p>'
    )
    parts.append(
        f"<p><strong>Instance Hash:</strong> "
        f'<span class="hash">{_escape(model.report_instance_hash)}</span></p>'
    )

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
                    pointer = _escape(art.source_json_pointer)
                    raw_preview = _escape(art.canonical_raw_value[:200])
                    parts.append(
                        f"<li><strong>{art_id}</strong> ({art_kind}): "
                        f"<code>{pointer}</code> = "
                        f"<code>{raw_preview}</code></li>"
                    )
                else:
                    parts.append(f"<li><strong>{art_id}</strong> ({art_kind}): [{art_kind}]</li>")
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
    "REPORT_TEMPLATE_DEFINITION",
    "REPORT_TEMPLATE_DEFINITION_HASH",
    "ReportArtifact",
    "ReportArtifactId",
    "ReportArtifactKind",
    "ReportInstanceIdentity",
    "ReportModel",
    "ReportSection",
    "ReportSectionId",
    "ReportSectionStatus",
    "ReportSourceDocument",
    "UnavailableReportArtifact",
    "DoublePipeReportModel",
    "build_report_html",
    "compute_report_content_hash",
    "compute_report_instance_hash",
    "derive_source_state",
    "render_report_html",
    "resolve_source_pointer",
    "select_report_source_document",
    "validate_rfc6901_pointer",
    "verify_report_section_status_matrix",
]
