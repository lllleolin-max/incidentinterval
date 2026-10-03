"""Self-review: all advertised witness components must survive tamper checks."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from incidentinterval import analyze
from incidentinterval.checker import check_model_witness, check_intervention_witness, check_causal_cycle
from incidentinterval.temporal import ANCHOR, bounds, check_assignment

BASE = json.loads((Path(__file__).resolve().parents[1] / "examples" / "incident.json").read_text(encoding="utf-8"))


class CertificateReviewTests(unittest.TestCase):
    def test_counterfactual_certificates_and_relaxation_tamper(self):
        report = analyze(BASE)
        for h, entry in report["hypotheses"].items():
            for aid, scenario in entry["interventions"].items():
                if scenario["status"] == "FEASIBLE":
                    self.assertTrue(check_intervention_witness(BASE, h, aid, scenario,
                                    baseline_duration=entry["model"]["impact_duration"]), (h, aid))
        scenario = deepcopy(report["hypotheses"]["deploy_fault"]["interventions"]["faster_recovery"])
        scenario["relaxed_event_observations"] = []
        self.assertFalse(check_intervention_witness(BASE, "deploy_fault", "faster_recovery", scenario))
        scenario = deepcopy(report["hypotheses"]["deploy_fault"]["interventions"]["rollback"])
        scenario["removed_events"] = ["deploy"]
        self.assertFalse(check_intervention_witness(BASE, "deploy_fault", "rollback", scenario))
        scenario = deepcopy(report["hypotheses"]["deploy_fault"]["interventions"]["slower_recovery"])
        scenario["effect"] = "guaranteed_shorter_under_model"
        self.assertFalse(check_intervention_witness(BASE, "deploy_fault", "slower_recovery", scenario))

    def test_causal_cycle_certificate(self):
        data = deepcopy(BASE)
        data["hypotheses"][0]["links"].append({"id": "feedback", "from": "recovery", "to": "deploy", "delay": [0, 0]})
        cycle = analyze(data)["hypotheses"]["deploy_fault"]["model"]["causal_cycle"]
        self.assertTrue(check_causal_cycle(data["hypotheses"][0], cycle))
        self.assertFalse(check_causal_cycle(data["hypotheses"][0], cycle[:-1]))
    def test_critical_parent_and_duration_claims_are_checked(self):
        data = deepcopy(BASE)
        hyp = data["hypotheses"][0]
        witness = analyze(data)["hypotheses"][hyp["id"]]["model"]["witness"]
        changes = [
            lambda w: w["critical_parents"].update(impact="not_a_link"),
            lambda w: w["critical_parents"].pop("impact"),
            lambda w: w["critical_parents"].update(deploy="deploy_to_impact"),
            lambda w: w.update(impact_duration=999),
            lambda w: w["assignment"].update({ANCHOR: False}),
        ]
        for mutate in changes:
            tampered = deepcopy(witness)
            mutate(tampered)
            with self.subTest(mutation=mutate.__code__.co_firstlineno):
                self.assertFalse(check_model_witness({e["id"]: e for e in data["events"]},
                    {o["id"]: o for o in data["observations"]}, data["impact"], hyp, tampered))

    def test_assignment_checker_rejects_float_bool_and_missing_nodes(self):
        edges = bounds("a", [0, 0], "a")
        self.assertTrue(check_assignment(edges, {ANCHOR: 0, "a": 0}))
        for candidate in [{ANCHOR: 0, "a": 0.0}, {ANCHOR: False, "a": 0}, {ANCHOR: 0, "a": False}, {ANCHOR: 0}]:
            with self.subTest(candidate=candidate):
                self.assertFalse(check_assignment(edges, candidate))
