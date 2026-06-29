"""TASK-010 immutable registries for provider and catalog resolution.

Registries are **frozen after construction**: the constructor validates
all invariants and the ``resolve`` methods are pure lookups that never
mutate state.  This makes them safe to share across request boundaries
and to persist as part of audit trails.
"""

from __future__ import annotations

from collections.abc import Sequence
from types import MappingProxyType

from hexagent.api.models import (
    CatalogSnapshotReference,
    ResolvedProviderAuthority,
    canonical_provider_identity_payload,
)
from hexagent.core.canonical import sha256_digest
from hexagent.core.heat_balance import ProviderIdentitySnapshot
from hexagent.domain.models import StrictBaseModel
from hexagent.optimization.catalog import (
    catalog_identity_key,
    compute_catalog_content_hash,
)
from hexagent.optimization.models import (
    CatalogSnapshotRef,
    CompleteDoublePipeCatalogSnapshot,
)

# --------------------------------------------------------------------------- #
# Canonical payload helpers                                                   #
# --------------------------------------------------------------------------- #


def canonical_catalog_authority_payload(
    ref: CatalogSnapshotRef,
    snapshot: CompleteDoublePipeCatalogSnapshot,
) -> dict[str, str | object]:
    """Return a canonical dict binding a catalog reference to its snapshot.

    The payload contains the five reference identity fields plus a dump
    of the snapshot's assembly options (sorted by ID, as per the
    ``CompleteDoublePipeCatalogSnapshot`` invariants).
    """
    return {
        "catalog_id": ref.catalog_id,
        "catalog_version": ref.catalog_version,
        "catalog_content_hash": ref.catalog_content_hash,
        "source_identity": ref.source_identity,
        "schema_version": ref.schema_version,
        "assembly_options": [opt.model_dump(mode="python") for opt in snapshot.assembly_options],
    }


# --------------------------------------------------------------------------- #
# ProviderRegistry                                                            #
# --------------------------------------------------------------------------- #


class ProviderRegistry:
    """Immutable registry of :class:`ProviderIdentitySnapshot` instances.

    Construction:
        ``ProviderRegistry({"default": snapshot})``

    Invariants (validated at construction):
        - No blank/empty/whitespace-only reference strings.
        - No duplicate reference strings (explicit check beyond dict dedup).
        - Internally stored as ``MappingProxyType`` (truly immutable).

    Resolution:
        ``registry.resolve("default")`` returns a
        :class:`ResolvedProviderAuthority` with auto-computed
        ``identity_digest``.

    The ``identity_digest`` is the ``sha256`` digest of the canonical
    payload produced by :func:`canonical_provider_identity_payload`.
    """

    __slots__ = ("_providers",)

    def __init__(
        self,
        providers: (
            dict[str, ProviderIdentitySnapshot] | Sequence[tuple[str, ProviderIdentitySnapshot]]
        ),
    ) -> None:
        # Normalize input to a list of (ref, snapshot) pairs for uniform processing
        items = list(providers.items()) if isinstance(providers, dict) else list(providers)

        # Validate keys: reject blank/empty/whitespace-only and detect duplicates
        seen: set[str] = set()
        clean: dict[str, ProviderIdentitySnapshot] = {}
        for ref, snapshot in items:
            if not isinstance(ref, str) or not ref.strip():
                raise ValueError(f"Provider reference must be a non-blank string, got {ref!r}")
            clean_ref = ref.strip()
            if clean_ref in seen:
                raise ValueError(f"Duplicate provider reference: {clean_ref!r}")
            seen.add(clean_ref)
            clean[clean_ref] = snapshot

        self._providers: MappingProxyType[str, ProviderIdentitySnapshot] = MappingProxyType(
            dict(clean)
        )

    def resolve(self, ref: str) -> ResolvedProviderAuthority:
        """Return the :class:`ResolvedProviderAuthority` for *ref*.

        Raises :class:`ValueError`` if *ref* is blank or not present.
        """
        if not isinstance(ref, str) or not ref.strip():
            raise ValueError(f"Provider reference must be a non-blank string, got {ref!r}")
        try:
            identity = self._providers[ref]
        except KeyError:
            available = sorted(self._providers.keys())
            raise ValueError(
                f"Unknown provider reference {ref!r}. Available: {available}"
            ) from None

        # Auto-compute identity_digest from canonical payload
        payload = canonical_provider_identity_payload(identity)
        identity_digest = sha256_digest(payload)

        return ResolvedProviderAuthority(
            provider_ref=ref,
            identity=identity,
            identity_digest=identity_digest,
        )

    def __repr__(self) -> str:
        keys = sorted(self._providers.keys())
        return f"ProviderRegistry(keys={keys!r})"


# --------------------------------------------------------------------------- #
# CatalogRegistry                                                             #
# --------------------------------------------------------------------------- #

# The 4-field identity key (without content hash) — used for duplicate
# identity-key detection with different content hashes.
_CATALOG_IDENTITY_KEY_TUPLE = tuple[str, str, str, str]


