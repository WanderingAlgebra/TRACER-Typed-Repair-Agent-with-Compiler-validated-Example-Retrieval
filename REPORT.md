# TRACER Pilot Report

- Experiment ID: `pilot-20260826T011418Z-06ffd827`
- Status: **FORMAL**
- Cache hits: `0`
- Provider configuration: `{"input_price_per_1k": 0.0, "max_response_bytes": 4194304, "max_tokens": 800, "model": "gpt-5.5", "output_price_per_1k": 0.0, "provider": "openai_compatible", "redirect_policy": "same_origin_only", "temperature": 0.0, "url": "https://yxai.chat/v1/chat/completions"}`
- Candidate policy: `{"environment": "minimal", "meta_execution": "blocked", "version": "tracer-candidate-v1"}`

## 汇总

| 条件 | 题数 | pass@1 | Wilson 95% CI | pass@3 | Wilson 95% CI | 平均轮次 | 平均编译毫秒 | 平均总 token | 估算成本 |
|---|---:|---:|---|---:|---|---:|---:|---:|---:|
| A | 18 | 17/18 (94.4%) | [74.2%, 99.0%] | 18/18 (100.0%) | [82.4%, 100.0%] | 1.06 | 2724.7 | 382.1 | unknown |
| B | 18 | 17/18 (94.4%) | [74.2%, 99.0%] | 18/18 (100.0%) | [82.4%, 100.0%] | 1.06 | 2375.5 | 321.8 | unknown |
| C | 18 | 18/18 (100.0%) | [82.4%, 100.0%] | 18/18 (100.0%) | [82.4%, 100.0%] | 1.00 | 2350.7 | 336.6 | unknown |

## 解释边界

- 18 道题是工作流 pilot，不构成通用自动定理证明能力或 SOTA 证据。
- C 条件的本地示例与部分评测题高度相似，泄漏风险必须逐题人工复核。
- 只有状态为 FORMAL、完整保留对应 JSONL 与 proof artifacts 的报告才能用于正式结论。
