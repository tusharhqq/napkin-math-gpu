# GPU Napkin Math

GPU numbers you can keep in your head, plus the benchmark that produced them.

This project is heavily inspired by Simon Eskildsen's
[Napkin Math](https://github.com/sirupsen/napkin-math): prefer a few measured,
rounded numbers over faux precision, keep the units visible, and aim to predict
systems within an order of magnitude. This is an original GPU-focused project;
the upstream repository is kept under `reference/` for study and is not part of
the benchmark implementation.

## Profile comparison

The same full-size, seven-round benchmark produces noticeably different napkin
numbers on the two GPUs. These are rounded for mental math; follow the report
links for the measured values and environment details.

| Profile | Tiny kernel | Pinned host link | HBM / fp32 add | fp16 / bf16 | tf32 | Strict fp32 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| H100 80 GB SXM | **5 μs** | **50 GB/s** | **3 TB/s** | **700 TFLOP/s** | **400 TFLOP/s** | **50 TFLOP/s** |
| A100 80 GB PCIe | **6 μs** | **25 GB/s** | **1.5 TB/s** | **250 TFLOP/s** | **100 TFLOP/s** | **20 TFLOP/s** |

- H100: [report](results/h100-sxm.md) · [raw profile](results/h100-sxm.json)
- A100: [report](results/a100-80gb-pcie.md) · [raw profile](results/a100-80gb-pcie.json)

The H100 is roughly 2× faster for transfers and bandwidth but about 3× faster
for tensor math in these runs. A GPU name is therefore part of every estimate,
not a footnote.

## H100 numbers worth memorizing

Measured on a Modal `NVIDIA H100 80GB HBM3` (SXM) on August 8, 2026. The
napkin numbers are deliberately rounded; the measured column points back to
the full-size seven-round run.

| Operation | Napkin number | Measured | Small job | Large job | What it helps estimate |
| --- | ---: | ---: | ---: | ---: | --- |
| Tiny GPU kernel | **5 μs** | 5.17 μs | 1K launches → **5 ms** | 1M launches → **5 s** | Death by many small launches |
| Pinned host → GPU | **50 GB/s** | 56 GB/s | 1 GB → **20 ms** | 1 TB → **20 s** | Input upload time |
| GPU → pinned host | **50 GB/s** | 55 GB/s | 1 GB → **20 ms** | 1 TB → **20 s** | Result download time |
| HBM copy | **3 TB/s** | 3,004 GB/s | 1 GB → **0.3 ms** | 1 TB → **0.3 s** | Memory-bound kernels |
| fp32 elementwise add | **3 TB/s** | 3,064 GB/s | 1 GB → **0.3 ms** | 1 TB → **0.3 s** | A realistic bandwidth ceiling |
| fp16 / bf16 GEMM | **700 TFLOP/s** | 702 / 711 TFLOP/s | 1 TFLOP → **1.4 ms** | 1 PFLOP → **1.4 s** | Tensor math |
| tf32 GEMM | **400 TFLOP/s** | 375 TFLOP/s | 1 TFLOP → **2.5 ms** | 1 PFLOP → **2.5 s** | Fast fp32-shaped training math |
| Strict fp32 GEMM | **50 TFLOP/s** | 52 TFLOP/s | 1 TFLOP → **20 ms** | 1 PFLOP → **20 s** | Full fp32 compute |

Throughput uses decimal `GB/s` and `TFLOP/s`; allocation sizes use binary MiB.
For HBM copy, bytes moved includes both the read and the write. GEMM counts
`2 × M × N × K` FLOPs. The small- and large-job times use the rounded
napkin numbers, so they are for mental math rather than precision prediction.

## Worked examples

These use the H100 table. Try each question before reading its calculation.
They are lower bounds: the point is to identify the dominant term and get the
scale right.

### 1. Batch of tokens through a matmul

**Problem:** An fp16 projection multiplies `[32K, 4096]` tokens by a
`[4096, 4096]` weight matrix. How long should the matmul take?

```text
FLOPs        = 2 × 32K × 4096 × 4096 ≈ 1.1 TFLOPs
compute time = 1.1 TFLOPs / 700 TFLOP/s ≈ 1.6 ms
HBM traffic  ≈ 0.27 GB input + 0.03 GB weights + 0.27 GB output
memory time  = 0.57 GB / 3,000 GB/s ≈ 0.19 ms
```

**Answer:** About **1.6 ms**, compute-bound. The roofline uses the larger of
the compute and memory times, not their sum.

### 2. Upload, then run a bandwidth-bound kernel

**Problem:** Upload a 2 GB tensor, then run one kernel that reads all 2 GB and
writes 2 GB. Assume negligible compute and no download.

```text
upload = 2 GB / 50 GB/s    = 40 ms
kernel = 4 GB / 3,000 GB/s ≈ 1.3 ms
launch = 1 × 5 μs           ≈ 0.005 ms
total                           ≈ 41 ms
```

**Answer:** About **41 ms**. Moving the input over the host link costs roughly
30× more than touching it on the GPU.

### 3. Death by tiny launches

**Problem:** A pipeline launches 10,000 tiny kernels whose useful work is
negligible. What is the launch-and-execute floor?

```text
10,000 launches × 5 μs/launch = 50 ms
```

**Answer:** About **50 ms**. If fusion cuts that to 100 launches, the same term
falls to about **0.5 ms**.

### 4. Pick the roofline bottleneck

**Problem:** A workload performs 200 TFLOPs, moves 1 TB through HBM, and uses
20 kernels. There are no host transfers. What is its lower bound?

```text
compute = 200 TFLOPs / 700 TFLOP/s ≈ 286 ms
memory  = 1 TB / 3 TB/s             ≈ 333 ms
device  = max(286 ms, 333 ms)       = 333 ms
launch  = 20 × 5 μs                  = 0.1 ms
```

**Answer:** About **333 ms**, slightly memory-bound. Adding compute and HBM
times would incorrectly predict 619 ms under this roofline model.

## Run the benchmark

Install and authenticate the [Modal](https://modal.com/) CLI, then run:

```sh
python3 -m pip install 'modal==1.5.3'
modal run modal_benchmark.py
modal run modal_benchmark.py --gpu a100
python3 render_results.py results/h100-sxm.json results/h100-sxm.md
python3 render_results.py results/a100-80gb-pcie.json results/a100-80gb-pcie.md
```

The default is H100. Its `gpu="H100!"` request prevents a silent H200 upgrade;
`--gpu a100` requests `gpu="A100-80GB"` rather than the capacity-ambiguous bare
`A100`. The container pins PyTorch and NumPy, records the exact
GPU/driver/runtime, warms every operation, uses CUDA events, reports the median
of seven rounds, retains all samples, and fails instead of publishing a result
if a correctness check fails.

For a short smoke test that must not be published as the canonical result:

```sh
modal run modal_benchmark.py --quick --output /tmp/gpu-napkin-quick.json
```

## Estimate a workload

The calculator uses the simple roofline lower bound:

```text
device time = max(FLOPs / measured compute, bytes / measured HBM bandwidth)
total time  = device time + transfers + launch overhead
```

For example, estimate an fp16 workload with 200 TFLOPs, 40 GB of device-memory
traffic, a 2 GB upload, a 1 GB download, and 20 kernels:

```sh
python3 gpu_napkin.py \
  --dtype fp16 \
  --flops 2e14 \
  --bytes 4e10 \
  --h2d-bytes 2e9 \
  --d2h-bytes 1e9 \
  --launches 20
```

The estimator defaults to the H100 profile. To use the A100 measurements, pass
`--profile results/a100-80gb-pcie.json` alongside the workload arguments.

This is a floor, not a promise. Real kernels also pay for dependencies,
synchronization, imperfect occupancy, non-coalesced access, framework overhead,
and contention. If an estimate is off by 2×, that is useful; if it is off by
100×, one of the assumptions is probably wrong.

## Benchmark boundaries

- These profiles cover one GPU at a time, not multi-GPU collectives or networking.
- PyTorch/cuBLAS performance is a production-relevant ceiling, not bare-metal
  hardware peak and not a claim about every framework.
- The tiny-kernel row is a one-element in-place add. It includes scheduling and
  execution; it is not a host-only CUDA API launch measurement.
- PCIe transfer numbers use reusable pinned host buffers and asynchronous copies.
- HBM and elementwise rows count algorithmic bytes moved, not hardware counters.
- Matrix validation uses an independent CPU float64 reference on a smaller fixed
  problem before the benchmark result is accepted.

## Development

Run the local, GPU-free checks with:

```sh
python3 -m pytest
python3 -m compileall gpu_napkin.py modal_benchmark.py render_results.py
```

## Acknowledgements

The structure and philosophy are inspired by
[sirupsen/napkin-math](https://github.com/sirupsen/napkin-math), created by
Simon Eskildsen and licensed under MIT. No upstream source code is copied into
the GPU benchmark. This project is also MIT licensed.
