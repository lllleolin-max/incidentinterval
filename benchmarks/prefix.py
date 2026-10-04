"""Frozen same-input work probe. Does not inject an alternative implementation."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import statistics
import sys
import time
import tracemalloc
from unittest.mock import patch
from incidentinterval import analyze, Limits
import incidentinterval.engine as engine
import incidentinterval.temporal as temporal


def fixture(contradiction):
    events = [{"id": n, "interval": [0, 0]} for n in ("r", "s")]
    events += [{"id": f"e{i}", "interval": [1, 1] if contradiction and i == 0 else [0, 1]}
               for i in range(9)]
    links = [{"id": f"{root}{i}", "from": root, "to": f"e{i}", "delay": [0, 0], "evidence": ["lab"]}
             for i in range(9) for root in ("r", "s")]
    # Root assumptions are deliberately wider than measured root intervals:
    # envelope alone allows e0=1, but either critical-parent choice contradicts it.
    return {"version": 1, "time_unit": "tick", "sources": [{"id": "lab", "reference": "synthetic://prefix"}],
            "events": events, "impact": {"start": "r", "end": "e8"},
            "hypotheses": [{"id": "h", "roots": {"r": [0, 1], "s": [0, 1]}, "links": links,
                             "assumptions": ["Independent bounded AND gates."]}], "interventions": []}


def measure(data):
    before = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    original = engine.solve
    calls = []
    def counted(nodes, edges, closure=True):
        calls.append({"closure": closure, "v": len(set(nodes) | {temporal.ANCHOR}),
                      "e": len(set(edges))})
        return original(nodes, edges, closure)
    counts = {"bellman_edge_visits": 0, "closure_candidates": 0}
    source, start = inspect.getsourcelines(temporal.solve)
    lines = {start + i: "bellman_edge_visits" if "if potential[edge.target]" in line
             else "closure_candidates" for i, line in enumerate(source)
             if "if potential[edge.target]" in line or "candidate = dist[a][k]" in line}
    def trace(frame, event, arg):
        if event == "line" and frame.f_code is original.__code__ and frame.f_lineno in lines:
            counts[lines[frame.f_lineno]] += 1
        return trace
    with patch.object(engine, "solve", counted):
        sys.settrace(trace)
        try:
            result = analyze(data, limits=Limits(work=20_000_000))
        finally:
            sys.settrace(None)
    times = []
    for _ in range(3):
        begin = time.perf_counter()
        analyze(data, limits=Limits(work=20_000_000))
        times.append(time.perf_counter() - begin)
    tracemalloc.start()
    analyze(data, limits=Limits(work=20_000_000))
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert before == hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    model = result["hypotheses"]["h"]["model"]
    return {"status": result["status"], "model_status": model["status"], "work": result["work"],
            "branches_total": model["branches_total"], "branches_tested": model["branches_tested"],
            "feasible_branches": model.get("feasible_branches"), "actual_solver_calls": len(calls),
            "actual_closure_calls": sum(c["closure"] for c in calls), **counts,
            "wall_seconds_median": statistics.median(times), "tracemalloc_peak_bytes": peak,
            "input_sha256": before, "input_unchanged": True,
            "branch_failures": len(model.get("branch_failures", [])),
            "branch_search": model.get("branch_search")}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--assert-prefix", action="store_true")
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    results = {"early_contradiction": measure(fixture(True)), "dense_all_feasible": measure(fixture(False))}
    (a.output / "result.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    if a.assert_prefix:
        assert results["early_contradiction"]["actual_solver_calls"] < 32, "complete leaves still trigger repeated STN solves"
        assert results["early_contradiction"]["branch_failures"] == 512, "all selector contradictions must remain available"
        assert results["dense_all_feasible"]["feasible_branches"] == 512, "feasible alternatives lost"


if __name__ == "__main__":
    main()
