"""R2A certificate provenance classification (fixture vs production immutable)."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Final, Literal

CertificateProvenance = Literal[
    "CONTRACT_FIXTURE_RECONSTRUCTION",
    "PRODUCTION_IMMUTABLE_ARTIFACT",
]

FIXTURE_ORIGIN_MARK: Final = "CONTRACT_FIXTURE_RECONSTRUCTION"
PRODUCTION_ORIGIN_MARK: Final = "PRODUCTION_IMMUTABLE_ARTIFACT"
FIXTURE_CERTIFICATE_SCHEMA_TAG: Final = "task173.r2a.contract-fixture-certificate.v1"
