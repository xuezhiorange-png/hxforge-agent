"""Frozen enums, structural constants, and typed-dict aliases for the
TASK-013 material / cost data governance runtime.

All enums are derived directly from the TASK-013 frozen design
contract (docs/tasks/TASK-013-material-cost-data-governance.md,
Frozen Contract Authority SHA
``ee7aa092bca854316be961b536c7a121490aa385``):

* Section 4 — five TASK-013-specific source-class values
  (closed set; intentionally distinct from the TASK-012 rule
  source classes).
* Section 5.1 — ``material_family`` closed set (16 tokens).
* Section 5.2 — ``form_factor`` closed set (17 tokens).
* Section 5.3.1 — ``issuing_body`` closed set (15 tokens).
* Section 6.1 — ``cost_category`` closed set (18 tokens).
* Section 6.2 — ``cost_basis`` closed set (7 tokens).
* Section 6.3 — ``quantity_basis`` closed set (8 tokens).
* Section 12 — ``quality_flags`` closed set (11 tokens).
* Section 13 — TASK-013-specific approval ladder (10 states).

The TASK-013-specific taxonomy is NOT a replacement for the TASK-012
rule source-class taxonomy; both coexist.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, NotRequired, TypedDict


class SourceClass(StrEnum):
    """TASK-013-specific source-class closed set (Section 4).

    Distinct from the TASK-012 rule source-class taxonomy. The TASK-012
    taxonomy is governed by
    :class:`hexagent.rule_packs.models.SourceClass` and remains
    unchanged by TASK-013.
    """

    INTERNAL_ENGINEERING_ASSUMPTION = "INTERNAL_ENGINEERING_ASSUMPTION"
    PUBLIC_METADATA = "PUBLIC_METADATA"
    VENDOR_PERMISSIONED = "VENDOR_PERMISSIONED"
    USER_PROVIDED_PROJECT_DATA = "USER_PROVIDED_PROJECT_DATA"
    RESTRICTED_REFERENCE_METADATA_ONLY = "RESTRICTED_REFERENCE_METADATA_ONLY"


# Source classes allowed to carry numeric consumable values (i.e.
# property_values / cost_value). See Section 5.5 rule #2 and
# Section 6.4 rule #2.
VALUE_CARRYING_SOURCE_CLASSES: frozenset[SourceClass] = frozenset(
    {
        SourceClass.INTERNAL_ENGINEERING_ASSUMPTION,
        SourceClass.PUBLIC_METADATA,
        SourceClass.VENDOR_PERMISSIONED,
        SourceClass.USER_PROVIDED_PROJECT_DATA,
    }
)


# Source classes allowed to carry numeric consumable values WITHOUT a
# usage_scope requirement. VENDOR_PERMISSIONED additionally requires
# usage_scope (Section 5.5 rule #2 / Section 6.4 rule #2).
SOURCE_CLASSES_REQUIRE_USAGE_SCOPE: frozenset[SourceClass] = frozenset(
    {SourceClass.VENDOR_PERMISSIONED}
)


class MaterialFamily(StrEnum):
    """Material family closed set (Section 5.1)."""

    CARBON_STEEL = "carbon_steel"
    LOW_ALLOY_STEEL = "low_alloy_steel"
    STAINLESS_STEEL = "stainless_steel"
    DUPLEX_STAINLESS = "duplex_stainless"
    NICKEL_ALLOY = "nickel_alloy"
    COPPER_ALLOY = "copper_alloy"
    ALUMINIUM_ALLOY = "aluminium_alloy"
    TITANIUM_ALLOY = "titanium_alloy"
    PLASTIC = "plastic"
    ELASTOMER = "elastomer"
    CERAMIC = "ceramic"
    GRAPHITE = "graphite"
    GLASS = "glass"
    COMPOSITE = "composite"
    REFRIGERANT = "refrigerant"
    PROCESS_FLUID = "process_fluid"
    UTILITY_FLUID = "utility_fluid"
    OTHER = "other"


class FormFactor(StrEnum):
    """Form-factor closed set (Section 5.2)."""

    PLATE = "plate"
    SHEET = "sheet"
    BAR = "bar"
    BILLET = "billet"
    TUBE = "tube"
    PIPE = "pipe"
    FITTING = "fitting"
    FLANGE = "flange"
    FORGING = "forging"
    CASTING = "casting"
    BRAZED_ASSEMBLY = "brazed_assembly"
    WELDED_ASSEMBLY = "welded_assembly"
    GASKET = "gasket"
    FASTENER = "fastener"
    FLUID_BULK = "fluid_bulk"
    FLUID_CHARGE = "fluid_charge"
    OTHER = "other"


class IssuingBody(StrEnum):
    """Issuing body closed set (Section 5.3.1)."""

    ASME = "ASME"
    ASTM = "ASTM"
    ISO = "ISO"
    EN = "EN"
    GB = "GB"
    JIS = "JIS"
    DIN = "DIN"
    NFPA = "NFPA"
    TEMA = "TEMA"
    API = "API"
    AWS = "AWS"
    ASHRAE = "ASHRAE"
    IIAR = "IIAR"
    EIGA = "EIGA"
    INTERNAL = "INTERNAL"
    OTHER = "OTHER"


class CostCategory(StrEnum):
    """Cost category closed set (Section 6.1)."""

    MATERIAL_UNIT_PRICE = "material_unit_price"
    MATERIAL_TOTAL_COST = "material_total_cost"
    FABRICATION_LABOR = "fabrication_labor"
    FABRICATION_OVERHEAD = "fabrication_overhead"
    INSTALLATION_LABOR = "installation_labor"
    ENGINEERING_HOURS = "engineering_hours"
    TRANSPORTATION = "transportation"
    TAXES_AND_DUTIES = "taxes_and_duties"
    OPERATING_ENERGY = "operating_energy"
    OPERATING_UTILITY = "operating_utility"
    MAINTENANCE = "maintenance"
    INSURANCE = "insurance"
    DECOMMISSIONING = "decommissioning"
    COMPLIANCE_PERMIT = "compliance_permit"
    COST_ESCALATION_INDEX = "cost_escalation_index"
    PRICE_INDEX = "price_index"
    OTHER = "other"


# Cost categories reserved for escalation index records themselves
# (Section 11). They MUST NOT be used to tag the cost items being
# escalated.
ESCALATION_INDEX_CATEGORIES: frozenset[CostCategory] = frozenset(
    {CostCategory.COST_ESCALATION_INDEX, CostCategory.PRICE_INDEX}
)


class CostBasis(StrEnum):
    """Cost basis closed set (Section 6.2)."""

    VENDOR_QUOTE = "vendor_quote"
    VENDOR_CATALOG_LISTING = "vendor_catalog_listing"
    INTERNAL_ASSUMPTION = "internal_assumption"
    PUBLIC_INDEX = "public_index"
    PROJECT_SPECIFIC_INPUT = "project_specific_input"
    ENGINEERING_ESTIMATE = "engineering_estimate"
    OTHER = "other"


class QuantityBasis(StrEnum):
    """Quantity basis closed set (Section 6.3)."""

    PER_MASS = "per_mass"
    PER_LENGTH = "per_length"
    PER_AREA = "per_area"
    PER_VOLUME = "per_volume"
    PER_UNIT = "per_unit"
    PER_ENERGY = "per_energy"
    PER_TIME = "per_time"
    LUMP_SUM = "lump_sum"
    OTHER = "other"


class QualityFlag(StrEnum):
    """Quality flag closed set (Section 12)."""

    ASSUMED_VALUE = "assumed_value"
    ENGINEERING_ESTIMATE = "engineering_estimate"
    FIELD_MEASURED = "field_measured"
    VENDOR_CERTIFIED = "vendor_certified"
    THIRD_PARTY_TESTED = "third_party_tested"
    STALE_5Y = "stale_>5y"
    PENDING_REVIEW = "pending_review"
    METADATA_ONLY_NO_VALUE = "metadata_only_no_value"
    ESCALATION_UNCERTAIN = "escalation_uncertain"
    CURRENCY_CONVERSION_INFERRED = "currency_conversion_inferred"
    REGION_PROXY_USED = "region_proxy_used"


class ApprovalState(StrEnum):
    """TASK-013-specific approval state machine (Section 13).

    Distinct from the TASK-012 rule-pack approval ladder: adds
    ``needs_value_normalization`` and ``needs_unit_validation`` for
    the canonical value payloads introduced in Section 5.5 / 6.4,
    removes ``needs_expected_outputs``.
    """

    DRAFT = "draft"
    NEEDS_SOURCE = "needs_source"
    NEEDS_LICENSE_EVIDENCE = "needs_license_evidence"
    NEEDS_VALUE_NORMALIZATION = "needs_value_normalization"
    NEEDS_UNIT_VALIDATION = "needs_unit_validation"
    NEEDS_RECORD_VALIDATION = "needs_record_validation"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


# Gate ordering (Section 13 gate-semantics table).
APPROVAL_GATE_ORDER: tuple[ApprovalState, ...] = (
    ApprovalState.DRAFT,
    ApprovalState.NEEDS_SOURCE,
    ApprovalState.NEEDS_LICENSE_EVIDENCE,
    ApprovalState.NEEDS_VALUE_NORMALIZATION,
    ApprovalState.NEEDS_UNIT_VALIDATION,
    ApprovalState.NEEDS_RECORD_VALIDATION,
    ApprovalState.UNDER_REVIEW,
    ApprovalState.APPROVED,
)


# ---------------- TypedDict aliases (structural) --------------------


class EngineeringPropertyDescriptor(TypedDict):
    """Metadata descriptor (Section 5.4). NOT a numeric quantity."""

    declared_unit: str
    declared_envelope: NotRequired[Any]
    declared_source_pointer: NotRequired[str]
    declared_quality_flags: list[str]
    declared_uncertainty: NotRequired[Any]


class PropertyValue(TypedDict):
    """Canonical consumable engineering value (Section 5.5)."""

    property_name: str
    value_si: str  # decimal string per RFC 8785 §3.3.1
    unit_si: str
    applicability_envelope: NotRequired[Any]
    uncertainty: NotRequired[Any]
    source_pointer: str
    quality_flags: list[str]


class StandardOrSpecReference(TypedDict, total=False):
    """Metadata-only bibliographic reference (Section 5.3)."""

    issuing_body: str
    designation: str
    edition_year: int
    clause_locator: str
    bibliographic_metadata: dict[str, Any]


class HumanEnteredEvidence(TypedDict, total=False):
    """Optional evidence block (Section 5 / 6 last row).

    Required when ``source_class`` is ``USER_PROVIDED_PROJECT_DATA``,
    ``INTERNAL_ENGINEERING_ASSUMPTION``, or ``VENDOR_PERMISSIONED``.
    """

    actor: str
    entered_at: str  # RFC 3339 UTC
    permission_scope: list[str]  # vendor scope tokens
    usage_scope: str  # free-text justification when source_class is VENDOR_PERMISSIONED
    justification: str  # required when issuing_body == OTHER


class MaterialRecord(TypedDict, total=False):
    """TASK-013 material record (Section 5)."""

    material_record_id: str
    material_record_version: str
    material_family: str
    material_grade_or_designation: str
    form_factor: str
    standard_or_spec_reference: StandardOrSpecReference
    region: str
    effective_date: str
    retirement_date: str
    source_class: str
    source_reference: str
    license_evidence: str
    engineering_properties: dict[str, EngineeringPropertyDescriptor]
    property_values: list[PropertyValue]
    dimensional_units: dict[str, str]
    quality_flags: list[str]
    uncertainty: dict[str, Any]
    approval_state: str
    supersedes: list[str]
    superseded_by: str
    provenance_edges: list[str]
    human_entered_evidence: HumanEnteredEvidence
    record_hash: str


class CostValue(TypedDict, total=False):
    """Canonical consumable cost value (Section 6.4)."""

    value: str
    currency: str
    quantity_value_si: str
    unit_basis: str
    normalized_unit_price: str
    escalation_index_reference: str
    source_pointer: str
    uncertainty_band: dict[str, Any]


class CostRecord(TypedDict, total=False):
    """TASK-013 cost record (Section 6)."""

    cost_record_id: str
    cost_record_version: str
    cost_category: str
    cost_basis: str
    currency: str
    region: str
    effective_date: str
    escalation_date: str
    quantity_basis: str
    unit_basis: str
    source_class: str
    source_reference: str
    license_evidence: str
    uncertainty_band: dict[str, Any]
    cost_value: CostValue
    quality_flags: list[str]
    approval_state: str
    supersedes: list[str]
    superseded_by: str
    provenance_edges: list[str]
    human_entered_evidence: HumanEnteredEvidence
    record_hash: str


# Required field sets per record type (used by schema validation).
MATERIAL_RECORD_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {
        "material_record_id",
        "material_record_version",
        "material_family",
        "material_grade_or_designation",
        "form_factor",
        "region",
        "effective_date",
        "source_class",
        "source_reference",
        "license_evidence",
        "dimensional_units",
        "quality_flags",
        "approval_state",
        "provenance_edges",
        "record_hash",
    }
)

COST_RECORD_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {
        "cost_record_id",
        "cost_record_version",
        "cost_category",
        "cost_basis",
        "currency",
        "region",
        "effective_date",
        "quantity_basis",
        "unit_basis",
        "source_class",
        "source_reference",
        "license_evidence",
        "quality_flags",
        "approval_state",
        "provenance_edges",
        "record_hash",
    }
)


# Required human_entered_evidence when the source_class is one of
# USER_PROVIDED_PROJECT_DATA / INTERNAL_ENGINEERING_ASSUMPTION /
# VENDOR_PERMISSIONED (material record field table last-but-one row).
# The contract also requires it for cost records whose source_class is
# USER_PROVIDED_PROJECT_DATA or VENDOR_PERMISSIONED.
HUMAN_EVIDENCE_REQUIRED_MATERIAL_SOURCE_CLASSES: frozenset[SourceClass] = frozenset(
    {
        SourceClass.USER_PROVIDED_PROJECT_DATA,
        SourceClass.INTERNAL_ENGINEERING_ASSUMPTION,
        SourceClass.VENDOR_PERMISSIONED,
    }
)

HUMAN_EVIDENCE_REQUIRED_COST_SOURCE_CLASSES: frozenset[SourceClass] = frozenset(
    {
        SourceClass.USER_PROVIDED_PROJECT_DATA,
        SourceClass.VENDOR_PERMISSIONED,
    }
)


__all__ = [
    "APPROVAL_GATE_ORDER",
    "ApprovalState",
    "COST_RECORD_REQUIRED_FIELDS",
    "CostBasis",
    "CostCategory",
    "CostRecord",
    "CostValue",
    "ESCALATION_INDEX_CATEGORIES",
    "EngineeringPropertyDescriptor",
    "FormFactor",
    "HUMAN_EVIDENCE_REQUIRED_COST_SOURCE_CLASSES",
    "HUMAN_EVIDENCE_REQUIRED_MATERIAL_SOURCE_CLASSES",
    "HumanEnteredEvidence",
    "IssuingBody",
    "MATERIAL_RECORD_REQUIRED_FIELDS",
    "MaterialFamily",
    "MaterialRecord",
    "PropertyValue",
    "QualityFlag",
    "QuantityBasis",
    "SOURCE_CLASSES_REQUIRE_USAGE_SCOPE",
    "SourceClass",
    "StandardOrSpecReference",
    "VALUE_CARRYING_SOURCE_CLASSES",
]
