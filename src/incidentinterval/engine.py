"""STN feasibility plus bounded, exact max-plus hypothesis/intervention analysis."""
from copy import deepcopy
from itertools import product
from math import prod
from .domain import parse, Limits
from .temporal import ANCHOR, Edge, bounds, delta, solve, public, window


MODEL_ASSUMPTIONS = [
    "All incoming causal links are necessary prerequisites (AND gating).",
    "Each nonroot time equals max(parent time + link delay); delays range independently.",
    "Root times lie in supplied activation windows; omitted causes and mechanism changes are excluded.",
    "Removal disables every downstream event under AND gating; prevention concerns impact start, not recovery.",
    "Model consistency and source references are not causal proof; simulated results are not observations.",
]


def graph(events, links):
    incoming = {n: [] for n in events}
    outgoing = {n: [] for n in events}
    for link in sorted(links, key=lambda x: x["id"]):
        incoming[link["to"]].append(link)
        outgoing[link["from"]].append(link)
    degree = {n: len(v) for n, v in incoming.items()}
    ready = sorted(n for n, degree in degree.items() if degree == 0)
    order = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for link in outgoing[node]:
            degree[link["to"]] -= 1
            if degree[link["to"]] == 0:
                ready.append(link["to"])
                ready.sort()
    if len(order) != len(events):
        return None, incoming, outgoing
    return order, incoming, outgoing


def descendants(seeds, outgoing):
    reached, stack = set(seeds), list(seeds)
    while stack:
        for link in outgoing[stack.pop()]:
            if link["to"] not in reached:
                reached.add(link["to"])
                stack.append(link["to"])
    return reached


def observed_edges(events, observations, impact):
    edges = []
    for n, event in events.items():
        edges += bounds(n, event["interval"], "event:" + n, event.get("evidence", []))
    for obs in observations.values():
        edges += delta(obs["from"], obs["to"], obs["delta"], "observation:" + obs["id"],
                       obs.get("evidence", []))
    if impact["start"] in events and impact["end"] in events:
        edges.append(Edge(impact["end"], impact["start"], 0, "impact:nonnegative"))
    return edges


def envelope(order, incoming, roots):
    result = {}
    for n in order:
        if not incoming[n]:
            result[n] = list(roots[n])
        else:
            result[n] = [max(result[e["from"]][k] + e["delay"][k] for e in incoming[n])
                         for k in (0, 1)]
    return result


def make_witness(result, chosen, links, impact, equality=None):
    if equality is not None:
        result = solve(result["assignment"], result["edges"] + delta(impact["start"], impact["end"],
                                                                    [equality, equality], "extremum"), False)
        assert result["status"] == "FEASIBLE"
    assignment = result["assignment"]
    delays = {link["id"]: (assignment[link["to"]] - assignment[link["from"]]
                           if chosen.get(link["to"]) == link["id"] else link["delay"][0])
              for link in links}
    witness = {"assignment": assignment, "delays": dict(sorted(delays.items())),
               "critical_parents": dict(sorted(chosen.items()))}
    if impact["start"] in assignment and impact["end"] in assignment:
        witness["impact_duration"] = assignment[impact["end"]] - assignment[impact["start"]]
    return witness


