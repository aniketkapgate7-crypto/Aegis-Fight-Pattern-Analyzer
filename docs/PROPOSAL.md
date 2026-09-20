# Challenge proposal: Aegis Fight Pattern Analyzer

## Problem

Sports trainees and supervised safety teams often review movement only after an incident. Cloud video analytics adds latency, connectivity dependence, and privacy exposure.

## Solution

Aegis is a local desktop application that converts live video into normalized human-pose landmarks, examines short movement windows, and highlights explainable fight-like patterns. It provides a human operator with real-time evidence instead of making autonomous judgments.

## Innovation

- Privacy-preserving, on-device pose analysis
- Temporal motion patterns rather than single-frame labels
- Explainable evidence attached to every alert
- Snapdragon NPU deployment path with graceful CPU fallback
- Useful offline in gyms, training rooms, and controlled safety demonstrations

## Evaluation alignment

| Criterion | Evidence planned |
| --- | --- |
| Technical implementation | Working camera pipeline, temporal engine, QNN adapter, tests, measured latency |
| Use case and innovation | Offline explainable motion intelligence with privacy safeguards |
| Deployment and accessibility | Windows on Arm package, local processing, keyboard controls, high-contrast HUD |
| Presentation and documentation | Architecture, setup guide, benchmark report, demo video, model card |

## Success targets

- At least 24 FPS end-to-end on the target Snapdragon HP PC
- p95 pose inference latency below 35 ms on QNN/NPU
- At least 85% event-level recall on the controlled five-scenario validation set
- Fewer than 0.2 false alerts per minute during neutral movement
- Zero required cloud calls during analysis

## Ownership note

All original application code, interface design, thresholds, documentation, and evaluation artifacts must be authored and retained by the participant. Third-party models and libraries must be documented with their licenses and sources.
