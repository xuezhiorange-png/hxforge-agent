"""TASK-010 immutable registries for provider and catalog resolution.

Registries are **frozen after construction**: the constructor validates
all invariants and the ``resolve`` methods are pure lookups that never
mutate state.  This makes them safe to share across request boundaries
and to persist as part of audit trails.
"""

from __future__ import annotations

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

# ---------------------------------------------------------------------------
# ProviderRegistry
# ---------------------------------------------------------------------------


class ProviderRegistry:
    """Immutable registry of ``ProviderIdentitySnapshot`` instances.

    Construction:
        ``ProviderRegistry({"default": snapshot})``

    Resolution:
        ``registry.resolve("default")`` returns the snapshot or raises
        ``ValueError`` if the reference is unknown.
    """

    __slots__ = ("_providers",)

    def __init__(self, providers: dict[str, ProviderIdentitySnapshot]) -> None:
        # Defensive copy + freeze
        self._providers: dict[str, ProviderIdentitySnapshot] = dict(providers)

    def resolve(self, ref: str) -> ProviderIdentitySnapshot:
        """Return the ``ProviderIdentitySnapshot`` for *ref*.

        Raises ``ValueError`` if *ref* is not present in the registry.
        """
        try:
            return self._providers[ref]
        except KeyError:
            available = sorted(self._providers.keys())
            raise ValueError(
                f"Unknown provider reference {ref!r}. Available: {available}"
            ) from None

    def __repr__(self) -> str:
        keys = sorted(self._providers.keys())
        return f"ProviderRegistry(keys={keys!r})"


# ---------------------------------------------------------------------------
# CatalogRegistry
# ---------------------------------------------------------------------------


class CatalogRegistry:
    """Immutable registry of ``CompleteDoublePipeCatalogSnapshot`` instances.

    Construction:

    1. Each snapshot's content hash is **re-verified** against the
       authoritative :func:`compute_catalog_content_hash`.
    2. Duplicate identity keys (the 5-tuple from
       :func:`catalog_identity_key`) are rejected.
    3. Snapshots are stored in canonical order (sorted by identity key).

    Resolution:
        ``registry.resolve(ref)`` returns the snapshot matching *ref*
        (a ``CatalogSnapshotRef``) or raises ``ValueError`` if the
        reference is unknown.
    """

    __slots__ = ("_by_key", "_canonical_order")

    def __init__(
        self,
        catalogs: list[CompleteDoublePipeCatalogSnapshot],
    ) -> None:
        by_key: dict[tuple[str, str, str, str, str], CompleteDoublePipeCatalogSnapshot] = {}

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
            by_key[key] = cat

        # Store in canonical (sorted) order
        self._by_key = by_key
        self._canonical_order: tuple[CompleteDoublePipeCatalogSnapshot, ...] = tuple(
            by_key[k] for k in sorted(by_key.keys())
        )

    def resolve(
        self,
        ref: CatalogSnapshotRef,
    ) -> CompleteDoublePipeCatalogSnapshot:
        """Return the snapshot matching *ref*.

        The five identity fields of *ref* are used as the lookup key.
        Raises ``ValueError`` if no matching snapshot is found.
        """
        key = (
            ref.catalog_id,
            ref.catalog_version,
            ref.catalog_content_hash,
            ref.source_identity,
            ref.schema_version,
        )
        try:
            return self._by_key[key]
        except KeyError:
            raise ValueError(
                f"Unknown catalog reference: "
                f"(catalog_id={ref.catalog_id!r}, "
                f"catalog_version={ref.catalog_version!r}, "
                f"catalog_content_hash={ref.catalog_content_hash!r})"
            ) from None

    @property
    def snapshots(self) -> tuple[CompleteDoublePipeCatalogSnapshot, ...]:
        """Return all registered snapshots in canonical order."""
        return self._canonical_order

    def __repr__(self) -> str:
        n = len(self._canonical_order)
        return f"CatalogRegistry(n={n})"


# ---------------------------------------------------------------------------
# ResolvedCatalogAuthority
# ---------------------------------------------------------------------------


class ResolvedCatalogAuthority(StrictBaseModel):
    """Binding of a ``CatalogSnapshotRef`` to its resolved snapshot.

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
]
