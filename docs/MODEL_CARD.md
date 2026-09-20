# Model Card: Aegis Motion Pattern Analysis Pipeline

## 1. Pipeline Overview

- **Architecture Name**: Aegis Combat Motion Intelligence Pipeline (MVP)
- **Active Pose Estimation Engine**: MediaPipe Pose (CPU Execution)
- **Temporal Pattern Logic**: Rule-based explainable kinematic pattern engine with sliding window
- **Target Hardware Architecture**: Qualcomm Snapdragon X Elite / X Plus platform (Windows 11 on Arm)
- **Model Card Version**: 1.0 (Snapdragon AI Lab Challenge MVP)

---

## 2. Model Pipeline Specifications

### Inputs
- **Input Modality**: Real-time RGB video stream (from local USB/integrated webcam) or prerecorded digital video file (`.mp4`, `.avi`, `.mov`).
- **Standard Processing Resolution**: $960 \times 540$ pixels (downsampled from source for responsive low-latency display).
- **Color Space**: BGR (OpenCV) converted to RGB for pose processing.
- **Sampling Frequency**: Live camera frame rate (nominally 30 FPS).

### Outputs
- **Primary Outputs**:
  - Normalized 2D landmark coordinates $(x, y \in [0.0, 1.0])$ and visibility confidence $(v \in [0.0, 1.0])$ across 9 anatomical keypoints (nose, left/right shoulders, left/right wrists, left/right hips, left/right ankles).
  - Categorical Pattern Label from the supported vocabulary.
  - Pattern Confidence Score ($\in [0.0, 1.0]$).
  - Aggregated Threat Assessment Score ($\in [0.0, 1.0]$).
  - Natural-language Kinematic Evidence Strings (e.g., `"right arm rapidly extended"`, `"arm reach 1.65x shoulder width"`, `"extension speed 1.15/s"`).
- **Secondary Outputs**:
  - Live HUD visualization buffer ($960 \times 540$ RGB).
  - Optional timestamped JSONL record written locally upon crossing threat threshold ($0.70$).

---

## 3. Supported Motion Patterns

| Pattern Key | Formal Description | Primary Biomechanical Criteria | Threat Weight |
| --- | --- | --- | --- |
| `neutral` | Baseline upright or resting posture | No risk-pattern threshold exceeded | Low ($0.05$) |
| `guard` | Defensive ready stance | One or both wrists maintained in close proximity to facial landmarks ($<1.30 \times$ shoulder width) | Low-Elevated ($0.30$) |
| `punch-like extension` | Ballistic linear arm extension | Rapid horizontal wrist excursion relative to shoulder axis ($>1.45 \times$ shoulder width at $>0.90 /s$) | High ($0.88$) |
| `kick-like extension` | Ballistic lower-limb elevation & extension | Ankle displacement beyond hip center ($>1.35 \times$ shoulder width at $>0.65 /s$, or static reach $>1.85 \times$) with vertical elevation | High-Critical ($0.90$) |
| `rapid approach` | Accelerating movement toward sensor | Torso scale expansion exceeding $6\%$ over 3 consecutive frames with relative speed $>0.80 /s$ | High ($0.72$) |
| `fall-like posture` | Loss of upright equilibrium / recumbent body | Torso horizontal-to-vertical aspect ratio $>1.25$ with reduced total vertical body span | Critical ($0.90$) |

---

## 4. Privacy & Ethical Design

- **Anonymity by Architecture**: No facial recognition, facial landmark mapping, identity inference, or demographic extraction.
- **On-Device Isolation**: 100% of frame processing occurs on local host memory. Zero cloud data transmission.
- **Ephemeral Frame Buffering**: Frames are processed immediately and discarded. Video is never saved unless external recording is explicitly configured.
- **Deterministic Synthetic Mode**: Supports complete testing and preview generation (`--demo` / `--export-preview`) without requiring access to a webcam or live human subject.

---

## 5. Test & Validation Methodology

The temporal pattern engine is evaluated using a deterministic, unit-tested suite covering 17 critical behavioral test cases:
1. Neutral baseline posture validation.
2. Incomplete landmark fail-safe handling.
3. Left-arm ballistic punch extension.
4. Right-arm ballistic punch extension.
5. Dual-hand and single-hand guard postures.
6. Elevated and dynamic leg kick extensions.
7. Predominantly horizontal recumbent fall detection.
8. Rapid forward body-scale approach.
9. Shoulder jitter resilience (preventing false approach triggers).
10. Sub-threshold body-scale change tolerance.
11. Strict boundedness of threat ($[0, 1]$) and confidence ($[0, 1]$) metrics.
12. Missing ONNX model runtime error handling.
13. Truthful runtime provider reporting (guaranteeing `MediaPipe CPU` is accurately identified).
14. Incident tracker re-arming and deduplication cycle.
15. Keyboard control mapping (`Q`, `Esc`, `R`, `Space`).
16. Pattern priority resolution (Fall taking precedence over limb strikes).
17. Landmark occlusion and low-visibility resilience.

> [!NOTE]
> Unit-test suite success verifies deterministic mathematical and logic correctness of kinematic heuristics. It is explicitly not presented as field model accuracy.

---

## 6. Snapdragon / Qualcomm QNN Optimization Pathway

The current system isolates runtime execution within `SnapdragonSession` and `RuntimeDiagnostics`:

1. **Current Verified Baseline**: MediaPipe CPU execution provider on Python 3.11.
2. **Planned Target Model**: Qualcomm AI Hub-compiled ONNX pose estimation model (e.g., lightweight YOLOv8-pose or RTMPose INT8/FP16 quantized for Snapdragon NPU).
3. **Execution Runtime**: ONNX Runtime with Qualcomm QNN Execution Provider (`QNNExecutionProvider`) targeting the Hexagon NPU on Snapdragon X Elite / X Plus PCs.
4. **Validation Contract**: Until a compiled QNN pose model is actively integrated into the landmark inference loop, the system truthfully displays and logs `MediaPipe CPU` as the active provider.
