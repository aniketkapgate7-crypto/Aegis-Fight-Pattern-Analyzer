from __future__ import annotations

import os
from pathlib import Path


class SnapdragonSession:
    """Select QNN when present, while making fallback behavior explicit."""

    def __init__(self, model_path: str | None = None, prefer_qnn: bool = False) -> None:
        self.model_path = model_path or os.getenv("AEGIS_MODEL_PATH")
        self.prefer_qnn = prefer_qnn
        self.provider = "MediaPipe CPU"
        self.session = None

    def initialize(self) -> str:
        if not self.model_path:
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
        self.session = ort.InferenceSession(str(path), providers=providers)
        self.provider = self.session.get_providers()[0]
        return self.provider
