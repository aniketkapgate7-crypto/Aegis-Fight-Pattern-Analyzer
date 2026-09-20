# Snapdragon deployment and evidence plan

## Target

HP PC powered by Snapdragon X Elite or Snapdragon X Plus, Windows 11 on Arm.

## Model path

1. Select a compatible pose-estimation model from Qualcomm AI Hub (or an eligible open-source model).
2. Export/compile it for the target Snapdragon chipset using Qualcomm AI Hub.
3. Download the resulting ONNX/QNN-compatible asset and record its source, license, input shape, precision, and checksum.
4. Place the model under `models/` and set `AEGIS_MODEL_PATH`.
5. Run with `--prefer-qnn` and confirm the HUD reports `QNNExecutionProvider`.

Do not claim NPU execution based only on expected compatibility. Capture provider output and measured results on the target HP PC.

## Benchmark protocol

- Warm up for 100 frames.
- Measure the next 1,000 frames on the same 1080p clip.
- Report median and p95 model latency, end-to-end FPS, peak memory, power mode, processor name, model precision, and execution provider.
- Compare QNN/NPU and CPU using the identical clip and thresholds.
- Run five representative scenarios: neutral movement, guard, punch-like extension, kick-like extension, and fall-like posture.
- Report false alerts and missed events; retain anonymized aggregate results only.

## Accessibility and privacy

- Fully local processing and logging
- High-contrast HUD with text labels in addition to color
- Keyboard controls and prerecorded-video support
- No face recognition, identity database, or automatic enforcement action
- Incident logs can be disabled and remain local
