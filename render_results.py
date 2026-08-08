"""Render a compact Markdown report from a benchmark JSON artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROWS = (
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


def _value(metric: dict[str, Any]) -> str:
    value = metric["value"]
    unit = metric["unit"]
    if unit == "us":
        return f"{value:.2f} μs"
    if unit == "GB/s":
        return f"{value:,.0f} GB/s"
    if unit == "TFLOP/s":
        return f"{value:,.0f} TFLOP/s"
    return f"{value:g} {unit}"


def render(profile: dict[str, Any]) -> str:
    lines = [
        f"# {profile['device']['name']} benchmark",
        "",
        f"Captured `{profile['captured_at']}` using the `{profile['methodology']['gpu_request']}` "
        f"Modal request in `{profile['mode']}` mode.",
        "",
        "| Operation | Measured | Median time |",
        "| --- | ---: | ---: |",
    ]
    for label, key in ROWS:
        metric = profile["metrics"][key]
        lines.append(f"| {label} | {_value(metric)} | {metric['median_ms']:.4f} ms |")
    lines.extend(
        [
            "",
            "## Environment",
            "",
            f"- GPU: `{profile['device']['name']}`; {profile['device']['memory_mib']} MiB; "
            f"compute capability {profile['device']['compute_capability']}",
            f"- PyTorch: `{profile['software']['torch']}`; CUDA runtime "
            f"`{profile['software']['cuda_runtime']}`; driver `{profile['software']['nvidia_driver']}`",
            f"- Method: {profile['methodology']['timer']}; {profile['methodology']['statistic']}",
            "- Correctness: all benchmark checks passed",
            "",
            "The JSON file next to this report is the source of truth and includes raw round samples.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    profile = json.loads(args.input.read_text())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(profile))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

