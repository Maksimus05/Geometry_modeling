"""Геометрия отрезка и преобразования координат."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    x: float
    y: float

    def polar(self) -> tuple[float, float]:
        """Возвращает (r, theta_rad) относительно начала координат."""
        r = math.hypot(self.x, self.y)
        theta = math.atan2(self.y, self.x)
        return r, theta

    @staticmethod
    def from_polar(r: float, theta_rad: float) -> Point:
        return Point(r * math.cos(theta_rad), r * math.sin(theta_rad))


@dataclass
class Segment:
    p1: Point
    p2: Point

    @property
    def length(self) -> float:
        return math.hypot(self.p2.x - self.p1.x, self.p2.y - self.p1.y)

    @property
    def inclination_rad(self) -> float:
        return math.atan2(self.p2.y - self.p1.y, self.p2.x - self.p1.x)


def to_degrees(radians: float) -> float:
    return math.degrees(radians)


def to_radians(degrees: float) -> float:
    return math.radians(degrees)


def format_angle(radians: float, degrees_mode: bool, precision: int = 3) -> str:
    if degrees_mode:
        return f"{to_degrees(radians):.{precision}f}°"
    return f"{radians:.{precision}f} рад"
