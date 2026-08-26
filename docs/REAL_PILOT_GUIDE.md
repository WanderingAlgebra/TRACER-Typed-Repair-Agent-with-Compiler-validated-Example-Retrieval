# 真实 54 题 Provider Pilot 操作说明

本说明用于运行冻结的 18 道 Lean 题目在 A、B、C 三种条件下的真实 provider 实验。总任务数为 `18 × 3 = 54`。实验不会修改原始题库；每轮候选、编译诊断、token 用量和成功证明都会落盘。

## 1. 准备环境

在 PowerShell 中进入仓库根目录：

```powershell
cd "C:\Users\王润祺\Desktop\LeanProofRepairAgent-整理版\TRACER"
python -m pip install -r requirements.txt
$env:ELAN_HOME = Join-Path $env:USERPROFILE ".elan"
lake build
```

如果 `python` 不在 PATH，可把下面所有 `python` 替换成已经安装依赖的 Python 解释器完整路径。

## 2. 设置 provider 配置

当前实现使用 OpenAI 兼容的 Chat Completions 接口。以 DeepSeek 为例，地址和模型名必须按账户实际可用配置填写：

```powershell
$env:LEAN_PROOF_API_URL = "https://api.deepseek.com/chat/completions"
$env:LEAN_PROOF_MODEL = "deepseek-v4-pro"
$env:LEAN_PROOF_TEMPERATURE = "0"
$env:LEAN_PROOF_MAX_TOKENS = "8000"
```

不要把密钥写入 README、脚本、Git 历史或 JSONL。单次正式运行推荐使用 `--api-key-prompt`，这样无需把密钥放进 PowerShell 命令历史：

```powershell
$secure = Read-Host "API key（输入时不会回显）" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
  $env:LEAN_PROOF_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}
```

可选地记录价格，未设置时报告会显示“未配置”，不会当作零成本：

```powershell
$env:LEAN_PROOF_INPUT_PRICE_PER_1K = "0"
$env:LEAN_PROOF_OUTPUT_PRICE_PER_1K = "0"
```

## 3. 运行完整真实实验

`--fresh` 会先把旧日志、证明、复核台账、报告和缓存移动到 `results/archive/`，然后开始新的实验批次。旧数据可恢复，不会被覆盖。

```powershell
python src/evaluate.py `
  --provider openai_compatible `
  --api-url "https://api.deepseek.com/chat/completions" `
  --model "deepseek-v4-pro" `
  --temperature 0 `
  --max-tokens 8000 `
  --api-key-prompt `
  --conditions A,B,C `
  --max-rounds 3 `
  --timeout 60 `
  --fresh
```

带较长推理过程的模型建议至少使用 `8000`。如果日志中 `completion_tokens` 多次达到上限且候选为空，应提高上限并用 `--fresh` 重跑整批。

运行过程结束后应看到一个新的 `experiment_id`。如果出现 `provider_error`、大量 `task_error` 或中途断网，不要把这批结果当作正式实验；修复配置后重新使用 `--fresh` 完整运行。

## 4. 检查原始轨迹和成功证明

```powershell
Get-Content results\real_pilot_runs.jsonl -Tail 1
Get-ChildItem results\solutions -Recurse -Filter *.lean
```

文件含义：

- `results/real_pilot_runs.jsonl`：逐题逐轮原始轨迹，最多 162 条记录；
- `results/solutions/A|B|C/`：通过 Lean 编译的最终隔离证明；
- `results/solutions/failures/`：未成功题目的最后候选；
- `results/manual_review.csv`：54 个题目×条件组合的复核台账。

## 5. 完成人工复核

打开 `results/manual_review.csv`。对每个成功候选至少填写：

- `kernel_pass`：确认独立 Lean 编译通过，填写 `yes`；
- `inappropriate_assumption`：没有不恰当额外假设时填写 `no`；
- `leakage_risk`：没有使用原题答案或不当示例时填写 `no`；
- `reviewer_note`：写一句可追溯备注，例如“独立复编译；仅使用题目上下文”。

失败题目也保留台账行；是否填写其复核字段由研究者决定，但成功题目的字段不能为空。

## 6. 严格校验、生成报告

```powershell
python scripts/validate_pilot.py `
  --runs results/real_pilot_runs.jsonl `
  --manifest benchmarks/manifest.json `
  --review results/manual_review.csv `
  --require-manual-review

python src/report.py
```

校验会拒绝：缺少 54 个组合、轮次不连续、成功后仍继续尝试、provider 配置不一致、基础设施错误、缓存命中或候选安全策略不一致。`report.py` 只有在门禁通过后才会生成 `formal` 报告；否则应先修正问题，不要使用 `--allow-*` 选项冒充正式结果。

报告文件包括：

- `results/pilot_report.json`；
- `results/pilot_summary.csv`；
- `results/pilot_failure_types.csv`；
- `results/pilot_topic_summary.csv`；
- `results/pass_at_1.svg` 和 `results/pass_at_3.svg`；
- 根目录 `REPORT.md`。

## 7. 导出可交付实验包

只有严格校验和人工复核通过后才执行：

```powershell
python scripts/export_pilot.py --out ..\TRACER-pilot-handoff
```

导出包包含脱敏后的逐轮 JSONL、54 个组合的复核表、正式报告和成功 `.lean` 文件。导出前会拒绝疑似认证信息，并把本机绝对路径替换为占位路径。输出目录必须不存在，以防止误覆盖旧交付物。

## 8. 最终验收

```powershell
python scripts/validate_pilot.py --require-manual-review
python src/report.py
python scripts/export_pilot.py --out ..\TRACER-pilot-handoff
python -m leancapsule audit capsules
lake build
```

最终交付前确认：`pilot_report.json` 的 `status` 为 `formal`，`cache_hits` 为 `0`，`experiment_id` 全程一致，并且导出包中存在每个成功记录对应的 `.lean` 文件。
