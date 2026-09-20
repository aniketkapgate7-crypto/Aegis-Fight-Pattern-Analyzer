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
from .runtime import SnapdragonSession
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
    incident_count = 0
    last_logged = 0.0
    incident_armed = True
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
    print("F.R.I.D.A.Y. // AEGIS ONLINE")
    print(f"Inference provider: {provider}")
    print("Press R to start or stop recording.")
    print("Press Q to close the application.")
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

            # Re-arm only after the action has returned to a safe state. This
            # prevents one continuous punch/approach from being logged every
            # second as several separate incidents.
            if detection.threat < INCIDENT_RESET_THRESHOLD:
                incident_armed = True

            should_log_incident = (
                recording
                and incident_armed
                and detection.threat
                >= INCIDENT_THREAT_THRESHOLD
                and current_time - last_logged
                >= INCIDENT_LOG_INTERVAL
            )

            if should_log_incident:
                event = {
                    "timestamp": time.time(),
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

                incident_count += 1
                last_logged = current_time
                incident_armed = False

                print(
                    "Incident recorded:",
                    detection.pattern.value,
                    f"| Threat "
                    f"{detection.threat * 100:.0f}%",
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
                incident_count=incident_count,
            )

            cv2.imshow(
                window_name,
                hud_frame,
            )

            # waitKeyEx is more reliable for OpenCV windows on Windows.
            raw_key = cv2.waitKeyEx(1)
            key = raw_key & 0xFF if raw_key >= 0 else -1

            if key in (ord("q"), ord("Q"), 27):
                print("Closing Aegis.")
                break

            if key in (ord("r"), ord("R"), ord(" ")):
                recording = not recording
                incident_armed = True

                recording_status = (
                    "ON" if recording else "OFF"
                )

                print(
                    "Incident recording:",
                    recording_status,
                )

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
                provider="Synthetic Demo",
                history=pattern_history,
                recording=False,
                incident_count=0,
            )

            cv2.imshow(
                window_name,
                hud_frame,
            )

            key = cv2.waitKey(700) & 0xFF

            if key == ord("q"):
                return

        cv2.waitKey(0)

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
            "execution provider"
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

    args = parser.parse_args()

    if args.demo:
        demo()
        return

    run(
        source=parse_source(args.source),
        prefer_qnn=args.prefer_qnn,
    )


if __name__ == "__main__":
    main()
