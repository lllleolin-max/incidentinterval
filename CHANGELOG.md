# Changelog

## 0.2.0

- Refute a critical-parent prefix with a checked negative cycle before solving
  its suffix branches. Every prefix check uses the existing shared analysis
  work budget. Exhaustion still returns UNKNOWN_LIMIT without an exact range.
- Preserve every complete selector's contradiction record in the v1 report;
  add versioned `branch_search` counters distinguishing solved leaves from
  assignments refuted by prefixes. Feasible branches, ties and extrema remain
  exhaustive.
- Add `check_model_contradiction`, an independent consumer that reconstructs
  constraints and checks complete selector coverage, negative-cycle membership
  and supported search metadata. Old v1 reports without metadata remain valid.
- Add a 512-selector SDK example, separate report-consumer example, work
  benchmark, raw integer/max-plus oracle and adversarial metadata probe.
- This optimization benefits contradicted subtrees. The disclosed all-feasible
  benchmark takes more work and time. Worst-case exponential enumeration and
  retained closure memory remain; source authenticity and real-world causal
  identification remain outside the contract.

## 0.1.0

Initial bounded interval, max-plus hypothesis and conditional intervention SDK
and CLI. The original three substantive corrections and their immutable commit
IDs are retained in `docs/ITERATIONS.md`.
