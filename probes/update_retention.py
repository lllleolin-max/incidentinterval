"""Repeated SDK calls must release internal branch closures on return.

Disables automatic cyclic GC to expose unreachable solver-state retention;
tracemalloc is Python allocation accounting, not a process-memory guarantee.
"""
import argparse
import gc
import json
from pathlib import Path
import tracemalloc
from incidentinterval import analyze, Limits


def fixture():
    return {"version": 1, "time_unit": "tick", "sources": [],
            "events": [{"id": n, "interval": [0, 0]} for n in ("r", "s")] +
                      [{"id": f"e{i}", "interval": [0, 1]} for i in range(9)],
            "impact": {"start": "r", "end": "e8"},
            "hypotheses": [{"id": "h", "roots": {"r": [0, 1], "s": [0, 1]},
                            "links": [{"id": r + str(i), "from": r, "to": f"e{i}", "delay": [0, 0]}
                                      for i in range(9) for r in ("r", "s")],
                            "assumptions": ["Synthetic AND gates."]}]}


def run():
    enabled = gc.isenabled()
    gc.collect()
    gc.disable()
    tracemalloc.start()
    try:
        data = fixture()
        after_each = []
        for _ in range(3):
            report = analyze(data, limits=Limits(work=20_000_000))
            assert report["hypotheses"]["h"]["model"]["feasible_branches"] == 512
            after_each.append(tracemalloc.get_traced_memory()[0])
        before, peak = tracemalloc.get_traced_memory()
        gc.collect()
        after, _ = tracemalloc.get_traced_memory()
        return {"runs": 3, "branches_each": 512, "automatic_gc_disabled_for_probe": True,
                "current_after_each_run_bytes": after_each, "current_before_explicit_gc_bytes": before,
                "current_after_explicit_gc_bytes": after, "unreachable_allocation_bytes": before - after,
                "peak_bytes": peak, "scope": "Python allocations; reports and input remain alive; not RSS"}
    finally:
        tracemalloc.stop()
        if enabled:
            gc.enable()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    result = run()
    (args.output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    assert result["unreachable_allocation_bytes"] < 500_000, "SDK return retains unreachable full branch closures until cyclic GC"
