# Implementation and real self-review evidence

Builder: GPT-6.1-Sol / Ultra. Local environment: Windows PowerShell, Python 3.14.3. This log records actual findings after a complete initial implementation. Builder self-review does not award portfolio scores; independent review is required at a frozen SHA. No revenue/adoption claims are made.

## Initial complete implementation

Initial scope includes installable SDK/CLI, STN negative cycles and tight partial orders, exact bounded max-plus branch solving, directly checked extremum witnesses, independent exhaustive small-instance oracles, competing hypotheses, observation-preserving and relaxed interventions, synthetic demo/contrast, security/commercial/architecture docs and CI definition.

Executed initial verification: `py -3 -m pip install .` built and installed `incidentinterval-0.1.0-py3-none-any.whl`; `py -3 -m unittest discover -s tests -v` ran 19 tests in 0.780s, OK; `py -3 examples/demo.py` passed its synthetic assertions; `py -3 examples/contrast.py` passed four executed contrasts. These are local results; remote CI is not yet run. Subsequent reviews will record before/after commits and actual failing probes here.

Initial complete implementation SHA: `a0156eba8e6998964e66bd72c7dd90df93c738b5`.

## Review 1 — malformed nested IDs and undeclared intervention conditions

Before: `a0156eba8e6998964e66bd72c7dd90df93c738b5`. Self-review tried nested arrays/objects where source/event IDs belong. Evidence arrays, link endpoints, impact endpoints and remove lists attempted set/dict operations before validating ID shape and raised uncaught TypeError. Empty action conditions were also accepted despite the explicit-assumption contract. This broke both the SDK domain-error boundary and structured CLI handling.

Actual failing command: `py -3 -m unittest discover -s tests -p test_review_input.py -v` exited 1: two test methods, one failure and four subtest errors. Observed examples: `TypeError: cannot use 'list' as a set element` for evidence, `TypeError: cannot use 'dict' as a dict key` for impact, and `InputError not raised` for empty conditions. Correction validates every nested ID before hashing/lookup and requires nonempty intervention conditions. A real CLI regression verifies exit 2, parseable INVALID_INPUT and no traceback.

After: `b4280d9b78c11070c5435756e1ba4d6e4efb861f` (`Reject malformed nested IDs and undeclared intervention conditions`). Rebuilt/reinstalled with `py -3 -m pip install . --force-reinstall`; full `py -3 -m unittest discover -s tests -v` exited 0: 22 tests in 0.866s, OK. Demo exited 0 with unchanged intended decisions. Remaining boundary: strict v1 integer/ASCII input, not an arbitrary data coercion API.

## Review 2 — independently check every witness component

Before: `b4280d9b78c11070c5435756e1ba4d6e4efb861f`. Self-review mutated critical-parent IDs, removed a critical parent, added a parent on a root and forged the claimed impact duration. The direct max-equation checker accepted those inconsistent witness fields because it checked times/delays alone. The public STN assignment checker also accepted float/bool values equal to integers. Real time equations still held, but the advertised certificate details were not fully checked.

Actual failing command: `py -3 -m unittest discover -s tests -p test_review_certificates.py -v` exited 1: two test methods, seven failing subtests (`True is not false`). Correction checks exact integer domains, exact graph-root/critical-node key sets, selected edge membership/arrival equality and claimed duration. It adds a separately implemented intervention checker that recomputes removal reachability, changed roots/links and relaxed observations without using engine graph or solver helpers, then directly verifies equation witnesses and duration/improvement coherence. Causal invalidity now includes a real closed link-ID cycle, checked independently.

After: `3466d04977fd73e225e5e58e813115e3815f8a7d` (`Independently verify complete model and intervention witnesses`). Rebuilt/reinstalled normal wheel; full unittest exited 0: 26 tests in 0.916s, OK. Four synthetic executable contrasts also passed during this round. Feasible witness checks and negative cycles are independent O(E) checks; global range optimality is established by exact union enumeration/closure and tested with a separate small-instance exhaustive oracle, not by one feasible endpoint witness alone.

