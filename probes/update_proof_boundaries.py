"""Standalone adversarial consumer probe; use a normal installed wheel."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from incidentinterval import analyze, check_model_contradiction


def fixture():
    return {"version": 1, "time_unit": "tick", "sources": [],
            "events": [{"id": "r", "interval": [0, 0]}, {"id": "s", "interval": [0, 0]},
                       {"id": "a", "interval": [1, 1]}, {"id": "b", "interval": [0, 1]}],
            "impact": {"start": "r", "end": "b"},
            "hypotheses": [{"id": "h", "roots": {"r": [0, 1], "s": [0, 1]},
                            "links": [{"id": r + n, "from": r, "to": n, "delay": [0, 0]}
                                      for n in ("a", "b") for r in ("r", "s")],
                            "assumptions": ["Synthetic AND gates."]}]}


def run():
    data = fixture()
    events = {e["id"]: e for e in data["events"]}
    hyp = data["hypotheses"][0]
    model = analyze(data)["hypotheses"]["h"]["model"]
    def check(value):
        return check_model_contradiction(events, {}, data["impact"], hyp, value)
    assert check(model)
    cases = {}
    for name, value in (("boolean_version", True), ("unknown_version", 2),
                        ("foreign_method", "enumerate_nothing"), ("boolean_prefix_checks", True),
                        ("negative_leaf_solves", -1), ("broken_assignment_count", 0),
                        ("impossible_subtree_count", 99), ("missing_metadata_field", None),
                        ("unknown_metadata_field", 1)):
        bad = deepcopy(model)
        meta = bad["branch_search"]
        if name.endswith("version"):
            meta["version"] = value
        elif name == "foreign_method":
            meta["method"] = value
        elif name == "boolean_prefix_checks":
            meta["prefix_checks"] = value
        elif name == "negative_leaf_solves":
            meta["leaf_solves"] = value
        elif name == "broken_assignment_count":
            meta["pruned_assignments"] = value
        elif name == "impossible_subtree_count":
            meta["pruned_subtrees"] = value
        elif name == "missing_metadata_field":
            del meta["leaf_solves"]
        else:
            meta["extra"] = value
        cases[name] = {"accepted": check(bad), "expected": False}
    legacy = deepcopy(model)
    del legacy["branch_search"]
    cases["legacy_without_metadata"] = {"accepted": check(legacy), "expected": True}
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cases = run()
    (args.output / "result.json").write_text(json.dumps(cases, indent=2), encoding="utf-8")
    print(json.dumps(cases, indent=2))
    assert all(c["accepted"] == c["expected"] for c in cases.values()), "malformed search metadata accepted"


if __name__ == "__main__":
    main()
