# Trace schema

Each repair attempt appends one JSON object to the configured trace file. The schema is designed for per-task, per-condition, per-round analysis and keeps the generated candidate alongside the compiler outcome.

| Field | Type | Meaning |
| --- | --- | --- |
| `run_id` | string | Identifier for one solve invocation |
| `benchmark_id` | string or null | Frozen-manifest task identifier |
| `problem_id` | string | Stable task key used by the agent |
| `theorem` | string | Fully qualified Lean theorem name |
| `condition` | string | `A`, `B`, or `C` prompt condition |
| `round` | integer | Repair round, from 1 through the configured limit |
| `candidate` | string | Local Lean proof term returned by the provider |
| `provider` | string | Provider name |
| `provider_config` | object | Non-secret model and generation settings |
| `usage` | object | Provider-reported input, output, and total token counts |
| `estimated_cost_usd` | number or null | Optional cost estimate from configured rates |
| `cache_hit` | boolean | Whether the exact request was served from SQLite |
| `retrieved_examples` | array | Examples included in condition C |
| `compile_ok` | boolean | Whether Lean accepted the isolated source |
| `compile_elapsed_ms` | number | Compiler wall-clock duration |
| `diagnostic` | object | Structured category, summary, and bounded feedback |
| `compiler_command` | array or null | Actual Lean/Lake command used |
| `timestamp_utc` | string | UTC event time |

The original source file is never overwritten. Accepted isolated sources are saved under `results/solutions/`; unsuccessful candidates are saved under `results/failures/`.
