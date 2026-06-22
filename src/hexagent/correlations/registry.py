"""Correlation registry Protocol and InMemoryCorrelationRegistry."""

from __future__ import annotations

import copy
from typing import Protocol

from hexagent.correlations.applicability import assess_applicability
from hexagent.correlations.errors import (
    CorrelationDuplicateError,
    CorrelationError,
    CorrelationHashMismatchError,
    CorrelationNotFoundError,
    CorrelationVersionNotFoundError,
)
from hexagent.correlations.models import (
    ApplicabilityAssessment,
    CorrelationApplicabilityInput,
    CorrelationDefinition,
    CorrelationImplementationStatus,
    CorrelationKey,
    CorrelationPurpose,
    GeometryType,
    PhaseRegime,
    compare_semver,
    compute_definition_hash,
    parse_semver,
)
from hexagent.domain.messages import ErrorCode

SortKey = tuple[int, int, int, int, tuple[tuple[int, int | str], ...]]


def _version_sort_key(defn: CorrelationDefinition) -> SortKey:
    """Item 2: Sort key with SemVer prerelease precedence.

    Prerelease versions sort BEFORE stable of the same version number:
    1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-alpha.2 < 1.0.0-alpha.10 < 1.0.0-beta < 1.0.0

    SemVer prerelease precedence:
    - Numeric identifiers compared numerically
    - Alphanumeric identifiers compared lexically
    - Numeric < alphanumeric
    - Fewer identifiers < more identifiers (when prefix matches)
    """
    major, minor, patch, prerelease = parse_semver(defn.key.version)
    # Prerelease versions sort BEFORE stable:
    # stable: (major, minor, patch, 1, ())
    # pre:    (major, minor, patch, 0, prerelease_tuple)
    pre_flag = 0 if prerelease else 1
    return (major, minor, patch, pre_flag, prerelease)


class CorrelationRegistry(Protocol):
    """Protocol defining the correlation registry interface."""

    def register(self, definition: CorrelationDefinition) -> None: ...

    def get(self, key: CorrelationKey) -> CorrelationDefinition: ...

    def get_latest(
        self,
        correlation_id: str,
        *,
        include_prerelease: bool = False,
        include_deprecated: bool = False,
    ) -> CorrelationDefinition: ...

    def list_versions(self, correlation_id: str) -> tuple[CorrelationDefinition, ...]: ...

    def search(
        self,
        *,
        purpose: CorrelationPurpose | None = None,
        geometry: GeometryType | None = None,
        phase: PhaseRegime | None = None,
        implementation_status: CorrelationImplementationStatus | None = None,
        tags: frozenset[str] = frozenset(),
    ) -> tuple[CorrelationDefinition, ...]: ...

    def assess(
        self,
        key: CorrelationKey,
        inputs: CorrelationApplicabilityInput,
    ) -> ApplicabilityAssessment: ...


