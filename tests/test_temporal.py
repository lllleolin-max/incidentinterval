import itertools
import random
import unittest
from incidentinterval.temporal import (ANCHOR, Edge, bounds, delta, solve, window,
                                       check_assignment, check_negative_cycle, public)


class TemporalTests(unittest.TestCase):
    def test_negative_cycle_and_independent_certificate(self):
        edges = bounds("a", [0, 0], "a") + bounds("b", [1, 1], "b") + delta("a", "b", [2, 3], "obs", ["log"])
        result = solve(["a", "b"], edges)
        self.assertEqual(result["status"], "INFEASIBLE")
        self.assertTrue(check_negative_cycle(edges, result["cycle"]))
        self.assertFalse(check_negative_cycle(edges, result["cycle"][:-1]))
        self.assertLess(sum(e.bound for e in result["cycle"]), 0)

    def test_ties_and_closed_boundary(self):
        edges = bounds("a", [2, 2], "a") + bounds("b", [2, 3], "b")
        result = solve(["a", "b"], edges)
        self.assertEqual(window(result, "a", "b"), [0, 1])
        self.assertEqual(public(result, True)["partial_order"][0]["relation"], "before_or_equal")
        tied = solve(["a", "b"], edges + delta("a", "b", [0, 0], "tie"))
        self.assertEqual(public(tied, True)["partial_order"][0]["relation"], "equal")

    def test_small_independent_exhaustive_oracle(self):
        rng = random.Random(731)
        for _ in range(80):
            edges = sum((bounds(n, [-2, 2], n) for n in ("a", "b", "c")), [])
            for _ in range(4):
                a, b = rng.sample(["a", "b", "c"], 2)
                edges.append(Edge(a, b, rng.randint(-3, 3), "generated"))
            assignments = [{ANCHOR: 0, **dict(zip(("a", "b", "c"), values))}
                           for values in itertools.product(range(-2, 3), repeat=3)]
            valid = [x for x in assignments if all(x[e.target] - x[e.source] <= e.bound for e in edges)]
            result = solve(["a", "b", "c"], edges)
            self.assertEqual(bool(valid), result["status"] == "FEASIBLE")
            if valid:
                self.assertTrue(check_assignment(edges, result["assignment"]))
                for a, b in itertools.permutations(("a", "b", "c"), 2):
                    self.assertEqual(window(result, a, b), [min(x[b] - x[a] for x in valid),
                                                           max(x[b] - x[a] for x in valid)])
            else:
                self.assertTrue(check_negative_cycle(edges, result["cycle"]))

    def test_permutation_determinism(self):
        edges = bounds("a", [0, 4], "a") + bounds("b", [0, 4], "b") + delta("a", "b", [1, 2], "ab")
        self.assertEqual(public(solve(["a", "b"], edges), True),
                         public(solve(["b", "a"], edges[::-1]), True))
