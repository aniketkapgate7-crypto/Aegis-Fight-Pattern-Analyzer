from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Pattern(str, Enum):
    NEUTRAL = "neutral"
    GUARD = "guard"
    PUNCH = "punch-like extension"
    KICK = "kick-like extension"
    RAPID_APPROACH = "rapid approach"
    FALL = "fall-like posture"


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    visibility: float = 1.0


@dataclass
class PoseFrame:
    timestamp: float
    points: dict[str, Point]


@dataclass
class Detection:
    pattern: Pattern
    confidence: float
    threat: float
    evidence: list[str] = field(default_factory=list)
