"""Synthetic test builders for TASK-023 shell geometry catalog.

This module is intentionally non-production — every builder produces
artificial, non-canonical synthetic geometry data that must never be
selected as production authority.

The synthetic dimensions used here (``0.25``, ``1``, ``1.125``) appear
in the TASK-023 design contract §7 as the documented acceptable
positive canonical decimal strings. The synthetic source classes
``PUBLIC_DOMAIN`` / ``VENDOR_PERMISSIONED`` / ``INTERNAL_ENGINEERING_RULE``
are the TASK-012 closed-set values mirrored from the existing
shell-bundle-geometry package.

This module is NOT a collected test module: leading underscore +
absence from ``ci-shard-manifest.yml``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.shell_geometry_catalogs.models import GEOMETRY_ROLE

# Synthetic authority strings used only by tests / builders.
_SYNTHETIC_AUTHORITY = "synthetic.task023.test-authority"


def _sha256_of_canonical(payload: Mapping[str, Any]) -> str:
    return canonical_sha256(dict(payload))


def synthetic_permission_payload(
    *,
    permission_id: str = "perm-synthetic-1",
    permission_scope: tuple[str, ...] = (
        "repository_storage",
        "repository_redistribution",
    ),
    usage_scope: tuple[str, ...] = ("internal_runtime",),
    evidence_ref: str = "synthetic.permission.evidence",
    approved_by: str = "synthetic.approver",
    approved_at: str = "1970-01-01T00:00:00Z",
) -> dict[str, Any]:
    """Build a TASK-023 vendor permission evidence payload.

    The ``permission_hash`` covers every other field per the design
    contract §6 ``permission_hash`` domain.
    """
    payload = {
        "permission_id": permission_id,
        "permission_scope": sorted(permission_scope),
        "usage_scope": sorted(usage_scope),
        "evidence_ref": evidence_ref,
        "approved_by": approved_by,
        "approved_at": approved_at,
    }
    payload["permission_hash"] = _sha256_of_canonical(payload)
    return payload


def synthetic_edge_payload(
    *,
    edge_id: str = "edge-synthetic-1",
    source_id: str = "synthetic.source-1",
    target_geometry_id: str = "synthetic-catalog-1/shell/shell-geometry-synthetic-1/1",
    relation_type: str = "derives_from",
    evidence_refs: tuple[str, ...] = ("synthetic.edge.evidence.1",),
) -> dict[str, Any]:
    """Build a single TASK-023 provenance-edge payload.

    ``target_geometry_id`` MUST match the stable identity of the
    record the edge points at; parsers reject mismatches via
    ``SGC_PROVENANCE_INCOMPLETE``.
    """
    payload = {
        "edge_id": edge_id,
        "source_id": source_id,
        "target_geometry_id": target_geometry_id,
        "relation_type": relation_type,
        "evidence_refs": sorted(evidence_refs),
    }
    payload["edge_hash"] = _sha256_of_canonical(payload)
    return payload


def synthetic_bundle_payload(
    *,
    bundle_id: str = "synthetic-bundle-1",
    bundle_version: str = "1",
    approval_status: str = "approved",
    permission_evidence: tuple[dict[str, Any], ...] = (),
    provenance_edges: tuple[dict[str, Any], ...] = (),
    local_kernel_usage_scope: tuple[str, ...] = ("internal_runtime",),
    evidence_refs: tuple[str, ...] = ("synthetic.bundle.evidence.1",),
    task012_validation_hash: str | None = None,
    bundle_hash_override: str | None = None,
) -> dict[str, Any]:
    """Build one TASK-023 evidence bundle payload.

    The bundle hash covers every other field plus the canonical
    ``(permission_id, permission_hash)``-sorted permission_hashes
    sequence and the same-bounded edge_hashes sequence (per the
    parser implementation). Callers may override ``bundle_hash``
    to validate the negative ``SGC_CATALOG_HASH_MISMATCH`` path.
    """
    sorted_perms = sorted(
        permission_evidence, key=lambda p: (p["permission_id"], p["permission_hash"])
    )
    permission_hashes = [p["permission_hash"] for p in sorted_perms]
    sorted_edges = sorted(provenance_edges, key=lambda e: (e["edge_id"], e["edge_hash"]))
    edge_hashes = [e["edge_hash"] for e in sorted_edges]
    t_hash = task012_validation_hash or ("a" * 64)
    bundle_payload = {
        "schema_version": "task023.shell-authority-evidence-bundle.v1",
        "bundle_id": bundle_id,
        "bundle_version": bundle_version,
        "approval_status": approval_status,
        "permission_hashes": permission_hashes,
        "edge_hashes": edge_hashes,
        "local_kernel_usage_scope": sorted(local_kernel_usage_scope),
        "evidence_refs": sorted(evidence_refs),
        "task012_validation_hash": t_hash,
    }
    bundle_hash = (
        bundle_hash_override
        if bundle_hash_override is not None
        else _sha256_of_canonical(bundle_payload)
    )
    return {
        "schema_version": "task023.shell-authority-evidence-bundle.v1",
        "bundle_id": bundle_id,
        "bundle_version": bundle_version,
        "approval_status": approval_status,
        "permission_evidence": list(permission_evidence),
        "provenance_edges": list(provenance_edges),
        "local_kernel_usage_scope": sorted(local_kernel_usage_scope),
        "evidence_refs": sorted(evidence_refs),
        "task012_validation_hash": t_hash,
        "bundle_hash": bundle_hash,
    }


def synthetic_record_payload(
    *,
    record_key: str = "shell-geometry-synthetic-1",
    catalog_id: str = "synthetic-catalog-1",
    revision: str = "1",
    approval_state: str = "approved",
    shell_inside_diameter_m: str = "0.25",
    nominal_label: str | None = None,
    source_class: str = "PUBLIC_DOMAIN",
    license_form: str = "public_domain",
    license_evidence_extras: Mapping[str, Any] | None = None,
    source_binding_extra: Mapping[str, Any] | None = None,
    permission_refs: tuple[str, ...] = (),
    provenance_refs: tuple[str, ...] = (),
    evidence_refs: tuple[str, ...] = ("synthetic.record.evidence.1",),
    record_hash_override: str | None = None,
) -> dict[str, Any]:
    """Build a TASK-023 shell-geometry record payload.

    ``record_key`` is the third segment of the design-frozen identity
    ``<catalog_id>/shell/<record_key>/<revision>``. The builder
    composes the full ``geometry_id`` accordingly.

    The ``record_hash`` covers every other field per the design
    contract §6 (excluding ``record_hash`` and ``nominal_label``).
    """
    stable_geometry_id = f"{catalog_id}/{GEOMETRY_ROLE}/{record_key}/{revision}"
    license_evidence: dict[str, Any] = {"license_form": license_form}
    if license_evidence_extras:
        license_evidence.update(dict(license_evidence_extras))
    source_binding: dict[str, Any] = {
        "source_id": f"synthetic.source.{record_key}",
        "source_type": "synthetic_test_builders",
        "source_revision": "synthetic-1",
        "source_location": f"synthetic://task023/{record_key}",
        "evidence_ref": f"synthetic.binding.{record_key}",
        "approved_by": "synthetic.approver",
        "approved_at": "1970-01-01T00:00:00Z",
    }
    if source_binding_extra:
        source_binding.update(dict(source_binding_extra))
    # Hash payload EXCLUDES ``record_hash`` AND ``nominal_label`` per §6.
    payload = {
        "schema_version": "task023.approved-shell-geometry-record.v1",
        "geometry_id": stable_geometry_id,
        "geometry_type": "shell",
        "profile_id": "hxforge.shell_geometry_catalog.v1",
        "revision": revision,
        "approval_state": approval_state,
        "shell_inside_diameter_m": shell_inside_diameter_m,
        "source_class": source_class,
        "license_evidence": license_evidence,
        "source_binding": source_binding,
        "permission_evidence_refs": sorted(permission_refs),
        "provenance_edge_ids": sorted(provenance_refs),
        "evidence_refs": sorted(evidence_refs),
    }
    record_hash = (
        record_hash_override if record_hash_override is not None else canonical_sha256(payload)
    )
    return {
        "schema_version": "task023.approved-shell-geometry-record.v1",
        "geometry_id": stable_geometry_id,
        "geometry_type": "shell",
        "profile_id": "hxforge.shell_geometry_catalog.v1",
        "revision": revision,
        "approval_state": approval_state,
        "shell_inside_diameter_m": shell_inside_diameter_m,
        "nominal_label": nominal_label,
        "source_class": source_class,
        "license_evidence": license_evidence,
        "source_binding": source_binding,
        "permission_evidence_refs": sorted(permission_refs),
        "provenance_edge_ids": sorted(provenance_refs),
        "evidence_refs": sorted(evidence_refs),
        "record_hash": record_hash,
    }


def synthetic_catalog_payload(
    *,
    catalog_id: str = "synthetic-catalog-1",
    catalog_version: str = "1",
    profile_id: str = "hxforge.shell_geometry_catalog.v1",
    authority: str = _SYNTHETIC_AUTHORITY,
    source_revision: str = "synthetic-1",
    records: tuple[dict[str, Any], ...] = (),
    evidence_bundle_hash: str = "",
    effective_at: str | None = "1970-01-01T00:00:00Z",
    catalog_hash_override: str | None = None,
    evidence_bundle_hash_override: str | None = None,
    extra_fields: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one TASK-023 shell-geometry catalog payload.

    The ``catalog_hash`` covers every other field plus the canonical
    ``(geometry_id, revision, record_hash)``-sorted record_hash
    sequence. Callers may override ``catalog_hash`` or
    ``evidence_bundle_hash`` for negative tests.
    """
    sorted_records_for_hash = sorted(
        records, key=lambda r: (r["geometry_id"], r["revision"], r["record_hash"])
    )
    record_hashes = [r["record_hash"] for r in sorted_records_for_hash]
    ebh = (
        evidence_bundle_hash_override
        if evidence_bundle_hash_override is not None
        else evidence_bundle_hash
    )
    catalog_hash_payload = {
        "schema_version": "task023.approved-shell-geometry-catalog.v1",
        "catalog_id": catalog_id,
        "catalog_version": catalog_version,
        "profile_id": profile_id,
        "authority": authority,
        "source_revision": source_revision,
        "effective_at": effective_at,
        "evidence_bundle_hash": ebh,
        "record_hashes": record_hashes,
    }
    catalog_hash = (
        catalog_hash_override
        if catalog_hash_override is not None
        else canonical_sha256(catalog_hash_payload)
    )
    payload = {
        "schema_version": "task023.approved-shell-geometry-catalog.v1",
        "catalog_id": catalog_id,
        "catalog_version": catalog_version,
        "profile_id": profile_id,
        "authority": authority,
        "source_revision": source_revision,
        "records": list(records),
        "evidence_bundle_hash": ebh,
        "catalog_hash": catalog_hash,
        "effective_at": effective_at,
    }
    if extra_fields:
        payload.update(dict(extra_fields))
    return payload


