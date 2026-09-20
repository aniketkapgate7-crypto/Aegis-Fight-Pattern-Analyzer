from aegis.models import Pattern, Point, PoseFrame
from aegis.patterns import PatternEngine


def make_pose(timestamp: float = 0.0, **changes) -> PoseFrame:
    points = {
        "nose": Point(0.50, 0.20),
        "left_shoulder": Point(0.40, 0.35),
        "right_shoulder": Point(0.60, 0.35),
        "left_wrist": Point(0.25, 0.55),
        "right_wrist": Point(0.75, 0.55),
        "left_hip": Point(0.44, 0.62),
        "right_hip": Point(0.56, 0.62),
        "left_ankle": Point(0.44, 0.92),
        "right_ankle": Point(0.56, 0.92),
    }

    points.update(changes)
    return PoseFrame(timestamp, points)


def test_neutral_pose() -> None:
    engine = PatternEngine()
    result = engine.update(make_pose())

    assert result.pattern == Pattern.NEUTRAL
    assert result.threat <= 0.10


def test_incomplete_pose_fails_safe() -> None:
    engine = PatternEngine()

    incomplete = PoseFrame(
        0.0,
        {
            "nose": Point(0.50, 0.20),
        },
    )

    result = engine.update(incomplete)

    assert result.pattern == Pattern.NEUTRAL
    assert result.confidence == 0.0
    assert "pose incomplete" in result.evidence


def test_fast_right_arm_extension_is_punch() -> None:
    engine = PatternEngine()

    engine.update(
        make_pose(
            0.0,
            right_wrist=Point(0.58, 0.34),
        )
    )

    engine.update(
        make_pose(
            0.1,
            right_wrist=Point(0.70, 0.34),
        )
    )

    result = engine.update(
        make_pose(
            0.2,
            right_wrist=Point(0.93, 0.34),
        )
    )

    assert result.pattern == Pattern.PUNCH
    assert result.threat >= 0.80
    assert any("right arm" in item for item in result.evidence)


def test_fast_left_arm_extension_is_punch() -> None:
    engine = PatternEngine()

    engine.update(
        make_pose(
            0.0,
            left_wrist=Point(0.42, 0.34),
        )
    )

    engine.update(
        make_pose(
            0.1,
            left_wrist=Point(0.30, 0.34),
        )
    )

    result = engine.update(
        make_pose(
            0.2,
            left_wrist=Point(0.07, 0.34),
        )
    )

    assert result.pattern == Pattern.PUNCH
    assert result.threat >= 0.80
    assert any("left arm" in item for item in result.evidence)


def test_guard_with_both_hands_near_face() -> None:
    engine = PatternEngine()

    result = engine.update(
        make_pose(
            left_wrist=Point(0.44, 0.27),
            right_wrist=Point(0.56, 0.27),
        )
    )

    assert result.pattern == Pattern.GUARD
    assert result.threat < 0.50


def test_extended_elevated_leg_is_kick() -> None:
    engine = PatternEngine()

    result = engine.update(
        make_pose(
            right_ankle=Point(0.95, 0.60),
        )
    )

    assert result.pattern == Pattern.KICK
    assert result.threat >= 0.80
    assert any("right leg" in item for item in result.evidence)


def test_horizontal_body_is_fall() -> None:
    engine = PatternEngine()

    result = engine.update(
        make_pose(
            left_shoulder=Point(0.20, 0.44),
            right_shoulder=Point(0.40, 0.44),
            left_hip=Point(0.60, 0.47),
            right_hip=Point(0.72, 0.47),
            left_ankle=Point(0.78, 0.52),
            right_ankle=Point(0.88, 0.52),
        )
    )

    assert result.pattern == Pattern.FALL
    assert result.threat >= 0.80


