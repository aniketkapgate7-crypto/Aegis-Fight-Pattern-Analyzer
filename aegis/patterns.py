from __future__ import annotations

from collections import deque
from math import hypot

from .models import Detection, Pattern, PoseFrame


def _distance(frame: PoseFrame, a: str, b: str) -> float:
    """Return normalized 2D distance between two landmarks."""
    p = frame.points[a]
    q = frame.points[b]
    return hypot(p.x - q.x, p.y - q.y)


def _midpoint(frame: PoseFrame, a: str, b: str) -> tuple[float, float]:
    """Return the midpoint between two landmarks."""
    p = frame.points[a]
    q = frame.points[b]
    return ((p.x + q.x) / 2, (p.y + q.y) / 2)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    """Restrict a value to a fixed range."""
    return max(minimum, min(value, maximum))


def _body_scale(frame: PoseFrame) -> float:
    """Estimate subject scale using several stable torso measurements."""
    shoulder_width = _distance(frame, "left_shoulder", "right_shoulder")
    hip_width = _distance(frame, "left_hip", "right_hip")
    shoulder_x, shoulder_y = _midpoint(frame, "left_shoulder", "right_shoulder")
    hip_x, hip_y = _midpoint(frame, "left_hip", "right_hip")
    torso_length = hypot(hip_x - shoulder_x, hip_y - shoulder_y)
    return shoulder_width * 0.50 + hip_width * 0.20 + torso_length * 0.30


