# 项目作用与已验证用法

IncidentInterval 用于 SRE 事故解释审查：跨机器时钟不一致时，把“真实时间可能在某区间”和有来源的时间差观察组织成约束；检查部署、负载等多个明确假设，再比较回滚、限流、修复提速的有界结果。它解决复盘中把日志点时间排序误当因果顺序、忽略替代解释、或者把不可能的干预效果写进跟进票据的问题。

为什么做：叙事时间线和贡献因素讨论已有成熟工具。这个项目提供可运行的补充检查——带来源的时间矛盾负环、可行偏序、关键前置条件、在已声明 AND 模型下的干预结果及未知项。它不自动发现原因，不把模拟说成事实，不执行生产操作，也不声称竞品没有这些能力。

实际已测命令（仓库目录，Windows/Python 3.14.3）：

```powershell
py -3 -m pip wheel --no-deps --wheel-dir dist .
py -3 -m venv .venv-verify
.venv-verify\Scripts\python.exe -m pip install --no-index --no-deps dist\incidentinterval-0.1.0-py3-none-any.whl
.venv-verify\Scripts\python.exe examples\demo.py
.venv-verify\Scripts\python.exe examples\contrast.py
.venv-verify\Scripts\incidentinterval.exe examples\incident.json
.venv-verify\Scripts\python.exe -m unittest discover -s tests -v
```

安装为非 editable wheel；SDK 从虚拟环境 site-packages 导入。32 项测试通过，含独立小实例穷举 oracle；演示完整完成 JSON→观察可行性→两种假设比较→干预决定。时间排序选择限流；仅部署假设下限流没有收益、回滚是条件性候选；加入负载假设后回滚和限流都变成假设敏感。修复提速在两假设下均把模型时长从 20 秒变为 5 秒，延迟审批增加到 30 秒则为不利；强行同时保留原始 20 秒观察的 5 秒修复被拒绝。所有数据与效果为合成模拟。

商业价值解释：特定用户是审核事故整改措施的可靠性工程师/服务负责人，可把 JSON/证书与现有复盘文档联用，先收集能区分假设的证据，再做人工验证。准备模型也有成本；`VALUE.md` 给出明确假设的正/负时间价值例子，没有客户、定价、收入或采用数据。

技术价值解释：整数差值约束、可行赋值与负环证据、精确 max 方程的有界分支求解、独立关键父边/干预证书检查、时长端点与偏序，以及整次分析工作预算。循环结构不在支持范围，返回 INVALID_MODEL/UNKNOWN；超过分支/工作量返回 UNKNOWN_LIMIT，不拿采样结果冒充证明。

创新价值解释：可执行区间一致性与机制模型共同影响干预选择；实际运行时间排序和去掉机制证据的消融，覆盖有利、不利、不可识别和不可能情况。已核查 incident.io 官方复盘/时间线文档并致谢；不是世界首创或对未运行竞品的胜负声明。

三轴分数：**等待独立评审，未自评为达标**。README、架构、格式、安全、贡献、价值机制、MIT、Ubuntu/Windows × Python 3.11/3.14 CI 和三轮真实审查修正记录齐全；远端 CI 仍需主代理发布后核验。
