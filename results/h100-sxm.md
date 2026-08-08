# NVIDIA H100 80GB HBM3 system-path benchmark

Captured `2026-08-08T19:07:55.650656+00:00` using the `H100!:2` Modal request in `full` mode.

| Operation | Measured | Median benchmark time | Small job | Large job |
| --- | ---: | ---: | ---: | ---: |
| Pinned CPU RAM copy (read + write) | 72 GB/s | 14.8278 ms | 1 GB → 13.8 ms | 1 TB → 13.8 s |
| Pinned host → device | 55 GB/s | 9.6820 ms | 1 GB → 18 ms | 1 TB → 18 s |
| Device → pinned host | 55 GB/s | 9.6775 ms | 1 GB → 18 ms | 1 TB → 18 s |
| HBM copy (read + write) | 3,000 GB/s | 0.3580 ms | 1 GB → 333 μs | 1 TB → 333 ms |
| Elementwise fp32 add (2 reads + write) | 3,058 GB/s | 0.2633 ms | 1 GB → 327 μs | 1 TB → 327 ms |
| Tiny elementwise kernel | 4.66 μs | 0.0047 ms | 1K launches → 4.66 ms | 1M launches → 4.66 s |
| fp16 matrix multiply | 693 TFLOP/s | 1.5855 ms | 1 TFLOP → 1.44 ms | 1 PFLOP → 1.44 s |
| bf16 matrix multiply | 717 TFLOP/s | 1.5326 ms | 1 TFLOP → 1.39 ms | 1 PFLOP → 1.39 s |
| tf32 matrix multiply | 380 TFLOP/s | 2.8954 ms | 1 TFLOP → 2.63 ms | 1 PFLOP → 2.63 s |
| fp32 matrix multiply (TF32 disabled) | 52 TFLOP/s | 21.2340 ms | 1 TFLOP → 19.3 ms | 1 PFLOP → 19.3 s |
| GPU 0 ↔ GPU 1 interconnect | 393 GB/s | 1.3661 ms | 1 GB → 2.54 ms | 1 TB → 2.54 s |

## Roofline ridge points

The ridge point is `compute ceiling ÷ HBM bandwidth`. A workload below it is memory-bound in this model; above it, compute-bound.

| Precision | Measured compute ceiling | Ridge point |
| --- | ---: | ---: |
| fp16 | 693 TFLOP/s | 231.2 FLOP/byte |
| bf16 | 717 TFLOP/s | 239.2 FLOP/byte |
| tf32 | 380 TFLOP/s | 126.6 FLOP/byte |
| fp32 | 52 TFLOP/s | 17.3 FLOP/byte |

## Environment

- CPU: `Modal CPU allocation (model not exposed)`; 8 PyTorch copy threads
- GPU: `NVIDIA H100 80GB HBM3`; 81559 MiB; compute capability 9.0; 2 devices
- GPU interconnect: GPU 0 ↔ GPU 1 is `18 × NVLink (26.562 GB/s/link)`; direct peer access passed
- PyTorch: `2.8.0+cu128`; CUDA runtime `12.8`; driver `580.95.05`
- Method: perf_counter for CPU RAM; CUDA events for GPU operations; median of 7 rounds after per-operation warmup
- Correctness: all benchmark checks passed

The JSON file next to this report is the source of truth and includes raw round samples.
