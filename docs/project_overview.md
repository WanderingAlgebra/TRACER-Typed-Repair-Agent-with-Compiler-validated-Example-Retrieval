# Project overview

TRACER (Typed Repair Agent with Compiler-validated Example Retrieval) is an engineering and evaluation framework for local proof repair in Lean 4.

## Components

1. `src/agent.py` implements the provider-driven solve CLI and bounded feedback loop.
2. `src/compiler.py` isolates source patches and selects the surrounding Lake environment.
3. `src/provider.py` supports OpenAI-compatible and command-line providers.
4. `src/retriever.py` supplies the local-example context used by condition C.
5. `src/cache.py` persists exact request/candidate pairs in SQLite.
6. `src/evaluate.py` runs the frozen 18-task, three-condition pilot.
7. `src/report.py` computes pass rates, Wilson intervals, token/cost summaries, and topic analyses.

## Current verification

- 18 benchmark tasks and 18 Lean theorem declarations.
- 17 automated unit and end-to-end tests.
- Successful candidates are independently compilable isolated files.
- Original benchmark sources remain unchanged during repair.
- The repository contains no formal provider-pilot measurements; those must be generated after provider configuration.

## Reproducible execution

```powershell
python -m unittest discover -s tests -v
lake build
python src/evaluate.py --provider openai_compatible --conditions A,B,C --fresh
python src/report.py
```

The last two commands require a real provider and should be accompanied by the resulting JSONL traces and completed `results/manual_review.csv`.
