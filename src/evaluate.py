"""使用真实配置的 provider 运行 18 题 A/B/C 试验。"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import uuid
from pathlib import Path

from agent import append_jsonl, solve_problem
from provider import build_provider


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_PATH = ROOT / "benchmarks" / "manifest.json"
PILOT_PATH = ROOT / "results" / "real_pilot_runs.jsonl"
REVIEW_PATH = ROOT / "results" / "manual_review.csv"
CACHE_PATH = ROOT / "results" / "requests.sqlite3"


def load_benchmarks() -> list[dict]:
    problems = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    for problem in problems:
        problem.setdefault("proof_region", {"start": "-- PROOF_START", "end": "-- PROOF_END"})
    return problems


def write_manual_review(conditions: list[str], experiment_id: str) -> None:
    """为每个冻结题目和条件组合建立复核台账。"""
    REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[tuple[str, str], dict[str, str]] = {}
    if REVIEW_PATH.exists():
        with REVIEW_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("experiment_id") == experiment_id:
                    existing[(row.get("problem_id", ""), row.get("condition", ""))] = row
    fields = [
        "experiment_id",
        "problem_id",
        "condition",
        "kernel_pass",
        "inappropriate_assumption",
        "leakage_risk",
        "reviewer_note",
    ]
    with REVIEW_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for problem in load_benchmarks():
            for condition in conditions:
                key = (problem["id"], condition)
                row = existing.get(key, {})
                writer.writerow(
                    {
                        "experiment_id": experiment_id,
                        "problem_id": problem["id"],
                        "condition": condition,
                        "kernel_pass": row.get("kernel_pass", ""),
                        "inappropriate_assumption": row.get("inappropriate_assumption", ""),
                        "leakage_risk": row.get("leakage_risk", ""),
                        "reviewer_note": row.get("reviewer_note", ""),
                    }
                )


def _clear_request_cache() -> None:
    for path in (CACHE_PATH, CACHE_PATH.with_name(CACHE_PATH.name + "-wal"), CACHE_PATH.with_name(CACHE_PATH.name + "-shm")):
        if path.exists():
            path.unlink()


def run_pilot(conditions: list[str], provider, max_rounds: int, timeout: float, fresh: bool, experiment_id: str | None = None) -> str:
    experiment_id = experiment_id or str(uuid.uuid4())
    if fresh:
        if PILOT_PATH.exists():
            PILOT_PATH.unlink()
        _clear_request_cache()
    write_manual_review(conditions, experiment_id)
    print(f"experiment_id={experiment_id}")
    for condition in conditions:
        for problem in load_benchmarks():
            try:
                result = solve_problem(
                    ROOT / problem["file"],
                    problem["theorem"],
                    condition,
                    provider,
                    max_rounds,
                    timeout,
                    ROOT / "examples",
                    CACHE_PATH,
                    ROOT / "results" / "solutions" / experiment_id,
                    PILOT_PATH,
                    problem["proof_region"]["start"],
                    problem["proof_region"]["end"],
                    "sorry",
                    problem["id"],
                    problem.get("tags", []),
                    problem.get("difficulty"),
                    experiment_id,
                )
                print(f"{condition}: {problem['id']} -> {'PASS' if result['compile_ok'] else 'FAIL'} ({result['round']} round(s))")
            except Exception as exc:
                config = provider.metadata() if hasattr(provider, "metadata") else {"provider": provider.name}
                append_jsonl(
                    PILOT_PATH,
                    {
                        "run_id": f"task-error-{condition}-{problem['id']}",
                        "experiment_id": experiment_id,
                        "problem_id": problem["id"],
                        "benchmark_id": problem["id"],
                        "tags": problem.get("tags", []),
                        "difficulty": problem.get("difficulty"),
                        "source_file": problem["file"],
                        "theorem": problem["theorem"],
                        "condition": condition,
                        "round": 0,
                        "candidate": "",
                        "provider": config.get("provider"),
                        "provider_config": config,
                        "provider_error": None,
                        "usage": {},
                        "estimated_cost_usd": None,
                        "cache_hit": False,
                        "retrieved_examples": [],
                        "prompt_chars": 0,
                        "compile_ok": False,
                        "compile_elapsed_ms": 0.0,
                        "diagnostic": {"category": "task_error", "summary": str(exc)[:700], "feedback": "任务执行异常，已记录并继续后续题目。", "errors": [], "truncated": len(str(exc)) > 700},
                        "raw_diagnostics": str(exc)[:4000],
                        "compiler_command": None,
                        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    },
                )
                print(f"{condition}: {problem['id']} -> TASK_ERROR")
    return experiment_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Run real Lean proof-repair pilot")
    parser.add_argument("--provider", choices=["command", "openai_compatible"], required=True)
    parser.add_argument("--provider-command")
    parser.add_argument("--conditions", default="A,B,C")
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--experiment-id", help="为整批 A/B/C 运行指定稳定标识；默认自动生成")
    args = parser.parse_args()
    conditions = [item.strip().upper() for item in args.conditions.split(",") if item.strip()]
    if any(item not in {"A", "B", "C"} for item in conditions):
        raise SystemExit("--conditions 只能包含 A、B、C")
    if not 1 <= args.max_rounds <= 3:
        raise SystemExit("--max-rounds 必须在 1 到 3 之间")
    provider = build_provider(args.provider, args.provider_command)
    run_pilot(conditions, provider, args.max_rounds, args.timeout, args.fresh, args.experiment_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
