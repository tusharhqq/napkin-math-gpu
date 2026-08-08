"""Render a compact Markdown report from a benchmark JSON artifact."""

from __future__ import annotations

import argparse
from pathlib import Path

from napkin_profile import (
    GEMM_DTYPES,
    METRIC_ROWS,
    Metric,
    Profile,
    get_metric,
    load_profile,
    roofline_ceiling,
)


def _value(metric: Metric) -> str:
    value = metric["value"]
    unit = metric["unit"]
    if unit == "us":
        return f"{value:.2f} μs"
    if unit == "GB/s":
        return f"{value:,.0f} GB/s"
    if unit == "TFLOP/s":
        return f"{value:,.0f} TFLOP/s"
    return f"{value:g} {unit}"


def _duration(seconds: float) -> str:
    if seconds < 1e-6:
        return f"{seconds * 1e9:.3g} ns"
    if seconds < 1e-3:
        return f"{seconds * 1e6:.3g} μs"
    if seconds < 1:
        return f"{seconds * 1e3:.3g} ms"
    return f"{seconds:.3g} s"


def _work_examples(metric: Metric) -> tuple[str, str]:
    value = metric["value"]
    unit = metric["unit"]
    if unit == "us":
        seconds_per_launch = value / 1e6
        return (
            f"1K launches → {_duration(1_000 * seconds_per_launch)}",
            f"1M launches → {_duration(1_000_000 * seconds_per_launch)}",
        )
    if unit == "GB/s":
        return (
            f"1 GB → {_duration(1 / value)}",
            f"1 TB → {_duration(1_000 / value)}",
        )
    if unit == "TFLOP/s":
        return (
            f"1 TFLOP → {_duration(1 / value)}",
            f"1 PFLOP → {_duration(1_000 / value)}",
        )
    return ("—", "—")


def render(profile: Profile) -> str:
    lines = [
        f"# {profile['device']['name']} system-path benchmark",
        "",
        (
            f"Captured `{profile['captured_at']}` using the `{profile['methodology']['gpu_request']}` "
            + f"Modal request in `{profile['mode']}` mode."
        ),
        "",
        "| Operation | Measured | Median benchmark time | Small job | Large job |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for label, key in METRIC_ROWS:
        metric = get_metric(profile, key)
        small_job, large_job = _work_examples(metric)
        lines.append(
            f"| {label} | {_value(metric)} | {metric['median_ms']:.4f} ms | "
            + f"{small_job} | {large_job} |"
        )
    lines.extend(
        [
            "",
            "## Roofline ridge points",
            "",
            (
                "The ridge point is `compute ceiling ÷ HBM bandwidth`. A workload below it is "
                + "memory-bound in this model; above it, compute-bound."
            ),
            "",
            "| Precision | Measured compute ceiling | Ridge point |",
            "| --- | ---: | ---: |",
        ]
    )
    for dtype in GEMM_DTYPES:
        ceiling = roofline_ceiling(profile, dtype)
        lines.append(
            f"| {dtype} | {ceiling.compute_tflops:,.0f} TFLOP/s | "
            + f"{ceiling.ridge_point_flops_per_byte:,.1f} FLOP/byte |"
        )
    lines.extend(
        [
            "",
            "## Environment",
            "",
            (
                f"- CPU: `{profile['host']['cpu_model']}`; "
                + f"{profile['host']['torch_threads']} PyTorch copy threads"
            ),
            (
                f"- GPU: `{profile['device']['name']}`; {profile['device']['memory_mib']} MiB; "
                + f"compute capability {profile['device']['compute_capability']}; "
                + f"{1 + len(profile['peer_devices'])} devices"
            ),
            (
                "- GPU interconnect: GPU 0 ↔ GPU 1 is "
                + f"`{profile['interconnect']['topology_label']}`; direct peer access passed"
            ),
            (
                f"- PyTorch: `{profile['software']['torch']}`; CUDA runtime "
                + f"`{profile['software']['cuda_runtime']}`; "
                + f"driver `{profile['software']['nvidia_driver']}`"
            ),
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
    profile = load_profile(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(profile))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