def max_model(events, observations, impact, hyp, limits):
    links = sorted(hyp["links"], key=lambda x: x["id"])
    order, incoming, outgoing = graph(events, links)
    if order is None:
        return {"status": "INVALID_MODEL", "reason": "causal cycle is outside the declared DAG subset",
                "blocked_events": sorted(n for n in events if incoming[n])}
    roots = {n for n in events if not incoming[n]}
    if roots != set(hyp["roots"]):
        return {"status": "INVALID_MODEL", "reason": "activation windows must exactly match graph roots",
                "expected_roots": sorted(roots), "declared_roots": sorted(hyp["roots"])}
    # The max equation is a union of STNs: every parent gives a lower bound,
    # and at least one selected parent gives an upper bound within its delay.
    base = observed_edges(events, observations, impact)
    support = envelope(order, incoming, hyp["roots"])
    for n in order:
        base += bounds(n, support[n], "model-envelope:" + n)
    for link in links:
        base.append(Edge(link["to"], link["from"], -link["delay"][0], "link:" + link["id"] + ":lower",
                         tuple(link.get("evidence", []))))
    nonroots = sorted(n for n in events if incoming[n])
    branch_count = prod(len(incoming[n]) for n in nonroots)
    temporal = solve(events, base)
    out = {"temporal": public(temporal, True), "branches_total": branch_count,
           "base_constraints": [e.json() for e in sorted(set(base))],
           "structural_envelopes": support}
    if temporal["status"] == "INFEASIBLE":
        return {**out, "status": "INFEASIBLE", "branches_tested": 0,
                "reason": "necessary temporal constraints already contradict observations or root assumptions"}
    if branch_count > limits.branches:
        return {**out, "status": "UNKNOWN_LIMIT", "branches_tested": 0,
                "reason": f"exact max model needs {branch_count} branches; limit is {limits.branches}"}
    feasible, failures = [], []
    for selection in product(*(incoming[n] for n in nonroots)):
        chosen = {n: link["id"] for n, link in zip(nonroots, selection)}
        branch_edges = base + [Edge(link["from"], link["to"], link["delay"][1],
                                   "link:" + link["id"] + ":critical-upper",
                                   tuple(link.get("evidence", []))) for link in selection]
        result = solve(events, branch_edges)
        if result["status"] == "INFEASIBLE":
            failures.append({"critical_parents": chosen, "contradiction": public(result)["contradiction"]})
        else:
            feasible.append((chosen, result))
    out["branches_tested"] = branch_count
    out["feasible_branches"] = len(feasible)
    if not feasible:
        return {**out, "status": "INFEASIBLE", "branch_failures": failures,
                "reason": "every possible max-equation critical-parent assignment is contradicted"}
    chosen, result = feasible[0]
    out.update(status="FEASIBLE", witness=make_witness(result, chosen, links, impact))
    # This path describes one feasible explanation, not an identified historical critical path.
    by_id = {x["id"]: x for x in links}
    cursor = impact["end"]
    path = [cursor] if cursor in events else []
    while cursor in chosen:
        cursor = by_id[chosen[cursor]]["from"]
        path.append(cursor)
    out["witness_critical_path"] = path[::-1]
    out["critical_parent_alternatives"] = {n: sorted({c[n] for c, _ in feasible}) for n in nonroots}
    if impact["start"] in events and impact["end"] in events:
        ranged = [(window(r, impact["start"], impact["end"]), c, r) for c, r in feasible]
        low = min(ranged, key=lambda x: (x[0][0], sorted(x[1].items())))
        high = max(ranged, key=lambda x: (x[0][1], sorted(x[1].items())))
        out["impact_duration"] = [low[0][0], high[0][1]]
        out["duration_extrema"] = [make_witness(low[2], low[1], links, impact, low[0][0]),
                                   make_witness(high[2], high[1], links, impact, high[0][1])]
        out["duration_kind"] = "exact integer min/max envelope; interior values may have gaps"
    return out


def changed_model(events, hyp, action):
    order, incoming, outgoing = graph(events, hyp["links"])
    if order is None:
        return None, {"status": "INVALID_MODEL", "reason": "baseline has a causal cycle"}
    unknown_roots = set(action.get("roots", {})) - set(hyp["roots"])
    if unknown_roots:
        return None, {"status": "INVALID_INTERVENTION", "reason": "time override targets nonroots in this hypothesis",
                      "events": sorted(unknown_roots)}
    removed = descendants(action.get("remove", []), outgoing)
    changed = set(action.get("roots", {}))
    for link in hyp["links"]:
        if link["id"] in action.get("delays", {}):
            changed.add(link["to"])
    affected = descendants(changed, outgoing) | removed
    active = {n: event for n, event in events.items() if n not in removed}
    altered = deepcopy(hyp)
    altered["roots"] = {n: action.get("roots", {}).get(n, value)
                        for n, value in hyp["roots"].items() if n not in removed}
    altered["links"] = [dict(link, delay=action.get("delays", {}).get(link["id"], link["delay"]))
                        for link in hyp["links"] if link["from"] not in removed and link["to"] not in removed]
    return (active, altered, affected, removed), None