def test_increasing_body_scale_is_rapid_approach() -> None:
    engine = PatternEngine()

    engine.update(
        make_pose(
            0.0,
            left_shoulder=Point(0.40, 0.35),
            right_shoulder=Point(0.60, 0.35),
        )
    )

    engine.update(
        make_pose(
            0.1,
            left_shoulder=Point(0.375, 0.35),
            right_shoulder=Point(0.625, 0.35),
        )
    )

    result = engine.update(
        make_pose(
            0.2,
            left_shoulder=Point(0.35, 0.35),
            right_shoulder=Point(0.65, 0.35),
        )
    )

    assert result.pattern == Pattern.RAPID_APPROACH
    assert result.threat >= 0.65


def test_normal_shoulder_jitter_does_not_trigger_rapid_approach() -> None:
    engine = PatternEngine()

    engine.update(
        make_pose(
            0.0,
            left_shoulder=Point(0.40, 0.35),
            right_shoulder=Point(0.60, 0.35),
        )
    )
    engine.update(
        make_pose(
            0.1,
            left_shoulder=Point(0.398, 0.35),
            right_shoulder=Point(0.602, 0.35),
        )
    )
    result = engine.update(
        make_pose(
            0.2,
            left_shoulder=Point(0.40, 0.35),
            right_shoulder=Point(0.60, 0.35),
        )
    )

    assert result.pattern != Pattern.RAPID_APPROACH
    assert result.pattern == Pattern.NEUTRAL


def test_small_body_scale_change_does_not_trigger_rapid_approach() -> None:
    engine = PatternEngine()

    # 2.5% scale growth (below the 6% threshold required for rapid approach)
    engine.update(
        make_pose(
            0.0,
            left_shoulder=Point(0.40, 0.35),
            right_shoulder=Point(0.60, 0.35),
        )
    )
    engine.update(
        make_pose(
            0.1,
            left_shoulder=Point(0.398, 0.35),
            right_shoulder=Point(0.602, 0.35),
        )
    )
    result = engine.update(
        make_pose(
            0.2,
            left_shoulder=Point(0.395, 0.35),
            right_shoulder=Point(0.605, 0.35),
        )
    )

    assert result.pattern != Pattern.RAPID_APPROACH
    assert result.pattern == Pattern.NEUTRAL


def test_threat_and_confidence_values_remain_bounded() -> None:
    engine = PatternEngine()

    test_poses = [
        make_pose(),
        make_pose(right_wrist=Point(0.95, 0.34)),
        make_pose(left_wrist=Point(0.44, 0.27), right_wrist=Point(0.56, 0.27)),
        make_pose(right_ankle=Point(0.95, 0.60)),
        make_pose(
            left_shoulder=Point(0.20, 0.44),
            right_shoulder=Point(0.40, 0.44),
            left_hip=Point(0.60, 0.47),
            right_hip=Point(0.72, 0.47),
            left_ankle=Point(0.78, 0.52),
            right_ankle=Point(0.88, 0.52),
        ),
    ]

    for pose in test_poses:
        result = engine.update(pose)
        assert 0.0 <= result.threat <= 1.0, f"Threat out of range: {result.threat}"
        assert 0.0 <= result.confidence <= 1.0, f"Confidence out of range: {result.confidence}"


def test_missing_model_produces_clear_runtime_error() -> None:
    import pytest
    from aegis.runtime import SnapdragonSession

    session = SnapdragonSession(model_path="models/nonexistent_model_xyz.onnx")
    with pytest.raises(FileNotFoundError) as exc_info:
        session.initialize()

    assert "Model not found" in str(exc_info.value)


def test_cpu_fallback_runtime_status_is_truthful() -> None:
    from aegis.runtime import SnapdragonSession

    session = SnapdragonSession(prefer_qnn=True)
    provider = session.initialize()

    # Truthful check: MediaPipe CPU is always reported as active landmark engine
    assert provider == "MediaPipe CPU"
    diag = session.get_diagnostics()
    assert diag.active_pose_provider == "MediaPipe CPU"
    assert diag.active_inference_provider == "MediaPipe CPU"
    assert diag.qnn_pose_active is False
    assert "MediaPipe" in diag.notes


