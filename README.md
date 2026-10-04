# IncidentInterval

Review an incident explanation across skewed clocks, before turning it into a remediation ticket. This local Python SDK and CLI checks timestamp intervals and sourced time differences, compares **explicitly supplied** causal hypotheses, and computes bounded intervention effects under an exact, declared max-plus model. It returns independently checkable assignments, negative-cycle witnesses, partial orders and critical-parent alternatives.

面向 SRE 事故复盘：把不确定的时间区间、带来源 ID 的观察和多个明确声明的因果假设一起检查。发现不可能的时间线时给出矛盾证据；对回滚、限流和修复提速给出有条件的模拟结果，保留替代解释和未知项。时间接近不证明因果，模拟结果不是已观察到的事实。

## Tested quickstart / 已测快速开始

Install from a source checkout with Python 3.11+:

```sh
git clone https://github.com/lllleolin-max/incidentinterval.git
cd incidentinterval
```

Linux/macOS:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/python examples/demo.py
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install .
.venv\Scripts\python.exe examples/demo.py
```

In the remaining examples, `python` means this environment's interpreter:
`.venv/bin/python` on Linux/macOS or `.venv\Scripts\python.exe` on Windows.
The runtime uses the standard library; source installation may download build
dependencies. No PyPI release is required for these instructions.

The demo reads the checked-in synthetic fixture, prints the results below and
exits `0`; it performs no production action. To inspect the full JSON report:

```sh
python -m incidentinterval.cli examples/incident.json
```

Optional comparison and development checks are `python examples/contrast.py`
and `python -m unittest discover -s tests -v`.

`pip install .` builds and installs a normal wheel, not an editable checkout. The installed console command is `incidentinterval examples/incident.json`. The module form avoids a scripts-directory PATH issue. GitHub Actions declares Ubuntu/Windows with Python 3.11/3.14; local evidence is Windows/Python 3.14.3. Remote CI results remain unverified until publication.

Expected key demo outputs:

```text
deploy_fault duration [20, 20] critical path ['deploy', 'impact', 'recovery']
load_fault duration [20, 20] critical path ['load', 'impact', 'recovery']
faster_recovery CONDITIONAL_CANDIDATE
rollback HYPOTHESIS_SENSITIVE
slower_recovery AVOID_UNDER_DECLARED_MODELS
remove_recovery INSUFFICIENT_MODEL_INFORMATION
```

例子全部为合成数据：部署日志的记录时间是 20 秒，真实时间区间是 0–40 秒。单一部署假设下，时间排序误选限流，区间机制建议把回滚作为条件性候选；加入负载假设后，回滚变成“取决于假设”。把部署时钟校准到 20 秒又排除部署假设。两假设下修复提速均把影响持续时间从 20 秒变为 5 秒；保留原始 20 秒观察同时声称修复只用 5 秒会被拒绝。这些是执行过的模拟断言，不能视作生产改善。

## SDK / SDK 使用

CLI input is one local incident JSON file containing sourced event intervals,
observations, declared hypotheses and interventions. Stdout is the JSON report;
handled input errors are JSON on stderr. Exit codes:

| Code | Meaning |
|---|---|
| `0` | Analysis completed; read each decision's conditions before acting |
| `2` | Invalid input, usage or file error |
| `3` | Observations are inconsistent or no declared model is consistent |
| `4` | The bounded analysis is `UNKNOWN`; not proof of infeasibility |

**中文：** 退出 `0` 表示分析完成，不代表自动批准某个修复动作；`3` 是已发现矛盾，
`4` 是资源边界内无法确定。报告中的候选措施仍需要维护者审阅与验证。

```python
import json
from incidentinterval import analyze, Limits

with open("examples/incident.json", encoding="utf-8") as file:
    incident = json.load(file)