def scenario(events, observations, impact, hyp, baseline, action, limits):
    transformed, error = changed_model(events, hyp, action)
    if error:
        return error
    active, altered, affected, removed = transformed
    if removed:
        historical = {"status": "INFEASIBLE", "contradiction": {"kind": "removed_observed_events",
                       "events": [{"id": n, "evidence": events[n].get("evidence", [])} for n in sorted(removed)]}}
    else:
        historical = max_model(events, observations, impact, altered, limits)
    preserve = action.get("preserve_observations", False)
    if preserve and removed:
        return {"status": "INFEASIBLE", "historical_compatibility": historical,
                "reason": "cannot both remove an observed event and preserve its observation"}
    retained = active if preserve else {n: event for n, event in active.items() if n not in affected}
    retained_obs = {n: obs for n, obs in observations.items()
                    if obs["from"] in retained and obs["to"] in retained}
    # Keep active node identities, but replace relaxed event windows with sound structural envelopes.
    order, incoming, _ = graph(active, altered["links"])
    support = envelope(order, incoming, altered["roots"])
    scenario_events = {n: event if n in retained else {"id": n, "interval": support[n], "evidence": []}
                       for n, event in active.items()}
    model = max_model(scenario_events, retained_obs, impact, altered, limits)
    out = {"status": model["status"], "historical_compatibility": historical,
           "counterfactual": model, "affected_events": sorted(affected), "removed_events": sorted(removed),
           "relaxed_event_observations": sorted(set(events) - set(retained)),
           "relaxed_difference_observations": sorted(set(observations) - set(retained_obs)),
           "conditions": action["assumptions"], "kind": "simulated_under_declared_hypothesis"}
    if model["status"] != "FEASIBLE":
        out["effect"] = "unidentified"
    elif impact["start"] in removed:
        out["effect"] = "impact_prevented_under_model"
        out["impact_duration"] = [0, 0]
    elif impact["end"] in removed:
        out["effect"] = "unidentified_recovery_removed"
    else:
        duration = model["impact_duration"]
        before = baseline["impact_duration"]
        improvement = [before[0] - duration[1], before[1] - duration[0]]
        out.update(impact_duration=duration, improvement_enclosure=improvement,
                   effect=("guaranteed_shorter_under_model" if improvement[0] > 0 else
                           "guaranteed_longer_under_model" if improvement[1] < 0 else
                           "equal_duration_under_model" if improvement == [0, 0] else "unidentified"),
                   comparison="conservative unpaired difference envelope; no shared-world effect estimate")
    return out


def analyze(data, *, limits=None):
    """Return JSON-compatible observations, competing models and conditional decisions.

    Raises InputError for malformed/unsupported JSON. UNKNOWN_LIMIT is a valid
    result: resource limits never certify infeasibility or safety.
    """
    limits = limits or Limits()
    sources, events, observations, hypotheses, interventions = parse(data, limits)
    impact = data["impact"]
    historical = solve(events, observed_edges(events, observations, impact))
    report = {"version": 1, "time_unit": data["time_unit"], "sources": sources,
              "observations": public(historical, True), "model_assumptions": MODEL_ASSUMPTIONS,
              "hypotheses": {}, "decisions": {},
              "causal_identification": "UNKNOWN: consistency does not prove a cause; supplied hypotheses are not exhaustive"}
    if historical["status"] == "INFEASIBLE":
        report["status"] = "INFEASIBLE_OBSERVATIONS"
        return report
    unknown_model = False
    for hid, hyp in hypotheses.items():
        model = max_model(events, observations, impact, hyp, limits)
        missing = sorted(link["id"] for link in hyp["links"] if not link.get("evidence"))
        entry = {"conditions": hyp["assumptions"], "missing_mechanism_evidence": missing,
                 "model": model, "interventions": {}}
        if model["status"] == "FEASIBLE":
            entry["status"] = "CONSISTENT_CONDITIONAL_MODEL"
            entry["interventions"] = {aid: scenario(events, observations, impact, hyp, model, action, limits)
                                      for aid, action in interventions.items()}
        elif model["status"] == "INFEASIBLE":
            entry["status"] = "CONTRADICTED_MODEL"
        else:
            entry["status"] = "UNKNOWN_MODEL"
            unknown_model = True
        report["hypotheses"][hid] = entry
    consistent = {h: e for h, e in report["hypotheses"].items() if e["model"]["status"] == "FEASIBLE"}
    report["status"] = "UNKNOWN" if unknown_model else "ANALYZED" if consistent else "NO_CONSISTENT_MODEL"
    for aid in interventions:
        effects = {h: e["interventions"][aid].get("effect", "unidentified") for h, e in consistent.items()}
        beneficial = {"impact_prevented_under_model", "guaranteed_shorter_under_model"}
        values = list(effects.values())
        missing = any(e["missing_mechanism_evidence"] for e in consistent.values())
        if not values or unknown_model or any(x.startswith("unidentified") for x in values):
            decision = "INSUFFICIENT_MODEL_INFORMATION"
        elif missing:
            decision = "NEEDS_MECHANISM_EVIDENCE"
        elif all(x in beneficial for x in values):
            decision = "CONDITIONAL_CANDIDATE"
        elif any(x in beneficial for x in values):
            decision = "HYPOTHESIS_SENSITIVE"
        elif all(x == "guaranteed_longer_under_model" for x in values):
            decision = "AVOID_UNDER_DECLARED_MODELS"
        else:
            decision = "NO_GUARANTEED_BENEFIT"
        report["decisions"][aid] = {"decision": decision, "effects_by_hypothesis": effects,
                                    "scope": "only supplied consistent hypotheses; no causal proof or production action"}
    return report
