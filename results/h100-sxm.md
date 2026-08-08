# NVIDIA H100 80GB HBM3 benchmark

Captured `2026-08-08T17:38:29.399349+00:00` using the `H100!` Modal request in `full` mode.

| Operation | Measured | Median benchmark time | Small job | Large job |
| --- | ---: | ---: | ---: | ---: |
| Tiny elementwise kernel | 5.17 μs | 0.0052 ms | 1K launches → 5.17 ms | 1M launches → 5.17 s |
| Pinned host → device | 56 GB/s | 9.6647 ms | 1 GB → 18 ms | 1 TB → 18 s |
| Device → pinned host | 55 GB/s | 9.7835 ms | 1 GB → 18.2 ms | 1 TB → 18.2 s |
| HBM copy (read + write) | 3,004 GB/s | 0.3575 ms | 1 GB → 333 μs | 1 TB → 333 ms |
| Elementwise fp32 add (2 reads + write) | 3,064 GB/s | 0.2628 ms | 1 GB → 326 μs | 1 TB → 326 ms |
| fp16 matrix multiply | 702 TFLOP/s | 1.5667 ms | 1 TFLOP → 1.42 ms | 1 PFLOP → 1.42 s |
| bf16 matrix multiply | 711 TFLOP/s | 1.5454 ms | 1 TFLOP → 1.41 ms | 1 PFLOP → 1.41 s |
| tf32 matrix multiply | 375 TFLOP/s | 2.9357 ms | 1 TFLOP → 2.67 ms | 1 PFLOP → 2.67 s |
| fp32 matrix multiply (TF32 disabled) | 52 TFLOP/s | 21.2375 ms | 1 TFLOP → 19.3 ms | 1 PFLOP → 19.3 s |

## Roofline ridge points

The ridge point is `compute ceiling ÷ HBM bandwidth`. A workload below it is memory-bound in this model; above it, compute-bound.

| Precision | Measured compute ceiling | Ridge point |
| --- | ---: | ---: |
| fp16 | 702 TFLOP/s | 233.7 FLOP/byte |
| bf16 | 711 TFLOP/s | 236.9 FLOP/byte |
| tf32 | 375 TFLOP/s | 124.7 FLOP/byte |
| fp32 | 52 TFLOP/s | 17.2 FLOP/byte |

## Environment

- GPU: `NVIDIA H100 80GB HBM3`; 81559 MiB; compute capability 9.0
- PyTorch: `2.8.0+cu128`; CUDA runtime `12.8`; driver `580.95.05`
- Method: CUDA events on the default stream; median of 7 rounds after per-operation warmup
- Correctness: all benchmark checks passed

The JSON file next to this report is the source of truth and includes raw round samples.
