"""Disclosed timestamp-proximity heuristic, not a competitor implementation."""


def timestamp_only(data):
    times = {e["id"]: e.get("timestamp", (e["interval"][0] + e["interval"][1]) // 2)
             for e in data["events"]}
    start = data["impact"]["start"]
    # Heuristic: the latest earlier removable root is blamed; uncertainty ignored.
    candidates = sorted((times[n], n, action["id"]) for action in data.get("interventions", [])
                        for n in action.get("remove", []) if times[n] < times[start])
    return {"sorted_events": sorted(times, key=lambda n: (times[n], n)),
            "selected_intervention": candidates[-1][2] if candidates else None,
            "limitations": "heuristic proximity blame, no evidence/interval/alternative-model checks"}
