# Methodology

## Task formulation

Each benchmark item specifies a Lean source file, a fully qualified theorem name, topical tags, and a proof obligation represented by a marked region or a unique placeholder. The agent is allowed to replace only that local proof region.

## Controlled conditions

- **A**: theorem statement and local source context only.
- **B**: A plus the bounded diagnostic from the preceding compilation attempt.
- **C**: B plus the top-k locally retrieved examples, recorded verbatim in the trace.

Provider, model, generation limits, compiler, timeout, task order, and repair budget are held constant across conditions. Only the prompt context changes.

## Verification protocol

1. Read the original source without modifying it.
2. Generate a local proof term through the configured provider.
3. Patch an isolated temporary copy and invoke the project-aware Lean/Lake compiler.
4. Normalize diagnostics into a bounded category and feedback string.
5. Retry at most three rounds, stopping immediately after a successful compile.
6. Save successful isolated sources, unsuccessful candidates, structured traces, and optional manual-review decisions.

## Validity constraints

The evaluation path must not contain a standard-answer table or deterministic answer routing. A formal claim requires a configured real provider, complete JSONL traces, token/cost metadata, and manual review of every accepted proof. The 18-item set is a workflow pilot rather than evidence of general automated theorem-proving ability.
