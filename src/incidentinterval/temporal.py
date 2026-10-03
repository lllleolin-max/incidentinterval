"""Integer simple temporal networks: x[target] - x[source] <= bound."""
from dataclasses import dataclass, asdict

ANCHOR = "@origin"


@dataclass(frozen=True, order=True)
class Edge:
    source: str
    target: str
    bound: int
    reason: str
    evidence: tuple = ()

    def json(self):
        result = asdict(self)
        result["evidence"] = list(self.evidence)
        return result


def bounds(event, window, reason, evidence=()):
    return [Edge(ANCHOR, event, window[1], reason + ":upper", tuple(evidence)),
            Edge(event, ANCHOR, -window[0], reason + ":lower", tuple(evidence))]


def delta(a, b, window, reason, evidence=()):
    return [Edge(a, b, window[1], reason + ":upper", tuple(evidence)),
            Edge(b, a, -window[0], reason + ":lower", tuple(evidence))]


def check_assignment(edges, assignment):
    """Independent O(E) certificate checker, requiring origin to be zero."""
    if assignment.get(ANCHOR) != 0:
        return False
    return all(e.source in assignment and e.target in assignment
               and assignment[e.target] - assignment[e.source] <= e.bound for e in edges)


def check_negative_cycle(edges, witness):
    """Check membership, a closed connected walk and strictly negative sum."""
    if not witness:
        return False
    known = set(edges)
    return (all(e in known for e in witness)
            and all(a.target == b.source for a, b in zip(witness, witness[1:] + witness[:1]))
            and sum(e.bound for e in witness) < 0)


def solve(nodes, edges, closure=True):
    """Bellman-Ford certificate, followed by all-pairs tight bounds if feasible."""
    nodes = sorted(set(nodes) | {ANCHOR})
    edges = sorted(set(edges))
    potential = dict.fromkeys(nodes, 0)
    previous = {}
    changed = None
    for _ in nodes:
        changed = None
        for edge in edges:
            if potential[edge.target] > potential[edge.source] + edge.bound:
                potential[edge.target] = potential[edge.source] + edge.bound
                previous[edge.target] = edge
                changed = edge.target
        if changed is None:
            break
    if changed is not None:
        node = changed
        for _ in nodes:
            node = previous[node].source
        cycle, cursor = [], node
        while True:
            edge = previous[cursor]
            cycle.append(edge)
            cursor = edge.source
            if cursor == node:
                break
        cycle.reverse()
        assert check_negative_cycle(edges, cycle)
        return {"status": "INFEASIBLE", "cycle": cycle, "edges": edges}
    offset = potential[ANCHOR]
    assignment = {n: value - offset for n, value in potential.items()}
    assert check_assignment(edges, assignment)
    result = {"status": "FEASIBLE", "assignment": assignment, "edges": edges}
    if not closure:
        return result
    inf = float("inf")
    dist = {a: {b: (0 if a == b else inf) for b in nodes} for a in nodes}
    for edge in edges:
        dist[edge.source][edge.target] = min(dist[edge.source][edge.target], edge.bound)
    for k in nodes:
        for a in nodes:
            if dist[a][k] == inf:
                continue
            for b in nodes:
                candidate = dist[a][k] + dist[k][b]
                if candidate < dist[a][b]:
                    dist[a][b] = candidate
    result["dist"] = dist
    return result


def window(result, a, b):
    """Tight range of x[b]-x[a] for a feasible network with finite bounds."""
    return [-result["dist"][b][a], result["dist"][a][b]]


def public(result, relations=False):
    out = {"status": result["status"], "constraints": [e.json() for e in result["edges"]]}
    if result["status"] == "INFEASIBLE":
        out["contradiction"] = {"kind": "negative_cycle", "edges": [e.json() for e in result["cycle"]],
                                "sum_upper_bounds": sum(e.bound for e in result["cycle"])}
        return out
    out["assignment"] = result["assignment"]
    if "dist" in result:
        nodes = sorted(set(result["assignment"]) - {ANCHOR})
        out["event_intervals"] = {n: window(result, ANCHOR, n) for n in nodes}
        if relations:
            pairs = []
            for i, a in enumerate(nodes):
                for b in nodes[i + 1:]:
                    lo, hi = window(result, a, b)
                    relation = ("equal" if lo == hi == 0 else "strictly_before" if lo > 0
                                else "strictly_after" if hi < 0 else "before_or_equal" if lo == 0
                                else "after_or_equal" if hi == 0 else "unresolved")
                    pairs.append({"a": a, "b": b, "delta": [lo, hi], "relation": relation})
            out["partial_order"] = pairs
    return out
