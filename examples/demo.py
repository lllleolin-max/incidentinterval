"""Run from the repository after installation. All data are explicitly synthetic."""
import json
from pathlib import Path
from incidentinterval import analyze
from incidentinterval.checker import check_model_witness

data = json.loads(Path(__file__).with_name("incident.json").read_text(encoding="utf-8"))
report = analyze(data)
for h in data["hypotheses"]:
    model = report["hypotheses"][h["id"]]["model"]
    assert check_model_witness({e["id"]: e for e in data["events"]},
                               {o["id"]: o for o in data["observations"]}, data["impact"], h, model["witness"])
    print(h["id"], "duration", model["impact_duration"], "critical path", model["witness_critical_path"])
for aid, decision in report["decisions"].items():
    print(aid, decision["decision"], decision["effects_by_hypothesis"])
assert report["decisions"]["rollback"]["decision"] == "HYPOTHESIS_SENSITIVE"
assert report["decisions"]["faster_recovery"]["decision"] == "CONDITIONAL_CANDIDATE"
assert report["decisions"]["slower_recovery"]["decision"] == "AVOID_UNDER_DECLARED_MODELS"
assert report["hypotheses"]["deploy_fault"]["interventions"]["impossible_keep_history"]["status"] == "INFEASIBLE"
print("synthetic demo assertions passed; no causal identification or observed intervention effect")
