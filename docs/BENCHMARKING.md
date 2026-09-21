# Aegis Core Benchmarking & Evaluation Protocol

This document outlines the standardized, reproducible benchmarking protocol for Aegis. It establishes rigorous guidelines for comparing the current **MediaPipe CPU** baseline against future **Qualcomm QNN / Snapdragon NPU** acceleration on Snapdragon-powered HP PCs.

---

## 1. Principles of Honest Evaluation

1. **Zero Fabrication**: Benchmark metrics (FPS, median latency, p95 latency, power draw) must never be estimated, simulated, or fabricated. Every reported number must originate from verified execution logs.
2. **Provider Transparency**: The benchmark tool explicitly reports the execution provider actually generating pose landmarks (`MediaPipe CPU` in the current MVP). It will never claim QNN execution unless a verified QNN pose estimator is active.
3. **Controlled Comparison**: Any comparative evaluation between CPU and QNN/NPU must use:
   - The identical video source file and resolution (e.g., 1080p @ 30 FPS).
   - Identical warm-up frames (default: 100 frames).
   - Identical measured frames (default: 1,000 frames).
   - Identical pattern recognition thresholds.
   - Identical hardware device and Windows power profile (e.g., "Best Performance").

---

## 2. Benchmark CLI Tool

Aegis includes a dedicated benchmarking tool at [`scripts/benchmark.py`](../scripts/benchmark.py).

### Usage

```bash
# Basic benchmark execution against a recorded video clip
python scripts/benchmark.py --source path/to/eval_clip.mp4 --warmup 100 --frames 1000 --output artifacts/benchmark.json

# Generate a Markdown summary alongside JSON
python scripts/benchmark.py --source path/to/eval_clip.mp4 --warmup 100 --frames 1000 --output artifacts/benchmark.json --markdown artifacts/benchmark.md
```

### CLI Arguments

| Argument | Type | Default | Description |
| --- | --- | --- | --- |
| `--source` | Path | *Required* | Path to input evaluation video file (`.mp4`, `.avi`, `.mov`). |
| `--warmup` | Integer | `100` | Number of initial frames to process and discard to eliminate warm-up and cache jitter. |
| `--frames` | Integer | `1000` | Number of sequential frames to measure for latency and throughput. |
| `--prefer-qnn` | Flag | `False` | Attempt QNN execution provider selection. Reports CPU truthfully if no QNN pose model is loaded. |
| `--output` | Path | `None` | Path to save structured machine-readable JSON results. |
| `--markdown` | Path | `None` | Path to save a human-readable Markdown evaluation report. |

---

## 3. Metrics Collected

The benchmark utility captures:

- **Analysed Frames**: Exact count of measured frames executed.
- **Average FPS**: End-to-end throughput calculated as $\frac{\text{Frames}}{\text{Total Wall Time}}$.
- **Latency Percentiles**:
  - Minimum latency ($ms$)
  - Mean latency ($ms$)
  - Median ($p50$) latency ($ms$)
  - 95th percentile ($p95$) latency ($ms$)
  - 99th percentile ($p99$) latency ($ms$)
  - Maximum latency ($ms$)
- **Active Inference Provider**: Verifies whether landmarks were produced by CPU or QNN.
- **Detected Event Distribution**: Tallies occurrences of `neutral`, `guard`, `punch-like extension`, `kick-like extension`, `rapid approach`, and `fall-like posture`.
- **System Telemetry**: Operating system version, Python runtime, and host processor.

---

## 4. Benchmark JSON Schema

Outputs saved via `--output` adhere to the following schema:

```json
{
  "timestamp": 1758416400.0,
  "video_source": "eval_combat_1080p.mp4",
  "environment": {
    "platform": "Windows-11-10.0.26100-SP0",
    "python_version": "3.11.9",
    "processor": "Snapdragon(R) X Elite - X1E78100 - Qualcomm(R) Oryon(TM) CPU"
  },
  "execution": {
    "active_inference_provider": "MediaPipe CPU",
    "qnn_available": false,
    "qnn_pose_active": false,
    "is_truthful_cpu_baseline": true
  },
  "frames": {
    "warmup_frames_executed": 100,
    "measured_frames_executed": 1000,
    "total_wall_time_seconds": 33.24
  },
  "performance": {
    "average_fps": 30.08,
    "median_latency_ms": 28.45,
    "p95_latency_ms": 34.12,
    "p99_latency_ms": 38.60,
    "mean_latency_ms": 29.10,
    "min_latency_ms": 22.30,
    "max_latency_ms": 45.20
  },
  "detected_events": {
    "neutral": 650,
    "guard": 180,
    "punch-like extension": 95,
    "kick-like extension": 45,
    "rapid approach": 20,
    "fall-like posture": 10
  },
  "notes": "Measurements represent the functional MediaPipe CPU baseline..."
}
```

---

## 5. Comparative Evaluation Protocol (CPU vs. Qualcomm QNN)

> [!IMPORTANT]
> **Technical Truthfulness & Integration Scope**: Supplying `AEGIS_MODEL_PATH` or passing `--prefer-qnn` does not connect model outputs to pose estimation; runtime diagnostics only verify provider availability. Genuine QNN pose execution requires an ONNX/QNN pose-estimator adapter that preprocesses frames, calls `session.run()`, converts outputs to normalized `PoseFrame` landmarks, and replaces `MediaPipePoseEstimator`. MediaPipe CPU is the only currently verified active pose provider.

When transitioning to a compiled Qualcomm AI Hub pose model on a Snapdragon-powered HP PC:

1. **Step 1 — Establish CPU Baseline**: Run `scripts/benchmark.py` with default provider on the evaluation clip. Save results to `artifacts/benchmark_cpu.json`.
2. **Step 2 — Configure Qualcomm QNN**:
   - Set `$env:AEGIS_MODEL_PATH = "models/qualcomm_pose_model.onnx"`
   - Ensure Qualcomm AI Engine Direct SDK (QNN) runtime libraries are on `PATH`.
   - Run `scripts/benchmark.py` with `--prefer-qnn`. Save results to `artifacts/benchmark_qnn.json`.
3. **Step 3 — Compute Speedup & Latency Reduction**:
   - $\text{Speedup Factor} = \frac{\text{FPS}_{\text{QNN}}}{\text{FPS}_{\text{CPU}}}$
   - $\text{p95 Latency Reduction} = \frac{\text{Latency}_{\text{CPU}} - \text{Latency}_{\text{QNN}}}{\text{Latency}_{\text{CPU}}} \times 100\%$
4. **Step 4 — Verify Output Equivalence**: Check that detected event distribution remains consistent between CPU and QNN within normal numerical floating-point tolerances.
