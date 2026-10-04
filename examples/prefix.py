"""512 complete selectors refuted by two independently checkable prefix cycles."""
import json
from incidentinterval import analyze, check_model_contradiction


def incident():
    return {"version": 1, "time_unit": "tick", "sources": [],
            "events": [{"id": n, "interval": [0, 0]} for n in ("r", "s")] +
                      [{"id": f"e{i}", "interval": [1, 1] if i == 0 else [0, 1]} for i in range(9)],
            "impact": {"start": "r", "end": "e8"},
            "hypotheses": [{"id": "h", "roots": {"r": [0, 1], "s": [0, 1]},
                            "links": [{"id": r + str(i), "from": r, "to": f"e{i}", "delay": [0, 0]}
                                      for i in range(9) for r in ("r", "s")],
                            "assumptions": ["Synthetic independent AND gates."]}]}


if __name__ == "__main__":
    data = incident()
    report = analyze(data)
    model = report["hypotheses"]["h"]["model"]
    checked = check_model_contradiction({e["id"]: e for e in data["events"]}, {},
                                       data["impact"], data["hypotheses"][0], model)
    assert checked and len(model["branch_failures"]) == 512
    print(json.dumps({"status": report["status"], "independent_contradiction_check": checked,
                      "branches_covered": model["branches_tested"], "search": model["branch_search"],
                      "work": report["work"]}, sort_keys=True))
