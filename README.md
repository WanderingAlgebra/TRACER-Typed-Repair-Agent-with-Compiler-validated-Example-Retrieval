# TRACER / LeanCapsule

TRACER 是一个由 Lean 编译器验证的证明修复与失败工件工具。LeanCapsule 是其中面向社区复现的核心协议：它把 Lean 文件、工具链、项目配置和规范化诊断打包成可回放的 capsule。

仓库同时保留两条互补路径：

- `leancapsule`：生成、回放、批量验收和渲染 Lean 失败工件；
- `src/agent.py`：使用编译反馈和本地示例进行局部证明修复。

## 快速开始

建议在已经安装 Lean、Lake 和 Python 的环境中运行：

```powershell
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
python -m leancapsule issue capsules/std/unknown-identifier --out issue.md
python -m leancapsule gallery capsules --out capsules/index.json
```

四个命令都输出机器可读 JSON；`replay` 和 `verify` 会用进程退出码表示是否通过。

使用 `--theorem` 时，工具会先尝试保留 imports、namespace 和目标定理的 standalone 文件；如果编译结果与原始诊断不一致，就自动退回完整文件。standalone 成功后会在固定编译预算内逐个尝试删除 imports，也可以使用 `--no-minimize-imports` 关闭。

## 公开失败 gallery

仓库当前包含 24 个可回放 capsule，覆盖四类失败：`Name / import`、`Type / application`、`Elaboration / instance` 和 `Goal / scope`，每类至少 3 个；来源覆盖 Std、Mathlib 和 project-local，每类来源至少 4 个。`capsules/index.json`、`capsules/index.csv` 和 `capsules/index.md` 是由 CLI 生成的三种 gallery 索引，`capsules/MANUAL_REVIEW.csv` 记录每个案例的自动回放状态与人工复核栏位。

Mathlib 案例使用独立的 `mathlib_project/` 依赖工程。首次回放前请执行：

```powershell
./scripts/setup_mathlib.ps1
```

Linux/macOS 可执行 `bash scripts/setup_mathlib.sh`。该步骤会按 `mathlib_project/lakefile.lean` 中的固定版本下载依赖和预编译缓存；依赖缓存不纳入仓库。没有网络或未准备缓存时，Std 与 project-local 案例仍可独立回放，Mathlib 案例会明确报告缺少依赖环境。

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

单次运行可以在命令行输入接口地址、模型，并通过安全提示输入密钥。密钥只存在于当前进程内，不写入日志和缓存：

```powershell
python src/agent.py solve `
  --file input.lean `
  --theorem Demo.target `
  --condition B `
  --provider openai_compatible `
  --api-url "https://example.invalid/v1/chat/completions" `
  --model "your-model" `
  --api-key-prompt
```

也可以使用本地 HTTP 接口：

```powershell
python src/api_server.py --host 127.0.0.1 --port 8765
```

向 `POST /solve` 发送 JSON，字段包括 `file`、`theorem`、`condition`、`api_url`、`api_key` 和 `model`。服务默认只监听本机，请勿直接暴露到公网。请求体不会写入服务日志。

PowerShell 请求示例：

```powershell
$body = @{
  file = "lean_project/Benchmarks/Evaluation18.lean"
  theorem = "Eval18.and_swap_eval"
  condition = "B"
  api_url = "https://example.invalid/v1/chat/completions"
  api_key = "在本地粘贴密钥"
  model = "your-model"
  max_rounds = 3
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8765/solve -ContentType "application/json" -Body $body
```

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
```

## 设计边界

- capsule 核心不依赖模型或 API；Agent 只是可选消费者。
- 当前支持经过编译验证的 theorem standalone 和完整文件 fallback；多文件依赖切片和数学意义上的全局最小化尚未承诺。
- 诊断比较使用可读的规范化文本 `diagnostic_key`，并保留原始诊断供人工审计。
- API 密钥不进入 JSONL、SQLite、候选文件、manifest 或错误响应。
- 仓库中的实验结果不能替代正式的模型对比实验；正式实验必须记录模型配置、token、延迟和人工复核。

## 贡献

请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [docs/CAPSULE_FORMAT.md](docs/CAPSULE_FORMAT.md)，为每个公开 capsule 补充来源、许可、预期诊断和回放结果。
