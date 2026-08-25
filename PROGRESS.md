# 当前工作进度

更新时间：2026-08-25

## 已完成

- 将 TRACER 的编译器封装扩展为可直接运行 Lean 文件的 `run_lean_file()`。
- 新增 `leancapsule pack`，支持按定理名或行区间选择输入并生成完整文件 fallback capsule。
- 新增 `leancapsule replay`，编译 `Capsule.lean` 并比较编译状态、诊断类别和规范化 `diagnostic_key`。
- 新增 `leancapsule verify` 批量验收和 `leancapsule issue` Markdown 渲染。
- 保存 `capsule.json`、工具链与 Lake 配置、原始诊断、README、PowerShell/Unix 回放脚本。
- 增加 Std、Mathlib、project-local 三类来源的公开失败 gallery，共 24 个 capsule。
- 增加单次 Agent 的 API 配置参数和本地 HTTP `/solve` 接口；密钥只在内存中使用。
- README、Progress、核心新增代码注释统一使用中文。
- 新增 theorem standalone 抽取：保留 imports、namespace 和目标定理，并在编译不一致时自动 fallback。
- 新增有界贪心 import 删除；每次删除都重新编译并比较诊断键。
- 增加 project-local fallback 示例、Mathlib v4.32.0 依赖工程和跨平台依赖准备脚本。
- 生成 `capsules/index.json`，四类 taxonomy 和三类来源均达到 gallery 覆盖门槛。
- 同步生成 `capsules/index.csv` 和 `capsules/index.md`，便于表格分析与 GitHub 浏览。
- 增加 `capsules/MANUAL_REVIEW.csv`，逐 capsule 登记自动回放与人工复核状态。
- 新增 `leancapsule audit` 发布审计，检查布局、许可、本机路径、敏感内容、成功证明和复核台账。
- 发布审计同时使用 `capsule_schema/leancapsule-v0.1.schema.json` 执行 Draft 2020-12 结构校验。
- 清理全部公开诊断中的本机绝对路径，补齐旧案例许可，并完成 24 个案例的仓库级逐项复核。
- 将 Mathlib 冷启动回放预算调整为 180 秒，并避免环境脚本重复获取已存在的预编译缓存。
- 修正 GitHub Actions 顺序：端到端测试依赖真实 Lean 编译器，现已在运行测试前安装 Lean，并增加顺序回归测试。
- GitHub runner 的端到端 Lean 编译采用独立 120 秒预算；测试失败详情会直接写入 Actions Summary。

## 当前验证状态

- `leancapsule verify capsules`：24/24 通过（Std 14、Mathlib 4、project-local 6）。
- `leancapsule gallery capsules --out capsules/index.json`：通过；四类 taxonomy 均不少于 3 个，三类来源均不少于 4 个。
- `leancapsule audit capsules`：24/24 通过，无发布审计错误。
- 完整 Python 测试 34/34：包含外部文件显式工具链、CI 安装/构建/测试顺序、Lean Action 仅安装模式、gallery、manifest、索引输出、路径清理和复核账本检查；`lake build` 通过。
- Mathlib 回放在准备 `mathlib_project` 依赖缓存后通过；缓存目录不提交到仓库。

## 明确边界

- capsule gallery 验收的是失败复现协议，不等同于真实模型 A/B/C 实验；模型实验需另行配置 provider、冻结模型参数并记录 token、延迟和编译次数。
- 多文件依赖目前采用完整文件 fallback 与显式本地文件清单，不承诺任意项目的程序切片。