class CatalogRegistry:
    """Immutable registry of :class:`CompleteDoublePipeCatalogSnapshot` instances.

    Construction:

    1. Each snapshot's content hash is **re-verified** against the
       authoritative :func:`compute_catalog_content_hash`.
    2. Duplicate identity keys (the 5-tuple from
       :func:`catalog_identity_key`) are rejected.
    3. Same identity key with different content hash is rejected.
    4. Snapshots are stored in canonical order (sorted by 5-field identity key).
    5. Internally stored as ``MappingProxyType`` (truly immutable).

    Resolution:
        ``registry.resolve(ref)`` returns a
        :class:`ResolvedCatalogAuthority` (verified) matching *ref*.
    """

    __slots__ = ("_by_key", "_canonical_order")

    def __init__(
        self,
        catalogs: list[CompleteDoublePipeCatalogSnapshot],
    ) -> None:
        by_key: dict[tuple[str, str, str, str, str], CompleteDoublePipeCatalogSnapshot] = {}
        # Track 4-field identity keys to detect same-identity different-hash
        identity_to_hash: dict[tuple[str, str, str, str], str] = {}

        for cat in catalogs:
            # Re-verify content hash against authoritative computation
            expected_hash = compute_catalog_content_hash(
                catalog_id=cat.catalog_id,
                catalog_version=cat.catalog_version,
                source_identity=cat.source_identity,
                schema_version=cat.schema_version,
                assembly_options=cat.assembly_options,
            )
            if cat.catalog_content_hash != expected_hash:
                raise ValueError(
                    f"Catalog {cat.catalog_id!r}: content hash mismatch — "
                    f"claimed {cat.catalog_content_hash!r}, "
                    f"computed {expected_hash!r}"
                )

            key = catalog_identity_key(cat)
            if key in by_key:
                raise ValueError(f"Duplicate catalog identity key: {key!r}")

            # Check same identity key (4-field) with different content hash
            id_key: _CATALOG_IDENTITY_KEY_TUPLE = (
                cat.catalog_id,
                cat.catalog_version,
                cat.source_identity,
                cat.schema_version,
            )
            if id_key in identity_to_hash:
                existing_hash = identity_to_hash[id_key]
                if existing_hash != cat.catalog_content_hash:
                    raise ValueError(
                        f"Same catalog identity {id_key!r} with different "
                        f"content hash: {existing_hash!r} vs "
                        f"{cat.catalog_content_hash!r}"
                    )
            else:
                identity_to_hash[id_key] = cat.catalog_content_hash

            by_key[key] = cat

        # Store in canonical (sorted) order as frozen tuple
        self._canonical_order: tuple[CompleteDoublePipeCatalogSnapshot, ...] = tuple(
            by_key[k] for k in sorted(by_key.keys())
        )

        # Truly immutable mapping
        self._by_key: MappingProxyType[
            tuple[str, str, str, str, str], CompleteDoublePipeCatalogSnapshot
        ] = MappingProxyType(dict(by_key))

    def resolve(
        self,
        ref: CatalogSnapshotRef | CatalogSnapshotReference,
    ) -> ResolvedCatalogAuthority:
        """Return the :class:`ResolvedCatalogAuthority` matching *ref*.

        The five identity fields of *ref* are used as the lookup key.
        Raises :class:`ValueError`` if no matching snapshot is found.
        """
        key = (
            ref.catalog_id,
            ref.catalog_version,
            ref.catalog_content_hash,
            ref.source_identity,
            ref.schema_version,
        )
        try:
            snapshot = self._by_key[key]
        except KeyError:
            raise ValueError(
                f"Unknown catalog reference: "
                f"(catalog_id={ref.catalog_id!r}, "
                f"catalog_version={ref.catalog_version!r}, "
                f"catalog_content_hash={ref.catalog_content_hash!r})"
            ) from None

        # Ensure ref is a CatalogSnapshotRef (not a CatalogSnapshotReference)
        catalog_ref = CatalogSnapshotRef(
            catalog_id=ref.catalog_id,
            catalog_version=ref.catalog_version,
            catalog_content_hash=ref.catalog_content_hash,
            source_identity=ref.source_identity,
            schema_version=ref.schema_version,
        )
        return ResolvedCatalogAuthority(
            ref=catalog_ref,
            snapshot=snapshot,
            content_hash_verified=True,
        )

    @property
    def snapshots(self) -> tuple[CompleteDoublePipeCatalogSnapshot, ...]:
        """Return all registered snapshots in canonical order."""
        return self._canonical_order

    def __repr__(self) -> str:
        n = len(self._canonical_order)
        return f"CatalogRegistry(n={n})"


# --------------------------------------------------------------------------- #
# ResolvedCatalogAuthority                                                    #
# --------------------------------------------------------------------------- #


class ResolvedCatalogAuthority(StrictBaseModel):
    """Binding of a :class:`CatalogSnapshotRef` to its resolved snapshot.

    Produced by :meth:`CatalogRegistry.resolve` when the caller needs
    to carry both the reference and the resolved snapshot together,
    along with a flag indicating whether the content hash was verified
    during resolution.
    """

    ref: CatalogSnapshotRef
    snapshot: CompleteDoublePipeCatalogSnapshot
    content_hash_verified: bool


__all__ = [
    "CatalogRegistry",
    "ProviderRegistry",
    "ResolvedCatalogAuthority",
    "canonical_catalog_authority_payload",
    "canonical_provider_identity_payload",
]
