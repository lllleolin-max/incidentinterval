"""Self-review: a per-model branch cap does not bound the complete workflow."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from incidentinterval import analyze, Limits
import incidentinterval.engine as engine


def branching_fixture():
    events = [{"id": n, "interval": [0, 0]} for n in ("r", "s")]
    events += [{"id": f"e{i}", "interval": [0, 1]} for i in range(8)]
    links = [{"id": f"{root}{i}", "from": root, "to": f"e{i}", "delay": [0, 1], "evidence": ["lab"]}
             for i in range(8) for root in ("r", "s")]
    h = {"id": "h0", "roots": {"r": [0, 0], "s": [0, 0]}, "links": links,
         "assumptions": ["Independent bounded AND gates."]}
    return {"version": 1, "time_unit": "tick", "sources": [{"id": "lab", "reference": "synthetic://branch-work"}],
            "events": events, "impact": {"start": "r", "end": "e7"},
            "hypotheses": [h, dict(deepcopy(h), id="h1")],
            "interventions": [{"id": f"a{i}", "delays": {"r7": [0, 0]}, "assumptions": ["One delay is zero."]}
                              for i in range(4)]}


class WorkReviewTests(unittest.TestCase):
    def test_full_analysis_has_aggregate_work_accounting(self):
        calls, units = 0, 0
        original = engine.solve

        def measured(nodes, edges, closure=True):
            nonlocal calls, units
            v = len(set(nodes) | {"@origin"})
            calls += 1
            units += v * len(set(edges)) + (v**3 if closure else 0)
            return original(nodes, edges, closure)

        with patch.object(engine, "solve", measured):
            result = analyze(branching_fixture())
        print(f"probe solver_calls={calls} estimated_work_units={units} status={result['status']}")
        self.assertTrue("work" in result, "aggregate work accounting is missing")
        self.assertEqual(result["work"]["charged"], units)
        self.assertLessEqual(units, 2_000_000)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertTrue(result["work"]["exhausted"])

    def test_tiny_work_budget_and_reproducible_resume_by_rerun(self):
        data = branching_fixture()
        tiny = analyze(data, limits=Limits(work=1))
        self.assertEqual(tiny["status"], "UNKNOWN")
        self.assertEqual(tiny["observations"]["status"], "UNKNOWN_LIMIT")
        self.assertEqual(tiny["work"]["solver_calls"], 0)
        enough = analyze(data, limits=Limits(work=20_000_000))
        self.assertEqual(enough["status"], "ANALYZED")
        self.assertFalse(enough["work"]["exhausted"])
        data["hypotheses"].reverse()
        data["interventions"].reverse()
        self.assertEqual(enough, analyze(data, limits=Limits(work=20_000_000)))


if __name__ == "__main__":
    unittest.main()
