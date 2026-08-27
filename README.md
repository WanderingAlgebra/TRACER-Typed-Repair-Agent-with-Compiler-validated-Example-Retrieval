# TRACER / LeanCapsule
  ![TRACER Poster](TRACER.png)
TRACER 是一个由 Lean 编译器验证的证明修复与失败工件工具。LeanCapsule 是其中面向社区复现的核心协议：它把 Lean 文件、工具链、项目配置和规范化诊断打包成可回放的 capsule。本项目的结果将会展示在[这里](https://sjtu-ai4math.github.io/summer-school/2026/)。

仓库同时保留两条互补路径：

- `leancapsule`：生成、回放、批量验收和渲染 Lean 失败工件；
- `src/agent.py`：使用编译反馈和本地示例进行局部证明修复。

## 快速开始

建议在已经安装 Lean、Lake 和 Python 的环境中运行：

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
lake build
```

生成一个 capsule：

```powershell
python -m leancapsule pack `
  --project . `
  --file examples/capsule_failures/unknown_identifier.lean `
  --lines 1:7 `
  --out capsules/std/unknown-identifier
```

回放并核验：

```powershell
python -m leancapsule replay capsules/std/unknown-identifier
python -m leancapsule verify capsules
python -m leancapsule audit capsules
python -m leancapsule issue capsules/std/unknown-identifier --out issue.md
python -m leancapsule gallery capsules --out capsules/index.json
```

所有命令都输出机器可读 JSON；`replay`、`verify`、`audit` 和 `gallery` 会用进程退出码表示是否通过。Mathlib 冷启动可能需要较长时间，因此回放默认超时为 180 秒。

当前修订包含严格的 pilot 校验、正式报告门禁和脱敏导出流程。仓库中的示例结果不会代替真实 A/B/C 模型实验；正式结论必须同时具备完整原始 JSONL 轨迹、成功证明文件和人工复核。

使用 `--theorem` 时，工具会先尝试保留 imports、namespace 和目标定理的 standalone 文件；如果编译结果与原始诊断不一致，就自动退回完整文件。standalone 成功后会在固定编译预算内逐个尝试删除 imports，也可以使用 `--no-minimize-imports` 关闭。

## 公开失败 gallery

仓库当前包含 24 个可回放 capsule，覆盖四类失败：`Name / import`、`Type / application`、`Elaboration / instance` 和 `Goal / scope`，每类至少 3 个；来源覆盖 Std、Mathlib 和 project-local，每类来源至少 4 个。`capsules/index.json`、`capsules/index.csv` 和 `capsules/index.md` 是由 CLI 生成的三种 gallery 索引，`capsules/MANUAL_REVIEW.csv` 记录逐案例的语义、来源和敏感内容复核结论。

发布审计会检查必需文件、manifest、冻结分类、来源许可、绝对本机路径、疑似敏感凭据、成功案例中的未完成证明以及复核台账完整性。CI 会在构建和全量回放前强制运行该审计。

Mathlib 案例使用独立的 `mathlib_project/` 依赖工程。首次回放前请执行：

```powershell
./scripts/setup_mathlib.ps1
```

Linux/macOS 可执行 `bash scripts/setup_mathlib.sh`。该步骤会按 `mathlib_project/lakefile.lean` 中的固定版本下载依赖和预编译缓存；依赖缓存不纳入仓库。没有网络或未准备缓存时，Std 与 project-local 案例仍可独立回放，Mathlib 案例会明确报告缺少依赖环境。

若网络中断导致 `.lake/packages/mathlib` 只留下残缺 Git 目录，Windows 脚本会自动清理该可再生成目录后重试。使用 PowerShell 时请先设置正确的工具链目录：`$env:ELAN_HOME = "$env:USERPROFILE\\.elan"`；若通过本地代理联网，同时设置 `HTTP_PROXY` 和 `HTTPS_PROXY`。

## 证明修复 Agent

目标文件可以包含 `-- PROOF_START` / `-- PROOF_END` 标记，也可以包含唯一的 `sorry` 占位符。原文件不会被覆盖，成功的隔离证明会保存到 `results/solutions/`。

```powershell
python src/agent.py solve `
  --file lean_project/Benchmarks/Evaluation18.lean `
  --theorem Eval18.and_swap_eval `
  --condition B `
  --provider mock `
  --mock-candidate "by intro h; exact And.intro h.right h.left"
```

## 直接输入 API 配置

完整的 DeepSeek、OpenAI GPT、PowerShell / Git Bash 配置、环境变量、本地 HTTP 接口和排错步骤见 [模型 API 使用指南](docs/API_GUIDE.md)。当前内置 provider 使用 **Chat Completions**；不直接支持 Responses API，也不能把其他协议的 URL 原样替换进来。

单次运行可以在命令行输入接口地址、模型，并通过安全提示输入密钥。输入时终端不会显示密钥；读取完成后只显示字符数和末四位，便于确认粘贴是否成功。完整密钥只存在于当前进程内，不写入日志和缓存：

DeepSeek 示例（下列单行命令同时适用于 PowerShell 与 Git Bash）：

```text
python src/agent.py solve --file lean_project/Benchmarks/Evaluation18.lean --theorem Eval18.and_swap_eval --condition B --provider openai_compatible --api-url "https://api.deepseek.com/chat/completions" --model deepseek-v4-pro --temperature 0 --max-tokens 12000 --api-key-prompt --max-rounds 3 --timeout 60
```

OpenAI GPT 示例（输入 OpenAI 官方 API 密钥，不是 DeepSeek 密钥）：

```text
python src/agent.py solve --file lean_project/Benchmarks/Evaluation18.lean --theorem Eval18.and_swap_eval --condition B --provider openai_compatible --api-url "https://api.openai.com/v1/chat/completions" --model gpt-4.1 --temperature 0 --max-tokens 4000 --api-key-prompt --max-rounds 3 --timeout 60
```

DeepSeek Flash 可将模型改为 `deepseek-v4-flash`。GPT-4.1 是当前请求结构的兼容示例，并非最新模型推荐；GPT-5 等模型的参数不能直接照搬。示例预算不保证成功，也不构成等预算模型比较。DeepSeek 思考模式下温度参数不生效，详见指南中的官方依据。

如果账户不支持该模型，再替换为接口返回的其他可用模型名称；不要保留占位符文字。模型即使返回 Markdown 的 `lean` 代码围栏，TRACER 也会先提取其中的局部证明，再交给 Lean 编译器；相同请求命中旧缓存时也会执行同样的清洗。

### 如何判断失败位置

- 出现 `provider_error`：请求尚未进入 Lean 编译阶段，应检查接口地址、密钥、模型名、额度或代理。
- 出现 `diagnostic.category = syntax/type/goal`：模型请求已经成功，失败来自候选证明的 Lean 编译结果。
- `compile_ok: false` 本身不代表 API 损坏；应同时阅读 `diagnostic`。
- 每轮详细候选、缓存命中、模型 usage 和编译诊断记录在 `results/agent_runs.jsonl`。
- 成功证明保存到 `results/solutions/`；持续失败的最后候选保存到 `results/solutions/failures/`。

### 正式 pilot、报告门禁与导出

完整的操作步骤见 [`docs/REAL_PILOT_GUIDE.md`](docs/REAL_PILOT_GUIDE.md)；不同模型的启动命令见 [API 指南](docs/API_GUIDE.md)。每个模型独立运行一批并导出，不混合不同模型的日志。

先使用真实 provider 运行完整冻结集。`--fresh` 会把旧日志、证明、复核表和报告移入可恢复的 `results/archive/`；默认同时清空持久缓存。若明确使用 `--reuse-cache`，报告只能作为带警告的草稿。

```powershell
python src/evaluate.py --provider openai_compatible --api-url "https://api.deepseek.com/chat/completions" --model deepseek-v4-pro --temperature 0 --max-tokens 12000 --api-key-prompt --conditions A,B,C --max-rounds 3 --timeout 60 --fresh
```

完成这一批的人工复核后，再校验、生成报告与导出；下面 PowerShell 命令会在失败时停止。导出目录必须尚不存在：

```powershell
python scripts/validate_pilot.py --runs results/real_pilot_runs.jsonl --require-manual-review
if ($LASTEXITCODE -ne 0) { throw "校验未通过，停止发布" }
python src/report.py
if ($LASTEXITCODE -ne 0) { throw "报告生成失败，停止导出" }
python scripts/export_pilot.py --out published/deepseek-v4-pro-12000-run01
```

`validate_pilot.py` 检查 54 个题目×条件组合、连续轮次、统一 provider 配置、候选安全策略、基础设施错误和缓存命中；`report.py` 在门禁不通过时拒绝生成 formal 报告；`export_pilot.py` 只导出通过复核的轨迹、报告和成功 `.lean` 文件，并清理本机路径与认证信息。

也可以使用本地 HTTP 接口：

```powershell
python src/api_server.py --host 127.0.0.1 --port 8765
```

向 `POST /solve` 发送 JSON，字段包括 `file`、`theorem`、`condition`、`api_url`、`api_key` 和 `model`。服务默认只监听本机，请勿直接暴露到公网。请求体不会写入服务日志。

安全输入密钥的完整 PowerShell 请求示例与 JSON 字段说明见 [API 指南](docs/API_GUIDE.md)。不要把密钥直接写进 `$body` 的命令文本，也不要打印请求体。

## 仓库结构

```text
src/leancapsule/       capsule 的打包、回放、验收和 issue 渲染
src/agent.py           编译反馈证明修复 Agent
src/api_server.py      本地 HTTP API
capsule_schema/        manifest 结构说明
capsules/               可公开回放的示例工件
examples/               检索示例与失败输入
lean_project/           Lean 测试项目
tests/                  Python 自动化测试
scripts/                环境准备与复现实用脚本
docs/                   方法、格式和贡献说明
PROGRESS.md             唯一的当前工作进度记录
CHANGELOG.md            面向 GitHub 的补丁与版本变更记录
```

## 设计边界

- capsule 核心不依赖模型或 API；Agent 只是可选消费者。
- 当前支持经过编译验证的 theorem standalone 和完整文件 fallback；多文件依赖切片和数学意义上的全局最小化尚未承诺。
- 诊断比较使用可读的规范化文本 `diagnostic_key`，并保留原始诊断供人工审计。
- API 密钥不进入 JSONL、SQLite、候选文件、manifest 或错误响应。
- Provider 返回的 Markdown 代码围栏会在解析边界和编译边界各清洗一次，兼容历史缓存。
- 仓库中的实验结果不能替代正式的模型对比实验；正式实验必须记录模型配置、token、延迟和人工复核。
- 安全、实验协议和发布审计相关改动记录在 [CHANGELOG.md](CHANGELOG.md)；当前状态和未完成事项记录在 [PROGRESS.md](PROGRESS.md)。

## 贡献

请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [docs/CAPSULE_FORMAT.md](docs/CAPSULE_FORMAT.md)，为每个公开 capsule 补充来源、许可、预期诊断和回放结果。

共同完成的修改请使用贡献指南中的 `Co-authored-by: Name <email>` 提交格式。PR 描述中的 `@mention` 仅是文字署名，不会替代 commit message 中的共同作者记录。
