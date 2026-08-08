"""Shared typed contract for measured GPU napkin-math profiles."""

from __future__ import annotations

import json
import statistics
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NotRequired, TypedDict, cast


SCHEMA_VERSION = 1

MetricUnit = Literal["us", "GB/s", "TFLOP/s"]
ProfileMode = Literal["quick", "full"]
GemmDtype = Literal["fp16", "bf16", "tf32", "fp32"]
GEMM_DTYPES: tuple[GemmDtype, ...] = ("fp16", "bf16", "tf32", "fp32")

REQUIRED_METRICS: tuple[str, ...] = (
    "tiny_kernel",
    "host_to_device",
    "device_to_host",
    "hbm_copy",
    "elementwise_add",
    "gemm_fp16",
    "gemm_bf16",
    "gemm_tf32",
    "gemm_fp32",
)

METRIC_ROWS: tuple[tuple[str, str], ...] = (
    ("Tiny elementwise kernel", "tiny_kernel"),
    ("Pinned host → device", "host_to_device"),
    ("Device → pinned host", "device_to_host"),
    ("HBM copy (read + write)", "hbm_copy"),
    ("Elementwise fp32 add (2 reads + write)", "elementwise_add"),
    ("fp16 matrix multiply", "gemm_fp16"),
    ("bf16 matrix multiply", "gemm_bf16"),
    ("tf32 matrix multiply", "gemm_tf32"),
    ("fp32 matrix multiply (TF32 disabled)", "gemm_fp32"),
)


class Metric(TypedDict):
    value: float
    unit: MetricUnit
    median_ms: float
    samples_ms: NotRequired[list[float]]
    operation: NotRequired[str]
    allocation_mib: NotRequired[int]
    bytes_counted: NotRequired[int]
    convention: NotRequired[str]
    direction: NotRequired[str]
    elements: NotRequired[int]
    shape: NotRequired[list[int]]
    flops: NotRequired[int]
    input_dtype: NotRequired[str]
    allow_tf32: NotRequired[bool]


class Metrics(TypedDict):
    tiny_kernel: Metric
    host_to_device: Metric
    device_to_host: Metric
    hbm_copy: Metric
    elementwise_add: Metric
    gemm_fp16: Metric
    gemm_bf16: Metric
    gemm_tf32: Metric
    gemm_fp32: Metric


class DeviceInfo(TypedDict):
    name: str
    memory_mib: int
    compute_capability: str
    uuid: NotRequired[str]
    pci_bus_id: NotRequired[str]
    power_limit_w: NotRequired[float]
    multiprocessor_count: NotRequired[int]


class SoftwareInfo(TypedDict):
    torch: str
    cuda_runtime: str
    nvidia_driver: str
    python: NotRequired[str]
    cudnn: NotRequired[str]


class MethodologyInfo(TypedDict):
    timer: str
    statistic: str
    gpu_request: str
    allocation_units: NotRequired[str]
    throughput_units: NotRequired[str]
    seed: NotRequired[int]


class Profile(TypedDict):
    schema_version: int
    captured_at: str
    mode: ProfileMode
    device: DeviceInfo
    software: SoftwareInfo
    methodology: MethodologyInfo
    metrics: Metrics
    checks: NotRequired[dict[str, bool]]


@dataclass(frozen=True)
class RooflineCeiling:
    """Measured compute/HBM ceilings and their arithmetic-intensity crossover."""

    dtype: GemmDtype
    compute_tflops: float
    memory_gbps: float
    ridge_point_flops_per_byte: float


def make_metric(
    samples_ms: list[float],
    *,
    value: float,
    unit: MetricUnit,
    **details: object,
) -> Metric:
    payload: dict[str, object] = {
        "value": value,
        "unit": unit,
        "median_ms": statistics.median(samples_ms),
        "samples_ms": samples_ms,
        **details,
    }
    return cast(Metric, payload)


def get_metric(profile: Profile, name: str) -> Metric:
    metrics: Mapping[str, Metric] = cast(Mapping[str, Metric], profile["metrics"])
    try:
        return metrics[name]
    except KeyError as exc:
        raise ValueError(f"profile does not contain metric {name!r}") from exc


def roofline_ceiling(profile: Profile, dtype: GemmDtype) -> RooflineCeiling:
    """Return measured roofline ceilings and the ridge point for one precision."""

    compute_tflops = get_metric(profile, f"gemm_{dtype}")["value"]
    memory_gbps = get_metric(profile, "hbm_copy")["value"]
    if compute_tflops <= 0 or memory_gbps <= 0:
        raise ValueError("roofline metrics must be positive")
    return RooflineCeiling(
        dtype=dtype,
        compute_tflops=compute_tflops,
        memory_gbps=memory_gbps,
        ridge_point_flops_per_byte=compute_tflops * 1_000 / memory_gbps,
    )


def parse_profile(data: object) -> Profile:
    if not isinstance(data, dict):
        raise TypeError("profile must be a JSON object")
    payload = cast(dict[str, object], data)

    version = payload.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version {version!r}; expected {SCHEMA_VERSION}")

    for key in ("captured_at", "mode", "device", "software", "methodology", "metrics"):
        if key not in payload:
            raise ValueError(f"profile missing {key!r}")

    raw_metrics = payload["metrics"]
    if not isinstance(raw_metrics, dict):
        raise TypeError("profile.metrics must be an object")
    metrics = cast(dict[str, object], raw_metrics)

    missing = [name for name in REQUIRED_METRICS if name not in metrics]
    if missing:
        raise ValueError(f"profile missing metrics: {missing}")

    for name in REQUIRED_METRICS:
        metric = metrics[name]
        if not isinstance(metric, dict):
            raise TypeError(f"metric {name!r} must be an object")
        for field in ("value", "unit", "median_ms"):
            if field not in metric:
                raise ValueError(f"metric {name!r} missing {field!r}")

    return cast(Profile, payload)


def load_profile(path: Path) -> Profile:
    return parse_profile(json.loads(path.read_text()))
