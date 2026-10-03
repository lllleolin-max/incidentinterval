"""Strict, bounded v1 input validation. No source URLs are fetched."""
from dataclasses import dataclass
import re


class InputError(ValueError):
    """Malformed or unsupported input; distinct from an infeasible valid model."""


@dataclass(frozen=True)
class Limits:
    events: int = 48
    constraints: int = 256
    hypotheses: int = 12
    interventions: int = 24
    branches: int = 512
    bytes: int = 1_000_000

    def __post_init__(self):
        caps = {"events": 96, "constraints": 512, "hypotheses": 24,
                "interventions": 48, "branches": 4096, "bytes": 4_000_000}
        for name, cap in caps.items():
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= cap:
                raise InputError(f"limits.{name}: integer in [1, {cap}] required")


BOUND = 10**12
ID = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,79}\Z")


def obj(value, keys, path, required=()):
    if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
        raise InputError(f"{path}: object required")
    extra = set(value) - set(keys)
    missing = set(required) - set(value)
    if extra or missing:
        raise InputError(f"{path}: unknown keys {sorted(extra)}, missing keys {sorted(missing)}")


def identifier(value, path):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise InputError(f"{path}: ASCII ID of 1..80 characters required")
    return value


def sequence(value, cap, path):
    if not isinstance(value, list) or len(value) > cap:
        raise InputError(f"{path}: list with at most {cap} entries required")
    return value


def text(value, path):
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise InputError(f"{path}: nonempty text of at most 2000 characters required")


def integer(value, path, nonnegative=False):
    if type(value) is not int or abs(value) > BOUND or (nonnegative and value < 0):
        raise InputError(f"{path}: bounded integer required (bool/float are unsupported)")
    return value


def interval(value, path, nonnegative=False):
    if not isinstance(value, list) or len(value) != 2:
        raise InputError(f"{path}: [inclusive_min, inclusive_max] required")
    lo, hi = [integer(x, path, nonnegative) for x in value]
    if lo > hi:
        raise InputError(f"{path}: lower bound exceeds upper bound")
    return [lo, hi]


def unique(items, path):
    result = {}
    for item in items:
        key = identifier(item.get("id"), f"{path}.id") if isinstance(item, dict) else None
        if key is None or key in result:
            raise InputError(f"{path}: duplicate or missing ID {key}")
        result[key] = item
    return dict(sorted(result.items()))


def parse(data, limits):
    obj(data, ("version", "time_unit", "sources", "events", "observations",
               "hypotheses", "interventions", "impact"), "$",
        ("version", "time_unit", "sources", "events", "hypotheses", "impact"))
    if type(data["version"]) is not int or data["version"] != 1:
        raise InputError("version: only integer 1 supported")
    if data["time_unit"] not in ("ms", "s", "tick"):
        raise InputError("time_unit: ms, s or tick required; use a common origin and resolution")
    sources = unique(sequence(data["sources"], limits.constraints, "sources"), "sources")
    for src in sources.values():
        obj(src, ("id", "reference", "description"), "source", ("id", "reference"))
        text(src["reference"], "source.reference")
        if "description" in src:
            text(src["description"], "source.description")

    def evidence(item, path):
        refs = sequence(item.get("evidence", []), limits.constraints, path + ".evidence")
        if len(set(refs)) != len(refs) or any(ref not in sources for ref in refs):
            raise InputError(f"{path}.evidence: unique known source IDs required")

    events = unique(sequence(data["events"], limits.events, "events"), "events")
    if not events:
        raise InputError("events: at least one event required")
    for event in events.values():
        obj(event, ("id", "interval", "evidence", "label", "timestamp"), "event", ("id", "interval"))
        interval(event["interval"], "event.interval")
        evidence(event, "event")
        if "label" in event:
            text(event["label"], "event.label")
        if "timestamp" in event:
            integer(event["timestamp"], "event.timestamp")
            if not event["interval"][0] <= event["timestamp"] <= event["interval"][1]:
                raise InputError("event.timestamp: must lie in declared clock interval")

    def endpoints(item, path):
        if item.get("from") not in events or item.get("to") not in events:
            raise InputError(f"{path}: known from/to event IDs required")

    observations = unique(sequence(data.get("observations", []), limits.constraints,
                                   "observations"), "observations")
    for obs in observations.values():
        obj(obs, ("id", "from", "to", "delta", "evidence"), "observation",
            ("id", "from", "to", "delta"))
        endpoints(obs, "observation")
        interval(obs["delta"], "observation.delta")
        evidence(obs, "observation")
    obj(data["impact"], ("start", "end"), "impact", ("start", "end"))
    if any(data["impact"][key] not in events for key in ("start", "end")):
        raise InputError("impact: known start/end event IDs required")
    if data["impact"]["start"] == data["impact"]["end"]:
        raise InputError("impact: distinct occurrence and recovery events required")
    hypotheses = unique(sequence(data["hypotheses"], limits.hypotheses, "hypotheses"), "hypotheses")
    if not hypotheses:
        raise InputError("hypotheses: at least one explicitly supplied hypothesis required")
    for hyp in hypotheses.values():
        obj(hyp, ("id", "assumptions", "links", "roots"), "hypothesis",
            ("id", "assumptions", "links", "roots"))
        assumptions = sequence(hyp["assumptions"], 64, "hypothesis.assumptions")
        if not assumptions:
            raise InputError("hypothesis.assumptions: explicitly state model assumptions")
        for assumption in assumptions:
            text(assumption, "assumption")
        links = unique(sequence(hyp["links"], limits.constraints, "hypothesis.links"), "links")
        for link in links.values():
            obj(link, ("id", "from", "to", "delay", "evidence"), "link",
                ("id", "from", "to", "delay"))
            endpoints(link, "link")
            interval(link["delay"], "link.delay", nonnegative=True)
            evidence(link, "link")
        obj(hyp["roots"], events, "hypothesis.roots")
        for root, window in hyp["roots"].items():
            interval(window, f"roots.{root}")
    interventions = unique(sequence(data.get("interventions", []), limits.interventions,
                                   "interventions"), "interventions")
    for action in interventions.values():
        obj(action, ("id", "remove", "delays", "roots", "preserve_observations", "assumptions"),
            "intervention", ("id", "assumptions"))
        for assumption in sequence(action["assumptions"], 64, "intervention.assumptions"):
            text(assumption, "intervention.assumption")
        removed = sequence(action.get("remove", []), limits.events, "intervention.remove")
        if len(set(removed)) != len(removed) or any(x not in events for x in removed):
            raise InputError("intervention.remove: unique known event IDs required")
        obj(action.get("delays", {}), {x["id"] for h in hypotheses.values() for x in h["links"]},
            "intervention.delays")
        for window in action.get("delays", {}).values():
            interval(window, "intervention.delay", True)
        obj(action.get("roots", {}), events, "intervention.roots")
        for window in action.get("roots", {}).values():
            interval(window, "intervention.root")
        if type(action.get("preserve_observations", False)) is not bool:
            raise InputError("preserve_observations: bool required")
    return sources, events, observations, hypotheses, interventions
