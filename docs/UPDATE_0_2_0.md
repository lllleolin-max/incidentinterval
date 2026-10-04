# 0.2.0: proved prefix pruning within the existing work budget

This update improves repeat STN work in explicitly contradicted critical-parent
subtrees. It preserves the input/report v1 contract, complete selector failure
records, exact feasible duration endpoints and alternatives, conditional action
semantics, and the existing whole-analysis work budget. It adds an independent
contradiction consumer with metadata validation. It is not a causal inference
or production-operation capability.

Baseline `e79e924137ba006c525ac2e25c57386991509ba3` is the original 0.1.0 artifact.
The fetched README-only update was normally fast-forwarded to
`d195de259507c49c74ca6f0a6302ba4030ea541f` and retained. No history was rewritten.
Baseline canonical LF Git archive, raw Git blob, ordinary wheel and isolated
site-package bytes matched all seven package modules. Installed baseline suite:
32 tests, 4.212 seconds, PASS. Existing aggregate-budget protection was already
correct; it is not presented as a new bug or repair.

## Review 1: repeated suffix work

The unchanged `benchmarks/prefix.py` probe uses eleven events, nine binary gates
and 512 complete selectors. Root activation assumptions permit [0,1], measured
roots equal zero, and the first child must equal one despite zero delays. The
necessary envelope remains feasible, but either first-parent choice creates a
negative cycle. Both variants use `Limits(work=20_000_000)` within existing caps;
the default cap was not raised in code.

The probe before 0.2.0 failed its requested-work assertion: every complete leaf
still invoked a solver. Commit
`8967dab00e4fb396caa5ec4816ab4b1f00358e94` checks multiple-choice prefixes with
Bellman-Ford, precharged to the same budget. It emits every full selector's cycle
and skips suffix solves. The same probe then passed from a fresh normal wheel;
all seven module bytes matched and all 35 installed tests passed.

| Same-input measurement | Original 0.1.0 | Initial prefix implementation at 8967dab |
|---|---:|---:|
| Early contradiction: actual solve calls | 514 | 4 |
| Requested closure calls | 514 | 2 |
| Executed Bellman-Ford edge visits | 442,626 | 1,794 |
| Executed closure candidates | 3,456 | 3,456 |
| Charged work units | 1,331,592 | 6,024 |
| Median of three untraced runs, seconds | 0.11668 | 0.001827 |
| Whole-analysis tracemalloc peak, bytes | 899,244 | 319,530 |
| Complete failing selector records | 512 | 512 |
| All-feasible adverse case: actual solve calls | 516 | 1,026 |
| Requested closure calls | 514 | 514 |
| Executed Bellman-Ford edge visits | 37,098 | 72,814 |
| Executed closure candidates | 888,192 | 888,192 |
| Charged work units | 1,333,368 | 1,761,960 |
| Median of three untraced runs, seconds | 0.13066 | 0.14543 |
| Whole-analysis tracemalloc peak, bytes | 4,978,418 | 4,296,724 |
| Complete feasible selectors | 512 | 512 |

These are Windows/Python 3.14.3 local synthetic measurements. Actual loop counts
use line tracing of the installed solver; timing is measured separately without
tracing, and memory is Python allocation peak, not process RSS. Closure-call
counts describe requests: an infeasible solver returns before running closure.
The adverse case costs about 32% more charged work and 11% more wall time here;
timing and peak differences are not universal guarantees. Prefix checks can
cause UNKNOWN at a budget where the old complete search fitted. Initial closure,
worst-case exponential enumeration, retained feasible closures and serialized
proof volume remain. This is neither constant-memory nor unconditional speedup.

The first observation/base closure calls were also measured separately. In both
versions their incremental tracemalloc peak growth was 7,944/8,376 bytes for
12 nodes and 23/63 unique edges; retained growth was 7,240/7,672 bytes. This
excludes previously allocated outer state and is not whole-process peak/RSS.
The optimization leaves this initialization cost in place.

## Review 2: independent semantics and proof consumption

`probes/update_oracle.py` determines expected worlds by literal integer roots,
delays and max equations. It calls no production graph, envelope, transformation,
solver or checker to compute expected results. Actual counts:

- 180 incident fixtures, 197 model comparisons, 176 feasible models;
- 528 complete critical-parent alternative sets and feasible-selector counts;
- 880 historical and 880 counterfactual comparisons;
- 1,065 historical and 1,589 counterfactual critical-parent alternative sets,
  including complete feasible-selector counts and raw-world endpoint attainment;
