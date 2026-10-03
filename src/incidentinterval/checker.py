"""Independent direct-equation checker; does not use the solver or its closure."""
from .temporal import ANCHOR


def check_causal_cycle(hypothesis, link_ids):
    """Verify that a supplied ordered link-ID list is an actual closed cycle."""
    try:
        links = {e["id"]: e for e in hypothesis["links"]}
        path = [links[key] for key in link_ids]
        return bool(path) and all(a["to"] == b["from"] for a, b in zip(path, path[1:] + path[:1]))
    except (KeyError, TypeError):
        return False


def check_model_witness(events, observations, impact, hypothesis, witness, *, relaxed_events=()):
    """Validate one existence certificate against observed bounds and max equations."""
    try:
        times, delays, critical = witness["assignment"], witness["delays"], witness["critical_parents"]
        if set(times) != set(events) | {ANCHOR} or times[ANCHOR] != 0:
            return False
        if any(type(t) is not int for t in times.values()):
            return False
        for n, event in events.items():
            if n not in relaxed_events and not event["interval"][0] <= times[n] <= event["interval"][1]:
                return False
        for obs in observations.values():
            value = times[obs["to"]] - times[obs["from"]]
            if not obs["delta"][0] <= value <= obs["delta"][1]:
                return False
        if impact["start"] in times and impact["end"] in times:
            duration = times[impact["end"]] - times[impact["start"]]
            if duration < 0 or type(witness.get("impact_duration")) is not int or witness["impact_duration"] != duration:
                return False
        elif "impact_duration" in witness:
            return False
        incoming = {n: [] for n in events}
        if set(delays) != {e["id"] for e in hypothesis["links"]}:
            return False
        by_id = {edge["id"]: edge for edge in hypothesis["links"]}
        for edge in hypothesis["links"]:
            d = delays[edge["id"]]
            if type(d) is not int or not edge["delay"][0] <= d <= edge["delay"][1]:
                return False
            incoming[edge["to"]].append(times[edge["from"]] + d)
        if set(critical) != {n for n in events if incoming[n]}:
            return False
        if set(hypothesis["roots"]) != {n for n in events if not incoming[n]}:
            return False
        for n in events:
            if incoming[n]:
                if times[n] != max(incoming[n]):
                    return False
                selected = by_id[critical[n]]
                if selected["to"] != n or times[n] != times[selected["from"]] + delays[selected["id"]]:
                    return False
            elif n not in hypothesis["roots"] or not hypothesis["roots"][n][0] <= times[n] <= hypothesis["roots"][n][1]:
                return False
        return True
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def check_intervention_witness(data, hypothesis_id, intervention_id, scenario, *, baseline_duration=None):
    """Independently reconstruct removal/relaxation and check a simulated witness.

    Does not call graph helpers, max_model, STN solving, or read reported
    affected-event sets as truth. Verifies existence, not global optimality.
    """
    try:
        if scenario["status"] != "FEASIBLE" or scenario["kind"] != "simulated_under_declared_hypothesis":
            return False
        events = {e["id"]: e for e in data["events"]}
        hypothesis = next(h for h in data["hypotheses"] if h["id"] == hypothesis_id)
        action = next(a for a in data["interventions"] if a["id"] == intervention_id)
        outgoing = {n: set() for n in events}
        for link in hypothesis["links"]:
            outgoing[link["from"]].add(link["to"])

        def closure(seeds):
            reached = set(seeds)
            while True:
                updated = reached | {child for parent in reached for child in outgoing[parent]}
                if updated == reached:
                    return reached
                reached = updated

        removed = closure(action.get("remove", []))
        modified = set(action.get("roots", {})) | {e["to"] for e in hypothesis["links"]
                                                   if e["id"] in action.get("delays", {})}
        affected = closure(modified) | removed
        preserve = action.get("preserve_observations", False)
        if preserve and removed:
            return False
        active = {n: e for n, e in events.items() if n not in removed}
        relaxed = set(events) - set(active) if preserve else affected
        observations = {o["id"]: o for o in data.get("observations", [])
                        if o["from"] not in relaxed and o["to"] not in relaxed}
        altered = {"roots": {n: action.get("roots", {}).get(n, v) for n, v in hypothesis["roots"].items()
                             if n not in removed},
                   "links": [dict(e, delay=action.get("delays", {}).get(e["id"], e["delay"]))
                             for e in hypothesis["links"] if e["from"] not in removed and e["to"] not in removed]}
        if scenario["removed_events"] != sorted(removed) or scenario["affected_events"] != sorted(affected):
            return False
        if scenario["relaxed_event_observations"] != sorted(relaxed):
            return False
        if scenario["relaxed_difference_observations"] != sorted({o["id"] for o in data.get("observations", [])} - set(observations)):
            return False
        witness = scenario["counterfactual"]["witness"]
        if not check_model_witness(active, observations, data["impact"], altered, witness,
                                   relaxed_events=relaxed):
            return False
        for cert in scenario["counterfactual"].get("duration_extrema", []):
            if not check_model_witness(active, observations, data["impact"], altered, cert,
                                       relaxed_events=relaxed):
                return False
        if data["impact"]["start"] in removed:
            return scenario["effect"] == "impact_prevented_under_model" and scenario["impact_duration"] == [0, 0]
        if data["impact"]["end"] in removed:
            return scenario["effect"] == "unidentified_recovery_removed" and "impact_duration" not in scenario
        durations = scenario["counterfactual"]["impact_duration"]
        certs = scenario["counterfactual"]["duration_extrema"]
        if scenario["impact_duration"] != durations or [c["impact_duration"] for c in certs] != durations:
            return False
        improvement = scenario["improvement_enclosure"]
        if (not isinstance(improvement, list) or len(improvement) != 2
                or any(type(x) is not int for x in improvement) or improvement[0] > improvement[1]):
            return False
        if baseline_duration is not None and improvement != [baseline_duration[0] - durations[1],
                                                             baseline_duration[1] - durations[0]]:
            return False
        effect = ("guaranteed_shorter_under_model" if improvement[0] > 0 else
                  "guaranteed_longer_under_model" if improvement[1] < 0 else
                  "equal_duration_under_model" if improvement == [0, 0] else "unidentified")
        return scenario["effect"] == effect
    except (KeyError, TypeError, ValueError, AttributeError, StopIteration):
        return False
