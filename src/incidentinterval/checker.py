"""Independent direct-equation checker; does not use the solver or its closure."""
from .temporal import ANCHOR


def check_model_witness(events, observations, impact, hypothesis, witness):
    """Validate one existence certificate against observed bounds and max equations."""
    try:
        times, delays = witness["assignment"], witness["delays"]
        if set(times) != set(events) | {ANCHOR} or times[ANCHOR] != 0:
            return False
        if any(type(t) is not int for t in times.values()):
            return False
        for n, event in events.items():
            if not event["interval"][0] <= times[n] <= event["interval"][1]:
                return False
        for obs in observations.values():
            value = times[obs["to"]] - times[obs["from"]]
            if not obs["delta"][0] <= value <= obs["delta"][1]:
                return False
        if impact["start"] in times and impact["end"] in times:
            if times[impact["end"]] < times[impact["start"]]:
                return False
        incoming = {n: [] for n in events}
        if set(delays) != {e["id"] for e in hypothesis["links"]}:
            return False
        for edge in hypothesis["links"]:
            d = delays[edge["id"]]
            if type(d) is not int or not edge["delay"][0] <= d <= edge["delay"][1]:
                return False
            incoming[edge["to"]].append(times[edge["from"]] + d)
        for n in events:
            if incoming[n]:
                if times[n] != max(incoming[n]):
                    return False
            elif n not in hypothesis["roots"] or not hypothesis["roots"][n][0] <= times[n] <= hypothesis["roots"][n][1]:
                return False
        return True
    except (KeyError, TypeError, ValueError):
        return False
