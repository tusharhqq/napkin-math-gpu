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
from typing import Any

import modal


TORCH_VERSION = "2.8.0"
NUMPY_VERSION = "2.2.6"
H100_GPU = "H100!"  # The ! suffix prevents an automatic H200 upgrade.
A100_GPU = "A100-80GB"

image = modal.Image.debian_slim(python_version="3.12").uv_pip_install(
    f"torch=={TORCH_VERSION}",
    f"numpy=={NUMPY_VERSION}",
)
app = modal.App("gpu-napkin-math", image=image)


def _benchmark(*, gpu_request: str, quick: bool = False) -> dict[str, Any]:
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

    def metric(
        samples_ms: list[float], *, value: float, unit: str, **details: Any
    ) -> dict[str, Any]:
        return {
            "value": value,
            "unit": unit,
            "median_ms": statistics.median(samples_ms),
            "samples_ms": samples_ms,
            **details,
        }

    rounds = 3 if quick else 7
    metrics: dict[str, dict[str, Any]] = {}
    checks: dict[str, bool] = {}

    # One-element in-place add: end-to-end tiny-kernel latency.
    tiny = torch.ones(1, device=device)
    tiny_samples = cuda_samples(
        lambda: tiny.add_(1), warmups=20, iterations=100 if quick else 1000, rounds=rounds
    )
    tiny_us = statistics.median(tiny_samples) * 1e3
    metrics["tiny_kernel"] = metric(
        tiny_samples,
        value=tiny_us,
        unit="us",
        operation="torch.Tensor.add_ on one fp32 element",
    )
    checks["tiny_kernel_finite"] = torch.isfinite(tiny).all().item()

    # HBM copy counts both the read and the write.
    copy_mib = 128 if quick else 512
    copy_elements = copy_mib * 1024 * 1024 // 4
    copy_src = torch.arange(copy_elements, dtype=torch.float32, device=device)
    copy_dst = torch.empty_like(copy_src)
    copy_samples = cuda_samples(
        lambda: copy_dst.copy_(copy_src), warmups=10, iterations=10 if quick else 30, rounds=rounds
    )
    copy_ms = statistics.median(copy_samples)
    copy_bytes = copy_src.numel() * copy_src.element_size() * 2
    copy_gbps = copy_bytes / (copy_ms / 1e3) / 1e9
    metrics["hbm_copy"] = metric(
        copy_samples,
        value=copy_gbps,
        unit="GB/s",
        allocation_mib=copy_mib,
        bytes_counted=copy_bytes,
        convention="source read plus destination write",
    )
    check_idx = torch.tensor([0, copy_elements // 2, copy_elements - 1], device=device)
    checks["hbm_copy"] = torch.equal(copy_src[check_idx], copy_dst[check_idx])

    # Elementwise add: 12 bytes/element (2 fp32 reads + 1 write).
    add_mib = 64 if quick else 256
    add_elements = add_mib * 1024 * 1024 // 4
    add_a = torch.randn(add_elements, dtype=torch.float32, device=device)
    add_b = torch.randn_like(add_a)
    add_out = torch.empty_like(add_a)
    add_samples = cuda_samples(
        lambda: torch.add(add_a, add_b, out=add_out),
        warmups=10,
        iterations=10 if quick else 30,
        rounds=rounds,
    )
    add_ms = statistics.median(add_samples)
    add_bytes = add_elements * 3 * 4
    add_gbps = add_bytes / (add_ms / 1e3) / 1e9
    metrics["elementwise_add"] = metric(
        add_samples,
        value=add_gbps,
        unit="GB/s",
        elements=add_elements,
        bytes_counted=add_bytes,
        convention="two reads plus one write",
    )
    add_check_idx = torch.tensor([0, add_elements // 2, add_elements - 1], device=device)
    checks["elementwise_add"] = bool(
        torch.allclose(add_out[add_check_idx], add_a[add_check_idx] + add_b[add_check_idx])
    )

    # Pinned host + non-blocking copies measure link bandwidth, not pageable staging.
    transfer_mib = 64 if quick else 512
    transfer_elements = transfer_mib * 1024 * 1024 // 4
    host_src = torch.arange(transfer_elements, dtype=torch.float32, pin_memory=True)
    host_dst = torch.empty(transfer_elements, dtype=torch.float32, pin_memory=True)
    gpu_transfer = torch.empty(transfer_elements, dtype=torch.float32, device=device)
    h2d_samples = cuda_samples(
        lambda: gpu_transfer.copy_(host_src, non_blocking=True),
        warmups=5,
        iterations=5 if quick else 20,
        rounds=rounds,
    )
    d2h_samples = cuda_samples(
        lambda: host_dst.copy_(gpu_transfer, non_blocking=True),
        warmups=5,
        iterations=5 if quick else 20,
        rounds=rounds,
    )
    torch.cuda.synchronize()
    transfer_bytes = transfer_elements * 4
    for name, samples, direction in (
        ("host_to_device", h2d_samples, "pinned host to device"),
        ("device_to_host", d2h_samples, "device to pinned host"),
    ):
        median_ms = statistics.median(samples)
        gbps = transfer_bytes / (median_ms / 1e3) / 1e9
        metrics[name] = metric(
            samples,
            value=gbps,
            unit="GB/s",
            allocation_mib=transfer_mib,
            bytes_counted=transfer_bytes,
            direction=direction,
        )
    transfer_indices = torch.tensor([0, transfer_elements // 2, transfer_elements - 1])
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
        metrics[f"gemm_{label}"] = metric(
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
        "schema_version": 1,
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
        "metrics": metrics,
    }


@app.function(gpu=H100_GPU, timeout=20 * 60, scaledown_window=60)
def benchmark_h100(quick: bool = False) -> dict[str, Any]:
    return _benchmark(gpu_request=H100_GPU, quick=quick)


@app.function(gpu=A100_GPU, timeout=20 * 60, scaledown_window=60)
def benchmark_a100(quick: bool = False) -> dict[str, Any]:
    return _benchmark(gpu_request=A100_GPU, quick=quick)


@app.local_entrypoint()
def main(gpu: str = "h100", output: str = "", quick: bool = False) -> None:
    if gpu == "h100":
        remote_benchmark = benchmark_h100
        default_output = "results/h100-sxm.json"
    elif gpu == "a100":
        remote_benchmark = benchmark_a100
        default_output = "results/a100-80gb-pcie.json"
    else:
        raise ValueError("--gpu must be 'h100' or 'a100'")

    result = remote_benchmark.remote(quick=quick)
    output_path = Path(output or default_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Wrote {output_path}")
