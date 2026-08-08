import math
from pathlib import Path

import pytest

from gpu_napkin import estimate
from napkin_profile import (
    REQUIRED_METRICS,
    Profile,
    get_metric,
    load_profile,
    parse_profile,
    roofline_ceiling,
)
from render_results import render


PROFILE: Profile = {
    "schema_version": 2,
    "captured_at": "2026-08-08T00:00:00+00:00",
    "mode": "full",
    "host": {
        "cpu_model": "Test CPU",
        "logical_cpu_count": 16,
        "torch_threads": 8,
    },
    "device": {"name": "Test GPU", "memory_mib": 80, "compute_capability": "9.0"},
    "peer_devices": [
        {"name": "Test GPU", "memory_mib": 80, "compute_capability": "9.0"}
    ],
    "interconnect": {
        "source_device": 0,
        "destination_device": 1,
        "topology_label": "NV18",
        "peer_access": True,
        "nvidia_smi_p2p": "GPU0 GPU1\nGPU0 X OK\nGPU1 OK X",
        "nvidia_smi_nvlink": "GPU 0\nLink 0: 25 GB/s",
    },
    "software": {"torch": "x", "cuda_runtime": "y", "nvidia_driver": "z"},
    "methodology": {
        "gpu_request": "H100!",
        "timer": "CUDA events",
        "statistic": "median",
    },
    "checks": {
        "cpu_memory_copy": True,
        "tiny_kernel_finite": True,
        "hbm_copy": True,
        "elementwise_add": True,
        "host_device_round_trip": True,
        "gemm_fp16": True,
        "gemm_bf16": True,
        "gemm_tf32": True,
        "gemm_fp32": True,
        "gpu_to_gpu_0_to_1": True,
        "gpu_to_gpu_1_to_0": True,
    },
    "metrics": {
        "cpu_memory_copy": {"value": 100.0, "unit": "GB/s", "median_ms": 1.0},
        "tiny_kernel": {"value": 5.0, "unit": "us", "median_ms": 0.005},
        "hbm_copy": {"value": 2_000.0, "unit": "GB/s", "median_ms": 1.0},
        "host_to_device": {"value": 50.0, "unit": "GB/s", "median_ms": 1.0},
        "device_to_host": {"value": 40.0, "unit": "GB/s", "median_ms": 1.0},
        "elementwise_add": {"value": 1_500.0, "unit": "GB/s", "median_ms": 1.0},
        "gemm_fp16": {"value": 800.0, "unit": "TFLOP/s", "median_ms": 1.0},
        "gemm_bf16": {"value": 750.0, "unit": "TFLOP/s", "median_ms": 1.0},
        "gemm_tf32": {"value": 400.0, "unit": "TFLOP/s", "median_ms": 1.0},
        "gemm_fp32": {"value": 50.0, "unit": "TFLOP/s", "median_ms": 1.0},
        "gpu_to_gpu": {"value": 300.0, "unit": "GB/s", "median_ms": 1.0},
    },
}


def test_memory_bound_estimate_includes_transfer_and_launch() -> None:
    result = estimate(
        PROFILE,
        flops=8e12,
        device_bytes=200e9,
        host_memory_bytes=2e9,
        host_to_device_bytes=5e9,
        device_to_host_bytes=4e9,
        gpu_to_gpu_bytes=30e9,
        launches=10,
    )

    assert result.host_memory_ms == pytest.approx(20)
    assert result.compute_ms == pytest.approx(10)
    assert result.memory_ms == pytest.approx(100)
    assert result.transfer_ms == pytest.approx(200)
    assert result.interconnect_ms == pytest.approx(100)
    assert result.launch_ms == pytest.approx(0.05)
    assert result.total_ms == pytest.approx(420.05)
    assert result.bottleneck == "memory"
    assert result.arithmetic_intensity == pytest.approx(40)
    assert result.ridge_point_flops_per_byte == pytest.approx(400)


def test_roofline_ceiling_uses_measured_profile_values() -> None:
    ceiling = roofline_ceiling(PROFILE, "tf32")

    assert ceiling.compute_tflops == 400
    assert ceiling.memory_gbps == 2_000
    assert ceiling.ridge_point_flops_per_byte == pytest.approx(200)


def test_compute_only_intensity_is_infinite() -> None:
    result = estimate(PROFILE, flops=8e12, device_bytes=0)
    assert math.isinf(result.arithmetic_intensity)
    assert result.bottleneck == "compute"


def test_negative_work_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        estimate(PROFILE, flops=-1, device_bytes=0)


def test_parse_profile_rejects_wrong_schema_version() -> None:
    bad = {**PROFILE, "schema_version": 0}
    with pytest.raises(ValueError, match="schema_version"):
        parse_profile(bad)


def test_parse_profile_rejects_missing_metric() -> None:
    metrics = dict(PROFILE["metrics"])
    del metrics["hbm_copy"]
    bad = {**PROFILE, "metrics": metrics}
    with pytest.raises(ValueError, match="missing metrics"):
        parse_profile(bad)


@pytest.mark.parametrize(
    ("profile_path", "gpu_request", "device_name"),
    [
        (Path("results/h100-sxm.json"), "H100!:2", "NVIDIA H100 80GB HBM3"),
        (Path("results/a100-80gb-sxm4.json"), "A100-80GB:2", "NVIDIA A100-SXM4-80GB"),
    ],
)
def test_checked_in_profile_is_complete(
    profile_path: Path, gpu_request: str, device_name: str
) -> None:
    profile = load_profile(profile_path)
    assert profile["mode"] == "full"
    assert profile["methodology"]["gpu_request"] == gpu_request
    assert profile["device"]["name"] == device_name
    assert profile["checks"] is not None and all(profile["checks"].values())
    assert set(REQUIRED_METRICS).issubset(profile["metrics"])
    assert all(get_metric(profile, name)["value"] > 0 for name in REQUIRED_METRICS)


def test_markdown_renderer_contains_every_metric() -> None:
    report = render(PROFILE)
    assert "Test GPU system-path benchmark" in report
    assert "Pinned CPU RAM copy" in report
    assert "GPU 0 ↔ GPU 1 interconnect" in report
    assert "800 TFLOP/s" in report
    assert "1K launches → 5 ms" in report
    assert "1M launches → 5 s" in report
    assert "1 GB → 20 ms" in report
    assert "1 TB → 20 s" in report
    assert "1 TFLOP → 1.25 ms" in report
    assert "1 PFLOP → 1.25 s" in report
    assert "## Roofline ridge points" in report
    assert "| fp16 | 800 TFLOP/s | 400.0 FLOP/byte |" in report
    assert "all benchmark checks passed" in report
    assert "GPU 0 ↔ GPU 1 is `NV18`" in report
