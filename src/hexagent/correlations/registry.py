"""Correlation registry Protocol and InMemoryCorrelationRegistry."""

from __future__ import annotations

import copy
import re
from typing import Protocol

from hexagent.correlations.applicability import assess_applicability
from hexagent.correlations.errors import (
    CorrelationDuplicateError,
    CorrelationHashMismatchError,
    CorrelationNotFoundError,
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
)


def _parse_version(version: str) -> tuple[int, int, int, str]:
    """Parse semver string into (major, minor, patch, prerelease).

    Prerelease strings are sorted after the stable release of the same
    version number (e.g. 1.0.0-alpha < 1.0.0).
    """
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$", version)
    if not match:
        raise ValueError(f"Invalid version string: {version!r}")
    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    prerelease = match.group(4) or ""
    return (major, minor, patch, prerelease)


def _version_sort_key(defn: CorrelationDefinition) -> tuple[int, int, int, int, str]:
    """Sort key: stable versions first, then prerelease, sorted numerically."""
    major, minor, patch, prerelease = _parse_version(defn.key.version)
    # Prerelease versions sort after stable of same number:
    # (1,0,0,"") < (1,0,0,"alpha") is False, so we use a trick:
    # stable: (major, minor, patch, 0, "")
    # pre:    (major, minor, patch, 1, prerelease)
    pre_flag = 1 if prerelease else 0
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
    - Version sorting: numeric major.minor.patch, prerelease after stable.
    """

    def __init__(self) -> None:
        self._store: dict[CorrelationKey, CorrelationDefinition] = {}

    def register(self, definition: CorrelationDefinition) -> None:
        """Register a correlation definition.

        Raises CorrelationDuplicateError if the key already exists.
        Raises CorrelationHashMismatchError if the definition_hash doesn't match.
        """
        key = definition.key

        # Validate definition_hash
        if definition.definition_hash:
            from hexagent.core.canonical import sha256_digest

            # Build canonical payload excluding definition_hash
            dump = definition.model_dump()
            dump.pop("definition_hash", None)
            computed_hash = sha256_digest(dump)
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

        self._store[key] = copy.deepcopy(definition)

    def get(self, key: CorrelationKey) -> CorrelationDefinition:
        """Get a specific correlation by key.

        Returns a deep copy.
        Raises CorrelationNotFoundError if not found.
        """
        if key not in self._store:
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
        Excludes withdrawn correlations.
        """
        candidates = [
            defn for defn in self._store.values() if defn.key.correlation_id == correlation_id
        ]
        if not candidates:
            raise CorrelationNotFoundError(correlation_id)

        # Exclude withdrawn
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
        stable = [d for d in candidates if not _parse_version(d.key.version)[3]]
        prerelease = [d for d in candidates if _parse_version(d.key.version)[3]]

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
    ) -> tuple[CorrelationDefinition, ...]:
        """Search correlations with optional filters.

        Returns matches sorted by correlation_id then version.
        """
        results: list[CorrelationDefinition] = []
        for defn in self._store.values():
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
