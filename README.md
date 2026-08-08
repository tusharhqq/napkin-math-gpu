# GPU Napkin Math

Use a handful of measured ceilings to decide whether a GPU workload is limited
by compute, memory, transfers, communication, launch overhead, or capacity. The
equations on this page apply to every GPU; the numbers do not.

## Pick a GPU profile

| Profile | Architecture | Modal request | Status |
| --- | --- | --- | --- |
| [H100](H100.md) | Hopper | `H100!` | Calibrated on Modal |
| [B200](B200.md) | Blackwell | `B200` | Vendor-ceiling planning profile |
| [B300](B300.md) | Blackwell Ultra | `B300` | Vendor-ceiling planning profile |

Modal also offers `H200`. It is a Hopper GPU with more and faster memory than
H100, not the predecessor of B300. There is no `H300` request on Modal. For
benchmarking H100 specifically, use `H100!`: an unpinned `H100` request may be
upgraded to H200. `B200+` similarly opts into either B200 or B300.

## The metrics that matter on any GPU

| Metric | Symbol | Why it matters |
| --- | ---: | --- |
| Usable device-memory capacity | `C` | Whether the workload fits at all |
| Achievable compute throughput at the actual dtype | `F` | Compute-time floor |
| Achievable HBM bandwidth | `M` | Device-memory-time floor |
| Host-to-device and device-to-host bandwidth | `P_h2d`, `P_d2h` | Input and output transfer floors |
| GPU-to-GPU bandwidth | `P_g2g` | Tensor/pipeline parallel communication floor |
| Kernel-launch latency | `L` | Cost of many small kernels |

Keep the qualifiers attached to every number: exact SKU and form factor,
precision, dense versus sparse, theoretical versus achieved, direction,
topology, and software stack. No throughput number is universal across dtypes,
layouts, shapes, kernels, or systems.

## The reusable arithmetic

For a workload with `W` FLOPs and `Q` bytes of HBM traffic:

```text
arithmetic intensity = W / Q                         FLOP/byte
ridge point          = F / M                         FLOP/byte
compute time         = W / F
memory time          = Q / M
device time          = max(compute time, memory time)
```

The unit shortcut is:

```text
ridge point = compute TFLOP/s × 1,000 / memory GB/s
```

If arithmetic intensity is below the ridge point, the roofline model predicts
a memory-bound kernel. If it is above the ridge point, it predicts a
compute-bound kernel.

Add data movement and launch overhead when they are on the critical path:

```text
host copy time   = host bytes / host bandwidth
H2D time         = H2D bytes / P_h2d
D2H time         = D2H bytes / P_d2h
GPU-to-GPU time  = communicated bytes / P_g2g
launch time      = kernel launches × L

serial estimate  = host copy + H2D + device + GPU-to-GPU + D2H + launch
```

The serial sum is conservative. When stages genuinely overlap, model the
overlapped section with `max(...)`, not a sum. Count algorithmic traffic, not
just allocation size: a copy reads and writes two buffer-sized byte streams,
while `C = A + B` reads two and writes one.

## Capacity is a separate constraint

Speed does not matter when the working set does not fit:

```text
working set = weights + activations + KV cache + temporary workspace
fits        = working set <= usable device memory
```

For replicated weights, a quick lower bound is:

```text
weight bytes = parameter count × bits per parameter / 8
```

Leave headroom for runtime state, allocator fragmentation, communication
buffers, and workspaces. Multi-GPU capacity scales only when the software
actually shards the relevant tensors.

## Estimation discipline

1. Choose the exact GPU and precision.
2. Measure or obtain ceilings with matching dense/sparse conventions.
3. Count FLOPs and bytes for the workload.
4. Compute the roofline lower bound.
5. Add transfers, communication, launches, and non-overlapped CPU work.
6. Report one or two significant digits and name the predicted bottleneck.
7. Check the estimate against a representative end-to-end run.

A napkin estimate is a lower-bound model, not a latency promise. Cache effects,
occupancy, synchronization, collectives, framework overhead, power limits, and
contention can make real execution slower.

## Calculator

The CLI implements the same arithmetic using a measured JSON profile. It
currently defaults to the checked-in H100 calibration:

```sh
python3 gpu_napkin.py \
  --dtype bf16 \
  --flops 2e14 \
  --bytes 1e12 \
  --h2d-bytes 2e9 \
  --launches 20
```

It can also include `--cpu-bytes`, `--d2h-bytes`, and
`--gpu-to-gpu-bytes`. Extra printed digits do not make the estimate more
certain.

## Website

The interactive estimator is an Astro static site deployed with Cloudflare
Workers Static Assets. Website builds run locally; Modal remains reserved for
GPU benchmarks and tests.

```sh
npm install
npm run dev
npm run build
npm run deploy
```

PostHog Product Analytics, Session Replay, and Web Analytics are initialized
when `PUBLIC_POSTHOG_KEY` and `PUBLIC_POSTHOG_HOST` are present at build time.
Copy `.env.example` to `.env` for local development and keep production values
in the deployment environment.

The interface takes visual cues from [turbopuffer](https://turbopuffer.com/):
monospace type, ruled technical panels, restrained color, and dense operational
information.

## Evidence

The [evidence guide](BENCHMARKS.md) defines the source-of-truth policy and maps
each metric to NVIDIA datasheets, NVBandwidth, NCCL Tests, Nsight Compute,
cuBLAS/cuBLASLt, or MLPerf. The checked-in [H100 report](results/h100-sxm.md)
and [JSON](results/h100-sxm.json) are prototype calibration artifacts.

Modal availability and request semantics were checked against the
[Modal GPU guide](https://modal.com/docs/guide/gpu) and with live `nvidia-smi`
allocations on 2026-08-09. Hardware ceilings come from NVIDIA's
[H100 specifications](https://www.nvidia.com/en-us/data-center/h100/) and
[HGX B200/B300 specifications](https://www.nvidia.com/en-us/data-center/hgx/).

This project is inspired by Simon Eskildsen's
[Napkin Math](https://github.com/sirupsen/napkin-math) and is MIT licensed.
