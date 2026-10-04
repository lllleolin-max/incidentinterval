"""Independent finite integer/max-plus oracle, not an engine differential.

The expected worlds, parent ties, transformations and decisions use only raw
integer enumeration. Production solve/graph/envelope/checker never determine
expected results. Counts below describe actual cases, not loop multipliers.
"""
import argparse
from copy import deepcopy
import itertools
import json
from pathlib import Path
import random
from incidentinterval import analyze, Limits, check_model_contradiction
from incidentinterval.temporal import ANCHOR, Edge, bounds, solve, window


def reached(links, seeds):
    result = set(seeds)
    while True:
        updated = result | {e["to"] for e in links if e["from"] in result}
        if updated == result:
            return result
        result = updated


def worlds(data, hyp, action=None, historical=False):
    events = {e["id"]: e for e in data["events"]}
    action = action or {}
    removed = reached(hyp["links"], action.get("remove", []))
    if historical and removed:
        return [], {}, removed, set()
    affected = reached(hyp["links"], set(action.get("roots", {})) |
                       {e["to"] for e in hyp["links"] if e["id"] in action.get("delays", {})}) | removed
    preserve = historical or action.get("preserve_observations", False)
    if not historical and preserve and removed:
        return [], {}, removed, affected
    active = sorted(set(events) - removed)
    links = [dict(e, delay=action.get("delays", {}).get(e["id"], e["delay"]))
             for e in hyp["links"] if e["from"] in active and e["to"] in active]
    roots = {n: action.get("roots", {}).get(n, v) for n, v in hyp["roots"].items() if n in active}
    retained = set(active) if preserve else set(active) - affected
    obs = [o for o in data.get("observations", []) if o["from"] in retained and o["to"] in retained]
    root_names = sorted(roots)
    valid, alternatives = [], {n: set() for n in active if n not in roots}
    identities = set()
    domains = [range(v[0], v[1] + 1) for v in roots.values()]
    # Dict construction order is intentionally not assumed by the enumeration.
    domains = [range(roots[n][0], roots[n][1] + 1) for n in root_names]
    domains += [range(e["delay"][0], e["delay"][1] + 1) for e in links]
    for values in itertools.product(*domains):
        times = dict(zip(root_names, values[:len(root_names)]))
        delays = dict(zip((e["id"] for e in links), values[len(root_names):]))
        pending = set(active) - set(times)
        while pending:
            ready = [n for n in sorted(pending) if all(e["from"] in times for e in links if e["to"] == n)]
            assert ready, "fixture must be an acyclic graph"
            for n in ready:
                times[n] = max(times[e["from"]] + delays[e["id"]] for e in links if e["to"] == n)
                pending.remove(n)
        if any(not events[n]["interval"][0] <= times[n] <= events[n]["interval"][1] for n in retained):
            continue
        if any(not o["delta"][0] <= times[o["to"]] - times[o["from"]] <= o["delta"][1] for o in obs):
            continue
        start, end = data["impact"]["start"], data["impact"]["end"]
        if start in times and end in times and times[end] < times[start]:
            continue
        valid.append(times)
        ties = {n: sorted(e["id"] for e in links if e["to"] == n and times[e["from"]] + delays[e["id"]] == times[n])
                for n in alternatives}
        for n, ids in ties.items():
            alternatives[n].update(ids)
        identities.update(itertools.product(*(ties[n] for n in sorted(ties))))
    return valid, {n: sorted(ids) for n, ids in alternatives.items()}, removed, affected, len(identities)


def range_of(states, impact):
    values = [x[impact["end"]] - x[impact["start"]] for x in states]
    return [min(values), max(values)]


def check_attainment(model, states, impact):
    """Reported witnesses must be actual raw-enumerated worlds, not only ranges."""
    for cert in [model["witness"], *model.get("duration_extrema", [])]:
        assignment = cert["assignment"]
        assert assignment[ANCHOR] == 0
        assert {n: v for n, v in assignment.items() if n != ANCHOR} in states
    if impact["start"] in states[0] and impact["end"] in states[0]:
        expected = range_of(states, impact)
        assert model["impact_duration"] == expected
        assert [c["impact_duration"] for c in model["duration_extrema"]] == expected


