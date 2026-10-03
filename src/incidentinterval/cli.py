"""Strict local JSON CLI. Exit 0=analyzed, 2=invalid, 3=inconsistent, 4=unknown."""
import argparse
import json
import sys
from pathlib import Path
from .domain import InputError, Limits
from .engine import analyze
from .baseline import timestamp_only


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Review interval evidence and explicitly supplied incident hypotheses")
    parser.add_argument("input", type=Path, help="v1 incident JSON (local file only)")
    parser.add_argument("--max-branches", type=int, default=512)
    parser.add_argument("--baseline", action="store_true", help="run disclosed timestamp-only heuristic")
    args = parser.parse_args(argv)
    try:
        limits = Limits(branches=args.max_branches)
        with args.input.open("rb") as handle:
            raw = handle.read(limits.bytes + 1)
        if len(raw) > limits.bytes:
            raise InputError(f"file exceeds {limits.bytes} byte limit")
        data = json.loads(raw, object_pairs_hook=unique_object,
                          parse_constant=lambda x: (_ for _ in ()).throw(InputError(f"nonfinite JSON: {x}")))
        report = analyze(data, limits=limits)
        if args.baseline:
            report = timestamp_only(data)
            status = 0
        else:
            status = (4 if report["status"] == "UNKNOWN" else
                      3 if report["status"] in ("INFEASIBLE_OBSERVATIONS", "NO_CONSISTENT_MODEL") else 0)
        print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False))
        return status
    except (InputError, OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        print(json.dumps({"status": "INVALID_INPUT", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
