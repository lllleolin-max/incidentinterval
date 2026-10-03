# Contributing

Create a normal virtual environment and install `python -m pip install .`; run `python -m unittest discover -s tests -v`, `python examples/demo.py` and `python examples/contrast.py`. After changing code, reinstall the package before running these tests, so an old installed wheel does not mask your changes. CI runs Ubuntu/Windows and Python 3.11/3.14. Keep Python 3.11 compatibility and MIT licensing.

Please give a small synthetic incident, expected/actual status and declared model assumptions. A changed causal inference promise requires an independent direct-equation oracle or certificate check. Add adversarial cases for unknown models, limit handling, inclusive endpoints and permutation invariants rather than tests that merely mirror implementation lines. Do not add probability or source-authenticity claims without implementing/verifying their meaning. Keep references and customer information sanitized.

Document unsupported subsets explicitly. A cycle is an invalid DAG model, not an automatically disproven real-world feedback loop. UNKNOWN must stay distinguishable from infeasibility. Baselines must be runnable and honestly scoped; narrative competitor documentation is not executable evidence of beating their implementation. Contributions improving JSON import from existing incident tooling are welcome, provided imported assumptions remain explicit.