class InMemoryCorrelationRegistry:
    """Dict-backed in-memory correlation registry.

    - Deep copies on get/register to prevent external mutation.
    - Duplicate keys are rejected.
    - Same ID with multiple versions is allowed.
    - Version sorting: SemVer precedence with numeric prerelease comparison.
    - Default search excludes deprecated and withdrawn definitions.
    """

    def __init__(self) -> None:
        self._store: dict[CorrelationKey, CorrelationDefinition] = {}

    def register(self, definition: CorrelationDefinition) -> None:
        """Register a correlation definition.

        Raises CorrelationDuplicateError if the key already exists.
        Raises CorrelationHashMismatchError if the definition_hash is empty or wrong.
        Item 4: Reject empty definition_hash at registry boundary.
        Item 6: Always recomputes and verifies definition_hash on register.
        """
        key = definition.key

        # Item 4: Reject empty definition_hash — must be pre-computed via .create()
        if not definition.definition_hash:
            raise CorrelationHashMismatchError(
                key.correlation_id,
                expected="sha256:<computed>",
                actual="(empty)",
            )

        # Item 6: Always recompute and verify definition_hash
        computed_hash = compute_definition_hash(definition)
        if computed_hash != definition.definition_hash:
            raise CorrelationHashMismatchError(
                key.correlation_id,
                expected=definition.definition_hash,
                actual=computed_hash,
            )

        if key in self._store:
            raise CorrelationDuplicateError(
                key.correlation_id,
                key.version,
            )

        # Supersedes validation
        if definition.supersedes is not None:
            # Must share same correlation ID
            if definition.supersedes.correlation_id != key.correlation_id:
                raise CorrelationError(
                    ErrorCode.CORRELATION_NOT_FOUND,
                    "supersedes references different correlation ID: "
                    f"{definition.supersedes.correlation_id}",
                )
            # Must be earlier version (SemVer-aware comparison)
            if compare_semver(definition.supersedes.version, key.version) >= 0:
                raise CorrelationError(
                    ErrorCode.CORRELATION_NOT_FOUND,
                    f"supersedes version {definition.supersedes.version} must be earlier"
                    f" than {key.version}",
                )
            # Must exist in registry
            try:
                self.get(definition.supersedes)
            except (CorrelationNotFoundError, CorrelationVersionNotFoundError) as exc:
                raise CorrelationError(
                    ErrorCode.CORRELATION_NOT_FOUND,
                    "supersedes target not found: "
                    f"{definition.supersedes.correlation_id} "
                    f"v{definition.supersedes.version}",
                ) from exc

        self._store[key] = copy.deepcopy(definition)

    def get(self, key: CorrelationKey) -> CorrelationDefinition:
        """Get a specific correlation by key.
        Returns a deep copy.
        Raises CorrelationVersionNotFoundError if ID exists but version doesn't.
        Raises CorrelationNotFoundError if ID not found.
        """
        if key not in self._store:
            # Check if the ID exists but the version doesn't
            id_exists = any(k.correlation_id == key.correlation_id for k in self._store)
            if id_exists:
                raise CorrelationVersionNotFoundError(key.correlation_id, key.version)
            raise CorrelationNotFoundError(key.correlation_id, key.version)
        return copy.deepcopy(self._store[key])

    def get_latest(
        self,
        correlation_id: str,
        *,
        include_prerelease: bool = False,
        include_deprecated: bool = False,
    ) -> CorrelationDefinition:
        """Get the latest version of a correlation by ID.
        Latest = highest stable version. Prerelease only used if no
        stable version exists and include_prerelease is True.
        Excludes withdrawn definitions. Default excludes deprecated.
        """
        candidates = [
            defn for defn in self._store.values() if defn.key.correlation_id == correlation_id
        ]
        if not candidates:
            raise CorrelationNotFoundError(correlation_id)

        # Exclude withdrawn (always)
        candidates = [
            d
            for d in candidates
            if d.implementation_status != CorrelationImplementationStatus.withdrawn
        ]

        # Exclude deprecated unless opted in
        if not include_deprecated:
            candidates = [
                d
                for d in candidates
                if d.implementation_status != CorrelationImplementationStatus.deprecated
            ]

        if not candidates:
            raise CorrelationNotFoundError(correlation_id)

        # Separate stable and prerelease
        stable = [d for d in candidates if not parse_semver(d.key.version)[3]]
        prerelease = [d for d in candidates if parse_semver(d.key.version)[3]]

        if stable:
            latest = max(stable, key=_version_sort_key)
        elif include_prerelease and prerelease:
            latest = max(prerelease, key=_version_sort_key)
        else:
            raise CorrelationNotFoundError(correlation_id)

        return copy.deepcopy(latest)

    def list_versions(self, correlation_id: str) -> tuple[CorrelationDefinition, ...]:
        """List all versions of a correlation, sorted oldest to newest."""
        candidates = [
            defn for defn in self._store.values() if defn.key.correlation_id == correlation_id
        ]
        if not candidates:
            raise CorrelationNotFoundError(correlation_id)

        sorted_versions = sorted(candidates, key=_version_sort_key)
        return tuple(copy.deepcopy(d) for d in sorted_versions)

    def search(
        self,
        *,
        purpose: CorrelationPurpose | None = None,
        geometry: GeometryType | None = None,
        phase: PhaseRegime | None = None,
        implementation_status: CorrelationImplementationStatus | None = None,
        tags: frozenset[str] = frozenset(),
        include_deprecated: bool = False,
        include_withdrawn: bool = False,
    ) -> tuple[CorrelationDefinition, ...]:
        """Search correlations with optional filters.

        Item 7: Default search excludes deprecated and withdrawn.
        Returns matches sorted by correlation_id then version.
        """
        results: list[CorrelationDefinition] = []
        for defn in self._store.values():
            # Item 7: Exclude deprecated/withdrawn by default
            status = defn.implementation_status
            if not include_deprecated and status == CorrelationImplementationStatus.deprecated:
                continue
            if not include_withdrawn and status == CorrelationImplementationStatus.withdrawn:
                continue
            if purpose is not None and defn.purpose != purpose:
                continue
            if geometry is not None and geometry not in defn.geometry:
                continue
            if phase is not None and phase not in defn.phase_regimes:
                continue
            if (
                implementation_status is not None
                and defn.implementation_status != implementation_status
            ):
                continue
            if tags and not tags.issubset(defn.tags):
                continue
            results.append(defn)

        # Deterministic order: sort by correlation_id, then version
        results.sort(key=lambda d: (d.key.correlation_id, _version_sort_key(d)))
        return tuple(copy.deepcopy(d) for d in results)

    def assess(
        self,
        key: CorrelationKey,
        inputs: CorrelationApplicabilityInput,
    ) -> ApplicabilityAssessment:
        """Assess applicability for a registered correlation."""
        defn = self.get(key)
        return assess_applicability(defn, inputs)


__all__ = [
    "CorrelationRegistry",
    "InMemoryCorrelationRegistry",
]