def build(rng, index):
    names = ("r", "s", "a", "b", "c")
    roots = {n: [rng.randint(-1, 0), rng.randint(0, 1)] for n in ("r", "s")}
    links = [{"id": f"l{i}", "from": a, "to": b, "delay": [rng.randint(0, 1), rng.randint(1, 2)], "evidence": ["lab"]}
             for i, (a, b) in enumerate((("r", "a"), ("s", "a"), ("r", "b"), ("a", "b"), ("a", "c"), ("b", "c")))]
    hyp = {"id": "h", "roots": roots, "links": links, "assumptions": ["Finite synthetic AND model."]}
    data = {"version": 1, "time_unit": "tick", "sources": [{"id": "lab", "reference": "synthetic://integer-oracle"}],
            "events": [{"id": n, "interval": [-2, 8]} for n in names],
            "impact": {"start": "r", "end": "c"}, "hypotheses": [hyp], "observations": [], "interventions": []}
    candidates = worlds(data, hyp)[0]
    point = rng.choice(candidates)
    for event in data["events"]:
        n = event["id"]
        if rng.random() < .7:
            event["interval"] = [point[n] - rng.randint(0, 1), point[n] + rng.randint(0, 1)]
    if index % 4 == 0:
        data["events"][-1]["interval"] = [point["c"] + 1, point["c"] + 1]
    if index % 3 == 0:
        data["observations"] = [{"id": "o", "from": "s", "to": "b",
                                 "delta": [point["b"] - point["s"], point["b"] - point["s"] + 1]}]
    data["interventions"] = [
        {"id": "delay", "delays": {"l5": [0, 0]}, "assumptions": ["Change one propagation delay."]},
        {"id": "root", "roots": {"r": [-1, -1]}, "assumptions": ["Change one activation window."]},
        {"id": "preserve", "delays": {"l5": [0, 0]}, "preserve_observations": True, "assumptions": ["Retain observations."]},
        {"id": "remove", "remove": ["a" if index % 2 else "c"], "assumptions": ["Disable an AND prerequisite."]},
        {"id": "remove_preserve", "remove": ["a"], "preserve_observations": True, "assumptions": ["Conflicting retention request."]}]
    if index % 11 == 0:
        data["hypotheses"].append(dict(deepcopy(hyp), id="other", roots={"r": [-1, 1], "s": [0, 1]}))
    if index % 13 == 0:
        data["hypotheses"][0]["links"][0]["evidence"] = []
    return data


