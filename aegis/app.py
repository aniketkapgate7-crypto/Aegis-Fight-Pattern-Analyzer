from __future__ import annotations

import argparse
import json
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np

from .models import Detection, Pattern
from .patterns import PatternEngine
from .pose import MediaPipePoseEstimator
from .runtime import SnapdragonSession, get_runtime_diagnostics
from .ui import draw_hud


DISPLAY_WIDTH = 960
DISPLAY_HEIGHT = 540

INCIDENT_THREAT_THRESHOLD = 0.70
INCIDENT_LOG_INTERVAL = 1.0
INCIDENT_RESET_THRESHOLD = 0.40


def parse_source(value: str):
    """Convert a camera number to int or preserve a video path."""
    return int(value) if value.isdigit() else value


def resize_display(frame: np.ndarray) -> np.ndarray:
    """Resize the camera frame before drawing the HUD."""
    return cv2.resize(
        frame,
        (DISPLAY_WIDTH, DISPLAY_HEIGHT),
        interpolation=cv2.INTER_AREA,
    )


def create_neutral_detection(
    evidence: str,
) -> Detection:
    """Create a safe neutral detection."""
    return Detection(
        pattern=Pattern.NEUTRAL,
        confidence=0.0,
        threat=0.0,
        evidence=[evidence],
    )


def handle_keypress(key: int) -> str | None:
    """Map raw keycode to an Aegis application action.

    Supports:
      - 'q', 'Q', 27 (Esc) -> 'exit'
      - 'r', 'R', ' ', 32 (Space) -> 'toggle_recording'
    """
    if key in (ord("q"), ord("Q"), 27):
        return "exit"
    if key in (ord("r"), ord("R"), ord(" "), 32):
        return "toggle_recording"
    return None


class IncidentTracker:
    """Manage incident threat detection, re-arming, and deduplication."""

    def __init__(
        self,
        threat_threshold: float = INCIDENT_THREAT_THRESHOLD,
        reset_threshold: float = INCIDENT_RESET_THRESHOLD,
        log_interval: float = INCIDENT_LOG_INTERVAL,
    ) -> None:
        self.threat_threshold = threat_threshold
        self.reset_threshold = reset_threshold
        self.log_interval = log_interval
        self.armed = True
        self.last_logged = 0.0
        self.incident_count = 0

    def should_log(
        self,
        threat: float,
        recording: bool,
        current_time: float,
    ) -> bool:
        if threat < self.reset_threshold:
            self.armed = True

        return bool(
            recording
            and self.armed
            and threat >= self.threat_threshold
            and (current_time - self.last_logged >= self.log_interval)
        )

    def record_incident(self, current_time: float) -> int:
        self.incident_count += 1
        self.last_logged = current_time
        self.armed = False
        return self.incident_count


def export_preview(
    output_path: str | Path = "docs/assets/aegis-core-dashboard.png",
) -> Path:
    """Generate a privacy-safe synthetic preview image without using a personal webcam frame.

    The image uses a synthetic dark background and deterministic landmarks showing
    the AEGIS CORE dashboard suitable for documentation and presentation.
    """
    from .models import Point, PoseFrame

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    points = {
        "nose": Point(0.50, 0.20),
        "left_shoulder": Point(0.40, 0.35),
        "right_shoulder": Point(0.60, 0.35),
        "left_wrist": Point(0.42, 0.48),
        "right_wrist": Point(0.93, 0.34),  # Extended punch
        "left_hip": Point(0.44, 0.62),
        "right_hip": Point(0.56, 0.62),
        "left_ankle": Point(0.44, 0.92),
        "right_ankle": Point(0.56, 0.92),
    }
    pose = PoseFrame(timestamp=0.2, points=points)

    detection = Detection(
        pattern=Pattern.PUNCH,
        confidence=0.92,
        threat=0.88,
        evidence=[
            "right arm rapidly extended",
            "arm reach 1.65x shoulder width",
            "extension speed 1.15/s",
        ],
    )

    history = [
        Detection(Pattern.NEUTRAL, 0.85, 0.05, ["baseline stance"]),
        Detection(Pattern.NEUTRAL, 0.85, 0.05, ["baseline stance"]),
        Detection(Pattern.GUARD, 0.78, 0.30, ["hands near face"]),
        detection,
    ]

    # Create synthetic dark background with subtle technical styling
    canvas = np.full((DISPLAY_HEIGHT, DISPLAY_WIDTH, 3), 14, dtype=np.uint8)
    for y in range(0, DISPLAY_HEIGHT, 40):
        cv2.line(canvas, (0, y), (DISPLAY_WIDTH, y), (20, 26, 30), 1)
    for x in range(0, DISPLAY_WIDTH, 40):
        cv2.line(canvas, (x, 0), (x, DISPLAY_HEIGHT), (20, 26, 30), 1)

    hud_frame = draw_hud(
        frame=canvas,
        pose=pose,
        detection=detection,
        fps=30.0,
        latency_ms=8.4,
        provider="MediaPipe CPU",
        history=history,
        recording=True,
        incident_count=1,
    )

    cv2.imwrite(str(out_file), hud_frame)
    print(f"Privacy-safe preview exported to: {out_file.resolve()}")
    return out_file