class PatternEngine:
    """Explainable fight-pattern recognition over a short pose window."""

    REQUIRED = {
        "nose",
        "left_shoulder",
        "right_shoulder",
        "left_wrist",
        "right_wrist",
        "left_hip",
        "right_hip",
        "left_ankle",
        "right_ankle",
    }

    def __init__(self, window: int = 12) -> None:
        self.frames: deque[PoseFrame] = deque(maxlen=window)

    def _arm_reach(
        self,
        frame: PoseFrame,
        wrist_name: str,
        shoulder_width: float,
    ) -> float:
        """Measure horizontal wrist extension relative to body scale."""
        wrist = frame.points[wrist_name]
        nose = frame.points["nose"]
        return abs(wrist.x - nose.x) / shoulder_width

    def _leg_reach(
        self,
        frame: PoseFrame,
        ankle_name: str,
        shoulder_width: float,
    ) -> float:
        """Measure ankle extension relative to the hip centre."""
        hip_x, _ = _midpoint(frame, "left_hip", "right_hip")
        ankle = frame.points[ankle_name]
        return abs(ankle.x - hip_x) / shoulder_width

    def _detect_fall(
        self,
        frame: PoseFrame,
        shoulder_width: float,
    ) -> Detection | None:
        """Detect a body orientation that is predominantly horizontal."""
        shoulder_x, shoulder_y = _midpoint(
            frame,
            "left_shoulder",
            "right_shoulder",
        )
        hip_x, hip_y = _midpoint(
            frame,
            "left_hip",
            "right_hip",
        )

        torso_dx = abs(hip_x - shoulder_x)
        torso_dy = abs(hip_y - shoulder_y)
        torso_length = hypot(torso_dx, torso_dy)

        if torso_length < 0.05:
            return None

        horizontal_ratio = torso_dx / max(torso_dy, 0.02)

        ankles_y = (
            frame.points["left_ankle"].y
            + frame.points["right_ankle"].y
        ) / 2

        body_vertical_span = abs(ankles_y - shoulder_y)
        compact_vertical_body = body_vertical_span < shoulder_width * 2.0

        if horizontal_ratio > 1.25 and compact_vertical_body:
            confidence = _clamp(
                0.68 + horizontal_ratio * 0.08,
                0.0,
                0.96,
            )

            return Detection(
                Pattern.FALL,
                confidence,
                0.90,
                [
                    f"torso horizontal ratio {horizontal_ratio:.2f}",
                    "body has reduced vertical height",
                ],
            )

        return None

    def _detect_punch(
        self,
        frame: PoseFrame,
        old: PoseFrame,
        dt: float,
        shoulder_width: float,
    ) -> Detection | None:
        """Detect rapid left- or right-arm extension."""
        old_shoulder_width = max(
            _distance(old, "left_shoulder", "right_shoulder"),
            0.05,
        )

        candidates: list[tuple[str, float, float]] = []

        for side in ("left", "right"):
            wrist_name = f"{side}_wrist"

            current_reach = self._arm_reach(
                frame,
                wrist_name,
                shoulder_width,
            )

            old_reach = self._arm_reach(
                old,
                wrist_name,
                old_shoulder_width,
            )

            extension_speed = (current_reach - old_reach) / dt
            candidates.append((side, current_reach, extension_speed))

        side, reach, speed = max(
            candidates,
            key=lambda item: item[2],
        )

        if reach > 1.45 and speed > 0.90:
            confidence = _clamp(
                0.58 + (reach - 1.45) * 0.12 + speed * 0.06,
                0.0,
                0.98,
            )

            return Detection(
                Pattern.PUNCH,
                confidence,
                0.88,
                [
                    f"{side} arm rapidly extended",
                    f"arm reach {reach:.2f}x shoulder width",
                    f"extension speed {speed:.2f}/s",
                ],
            )

        return None

    def _detect_kick(
        self,
        frame: PoseFrame,
        old: PoseFrame | None,
        dt: float,
        shoulder_width: float,
    ) -> Detection | None:
        """Detect an extended and elevated leg."""
        _, hips_y = _midpoint(frame, "left_hip", "right_hip")

        old_shoulder_width = shoulder_width

        if old is not None:
            old_shoulder_width = max(
                _distance(old, "left_shoulder", "right_shoulder"),
                0.05,
            )

        candidates: list[tuple[str, float, float, bool]] = []

        for side in ("left", "right"):
            ankle_name = f"{side}_ankle"
            ankle = frame.points[ankle_name]

            reach = self._leg_reach(
                frame,
                ankle_name,
                shoulder_width,
            )

            elevated = ankle.y < hips_y + shoulder_width * 2.2
            speed = 0.0

            if old is not None:
                old_reach = self._leg_reach(
                    old,
                    ankle_name,
                    old_shoulder_width,
                )
                speed = (reach - old_reach) / dt

            candidates.append((side, reach, speed, elevated))

        side, reach, speed, elevated = max(
            candidates,
            key=lambda item: item[1],
        )

        dynamic_kick = reach > 1.35 and speed > 0.65 and elevated
        strong_extended_kick = reach > 1.85 and elevated

        if dynamic_kick or strong_extended_kick:
            confidence = _clamp(
                0.60 + (reach - 1.35) * 0.14 + max(speed, 0.0) * 0.05,
                0.0,
                0.96,
            )

            return Detection(
                Pattern.KICK,
                confidence,
                0.90,
                [
                    f"{side} leg extended",
                    f"leg reach {reach:.2f}x shoulder width",
                    f"leg extension speed {speed:.2f}/s",
                    "ankle elevated",
                ],
            )

        return None

    def _detect_rapid_approach(
        self,
        frame: PoseFrame,
        old: PoseFrame,
        dt: float,
    ) -> Detection | None:
        """Estimate rapid movement toward the camera from body scale."""
        current_scale = max(_body_scale(frame), 0.05)
        old_scale = max(_body_scale(old), 0.05)
        scale_growth = (current_scale - old_scale) / old_scale
        relative_scale_speed = scale_growth / dt

        # Shoulder-only jitter frequently looked like an approach. Requiring
        # the complete torso to grow by at least 6% makes the signal stable.
        if scale_growth > 0.06 and relative_scale_speed > 0.80:
            confidence = _clamp(
                0.56 + scale_growth * 1.6 + relative_scale_speed * 0.08,
                0.0,
                0.94,
            )

            return Detection(
                Pattern.RAPID_APPROACH,
                confidence,
                0.72,
                [
                    "body scale increased rapidly",
                    f"torso scale growth {scale_growth * 100:.1f}%",
                    f"relative approach speed "
                    f"{relative_scale_speed:.2f}/s",
                ],
            )

        return None

    def _detect_guard(
        self,
        frame: PoseFrame,
        shoulder_width: float,
    ) -> Detection | None:
        """Detect both hands positioned close to the face."""
        nose = frame.points["nose"]

        left_wrist = frame.points["left_wrist"]
        right_wrist = frame.points["right_wrist"]

        left_distance = hypot(
            left_wrist.x - nose.x,
            left_wrist.y - nose.y,
        ) / shoulder_width

        right_distance = hypot(
            right_wrist.x - nose.x,
            right_wrist.y - nose.y,
        ) / shoulder_width

        both_hands_near_face = (
            left_distance < 1.30
            and right_distance < 1.30
        )

        one_hand_very_close = min(
            left_distance,
            right_distance,
        ) < 0.65

        if both_hands_near_face or one_hand_very_close:
            average_distance = (left_distance + right_distance) / 2

            confidence = _clamp(
                0.90 - average_distance * 0.20,
                0.55,
                0.92,
            )

            evidence = [
                f"left wrist-face distance {left_distance:.2f}",
                f"right wrist-face distance {right_distance:.2f}",
            ]

            if both_hands_near_face:
                evidence.append("both hands raised near face")
            else:
                evidence.append("one hand held very close to face")

            return Detection(
                Pattern.GUARD,
                confidence,
                0.30,
                evidence,
            )

        return None

    def update(self, frame: PoseFrame) -> Detection:
        """Analyze a new pose and return the highest-priority pattern."""
        if not self.REQUIRED.issubset(frame.points):
            return Detection(
                Pattern.NEUTRAL,
                0.0,
                0.0,
                ["pose incomplete"],
            )

        self.frames.append(frame)

        shoulder_width = max(
            _distance(
                frame,
                "left_shoulder",
                "right_shoulder",
            ),
            0.05,
        )

        fall = self._detect_fall(frame, shoulder_width)

        if fall is not None:
            return fall

        old: PoseFrame | None = None
        dt = 0.01

        if len(self.frames) >= 3:
            old = self.frames[-3]
            dt = max(frame.timestamp - old.timestamp, 0.01)

            punch = self._detect_punch(
                frame,
                old,
                dt,
                shoulder_width,
            )

            if punch is not None:
                return punch

        kick = self._detect_kick(
            frame,
            old,
            dt,
            shoulder_width,
        )

        if kick is not None:
            return kick

        if old is not None:
            approach = self._detect_rapid_approach(
                frame,
                old,
                dt,
            )

            if approach is not None:
                return approach

        guard = self._detect_guard(
            frame,
            shoulder_width,
        )

        if guard is not None:
            return guard

        return Detection(
            Pattern.NEUTRAL,
            0.78,
            0.05,
            ["no risk-pattern threshold crossed"],
        )