## Review 3 — bound the complete review, not only one hypothesis

Before: `3466d04977fd73e225e5e58e813115e3815f8a7d`. Self-review instrumented a ten-event fixture with eight binary max gates, two supplied hypotheses and four interventions. Each solve fit the 512-branch cap, yet their sum executed 4,663 solver calls and **9,491,306 conservative work units** (`V*E + V^3` for closure). Scaling permitted hypothesis/action cardinalities multiplied this cost with no aggregate budget/accounting. The contract's small-review scope needed a workflow-wide guard.

Actual failing command: `py -3 -m unittest discover -s tests -p test_review_work.py -v` exited 1: `aggregate work accounting is missing`; printed `probe solver_calls=4663 estimated_work_units=9491306 status=ANALYZED`. Correction introduces a shared deterministic budget across observation solving, all baseline hypotheses, historical intervention checks, counterfactuals and extremum certificate solves. Every solve reserves its conservative units before execution. Partially tested max models become UNKNOWN_LIMIT and never inherit an exact range from explored branches. Defaults cap the whole analysis at 2,000,000 units; hard configurable cap is 20,000,000. Reports expose charged work and CLI accepts `--max-work`.

After: `af6a83ee744ccdad5d8dbe381deb53ef5f987010` (`Enforce aggregate solver work across hypothesis and intervention review`). Rebuilt/reinstalled; full unittest exited 0: 29 tests in 3.190s, OK. Same probe printed `solver_calls=981 estimated_work_units=1998436 status=UNKNOWN`, staying within budget. A 1-unit request invokes zero solves and returns UNKNOWN; rerunning the complete fixture with 20,000,000 units finishes ANALYZED and remains permutation-stable. The CLI returns exit 4 for budget exhaustion. These units are reproducible algorithmic upper estimates, not CPU instructions, wall-time or OS memory isolation.

## Final independent-install verification and additional probes

Additional verification adds three meaningful assertions without changing implementation: analysis leaves original observations/hypotheses intact; removing an observed deployment while preserving observations is INFEASIBLE with its source IDs; an observation-feasible max equation contradicted in **every** critical-parent branch supplies two independently checked branch negative-cycle witnesses. This is extra verification, not a fourth correction cycle.

Executed clean noneditable install:

```powershell
py -3 -m pip wheel --no-deps --wheel-dir dist .
py -3 -m venv .venv-verify
.venv-verify\Scripts\python.exe -m pip install --no-index --no-deps dist\incidentinterval-0.1.0-py3-none-any.whl
.venv-verify\Scripts\python.exe -m unittest discover -s tests -v
.venv-verify\Scripts\python.exe examples\demo.py
.venv-verify\Scripts\python.exe examples\contrast.py
.venv-verify\Scripts\incidentinterval.exe examples\incident.json
.venv-verify\Scripts\incidentinterval.exe examples\incident.json --max-work 1
```

Fresh environment imported SDK from `.venv-verify/Lib/site-packages/incidentinterval/__init__.py`, not `src/`. Final expanded suite: **32 tests in 3.948s, OK**, including 80 independent STN integer enumerations and 45 separate direct max-equation oracle cases. Synthetic demo assertions and four contrast cases passed. Installed console report: `status=ANALYZED`, `rollback=HYPOTHESIS_SENSITIVE`, charged work 8,316; tiny-budget CLI exit 4. From the separate `dist` working directory, installed SDK also returned ANALYZED with faster repair a CONDITIONAL_CANDIDATE and installed baseline returned rate_limit. This demonstrates ordinary wheel use without an editable checkout/source-path injection.

Limits remaining: only finite integer DAG AND models with independent delay intervals; critical-parent branch and total work limits; sources are opaque/unverified; hypothesis list may omit the real cause; min/max simulation bounds and unpaired improvements are not identified production effects. All fixtures are synthetic. Ubuntu/Python 3.11/remote CI are declared scope, not locally observed results. Adoption, willingness to pay and revenue are unknown. Exact final frozen SHA is supplied in the delivery report; this log cannot contain its own commit hash.