def run(
    source=0,
    prefer_qnn: bool = False,
) -> None:
    """Run live Aegis fight-pattern analysis."""
    runtime = SnapdragonSession(
        prefer_qnn=prefer_qnn,
    )
    provider = runtime.initialize()

    estimator = MediaPipePoseEstimator()
    engine = PatternEngine()

    capture = cv2.VideoCapture(source)

    if not capture.isOpened():
        estimator.close()
        raise RuntimeError(
            f"Cannot open video source: {source}"
        )

    # Reduce camera buffering for lower latency.
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    log_directory = Path("artifacts")
    log_directory.mkdir(exist_ok=True)

    log_path = log_directory / "incidents.jsonl"

    recording = False
    tracker = IncidentTracker()
    previous_time = time.perf_counter()
    smoothed_fps = 0.0
    smoothed_latency_ms = 0.0

    pattern_history: deque[Detection] = deque(
        maxlen=5
    )

    last_pattern: Pattern | None = None

    detection = create_neutral_detection(
        "waiting for pose"
    )

    window_name = "Aegis Fight Pattern Analyzer"

    cv2.namedWindow(
        window_name,
        cv2.WINDOW_NORMAL,
    )

    cv2.resizeWindow(
        window_name,
        DISPLAY_WIDTH,
        DISPLAY_HEIGHT,
    )

    print()
    print("AEGIS CORE // SYSTEM ONLINE")
    print(f"Active inference provider: {provider}")
    print("Controls: R / Space = Toggle Recording | Q / Esc = Exit")
    print()

    try:
        while True:
            frame_available, camera_frame = (
                capture.read()
            )

            if not frame_available:
                print(
                    "Unable to read a frame "
                    "from the video source."
                )
                break

            analysis_started = time.perf_counter()

            pose = estimator.estimate(
                camera_frame,
                analysis_started,
            )

            if pose is not None:
                detection = engine.update(pose)
            else:
                detection = create_neutral_detection(
                    "no pose detected"
                )

            if detection.pattern != last_pattern:
                pattern_history.append(detection)
                last_pattern = detection.pattern

            latency_ms = (
                time.perf_counter()
                - analysis_started
            ) * 1000

            current_time = time.perf_counter()

            frame_interval = max(
                current_time - previous_time,
                1e-6,
            )

            instant_fps = 1.0 / frame_interval
            previous_time = current_time

            # Smooth rapidly changing metrics so the HUD remains readable.
            if smoothed_fps == 0.0:
                smoothed_fps = instant_fps
                smoothed_latency_ms = latency_ms
            else:
                smoothed_fps = smoothed_fps * 0.85 + instant_fps * 0.15
                smoothed_latency_ms = (
                    smoothed_latency_ms * 0.85 + latency_ms * 0.15
                )

            fps = smoothed_fps
            latency_ms = smoothed_latency_ms

            if tracker.should_log(detection.threat, recording, current_time):
                incident_number = tracker.record_incident(current_time)
                event = {
                    "timestamp": time.time(),
                    "incident_id": incident_number,
                    "pattern": (
                        detection.pattern.value
                    ),
                    "confidence": round(
                        detection.confidence,
                        4,
                    ),
                    "threat": round(
                        detection.threat,
                        4,
                    ),
                    "evidence": detection.evidence,
                    "provider": provider,
                    "fps": round(fps, 2),
                    "latency_ms": round(
                        latency_ms,
                        2,
                    ),
                }

                with log_path.open(
                    "a",
                    encoding="utf-8",
                ) as log_file:
                    log_file.write(
                        json.dumps(event) + "\n"
                    )

                print(
                    f"Incident #{incident_number:02d} recorded:",
                    detection.pattern.value,
                    f"| Threat {detection.threat * 100:.0f}%",
                )

            # Resize first so the HUD text stays sharp.
            display_frame = resize_display(
                camera_frame.copy()
            )

            # Pose points are normalized, so they remain
            # correct after resizing the camera frame.
            hud_frame = draw_hud(
                frame=display_frame,
                pose=pose,
                detection=detection,
                fps=fps,
                latency_ms=latency_ms,
                provider=provider,
                history=pattern_history,
                recording=recording,
                incident_count=tracker.incident_count,
            )

            cv2.imshow(
                window_name,
                hud_frame,
            )

            raw_key = cv2.waitKeyEx(1)
            key = raw_key & 0xFF if raw_key >= 0 else -1
            action = handle_keypress(key)

            if action == "exit":
                print("Closing Aegis.")
                break

            if action == "toggle_recording":
                recording = not recording
                tracker.armed = True
                status_text = "ON" if recording else "OFF"
                print(f"Incident recording: {status_text}")

    except KeyboardInterrupt:
        print()
        print("Aegis interrupted by user.")

    finally:
        capture.release()
        estimator.close()
        cv2.destroyAllWindows()

        print("Camera released.")
        print("Aegis offline.")


