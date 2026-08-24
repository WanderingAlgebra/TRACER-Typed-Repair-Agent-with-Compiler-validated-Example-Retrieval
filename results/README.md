# Results

正式评测结果写入 `real_pilot_runs.jsonl`，成功证明写入 `solutions/`，请求缓存写入 `requests.sqlite3`。`report.py` 还会生成 token 汇总和 `pilot_topic_summary.csv`。

旧的 `pilot_runs.jsonl`、`pilot_summary.csv`、`pilot_report.json` 和 SVG 只属于历史离线脚手架演示，不得用于研究结论；重新运行正式 provider 后，应使用 `real_pilot_runs.jsonl` 和新生成的报告。

`manual_review.csv` 是逐题逐条件的人工复核台账。正式 pilot 后，应为成功候选填写 `kernel_pass`、不恰当假设、泄漏风险和复核备注。