report = analyze(incident, limits=Limits(branches=512))
print(report["decisions"]["rollback"]["decision"])
# HYPOTHESIS_SENSITIVE
```

`analyze` does not mutate the input. Malformed/unsupported inputs raise `InputError`; contradictions and resource-limit unknowns are valid report statuses. The [input and output contract](docs/FORMAT.md) describes every field. [Architecture](docs/ARCHITECTURE.md) includes the max-equation proof, complexity, certificates and supported subset. [Independent checker](src/incidentinterval/checker.py) verifies feasible model witnesses directly without invoking the solver.

Version 0.2.0 checks critical-parent prefixes for negative cycles before solving
their suffixes. A contradiction of a prefix refutes every extension. Reports
still contain a certificate for every complete selector, so v1 report consumers
retain the same proof format. `branch_search` distinguishes actual prefix checks,
leaf solves and covered assignments. All work shares the existing whole-analysis
budget; an incomplete search returns UNKNOWN rather than a partial exact result.

```sh
python examples/prefix.py
python probes/update_oracle.py --output oracle-results
python probes/update_proof_boundaries.py --output proof-results
```

The prefix example covers 512 complete selectors with two prefix checks and no
leaf solves. It uses `check_model_contradiction` to reconstruct constraints and
verify complete coverage independently. To consume a saved contradicted-model
report separately, run `python examples/check_contradictions.py INCIDENT.json
REPORT.json`. That example checks refuted models; a feasible endpoint alone does
not certify global optimality. The SDK checker accepts old v1 contradiction
reports without the new metadata.

The [measured update](docs/UPDATE_0_2_0.md) includes an adverse all-feasible case:
prefix checks can cost more, and they do not reduce worst-case exponential
enumeration or retained feasible closure memory. Default branch/work limits are
unchanged. The [changelog](CHANGELOG.md) describes the additive interface.

## Review workflow / 用于实际复盘

1. Pick a small set of significant events; normalize a common origin/unit and record inclusive clock bounds. Add source IDs pointing to logs, offset measurements or experiment notes. The tool does not retrieve or authenticate these sources.
2. Add observed time differences (for example one monotonic-clock span) separately from causal assumptions. Write competing hypothesis graphs with explicit root windows and propagation delays. A missing mechanism source blocks a conditional action recommendation.
3. Run the CLI. Fix an observation contradiction before evaluating hypotheses. Read conditions, unknowns, temporal relations and each model's critical-parent alternatives; one critical path is a witness rather than an identified historical truth.
4. Review each intervention's historical compatibility, relaxed observations and modeled outcome. Leave an evidence collection ticket when the result is hypothesis-sensitive or unidentified; use a conditional candidate as input to human staging validation, never as an automatic production instruction.

先整理来源与时钟误差，再写明假设；不要把报告里的可行解复制成“精确发生时间”。干预只放宽受影响节点及相关差值观察，保留未受影响观察。删除恢复事件不等于避免事故。当前只支持无环、AND 前置条件模型，概率因果推断、OR 触发、反馈控制和外部生产操作不在范围内。

## Comparison and scope

[incident.io's official post-mortem template](https://incident.io/hubs/post-mortem/incident-post-mortem-template) already organizes incident timelines, contributors, mitigators and follow-up actions. Its [timeline editing documentation](https://docs.incident.io/incidents/edit-timeline) is an existing workflow reference. These primary sources were checked on 2026-10-03. The timeline page returned its title/navigation to the text retrieval tool, so no detailed feature-absence inference is made. IncidentInterval complements narrative review with executable uncertainty constraints and assumption-sensitive counterfactual certificates; it does not claim that incident.io lacks those features or that this is a first invention.

`python examples/contrast.py` executes a disclosed local timestamp-proximity heuristic and a mechanism-evidence ablation on four synthetic cases. It is **not** a benchmark against incident.io. See [measured comparisons and bounded commercial rationale](docs/VALUE.md). Customer adoption, revenue and willingness to pay are unknown. No independent axis scores have been awarded by this repository.

MIT licensed. [Security and trust boundaries](SECURITY.md), [contributing](CONTRIBUTING.md), and [real review/change/verification history](docs/ITERATIONS.md).
