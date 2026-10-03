"""Executable timestamp-only and mechanism ablations; no incumbent benchmark."""
from copy import deepcopy
import json
from pathlib import Path
from incidentinterval import analyze
from incidentinterval.baseline import timestamp_only


def run():
    data = json.loads(Path(__file__).with_name("incident.json").read_text(encoding="utf-8"))
    deploy_only = deepcopy(data)
    deploy_only["hypotheses"] = deploy_only["hypotheses"][:1]
    alternative = deepcopy(data)
    precise_clock = deepcopy(data)
    precise_clock["events"][0]["interval"] = [20, 20]
    for h in precise_clock["hypotheses"]:
        h["roots"]["deploy"] = [20, 20]
    no_evidence = deepcopy(data)
    for h in no_evidence["hypotheses"]:
        for link in h["links"]:
            link["evidence"] = []
    cases = {"skew_deploy_only": deploy_only, "alternative_cause": alternative,
             "precise_clock_rejects_deploy": precise_clock, "evidence_ablation": no_evidence}
    measured = {}
    for name, fixture in cases.items():
        full = analyze(fixture)
        baseline = timestamp_only(fixture)
        measured[name] = {"timestamp_only": baseline["selected_intervention"],
                          "decisions": {a: v["decision"] for a, v in full["decisions"].items()},
                          "hypotheses": {h: v["status"] for h, v in full["hypotheses"].items()}}
    assert measured["skew_deploy_only"]["timestamp_only"] == "rate_limit"
    assert measured["skew_deploy_only"]["decisions"]["rate_limit"] == "NO_GUARANTEED_BENEFIT"
    assert measured["skew_deploy_only"]["decisions"]["rollback"] == "CONDITIONAL_CANDIDATE"
    assert measured["alternative_cause"]["decisions"]["rollback"] == "HYPOTHESIS_SENSITIVE"
    assert measured["precise_clock_rejects_deploy"]["decisions"]["rate_limit"] == "CONDITIONAL_CANDIDATE"
    assert measured["evidence_ablation"]["decisions"]["faster_recovery"] == "NEEDS_MECHANISM_EVIDENCE"
    print(json.dumps({"synthetic": True, "cases": measured}, sort_keys=True, indent=2))
    print("4 executable contrasts passed; favorable, adverse and unidentified cases included")
    return measured


if __name__ == "__main__":
    run()
