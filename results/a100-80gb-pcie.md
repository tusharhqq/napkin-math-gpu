# NVIDIA A100 80GB PCIe benchmark

Captured `2026-08-08T18:02:54.230590+00:00` using the `A100-80GB` Modal request in `full` mode.

| Operation | Measured | Median benchmark time | Small job | Large job |
| --- | ---: | ---: | ---: | ---: |
| Tiny elementwise kernel | 6.08 μs | 0.0061 ms | 1K launches → 6.08 ms | 1M launches → 6.08 s |
| Pinned host → device | 25 GB/s | 21.8904 ms | 1 GB → 40.8 ms | 1 TB → 40.8 s |
| Device → pinned host | 26 GB/s | 20.4056 ms | 1 GB → 38 ms | 1 TB → 38 s |
| HBM copy (read + write) | 1,660 GB/s | 0.6469 ms | 1 GB → 602 μs | 1 TB → 602 ms |
| Elementwise fp32 add (2 reads + write) | 1,689 GB/s | 0.4768 ms | 1 GB → 592 μs | 1 TB → 592 ms |
| fp16 matrix multiply | 231 TFLOP/s | 4.7645 ms | 1 TFLOP → 4.33 ms | 1 PFLOP → 4.33 s |
| bf16 matrix multiply | 236 TFLOP/s | 4.6534 ms | 1 TFLOP → 4.23 ms | 1 PFLOP → 4.23 s |
| tf32 matrix multiply | 113 TFLOP/s | 9.6875 ms | 1 TFLOP → 8.81 ms | 1 PFLOP → 8.81 s |
| fp32 matrix multiply (TF32 disabled) | 19 TFLOP/s | 58.2421 ms | 1 TFLOP → 53 ms | 1 PFLOP → 53 s |

## Environment

- GPU: `NVIDIA A100 80GB PCIe`; 81920 MiB; compute capability 8.0
- PyTorch: `2.8.0+cu128`; CUDA runtime `12.8`; driver `580.95.05`
- Method: CUDA events on the default stream; median of 7 rounds after per-operation warmup
- Correctness: all benchmark checks passed

The JSON file next to this report is the source of truth and includes raw round samples.