def run_cases():
    rng = random.Random(61005)
    counts = {"max_plus_incidents": 180, "model_comparisons": 0, "feasible_models": 0,
              "critical_alternative_sets": 0, "intervention_comparisons": 0,
              "historical_comparisons": 0, "historical_alternative_sets": 0,
              "counterfactual_alternative_sets": 0, "decision_comparisons": 0, "stn_cases": 150,
              "stn_feasible": 0, "stn_pair_ranges": 0}
    for i in range(180):
        data = build(rng, i)
        saved = deepcopy(data)
        report = analyze(data, limits=Limits(work=20_000_000))
        assert report["status"] != "UNKNOWN"
        expected_effects, missing = {}, False
        for hyp in data["hypotheses"]:
            counts["model_comparisons"] += 1
            states, alternatives, _, _, branch_count = worlds(data, hyp)
            if report["status"] == "INFEASIBLE_OBSERVATIONS":
                assert not states
                continue
            model = report["hypotheses"][hyp["id"]]["model"]
            assert bool(states) == (model["status"] == "FEASIBLE"), (i, hyp["id"], model)
            if not states:
                assert check_model_contradiction({e["id"]: e for e in data["events"]},
                                                {o["id"]: o for o in data["observations"]}, data["impact"], hyp, model)
                continue
            counts["feasible_models"] += 1
            counts["critical_alternative_sets"] += len(alternatives)
            baseline = range_of(states, data["impact"])
            assert model["impact_duration"] == baseline, (i, baseline, model["impact_duration"])
            assert model["critical_parent_alternatives"] == alternatives
            assert model["feasible_branches"] == branch_count
            check_attainment(model, states, data["impact"])
            missing |= any(not e.get("evidence") for e in hyp["links"])
            for action in data["interventions"]:
                counts["intervention_comparisons"] += 1
                counts["historical_comparisons"] += 1
                entry = report["hypotheses"][hyp["id"]]["interventions"][action["id"]]
                hist_info = worlds(data, hyp, action, historical=True)
                hist = hist_info[0]
                assert bool(hist) == (entry["historical_compatibility"]["status"] == "FEASIBLE")
                if hist:
                    counts["historical_alternative_sets"] += len(hist_info[1])
                    assert entry["historical_compatibility"]["critical_parent_alternatives"] == hist_info[1]
                    assert entry["historical_compatibility"]["feasible_branches"] == hist_info[4]
                    check_attainment(entry["historical_compatibility"], hist, data["impact"])
                result = worlds(data, hyp, action)
                after, _, removed, affected = result[:4]
                assert bool(after) == (entry["status"] == "FEASIBLE"), (i, action["id"], entry)
                if after:
                    counts["counterfactual_alternative_sets"] += len(result[1])
                    assert entry["counterfactual"]["critical_parent_alternatives"] == result[1]
                    assert entry["counterfactual"]["feasible_branches"] == result[4]
                    check_attainment(entry["counterfactual"], after, data["impact"])
                if action.get("preserve_observations") and removed:
                    effect = "unidentified"
                else:
                    assert entry["removed_events"] == sorted(removed)
                    assert entry["affected_events"] == sorted(affected)
                    if not after:
                        effect = "unidentified"
                    elif data["impact"]["start"] in removed:
                        effect = "impact_prevented_under_model"
                    elif data["impact"]["end"] in removed:
                        effect = "unidentified_recovery_removed"
                    else:
                        duration = range_of(after, data["impact"])
                        assert entry["impact_duration"] == duration
                        difference = [baseline[0] - duration[1], baseline[1] - duration[0]]
                        assert entry["improvement_enclosure"] == difference
                        effect = ("guaranteed_shorter_under_model" if difference[0] > 0 else
                                  "guaranteed_longer_under_model" if difference[1] < 0 else
                                  "equal_duration_under_model" if difference == [0, 0] else "unidentified")
                    assert entry.get("effect", "unidentified") == effect
                expected_effects.setdefault(action["id"], {})[hyp["id"]] = effect
        if report["status"] != "INFEASIBLE_OBSERVATIONS":
            for action in data["interventions"]:
                effects = expected_effects.get(action["id"], {})
                values = list(effects.values())
                benefits = {"impact_prevented_under_model", "guaranteed_shorter_under_model"}
                decision = ("INSUFFICIENT_MODEL_INFORMATION" if not values or any(x.startswith("unidentified") for x in values)
                            else "NEEDS_MECHANISM_EVIDENCE" if missing else "CONDITIONAL_CANDIDATE" if all(x in benefits for x in values)
                            else "HYPOTHESIS_SENSITIVE" if any(x in benefits for x in values)
                            else "AVOID_UNDER_DECLARED_MODELS" if all(x == "guaranteed_longer_under_model" for x in values)
                            else "NO_GUARANTEED_BENEFIT")
                assert report["decisions"][action["id"]]["decision"] == decision
                assert report["decisions"][action["id"]]["effects_by_hypothesis"] == effects
                counts["decision_comparisons"] += 1
        assert data == saved
    for _ in range(150):
        names = ("a", "b", "c")
        edges = sum((bounds(n, [-2, 2], "domain:" + n) for n in names), [])
        for _ in range(5):
            a, b = rng.sample(names, 2)
            edges.append(Edge(a, b, rng.randint(-3, 3), "raw"))
        valid = []
        for values in itertools.product(range(-2, 3), repeat=3):
            times = {ANCHOR: 0, **dict(zip(names, values))}
            if all(times[e.target] - times[e.source] <= e.bound for e in edges):
                valid.append(times)
        result = solve(names, edges)
        assert bool(valid) == (result["status"] == "FEASIBLE")
        if valid:
            counts["stn_feasible"] += 1
            for a, b in itertools.permutations(names, 2):
                assert window(result, a, b) == [min(t[b] - t[a] for t in valid), max(t[b] - t[a] for t in valid)]
                counts["stn_pair_ranges"] += 1
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    counts = run_cases()
    (args.output / "result.json").write_text(json.dumps(counts, indent=2), encoding="utf-8")
    print(json.dumps(counts, indent=2))
