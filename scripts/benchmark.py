from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aegis.models import Pattern
from aegis.patterns import PatternEngine
from aegis.pose import MediaPipePoseEstimator
from aegis.runtime import SnapdragonSession, get_runtime_diagnostics


def run_benchmark(
    source: str | Path,
    warmup_frames: int = 100,
    measured_frames: int = 1000,
    prefer_qnn: bool = False,
    output_json: str | Path | None = None,
    output_markdown: str | Path | None = None,
) -> dict:
    """Execute reproducible pose estimation and pattern recognition benchmark."""
    source_path = Path(source)
    if not source_path.exists():
        print(f"Error: Benchmark video source not found: {source_path}", file=sys.stderr)
        sys.exit(1)

    runtime = SnapdragonSession(prefer_qnn=prefer_qnn)
    provider = runtime.initialize()
    diagnostics = get_runtime_diagnostics(prefer_qnn=prefer_qnn)

    estimator = MediaPipePoseEstimator()
    engine = PatternEngine()

    capture = cv2.VideoCapture(str(source_path))
    if not capture.isOpened():
        estimator.close()
        print(f"Error: Failed to open video file: {source_path}", file=sys.stderr)
        sys.exit(1)

    total_video_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_source = capture.get(cv2.CAP_PROP_FPS)

    print("=" * 68)
    print("AEGIS CORE // BENCHMARK PROTOCOL")
    print("=" * 68)
    print(f"Video Source:              {source_path.name} ({total_video_frames} frames @ {fps_source:.1f} FPS)")
    print(f"Active Inference Provider: {provider}")
    print(f"Warm-up Target:            {warmup_frames} frames")
    print(f"Measurement Target:        {measured_frames} frames")
    print(f"Qualcomm QNN Active:       {'Yes' if diagnostics.qnn_pose_active else 'No (MediaPipe CPU pipeline active)'}")
    print("-" * 68)

    # 1. Warm-up Phase
    print("Executing warm-up phase...")
    warmup_count = 0
    while warmup_count < warmup_frames:
        ret, frame = capture.read()
        if not ret:
            # Video loop or early stop
            break
        t0 = time.perf_counter()
        pose = estimator.estimate(frame, t0)
        if pose is not None:
            engine.update(pose)
        warmup_count += 1

    print(f"Warm-up completed ({warmup_count} frames). Starting measured execution...")

    # 2. Measurement Phase
    latencies_ms: list[float] = []
    pattern_counts: Counter[str] = Counter()
    measured_count = 0
    wall_start = time.perf_counter()

    while measured_count < measured_frames:
        ret, frame = capture.read()
        if not ret:
            break

        frame_start = time.perf_counter()
        pose = estimator.estimate(frame, frame_start)

        if pose is not None:
            detection = engine.update(pose)
            pattern_counts[detection.pattern.value] += 1
        else:
            pattern_counts["no_pose"] += 1

        frame_latency_ms = (time.perf_counter() - frame_start) * 1000.0
        latencies_ms.append(frame_latency_ms)
        measured_count += 1

    wall_duration = time.perf_counter() - wall_start
    capture.release()
    estimator.close()

    if not latencies_ms:
        print("Error: No frames were processed during measurement phase.", file=sys.stderr)
        sys.exit(1)

    latencies_arr = np.array(latencies_ms, dtype=np.float64)
    avg_fps = measured_count / wall_duration if wall_duration > 0 else 0.0
    median_latency = float(np.median(latencies_arr))
    p95_latency = float(np.percentile(latencies_arr, 95))
    p99_latency = float(np.percentile(latencies_arr, 99))
    min_latency = float(np.min(latencies_arr))
    max_latency = float(np.max(latencies_arr))
    mean_latency = float(np.mean(latencies_arr))

    results = {
        "timestamp": time.time(),
        "video_source": str(source_path.name),
        "environment": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "processor": platform.processor() or "Unknown",
        },
        "execution": {
            "active_inference_provider": provider,
            "qnn_available": diagnostics.qnn_available,
            "qnn_pose_active": diagnostics.qnn_pose_active,
            "is_truthful_cpu_baseline": (provider == "MediaPipe CPU"),
        },
        "frames": {
            "warmup_frames_executed": warmup_count,
            "measured_frames_executed": measured_count,
            "total_wall_time_seconds": round(wall_duration, 4),
        },
        "performance": {
            "average_fps": round(avg_fps, 2),
            "median_latency_ms": round(median_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
            "p99_latency_ms": round(p99_latency, 2),
            "mean_latency_ms": round(mean_latency, 2),
            "min_latency_ms": round(min_latency, 2),
            "max_latency_ms": round(max_latency, 2),
        },
        "detected_events": dict(pattern_counts),
        "notes": (
            "Measurements represent the functional MediaPipe CPU baseline. "
            "Snapdragon NPU / QNN comparisons must evaluate an identical video "
            "file and identical warmup/measurement frame counts."
        ),
    }

    print("=" * 68)
    print("AEGIS CORE // BENCHMARK RESULTS")
    print("=" * 68)
    print(f"Analysed Frames:           {measured_count}")
    print(f"Average FPS:               {avg_fps:.2f}")
    print(f"Median Latency:            {median_latency:.2f} ms")
    print(f"p95 Latency:               {p95_latency:.2f} ms")
    print(f"p99 Latency:               {p99_latency:.2f} ms")
    print(f"Active Provider:           {provider}")
    print(f"Event Counts:              {dict(pattern_counts)}")
    print("=" * 68)

    # Save JSON
    if output_json:
        out_json_path = Path(output_json)
        out_json_path.parent.mkdir(parents=True, exist_ok=True)
        with out_json_path.open("w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Machine-readable benchmark saved to: {out_json_path.resolve()}")

    # Save Markdown if requested
    if output_markdown:
        out_md_path = Path(output_markdown)
        out_md_path.parent.mkdir(parents=True, exist_ok=True)
        md_lines = [
            "# Aegis Core Benchmark Report",
            "",
            f"- **Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **Source Clip**: `{source_path.name}`",
            f"- **Active Provider**: `{provider}`",
            f"- **Analysed Frames**: {measured_count}",
            f"- **Average FPS**: {avg_fps:.2f}",
            f"- **Median Latency**: {median_latency:.2f} ms",
            f"- **p95 Latency**: {p95_latency:.2f} ms",
            f"- **p99 Latency**: {p99_latency:.2f} ms",
            "",
            "## Detected Events",
            "",
            "| Pattern | Count |",
            "| --- | --- |",
        ]
        for pattern_name, count in pattern_counts.items():
            md_lines.append(f"| `{pattern_name}` | {count} |")
        md_lines.append("")
        md_lines.append("## Notes")
        md_lines.append("")
        md_lines.append(results["notes"])
        with out_md_path.open("w", encoding="utf-8") as f:
            f.write("\n".join(md_lines) + "\n")
        print(f"Markdown benchmark report saved to: {out_md_path.resolve()}")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aegis Core Reproducible Benchmark & Evaluation Utility"
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Path to prerecorded benchmark video file",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=100,
        help="Number of warm-up frames before measurement (default: 100)",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=1000,
        help="Number of frames to measure (default: 1000)",
    )
    parser.add_argument(
        "--prefer-qnn",
        action="store_true",
        help="Attempt QNN provider selection (truthfully reports CPU if no QNN pose model)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to save output JSON benchmark results (e.g., artifacts/benchmark.json)",
    )
    parser.add_argument(
        "--markdown",
        default=None,
        help="Optional path to save a Markdown benchmark report",
    )

    args = parser.parse_args()

    run_benchmark(
        source=args.source,
        warmup_frames=args.warmup,
        measured_frames=args.frames,
        prefer_qnn=args.prefer_qnn,
        output_json=args.output,
        output_markdown=args.markdown,
    )


if __name__ == "__main__":
    main()