- 900 conditional action decision/effect comparisons;
- 150 additional tiny integer STNs, 54 feasible, 324 exact pair-range comparisons.

All matched. Inputs remained unchanged. The original independent probe also ran
unchanged against the installed wheel: 100 STNs/1,025 pair ranges, 140 max-plus
fixtures/62 alternative sets, 155 interventions, malformed domains, forged
certificates, missing evidence and shared-budget boundaries all passed.

An actual adversarial consumer finding remained: the new checker validated the
negative cycles and selector coverage but ignored malformed `branch_search`
metadata. The unchanged `probes/update_proof_boundaries.py` observed nine invalid
metadata cases accepted at `8967dab`; these include bool/unknown version,
unknown method, impossible or negative counters, and missing/extra fields.
Commit `d5e60d824ab6da3f883922d72a79a54d8e8b45c5` validates exact field types,
supported format and possible coverage accounting. Same normal-wheel probe:
all nine rejected, legacy no-metadata report accepted. Fresh seven-module
association and all 36 installed tests passed (5.701 seconds). Metadata remains
an execution claim, not authenticated telemetry. Logical contradiction is proved
by independently reconstructed constraints, every complete selector and each
negative cycle.

## Review 3: installed delivery and compatibility

The ordinary installed SDK and actual sysconfig console ran 33 cases across
native, PYTHONUTF8=0 and PYTHONUTF8=1. Normal/baseline/BOM inputs returned 0;
malformed duplicate/nonfinite/UTF-8/oversize inputs returned structured JSON 2;
inconsistent observations and the 512-selector contradiction returned 3;
whole-work and branch limits returned 4 with no partial exact range. All input
file bytes were preserved. SDK and console reports matched. The original demo,
four-case contrast, new prefix example and separate independent report consumer
all returned 0. A report actually produced by the ordinary 0.1.0 console,
containing 512 full selector failures and no search metadata, passed the new
consumer unchanged (SHA256
`caed9b5d0d08cf7f51b1f9cc0e215c7fa7f4afd81ddb05521e2ba30f4d8e93c3`).
Old v1 reports retain the same selector/cycle proof format.

Those initial delivery checks passed, but an additional repeated-return memory
probe found a real regression before publication. The nested recursive `visit`
function referenced its own closure cell, retaining every explored branch's
closure until cyclic garbage collection. With automatic GC disabled for a
reproducible diagnostic, three legal 512-leaf SDK calls returned while current
Python allocations grew 4,251,585 → 8,375,593 → 12,488,489 bytes. Explicit GC
reclaimed 12,392,830 bytes. Original 0.1.0 on the same probe remained near
186,831 bytes after three calls, with 91,544 bytes reclaimed. This is delayed
release of unreachable state, not a claim of permanently uncollectable memory.

The before artifact `8941acf726ed33932d16619825f8f8d2f20450d0` is retained. An
installed-wheel regression independently exercised both completed searches and
200,000-unit WorkLimit interruptions: 12,567,538 and 1,432,012 bytes respectively
remained unreachable until explicit GC; both subtests failed the 500 KB fixture
bound. Commit `17a47410f6ad0bef10022e24be5320db92cddc32` clears the recursive cell
in `finally`, including exception unwind. The unchanged standalone retention
probe then passed: current allocations after three runs were 186,911 → 187,287
→ 187,319 bytes, with 91,696 reclaimed by explicit GC. The meaningful completed
and interrupted regression and all 37 installed tests passed. Disabled GC is
diagnostic only; reports/input remain alive, and values measure Python
allocations, not RSS or an OS quota. The full live search still uses O(BV²)
closure memory. Solver/loop/work counts and complete proof records did not change
in this correction. Wall times varied between local runs and remain observations
rather than performance guarantees.

The original three substantive corrections remain in `ITERATIONS.md`; this
update now has three actual substantive corrections across three review stages.
Extra probe coverage and documentation commits are not additional fix cycles.

Two probe errors are preserved separately from product findings: the first work
driver treated the hypotheses dictionary as a list, causing KeyError before
measuring results; the first delivery driver incorrectly expected BOM rejection.
The unchanged CLI has always passed binary input to json.loads, which accepts a
BOM. Corrected drivers produced the reported results; no product changes were
made for those harness mistakes. The final exact SHA and canonical installation
receipts are supplied separately because this file cannot contain its own hash.

Customer usage, revenue and production savings remain unknown. Source references
are opaque, hypotheses may omit the true mechanism, and independent delay/AND
assumptions remain. Linux/Python 3.11 and remote CI are not locally executed claims.
