"""Consume a report separately; checks refuted models, not feasible optimality.

Usage: python examples/check_contradictions.py INCIDENT.json REPORT.json
No analyzer/solver is called. Input validation uses the unchanged v1 domain.
"""
import argparse
import json
import sys
from incidentinterval import Limits, check_model_contradiction
from incidentinterval.domain import InputError, parse


def read_json(path, cap):
    with open(path, "rb") as stream:
        raw = stream.read(cap + 1)
    if len(raw) > cap:
        raise ValueError("example input exceeds its byte limit")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    def finite(value):
        raise ValueError("nonfinite JSON number")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=finite)


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("incident")
    args.add_argument("report")
    options = args.parse_args()
    try:
        data = read_json(options.incident, 4_000_000)
        _, events, observations, hypotheses, _ = parse(data, Limits(events=96, constraints=512, hypotheses=24,
                                                                  interventions=48, bytes=4_000_000))
        report = read_json(options.report, 32_000_000)
        if type(report.get("version")) is not int or report["version"] != 1 or set(report["hypotheses"]) != set(hypotheses):
            raise ValueError("report identity mismatch")
        results = {}
        for hid, entry in report["hypotheses"].items():
            model = entry["model"]
            if model["status"] == "INFEASIBLE":
                results[hid] = check_model_contradiction(events, observations, data["impact"], hypotheses[hid], model)
        valid = bool(results) and all(results.values())
        print(json.dumps({"contradicted_models_checked": results, "all_supplied_contradictions_valid": valid,
                          "scope": "refuted model constraints and exhaustive selector coverage; no source authentication or feasible optimality"},
                         sort_keys=True))
        return 0 if valid else 1
    except (InputError, OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
        print(json.dumps({"status": "INVALID_CHECK_INPUT"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
