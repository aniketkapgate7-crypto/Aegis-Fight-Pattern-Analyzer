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