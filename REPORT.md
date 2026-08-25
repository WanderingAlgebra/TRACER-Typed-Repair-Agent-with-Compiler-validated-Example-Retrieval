# TRACER 验收状态

当前版本已经移除离线答案表驱动的 A/B/C 评测路径。正式 pilot 必须通过 `command` 或 `openai_compatible` provider 运行；没有 provider 时不会生成指标。

## 当前可验收项

- 任意 Lean 文件、定理名和证明区域可以通过 `src/agent.py solve` 输入。
- A/B/C 只改变 prompt 上下文：题目、题目加诊断、题目加诊断和本地示例。
- 每轮最多三次，Lean 编译结果作为 verifier。
- 请求使用 SQLite 精确文本唯一键缓存，成功证明保存到 `results/solutions/`。
- 失败候选、结构化诊断、provider 配置、usage、缓存命中、编译命令和编译耗时保存到 JSONL。
- 模型返回的 Markdown 代码围栏会在解析和编译边界清洗；旧缓存候选同样适用。
- CLI 失败输出会区分 provider 调用错误与 Lean 语法、类型或目标错误，不能仅凭 `compile_ok` 判断 API 状态。
- 报告同时生成平均 token、可选的估算 API 成本和按题型汇总；人工复核台账使用同一 benchmark ID。

## 正式 pilot 命令

```powershell
python src/evaluate.py --provider openai_compatible --conditions A,B,C --fresh
python src/report.py
```

或者：

```powershell
python src/evaluate.py --provider command --provider-command 'python my_provider.py' --conditions A,B,C --fresh
```

## 解释边界

正式结果必须使用同一个 provider、模型、温度、最大输出长度和固定题集。报告会记录真实 usage 与按题型结果；题目与本地示例的相似性仍需人工标注，Wilson 区间只作为小样本 pilot evidence。没有真实 provider 的旧离线结果不具有实验解释力。
