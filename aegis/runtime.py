from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RuntimeDiagnostics:
    """Truthful report of active inference engines and Snapdragon deployment readiness."""

    active_pose_provider: str = "MediaPipe CPU"
    active_inference_provider: str = "MediaPipe CPU"
    available_ort_providers: list[str] = field(default_factory=list)
    qnn_available: bool = False
    qnn_pose_active: bool = False
    model_path: str | None = None
    notes: str = (
        "The current MVP uses MediaPipe CPU as the only verified active pose provider. "
        "Supplying AEGIS_MODEL_PATH initializes an ONNX session to verify provider availability, "
        "but does not connect model outputs to pose estimation. Runtime diagnostics only verify "
        "provider availability. Genuine QNN pose execution requires an ONNX/QNN pose-estimator "
        "adapter that preprocesses frames, calls session.run(), converts outputs to normalized "
        "PoseFrame landmarks, and replaces MediaPipePoseEstimator."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_pose_provider": self.active_pose_provider,
            "active_inference_provider": self.active_inference_provider,
            "available_ort_providers": self.available_ort_providers,
            "qnn_available": self.qnn_available,
            "qnn_pose_active": self.qnn_pose_active,
            "model_path": self.model_path,
            "notes": self.notes,
        }

    def format_report(self) -> str:
        qnn_status = "Available" if self.qnn_available else "Not detected"
        qnn_pose_status = "Active" if self.qnn_pose_active else "Inactive (MediaPipe CPU active)"
        lines = [
            "=" * 68,
            "AEGIS CORE // RUNTIME DIAGNOSTICS",
            "=" * 68,
            f"Active Pose Provider:      {self.active_pose_provider}",
            f"Active Inference Provider: {self.active_inference_provider}",
            f"Available ORT Providers:   {self.available_ort_providers}",
            f"Qualcomm QNN Provider:     {qnn_status}",
            f"QNN Pose Execution:        {qnn_pose_status}",
            f"Configured Model Path:     {self.model_path or 'None (default CPU pipeline)'}",
            "-" * 68,
            "Architecture & Optimization Pathway:",
            f"  {self.notes}",
            "=" * 68,
        ]
        return "\n".join(lines)


def get_available_ort_providers() -> list[str]:
    """Return available ONNX Runtime execution providers safely."""
    try:
        import onnxruntime as ort

        return list(ort.get_available_providers())
    except Exception:
        return []


def get_runtime_diagnostics(
    model_path: str | None = None,
    prefer_qnn: bool = False,
) -> RuntimeDiagnostics:
    """Inspect environment and return truthful runtime status."""
    resolved_path = model_path or os.getenv("AEGIS_MODEL_PATH")
    ort_providers = get_available_ort_providers()
    qnn_available = "QNNExecutionProvider" in ort_providers

    return RuntimeDiagnostics(
        active_pose_provider="MediaPipe CPU",
        active_inference_provider="MediaPipe CPU",
        available_ort_providers=ort_providers,
        qnn_available=qnn_available,
        qnn_pose_active=False,
        model_path=resolved_path,
    )


class SnapdragonSession:
    """Runtime provider manager with truthful CPU/QNN separation.

    Truthful Execution Contract:
    MediaPipe CPU is the only currently verified active pose provider.
    Supplying AEGIS_MODEL_PATH does not connect model outputs to pose estimation.
    Runtime diagnostics only verify provider availability.
    Genuine QNN pose execution requires an ONNX/QNN pose-estimator adapter that
    preprocesses frames, calls session.run(), converts outputs to normalized
    PoseFrame landmarks, and replaces MediaPipePoseEstimator.
    """

    def __init__(
        self,
        model_path: str | None = None,
        prefer_qnn: bool = False,
    ) -> None:
        self.model_path = model_path or os.getenv("AEGIS_MODEL_PATH")
        self.prefer_qnn = prefer_qnn
        self.active_provider = "MediaPipe CPU"
        self.provider = "MediaPipe CPU"
        self.session = None

    def initialize(self) -> str:
        """Initialize runtime environment and return active pose provider name.

        Always returns 'MediaPipe CPU' for the current functional pose pipeline,
        ensuring UI, logging and console output remain technically honest.
        """
        if self.prefer_qnn:
            available = get_available_ort_providers()
            if "QNNExecutionProvider" not in available or not self.model_path:
                print(
                    "[AEGIS RUNTIME] QNN pathway requested (--prefer-qnn), "
                    "but no QNN-compatible pose model is loaded."
                )
                print(
                    "[AEGIS RUNTIME] QNN pathway unavailable / not active. "
                    "Continuing with functional MediaPipe CPU pipeline."
                )

        if not self.model_path:
            self.provider = "MediaPipe CPU"
            self.active_provider = "MediaPipe CPU"
            return self.provider

        path = Path(self.model_path)
        if not path.exists():
            raise FileNotFoundError(f"Model not found: {path}")

        import onnxruntime as ort

        available = ort.get_available_providers()
        providers = []
        if self.prefer_qnn and "QNNExecutionProvider" in available:
            providers.append("QNNExecutionProvider")
        providers.append("CPUExecutionProvider")
        self.session = ort.InferenceSession(
            str(path),
            providers=providers,
        )

        # Note: Supplying AEGIS_MODEL_PATH does not connect model outputs to pose estimation.
        # Runtime diagnostics only verify provider availability.
        # Genuine QNN pose execution requires an ONNX/QNN pose-estimator adapter that
        # preprocesses frames, calls session.run(), converts outputs to normalized
        # PoseFrame landmarks, and replaces MediaPipePoseEstimator.
        # MediaPipe CPU is the only currently verified active pose provider.
        self.provider = "MediaPipe CPU"
        self.active_provider = "MediaPipe CPU"
        return self.provider

    def get_diagnostics(self) -> RuntimeDiagnostics:
        """Return structured runtime diagnostics."""
        return get_runtime_diagnostics(
            model_path=self.model_path,
            prefer_qnn=self.prefer_qnn,
        )
