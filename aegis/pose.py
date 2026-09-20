from __future__ import annotations

from .models import Point, PoseFrame

LANDMARKS = {
    "nose": 0, "left_shoulder": 11, "right_shoulder": 12,
    "left_wrist": 15, "right_wrist": 16, "left_hip": 23,
    "right_hip": 24, "left_ankle": 27, "right_ankle": 28,
}


class MediaPipePoseEstimator:
    def __init__(self) -> None:
        import mediapipe as mp
        self._pose = mp.solutions.pose.Pose(model_complexity=1, min_detection_confidence=0.55, min_tracking_confidence=0.55)

    def estimate(self, bgr_frame, timestamp: float) -> PoseFrame | None:
        import cv2
        result = self._pose.process(cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB))
        if not result.pose_landmarks:
            return None
        landmarks = result.pose_landmarks.landmark
        points = {name: Point(landmarks[i].x, landmarks[i].y, landmarks[i].visibility) for name, i in LANDMARKS.items()}
        return PoseFrame(timestamp, points)

    def close(self) -> None:
        self._pose.close()