def test_incident_tracker_rearming_and_deduplication() -> None:
    from aegis.app import IncidentTracker

    tracker = IncidentTracker(
        threat_threshold=0.70,
        reset_threshold=0.40,
        log_interval=1.0,
    )

    # 1. Not recording -> should not log even with high threat
    assert not tracker.should_log(threat=0.85, recording=False, current_time=0.0)

    # 2. Recording active, high threat -> logs first incident
    assert tracker.should_log(threat=0.85, recording=True, current_time=1.0)
    count = tracker.record_incident(current_time=1.0)
    assert count == 1
    assert not tracker.armed

    # 3. Threat remains high shortly after -> deduplication blocks repeated log
    assert not tracker.should_log(threat=0.90, recording=True, current_time=1.5)

    # 4. Threat remains high past interval -> still blocked until re-armed
    assert not tracker.should_log(threat=0.90, recording=True, current_time=3.0)

    # 5. Threat drops below reset threshold -> re-arms
    assert not tracker.should_log(threat=0.30, recording=True, current_time=3.5)
    assert tracker.armed

    # 6. New high-threat event -> logs second incident
    assert tracker.should_log(threat=0.88, recording=True, current_time=4.0)
    count2 = tracker.record_incident(current_time=4.0)
    assert count2 == 2


def test_keyboard_control_mapping() -> None:
    from aegis.app import handle_keypress

    # Exit keys
    assert handle_keypress(ord("q")) == "exit"
    assert handle_keypress(ord("Q")) == "exit"
    assert handle_keypress(27) == "exit"  # Esc key

    # Record toggle keys
    assert handle_keypress(ord("r")) == "toggle_recording"
    assert handle_keypress(ord("R")) == "toggle_recording"
    assert handle_keypress(ord(" ")) == "toggle_recording"  # Space key
    assert handle_keypress(32) == "toggle_recording"

    # Unmapped keys
    assert handle_keypress(ord("a")) is None
    assert handle_keypress(ord("x")) is None
    assert handle_keypress(-1) is None


def test_pattern_priority_behaviour() -> None:
    engine = PatternEngine()

    # Create a pose that matches both Fall criteria (horizontal body)
    # and has an extended arm. Fall has higher priority than limb reach.
    fall_pose = make_pose(
        0.0,
        left_shoulder=Point(0.20, 0.44),
        right_shoulder=Point(0.40, 0.44),
        left_hip=Point(0.60, 0.47),
        right_hip=Point(0.72, 0.47),
        left_ankle=Point(0.78, 0.52),
        right_ankle=Point(0.88, 0.52),
        right_wrist=Point(0.95, 0.44),
    )

    result = engine.update(fall_pose)
    assert result.pattern == Pattern.FALL
    assert result.threat >= 0.80


def test_low_visibility_or_unreliable_landmarks_fail_safely() -> None:
    import numpy as np
    from aegis.ui import draw_pose

    # Low visibility (< 0.40) landmarks should not crash drawing routines
    low_vis_pose = make_pose(
        0.0,
        nose=Point(0.50, 0.20, visibility=0.10),
        right_wrist=Point(0.75, 0.55, visibility=0.20),
        left_ankle=Point(0.44, 0.92, visibility=0.05),
    )
    frame = np.zeros((540, 960, 3), dtype=np.uint8)
    draw_pose(frame, low_vis_pose)

    # Incomplete landmarks fail safely in pattern engine
    engine = PatternEngine()
    incomplete_pose = PoseFrame(0.0, {"nose": Point(0.5, 0.2)})
    result = engine.update(incomplete_pose)
    assert result.pattern == Pattern.NEUTRAL
    assert result.confidence == 0.0
    assert "pose incomplete" in result.evidence