def assemble_synthetic_catalog_and_bundle(
    *,
    record_payloads: tuple[dict[str, Any], ...] = (),
    permission_payloads: tuple[dict[str, Any], ...] = (),
    edge_payloads: tuple[dict[str, Any], ...] = (),
    catalog_id: str = "synthetic-catalog-1",
    catalog_version: str = "1",
    authority: str = _SYNTHETIC_AUTHORITY,
    source_revision: str = "synthetic-1",
    effective_at: str | None = "1970-01-01T00:00:00Z",
    bundle_approval_status: str = "approved",
    bundle_id: str = "synthetic-bundle-1",
    bundle_version: str = "1",
    bundle_local_kernel_usage_scope: tuple[str, ...] = ("internal_runtime",),
    bundle_evidence_refs: tuple[str, ...] = ("synthetic.bundle.evidence.1",),
    task012_validation_hash: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a self-consistent (catalog, bundle) payload pair.

    The ``record_payloads`` MUST already be in canonical form
    (sorted refs, recomputed ``record_hash``); the helper wires them
    through the parser's exact hash domains.
    """
    bundle = synthetic_bundle_payload(
        bundle_id=bundle_id,
        bundle_version=bundle_version,
        approval_status=bundle_approval_status,
        permission_evidence=permission_payloads,
        provenance_edges=edge_payloads,
        local_kernel_usage_scope=bundle_local_kernel_usage_scope,
        evidence_refs=bundle_evidence_refs,
        task012_validation_hash=task012_validation_hash,
    )
    catalog = synthetic_catalog_payload(
        catalog_id=catalog_id,
        catalog_version=catalog_version,
        authority=authority,
        source_revision=source_revision,
        records=record_payloads,
        evidence_bundle_hash=bundle["bundle_hash"],
        effective_at=effective_at,
    )
    return catalog, bundle


__all__ = [
    "assemble_synthetic_catalog_and_bundle",
    "synthetic_bundle_payload",
    "synthetic_catalog_payload",
    "synthetic_edge_payload",
    "synthetic_permission_payload",
    "synthetic_record_payload",
]


def _hex_of_dict(payload: Mapping[str, Any]) -> str:
    """Hex digest over a JSON dump with sorted keys. Internal helper
    used only by tests that need to debug hash recomputations. Not
    exported in ``__all__``.
    """
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
