# Agent instructions

- Use `jj` for version control.
- Edit locally; run executions and benchmarks on Modal—never locally.
- Prefer table/registry config (`GPU_TARGETS`) over growing if/elif dispatch.
- Prefer one shared typed profile contract over stringly `dict[str, Any]` metric keys.
- `modal_benchmark.py` is producer-only; it must not import the estimator.
- Canonical runs pin GPUs with `!` where needed (e.g. `H100!`); never publish `--quick` smoke output as canonical.
