# Contributing

1. Install Python 3.10+ and Lean/Lake matching `lean-toolchain`.
2. Run `python -m unittest discover -s tests -v` before submitting changes.
3. Run `lake build` for changes affecting Lean compilation.
4. Do not add standard-answer tables or deterministic answer routing to the evaluation path.
5. Keep provider credentials in environment variables; never commit secrets or pilot logs containing secrets.
6. Formal A/B/C claims require a real provider, the frozen 18-question manifest, JSONL logs, and completed manual review.
