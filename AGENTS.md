# Agent instructions

- Use `jj` for version control.
- Edit locally; run GPU executions and benchmarks on Modal—never locally.
- Modal is GPU/test only. Never use Modal to build or deploy the website.
- Build the Astro site locally; deploy the website only with Cloudflare Wrangler.
- Prefer table/registry config (`GPU_TARGETS`) over growing if/elif dispatch.
- Prefer one shared typed profile contract over stringly `dict[str, Any]` metric keys.
- `modal_benchmark.py` is producer-only; it must not import the estimator.
- Canonical runs pin GPUs with `!` where needed (e.g. `H100!`); never publish `--quick` smoke output as canonical.
