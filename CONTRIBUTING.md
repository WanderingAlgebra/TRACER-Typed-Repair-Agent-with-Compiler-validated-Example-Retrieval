# 贡献指南

1. 安装 Python 3.10+，并使用 `lean-toolchain` 指定的 Lean/Lake 版本。
2. 提交前运行 `python -m unittest discover -s tests -v`。
3. 修改 Lean 编译链路后运行 `lake build`。
4. 修改公开案例后运行 `python -m leancapsule audit capsules` 和 `python -m leancapsule verify capsules`。
5. 不得在正式评测路径中加入标准答案表或按题号路由的确定性答案逻辑。
6. provider 凭据只通过进程内参数或环境变量提供，不提交凭据和包含敏感信息的运行日志。
7. 正式 A/B/C 结论必须来自同一真实 provider、冻结题集、完整 JSONL 日志和已完成的人工复核。
