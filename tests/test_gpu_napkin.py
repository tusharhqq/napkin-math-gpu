import json
import math
from pathlib import Path

import pytest

from gpu_napkin import estimate
from render_results import render


PROFILE = {
    "captured_at": "2026-08-08T00:00:00+00:00",
    "mode": "full",
    "device": {"name": "Test GPU", "memory_mib": 80, "compute_capability": "9.0"},
    "software": {"torch": "x", "cuda_runtime": "y", "nvidia_driver": "z"},
    "methodology": {
        "gpu_request": "H100!",
        "timer": "CUDA events",
        "statistic": "median",
    },
    "metrics": {
        "tiny_kernel": {"value": 5.0, "unit": "us", "median_ms": 0.005},
        "hbm_copy": {"value": 2_000.0, "unit": "GB/s", "median_ms": 1.0},
        "host_to_device": {"value": 50.0, "unit": "GB/s", "median_ms": 1.0},
        "device_to_host": {"value": 40.0, "unit": "GB/s", "median_ms": 1.0},
        "elementwise_add": {"value": 1_500.0, "unit": "GB/s", "median_ms": 1.0},
        "gemm_fp16": {"value": 800.0, "unit": "TFLOP/s", "median_ms": 1.0},
        "gemm_bf16": {"value": 750.0, "unit": "TFLOP/s", "median_ms": 1.0},
        "gemm_tf32": {"value": 400.0, "unit": "TFLOP/s", "median_ms": 1.0},
        "gemm_fp32": {"value": 50.0, "unit": "TFLOP/s", "median_ms": 1.0},
    },
}


def test_memory_bound_estimate_includes_transfer_and_launch() -> None:
    result = estimate(
        PROFILE,
        flops=8e12,
        device_bytes=200e9,
        host_to_device_bytes=5e9,
        device_to_host_bytes=4e9,
        launches=10,
    )

    assert result.compute_ms == pytest.approx(10)
    assert result.memory_ms == pytest.approx(100)
    assert result.transfer_ms == pytest.approx(200)
    assert result.launch_ms == pytest.approx(0.05)
    assert result.total_ms == pytest.approx(300.05)
    assert result.bottleneck == "memory"
    assert result.arithmetic_intensity == pytest.approx(40)


def test_compute_only_intensity_is_infinite() -> None:
    result = estimate(PROFILE, flops=8e12, device_bytes=0)
    assert math.isinf(result.arithmetic_intensity)
    assert result.bottleneck == "compute"


def test_negative_work_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        estimate(PROFILE, flops=-1, device_bytes=0)


@pytest.mark.parametrize(
    ("profile_path", "gpu_request", "device_name"),
    [
        (Path("results/h100-sxm.json"), "H100!", "NVIDIA H100 80GB HBM3"),
        (Path("results/a100-80gb-pcie.json"), "A100-80GB", "NVIDIA A100 80GB PCIe"),
    ],
)
def test_checked_in_profile_is_complete(
    profile_path: Path, gpu_request: str, device_name: str
) -> None:
    profile = json.loads(profile_path.read_text())
    assert profile["mode"] == "full"
    assert profile["methodology"]["gpu_request"] == gpu_request
    assert profile["device"]["name"] == device_name
    assert all(profile["checks"].values())
    assert set(PROFILE["metrics"]).issubset(profile["metrics"])
    assert all(metric["value"] > 0 for metric in profile["metrics"].values())


def test_markdown_renderer_contains_every_metric() -> None:
    report = render(PROFILE)
    assert "Test GPU benchmark" in report
    assert "800 TFLOP/s" in report
    assert "1K launches → 5 ms" in report
    assert "1M launches → 5 s" in report
    assert "1 GB → 20 ms" in report
    assert "1 TB → 20 s" in report
    assert "1 TFLOP → 1.25 ms" in report
    assert "1 PFLOP → 1.25 s" in report
    assert "all benchmark checks passed" in report
