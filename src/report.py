"""生成评测表、Wilson 区间、图表和试验报告。"""

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PILOT = RESULTS / "real_pilot_runs.jsonl"
REVIEW = RESULTS / "manual_review.csv"


def usage_value(usage: object, *names: str) -> int:
    if not isinstance(usage, dict):
        return 0
    for name in names:
        value = usage.get(name)
        if isinstance(value, (int, float)):
            return int(value)
    return 0


def wilson(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)


def load_frame(experiment_id: str | None = None) -> pd.DataFrame:
    if not PILOT.exists():
        raise SystemExit("找不到 real_pilot_runs.jsonl：请先使用真实 provider 运行 evaluate.py")
    rows = [json.loads(line) for line in PILOT.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise SystemExit("real_pilot_runs.jsonl 为空：请先完成至少一个 provider 任务")
    frame = pd.DataFrame(rows)
    if "experiment_id" not in frame.columns:
        if experiment_id:
            raise SystemExit("旧轨迹不含 experiment_id，不能按实验批次选择；请重新运行正式 pilot")
        return frame
    identifiers = [str(value) for value in frame["experiment_id"].dropna().unique() if str(value)]
    if experiment_id is None:
        if len(identifiers) != 1:
            raise SystemExit("轨迹包含多个实验批次，请使用 --experiment-id 明确选择，禁止自动合并")
        experiment_id = identifiers[0]
    selected = frame[frame["experiment_id"] == experiment_id].copy()
    if selected.empty:
        raise SystemExit(f"找不到 experiment_id={experiment_id} 的轨迹")
    return selected


def manual_review_complete(experiment_id: str | None, expected_pairs: set[tuple[str, str]] | None = None) -> bool:
    """只有同一实验的全部题目×条件复核字段非空时才标记为可发布。"""

    if not experiment_id or not REVIEW.exists():
        return False
    required = {"kernel_pass", "inappropriate_assumption", "leakage_risk", "reviewer_note"}
    frame = pd.read_csv(REVIEW, dtype=str, encoding="utf-8-sig").fillna("")
    if not required.issubset(frame.columns) or "experiment_id" not in frame.columns:
        return False
    matching = frame[frame.get("experiment_id", "") == experiment_id]
    if matching.empty:
        return False
    if expected_pairs is not None:
        actual_pairs = set(zip(matching["condition"], matching["problem_id"]))
        if actual_pairs != expected_pairs or len(matching) != len(expected_pairs):
            return False
    return all(bool(str(value).strip()) for field in required for value in matching[field].tolist())


def summarize(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    if "run_id" in frame.columns:
        counts = frame.groupby(["condition", "problem_id"])["run_id"].nunique()
        if bool((counts > 1).any()):
            raise ValueError("同一条件和题目包含多个 run_id；请先按 experiment_id 选择单一实验批次")
    records: list[dict] = []
    final_failures: list[dict] = []
    for (condition, problem_id), group in frame.groupby(["condition", "problem_id"], sort=True):
        group = group.sort_values("round")
        first_pass = bool(group.iloc[0]["compile_ok"])
        pass3 = bool(group["compile_ok"].any())
        successful = group[group["compile_ok"]]
        rounds = int(successful.iloc[0]["round"]) if not successful.empty else int(group["round"].max())
        if not pass3:
            last = group.iloc[-1]
            final_failures.append(
                {
                    "condition": condition,
                    "problem_id": problem_id,
                    "category": last["diagnostic"]["category"],
                    "tags": last.get("tags", []),
                }
            )
        prompt_tokens = sum(usage_value(item, "prompt_tokens", "input_tokens") for item in group["usage"])
        completion_tokens = sum(usage_value(item, "completion_tokens", "output_tokens") for item in group["usage"])
        total_tokens = sum(usage_value(item, "total_tokens") for item in group["usage"])
        if total_tokens == 0:
            total_tokens = prompt_tokens + completion_tokens
        cost_values = [
            float(item) for item in group.get("estimated_cost_usd", [])
            if isinstance(item, (int, float)) and not pd.isna(item)
        ]
        total_cost = sum(cost_values) if cost_values else None
        records.append(
            {
                "condition": condition,
                "problem_id": problem_id,
                "pass_at_1": int(first_pass),
                "pass_at_3": int(pass3),
                "rounds": rounds,
                "compile_ms": round(float(group["compile_elapsed_ms"].mean()), 1),
                "retrieval_count": int(max(len(item) for item in group["retrieved_examples"])),
                "tags": list(group.iloc[0].get("tags", [])),
                "difficulty": group.iloc[0].get("difficulty"),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost_usd": total_cost,
            }
        )

    task_frame = pd.DataFrame(records)
    summary_rows: list[dict] = []
    for condition, group in task_frame.groupby("condition", sort=True):
        total = len(group)
        p1 = int(group["pass_at_1"].sum())
        p3 = int(group["pass_at_3"].sum())
        p1_lo, p1_hi = wilson(p1, total)
        p3_lo, p3_hi = wilson(p3, total)
        known_costs = [float(value) for value in group["cost_usd"] if isinstance(value, (int, float)) and not pd.isna(value)]
        summary_rows.append(
            {
                "condition": condition,
                "tasks": total,
                "pass_at_1": p1,
                "pass_at_1_rate": round(p1 / total, 4),
                "pass_at_1_wilson_low": round(p1_lo, 4),
                "pass_at_1_wilson_high": round(p1_hi, 4),
                "pass_at_3": p3,
                "pass_at_3_rate": round(p3 / total, 4),
                "pass_at_3_wilson_low": round(p3_lo, 4),
                "pass_at_3_wilson_high": round(p3_hi, 4),
                "avg_rounds": round(float(group["rounds"].mean()), 3),
                "avg_compile_ms": round(float(group["compile_ms"].mean()), 1),
                "avg_prompt_tokens": round(float(group["prompt_tokens"].mean()), 1),
                "avg_completion_tokens": round(float(group["completion_tokens"].mean()), 1),
                "avg_total_tokens": round(float(group["total_tokens"].mean()), 1),
                "avg_cost_usd": round(sum(known_costs) / len(known_costs), 8) if known_costs else None,
            }
        )
    summary = pd.DataFrame(summary_rows)
    failures = pd.DataFrame(final_failures)
    topic_rows: list[dict] = []
    for row in records:
        for tag in row.get("tags", []):
            topic_rows.append(
                {
                    "condition": row["condition"],
                    "tag": tag,
                    "tasks": 1,
                    "pass_at_1": row["pass_at_1"],
                    "pass_at_3": row["pass_at_3"],
                }
            )
    topic_frame = pd.DataFrame(topic_rows)
    if not topic_frame.empty:
        topic_summary = (
            topic_frame.groupby(["condition", "tag"], as_index=False)
            .agg(tasks=("tasks", "sum"), pass_at_1=("pass_at_1", "sum"), pass_at_3=("pass_at_3", "sum"))
        )
        topic_summary["pass_at_1_rate"] = (topic_summary["pass_at_1"] / topic_summary["tasks"]).round(4)
        topic_summary["pass_at_3_rate"] = (topic_summary["pass_at_3"] / topic_summary["tasks"]).round(4)
    else:
        topic_summary = pd.DataFrame(columns=["condition", "tag", "tasks", "pass_at_1", "pass_at_3", "pass_at_1_rate", "pass_at_3_rate"])
    failure_counts = {
        f"{key[0]}::{key[1]}": int(value)
        for key, value in (failures.value_counts(["condition", "category"]).items() if not failures.empty else [])
    }
    experiment_id = str(frame.iloc[0].get("experiment_id")) if "experiment_id" in frame.columns else None
    expected_review_pairs = set(zip(frame["condition"], frame["problem_id"]))
    report = {
        "pilot": "TRACER provider pilot",
        "experiment_id": experiment_id,
        "manual_review_complete": manual_review_complete(experiment_id, expected_review_pairs),
        "tasks": int(task_frame["problem_id"].nunique()),
        "conditions": summary.to_dict(orient="records"),
        "failure_types": failure_counts,
        "by_tag": topic_summary.to_dict(orient="records"),
        "limitations": [
            "题目数量小，区间只应作为 pilot evidence。",
            "题目与本地示例存在结构相似性，不能据此排除训练泄漏。",
            "模型随机性受 provider 配置和服务端 seed 支持影响。",
        ],
    }
    return summary, failures, report


def bar_svg(summary: pd.DataFrame, field: str, title: str, path: Path) -> None:
    width, height = 760, 420
    margin_left, margin_bottom = 70, 70
    values = [float(v) for v in summary[field]]
    max_value = max(1.0, max(values) * 1.15)
    bar_width = 120
    gap = 70
    elements = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">']
    elements.append(f'<rect width="100%" height="100%" fill="white"/><text x="{width/2}" y="32" text-anchor="middle" font-size="20">{html.escape(title)}</text>')
    base_y = height - margin_bottom
    elements.append(f'<line x1="{margin_left}" y1="{base_y}" x2="{width-30}" y2="{base_y}" stroke="#444"/>')
    for idx, (_, row) in enumerate(summary.iterrows()):
        x = margin_left + 55 + idx * (bar_width + gap)
        value = float(row[field])
        bar_h = (height - margin_bottom - 80) * value / max_value
        y = base_y - bar_h
        elements.append(f'<rect x="{x}" y="{y:.1f}" width="{bar_width}" height="{bar_h:.1f}" fill="#4f81bd"/>')
        elements.append(f'<text x="{x+bar_width/2}" y="{y-8:.1f}" text-anchor="middle" font-size="14">{value:.3f}</text>')
        elements.append(f'<text x="{x+bar_width/2}" y="{base_y+24}" text-anchor="middle" font-size="14">{html.escape(str(row["condition"]))}</text>')
    elements.append(f'<text x="18" y="{height/2}" transform="rotate(-90 18 {height/2})" text-anchor="middle" font-size="14">rate</text></svg>')
    path.write_text("".join(elements), encoding="utf-8")


def write_report(summary: pd.DataFrame, failures: pd.DataFrame, report: dict) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    summary.to_csv(RESULTS / "pilot_summary.csv", index=False, encoding="utf-8-sig")
    failures.to_csv(RESULTS / "pilot_failure_types.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(report.get("by_tag", [])).to_csv(RESULTS / "pilot_topic_summary.csv", index=False, encoding="utf-8-sig")
    (RESULTS / "pilot_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    bar_svg(summary, "pass_at_1_rate", "TRACER pass@1", RESULTS / "pass_at_1.svg")
    bar_svg(summary, "pass_at_3_rate", "TRACER pass@3", RESULTS / "pass_at_3.svg")
    lines = [
        "# TRACER Pilot Report",
        "",
        "这是 provider workflow pilot。A 只使用题目，B 增加编译反馈，C 再增加 Top-k 本地示例。结果用于验证流程，不作通用自动定理证明能力或 SOTA 宣称。",
        "",
        "## 汇总",
        "",
        "| 条件 | 题数 | pass@1 | Wilson 95% CI | pass@3 | Wilson 95% CI | 平均轮次 | 平均编译毫秒 | 平均总 token | 估算成本 |",
        "|---|---:|---:|---|---:|---|---:|---:|---:|---:|",
    ]
    for row in summary.to_dict(orient="records"):
        cost = row.get("avg_cost_usd")
        cost_text = f"${cost:.8f}" if isinstance(cost, (int, float)) and not pd.isna(cost) else "未配置"
        lines.append(
            f"| {row['condition']} | {row['tasks']} | {row['pass_at_1']}/{row['tasks']} ({row['pass_at_1_rate']:.1%}) | [{row['pass_at_1_wilson_low']:.1%}, {row['pass_at_1_wilson_high']:.1%}] | {row['pass_at_3']}/{row['tasks']} ({row['pass_at_3_rate']:.1%}) | [{row['pass_at_3_wilson_low']:.1%}, {row['pass_at_3_wilson_high']:.1%}] | {row['avg_rounds']:.2f} | {row['avg_compile_ms']:.1f} | {row['avg_total_tokens']:.1f} | {cost_text} |"
        )
    lines += [
        "",
        "## 主要观察",
        "",
        "- A 是题目-only 基线；B 和 C 分别加入编译诊断、编译诊断加本地示例。是否产生增益必须由本次 pilot 的逐题结果决定。",
        "- 每条成功证明都由 Lean 编译器检查；失败记录保留题目、候选、轮次和结构化诊断。",
        "- 18 道题为小样本冻结集，Wilson 区间用于表达不确定性，不用于强显著性结论。",
        "- 人工复核台账未完整填写时，报告只能作为内部流程产物，不能作为正式发布结论。",
        "",
        "## 局限与复现",
        "",
        "- 使用何种 provider、模型、温度和最大输出长度必须在运行记录和环境配置中明确。",
        "- 本地示例与评测题有意保持窄领域相似，存在数据泄漏风险；该结果只能称为 workflow pilot。",
        "- 新环境可运行 `python src/evaluate.py --provider openai_compatible --conditions A,B,C --fresh`，随后运行 `python src/report.py`。",
    ]
    (ROOT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="生成单一 TRACER 实验批次报告")
    parser.add_argument("--experiment-id", help="当轨迹包含多个批次时必须明确指定")
    args = parser.parse_args()
    summary, failures, report = summarize(load_frame(args.experiment_id))
    write_report(summary, failures, report)
    print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
