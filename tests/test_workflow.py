from copy import deepcopy
import itertools
import json
from pathlib import Path
import random
import unittest
from incidentinterval import analyze, InputError, Limits
from incidentinterval.checker import check_model_witness
from incidentinterval.engine import max_model
from incidentinterval.temporal import Edge, check_negative_cycle

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "incident.json"


def fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class WorkflowTests(unittest.TestCase):
    def test_analysis_preserves_original_observation_and_hypothesis_input(self):
        data = fixture()
        original = deepcopy(data)
        analyze(data)
        self.assertEqual(data, original)

    def test_removal_cannot_preserve_removed_observation(self):
        data = fixture()
        data["interventions"] = [{"id": "remove_keep", "remove": ["deploy"],
                                  "preserve_observations": True, "assumptions": ["Keep the original deployment observation."]}]
        entry = analyze(data)["hypotheses"]["deploy_fault"]["interventions"]["remove_keep"]
        self.assertEqual(entry["status"], "INFEASIBLE")
        removed = entry["historical_compatibility"]["contradiction"]["events"]
        self.assertIn({"id": "deploy", "evidence": ["deploy_log"]}, removed)

    def test_every_max_equation_branch_has_checkable_contradiction(self):
        events = {n: {"id": n, "interval": [0, 10]} for n in ("a", "b", "c")}
        events["c"]["interval"] = [10, 10]
        observations = {"same": {"id": "same", "from": "a", "to": "b", "delta": [0, 0]},
                        "later": {"id": "later", "from": "a", "to": "c", "delta": [1, 10]}}
        links = [{"id": "ac", "from": "a", "to": "c", "delay": [0, 0]},
                 {"id": "bc", "from": "b", "to": "c", "delay": [0, 0]}]
        hyp = {"roots": {"a": [0, 10], "b": [0, 10]}, "links": links}
        result = max_model(events, observations, {"start": "a", "end": "c"}, hyp, Limits())
        self.assertEqual(result["temporal"]["status"], "FEASIBLE")
        self.assertEqual(result["status"], "INFEASIBLE")
        self.assertEqual(len(result["branch_failures"]), 2)
        base = [Edge(e["source"], e["target"], e["bound"], e["reason"], tuple(e["evidence"]))
                for e in result["base_constraints"]]
        for failure in result["branch_failures"]:
            lid = failure["critical_parents"]["c"]
            chosen = next(link for link in links if link["id"] == lid)
            edges = base + [Edge(chosen["from"], "c", 0, f"link:{lid}:critical-upper")]
            cycle = [Edge(e["source"], e["target"], e["bound"], e["reason"], tuple(e["evidence"]))
                     for e in failure["contradiction"]["edges"]]
            self.assertTrue(check_negative_cycle(edges, cycle))

    def test_complete_workflow_and_competing_causes(self):
        data = fixture()
        report = analyze(data)
        self.assertEqual(report["status"], "ANALYZED")
        self.assertEqual(report["decisions"]["rollback"]["decision"], "HYPOTHESIS_SENSITIVE")
        self.assertEqual(report["decisions"]["faster_recovery"]["decision"], "CONDITIONAL_CANDIDATE")
        for hyp in data["hypotheses"]:
            model = report["hypotheses"][hyp["id"]]["model"]
            for cert in [model["witness"], *model["duration_extrema"]]:
                self.assertTrue(check_model_witness({e["id"]: e for e in data["events"]},
                    {o["id"]: o for o in data["observations"]}, data["impact"], hyp, cert))
            tampered = deepcopy(model["witness"])
            tampered["assignment"]["recovery"] += 1
            self.assertFalse(check_model_witness({e["id"]: e for e in data["events"]},
                {o["id"]: o for o in data["observations"]}, data["impact"], hyp, tampered))

    def test_history_conflict_and_counterfactual_separation(self):
        report = analyze(fixture())
        entry = report["hypotheses"]["deploy_fault"]["interventions"]
        self.assertEqual(entry["faster_recovery"]["historical_compatibility"]["status"], "INFEASIBLE")
        self.assertEqual(entry["faster_recovery"]["status"], "FEASIBLE")
        self.assertEqual(entry["faster_recovery"]["improvement_enclosure"], [15, 15])
        self.assertEqual(entry["impossible_keep_history"]["status"], "INFEASIBLE")
        self.assertEqual(entry["rollback"]["historical_compatibility"]["contradiction"]["kind"], "removed_observed_events")

    def test_removing_recovery_is_not_prevention(self):
        report = analyze(fixture())
        for h in report["hypotheses"].values():
            self.assertEqual(h["interventions"]["remove_recovery"]["effect"], "unidentified_recovery_removed")
        self.assertEqual(report["decisions"]["remove_recovery"]["decision"], "INSUFFICIENT_MODEL_INFORMATION")

    def test_absent_evidence_blocks_action_recommendation(self):
        data = fixture()
        for hyp in data["hypotheses"]:
            for link in hyp["links"]:
                link.pop("evidence")
        self.assertEqual(analyze(data)["decisions"]["faster_recovery"]["decision"], "NEEDS_MECHANISM_EVIDENCE")

    def test_causal_cycle_is_invalid_subset_not_temporal_proof(self):
        data = fixture()
        data["hypotheses"][0]["links"].append({"id": "cycle", "from": "recovery", "to": "deploy", "delay": [0, 0]})
        report = analyze(data)
        self.assertEqual(report["hypotheses"]["deploy_fault"]["model"]["status"], "INVALID_MODEL")
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertEqual(report["decisions"]["faster_recovery"]["decision"], "INSUFFICIENT_MODEL_INFORMATION")

    def test_nonroot_override_and_unknown_source(self):
        data = fixture()
        data["interventions"] = [{"id": "move", "roots": {"impact": [0, 0]}, "assumptions": ["Move impact directly"]}]
        self.assertEqual(analyze(data)["hypotheses"]["deploy_fault"]["interventions"]["move"]["status"], "INVALID_INTERVENTION")
        data["events"][0]["evidence"] = ["unknown"]
        with self.assertRaises(InputError):
            analyze(data)

    def test_observation_contradiction(self):
        data = fixture()
        data["observations"][0]["delta"] = [50, 60]
        report = analyze(data)
        self.assertEqual(report["status"], "INFEASIBLE_OBSERVATIONS")
        net = report["observations"]
        edges = [Edge(x["source"], x["target"], x["bound"], x["reason"], tuple(x["evidence"])) for x in net["constraints"]]
        cycle = [Edge(x["source"], x["target"], x["bound"], x["reason"], tuple(x["evidence"])) for x in net["contradiction"]["edges"]]
        self.assertTrue(check_negative_cycle(edges, cycle))

    def test_strict_integer_limits_and_duplicate_ids(self):
        for value in [True, 1.5, float("inf"), 10**13]:
            data = fixture()
            data["events"][0]["interval"][0] = value
            with self.assertRaises(InputError):
                analyze(data)
        data = fixture()
        data["events"].append(deepcopy(data["events"][0]))
        with self.assertRaises(InputError):
            analyze(data)
        with self.assertRaises(InputError):
            analyze(fixture(), limits=Limits(events=2))
        with self.assertRaises(InputError):
            Limits(branches=4097)

    def test_input_permutation(self):
        data = fixture()
        expected = analyze(data)
        for name in ("sources", "events", "observations", "hypotheses", "interventions"):
            data[name].reverse()
        for h in data["hypotheses"]:
            h["links"].reverse()
            h["roots"] = dict(reversed(list(h["roots"].items())))
        self.assertEqual(expected, analyze(data))

    def test_exact_max_equation_vs_exhaustive_structural_oracle(self):
        rng = random.Random(993)
        for case in range(45):
            root_window = [-1, 1]
            links = [{"id": "ra", "from": "r", "to": "a", "delay": [0, rng.randint(0, 2)]},
                     {"id": "rb", "from": "r", "to": "b", "delay": [0, rng.randint(0, 2)]},
                     {"id": "ab", "from": "a", "to": "b", "delay": [0, rng.randint(0, 2)]}]
            events = {n: {"id": n, "interval": sorted([rng.randint(-1, 4), rng.randint(-1, 4)])}
                      for n in ("r", "a", "b")}
            hyp = {"id": "h", "roots": {"r": root_window}, "links": links}
            valid = []
            for root, *lag in itertools.product(range(-1, 2), *(range(e["delay"][1] + 1) for e in links)):
                times = {"r": root, "a": root + lag[0]}
                times["b"] = max(root + lag[1], times["a"] + lag[2])
                if all(e["interval"][0] <= times[n] <= e["interval"][1] for n, e in events.items()):
                    valid.append(times)
            result = max_model(events, {}, {"start": "a", "end": "b"}, hyp, Limits())
            self.assertEqual(bool(valid), result["status"] == "FEASIBLE", case)
            if valid:
                self.assertEqual(result["impact_duration"], [min(t["b"] - t["a"] for t in valid),
                                                           max(t["b"] - t["a"] for t in valid)], case)
                for cert in result["duration_extrema"]:
                    self.assertTrue(check_model_witness(events, {}, {"start": "a", "end": "b"}, hyp, cert))

    def test_branch_limit_is_unknown_not_safe(self):
        data = fixture()
        data["hypotheses"] = data["hypotheses"][:1]
        data["hypotheses"][0]["links"].append({"id": "extra", "from": "load", "to": "impact", "delay": [0, 0]})
        report = analyze(data, limits=Limits(branches=1))
        self.assertEqual(report["status"], "UNKNOWN")
        model = report["hypotheses"]["deploy_fault"]["model"]
        self.assertEqual(model["status"], "UNKNOWN_LIMIT")
        self.assertEqual(model["branches_total"], 2)
        self.assertEqual(model["branches_tested"], 0)
