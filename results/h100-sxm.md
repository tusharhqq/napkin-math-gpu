# NVIDIA H100 80GB HBM3 benchmark

Captured `2026-08-08T17:38:29.399349+00:00` using the `H100!` Modal request in `full` mode.

| Operation | Measured | Median time |
| --- | ---: | ---: |
| Tiny elementwise kernel | 5.17 μs | 0.0052 ms |
| Pinned host → device | 56 GB/s | 9.6647 ms |
| Device → pinned host | 55 GB/s | 9.7835 ms |
| HBM copy (read + write) | 3,004 GB/s | 0.3575 ms |
| Elementwise fp32 add (2 reads + write) | 3,064 GB/s | 0.2628 ms |
| fp16 matrix multiply | 702 TFLOP/s | 1.5667 ms |
| bf16 matrix multiply | 711 TFLOP/s | 1.5454 ms |
| tf32 matrix multiply | 375 TFLOP/s | 2.9357 ms |
| fp32 matrix multiply (TF32 disabled) | 52 TFLOP/s | 21.2375 ms |

## Environment

- GPU: `NVIDIA H100 80GB HBM3`; 81559 MiB; compute capability 9.0
- PyTorch: `2.8.0+cu128`; CUDA runtime `12.8`; driver `580.95.05`
- Method: CUDA events on the default stream; median of 7 rounds after per-operation warmup
- Correctness: all benchmark checks passed

The JSON file next to this report is the source of truth and includes raw round samples.
