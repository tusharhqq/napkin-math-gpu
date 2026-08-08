# GPU Napkin Math

GPU numbers you can keep in your head, plus the benchmark that produced them.

This project is heavily inspired by Simon Eskildsen's
[Napkin Math](https://github.com/sirupsen/napkin-math): prefer a few measured,
rounded numbers over faux precision, keep the units visible, and aim to predict
systems within an order of magnitude. This is an original GPU-focused project;
the upstream repository is kept under `reference/` for study and is not part of
the benchmark implementation.

## Numbers worth memorizing

Measured on a Modal `NVIDIA H100 80GB HBM3` (SXM) on August 8, 2026. The
napkin numbers are deliberately rounded; the measured column points back to
the full-size seven-round run.

| Operation | Napkin number | Measured | What it helps estimate |
| --- | ---: | ---: | --- |
| Tiny GPU kernel | **5 μs** | 5.17 μs | Death by many small launches |
| Pinned host → GPU | **50 GB/s** | 56 GB/s | Input upload time |
| GPU → pinned host | **50 GB/s** | 55 GB/s | Result download time |
| HBM copy | **3 TB/s** | 3,004 GB/s | Memory-bound kernels |
| fp32 elementwise add | **3 TB/s** | 3,064 GB/s | A realistic bandwidth ceiling |
| fp16 / bf16 GEMM | **700 TFLOP/s** | 702 / 711 TFLOP/s | Tensor math |
| tf32 GEMM | **400 TFLOP/s** | 375 TFLOP/s | Fast fp32-shaped training math |
| Strict fp32 GEMM | **50 TFLOP/s** | 52 TFLOP/s | Full fp32 compute |

See the [human-readable report](results/h100-sxm.md) and
[raw result with every sample](results/h100-sxm.json).

Throughput uses decimal `GB/s` and `TFLOP/s`; allocation sizes use binary MiB.
For HBM copy, bytes moved includes both the read and the write. GEMM counts
`2 × M × N × K` FLOPs.

## Run the benchmark

Install and authenticate the [Modal](https://modal.com/) CLI, then run:

```sh
python3 -m pip install 'modal==1.5.3'
modal run modal_benchmark.py
python3 render_results.py results/h100-sxm.json results/h100-sxm.md
```

The benchmark requests `gpu="H100!"`; the exclamation mark is important because
it prevents Modal from silently upgrading the run to an H200. The container pins
PyTorch and NumPy, records the exact GPU/driver/runtime, warms every operation,
uses CUDA events, reports the median of seven rounds, retains all samples, and
fails instead of publishing a result if a correctness check fails.

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

This is a floor, not a promise. Real kernels also pay for dependencies,
synchronization, imperfect occupancy, non-coalesced access, framework overhead,
and contention. If an estimate is off by 2×, that is useful; if it is off by
100×, one of the assumptions is probably wrong.

## Benchmark boundaries

- This first profile covers one GPU, not multi-GPU collectives or networking.
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
