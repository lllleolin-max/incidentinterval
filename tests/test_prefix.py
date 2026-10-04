"""Prefix contradictions must cover all complete selectors without losing ties."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from incidentinterval import analyze, Limits, check_model_contradiction
import incidentinterval.engine as engine


def branching(contradiction, gates=9):
    return {"version": 1, "time_unit": "tick", "sources": [{"id": "s", "reference": "synthetic://prefix"}],
            "events": [{"id": n, "interval": [0, 0]} for n in ("r", "s")] +
                      [{"id": f"e{i}", "interval": [1, 1] if contradiction and i == 0 else [0, 1]}
                       for i in range(gates)],
            "impact": {"start": "r", "end": f"e{gates - 1}"},
            "hypotheses": [{"id": "h", "roots": {"r": [0, 1], "s": [0, 1]},
                            "links": [{"id": f"{r}{i}", "from": r, "to": f"e{i}", "delay": [0, 0], "evidence": ["s"]}
                                      for i in range(gates) for r in ("r", "s")],
                            "assumptions": ["AND, independent delays."]}]}


class PrefixTests(unittest.TestCase):
    def test_512_selector_contradiction_keeps_full_independent_proof(self):
        data = branching(True)
        original = deepcopy(data)
        with patch.object(engine, "solve", wraps=engine.solve) as spy:
            report = analyze(data)
        model = report["hypotheses"]["h"]["model"]
        self.assertEqual(report["status"], "NO_CONSISTENT_MODEL")
        self.assertEqual(spy.call_count, 4)
        self.assertEqual(model["branches_tested"], 512)
        self.assertEqual(len(model["branch_failures"]), 512)
        self.assertEqual(model["branch_search"]["pruned_assignments"], 512)
        events = {e["id"]: e for e in data["events"]}
        self.assertTrue(check_model_contradiction(events, {}, data["impact"], data["hypotheses"][0], model))
        for change in ("duplicate", "missing", "foreign", "cycle", "boolean", "source"):
            bad = deepcopy(model)
            if change == "duplicate":
                bad["branch_failures"][-1] = bad["branch_failures"][0]
            elif change == "missing":
                bad["branch_failures"].pop()
            elif change == "foreign":
                bad["branch_failures"][0]["critical_parents"]["e0"] = "r1"
            elif change == "cycle":
                bad["branch_failures"][0]["contradiction"]["edges"][0]["bound"] -= 1
            elif change == "boolean":
                bad["branches_total"] = True
            else:
                bad["base_constraints"][0]["evidence"] = ["invented"]
            self.assertFalse(check_model_contradiction(events, {}, data["impact"], data["hypotheses"][0], bad), change)
        self.assertEqual(data, original)

    def test_all_feasible_branches_and_tied_parents_survive(self):
        model = analyze(branching(False), limits=Limits(work=20_000_000))["hypotheses"]["h"]["model"]
        self.assertEqual(model["status"], "FEASIBLE")
        self.assertEqual(model["feasible_branches"], 512)
        self.assertEqual(model["branch_search"]["pruned_assignments"], 0)
        self.assertEqual(model["impact_duration"], [0, 0])
        self.assertEqual(model["critical_parent_alternatives"], {f"e{i}": [f"r{i}", f"s{i}"] for i in range(9)})

    def test_prefix_budget_exhaustion_does_not_publish_partial_contradiction(self):
        complete = analyze(branching(True))
        used = complete["work"]["charged"]
        exhausted = analyze(branching(True), limits=Limits(work=used - 1))
        self.assertEqual(exhausted["status"], "UNKNOWN")
        self.assertTrue(exhausted["work"]["exhausted"])
        self.assertEqual(exhausted["hypotheses"]["h"]["model"]["status"], "UNKNOWN_LIMIT")
        self.assertNotIn("branch_failures", exhausted["hypotheses"]["h"]["model"])

    def test_consumer_checks_search_metadata_and_accepts_legacy_reports(self):
        data = branching(True, 2)
        events = {e["id"]: e for e in data["events"]}
        hyp = data["hypotheses"][0]
        model = analyze(data)["hypotheses"]["h"]["model"]
        def check(value):
            return check_model_contradiction(events, {}, data["impact"], hyp, value)
        legacy = deepcopy(model)
        del legacy["branch_search"]
        self.assertTrue(check(legacy))
        for field, value in (("version", True), ("version", 2), ("method", "unknown"),
                             ("prefix_checks", 1.0), ("leaf_solves", -1),
                             ("pruned_assignments", 0), ("pruned_subtrees", 99)):
            bad = deepcopy(model)
            bad["branch_search"][field] = value
            self.assertFalse(check(bad), (field, value))
        for shape in (None, [], {"version": 1}, {**model["branch_search"], "extra": 0}):
            bad = deepcopy(model)
            bad["branch_search"] = shape
            self.assertFalse(check(bad))


if __name__ == "__main__":
    unittest.main()
