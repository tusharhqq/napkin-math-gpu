"""Run the GPU Napkin Math benchmark on a pinned Modal GPU.

Usage:
    modal run modal_benchmark.py
    modal run modal_benchmark.py --gpu a100
    modal run modal_benchmark.py --quick
    modal run modal_benchmark.py --output results/my-run.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple, cast

import modal

from napkin_profile import SCHEMA_VERSION, Metric, Metrics, Profile, make_metric


TORCH_VERSION = "2.8.0"
NUMPY_VERSION = "2.2.6"


class GpuTarget(NamedTuple):
    key: str
    modal_request: str
    default_output: str


# One row per supported GPU. Modal needs a decorate-time gpu= string, so wrappers
# are generated from this table (H100! blocks a silent H200 upgrade).
GPU_TARGETS: tuple[GpuTarget, ...] = (
    GpuTarget("h100", "H100!", "results/h100-sxm.json"),
    GpuTarget("a100", "A100-80GB", "results/a100-80gb-pcie.json"),
)
GPU_BY_KEY = {target.key: target for target in GPU_TARGETS}

image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(
        f"torch=={TORCH_VERSION}",
        f"numpy=={NUMPY_VERSION}",
    )
    .add_local_python_source("napkin_profile")
)
app = modal.App("gpu-napkin-math", image=image)


def _benchmark(*, gpu_request: str, quick: bool = False) -> Profile:
    import platform
    import statistics
    import subprocess
    from datetime import datetime, timezone

    import numpy as np
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available")

    torch.manual_seed(20260808)
    torch.cuda.manual_seed_all(20260808)
    device = torch.device("cuda:0")
    props = torch.cuda.get_device_properties(device)

    def cuda_samples(fn, *, warmups: int, iterations: int, rounds: int) -> list[float]:
        for _ in range(warmups):
            fn()
        torch.cuda.synchronize()

        samples = []
        for _ in range(rounds):
            start = torch.cuda.Event(enable_timing=True)
            end = torch.cuda.Event(enable_timing=True)
            start.record()
            for _ in range(iterations):
                fn()
            end.record()
            end.synchronize()
            samples.append(start.elapsed_time(end) / iterations)
        return samples

    rounds = 3 if quick else 7
    metrics: dict[str, Metric] = {}
    checks: dict[str, bool] = {}

    def record_bandwidth(
        name: str,
        *,
        samples_ms: list[float],
        bytes_counted: int,
        **details: object,
    ) -> None:
        median_ms = statistics.median(samples_ms)
        metrics[name] = make_metric(
            samples_ms,
            value=bytes_counted / (median_ms / 1e3) / 1e9,
            unit="GB/s",
            bytes_counted=bytes_counted,
            **details,
        )

    def probe_indices(n: int, *, on_device: bool = False) -> torch.Tensor:
        return torch.tensor([0, n // 2, n - 1], device=device if on_device else "cpu")

    # One-element in-place add: end-to-end tiny-kernel latency.
    tiny = torch.ones(1, device=device)
    tiny_samples = cuda_samples(
        lambda: tiny.add_(1), warmups=20, iterations=100 if quick else 1000, rounds=rounds
    )
    tiny_us = statistics.median(tiny_samples) * 1e3
    metrics["tiny_kernel"] = make_metric(
        tiny_samples,
        value=tiny_us,
        unit="us",
        operation="torch.Tensor.add_ on one fp32 element",
    )
    checks["tiny_kernel_finite"] = torch.isfinite(tiny).all().item()

    # Device bandwidth ops: one row per measurement (time → GB/s from algorithmic bytes).
    device_bw_iters = 10 if quick else 30

    def setup_hbm_copy(mib: int):
        n = mib * 1024 * 1024 // 4
        src = torch.arange(n, dtype=torch.float32, device=device)
        dst = torch.empty_like(src)
        idx = probe_indices(n, on_device=True)
        return (
            lambda: dst.copy_(src),
            src.numel() * src.element_size() * 2,
            lambda: torch.equal(src[idx], dst[idx]),
            {"allocation_mib": mib, "convention": "source read plus destination write"},
        )

    def setup_elementwise_add(mib: int):
        n = mib * 1024 * 1024 // 4
        a = torch.randn(n, dtype=torch.float32, device=device)
        b = torch.randn_like(a)
        out = torch.empty_like(a)
        idx = probe_indices(n, on_device=True)
        return (
            lambda: torch.add(a, b, out=out),
            n * 3 * 4,
            lambda: bool(torch.allclose(out[idx], a[idx] + b[idx])),
            {"elements": n, "convention": "two reads plus one write"},
        )

    for name, mib, setup in (
        ("hbm_copy", 128 if quick else 512, setup_hbm_copy),
        ("elementwise_add", 64 if quick else 256, setup_elementwise_add),
    ):
        fn, bytes_counted, check_fn, details = setup(mib)
        samples = cuda_samples(fn, warmups=10, iterations=device_bw_iters, rounds=rounds)
        record_bandwidth(name, samples_ms=samples, bytes_counted=bytes_counted, **details)
        checks[name] = check_fn()

    # Pinned host + non-blocking copies measure link bandwidth, not pageable staging.
    transfer_mib = 64 if quick else 512
    transfer_elements = transfer_mib * 1024 * 1024 // 4
    transfer_bytes = transfer_elements * 4
    transfer_iters = 5 if quick else 20
    host_src = torch.arange(transfer_elements, dtype=torch.float32, pin_memory=True)
    host_dst = torch.empty(transfer_elements, dtype=torch.float32, pin_memory=True)
    gpu_transfer = torch.empty(transfer_elements, dtype=torch.float32, device=device)
    host_transfer_ops = (
        (
            "host_to_device",
            lambda: gpu_transfer.copy_(host_src, non_blocking=True),
            "pinned host to device",
        ),
        (
            "device_to_host",
            lambda: host_dst.copy_(gpu_transfer, non_blocking=True),
            "device to pinned host",
        ),
    )
    for name, fn, direction in host_transfer_ops:
        samples = cuda_samples(fn, warmups=5, iterations=transfer_iters, rounds=rounds)
        record_bandwidth(
            name,
            samples_ms=samples,
            bytes_counted=transfer_bytes,
            allocation_mib=transfer_mib,
            direction=direction,
        )
    torch.cuda.synchronize()
    transfer_indices = probe_indices(transfer_elements)
    checks["host_device_round_trip"] = torch.equal(
        host_src[transfer_indices], host_dst[transfer_indices]
    )

    # GEMM: C = A @ B, 2*M*N*K FLOPs.
    gemm_n = 4096 if quick else 8192
    gemm_specs = (
        ("fp16", torch.float16, True),
        ("bf16", torch.bfloat16, True),
        ("tf32", torch.float32, True),
        ("fp32", torch.float32, False),
    )
    gemm_tolerance = {
        "fp16": (0.03, 0.25),
        "bf16": (0.08, 1.0),
        "tf32": (0.01, 0.08),
        "fp32": (0.0001, 0.001),
    }
    for label, dtype, allow_tf32 in gemm_specs:
        torch.backends.cuda.matmul.allow_tf32 = allow_tf32
        a = torch.randn((gemm_n, gemm_n), dtype=dtype, device=device)
        b = torch.randn((gemm_n, gemm_n), dtype=dtype, device=device)
        out = torch.empty((gemm_n, gemm_n), dtype=dtype, device=device)
        samples = cuda_samples(
            lambda: torch.mm(a, b, out=out),
            warmups=5 if quick else 10,
            iterations=5 if quick else 20,
            rounds=rounds,
        )
        median_ms = statistics.median(samples)
        flops = 2 * gemm_n**3
        tflops = flops / (median_ms / 1e3) / 1e12
        metrics[f"gemm_{label}"] = make_metric(
            samples,
            value=tflops,
            unit="TFLOP/s",
            shape=[gemm_n, gemm_n, gemm_n],
            flops=flops,
            input_dtype=str(dtype).removeprefix("torch."),
            allow_tf32=allow_tf32,
        )

        # CPU float64 reference on a smaller seeded problem.
        check_n = 256
        generator = torch.Generator().manual_seed(20260808)
        check_a_cpu = torch.randn((check_n, check_n), generator=generator, dtype=torch.float32)
        check_b_cpu = torch.randn((check_n, check_n), generator=generator, dtype=torch.float32)
        reference = check_a_cpu.double().numpy() @ check_b_cpu.double().numpy()
        check_actual = (
            (
                check_a_cpu.to(device=device, dtype=dtype)
                @ check_b_cpu.to(device=device, dtype=dtype)
            )
            .float()
            .cpu()
            .numpy()
        )
        rtol, atol = gemm_tolerance[label]
        checks[f"gemm_{label}"] = bool(np.allclose(check_actual, reference, rtol=rtol, atol=atol))
    torch.backends.cuda.matmul.allow_tf32 = True

    query = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=name,uuid,memory.total,pci.bus_id,driver_version,power.limit",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    smi_name, uuid, memory_mib, pci_bus_id, driver, power_limit_w = [
        item.strip() for item in query.split(",")
    ]

    if not all(checks.values()):
        failures = [name for name, passed in checks.items() if not passed]
        raise AssertionError(f"correctness checks failed: {failures}")

    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "mode": "quick" if quick else "full",
        "device": {
            "name": smi_name,
            "uuid": uuid,
            "memory_mib": int(memory_mib),
            "pci_bus_id": pci_bus_id,
            "power_limit_w": float(power_limit_w),
            "compute_capability": f"{props.major}.{props.minor}",
            "multiprocessor_count": props.multi_processor_count,
        },
        "software": {
            "python": platform.python_version(),
            "torch": str(torch.__version__),
            "cuda_runtime": str(torch.version.cuda),
            "nvidia_driver": driver,
            "cudnn": str(torch.backends.cudnn.version()),
        },
        "methodology": {
            "timer": "CUDA events on the default stream",
            "statistic": f"median of {rounds} rounds after per-operation warmup",
            "allocation_units": "MiB (2^20 bytes)",
            "throughput_units": "GB/s (10^9 bytes/s) and TFLOP/s (10^12 FLOP/s)",
            "gpu_request": gpu_request,
            "seed": 20260808,
        },
        "checks": checks,
        "metrics": cast(Metrics, metrics),
    }


def _make_remote_benchmark(target: GpuTarget):
    """Bind a Modal Function to a fixed decorate-time GPU request string."""

    @app.function(
        gpu=target.modal_request,
        timeout=20 * 60,
        scaledown_window=60,
        name=f"benchmark_{target.key}",
    )
    def benchmark(quick: bool = False) -> Profile:
        return _benchmark(gpu_request=target.modal_request, quick=quick)

    return benchmark


REMOTE_BENCHMARKS = {target.key: _make_remote_benchmark(target) for target in GPU_TARGETS}


@app.local_entrypoint()
def main(gpu: str = "h100", output: str = "", quick: bool = False) -> None:
    try:
        target = GPU_BY_KEY[gpu]
    except KeyError as exc:
        choices = ", ".join(repr(key) for key in GPU_BY_KEY)
        raise ValueError(f"--gpu must be one of: {choices}") from exc

    result = REMOTE_BENCHMARKS[target.key].remote(quick=quick)
    output_path = Path(output or target.default_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Wrote {output_path}")
