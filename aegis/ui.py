from __future__ import annotations

from collections.abc import Sequence

import cv2
import numpy as np

from .models import Detection, Pattern, PoseFrame

CONNECTIONS = [
    ("left_shoulder", "right_shoulder"), ("left_shoulder", "left_wrist"),
    ("right_shoulder", "right_wrist"), ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"), ("left_hip", "right_hip"),
    ("left_hip", "left_ankle"), ("right_hip", "right_ankle"),
]

CYAN = (255, 224, 0)
CYAN_DIM = (125, 88, 0)
WHITE = (245, 248, 250)
GREY = (165, 180, 188)
DARK = (7, 15, 20)
PANEL = (10, 25, 31)
GREEN = (70, 245, 85)
ORANGE = (0, 185, 255)
RED = (40, 55, 245)
FONT = cv2.FONT_HERSHEY_DUPLEX


def _clamp(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


def threat_color(threat: float) -> tuple[int, int, int]:
    if threat < 0.40:
        return GREEN
    if threat < 0.75:
        return ORANGE
    return RED


def threat_label(threat: float) -> str:
    if threat < 0.25:
        return "LOW"
    if threat < 0.50:
        return "ELEVATED"
    if threat < 0.75:
        return "HIGH"
    return "CRITICAL"


def pattern_name(pattern: Pattern) -> str:
    names = {
        Pattern.NEUTRAL: "NEUTRAL", Pattern.GUARD: "GUARD",
        Pattern.PUNCH: "PUNCH", Pattern.KICK: "KICK",
        Pattern.RAPID_APPROACH: "RAPID APPROACH",
        Pattern.FALL: "FALL DETECTED",
    }
    return names.get(pattern, pattern.value.upper())


def _text(frame, value, position, scale, color=WHITE, thickness=1) -> None:
    # A one-pixel shadow keeps thin geometric text readable on video.
    shadow_position = (position[0] + 1, position[1] + 1)
    cv2.putText(frame, value, shadow_position, FONT, scale,
                (2, 7, 9), max(1, thickness), cv2.LINE_AA)
    cv2.putText(frame, value, position, FONT, scale,
                color, thickness, cv2.LINE_AA)


def _panel_points(x1: int, y1: int, x2: int, y2: int, cut: int = 12):
    return np.array([
        [x1 + cut, y1], [x2 - cut, y1], [x2, y1 + cut],
        [x2, y2 - cut], [x2 - cut, y2], [x1 + cut, y2],
        [x1, y2 - cut], [x1, y1 + cut],
    ], dtype=np.int32)


def draw_panel(frame, bounds, opacity=0.86, color=CYAN, cut=12) -> None:
    points = _panel_points(*bounds, cut=cut)
    overlay = frame.copy()
    cv2.fillPoly(overlay, [points], PANEL, cv2.LINE_AA)
    cv2.addWeighted(overlay, opacity, frame, 1.0 - opacity, 0, frame)
    cv2.polylines(frame, [points], True, color, 1, cv2.LINE_AA)
    x1, y1, x2, y2 = bounds
    cv2.line(frame, (x1 + cut, y1 + 3), (x1 + cut + 28, y1 + 3), color, 2)
    cv2.line(frame, (x2 - cut, y2 - 3), (x2 - cut - 28, y2 - 3), color, 2)


def _fit_text(text: str, max_width: int, initial: float, thickness: int = 1) -> float:
    scale = initial
    while scale > 0.22:
        measured = cv2.getTextSize(text, FONT, scale, thickness)[0][0]
        if measured <= max_width:
            return scale
        scale -= 0.04
    return 0.22


def draw_pose(frame: np.ndarray, pose: PoseFrame) -> None:
    height, width = frame.shape[:2]
    for first_name, second_name in CONNECTIONS:
        if first_name not in pose.points or second_name not in pose.points:
            continue
        first, second = pose.points[first_name], pose.points[second_name]
        if first.visibility < 0.40 or second.visibility < 0.40:
            continue
        a = (int(first.x * width), int(first.y * height))
        b = (int(second.x * width), int(second.y * height))
        cv2.line(frame, a, b, CYAN, 2, cv2.LINE_AA)
    for point in pose.points.values():
        if point.visibility < 0.40:
            continue
        position = (int(point.x * width), int(point.y * height))
        cv2.circle(frame, position, 6, DARK, -1, cv2.LINE_AA)
        cv2.circle(frame, position, 3, CYAN, -1, cv2.LINE_AA)


def draw_targeting_reticle(frame: np.ndarray, pose: PoseFrame | None) -> None:
    if pose is None or "nose" not in pose.points:
        return
    height, width = frame.shape[:2]
    nose = pose.points["nose"]
    x, y = int(nose.x * width), int(nose.y * height)
    cv2.circle(frame, (x, y), 6, DARK, -1, cv2.LINE_AA)
    cv2.circle(frame, (x, y), 5, CYAN, 2, cv2.LINE_AA)
    cv2.circle(frame, (x, y), 2, WHITE, -1, cv2.LINE_AA)
    for a, b in [((x - 16, y), (x - 8, y)), ((x + 8, y), (x + 16, y)),
                 ((x, y - 16), (x, y - 8)), ((x, y + 8), (x, y + 16))]:
        cv2.line(frame, a, b, CYAN, 1, cv2.LINE_AA)


def draw_viewfinder(frame: np.ndarray, top: int, bottom: int) -> None:
    width = frame.shape[1]
    for x, direction in ((14, 1), (width - 14, -1)):
        cv2.line(frame, (x, top), (x + direction * 36, top), CYAN, 2)
        cv2.line(frame, (x, top), (x, top + 36), CYAN, 2)
        cv2.line(frame, (x, bottom), (x + direction * 36, bottom), CYAN, 2)
        cv2.line(frame, (x, bottom), (x, bottom - 36), CYAN, 2)


def draw_timeline(frame, history, x, y, width, active) -> None:
    segments, gap = 30, 3
    segment_width = max(4, (width - 29 * gap) // segments)
    recent = list(history)[-segments:]
    values = [None] * (segments - len(recent)) + recent
    for index, item in enumerate(values):
        left = x + index * (segment_width + gap)
        fill = (52, 79, 89) if item is None else threat_color(item.threat)
        cv2.rectangle(frame, (left, y), (left + segment_width, y + 12), fill, -1)
    marker_x = x + width - 1
    cv2.line(frame, (marker_x, y - 3), (marker_x, y + 16), threat_color(active.threat), 1)


def draw_metric_card(frame, bounds, value, label, color=WHITE) -> None:
    draw_panel(frame, bounds, opacity=0.90, cut=8)
    x1, y1, x2, _ = bounds
    max_width = x2 - x1 - 16
    scale = _fit_text(value, max_width, 0.44, 1)
    value_width = cv2.getTextSize(value, FONT, scale, 1)[0][0]
    _text(frame, value, (x1 + (x2 - x1 - value_width) // 2, y1 + 27), scale, color, 1)
    label_scale = _fit_text(label, max_width, 0.26)
    label_width = cv2.getTextSize(label, FONT, label_scale, 1)[0][0]
    _text(frame, label, (x1 + (x2 - x1 - label_width) // 2, y1 + 47), label_scale, GREY)


def draw_threat_gauge(frame, threat, x, y, width) -> None:
    value, color = _clamp(threat), threat_color(threat)
    cv2.rectangle(frame, (x, y), (x + width, y + 16), (26, 55, 64), -1)
    cv2.rectangle(frame, (x, y), (x + int(width * value), y + 16), color, -1)
    cv2.rectangle(frame, (x, y), (x + width, y + 16), (140, 225, 232), 1)
    for index in range(1, 10):
        marker = x + int(width * index / 10)
        cv2.line(frame, (marker, y + 20), (marker, y + 27), CYAN_DIM, 1)


def draw_hud(
    frame: np.ndarray,
    pose: PoseFrame | None,
    detection: Detection,
    fps: float,
    latency_ms: float,
    provider: str,
    history: Sequence[Detection] | None = None,
    recording: bool = False,
    incident_count: int = 0,
) -> np.ndarray:
    height, width = frame.shape[:2]
    if width < 720 or height < 400:
        raise ValueError("AEGIS CORE HUD requires a display of at least 720x400")

    color = threat_color(detection.threat)
    timeline_bottom, footer_top, card_top = 104, height - 38, height - 112
    if pose is not None:
        draw_pose(frame, pose)
    draw_targeting_reticle(frame, pose)
    draw_viewfinder(frame, timeline_bottom + 14, card_top - 10)

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, timeline_bottom), DARK, -1)
    cv2.rectangle(overlay, (0, footer_top), (width, height), DARK, -1)
    cv2.addWeighted(overlay, 0.91, frame, 0.09, 0, frame)
    cv2.line(frame, (0, timeline_bottom), (width, timeline_bottom), CYAN, 1)
    cv2.line(frame, (0, footer_top), (width, footer_top), CYAN, 1)

    margin = 6
    brand_right = int(width * 0.31)
    state_left, state_right = brand_right + 6, int(width * 0.61)
    metrics_left, metric_gap = state_right + 6, 6
    metric_width = (width - metrics_left - margin - metric_gap * 2) // 3

    draw_panel(frame, (margin, 5, brand_right, 65), opacity=0.92)
    _text(frame, "AEGIS CORE", (24, 34), 0.66, CYAN, 1)
    _text(frame, "AEGIS COMBAT ANALYSIS", (24, 55), 0.29, WHITE)

    draw_panel(frame, (state_left, 5, state_right, 65), opacity=0.92)
    _text(frame, "/// CURRENT STATE", (state_left + 20, 23), 0.28, CYAN)
    state = pattern_name(detection.pattern)
    state_scale = _fit_text(state, state_right - state_left - 30, 0.72, 2)
    state_width = cv2.getTextSize(state, FONT, state_scale, 2)[0][0]
    _text(frame, state, (state_left + (state_right - state_left - state_width) // 2, 54), state_scale, color, 2)

    metric_x = metrics_left
    draw_metric_card(frame, (metric_x, 5, metric_x + metric_width, 65), f"{fps:.1f} FPS", "FRAME RATE", CYAN)
    metric_x += metric_width + metric_gap
    draw_metric_card(frame, (metric_x, 5, metric_x + metric_width, 65), f"{latency_ms:.1f} ms", "INFERENCE")
    metric_x += metric_width + metric_gap
    if provider == "MediaPipe CPU":
        provider_text = "MediaPipe CPU"
    else:
        provider_text = str(provider).replace("ExecutionProvider", "").replace("Provider", "").strip()
    draw_metric_card(frame, (metric_x, 5, width - margin, 65), provider_text, "ENGINE", CYAN)

    _text(frame, "MOTION PATTERN TIMELINE", (18, 94), 0.30, WHITE)
    timeline_x = min(220, int(width * 0.23))
    timeline_width = width - timeline_x - 174
    draw_timeline(frame, history or [], timeline_x, 80, timeline_width, detection)
    cv2.rectangle(frame, (width - 154, 81), (width - 143, 92), GREEN, -1)
    _text(frame, "NEUTRAL", (width - 137, 93), 0.31, WHITE)
    cv2.rectangle(frame, (width - 70, 81), (width - 59, 92), (48, 91, 107), -1)
    _text(frame, "OTHER", (width - 53, 93), 0.31, WHITE)

    left = (12, card_top, int(width * 0.46), footer_top - 7)
    right = (int(width * 0.48), card_top, width - 12, footer_top - 7)
    draw_panel(frame, left, opacity=0.88)
    draw_panel(frame, right, opacity=0.88)

    lx1, ly1, lx2, _ = left
    _text(frame, "LIVE ANALYSIS", (lx1 + 50, ly1 + 27), 0.40, CYAN)
    cv2.circle(frame, (lx1 + 27, ly1 + 48), 13, color, 2, cv2.LINE_AA)
    cv2.line(frame, (lx1 + 20, ly1 + 48), (lx1 + 25, ly1 + 53), color, 2)
    cv2.line(frame, (lx1 + 25, ly1 + 53), (lx1 + 34, ly1 + 42), color, 2)
    evidence = detection.evidence[0] if detection.evidence else "No motion evidence available"
    evidence_scale = _fit_text(evidence, lx2 - lx1 - 70, 0.34)
    _text(frame, evidence[:62], (lx1 + 50, ly1 + 56), evidence_scale, WHITE)

    rx1, ry1, rx2, _ = right
    _text(frame, "THREAT ASSESSMENT", (rx1 + 24, ry1 + 27), 0.37, CYAN)
    percentage = f"{_clamp(detection.threat) * 100:.0f}%"
    pct_width = cv2.getTextSize(percentage, FONT, 0.64, 2)[0][0]
    label = threat_label(detection.threat)
    label_width = cv2.getTextSize(label, FONT, 0.38, 1)[0][0]
    _text(frame, label, (rx2 - pct_width - label_width - 44, ry1 + 56), 0.38, color, 1)
    _text(frame, percentage, (rx2 - pct_width - 16, ry1 + 57), 0.64, color, 2)
    gauge_width = max(120, rx2 - rx1 - pct_width - label_width - 86)
    draw_threat_gauge(frame, detection.threat, rx1 + 24, ry1 + 41, gauge_width)

    record_color = RED if recording else (110, 120, 125)
    cv2.circle(frame, (24, height - 19), 7, record_color, -1, cv2.LINE_AA)
    _text(frame, "RECORDING ACTIVE" if recording else "RECORDING OFF", (39, height - 13), 0.30, WHITE)
    _text(frame, f"INCIDENTS {incident_count:02d}", (238, height - 13), 0.30, WHITE)
    _text(frame, "R / SPACE", (width - 240, height - 13), 0.32, CYAN, 1)
    _text(frame, "RECORD", (width - 168, height - 13), 0.28, WHITE)
    _text(frame, "Q / ESC", (width - 105, height - 13), 0.32, CYAN, 1)
    _text(frame, "EXIT", (width - 50, height - 13), 0.28, WHITE)
    return frame
