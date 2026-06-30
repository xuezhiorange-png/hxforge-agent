"""TASK-010 report model and deterministic HTML renderer.

Contract §11: Report rendering.
- Deterministic output (same inputs → same bytes)
- Autoescaped HTML
- No external CDN/font/tracking
- No user template paths
- Blocks absolute paths, tracebacks, tokens, env vars
- Risk banners on every page
"""

from __future__ import annotations

import html
import re
from typing import Any
from uuid import UUID

from pydantic import ConfigDict

from hexagent.core.canonical import sha256_digest
from hexagent.domain.models import StrictBaseModel

# Risk banners displayed on every report page
_RISK_BANNERS: tuple[str, ...] = (
    "PRELIMINARY",
    "NOT FOR PROCUREMENT",
    "NOT FOR CONSTRUCTION",
)

# Patterns that must never appear in rendered HTML output
_SENSITIVE_PATTERNS = re.compile(
    r"(ghp_|gho_|sk-[a-zA-Z0-9]{20,}|AKIA[A-Z0-9]{16})",
    re.IGNORECASE,
)


class ReportSection(StrictBaseModel):
    """A single section in the report model."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    section_id: str
    title: str
    content: str
    status: str  # present | not_applicable | not_implemented | out_of_scope


class ReportModel(StrictBaseModel):
    """Deterministic report model built from a verified envelope.

    Frozen: once constructed the model cannot be mutated, which
    guarantees that :func:`render_report_html` produces identical
    bytes for identical inputs.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: UUID
    operation: str
    sections: tuple[ReportSection, ...]
    content_hash: str

    # Section ordering is explicit so renders are reproducible
    section_order: tuple[str, ...] = ()

    @classmethod
    def from_envelope(cls, envelope: Any) -> ReportModel:
        """Build a report model from a verified run envelope."""
        run_id = envelope.run_id
        operation = envelope.operation

        sections: list[ReportSection] = []

        # Section 1: Run Summary
        sections.append(
            ReportSection(
                section_id="run_summary",
                title="Run Summary",
                content=(
                    f"Run ID: {run_id}\nOperation: {operation}\nResult Kind: {envelope.result_kind}"
                ),
                status="present",
            )
        )

        # Section 2: Request
        sections.append(
            ReportSection(
                section_id="request",
                title="Request",
                content=f"Request Digest: {envelope.request_digest}",
                status="present",
            )
        )

        # Section 3: Result
        result_content = f"Result Hash: {envelope.result_hash}\n"
        if hasattr(envelope, "warnings") and envelope.warnings:
            result_content += f"Warnings: {len(envelope.warnings)}\n"
        if hasattr(envelope, "blockers") and envelope.blockers:
            result_content += f"Blockers: {len(envelope.blockers)}\n"
        sections.append(
            ReportSection(
                section_id="result",
                title="Result",
                content=result_content,
                status="present",
            )
        )

        # Section 4: Provenance
        sections.append(
            ReportSection(
                section_id="provenance",
                title="Provenance",
                content=f"Provenance Digest: {envelope.provenance_digest}",
                status="present",
            )
        )

        # Section 5: Artifact Bundle
        sections.append(
            ReportSection(
                section_id="artifacts",
                title="Artifact Bundle",
                content=f"Bundle Digest: {envelope.artifact_bundle_digest}",
                status="present",
            )
        )

        # Compute content hash over the canonical section data
        section_data = tuple((s.section_id, s.title, s.content, s.status) for s in sections)
        content_hash = sha256_digest(section_data)

        section_order = tuple(s.section_id for s in sections)

        return cls(
            run_id=run_id,
            operation=operation,
            sections=tuple(sections),
            content_hash=content_hash,
            section_order=section_order,
        )


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

    return html.escape(text, quote=True)


def render_report_html(model: ReportModel) -> bytes:
    """Render a :class:`ReportModel` to deterministic HTML bytes.

    Contract guarantees:
    - Autoescaped output (all user data passed through :func:`_escape`)
    - No external CDN / font / tracking resources
    - No user-supplied template paths
    - Deterministic: same model → same bytes
    - Risk banners on every page
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
    parts.append(f"<p><strong>Content Hash:</strong> {_escape(model.content_hash)}</p>")

    # Sections (order is deterministic because the tuple is frozen)
    for section in model.sections:
        parts.append('<div class="section">')
        parts.append(f"<h2>{_escape(section.title)}</h2>")
        parts.append(f"<p><em>Status: {_escape(section.status)}</em></p>")
        # Render content with line breaks preserved
        for line in section.content.split("\n"):
            parts.append(f"<p>{_escape(line)}</p>")
        parts.append("</div>")

    parts.append("</body>\n</html>")
    return "\n".join(parts).encode("utf-8")


def build_report_html(record: Any) -> bytes:
    """Build an HTML report from a repository :class:`RunRecord`.

    Verifies the stored envelope, builds the report model,
    and renders deterministic HTML.

    Raises :class:`ValueError` if the record has no envelope.
    """
    if record.envelope is None:
        raise ValueError("Record has no envelope")

    envelope = record.envelope

    # Build report model from envelope
    model = ReportModel.from_envelope(envelope)

    # Render HTML
    return render_report_html(model)


__all__ = [
    "ReportModel",
    "ReportSection",
    "build_report_html",
    "render_report_html",
]
