"""Tests for provenance graph validation (Section 11)."""

from __future__ import annotations

import pytest

from hexagent.rule_packs.errors import RulePackValidationError
from hexagent.rule_packs.provenance import validate_provenance_edges, validate_supersedes_edges


def test_provenance_passes_minimal_graph() -> None:
    rules = {"r1": {"rule_id": "r1"}}
    edges = [
        {
            "edge_id": "e1",
            "from_rule_id": "external:PUBLIC_DOMAIN:foo",
            "to_rule_id": "r1",
            "relation": "paraphrases",
            "evidence_ref": "ext:foo",
        }
    ]
    validate_provenance_edges(rules, edges)


def test_provenance_rejects_missing_edge_per_rule() -> None:
    rules = {"r1": {"rule_id": "r1"}, "r2": {"rule_id": "r2"}}
    edges = [
        {
            "edge_id": "e1",
            "from_rule_id": "external:PUBLIC_DOMAIN:foo",
            "to_rule_id": "r1",
            "relation": "paraphrases",
            "evidence_ref": "ext:foo",
        }
    ]
    with pytest.raises(RulePackValidationError):
        validate_provenance_edges(rules, edges)


def test_provenance_rejects_cycle() -> None:
    rules = {"r1": {"rule_id": "r1"}, "r2": {"rule_id": "r2"}}
    edges = [
        {
            "edge_id": "e1",
            "from_rule_id": "external:PUBLIC_DOMAIN:foo",
            "to_rule_id": "r1",
            "relation": "derived_from",
            "evidence_ref": "ext:foo",
        },
        {
            "edge_id": "e2",
            "from_rule_id": "r1",
            "to_rule_id": "r2",
            "relation": "derived_from",
            "evidence_ref": "e1",
        },
        {
            "edge_id": "e3",
            "from_rule_id": "r2",
            "to_rule_id": "r1",
            "relation": "derived_from",
            "evidence_ref": "e2",
        },
    ]
    with pytest.raises(RulePackValidationError) as exc:
        validate_provenance_edges(rules, edges)
    assert "cycle" in str(exc.value).lower()


def test_provenance_rejects_unknown_internal_reference() -> None:
    rules = {"r1": {"rule_id": "r1"}}
    edges = [
        {
            "edge_id": "e1",
            "from_rule_id": "r2",  # not in rules
            "to_rule_id": "r1",
            "relation": "derived_from",
            "evidence_ref": "ext:foo",
        }
    ]
    with pytest.raises(RulePackValidationError):
        validate_provenance_edges(rules, edges)


def test_provenance_rejects_duplicate_edge_id() -> None:
    rules = {"r1": {"rule_id": "r1"}}
    edges = [
        {
            "edge_id": "e1",
            "from_rule_id": "external:PUBLIC_DOMAIN:foo",
            "to_rule_id": "r1",
            "relation": "paraphrases",
            "evidence_ref": "ext:foo",
        },
        {
            "edge_id": "e1",
            "from_rule_id": "external:PUBLIC_DOMAIN:bar",
            "to_rule_id": "r1",
            "relation": "paraphrases",
            "evidence_ref": "ext:bar",
        },
    ]
    with pytest.raises(RulePackValidationError):
        validate_provenance_edges(rules, edges)


def test_provenance_rejects_missing_required_field() -> None:
    rules = {"r1": {"rule_id": "r1"}}
    edges = [
        {
            "edge_id": "e1",
            "from_rule_id": "external:PUBLIC_DOMAIN:foo",
            "to_rule_id": "r1",
            # missing relation and evidence_ref
        }
    ]
    with pytest.raises(RulePackValidationError):
        validate_provenance_edges(rules, edges)


def test_supersedes_edge_to_external_source_passes() -> None:
    rules = {"r1": {"rule_id": "r1"}}
    edges = [
        {
            "edge_id": "e1",
            "from_rule_id": "r1",
            "to_rule_id": "external:PUBLIC_DOMAIN:prior-v1",
            "relation": "supersedes",
            "evidence_ref": "ext:prior-v1",
        }
    ]
    validate_supersedes_edges(rules, edges)


def test_supersedes_edge_to_unknown_rejected() -> None:
    rules = {"r1": {"rule_id": "r1"}}
    edges = [
        {
            "edge_id": "e1",
            "from_rule_id": "r1",
            "to_rule_id": "prior_unknown",
            "relation": "supersedes",
            "evidence_ref": "ext:prior",
        }
    ]
    with pytest.raises(RulePackValidationError):
        validate_supersedes_edges(rules, edges)
