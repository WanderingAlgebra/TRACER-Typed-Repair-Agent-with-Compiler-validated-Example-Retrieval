# 贡献指南

1. 安装 Python 3.10+，并使用 `lean-toolchain` 指定的 Lean/Lake 版本。
2. 先运行 `lake build`，再运行 `python -m unittest discover -s tests -v`；端到端测试依赖已准备好的 Lean 工程。
3. 修改 Windows 入口脚本后，确认文件保持 ASCII，并使用 Windows PowerShell 5.1 parser 检查语法；CI 的 Windows job 会重复该检查。
4. 修改公开案例后运行 `python -m leancapsule audit capsules` 和 `python -m leancapsule verify capsules`。
5. 不得在正式评测路径中加入标准答案表或按题号路由的确定性答案逻辑。
6. provider 凭据只通过进程内参数或环境变量提供，不提交凭据和包含敏感信息的运行日志。
7. 正式 A/B/C 结论必须来自同一真实 provider、冻结题集、无缓存命中的严格 fresh 运行、完整 JSONL 日志和已完成的人工复核。
8. 原始 JSONL、SQLite 缓存、solutions 和归档受 `.gitignore` 保护；只交接经 `scripts/export_pilot.py` 脱敏并人工检查后的目录，且不得复制请求缓存。
9. 检索示例不得复制或仅改名冻结题目的声明；修改 `examples/` 后必须运行检索泄漏回归测试。
10. 不得放宽 provider 的 HTTPS/同源重定向规则，或让 Lean 候选子进程重新继承父进程凭据；新增候选语法必须先评估元编程执行风险。
