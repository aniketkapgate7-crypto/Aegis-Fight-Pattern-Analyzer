# Third-Party Notices and Intellectual Property

## 1. Project Ownership Statement

- **Author & Participant**: Aniket Kapgate
- **Project**: Aegis: Privacy-Preserving On-Device Combat Motion Intelligence
- **Repository**: [https://github.com/aniketkapgate7-crypto/Aegis-Fight-Pattern-Analyzer](https://github.com/aniketkapgate7-crypto/Aegis-Fight-Pattern-Analyzer)

All original Aegis software code, including but not limited to the kinematic temporal pattern engine (`aegis/patterns.py`), heads-up display layout and rendering (`aegis/ui.py`), incident deduplication and application lifecycle management (`aegis/app.py`), runtime diagnostic provider framework (`aegis/runtime.py`), evaluation suite (`scripts/benchmark.py`), automated test specifications (`tests/test_patterns.py`), and all original documentation, proposals, pitch decks, and submission descriptions are authored by and remain the intellectual property of the participant, Aniket Kapgate.

Third-party libraries, dependencies, and external models utilized by Aegis remain the property of their respective copyright holders and are governed by their respective licenses as enumerated below.

*(Note: In accordance with competition requirements, no general permissive license such as MIT is granted for the Aegis proprietary codebase without explicit prior written authorization from the project owner).*

---

## 2. Third-Party Dependencies and Licenses

The following open-source software libraries are utilized by Aegis. License terms and repository references are verified from authoritative upstream project sources:

### 1. Google MediaPipe
- **Project Name**: MediaPipe
- **Official Repository**: [https://github.com/google/mediapipe](https://github.com/google/mediapipe)
- **License**: Apache License, Version 2.0
- **How Aegis Uses It**: Provides on-device vision-based skeletal pose estimation, extracting normalized 2D landmark coordinates across human joints in live camera streams and synthetic demo modes.

### 2. OpenCV (Open Source Computer Vision Library)
- **Project Name**: OpenCV (`opencv-contrib-python`)
- **Official Repository**: [https://github.com/opencv/opencv](https://github.com/opencv/opencv)
- **License**: Apache License, Version 2.0 (OpenCV 4.5+)
- **How Aegis Uses It**: Handles video capture stream acquisition, camera frame resizing, HUD canvas drawing, geometric polygon overlays, anti-aliased text rendering, and privacy-safe synthetic preview image exports.

### 3. NumPy
- **Project Name**: NumPy
- **Official Repository**: [https://github.com/numpy/numpy](https://github.com/numpy/numpy)
- **License**: BSD 3-Clause "New" or "Revised" License
- **How Aegis Uses It**: Powers high-performance multi-dimensional array operations, HUD panel coordinate matrices, image buffer manipulations, and benchmark latency percentile calculations ($p50, p95, p99$).

### 4. Microsoft ONNX Runtime
- **Project Name**: ONNX Runtime (`onnxruntime`)
- **Official Repository**: [https://github.com/microsoft/onnxruntime](https://github.com/microsoft/onnxruntime)
- **License**: MIT License
- **How Aegis Uses It**: Serves as the cross-platform execution runtime framework for hardware provider discovery (`get_available_providers()`) and orchestrates the planned Snapdragon optimization pathway via the Qualcomm QNN Execution Provider (`QNNExecutionProvider`).

### 5. pytest
- **Project Name**: pytest
- **Official Repository**: [https://github.com/pytest-dev/pytest](https://github.com/pytest-dev/pytest)
- **License**: MIT License
- **How Aegis Uses It**: Provides the deterministic unit-testing test harness for verifying pattern logic, runtime error handling, boundary safety conditions, and incident re-arming mechanics.

---

## 3. Trademarks

- **Qualcomm**, **Snapdragon**, **Hexagon**, and **Qualcomm AI Hub** are registered trademarks or trademarks of Qualcomm Incorporated.
- **HP** is a registered trademark of HP Inc.
- **Windows** is a registered trademark of Microsoft Corporation.
- All other brand names, product names, or trademarks belong to their respective holders and are referenced solely for technical description and hardware compatibility identification.
