# TRACER

**Typed Repair Agent with Compiler-validated Example Retrieval**

TRACER is a reproducible research prototype for repairing local Lean proof obligations with compiler feedback and retrieval-augmented prompts.

## Abstract

The system generates a local proof term for a selected theorem, validates it in an isolated Lean/Lake environment, classifies compiler diagnostics, and optionally retries with structured feedback. Three prompt conditions support a controlled workflow study: theorem-only input (A), theorem plus compiler feedback (B), and theorem plus feedback plus retrieved local examples (C). The repository does not contain a standard-answer generator; candidates come from a configured provider.

## Research status

- Frozen evaluation set: 18 Lean theorems.
- Maximum repair budget: three compilation rounds per task.
- Providers: OpenAI-compatible HTTP endpoint and user-defined command provider.
- Reproducibility: SQLite request cache, JSONL traces, token/cost fields, topic summaries, and manual-review ledger.
- Verification: every accepted candidate is checked by Lean and saved as an isolated source file.
- The formal provider pilot is not included in this snapshot; configure a real provider before collecting research evidence.

## Quick start

```powershell
python -m unittest discover -s tests -v
lake build
```

Single-theorem execution:

```powershell
python src/agent.py solve `
  --file input.lean `
  --theorem Demo.target `
  --condition B `
  --provider openai_compatible
```

The target file may use `PROOF_START`/`PROOF_END` markers or one unique `sorry` placeholder. The original file is never overwritten. Successful isolated proofs are written below `results/solutions/`.

## Provider configuration

For an OpenAI-compatible endpoint:

```powershell
$env:LEAN_PROOF_API_URL="https://example.invalid/v1/chat/completions"
$env:LEAN_PROOF_API_KEY="..."
$env:LEAN_PROOF_MODEL="..."
.\run_all.ps1 -Provider openai_compatible
```

Alternatively, configure a command that reads `{"prompt":"..."}` from stdin and returns `{"candidate":"by ...","usage":{...}}`:

```powershell
.\run_all.ps1 -Provider command -ProviderCommand "python my_provider.py"
```

Optional pricing variables are `LEAN_PROOF_INPUT_PRICE_PER_1K` and `LEAN_PROOF_OUTPUT_PRICE_PER_1K`.

## Repository layout

```text
src/              agent, compiler, provider, cache, evaluator, report
tests/            unit and end-to-end tests
benchmarks/       frozen task manifest
lean_project/     Lean benchmark project
examples/         local retrieval examples
prompts/          controlled prompt templates
results/          logs, solutions, and review ledger
docs/             method, schema, and project documentation
```

## Reproducibility and limitations

Run `python src/evaluate.py --provider openai_compatible --conditions A,B,C --fresh` and then `python src/report.py` after configuring a real provider. Reported differences between conditions must be inferred from the resulting per-task logs; the repository makes no causal or general theorem-proving claim. The frozen set is small and locally related examples may introduce similarity or leakage risk.

See [docs/project_overview.md](docs/project_overview.md), [docs/methodology.md](docs/methodology.md), [docs/jsonl_schema.md](docs/jsonl_schema.md), [REPORT.md](REPORT.md), and [CONTRIBUTING.md](CONTRIBUTING.md).
