# Benchmark an endpoint

Live metrics tell you how an endpoint behaves under whatever traffic it happens
to be getting. A **benchmark** tells you how it behaves under a known,
repeatable load — so you can compare models, regions, and configurations on an
apples-to-apples basis.

Modal runs benchmarks for you: it drives a standard load generator against your
live endpoint from a sandbox and reports the results. Start one from the
**Benchmark** tab on the endpoint's detail page. The resulting metrics are
available in the dashboard once completed.

## Workload patterns

A benchmark runs one of two built-in patterns, each shaped like a different
real-world workload:

| Pattern                  | Prompt shape                                                                    | Models                                               |
| ------------------------ | ------------------------------------------------------------------------------- | ---------------------------------------------------- |
| **Real-time generation** | ~3,000 input tokens → ~100 output tokens, randomized prompts                    | Interactive chat / short-answer Q\&A                  |
| **Agentic multi-turn**   | ~45,000-token shared system prefix + ~5,000-token question → ~200 output tokens | Agent / tool-use workloads with long, reused context |

The agentic pattern reuses a long shared prefix across requests, so it also
exercises prefix caching — a major factor in agent workload performance.

## Endpoint preview benchmarks

When you pick a model while creating an endpoint, you'll also see **precomputed
benchmarks** attached to the model's recipe. These are reference numbers Modal
measured on a known GPU configuration, so you can compare candidate models
before deploying anything. They differ from the benchmarks above in two ways:
they're produced ahead of time by Modal (not run against your endpoint), and
they're tied to the recipe rather than your specific deployment. Use recipe
benchmarks to choose a model; run your own benchmark to validate an endpoint in
your region with your settings.

## Caveats

* **Benchmarks send real traffic.** A run drives your live endpoint, triggers
  autoscaling, and incurs the usual compute cost while it runs.
* **Results are point-in-time.** Numbers depend on the current fleet size,
  region, and any cold starts during the run. Compare runs taken under similar
  conditions, and let the endpoint warm up first for steady-state figures.
* **Pick the pattern that matches your use case.** Real-time and agentic
  workloads stress very different parts of the serving stack; benchmarking the
  wrong shape can be misleading.
