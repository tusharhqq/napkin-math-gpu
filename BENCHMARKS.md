# Behind the GPU Napkin Math numbers

This is the evidence and implementation layer. The user-facing product is the
small set of rounded numbers and arithmetic in the [README](README.md).

## Canonical profiles

Both profiles are full, seven-round, two-GPU Modal runs captured on August 8,
2026. The table below is intentionally precise; these values support the rounded
numbers in the README and are not another table to memorize.

| Measurement | H100 | A100 |
| --- | ---: | ---: |
| Pinned CPU RAM copy | 72 GB/s | 71 GB/s |
| Pinned host → GPU | 55 GB/s | 26 GB/s |
| GPU → pinned host | 55 GB/s | 26 GB/s |
| HBM copy | 3,000 GB/s | 1,750 GB/s |
| Tiny kernel | 4.66 μs | 5.23 μs |
| BF16 GEMM | 717 TFLOP/s | 289 TFLOP/s |
| BF16 ridge point | 239.2 FLOP/byte | 165.4 FLOP/byte |
| GPU 0 ↔ GPU 1 | 393 GB/s | 274 GB/s |

- H100: [report](results/h100-sxm.md) · [raw JSON](results/h100-sxm.json)
- A100: [report](results/a100-80gb-sxm4.md) · [raw JSON](results/a100-80gb-sxm4.json)

The JSON files are the source of truth and retain every round sample, precise
directional peer-transfer values, correctness checks, software versions, and
the NVIDIA topology output exposed inside the container.

## Evidence pipeline

```text
Modal two-GPU allocation
          │
modal_benchmark.py
          │
PyTorch / cuBLAS measurements + correctness checks
          │
schema-v2 typed JSON profile
          │
render_results.py + tests
          │
rounded README numbers
```

`modal_benchmark.py` is producer-only and does not import the estimator. The
shared contract in `napkin_profile.py` requires CPU RAM, CPU↔GPU, HBM, compute,
tiny-kernel, and GPU↔GPU metrics. A profile missing one of those stages does not
validate.

## Run the canonical benchmarks

Install and authenticate the Modal CLI, then run:

```sh
python3 -m pip install 'modal==1.5.3'
modal run modal_benchmark.py
modal run modal_benchmark.py --gpu a100
python3 render_results.py results/h100-sxm.json results/h100-sxm.md
python3 render_results.py results/a100-80gb-sxm4.json results/a100-80gb-sxm4.md
```

| Profile | Measured devices | Modal request | Exposed topology |
| --- | --- | --- | --- |
| H100 | 2× `NVIDIA H100 80GB HBM3` | `H100!:2` | 18 active NVLinks per GPU |
| A100 | 2× `NVIDIA A100-SXM4-80GB` | `A100-80GB:2` | 12 active NVLinks per GPU |

The H100 `!` prevents a silent H200 upgrade. The A100 artifact is named SXM4
because that is the device returned by the two-GPU allocation; it is not the
PCIe device returned by the earlier single-GPU run.

For a short smoke test:

```sh
modal run modal_benchmark.py --quick --output /tmp/gpu-napkin-quick.json
```

Never publish `--quick` output as a canonical profile.

## Measurement method

- CPU RAM is an 8-thread pinned-buffer copy timed with `perf_counter`. Bytes
  counted include the source read and destination write.
- CPU↔GPU uses reusable pinned host buffers and asynchronous copies.
- HBM copy counts the source read and destination write. Elementwise add counts
  two reads and one write.
- GPU operations use CUDA events after per-operation warmup.
- GEMM counts `2 × M × N × K` FLOPs. The BF16, FP16, TF32, and strict-FP32
  paths are recorded separately.
- GPU↔GPU is a direct one-way peer copy. The reported value is the slower of
  GPU 0→1 and GPU 1→0; both directional values remain in JSON.
- Each full result is the median of seven rounds. All round samples are retained.

## Correctness and scope boundaries

- Every run fails if the CPU copy, host/device round trip, HBM operations, peer
  copies, or GEMM checks fail.
- Matrix validation uses an independent CPU float64 reference on a smaller fixed
  problem.
- PyTorch/cuBLAS throughput is a production-relevant ceiling, not bare-metal
  hardware peak and not a claim about every framework.
- The tiny-kernel metric is a one-element in-place add including scheduling and
  execution. It is not a host-only CUDA API launch measurement.
- Algorithmic bytes are used instead of hardware performance counters.
- The CPU model and PCI bus IDs are masked by the Modal runtime and are recorded
  as unavailable rather than inferred.
- The interconnect profile covers same-host point-to-point copies. Collective
  algorithms and multi-node networking are not modeled yet.

## Development checks

Run GPU-free checks in a Modal CPU container:

```sh
modal shell --add-python 3.12 --add-local . -c \
  'cd /mnt/napkin-math-gpu && python -m pip install ".[test]" ty && \
   python -m pytest && \
   ty check gpu_napkin.py napkin_profile.py render_results.py tests/test_gpu_napkin.py && \
   python -m compileall gpu_napkin.py napkin_profile.py modal_benchmark.py render_results.py'
```

The ridge-point presentation was informed by George Typaldos's
[GPU-Roofline-Python](https://github.com/Giotyp/GPU-Roofline-Python), licensed
under MIT. The repository also bundles an MIT-licensed upstream
[Napkin Math snapshot](reference/napkin-math) for study; its CPU numbers are not
used as this project's measured CPU profile.
