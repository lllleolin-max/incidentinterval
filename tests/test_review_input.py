"""Self-review regressions: malformed nested IDs must be domain errors, not crashes."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from incidentinterval import analyze, InputError

BASE = json.loads((Path(__file__).resolve().parents[1] / "examples" / "incident.json").read_text(encoding="utf-8"))


class InputReviewTests(unittest.TestCase):
    def test_nested_id_shapes_raise_input_error(self):
        mutations = [
            lambda d: d["events"][0].update(evidence=[["deploy_log"]]),
            lambda d: d["hypotheses"][0]["links"][0].update(**{"from": []}),
            lambda d: d["impact"].update(start={}),
            lambda d: d["interventions"][0].update(remove=[{}]),
            lambda d: d["events"][0].update(evidence=[3]),
        ]
        for mutate in mutations:
            data = deepcopy(BASE)
            mutate(data)
            with self.subTest(mutation=mutate.__code__.co_firstlineno):
                with self.assertRaises(InputError):
                    analyze(data)

    def test_empty_intervention_conditions_are_invalid(self):
        data = deepcopy(BASE)
        data["interventions"][0]["assumptions"] = []
        with self.assertRaises(InputError):
            analyze(data)