def demo() -> None:
    """Run a deterministic demonstration without a camera."""
    from .models import Point, PoseFrame

    engine = PatternEngine()

    base_points = {
        "nose": Point(0.50, 0.20),
        "left_shoulder": Point(0.40, 0.35),
        "right_shoulder": Point(0.60, 0.35),
        "left_wrist": Point(0.42, 0.50),
        "right_wrist": Point(0.58, 0.50),
        "left_hip": Point(0.44, 0.62),
        "right_hip": Point(0.56, 0.62),
        "left_ankle": Point(0.44, 0.92),
        "right_ankle": Point(0.56, 0.92),
    }

    pattern_history: deque[Detection] = deque(
        maxlen=5
    )

    last_pattern: Pattern | None = None

    window_name = "Aegis Synthetic Demo"

    cv2.namedWindow(
        window_name,
        cv2.WINDOW_NORMAL,
    )

    cv2.resizeWindow(
        window_name,
        DISPLAY_WIDTH,
        DISPLAY_HEIGHT,
    )

    demo_reaches = (
        0.58,
        0.70,
        0.93,
    )

    try:
        for index, reach in enumerate(
            demo_reaches
        ):
            points = dict(base_points)

            points["right_wrist"] = Point(
                reach,
                0.34,
            )

            pose = PoseFrame(
                timestamp=index * 0.1,
                points=points,
            )

            detection = engine.update(pose)

            if detection.pattern != last_pattern:
                pattern_history.append(detection)
                last_pattern = detection.pattern

            canvas = np.zeros(
                (
                    DISPLAY_HEIGHT,
                    DISPLAY_WIDTH,
                    3,
                ),
                dtype=np.uint8,
            )

            hud_frame = draw_hud(
                frame=canvas,
                pose=pose,
                detection=detection,
                fps=30.0,
                latency_ms=8.4,
                provider="MediaPipe CPU",
                history=pattern_history,
                recording=False,
                incident_count=0,
            )

            cv2.imshow(
                window_name,
                hud_frame,
            )

            raw_key = cv2.waitKey(700)
            key = raw_key & 0xFF if raw_key >= 0 else -1
            if handle_keypress(key) == "exit":
                return

        # Keep the final state visible until user dismisses
        raw_key = cv2.waitKey(0)
        key = raw_key & 0xFF if raw_key >= 0 else -1
        handle_keypress(key)

    finally:
        cv2.destroyAllWindows()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Aegis on-device fight-pattern analyzer"
        )
    )

    parser.add_argument(
        "--source",
        default="0",
        help="Camera index or video path",
    )

    parser.add_argument(
        "--prefer-qnn",
        action="store_true",
        help=(
            "Prefer the Qualcomm QNN "
            "execution provider (falls back truthfully if model not loaded)"
        ),
    )

    parser.add_argument(
        "--demo",
        action="store_true",
        help=(
            "Run the deterministic "
            "no-camera demonstration"
        ),
    )

    parser.add_argument(
        "--export-preview",
        nargs="?",
        const="docs/assets/aegis-core-dashboard.png",
        default=None,
        metavar="PATH",
        help=(
            "Export a privacy-safe synthetic preview image to PATH "
            "(default: docs/assets/aegis-core-dashboard.png) and exit"
        ),
    )

    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="Display runtime and Snapdragon execution diagnostics and exit",
    )

    args = parser.parse_args()

    if args.diagnostics:
        diag = get_runtime_diagnostics(prefer_qnn=args.prefer_qnn)
        print(diag.format_report())
        return

    if args.export_preview is not None:
        export_preview(args.export_preview)
        return

    if args.demo:
        demo()
        return

    run(
        source=parse_source(args.source),
        prefer_qnn=args.prefer_qnn,
    )


if __name__ == "__main__":
    main()
