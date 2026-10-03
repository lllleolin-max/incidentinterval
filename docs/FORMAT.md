# Version 1 JSON and SDK contract

All timestamps/delays are integers at a **declared resolution**, using one incident-relative origin and `time_unit` `ms`, `s` or `tick`. Intervals are inclusive. Booleans, floats, nonfinite values and inputs outside ±10^12 are invalid; delays must be nonnegative. Quantizing real timestamps is the caller's responsibility: widen bounds outward, do not round away uncertainty. Source/event/constraint/hypothesis/action IDs are ASCII, 1..80 characters; duplicate IDs and unknown keys are rejected. The complete runnable example is `examples/incident.json`.

| Field | Required meaning |
| --- | --- |
| `version` | Integer 1 |
| `sources` | Array of `{id, reference, description?}`; references are opaque and never fetched |
| `events` | Nonempty array of `{id, interval:[min,max], evidence:[source_id]?, timestamp?, label?}`. `timestamp` is optional point inside interval, used only by the baseline |
| `observations` | Array of `{id, from, to, delta:[min,max], evidence?}` for measured `t[to]-t[from]` |
| `impact` | `{start,end}`: distinct known failure-occurrence and recovery events; duration must be nonnegative |
| `hypotheses` | Nonempty array `{id, assumptions:[text,...], roots:{root_event:[min,max]}, links:[...]}` |
| hypothesis link | `{id, from, to, delay:[min,max], evidence?}`; every incoming link is a necessary prerequisite |
| `interventions` | Array `{id, assumptions:[text,...], remove?:[event], roots?:{root:[min,max]}, delays?:{link_id:[min,max]}, preserve_observations?:bool}` |

Every graph root, including an unrelated observed event, needs an activation window. Root maps must exactly match the graph roots. The same link ID across hypotheses intentionally lets one delay intervention target their common mechanism; absent link IDs in a specific hypothesis have no effect there. A root override on a nonroot in a specific hypothesis is `INVALID_INTERVENTION`, not a valid do-operation. The tool does not infer causal graphs from observation ordering.

Removing a node removes all descendants under the AND prerequisite model. Removing impact start predicts prevention under that assumption; removing recovery while retaining impact start gives unidentified duration. `preserve_observations:true` requests that counterfactual times still satisfy all original observations and therefore can be infeasible. By default, bounds on affected descendants and observations touching them are relaxed; unaffected observations remain. Every relaxed ID is listed. A separate `historical_compatibility` check always tests original observations first.

## Output

Top-level statuses: `ANALYZED`, `INFEASIBLE_OBSERVATIONS`, `NO_CONSISTENT_MODEL`, `UNKNOWN`. CLI exit codes: 0=analyzed, 2=invalid input/file/limits, 3=contradicted observations or no consistent hypothesis, 4=an unknown hypothesis remains. Action-level unknowns do not change the report exit code: read `decisions` and intervention statuses. CLI `--baseline` produces only the timestamp heuristic output after validating the input.

The observation network contains source-bearing inequalities `t[target]-t[source] <= bound`, an assignment with `@origin = 0`, tight event bounds, and pairwise partial-order relations. `delta` means `t[b]-t[a]`; a relation label is relative to `a` and `b`. `equal` is proven equal by constraints; `before_or_equal` permits ties; `unresolved` means neither order is forced.

`INFEASIBLE` temporal networks carry a negative-cycle certificate. Its edges form a closed connected walk, belong to the supplied inequalities, and sum to a strictly negative upper bound. This contradicts the telescoping sum of time differences, which is zero. Sources identify what to inspect; the certificate is sufficient but need not be a minimal unsatisfiable subset.

Each hypothesis contains its user conditions, missing mechanism evidence, model status and intervention reports. `INVALID_MODEL` is a causal cycle/root mismatch outside the supported structural subset; it stays UNKNOWN and is not called disproven causality. `UNKNOWN_LIMIT` means exact enumeration was not run. A FEASIBLE max model supplies a concrete assignment and in-range delays satisfying every max equation; `duration_extrema` proves attained minimum/maximum times. The min/max envelope may have gaps in its interior.

`critical_parent_alternatives` lists selections from all feasible critical-parent branches. `witness_critical_path` is one feasible path to recovery, not the unique historical critical path. `impact_duration` is exact within the bounded structural model. `improvement_enclosure` subtracts independently varying baseline and scenario envelopes, and is a conservative **unpaired** bound, not a shared-world causal effect distribution.

Decision values: `CONDITIONAL_CANDIDATE` means every supplied consistent hypothesis predicts guaranteed duration reduction or prevention under its assumptions; `HYPOTHESIS_SENSITIVE` means benefit depends on which supplied hypothesis holds; `NEEDS_MECHANISM_EVIDENCE` means a mechanism link has no source; `INSUFFICIENT_MODEL_INFORMATION` means unknown models/effects remain; `AVOID_UNDER_DECLARED_MODELS` means all models worsen duration; otherwise `NO_GUARANTEED_BENEFIT`. No result proves causality, authenticates sources, or establishes that the hypothesis list is complete.

Default Limits: 48 events, 256 observations/links/sources, 12 hypotheses, 24 interventions, 512 critical-parent branches per solve, 1 MB CLI input, and **2,000,000 aggregate work units per analyze call**. Hard configurable caps are 96, 512, 24, 48, 4096, 4 MB and 20,000,000 respectively. Every solver call reserves `V*E + V^3` for closure or `V*E` without closure, with unique edges and origin included. Work is conservatively charged before execution, across observations, all hypotheses, historical checks, counterfactuals and extremum certificates. The report exposes `work.limit/charged/solver_calls/exhausted`. Use SDK `Limits(work=...)` or CLI `--max-work`; exhaustion returns UNKNOWN and CLI 4, never extrapolating untested branches. These are algorithmic estimates, not measured CPU instructions or an OS time/memory sandbox. Input-cardinality violations are `InputError`; a valid model exceeding its branch/work cap is `UNKNOWN_LIMIT`.
