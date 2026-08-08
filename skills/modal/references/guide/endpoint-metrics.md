# Endpoint metrics

Every endpoint reports live inference metrics so you can see how it's performing
under real traffic — latency, throughput, and how many requests are in flight.
Open an endpoint from the **Endpoints** tab and go to the **Activity** view to
see them.

There are two types of metrics available:

* **Inference metrics** — LLM engine-specific metrics designed to give you more
  performance observability.
* **Server metrics** — the standard Modal container health metrics.

## What the metrics mean

**Latency** (reported as p50 / p95 / p99):

* **Time to first token (TTFT)** — how long after a request arrives before the
  first output token streams back. The number users feel first.
* **Inter-token latency (ITL)** — average gap between successive output tokens.
  Drives perceived "typing speed."
* **End-to-end latency (E2E)** — total time to complete a request.

**Throughput:**

* **Requests per second (QPS)** — request arrival rate.
* **Token throughput** — tokens/second, split into prefill (processing the
  prompt, with a separate line for cache-hit tokens) and decode (generating
  output).

**Request load:**

* **Request activity** — the rate of requests arriving at and completing on the
  endpoint over time.
* **Running** — requests currently being processed.
* **Queued** — requests waiting for a free slot. Sustained queueing means the
  fleet is saturated and scaling up.

**Speculative decoding** (only for recipes that use it) — the average number of
draft tokens accepted per step; higher means speculation is paying off.

## Caveats

* **Metrics need traffic.** Latency and throughput are computed over recent
  rolling windows; an idle or scaled-to-zero endpoint shows no current data.
* **Cold starts skew early numbers.** The first requests after a scale-up
  include model load time. Look at steady-state windows when evaluating
  performance.
* **Percentiles need volume.** p95/p99 are only meaningful once enough requests
  have accumulated in the window.
* Endpoint metrics are available in the dashboard. To get repeatable performance
  numbers under a controlled load, [run a
  benchmark](/docs/guide/endpoint-benchmarks).
