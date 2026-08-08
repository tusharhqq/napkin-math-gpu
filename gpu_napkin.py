"""Estimate GPU latency from measured bandwidth and compute ceilings."""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPOSITORY_PROFILE = Path(__file__).parent / "results" / "h100-sxm.json"
INSTALLED_PROFILE = Path(sys.prefix) / "share" / "gpu-napkin-math" / "h100-sxm.json"
DEFAULT_PROFILE = REPOSITORY_PROFILE if REPOSITORY_PROFILE.exists() else INSTALLED_PROFILE


@dataclass(frozen=True)
class Estimate:
    compute_ms: float
    memory_ms: float
    transfer_ms: float
    launch_ms: float
    device_ms: float
    total_ms: float
    bottleneck: str
    arithmetic_intensity: float


def _metric(profile: dict[str, Any], name: str) -> dict[str, Any]:
    metrics = profile["metrics"]
    if name not in metrics:
        raise ValueError(f"profile does not contain metric {name!r}")
    return metrics[name]


def estimate(
    profile: dict[str, Any],
    *,
    flops: float,
    device_bytes: float,
    dtype: str = "fp16",
    host_to_device_bytes: float = 0.0,
    device_to_host_bytes: float = 0.0,
    launches: int = 1,
) -> Estimate:
    """Roofline lower bound: max(compute, memory), plus transfers and launches."""

    if (
        flops < 0
        or device_bytes < 0
        or host_to_device_bytes < 0
        or device_to_host_bytes < 0
        or launches < 0
    ):
        raise ValueError("work quantities must be non-negative")

    compute_metric = _metric(profile, f"gemm_{dtype}")
    memory_metric = _metric(profile, "hbm_copy")
    launch_metric = _metric(profile, "tiny_kernel")

    compute_ms = flops / (compute_metric["value"] * 1e12) * 1e3
    memory_ms = device_bytes / (memory_metric["value"] * 1e9) * 1e3

    transfer_ms = 0.0
    if host_to_device_bytes:
        h2d = _metric(profile, "host_to_device")["value"] * 1e9
        transfer_ms += host_to_device_bytes / h2d * 1e3
    if device_to_host_bytes:
        d2h = _metric(profile, "device_to_host")["value"] * 1e9
        transfer_ms += device_to_host_bytes / d2h * 1e3

    launch_ms = launches * launch_metric["value"] / 1e3
    device_ms = max(compute_ms, memory_ms)
    total_ms = device_ms + transfer_ms + launch_ms

    if compute_ms > memory_ms:
        bottleneck = "compute"
    elif memory_ms > compute_ms:
        bottleneck = "memory"
    else:
        bottleneck = "balanced"

    if device_bytes == 0:
        intensity = math.inf if flops else 0.0
    else:
        intensity = flops / device_bytes
    return Estimate(
        compute_ms=compute_ms,
        memory_ms=memory_ms,
        transfer_ms=transfer_ms,
        launch_ms=launch_ms,
        device_ms=device_ms,
        total_ms=total_ms,
        bottleneck=bottleneck,
        arithmetic_intensity=intensity,
    )


def _positive_number(value: str) -> float:
    number = float(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Estimate a GPU workload from a measured napkin-math profile."
    )
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--flops", type=_positive_number, required=True)
    parser.add_argument("--bytes", dest="device_bytes", type=_positive_number, required=True)
    parser.add_argument("--dtype", choices=("fp16", "bf16", "tf32", "fp32"), default="fp16")
    parser.add_argument("--h2d-bytes", type=_positive_number, default=0.0)
    parser.add_argument("--d2h-bytes", type=_positive_number, default=0.0)
    parser.add_argument("--launches", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.launches < 0:
        raise SystemExit("--launches must be non-negative")
    profile = json.loads(args.profile.read_text())
    result = estimate(
        profile,
        flops=args.flops,
        device_bytes=args.device_bytes,
        dtype=args.dtype,
        host_to_device_bytes=args.h2d_bytes,
        device_to_host_bytes=args.d2h_bytes,
        launches=args.launches,
    )

    intensity = (
        "infinite"
        if math.isinf(result.arithmetic_intensity)
        else f"{result.arithmetic_intensity:.2f}"
    )
    print(f"GPU:              {profile['device']['name']}")
    print(f"Arithmetic intensity: {intensity} FLOP/byte")
    print(f"Compute floor:    {result.compute_ms:.3f} ms")
    print(f"Memory floor:     {result.memory_ms:.3f} ms")
    print(f"Device estimate:  {result.device_ms:.3f} ms ({result.bottleneck}-bound)")
    print(f"Transfer:         {result.transfer_ms:.3f} ms")
    print(f"Launches:         {result.launch_ms:.3f} ms")
    print(f"Total estimate:   {result.total_ms:.3f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
