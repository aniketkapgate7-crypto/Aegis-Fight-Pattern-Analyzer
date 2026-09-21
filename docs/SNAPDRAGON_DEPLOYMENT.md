# Snapdragon Deployment & Optimization Guide

This document outlines the technical architecture for transitioning Aegis from its current **MediaPipe CPU** functional baseline to hardware-accelerated **Qualcomm QNN / Snapdragon NPU** execution on Snapdragon-powered HP PCs (Snapdragon X Elite / Snapdragon X Plus running Windows 11 on Arm).

---

## 1. Current State: MediaPipe CPU Baseline

In the current MVP:
- Pose estimation is executed via Google MediaPipe on the host CPU.
- Frame preprocessing, landmark detection, and visibility filtering are handled on general-purpose CPU cores.
- `aegis/runtime.py` transparently inspects the execution environment. The AEGIS CORE HUD and incident logger truthfully report `MediaPipe CPU` as the active landmark engine.
- This baseline establishes functional correctness, temporal pattern stability, and automated unit test verification before introducing compiled NPU binary assets.

---

## 2. Planned Qualcomm AI Hub Model Selection

To migrate pose estimation to the Qualcomm Hexagon NPU:

1. **Target Architecture**: Snapdragon X Elite (e.g., X1E-84-100 / X1E-78-100) or Snapdragon X Plus compute platforms.
2. **Model Family Selection**: Select a lightweight, single-person or multi-person pose estimation model supported by Qualcomm AI Hub:
   - *Option A (Recommended)*: **YOLOv8n-pose** / **YOLOv8s-pose** — highly optimized for low-latency edge deployment with well-defined 17-keypoint outputs.
   - *Option B*: **RTMPose** (Real-Time Multi-Person Pose) — exceptional accuracy-to-latency balance on mobile and edge NPUs.
3. **Quantization Precision**: Choose **INT8** (quantized via Qualcomm AI Hub post-training quantization) for maximum throughput and power efficiency, or **FP16** for maximum precision.

---

## 3. Compilation & Optimization via Qualcomm AI Hub

The Qualcomm AI Hub compilation workflow consists of:

```powershell
# 1. Install Qualcomm AI Hub client
pip install qai-hub

# 2. Authenticate with Qualcomm AI Hub API
qai-hub configure --api_token <YOUR_QUALCOMM_AI_HUB_TOKEN>

# 3. Submit model compilation job targeting Snapdragon X Elite NPU
# Example submission:
qai-hub compile \
  --model "models/yolov8n-pose.onnx" \
  --device "Snapdragon X Elite CRD" \
  --options "--target_runtime qnn_lib_aarch64_android" \
  --output "models/yolov8n_pose_qnn.onnx"
```

The resulting model asset is an optimized ONNX graph utilizing Qualcomm QNN execution delegates specifically mapped to the Hexagon Tensor Processor and Vector Extensions.

---

## 4. Replacing MediaPipe with ONNX/QNN Pose Estimator

Aegis uses a modular pose estimator interface. Replacing MediaPipe involves implementing an `ONNXQNNPoseEstimator` adhering to the existing `estimate(frame, timestamp) -> PoseFrame | None` signature:

```python
class ONNXQNNPoseEstimator:
    """Qualcomm QNN-accelerated pose estimation for Snapdragon NPU."""

    def __init__(self, model_path: str, prefer_qnn: bool = True) -> None:
        import onnxruntime as ort

        providers = ["CPUExecutionProvider"]
        if prefer_qnn and "QNNExecutionProvider" in ort.get_available_providers():
            # Configure QNN provider options for Hexagon NPU
            qnn_options = {
                "backend_path": "QnnHtp.dll",  # Hexagon Tensor Processor backend
                "htp_performance_mode": "burst",
                "htp_precision": "quantized",
            }
            providers.insert(0, ("QNNExecutionProvider", qnn_options))

        self.session = ort.InferenceSession(model_path, providers=providers)
        self.active_provider = self.session.get_providers()[0]
        self.input_name = self.session.get_inputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape  # e.g., [1, 3, 256, 256]

    def estimate(self, bgr_frame: np.ndarray, timestamp: float) -> PoseFrame | None:
        # 1. Resize & normalize frame to model input shape
        tensor = self._preprocess(bgr_frame)
        # 2. Execute on Hexagon NPU via QNNExecutionProvider
        outputs = self.session.run(None, {self.input_name: tensor})
        # 3. Postprocess heatmaps/coords to normalized landmark Points
        points = self._postprocess(outputs)
        return PoseFrame(timestamp=timestamp, points=points)

    def close(self) -> None:
        pass
```

---

## 5. Verification Contract for Active Provider

To maintain absolute technical truthfulness:
- **MediaPipe CPU Baseline**: MediaPipe CPU is the only currently verified active pose provider.
- **Provider Verification**: Supplying `AEGIS_MODEL_PATH` does not connect model outputs to pose estimation. Runtime diagnostics only verify provider availability.
- **Pose Adapter Requirement**: Genuine QNN pose execution requires an ONNX/QNN pose-estimator adapter that preprocesses frames, calls `session.run()`, converts outputs to normalized `PoseFrame` landmarks, and replaces `MediaPipePoseEstimator`.
- Aegis will only report `QNNExecutionProvider` on the HUD when:
  1. An ONNX Runtime session has successfully bound the `QNNExecutionProvider`.
  2. The landmark coordinate generation loop genuinely invokes that QNN session for every frame via an integrated adapter.
- If `--prefer-qnn` is passed but the QNN runtime library or model asset is absent, the system explicitly prints:
  ```
  [AEGIS RUNTIME] QNN pathway requested (--prefer-qnn), but no QNN-compatible pose model is loaded.
  [AEGIS RUNTIME] QNN pathway unavailable / not active. Continuing with functional MediaPipe CPU pipeline.
  ```
- The diagnostic command `python -m aegis.app --diagnostics` confirms active vs. detected providers at any time.

---

## 6. CPU vs. QNN Benchmarking Protocol

Once an ONNX/QNN pose-estimator adapter and compiled model are integrated, the benchmark will execute `scripts/benchmark.py` under strictly controlled conditions:

```powershell
# 1. Measure CPU Baseline (Current verified pipeline)
python scripts/benchmark.py --source data/sparring_eval_1080p.mp4 --warmup 100 --frames 1000 --output artifacts/benchmark_cpu.json

# 2. Measure Qualcomm QNN / Snapdragon NPU (Planned optimization)
$env:AEGIS_MODEL_PATH = "models/yolov8n_pose_qnn.onnx"
python scripts/benchmark.py --source data/sparring_eval_1080p.mp4 --warmup 100 --frames 1000 --prefer-qnn --output artifacts/benchmark_qnn.json
```

### Metrics Comparison Criteria:
- **Throughput**: Target $\ge 30\text{ FPS}$ sustained on battery power.
- **Inference Latency**: Target $p95$ latency $\le 25\text{ ms}$ on Hexagon NPU.
- **CPU Offload**: Measure reduced host CPU utilization (% CPU core load offloaded to NPU).
- **Power Efficiency**: Monitor system battery discharge rate ($W$) during continuous analysis.
