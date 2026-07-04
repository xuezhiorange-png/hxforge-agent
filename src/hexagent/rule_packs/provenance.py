"""Provenance graph validation (Section 11).

Each rule MUST carry at least one provenance edge. Edges form a connected
directed graph that allows an auditor to trace a rule back to its inputs
and review chain. The graph MUST be acyclic.

Provenance edges reference either:

* A real rule id within the same rule-pack (``from_rule_id``,
  ``to_rule_id``).
* An external source reference recorded in a ``external:<source_class>``
  namespace (``from_rule_id`` only).

Supersedes edges (relation = ``supersedes``) MUST point from a rule to a
prior rule_version that is recorded in the rule-pack's provenance edges.
"""

from __future__ import annotations

from typing import Any

from hexagent.rule_packs.errors import RulePackValidationError

PROVENANCE_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {"edge_id", "from_rule_id", "to_rule_id", "relation", "evidence_ref"}
)


def _is_external_source(rule_id: str) -> bool:
    """True if ``rule_id`` is an external source pointer (Section 11).

    External sources are recorded as ``external:<source_class>:<token>``.
    """
    return isinstance(rule_id, str) and rule_id.startswith("external:")


def validate_provenance_edges(
    rules: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
) -> None:
    """Validate the provenance edge list for a rule-pack.

    Raises ``RulePackValidationError`` with a precise ``path`` on any
    structural failure.
    """
    if not isinstance(edges, list):
        raise RulePackValidationError(
            "provenance_edges must be a list",
            path="provenance_edges",
        )
    seen_edge_ids: set[str] = set()
    for i, edge in enumerate(edges):
        path = f"provenance_edges[{i}]"
        for field in PROVENANCE_REQUIRED_FIELDS:
            if field not in edge:
                raise RulePackValidationError(
                    f"provenance edge missing required field {field!r}",
                    path=f"{path}.{field}",
                )
        edge_id = edge["edge_id"]
        if not isinstance(edge_id, str) or not edge_id:
            raise RulePackValidationError(
                "provenance edge edge_id must be a non-empty string",
                path=f"{path}.edge_id",
            )
        if edge_id in seen_edge_ids:
            raise RulePackValidationError(
                f"duplicate provenance edge_id {edge_id!r}",
                path=f"{path}.edge_id",
            )
        seen_edge_ids.add(edge_id)
        from_id = edge["from_rule_id"]
        to_id = edge["to_rule_id"]
        if not _is_external_source(from_id) and from_id not in rules:
            raise RulePackValidationError(
                f"provenance edge from_rule_id {from_id!r} does not match "
                "any rule in this rule-pack or an external source",
                path=f"{path}.from_rule_id",
            )
        if to_id not in rules:
            raise RulePackValidationError(
                f"provenance edge to_rule_id {to_id!r} does not match any rule in this rule-pack",
                path=f"{path}.to_rule_id",
            )

    # Every rule MUST have at least one provenance edge.
    referenced: set[str] = set()
    for edge in edges:
        to_id = edge["to_rule_id"]
        if isinstance(to_id, str):
            referenced.add(to_id)
    for rule_id in rules:
        if rule_id not in referenced:
            raise RulePackValidationError(
                f"rule {rule_id!r} has no provenance edge pointing to it "
                "(Section 11.1: every rule MUST list at least one edge)",
                path=f"rules[{rule_id}].provenance_edges",
            )

    # Acyclicity: edges from rules to rules form a DAG rooted at external
    # sources. We DFS from each rule and detect cycles.
    _assert_no_cycles(rules, edges)


def _assert_no_cycles(
    rules: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
) -> None:
    """Detect cycles in the rule-to-rule provenance subgraph.

    The cycle check excludes external sources (which are roots, not targets).
    """
    # Adjacency list restricted to internal targets.
    adjacency: dict[str, list[str]] = {rule_id: [] for rule_id in rules}
    for edge in edges:
        from_id = edge["from_rule_id"]
        to_id = edge["to_rule_id"]
        if from_id in adjacency and to_id in adjacency:
            adjacency[from_id].append(to_id)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {rule_id: WHITE for rule_id in rules}

    def dfs(node: str, stack: list[str]) -> None:
        color[node] = GRAY
        stack.append(node)
        for nxt in adjacency[node]:
            if nxt not in color:
                # External target — skip.
                continue
            if color[nxt] == GRAY:
                cycle = " -> ".join(stack + [nxt])
                raise RulePackValidationError(
                    f"provenance cycle detected: {cycle} (Section 11.2)",
                    path=f"provenance_edges[{nxt}]",
                )
            if color[nxt] == WHITE:
                dfs(nxt, stack)
        stack.pop()
        color[node] = BLACK

    for rule_id in rules:
        if color[rule_id] == WHITE:
            dfs(rule_id, [])


def validate_supersedes_edges(
    rules: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
) -> None:
    """Validate that ``relation='supersedes'`` edges target a known rule.

    The superseded rule MAY be in the same rule-pack or a prior rule-pack
    recorded as an external source. We enforce that the target is either a
    rule id in this rule-pack or an ``external:`` pointer.
    """
    for i, edge in enumerate(edges):
        if edge.get("relation") != "supersedes":
            continue
        path = f"provenance_edges[{i}]"
        to_id = edge.get("to_rule_id")
        if to_id in rules:
            continue
        if isinstance(to_id, str) and to_id.startswith("external:"):
            continue
        raise RulePackValidationError(
            f"supersedes edge to_rule_id {to_id!r} must reference a rule "
            "in this rule-pack or an external source",
            path=f"{path}.to_rule_id",
        )
