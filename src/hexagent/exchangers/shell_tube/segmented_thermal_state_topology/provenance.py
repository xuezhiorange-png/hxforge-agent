"""Typed acyclic authority/ownership/result graph; not fluid connectivity."""

from .errors import Code, Failure
from .models import Edge


def verify_edges(edges: tuple[Edge, ...]) -> tuple[Edge, ...]:
    pairs = [(e.source, e.target) for e in edges]
    if len(pairs) != len(set(pairs)):
        raise Failure(Code.PROVENANCE_INVALID, "duplicate_edge")
    graph: dict[str, set[str]] = {}
    indegree: dict[str, int] = {}
    for source, target in pairs:
        if not source or not target or source == target:
            raise Failure(Code.PROVENANCE_INVALID, "self_edge")
        graph.setdefault(source, set()).add(target)
        indegree.setdefault(source, 0)
        indegree[target] = indegree.get(target, 0) + 1
    ready = sorted(k for k, v in indegree.items() if v == 0)
    count = 0
    while ready:
        node = ready.pop()
        count += 1
        for child in sorted(graph.get(node, ())):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
    if count != len(indegree):
        raise Failure(Code.PROVENANCE_INVALID, "cycle")
    return tuple(Edge(source=a, target=b) for a, b in sorted(pairs))
