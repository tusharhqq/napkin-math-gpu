# GPU Napkin Math

Five numbers, simple arithmetic, and a rough answer for an H100 workload.

## Memorize these

| | Napkin number |
| --- | ---: |
| Tiny kernel | **5 μs** |
| CPU ↔ GPU | **50 GB/s** |
| HBM | **3 TB/s** |
| BF16 compute | **700 TFLOP/s** |
| BF16 ridge point | **240 FLOP/byte** |

These are measured H100 numbers rounded for mental math, not precision
predictions.

## Use them

```text
launch time   = kernels × 5 μs
transfer time = CPU↔GPU bytes / 50 GB/s
memory time   = HBM bytes / 3 TB/s
compute time  = BF16 FLOPs / 700 TFLOP/s
device time   = max(memory time, compute time)
rough time    = transfer time + device time + launch time
```

The ridge point gives the bottleneck without calculating both times:

```text
arithmetic intensity = FLOPs / HBM bytes

below 240 FLOP/byte  → probably memory-bound
above 240 FLOP/byte  → probably compute-bound
```

Keep one or two significant digits. A useful estimate is allowed to be off by
2×; it should not pretend to know microseconds it cannot know.

## One worked estimate

A BF16 workload performs 200 TFLOPs, moves 1 TB through HBM, uploads 2 GB, and
launches 20 kernels.

```text
intensity = 200 TFLOP / 1 TB = 200 FLOP/byte  → memory-bound

compute   = 200 TFLOP / 700 TFLOP/s ≈ 0.29 s
memory    = 1 TB / 3 TB/s            ≈ 0.33 s
device    = max(0.29 s, 0.33 s)      ≈ 0.33 s
upload    = 2 GB / 50 GB/s           = 0.04 s
launches  = 20 × 5 μs                 ≈ 0 s at this scale
total                                    ≈ 0.37 s
```

Rough answer: **about 0.4 seconds, slightly memory-bound**.

## Extend the path when needed

The core five numbers cover a host transfer and one GPU. For input staging or
model parallelism, add two more H100-system numbers:

| Optional stage | Napkin number |
| --- | ---: |
| Pinned CPU RAM copy | **70 GB/s** |
| GPU ↔ GPU | **400 GB/s** |

```text
CPU RAM
   │  70 GB/s
PCIe
   ▼  50 GB/s
GPU HBM
   │  3 TB/s
GPU compute
   │  700 TFLOP/s BF16
NVLink / GPU interconnect
   ▼  400 GB/s
other GPUs
```

For a CPU copy, count both the read and the write. Copying a 2 GB buffer creates
4 GB of CPU-memory traffic.

## Calculator

The CLI checks the same arithmetic:

```sh
python3 gpu_napkin.py \
  --dtype bf16 \
  --flops 2e14 \
  --bytes 1e12 \
  --h2d-bytes 2e9 \
  --launches 20
```

It can also include `--cpu-bytes`, `--d2h-bytes`, and
`--gpu-to-gpu-bytes`. Its extra digits do not make the answer more certain.

## Behind the numbers

The [benchmark and evidence guide](BENCHMARKS.md) contains the Modal workflow,
A100 comparison, exact measurements, topology, raw-profile schema, caveats, and
development checks. Precise artifacts are available as the H100
([report](results/h100-sxm.md), [JSON](results/h100-sxm.json)) and A100
([report](results/a100-80gb-sxm4.md), [JSON](results/a100-80gb-sxm4.json))
profiles.

This project is inspired by Simon Eskildsen's
[Napkin Math](https://github.com/sirupsen/napkin-math), whose goal is to collect
numbers and techniques for quick first-principles estimates. This project is
also MIT licensed.
