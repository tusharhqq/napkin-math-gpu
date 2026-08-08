"""Run the prototype calibration harness on pinned Modal GPUs.

Published evidence should come from the authoritative tools mapped in
BENCHMARKS.md. Keep this producer for calibration and cross-checking; do not grow
it into a replacement for NVIDIA datasheets, NVBandwidth, NCCL Tests, Nsight
Compute, cuBLAS/cuBLASLt, or MLPerf.

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

from napkin_profile import SCHEMA_VERSION, DeviceInfo, Metric, Metrics, Profile, make_metric

TORCH_VERSION = "2.8.0"
NUMPY_VERSION = "2.2.6"


class GpuTarget(NamedTuple):
    key: str
    modal_request: str
    default_output: str


# One row per supported GPU. Full calibration runs use two same-host GPUs so the
# prototype profile covers CPU RAM → PCIe → HBM → compute → interconnect.
# Modal needs a decorate-time gpu= string, so wrappers are generated here.
GPU_TARGETS: tuple[GpuTarget, ...] = (
    GpuTarget("h100", "H100!:2", "results/h100-sxm.json"),
    GpuTarget("a100", "A100-80GB:2", "results/a100-80gb-sxm4.json"),
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
    import os
    import platform
    import re
    import statistics
    import subprocess
    import time
    from datetime import UTC, datetime

    import numpy as np
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available")

    torch.manual_seed(20260808)
    torch.cuda.manual_seed_all(20260808)
    if torch.cuda.device_count() != 2:
        raise RuntimeError(f"expected exactly 2 GPUs, found {torch.cuda.device_count()}")

    device = torch.device("cuda:0")
    peer_device = torch.device("cuda:1")

    def cuda_samples(
        fn,
        *,
        warmups: int,
        iterations: int,
        rounds: int,
        timing_device: torch.device = device,
    ) -> list[float]:
        with torch.cuda.device(timing_device):
            for _ in range(warmups):
                fn()
            torch.cuda.synchronize(timing_device)

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

    def wall_samples(fn, *, warmups: int, iterations: int, rounds: int) -> list[float]:
        for _ in range(warmups):
            fn()

        samples = []
        for _ in range(rounds):
            started_ns = time.perf_counter_ns()
            for _ in range(iterations):
                fn()
            elapsed_ms = (time.perf_counter_ns() - started_ns) / 1e6
            samples.append(elapsed_ms / iterations)
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

    # Pinned CPU RAM copy models preparation/staging before the PCIe transfer.
    cpu_threads = min(8, os.cpu_count() or 1)
    torch.set_num_threads(cpu_threads)
    cpu_memory_mib = 64 if quick else 512
    cpu_memory_elements = cpu_memory_mib * 1024 * 1024 // 4
    cpu_memory_src = torch.arange(cpu_memory_elements, dtype=torch.float32, pin_memory=True)
    cpu_memory_dst = torch.empty(cpu_memory_elements, dtype=torch.float32, pin_memory=True)
    cpu_memory_samples = wall_samples(
        lambda: cpu_memory_dst.copy_(cpu_memory_src),
        warmups=5,
        iterations=5 if quick else 20,
        rounds=rounds,
    )
    record_bandwidth(
        "cpu_memory_copy",
        samples_ms=cpu_memory_samples,
        bytes_counted=cpu_memory_src.numel() * cpu_memory_src.element_size() * 2,
        allocation_mib=cpu_memory_mib,
        threads=cpu_threads,
        convention="pinned source read plus pinned destination write",
    )
    cpu_memory_indices = probe_indices(cpu_memory_elements)
    checks["cpu_memory_copy"] = torch.equal(
        cpu_memory_src[cpu_memory_indices], cpu_memory_dst[cpu_memory_indices]
    )

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

    # Direct peer copies cover the GPU interconnect in both directions. The
    # published metric is the slower direction, which is conservative for
    # napkin estimates; both directional values remain in the raw profile.
    peer_access = torch.cuda.can_device_access_peer(0, 1)
    if not peer_access:
        raise RuntimeError("GPU 0 and GPU 1 do not support direct peer access")
    peer_mib = 64 if quick else 512
    peer_elements = peer_mib * 1024 * 1024 // 4
    peer_bytes = peer_elements * 4
    peer_src_0 = torch.arange(peer_elements, dtype=torch.float32, device=device)
    peer_dst_1 = torch.empty(peer_elements, dtype=torch.float32, device=peer_device)
    peer_src_1 = torch.arange(peer_elements, dtype=torch.float32, device=peer_device)
    peer_dst_0 = torch.empty(peer_elements, dtype=torch.float32, device=device)
    peer_iterations = 5 if quick else 20
    peer_01_samples = cuda_samples(
        lambda: peer_dst_1.copy_(peer_src_0, non_blocking=True),
        warmups=5,
        iterations=peer_iterations,
        rounds=rounds,
        timing_device=peer_device,
    )
    peer_10_samples = cuda_samples(
        lambda: peer_dst_0.copy_(peer_src_1, non_blocking=True),
        warmups=5,
        iterations=peer_iterations,
        rounds=rounds,
        timing_device=device,
    )
    peer_01_gbps = peer_bytes / (statistics.median(peer_01_samples) / 1e3) / 1e9
    peer_10_gbps = peer_bytes / (statistics.median(peer_10_samples) / 1e3) / 1e9
    slower_samples = peer_01_samples if peer_01_gbps <= peer_10_gbps else peer_10_samples
    metrics["gpu_to_gpu"] = make_metric(
        slower_samples,
        value=min(peer_01_gbps, peer_10_gbps),
        unit="GB/s",
        bytes_counted=peer_bytes,
        allocation_mib=peer_mib,
        convention="one-way direct peer copy; slower of the two directions",
        source_device=0,
        destination_device=1,
        forward_gbps=peer_01_gbps,
        reverse_gbps=peer_10_gbps,
    )
    peer_indices_0 = probe_indices(peer_elements, on_device=True)
    peer_indices_1 = torch.tensor([0, peer_elements // 2, peer_elements - 1], device=peer_device)
    checks["gpu_to_gpu_0_to_1"] = torch.equal(
        peer_src_0[peer_indices_0].cpu(), peer_dst_1[peer_indices_1].cpu()
    )
    checks["gpu_to_gpu_1_to_0"] = torch.equal(
        peer_src_1[peer_indices_1].cpu(), peer_dst_0[peer_indices_0].cpu()
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
            lambda a=a, b=b, out=out: torch.mm(a, b, out=out),
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
    device_rows: list[DeviceInfo] = []
    for row in query.splitlines():
        smi_name, uuid, memory_mib, pci_bus_id, _driver, power_limit_w = [
            item.strip() for item in row.split(",")
        ]
        device_index = len(device_rows)
        device_props = torch.cuda.get_device_properties(device_index)
        device_rows.append(
            {
                "name": smi_name,
                "uuid": uuid,
                "memory_mib": int(memory_mib),
                "pci_bus_id": pci_bus_id,
                "power_limit_w": float(power_limit_w),
                "compute_capability": f"{device_props.major}.{device_props.minor}",
                "multiprocessor_count": device_props.multi_processor_count,
            }
        )

    p2p_topology = subprocess.run(
        ["nvidia-smi", "topo", "-p2p", "r"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    p2p_topology = re.sub(r"\x1b\[[0-9;]*m", "", p2p_topology)
    topology_lines = [line.split() for line in p2p_topology.splitlines() if line.strip()]
    header = next(tokens for tokens in topology_lines if tokens[:2] == ["GPU0", "GPU1"])
    gpu1_column = header.index("GPU1")
    gpu0_row = next(tokens for tokens in topology_lines if tokens[0] == "GPU0" and tokens != header)
    p2p_status = gpu0_row[gpu1_column + 1]
    if p2p_status != "OK":
        raise RuntimeError(f"nvidia-smi reports GPU 0 → GPU 1 P2P status {p2p_status!r}")

    nvlink_status = subprocess.run(
        ["nvidia-smi", "nvlink", "--status"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    gpu0_nvlink_block = nvlink_status.split("GPU 1:", 1)[0]
    nvlink_speeds = [
        float(line.split(":", 1)[1].split()[0])
        for line in gpu0_nvlink_block.splitlines()
        if line.strip().startswith("Link ")
    ]
    if not nvlink_speeds or len(set(nvlink_speeds)) != 1:
        raise RuntimeError("could not derive a uniform active NVLink topology")
    topology_label = f"{len(nvlink_speeds)} × NVLink ({nvlink_speeds[0]:g} GB/s/link)"

    cpu_model = "Modal CPU allocation (model not exposed)"
    for line in Path("/proc/cpuinfo").read_text().splitlines():
        if line.startswith("model name"):
            exposed_model = line.split(":", 1)[1].strip()
            if exposed_model.lower() != "unknown":
                cpu_model = exposed_model
            break

    if not all(checks.values()):
        failures = [name for name, passed in checks.items() if not passed]
        raise AssertionError(f"correctness checks failed: {failures}")

    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at": datetime.now(UTC).isoformat(),
        "mode": "quick" if quick else "full",
        "host": {
            "cpu_model": cpu_model,
            "logical_cpu_count": os.cpu_count() or 1,
            "torch_threads": cpu_threads,
        },
        "device": device_rows[0],
        "peer_devices": device_rows[1:],
        "interconnect": {
            "source_device": 0,
            "destination_device": 1,
            "topology_label": topology_label,
            "peer_access": peer_access,
            "nvidia_smi_p2p": p2p_topology,
            "nvidia_smi_nvlink": nvlink_status,
        },
        "software": {
            "python": platform.python_version(),
            "torch": str(torch.__version__),
            "cuda_runtime": str(torch.version.cuda),
            "nvidia_driver": query.splitlines()[0].split(",")[4].strip(),
            "cudnn": str(torch.backends.cudnn.version()),
        },
        "methodology": {
            "timer": "perf_counter for CPU RAM; CUDA events for GPU operations",
            "statistic": f"median of {rounds} rounds after per-operation warmup",
            "allocation_units": "MiB (2^20 bytes)",
            "throughput_units": "GB/s (10^9 bytes/s) and TFLOP/s (10^12 FLOP/s)",
            "gpu_request": gpu_request,
            "seed": 20260808,
        },
        "checks": checks,
        "metrics": cast(Metrics, metrics),
    }


@app.function(
    gpu=GPU_BY_KEY["h100"].modal_request,
    cpu=8.0,
    memory=8192,
    timeout=20 * 60,
    scaledown_window=60,
    name="benchmark_h100",
)
def benchmark_h100(quick: bool = False) -> Profile:
    return _benchmark(gpu_request=GPU_BY_KEY["h100"].modal_request, quick=quick)


@app.function(
    gpu=GPU_BY_KEY["a100"].modal_request,
    cpu=8.0,
    memory=8192,
    timeout=20 * 60,
    scaledown_window=60,
    name="benchmark_a100",
)
def benchmark_a100(quick: bool = False) -> Profile:
    return _benchmark(gpu_request=GPU_BY_KEY["a100"].modal_request, quick=quick)


REMOTE_BENCHMARKS = {
    "h100": benchmark_h100,
    "a100": benchmark_a100,
}


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
